# Cortex Protocol: Open Standard Specification
**Document ID: CORE-STANDARD-001 | Version: 0.2-draft (RFC)**
**White Branch — 2025/2026**

> **Status: Request for Comments (RFC)**
> Open for review by neurotechnology, clinical research, and AI ethics communities.
> Submit comments via Issue tagged `[RFC-Comment]`.

---

## Preamble

The Cortex Protocol is an open, royalty-free technical standard for the governance of human-AI interaction at the neurophysiological level. It defines the minimum requirements for a compliant implementation of the Sovereignty Abstraction Layer (SAL), the Clinical Drift Index (CDI), and the Clinical Bridge.

The standard is maintained by the White Branch under the governance framework in [GOVERNANCE.md](GOVERNANCE.md). Licensed under GPL v3.

---

## Part I — Scope and Definitions

### 1.1 Scope

This standard applies to any system that:
1. Collects, processes, or transmits neurophysiological or biometric data from a human user.
2. Operates an AI agent (Acolyte) where outputs can influence the user's cognitive or emotional state.
3. Claims compliance with the Cortex Protocol.

Systems operating exclusively on non-biometric data are outside scope.

### 1.2 Normative Language

**SHALL** — mandatory. A compliant implementation must satisfy all SHALL requirements.
**SHOULD** — recommended. Comply unless documented clinical justification exists for deviation.
**MAY** — optional.

### 1.3 Key Definitions

**Compliant Implementation:** Satisfies all SHALL requirements of this specification.
**Certified Acolyte:** AI agent that has passed the White Branch validation loop and operates under a signed Clinical Capability Module.
**Cortex-Ready Device:** Hardware sensor meeting minimum quality thresholds and registered in a Governance Node whitelist.
**Voluntary Activation Mode (VAM):** User-declared high-intensity session where CDI thresholds are elevated with documented consent.
**User-Verifiable Audit Protocol (UVAP):** Mechanism by which the user independently verifies implementation compliance — distinct from Governance Node verification.

---

## Part II — Core Requirements

### 2.1 The Sovereignty Abstraction Layer (SAL)

#### 2.1.1 Data Boundary

**SHALL:** Raw biometric data SHALL NOT be transmitted beyond the SAL boundary. All processing occurs locally on the user's device.

**SHALL:** The SAL SHALL implement the two-phase transformation (Section 2.2) before any data exits the SAL boundary.

**SHALL NOT:** Raw biometric data SHALL NOT be logged, cached to disk, or stored in any persistent medium in its original form.

#### 2.1.2 Session Isolation

**SHALL:** Each session SHALL be cryptographically isolated using a unique session salt of ≥ 256 bits from a cryptographically secure random number generator.

**SHALL:** Session salts SHALL be destroyed at session end via a session destruction function that: (a) replaces the salt with a new random value, (b) clears the session audit log, (c) renders all session tensors permanently inaccessible, (d) revokes all active ETHOS consents.

**SHALL NOT:** Session salts SHALL NOT be derived from user-identifiable data.

#### 2.1.3 Ephemeral Memory

**SHALL:** Raw biometric frames SHALL be held using a deterministic destruction pattern (context manager or equivalent) guaranteeing memory zeroing upon frame exit, independent of garbage collection.

**SHALL NOT:** Implementations SHALL NOT rely solely on finalizer methods (`__del__`, `finalize()`) for raw data destruction.

---

### 2.2 Two-Phase Tensor Transformation

#### 2.2.1 Phase A — Clinical Feature Extraction

**SHALL:** Phase A SHALL extract ≥ 5 statistical descriptors sufficient to classify autonomic state (minimum: mean, std, p25, p75, max of the signal envelope).

**SHALL:** Phase A output SHALL be normalized to [0, 1] relative to a clinically defined physiological reference range documented in the implementation's Clinical Bridge specification.

**SHALL:** Phase A output SHALL be the exclusive input to the Clinical Bridge. The Clinical Bridge SHALL NOT receive Phase B output.

#### 2.2.2 Phase B — Privacy Obfuscation

**SHALL:** Phase B SHALL apply an irreversible cryptographic transformation using the session salt, with minimum security of 256 bits (e.g., HMAC-SHA256).

**SHALL:** The Acolyte SHALL receive only Phase B output. The Acolyte SHALL NOT receive Phase A features, raw biometric values, or the session salt.

---

### 2.3 Clinical Bridge

#### 2.3.1 Per-Frame Validation

**SHALL:** Every biometric frame SHALL pass Clinical Bridge validation before Acolyte processing.

**SHALL:** Clinical Bridge thresholds SHALL be derived from peer-reviewed literature with bibliographic citations in the implementation's clinical specification.

**SHALL:** Clinical Bridge thresholds SHALL be defined and maintained exclusively by clinically qualified personnel.

**SHALL NOT:** Clinical Bridge thresholds SHALL NOT be modified by the Technical Branch, by Acolyte logic, or by any automated process without explicit clinical governance approval.

