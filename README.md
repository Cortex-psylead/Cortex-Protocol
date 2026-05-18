# 🧠 Cortex Protocol
### An Open Standard for Neurophysiological Data Sovereignty in Human-AI Interaction

[![Milestone 0: Locked](https://img.shields.io/badge/Milestone-0--Locked-green.svg)](#-milestone-0-the-cognitive-shield)
[![Standard: RFC](https://img.shields.io/badge/Standard-RFC%20v0.1-orange.svg)](STANDARD.md)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Branch: Clinical/White](https://img.shields.io/badge/Branch-White%20(Clinical)-blue.svg)](GOVERNANCE.md)

The **Cortex Protocol** is an open, royalty-free technical standard that defines the minimum requirements for protecting neurophysiological data sovereignty in any system where an AI agent interacts with human biometric data.

It is the technical layer that makes privacy and clinical safety the architectural default — not a policy promise.

Think of it as what HTTPS did for web security, applied to the human nervous system.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Cortex-psylead/Cortex-OS-protocol
cd Cortex-OS-protocol
pip install -r requirements.txt
python src/sal/cognitive_shield.py
```

The demo runs in under 60 seconds and produces `cortex_demo.png` — a visual output of the full protection pipeline showing baseline establishment and CDI block event.

To run the test suite:

```bash
python tests/test_cognitive_shield.py
```

---

## 📐 What the Standard Defines

The Cortex Protocol Standard ([STANDARD.md](STANDARD.md)) specifies three mandatory components for any compliant implementation:

**The Sovereignty Abstraction Layer (SAL):** Raw neurophysiological data never leaves the device. Two-phase transformation ensures the AI agent receives only an anonymized, HMAC-obfuscated tensor — never raw values.

**The Clinical Bridge:** Every biometric frame is validated against Polyvagal Theory-grounded thresholds before the AI processes it. Thresholds are defined exclusively by clinical professionals and backed by peer-reviewed literature.

**The Clinical Drift Index (CDI):** Temporal monitoring across sessions using dual-threshold detection (absolute clinical limits + personal Z-score baseline) to detect both acute and chronic pathological drift induced by AI interaction.

Three conformance levels are defined: **Core Compliant** (all SHALL requirements), **Clinically Validated** (plus real-hardware clinical validation), and **Certified Standard** (plus multi-institutional governance and regulatory recognition).

---

## 🛡️ Milestone 0: The Cognitive Shield (Complete)

The reference implementation demonstrating that the standard is technically feasible. The Sovereignty Abstraction Layer (SAL) is fully implemented and validated.

**Key Technical Features:**

- **Sensor Hardening:** Hardware certification handshake — sensors not meeting clinical quality thresholds (SNR ≥ 30 dB, ≥ 12-bit resolution) are rejected before data ingestion.
- **Two-Phase Tensor Transformation:** Phase A extracts 5 clinical features (interpretable, validated by Clinical Bridge). Phase B applies HMAC-SHA256 obfuscation. The AI receives only Phase B output.
- **Clinical Drift Index:** Dual detection — absolute clinical threshold (hard violations) + personal Z-score baseline (soft violations). Blocks sessions when pathological drift is detected.
- **Secure Ephemeral Memory:** Context manager pattern guarantees deterministic memory zeroing — not dependent on garbage collection.
- **Test Suite:** 7 test classes, 18 cases covering all core components.

> Full implementation: `src/sal/cognitive_shield.py`
> Architecture decisions: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🗂️ Full Document Index

### Standard & Reference

| Document | Purpose |
| :--- | :--- |
| [STANDARD.md](STANDARD.md) | **The standard specification** — SHALL/SHOULD/MAY requirements for compliant implementations |
| [WHITE_PAPER.md](WHITE_PAPER.md) | Full technical and clinical specification with bibliographic basis |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers, hardware topology, and sovereignty loop |

### Clinical & Scientific Foundation

| Document | Purpose |
| :--- | :--- |
| [CLINICAL-BRIDGE.md](CLINICAL-BRIDGE.md) | Evidence-based clinical protocols and hardware safety margins |
| [MODULE-ISOLATION.md](MODULE-ISOLATION.md) | Zero-trust sandboxing and module isolation protocol |
| [USER-DATA-MODEL.md](USER-DATA-MODEL.md) | Data layers, tensor model, and No-Trace guarantee |

### Governance & Legal

| Document | Purpose |
| :--- | :--- |
| [GOVERNANCE.md](GOVERNANCE.md) | Governance roles, validation loop, anti-capture provisions |
| [GOVERNANCE-BASE.md](GOVERNANCE-BASE.md) | Constitutional law — unalterable foundational principles |
| [SECURITY.md](SECURITY.md) | Threat model, cryptographic governance, vulnerability reporting |
| [DISCLAIMER.md](DISCLAIMER.md) | Legal framework, safety notice, scope |

### Community

| Document | Purpose |
| :--- | :--- |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor profiles, validation loop, how to join |
| [ROADMAP.md](ROADMAP.md) | Milestones from M0 to Universal Standard |
| [LEXICON.md](LEXICON.md) | Bilingual glossary — 20+ operational definitions |
| [VISION_2045.md](VISION_2045.md) | Long-term vision and regulatory context |
| [MANIFESTO.md](MANIFESTO.md) | Ethical declaration and statement of neuro-rights |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |

---

## 👥 Two Entry Points

**If you are a clinician, neuroscientist, or researcher:**
Start with [CLINICAL-BRIDGE.md](CLINICAL-BRIDGE.md) and [WHITE_PAPER.md](WHITE_PAPER.md). These documents translate the protocol's technical decisions into the clinical frameworks you work with. If your institution wants to become a Governance Node, open an Issue tagged `[Governance-Node-Application]`.

**If you are a developer or engineer:**
Start with [STANDARD.md](STANDARD.md) and `src/sal/cognitive_shield.py`. The standard defines what a compliant implementation must do. The reference code shows one way to do it. To contribute, open an Issue tagged `[Technical-Track]`.

---

## 🗺️ Roadmap

| Milestone | Status | Objective |
| :--- | :--- | :--- |
| **0: Cognitive Shield** | ✅ Complete | Reference implementation, full documentation, test suite |
| **1: Clinical Validation** | 🔍 Seeking collaborators | Real-hardware CDI validation, first Governance Node, peer-reviewed publication |
| **2: Acolyte SDK** | ⏳ Not started | pip-installable SDK, Certified Acolyte specification, IEEE standards engagement |
| **3: Universal Standard** | ⏳ Not started | Global Governance Council, hardware manufacturer certification, regulatory recognition |

---

## 🤝 Contributing

We need three types of collaborators right now:

**Clinical researchers** to validate CDI thresholds against real EEG data and form the first Governance Node. Open an Issue tagged `[Clinical-Track]`.

**Engineers** to build the BrainFlow sensor adapter and Judicial Kill Switch. Open an Issue tagged `[Technical-Track]`.

**Standards and regulatory specialists** to review the RFC and engage with IEEE P2510 and EU AI Act implementation bodies. Open an Issue tagged `[Standards-Track]`.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution process.

---

## ⚖️ License

**GNU GPL v3** — see [LICENSE](LICENSE).

The protocol is permanently open. Any implementation of this standard is free to use, modify, and distribute under the same terms. No entity can make this standard proprietary.

---

*"The standard does not need to be everywhere. It needs to make everywhere safer."*
