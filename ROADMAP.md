# 🛣️ Cortex Protocol — Development Roadmap
**From Proof of Concept to Universal Neuro-Privacy Standard**

> **Current Status: Milestone 0 — Locked ✅**
> The Cognitive Shield is implemented and documented. The protocol is now an open RFC seeking clinical validation partners and technical contributors.

---

## 🎯 Milestone 0: The Cognitive Shield
**Status: ✅ Complete | Period: 2024–2025**

The foundational Proof of Concept demonstrating that a clinically governed, mathematically verifiable sovereignty layer between biometric sensors and AI agents is technically feasible.

**Completed deliverables:**
- `src/sal/cognitive_shield.py` — functional SAL implementation with dual CDI detection
- Full documentation suite (18 documents) covering architecture, clinical protocols, governance, and legal framework
- GPL v3 licensing establishing the protocol as permanent open-source infrastructure
- Bilingual community framework (English documentation, Spanish community language)

**Success criteria met:**
- [x] Two-phase tensor transformation (Phase A clinical + Phase B HMAC obfuscation)
- [x] Sensor certification handshake with hardware quality thresholds
- [x] CDI dual-threshold detection (hard violations + Z-score baseline)
- [x] Context-manager ephemeral memory (deterministic zeroing)
- [x] Clinical Bridge with Polyvagal Theory-grounded thresholds and bibliographic basis
- [x] Test suite covering 7 test classes and 18 cases

---

## ⚙️ Milestone 1: Clinical Validation & First Governance Node
**Status: 🔍 Seeking collaborators | Target: 12–18 months post-M0**

The transition from simulated signals to validated clinical data. This milestone establishes the first institutional partnership and produces the first peer-reviewed output.

**Objectives:**

**Clinical:**
- Partner with a university research center (target: Universidad Santiago de Cali, Colombia) to run a controlled study validating CDI thresholds against real EEG hardware (OpenBCI or Muse 2) with a clinical population.
- Produce a validation dataset comparing CDI readings against established HRV metrics (RMSSD, LF/HF ratio) to confirm the Coherency Index's clinical correspondence.
- Publish first peer-reviewed paper: *"A hardware-enforced sovereignty layer for neurophysiological data in clinical AI settings."*

**Technical:**
- Implement `BiometricSensorAdapter` abstract interface enabling plug-in support for real hardware.
- Integrate BrainFlow SDK to support OpenBCI Cyton, Muse 2, and Neurosity Crown out of the box.
- Implement the Judicial Kill Switch with legally auditable session destruction log (GDPR Article 17 compliant).
- Add CDI reset protocol with clinician-authorization flow (resolves current permanent-block limitation).

**Governance:**
- Constitute the first independent Governance Node: a faculty or professional association that issues a signed Clinical Capability Module.
- Establish the GPG key registry for White Branch members, making clinical approval cryptographically verifiable in git history.
- Publish the CCM signing specification so any institution can become a Governance Node.

**Success criteria:**
- [ ] CDI thresholds validated against real HRV data from ≥ 20 participants
- [ ] At least 1 independent Governance Node actively signing CCMs
- [ ] BrainFlow integration working with ≥ 2 real sensor models
- [ ] Judicial Kill Switch passing legal review in ≥ 1 jurisdiction (Colombia/EU)
- [ ] 1 peer-reviewed submission

---

## 🛡️ Milestone 2: The Acolyte SDK
**Status: ⏳ Not started | Target: 18–30 months post-M0**

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
- [ ] ≥ 3 independent Governance Nodes active
- [ ] RFC published and open for community comment
- [ ] IEEE P2510 submission or equivalent standards body engagement

---

## 🌐 Phase 3: Universal Sovereign Standard
**Status: ⏳ Not started | Target: 36+ months post-M0**

The Cortex Protocol transitions from a project to a standard. Governance is distributed across an international network of independent nodes. The protocol is hardware-manufacturer-adoptable.

**Objectives:**

**Standard:**
- Release Cortex Protocol Specification v1.0 as a stable, versioned standard document with a formal change management process.
- Establish the Global Governance Council: a multi-institutional body with representatives from ≥ 5 countries providing consensus-based protocol updates.
- Define the "Cortex-Ready" hardware certification: a specification that sensor and device manufacturers can implement to indicate their products are compatible with the SAL.

**Federated Learning:**
- Implement privacy-preserving federated CDI refinement: Governance Nodes aggregate gradient updates (not raw data) from consenting users to improve baseline models population-wide.
- Publish federated learning architecture specification ensuring no raw biometric data leaves individual devices.

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
Open an Issue tagged `[Technical-Track]`. Priority contributions: BrainFlow sensor adapter, CDI reset protocol, Judicial Kill Switch implementation.

**Standards Track** — If you work in AI ethics, regulatory affairs, or standards bodies:
Open an Issue tagged `[Standards-Track]`. We are building toward IEEE and ISO engagement and need reviewers for the RFC draft.

---

> *"A roadmap is not a promise of a product. It is a statement of direction, maintained honestly, updated as reality demands, and always subordinate to the clinical mandate."*
> 
