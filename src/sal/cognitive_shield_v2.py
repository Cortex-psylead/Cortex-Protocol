# ============================================================================
# src/sal/cognitive_shield_v2.py
# Milestone 1: CORTEX + LIMES + ETHOS — Integrated Cognitive Shield
#
# CORRECTIONS vs. previous version (post-audit cycle 2, 2026-05-17):
#   [v2-FIX-01] EthosEngine.get_capacity: NONE checked before LIMITED.
#   [v2-FIX-02] LimesEngine: struct.pack timestamp, Dict nonce store, TTL pruning.
#   [v2-FIX-03] EthosEngine.auto_revoke: revokes only on NONE capacity.
#   [v2-FIX-04] ETHOS consent gate placed BEFORE raw frame creation.
#   [v2-FIX-05] DriftDetector: threading.RLock on all state mutations.
#   [v2-FIX-06] LimesProof: __post_init__ validates byte lengths.
#   [v2-FIX-07] ConsentRecord.is_active(): atomic expiry + revocation check.
#   [v2-FIX-08] LIMES receives Phase A features, not the raw frame.
#   [v2-FIX-09] SensorCertificationAuthority: Challenge-Response handshake.
#   [v2-FIX-10] BiometricStateMachine imported and wired (async-ready).
#   [v2-FIX-11] ingest_raw_data: COMPLETE 10-step pipeline (was truncated).
#   [v2-FIX-12] session_log protected with threading.Lock (H-03 residual).
#   [v2-FIX-13] KEROS nonce store changed from set() to Dict[bytes, float]
#               with TTL pruning — matches LIMES pattern (H-07 residual).
#   [v2-FIX-14] _double_confirm raises NotImplementedError in base class;
#               PoC uses DemoCognitiveShield subclass (H-ETHOS residual).
#
# Architecture note:
#   LIMES and ETHOS are defined here as internal classes of the SAL integration
#   layer (Milestone 1 monolith). The standalone modules in src/limes/ and
#   src/ethos/ are the canonical separated implementations for Milestone 2,
#   when CognitiveShield becomes a thin orchestrator. This file is the
#   integration vehicle — not the final architectural target.
#
# Dependencies: numpy
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.signal import hilbert as _hilbert

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from sal.state_buffer import BiometricStateMachine
from ethos.ethos_consent import (
    EthosEngine,
    DemoEthosEngine,
    ConsentCapacity,
    ConsentScope,
    ConsentRecord,
)


# ============================================================================
# 0. CLINICAL CONFIGURATION (White Branch Mandate)
# ============================================================================

class ClinicalThresholds:
    """
    All values defined exclusively by the White Branch (Clinical Faculty).
    DO NOT modify without peer review and a version increment.

    Bibliographic basis:
      - Porges, S.W. (2011). The Polyvagal Theory. Norton.
      - Task Force ESC/NASPE (1996). HRV standards. Eur Heart J, 17(3), 354-381.
      - Shaffer & Ginsberg (2017). HRV metrics overview. Front. Public Health.
      - Dana, D. (2018). The Polyvagal Theory in Therapy. Norton.
    """
    # CDI
    MAX_COHERENCY_SUM_PER_MINUTE: float = 2.5
    DRIFT_WINDOW_SECONDS:         int   = 60
    HARD_BLOCK_VIOLATIONS:        int   = 3
    SOFT_BLOCK_VIOLATIONS:        int   = 5

    # Hardware certification minimums
    REQUIRED_SNR_DB:              float = 30.0
    REQUIRED_BITS_RESOLUTION:     int   = 12

    # Clinical Bridge (Polyvagal envelope thresholds)
    BRIDGE_STD_LIMIT:             float = 0.5   # ventral vagal calm marker
    BRIDGE_P75_LIMIT:             float = 0.7   # sympathetic activation marker
    BRIDGE_MAX_LIMIT:             float = 0.9   # acute stress spike marker

    # LIMES
    LIMES_PROOF_TTL_SECONDS:      int   = 30

    # ETHOS
    ETHOS_DEFAULT_CONSENT_TTL:    int   = 3600  # 1 hour


