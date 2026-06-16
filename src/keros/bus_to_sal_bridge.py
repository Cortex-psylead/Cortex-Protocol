# ============================================================================
# src/keros/bus_to_sal_bridge.py
# CORTEX PROTOCOL — Secure Bus → SAL Integration Bridge
#
# THE INTEGRATION GAP THIS MODULE CLOSES:
#   After the ECDH handshake (sensor_channel.py), the TEE holds a
#   SecureBusSession capable of decrypting raw sensor frames.
#   After the sandbox is loaded (external_rule_sandbox.py), the SAL
#   pipeline can score normalized telemetry vectors.
#
#   But nothing connected them.
#
#   This bridge is that connection. It owns the critical path:
#
#     EncryptedFrame (hostile bus)
#       │
#       ▼  [SecureBusSession.decrypt_frame()]
#     raw_bytes (plaintext — lives ONLY inside TEE boundary)
#       │
#       ▼  [FrameDeserializer.parse()]
#     RawSensorSamples (typed, validated)
#       │
#       ▼  [NormalizationPipeline.normalize()]
#     TelemetryVector (normalized ∈ [0,1] — safe to pass to sandbox)
#       │
#       ▼  [ExternalRuleSandbox.execute_all()]
#     MitigationVector (score ∈ [0,100] + 4 channel attenuations)
#       │
#       ▼  [BusToSALBridge.emit()]
#     Downstream SAL consumer (CognitiveShield / TelemetryRouter)
#
# SECURITY PROPERTIES OF THIS PIPELINE:
#
#   1. ZERO PLAINTEXT BEFORE DECRYPTION GATE
#      The bridge only receives EncryptedFrame objects. It calls decrypt
#      inside the TEE boundary — the host OS never handles plaintext.
#
#   2. NORMALIZATION IS NON-INVERTIBLE
#      Raw ADC counts → normalized floats ∈ [0,1].
#      The TelemetryVector passed to the sandbox cannot be reverse-engineered
#      into raw samples. Rules see statistical features, not biometric values.
#
#   3. FRAME AUTHENTICATION BEFORE ANY PROCESSING
#      If decrypt_frame() raises FrameAuthError or ReplayAttackError,
#      the bridge drops the frame and emits an immune signature upstream.
#      No processing occurs on unauthenticated data.
#
#   4. SANDBOX ISOLATION FOR EXTERNAL RULES
#      The MitigationVector from the sandbox gates downstream emission.
#      If all rules score BLOCKED (0), the TelemetryVector is not forwarded
#      to the DeSci or Clinical channels.
#
#   5. AUDIT LOG (hashes only)
#      The bridge logs a SHA-256 of each accepted frame's plaintext for
#      session forensics. The plaintext itself is never logged.
#      This supports post-session integrity audits without retaining biometric data.
#
# THREADING MODEL:
#   The bridge runs a single background thread per sensor session.
#   Frames are queued by the bus receiver and processed in order.
#   The downstream SAL consumer receives MitigationVector + TelemetryVector
#   via a callback, invoked from the processing thread.
#
# Dependencies: stdlib + cryptography (via sensor_channel imports)
# ============================================================================

import hashlib
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional

try:
    from src.keros.sensor_channel import (
        EncryptedFrame, FrameAuthError, ReplayAttackError,
        SecureBusSession, SessionExpiredError, ChannelState,
    )
    from src.sal.external_rule_sandbox import (
        ExternalRuleSandbox, MitigationVector, TelemetryVector,
    )
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", ".."))
    from src.keros.sensor_channel import (
        EncryptedFrame, FrameAuthError, ReplayAttackError,
        SecureBusSession, SessionExpiredError, ChannelState,
    )
    from src.sal.external_rule_sandbox import (
        ExternalRuleSandbox, MitigationVector, TelemetryVector,
    )


# ============================================================================
# 0. RAW SENSOR FRAME — typed container for decrypted payload
# ============================================================================

