# ROADMAP-CLINICAL.md
# Cortex Protocol — Sovereign Dual-Channel Telemetry Architecture
**Specification Version:** 1.0-draft  
**Status:** Milestone 1 Design Specification  
**Scope:** Extension of `ARCHITECTURE.md` and `ROADMAP.md` for clinical and research data routing  
**Relation to Pentagon:** CORTEX extension — outbound data sovereignty  
**Authors:** Cortex Protocol Core Team  
**Governance Authority:** White Branch (Research & Sustainability Committee)  

---

## 1. Executive Summary

Milestone 0 established the Cortex Protocol as a **passive biological circuit breaker**: a middleware that intercepts biometric signals, validates user physiological capacity, and controls the flow of information *into* AI agents.

Milestone 1 extends the protocol to control the flow of information **out** of the edge device and into two distinct downstream destinations, each with independent privacy, consent, and key lifecycle requirements.

This extension is named the **Sovereign Telemetry Layer (STL)**. It is architecturally positioned within CORTEX (the SAL's outbound routing stage) and is subject to the same Pentagon sovereignty rules: no data leaves the device without an active ETHOS consent record, and the user can sever any outbound channel instantly and irreversibly.

The extension introduces two parallel channels:

| Channel | Destination | Privacy Model | Termination Mechanism |
|---------|-------------|---------------|-----------------------|
| **DeSci** | Federated research databases | Mathematical anonymization (no keys, no PII) | Channel close |
| **Clinical** | Hospital / specialist system | E2EE pseudonymization (X25519 + ChaCha20-Poly1305) | Key zeroization |

---

## 2. Architecture Position

### 2.1 Position in the existing SAL pipeline

The STL integrates into `ingest_raw_data()` as **Step 11** — after all existing CDI validation, consent gating, and frame destruction steps:
