# ============================================================================
# src/ethos/ethos_consent.py
# ETHOS Module: Physiologically-Grounded Dynamic Consent
#
# Pentagon Question: "¿Tiene el usuario capacidad de consentir ahora mismo?"
#
# CORRECTIONS (post-audit cycle 2, 2026-05-17):
#   [ETHOS-FIX-01] get_consent_capacity: NONE checked before LIMITED.
#                  Previous code had elif >= 3 after if >= 2, making NONE
#                  unreachable via the violation path. A user with 3+ hard
#                  violations always received LIMITED instead of NONE.
#                  This directly violated the neuro-rights protection mandate.
#   [ETHOS-FIX-02] _double_confirmation raises NotImplementedError in base class.
#                  Previous implementation silently returned True, meaning
#                  LIMITED-capacity consent was always granted without any
#                  actual user confirmation. Use DemoEthosEngine for PoC.
#   [ETHOS-FIX-03] auto_revoke_on_dysregulation revokes only on NONE capacity.
#   [ETHOS-FIX-04] ConsentRecord.is_active() provides atomic expiry check.
#
# Dependencies: stdlib only
# ============================================================================

import hashlib
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ConsentCapacity(Enum):
    FULL    = "full"     # Ventral vagal — user can consent normally
    LIMITED = "limited"  # Sympathetic — requires explicit double confirmation
    NONE    = "none"     # Dorsal vagal / CDI blocked — consent refused


class ConsentScope(Enum):
    BIOMETRIC      = "biometric"
    ACOLYTE        = "acolyte"
    AUDIO          = "audio"
    LOCATION       = "location"


@dataclass
class ConsentRecord:
    """Record of a consent grant. Mutable only via revoke_consent / revoke_all."""
    id:              str
    scope:           ConsentScope
    purpose:         str
    granted_at:      float
    expires_at:      float
    user_state_hash: str   # Hash of CDI status at grant time — audit trail
    revoked:         bool = False

    def is_active(self) -> bool:
        """[ETHOS-FIX-04] Atomic expiry + revocation check."""
        return not self.revoked and time.time() < self.expires_at


