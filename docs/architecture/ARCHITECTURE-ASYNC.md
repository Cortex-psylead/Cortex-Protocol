## Asynchronous Architecture: Solving the Biological-AI Latency Asymmetry

**Document ID: ARCH-ASYNC-001 | Version: 1.0**
**Relates to:** [ARCHITECTURE.md](ARCHITECTURE.md) — extends the Sovereignty Loop section.

---

## The Problem: Speed Asymmetry

The Cortex Protocol mediates between two systems that operate at fundamentally different timescales:

| System | Timescale | Example |
| :--- | :--- | :--- |
| AI agent (Acolyte) | Milliseconds | Token generation, inference, response |
| Biometric sensor (HRV, GSR) | Seconds | Heart rate update, HRV window calculation |
| Governance Node validation | Minutes to hours | Policy snapshot refresh |

**If the AI pipeline waits for synchronous biometric validation on every request, the system becomes unusable.** A 2-second HRV update cycle would introduce 2-second latency into every AI interaction. At scale, this collapses the user experience and defeats the protocol's purpose.

This is a known architectural constraint, not an oversight. This document specifies the required solution.

---

## The Solution: Three Non-Negotiable Design Decisions

### Decision 1 — Separated Threads (Async Processing)

The AI pipeline and the biometric reader run in completely independent threads or processes. They never block each other.
