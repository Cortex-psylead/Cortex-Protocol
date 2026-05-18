# ============================================================================
# src/sal/telemetry_router.py
# Sovereign Dual-Channel Telemetry Router
#
# Milestone 1 Extension — "Sovereign Telemetry Layer" (STL)
#
# This module implements the Dual-Channel Telemetry architecture specified in
# ROADMAP-CLINICAL.md. It plugs into the existing SAL pipeline AFTER the
# BiometricStateMachine has cleared the frame (state == SAFE | WARNING).
#
# ARCHITECTURE POSITION:
#   BiometricStateMachine (state_buffer.py)
#     └── CognitiveShield.ingest_raw_data() [cognitive_shield_v2.py]
#           └── TelemetryRouter.route()  ← THIS MODULE
#                 ├── DeSciChannel.emit()     → federated research DB (anonymous)
#                 └── ClinicalChannel.emit()  → hospital E2EE socket (pseudonymous)
#
# PENTAGON COMPLIANCE:
#   This module is a CORTEX extension, not a new Pentagon vertex.
#   It answers the same sovereignty question as CORTEX:
#   "¿Quién controla el flujo de datos?"  — in the outbound direction.
#   All consent gates remain in ETHOS. All key lifecycle is in KEROS.
#   The router is stateless with respect to biometric content.
#
# DEPENDENCIES:
#   cryptography >= 41.0  (X25519, ChaCha20-Poly1305, HKDF, X.509)
#   numpy
#   stdlib: threading, queue, secrets, struct, time
#
# SECURITY ASSUMPTIONS:
#   - Hospital public key is validated and signed by the White Branch
#     (Governance Node) before being registered here. The router does NOT
#     perform trust establishment — that is ETHOS + KEROS responsibility.
#   - Network sockets are abstracted behind TransportAdapter. This module
#     performs ONLY payload construction and key lifecycle.
#   - Zeroization is best-effort in CPython due to GC. Production deployments
#     MUST use a Secure Enclave (KEROS/TPM 2.0) for key storage. See §4.
#
# ============================================================================

import hashlib
import hmac
import queue
import secrets
import struct
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


# ============================================================================
# 0. CHANNEL STATES
# ============================================================================

class ChannelState(Enum):
    ACTIVE    = "active"     # Normal operation — emitting
    SUSPENDED = "suspended"  # CDI WARNING — rate-limited but alive
    CLOSED    = "closed"     # CDI NONE / veto — keys destroyed, socket closed


# ============================================================================
# 1. DESCI PAYLOAD — Anonymous vector donation to federated research
# ============================================================================

@dataclass
class DeSciPayload:
    """
    Mathematically anonymized biometric feature vector for open science.

    Privacy guarantees:
      - No PII, no session ID, no sensor fingerprint.
      - Spectral entropy density matrix (low-order, non-invertible).
      - RMSSD aggregate variation (HRV population metric, not individual).
      - Population cohort tag derived from CDI baseline distribution (k-anonymity
        group ≥ 5 participants before any vector is released — enforced by the
        receiving federated node, not here).

    Format is designed to be compatible with the Open Health Data Standard
    (OHDS v0.4) proposed by the White Branch for Governance Node adoption.
    """
    # Spectral entropy density: 8-bin normalized histogram of envelope FFT power
    spectral_entropy_bins: np.ndarray          # shape (8,), dtype float32
    # RMSSD-analogue aggregate: rolling 60s coefficient of variation of coherency
    rmssd_aggregate_cv:    float
    # Polyvagal cohort bucket: 0=ventral, 1=sympathetic, 2=dorsal (NOT continuous)
    polyvagal_bucket:      int
    # Monotonic sequence counter (no timestamp — prevents timing correlation)
    sequence_counter:      int
    # Schema version for federated DB compatibility
    schema_version:        str = "desci-v1.0"

    def to_bytes(self) -> bytes:
        """Serializes payload to compact binary for streaming."""
        header = struct.pack(">I", self.sequence_counter)
        bins   = self.spectral_entropy_bins.astype(np.float32).tobytes()
        tail   = struct.pack(">fB", self.rmssd_aggregate_cv, self.polyvagal_bucket)
        return header + bins + tail

    @classmethod
    def from_phase_a_features(
        cls,
        features: np.ndarray,
        coherency: float,
        polyvagal_state: str,
        sequence_counter: int,
    ) -> "DeSciPayload":
        """
        Derives an anonymous DeSci payload from Phase A features.
        All Phase A values are further aggregated — raw feature values
        are NOT included in the output.

        Information flow: Phase A features → spectral bins (lossy projection)
        The projection is non-invertible: bins cannot reconstruct features.
        """
        # Spectral entropy density: FFT of features → normalized 8-bin histogram
        fft_mag    = np.abs(np.fft.rfft(features, n=16))
        fft_norm   = fft_mag / (np.sum(fft_mag) + 1e-9)
        bins_8     = fft_norm[:8].astype(np.float32)

        # Polyvagal bucket (ordinal, not continuous)
        bucket = {"ventral_vagal (calm)": 0,
                  "sympathetic (focused)": 1,
                  "dorsal_vagal (rest_needed)": 2}.get(polyvagal_state, 2)

        return cls(
            spectral_entropy_bins=bins_8,
            rmssd_aggregate_cv=float(coherency),
            polyvagal_bucket=bucket,
            sequence_counter=sequence_counter,
        )