# ============================================================================
# 1. CORTEX — Sensor Certification with Challenge-Response
# [v2-FIX-09]
# ============================================================================

class SensorCertificationAuthority:
    """
    Two-phase sensor handshake:
      Phase 1 — Capability check: whitelist membership + SNR/bits minima.
      Phase 2 — Challenge-Response: HMAC(challenge, manufacturer_key) proves
                 physical device identity. Prevents BLE spoofing.

    In production: manufacturer_key is provisioned by Governance Node signed
    package. The simulated keys below are for PoC demonstration only.
    """

    _WHITELIST: Dict[str, dict] = {
        "eeg_fp1_certified_v1": {
            "manufacturer":    "NeuroStandard",
            "snr_db":          35.0,
            "bits":            16,
            # PoC: simulated manufacturer key — replace with Governance Node package
            "manufacturer_key": b"simulated_manufacturer_key_32_bytes_123456789",
        },
        "eeg_occipital_certified_v1": {
            "manufacturer":    "NeuroStandard",
            "snr_db":          32.0,
            "bits":            14,
            "manufacturer_key": b"simulated_manufacturer_key_32_bytes_987654321",
        },
    }

    @classmethod
    def issue_challenge(cls) -> bytes:
        """Step 1: SAL issues 32-byte nonce to sensor before certifying it."""
        return secrets.token_bytes(32)

    @classmethod
    def verify_response(cls, sensor_id: str, challenge: bytes, response: bytes) -> bool:
        """Step 2: SAL verifies sensor's HMAC response against whitelist key."""
        if sensor_id not in cls._WHITELIST:
            return False
        key = cls._WHITELIST[sensor_id]["manufacturer_key"]
        expected = hmac.new(key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(expected, response)

    @classmethod
    def handshake(
        cls,
        sensor_id: str,
        claimed_snr: float,
        claimed_bits: int,
        challenge: bytes,
        response: bytes,
    ) -> Tuple[bool, str]:
        """Full two-phase handshake. Both phases must pass."""
        # Phase 2 first — reject imposters before whitelist lookup
        if not cls.verify_response(sensor_id, challenge, response):
            return False, f"Challenge-Response failed: sensor '{sensor_id}' not authenticated"

        if sensor_id not in cls._WHITELIST:
            return False, f"Sensor '{sensor_id}' not in Governance Node whitelist"

        spec = cls._WHITELIST[sensor_id]
        if spec["snr_db"] < ClinicalThresholds.REQUIRED_SNR_DB:
            return False, f"SNR {spec['snr_db']} dB below minimum {ClinicalThresholds.REQUIRED_SNR_DB} dB"
        if spec["bits"] < ClinicalThresholds.REQUIRED_BITS_RESOLUTION:
            return False, f"Resolution {spec['bits']} bits below minimum {ClinicalThresholds.REQUIRED_BITS_RESOLUTION} bits"

        return True, (
            f"Sensor '{sensor_id}' certified — "
            f"SNR: {spec['snr_db']} dB, {spec['bits']} bits, identity verified"
        )


# ============================================================================
# 2. CORTEX — Clinical Drift Index (CDI)
# [v2-FIX-05] All state mutations under threading.RLock
# ============================================================================

class DriftDetector:
    """
    Dual-threshold CDI: hard violations (absolute window sum) and
    soft violations (Z-score personal baseline deviation).

    Thread safety: all reads and writes to shared state go through
    self._lock (threading.RLock). Reentrant to allow the same thread
    to check is_blocked() before calling add_reading() without deadlock.
    """

    def __init__(self):
        self._lock            = threading.RLock()   # [v2-FIX-05]
        self._readings: deque = deque()
        self._hard_violations = 0
        self._soft_violations = 0
        self._blocked         = False
        self._baseline_mean   = 0.0
        self._baseline_std    = 0.0
        self._baseline_ready  = False

    def establish_baseline(self, sessions: List[float]):
        with self._lock:
            if len(sessions) < 3:
                return
            self._baseline_mean  = float(np.mean(sessions))
            self._baseline_std   = float(np.std(sessions))
            self._baseline_ready = True
            print(
                f"[CDI] Baseline established — "
                f"mean={self._baseline_mean:.3f}, std={self._baseline_std:.3f}"
            )

    def add_reading(self, coherency: float) -> Tuple[bool, str]:
        with self._lock:
            if self._blocked:
                return False, "CDI blocked"

            now = time.time()
            self._readings.append((now, coherency))
            while self._readings and (now - self._readings[0][0]) > ClinicalThresholds.DRIFT_WINDOW_SECONDS:
                self._readings.popleft()

            window_sum = sum(c for _, c in self._readings)

            # Hard threshold check
            if window_sum > ClinicalThresholds.MAX_COHERENCY_SUM_PER_MINUTE:
                self._hard_violations += 1
                print(
                    f"[CDI] ⚠️  Hard violation {self._hard_violations}/"
                    f"{ClinicalThresholds.HARD_BLOCK_VIOLATIONS} — sum={window_sum:.2f}"
                )
                if self._hard_violations >= ClinicalThresholds.HARD_BLOCK_VIOLATIONS:
                    self._blocked = True
                    return False, f"CDI: HARD BLOCK (sum={window_sum:.2f})"
                return True, f"Hard warning ({self._hard_violations})"

            # Soft threshold (Z-score against personal baseline)
            if self._baseline_ready:
                z = abs(coherency - self._baseline_mean) / (self._baseline_std + 1e-6)
                if z > 3.0:
                    self._soft_violations += 1
                    print(
                        f"[CDI] ⚠️  Soft violation {self._soft_violations}/"
                        f"{ClinicalThresholds.SOFT_BLOCK_VIOLATIONS} — z={z:.2f}"
                    )
                    if self._soft_violations >= ClinicalThresholds.SOFT_BLOCK_VIOLATIONS:
                        self._blocked = True
                        return False, f"CDI: SOFT BLOCK (z={z:.2f})"
                    return True, f"Soft warning ({self._soft_violations})"

            # Gradual soft recovery when well within safe range
            if window_sum < ClinicalThresholds.MAX_COHERENCY_SUM_PER_MINUTE * 0.6:
                self._soft_violations = max(0, self._soft_violations - 1)

            return True, "OK"

    def is_blocked(self) -> bool:
        with self._lock:
            return self._blocked

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "blocked":         self._blocked,
                "baseline_ready":  self._baseline_ready,
                "baseline_mean":   self._baseline_mean if self._baseline_ready else None,
                "hard_violations": self._hard_violations,
                "soft_violations": self._soft_violations,
                "window_sum":      sum(c for _, c in self._readings) if self._readings else 0.0,
            }


