<div align="center">

# 🧠 Cortex Protocol

### An Open Standard for Neurophysiological Data Sovereignty in Human-AI Interaction

[![Milestone 0: Locked](https://img.shields.io/badge/Milestone_0-Locked_✅-brightgreen)](docs/ROADMAP.md)
[![Standard: RFC v0.2](https://img.shields.io/badge/Standard-RFC_v0.2-orange)](docs/governance/STANDARD.md)
[![Layer 1: Specification](https://img.shields.io/badge/Layer_1_(Rust/C)-Specification-blue)](src/layer1/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue)](LICENSE)
[![White Branch](https://img.shields.io/badge/Clinical_Authority-White_Branch-purple)](docs/governance/GOVERNANCE.md)

**"The hardware is yours. The protocol gives it back to you. The ethics make sure it stays that way."**

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Repository Map](#-repository-map) · [Contribute](#-contributing)

</div>

---

## What is Cortex Protocol?

Cortex Protocol is an **open, royalty-free technical standard** for protecting neurophysiological data sovereignty in any system where an AI agent interacts with human biometric data.

Think of it as what **HTTPS did for web security**, applied to the human nervous system.

It is **not an operating system**. It is a sovereignty abstraction layer — a governance protocol that enforces clinical and privacy constraints at the hardware level, ensuring that:

1. **Raw biometric data never leaves your device** — all processing is local.
2. **AI agents receive only anonymized tensors** — never raw physiological values.
3. **Clinical safety thresholds are set by clinicians** — backed by peer-reviewed literature, cryptographically signed, and hardware-enforced.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Cortex-psylead/Cortex-Protocol
cd Cortex-Protocol
pip install -r requirements.txt
python src/sal/cognitive_shield_v2.py
```

The demo runs in under 60 seconds, showing baseline establishment, CDI escalation, and automatic session protection.

To run the test suite:

```bash
python tests/test_cognitive_shield.py
# Expected: 23 tests, 23 passed
```

---

## 🏗️ Architecture

The protocol is structured in **three implementation layers** that correspond to increasing hardware proximity:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Python SAL (Milestone 0 ✅)                       │
│  Functional PoC. CORTEX + LIMES + ETHOS integrated.         │
│  src/sal/  src/ethos/  src/limes/  src/keros/               │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — Zero-Knowledge Proofs & Data Customs (Spec 📐)    │
│  Circom circuits, JSON schemas, Rust mediator.              │
│  src/layer2/                                                │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — Bare-Metal Firmware (Specification 📐)            │
│  ARM TrustZone EL1-S, C/Rust/ASM.                           │
│  Target: ARMv8.5-A (Snapdragon 8 Gen 1)                     │
│  src/layer1/                                                │
└─────────────────────────────────────────────────────────────┘
```

### The Pentagon (Five Sovereign Modules)

| Module | Function | Status |
|--------|----------|--------|
| **CORTEX** | Biometric privacy (SAL + CDI + Clinical Bridge) | ✅ Python PoC |
| **LIMES** | Proof of human liveness (entropy validation) | ✅ Python PoC |
| **ETHOS** | Dynamic consent (physiologically-grounded) | ✅ Python PoC |
| **KEROS** | Hardware attestation (TPM 2.0 / TrustZone) | 📐 Specification |
| **LOGOS** | Cognitive integrity monitoring | 📐 Planned M2 |

**Full technical specification:** [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)  
**Async pipeline design:** [docs/architecture/ARCHITECTURE-ASYNC.md](docs/architecture/ARCHITECTURE-ASYNC.md)

---

## 📁 Repository Map

```
Cortex-Protocol/
│
├── src/
│   ├── sal/                    # Layer 3: Sovereignty Abstraction Layer (Python)
│   │   ├── cognitive_shield_v2.py   # ← START HERE: full SAL integration
│   │   ├── state_buffer.py          # BiometricStateMachine (async-ready)
│   │   └── telemetry_router.py      # Dual-channel STL (DeSci + Clinical)
│   │
│   ├── ethos/                  # ETHOS: Dynamic consent engine
│   │   └── ethos_consent.py
│   ├── limes/                  # LIMES: Human liveness proof
│   │   └── limes_proof.py
│   ├── keros/                  # KEROS: Hardware attestation
│   │   └── keros_seal.py
│   ├── governance/             # Policy snapshot validator
│   │   └── policy_validator.py
│   │
│   ├── layer1/                 # Layer 1: Bare-metal firmware (SPECIFICATION)
│   │   ├── c/
│   │   │   ├── keros_types.h        # Secure enclave data structures
│   │   │   ├── biometric_filter.c   # Phi operator: Db2 wavelet + Box-Muller
│   │   │   └── keros_core.c         # FIQ handler + Hi-Z isolation sequence
│   │   ├── rust/
│   │   │   ├── matrix_inspector.rs  # LIMES: Shannon entropy validation
│   │   │   ├── agora_diff_privacy.rs # LDP: Laplace mechanism (constant-time)
│   │   │   └── Cargo.toml
│   │   ├── asm/
│   │   │   └── blind_switch.s       # Constant-time secure dispatch (AArch64)
│   │   └── linker/
│   │       └── keros_secure_enclave.ld  # TrustZone memory map
│   │
│   └── layer2/                 # Layer 2: ZKP circuits & data customs
│       ├── circom/
│       │   └── mvd_range_check.circom   # MVD range proof (compilable)
│       └── json_schemas/
│           ├── acolyte_manifest.json    # Acolyte request schema
│           └── white_branch_snapshot.json # Governance snapshot schema
│
├── tests/                      # Test suite (23 tests, Milestone 0)
├── docs/
│   ├── architecture/           # ARCHITECTURE.md, ARCHITECTURE-ASYNC.md
│   ├── clinical/               # WHITE_PAPER.md, CLINICAL-BRIDGE.md
│   ├── governance/             # GOVERNANCE.md, STANDARD.md
│   └── legal/                  # CONSTITUTION.md, DISCLAIMER.md
│
├── requirements.txt            # Python deps: numpy, scipy, cryptography
├── SECURITY.md                 # Threat model + vulnerability reporting
├── CONTRIBUTING.md             # How to join (Clinical / Technical / Standards)
└── CODE_OF_CONDUCT.md
```

---

## 🗺️ Roadmap

| Milestone | Status | Objective |
|-----------|--------|-----------|
| **M0: Cognitive Shield** | ✅ Complete | Python PoC, 23 tests, full documentation |
| **M1: Clinical Validation** | 🔍 Seeking partners | Real-hardware CDI validation, first Governance Node |
| **M2: Acolyte SDK** | ⏳ Not started | pip-installable SDK, Rust Layer 1 on real hardware |
| **M3: Universal Standard** | ⏳ Not started | Global Governance Council, regulatory recognition |

**Full roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)

---

## 🤝 Contributing

We need three types of collaborators:

**🧠 Clinical researchers** — Validate CDI thresholds with real EEG/HRV data. Become the first Governance Node. Open an Issue tagged `[Clinical-Track]`.

**⚙️ Engineers** — Build the BrainFlow adapter, integrate TPM 2.0, port Layer 1 to real hardware. Open an Issue tagged `[Technical-Track]`.

**📋 Standards specialists** — IEEE P2510 engagement, EU AI Act compliance review. Open an Issue tagged `[Standards-Track]`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.

---

## ⚖️ License

**GNU GPL v3** — see [LICENSE](LICENSE). Permanently open. No entity can make this standard proprietary.

---

<div align="center">

*"The standard does not need to be everywhere. It needs to make everywhere safer."*

</div>
