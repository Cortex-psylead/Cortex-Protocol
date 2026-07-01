# ============================================================================
# tests/test_cognitive_shield_v2_smoke.py
# Cortex Protocol — Smoke test for CognitiveShield v2 (CORTEX+LIMES+ETHOS)
#
# Purpose: minimal end-to-end check that DemoCognitiveShield's consent flow
# still works after refactoring EthosEngine to import from src/ethos/
# instead of duplicating it internally. Run before AND after the refactor;
# output must be identical.
#
# Run: python -m pytest tests/test_cognitive_shield_v2_smoke.py -v
# ============================================================================

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'sal'))
from cognitive_shield_v2 import DemoCognitiveShield, ConsentScope


def make_eeg(amp=10.0, noise=5.0, fs=256):
    t = np.linspace(0, 1, fs)
    return amp * np.sin(2 * np.pi * 8 * t) + noise * np.random.randn(fs)


class TestDemoCognitiveShieldSmoke:

    def test_full_pipeline_grants_consent_and_ingests_frame(self):
        """End-to-end: register sensor, ingest one frame, confirm consent
        was auto-requested and granted, confirm a result was returned."""
        shield = DemoCognitiveShield()
        approved, msg = shield.register_sensor("eeg_fp1_certified_v1", 35.0, 16)
        assert approved is True

        result = shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
        assert result is not None
        assert "coherency_index" in result
        assert result["consent_active"] is True
        assert shield.ethos.check_consent(ConsentScope.BIOMETRIC) is True

    def test_limited_capacity_demo_auto_confirms(self):
        """Force LIMITED capacity (2 hard violations) directly on the
        drift_detector, then confirm request_consent still grants via
        the demo double-confirmation override -- this is the exact path
        that depended on the types.MethodType monkey-patch."""
        shield = DemoCognitiveShield()
        shield.drift_detector._hard_violations = 2
        granted = shield.ethos.request_consent(ConsentScope.AUDIO)
        assert granted is True

    def test_none_capacity_refuses_consent(self):
        """CDI blocked -> NONE capacity -> consent refused, no crash."""
        shield = DemoCognitiveShield()
        shield.drift_detector._blocked = True
        granted = shield.ethos.request_consent(ConsentScope.AUDIO)
        assert granted is False


if __name__ == "__main__":
    import traceback
    instance = TestDemoCognitiveShieldSmoke()
    methods = [m for m in dir(instance) if m.startswith("test_")]
    passed, failed = 0, 0
    for method in methods:
        try:
            getattr(instance, method)()
            print(f"  OK  {method}")
            passed += 1
        except Exception:
            print(f"  FAIL  {method}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
