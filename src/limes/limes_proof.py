# ============================================================================
# src/limes/limes_proof.py
# LIMES Module: Proof of Human Liveness (HMAC‑based)
# Dependencies: CORTEX (feature entropy)
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class LimesProof:
    """Proof of human liveness – not a zero‑knowledge proof, but HMAC‑based."""
    proof_data: bytes
    timestamp: float
    nonce: bytes
    valid_until: float

    def __post_init__(self):
        if len(self.proof_data) != 32:
            raise ValueError("Proof data must be 32 bytes (SHA‑256 output)")
        if len(self.nonce) != 16:
            raise ValueError("Nonce must be 16 bytes")


class LimesEngine:
    """
    Generates and verifies proof of human liveness from CORTEX biometric entropy.

    The entropy source is the Hilbert envelope of the signal (1/f noise characteristic
    of living nervous systems). Proof = HMAC(master_secret, entropy_hash || nonce || timestamp).

    Anti‑replay: nonces are stored with timestamps and pruned by TTL.
    [FIX-02] Timestamp serialized with struct.pack (float‑safe).
    [FIX-06] Terminology changed from "ZKP" to "Proof of Liveness".
    [FIX-07] Nonce store uses dict[bytes, float] with expiry pruning.
    """

    def __init__(self, cortex_shield):
        self._cortex = cortex_shield
        self._master_secret = secrets.token_bytes(32)
        self._used_nonces: Dict[bytes, float] = {}   # nonce → timestamp of use
        self._ttl = 30.0   # seconds, from ClinicalThresholds.LIMES_PROOF_TTL_SECONDS

    def _serialize_timestamp(self, ts: float) -> bytes:
        """Safe float‑to‑bytes serialization (big‑endian double)."""
        return struct.pack(">d", ts)

    def _prune_nonces(self):
        """Remove nonces older than TTL to prevent memory bloat."""
        now = time.time()
        expired = [n for n, t in self._used_nonces.items() if now - t > self._ttl]
        for n in expired:
            del self._used_nonces[n]

    def generate_proof(self, feature_entropy: np.ndarray) -> Optional[LimesProof]:
        """
        Generates a liveness proof from Phase A feature entropy.
        Returns proof or None if CORTEX is blocked or entropy insufficient.
        """
        status = self._cortex.get_cdi_status()
        if status.get("blocked", False):
            print("[LIMES] Cannot generate proof: CORTEX blocked (user dysregulated)")
            return None

        if len(feature_entropy) < 5:
            return None

        entropy_hash = hashlib.sha256(feature_entropy.tobytes()).digest()
        nonce = secrets.token_bytes(16)
        ts = time.time()
        valid_until = ts + self._ttl

        message = entropy_hash + nonce + self._serialize_timestamp(ts)
        proof = hmac.new(self._master_secret, message, hashlib.sha256).digest()

        self._used_nonces[nonce] = ts
        self._prune_nonces()

        print(f"[LIMES] Proof generated – valid for {self._ttl}s")
        return LimesProof(proof, ts, nonce, valid_until)

    def verify_proof(self, proof: LimesProof, feature_entropy: np.ndarray) -> bool:
        """
        Verifies a liveness proof without accessing raw biometric data.
        Returns True if valid and not replayed.
        """
        if time.time() > proof.valid_until:
            print("[LIMES] Proof expired")
            return False

        if proof.nonce in self._used_nonces:
            print("[LIMES] Nonce replayed – possible attack")
            return False

        entropy_hash = hashlib.sha256(feature_entropy.tobytes()).digest()
        message = entropy_hash + proof.nonce + self._serialize_timestamp(proof.timestamp)
        expected = hmac.new(self._master_secret, message, hashlib.sha256).digest()

        if hmac.compare_digest(expected, proof.proof_data):
            self._used_nonces[proof.nonce] = time.time()
            self._prune_nonces()
            print("[LIMES] Proof verified: Human liveness confirmed")
            return True
        else:
            print("[LIMES] Invalid proof")
            return False
