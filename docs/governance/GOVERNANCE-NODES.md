# Cortex Protocol — University Node Governance Specification

```
Document ID:   GOVERNANCE-NODES.md
Version:       0.6.0-GOV
Status:        PROPOSED SPECIFICATION (DRAFT — Open for RFC Comment)
Date:          June 2026
Supersedes:    N/A (first edition)
License:       GNU GPL v3
Tier:          Operational (extends GOVERNANCE.md; subordinate to GOVERNANCE-BASE.md)
```

> Submit comments via Issue tagged `[RFC-Comment]` or `[Governance-Node-Application]`.

---

## Document Hierarchy Notice

This document operates within the existing Cortex Protocol governance stack. Readers MUST understand the hierarchy before applying any rule herein:

```
GOVERNANCE-BASE.md        ← Constitutional layer (unalterable principles)
        ↓
GOVERNANCE.md             ← Three-body governance framework (White Branch authority)
        ↓
GOVERNANCE-NODES.md       ← This document (Node admission, obligations, enforcement)
        ↓
Regional Compliance Modules (RCM)   ← Jurisdiction-specific annexes (pluggable)
```

Rules in this document SHALL NOT contradict `GOVERNANCE-BASE.md` or `GOVERNANCE.md`. In any conflict, the higher-tier document prevails. This document extends — it does not replace — the Governance Node definitions in `GOVERNANCE.md §Governance Nodes`.

---

## Preamble

The Cortex Protocol distributes its governance authority across independent institutional nodes — university faculties, professional associations, and research centers — to prevent capture by any single actor, including the protocol's own founders.

This document formalizes what it means to be a Governance Node: how an institution qualifies, what it can do, what it must do, what it is permanently prohibited from doing, and what happens when it fails. It is written for the audience that matters most at the institutional onboarding stage: university legal counsel, IRB coordinators, clinical faculty evaluating resource commitment, and open-source contributors verifying the anti-capture guarantees.

Two design principles govern every rule in this document:

**The Black Box Principle.** The protocol governs outputs and behaviors, never internal institutional topology. A Node that satisfies all structural invariants retains absolute freedom to organize its internal committees according to its own bylaws. The protocol does not specify how a university runs its meetings — it specifies what the Node's cryptographic output must certify.

**Honest Scope.** Rules in this document that lack an enforcement mechanism are explicitly flagged as institutionally mitigated rather than cryptographically enforced. A governance specification that overstates its own power is a liability, not a protection.

---

## §1 — The Four Core Invariants (Constitutional Backbone)

The four invariants defined in this section are the non-negotiable architectural backbone of Node governance. They are **non-waivable** by any individual Node, by the White Branch acting alone, or by any operational update process. Amendment requires the supermajority process defined in §5.1.

Every other rule in this document derives from, or operationalizes, one of these four invariants. When a specific rule appears to conflict with situational judgment, the invariant takes precedence.

---

### Invariant I — Interdisciplinarity

A Node SHALL NOT sign or validate any Clinical Capability Module (CCM) without documented consensus across all three of the following disciplinary domains:

1. **Clinical / Neuroscience domain** — evaluation of neurophysiological safety boundaries, CDI threshold applicability, and Polyvagal-grounded stress metrics (HRV, RMSSD, Window of Tolerance).
2. **Engineering / Computer Science domain** — audit of cryptographic proofs (X25519, ChaCha20-Poly1305, HKDF-SHA256), SAL boundary integrity, and WASM sandbox compliance.
3. **Legal / Bioethics domain** — verification of neuro-rights framework compliance and data sovereignty obligations applicable to the CCM's deployment context.

> **// Rationale:** Human cognitive protection at the protocol level requires the simultaneous lens of health, code, and law. A CCM approved by engineers alone may be technically correct but clinically harmful. A CCM approved by clinicians alone may be therapeutically sound but cryptographically weak. A CCM approved by legal counsel alone may be compliant but technically unenforceable. Single-domain sign-off is a single point of failure. The interdisciplinarity invariant is the structural defense against it.

> **// Gap acknowledged:** At Milestone 1, the first Governance Node may not have formally credentialed representation in all three domains from day one. A Node in this situation SHALL document the gap explicitly, seek interim peer review from the White Branch for the missing domain, and commit to a documented timeline for full compliance. Operating indefinitely under a single-domain sign-off is a compliance violation.

