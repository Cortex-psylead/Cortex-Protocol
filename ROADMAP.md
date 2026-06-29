# 🛣️ Cortex Protocol — Development Roadmap
**From Proof of Concept to Universal Neuro-Privacy Standard**

> **Current Status: Milestone 0 — Locked ✅ | Milestone 1 — In Progress 🔍**
> The Cognitive Shield is implemented, documented, and CI/CD-validated. The protocol is an open RFC with an active contributor community and the first hardware adapter (BrainFlow) merged.

---

## 🎯 Milestone 0: The Cognitive Shield
**Status: ✅ Complete | Period: April–June 2026**

The foundational Proof of Concept demonstrating that a clinically governed, mathematically verifiable sovereignty layer between biometric sensors and AI agents is technically feasible.

**Completed deliverables:**
- `src/sal/cognitive_shield.py` — functional SAL implementation with dual CDI detection
- Full documentation suite (18 documents) covering architecture, clinical protocols, governance, and legal framework
- GPL v3 licensing establishing the protocol as permanent open-source infrastructure
- Bilingual community framework (English documentation, Spanish community language)
- Hardened CI/CD stack: Zero-Trust workflows, SHA-pinned actions, SAL Boundary Guard with 5 architectural invariants, CodeQL semantic analysis, Bandit SAST, Dependabot supply chain monitoring
- GitHub Pages public documentation site: cortex-psylead.github.io/Cortex-Protocol

**Success criteria met:**
- [x] Two-phase tensor transformation (Phase A clinical + Phase B HMAC obfuscation)
- [x] Sensor certification handshake with hardware quality thresholds
- [x] CDI dual-threshold detection (hard violations + Z-score baseline)
- [x] Context-manager ephemeral memory (deterministic zeroing)
- [x] Clinical Bridge with Polyvagal Theory-grounded thresholds and bibliographic basis
- [x] Test suite: 23 tests, 23 passing — covering sensor certification, tensor transformation, clinical bridge, CDI thresholds, consent lifecycle, and session destruction
- [x] Zero-Trust CI/CD with branch protection, CODEOWNERS, and mandatory PR review
- [x] SAL Boundary Guard: 5 protocol invariants enforced on every commit

---

## ⚙️ Milestone 1: Clinical Validation & First Governance Node
**Status: 🔍 In progress | Target: Q4 2026 – Q1 2027**

The transition from simulated signals to validated clinical data. This milestone establishes the first institutional partnership and produces the first peer-reviewed output.

