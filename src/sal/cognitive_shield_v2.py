# ============================================================================
# cortex_protocol/sal/cognitive_shield_v2.py
# Milestone 1 Preview: CORTEX + LIMES + ETHOS
# 
# CORRECTIONS APPLIED (based on audit):
#   [FIX-01] EthosEngine.get_consent_capacity: correct order (NONE before LIMITED)
#   [FIX-02] LimesEngine: timestamp serialized with struct.pack
#   [FIX-03] EthosEngine.auto_revoke_on_dysregulation: revoke only on NONE
#   [FIX-04] ETHOS consent check before creating RawBiometricFrame
#   [FIX-05] DriftDetector with threading.RLock (mitigates race condition)
#   [FIX-06] LimesProof __post_init__ validation
#   [FIX-07] ConsentRecord.is_active() for atomic expiry check
#   [FIX-08] LIMES receives features (entropy), not raw frame
#   [FIX-09] BiometricStateMachine integrated (for future async)
#   [FIX-10] PolicyValidator integrated (for future governance)
#
# Dependencies: numpy
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import time
import threading
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Set
from collections import deque
from enum import Enum

import numpy as np


# ============================================================================
# 0. CLINICAL CONFIGURATION (White Branch Mandate)
# ============================================================================

class ClinicalThresholds:
    MAX_COHERENCY_SUM_PER_MINUTE = 2.5
    DRIFT_WINDOW_SECONDS         = 60
    HARD_BLOCK_VIOLATIONS        = 3
    SOFT_BLOCK_VIOLATIONS        = 5

    REQUIRED_SNR_DB              = 30.0
    REQUIRED_BITS_RESOLUTION     = 12

    BRIDGE_STD_LIMIT             = 0.5
    BRIDGE_P75_LIMIT             = 0.7
    BRIDGE_MAX_LIMIT             = 0.9

    LIMES_PROOF_TTL_SECONDS      = 30
    ETHOS_DEFAULT_CONSENT_TTL    = 3600


# ============================================================================
# 1. CORTEX — Sensor Certification (with challenge‑response)
# ============================================================================