---

### Invariant II — Intergenerational Parity

Every Node SHALL maintain an internal operational structure that grants **binding participation rights** to advanced students — defined as final-year undergraduate, graduate, or postgraduate researchers actively affiliated with the Node's institution — within the three core disciplines, during the CCM **proposal phase** and the CCM **review phase**.

"Binding" means: a student body objection during the proposal or review phase SHALL be documented in the CCM record and SHALL require a written response from credentialed Node members before the CCM proceeds to signature. An objection that receives no written response SHALL block CCM progression.

Final cryptographic signing authority resides with credentialed institutional representatives to ensure key continuity across academic cycles. A Node whose internal structure structurally excludes students from the proposal and review phases SHALL be deemed non-compliant with this invariant.

> **// Rationale:** Faculty governance models in long-tenured institutions are susceptible to disciplinary inertia — the gradual calcification of consensus around existing paradigms. Students represent the primary long-term stakeholders of neurotechnology standards: the populations who will live inside the systems these standards govern for the largest fraction of their lives. Their participation is not decorative. It is the mechanism by which the governance structure remains responsive to the people it is designed to protect. A standard that excludes students from review is, in a technical sense, writing rules for a constituency that has no voice in writing them.

> **// Implementation note:** The protocol does not specify how student participation is organized internally. A Node may use standing student committees, rotating reviewer pools, or structured comment periods. The invariant requires only that the mechanism (a) is structurally present, (b) produces binding objections, and (c) is documented in the Node's operational charter submitted at admission.

---

### Invariant III — Temporal SLA

A Node SHALL process, deliberate, and return a cryptographic response — either a signed approval or a rejection with bibliographic justification — to a CCM review request within **36 hours** of the request's decentralized broadcast timestamp.

A Node that fails to respond within 36 hours on three consecutive CCM requests SHALL automatically enter **Probationary Status** as defined in §4.1. Probationary Status is triggered by the protocol network state machine, not by a governance vote.

> **// Rationale:** The protocol enforces a non-bypassable 48-hour global propagation delay for safety-critical patches (NEUTRALITY.md §5). Nodes must operate within 36 hours to preserve a 12-hour buffer for final network synchronization. A Node that structurally cannot meet this SLA is a network liability regardless of its clinical or institutional quality.

> **// Force majeure provision:** A Node experiencing a documented institutional emergency (natural disaster, critical infrastructure failure, regulatory freeze) MAY submit a `NODE-SLA-SUSPENSION` artifact to the network signed by its GPG key, declaring the emergency and its expected duration. During a declared suspension, SLA violations SHALL NOT count toward the probation trigger. Undeclared suspensions receive no protection. A Node that uses this provision more than twice in any 12-month period SHALL trigger a White Branch audit of its operational resilience.

---

### Invariant IV — Commercial Conflict Mitigation

Any individual participating in a Node's CCM review process — faculty, researcher, or student — who holds a financial relationship, equity stake, active consultancy contract, or direct research funding from an entity that is the applicant for the CCM under review SHALL immediately recuse themselves from the entire review cycle for that CCM.

The recusal SHALL be logged in the Node's public audit record within 6 hours of the conflict being identified, with the following fields: individual role, nature of financial relationship, CCM identifier, and timestamp. The log entry SHALL be immutable once written.

A CCM signed by a Node in which a conflicted reviewer was not recused is invalid. The White Branch MAY revoke the CCM and require re-review.

> **// Rationale:** The clinical thresholds this protocol enforces are the boundary between user protection and user harm. An entity with commercial interest in a higher or lower threshold has a structural incentive misaligned with clinical safety. Recusal is not an accusation of bad faith — it is the architecture that makes bad faith unnecessary to assume. The public log is the mechanism that makes the recusal auditable by anyone, not just by the Node itself.

> **// Gap acknowledged:** Self-reported conflicts depend on individual honesty. The protocol cannot cryptographically verify that all conflicts have been declared. Community members who identify undisclosed conflicts MAY file a `[Governance-Conflict]` Issue referencing the CCM identifier and evidence. The White Branch SHALL investigate within 14 days.

