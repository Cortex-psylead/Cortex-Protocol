# 🏛️ Protocol Governance
**Cortex Protocol — Governance Framework v1.2**

This document defines how the Cortex Protocol is governed as an open standard. It establishes roles, validation processes, anti-capture mechanisms, and — critically — the limits of what governance can guarantee.

For foundational constitutional principles, see [GOVERNANCE-BASE.md](GOVERNANCE-BASE.md). For technical enforcement at runtime, see [ARCHITECTURE.md](../architecture/ARCHITECTURE.md).

---

## Governance Philosophy

The Cortex Protocol is a decentralized open standard, not a corporate product. Its governance rests on a single principle: **clinical safety parameters are maintained by the institutions best qualified to define them, not by those with commercial incentives to compromise them.**

But governance is not a complete solution. This document is explicit about what governance can and cannot guarantee — because a governance framework that overstates its own power is itself a form of capture.

---

## The Three Governance Bodies

### 1. ⚕️ White Branch (Clinical Authority)

**Composition:** Licensed mental health professionals, neuropsychologists, and neuroscience researchers.

**Authority:** Exclusive, non-delegable authority over:
- All numerical thresholds in `ClinicalThresholds` and `ClinicalBridge`
- Approval or rejection of any Clinical Capability Module (CCM)
- CDI reset protocol and Voluntary Activation Mode parameters
- Any modification to Clinical Bridge validation logic
- Annual review of LIMES entropy assumptions (see DISCLAIMER §4.1)

**Technical enforcement:** Commits modifying clinical threshold files require a GPG signature from a registered White Branch member key. Unsigned modifications are rejected.

**White Branch accountability:** Every threshold must carry a peer-reviewed bibliographic citation. Every modification must be versioned, publicly documented, and open to 30-day community comment before merging. The White Branch has authority because it shows its work — not because it declares authority.

**What the White Branch does NOT control:** Implementation architecture, programming language choices, or performance optimizations that do not affect clinical safety margins.

---

### 2. 🛡️ Protocol Stewards (Technical Branch)

**Composition:** Engineers, systems architects, open-source contributors.

**Authority:**
- Implementing the SAL, CDI, and Clinical Bridge as specified by the White Branch
- Maintaining the reference implementation and module SDK
- Reviewing pull requests for technical correctness, security, and hardware-agnosticism
- Publishing and versioning the standard specification
- Implementing the User-Verifiable Audit Protocol (Milestone 2)

**Constraint:** The Technical Branch cannot override a White Branch clinical decision. Technical necessity does not justify modifying clinical thresholds.

---

### 3. ⚖️ Legal Validator (Adscribed to the White Branch)

**Composition:** Legal professionals specializing in health data law, AI regulation, and digital rights.

**Authority:**
- Legal certification that CCMs comply with applicable law
- Review of DISCLAIMER and USER-DATA-MODEL for jurisdictional accuracy
- Advisory opinions on regulatory developments
- Annual review of the operator risk model (Section 5)

**Constraint:** No authority over clinical methodology. Legal risk management does not override clinical judgment.

---

## Governance Nodes: The Institutional Layer

Governance Nodes are the external institutional partners that distribute the protocol's authority across independent institutions. They are not advisory committees. Each node is a **structured technical institution** with two mandatory internal subcommittees. A node that does not maintain both subcommittees cannot issue valid Clinical Capability Modules.

**A Governance Node is:** A university faculty, professional association, or research center formally joined to the governance network, holding a GPG keypair for signing Clinical Capability Modules, and maintaining the two subcommittees defined below.

---

### Subcommittee A — Scientific Research & Resource Integrity

This subcommittee maintains the scientific and institutional foundation of the node. It does not write code — it maintains the clinical and legal legitimacy that makes the node's signatures meaningful.

**Scientific function (linked to ETHOS and Clinical Bridge):**
- Reviews new peer-reviewed literature in neuroscience, psychophysiology, and clinical psychology relevant to existing protocol thresholds.
- Proposes threshold updates to the White Branch during the Annual Review Cycle, supported by bibliographic evidence.
- Monitors sensor technology developments that may require hardware certification updates.
- Minimum composition: two licensed clinical or neuroscience professionals with active research affiliation.

**Resource transparency function (institutional independence):**
- Audits and publicly registers all funding sources sustaining the node.
- Enforces the Funding Independence Rule: node funding may only originate from universities, public research grants, open-source foundations, or transparent private donations. Funding from technology corporations, AI developers, hardware manufacturers, or any entity with commercial interest in protocol threshold outcomes is permanently prohibited.
- Publishes an annual funding transparency report as a condition of CCM renewal.
- If a prohibited funding source is detected, the subcommittee triggers immediate node suspension pending White Branch review — regardless of whether the funding has influenced any decision.

**Rationale:** A node whose funding is opaque or commercially compromised cannot be trusted to maintain threshold integrity. The resource transparency function is not administrative — it is the mechanism that makes the node's clinical authority credible.

---

### Subcommittee B — Technical Verification & Code Audit

This subcommittee is the node's engineering arm. Its function is to audit the silicon — to verify that what runs on users' devices faithfully implements what the standard specifies.

**CORTEX verification (linked to SAL and CDI):**
- Audits reference implementations and third-party deployments claiming CORTEX compliance.
- Verifies that the asynchronous State Buffer architecture (ARCHITECTURE-ASYNC.md) is correctly implemented: sensor silence defaults to BLOCKED, HMAC validation is present, and the AI pipeline has no synchronous coupling to the biometric thread.
- Tests for raw biometric data leakage beyond the SAL boundary.
- Verifies CDI threshold enforcement: hard and soft violation counters must be independent and not overridable by Acolyte logic.

**KEROS and LIMES integrity verification:**
- Audits GPG signatures on Clinical Capability Modules issued by the node and by other nodes within its oversight scope.
- Verifies TPM attestation chains in KEROS-compliant deployments.
- Monitors for advances in generative AI that may reduce the distinguishability of biological entropy from synthetic entropy, escalating to the White Branch when the annual LIMES entropy assessment warrants revision.
- Issues Critical Security Alerts when an AI agent pathway to bypass the biometric gateway is detected — through prompt injection, State Buffer manipulation, or policy snapshot replay — triggering immediate protocol update under expedited review.

**Minimum composition:** Two engineers or computer scientists with expertise in cryptographic systems, distributed architecture, or biometric signal processing.

---

### What a Governance Node Does

- Issues signed CCMs — valid only when both subcommittees are active and the annual funding transparency report is current.
- Participates in the Annual Review Cycle through Subcommittee A.
- Maintains a hardware whitelist verified by Subcommittee B.
- Publishes Critical Security Alerts when Subcommittee B detects implementation vulnerabilities or LIMES entropy degradation.
- Provides institutional credibility for regulatory submissions and academic publications.

### What a Governance Node Does NOT Do

- Govern the core standard specification — that is the White Branch's role.
- Hold veto power over other nodes' decisions.
- Represent commercial interests in governance processes.
- Issue CCMs without both subcommittees active and the funding transparency report current.
- Accept funding from any entity with commercial interest in protocol threshold outcomes.

### How to Become a Governance Node

Open an Issue tagged `[Governance-Node-Application]`. The application must include: institutional affiliation, proposed composition of both subcommittees, funding sources and transparency mechanism, field of expertise, and commitment to the Annual Review Cycle and annual funding transparency reporting. Acceptance requires White Branch approval.

**Full admission requirements, 36-hour SLA, and student research parity provisions are formally specified in [GOVERNANCE-NODES.md](docs/governance/GOVERNANCE-NODES.md) (Section C8) — the authoritative document for Governance Node onboarding in v0.5.0.**

**Current Governance Nodes:** *(None — Milestone 1 objective)*

---

## The Validation Loop

The Validation Loop is the core cryptographic consensus mechanism used to propose, verify, and commit modifications to the protocol's clinical variables or to deploy a new Clinical Capability Module (CCM). This loop ensures that code execution remains strictly subordinate to empirical evidence.
```
[ 1. Proposal ] ----> [ 2. Peer Review ] ----> [ 3. Legal/Tech Audit ]
|
v
[ 6. Runtime ] <---- [ 5. Multi-Sig ] <---- [ 4. Consensus Vote ]
```
### Step 1 — Initiation & Proof of Evidence

Any Governance Node may open a pull request (PR) to modify a threshold or submit a new CCM. The proposal must contain:
- The exact numerical changes within `ClinicalThresholds` or the compiled bytecode of the module.
- The corresponding peer-reviewed bibliographic citations mapping the changes to human psychophysiological behavior.

### Step 2 — Subcommittee A Evaluation (Scientific Validation)