#### 2.3.2 Threshold Documentation

**SHALL:** For each Clinical Bridge threshold, the implementation SHALL publish: (a) the parameter name and value, (b) the physiological condition it maps to, (c) the bibliographic reference(s).

---

### 2.4 Clinical Drift Index (CDI)

#### 2.4.1 Temporal Monitoring

**SHALL:** A compliant implementation SHALL monitor biometric coherency using a sliding temporal window of ≥ 60 seconds.

**SHALL:** The CDI SHALL employ at least one absolute threshold (hard violation) and one statistical deviation threshold relative to personal baseline (soft violation).

**SHALL:** Hard and soft violation counters SHALL be tracked independently with documented, clinically justified trigger thresholds.

#### 2.4.2 Baseline Personalization

**SHOULD:** The CDI SHOULD establish a personal baseline from ≥ 3 initial sessions (recommended: 7) to personalize statistical detection.

**SHALL:** Without an established baseline, the CDI SHALL operate using only absolute threshold detection.

#### 2.4.3 Block Response

**SHALL:** When CDI block thresholds are exceeded, Acolyte processing SHALL be immediately suspended and SHALL NOT resume without a documented reset protocol requiring explicit human action.

**SHALL:** The CDI reset protocol SHALL require user action (governance Level 0–1) or authorized clinical professional action (governance Level 2). Automatic reset without human authorization is not permitted.

#### 2.4.4 Voluntary Activation Mode (VAM)

**SHALL:** A compliant implementation SHALL provide a Voluntary Activation Mode allowing users to explicitly declare high-intensity sessions where CDI thresholds are elevated with documented consent.

**SHALL:** VAM activation SHALL be recorded in the session audit log with timestamp, declared duration, and elevated threshold values.

**SHALL:** VAM SHALL auto-expire at the declared duration end. Manual extension requires a new explicit activation.

**SHALL NOT:** VAM SHALL NOT be activatable when ETHOS consent capacity is NONE (dorsal vagal state / CDI blocked).

**SHALL NOT:** VAM SHALL NOT disable CDI monitoring. It recalibrates thresholds — it does not suspend protection.

**Rationale:** The CDI does not currently distinguish between pathological stress and voluntary high-intensity cognitive engagement (flow states, deliberate focused work). VAM preserves user sovereignty over this distinction while maintaining the audit record that allows clinical review.

---

### 2.5 Hardware Certification

#### 2.5.1 Sensor Quality Thresholds

**SHALL:** A compliant implementation SHALL verify sensors against minimum quality thresholds before data ingestion:

| Parameter | Minimum | Rationale |
| :--- | :--- | :--- |
| Signal-to-Noise Ratio | ≥ 30.0 dB | Minimum for reliable autonomic state classification |
| ADC Resolution | ≥ 12 bits | Minimum to resolve EEG microvolt amplitudes |
| Sampling Rate (cardiac) | ≥ 250 Hz | Required for accurate RMSSD computation |

**SHALL NOT:** Data from sensors failing quality thresholds SHALL NOT enter the SAL pipeline.

#### 2.5.2 Hardware Whitelist

**SHOULD:** Implementations SHOULD maintain a hardware whitelist signed by an active Governance Node.

**MAY:** Implementations MAY allow user-authorized exemptions for unlisted sensors, provided the exemption is explicitly logged.

---

### 2.6 LIMES — Proof of Human Liveness

#### 2.6.1 Liveness Proof Generation

**SHALL:** A LIMES-compliant implementation SHALL generate a liveness proof from the biological entropy of CORTEX biometric features — not from raw biometric data directly.

**SHALL:** The proof SHALL include a cryptographic timestamp and a unique nonce to prevent replay attacks.

**SHALL NOT:** The liveness proof SHALL NOT reveal: raw biometric values, sensor identity, user identity, or Phase A feature values.

#### 2.6.2 LIMES Temporal Validity Disclosure

**SHALL:** Any implementation claiming LIMES compliance SHALL document in its deployment materials that the liveness proof depends on the current computational distinguishability between biological entropy and synthetic entropy, and that this assumption is subject to annual review by the White Branch.

**SHALL:** The White Branch SHALL publish an annual LIMES entropy assessment as part of the Annual Review Cycle, documenting any changes to the validity of the biological entropy assumption.

**Rationale:** LIMES as currently specified is a strong defense against present-day synthetic signal generation. It is not a permanent cryptographic guarantee. As generative AI advances, the entropy distinguishability assumption may require hardware-bound entropy sources (e.g., TPM-based TRNG). Implementations must not represent LIMES as an unconditional guarantee.

---

### 2.7 ETHOS — Dynamic Consent

#### 2.7.1 Consent Capacity Assessment

