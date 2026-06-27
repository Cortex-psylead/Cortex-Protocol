# ============================================================================
# tests/test_cognitive_shield.py
# Cortex Protocol — Test Suite for Milestone 0
#
# Run: python -m pytest tests/ -v
# Or:  python tests/test_cognitive_shield.py
# ============================================================================

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'sal'))
from cognitive_shield import (
    CognitiveShield,
    SensorCertificationAuthority,
    DriftDetector,
    AnonymousTensorFactory,
    ClinicalBridge,
    RawBiometricFrame,
    ClinicalThresholds,
    compute_coherency_index,
    coherency_to_state,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_eeg(amp=10.0, noise=5.0, fs=256):
    """Generates a synthetic EEG-like signal."""
    t = np.linspace(0, 1, fs)
    return amp * np.sin(2 * np.pi * 8 * t) + noise * np.random.randn(fs)


def certified_shield():
    """Returns a CognitiveShield with one certified sensor ready to use."""
    shield = CognitiveShield()
    shield.register_sensor("eeg_fp1_certified_v1", 35.0, 16)
    return shield


# ── 1. Sensor Certification ───────────────────────────────────────────────────

class TestSensorCertification:

    def test_unknown_sensor_rejected(self):
        """A sensor not in the whitelist must be rejected."""
        approved, msg = SensorCertificationAuthority.handshake(
            "eeg_unknown_brand", 40.0, 16
        )
        assert not approved
        assert "not in clinical whitelist" in msg

    def test_certified_sensor_approved(self):
        """A whitelisted sensor meeting quality thresholds must be approved."""
        approved, msg = SensorCertificationAuthority.handshake(
            "eeg_fp1_certified_v1", 35.0, 16
        )
        assert approved
        assert "certified" in msg.lower()

    def test_ingestion_blocked_without_registration(self):
        """Raw data must be rejected if sensor was never registered."""
        shield = CognitiveShield()
        result = shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
        assert result is None

    def test_ingestion_allowed_after_registration(self):
        """Raw data must be accepted after sensor registration."""
        shield = certified_shield()
        result = shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
        assert result is not None
        assert "coherency_index" in result
        assert "polyvagal_state" in result


# ── 2. Two-Phase Tensor Transformation ───────────────────────────────────────

class TestTensorTransformation:

    def test_phase_a_produces_five_features(self):
        """Phase A extraction must return exactly 5 features."""
        features = AnonymousTensorFactory.extract_clinical_features(make_eeg())
        assert features.shape == (5,)

    def test_phase_a_features_are_normalized(self):
        """All Phase A features must be in [0, 1] after normalization."""
        features = AnonymousTensorFactory.extract_clinical_features(make_eeg())
        assert np.all(features >= 0.0), "Features contain negative values"
        assert np.all(features <= 1.0), "Features exceed normalized range"

    def test_phase_b_produces_obfuscated_tensor(self):
        """Phase B obfuscation must produce a tensor of the same shape as Phase A."""
        import secrets
        salt = secrets.token_bytes(32)
        sensor_hash = "abc123"
        features = AnonymousTensorFactory.extract_clinical_features(make_eeg())
        tensor = AnonymousTensorFactory.obfuscate(features, salt, sensor_hash)
        assert tensor.shape == features.shape

    def test_phase_b_different_salts_produce_different_tensors(self):
        """Two sessions with different salts must produce different tensors."""
        import secrets
        features = AnonymousTensorFactory.extract_clinical_features(make_eeg())
        salt1 = secrets.token_bytes(32)
        salt2 = secrets.token_bytes(32)
        t1 = AnonymousTensorFactory.obfuscate(features, salt1, "sensor")
        t2 = AnonymousTensorFactory.obfuscate(features, salt2, "sensor")
        assert not np.array_equal(t1, t2), "Different salts produced identical tensors"

    def test_raw_frame_zeroed_after_context_exit(self):
        """RawBiometricFrame must zero its data array upon context exit."""
        data = make_eeg()
        import hashlib
        sensor_hash = hashlib.sha256(b"test").hexdigest()
        with RawBiometricFrame(sensor_hash=sensor_hash, timestamp=time.time(),
                               data=data.copy()) as frame:
            original_sum = np.sum(np.abs(frame.data))
            assert original_sum > 0, "Frame data was empty before exit"
        # After exit, frame.data should be all zeros
        assert np.all(frame.data == 0), "Frame data not zeroed after context exit"


# ── 3. Clinical Bridge ────────────────────────────────────────────────────────

class TestClinicalBridge:

    def test_calm_signal_passes_bridge(self):
        """A low-amplitude calm signal must pass the Clinical Bridge."""
        # Small amplitude → low std, p75, max → passes thresholds
        features = AnonymousTensorFactory.extract_clinical_features(
            make_eeg(amp=2.0, noise=0.5)
        )
        is_safe, _ = ClinicalBridge.validate(features)
        assert is_safe

    def test_high_amplitude_signal_blocked_by_bridge(self):
        """A high-amplitude stress signal must be blocked by the Clinical Bridge."""
        # Very large amplitude → high std, p75, max → fails thresholds
        features = AnonymousTensorFactory.extract_clinical_features(
            make_eeg(amp=80.0, noise=40.0)
        )
        is_safe, msg = ClinicalBridge.validate(features)
        assert not is_safe
        assert "ClinicalBridge blocked" in msg


# ── 4. Coherency Index ────────────────────────────────────────────────────────

class TestCoherencyIndex:

    def test_coherency_is_non_negative(self):
        """Coherency index must always be >= 0."""
        for _ in range(20):
            features = AnonymousTensorFactory.extract_clinical_features(make_eeg())
            ci = compute_coherency_index(features)
            assert ci >= 0.0

    def test_coherency_state_mapping(self):
        """State labels must correspond to correct CV ranges."""
        assert coherency_to_state(0.1) == "ventral_vagal (calm)"
        assert coherency_to_state(0.5) == "sympathetic (focused)"
        assert coherency_to_state(0.9) == "dorsal_vagal (rest_needed)"


# ── 5. Clinical Drift Index (CDI) ─────────────────────────────────────────────

class TestCDI:

    def test_normal_sessions_do_not_trigger_block(self):
        """Multiple normal-amplitude sessions must not trigger CDI block."""
        shield = certified_shield()
        for _ in range(10):
            result = shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
            assert result is not None, "Normal session was blocked unexpectedly"
        assert not shield.drift_detector.is_blocked()

    def test_hard_violation_triggers_block(self):
        """Sustained high-amplitude sessions must trigger a CDI hard block."""
        shield = certified_shield()
        blocked = False
        # Escalate amplitude aggressively to force hard violations
        for amp in [5, 10, 20, 35, 50, 70, 90]:
            result = shield.ingest_raw_data(
                "eeg_fp1_certified_v1",
                make_eeg(amp=amp, noise=amp * 0.5)
            )
            if result is None:
                blocked = True
                break
        assert blocked, "CDI did not block despite sustained high-amplitude drift"

    def test_blocked_shield_rejects_all_subsequent_ingestions(self):
        """Once CDI blocks, all subsequent ingestion attempts must return None."""
        detector = DriftDetector()
        # Force block by injecting maximum violations directly
        for _ in range(ClinicalThresholds.HARD_BLOCK_VIOLATIONS + 1):
            detector._hard_violations = ClinicalThresholds.HARD_BLOCK_VIOLATIONS
            detector._blocked = True
            break
        assert detector.is_blocked()
        is_safe, msg = detector.add_reading(999.0)
        assert not is_safe
        assert "blocked" in msg.lower()

    def test_baseline_establishment(self):
        """Baseline must be established after 7 sessions."""
        detector = DriftDetector()
        assert not detector._baseline_ready
        sessions = [0.2, 0.25, 0.18, 0.22, 0.19, 0.21, 0.20]
        detector.establish_baseline(sessions)
        assert detector._baseline_ready
        assert abs(detector._baseline_mean - np.mean(sessions)) < 1e-6

    def test_baseline_requires_minimum_three_sessions(self):
        """Baseline establishment must be silently skipped with fewer than 3 sessions."""
        detector = DriftDetector()
        detector.establish_baseline([0.2, 0.3])  # only 2 — should not establish
        assert not detector._baseline_ready

    def test_soft_violation_z_score_detection(self):
        """A reading 3+ std deviations from baseline must increment soft violations."""
        detector = DriftDetector()
        detector.establish_baseline([0.2, 0.22, 0.21, 0.19, 0.20, 0.21, 0.20])
        initial_soft = detector._soft_violations
        # Inject a massive outlier (far above baseline mean ~0.20)
        detector.add_reading(0.85)
        assert detector._soft_violations > initial_soft


# ── 6. Audit Log & Session Destruction ───────────────────────────────────────

class TestAuditAndSession:

    def test_audit_log_contains_no_raw_identifiers(self):
        """Audit log entries must not contain full sensor hashes or raw feature values."""
        shield = certified_shield()
        for _ in range(3):
            shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
        log = shield.get_audit_log()
        assert len(log) == 3
        for entry in log:
            # Sensor hash must be truncated (8 chars), not full SHA-256 (64 chars)
            assert len(entry["sensor_hash"]) == 8, "Full sensor hash exposed in audit log"
            assert "coherency" in entry
            assert "polyvagal" in entry

    def test_session_destruction_clears_log(self):
        """destroy_session() must clear the audit log."""
        shield = certified_shield()
        for _ in range(3):
            shield.ingest_raw_data("eeg_fp1_certified_v1", make_eeg())
        assert len(shield.get_audit_log()) == 3
        shield.destroy_session()
        assert len(shield.get_audit_log()) == 0

    def test_session_destruction_renews_salt(self):
        """destroy_session() must generate a new session salt."""
        shield = certified_shield()
        salt_before = shield._session_salt
        shield.destroy_session()
        assert shield._session_salt != salt_before, "Session salt was not renewed"


# ── 7. Sensor Adapter Interface ──────────────────────────────────────────────

class TestSensorAdapterInterface:
    """
    Validates the abstract BiometricSensorAdapter interface.
    Any real sensor driver must pass these tests to be Cortex-compatible.
    """

    def test_mock_adapter_satisfies_interface(self):
        """A mock adapter implementing the interface must work end-to-end."""

        class MockMuseAdapter:
            """Simulates a Muse 2 headset returning synthetic EEG frames."""
            def get_frame(self) -> np.ndarray:
                return make_eeg(amp=8.0, noise=3.0)
            def get_sensor_id(self) -> str:
                return "eeg_fp1_certified_v1"

        adapter = MockMuseAdapter()
        shield = certified_shield()

        frame = adapter.get_frame()
        sensor_id = adapter.get_sensor_id()

        assert frame.shape == (256,), "Adapter must return 256-sample frames"
        assert isinstance(sensor_id, str), "Adapter must return string sensor ID"

        result = shield.ingest_raw_data(sensor_id, frame)
        assert result is not None, "Mock adapter frame was rejected by shield"


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback

    test_classes = [
        TestSensorCertification,
        TestTensorTransformation,
        TestClinicalBridge,
        TestCoherencyIndex,
        TestCDI,
        TestAuditAndSession,
        TestSensorAdapterInterface,
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 65)
    print("  Cortex Protocol — Test Suite (Milestone 0)")
    print("=" * 65)

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        print(f"\n▸ {cls.__name__} ({len(methods)} tests)")
        for method in methods:
            try:
                getattr(instance, method)()
                print(f"  ✅  {method}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌  {method}")
                errors.append((f"{cls.__name__}.{method}", str(e)))
                failed += 1
            except Exception as e:
                print(f"  💥  {method} — unexpected error")
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
        print("\n✅ All tests passed. Milestone 0 integrity verified.")
        sys.exit(0)
      