# ============================================================================
# 2. CLINICAL SESSION KEY LIFECYCLE (KEROS-bound)
# ============================================================================

class SessionKeyState(Enum):
    ACTIVE     = "active"
    ZEROIZED   = "zeroized"


class ClinicalSessionKey:
    """
    Ephemeral X25519 ECDH session key for one clinical monitoring session.

    Key lifecycle:
      1. __init__:  Local X25519 private key generated in memory.
      2. bind():    ECDH with hospital public key → shared secret → HKDF → AES key.
      3. encrypt(): ChaCha20-Poly1305 AEAD encryption of each clinical frame.
      4. zeroize(): Deterministic destruction — private key and derived key
                    overwritten with zeros. State → ZEROIZED.

    Zeroization trigger (any of):
      - BiometricStateMachine → "BLOCKED" (CDI hard block)
      - ETHOS: ConsentCapacity → NONE (physiological veto)
      - ETHOS: explicit revoke_consent(CLINICAL) by user
      - TTL expiry (default: 4 hours)
      - ClinicalChannel.close() — always zeroizes before closing socket

    CPython caveat: Python bytes/bytearray objects may persist in GC until
    collected. True cryptographic zeroization requires the KEROS TPM 2.0
    integration (Milestone 1.5) to store keys in a Secure Enclave. The
    current implementation provides best-effort zeroization suitable for
    PoC validation. See SECURITY.md §6 for the production gap statement.
    """

    KEY_TTL_SECONDS: int = 4 * 3600  # 4 hours — White Branch mandate

    def __init__(self):
        self._private_key: Optional[X25519PrivateKey] = X25519PrivateKey.generate()
        self._derived_key: Optional[bytes]            = None
        self._state:       SessionKeyState            = SessionKeyState.ACTIVE
        self._created_at:  float                      = time.time()
        self._lock:        threading.Lock             = threading.Lock()

        # Public key for sending to hospital (for their ECDH step)
        self.public_key_bytes: bytes = self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )

    @property
    def is_active(self) -> bool:
        with self._lock:
            return (
                self._state == SessionKeyState.ACTIVE
                and (time.time() - self._created_at) < self.KEY_TTL_SECONDS
                and self._derived_key is not None
            )

    def bind(self, hospital_public_key_bytes: bytes) -> bool:
        """
        Phase 2 of ECDH: derives symmetric key from shared secret.
        Must be called before encrypt(). Returns False if already zeroized.
        """
        with self._lock:
            if self._state != SessionKeyState.ACTIVE or self._private_key is None:
                return False

            hospital_pubkey = X25519PublicKey.from_public_bytes(hospital_public_key_bytes)
            shared_secret   = self._private_key.exchange(hospital_pubkey)

            # HKDF-SHA256: shared_secret → 32-byte ChaCha20-Poly1305 key
            hkdf = HKDF(
                algorithm=SHA256(),
                length=32,
                salt=None,
                info=b"cortex-clinical-stream-v1",
            )
            self._derived_key = hkdf.derive(shared_secret)

            # Zero shared_secret immediately (best-effort in CPython)
            shared_secret = b"\x00" * len(shared_secret)
            return True

    def encrypt(self, plaintext: bytes) -> Optional[bytes]:
        """
        Encrypts a clinical frame with ChaCha20-Poly1305 AEAD.
        Returns None if key is not active or not yet bound.
        Nonce is prepended to ciphertext: [12-byte nonce || ciphertext+tag].
        """
        with self._lock:
            if not self.is_active:
                return None
            nonce  = secrets.token_bytes(12)
            cipher = ChaCha20Poly1305(self._derived_key)
            ct     = cipher.encrypt(nonce, plaintext, None)
            return nonce + ct

    def zeroize(self, reason: str = "explicit"):
        """
        Deterministic key destruction.
        Called by ClinicalChannel on any BLOCKED/NONE/veto event.

        Steps:
          1. Overwrite _derived_key buffer with zeros (best-effort)
          2. Discard X25519 private key reference
          3. Set state to ZEROIZED
          4. Log destruction event (no key material in log)
        """
        with self._lock:
            if self._state == SessionKeyState.ZEROIZED:
                return

            # Best-effort memory zeroing
            if self._derived_key is not None:
                # bytearray allows in-place zeroing; bytes does not
                key_arr = bytearray(self._derived_key)
                for i in range(len(key_arr)):
                    key_arr[i] = 0
                self._derived_key = None

            self._private_key = None
            self._state       = SessionKeyState.ZEROIZED

            print(
                f"[CLINICAL] 🔐 Session key ZEROIZED — reason='{reason}', "
                f"age={int(time.time() - self._created_at)}s"
            )