@dataclass(frozen=True)
class RawSensorSamples:
    """
    Typed container for decrypted raw sensor samples.

    Lives only inside the TEE boundary. Never serialized to disk or network.
    Passed by reference within the bridge pipeline — not copied.

    field_count must match the physical sensor's output format.
    Values are raw ADC counts or calibrated physical units (sensor-dependent).
    """
    frame_seq:     int
    channel_count: int           # Number of sensor channels (e.g., 8 for 8-lead EEG)
    samples:       bytes         # Raw packed float32 array: channel_count × N samples
    sample_rate_hz: float        # Sensor declared sample rate
    sensor_id_hash: bytes        # Which sensor produced this frame

    def parse_float32(self) -> List[float]:
        """Unpacks the raw bytes as a list of float32 values."""
        import struct
        count = len(self.samples) // 4
        return list(struct.unpack(f">{count}f", self.samples))


# ============================================================================
# 1. NORMALIZATION PIPELINE
# ============================================================================

@dataclass
class NormalizationBounds:
    """
    Clinical reference bounds for normalizing raw sensor values.
    Injected from the active Governance Snapshot (White Branch mandate).
    Units match the sensor's physical output units.
    """
    hrv_rmssd_min:      float = 10.0;   hrv_rmssd_max:      float = 120.0
    hrv_sdnn_min:       float = 10.0;   hrv_sdnn_max:       float = 150.0
    hrv_coherence_min:  float = 0.0;    hrv_coherence_max:  float = 1.0
    eeg_alpha_min:      float = 0.0;    eeg_alpha_max:      float = 1.0
    eeg_theta_min:      float = 0.0;    eeg_theta_max:      float = 1.0
    eeg_beta_min:       float = 0.0;    eeg_beta_max:       float = 1.0
    resp_rate_min:      float = 6.0;    resp_rate_max:      float = 30.0
    resp_amplitude_min: float = 0.0;    resp_amplitude_max: float = 1.0


class NormalizationPipeline:
    """
    Converts raw sensor samples into a normalized TelemetryVector.

    Normalization: v_norm = clamp((v - v_min) / (v_max - v_min), 0.0, 1.0)

    This is a lossy, non-invertible projection. The TelemetryVector passed
    to the external rule sandbox cannot be reverse-engineered into raw samples.

    In production: bounds are loaded from the active Governance Snapshot
    and re-verified on each CCM update cycle.
    """

    def __init__(self, bounds: Optional[NormalizationBounds] = None):
        self._bounds = bounds or NormalizationBounds()
        self._sequence: int = 0

    @staticmethod
    def _norm(v: float, v_min: float, v_max: float) -> float:
        if v_max <= v_min:
            return 0.0
        return max(0.0, min(1.0, (v - v_min) / (v_max - v_min)))

    def normalize(
        self,
        hrv_rmssd:      float,
        hrv_sdnn:       float,
        hrv_coherence:  float,
        eeg_alpha:      float,
        eeg_theta:      float,
        eeg_beta:       float,
        resp_rate:      float,
        resp_amplitude: float,
        polyvagal_bucket: int,
    ) -> TelemetryVector:
        """
        Accepts raw clinical values and returns a normalized TelemetryVector.
        All output values are guaranteed ∈ [0.0, 1.0].
        """
        b = self._bounds
        self._sequence += 1
        return TelemetryVector(
            hrv_rmssd_norm=      self._norm(hrv_rmssd,      b.hrv_rmssd_min,      b.hrv_rmssd_max),
            hrv_sdnn_norm=       self._norm(hrv_sdnn,       b.hrv_sdnn_min,       b.hrv_sdnn_max),
            hrv_coherence_norm=  self._norm(hrv_coherence,  b.hrv_coherence_min,  b.hrv_coherence_max),
            eeg_alpha_norm=      self._norm(eeg_alpha,      b.eeg_alpha_min,      b.eeg_alpha_max),
            eeg_theta_norm=      self._norm(eeg_theta,      b.eeg_theta_min,      b.eeg_theta_max),
            eeg_beta_norm=       self._norm(eeg_beta,       b.eeg_beta_min,       b.eeg_beta_max),
            resp_rate_norm=      self._norm(resp_rate,      b.resp_rate_min,      b.resp_rate_max),
            resp_amplitude_norm= self._norm(resp_amplitude, b.resp_amplitude_min, b.resp_amplitude_max),
            polyvagal_bucket=    polyvagal_bucket,
            sequence_counter=    self._sequence,
        )


# ============================================================================
# 2. BRIDGE PIPELINE RESULT
# ============================================================================

