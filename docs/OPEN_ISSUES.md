# Open Technical Issues — Cortex Protocol

**Document ID:** OPEN-ISSUES-001 | **Maintained by:** Protocol Stewards + White Branch
**Status:** Living document — updated each milestone

This document consolidates all known technical gaps, open research questions, and
implementation risks identified through code audits and peer review.
It complements DISCLAIMER.md and is the engineering complement to governance risks
documented in GOVERNANCE.md §5.

---

## Priority 1 — Blocking for Clinical Deployment

### [OI-001] CDI Thresholds Unvalidated on Real Populations

**Component:** CORTEX — Clinical Drift Index
**Status:** Open — Milestone 1 deliverable

The CDI thresholds (CV < 0.3 ventral vagal, hard-block at 3 violations, soft-block at 5)
are derived from HRV literature but have not been validated with this specific implementation
on real human participants.

**Known false positive risk:** Athletes with chronically high vagal tone, users with benign
arrhythmias (e.g., respiratory sinus arrhythmia), or meditation practitioners may trigger
CDI blocks under normal healthy operation.

**Mitigation in current code:** Voluntary Activation Mode (VAM) allows users to declare
high-intensity sessions with elevated thresholds. This reduces but does not eliminate
the false positive risk.

**Required action:** Controlled study with ≥ 20 participants comparing CDI readings
against gold-standard RMSSD from certified cardiac sensors. Target: r ≥ 0.70 correlation.

---

### [OI-002] Art. 19.3 Negative Feedback Loop Risk

**Component:** KEROS — Hardware Isolation / Resuscitation Protocol
**Status:** Open — requires White Branch clinical design

The Art. 19.3 biometric unlock mechanism (120s continuous HF HRV in normal window)
has an unmitigated negative feedback loop risk:
