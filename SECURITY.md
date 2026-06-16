# 🔒 Security Policy: Cortex Protocol
### Protecting Cognitive Integrity and Data Sovereignty

Security in the Cortex Protocol is not a feature — it is the foundational layer that ensures the Sovereignty Abstraction Layer (SAL) remains uncompromised. We assume a zero-trust model: no module, agent, or external entity is trusted by default.

**This document also acknowledges what security cannot guarantee** — because a security policy that overstates its own coverage is itself a vulnerability.

---

## Security Pillars

### 1. Zero Data Exfiltration (Air-Gapped by Design)

All core functions operate without internet connectivity.

- **Local-only inference:** Intent parsing, clinical analysis, and biometric processing occur on local silicon (NPU/GPU).
- **Network kill-switch:** Any module attempting unauthorized network calls is immediately quarantined.
- **No telemetry:** The protocol does not collect usage data, error reports, or analytics by default.

### 2. Cryptographic Governance

- **Signed rulesets:** Only Clinical Capability Modules (CCMs) signed by authorized Governance Nodes can access sensitive hardware sensors.
- **Session isolation:** Per-session HMAC-SHA256 keys derived from ephemeral salts. No cross-session correlation is possible without the session salt.
- **Hardware attestation (KEROS):** In Level 3 deployments, TPM 2.0 attestation verifies that the SAL code has not been tampered with at the firmware level.

### 3. Anatomical Privacy

Biometric data is treated as an extension of the human body, not as data points.

- **Ephemeral processing:** Raw sensor data is processed in volatile memory via context manager pattern and destroyed immediately after clinical feature extraction. See `RawBiometricFrame.__exit__()`.
- **Encryption at rest:** Any persistent configuration or long-term clinical trends must be encrypted with user-only keys stored in the device's Secure Enclave.
- **Memory zeroing:** `data.fill(0)` is called deterministically on context manager exit — not deferred to garbage collection.

### 4. Operator Security Boundary

The protocol protects users from malicious AI agents. It provides reduced — but not zero — protection against malicious human operators.

**What cryptographic measures cover:**
- Raw biometric data cannot be transmitted externally without breaking the SAL architecture.
- Tensors cannot be reversed to raw values without the session salt.
- CCMs cannot be forged without a Governance Node's GPG private key.

**What cryptographic measures do NOT cover:**
- An operator who configures non-standard CDI thresholds to reduce sensitivity.
- An operator who uses technically compliant audit logs for unauthorized purposes.
- An operator who presents consent requests to users in states of reduced capacity.

These risks are addressed by institutional governance (GOVERNANCE.md §5) and the planned User-Verifiable Audit Protocol (UVAP, Milestone 2) — not by cryptography alone.

---

## Threat Model

| Threat | Defense | Coverage |
| :--- | :--- | :--- |
| Cloud exfiltration of biometric data | Hard-coded prohibition; SAL boundary enforcement | ✅ Architectural |
| Cross-session re-identification via tensors | Per-session ephemeral salt; HMAC-SHA256 | ✅ Cryptographic |
| Module collusion / cross-module data leak | Module Isolation (MODULE-ISOLATION.md); namespaced boundaries | ✅ Architectural |
| Replay attack on LIMES proof | Nonce store + proof TTL (30s default) | ✅ Implemented |
| Synthetic signal spoofing of LIMES | Biological entropy assumption (see §Known Limits) | ⚠️ Temporally bounded |
| Sensor spoofing with uncertified hardware | Certification handshake; hardware whitelist | ✅ Implemented |
| Memory forensics on raw biometric data | Deterministic zeroing via context manager | ✅ Implemented (not hardware-grade) |
| SAL code tampering | KEROS PCR quote (Level 3 only) | ⚠️ Level 3 only |
| Malicious operator (human) | Institutional governance + UVAP (planned) | ⚠️ Partially mitigated |
| Ethical drift in Governance Nodes | Annual Review Cycle; mandatory citation | ⚠️ Institutionally mitigated |
| Prompt injection in Acolyte context | Semantic Boundary Validator (planned) | ❌ Not yet implemented |

---

## Known Security Limits — Stated Explicitly

### Memory Zeroing is Not Cryptographic Erasure

`data.fill(0)` zeroes the NumPy array in Python-managed memory. On systems with memory-mapped files, swap partitions, or copy-on-write kernels, zeroed memory may persist on disk. Production deployments in high-threat environments should integrate OS-level secure memory (`mlock`, `SecureZeroMemory` on Windows) or hardware-backed Trusted Execution Environments (OP-TEE, Intel TDX).

### LIMES Entropy Assumption Has a Temporal Limit

The LIMES proof of liveness relies on the statistical distinguishability of biological entropy from synthetic entropy. This assumption is currently valid. It is subject to annual review by the White Branch and may require hardware-bound entropy sources (TPM TRNG) as generative AI advances. See STANDARD.md §2.6 and DISCLAIMER.md §4.1.

### Prompt Injection is Not Currently Defended

Prompt injection — adversarial instructions embedded in content that the Acolyte processes — is classified as the top LLM application vulnerability (OWASP LLM Top 10, 2025). The current protocol does not include a Semantic Boundary Validator. This is a known gap, planned for Milestone 2.

### The 5-Second Timestamp Window in KEROS

The current KEROS reference implementation uses a 5-second timestamp freshness window for seal verification. This is too strict for sequential demonstration use and too loose for high-security production deployments. The White Branch will define domain-specific timestamp windows in CIT specifications.

---

## Vulnerability Reporting

**Do not report security vulnerabilities as public Issues.**

If you discover a vulnerability that could compromise user sovereignty or clinical safety:

1. Open a **private** GitHub Security Advisory.
2. Include: detailed description, affected component, proof of concept if available.
3. Protocol Stewards will acknowledge within 72 hours and work on a local-first patch.
4. Vulnerabilities affecting Clinical Bridge thresholds or CDI logic require White Branch review before patch release.

---

## Security Audit Process

Unlike traditional software, Cortex Protocol security audits include a **Clinical Audit**:

- **Engineering review:** Memory safety, IPC security, cryptographic strength, timing attacks.
- **Clinical review:** Ensuring security patches do not accidentally override safety margins defined in the Clinical Bridge.
- **Governance review:** Ensuring patches do not introduce operator capabilities that violate Anti-Capture Provisions.

All three reviews are required for patches affecting Sections 2.1–2.7 of STANDARD.md.

---

## Security Principles Summary

| Principle | Implementation | Coverage |
| :--- | :--- | :--- |
| Zero-Trust | Process isolation + GPG-signed interfaces | ✅ |
| User-Only Keys | Keys never leave local hardware secure storage | ✅ |
| Transparency | All security logic is open-source and auditable | ✅ |
| Biological Safety | Security triggers activate if physiological stress thresholds are breached | ✅ |
| Honest Limits | Known gaps documented and dated | ✅ |

---

> *"Security is not what protects the system from the user. It is what protects the user from everyone else — including the system's own creators. And it is honest about what it cannot yet protect against."*

---

*Security Policy v1.1 — Cortex Protocol.*
*Maintained by Protocol Stewards. Clinical patches require White Branch approval.*
