<div align="center">
  
# 🧠 Cortex Protocol
### An Open Standard for Neurophysiological Data Sovereignty in Human-AI Interaction
[![Milestone 0: Locked](https://img.shields.io/badge/Milestone_0-Locked_✅-brightgreen)](docs/ROADMAP.md)
[![Standard: RFC v1.1-draft](https://img.shields.io/badge/Standard-RFC_v1.1--draft-orange)](docs/governance/STANDARD.md)
[![Layer 1: Specification](https://img.shields.io/badge/Layer_1_(Rust/C)-Specification-blue)](src/layer1/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue)](LICENSE)
[![Clinical Authority: White Branch](https://img.shields.io/badge/Clinical_Authority-White_Branch_v1.2-purple)](docs/governance/GOVERNANCE.md)
**"The hardware is yours. The protocol gives it back to you. The ethics make sure it stays that way."**
[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Repository Map](#-repository-map) · [Contribute](#-contributing)

</div>

---
## English

## What is Cortex Protocol?
Cortex Protocol is an **open, royalty-free technical standard** for protecting neurophysiological data sovereignty in environments where external AI agents interact with human biometric streams. 
Think of it as what **HTTPS did for web traffic**, engineered specifically for the human nervous system and neuro-rights enforcement.
It operates as a **Sovereignty Abstraction Layer (SAL)**—a local middleware that executes between neural/biometric hardware sensors and third-party large language models or autonomous agents. It guarantees that:
1. **Absolute Processing Locality:** Raw biological signals never leave the edge device; raw frames are completely destroyed from memory immediately after mathematical feature extraction.
2. **Lossy Feature Projection:** AI agents receive only anonymized mathematical manifolds or restricted semantic tokens—never raw physiological timeseries.
3. **Decentralized Clinical Gating:** Safety limits and the **Clinical Drift Index (CDI)** are governed by independent clinical institutions (White Branch) using peer-reviewed cryptographic snapshots, completely isolated from corporate commercial incentives.

## Español

## ¿Qué es Cortex Protocol?
Cortex Protocol es un estándar técnico abierto y libre de regalías diseñado para garantizar la soberanía de los datos neurofisiológicos en entornos donde agentes externos de Inteligencia Artificial interactúan con flujos biométricos humanos.
Piénsalo como lo que HTTPS hizo por el tráfico web, pero diseñado específicamente para el sistema nervioso humano y la protección de los neuroderechos.
Opera como una Capa de Abstracción de Soberanía (SAL): un middleware local que se ejecuta entre los sensores de hardware neuronales/biométricos y los modelos de lenguaje o agentes autónomos de terceros. El protocolo garantiza tres pilares fundamentales:
1. **Pilares Fundamentales de Soberanía**
Localidad Absoluta del Procesamiento: Las señales biológicas crudas nunca salen del dispositivo periférico (edge device). Los marcos de datos puros (raw frames) se destruyen por completo de la memoria RAM inmediatamente después de la extracción matemática de características.
2. **Proyección de Características con Pérdida (Lossy Feature Projection):** Los agentes de IA reciben únicamente variedades (manifolds) matemáticas anonimizadas o tokens semánticos restringidos, nunca las series temporales fisiológicas crudas. Esto hace imposible la reconstrucción inversa de la señal original.
3. **Regulación Clínica Descentralizada (Clinical Gating):** Los límites de seguridad y el Índice de Deriva Clínica (CDI) están gobernados por instituciones clínicas independientes (White Branch) mediante instantáneas criptográficas revisadas por pares, quedando completamente aislados de cualquier incentivo comercial corporativo.

---

## 🚀 Quick Start
### Installation
Clone the repository and install the baseline psychophysiological dependency stack:
```bash
git clone [https://github.com/Cortex-psylead/Cortex-Protocol](https://github.com/Cortex-psylead/Cortex-Protocol)
cd Cortex-Protocol
pip install -r requirements.txt
```
### Execution
Run the local Sovereignty Abstraction Layer integration demo to observe real-time baseline calibration, simulated sympathetic arousal escalation, and automated cryptographic zeroization loops:
```bash
python src/sal/cognitive_shield_v2.py
```
To run the deterministic test suite verifying the multi-state biometric engine:
```bash
python tests/test_cognitive_shield.py
# Expected output: 23 tests, 23 passed
```
## 🏗️ Architecture
The protocol decouples high-level telemetry routing from bare-metal execution across **three symmetrical implementation layers**:
```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Python SAL (Milestone 0 ✅ / Milestone 1 🔍)     │
│  Functional Architecture Runtime. Includes the Dual-Channel │
│  Sovereign Telemetry Layer (STL) for DeSci and Clinical.     │
│  src/sal/  src/ethos/  src/limes/  src/keros/               │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — ZK-Proofs & Cryptographic Data Customs (Spec 📐)  │
│  Circom range-check circuits, JSON validation schemas,      │
│  and constant-time Rust data-reduction mediators.          │
│  src/layer2/                                                │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — Bare-Metal Secure Firmware (Specification 📐)     │
│  ARM TrustZone EL1-S isolation, C/Rust/ASM execution.        │
│  Target Hardware: ARMv8.5-A architectures (e.g., Snapdragon) │
│  src/layer1/                                                │
└─────────────────────────────────────────────────────────────┘
```
### The Pentagon (The Five Sovereign Modules)
The protocol achieves runtime trust by binding five specialized cryptographic and mathematical frameworks together:

| Module | Core Function | Current Runtime Status |
| :--- | :--- | :--- |
| **CORTEX** | Outbound privacy management via the **Clinical Drift Index (CDI)** and Hilbert analytical envelope extraction ([\mu_A, \sigma^2_A, S_A, K_A, H_{sp}]). | ✅ Layer 3 PoC Operational |
| **LIMES** | Liveness verification. Analyzes raw physical telemetry for biological 1/f spectral pink noise to neutralize synthetic replay attacks. | ✅ Layer 3 PoC Operational |
| **ETHOS** | Physiologically-grounded dynamic consent engine. Upgrades or revokes processing privileges based on immediate cognitive capacity. | ✅ Layer 3 PoC Operational |
| **KEROS** | Hardware attestation. Signs sensor data hashes and session states using local TPM 2.0 primitives and Secure Enclaves. | 📐 Technical Specification |
| **LOGOS** | Cognitive integrity monitoring. Detects adversarial or manipulative semantic patterns targeted at the user's working memory. | ⏳ Planned for Milestone 2 |

## 📁 Repository Map
```
Cortex-Protocol/
│
├── src/
│   ├── sal/                    # Layer 3: Sovereignty Abstraction Layer
│   │   ├── cognitive_shield_v2.py   # ← CORE ENTRY POINT: Pipeline coordinator
│   │   ├── state_buffer.py          # BiometricStateMachine (asynchronous state tracking)
│   │   └── telemetry_router.py      # Dual-channel STL (Anonymized DeSci + E2EE Clinical)
│   │
│   ├── ethos/                  # ETHOS: Dynamic consent engine & scope manager
│   │   └── ethos_consent.py
│   ├── limes/                  # LIMES: Human liveness proof via spectral entropy
│   │   └── limes_proof.py
│   ├── keros/                  # KEROS: Hardware attestation framework
│   │   └── keros_seal.py
│   ├── governance/             # Policy snapshot validator (GPG ledger verification)
│   │   └── policy_validator.py
│   │
│   ├── layer1/                 # Layer 1: Bare-metal firmware specification
│   │   ├── c/
│   │   │   ├── keros_types.h        # Secure Enclave state registers
│   │   │   ├── biometric_filter.c   # Wavelet decomposition & noise filtering
│   │   │   └── keros_core.c         # Fast Interrupt Request (FIQ) isolation logic
│   │   ├── rust/
│   │   │   ├── matrix_inspector.rs  # Rust native Shannon entropy execution
│   │   │   ├── agora_diff_privacy.rs # Constant-time Laplace DP mechanism
│   │   │   └── Cargo.toml
│   │   ├── asm/
│   │   │   └── blind_switch.s       # Constant-time contextual dispatch (AArch64)
│   │   └── linker/
│   │       └── keros_secure_enclave.ld # TrustZone physical memory map
│   │
│   └── layer2/                 # Layer 2: ZKP circuits & data customs
│       ├── circom/
│       │   └── mvd_range_check.circom   # Compilable Mean Vector Distance verification
│       └── json_schemas/
│           ├── acolyte_manifest.json    # External AI agent metadata schema
│           └── white_branch_snapshot.json # Signed clinical threshold snapshot
│
├── tests/                      # Deterministic validation suite (Milestone 0 baseline)
├── docs/
│   ├── architecture/           # ARCHITECTURE.md, ARCHITECTURE-ASYNC.md
│   ├── clinical/               # ROADMAP-CLINICAL.md, WHITE_PAPER.md
│   ├── governance/             # GOVERNANCE.md, STANDARD.md
│   └── legal/                  # CONSTITUTION.md, DISCLAIMER.md
│
├── requirements.txt            # Operational dependencies (NumPy, SciPy, Cryptography)
├── SECURITY.md                 # Threat model vectors & disclosure parameters
├── CONTRIBUTING.md             # Contribution pipelines for clinical and technical tracks
└── CODE_OF_CONDUCT.md
```
## 🗺️ Roadmap

| Milestone | Target Status | Primary Objective |
| :--- | :--- | :--- |
| **M0: Cognitive Shield** | ✅ Complete | Functional Python PoC, local state containment, structural architectural specifications. |
| **M1: Clinical Validation** | 🔍 In Progress | Physical hardware streaming validation, deployment of the first academic Governance Node network. |
| **M2: Acolyte SDK** | ⏳ Planned | Production-ready native Rust implementation of Layer 1, pip-installable integration bindings for AI frameworks. |
| **M3: Universal Standard** | ⏳ Planned | International Governance Council expansion, IEEE P2510 mapping, and global regulatory compliance frameworks. |

## 🤝 Contributing
The protocol is structured as a collaborative open standard. We welcome three primary engineering and scientific pathways:
 * **🧠 Clinical Researchers:** Help validate and calibrate CDI thresholds against empirical EEG, ECG, and HRV timeseries. Join or form a decentralized Governance Node. (Tag issues with [Clinical-Track]).
 * **⚙️ Core Engineers:** Assist in porting Layer 1 modules to bare-metal architectures, integrate embedded TPM 2.0 communication protocols, or expand native Rust components. (Tag issues with [Technical-Track]).
 * **📋 Standards & Policy Specialists:** Lead alignment initiatives with the EU AI Act, regional neuro-rights legislations, and international data-minimization frameworks. (Tag issues with [Standards-Track]).
Please consult CONTRIBUTING.md for step-by-step branching and GPG signing guidelines.
## ⚖️ License
This project is licensed under the **GNU LGPL v3** / **GNU GPL v3** copyleft framework. See LICENSE for full details. The Cortex Protocol standard is, and will remain in perpetuity, royalty-free, un-copyable, and open. No commercial entity may enclose its operational parameters.
<div align="center">
*"The standard does not need to be everywhere. It needs to make everywhere safer."*

</div>