The proposal is routed to the scientific subcommittees of active Governance Nodes. They must independently verify that:
- The clinical rationale is scientifically sound and free from systemic bias.
- The adjustments match known homeostatic thresholds (e.g., polyvagal shifts or cognitive load markers).

### Step 3 — Subcommittee B & Legal Validation (Technical & Compliance Audit)

Simultaneously, the engineering and legal branches review the PR to guarantee:
- **Zero-leakage compliance:** The modification introduces no pathways that could expose raw biometric data beyond the SAL boundary.
- **Asynchronous integrity:** The change respects the non-blocking state buffer constraints.
- **Regulatory alignment:** The Legal Validator signs off certifying compliance with regional neuro-rights standards and data protection frameworks (such as GDPR or Ley 1581/2012).

### Step 4 — Consensus & Multi-Signature Ledger Commit

Once all reviews pass, the proposal requires a multi-signature endorsement. A minimum of 66% of registered White Branch active GPG keys must sign the cryptographic payload. 

### Step 5 — Runtime Deployment & Hardware Enforcement

The newly signed configuration snapshot is distributed to the decentralized network registry. Local edge clients running the Cortex Protocol fetch this signed manifest. The local `cognitive_shield` verifies the chain of custody against the embedded White Branch root public keys before applying the new safety parameters to the active telemetry pipelines.

---

## Anti-Capture Mechanisms

To prevent the protocol from being subtly co-opted by commercial entities, AI developers, or state actors, three structural anti-capture mechanisms are hardcoded into the governance layer:

### 1. The Financial Separation Rule

As defined under Subcommittee A’s mandates, any node that accepts capital, infrastructure, or indirect subsidies from closed-source AI conglomerates, hardware sensor vendors, or advertising platforms loses its voting keys instantly. Governance authority is derived exclusively from academic and clinical independence.

### 2. Forking and Sovereign Devolution

If the White Branch itself is captured or refuses to update safety parameters in the face of emerging clinical risk, the protocol grants the Technical Branch and individual users the un-alienable right to execute a **Sovereign Devolution**. Because the reference implementation is fully open-source and dual-licensed under open frameworks, users can instantly switch their hardware engines to follow an independent, uncaptured clinical root chain.
### 3. Cryptographic Immutability of Local Overrides
No governance body—including the White Branch—has the technical capability to push a remote override that relaxes safety limits on a user's local device without explicit, physical confirmation from the user through the ETHOS module. Governance flows downward to protect the user, never upward to control them.

---

## Governance Limitations & Hard Boundaries

A governance framework that overstates its own power is inherently dangerous. The Cortex Protocol explicitly acknowledges what this framework **cannot** guarantee:

| What Governance CAN Enforce | What Governance CANNOT Guarantee |
| :--- | :--- |
| **Statistical Integrity:** Ensuring that all thresholds in public releases match validated clinical literature. | **Hardware Malice:** Governance cannot stop a compromised, black-market physical sensor from spoofing raw data before it reaches the SAL handshake layer. |
| **Architectural Isolation:** Ensuring the reference code maintains an absolute boundary between raw data and external AI tensors. | **Operating System Compromise:** If the host device kernel is fully compromised at the root level, application-layer isolation requires a physical TPM 2.0/Secure Enclave via KEROS to survive. |
| **Node Transparency:** Auditing the capital structure and funding of institutional partners to eliminate hidden corporate incentives. | **User Self-Exploitation:** Governance cannot prevent a user from intentionally sidelining official profiles to run unvalidated, hazardous third-party modules at their own risk. |

---

## Open Governance Vectors for Milestone 1

The following issues are currently open for review and require consensus before the final Milestone 1 mainnet transition:
1.  **SLA Execution Latency:** Defining whether a 36-hour service-level agreement for emergency patch signatures from the White Branch is sustainable under distributed time-zone scenarios.
2.  **Student Research Parity:** Implementing zero-cost token access rules for independent, non-funded academic student research groups seeking Governance Node status without corporate back-channeling.
3.  **Local vs. Global Whitelisting:** Deciding if a local device can add custom sensor whitelists via physical key pairing without requiring global White Branch signature propagation.
---
*This framework is a living open standard. All modifications to this document require a formal Validation Loop execution and must be cryptographically anchored to the protocol's public key infrastructure.*
**Document ID:** GOV-FRAME-1.2-PRIME | **Version:** 1.2 | **Last Updated:** 2026-06-16
```
