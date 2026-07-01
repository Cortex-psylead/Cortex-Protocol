# ============================================================================
# tests/test_ethos_consent.py
# Cortex Protocol — Characterization tests for ETHOS Dynamic Consent
#
# Purpose: freeze the documented post-audit behavior of EthosEngine
# (src/ethos/ethos_consent.py) so future refactors -- including a possible
# merge with the EthosEngine duplicated inside src/sal/cognitive_shield_v2.py --
# cannot silently reintroduce ETHOS-FIX-01 through ETHOS-FIX-04.
#
# Run: python -m pytest tests/test_ethos_consent.py -v
# ============================================================================

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'ethos'))
from ethos_consent import (
    EthosEngine,
    DemoEthosEngine,
    ConsentCapacity,
    ConsentScope,
    ConsentRecord,
)


class MockCortexShield:
    """Minimal stand-in for CognitiveShield. EthosEngine only needs
    get_cdi_status() -> dict with 'blocked' and 'hard_violations'."""

    def __init__(self, blocked=False, hard_violations=0):
        self._status = {"blocked": blocked, "hard_violations": hard_violations}

    def set_status(self, blocked=False, hard_violations=0):
        self._status = {"blocked": blocked, "hard_violations": hard_violations}

    def get_cdi_status(self):
        return self._status


# -- 1. Consent capacity mapping [ETHOS-FIX-01] -----------------------------

class TestConsentCapacity:

    def test_full_capacity_when_clear(self):
        """Zero hard violations, not blocked -> FULL."""
        shield = MockCortexShield(blocked=False, hard_violations=0)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.FULL

    def test_full_capacity_with_one_violation(self):
        """One hard violation is still within FULL range."""
        shield = MockCortexShield(blocked=False, hard_violations=1)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.FULL

    def test_limited_capacity_at_two_violations(self):
        """Exactly two hard violations -> LIMITED."""
        shield = MockCortexShield(blocked=False, hard_violations=2)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.LIMITED

    def test_none_capacity_at_three_violations(self):
        """[ETHOS-FIX-01] Three or more hard violations -> NONE, not LIMITED.
        This is the exact regression the fix addressed: previous code had
        `if hard >= 2: LIMITED` evaluated before `>= 3`, making NONE
        unreachable via the violation-count path."""
        shield = MockCortexShield(blocked=False, hard_violations=3)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.NONE

    def test_none_capacity_with_many_violations(self):
        """Higher violation counts must not fall back to LIMITED."""
        shield = MockCortexShield(blocked=False, hard_violations=10)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.NONE

    def test_none_capacity_when_cdi_blocked(self):
        """CDI blocked overrides violation count entirely -> NONE."""
        shield = MockCortexShield(blocked=True, hard_violations=0)
        engine = EthosEngine(shield)
        assert engine.get_consent_capacity() == ConsentCapacity.NONE


# -- 2. Consent request gating -----------------------------------------------

class TestRequestConsent:

    def test_full_capacity_grants_without_confirmation(self):
        """FULL capacity must grant consent immediately, no double-confirm."""
        shield = MockCortexShield(blocked=False, hard_violations=0)
        engine = EthosEngine(shield)
        granted = engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
        assert granted is True
        assert engine.check_consent(ConsentScope.BIOMETRIC) is True

    def test_none_capacity_refuses_consent(self):
        """NONE capacity must refuse consent outright."""
        shield = MockCortexShield(blocked=True, hard_violations=0)
        engine = EthosEngine(shield)
        granted = engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
        assert granted is False
        assert engine.check_consent(ConsentScope.BIOMETRIC) is False

    def test_limited_capacity_base_class_raises(self):
        """[ETHOS-FIX-02] Base EthosEngine must raise NotImplementedError on
        LIMITED capacity -- it must never silently auto-confirm. A production
        deployment of the base class must fail loudly, not grant consent
        without real user confirmation."""
        shield = MockCortexShield(blocked=False, hard_violations=2)
        engine = EthosEngine(shield)
        try:
            engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
            assert False, "Expected NotImplementedError, but none was raised"
        except NotImplementedError:
            pass

    def test_limited_capacity_demo_engine_grants(self):
        """DemoEthosEngine overrides _double_confirmation and may grant
        LIMITED-capacity consent -- this is the documented PoC-only path."""
        shield = MockCortexShield(blocked=False, hard_violations=2)
        engine = DemoEthosEngine(shield)
        granted = engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
        assert granted is True


# -- 3. Revocation ------------------------------------------------------------

class TestRevocation:

    def test_revoke_consent_by_id(self):
        shield = MockCortexShield()
        engine = EthosEngine(shield)
        engine.request_consent(ConsentScope.AUDIO, purpose="test")
        record_id = engine.get_audit_log()[0]["id"]
        revoked = engine.revoke_consent(record_id)
        assert revoked is True
        assert engine.check_consent(ConsentScope.AUDIO) is False

    def test_revoke_unknown_id_returns_false(self):
        shield = MockCortexShield()
        engine = EthosEngine(shield)
        assert engine.revoke_consent("nonexistent") is False

    def test_revoke_all_clears_every_scope(self):
        shield = MockCortexShield()
        engine = EthosEngine(shield)
        engine.request_consent(ConsentScope.BIOMETRIC, purpose="a")
        engine.request_consent(ConsentScope.AUDIO, purpose="b")
        engine.revoke_all()
        assert engine.check_consent(ConsentScope.BIOMETRIC) is False
        assert engine.check_consent(ConsentScope.AUDIO) is False


