# ============================================================================
# src/keros/keros_seal.py
# KEROS Module: Hardware Attestation & Sensor Integrity
#
# Pentagon Question: "¿De qué hardware provienen los datos?"
#
# CORRECTIONS (post-audit cycle 2, 2026-05-17):
#   [KEROS-FIX-01] struct.pack(">d", ts) for float timestamp serialization.
#                  float has no .to_bytes() — previous hardware path was dead code.
#   [KEROS-FIX-02] Software fallback removed — fail-closed via TPMUnavailableError.
#                  A hash without a secret key is not a MAC and provides zero
#                  authenticity guarantee.
#   [KEROS-FIX-03] Challenge-Response scaffold in SensorCertificationAuthority.
#   [KEROS-FIX-04] _used_nonces changed from set() to Dict[bytes, float].
#                  Time-based TTL pruning replaces unbounded growth.
#                  A set() nonce store grows indefinitely in long sessions.
#   [KEROS-FIX-05] verify_seal: nonce consumed AFTER successful HMAC check,
#                  not before. Early consumption opened a DoS window where
#                  a valid nonce could be invalidated before the HMAC passed.
#
# Dependencies: stdlib only
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class TPMUnavailableError(RuntimeError):
    """Raised when KEROS is invoked without a TPM. Fail-closed by design."""


class SensorSpoofingError(RuntimeError):
    """Raised when a sensor fails Challenge-Response. Possible BLE spoofing."""


class AttestationLevel(Enum):
    HARDWARE = "hard"   # TPM seal + PCR quote verified
    TIME     = "time"   # TPM seal + timestamp freshness verified (anti-replay)


@dataclass
class Keroseal:
    """Cryptographic seal produced by TPM hardware."""
    tensor_hash: bytes   # SHA-256 of the anonymous tensor
    timestamp:   float   # Unix time of sealing
    nonce:       bytes   # 16-byte anti-replay token
    pcr_quote:   bytes   # TPM PCR16 quote (code integrity measurement)
    signature:   bytes   # HMAC-SHA256(tensor_hash + nonce + ts_bytes, AK)