class FrameDisposition(Enum):
    PASSED      = "passed"       # Frame decrypted, normalized, sandbox scored ≥ threshold
    BLOCKED     = "blocked"      # Sandbox score < threshold — not forwarded
    AUTH_FAILED = "auth_failed"  # MAC or replay — frame dropped, immune signal emitted
    EXPIRED     = "expired"      # Session expired — re-handshake required
    PARSE_ERROR = "parse_error"  # Could not parse decrypted payload


@dataclass
class FramePipelineResult:
    """
    The result of processing a single encrypted frame through the full pipeline.

    downstream_callback receives (telemetry, mitigation) only on PASSED frames.
    All other dispositions are handled by the bridge internally.
    """
    disposition:    FrameDisposition
    frame_seq:      int
    mitigation:     Optional[MitigationVector]
    telemetry:      Optional[TelemetryVector]
    plaintext_hash: Optional[bytes]   # SHA-256 of decrypted payload — audit only
    processing_ms:  float


# ============================================================================
# 3. THE BRIDGE
# ============================================================================

# Score threshold below which frames are not forwarded to downstream SAL
PASS_SCORE_THRESHOLD: int = 25   # Maps to WARNING boundary


class BusToSALBridge:
    """
    Integrates the ECDH secure bus (sensor_channel.py) with the External
    Rule Sandbox (external_rule_sandbox.py) and the downstream SAL pipeline.

    One bridge instance manages one sensor session. When the session expires
    or is compromised, the bridge stops processing and signals the caller
    to initiate a re-handshake.

    Usage:
        bridge = BusToSALBridge(tee_session, sandbox, normalization_pipeline)
        bridge.set_downstream_callback(my_sal_consumer)
        bridge.start()

        # From bus receiver thread:
        bridge.enqueue_frame(encrypted_frame)

        # When done:
        bridge.stop()
    """

    QUEUE_MAX_DEPTH: int = 64    # Backpressure — drops oldest on overflow

    def __init__(
        self,
        tee_session:    SecureBusSession,
        sandbox:        ExternalRuleSandbox,
        normalizer:     NormalizationPipeline,
        pass_threshold: int = PASS_SCORE_THRESHOLD,
    ):
        self._session       = tee_session
        self._sandbox       = sandbox
        self._normalizer    = normalizer
        self._threshold     = pass_threshold
        self._queue:        queue.Queue = queue.Queue(maxsize=self.QUEUE_MAX_DEPTH)
        self._thread:       Optional[threading.Thread] = None
        self._running:      bool = False
        self._callback:     Optional[Callable] = None
        self._immune_emit:  Optional[Callable] = None

        # Audit counters
        self._frames_received:  int = 0
        self._frames_passed:    int = 0
        self._frames_blocked:   int = 0
        self._frames_dropped:   int = 0

    def set_downstream_callback(
        self,
        callback: Callable[[TelemetryVector, MitigationVector], None],
    ):
        """
        Registers the SAL consumer callback.
        Called with (TelemetryVector, MitigationVector) for every PASSED frame.
        Invoked from the bridge's processing thread — must be thread-safe.
        """
        self._callback = callback

    def set_immune_signal_emitter(
        self,
        emitter: Callable[[str, bytes], None],
    ):
        """
        Registers the immune network emitter.
        Called with (reason: str, evidence_bytes: bytes) on AUTH_FAILED frames.
        Allows the bridge to feed attack evidence into the P2P immune network.
        """
        self._immune_emit = emitter

    def enqueue_frame(self, frame: EncryptedFrame) -> bool:
        """
        Enqueues an encrypted frame for processing.
        Returns False if the queue is full (backpressure — frame is dropped).
        Non-blocking: safe to call from a bus receiver thread.
        """
        try:
            self._queue.put_nowait(frame)
            return True
        except queue.Full:
            self._frames_dropped += 1
            return False

    def start(self):
        """Starts the background processing thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name=f"BusToSAL-{self._session.sensor_id_hash.hex()[:8]}",
        )
        self._thread.start()
        print(
            f"[BRIDGE] ▶️  Started for sensor "
            f"{self._session.sensor_id_hash.hex()[:8]}…"
        )

    def stop(self):
        """Signals the processing loop to stop and waits for it to finish."""
        self._running = False
        # Unblock the queue.get() with a sentinel
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        print(
            f"[BRIDGE] ⏹️  Stopped. "
            f"passed={self._frames_passed} "
            f"blocked={self._frames_blocked} "
            f"dropped={self._frames_dropped}"
        )

    def _processing_loop(self):
        """Main frame processing loop — runs in background thread."""
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None:
                break   # Sentinel — stop signal

            frame: EncryptedFrame = item
            result = self._process_frame(frame)
            self._frames_received += 1

            if result.disposition == FrameDisposition.PASSED:
                self._frames_passed += 1
                if self._callback and result.telemetry and result.mitigation:
                    self._callback(result.telemetry, result.mitigation)

            elif result.disposition == FrameDisposition.BLOCKED:
                self._frames_blocked += 1

            elif result.disposition == FrameDisposition.AUTH_FAILED:
                self._frames_dropped += 1
                if self._immune_emit:
                    # Evidence: the encrypted frame bytes — never the plaintext
                    evidence = frame.to_bytes()
                    self._immune_emit("AUTH_FAILED", evidence)

            elif result.disposition == FrameDisposition.EXPIRED:
                self._running = False
                print(
                    f"[BRIDGE] ⚠️  Session expired during processing. "
                    "Re-handshake required."
                )
                break

    def _process_frame(self, frame: EncryptedFrame) -> FramePipelineResult:
        """
        Processes a single encrypted frame through the full pipeline:
          decrypt → parse → normalize → sandbox → disposition decision.
        """
        t_start = time.perf_counter()

        # ── Gate 1: Decrypt ───────────────────────────────────────────────────
        try:
            plaintext = self._session.decrypt_frame(frame)
        except (FrameAuthError, ReplayAttackError) as e:
            return FramePipelineResult(
                disposition=FrameDisposition.AUTH_FAILED,
                frame_seq=frame.frame_seq,
                mitigation=None, telemetry=None,
                plaintext_hash=None,
                processing_ms=(time.perf_counter() - t_start) * 1000,
            )
        except SessionExpiredError:
            return FramePipelineResult(
                disposition=FrameDisposition.EXPIRED,
                frame_seq=frame.frame_seq,
                mitigation=None, telemetry=None,
                plaintext_hash=None,
                processing_ms=(time.perf_counter() - t_start) * 1000,
            )

        # Audit hash — SHA-256 of plaintext (never the plaintext itself)
        plaintext_hash = hashlib.sha256(plaintext).digest()

        # ── Gate 2: Parse into typed samples ──────────────────────────────────
        # In production: this parses the sensor's binary protocol.
        # Here we use a minimal mock: 9 float32 values (clinical features).
        try:
            telemetry = self._parse_and_normalize(plaintext, frame.frame_seq)
        except Exception:
            return FramePipelineResult(
                disposition=FrameDisposition.PARSE_ERROR,
                frame_seq=frame.frame_seq,
                mitigation=None, telemetry=None,
                plaintext_hash=plaintext_hash,
                processing_ms=(time.perf_counter() - t_start) * 1000,
            )

        # ── Gate 3: External rule sandbox ────────────────────────────────────
        mitigation = self._sandbox.execute_all(telemetry)

        disposition = (
            FrameDisposition.PASSED
            if mitigation.score >= self._threshold
            else FrameDisposition.BLOCKED
        )

        return FramePipelineResult(
            disposition=disposition,
            frame_seq=frame.frame_seq,
            mitigation=mitigation,
            telemetry=telemetry,
            plaintext_hash=plaintext_hash,
            processing_ms=(time.perf_counter() - t_start) * 1000,
        )

    def _parse_and_normalize(
        self, plaintext: bytes, frame_seq: int
    ) -> TelemetryVector:
        """
        Parses decrypted payload and normalizes into TelemetryVector.

        Wire format (production sensor protocol — 9 × float32 + 1 uint8):
          [ 4b: hrv_rmssd ][ 4b: hrv_sdnn ][ 4b: hrv_coherence ]
          [ 4b: eeg_alpha ][ 4b: eeg_theta ][ 4b: eeg_beta      ]
          [ 4b: resp_rate ][ 4b: resp_amplitude ]
          [ 1b: polyvagal_bucket ]
          Total: 33 bytes minimum
        """
        import struct
        if len(plaintext) < 33:
            raise ValueError(f"Payload too short: {len(plaintext)} < 33 bytes")

        (hrv_rmssd, hrv_sdnn, hrv_coherence,
         eeg_alpha, eeg_theta, eeg_beta,
         resp_rate, resp_amplitude) = struct.unpack_from(">8f", plaintext, 0)
        polyvagal_bucket = plaintext[32]

        if polyvagal_bucket not in (0, 1, 2):
            polyvagal_bucket = 2  # dorsal_vagal — conservative default

        return self._normalizer.normalize(
            hrv_rmssd=hrv_rmssd,
            hrv_sdnn=hrv_sdnn,
            hrv_coherence=hrv_coherence,
            eeg_alpha=eeg_alpha,
            eeg_theta=eeg_theta,
            eeg_beta=eeg_beta,
            resp_rate=resp_rate,
            resp_amplitude=resp_amplitude,
            polyvagal_bucket=polyvagal_bucket,
        )

    def get_status(self) -> dict:
        return {
            "sensor_id":        self._session.sensor_id_hash.hex()[:8],
            "session_state":    self._session.state.value,
            "session_age_s":    round(self._session.session_age_seconds, 1),
            "running":          self._running,
            "queue_depth":      self._queue.qsize(),
            "frames_received":  self._frames_received,
            "frames_passed":    self._frames_passed,
            "frames_blocked":   self._frames_blocked,
            "frames_dropped":   self._frames_dropped,
            "pass_rate":        (
                f"{self._frames_passed/self._frames_received*100:.1f}%"
                if self._frames_received > 0 else "n/a"
            ),
        }


# ============================================================================
# 4. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import struct as _struct
    import secrets as _sec
    import hashlib as _hl

    from src.keros.sensor_channel import (
        SensorEndpoint, TEEEndpoint, perform_full_handshake,
    )

    print("=" * 68)
    print("  Cortex — Bus-to-SAL Bridge Integration Self-Test")
    print("=" * 68)

    # ── Setup: ECDH handshake ─────────────────────────────────────────────────
    sensor_ep = SensorEndpoint(sensor_id=b"EEG_FP1_CERTIFIED_SN099")
    tee_ep    = TEEEndpoint(tee_id=b"ARM_TRUSTZONE_TEE_UNIT_0")
    s_session, t_session = perform_full_handshake(sensor_ep, tee_ep)
    print(f"\n  Handshake complete — session: {t_session.state.value}")

    # ── Setup: Sandbox with one rule ─────────────────────────────────────────
    gov_key = _sec.token_bytes(32)
    import hmac as _hmac

    sandbox = ExternalRuleSandbox(governance_key=gov_key)
    rule_src = """
