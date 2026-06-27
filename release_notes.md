## 🚀 Cortex Protocol v0.5.2-beta.1 — Hardware Abstraction Layer

This version marks the official transition of the protocol from a pure simulation environment (`NumPy` sine-waves) to real-time bio-sensory telemetry ingestion using real or synthetic hardware.

### 🧠 Main Changes
* **Sensor Abstraction Layer:** Implementation of the `BiometricSensorAdapter` abstract base class to standardize future hardware integrations (EEG, ECG, PPG).
* **Integrated BrainFlow Adapter:** End-to-end connection with the BrainFlow architecture, enabling the processing of native biometric frames from devices such as OpenBCI Cyton, Muse 2, and Neurosity Crown.
* **Phase A Processing:** Automated mathematical extraction of real-time clinical features using the Hilbert envelope (`scipy.signal.hilbert`), mapping vectors directly to the `TelemetryRouter` under Polyvagal Theory thresholds.

### 🧪 Testing & Stability
* Unit test coverage successfully completed using BrainFlow's virtual `BoardIds.SYNTHETIC_BOARD` to guarantee viability in Continuous Integration (CI) environments.
* Strict monotonic increment of frame sequences (`frame_seq`) to mitigate replay attacks on the data bridge.

### 👥 Contributors in this Release
* @Cortex-psylead (Architecture & Review)
* @mayoka0 (Core Implementation & Tests)
* **Claude Opus 4.8** (AI Co-Author — Pair Programming Support)

---
*Note: This is a development pre-release corresponding to Milestone 1 (Clinical Validation). It is not yet intended for mainnet clinical production environments.*
