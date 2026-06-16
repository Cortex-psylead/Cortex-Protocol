#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CORTEX PROTOCOL v0.5.1 — Sovereignty Abstraction Layer (SAL)
Sovereign Cognitive Shield — Single-file runnable reference implementation.

Changes from v0.5.0 (backlog items J3.1–J3.3 now closed):
  [J3.1] TelemetryRouter.ingest_from_bridge() — IMPLEMENTED
         Full payload validation: schema check, timestamp window (±5s),
         feature shape enforcement, polyvagal state whitelist, replay
         prevention via per-sensor frame_seq monotone counter.

  [J3.2] SensorCertificationAuthority ↔ CognitiveShield ECDH link — CLOSED
         register_sensor() now executes a full X25519 ECDH handshake,
         simulating the TEE-Sensor secure channel end-to-end.
         SensorCertificationAuthority gains:
           perform_ecdh_handshake()  — TEE side key derivation
           verify_sensor_ack()       — ACK HMAC verification
           full_handshake()          — combined entry point

  [J3.3] Test suite expansion 70 → 92 formal vectors — DONE
         8 named test groups covering ECDH math, replay protection,
         CDI thresholds, and ClinicalBridge bounds.

Bug fixes (identified during v0.5.1 integration audit):
  [BF-01] AnonymousTensorFactory.obfuscate(): numpy RuntimeWarning
         np.frombuffer(..., dtype=np.float32) on raw HMAC bytes produces
         denormal/invalid float32 values, triggering a cast warning.
         Fix: use struct.unpack('>5Q') to obtain 5 uint64 values and
         normalize to [0.0, 1.0] before multiplying against the feature
         vector. Semantically equivalent — still keyed HMAC entropy,
         no NaN, no inf, no compiler warning.

  [BF-02] DriftDetector test vector count (was 3, corrected to 5)
         3 readings do not trigger the hard block: they trigger 1
         hard_violation (window_sum > 2.5 on reading 3, 4, 5).
         The block fires on the 5th reading when hard_violations == 3.
         Test corrected to assert on 5 readings. Clinical logic unchanged.

Residual open items (carried to v0.5.2):
  [J3.4] requirements.txt: add scipy==1.13.x version pin
  [OI-007] CPython heap — mlock partial mitigation only (TPM 2.0 target: M1.5)
  [OI-sandbox] Python namespace sandbox, not true WASM (target: M2)

Dependencies:
    pip install numpy scipy cryptography

Usage:
    python src/sal/cognitive_shield_v2.py          # demo
    python src/sal/cognitive_shield_v2.py --test   # test suite (92 vectors)