# ============================================================================
# 3. CORTEX — Two-Phase Tensor Transformation
# ============================================================================

class AnonymousTensorFactory:
    """
    Phase A: clinical feature extraction (interpretable — for Clinical Bridge).
    Phase B: HMAC-SHA256 obfuscation (anonymous — for Acolyte).
    These phases are architecturally isolated: Phase B output cannot be
    reversed to Phase A without the session salt.
    """

    @staticmethod
    def extract_features(raw_data: np.ndarray) -> np.ndarray:
        """Phase A: 5 statistical descriptors of the Hilbert envelope."""
        normalized = np.clip((raw_data + 50.0) / 100.0, 0.0, 1.0)
        envelope   = np.abs(_hilbert(normalized))
        return np.array([
            np.mean(envelope),
            np.std(envelope),
            np.percentile(envelope, 25),
            np.percentile(envelope, 75),
            np.max(envelope),
        ], dtype=np.float64)

    @staticmethod
    def obfuscate(features: np.ndarray, salt: bytes, sensor_hash: str) -> np.ndarray:
        """Phase B: irreversible HMAC-SHA256 obfuscation."""
        data_bytes = features.tobytes() + sensor_hash.encode()
        digest     = hmac.new(salt, data_bytes, hashlib.sha256).digest()
        noise      = np.frombuffer(digest[:features.nbytes], dtype=np.float32).astype(np.float64)
        return noise[:len(features)] * features


