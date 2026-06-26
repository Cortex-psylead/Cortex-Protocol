"""
Tests for the BrainFlow Sensor Adapter (src/keros/brainflow_adapter.py).

The suite is split in two:

  * Shared SAL-contract logic (payload construction, validation, frame
    sequencing, the ABC) lives on ``BiometricSensorAdapter`` and needs no
    hardware *and no brainflow package* — these run everywhere and are
    exercised through a tiny brainflow-free ``_PayloadAdapter``.
  * Board-dependent behaviour (the lazy brainflow import and the
    SYNTHETIC_BOARD streaming path) is gated behind ``@requires_brainflow``
    so a CI image without brainflow's native wheel skips them gracefully
    instead of erroring out. When brainflow *is* installed (it is in
    requirements.txt) every test runs.

The whole suite must pass under ``python -W error`` (the acceptance bar in
issue #4): any warning is treated as a failure.

Run:
    PYTHONPATH=src python -W error -m pytest tests/test_brainflow_adapter.py -q
"""

import hashlib
import importlib.util

import numpy as np
import pytest

from keros.brainflow_adapter import (
    BiometricSensorAdapter,
    BrainFlowSensorAdapter,
)
from sal.cognitive_shield_v2 import TelemetryRouter

CANONICAL_STATES = TelemetryRouter._ALLOWED_POLYVAGAL_STATES
REQUIRED_KEYS = TelemetryRouter._REQUIRED_KEYS

# brainflow ships a native library and is not guaranteed to be importable in
# every CI image. Only the board-streaming tests truly need it; the shared
# base-class logic is tested without it.
_HAS_BRAINFLOW = importlib.util.find_spec("brainflow") is not None
requires_brainflow = pytest.mark.skipif(
    not _HAS_BRAINFLOW,
    reason="brainflow native package not installed",
)


class _PayloadAdapter(BiometricSensorAdapter):
    """Minimal brainflow-free adapter that exercises the shared base logic.

    ``BrainFlowSensorAdapter`` inherits ``build_bridge_payload``, validation,
    frame sequencing and the context-manager sugar unchanged from the base,
    so testing them here is equivalent — and keeps the core SAL-contract
    coverage alive even where brainflow cannot be installed.
    """

    def __init__(self, sensor_id: str = "UNIT_TEST_SENSOR", window_samples: int = 64):
        super().__init__(sensor_id=sensor_id, window_samples=window_samples)

    @property
    def sample_rate_hz(self) -> int:
        return 250

    def connect(self) -> None:
        self._connected = True
        self._frame_seq = 0

    def disconnect(self) -> None:
        self._connected = False

    def read_raw_window(self) -> np.ndarray:
        return np.sin(np.linspace(0, 8 * np.pi, self.window_samples))