---

## §2 — Node Admission Requirements

### 2.1 Eligibility Criteria

To be eligible to apply as a Governance Node, an institution SHALL satisfy all of the following:

**2.1.1 Institutional standing.** The institution MUST be a legally recognized, degree-granting higher education institution or accredited research organization within its operative jurisdiction. Professional associations with formal research mandates MAY apply under the same process, with additional documentation of their research governance structure.

> **[LEGAL REVIEW REQUIRED — jurisdiction-specific]** The legal definition of "accredited research institution" and the capacity to enter binding protocol participation agreements varies by jurisdiction. Each applicant MUST provide a legal opinion from counsel in their primary jurisdiction confirming institutional capacity to execute open-source protocol governance obligations. This opinion SHALL be included in the admission application.

**2.1.2 IRB / Ethics Board capacity.** The institution MUST maintain an active Institutional Review Board (IRB) or equivalent human-subject research ethics committee with documented authority over clinical and biometric research conducted under its affiliation. The Node's operations under Research Mode (§3.2) SHALL fall within the oversight scope of this committee.

> **[WHITE BRANCH REVIEW REQUIRED]** Any Research Mode CCM authorizing human-subject testing SHALL require documented IRB approval from the Node's ethics committee prior to execution. This is a non-waivable clinical safety requirement.

**2.1.3 Multi-domain representation.** The institution MUST demonstrate, at the time of application, that it has identified credentialed representatives in all three disciplinary domains required by Invariant I (§1). Named individuals, their credentials, and their domain assignment SHALL be included in the application. Vacancy in any domain at the time of application is grounds for deferral, not rejection — the application may resubmit when the vacancy is filled.

**2.1.4 Student participation structure.** The institution SHALL describe, in the application, the structural mechanism by which advanced students will hold binding participation rights in CCM review as required by Invariant II (§1). The description need not specify internal committee names — it must describe the mechanism and how student objections produce documented, mandatory responses.

**2.1.5 Funding independence.** The institution SHALL disclose all current and anticipated funding sources for the Node's operations at the time of application. Funding from any entity with a commercial interest in protocol threshold outcomes is permanently prohibited (§3.3.4). Funding from technology corporations, AI development companies, hardware manufacturers, or private investors with stake in neurotechnology products is explicitly prohibited regardless of the stated purpose of the funding.

> Permitted funding sources: public universities, public research grants, government research agencies, open-source foundations (e.g., Linux Foundation, Mozilla Foundation, Apache Software Foundation), transparent philanthropic organizations with no commercial neurotechnology stake, and peer-reviewed grant-funded research programs.

### 2.2 Cryptographic Infrastructure Requirements

**2.2.1 Key generation.** Upon acceptance, a Node SHALL generate a dedicated GPG keypair exclusively for Cortex Protocol governance actions. The keypair MUST use Ed25519 or RSA-4096. Keys generated for other institutional purposes SHALL NOT be used for protocol governance.

**2.2.2 Key custody.** The private key SHOULD be held via a hardware security module (HSM) or a secure multi-signature custody scheme. The custody arrangement SHALL span at least two of the three domain representatives (§2.1.3), so that no single individual's incapacity results in key inaccessibility.

**2.2.3 Key succession plan.** The Node SHALL maintain a documented key succession plan addressing: how signing authority transfers across academic appointment cycles, how key compromise is handled, and how the Node communicates a key rotation to the protocol network. The plan SHALL be included in the admission application and updated whenever domain representatives change.

**2.2.4 Key registration.** Accepted Nodes SHALL submit their public key to the White Branch GPG key registry, which is maintained as a verifiable, versioned artifact in the protocol repository. The registry entry SHALL include: Node identifier, institutional affiliation, key fingerprint, date of registration, and domain coverage.

### 2.3 Admission Process