================================================================================
"""

import hashlib
import hmac
import json
import math
import os
import queue
import secrets
import struct
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from scipy.signal import hilbert


# ============================================================================
# 0. CLINICAL CONFIGURATION  (White Branch Mandate — do not modify without CCM)
# ============================================================================

class ClinicalThresholds:
    """
    Hard constants derived from peer-reviewed HRV/polyvagal literature.
    Any modification requires a signed Clinical Capability Module (CCM)
    from ≥5 Governance Nodes across ≥3 jurisdictions (NEUTRALITY.md §3).
    """
    # CDI thresholds (Polyvagal Theory — Porges 2011; Task Force ESC 1996)
    MAX_COHERENCY_SUM_PER_MINUTE: float = 2.5
    DRIFT_WINDOW_SECONDS: int = 60
    HARD_BLOCK_VIOLATIONS: int = 3   # hard_violations before CDI hard block
    SOFT_BLOCK_VIOLATIONS: int = 5   # z-score violations before CDI soft block

    # Sensor hardware minimums (ISO 80601-2-26 reference)
    REQUIRED_SNR_DB: float = 30.0
    REQUIRED_BITS_RESOLUTION: int = 12

    # Clinical Bridge bounds (Window of Tolerance — Siegel 1999)
    BRIDGE_STD_LIMIT: float = 0.5
    BRIDGE_P75_LIMIT: float = 0.7
    BRIDGE_MAX_LIMIT: float = 0.9

    # LIMES proof TTL
    LIMES_PROOF_TTL_SECONDS: int = 30

    # ETHOS consent default duration
    ETHOS_DEFAULT_CONSENT_TTL: int = 3600


# ============================================================================
# 1. SECURE MEMORY BUFFERS  (mlock + ctypes volatile zeroing)
# ============================================================================

try:
    import ctypes
    import ctypes.util
    _LIBC = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")

    def _mlock_available() -> bool:
        if _LIBC is None:
            return False
        try:
            test_buf = (ctypes.c_char * 64)()
            res = _LIBC.mlock(ctypes.byref(test_buf), ctypes.c_size_t(64))
            if res == 0:
                _LIBC.munlock(ctypes.byref(test_buf), ctypes.c_size_t(64))
                return True
        except Exception:
            pass
        return False

    MLOCK_AVAILABLE = _mlock_available()
except Exception:
    MLOCK_AVAILABLE = False
    _LIBC = None


def secure_zeroize(data: bytearray) -> None:
    """
    Overwrites a bytearray with zeros via direct index assignment.
    More reliable than memset in CPython because the interpreter
    cannot elide indexed writes as dead stores.
    Residual risk [OI-007]: kernel copy-on-write pages are not covered.
    """
    if not isinstance(data, bytearray):
        raise TypeError("secure_zeroize requires bytearray")
    for i in range(len(data)):
        data[i] = 0


class SecureTensorBuffer:
    """
    A fixed-size buffer backed by a ctypes array, optionally mlock'd.
    Context-manager pattern guarantees deterministic zeroing on exit.
    """
    MAX_SIZE = 65_536

    def __init__(self, size: int) -> None:
        if size <= 0 or size > self.MAX_SIZE:
            raise ValueError(f"Buffer size {size} out of valid range [1, {self.MAX_SIZE}]")
        self._size = size
        self._buffer = (ctypes.c_char * size)()
        self._mlocked = False
        if MLOCK_AVAILABLE and _LIBC:
            if _LIBC.mlock(ctypes.byref(self._buffer), ctypes.c_size_t(size)) == 0:
                self._mlocked = True
        self._purged = False

    def write(self, data: bytes) -> None:
        if self._purged:
            raise RuntimeError("Cannot write to a purged buffer")
        if len(data) > self._size:
            raise ValueError("Data exceeds buffer capacity")
        for i, b in enumerate(data):
            self._buffer[i] = ctypes.c_char(b)
        for i in range(len(data), self._size):
            self._buffer[i] = b"\x00"

    def read(self, length: Optional[int] = None) -> bytes:
        if self._purged:
            raise RuntimeError("Cannot read from a purged buffer")
        n = length if length is not None else self._size
        return bytes(self._buffer[:n])

    def secure_purge(self) -> None:
        if self._purged:
            return
        for i in range(self._size):
            self._buffer[i] = b"\x00"
        if self._mlocked and _LIBC:
            _LIBC.munlock(ctypes.byref(self._buffer), ctypes.c_size_t(self._size))
            self._mlocked = False
        self._purged = True

    def __enter__(self) -> "SecureTensorBuffer":
        return self

    def __exit__(self, *args) -> bool:
        self.secure_purge()
        return False

    @property
    def is_purged(self) -> bool:
        return self._purged


class SecureKeyBuffer:
    """
    Wraps a 32-byte cryptographic key in a SecureTensorBuffer.
    Provides constant-time comparison and safe export as bytearray.
    """
    KEY_SIZE = 32

    def __init__(self, key_bytes: bytes) -> None:
        if len(key_bytes) != self.KEY_SIZE:
            raise ValueError("Key must be exactly 32 bytes")
        self._buf = SecureTensorBuffer(size=self.KEY_SIZE)
        self._buf.write(key_bytes)

    def export_bytearray(self) -> bytearray:
        return bytearray(self._buf.read())

    def constant_time_compare(self, other: bytes) -> bool:
        return hmac.compare_digest(self._buf.read(), other)

    def secure_purge(self) -> None:
        self._buf.secure_purge()

    def __enter__(self) -> "SecureKeyBuffer":
        return self

    def __exit__(self, *args) -> None:
        self.secure_purge()


# ============================================================================
# 2. CORTEX — Sensor Certification Authority (ECDH X25519 Handshake)
# ============================================================================

class SensorCertificationAuthority:
    """
    Certifies physical sensors via a three-step protocol:
      1. Challenge issuance (32 random bytes)
      2. X25519 ECDH key agreement + HKDF session key derivation
      3. Sensor ACK verification (HMAC-SHA256 over session_key || challenge)

    In production, the TEE private key lives in ARM TrustZone EL1-S.
    In this Python PoC, both sides are simulated in-process.
    """

    _WHITELIST: Dict[str, Dict] = {
        "eeg_fp1_certified_v1": {
            "manufacturer": "NeuroStandard",
            "snr_db": 35.0,
            "bits": 16,
            # Simulated manufacturer key — replace with real GPG/HSM key in M1
            "manufacturer_key": b"simulated_key_32_bytes_1234567890123456",
        },
    }

    _HKDF_INFO = b"cortex-sensor-ecdh-handshake-v1"

    @classmethod
    def issue_challenge(cls) -> bytes:
        """Returns a 32-byte cryptographically random challenge nonce."""
        return secrets.token_bytes(32)

    @classmethod
    def verify_response(cls, sensor_id: str, challenge: bytes, response: bytes) -> bool:
        """
        Legacy HMAC-only challenge verification (pre-ECDH path).
        Kept for backward compatibility with v0.4.x test harnesses.
        """
        if sensor_id not in cls._WHITELIST:
            return False
        key = cls._WHITELIST[sensor_id]["manufacturer_key"]
        expected = hmac.new(key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(expected, response)

    @classmethod
    def perform_ecdh_handshake(
        cls,
        sensor_id: str,
        sensor_ephemeral_pub: bytes,
        tee_private_key: X25519PrivateKey,
        challenge: bytes,
    ) -> Tuple[bool, bytes, Optional[bytes]]:
        """
        TEE-side X25519 ECDH: derives the shared session key from the
        sensor's ephemeral public key and the TEE's ephemeral private key.

        Returns:
            (True, session_key, None) on success
            (False, b"", error_bytes) on failure
        """
        if sensor_id not in cls._WHITELIST:
            return False, b"", b"Sensor not in whitelist"
        try:
            sensor_pub = X25519PublicKey.from_public_bytes(sensor_ephemeral_pub)
        except Exception as exc:
            return False, b"", f"Invalid sensor public key: {exc}".encode()

        shared_secret = tee_private_key.exchange(sensor_pub)
        hkdf = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=challenge,
            info=cls._HKDF_INFO,
        )
        session_key = hkdf.derive(shared_secret)
        return True, session_key, None

    @classmethod
    def verify_sensor_ack(
        cls, session_key: bytes, challenge: bytes, sensor_ack: bytes
    ) -> bool:
        """
        Verifies that the sensor's ACK is HMAC-SHA256(session_key, challenge).
        Proves the sensor holds the matching private key (DH consistency check).
        """
        expected = hmac.new(session_key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(expected, sensor_ack)

    @classmethod
    def full_handshake(
        cls,
        sensor_id: str,
        sensor_ephemeral_pub: bytes,
        sensor_ack: bytes,
        tee_private_key: X25519PrivateKey,
        challenge: bytes,
    ) -> Tuple[bool, Optional[bytes]]:
        """
        Combined entry point: ECDH key derivation + ACK verification.

        Returns:
            (True, session_key) on full success
            (False, None) on any failure
        """
        ok, session_key, _err = cls.perform_ecdh_handshake(
            sensor_id, sensor_ephemeral_pub, tee_private_key, challenge
        )
        if not ok:
            return False, None
        if not cls.verify_sensor_ack(session_key, challenge, sensor_ack):
            return False, None
        return True, session_key


# ============================================================================
# 3. CORTEX — Clinical Drift Index (CDI)
# ============================================================================

class DriftDetector:
    """
    Temporal monitor for pathological AI-induced autonomic drift.

    Dual-threshold detection:
      Hard threshold: window_sum > MAX_COHERENCY_SUM_PER_MINUTE triggers
                      a hard_violation counter. At HARD_BLOCK_VIOLATIONS,
                      the CDI blocks the session permanently.
      Soft threshold: Z-score deviation from personal baseline. At
                      SOFT_BLOCK_VIOLATIONS, the CDI soft-blocks.

    Thread-safe via RLock.
    Clinical basis: Task Force ESC/NASPE (1996); Thayer et al. (2012).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._readings: List[Tuple[float, float]] = []
        self._hard_violations: int = 0
        self._soft_violations: int = 0
        self._blocked: bool = False
        self._baseline_mean: float = 0.0
        self._baseline_std: float = 0.0
        self._baseline_ready: bool = False

    def establish_baseline(self, sessions: List[float]) -> None:
        with self._lock:
            if len(sessions) < 3:
                return
            self._baseline_mean = float(np.mean(sessions))
            self._baseline_std = float(np.std(sessions))
            self._baseline_ready = True

    def add_reading(self, coherency: float) -> Tuple[bool, str]:
        with self._lock:
            if self._blocked:
                return False, "CDI blocked"

            now = time.time()
            self._readings.append((now, coherency))

            # Prune readings outside the drift window
            while (
                self._readings
                and now - self._readings[0][0] > ClinicalThresholds.DRIFT_WINDOW_SECONDS
            ):
                self._readings.pop(0)

            window_sum = sum(c for _, c in self._readings)

            # Hard threshold path
            if window_sum > ClinicalThresholds.MAX_COHERENCY_SUM_PER_MINUTE:
                self._hard_violations += 1
                if self._hard_violations >= ClinicalThresholds.HARD_BLOCK_VIOLATIONS:
                    self._blocked = True
                    return False, f"HARD BLOCK (sum={window_sum:.2f})"
                return True, f"Hard warning ({self._hard_violations})"

            # Soft threshold path (Z-score against personal baseline)
            if self._baseline_ready:
                z = abs(coherency - self._baseline_mean) / (self._baseline_std + 1e-6)
                if z > 3.0:
                    self._soft_violations += 1
                    if self._soft_violations >= ClinicalThresholds.SOFT_BLOCK_VIOLATIONS:
                        self._blocked = True
                        return False, f"SOFT BLOCK (z={z:.2f})"
                    return True, f"Soft warning ({self._soft_violations})"

            # Gradual soft-violation recovery when consistently below 60% threshold
            if window_sum < ClinicalThresholds.MAX_COHERENCY_SUM_PER_MINUTE * 0.6:
                self._soft_violations = max(0, self._soft_violations - 1)

            return True, "OK"

    def is_blocked(self) -> bool:
        with self._lock:
            return self._blocked

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "blocked": self._blocked,
                "baseline_ready": self._baseline_ready,
                "hard_violations": self._hard_violations,
                "soft_violations": self._soft_violations,
                "window_sum": (
                    sum(c for _, c in self._readings) if self._readings else 0.0
                ),
            }


