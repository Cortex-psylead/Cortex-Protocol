# ============================================================================
# src/keros/brainflow_adapter.py
# CORTEX PROTOCOL — BrainFlow Sensor Adapter (Milestone 1)
#
# THE INTEGRATION GAP THIS MODULE CLOSES:
#   The SAL pipeline (Phase A feature extraction → Clinical Bridge → CDI →
#   TelemetryRouter) is fully implemented and tested, but every biometric
#   sample fed into it so far has been a NumPy sine-wave simulation.
#
#   This module connects REAL EEG hardware to that pipeline. It reads frames
#   from any BrainFlow-supported board (OpenBCI Cyton, Muse 2, Neurosity
#   Crown, or the zero-cost SYNTHETIC_BOARD used by CI), runs the existing
#   Phase A feature extraction, maps the result to a Polyvagal state, and
#   feeds a structured payload into `TelemetryRouter.ingest_from_bridge()`.
#
#     [EEG hardware / BrainFlow board]
#            │  read_raw_window()      (this module)
#            ▼
#     raw_samples : np.ndarray (N,) float
#            │  AnonymousTensorFactory.extract_features()   (reused from SAL)
#            ▼
#     features : np.ndarray (5,)   [mean, std, p25, p75, max] of Hilbert env.
#            │  compute_coherency() + coherency_to_state()  (reused from SAL)
#            ▼
#     bridge_payload : dict
#            │  TelemetryRouter.ingest_from_bridge()         (already J3.1)
#            ▼
#     DeSci / Clinical channels
#
# SOVEREIGNTY PROPERTIES (CONTRIBUTING.md compliance):
#   1. 100% LOCAL — BrainFlow reads from local USB/BLE/WiFi hardware. No
#      sample ever leaves the device through this adapter.
#   2. HARDWARE-AGNOSTIC — the adapter targets the BrainFlow abstraction, not
#      any single vendor. The BiometricSensorAdapter ABC lets future adapters
#      (Emotiv, etc.) follow the same contract. No hardware lock-in.
#   3. NO RAW EXFILTRATION — only the non-invertible Phase A feature vector
#      is forwarded downstream; the raw window stays inside this process and
#      is reused, never serialized.
#   4. REPLAY PROTECTION — frame_seq is monotone per sensor session; the
#      router rejects any non-increasing sequence as a replay attack.
#
# Dependencies: brainflow, numpy (+ the SAL package for feature reuse)
# ============================================================================

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import numpy as np

# Reuse the SAL's Phase A feature extraction and Polyvagal mapping rather than
# re-implementing them — the clinical thresholds and envelope maths are
# White-Branch-mandated and must stay single-sourced (DRY, audit integrity).
try:
    from sal.cognitive_shield_v2 import (
        AnonymousTensorFactory,
        TelemetryRouter,
        compute_coherency,
        coherency_to_state,
    )
except ImportError:  # pragma: no cover - source-tree fallback
    import os
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from sal.cognitive_shield_v2 import (  # type: ignore[no-redef]
        AnonymousTensorFactory,
        TelemetryRouter,
        compute_coherency,
        coherency_to_state,
    )


# ============================================================================
# 1. ABSTRACT SENSOR ADAPTER
# ============================================================================