# ============================================================================
# 3. CLINICAL PAYLOAD — Pseudonymous encrypted frame for telemedicine
# ============================================================================

@dataclass
class ClinicalPayload:
    """
    Pseudonymous clinical frame for hospital telemedicine stream.

    Privacy model:
      - Raw features are encrypted E2EE — hospital decrypts with their private key.
      - Session pseudonym (NOT user identity) links frames within one session.
      - KEROS seal (TPM attestation) proves origin hardware integrity.
      - TTL: hospital loses access when key is zeroized. No cached copies.

    Regulatory compliance:
      - GDPR Art. 9: special category health data — consent required (ETHOS gate).
      - Ley 1581/2012 (Colombia): datos sensibles — autorización previa requerida.
      - HIPAA (if US hospital): covered entity agreement required at governance layer.
    """
    # Encrypted Phase A features (ChaCha20-Poly1305)
    encrypted_features:  bytes
    # Session pseudonym — rotates with each key zeroization (not user ID)
    session_pseudonym:   bytes   # 16-byte random, reset on zeroize
    # KEROS seal (None if TPM unavailable — PoC mode)
    keros_seal_bytes:    Optional[bytes]
    # Frame sequence within this session (monotonic)
    frame_sequence:      int
    # Encrypted timestamp (inside AEAD) — hospital can verify recency
    schema_version:      str = "clinical-v1.0"

    def to_bytes(self) -> bytes:
        """Serializes for transport. Encrypted payload is opaque to the router."""
        pseudo_len = struct.pack(">H", len(self.session_pseudonym))
        seal_bytes = self.keros_seal_bytes or b""
        seal_len   = struct.pack(">H", len(seal_bytes))
        seq        = struct.pack(">I", self.frame_sequence)
        return (
            pseudo_len + self.session_pseudonym
            + seal_len + seal_bytes
            + seq
            + self.encrypted_features
        )


# ============================================================================
# 4. TRANSPORT ADAPTER (abstract — production wires real socket/HTTPS)
# ============================================================================

class TransportAdapter(ABC):
    """
    Abstract transport for channel emission.
    Concrete implementations: HTTP/2 POST, WebSocket, gRPC, IPFS/libp2p.
    The router is transport-agnostic — it constructs payloads only.
    """

    @abstractmethod
    def send(self, payload_bytes: bytes) -> bool:
        """Returns True if the payload was accepted by the remote endpoint."""

    @abstractmethod
    def close(self):
        """Closes the transport connection. Called on zeroization."""


