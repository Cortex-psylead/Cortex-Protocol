# BrainFlow Sensor Adapter — Hardware Setup

The `BrainFlowSensorAdapter` (`src/keros/brainflow_adapter.py`) connects real
EEG hardware to the Cortex SAL pipeline. It reads frames from any
[BrainFlow](https://brainflow.org)-supported board, runs the existing Phase A
feature extraction, maps the result to a Polyvagal state, and feeds a
structured payload into `TelemetryRouter.ingest_from_bridge()`.

> **Sovereignty note:** BrainFlow reads from your **local** USB / Bluetooth /
> WiFi device. No raw sample leaves your machine through this adapter — only
> the non-invertible 5-feature Phase A vector is passed downstream.

---

## 1. Install

```bash
pip install -r requirements.txt   # includes brainflow
# or, just the adapter dependency:
pip install brainflow
```

BrainFlow ships prebuilt native libraries for Linux, macOS, and Windows — no
compiler or board SDK is required.

---

## 2. Run with no hardware (synthetic board)

The synthetic board streams a deterministic signal and is what CI uses. It
needs **zero** hardware and is the right starting point:

```python
from keros.brainflow_adapter import BrainFlowSensorAdapter
from sal.cognitive_shield_v2 import TelemetryRouter

router = TelemetryRouter()
with BrainFlowSensorAdapter(sensor_id="DEV_SYNTHETIC_01") as adapter:
    results = adapter.stream_to_router(router, num_frames=10)
    print([r["reason"] for r in results])   # -> ['accepted', 'accepted', ...]
```

Or run the module self-test directly:

```bash
PYTHONPATH=src python -W error -m keros.brainflow_adapter
```

---

## 3. Run with real hardware

Pass the device's `BoardIds` value and a `BrainFlowInputParams` populated with
the connection detail that device needs. Everything else is identical.

### OpenBCI Cyton (8-ch, 250 Hz, USB dongle)

```python
from brainflow.board_shim import BoardIds, BrainFlowInputParams
from keros.brainflow_adapter import BrainFlowSensorAdapter

params = BrainFlowInputParams()
params.serial_port = "/dev/ttyUSB0"        # Windows: "COM3"; macOS: "/dev/cu.usbserial-XXXX"

adapter = BrainFlowSensorAdapter(
    sensor_id="OPENBCI_CYTON_SN0042",
    board_id=BoardIds.CYTON_BOARD,
    params=params,
)
```

### Muse 2 (4-ch, BLE)

```python
params = BrainFlowInputParams()
params.mac_address = "00:55:DA:B0:00:00"   # leave blank to auto-discover the first Muse

adapter = BrainFlowSensorAdapter(
    sensor_id="MUSE2_SNxxxx",
    board_id=BoardIds.MUSE_2_BOARD,
    params=params,
)
```

> Muse over BLE needs the BrainFlow BLED112 dongle **or** native BLE support —
> see the BrainFlow [Muse docs](https://brainflow.readthedocs.io/en/stable/SupportedBoards.html#muse).

### Neurosity Crown (8-ch, WiFi)

```python
params = BrainFlowInputParams()
params.ip_address = "192.168.4.1"
params.serial_number = "crown-XXXX"

adapter = BrainFlowSensorAdapter(
    sensor_id="NEUROSITY_CROWN_XXXX",
    board_id=BoardIds.CROWN_BOARD,
    params=params,
)
```

The exact `BoardIds` and required `params` field for any other supported device
are listed in the BrainFlow
[Supported Boards](https://brainflow.readthedocs.io/en/stable/SupportedBoards.html)
table.

---

## 4. Adapter options

| Argument            | Default                      | Meaning                                              |
| ------------------- | ---------------------------- | ---------------------------------------------------- |
| `sensor_id`         | `BRAINFLOW_SYNTHETIC_SN00`   | Certified sensor identifier (SHA-256 → replay table) |
| `board_id`          | `BoardIds.SYNTHETIC_BOARD`   | BrainFlow board id                                   |
| `params`            | empty `BrainFlowInputParams` | Connection detail (serial / mac / ip)                |
| `eeg_channel_index` | `0`                          | Which EEG channel to read                            |
| `window_samples`    | `256`                        | Samples per frame fed to Phase A extraction          |

---

## 5. Clinical validation status

Streaming the adapter against the synthetic board is sufficient to **merge**
the code (it is what CI validates). Validation against **physical** hardware
(SNR, electrode contact, montage) is a Milestone 1 clinical requirement tracked
separately by a Governance Node — it is not a precondition for this adapter.
```