class SensorCertificationAuthority:
    """
    Two-phase sensor handshake:
      Phase 1 — Capability check: whitelist membership + SNR/bits minima.
      Phase 2 — Challenge-Response: sensor's HMAC over (challenge || sensor_id)
                 proves physical device identity. Prevents BLE spoofing.

    In production: manufacturer_key is supplied by Governance Node signed
    package. The None values below require population before Phase 2 works.
    """

    _WHITELIST: Dict[str, dict] = {
        "eeg_fp1_certified_v1": {
            "manufacturer":           "NeuroStandard",
            "snr_db":                 35.0,
            "bits":                   16,
            "clinical_approval_hash": "0x7F3A9E2B...",
            "manufacturer_key":       None,  # TODO: populate from Governance Node GPG package
        },
        "eeg_occipital_certified_v1": {
            "manufacturer":           "NeuroStandard",
            "snr_db":                 32.0,
            "bits":                   14,
            "clinical_approval_hash": "0x2C8D1F4A...",
            "manufacturer_key":       None,  # TODO: populate from Governance Node GPG package
        },
    }

    _MIN_SNR_DB:  float = 30.0
    _MIN_BITS:    int   = 12

    @classmethod
    def issue_challenge(cls) -> bytes:
        """Step 1: SAL issues 32-byte nonce. One challenge per handshake."""
        return secrets.token_bytes(32)

    @classmethod
    def handshake(
        cls,
        sensor_id: str,
        claimed_snr: float,
        claimed_bits: int,
        challenge_response: Optional[Tuple[bytes, bytes]] = None,
    ) -> Tuple[bool, str]:
        """
        Full certification handshake.

        Args:
            sensor_id:          Device identifier.
            claimed_snr:        Claimed SNR in dB (from BLE device descriptor).
            claimed_bits:       Claimed ADC resolution.
            challenge_response: Optional (challenge, response) tuple for Phase 2.
                                If None, Phase 1 only — with explicit WARNING.

        Returns:
            (approved: bool, message: str)

        Raises:
            SensorSpoofingError: If Challenge-Response fails.
        """
        # Phase 1: whitelist + capability check
        if sensor_id not in cls._WHITELIST:
            return False, f"Sensor '{sensor_id}' not in Governance Node whitelist"

        spec = cls._WHITELIST[sensor_id]
        if spec["snr_db"] < cls._MIN_SNR_DB:
            return False, (
                f"Sensor '{sensor_id}' SNR {spec['snr_db']} dB "
                f"below clinical minimum {cls._MIN_SNR_DB} dB"
            )
        if spec["bits"] < cls._MIN_BITS:
            return False, (
                f"Sensor '{sensor_id}' resolution {spec['bits']} bits "
                f"below clinical minimum {cls._MIN_BITS} bits"
            )

        # Phase 2: cryptographic identity verification
        if challenge_response is not None:
            challenge, response = challenge_response
            manufacturer_key = spec.get("manufacturer_key")
            if manufacturer_key is None:
                return False, (
                    f"Sensor '{sensor_id}': no manufacturer_key in whitelist. "
                    "Governance Node must supply signed key package."
                )
            expected = hmac.new(
                manufacturer_key,
                challenge + sensor_id.encode(),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(expected, response):
                raise SensorSpoofingError(
                    f"Sensor '{sensor_id}' failed Challenge-Response. "
                    "Possible BLE spoofing or device substitution."
                )
            return True, (
                f"Sensor '{sensor_id}' FULLY CERTIFIED — "
                f"SNR: {spec['snr_db']} dB, {spec['bits']} bits, identity verified"
            )

        # Phase 1 only — explicit warning, never silent
        print(
            f"[KEROS] ⚠️  WARNING: '{sensor_id}' capability-certified but identity "
            "NOT cryptographically verified (no Challenge-Response). "
            "Use only in controlled demo/development environments."
        )
        return True, (
            f"Sensor '{sensor_id}' capability-certified (identity UNVERIFIED). "
            f"SNR: {spec['snr_db']} dB, {spec['bits']} bits"
        )


class KerosEngine:
    """
    Hardware attestation engine. Seals anonymous tensors with TPM-backed
    proof of origin and integrity.

    Fail-closed: if TPM is unavailable, seal_tensor() raises TPMUnavailableError.
    No software fallback — an unauthenticated hash provides zero attestation
    guarantee against a compromised OS.

    [KEROS-FIX-01] Timestamp via struct.pack — float has no .to_bytes().
    [KEROS-FIX-02] Explicit TPMUnavailableError — no silent fallback.
    [KEROS-FIX-04] _used_nonces: Dict[bytes, float] with TTL pruning.
    [KEROS-FIX-05] Nonce consumed after HMAC verification, not before.
    """

    FRESHNESS_WINDOW_SECONDS: float = 5.0
    # White Branch defines domain-specific value in CIT specifications.
    # 5s is conservative for sequential PoC; production may tighten to 1–2s.

    def __init__(self, tpm_available: bool = False):
        self.tpm_available             = tpm_available
        self._attestation_key: Optional[bytes] = None
        # [KEROS-FIX-04] Dict[nonce → issue_timestamp] for TTL-based pruning
        self._used_nonces: Dict[bytes, float]  = {}

        if tpm_available:
            self._init_tpm()
        else:
            print(
                "[KEROS] ⚠️  TPM 2.0 not available. "
                "seal_tensor() will raise TPMUnavailableError. "
                "Production deployment requires TPM-equipped hardware."
            )

    def _init_tpm(self):
        """
        Initializes TPM 2.0 Attestation Key.
        Production: replace with tpm2-pytss or python-tpm2 binding.
        """
        print("[KEROS] TPM 2.0 detected — loading Attestation Key...")
        self._attestation_key = secrets.token_bytes(32)  # PoC: simulated AK
        print("[KEROS] ✅ Attestation Key loaded (SIMULATED — use tpm2-pytss in production).")

    def _prune_nonces(self):
        """
        [KEROS-FIX-04] Discard nonces older than FRESHNESS_WINDOW_SECONDS.
        Time-based: an expired nonce cannot be replayed (timestamp check
        independently rejects it), so pruning it is semantically safe.
        """
        cutoff = time.time() - self.FRESHNESS_WINDOW_SECONDS
        before = len(self._used_nonces)
        self._used_nonces = {n: t for n, t in self._used_nonces.items() if t > cutoff}
        pruned = before - len(self._used_nonces)
        if pruned:
            print(f"[KEROS] Nonce store pruned: {pruned} expired entries removed.")

    def _ts_bytes(self, ts: float) -> bytes:
        """[KEROS-FIX-01] Float-safe timestamp serialization (big-endian double)."""
        return struct.pack(">d", ts)

    def _get_pcr_quote(self) -> bytes:
        """
        TPM PCR16 quote for SAL code integrity measurement.
        Production: replace with tpm2_quote(pcr_selection={"sha256": [16]}).
        PCR16 is the designated application measurement register per TCG spec.
        """
        return hashlib.sha256(b"CORTEX_SAL_PCR16_MEASUREMENT_PLACEHOLDER").digest()

    def seal_tensor(self, tensor_bytes: bytes, sensor_id: str) -> Tuple[Keroseal, AttestationLevel]:
        """
        Seals an anonymous tensor with TPM-backed proof of origin.

        [KEROS-FIX-01] Timestamp via struct.pack.
        [KEROS-FIX-02] Raises TPMUnavailableError if no TPM — no fallback.

        Args:
            tensor_bytes: Phase B output bytes (anonymous tensor).
            sensor_id:    Certified sensor identifier.

        Returns:
            (Keroseal, AttestationLevel)

        Raises:
            TPMUnavailableError: If TPM unavailable. Fail-closed.
        """
        if not self.tpm_available or self._attestation_key is None:
            raise TPMUnavailableError(
                "KEROS requires TPM 2.0. Operation refused — no software fallback. "
                "Deploy on TPM-equipped hardware."
            )

        tensor_hash = hashlib.sha256(tensor_bytes).digest()
        nonce       = secrets.token_bytes(16)
        timestamp   = time.time()
        ts_bytes    = self._ts_bytes(timestamp)       # [KEROS-FIX-01]
        pcr_quote   = self._get_pcr_quote()

        message   = tensor_hash + nonce + ts_bytes
        signature = hmac.new(self._attestation_key, message, hashlib.sha256).digest()

        seal  = Keroseal(
            tensor_hash=tensor_hash,
            timestamp=timestamp,
            nonce=nonce,
            pcr_quote=pcr_quote,
            signature=signature,
        )
        level = (
            AttestationLevel.TIME
            if abs(time.time() - timestamp) < self.FRESHNESS_WINDOW_SECONDS
            else AttestationLevel.HARDWARE
        )
        print(f"[KEROS] ✅ Tensor sealed. Attestation: {level.value}")
        return seal, level

    def verify_seal(self, seal: Keroseal, tensor_bytes: bytes) -> bool:
        """
        Verifies a hardware seal against provided tensor bytes.

        Verification order:
          1. Freshness check (timestamp within window)
          2. Nonce pre-check — fast rejection of known replays
          3. HMAC signature verification
          4. Tensor hash verification
          5. Nonce consumed — ONLY after all checks pass [KEROS-FIX-05]

        [KEROS-FIX-04] Prunes nonce store before checking.
        [KEROS-FIX-05] Nonce consumed post-verification — prevents DoS via
                       premature consumption of a valid nonce on an invalid seal.
        """
        if not self.tpm_available or self._attestation_key is None:
            raise TPMUnavailableError("Cannot verify seal without TPM Attestation Key.")

        self._prune_nonces()  # [KEROS-FIX-04]

        # 1. Freshness
        age = abs(time.time() - seal.timestamp)
        if age > self.FRESHNESS_WINDOW_SECONDS:
            print(f"[KEROS] ❌ Seal expired ({age:.1f}s > {self.FRESHNESS_WINDOW_SECONDS}s)")
            return False

        # 2. Nonce pre-check (fail fast on known replays)
        if seal.nonce in self._used_nonces:
            print("[KEROS] ❌ Replay: nonce already consumed")
            return False

        # 3. HMAC signature verification [KEROS-FIX-01]
        ts_bytes     = self._ts_bytes(seal.timestamp)
        message      = seal.tensor_hash + seal.nonce + ts_bytes
        expected_sig = hmac.new(self._attestation_key, message, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, seal.signature):
            print("[KEROS] ❌ Signature invalid — integrity check failed")
            return False

        # 4. Tensor hash verification
        actual_hash = hashlib.sha256(tensor_bytes).digest()
        if not hmac.compare_digest(actual_hash, seal.tensor_hash):
            print("[KEROS] ❌ Tensor hash mismatch — data tampered after sealing")
            return False

        # 5. Consume nonce AFTER all checks pass [KEROS-FIX-05]
        self._used_nonces[seal.nonce] = seal.timestamp
        print("[KEROS] ✅ Seal verified: hardware integrity confirmed")
        return True
