# 🏗️ System Architecture: Cortex Protocol Framework
**Canonical Technical Reference — replaces INTENT-PROTOCOL.md**

This document is the single source of truth for the technical structure of the Cortex Protocol. It covers system layers, hardware topology, the intent-based interaction model, and the sovereignty loop. For the clinical evidence behind each design decision, see [CLINICAL-BRIDGE.md](../clinical/CLINICAL-BRIDGE.md) and [WHITE_PAPER.md](../clinical/WHITE_PAPER.md).

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