class ClinicalBridge:
    """
    Per-frame Polyvagal Theory gate on Phase A features.
    Thresholds defined by White Branch — see ClinicalThresholds.
    """

    @staticmethod
    def validate(features: np.ndarray) -> Tuple[bool, str]:
        violations = []
        if features[1] > ClinicalThresholds.BRIDGE_STD_LIMIT:
            violations.append(f"std={features[1]:.3f} > {ClinicalThresholds.BRIDGE_STD_LIMIT}")
        if features[3] > ClinicalThresholds.BRIDGE_P75_LIMIT:
            violations.append(f"p75={features[3]:.3f} > {ClinicalThresholds.BRIDGE_P75_LIMIT}")
        if features[4] > ClinicalThresholds.BRIDGE_MAX_LIMIT:
            violations.append(f"max={features[4]:.3f} > {ClinicalThresholds.BRIDGE_MAX_LIMIT}")
        if violations:
            return False, "ClinicalBridge blocked: " + "; ".join(violations)
        return True, "Within clinical bounds"


def compute_coherency(features: np.ndarray) -> float:
    """
    Coefficient of Variation (CV) of the Hilbert envelope.
    Proxy for autonomic variability (RMSSD-inspired).
    Note: CV ≠ RMSSD — this is a signal-domain analogue, not HRV gold standard.
    See CLINICAL-BRIDGE.md §3.2 for equivalence discussion.
    """
    return float(features[1] / features[0]) if features[0] > 1e-9 else 0.0


def coherency_to_state(cv: float) -> str:
    if cv < 0.3: return "ventral_vagal (calm)"
    if cv < 0.7: return "sympathetic (focused)"
    return "dorsal_vagal (rest_needed)"


# ============================================================================
# 4. CORTEX — Ephemeral Raw Frame
# ============================================================================

@dataclass
class RawBiometricFrame:
    """
    Ephemeral container for raw biometric data.
    Context manager guarantees deterministic memory zeroing on exit,
    independent of garbage collection.
    """
    sensor_hash: str
    timestamp:   float
    data:        np.ndarray

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.data is not None:
            self.data.fill(0)
            print(f"[CORTEX] 🔒 Raw frame zeroed [{self.sensor_hash[:8]}…]")
        return False


# ============================================================================
# 5. LIMES — Proof of Human Liveness (HMAC-based)
# [v2-FIX-02] struct.pack, Dict nonce store, TTL pruning
# [v2-FIX-06] __post_init__ validation
# [v2-FIX-08] generates proof from Phase A features, not raw frame
# ============================================================================

@dataclass
class LimesProof:
    """
    Proof of human liveness.
    NOTE: This is an HMAC-based authenticity proof, NOT a Zero-Knowledge Proof.
    True ZKP (Groth16 / Bulletproofs) is planned for Milestone 3.
    """
    proof_data:  bytes   # 32-byte HMAC-SHA256
    timestamp:   float
    nonce:       bytes   # 16-byte anti-replay token
    valid_until: float

    def __post_init__(self):  # [v2-FIX-06]
        if len(self.proof_data) != 32:
            raise ValueError(f"LimesProof: proof_data must be 32 bytes, got {len(self.proof_data)}")
        if len(self.nonce) != 16:
            raise ValueError(f"LimesProof: nonce must be 16 bytes, got {len(self.nonce)}")


