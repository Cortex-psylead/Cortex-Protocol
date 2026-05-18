# 🏗️ System Architecture: Cortex Protocol Framework
**Canonical Technical Reference — replaces INTENT-PROTOCOL.md**

This document is the single source of truth for the technical structure of the Cortex Protocol. It covers system layers, hardware topology, the intent-based interaction model, and the sovereignty loop. For the clinical evidence behind each design decision, see [CLINICAL-BRIDGE.md](CLINICAL-BRIDGE.md) and [WHITE_PAPER.md](WHITE_PAPER.md).

---

## 🧭 Design Philosophy: Protocol, Not OS

Cortex is not a traditional Operating System. It is a **Sovereignty Abstraction Layer (SAL)**—a governance protocol that sits between hardware and the human, enforcing clinical and ethical constraints at the hardware level.

The user does not "open apps." The user declares an **Intent**. The Protocol delivers the **Result** while guaranteeing **Cognitive Sovereignty**.

Whether running on a mobile device, a high-end workstation, or a local edge server, the Acolyte orchestrates hardware resources (NPU, GPU, DSP, biometric sensors) in response to user intent, under the real-time supervision of cryptographically signed **Ethical Governance Nodes**.

---

## 🛰️ System Layers

The protocol is structured in four fundamental layers. Biometric and personal data never leave the device.

### Layer 1 — 🔩 Sovereignty Abstraction Layer (SAL): *"The Body"*

The hardware interface. Handles all physical I/O and enforces the mathematical privacy transformation.

**Responsibilities:**
- Interfaces with any hardware architecture (ARM, x86, RISC-V) without vendor lock-in.
- Runs Local Inference Units (NPU/GPU) 100% locally. No cloud dependency.
- Manages the **Biosensor Hub**: low-latency access to HRV, EEG, GSR, and environmental sensors.
- Executes the two-phase tensor transformation: clinical feature extraction → HMAC obfuscation.
- Enforces GPG signature verification of Clinical Capability Modules at load time.

### Layer 2 — 🔢 Mathematical Privacy Layer: *"The Filter"*

Implements **Differential Privacy** principles (OpenMined/PySyft-inspired) to ensure the Acolyte learns from *patterns* without ever accessing raw biometric *values*.

**Key operations:**
- Normalization of raw signals to physiological reference ranges.
- Hilbert transform envelope extraction for dimensionality reduction.
- HMAC-SHA256 obfuscation with ephemeral per-session salt.
- Tensor encapsulation: all physiological inputs are converted to anonymous mathematical tensors before leaving the SAL boundary.

**Privacy guarantee:** The Mathematical Privacy Layer ensures that even a compromised Acolyte cannot reconstruct the user's raw biometric state from the tensors it receives.

### Layer 3 — 🤖 Master Agent Core (The Acolyte): *"The Mind"*

The central AI agent. Built on local Small Language Models (SLMs) optimized for edge silicon.

**Responsibilities:**
- **Intent Orchestrator:** Parses user intent and allocates hardware resources without intermediate app layers. Compatible with local inference engines: Llama.cpp, ExecuTorch, Whisper.
- **Cognitive State Engine:** Analyzes anonymized tensors to classify mental load states (Flow, Stress, Overload) using the Polyvagal state mapping from the Clinical Bridge.
- **Ethical Sandbox:** Every Acolyte decision is cross-referenced against GPG-signed rulesets from Governance Nodes before hardware execution. If rulesets are missing or invalid, the capability module is blocked.

**What the Acolyte never sees:**
- Raw biometric values (EEG amplitude, HRV intervals, GSR).
- The session salt used for HMAC obfuscation.
- The Phase A clinical features before obfuscation.

### Layer 4 — 🖥️ Sovereign Neural Interface (SNI): *"The Senses"*

The adaptive user interface layer. Replaces static app grids with intent-driven, clinically-aware environments.

**Capabilities:**
- **Adaptive UX:** Visual complexity adjusts based on detected cognitive load state.
- **Sensory Buffer:** Hardware-level modulation of screen Hz, blue light temperature, and audio frequencies to maintain autonomic homeostasis.
- **Sovereign Kill-Switch:** The user can override any Protocol decision at any point. Human sovereignty is unconditional.