# -- 4. Auto-revocation on dysregulation [ETHOS-FIX-03] ----------------------

class TestAutoRevoke:

    def test_auto_revoke_triggers_on_none_capacity(self):
        """[ETHOS-FIX-03] NONE capacity must trigger auto-revocation of all
        active consents."""
        shield = MockCortexShield(blocked=False, hard_violations=0)
        engine = EthosEngine(shield)
        engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
        assert engine.check_consent(ConsentScope.BIOMETRIC) is True

        shield.set_status(blocked=True, hard_violations=0)
        engine.auto_revoke_on_dysregulation()
        assert engine.check_consent(ConsentScope.BIOMETRIC) is False

    def test_auto_revoke_does_not_trigger_on_limited_capacity(self):
        """[ETHOS-FIX-03] LIMITED (sympathetic, stressed-but-capable) must
        NOT trigger auto-revocation. A stressed user must not silently lose
        an already-active consent mid-session."""
        shield = MockCortexShield(blocked=False, hard_violations=0)
        engine = DemoEthosEngine(shield)
        engine.request_consent(ConsentScope.BIOMETRIC, purpose="test")
        assert engine.check_consent(ConsentScope.BIOMETRIC) is True

        shield.set_status(blocked=False, hard_violations=2)  # LIMITED
        engine.auto_revoke_on_dysregulation()
        assert engine.check_consent(ConsentScope.BIOMETRIC) is True

    def test_auto_revoke_is_noop_when_nothing_active(self):
        """Calling auto-revoke with no active consents must not error."""
        shield = MockCortexShield(blocked=True, hard_violations=0)
        engine = EthosEngine(shield)
        engine.auto_revoke_on_dysregulation()  # must not raise


# -- 5. ConsentRecord expiry semantics [ETHOS-FIX-04] ------------------------

class TestConsentRecordExpiry:

    def test_is_active_true_for_fresh_unrevoked_record(self):
        record = ConsentRecord(
            id="test1", scope=ConsentScope.AUDIO, purpose="x",
            granted_at=time.time(), expires_at=time.time() + 3600,
            user_state_hash="deadbeef",
        )
        assert record.is_active() is True

    def test_is_active_false_when_expired(self):
        """[ETHOS-FIX-04] Atomic expiry check -- expired record is inactive
        even if revoked is False."""
        record = ConsentRecord(
            id="test2", scope=ConsentScope.AUDIO, purpose="x",
            granted_at=time.time() - 7200, expires_at=time.time() - 3600,
            user_state_hash="deadbeef",
        )
        assert record.is_active() is False

    def test_is_active_false_when_revoked(self):
        """Revoked record is inactive even if not yet expired."""
        record = ConsentRecord(
            id="test3", scope=ConsentScope.AUDIO, purpose="x",
            granted_at=time.time(), expires_at=time.time() + 3600,
            user_state_hash="deadbeef", revoked=True,
        )
        assert record.is_active() is False


# -- 6. Audit log privacy -----------------------------------------------------

class TestAuditLog:

    def test_audit_log_contains_no_biometric_data(self):
        """Audit log entries must expose only metadata -- no biometric
        values, no user-identifiable information beyond a truncated hash."""
        shield = MockCortexShield()
        engine = EthosEngine(shield)
        engine.request_consent(ConsentScope.BIOMETRIC, purpose="test purpose")

        log = engine.get_audit_log()
        assert len(log) == 1
        entry = log[0]
        expected_keys = {
            "id", "scope", "purpose", "granted_at",
            "expires_at", "user_state_hash", "revoked", "active",
        }
        assert set(entry.keys()) == expected_keys
        assert entry["scope"] == "biometric"
        assert entry["active"] is True


# -- Runner --------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    test_classes = [
        TestConsentCapacity,
        TestRequestConsent,
        TestRevocation,
        TestAutoRevoke,
        TestConsentRecordExpiry,
        TestAuditLog,
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 65)
    print("  Cortex Protocol -- ETHOS Consent Test Suite")
    print("=" * 65)

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        print(f"\n> {cls.__name__} ({len(methods)} tests)")
        for method in methods:
            try:
                getattr(instance, method)()
                print(f"  OK  {method}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {method}")
                errors.append((f"{cls.__name__}.{method}", str(e)))
                failed += 1
            except Exception as e:
                print(f"  ERROR  {method}")
                errors.append((f"{cls.__name__}.{method}", traceback.format_exc()))
                failed += 1

    print("\n" + "=" * 65)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 65)

    if errors:
        print("\nFailure details:")
        for name, msg in errors:
            print(f"\n  {name}:\n    {msg}")
        sys.exit(1)
    else:
        print("\nAll tests passed. ETHOS consent behavior characterized.")
        sys.exit(0)