class BiometricSensorAdapter(ABC):
    """
    Contract every biometric sensor adapter must satisfy to feed the SAL.

    Concrete adapters (BrainFlow, Emotiv, ...) implement only the hardware
    I/O — `connect`, `disconnect`, `read_raw_window`, and `sample_rate_hz`.
    The shared, security-critical logic (feature extraction, Polyvagal
    mapping, monotone frame sequencing, payload construction) lives here so
    every adapter routes data through the SAL identically.

    Usage:
        with BrainFlowSensorAdapter(sensor_id="MUSE2_SN01") as adapter:
            adapter.stream_to_router(router, num_frames=10)
    """

    def __init__(self, sensor_id: str, window_samples: int = 256) -> None:
        if not sensor_id:
            raise ValueError("sensor_id must be a non-empty certified identifier")
        if window_samples < 8:
            # Hilbert envelope statistics are meaningless on a tiny window.
            raise ValueError("window_samples must be >= 8")

        self.sensor_id: str = sensor_id
        # Stable per-sensor identifier for the router's replay table. The raw
        # sensor_id is hashed so the downstream table never holds a plaintext
        # device serial.
        self.sensor_id_hash: bytes = hashlib.sha256(sensor_id.encode()).digest()
        self.window_samples: int = window_samples

        self._frame_seq: int = 0
        self._connected: bool = False

    # ── Hardware I/O — implemented by concrete adapters ─────────────────────

    @abstractmethod
    def connect(self) -> None:
        """Open the device session and begin streaming. Resets frame_seq."""

    @abstractmethod
    def disconnect(self) -> None:
        """Stop streaming and release the device session."""

    @abstractmethod
    def read_raw_window(self) -> np.ndarray:
        """
        Block until one window of EEG samples is available and return it.

        Returns:
            1-D float ndarray of length ``window_samples`` for a single
            EEG channel (the channel the adapter was configured to read).
        """

    @property
    @abstractmethod
    def sample_rate_hz(self) -> int:
        """The device's native EEG sample rate in Hz."""

    # ── Shared SAL integration logic ────────────────────────────────────────

    def build_bridge_payload(self, raw_window: np.ndarray) -> Dict[str, Any]:
        """
        Turn one raw EEG window into a TelemetryRouter bridge payload.

        Reuses the SAL's Phase A feature extraction and Polyvagal mapping, so
        the labels and feature semantics match exactly what
        ``ingest_from_bridge`` validates against. ``frame_seq`` is incremented
        on every call to guarantee a strictly monotone sequence per session.
        """
        features = AnonymousTensorFactory.extract_features(raw_window)
        coherency = compute_coherency(features)
        # coherency_to_state returns one of the three canonical, whitelisted
        # Polyvagal labels — so the payload always passes the router's check.
        polyvagal_state = coherency_to_state(coherency)

        payload: Dict[str, Any] = {
            "features": features,
            "coherency": coherency,
            "polyvagal_state": polyvagal_state,
            "timestamp": time.time(),
            "frame_seq": self._frame_seq,
            "sensor_id_hash": self.sensor_id_hash,
            "keros_seal_bytes": None,
        }
        self._frame_seq += 1
        return payload

    def stream_to_router(
        self,
        router: "TelemetryRouter",
        num_frames: int,
        on_result: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read ``num_frames`` windows from the device and feed each into the
        router's ``ingest_from_bridge``.

        Args:
            router:     A SAL TelemetryRouter (the J3.1 ingest target).
            num_frames: How many windows to read and route.
            on_result:  Optional callback invoked with each router result dict.

        Returns:
            The list of per-frame result dicts returned by the router.
        """
        if not self._connected:
            raise RuntimeError("Adapter is not connected; call connect() first")
        if num_frames < 0:
            raise ValueError("num_frames must be >= 0")

        results: List[Dict[str, Any]] = []
        for _ in range(num_frames):
            raw_window = self.read_raw_window()
            payload = self.build_bridge_payload(raw_window)
            result = router.ingest_from_bridge(payload)
            results.append(result)
            if on_result is not None:
                on_result(result)
        return results

    @property
    def frame_seq(self) -> int:
        """The next frame sequence number that will be emitted."""
        return self._frame_seq

    @property
    def connected(self) -> bool:
        return self._connected

    # ── Context manager sugar ───────────────────────────────────────────────

    def __enter__(self) -> "BiometricSensorAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()


# ============================================================================
# 2. BRAINFLOW ADAPTER
# ============================================================================

class BrainFlowSensorAdapter(BiometricSensorAdapter):
    """
    Reads EEG from any BrainFlow-supported board and feeds the SAL pipeline.

    For CI and local development, use ``BoardIds.SYNTHETIC_BOARD`` (the
    default) — it streams a deterministic signal with no physical hardware.
    For real devices, pass the matching board id plus a populated
    ``BrainFlowInputParams`` (serial_port / mac_address / ip_address).

    See ``docs/hardware/BRAINFLOW_SETUP.md`` for per-device wiring.
    """

    # How long to wait for the ring buffer to fill before giving up on a frame.
    _READ_TIMEOUT_SECONDS: float = 5.0

    def __init__(
        self,
        sensor_id: str = "BRAINFLOW_SYNTHETIC_SN00",
        board_id: Optional[int] = None,
        params: Optional[Any] = None,
        eeg_channel_index: int = 0,
        window_samples: int = 256,
    ) -> None:
        # Imported lazily so importing this module never hard-requires brainflow
        # (e.g. for the ABC alone). Concrete construction does require it.
        from brainflow.board_shim import (
            BoardIds,
            BoardShim,
            BrainFlowInputParams,
        )

        super().__init__(sensor_id=sensor_id, window_samples=window_samples)

        self._BoardShim = BoardShim
        self._board_id = int(BoardIds.SYNTHETIC_BOARD if board_id is None else board_id)
        self._params = params if params is not None else BrainFlowInputParams()
        self._eeg_channel_index = eeg_channel_index

        eeg_channels = BoardShim.get_eeg_channels(self._board_id)
        if not eeg_channels:
            raise ValueError(f"Board {self._board_id} reports no EEG channels")
        if not 0 <= eeg_channel_index < len(eeg_channels):
            raise ValueError(
                f"eeg_channel_index {eeg_channel_index} out of range "
                f"(board has {len(eeg_channels)} EEG channels)"
            )
        # Row index into the BrainFlow data matrix for the chosen EEG channel.
        self._eeg_row = eeg_channels[eeg_channel_index]
        self._sample_rate = int(BoardShim.get_sampling_rate(self._board_id))

        self._board: Optional[Any] = None

    @property
    def sample_rate_hz(self) -> int:
        return self._sample_rate

    @property
    def board_id(self) -> int:
        return self._board_id

    def connect(self) -> None:
        if self._connected:
            return
        # Silence BrainFlow's native logger so CI output stays clean.
        self._BoardShim.disable_board_logger()
        self._board = self._BoardShim(self._board_id, self._params)
        self._board.prepare_session()
        self._board.start_stream()
        self._frame_seq = 0  # fresh monotone sequence per session
        self._connected = True

    def disconnect(self) -> None:
        if not self._connected or self._board is None:
            return
        try:
            if self._board.is_prepared():
                self._board.stop_stream()
                self._board.release_session()
        finally:
            self._board = None
            self._connected = False

    def read_raw_window(self) -> np.ndarray:
        """
        Wait until ``window_samples`` samples are buffered, then return the
        most recent window from the configured EEG channel as float64.
        """
        if not self._connected or self._board is None:
            raise RuntimeError("Adapter is not connected; call connect() first")

        # Poll until the ring buffer holds at least one full window. Sleeping
        # one window-duration at a time keeps this responsive without busy-wait.
        window_seconds = self.window_samples / self._sample_rate
        deadline = time.monotonic() + self._READ_TIMEOUT_SECONDS
        while self._board.get_board_data_count() < self.window_samples:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Timed out waiting for {self.window_samples} samples "
                    f"from board {self._board_id}"
                )
            time.sleep(window_seconds)

        # get_current_board_data returns the latest N columns without clearing
        # the buffer, so consecutive frames advance with real time.
        data = self._board.get_current_board_data(self.window_samples)
        return np.ascontiguousarray(data[self._eeg_row], dtype=np.float64)


# ============================================================================
# 3. SELF-TEST  (synthetic board — no hardware, no network)
# ============================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  Cortex — BrainFlow Sensor Adapter Self-Test (SYNTHETIC_BOARD)")
    print("=" * 68)

    router = TelemetryRouter()
    accepted = 0

    with BrainFlowSensorAdapter(
        sensor_id="BRAINFLOW_SYNTHETIC_SELFTEST",
        window_samples=256,
    ) as adapter:
        print(f"\n  board_id={adapter.board_id}  rate={adapter.sample_rate_hz} Hz")

        def _show(result: Dict[str, Any]) -> None:
            global accepted
            if result.get("reason") == "accepted":
                accepted += 1

        results = adapter.stream_to_router(router, num_frames=5, on_result=_show)

    seqs = [i for i, _ in enumerate(results)]
    print(f"\n  frames routed : {len(results)}")
    print(f"  accepted      : {accepted}")
    print(f"  reasons       : {[r['reason'] for r in results]}")
    assert len(results) == 5, "expected 5 routed frames"
    assert accepted == 5, "all synthetic frames should be accepted"
    print("\n✅ BrainFlow adapter self-test complete")
    print("   Pipeline: BrainFlow → Phase A features → ingest_from_bridge → OK")
