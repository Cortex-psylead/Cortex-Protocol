# 📊 User Data Model: Sovereign Mathematical Tensors

### The Standard for Ephemeral and Private Physiological Information
This document defines how the **Cortex Protocol** structures and protects user data. Following the **Mathematical Privacy Layer**, this model ensures that raw physiological signals are never stored; only anonymized, sovereign tensors exist within the system.
---

## 🧭 Design Philosophy: Data as a Biological Extension

User data in the Cortex Protocol follows three absolute principles:
1. **Ephemeral by Default:** Raw biometric signals (HRV, EEG, Voice) exist only in volatile memory (RAM) and are destroyed immediately after being processed into mathematical tensors.
2. **Sovereign Encryption:** Any data that persists (user preferences, local learning weights) is encrypted using hardware-backed keys (Secure Enclave) that the Protocol cannot access without a direct user command.
3. **Information over Data:** We store the *meaning* (e.g., "State: Flow") rather than the *measurement* (e.g., "Heart Rate: 85bpm").
---
## 📐 Data Layers
The protocol organizes information into three distinct, isolated layers:
### 1. The Transient Layer (Raw Signals)
- **Status:** **NON-PERSISTENT.**
- **Content:** Raw buffers from microphones, heart rate sensors, and environmental sensors.
- **Handling:** These stay within the **Sovereignty Abstraction Layer (SAL)**. They are piped directly into the Mathematical Privacy Layer and then wiped from memory.
### 2. The Tensor Layer (Anonymized Features)
- **Status:** **EPHEMERAL / ENCRYPTED.**
- **Content:** Vectorized mathematical representations of the user's state. 
- **Purpose:** Used by the **Acolyte** to understand intent and cognitive load without knowing the raw biological values.
- **Privacy:** These tensors are processed using **Differential Privacy** to ensure no raw signal can be reconstructed.
### 3. The Insight Layer (Sovereign History)
- **Status:** **OPT-IN / PERSISTENT.**
- **Content:** Derived clinical metrics (e.g., "Weekly Focus Trend", "Ventral Vagal Baseline").
- **Storage:** Stored locally in an encrypted vault.
- **Interoperability:** Uses a simplified version of the **BIDS-Physio** standard, allowing the user to export their history for professional clinical review without compromising their identity.
---
## 🔐 The "No-Trace" Guarantee

| Data Type | Storage Location | Retention | Access Level |
| :--- | :--- | :--- | :--- |
| **Raw Voice** | RAM only | Milliseconds | SAL only |
| **Raw HRV** | RAM only | Milliseconds | SAL only |
| **State Tensors** | Secure Sandbox | Session only | Acolyte |
| **Clinical Trends** | Encrypted Vault | User-defined | User Only |

---
## 🛠️ Implementation for Contributors
### 🔢 Tensor Conversion (The OpenMined Path)
All modules must emit data in **Encapsulated Tensor** format. A module cannot send a raw integer representing "Heart Rate". It must send a normalized, differentially private vector that the Acolyte's neural engine can interpret.
### 🔑 Key Management
The protocol utilizes the device's **Root of Trust**:
- **Android:** Keystore + OP-TEE.
- **Linux/Desktop:** TPM 2.0 / LUKS.
- **Keys:** Generated locally, never backed up to the cloud, and destroyed if the user invokes the "Protocol Wipe" command.
---
## 📊 Research Interoperability
To support the **Clinical Bridge**, the protocol allows for "Sovereign Research Contributions":
- Users can choose to share **Mathematical Gradients** (not data) with **Governance Nodes** (Universities).
- This uses **Federated Learning**, allowing the protocol to become smarter for everyone while the user's individual data remains on their own silicon.
---
> *"In the Cortex Protocol, your data is not an asset to be harvested. It is a biological signature that belongs only to you. We don't store your life; we help you navigate it."*