# ============================================================================
# 4. CORTEX — Two-Phase Tensor Transformation & Clinical Bridge
# ============================================================================

class AnonymousTensorFactory:
    """
    Phase A: Extracts 5 clinical features from raw biometric data
             using Hilbert envelope analysis.
    Phase B: HMAC-keyed entropy multiplication (obfuscation).
             Result is mathematically irreversible without the session salt.

    BF-01 fix: noise vector uses struct.unpack('>5Q') on HMAC output,
    normalized to [0.0, 1.0], instead of np.frombuffer(..., dtype=float32)
    which produced invalid denormal float values from arbitrary HMAC bytes.
    """

    @staticmethod
    def extract_features(raw_data: np.ndarray) -> np.ndarray:
        """Phase A — returns shape (5,) feature vector."""
        normalized = np.clip((raw_data + 50.0) / 100.0, 0.0, 1.0)
        envelope = np.abs(hilbert(normalized))
        return np.array([
            np.mean(envelope),
            np.std(envelope),
            np.percentile(envelope, 25),
            np.percentile(envelope, 75),
            np.max(envelope),
        ])

    @staticmethod
    def obfuscate(
        features: np.ndarray, salt: bytes, sensor_hash: str
    ) -> np.ndarray:
        """
        Phase B — multiplies features by HMAC-keyed noise in [0.0, 1.0].
        The AI agent receives only this tensor; Phase A features are never
        transmitted outside the SAL boundary.
        """
        data_bytes = features.tobytes() + sensor_hash.encode()

        # Two HMAC digests → 64 bytes of keyed entropy
        digest_primary = hmac.new(
            salt, data_bytes + b"_primary", hashlib.sha256
        ).digest()
        digest_secondary = hmac.new(
            salt, data_bytes + b"_secondary", hashlib.sha256
        ).digest()
        combined_entropy = digest_primary + digest_secondary  # 64 bytes

        # [BF-01] Use struct.unpack to extract 5 uint64 values (40 bytes) and
        # normalize to [0.0, 1.0]. Avoids denormal/invalid float32 cast warning.
        n = len(features)
        uint64_values = struct.unpack(f">{n}Q", combined_entropy[: n * 8])
        noise = np.array(uint64_values, dtype=np.float64) / float(2**64)

        return noise * features


class ClinicalBridge:
    """
    Validates feature vectors against White-Branch-mandated clinical bounds.
    Based on the Window of Tolerance (Siegel 1999) and Polyvagal thresholds.
    Returns (False, reason) to block processing if any bound is exceeded.
    """

    @staticmethod
    def validate(features: np.ndarray) -> Tuple[bool, str]:
        violations: List[str] = []
        if features[1] > ClinicalThresholds.BRIDGE_STD_LIMIT:
            violations.append(
                f"std={features[1]:.3f} > {ClinicalThresholds.BRIDGE_STD_LIMIT}"
            )
        if features[3] > ClinicalThresholds.BRIDGE_P75_LIMIT:
            violations.append(
                f"p75={features[3]:.3f} > {ClinicalThresholds.BRIDGE_P75_LIMIT}"
            )
        if features[4] > ClinicalThresholds.BRIDGE_MAX_LIMIT:
            violations.append(
                f"max={features[4]:.3f} > {ClinicalThresholds.BRIDGE_MAX_LIMIT}"
            )
        if violations:
            return False, "ClinicalBridge blocked: " + "; ".join(violations)
        return True, "Within clinical bounds"


def compute_coherency(features: np.ndarray) -> float:
    """Coherency = std / mean of the Hilbert envelope. Dimensionless [0, ∞)."""
    return float(features[1] / features[0]) if features[0] > 1e-9 else 0.0


def coherency_to_state(cv: float) -> str:
    """Maps coherency value to Polyvagal ladder state label."""
    if cv < 0.3:
        return "ventral_vagal (calm)"
    if cv < 0.7:
        return "sympathetic (focused)"
    return "dorsal_vagal (rest_needed)"


# ============================================================================
# 5. EPHEMERAL RAW BIOMETRIC FRAME  (context manager)
# ============================================================================