1. Applicant institution opens a GitHub Issue tagged `[Governance-Node-Application]`.
2. Application MUST include: institutional affiliation and legal jurisdiction, legal opinion on institutional capacity (§2.1.1), IRB documentation (§2.1.2), named domain representatives with credentials (§2.1.3), student participation mechanism description (§2.1.4), funding sources disclosure (§2.1.5), proposed GPG key custody arrangement (§2.2.2), and key succession plan (§2.2.3).
3. White Branch conducts clinical and governance review within 30 days.
4. If active Governance Nodes exist: admission requires White Branch approval AND a simple majority of active Nodes. If no active Nodes exist: White Branch approval is sufficient (bootstrap condition for first Node).
5. Applicant is notified of decision with written reasoning. Rejections SHALL identify specific unmet criteria. Deferrals SHALL identify what is missing and invite resubmission.
6. Upon acceptance: Node registers GPG public key, Node identifier is added to the registry, Node is designated `ACTIVE`.

---

## §3 — Node Authorities and Obligations

### 3.1 The Black Box Principle (Restated)

The protocol governs the Node's outputs and behaviors. It does not govern how the Node organizes its internal committees, what it calls them, how often they meet, or what its internal voting procedures are. A Node that satisfies all four Core Invariants and produces compliant outputs is in full compliance, regardless of how it achieves that internally.

This principle exists to ensure the protocol is adoptable by institutions with diverse internal governance structures — different academic traditions, different faculty-student relationship models, different committee cultures — without requiring any institution to reorganize itself to fit a template.

### 3.2 CCM Signing Authority

**3.2.1 Authorized actions.** An `ACTIVE` Node with current funding transparency compliance and all three domain representations staffed MAY:

- Cryptographically sign Clinical Capability Modules (CCMs) for deployment in Commercial Mode.
- Issue Research Mode CCMs (§3.2.2) for human-subject validation studies under IRB oversight.
- Participate in the Annual Review Cycle by submitting evidence-backed threshold proposals to the White Branch.
- Maintain a hardware whitelist of Cortex-Ready devices verified by its engineering domain representatives.
- Publish Critical Security Alerts when its technical representatives detect implementation vulnerabilities, LIMES entropy degradation, or SAL boundary violations.
- Provide institutional documentation for regulatory submissions and academic publications referencing the protocol.

**3.2.2 Research Mode CCMs.** A Node MAY co-sign ephemeral Research Mode CCMs authorizing human-subject studies. Research Mode CCMs SHALL include:

- Documented IRB approval number and issuing ethics committee.
- An `Entropy TTL` not exceeding 6 months from issuance date.
- A `Telemetry-Zero` sandbox profile enforcing that no individual-identifiable data leaves the SAL boundary.
- A defined participant ceiling (maximum N for the study).
- A data destruction timeline not exceeding 24 months post-study completion.

> **[WHITE BRANCH REVIEW REQUIRED]** Any Research Mode CCM that proposes modifications to CDI thresholds, Clinical Bridge parameters, or LIMES entropy assumptions — even temporarily for study purposes — SHALL be submitted to the White Branch for clinical review before the Node signs it. Research design does not override clinical safety architecture.

**3.2.3 CCM invalidity conditions.** A CCM signed by a Node is invalid if, at the time of signing:

- The Node was in Probationary Status (§4.1).
- One or more domain representative positions were vacant and the gap was not documented with White Branch interim review.
- A known commercial conflict had not been recused and logged (Invariant IV).
- The annual funding transparency report was overdue by more than 30 days.
- The Node's GPG key had been placed in `SUSPENDED` or `REVOKED` status.

### 3.3 Mandatory Obligations

**3.3.1 Annual Review Cycle participation.** Nodes SHALL participate in the Annual Review Cycle defined in `GOVERNANCE.md`. Participation requires: review of new peer-reviewed literature relevant to CDI and LIMES thresholds, submission of evidence-backed proposals or confirmation of no changes warranted, and attendance at the White Branch review deliberation (remote participation is acceptable).

A Node that misses two consecutive Annual Review Cycles without a documented `NODE-SLA-SUSPENSION` (§1 Invariant III force majeure) SHALL trigger a White Branch compliance review.

**3.3.2 Funding transparency report.** Nodes SHALL publish an annual funding transparency report as a condition of CCM renewal. The report SHALL disclose: all funding sources for Node operations in the preceding 12 months, the amount or range for each source, the purpose of the funding, and a signed statement from the Node's legal representative that no prohibited funding sources are present.

The report SHALL be published as a signed, versioned artifact in the protocol repository. CCM signing authority is suspended automatically if the report is overdue by more than 30 days.

**3.3.3 Public audit log.** Nodes SHALL maintain a public, append-only audit log recording: all CCMs reviewed (approved or rejected with bibliographic justification), all recusals under Invariant IV, all SLA timestamps (request received, deliberation completed, response broadcast), all domain representative changes with dates, and all funding transparency reports.

The audit log SHALL be hosted in a publicly accessible location declared at admission. The format SHALL allow machine-readable parsing to support automated SLA monitoring.

**3.3.4 Prohibition on prohibited funding.** Nodes SHALL NOT accept, at any time during their active status, funding from: technology corporations, AI development companies, hardware manufacturers, private investors with equity stake in neurotechnology products, or any entity that is a CCM applicant to the same Node in the same funding period. Discovery of a prohibited funding relationship triggers immediate suspension pending White Branch review (§4.2), regardless of whether the funding has influenced any decision.

**3.3.5 Key hygiene.** Nodes SHALL notify the White Branch GPG registry within 48 hours of any key compromise, key rotation, or change in key custody arrangement. Nodes SHALL rotate their GPG keypair at least every 4 years. Key rotation requires re-registration in the public registry and does not interrupt Node status provided the succession plan (§2.2.3) is followed.

---

## §4 — Accountability and Enforcement

The enforcement architecture distinguishes deterministic failures — those triggerable by objective, measurable criteria — from qualitative failures — those requiring investigative judgment. Different mechanisms apply to each.

```
Enforcement trigger taxonomy:

DETERMINISTIC ──► Automated network state machine response
  Examples: SLA timeout × 3, funding report overdue > 30d, key expiry

QUALITATIVE   ──► White Branch audit → supermajority vote
  Examples: undisclosed conflict, CCM data manipulation, bioethics breach
```

### 4.1 Automated Deterministic Enforcement

**4.1.1 SLA probation trigger.** If a Node registers three consecutive SLA timeouts (failure to respond within 36 hours to a CCM review request), the protocol network state machine SHALL automatically downgrade the Node's status to `PROBATION`. This transition is logged in the public registry with the timestamp of the third violation.

**4.1.2 Probation conditions.** A Node in `PROBATION` status:
- MAY continue reviewing CCMs but its signatures carry a `PROBATION` flag visible to all consumers.
- SHALL NOT have its CCM signatures treated as a quorum-qualifying vote in inter-Node consensus processes.
- SHALL submit a written remediation plan to the White Branch within 14 days explaining the cause of the SLA failures and structural changes to prevent recurrence.

**4.1.3 Probation resolution.** A Node exits `PROBATION` by responding to 5 consecutive CCM requests within the 36-hour SLA. Automatic restoration to `ACTIVE` status is logged in the registry.

**4.1.4 Auto-suspension from probation.** A Node in `PROBATION` that: (a) fails to submit a remediation plan within 14 days, OR (b) fails to respond to a network-critical synchronization block within 72 hours, SHALL have its signing capabilities automatically suspended (`SUSPENDED` status) by the network state machine. Restoration from `SUSPENDED` requires White Branch review.

**4.1.5 Funding report suspension.** A Node whose annual funding transparency report is overdue by more than 30 days SHALL have its CCM signing authority automatically suspended until the report is published and validated. This suspension does not affect the Node's `ACTIVE` status for other purposes — it affects only new CCM signatures.

> **// Rationale:** Network integrity during zero-day neurophysiological exploit response cannot depend on human voting processes operating on multi-day timescales. Deterministic enforcement for objective criteria is the architecture that makes the 48-hour propagation window meaningful.

### 4.2 Qualitative Non-Deterministic Enforcement

**4.2.1 Investigation trigger.** The White Branch SHALL initiate a formal audit upon receiving verifiable evidence — in the form of a `[Governance-Conflict]` Issue with documented supporting artifacts — of any of the following: undisclosed commercial conflict of interest, data manipulation in CCM review, breach of bioethical standards in Research Mode operations, or operation under prohibited funding.