class EthosEngine:
    """
    Physiologically-grounded dynamic consent engine.

    Polyvagal capacity mapping:
      FULL    → CDI clear, 0–1 hard violations
      LIMITED → 2 hard violations (double confirmation required)
      NONE    → CDI blocked OR ≥3 hard violations (consent refused)

    [ETHOS-FIX-01] Capacity logic: NONE evaluated before LIMITED.
    [ETHOS-FIX-02] _double_confirmation: raises NotImplementedError in base.
                   Production subclasses must implement real UI flow.
                   Use DemoEthosEngine for PoC and automated tests.
    [ETHOS-FIX-03] auto_revoke: only triggers on NONE capacity.
    """

    DEFAULT_TTL: int = 3600  # 1 hour

    def __init__(self, cortex_shield):
        self._cortex          = cortex_shield
        self._active_consents: Dict[str, ConsentRecord] = {}
        self._consent_log:     List[ConsentRecord]      = []

    def get_consent_capacity(self) -> ConsentCapacity:
        """
        [ETHOS-FIX-01] NONE is checked BEFORE LIMITED.
        hard_violations >= 3 must return NONE, not LIMITED.
        """
        status = self._cortex.get_cdi_status()

        if status.get("blocked", False):
            return ConsentCapacity.NONE

        hard_violations = status.get("hard_violations", 0)

        # [ETHOS-FIX-01] >= 3 evaluated FIRST — was unreachable in previous version
        if hard_violations >= 3:
            return ConsentCapacity.NONE

        if hard_violations >= 2:
            return ConsentCapacity.LIMITED

        return ConsentCapacity.FULL

    def request_consent(
        self,
        scope: ConsentScope,
        purpose: str = "general",
        duration_seconds: int = DEFAULT_TTL,
    ) -> bool:
        """
        Requests consent with physiological capacity gate.
        Returns True if consent is granted and recorded.
        """
        capacity = self.get_consent_capacity()

        if capacity == ConsentCapacity.NONE:
            print(
                f"[ETHOS] ❌ Consent refused — dorsal vagal / CDI blocked "
                f"(capacity=NONE, scope={scope.value})"
            )
            return False

        if capacity == ConsentCapacity.LIMITED:
            print(f"[ETHOS] ⚠️  Limited capacity — double confirmation required (scope={scope.value})")
            if not self._double_confirmation(scope, purpose):
                print("[ETHOS] ❌ Double confirmation not completed — consent refused")
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
            user_state_hash=self._get_state_hash(),
        )

        self._active_consents[record_id] = record
        self._consent_log.append(record)
        print(
            f"[ETHOS] ✅ Consent granted — scope={scope.value}, "
            f"purpose='{purpose}', duration={duration_seconds}s, "
            f"capacity={capacity.value}, id={record_id}"
        )
        return True

    def revoke_consent(self, consent_id: str) -> bool:
        if consent_id in self._active_consents:
            self._active_consents[consent_id].revoked = True
            print(f"[ETHOS] 🔒 Consent revoked: {consent_id}")
            return True
        return False

    def revoke_all(self):
        """Judicial Kill Switch integration point. Revokes all active consents."""
        active_count = sum(1 for r in self._active_consents.values() if r.is_active())
        for record in self._active_consents.values():
            record.revoked = True
        print(f"[ETHOS] 🔒 All consents revoked ({active_count} active records)")

    def check_consent(self, scope: ConsentScope) -> bool:
        """Returns True if there is at least one active, unexpired consent for scope."""
        return any(
            r.scope == scope and r.is_active()
            for r in self._active_consents.values()
        )

    def auto_revoke_on_dysregulation(self):
        """
        [ETHOS-FIX-03] Revokes all consents ONLY when capacity is NONE.
        Sympathetic state (LIMITED) does NOT trigger auto-revocation:
        a stressed-but-capable user must not lose access mid-session.
        """
        if self.get_consent_capacity() == ConsentCapacity.NONE:
            any_active = any(r.is_active() for r in self._active_consents.values())
            if any_active:
                self.revoke_all()
                print("[ETHOS] 🔒 Auto-revocation: dorsal vagal / CDI blocked state")

    def get_audit_log(self) -> List[Dict]:
        """
        Returns full consent history for forensic review.
        Contains no biometric data and no user-identifiable information.
        """
        return [
            {
                "id":              r.id,
                "scope":           r.scope.value,
                "purpose":         r.purpose,
                "granted_at":      r.granted_at,
                "expires_at":      r.expires_at,
                "user_state_hash": r.user_state_hash,
                "revoked":         r.revoked,
                "active":          r.is_active(),
            }
            for r in self._consent_log
        ]

    def _get_state_hash(self) -> str:
        """Hashes current CDI status for audit trail. No raw data included."""
        status = self._cortex.get_cdi_status()
        return hashlib.sha256(str(status).encode()).hexdigest()[:16]

    def _double_confirmation(self, scope: ConsentScope, purpose: str) -> bool:
        """
        [ETHOS-FIX-02] Raises NotImplementedError in base class.

        This method MUST be overridden in production subclasses to implement
        a real, user-facing confirmation flow (timed gesture, PIN entry,
        voice command, explicit UI button).

        The previous implementation returned True unconditionally, which made
        the LIMITED capacity gate functionally identical to FULL — any user,
        regardless of physiological state, could obtain consent with no
        additional confirmation. This is a neuro-rights violation.

        For PoC environments, use DemoEthosEngine instead of this base class.
        """
        raise NotImplementedError(
            "EthosEngine._double_confirmation() must be overridden in production. "
            "The base class does NOT auto-confirm — this forces correct subclassing. "
            "Use DemoEthosEngine for PoC and automated testing."
        )


# ============================================================================
# Demo subclass — PoC and automated tests ONLY
# ============================================================================

class DemoEthosEngine(EthosEngine):
    """
    PoC / test subclass. Auto-confirms double confirmation with explicit warning.

    ⚠️  NEVER use in production. The warning is the contract.
    The base EthosEngine raises NotImplementedError on _double_confirmation().
    """

    def _double_confirmation(self, scope: ConsentScope, purpose: str) -> bool:
        print(
            f"[ETHOS][DEMO] ⚠️  Auto-confirming double confirmation — "
            f"scope={scope.value}, purpose='{purpose}'. "
            "FOR DEMO/TEST ONLY. Override in production."
        )
        return True