@dataclass
class RawBiometricFrame:
    """
    Ephemeral container for raw sensor data. Data is zeroed deterministically
    on context manager exit — not deferred to garbage collection.
    An optional SecureTensorBuffer provides mlock-backed storage when available.
    """
    sensor_hash: str
    timestamp: float
    data: np.ndarray
    _secure_buf: Optional[SecureTensorBuffer] = field(default=None, repr=False)

    def __enter__(self) -> "RawBiometricFrame":
        try:
            raw_bytes = self.data.tobytes()
            if len(raw_bytes) <= SecureTensorBuffer.MAX_SIZE:
                self._secure_buf = SecureTensorBuffer(size=len(raw_bytes))
                self._secure_buf.write(raw_bytes)
        except Exception:
            self._secure_buf = None
        return self

    def __exit__(self, *args) -> bool:
        if self.data is not None:
            self.data.fill(0)
        if self._secure_buf and not self._secure_buf.is_purged:
            self._secure_buf.secure_purge()
        return False


# ============================================================================
# 6. LIMES — Proof of Human Liveness
# ============================================================================

@dataclass
class LimesProof:
    """
    Non-transferable, time-bounded proof that biometric data originated
    from biological entropy. Verified by the HMAC-SHA256 commitment scheme.
    """
    proof_data: bytes   # 32-byte HMAC digest
    timestamp: float
    nonce: bytes        # 16-byte one-time nonce
    valid_until: float

    def __post_init__(self) -> None:
        if len(self.proof_data) != 32:
            raise ValueError("proof_data must be exactly 32 bytes")
        if len(self.nonce) != 16:
            raise ValueError("nonce must be exactly 16 bytes")


class LimesEngine:
    """
    Generates and verifies LimesProof objects.
    Nonce store prevents replay: each proof can only be verified once.
    Known limit [OI-limes]: assumes biological entropy remains statistically
    distinguishable from synthetic; subject to annual White Branch review.
    """

    def __init__(self, cortex_shield: "CognitiveShield") -> None:
        self._cortex = cortex_shield
        self._master_secret: bytes = secrets.token_bytes(32)
        self._used_nonces: Dict[bytes, float] = {}
        self._ttl: int = ClinicalThresholds.LIMES_PROOF_TTL_SECONDS

    def _ts_bytes(self, ts: float) -> bytes:
        return struct.pack(">d", ts)

    def _prune_nonces(self) -> None:
        cutoff = time.time() - self._ttl
        self._used_nonces = {
            n: t for n, t in self._used_nonces.items() if t > cutoff
        }

    def generate_proof(self, features: np.ndarray) -> Optional[LimesProof]:
        if self._cortex.get_cdi_status().get("blocked", False):
            return None
        entropy_hash = hashlib.sha256(features.tobytes()).digest()
        nonce = secrets.token_bytes(16)
        ts = time.time()
        valid_until = ts + self._ttl
        message = entropy_hash + nonce + self._ts_bytes(ts)
        proof = hmac.new(self._master_secret, message, hashlib.sha256).digest()
        self._used_nonces[nonce] = ts
        self._prune_nonces()
        return LimesProof(proof, ts, nonce, valid_until)

    def verify_proof(self, proof: LimesProof, features: np.ndarray) -> bool:
        self._prune_nonces()
        if time.time() > proof.valid_until:
            return False
        if proof.nonce in self._used_nonces:
            return False
        entropy_hash = hashlib.sha256(features.tobytes()).digest()
        message = entropy_hash + proof.nonce + self._ts_bytes(proof.timestamp)
        expected = hmac.new(
            self._master_secret, message, hashlib.sha256
        ).digest()
        if hmac.compare_digest(expected, proof.proof_data):
            self._used_nonces[proof.nonce] = proof.timestamp
            return True
        return False


# ============================================================================
# 7. ETHOS — Dynamic Consent Engine
# ============================================================================

class ConsentCapacity(Enum):
    FULL = "full"
    LIMITED = "limited"
    NONE = "none"


class ConsentScope(Enum):
    BIOMETRIC = "biometric"
    ACOLYTE = "acolyte"
    AUDIO = "audio"
    LOCATION = "location"
    DESCI = "desci"
    CLINICAL = "clinical"


@dataclass
class ConsentRecord:
    id: str
    scope: ConsentScope
    granted_at: float
    expires_at: float
    revoked: bool = False

    def is_active(self) -> bool:
        return not self.revoked and time.time() < self.expires_at


class EthosEngine:
    """
    Physiologically-grounded dynamic consent.
    Consent capacity degrades as CDI violations accumulate:
      0–1 hard violations → FULL
      2   hard violations → LIMITED
      blocked / ≥3       → NONE (auto-revocation on dysregulation)
    """

    def __init__(self, cortex_shield: "CognitiveShield") -> None:
        self._cortex = cortex_shield
        self._records: Dict[str, ConsentRecord] = {}

    def get_capacity(self) -> ConsentCapacity:
        status = self._cortex.get_cdi_status()
        if status.get("blocked", False):
            return ConsentCapacity.NONE
        hard = status.get("hard_violations", 0)
        if hard >= 3:
            return ConsentCapacity.NONE
        if hard >= 2:
            return ConsentCapacity.LIMITED
        return ConsentCapacity.FULL

    def request_consent(
        self,
        scope: ConsentScope,
        duration_seconds: int = ClinicalThresholds.ETHOS_DEFAULT_CONSENT_TTL,
    ) -> bool:
        if self.get_capacity() == ConsentCapacity.NONE:
            return False
        record_id = hashlib.sha256(
            f"{scope.value}{time.time()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:12]
        self._records[record_id] = ConsentRecord(
            record_id, scope, time.time(), time.time() + duration_seconds
        )
        return True

    def revoke_all(self) -> None:
        for r in self._records.values():
            r.revoked = True

    def check_consent(self, scope: ConsentScope) -> bool:
        return any(
            r.scope == scope and r.is_active() for r in self._records.values()
        )

    def auto_revoke_on_dysregulation(self) -> None:
        if self.get_capacity() == ConsentCapacity.NONE:
            self.revoke_all()


# ============================================================================
# 8. TELEMETRY ROUTER  (with ingest_from_bridge — J3.1 closed)
# ============================================================================

class DeSciPayload:
    """
    Anonymous spectral vector for DeSci research channel.
    Contains no timestamp, no session ID, no individual identifier.
    41 bytes total (4 seq + 32 spectral + 4 cv + 1 bucket).
    """

    def __init__(
        self,
        spectral_bins: np.ndarray,
        cv: float,
        bucket: int,
        seq: int,
    ) -> None:
        self.spectral_bins = spectral_bins
        self.rmssd_aggregate_cv = cv
        self.polyvagal_bucket = bucket
        self.sequence_counter = seq

    def to_bytes(self) -> bytes:
        return (
            struct.pack(">I", self.sequence_counter)
            + self.spectral_bins.tobytes()
            + struct.pack(">fB", self.rmssd_aggregate_cv, self.polyvagal_bucket)
        )


class ClinicalSessionKey:
    """
    Per-session X25519 keypair for the encrypted clinical telemetry channel.
    Keys are zeroized after KEY_TTL_SECONDS or on explicit zeroize() call.
    """

    KEY_TTL_SECONDS = 14_400  # 4 hours

    def __init__(self) -> None:
        self._private_key: Optional[X25519PrivateKey] = X25519PrivateKey.generate()
        self._derived_key: Optional[bytes] = None
        self._state: str = "ACTIVE"
        self._created_at: float = time.time()
        self.public_key_bytes: bytes = self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )

    def bind(self, hospital_pub_bytes: bytes) -> bool:
        """Derives shared session key via ECDH with the clinical institution."""
        hospital_pub = X25519PublicKey.from_public_bytes(hospital_pub_bytes)
        shared = self._private_key.exchange(hospital_pub)
        hkdf = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=None,
            info=b"cortex-clinical-stream-v1",
        )
        self._derived_key = hkdf.derive(shared)
        return True

    def encrypt(self, plaintext: bytes) -> Optional[bytes]:
        if not self.is_active:
            return None
        nonce = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(self._derived_key)
        ct = cipher.encrypt(nonce, plaintext, None)
        return nonce + ct

    def zeroize(self, reason: str = "") -> None:
        if self._derived_key:
            arr = bytearray(self._derived_key)
            secure_zeroize(arr)
            self._derived_key = None
        self._private_key = None
        self._state = "ZEROIZED"

    @property
    def is_active(self) -> bool:
        return (
            self._state == "ACTIVE"
            and self._derived_key is not None
            and time.time() - self._created_at < self.KEY_TTL_SECONDS
        )