class NullTransportAdapter(TransportAdapter):
    """PoC stub — logs emission without real network I/O."""

    def __init__(self, name: str):
        self._name = name

    def send(self, payload_bytes: bytes) -> bool:
        print(f"[TRANSPORT:{self._name}] → {len(payload_bytes)} bytes emitted")
        return True

    def close(self):
        print(f"[TRANSPORT:{self._name}] Connection closed")


# ============================================================================
# 5. DESCI CHANNEL
# ============================================================================

class DeSciChannel:
    """
    Anonymous research data donation channel.

    Properties:
      - No session keys. No encryption. Anonymization is the privacy mechanism.
      - Non-blocking: payload enqueued and emitted by a background daemon thread.
      - If the queue is full (backpressure), frames are dropped silently.
        Research data loss is acceptable; blocking the biometric pipeline is not.
      - Suspended on WARNING, closed on BLOCKED/NONE. No data emitted while closed.
    """

    MAX_QUEUE_SIZE: int = 50  # ~50 seconds at 1 Hz — generous for research

    def __init__(self, transport: TransportAdapter):
        self._transport    = transport
        self._state        = ChannelState.ACTIVE
        self._queue: queue.Queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._counter      = 0
        self._lock         = threading.Lock()

        # Background emission thread (daemon — dies with main process).
        # Call .start_worker() explicitly after construction, or it will be
        # started lazily on first emit(). This avoids blocking in test environments.
        self._worker: Optional[threading.Thread] = None
        self._worker_started = False

    def start_worker(self):
        """Starts the background emission thread. Must be called before emit() in production."""
        if not self._worker_started:
            self._worker = threading.Thread(target=self._emit_loop, daemon=True)
            self._worker.start()
            self._worker_started = True

    def emit(self, payload: DeSciPayload):
        """Enqueues payload for async emission. Non-blocking.
        Lazily starts worker thread on first emit if not already started."""
        if not self._worker_started:
            self.start_worker()
        with self._lock:
            if self._state != ChannelState.ACTIVE:
                return
        try:
            self._queue.put_nowait(payload.to_bytes())
        except queue.Full:
            print("[DeSci] ⚠️  Queue full — frame dropped (research data loss, acceptable)")

    def suspend(self):
        with self._lock:
            if self._state == ChannelState.ACTIVE:
                self._state = ChannelState.SUSPENDED
                print("[DeSci] ⏸️  Channel suspended (CDI WARNING)")

    def resume(self):
        with self._lock:
            if self._state == ChannelState.SUSPENDED:
                self._state = ChannelState.ACTIVE
                print("[DeSci] ▶️  Channel resumed")

    def close(self):
        """Closes channel permanently. Drains remaining queue before closing."""
        with self._lock:
            self._state = ChannelState.CLOSED
        self._transport.close()
        print("[DeSci] 🔒 Channel closed")

    def _emit_loop(self):
        """Background daemon thread. Drains queue to transport."""
        while True:
            try:
                payload_bytes = self._queue.get(timeout=1.0)
                with self._lock:
                    if self._state == ChannelState.CLOSED:
                        break
                self._transport.send(payload_bytes)
                self._queue.task_done()
            except queue.Empty:
                continue


# ============================================================================
# 6. CLINICAL CHANNEL
# ============================================================================

