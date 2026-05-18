# ⚠️ Disclaimer & Known Limitations: Cortex Protocol
### Legal Framework, Honest Boundaries, and Scope of Guarantees

**Read this document before using, implementing, or contributing to the Cortex Protocol.**

---

## 1. Nature of the Project

**[EN]** The Cortex Protocol is an open-source research and development framework. It is not a commercial product. It is not a substitute for professional medical or psychological judgment. It provides technical infrastructure for neurophysiological data sovereignty — the responsibility for its deployment lies with the implementer and the end user.

**[ES]** El Protocolo Cortex es un marco de investigación y desarrollo de código abierto. No es un producto comercial. No sustituye el juicio médico o psicológico profesional. Proporciona infraestructura técnica para la soberanía de datos neurofisiológicos — la responsabilidad de su despliegue recae en el implementador y el usuario final.

---

## 2. What the Protocol IS and IS NOT

| What Cortex Protocol IS | What Cortex Protocol IS NOT |
| :--- | :--- |
| A research and technical standard | A medical device or diagnostic tool |
| An open-source framework (GPL v3) | A certified clinical intervention |
| An academic proposal | A substitute for professional care |
| A hardware sovereignty specification | A production-ready commercial product |
| A protection layer against involuntary AI influence | A guarantee against all forms of AI harm |
| A framework requiring human clinical governance | An autonomous protection system |

---

## 3. Not a Medical Device

The protocol and its Clinical Capability Modules (CCM) are academic proposals grounded in peer-reviewed literature. Specifically:

- **No diagnostic authority:** HRV and EEG monitoring modules are not diagnostic tools for cardiac, neurological, or psychiatric conditions.
- **Not a treatment:** Autonomic regulation features and the Clinical Drift Index are not substitutes for clinical therapy, psychiatric intervention, or medical supervision.
- **Unvalidated thresholds:** The clinical thresholds in the Clinical Bridge and CDI are derived from published literature but have not been validated in controlled clinical trials using this specific implementation. This is the explicit objective of Milestone 1.

---

## 4. Known Technical Limits — Stated Explicitly

The following limitations are acknowledged by the White Branch and are not design oversights. They are honest statements about what the protocol cannot currently guarantee.

### 4.1 LIMES — Proof of Life (Temporal Validity)

LIMES generates proof of human liveness from the biological entropy of the nervous system — the statistical irregularity of HRV, EEG 1/f noise, and autonomic fluctuations that current AI systems cannot synthesize with sufficient fidelity.

**This assumption has a temporal limit.** As generative AI advances, the computational distinguishability between biological entropy and synthetic entropy may decrease. The White Branch commits to reviewing the LIMES specification annually and publishing an updated threat assessment as part of the Annual Review Cycle. If the biological entropy assumption becomes clinically untenable, LIMES will require a hardware-bound entropy source (e.g., TPM-based true random number generator) rather than signal-derived entropy.

Users and implementers should understand that LIMES as currently specified is a strong defense against present-day synthetic signal generation, not a permanent cryptographic guarantee.

### 4.2 CDI — Distinguishing Protective Stress from Pathological Stress

The Clinical Drift Index monitors autonomic arousal using the Coefficient of Variation of the biometric signal envelope. High CV values can indicate both pathological stress (the condition the CDI is designed to detect) and voluntary high-intensity cognitive engagement (flow states, deliberate high-focus work, physical exercise with cognitive load).

**The CDI does not currently distinguish between these states.** A user in a state of intense voluntary concentration may generate CDI readings that trigger warnings designed for involuntary pathological drift.

Mitigation: the Voluntary Activation Mode (VAM), described in the STANDARD.md, allows a user to explicitly declare a high-intensity work session. In VAM, CDI thresholds are elevated with the user's documented consent and the session is flagged in the audit log. VAM does not disable monitoring — it recalibrates it to the user's declared context.

### 4.3 LOGOS / CIP — Empirical Uncertainty in Cognitive Offloading

The Cognitive Integrity Protocol operates on the hypothesis that sustained AI delegation erodes epistemic autonomy. The evidence for cognitive schema atrophy under AI assistance is documented (Kosmyna et al., 2025; Xu et al., 2026; Wu et al., 2025). However, the research on cognitive offloading as healthy tool extension (Clark & Chalmers, 1998; Hutchins, 1995) documents equally that humans routinely extend cognition into external tools without capability loss.

**The line between healthy delegation and pathological dependency is not resolved in the scientific literature.** The LOGOS thresholds (DI > 0.60 for Level 1 warning, DI > 0.85 for Level 3 block) are clinically informed but not empirically validated in the context of human-AI interaction specifically. The CIP specification acknowledges this and designates threshold validation as an explicit open research question.

The Delegation Index is a monitoring instrument, not a judgment. All LOGOS interventions are graduated, transparent to the user, and reversible at the user's discretion (sovereignty clause).

---

## 5. The Operator Threat Model

The protocol protects users from AI agents that operate against their interests. It does not automatically protect users from human operators who deploy the protocol in bad faith.

**Identified operator risk vectors:**

- An institution requiring employees to use Cortex-certified devices for workplace monitoring, using CDI data as a performance or compliance metric.
- A clinical operator interpreting session audit logs beyond their declared purpose.
- A platform claiming Cortex compliance while implementing non-standard threshold configurations that favor engagement over clinical safety.

**Current mitigations:** Anti-Capture Provisions (GOVERNANCE.md Section 5), Module Boundary Discipline, and the White Branch veto over threshold modifications.

**Acknowledged gap:** These mitigations are institutional, not cryptographic. A technically compliant implementation operated by an institution with misaligned incentives remains a risk that governance provisions alone cannot eliminate.

**Planned mitigation (Milestone 2+):** User-Verifiable Audit Protocol — a mechanism by which the user can independently verify, at any time, that the active implementation is operating within the parameters that were declared to them. This is distinct from what Governance Nodes can verify — it is verification by the person whose data is at stake.

---

## 6. Liability

1. **Hardware risk:** The protocol allows orchestration of local hardware (GPU, NPU, DSP, biometric sensors). The user assumes all risk regarding hardware stability. The protocol is not liable for hardware damage.
2. **Data responsibility:** While the protocol mandates local execution, the user is responsible for the security of their local environment.
3. **No professional relationship:** Use of the protocol does not establish a therapist-client or doctor-patient relationship with contributors or Governance Nodes.
4. **Research status:** All clinical modules are at research stage. Do not use in contexts requiring regulatory approval without independent clinical validation.

---

## 7. User and Implementer Agreement

By interacting with this protocol, you acknowledge:

- You will not use this protocol to process sensitive health data without appropriate legal authorization in your jurisdiction.
- You will communicate clearly to end users that this is a research protocol, not a validated clinical tool.
- You understand that sovereignty implies full responsibility for the outcomes of the technology.
- You will not use the protocol's monitoring capabilities to surveil users without their explicit, informed, and revocable consent — regardless of technical compliance status.

---

> *"A sovereignty framework that is not honest about its own limits is not a sovereignty framework. It is a new form of the problem it claims to solve."*

---

*Cortex Protocol — DISCLAIMER v1.1*
*Maintained by the White Branch under the Annual Review Cycle.*