**4.2.2 Investigation process.** The White Branch SHALL:
1. Acknowledge the report publicly within 72 hours.
2. Notify the subject Node within 72 hours with a description of the allegation.
3. Compile a Technical Infraction Report within 21 days, documenting findings and proposed disposition.
4. Publish the report for 14-day community comment before any enforcement action.

**4.2.3 Suspension pending investigation.** If the White Branch determines that the alleged conduct — if confirmed — would constitute an immediate risk to protocol integrity or user safety, it MAY suspend the Node's signing authority provisionally during the investigation. Provisional suspension requires documented clinical justification and SHALL be time-bounded to the investigation period.

**4.2.4 Supermajority execution for revocation.** To permanently revoke a Node's credentials based on the Technical Infraction Report, a network consensus vote requiring **two-thirds (2/3) supermajority of all other active, non-probationary Nodes** SHALL be obtained. The White Branch presents the report; the vote is by active Nodes.

> **// Rationale for supermajority, not White Branch unilateral:** The White Branch has clinical authority, not political authority. Unilateral White Branch power to expel Nodes creates a capture vector in which a compromised White Branch could selectively remove dissenting Nodes. The supermajority requirement ensures that Node expulsion requires the consent of the institutional peer community — while the White Branch evidence threshold ensures that peer-solidarity cannot protect a Node with documented clinical malpractice.

**4.2.5 Node response rights.** A Node subject to investigation SHALL have the right to submit a written response to the Technical Infraction Report before the community comment period closes. The response SHALL be published alongside the report.

---

## §5 — Inter-Node Consensus Rules

### 5.1 Amendment Tiers

Decisions affecting the Cortex Protocol governance framework are tiered by consequence:

**Constitutional amendments** — modifications to §1 (Core Invariants), §4.2.4 (supermajority threshold for revocation), or this section (§5.1) — SHALL require:
- 100% consensus of all active, non-probationary Nodes, AND
- White Branch written sign-off, AND
- A MAJOR version increment to this document, AND
- A 30-day public comment period before ratification.

> **// Rationale:** The Core Invariants are the backbone. An amendment process that allows simple majority modification of the backbone is not a constitutional layer — it is a persuasion layer. 100% consensus is not an impossibly high bar for rules that exist precisely because they should never be weakened.

**Operational updates** — modifications to admission parameters (§2), CCM procedural requirements (§3), enforcement timescales (§4), or regional compliance annexes (§6) — SHALL require:
- Simple majority (>51%) of active, non-probationary Nodes voting in favor, AND
- White Branch non-objection within 14 days of the vote, AND
- A MINOR version increment to this document.

**Administrative corrections** — typographical errors, broken links, non-normative clarifications — MAY be merged by Protocol Stewards with White Branch confirmation and a PATCH version increment.

### 5.2 Voting Mechanics

**5.2.1 Quorum.** A valid operational vote requires participation from at least 60% of active, non-probationary Nodes. Votes that do not reach quorum within 21 days of opening are closed without result and may be resubmitted.

**5.2.2 Abstention.** A Node MAY formally abstain from a vote. Abstentions count toward quorum but not toward the majority calculation. A Node with a documented conflict of interest in the subject matter SHALL abstain.

**5.2.3 Deadlock resolution.** If an operational update vote reaches exactly 50%/50% among participating Nodes, the issue SHALL be escalated to the White Branch for a binding tie-breaking determination based on clinical and governance merit. The White Branch tie-breaking determination is final and not subject to further vote.

**5.2.4 Bootstrap condition.** When fewer than 3 active Nodes exist, inter-Node voting requirements are suspended. During the bootstrap period, White Branch approval constitutes sufficient authority for operational updates. The bootstrap period ends when the third Node achieves `ACTIVE` status.

### 5.3 Proposal Process

Any Node, White Branch member, or Protocol Steward MAY initiate a governance proposal by opening a GitHub Issue tagged `[Governance-Proposal]` with: the proposed change in RFC 2119 normative language, the rationale, the amendment tier assessment (§5.1), and any known objections or open questions.

Proposals that misidentify their amendment tier SHALL be corrected by Protocol Stewards before the vote opens.

---

## §6 — Anti-Capture Provisions for Nodes

These provisions supplement the Anti-Capture Provisions in `GOVERNANCE.md §Anti-Capture Provisions`, which remain in force. The provisions below address capture risks specific to the multi-Node architecture.