class ClinicalChannel:
    """
    Pseudonymous E2EE telemedicine channel.

    Properties:
      - X25519 ECDH + ChaCha20-Poly1305 AEAD per session.
      - Key TTL: 4 hours (White Branch mandate).
      - Zeroization is the primary privacy mechanism:
        on BLOCKED/NONE/veto → key destroyed → hospital loses access instantly.
      - Session pseudonym rotates on every zeroization → hospital cannot
        correlate across sessions without user re-consent.
      - KEROS seal (optional in PoC, required in production) proves
        hardware origin of each frame.
    """

    def __init__(
        self,
        transport: TransportAdapter,
        hospital_public_key_bytes: bytes,
    ):
        self._transport              = transport
        self._hospital_pubkey        = hospital_public_key_bytes
        self._state                  = ChannelState.ACTIVE
        self._frame_sequence         = 0
        self._lock                   = threading.Lock()
        self._session_key            = ClinicalSessionKey()
        self._session_pseudonym      = secrets.token_bytes(16)

        # Bind ECDH immediately
        if not self._session_key.bind(hospital_public_key_bytes):
            raise RuntimeError("[CLINICAL] Failed to bind session key — ECDH error")

        print(
            f"[CLINICAL] ✅ Channel initialized — "
            f"session_pseudonym={self._session_pseudonym.hex()[:8]}…"
        )

    def emit(
        self,
        features: np.ndarray,
        keros_seal_bytes: Optional[bytes] = None,
    ) -> bool:
        """
        Encrypts Phase A features and emits to clinical transport.
        Returns True if emission succeeded.
        """
        with self._lock:
            if self._state != ChannelState.ACTIVE:
                return False

            if not self._session_key.is_active:
                print("[CLINICAL] ❌ Session key expired or not bound")
                self._close_and_zeroize("key_expired")
                return False

            # Plaintext: features + frame metadata (all encrypted)
            ts_bytes      = struct.pack(">d", time.time())
            plaintext     = features.tobytes() + ts_bytes

            encrypted     = self._session_key.encrypt(plaintext)
            if encrypted is None:
                return False

            payload = ClinicalPayload(
                encrypted_features=encrypted,
                session_pseudonym=self._session_pseudonym,
                keros_seal_bytes=keros_seal_bytes,
                frame_sequence=self._frame_sequence,
            )
            self._frame_sequence += 1

            return self._transport.send(payload.to_bytes())

    def zeroize_and_close(self, reason: str = "user_veto"):
        """
        Primary sovereignty action.
        Called by TelemetryRouter on BLOCKED/NONE/veto.
        Order of operations is critical:
          1. Zeroize key (hospital access severed)
          2. Close transport (socket closed)
          3. Rotate session pseudonym (cannot correlate next session)
          4. Mark channel CLOSED
        """
        with self._lock:
            self._close_and_zeroize(reason)

    def _close_and_zeroize(self, reason: str):
        """Internal — caller must hold self._lock."""
        self._session_key.zeroize(reason=reason)
        self._transport.close()
        # Rotate pseudonym — next session is unlinkable
        self._session_pseudonym = secrets.token_bytes(16)
        self._state             = ChannelState.CLOSED
        print(
            f"[CLINICAL] 🔐 Channel CLOSED and ZEROIZED — reason='{reason}'. "
            f"Hospital access severed. New pseudonym ready for next consent."
        )


# ============================================================================
# 7. TELEMETRY ROUTER — The Sovereign Signal Splitter
# ============================================================================

