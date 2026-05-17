# ============================================================================
# src/sal/state_buffer.py
# Biometric State Buffer for Asynchronous Architecture
# Implements ARCHITECTURE-ASYNC.md (Decision 1 & 2)
# ============================================================================

import threading
import time
import hmac
import hashlib
from dataclasses import dataclass
from typing import Tuple


@dataclass
class BiometricStateBuffer:
    """
    Local, in‑memory state object that the AI pipeline reads with zero latency.
    Only the biometric thread may write; AI thread is read‑only.
    """
    status: str           # "SAFE" | "WARNING" | "BLOCKED"
    polyvagal_state: str  # "ventral_vagal" | "sympathetic" | "dorsal_vagal"
    coherency_index: float
    timestamp: float
    sensor_hmac: bytes
    ttl_seconds: int = 5

    def is_valid(self, sensor_key: bytes) -> bool:
        """Returns True only if the state is fresh and HMAC‑authenticated."""
        if time.time() - self.timestamp > self.ttl_seconds:
            return False
        expected = hmac.new(
            sensor_key,
            f"{self.status}{self.timestamp}".encode(),
            hashlib.sha256
        ).digest()
        return hmac.compare_digest(expected, self.sensor_hmac)


class BiometricStateMachine:
    """
    Thread‑safe finite state machine with atomic transitions.
    Implements the circuit breaker pattern from ARCHITECTURE-ASYNC.md.
    """

    _VALID_TRANSITIONS = {
        "SAFE": {"WARNING", "BLOCKED"},
        "WARNING": {"SAFE", "BLOCKED"},
        "BLOCKED": {"SAFE"},          # Only recovery via explicit SAFE
    }

    def __init__(self, sensor_key: bytes):
        self._lock = threading.RLock()
        self._sensor_key = sensor_key
        self._state = "BLOCKED"        # fail‑safe initial state
        self._hmac_tag = b""
        self._timestamp = 0.0

    def transition(self, new_state: str) -> bool:
        """
        Atomically transition to new_state if the transition is allowed.
        Returns True on success.
        """
        with self._lock:
            if new_state not in self._VALID_TRANSITIONS.get(self._state, set()):
                return False
            ts = time.time()
            tag = hmac.new(
                self._sensor_key,
                f"{new_state}{ts:.6f}".encode(),
                hashlib.sha256
            ).digest()
            self._state = new_state
            self._timestamp = ts
            self._hmac_tag = tag
            return True

    def read(self) -> Tuple[str, bool]:
        """
        Thread‑safe read that returns (state, is_valid).
        The validity check includes both HMAC authentication and TTL (5 seconds).
        """
        with self._lock:
            if time.time() - self._timestamp > 5.0:
                return "BLOCKED", False
            expected = hmac.new(
                self._sensor_key,
                f"{self._state}{self._timestamp:.6f}".encode(),
                hashlib.sha256
            ).digest()
            valid = hmac.compare_digest(expected, self._hmac_tag)
            return self._state, valid