**6.1 Signing authority concentration limit.** No single Node SHALL hold signing authority over more than **33%** of all active CCMs at any time. If a Node's CCM portfolio exceeds this threshold due to other Nodes' deactivation, the Node SHALL flag the condition to the White Branch within 30 days. The White Branch SHALL prioritize new Node admission to restore distribution.

> **// Rationale:** A network where one Node effectively controls one-third or more of active CCMs is a fragile network. The concentration limit is not punitive — it is structural insurance against the protocol's safety guarantees depending on a single institution's continued integrity.

**6.2 Geographic distribution imperative.** The Global Governance Council (Milestone 3 target) SHALL maintain active Nodes in at least 5 distinct countries. No single nation-state's institutions SHALL hold a collective signing majority. This provision is aspirational at Milestone 1 but is stated here to govern admission priorities as the network grows.

**6.3 No self-certification.** A Node SHALL NOT sign a CCM for a hardware device, AI agent, or clinical implementation in which the Node's own institution has a financial or intellectual property interest. Self-certification is a conflict of interest under Invariant IV regardless of the magnitude of the financial relationship.

**6.4 Vendor firewall.** A Node SHALL NOT employ, as a domain representative, any individual whose primary employer is a technology corporation, AI developer, hardware manufacturer, or other entity with commercial interest in protocol threshold outcomes. Academic affiliation with dual commercial employment SHALL be disclosed at admission and is grounds for the White Branch to request reassignment of that individual's domain role.

**6.5 No governance role for commercial entities.** Commercial entities — regardless of their contribution to the protocol's technical development — SHALL NOT hold Governance Node status. Commercial entities MAY contribute technically via the Protocol Stewards track (`[Technical-Track]` Issues). They SHALL NOT sign CCMs.

---

## §7 — Node Termination and Succession

### 7.1 Voluntary Decommissioning

A Node MAY voluntarily withdraw from the protocol by broadcasting a signed `NODE-DECOMMISSION` artifact at least **30 days** before cessation of operations. The artifact SHALL include: Node identifier, effective decommission date, disposition of pending CCM reviews (transferred to which Node or to White Branch interim review), and a final funding transparency report.

The 30-day notice period exists to allow: transfer of pending CCM reviews, community notification, and White Branch assessment of concentration impact under §6.1.

### 7.2 Involuntary Deactivation

A Node is involuntarily deactivated when:
- Its GPG key is placed in `REVOKED` status following the supermajority process (§4.2.4), OR
- The institution loses its accreditation or legal standing in its primary jurisdiction, OR
- The institution is formally dissolved.

Involuntary deactivation is immediate. The White Branch SHALL notify the network within 24 hours of confirmation.

### 7.3 Legacy CCM Handling

CCMs signed exclusively by a deactivated Node (voluntary or involuntary) SHALL automatically transition to `UNVERIFIED` status in the protocol runtime over a **7-day degradation window** beginning on the deactivation date.

During the 7-day window, client systems SHALL display a `PENDING-REVALIDATION` flag for affected CCMs. After 7 days, `UNVERIFIED` CCMs SHALL NOT be treated as valid by compliant implementations.

> **// Rationale:** Orphaned keys from deactivated Nodes represent a permanent permission leak if not addressed. An abandoned Node key that remains technically valid can authorize AI capabilities indefinitely without any active institutional oversight. The 7-day degradation window provides operational continuity without creating a permanent gap.

**Revalidation pathway.** CCMs that transition to `UNVERIFIED` due to Node deactivation MAY be revalidated by a different active Node, provided the revalidating Node conducts a full CCM review as if the CCM were a new application.

### 7.4 Key Compromise

If a Node's private key is compromised, the Node SHALL:
1. Notify the White Branch and the protocol network immediately via a signed `KEY-COMPROMISE` artifact (signed with a pre-registered backup key if available, or via the White Branch if the primary key is unrecoverable).
2. All CCMs signed with the compromised key SHALL be placed in `SUSPENDED` status pending revalidation.
3. The Node SHALL generate a new keypair and follow the re-registration process (§2.2.4) within 72 hours.
4. If the Node cannot recover signing capability within 72 hours, it SHALL be treated as involuntarily deactivated under §7.2 until recovery is confirmed.