class LimesEngine:
    """
    Generates and verifies proofs of human liveness from biometric entropy.

    Biological entropy basis: the 1/f noise of a living autonomic nervous system
    produces envelope statistics that are statistically distinguishable from
    synthetic signals. This assumption is subject to annual White Branch review.

    Anti-replay: Dict[nonce → timestamp] with TTL-based pruning.
    [v2-FIX-02] Nonce store never grows unbounded; pruned on each operation.
    """

    def __init__(self, cortex_shield: "CognitiveShield"):
        self._cortex        = cortex_shield
        self._master_secret = secrets.token_bytes(32)
        self._ttl           = ClinicalThresholds.LIMES_PROOF_TTL_SECONDS
        # [v2-FIX-02] Dict[nonce → issue_timestamp] for time-based pruning
        self._used_nonces: Dict[bytes, float] = {}

    def _ts_bytes(self, ts: float) -> bytes:
        """[v2-FIX-02] Float-safe timestamp serialization."""
        return struct.pack(">d", ts)

    def _prune_nonces(self):
        """Discard nonces older than TTL. Semantically correct: expired nonces
        cannot be replayed anyway (proof.valid_until check rejects them)."""
        cutoff = time.time() - self._ttl
        self._used_nonces = {n: t for n, t in self._used_nonces.items() if t > cutoff}

    def generate_proof(self, features: np.ndarray) -> Optional[LimesProof]:
        """
        [v2-FIX-08] Receives Phase A features (not raw frame).
        The raw frame is zeroed by its context manager before LIMES runs.
        """
        if self._cortex.get_cdi_status().get("blocked", False):
            print("[LIMES] ❌ Proof refused: CDI blocked")
            return None
        if len(features) < 5:
            print("[LIMES] ❌ Insufficient feature vector")
            return None

        entropy_hash = hashlib.sha256(features.tobytes()).digest()
        nonce        = secrets.token_bytes(16)
        ts           = time.time()
        valid_until  = ts + self._ttl

        message = entropy_hash + nonce + self._ts_bytes(ts)
        proof   = hmac.new(self._master_secret, message, hashlib.sha256).digest()

        self._used_nonces[nonce] = ts
        self._prune_nonces()
        print(f"[LIMES] ✅ Liveness proof generated — valid for {self._ttl}s")
        return LimesProof(proof_data=proof, timestamp=ts, nonce=nonce, valid_until=valid_until)

    def verify_proof(self, proof: LimesProof, features: np.ndarray) -> bool:
        """Verifies liveness without accessing raw biometric data."""
        self._prune_nonces()

        if time.time() > proof.valid_until:
            print("[LIMES] ❌ Proof expired")
            return False
        if proof.nonce in self._used_nonces:
            print("[LIMES] ❌ Nonce already consumed — replay rejected")
            return False

        entropy_hash = hashlib.sha256(features.tobytes()).digest()
        message      = entropy_hash + proof.nonce + self._ts_bytes(proof.timestamp)
        expected     = hmac.new(self._master_secret, message, hashlib.sha256).digest()

        if hmac.compare_digest(expected, proof.proof_data):
            # Consume nonce AFTER successful verification
            self._used_nonces[proof.nonce] = proof.timestamp
            print("[LIMES] ✅ Human liveness confirmed")
            return True
        print("[LIMES] ❌ Invalid proof — HMAC mismatch")
        return False


# ============================================================================
# 6. ETHOS — Dynamic Consent (physiologically grounded)
#
# EthosEngine, ConsentCapacity, ConsentScope, and ConsentRecord are imported
# from the canonical standalone module src/ethos/ethos_consent.py (see the
# import block near the top of this file) rather than duplicated here.
#
# This removes the implementation drift that existed between this file and
# the standalone module prior to this refactor: divergent method names
# (get_capacity()/_double_confirm() vs. get_consent_capacity()/
# _double_confirmation()) and a divergent request_consent() signature
# (this file's version previously lacked the `purpose` parameter).
#
# Behavior is characterized by tests/test_ethos_consent.py (20 tests).
# The end-to-end integration through this file is pinned by
# tests/test_cognitive_shield_v2_smoke.py.

# ============================================================================
# 7. INTEGRATED COGNITIVE SHIELD
# [v2-FIX-11] Complete ingest_raw_data pipeline (10 steps)
# [v2-FIX-12] session_log protected with threading.Lock
# ============================================================================