**Progress to date:**
- BrainFlow sensor adapter (PR #7) merged — first external contribution by @mayoka0
- Hardware abstraction layer (`BiometricSensorAdapter`) specification underway (Issue #4)
- P2P UDP transport layer specification opened (Issue #16)

**Objectives:**

**Clinical:**
- Partner with an independent university research center to run a controlled study validating CDI thresholds against real EEG hardware (OpenBCI or Muse 2) with a clinical population.
- Produce a validation dataset comparing CDI readings against established HRV metrics (RMSSD, LF/HF ratio) to confirm the Coherency Index's clinical correspondence.
- Publish first peer-reviewed paper: *"A hardware-enforced sovereignty layer for neurophysiological data in clinical AI settings."*

**Technical:**
- Complete `BiometricSensorAdapter` abstract interface enabling plug-in support for real hardware.
- Extend BrainFlow SDK integration to support OpenBCI Cyton, Muse 2, and Neurosity Crown out of the box.
- Implement the **Compliance-Driven Data Erasure Protocol** — legally auditable session destruction log, compliant with GDPR Article 17 (Right to Erasure). Also referred to as the Judicial Kill Switch in internal architecture documentation.
- Add CDI reset protocol with clinician-authorization flow (resolves current permanent-block limitation).
- Implement P2P UDP transport for the DeSci Channel (Issue #16).
- Resolve ECDH session key persistence — wrap session_key in SecureKeyBuffer (Issue #3).

**Governance:**
- Constitute the first **Independent & Decentralized Governance Node**: a faculty or professional association that issues a signed Clinical Capability Module. Governance Nodes are structurally independent from the Protocol Steward — no single entity, government, or corporation can capture the standard.
- Establish the GPG key registry for White Branch members, making clinical approval cryptographically verifiable in git history.
- Publish the CCM signing specification so any institution globally can become a Governance Node.

**Success criteria:**
- [ ] CDI thresholds validated against real HRV data from ≥ 20 participants
- [ ] At least 1 independent Governance Node actively signing CCMs
- [ ] BrainFlow integration working with ≥ 2 real sensor models
- [ ] Compliance-Driven Data Erasure Protocol passing legal review in ≥ 1 jurisdiction (Colombia/EU)
- [ ] 1 peer-reviewed submission

---

## 🛡️ Milestone 2: The Acolyte SDK
**Status: ⏳ Not started | Target: Q1 2027 – Q1 2028**

The protocol becomes adoptable by external developers. The Acolyte SDK is the mechanism by which therapeutic AI developers can build Cortex-Certified applications.

**Objectives:**

**SDK:**
- Release `cortex-sdk` Python package (pip-installable) with stable public API.
- Define and publish the Cortex Certification Specification: the technical requirements an AI agent must meet to be designated a Certified Acolyte.
- Implement the Intent API: a clean interface for applications to declare user intent and receive a clinically validated interaction context.

**Clinical:**
- Develop the first Cortex-Certified Acolyte reference implementation: a therapeutic support agent for anxiety management using validated CBT and polyvagal regulation prompts.
- Establish the CCM library: a curated, peer-reviewed collection of Clinical Capability Modules available to SDK users.

**Platform:**
- Publish the protocol as a formal RFC (Request for Comments) inviting review from the international neurotechnology and AI ethics communities.
- Submit the SAL specification to IEEE for consideration as a contributing standard to P2510 (Quality of Data for Neural Interface).

**Success criteria:**
- [ ] `cortex-sdk` published on PyPI with semantic versioning
- [ ] Cortex Certification Specification v1.0 released
- [ ] ≥ 1 reference Certified Acolyte implementation
- [ ] ≥ 3 independent Governance Nodes active across different jurisdictions
- [ ] RFC published and open for community comment
- [ ] IEEE P2510 submission or equivalent standards body engagement

---

## 🌐 Milestone 3: Universal Sovereign Standard
**Status: ⏳ Not started | Target: Q1 2028+**

The Cortex Protocol transitions from a project to a standard. Governance is distributed across an international network of independent nodes. The protocol is hardware-manufacturer-adoptable.

**Objectives:**

**Standard:**
- Release Cortex Protocol Specification v1.0 as a stable, versioned standard document with a formal change management process.
- Establish the Global Governance Council: a multi-institutional body with representatives from ≥ 5 countries providing consensus-based protocol updates. No single country, institution, or entity holds veto power.
- Define the "Cortex-Ready" hardware certification: a specification that sensor and device manufacturers can implement to indicate their products are compatible with the SAL.

**Federated Learning:**
- Implement privacy-preserving federated CDI refinement: Governance Nodes aggregate gradient updates (not raw data) from consenting users to improve baseline models population-wide.
- Publish federated learning architecture specification ensuring no raw biometric data ever leaves individual devices.

**Regulatory:**
- Engage with EU AI Act implementation bodies to position the SAL specification as a recognized technical measure for high-risk AI compliance.
- Support neuro-rights legislative efforts in Latin America with technical documentation establishing the protocol as an implementation reference.

**Success criteria:**
- [ ] Cortex Protocol Specification v1.0 published under formal standards process
- [ ] ≥ 5 countries represented in Governance Council
- [ ] ≥ 1 hardware manufacturer with "Cortex-Ready" certification
- [ ] Federated CDI refinement operational across ≥ 3 Governance Nodes
- [ ] Recognized by ≥ 1 national or international regulatory body

---

## 🤝 How to Contribute Now

The fastest path to Milestone 1 runs through three parallel tracks:

**Clinical Track** — If you are a psychologist, neuroscientist, or clinical researcher:
Open an Issue tagged `[Clinical-Track]`. We need collaborators for the CDI validation study. Your institution can become the first independent Governance Node.

**Technical Track** — If you are an engineer (Python, DSP, hardware):
Open an Issue tagged `[Technical-Track]`. Priority contributions: BrainFlow sensor adapter extension, CDI reset protocol, Compliance-Driven Data Erasure Protocol, P2P UDP transport.

**Standards Track** — If you work in AI ethics, regulatory affairs, or standards bodies:
Open an Issue tagged `[Standards-Track]`. We are building toward IEEE and ISO engagement and need reviewers for the RFC draft.

---

> *"A roadmap is not a promise of a product. It is a statement of direction, maintained honestly, updated as reality demands, and always subordinate to the clinical mandate."*