---

## §8 — Regional Compliance Module Interface

The Cortex Protocol core is jurisdiction-agnostic. Governance Nodes operating in specific legal jurisdictions MAY attach a Regional Compliance Module (RCM) to their Node registration, specifying how the Node's operations satisfy local statutory requirements.

RCMs are pluggable annexes — they do not modify the core protocol. They document how a Node implements the core in its local legal context.

### 8.1 RCM Structure (Template)

A valid RCM SHALL include the following fields:

```
RCM Identifier:        [e.g., RCM-EU-v1, RCM-LATAM-v1]
Node Identifier:       [Node's registered identifier]
Applicable Jurisdiction: [Country / Region / Supranational body]
Primary Statutory Framework: [Citation of governing law(s)]
Data Classification:   [How neurophysiological data is classified under local law]
Consent Requirements:  [Specific consent obligations beyond protocol baseline]
Data Residency:        [Where data may be processed and stored]
Ethics Board Reference:[Local IRB / ethics committee name and authorization scope]
Legal Review Date:     [Date of most recent legal counsel review]
Legal Counsel:         [Firm or individual — name and jurisdiction bar]
Validity Period:       [Date range; must be renewed annually]
```

### 8.2 RCM and Core Protocol Relationship

An RCM SHALL NOT reduce the protections mandated by the core protocol. An RCM MAY impose additional protections beyond the core. If local law requires a protection that the core protocol does not mandate, the RCM documents how the Node implements both.

If local law appears to conflict with a core protocol requirement, the Node SHALL flag the conflict in its RCM and submit it as a `[Governance-Conflict]` Issue for White Branch resolution before operating under the conflicting regime.

### 8.3 RCM Review and Expiry

RCMs SHALL be reviewed annually as part of the Node's annual obligations (§3.3.1). An expired RCM does not suspend the Node's `ACTIVE` status but SHALL be flagged in the public audit log and in the Node's public registry entry.

---

## §9 — Known Gaps and Open Questions

Consistent with the protocol's commitment to honest scope, this section documents limitations in this governance specification that are acknowledged but not yet resolved.

**Gap 1 — Self-reported conflict of interest.** Invariant IV relies on individual honesty for conflict disclosure. No cryptographic mechanism currently verifies that all financial relationships have been declared. Community reporting (§1 Invariant IV rationale) provides a partial mitigation. A formal Node member financial disclosure system is a Milestone 2 governance deliverable.

**Gap 2 — Bootstrap concentration risk.** When only one or two Nodes exist, the concentration limits of §6.1 cannot be meaningfully enforced, and the supermajority requirement of §4.2.4 is either impossible or trivially achievable. The White Branch serves as the governance backstop during the bootstrap period. This is institutionally mitigated, not cryptographically enforced.

**Gap 3 — Student parity verification.** Invariant II requires that the Node's internal structure grants binding student participation. The protocol verifies this through the Node's self-declared operational charter at admission and through community auditing. It does not cryptographically enforce student participation in any individual CCM review. A future CCM signing schema that includes a student-domain attestation field would close this gap.

**Gap 4 — Key succession across institutional dissolution.** §7.4 addresses individual key compromise. It does not fully address the scenario of an institution undergoing slow dissolution (loss of accreditation, prolonged administrative freeze) where the Node continues to sign CCMs while its institutional foundation erodes. The annual funding transparency report and White Branch audit triggers provide partial mitigation. This remains an open governance design question.

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 0.6.0-GOV | June 2026 | Initial edition. Jurisdiction-agnostic, permissionless entry model. Four Core Invariants as constitutional backbone. Deterministic and qualitative enforcement split. Regional Compliance Module interface. Black Box Principle. Explicit gap catalog. |

---

> *"Governance legitimacy is not declared. It is demonstrated — through transparent records, honest limits, and institutions that can show their work."*

---

*Cortex Protocol — GOVERNANCE-NODES.md v0.6.0-GOV*
*Maintained by Protocol Stewards under White Branch oversight.*
*Constitutional amendments require 100% Node consensus + White Branch sign-off.*
*Operational updates require >51% Node majority + White Branch non-objection.*