class _RecordingRouter:
    """Captures every payload passed to ingest_from_bridge for assertions."""

    def __init__(self) -> None:
        self.payloads: list = []

    def ingest_from_bridge(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return {"desci": True, "clinical": False, "reason": "accepted"}


# =============================================================================
# Payload construction (no hardware, no brainflow)
# =============================================================================


class TestBridgePayload:
    """build_bridge_payload must satisfy the exact ingest_from_bridge contract."""

    def _adapter(self) -> _PayloadAdapter:
        return _PayloadAdapter(sensor_id="UNIT_TEST_SENSOR", window_samples=64)

    def test_payload_has_all_required_keys(self):
        adapter = self._adapter()
        raw = np.sin(np.linspace(0, 8 * np.pi, 64))
        payload = adapter.build_bridge_payload(raw)
        assert REQUIRED_KEYS.issubset(payload.keys())

    def test_features_shape_is_5(self):
        adapter = self._adapter()
        raw = np.random.default_rng(0).standard_normal(64)
        payload = adapter.build_bridge_payload(raw)
        assert isinstance(payload["features"], np.ndarray)
        assert payload["features"].shape == (5,)

    def test_polyvagal_state_is_canonical(self):
        adapter = self._adapter()
        for seed in range(20):
            raw = np.random.default_rng(seed).standard_normal(64) * (seed + 1)
            payload = adapter.build_bridge_payload(raw)
            assert payload["polyvagal_state"] in CANONICAL_STATES

    def test_frame_seq_increments_monotonically(self):
        adapter = self._adapter()
        raw = np.sin(np.linspace(0, 8 * np.pi, 64))
        seqs = [adapter.build_bridge_payload(raw)["frame_seq"] for _ in range(5)]
        assert seqs == [0, 1, 2, 3, 4]

    def test_sensor_id_hash_is_sha256_of_id(self):
        adapter = self._adapter()
        expected = hashlib.sha256(b"UNIT_TEST_SENSOR").digest()
        assert adapter.sensor_id_hash == expected

    def test_payload_accepted_by_real_router(self):
        adapter = self._adapter()
        router = TelemetryRouter()
        raw = np.sin(np.linspace(0, 8 * np.pi, 64))
        result = router.ingest_from_bridge(adapter.build_bridge_payload(raw))
        assert result["reason"] == "accepted"


# =============================================================================
# Shared base-class validation (no brainflow)
# =============================================================================


class TestBaseValidation:
    def test_empty_sensor_id_rejected(self):
        with pytest.raises(ValueError, match="sensor_id"):
            _PayloadAdapter(sensor_id="")

    def test_tiny_window_rejected(self):
        with pytest.raises(ValueError, match="window_samples"):
            _PayloadAdapter(sensor_id="X", window_samples=4)


# =============================================================================
# ABC contract (no brainflow)
# =============================================================================


class TestAbstractContract:
    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BiometricSensorAdapter(sensor_id="X")  # type: ignore[abstract]

    def test_minimal_subclass_streams(self):
        """A non-BrainFlow subclass can reuse all shared SAL logic."""
        router = _RecordingRouter()
        with _PayloadAdapter(sensor_id="FAKE", window_samples=64) as adapter:
            results = adapter.stream_to_router(router, num_frames=3)

        assert len(results) == 3
        assert [p["frame_seq"] for p in router.payloads] == [0, 1, 2]

    def test_stream_before_connect_raises(self):
        adapter = _PayloadAdapter(sensor_id="X", window_samples=64)
        with pytest.raises(RuntimeError, match="not connected"):
            adapter.stream_to_router(TelemetryRouter(), num_frames=1)


# =============================================================================
# BrainFlow-specific construction (needs the brainflow package)
# =============================================================================


@requires_brainflow
class TestBrainFlowConstruction:
    def test_out_of_range_channel_rejected(self):
        with pytest.raises(ValueError, match="eeg_channel_index"):
            BrainFlowSensorAdapter(sensor_id="X", eeg_channel_index=9999)

    def test_brainflow_adapter_enforces_base_validation(self):
        """The concrete adapter still applies the shared sensor_id guard."""
        with pytest.raises(ValueError, match="sensor_id"):
            BrainFlowSensorAdapter(sensor_id="")


# =============================================================================
# Synthetic-board integration (real BrainFlow streaming)
# =============================================================================


@requires_brainflow
class TestSyntheticBoardIntegration:
    def test_connect_and_stream_end_to_end(self):
        router = TelemetryRouter()
        with BrainFlowSensorAdapter(
            sensor_id="SYNTH_E2E", window_samples=64
        ) as adapter:
            assert adapter.connected is True
            assert adapter.sample_rate_hz == 250
            results = adapter.stream_to_router(router, num_frames=4)

        assert len(results) == 4
        assert all(r["reason"] == "accepted" for r in results)

    def test_frame_seq_monotonic_and_states_canonical(self):
        router = _RecordingRouter()
        with BrainFlowSensorAdapter(
            sensor_id="SYNTH_SEQ", window_samples=64
        ) as adapter:
            adapter.stream_to_router(router, num_frames=5)

        seqs = [p["frame_seq"] for p in router.payloads]
        assert seqs == sorted(seqs)
        assert seqs == list(range(5))
        assert all(p["polyvagal_state"] in CANONICAL_STATES for p in router.payloads)

    def test_reconnect_resets_frame_seq(self):
        adapter = BrainFlowSensorAdapter(sensor_id="SYNTH_RESET", window_samples=64)
        router = _RecordingRouter()

        adapter.connect()
        adapter.stream_to_router(router, num_frames=2)
        adapter.disconnect()
        assert adapter.connected is False

        adapter.connect()
        adapter.stream_to_router(router, num_frames=2)
        adapter.disconnect()

        # Two sessions of [0, 1] each — frame_seq is per-session monotone.
        assert [p["frame_seq"] for p in router.payloads] == [0, 1, 0, 1]

    def test_disconnect_is_idempotent(self):
        adapter = BrainFlowSensorAdapter(sensor_id="SYNTH_IDEM", window_samples=64)
        adapter.connect()
        adapter.disconnect()
        adapter.disconnect()  # second call must not raise
        assert adapter.connected is False