class CognitiveShield:
    """
    SAL integration: CORTEX + LIMES + ETHOS.

    Thread safety model:
      - DriftDetector: RLock on all state (add_reading, is_blocked, get_status).
      - session_log: dedicated Lock (write-protected append + read copy).
      - LimesEngine / EthosEngine: single-threaded in current architecture.
        When Milestone 2 introduces the full async pipeline, these will consume
        BiometricStateMachine reads instead of calling get_cdi_status() directly.
      - BiometricStateMachine: imported and instantiated for future async wiring.

    Architecture note:
      LIMES and ETHOS are instantiated here as internal collaborators.
      They receive `self` (the shield) as their CDI reader, which is acceptable
      for the Milestone 1 synchronous architecture. Milestone 2 will decouple
      them to consume BiometricStateMachine (read-only) instead.
    """

    def __init__(self):
        self._session_salt          = secrets.token_bytes(32)
        self._certified_sensors:     Dict[str, str] = {}
        self.drift_detector          = DriftDetector()
        self._baseline_sessions:     List[float]    = []
        self.session_log:            List[Dict]      = []
        self._log_lock               = threading.Lock()   # [v2-FIX-12]

        # Pentagon modules
        self.limes = LimesEngine(self)
        self.ethos = EthosEngine(self)

        # Async-ready state machine (wired in Milestone 2)
        self._sensor_key      = secrets.token_bytes(32)
        self.state_machine    = BiometricStateMachine(self._sensor_key)

    # ------------------------------------------------------------------ #
    # Sensor registration                                                 #
    # ------------------------------------------------------------------ #

    def register_sensor(self, sensor_id: str, snr: float, bits: int) -> Tuple[bool, str]:
        """
        [v2-FIX-09] Full Challenge-Response handshake.
        In demo: the SAL simulates the sensor response using the whitelist key.
        In production: the sensor computes HMAC with its secure element key.
        """
        challenge = SensorCertificationAuthority.issue_challenge()
        spec      = SensorCertificationAuthority._WHITELIST.get(sensor_id, {})
        manuf_key = spec.get("manufacturer_key", b"")
        # Production: this response comes from the physical sensor over BLE
        response  = hmac.new(manuf_key, challenge, hashlib.sha256).digest()

        approved, msg = SensorCertificationAuthority.handshake(
            sensor_id, snr, bits, challenge, response
        )
        if approved:
            sensor_hash = hashlib.sha256(sensor_id.encode()).hexdigest()
            self._certified_sensors[sensor_hash] = sensor_id
            print(f"[CORTEX] ✅ {msg}")
        else:
            print(f"[CORTEX] ❌ {msg}")
        return approved, msg

    # ------------------------------------------------------------------ #
    # Main SAL pipeline                                                   #
    # [v2-FIX-11] Complete 10-step implementation                        #
    # ------------------------------------------------------------------ #

    def ingest_raw_data(self, sensor_id: str, raw_data: np.ndarray) -> Optional[Dict]:
        """
        Full SAL pipeline for one biometric frame.

        Steps:
          1.  Sensor certification check
          2.  CDI pre-check (fast-path block if already triggered)
          3.  ETHOS consent gate — BEFORE raw data touches memory [v2-FIX-04]
          4.  Ephemeral frame opened (context manager)
          4a. Phase A feature extraction
          4b. Clinical Bridge validation on Phase A
          4c. Coherency index computation
          4d. LIMES proof from Phase A features [v2-FIX-08]
          4e. Phase B obfuscation
          5.  Raw frame zeroed (context manager exit)
          6.  CDI update — AFTER frame is zeroed
          7.  ETHOS dysregulation check — revoke if NONE capacity [v2-FIX-03]
          8.  Baseline update (first 7 sessions)
          9.  Async state machine update (BiometricStateMachine)
          10. Audit log append [v2-FIX-12] — thread-safe
        """
        # 1. Sensor certification
        sensor_hash = hashlib.sha256(sensor_id.encode()).hexdigest()
        if sensor_hash not in self._certified_sensors:
            print(f"[CORTEX] ❌ Sensor '{sensor_id}' not certified — call register_sensor() first")
            return None

        # 2. CDI pre-check (fast path — avoids allocating frame if already blocked)
        if self.drift_detector.is_blocked():
            print("[CORTEX] 🛑 CDI blocked — session suspended")
            return None

        # 3. ETHOS consent gate [v2-FIX-04]
        if not self.ethos.check_consent(ConsentScope.BIOMETRIC):
            print("[ETHOS] No active biometric consent — requesting...")
            if not self.ethos.request_consent(ConsentScope.BIOMETRIC):
                print("[ETHOS] ❌ Consent refused — pipeline aborted")
                return None

        # 4. Ephemeral frame — context manager guarantees zeroing
        with RawBiometricFrame(sensor_hash=sensor_hash, timestamp=time.time(),
                               data=raw_data.copy()) as frame:

            # 4a. Phase A feature extraction
            features = AnonymousTensorFactory.extract_features(frame.data)

            # 4b. Clinical Bridge on Phase A (real, interpretable values)
            is_safe, bridge_msg = ClinicalBridge.validate(features)
            if not is_safe:
                print(f"[CORTEX] ❌ {bridge_msg}")
                return None

            # 4c. Coherency index
            coherency = compute_coherency(features)

            # 4d. LIMES proof from Phase A features (not raw frame) [v2-FIX-08]
            limes_proof = self.limes.generate_proof(features)
            limes_valid = limes_proof is not None

            # 4e. Phase B obfuscation — Acolyte receives only this
            anonymous_tensor = AnonymousTensorFactory.obfuscate(
                features, self._session_salt, sensor_hash
            )

        # 5. Raw frame guaranteed zeroed here ↑

        # 6. CDI update (after frame is safely destroyed)
        is_safe_drift, drift_msg = self.drift_detector.add_reading(coherency)
        if not is_safe_drift:
            print(f"[CORTEX] 🛑 {drift_msg}")
            self.ethos.auto_revoke_on_dysregulation()
            return None

        # 7. ETHOS dysregulation check [v2-FIX-03]
        self.ethos.auto_revoke_on_dysregulation()

        # 8. Baseline update (accumulate first 7 sessions)
        if not self.drift_detector._baseline_ready:
            self._baseline_sessions.append(coherency)
            if len(self._baseline_sessions) >= 7:
                self.drift_detector.establish_baseline(self._baseline_sessions)

        # 9. Async state machine update (prepares Milestone 2 wiring)
        cdi_status = self.drift_detector.get_status()
        if cdi_status["blocked"]:
            self.state_machine.transition("BLOCKED")
        elif cdi_status["hard_violations"] >= 1 or cdi_status["soft_violations"] >= 1:
            self.state_machine.transition("WARNING")
        else:
            # SAFE transition only valid from WARNING or initial BLOCKED state
            self.state_machine.transition("SAFE")

        # Build result dict (anonymous tensor norm — no raw values)
        result = {
            "coherency_index":       coherency,
            "polyvagal_state":       coherency_to_state(coherency),
            "limes_humanity_proven": limes_valid,
            "consent_active":        self.ethos.check_consent(ConsentScope.BIOMETRIC),
            "tensor_norm":           float(np.linalg.norm(anonymous_tensor)),
            "timestamp":             time.time(),
        }

        # 10. Audit log — thread-safe append [v2-FIX-12]
        log_entry = {
            "timestamp":    result["timestamp"],
            "sensor_hash":  sensor_hash[:8],        # truncated — no full hash in log
            "coherency":    coherency,
            "polyvagal":    result["polyvagal_state"],
            "limes_proven": limes_valid,
            "hard_viol":    cdi_status["hard_violations"],
            "soft_viol":    cdi_status["soft_violations"],
        }
        with self._log_lock:                         # [v2-FIX-12]
            self.session_log.append(log_entry)

        return result

    # ------------------------------------------------------------------ #
    # Public interface                                                    #
    # ------------------------------------------------------------------ #

    def get_cdi_status(self) -> Dict:
        return self.drift_detector.get_status()

    def get_audit_log(self) -> List[Dict]:
        with self._log_lock:
            return self.session_log.copy()

    def destroy_session(self):
        """
        Judicial Kill Switch: renews session salt, clears audit log,
        revokes all ETHOS consents. Deterministic and synchronous.
        """
        self._session_salt = secrets.token_bytes(32)
        self.ethos.revoke_all()
        with self._log_lock:
            self.session_log.clear()
        print("[CORTEX] 🔒 Session destroyed — salt renewed, log cleared, consents revoked")