---

## 🔄 The Sovereignty Loop (Privacy by Design)

The full processing cycle for each biometric frame:

```
[User Intent / Biometric Sensor Input]
           ↓
[SAL: Sensor Certification Handshake]
    ↙ Rejected        ↘ Certified
[Block]          [Phase A: Clinical Feature Extraction]
                           ↓
                 [Clinical Bridge Validation]
                   ↙ Violation   ↘ Cleared
                [Block]     [Phase B: HMAC Obfuscation]
                                       ↓
                            [Acolyte: Tensor Processing]
                                       ↓
                         [CDI: Drift Detection Update]
                           ↙ Drift         ↘ Safe
                    [Block/Alert]     [Hardware Execution]
                                           ↓
                              [Result delivered to user]
```

**All processing is local. All data stays on the device.**

---

## 🧰 Technical Stack

| Component | Library / Tool | Purpose |
| :--- | :--- | :--- |
| **Local Inference** | Llama.cpp / ExecuTorch | High-performance local LLM/SLM execution on edge silicon |
| **EEG/Biometric Processing** | NumPy / MNE-Python | Signal normalization, Hilbert transform, feature extraction |
| **Audio (therapeutic)** | PipeWire / Oboe | Low-latency, universal audio orchestration |
| **Spatial Audio** | Resonance Audio / libmysofa | 3D sound field rendering for therapeutic use |
| **Cryptography** | Python `hmac`, `hashlib`, `secrets` | Session salt generation, HMAC-SHA256 tensor obfuscation |
| **Governance Signing** | GPG / OpenPGP | Digital signatures for Clinical Capability Modules |
| **Trusted Execution** | OP-TEE / TPM 2.0 | Secure local storage of manifests and user keys |
| **Privacy Layer** | OpenMined / PySyft (roadmap) | Federated learning for population-level CDI refinement |

---

## 🔐 Ethical Governance Mechanism

Governance Nodes do not merely audit documents — they control what the Acolyte can physically execute at runtime.

**Constitutional System Prompts:** Ethical constraints are loaded into the Acolyte's context as Constitutional Law before any intent processing begins.

**Signed Manifests:** Constraints are structured text files, validated and digitally signed by independent Governance Nodes (university faculties, professional associations).

**Hardware Enforcement:** The SAL verifies GPG signatures at module load time. If the signature is absent or invalid, the Protocol refuses to activate the capability module — regardless of Acolyte instructions.

**Annual Review Cycle:** Signed manifests are time-limited and require renewal after peer review. A manifest that has not been reviewed in 12 months is automatically downgraded to advisory-only status.

---

## 🛤️ Architecture Roadmap

| Milestone | Architecture Focus | Deliverable |
| :--- | :--- | :--- |
| **0 (current)** | SAL core, CDI, sensor certification | `cognitive_shield.py` — functional Python PoC |
| **1** | Legal audit trail, Judicial Kill Switch | GDPR-compliant session destruction with verifiable log |
| **2** | Acolyte SDK, real hardware integration | SDK for Muse / Emotiv / OpenBCI + REST-like intent API |
| **3** | Universal SAL, multi-architecture | ARM/x86/RISC-V abstraction layer; TEE integration |
| **4 (2030+)** | Federated Governance Network | University node network; federated CDI refinement |

---

## 📎 Related Documents

- [WHITE_PAPER.md](WHITE_PAPER.md) — Clinical and scientific specification with full references
- [MODULE-ISOLATION.md](MODULE-ISOLATION.md) — Zero-trust sandboxing between capability modules
- [USER-DATA-MODEL.md](USER-DATA-MODEL.md) — Data layers and No-Trace guarantee
- [CLINICAL-BRIDGE.md](CLINICAL-BRIDGE.md) — Evidence-based clinical protocols and hardware margins
- [GOVERNANCE.md](GOVERNANCE.md) — Governance roles and validation loop

---

> *"The hardware is yours. The protocol gives it back to you. The ethics make sure it stays that way."*
> 