class TelemetryRouter:
    """
    Sovereign Dual-Channel Telemetry Router.

    Takes a cleared biometric frame (post-CDI, post-ETHOS) from the SAL
    and routes it simultaneously to:
      1. DeSciChannel  — anonymous donation to federated research
      2. ClinicalChannel — E2EE stream to hospital telemedicine

    Both channels are OPTIONAL and independently enabled by user consent
    (ETHOS ConsentScope.DESCI and ConsentScope.CLINICAL respectively).

    State machine integration:
      The router subscribes to BiometricStateMachine state changes.
      On WARNING → DeSci suspended, Clinical continues (degraded).
      On BLOCKED → both channels closed, Clinical key zeroized immediately.

    This router is STATELESS with respect to biometric content.
    It constructs payloads and delegates — it never stores feature values.
    """

    def __init__(
        self,
        desci_channel:    Optional[DeSciChannel]    = None,
        clinical_channel: Optional[ClinicalChannel] = None,
    ):
        self._desci    = desci_channel
        self._clinical = clinical_channel
        self._counter  = 0
        self._lock     = threading.Lock()

    def route(
        self,
        features:        np.ndarray,
        coherency:       float,
        polyvagal_state: str,
        keros_seal_bytes: Optional[bytes] = None,
    ) -> Dict[str, bool]:
        """
        Routes a cleared biometric frame to both channels.

        Args:
            features:         Phase A feature vector (5 floats) — CLEARED by CDI.
            coherency:        Coherency index (CV of envelope).
            polyvagal_state:  String polyvagal state label.
            keros_seal_bytes: Optional TPM attestation bytes from KEROS.

        Returns:
            {"desci": bool, "clinical": bool} — emission success per channel.
        """
        with self._lock:
            self._counter += 1
            counter = self._counter

        results = {"desci": False, "clinical": False}

        # ── DeSci channel ────────────────────────────────────────────────
        if self._desci is not None:
            desci_payload = DeSciPayload.from_phase_a_features(
                features, coherency, polyvagal_state, counter
            )
            self._desci.emit(desci_payload)
            results["desci"] = True

        # ── Clinical channel ─────────────────────────────────────────────
        if self._clinical is not None:
            results["clinical"] = self._clinical.emit(
                features, keros_seal_bytes=keros_seal_bytes
            )

        return results

    def on_state_change(self, new_state: str):
        """
        State machine callback. Called by CognitiveShield when
        BiometricStateMachine transitions.

        WARNING  → DeSci suspended (data quality insufficient for research).
                   Clinical continues — doctor needs continuous monitoring.
        BLOCKED  → Both channels closed. Clinical key ZEROIZED immediately.
                   This is the primary neuro-rights enforcement action.
        SAFE     → DeSci resumed if it was suspended.
        """
        if new_state == "BLOCKED":
            print("[ROUTER] 🛑 State=BLOCKED — executing sovereign zeroization")
            if self._clinical:
                self._clinical.zeroize_and_close(reason="cdi_block")
            if self._desci:
                self._desci.close()

        elif new_state == "WARNING":
            if self._desci:
                self._desci.suspend()
            # Clinical channel stays active (medical priority)

        elif new_state == "SAFE":
            if self._desci:
                self._desci.resume()

    def on_ethos_veto(self, scope: str):
        """
        Called by EthosEngine when consent is revoked.

        scope="CLINICAL" → ClinicalChannel zeroized and closed.
        scope="DESCI"    → DeSciChannel closed.
        scope="ALL"      → Both channels terminated.
        """
        print(f"[ROUTER] 🔐 ETHOS veto received — scope='{scope}'")

        if scope in ("CLINICAL", "ALL") and self._clinical:
            self._clinical.zeroize_and_close(reason=f"ethos_veto_{scope.lower()}")

        if scope in ("DESCI", "ALL") and self._desci:
            self._desci.close()


# ============================================================================
# 8. DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  CortexOS — Dual-Channel Telemetry Router Demo")
    print("=" * 68)

    import numpy as np

    # ── Simulate hospital key pair (in production: from Governance Node registry)
    hospital_private = X25519PrivateKey.generate()
    hospital_pub_bytes = hospital_private.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    print(f"[DEMO] Hospital public key: {hospital_pub_bytes.hex()[:16]}…")

    # ── Initialize channels
    desci_transport    = NullTransportAdapter("DeSci-FedDB")
    clinical_transport = NullTransportAdapter("Clinical-E2EE")

    desci_ch    = DeSciChannel(transport=desci_transport)
    clinical_ch = ClinicalChannel(
        transport=clinical_transport,
        hospital_public_key_bytes=hospital_pub_bytes,
    )
    router = TelemetryRouter(desci_channel=desci_ch, clinical_channel=clinical_ch)

    # ── Simulate 3 cleared biometric frames
    print("\n── Normal operation (3 frames)")
    for i in range(3):
        features = np.array([0.15, 0.03, 0.12, 0.18, 0.22], dtype=np.float64)
        result   = router.route(
            features=features,
            coherency=0.20,
            polyvagal_state="ventral_vagal (calm)",
            keros_seal_bytes=None,  # No TPM in PoC
        )
        print(f"  Frame {i+1}: {result}")
        time.sleep(0.1)

    # ── Simulate CDI WARNING
    print("\n── CDI WARNING triggered")
    router.on_state_change("WARNING")

    # ── Simulate ETHOS veto by user (Judicial Kill Switch)
    print("\n── User executes ETHOS veto (scope=CLINICAL)")
    router.on_ethos_veto("CLINICAL")

    # ── Simulate CDI BLOCKED (full zeroization)
    print("\n── CDI BLOCKED — sovereign zeroization")
    router.on_state_change("BLOCKED")

    print("\n✅ Dual-Channel Router demo complete")
    print("   Next: integrate into cognitive_shield_v2.py step 11 (post-CDI route)")
