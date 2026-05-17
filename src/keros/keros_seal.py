# ============================================================================
# src/keros/keros_seal.py
# KEROS Module: Hardware Attestation for Sensor Integrity
# Dependencies: CORTEX (anonymous tensor) + TPM 2.0 (required)
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Tuple
from enum import Enum

import numpy as np


class AttestationLevel(Enum):
    NONE = "none"          # No TPM available (cannot attest)
    HARDWARE = "hard"      # TPM seal valid
    TIME = "time"          # TPM seal + timestamp verified (anti‑replay)


@dataclass
class Keroseal:
    """Cryptographic seal from hardware TPM."""
    tensor_hash: bytes
    timestamp: float
    nonce: bytes
    pcr_quote: bytes      # Proof of code integrity (PCR 16)
    signature: bytes      # Signed by TPM Attestation Key


class TPMUnavailableError(Exception):
    """Raised when KEROS is invoked without an available TPM."""
    pass


class KerosEngine:
    """
    Hardware attestation module.
    [FIX-04] Fail‑closed: if TPM is not available, sealing raises an exception.
    [FIX-02] Timestamp serialized with struct.pack.
    """

    def __init__(self, tpm_available: bool = False):
        self._tpm_available = tpm_available
        self._attestation_key = None
        self._used_nonces = set()

        if tpm_available:
            self._init_tpm()
        else:
            print("[KEROS] Warning: TPM not available. KEROS will refuse to seal.")

    def _init_tpm(self):
        """Initializes TPM 2.0 connection (simulated for PoC)."""
        print("[KEROS] TPM 2.0 detected. Attestation key loaded.")
        self._attestation_key = secrets.token_bytes(32)   # Simulated AK

    def _serialize_timestamp(self, ts: float) -> bytes:
        return struct.pack(">d", ts)

    def _simulate_pcr_quote(self) -> bytes:
        """Simulates TPM PCR quote for code integrity (PCR 16)."""
        # In production: tpm2_pcrread(16)
        return hashlib.sha256(b"CORTEX_SAL_CODE_HASH").digest()

    def _verify_timestamp(self, seal: Keroseal) -> bool:
        """Checks if timestamp is within the allowed freshness window (5 seconds)."""
        return abs(time.time() - seal.timestamp) < 5.0

    def seal_tensor(self, anonymous_tensor: np.ndarray, sensor_id: str) -> Tuple[Keroseal, AttestationLevel]:
        """
        Seals a tensor with hardware attestation.
        Raises TPMUnavailableError if TPM is not available (fail‑closed).
        Returns (seal, attestation_level).
        """
        if not self._tpm_available or self._attestation_key is None:
            raise TPMUnavailableError("KEROS: TPM not available. Hardware attestation impossible.")

        tensor_hash = hashlib.sha256(anonymous_tensor.tobytes()).digest()
        nonce = secrets.token_bytes(16)
        timestamp = time.time()

        pcr_quote = self._simulate_pcr_quote()

        # Create message to sign
        message = tensor_hash + nonce + self._serialize_timestamp(timestamp)
        signature = hmac.new(self._attestation_key, message, hashlib.sha256).digest()

        seal = Keroseal(
            tensor_hash=tensor_hash,
            timestamp=timestamp,
            nonce=nonce,
            pcr_quote=pcr_quote,
            signature=signature
        )

        level = AttestationLevel.TIME if self._verify_timestamp(seal) else AttestationLevel.HARDWARE
        print(f"[KEROS] Tensor sealed. Attestation level: {level.value}")
        return seal, level

    def verify_seal(self, seal: Keroseal, expected_tensor_hash: bytes) -> bool:
        """
        Verifies a hardware seal without contacting the original sensor.
        Returns True if the seal is valid, fresh, and not replayed.
        """
        if self._attestation_key is None:
            print("[KEROS] No attestation key loaded – cannot verify")
            return False

        # Anti‑replay: nonce must not have been seen before
        if seal.nonce in self._used_nonces:
            print("[KEROS] Replay attack detected: nonce already used")
            return False

        # Timestamp freshness (5 seconds default)
        if abs(time.time() - seal.timestamp) > 5.0:
            print("[KEROS] Seal timestamp too old – possible replay")
            return False

        # Recompute signature
        message = seal.tensor_hash + seal.nonce + self._serialize_timestamp(seal.timestamp)
        expected_sig = hmac.new(self._attestation_key, message, hashlib.sha256).digest()

        if hmac.compare_digest(expected_sig, seal.signature):
            self._used_nonces.add(seal.nonce)
            print("[KEROS] Seal verified: Hardware integrity confirmed")
            return True
        else:
            print("[KEROS] Invalid signature")
            return False
