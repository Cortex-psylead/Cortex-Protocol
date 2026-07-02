## 🚀 Cortex Protocol v0.6.0 — Governance & Scientific Rigor Hardening

This release closes a full audit-and-harden pass triggered by discovering the
Bandit SAST step had silently failed on every run since the workflow's
creation, masked by `|| true` and an empty-SARIF fallback.

### 🔒 CI/CD Fixes
* SAL Boundary Guard no longer deadlocks on PRs that don't touch src/requirements.txt.
* Bandit SAST now actually runs (was previously fabricating a fake "no findings" result every time due to uppercase --confidence-level/--severity-level flags it silently rejected).

### 🧪 Test Coverage
* 20 new characterization tests for ETHOS dynamic consent (previously zero coverage).
* 3 new end-to-end smoke tests for CognitiveShield v2's consent flow.

### 🔧 Refactor
* EthosEngine consolidated to a single source of truth (src/ethos/ethos_consent.py); removed the duplicated, drifted copy in cognitive_shield_v2.py and its fragile types.MethodType monkey-patch.

### 📖 Governance & Documentation
* LEXICON.md: institutional terminology bridge for grant/IRB/regulatory readers.
* GOVERNANCE.md: explicit Transitional Governance note (single-person White Branch, pending Issue #5).
* CLINICAL-BRIDGE.md: Module 3 — proposed validation roadmap for the CV/RMSSD proxy, the protocol's largest unvalidated scientific claim.
* ROADMAP.md: Milestone 1 scope narrowed explicitly to CORTEX+ETHOS; LIMES/KEROS/LOGOS deferred with stated technical/scientific reasons.

---

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