class SensorCertificationAuthority:
    _WHITELIST = {
        "eeg_fp1_certified_v1": {
            "manufacturer": "NeuroStandard",
            "snr_db": 35.0,
            "bits": 16,
            "manufacturer_key": b"simulated_manufacturer_key_32_bytes_123456789",
        },
        "eeg_occipital_certified_v1": {
            "manufacturer": "NeuroStandard",
            "snr_db": 32.0,
            "bits": 14,
            "manufacturer_key": b"simulated_manufacturer_key_32_bytes_987654321",
        }
    }

    @classmethod
    def issue_challenge(cls) -> bytes:
        return secrets.token_bytes(32)

    @classmethod
    def verify_response(cls, sensor_id: str, challenge: bytes, response: bytes) -> bool:
        if sensor_id not in cls._WHITELIST:
            return False
        manufacturer_key = cls._WHITELIST[sensor_id]["manufacturer_key"]
        expected = hmac.new(manufacturer_key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(expected, response)

    @classmethod
    def handshake(cls, sensor_id: str, claimed_snr: float, claimed_bits: int,
                  challenge: bytes, response: bytes) -> Tuple[bool, str]:
        # 1. Challenge‑response
        if not cls.verify_response(sensor_id, challenge, response):
            return False, "Challenge‑response failed: sensor not authenticated"
        # 2. Whitelist + quality thresholds
        if sensor_id not in cls._WHITELIST:
            return False, f"Sensor '{sensor_id}' not in clinical whitelist"
        spec = cls._WHITELIST[sensor_id]
        if spec["snr_db"] < ClinicalThresholds.REQUIRED_SNR_DB:
            return False, f"SNR {spec['snr_db']} dB below minimum"
        if spec["bits"] < ClinicalThresholds.REQUIRED_BITS_RESOLUTION:
            return False, f"Resolution {spec['bits']} bits below minimum"
        return True, f"Sensor '{sensor_id}' certified"


# ============================================================================
# 2. CORTEX — Clinical Drift Index (CDI) with threading.RLock
# ============================================================================

class DriftDetector:
    def __init__(self):
        self._lock = threading.RLock()
        self._readings: deque = deque()
        self._hard_violations = 0
        self._soft_violations = 0
        self._blocked = False
        self._baseline_mean = 0.0
        self._baseline_std = 0.0
        self._baseline_ready = False

    def establish_baseline(self, sessions: List[float]):
        if len(sessions) < 3:
            return
        self._baseline_mean = float(np.mean(sessions))
        self._baseline_std = float(np.std(sessions))
        self._baseline_ready = True
        print(f"[CDI] Baseline established → mean={self._baseline_mean:.3f}, std={self._baseline_std:.3f}")

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
                print(f"[CDI] ⚠️ Hard violation {self._hard_violations}/"
                      f"{ClinicalThresholds.HARD_BLOCK_VIOLATIONS} — sum={window_sum:.2f}")
                if self._hard_violations >= ClinicalThresholds.HARD_BLOCK_VIOLATIONS:
                    self._blocked = True
                    return False, f"CDI: HARD BLOCK (sum={window_sum:.2f})"
                return True, f"Hard warning ({self._hard_violations})"

            # Soft threshold (Z‑score)
            if self._baseline_ready:
                z = abs(coherency - self._baseline_mean) / (self._baseline_std + 1e-6)
                if z > 3.0:
                    self._soft_violations += 1
                    print(f"[CDI] ⚠️ Soft violation {self._soft_violations}/"
                          f"{ClinicalThresholds.SOFT_BLOCK_VIOLATIONS} — z={z:.2f}")
                    if self._soft_violations >= ClinicalThresholds.SOFT_BLOCK_VIOLATIONS:
                        self._blocked = True
                        return False, f"CDI: SOFT BLOCK (z={z:.2f})"
                    return True, f"Soft warning ({self._soft_violations})"

            # Gradual recovery for soft violations
            if window_sum < ClinicalThresholds.MAX_COHERENCY_SUM_PER_MINUTE * 0.6:
                self._soft_violations = max(0, self._soft_violations - 1)

            return True, "OK"

    def is_blocked(self) -> bool:
        with self._lock:
            return self._blocked

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "blocked": self._blocked,
                "baseline_ready": self._baseline_ready,
                "baseline_mean": self._baseline_mean if self._baseline_ready else None,
                "hard_violations": self._hard_violations,
                "soft_violations": self._soft_violations,
                "window_sum": sum(c for _, c in self._readings) if self._readings else 0.0,
            }


# ============================================================================
# 3. CORTEX — Two‑Phase Tensor Transformation
# ============================================================================

class AnonymousTensorFactory:
    @staticmethod
    def extract_features(raw_data: np.ndarray) -> np.ndarray:
        """Phase A: extract 5 clinical features from the Hilbert envelope."""
        # Normalize to clinical range (-50µV to +50µV for EEG)
        normalized = np.clip((raw_data + 50.0) / 100.0, 0.0, 1.0)
        envelope = np.abs(np.fft.hilbert(normalized))
        return np.array([
            np.mean(envelope),
            np.std(envelope),
            np.percentile(envelope, 25),
            np.percentile(envelope, 75),
            np.max(envelope),
        ], dtype=np.float64)

    @staticmethod
    def obfuscate(features: np.ndarray, salt: bytes, sensor_hash: str) -> np.ndarray:
        """Phase B: HMAC‑SHA256 obfuscation, irreversible without the session salt."""
        data_bytes = features.tobytes() + sensor_hash.encode()
        digest = hmac.new(salt, data_bytes, hashlib.sha256).digest()
        noise = np.frombuffer(digest[:features.nbytes], dtype=np.float32).astype(np.float64)
        return noise[:len(features)] * features