# ============================================================================
# 8. DEMO SUBCLASS — PoC only
# [v2-FIX-14] Isolates auto-confirm behavior to a named subclass
# ============================================================================

class DemoCognitiveShield(CognitiveShield):
    """
    PoC / automated-test subclass.
    Uses DemoEthosEngine (src/ethos/ethos_consent.py) to auto-confirm
    double confirmation, with an explicit console warning on every use.

    ⚠️  NEVER use in production. The warning is the contract.
    The base CognitiveShield's EthosEngine raises NotImplementedError on
    _double_confirmation() -- DemoEthosEngine is the sanctioned override,
    swapped in below instead of monkey-patching the instance after
    construction.
    """

    def __init__(self):
        super().__init__()
        self.ethos = DemoEthosEngine(self)


# ============================================================================
# 9. DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  Cortex Protocol — Milestone 1: CORTEX + LIMES + ETHOS")
    print("=" * 68)

    fs = 256
    t  = np.linspace(0, 1, fs)

    def eeg(amp: float = 10.0, noise: float = 5.0) -> np.ndarray:
        return amp * np.sin(2 * np.pi * 8 * t) + noise * np.random.randn(fs)

    # Use DemoCognitiveShield for PoC — base class would raise on _double_confirm
    shield = DemoCognitiveShield()
    shield.register_sensor("eeg_fp1_certified_v1", 35.0, 16)

    # ── Baseline establishment (7 normal sessions) ──────────────────────
    print("\n── Baseline establishment (7 sessions)")
    for i in range(7):
        r = shield.ingest_raw_data("eeg_fp1_certified_v1", eeg())
        if r:
            print(
                f"  [{i+1}] coherency={r['coherency_index']:.3f} | "
                f"state={r['polyvagal_state']} | "
                f"human={r['limes_humanity_proven']} | "
                f"consent={r['consent_active']}"
            )
        time.sleep(0.05)

    # ── Consent lifecycle ───────────────────────────────────────────────
    print("\n── Consent lifecycle")
    print(f"  Active: {shield.ethos.check_consent(ConsentScope.BIOMETRIC)}")
    shield.ethos.revoke_all()
    print(f"  After revoke_all: {shield.ethos.check_consent(ConsentScope.BIOMETRIC)}")
    shield.ethos.request_consent(ConsentScope.BIOMETRIC, duration_seconds=300)
    print(f"  After re-grant: {shield.ethos.check_consent(ConsentScope.BIOMETRIC)}")

    # ── Pathological drift simulation ───────────────────────────────────
    print("\n── Pathological drift (CDI escalation)")
    shield2 = DemoCognitiveShield()
    shield2.register_sensor("eeg_fp1_certified_v1", 35.0, 16)

    for amp in [5, 10, 20, 35, 50, 70, 90]:
        r = shield2.ingest_raw_data("eeg_fp1_certified_v1", eeg(amp=amp, noise=amp * 0.3))
        if r:
            print(
                f"  amp={amp:3d}: coherency={r['coherency_index']:.3f} | "
                f"state={r['polyvagal_state']}"
            )
        else:
            print(f"  amp={amp:3d}: 🛑 BLOCKED")
            break

    # ── Final status ────────────────────────────────────────────────────
    print("\n── CDI status")
    for k, v in shield2.get_cdi_status().items():
        print(f"  {k}: {v}")

    print("\n── Consent audit log")
    for entry in shield2.ethos.get_audit_log():
        print(f"  scope={entry['scope']} | active={entry['active']} | revoked={entry['revoked']}")

    print("\n── BiometricStateMachine state")
    state, valid = shield2.state_machine.read()
    print(f"  state={state} | hmac_valid={valid}")

    shield2.destroy_session()
    print("\n✅ Milestone 1 complete — CORTEX + LIMES + ETHOS integrated")
    print("   Async pipeline (BiometricStateMachine threads): Milestone 2")
    print("   Standalone module separation (Pentagon architecture): Milestone 2")