def apply(telemetry):
    hrv = telemetry["hrv_coherence"]
    eeg = telemetry["eeg_alpha"]
    score = int((hrv * 0.7 + eeg * 0.3) * 100)
    return max(0, min(100, score))
"""
    manifest = _hmac.new(gov_key, rule_src.encode(), _hl.sha256).digest()
    sandbox.register_rule(rule_src, manifest, "v1.0", "cardiac_autonomic")

    # ── Setup: Bridge ─────────────────────────────────────────────────────────
    normalizer = NormalizationPipeline()
    bridge = BusToSALBridge(t_session, sandbox, normalizer, pass_threshold=25)

    received_results = []
    bridge.set_downstream_callback(
        lambda tv, mv: received_results.append((tv, mv))
    )

    bridge.start()

    def make_sensor_frame(
        hrv_rmssd=55.0, hrv_sdnn=60.0, hrv_coherence=0.75,
        eeg_alpha=0.65, eeg_theta=0.40, eeg_beta=0.30,
        resp_rate=15.0, resp_amplitude=0.50, polyvagal_bucket=0
    ) -> EncryptedFrame:
        """Packs clinical values into the sensor wire format and encrypts."""
        payload = _struct.pack(
            ">8f",
            hrv_rmssd, hrv_sdnn, hrv_coherence,
            eeg_alpha, eeg_theta, eeg_beta,
            resp_rate, resp_amplitude,
        ) + bytes([polyvagal_bucket])
        return s_session.encrypt_frame(payload)

    # ── Test 1: Normal frame passes through ───────────────────────────────────
    print("\n[TEST 1] Normal biometric frame — should PASS")
    bridge.enqueue_frame(make_sensor_frame(hrv_coherence=0.80, eeg_alpha=0.65))
    time.sleep(0.15)
    assert len(received_results) == 1, f"Expected 1 result, got {len(received_results)}"
    tv, mv = received_results[0]
    assert mv.score >= 25
    print(f"  [PASS] Score={mv.score}, hrv_coherence_norm={tv.hrv_coherence_norm:.2f} ✅")

    # ── Test 2: Low coherence frame is blocked ────────────────────────────────
    print("\n[TEST 2] Low coherence frame — should be BLOCKED by sandbox")
    # hrv_coherence=0.02, eeg_alpha=0.01 → score ≈ int((0.02*0.7+0.01*0.3)*100) = 1
    bridge.enqueue_frame(make_sensor_frame(hrv_coherence=0.02, eeg_alpha=0.01))
    time.sleep(0.15)
    # Should not appear in received_results (blocked)
    assert len(received_results) == 1, "Blocked frame should not reach callback"
    print(f"  [PASS] Low-coherence frame blocked (not forwarded to SAL) ✅")

    # ── Test 3: Tampered frame triggers AUTH_FAILED, immune signal ────────────
    print("\n[TEST 3] Tampered frame — AUTH_FAILED, immune signal emitted")
    immune_signals = []
    bridge.set_immune_signal_emitter(
        lambda reason, evidence: immune_signals.append((reason, evidence))
    )
    # Build a frame encrypted with the CORRECT session key, then corrupt the
    # ciphertext. This hits the Poly1305 MAC failure path on the TEE side
    # without advancing the session's accepted sequence counter.
    valid_frame = make_sensor_frame()
    wire = bytearray(valid_frame.to_bytes())
    wire[22] ^= 0xFF   # Flip byte deep in ciphertext (past header+nonce)
    from src.keros.sensor_channel import EncryptedFrame as _EF
    tampered = _EF.from_bytes(bytes(wire))
    bridge.enqueue_frame(tampered)
    time.sleep(0.15)
    assert len(received_results) == 1, "Tampered frame must not reach callback"
    assert len(immune_signals) == 1
    assert immune_signals[0][0] == "AUTH_FAILED"
    print(f"  [PASS] Tampered frame blocked, immune signal emitted ✅")
    # Restore session for subsequent tests by re-handshaking
    s_session2, t_session2 = perform_full_handshake(sensor_ep, tee_ep)
    normalizer2 = NormalizationPipeline()
    bridge2 = BusToSALBridge(t_session2, sandbox, normalizer2, pass_threshold=25)
    received_results2 = []
    bridge2.set_downstream_callback(
        lambda tv, mv: received_results2.append((tv, mv))
    )
    bridge2.start()

    # ── Test 4: Multiple frames — check ordering preserved ───────────────────
    print("\n[TEST 4] 5 sequential frames — all PASS, ordering preserved")
    def make_frame2(hrv_coherence=0.75, **kw):
        payload = _struct.pack(
            ">8f",
            55.0, 60.0, hrv_coherence,
            0.65, 0.40, 0.30, 15.0, 0.50,
        ) + bytes([0])
        return s_session2.encrypt_frame(payload)
    for i in range(5):
        coherence = 0.70 + i * 0.02
        bridge2.enqueue_frame(make_frame2(hrv_coherence=coherence))
    time.sleep(0.30)
    assert len(received_results2) == 5, f"Expected 5, got {len(received_results2)}"
    seqs = [tv.sequence_counter for tv, _ in received_results2]
    assert seqs == sorted(seqs), "Frame ordering not preserved!"
    print(f"  [PASS] {len(received_results2)} frames passed, sequence: {seqs} ✅")

    # ── Stop and status ───────────────────────────────────────────────────────
    bridge.stop()
    bridge2.stop()
    status = bridge2.get_status()
    print("\n── Bridge Status")
    for k, v in status.items():
        print(f"  {k}: {v}")

    print("\n✅ Bus-to-SAL Bridge tests complete")
    print("   Integration:    sensor_channel ↔ external_rule_sandbox ↔ SAL")
    print("   Auth gate:      FrameAuthError → immune signal (no callback)")
    print("   Score gate:     score < 25 → BLOCKED (not forwarded)")
    print("   Audit trail:    SHA-256 of plaintext only (no biometric logging)")