class ClinicalBridge:
    """Validates Phase A features against Polyvagal Theory thresholds."""
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
    """Coefficient of Variation (CV) – proxy for autonomic variability."""
    return features[1] / features[0] if features[0] > 1e-9 else 0.0


def coherency_to_state(cv: float) -> str:
    if cv < 0.3:
        return "ventral_vagal (calm)"
    if cv < 0.7:
        return "sympathetic (focused)"
    return "dorsal_vagal (rest_needed)"


# ============================================================================
# 4. CORTEX — Ephemeral Raw Frame (context manager)
# ============================================================================

@dataclass
class RawBiometricFrame:
    sensor_hash: str
    timestamp: float
    data: np.ndarray

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.data is not None:
            self.data.fill(0)
            print(f"[CORTEX] 🔒 Raw frame zeroed [{self.sensor_hash[:8]}…]")
        return False


# ============================================================================
# 5. LIMES — Proof of Human Liveness (HMAC‑based, not ZKP)
# ============================================================================

@dataclass
class LimesProof:
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
    Uses HMAC with an ephemeral master secret, not a zero‑knowledge proof.
    Anti‑replay: nonce store with expiry pruning.
    """

    def __init__(self, cortex_shield):
        self._cortex = cortex_shield
        self._master_secret = secrets.token_bytes(32)
        self._used_nonces: Dict[bytes, float] = {}  # nonce → timestamp
        self._ttl = ClinicalThresholds.LIMES_PROOF_TTL_SECONDS

    def _serialize_timestamp(self, ts: float) -> bytes:
        return struct.pack(">d", ts)

    def _prune_nonces(self):
        now = time.time()
        expired = [n for n, t in self._used_nonces.items() if now - t > self._ttl]
        for n in expired:
            del self._used_nonces[n]

    def generate_proof(self, feature_entropy: np.ndarray) -> Optional[LimesProof]:
        if self._cortex.get_cdi_status().get("blocked", False):
            print("[LIMES] Cannot generate proof: CORTEX blocked")
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
        print(f"[LIMES] Proof generated — valid for {self._ttl}s")
        return LimesProof(proof, ts, nonce, valid_until)

    def verify_proof(self, proof: LimesProof, feature_entropy: np.ndarray) -> bool:
        if time.time() > proof.valid_until:
            print("[LIMES] Proof expired")
            return False
        if proof.nonce in self._used_nonces:
            print("[LIMES] Nonce replayed — possible attack")
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


# ============================================================================
# 6. ETHOS — Dynamic Consent (physiologically‑grounded)
# ============================================================================

class ConsentCapacity(Enum):
    FULL = "full"
    LIMITED = "limited"
    NONE = "none"


class ConsentScope(Enum):
    BIOMETRIC = "biometric"
    ACOLYTE = "acolyte"


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
    Manages dynamic consent based on polyvagal state (via CORTEX).
    FULL capacity  → normal consent flow.
    LIMITED        → requires double confirmation.
    NONE           → consent refused, existing consents auto‑revoked.
    """

    def __init__(self, cortex_shield):
        self._cortex = cortex_shield
        self._records: Dict[str, ConsentRecord] = {}

    def get_capacity(self) -> ConsentCapacity:
        status = self._cortex.get_cdi_status()
        if status.get("blocked", False):
            return ConsentCapacity.NONE
        hard = status.get("hard_violations", 0)
        # NONE takes priority over LIMITED
        if hard >= 3:
            return ConsentCapacity.NONE
        if hard >= 2:
            return ConsentCapacity.LIMITED
        return ConsentCapacity.FULL

    def request_consent(self, scope: ConsentScope, duration_seconds: int = 3600) -> bool:
        cap = self.get_capacity()
        if cap == ConsentCapacity.NONE:
            print(f"[ETHOS] ❌ Consent refused — dorsal vagal state (capacity=NONE)")
            return False
        if cap == ConsentCapacity.LIMITED:
            print(f"[ETHOS] ⚠️ Limited capacity — double confirmation required")
            if not self._double_confirm(scope):
                return False

        record_id = hashlib.sha256(
            f"{scope.value}{time.time()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:12]
        self._records[record_id] = ConsentRecord(
            id=record_id,
            scope=scope,
            granted_at=time.time(),
            expires_at=time.time() + duration_seconds,
        )
        print(f"[ETHOS] ✅ Consent granted — scope={scope.value}, expires in {duration_seconds}s")
        return True

    def revoke_consent(self, consent_id: str) -> bool:
        if consent_id in self._records:
            self._records[consent_id].revoked = True
            print(f"[ETHOS] Consent revoked: {consent_id}")
            return True
        return False

    def revoke_all(self):
        for r in self._records.values():
            r.revoked = True
        print(f"[ETHOS] All consents revoked ({len(self._records)} records)")

    def check_consent(self, scope: ConsentScope) -> bool:
        return any(r.scope == scope and r.is_active() for r in self._records.values())

    def auto_revoke_on_dysregulation(self):
        """Called when CORTEX reports dysregulation. Revokes only in NONE capacity."""
        if self.get_capacity() == ConsentCapacity.NONE:
            any_active = any(r.is_active() for r in self._records.values())
            if any_active:
                self.revoke_all()
                print("[ETHOS] Auto‑revoked all consents due to physiological dysregulation")

    def _double_confirm(self, scope: ConsentScope) -> bool:
        # In production: present a second explicit confirmation UI element.
        # Here we simulate a successful confirmation.
        print(f"[ETHOS] Double confirmation simulated for scope={scope.value}")
        return True


# ============================================================================
# 7. INTEGRATED COGNITIVE SHIELD (CORTEX + LIMES + ETHOS)
# ============================================================================

class CognitiveShield:
    """
    Milestone 1 Preview: integrates CORTEX (SAL + CDI), LIMES (proof of life),
    and ETHOS (dynamic consent). Fully local, ephemeral, and thread‑safe.
    """

    def __init__(self):
        self._session_salt = secrets.token_bytes(32)
        self._certified_sensors: Dict[str, str] = {}
        self.drift_detector = DriftDetector()
        self._baseline_sessions: List[float] = []
        self.session_log: List[Dict] = []

        # Pentágono modules
        self.limes = LimesEngine(self)
        self.ethos = EthosEngine(self)

    def register_sensor(self, sensor_id: str, snr: float, bits: int) -> Tuple[bool, str]:
        """
        Registers a sensor using challenge‑response handshake.
        Simulates the sensor's response using the manufacturer key from whitelist.
        """
        challenge = SensorCertificationAuthority.issue_challenge()
        # In a real deployment, the sensor would compute the HMAC with its private key.
        # Here we fetch the manufacturer key from the whitelist for demonstration.
        spec = SensorCertificationAuthority._WHITELIST.get(sensor_id, {})
        manuf_key = spec.get("manufacturer_key", b"")
        response = hmac.new(manuf_key, challenge, hashlib.sha256).digest()
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

    def ingest_raw_data(self, sensor_id: str, raw_data: np.ndarray) -> Optional[Dict]:
        """
        Full SAL pipeline for one biometric frame:
        1. Sensor certification check
        2. CDI pre‑check
        3. ETHOS consent verification (before touching raw data)
        4. Phase A feature extraction
        5. Clinical Bridge validation
        6. Coherency computation
        7. LIMES proof generation
        8. Phase B obfuscation
        9. CDI update
        10. Audit log
        """
        sensor_hash = hashlib.sha256(sensor_id.encode()).hexdigest()
        if sensor_hash not in self._certified_sensors:
            print("[CORTEX] ❌ Sensor not certified")
            return None

        if self.drift_detector.is_blocked():
            print("[CORTEX] 🛑 CDI blocked — session suspended")
            return 
