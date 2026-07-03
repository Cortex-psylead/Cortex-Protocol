# Clinical Roadmap: The Sovereign Dual-Channel Telemetry Layer

**Status: Not implemented. Milestone 1 objective (see [ROADMAP.md](ROADMAP.md)).**

This document is a stub. It exists so that the references to it from
[README.md](README.md) and [CLINICAL-BRIDGE.md](CLINICAL-BRIDGE.md) point to
something real instead of a broken link — consistent with this project's
practice of naming gaps explicitly rather than leaving them undocumented
(see DISCLAIMER.md).

## What this document will specify, once written

The **DeSci Channel** described in README.md's "For Researchers and
Universities" section, in full technical detail:

- **The non-invertible FFT transformation** applied on-device to biometric
  feature vectors before any data leaves the SAL boundary.
- **The 41-byte anonymous vector format** — its exact structure, what it
  encodes, and a formal argument (not just an assertion) for why it carries
  no timestamp, session identifier, or cryptographic signature linking it
  to an individual.
- **The zeroization protocol** for data in transit and at rest on the
  Governance Node side.
- **Regulatory compliance mapping** — how this channel satisfies GDPR
  Article 9 (special category data) and Colombia's Ley 1581/2012 in a
  research-data-sharing context specifically (as opposed to the general
  mapping already covered in USER-DATA-MODEL.md).
- **The real-time channel control mechanism** — the exact conditions and
  latency bound under which the channel closes on CDI block or consent
  revocation.

## Why this isn't written yet

Writing this specification before Milestone 0's CDI and Clinical Bridge
have real-sensor clinical validation (see CLINICAL-BRIDGE.md, Module 3 —
Validation Roadmap) would mean formalizing a data-sharing protocol for a
metric whose clinical validity is not yet established. The technical
sequencing is deliberate: validate CORTEX's core signal first, specify how
to share it with research partners second.

## Path to completion

Tracked under Milestone 1 in [ROADMAP.md](ROADMAP.md), alongside
constituting the first Governance Node (Issue #5). A Governance Node
partner is also the appropriate reviewer for this specification once
drafted, since the regulatory and zeroization requirements are exactly
the kind of claim this project does not publish unilaterally.

---

*This is a stub, not a placeholder for hype. If you are reading this
because you are evaluating the DeSci Channel for a research partnership,
the honest current state is: the architecture is described at a high
level in README.md, and the implementable specification does not exist
yet. Open an Issue tagged `[Governance-Node-Application]` to discuss
timeline and co-design.*
