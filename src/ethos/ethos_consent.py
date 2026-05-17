# ============================================================================
# src/ethos/ethos_consent.py
# ETHOS Module: Dynamic, Physiologically‑Grounded Consent
# Dependencies: CORTEX (polyvagal state via CDI status)
# ============================================================================

import time
import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ConsentCapacity(Enum):
    FULL = "full"          # Ventral vagal – can consent normally
    LIMITED = "limited"    # Sympathetic – requires double confirmation
    NONE = "none"          # Dorsal vagal / CDI blocked – cannot consent


class ConsentScope(Enum):
    BIOMETRIC = "biometric"
    ACOLYTE = "acolyte"
    AUDIO = "audio"
    LOCATION = "location"


@dataclass
class ConsentRecord:
    """Immutable record of a consent event."""
    id: str
    scope: ConsentScope
    purpose: str
    granted_at: float
    expires_at: float
    user_state_hash: str   # Hash of CORTEX state at time of consent
    revoked: bool = False

    def is_active(self) -> bool:
        """Returns True if not revoked and not expired."""
        return not self.revoked and time.time() < self.expires_at


class EthosEngine:
    """
    Manages dynamic consent based on physiological capacity (from CORTEX).
    Consent is automatically revoked when capacity drops to NONE.
    """

    def __init__(self, cortex_shield):
        self._cortex = cortex_shield
        self._active_consents: Dict[str, ConsentRecord] = {}
        self._consent_log: List[ConsentRecord] = []

    def get_consent_capacity(self) -> ConsentCapacity:
        """
        Determines consent capacity from current CORTEX CDI status.
        [FIX-01] Correct order: NONE takes priority over LIMITED.
        """
        status = self._cortex.get_cdi_status()
        if status.get("blocked", False):
            return ConsentCapacity.NONE

        hard_violations = status.get("hard_violations", 0)
        if hard_violations >= 3:
            return ConsentCapacity.NONE
        if hard_violations >= 2:
            return ConsentCapacity.LIMITED
        return ConsentCapacity.FULL

    def request_consent(self, scope: ConsentScope, purpose: str,
                        duration_seconds: int = 3600) -> bool:
        """
        Requests consent with physiological capacity check.
        Returns True if consent is granted and recorded.
        """
        capacity = self.get_consent_capacity()

        if capacity == ConsentCapacity.NONE:
            print(f"[ETHOS] ❌ Consent denied: User in dorsal vagal state (cannot consent)")
            return False

        if capacity == ConsentCapacity.LIMITED:
            print(f"[ETHOS] ⚠️ Limited capacity: Requiring double confirmation")
            if not self._double_confirmation(scope, purpose):
                return False

        record_id = hashlib.sha256(
            f"{scope.value}{purpose}{time.time()}{secrets.token_hex(4)}".encode()
        ).hexdigest()[:16]

        record = ConsentRecord(
            id=record_id,
            scope=scope,
            purpose=purpose,
            granted_at=time.time(),
            expires_at=time.time() + duration_seconds,
            user_state_hash=self._get_state_hash()
        )

        self._active_consents[record_id] = record
        self._consent_log.append(record)
        print(f"[ETHOS] ✅ Consent granted: {scope.value} for '{purpose}' "
              f"(expires in {duration_seconds}s)")
        return True

    def revoke_consent(self, consent_id: str) -> bool:
        if consent_id in self._active_consents:
            self._active_consents[consent_id].revoked = True
            print(f"[ETHOS] Consent revoked: {consent_id}")
            return True
        return False

    def revoke_all(self):
        """Immediate revocation of all consents (Judicial Kill Switch integration)."""
        for record in self._active_consents.values():
            record.revoked = True
        print(f"[ETHOS] All consents revoked ({len(self._active_consents)} records)")

    def check_consent(self, scope: ConsentScope) -> bool:
        """Returns True if there is an active, unrevoked consent for the given scope."""
        for record in self._active_consents.values():
            if record.scope == scope and record.is_active():
                return True
        return False

    def auto_revoke_on_dysregulation(self):
        """
        Called when CORTEX detects dysregulation.
        Revokes all consents only when capacity becomes NONE.
        """
        if self.get_consent_capacity() == ConsentCapacity.NONE:
            any_active = any(r.is_active() for r in self._active_consents.values())
            if any_active:
                self.revoke_all()
                print("[ETHOS] Auto‑revoked all consents due to physiological dysregulation")

    def get_audit_log(self) -> List[Dict]:
        """Returns consent history for forensic review – no biometric data."""
        return [
            {
                "id": r.id,
                "scope": r.scope.value,
                "purpose": r.purpose,
                "granted_at": r.granted_at,
                "expires_at": r.expires_at,
                "revoked": r.revoked,
                "active": r.is_active(),
            }
            for r in self._consent_log
        ]

    def _double_confirmation(self, scope: ConsentScope, purpose: str) -> bool:
        """Simulates a second confirmation dialog for LIMITED capacity states."""
        # In production: present a distinct UI element and wait for explicit user action.
        print(f"[ETHOS] Double confirmation required for {scope.value}: {purpose}")
        return True  # Simulate user confirming

    def _get_state_hash(self) -> str:
        """Hashes current CORTEX state for audit trail (no raw data)."""
        status = self._cortex.get_cdi_status()
        return hashlib.sha256(str(status).encode()).hexdigest()[:16]