**SHALL:** A compliant ETHOS implementation SHALL assess user consent capacity based on current CORTEX polyvagal state before processing any consent request:
- Ventral vagal → FULL capacity
- Sympathetic with CDI warning → LIMITED capacity (requires double confirmation)
- Dorsal vagal / CDI blocked → NONE (consent requests refused; existing consents revoked)

**SHALL NOT:** Consent requests SHALL NOT be presented to users in NONE capacity states.

#### 2.7.2 Consent Records

**SHALL:** Each consent record SHALL include: scope, purpose, granted timestamp, expiry, physiological state hash at time of consent, and revocation status.

**SHALL:** Consent records SHALL be stored locally. Consent records SHALL NOT be transmitted to external parties.

**SHALL:** Users SHALL be able to revoke any consent immediately with a single command (`revoke_all()` or equivalent).

---

### 2.8 Audit and Logging

#### 2.8.1 Audit Log Contents

**SHALL:** The session audit log SHALL contain per frame: timestamp, truncated sensor identifier (≤ 8 characters of hash), coherency index, autonomic state classification, CDI status, LIMES proof validity, ETHOS consent status.

**SHALL NOT:** The audit log SHALL NOT contain: raw biometric values, Phase A features, full sensor identifiers, session salts, or user-identifiable information.

#### 2.8.2 Log Accessibility

**SHALL:** The audit log SHALL be accessible to the user at any time during an active session.

**SHALL:** The audit log SHALL be destroyed as part of session destruction.

---

## Part III — Governance Requirements

### 3.1 White Branch (Clinical Authority)

**SHALL:** Any organization claiming Cortex compliance SHALL designate a clinical governance body composed of licensed mental health or neuroscience professionals with authority to define and modify Clinical Bridge thresholds.

**SHALL:** Clinical Bridge threshold modifications SHALL be documented with the approving clinician's identifier and supporting bibliographic evidence.

### 3.2 Governance Nodes

**SHOULD:** Compliant implementations SHOULD operate under at least one independent Governance Node issuing signed CCMs.

**SHALL:** CCMs SHALL carry a cryptographic signature verifiable against a published public key.

**SHALL NOT:** A hardware manufacturer, commercial AI developer, or for-profit entity SHALL NOT serve as its own Governance Node.

### 3.3 Anti-Capture Provisions

**SHALL NOT:** Transmit raw biometric data to cloud infrastructure under any circumstances.

**SHALL NOT:** Implement Clinical Bridge thresholds favoring commercial engagement metrics over clinical safety.

**SHALL NOT:** Restrict the protocol to hardware from a single manufacturer.

**SHALL NOT:** Require users to authenticate to a centralized server to activate local protection features.

**SHALL NOT:** Use CDI, ETHOS, or LIMES data for operator analytics, performance monitoring, or any purpose beyond protecting the user whose data generated it.

---

## Part IV — Conformance Levels

Conformance levels are defined per module. A system declares compliance at the module level.

### Level 1 — CORTEX Compliant
All SHALL requirements for CORTEX (SAL, Clinical Bridge, CDI including VAM). Suitable for health monitoring and therapeutic AI.

### Level 2 — CORTEX + LIMES + ETHOS Compliant
Level 1, plus: LIMES liveness proof with temporal validity disclosure, ETHOS dynamic consent engine. Suitable for regulated clinical platforms and any application requiring legally defensible consent.

### Level 3 — Full Pentagon Compliant
Level 2, plus: KEROS hardware attestation, LOGOS cognitive integrity monitoring, and User-Verifiable Audit Protocol (UVAP). Suitable for education, digital democracy, and high-assurance cognitive environments.

### Optional Extensions (Outside Core Standard)
- **AGORA** — Distributed governance network (≥ 5 active Governance Nodes required)
- **MNEME** — Sovereign memory (implementation varies)

---

## Part V — Reference Implementation

The reference implementation is maintained at:
`https://github.com/Cortex-psylead/Cortex-OS-protocol`

- `src/sal/cognitive_shield.py` — CORTEX (M0, Level 1)
- `src/sal/cognitive_shield_v2.py` — CORTEX + LIMES + ETHOS (M1 preview, Level 2)
- `src/limes/limes_proof.py` — LIMES standalone module
- `src/ethos/ethos_consent.py` — ETHOS standalone module
- `src/keros/keros_seal.py` — KEROS standalone module (Level 3, hardware required)

All implementations use synthetic signals for demonstration. Real-hardware validation is the objective of Milestone 1.

---

## Part VI — Versioning

- **MAJOR:** Breaking change to backward compatibility
- **MINOR:** New requirements, backward-compatible
- **PATCH:** Clarifications, editorial corrections, bibliographic updates

Changes to SHALL requirements in Sections 2.1–2.8 require White Branch approval and MINOR or MAJOR increment. Changes to SHOULD and MAY require Technical Branch review only.

---

*Cortex Protocol Standard Specification v0.2-draft. Released for public comment under GPL v3.*
*White Branch — 2025/2026.*