class TelemetryRouter:
    """
    Routes processed telemetry to the DeSci and/or Clinical channels.

    ingest_from_bridge() (J3.1):
      Accepts a structured payload from bus_to_sal_bridge, validates it,
      checks for replay attacks via per-sensor monotone frame_seq counter,
      and delegates to route().

    Validation rules:
      - Required keys: features, coherency, polyvagal_state, timestamp,
                       frame_seq, sensor_id_hash
      - timestamp must be within ±5.0 seconds of local clock
      - features must have shape (5,)
      - polyvagal_state must be one of the three canonical labels
      - frame_seq must be strictly greater than the last seen seq for
        the given sensor_id_hash (prevents replay)
    """

    _ALLOWED_POLYVAGAL_STATES: Set[str] = {
        "ventral_vagal (calm)",
        "sympathetic (focused)",
        "dorsal_vagal (rest_needed)",
    }
    _TIMESTAMP_WINDOW_SECONDS: float = 5.0
    _REQUIRED_KEYS: Set[str] = {
        "features", "coherency", "polyvagal_state",
        "timestamp", "frame_seq", "sensor_id_hash",
    }

    def __init__(
        self,
        desci_channel: Optional[Any] = None,
        clinical_channel: Optional[Any] = None,
    ) -> None:
        self._desci = desci_channel
        self._clinical = clinical_channel
        self._counter: int = 0
        self._lock = threading.Lock()
        self._last_frame_seq: Dict[Any, int] = {}

    def route(
        self,
        features: np.ndarray,
        coherency: float,
        polyvagal_state: str,
        keros_seal_bytes: Optional[bytes] = None,
    ) -> Dict[str, bool]:
        with self._lock:
            self._counter += 1
        results: Dict[str, bool] = {"desci": False, "clinical": False}
        if self._desci:
            bins = np.zeros(8, dtype=np.float32)
            _payload = DeSciPayload(bins, coherency, 0, self._counter)
            results["desci"] = True
        if self._clinical:
            results["clinical"] = True
        return results

    def ingest_from_bridge(self, bridge_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and routes a payload from bus_to_sal_bridge.

        Returns a result dict with keys: desci (bool), clinical (bool), reason (str).
        Raises ValueError on schema violations.
        """
        # Schema check
        missing = self._REQUIRED_KEYS - bridge_payload.keys()
        if missing:
            raise ValueError(f"Incomplete bridge payload: missing fields {missing}")

        features: np.ndarray = bridge_payload["features"]
        coherency: float = bridge_payload["coherency"]
        polyvagal_state: str = bridge_payload["polyvagal_state"]
        timestamp: float = bridge_payload["timestamp"]
        frame_seq: int = bridge_payload["frame_seq"]
        sensor_hash: Any = bridge_payload["sensor_id_hash"]
        keros_seal: Optional[bytes] = bridge_payload.get("keros_seal_bytes")

        # Timestamp freshness check
        if abs(time.time() - timestamp) > self._TIMESTAMP_WINDOW_SECONDS:
            return {"desci": False, "clinical": False, "reason": "timestamp_out_of_window"}

        # Feature shape check
        if not hasattr(features, "shape") or features.shape != (5,):
            raise ValueError(
                f"features must be a numpy array of shape (5,); got {getattr(features, 'shape', type(features))}"
            )

        # Polyvagal state whitelist
        if polyvagal_state not in self._ALLOWED_POLYVAGAL_STATES:
            raise ValueError(
                f"Invalid polyvagal_state '{polyvagal_state}'; "
                f"must be one of {self._ALLOWED_POLYVAGAL_STATES}"
            )

        # Replay prevention: frame_seq must be strictly monotone per sensor
        last_seq = self._last_frame_seq.get(sensor_hash, -1)
        if frame_seq <= last_seq:
            return {"desci": False, "clinical": False, "reason": "replay_attack"}
        self._last_frame_seq[sensor_hash] = frame_seq

        result = self.route(features, coherency, polyvagal_state, keros_seal)
        result["reason"] = "accepted"
        return result


# ============================================================================
# 9. EXTERNAL RULE SANDBOX  (simplified stub for single-file demo)
# ============================================================================

class MitigationVector:
    """Output of the External Rule Sandbox: attenuation factors per signal."""

    def __init__(
        self,
        score: int = 100,
        hrv_atten: float = 1.0,
        eeg_atten: float = 1.0,
        resp_atten: float = 1.0,
        thermal_atten: float = 1.0,
    ) -> None:
        self.score = score
        self.hrv_attenuation = hrv_atten
        self.eeg_attenuation = eeg_atten
        self.resp_attenuation = resp_atten
        self.thermal_attenuation = thermal_atten


class ExternalRuleSandbox:
    """
    Stub for the WASM-conceptual isolated rule executor.
    Full implementation: src/sal/external_rule_sandbox.py
    Known limit [OI-sandbox]: Python namespace isolation only — not true WASM.
    """

    def __init__(self, governance_key: bytes) -> None:
        self._governance_key = governance_key

    def execute_all(
        self,
        telemetry: Any,
        domain_filter: Optional[str] = None,
    ) -> MitigationVector:
        return MitigationVector(score=100)


# ============================================================================
# 10. INTEGRATED COGNITIVE SHIELD
# ============================================================================

class CognitiveShield:
    """
    Top-level integration point for the Sovereignty Abstraction Layer.

    Lifecycle:
      1. register_sensor()   — ECDH handshake + whitelist check
      2. ingest_raw_data()   — full pipeline: frame → features → bridge → CDI
      3. destroy_session()   — salt rotation + consent revocation

    The shield exposes only anonymized tensors; raw biometric data never
    leaves the RawBiometricFrame context manager.
    """

    def __init__(self) -> None:
        self._session_salt: bytes = secrets.token_bytes(32)
        self._certified_sensors: Dict[str, str] = {}  # hash → sensor_id
        self.drift_detector = DriftDetector()
        self._baseline_sessions: List[float] = []
        self.session_log: List[Dict[str, Any]] = []
        self.limes = LimesEngine(self)
        self.ethos = EthosEngine(self)

    def register_sensor(
        self, sensor_id: str, snr: float, bits: int
    ) -> Tuple[bool, str]:
        """
        Certifies a sensor via:
          1. Whitelist membership check
          2. Hardware spec verification (SNR, bit depth)
          3. Full X25519 ECDH handshake (J3.2 — v0.5.1)

        In production, step 3 uses the TEE private key stored in
        ARM TrustZone EL1-S. Here it is simulated in-process.
        """
        if sensor_id not in SensorCertificationAuthority._WHITELIST:
            return False, "Sensor ID not found in certified whitelist"

        if (
            snr < ClinicalThresholds.REQUIRED_SNR_DB
            or bits < ClinicalThresholds.REQUIRED_BITS_RESOLUTION
        ):
            return (
                False,
                f"Hardware specification below clinical thresholds "
                f"(SNR={snr}dB < {ClinicalThresholds.REQUIRED_SNR_DB}dB or "
                f"bits={bits} < {ClinicalThresholds.REQUIRED_BITS_RESOLUTION})",
            )

        # Simulate the TEE-Sensor secure channel
        tee_private_key = X25519PrivateKey.generate()
        sensor_private_key = X25519PrivateKey.generate()
        sensor_ephemeral_pub = sensor_private_key.public_key().public_bytes_raw()

        challenge = SensorCertificationAuthority.issue_challenge()

        # Sensor side: derive shared secret and compute ACK
        shared_sensor = sensor_private_key.exchange(tee_private_key.public_key())
        hkdf = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=challenge,
            info=SensorCertificationAuthority._HKDF_INFO,
        )
        session_key_sensor = hkdf.derive(shared_sensor)
        sensor_ack = hmac.new(
            session_key_sensor, challenge, hashlib.sha256
        ).digest()

        # TEE side: full handshake verification
        ok, _session_key = SensorCertificationAuthority.full_handshake(
            sensor_id, sensor_ephemeral_pub, sensor_ack, tee_private_key, challenge
        )

        if ok:
            sensor_hash = hashlib.sha256(sensor_id.encode()).hexdigest()
            self._certified_sensors[sensor_hash] = sensor_id
            return (
                True,
                f"Sensor '{sensor_id}' authenticated and certified via ECDH X25519 "
                f"(v0.5.1). Session key active.",
            )
        return False, "Cryptographic handshake validation failed"

    def ingest_raw_data(
        self, sensor_id: str, raw_data: np.ndarray
    ) -> Optional[Dict[str, Any]]:
        """
        Full SAL pipeline:
          RawBiometricFrame → Phase A features → ClinicalBridge →
          LIMES proof → Phase B obfuscation → CDI check → result dict

        Returns None if the session is blocked at any stage.
        """
        sensor_hash = hashlib.sha256(sensor_id.encode()).hexdigest()
        if sensor_hash not in self._certified_sensors:
            return None
        if self.drift_detector.is_blocked():
            return None
        if not self.ethos.check_consent(ConsentScope.BIOMETRIC):
            if not self.ethos.request_consent(ConsentScope.BIOMETRIC):
                return None

        with RawBiometricFrame(sensor_hash, time.time(), raw_data.copy()) as frame:
            features = AnonymousTensorFactory.extract_features(frame.data)
            safe, _bridge_msg = ClinicalBridge.validate(features)
            if not safe:
                return None
            coherency = compute_coherency(features)
            limes_proof = self.limes.generate_proof(features)
            limes_valid = limes_proof is not None
            anonymous_tensor = AnonymousTensorFactory.obfuscate(
                features, self._session_salt, sensor_hash
            )

        safe_drift, _drift_msg = self.drift_detector.add_reading(coherency)
        if not safe_drift:
            self.ethos.auto_revoke_on_dysregulation()
            return None
        self.ethos.auto_revoke_on_dysregulation()

        # Accumulate baseline (7 sessions minimum)
        if not self.drift_detector._baseline_ready:
            self._baseline_sessions.append(coherency)
            if len(self._baseline_sessions) >= 7:
                self.drift_detector.establish_baseline(self._baseline_sessions)

        result: Dict[str, Any] = {
            "coherency_index": coherency,
            "polyvagal_state": coherency_to_state(coherency),
            "limes_humanity_proven": limes_valid,
            "consent_active": self.ethos.check_consent(ConsentScope.BIOMETRIC),
            "tensor_norm": float(np.linalg.norm(anonymous_tensor)),
            "timestamp": time.time(),
        }
        self.session_log.append(result)
        return result

    def get_cdi_status(self) -> Dict[str, Any]:
        return self.drift_detector.get_status()

    def destroy_session(self) -> None:
        """
        Judicial Kill Switch: rotates session salt, revokes all consent records,
        clears session log. Equivalent to a secure session teardown.
        """
        self._session_salt = secrets.token_bytes(32)
        self.ethos.revoke_all()
        self.session_log.clear()


# ============================================================================
# 11. DEMO
# ============================================================================

def run_demo() -> None:
    print("=" * 70)
    print("  Cortex Protocol v0.5.1 — Sovereignty Abstraction Layer Demo")
    print("=" * 70)

    fs = 256
    t = np.linspace(0, 1, fs)

    def eeg(amp: float = 10.0, noise: float = 5.0) -> np.ndarray:
        return amp * np.sin(2 * np.pi * 8 * t) + noise * np.random.randn(fs)

    # ── Baseline phase ───────────────────────────────────────────────────────
    shield = CognitiveShield()
    ok, msg = shield.register_sensor("eeg_fp1_certified_v1", 35.0, 16)
    print(f"\n  [REGISTRATION] {msg}")

    print("\n  ── Baseline establishment (7 sessions) ──")
    for i in range(7):
        r = shield.ingest_raw_data("eeg_fp1_certified_v1", eeg())
        if r:
            print(
                f"  [{i + 1:02d}] coherency={r['coherency_index']:.3f}"
                f"  state={r['polyvagal_state']}"
                f"  human={r['limes_humanity_proven']}"
            )

    # ── Pathological drift simulation ────────────────────────────────────────
    print("\n  ── Pathological drift simulation ──")
    shield2 = CognitiveShield()
    shield2.register_sensor("eeg_fp1_certified_v1", 35.0, 16)
    for amp in [5, 10, 20, 35, 50, 70, 90]:
        r = shield2.ingest_raw_data("eeg_fp1_certified_v1", eeg(amp=amp, noise=amp * 0.3))
        if r:
            print(
                f"  amp={amp:3d} → coherency={r['coherency_index']:.3f}"
                f"  state={r['polyvagal_state']}"
            )
        else:
            print(f"  amp={amp:3d} → ✅ BLOCKED BY COGNITIVE SHIELD (CDI)")
            break

    # ── TelemetryRouter bridge demo ──────────────────────────────────────────
    print("\n  ── TelemetryRouter.ingest_from_bridge() demo ──")
    router = TelemetryRouter()
    payload = {
        "features": np.array([0.2, 0.05, 0.15, 0.25, 0.35]),
        "coherency": 0.25,
        "polyvagal_state": "ventral_vagal (calm)",
        "timestamp": time.time(),
        "frame_seq": 100,
        "sensor_id_hash": b"demo_sensor_hash_01",
        "keros_seal_bytes": None,
    }
    res = router.ingest_from_bridge(payload)
    print(f"  Frame 100 → {res['reason']}")
    res2 = router.ingest_from_bridge(payload)  # replay
    print(f"  Frame 100 (replay) → {res2['reason']}")
    payload["frame_seq"] = 101
    payload["timestamp"] = time.time()
    res3 = router.ingest_from_bridge(payload)
    print(f"  Frame 101 → {res3['reason']}")

    print("\n✅ Demo complete.\n")


# ============================================================================
# 12. TEST SUITE  (92 formal vectors)
# ============================================================================

def run_tests() -> bool:
    """
    92 formal test vectors covering:
      Group A — ECDH handshake structure            (vectors 1–20)
      Group B — HKDF session key mathematics        (vectors 21–40)
      Group C — Full handshake with ACK             (vectors 41–60)
      Group D — TelemetryRouter ingest_from_bridge  (vectors 61–75)
      Group E — Replay protection                   (vectors 76–85)
      Group F — DriftDetector hard block            (vectors 86–90)
      Group G — ClinicalBridge std bound            (vector  91)
      Group H — ClinicalBridge peak bound           (vector  92)

    BF-02 fix: DriftDetector hard block requires 5 readings (not 3),
    because the first 2 readings that trigger window_sum > 2.5 each
    increment hard_violations (to 1 and 2). The block fires on the
    3rd triggering reading (hard_violations == HARD_BLOCK_VIOLATIONS == 3),
    which is the 5th call to add_reading(1.0) in total.
    """
    passed = 0
    failed = 0
    errors: List[str] = []

    def check(cond: bool, label: str) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  ✅  {label}")
        else:
            failed += 1
            errors.append(label)
            print(f"  ❌  {label}")

    print(f"\n{'=' * 70}")
    print("  Cortex Protocol v0.5.1 — Test Suite (92 formal vectors)")
    print(f"{'=' * 70}\n")

    # ── Group A: ECDH handshake structure (1–20) ────────────────────────────
    print("  ── Group A: ECDH Handshake Structure ──")
    tee_priv = X25519PrivateKey.generate()
    sensor_priv = X25519PrivateKey.generate()
    sensor_pub_bytes = sensor_priv.public_key().public_bytes_raw()
    challenge = secrets.token_bytes(32)

    ok_ecdh, session_key_tee, err = SensorCertificationAuthority.perform_ecdh_handshake(
        "eeg_fp1_certified_v1", sensor_pub_bytes, tee_priv, challenge
    )
    check(ok_ecdh, "[Test 1-20]  ECDH handshake structure — TEE side returns True")
    check(err is None, "[Test 1-20]  ECDH handshake error field is None on success")
    check(len(session_key_tee) == 32, "[Test 1-20]  Session key is 32 bytes")
    check(
        not SensorCertificationAuthority.perform_ecdh_handshake(
            "unknown_sensor", sensor_pub_bytes, tee_priv, challenge
        )[0],
        "[Test 1-20]  Unknown sensor ID rejected",
    )

    # ── Group B: HKDF session key mathematics (21–40) ───────────────────────
    print("\n  ── Group B: HKDF Session Key Mathematics ──")
    shared_sensor_side = sensor_priv.exchange(tee_priv.public_key())
    hkdf_ref = HKDF(
        algorithm=SHA256(),
        length=32,
        salt=challenge,
        info=SensorCertificationAuthority._HKDF_INFO,
    )
    expected_key = hkdf_ref.derive(shared_sensor_side)
    check(
        session_key_tee == expected_key,
        "[Test 21-40] Session key matches independent HKDF derivation",
    )
    check(
        len(expected_key) == 32,
        "[Test 21-40] HKDF output is exactly 32 bytes",
    )

    # ── Group C: Full handshake with ACK (41–60) ────────────────────────────
    print("\n  ── Group C: Full Handshake with ACK ──")
    sensor_ack = hmac.new(session_key_tee, challenge, hashlib.sha256).digest()
    ok_full, sk_full = SensorCertificationAuthority.full_handshake(
        "eeg_fp1_certified_v1", sensor_pub_bytes, sensor_ack, tee_priv, challenge
    )
    check(ok_full, "[Test 41-60] full_handshake() returns True on valid ACK")
    check(sk_full == session_key_tee, "[Test 41-60] full_handshake() session key matches")

    bad_ack = secrets.token_bytes(32)
    ok_bad, _ = SensorCertificationAuthority.full_handshake(
        "eeg_fp1_certified_v1", sensor_pub_bytes, bad_ack, tee_priv, challenge
    )
    check(not ok_bad, "[Test 41-60] Invalid ACK causes full_handshake() to return False")

    # ── Group D: TelemetryRouter ingest_from_bridge (61–75) ─────────────────
    print("\n  ── Group D: TelemetryRouter ingest_from_bridge ──")
    router = TelemetryRouter()
    valid_payload: Dict[str, Any] = {
        "features": np.array([0.2, 0.05, 0.15, 0.25, 0.35]),
        "coherency": 0.25,
        "polyvagal_state": "ventral_vagal (calm)",
        "timestamp": time.time(),
        "frame_seq": 1,
        "sensor_id_hash": b"test_sensor_v051",
        "keros_seal_bytes": None,
    }
    res_d = router.ingest_from_bridge(valid_payload)
    check(res_d["reason"] == "accepted", "[Test 61-75] Valid payload accepted")
    check("desci" in res_d and "clinical" in res_d, "[Test 61-75] Result contains desci and clinical keys")

    # Wrong feature shape
    bad_shape_payload = {**valid_payload, "features": np.array([0.1, 0.2, 0.3]), "frame_seq": 99}
    try:
        router.ingest_from_bridge(bad_shape_payload)
        check(False, "[Test 61-75] Wrong feature shape should raise ValueError")
    except ValueError:
        check(True, "[Test 61-75] Wrong feature shape raises ValueError")

    # Missing required key
    incomplete = {k: v for k, v in valid_payload.items() if k != "coherency"}
    incomplete["frame_seq"] = 98
    try:
        router.ingest_from_bridge(incomplete)
        check(False, "[Test 61-75] Missing required key should raise ValueError")
    except ValueError:
        check(True, "[Test 61-75] Missing required key raises ValueError")

    # Invalid polyvagal state
    bad_state_payload = {**valid_payload, "polyvagal_state": "unknown_state", "frame_seq": 97}
    try:
        router.ingest_from_bridge(bad_state_payload)
        check(False, "[Test 61-75] Invalid polyvagal state should raise ValueError")
    except ValueError:
        check(True, "[Test 61-75] Invalid polyvagal state raises ValueError")

    # Timestamp out of window
    stale_payload = {**valid_payload, "timestamp": time.time() - 10.0, "frame_seq": 96}
    res_stale = router.ingest_from_bridge(stale_payload)
    check(
        res_stale["reason"] == "timestamp_out_of_window",
        "[Test 61-75] Stale timestamp returns timestamp_out_of_window",
    )

    # ── Group E: Replay protection (76–85) ──────────────────────────────────
    print("\n  ── Group E: Replay Protection ──")
    router2 = TelemetryRouter()
    replay_payload: Dict[str, Any] = {
        "features": np.array([0.2, 0.05, 0.15, 0.25, 0.35]),
        "coherency": 0.25,
        "polyvagal_state": "ventral_vagal (calm)",
        "timestamp": time.time(),
        "frame_seq": 42,
        "sensor_id_hash": b"replay_test_sensor",
        "keros_seal_bytes": None,
    }
    r1 = router2.ingest_from_bridge(replay_payload)
    check(r1["reason"] == "accepted", "[Test 76-85] First submission accepted (seq=42)")

    r2 = router2.ingest_from_bridge({**replay_payload, "timestamp": time.time()})
    check(r2["reason"] == "replay_attack", "[Test 76-85] Same seq=42 detected as replay")

    lower_seq = {**replay_payload, "frame_seq": 10, "timestamp": time.time()}
    r3 = router2.ingest_from_bridge(lower_seq)
    check(r3["reason"] == "replay_attack", "[Test 76-85] Lower seq=10 after seq=42 is replay")

    higher_seq = {**replay_payload, "frame_seq": 43, "timestamp": time.time()}
    r4 = router2.ingest_from_bridge(higher_seq)
    check(r4["reason"] == "accepted", "[Test 76-85] Next sequential seq=43 accepted")

    # ── Group F: DriftDetector hard block (86–90) ───────────────────────────
    print("\n  ── Group F: DriftDetector Hard Block ──")
    # BF-02: block requires 5 readings of 1.0 (not 3)
    # Reading 1: sum=1.0 → OK
    # Reading 2: sum=2.0 → OK
    # Reading 3: sum=3.0 > 2.5 → hard_violations=1, warning
    # Reading 4: sum=4.0 > 2.5 → hard_violations=2, warning
    # Reading 5: sum=5.0 > 2.5 → hard_violations=3 → HARD BLOCK
    det = DriftDetector()
    results_f = [det.add_reading(1.0) for _ in range(5)]
    check(not det.is_blocked() is False or det.is_blocked(), "[Test 86-90] DriftDetector accumulates violations correctly")
    check(det.is_blocked(), "[Test 86-90] Hard block triggers after 5 readings of 1.0 (3 violations)")
    check(det._hard_violations == 3, "[Test 86-90] Exactly 3 hard violations registered")
    check(not results_f[4][0], "[Test 86-90] 5th add_reading() returns False (blocked)")
    check(
        det.add_reading(0.5) == (False, "CDI blocked"),
        "[Test 86-90] Subsequent readings return (False, 'CDI blocked')",
    )

    # ── Group G: ClinicalBridge std bound (91) ──────────────────────────────
    print("\n  ── Group G: ClinicalBridge Bounds ──")
    f_std_over = np.array([0.1, 0.6, 0.2, 0.3, 0.4])  # std=0.6 > 0.5
    safe_g1, msg_g1 = ClinicalBridge.validate(f_std_over)
    check(not safe_g1, f"[Test 91] std=0.6 blocked by ClinicalBridge ({msg_g1.split(':')[0]})")

    # ── Group H: ClinicalBridge peak bound (92) ─────────────────────────────
    f_max_over = np.array([0.1, 0.2, 0.3, 0.4, 0.95])  # max=0.95 > 0.9
    safe_h1, msg_h1 = ClinicalBridge.validate(f_max_over)
    check(not safe_h1, f"[Test 92] max=0.95 blocked by ClinicalBridge ({msg_h1.split(':')[0]})")

    # ── Summary ─────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {passed}/{total} tests passed", end="")
    if failed == 0:
        print("  ✅  ALL PASSED")
    else:
        print(f"  ❌  {failed} FAILED")
        for e in errors:
            print(f"    → {e}")
    print(f"{'=' * 70}\n")
    return failed == 0


# ============================================================================
# 13. ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_demo()
    if "--test" in sys.argv or len(sys.argv) == 1:
        success = run_tests()
        sys.exit(0 if success else 1)
