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

```
ingest_raw_data() pipeline (cognitive_shield_v2.py):

  Step 1-2:   Sensor cert + CDI pre-check
  Step 3:     ETHOS consent gate (BIOMETRIC scope)
  Step 4a-4e: Phase A extraction → Clinical Bridge → LIMES → Phase B
  Step 5:     Raw frame zeroed (context manager)
  Step 6-7:   CDI update → ETHOS dysregulation check
  Step 8-9:   Baseline update → BiometricStateMachine transition
  Step 10:    Audit log append
  ─────────────────────────────────────────────────────
  Step 11:    TelemetryRouter.route()  ← STL ENTRY POINT
                ├── DeSciChannel.emit()     [if DESCI consent active]
                └── ClinicalChannel.emit() [if CLINICAL consent active]
```

### 2.2 Pentagon compliance

The STL does not add a new Pentagon vertex. It extends CORTEX's sovereignty question — *"who controls the data flow?"* — into the outbound direction. The boundaries are:

- **ETHOS** owns all consent decisions (which channels are active, when they are revoked).
- **KEROS** owns all key material (TPM attestation seals, session key generation in Secure Enclave in production).
- **CORTEX / STL** owns routing logic only — it constructs payloads and delegates to transport adapters.
- **GOVERNANCE** validates all downstream endpoints (hospital public keys, federated DB certificates) via signed snapshots before they are registered.

---

## 3. DeSci Channel — Anonymous Research Donation

### 3.1 Purpose

The DeSci channel enables users to voluntarily donate anonymized biometric feature vectors to federated, open-access research databases maintained by partner universities (initial target: Universidad Santiago de Cali, Colombia) for validation of the Clinical Drift Index (CDI) across diverse populations.

### 3.2 Privacy model: mathematical anonymization

The DeSci channel applies a two-stage lossy projection before any data leaves the device:

**Stage 1 — Phase A feature derivation** (already performed by SAL):
```
raw_signal → Hilbert envelope → [mean, std, p25, p75, max]  (5 floats)
```

**Stage 2 — DeSci projection** (performed by `DeSciPayload.from_phase_a_features()`):
```
Phase A features → FFT magnitude spectrum (16 bins) → normalized 8-bin histogram
                   [spectral_entropy_density_matrix]

Phase A coherency → rolling 60s CV aggregate
                    [rmssd_aggregate_cv]

Polyvagal state string → ordinal bucket {0, 1, 2}
                         [polyvagal_bucket]
```

The projection is **non-invertible**: the 8-bin histogram cannot reconstruct the original 5 Phase A features, and the Phase A features cannot reconstruct the raw signal. This is the mathematical anonymization guarantee.

**What is NOT included in the DeSci payload:**
- Session identifiers or cryptographic signatures
- Timestamps (only a monotonic sequence counter with no epoch reference)
- Sensor identifiers or hardware fingerprints
- Any KEROS attestation material
- IP addresses or network metadata (stripped at transport layer)

### 3.3 k-Anonymity enforcement (federated node responsibility)

The receiving federated database node is contractually required (Governance Node CCM specification) to enforce k-anonymity ≥ 5 before any vector is queryable: a submitted vector is held in a staging buffer until at least 5 statistically similar vectors from distinct sessions have been received. The Cortex Protocol client does not implement k-anonymity locally — it is a federated node obligation.

### 3.4 Data structure

```python
@dataclass
class DeSciPayload:
    spectral_entropy_bins: np.ndarray  # shape (8,), float32
    rmssd_aggregate_cv:    float        # rolling coherency CV
    polyvagal_bucket:      int          # 0=ventral, 1=sympathetic, 2=dorsal
    sequence_counter:      int          # monotonic, no epoch
    schema_version:        str          # "desci-v1.0"
```

Binary serialization: `[4-byte counter][32-byte bins][4-byte CV][1-byte bucket]` = 41 bytes per frame.

### 3.5 Channel lifecycle

```
ETHOS.request_consent(DESCI) → DeSciChannel.ACTIVE
                                  ↓ (CDI WARNING)
                              DeSciChannel.SUSPENDED  (data quality insufficient)
                                  ↓ (CDI SAFE)
                              DeSciChannel.ACTIVE
                                  ↓ (CDI BLOCKED or ETHOS veto)
                              DeSciChannel.CLOSED  ──→ no further emission possible
```

Closed is a terminal state. Re-opening requires a new ETHOS consent grant.

---

## 4. Clinical Channel — E2EE Telemedicine Stream

### 4.1 Purpose

The Clinical channel enables real-time physiological monitoring by a validated medical provider (hospital, GP, specialist) using the user's encrypted biometric features. The medical provider can integrate the stream into their clinical information system for preventive monitoring, chronic condition management, or therapeutic support.

### 4.2 Privacy model: pseudonymized E2EE

The Clinical channel applies **pseudonymization** (not anonymization) — the medical provider can identify the patient within a session via their own clinical records, but:

- The Cortex Protocol never transmits patient identity. The linking of session data to patient identity is done within the hospital system, not in the stream.
- Each session uses a fresh random **session pseudonym** (16-byte random token). If the session key is zeroized, the pseudonym rotates — the next session is cryptographically unlinkable to the previous one.
- All biometric content is **end-to-end encrypted** using the hospital's public key. The Cortex Protocol client, the transport adapter, and all intermediary nodes are unable to decrypt the payload.

### 4.3 Cryptographic design

#### Key establishment: X25519 ECDH

```
Client (edge device):
  local_private  ← X25519PrivateKey.generate()
  local_public   → [transmitted to hospital during session init]

Hospital:
  hospital_private  [stored in hospital HSM]
  hospital_public   → [registered with Governance Node, signed CCM]

Shared secret:
  shared = local_private.exchange(hospital_public_key)

Derived key (HKDF-SHA256):
  derived_key = HKDF(
      algorithm=SHA256(),
      length=32,
      salt=None,
      info=b"cortex-clinical-stream-v1"
  ).derive(shared)
```

The `info` string binds the derived key to this protocol context, preventing cross-context key reuse.

#### Payload encryption: ChaCha20-Poly1305 AEAD

```
For each clinical frame:
  nonce      = secrets.token_bytes(12)  # 96-bit random nonce per frame
  plaintext  = phase_a_features.tobytes() + struct.pack(">d", timestamp)
  ciphertext = ChaCha20Poly1305(derived_key).encrypt(nonce, plaintext, aad=None)
  wire_frame = nonce + ciphertext  # [12 bytes nonce][N+16 bytes AEAD ciphertext]
```

ChaCha20-Poly1305 provides both confidentiality and authentication. The AEAD tag (16 bytes) detects any tampering in transit.

#### Why X25519 + ChaCha20-Poly1305 over RSA/AES

- **X25519**: Curve25519 ECDH provides 128-bit security with 32-byte keys. No parameter negotiation, no padding oracle vulnerabilities, forward secrecy per session.
- **ChaCha20-Poly1305**: Constant-time on all architectures, including ARM edge devices without AES-NI hardware. AES-GCM is faster on x86 with hardware acceleration but vulnerable to nonce reuse; ChaCha20-Poly1305 is more robust to implementation errors in constrained environments.
- **HKDF**: Standard key derivation with domain separation via `info` label, following RFC 5869.

### 4.4 Session key data structure

```python
class ClinicalSessionKey:
    _private_key:  X25519PrivateKey  # Discarded after bind()
    _derived_key:  bytes             # 32-byte ChaCha20 key
    _state:        SessionKeyState   # ACTIVE | ZEROIZED
    _created_at:   float             # Unix timestamp
    KEY_TTL_SECONDS: int = 14400     # 4 hours (White Branch mandate)
```

### 4.5 KEROS integration (Milestone 1.5, TPM 2.0 required)

In Milestone 1 PoC, KEROS attestation seals are optional (`keros_seal_bytes=None`). In production (Milestone 1.5+), each clinical frame includes a TPM PCR16 quote proving:

1. The frame originated from a certified edge device.
2. The SAL code measurement matches the signed Governance Node hash.
3. The frame was not modified after sealing.

This provides the hospital with a hardware-rooted chain of custody for each biometric frame.

```
Clinical frame wire format (with KEROS):
  [2-byte pseudonym_len][16-byte session_pseudonym]
  [2-byte seal_len][N-byte KEROS seal]
  [4-byte frame_sequence]
  [12-byte nonce][M+16-byte AEAD ciphertext]
```

---

## 5. Zeroization Protocol — The Sovereignty Enforcement Mechanism

### 5.1 Definition

**Zeroization** is the deterministic destruction of session key material, rendering all previously transmitted clinical data undecryptable and severing the hospital's ability to receive new frames. It is the primary neuro-rights enforcement action at the data level.

Zeroization is triggered by any of the following events:

| Event | Trigger | Scope |
|-------|---------|-------|
| CDI hard block | `BiometricStateMachine → "BLOCKED"` | Clinical + DeSci |
| ETHOS veto (physiological) | `ConsentCapacity → NONE` | Clinical + DeSci |
| User explicit veto | `ETHOS.revoke_consent(CLINICAL)` | Clinical only |
| Key TTL expiry | `time.time() - created_at > KEY_TTL_SECONDS` | Clinical only |
| Judicial Kill Switch | `CognitiveShield.destroy_session()` | Clinical + DeSci + audit log |

### 5.2 Zeroization sequence

The sequence is strictly ordered. All steps execute before `ClinicalChannel` returns to the caller:

```
1. ClinicalSessionKey._derived_key:
   key_arr = bytearray(derived_key)
   for i in range(len(key_arr)): key_arr[i] = 0
   self._derived_key = None

2. ClinicalSessionKey._private_key = None
   (X25519PrivateKey reference released — GC will collect)

3. ClinicalSessionKey._state = SessionKeyState.ZEROIZED

4. TransportAdapter.close()
   (TCP socket FIN/RST — hospital connection terminated at transport layer)

5. ClinicalChannel._session_pseudonym = secrets.token_bytes(16)
   (New pseudonym generated — next session is unlinkable)

6. ClinicalChannel._state = ChannelState.CLOSED

7. ZeroizationEvent appended to audit log:
   {"event": "ZEROIZED", "reason": reason, "timestamp": ..., "age_seconds": ...}
   (No key material in log)
```

### 5.3 CPython memory caveat and production mitigation

Python `bytes` objects are immutable and may persist in the CPython GC heap until collected. The zeroization above overwrites the `bytearray` copy but cannot guarantee the original `bytes` object from the HKDF output is collected immediately. This is a known limitation of CPython that affects all pure-Python cryptographic implementations.

**Production mitigation (Milestone 1.5):** The `_derived_key` must be stored in a TPM 2.0 Secure Enclave or ARM TrustZone TEE via KEROS. The derived key never enters the Python heap — all encryption operations are performed inside the Secure Enclave, and zeroization is a hardware `TPM2_FlushContext()` call. This eliminates the GC residue problem entirely.

Until KEROS hardware integration is complete, the protocol MUST include the following notice in any clinical deployment agreement:

> *"Key zeroization is implemented at the application layer with best-effort memory clearing. Residual key material may persist in the operating system heap until garbage collection. Production deployment in regulated clinical environments requires TPM 2.0 / Secure Enclave hardware."*

---

## 6. Consent Scopes — ETHOS Extension

Milestone 1 adds two new `ConsentScope` values to `EthosEngine`:

```python
class ConsentScope(Enum):
    BIOMETRIC = "biometric"      # existing — M0
    ACOLYTE   = "acolyte"        # existing — M0
    AUDIO     = "audio"          # existing — M0
    LOCATION  = "location"       # existing — M0
    DESCI     = "desci"          # NEW — M1: anonymous research donation
    CLINICAL  = "clinical"       # NEW — M1: E2EE hospital telemedicine
```

Consent for `DESCI` and `CLINICAL` is:
- Independent of `BIOMETRIC` consent — a user can enable the Acolyte (BIOMETRIC) without donating to research (DESCI) or enabling hospital monitoring (CLINICAL).
- Revocable independently — revoking CLINICAL does not affect DESCI.
- Subject to the same physiological capacity gate as all other ETHOS consents: `ConsentCapacity.NONE` prevents new consent grants and triggers auto-revocation of active CLINICAL consents.

---

## 7. Regulatory Compliance Framework

### 7.1 Colombia — Ley 1581/2012 (Habeas Data) + Ley 1751/2015 (Derecho a la Salud)

| Requirement | STL Mechanism |
|-------------|---------------|
| Autorización previa y expresa | ETHOS consent gate with explicit `request_consent(CLINICAL)` |
| Datos sensibles (biométricos, salud) | E2EE — only hospital can decrypt; SAL never transmits cleartext |
| Derecho de supresión | Key zeroization = instant data access revocation |
| Finalidad determinada | Separate consent scopes for DESCI vs CLINICAL |

### 7.2 European Union — GDPR Article 9 (Special Category Data) + Article 17 (Right to Erasure)

| Requirement | STL Mechanism |
|-------------|---------------|
| Explicit consent for health data | ETHOS double-confirmation for LIMITED capacity grants |
| Data minimization | DeSci projection is non-invertible; Clinical transmits only feature vectors |
| Right to erasure | Zeroization severs access; session pseudonym rotation prevents correlation |
| Technical measures (Art. 32) | X25519 + ChaCha20-Poly1305 + KEROS TPM attestation |

### 7.3 United States — HIPAA (if US hospital)

The Cortex Protocol does not store Protected Health Information (PHI) on the edge device. If the hospital receiving the Clinical stream is a HIPAA covered entity, the hospital is responsible for BAA (Business Associate Agreement) compliance on their receiving infrastructure. The protocol's role ends at the encrypted wire frame.

---

## 8. Milestone 1 Deliverables

### 8.1 Code deliverables

| File | Status | Description |
|------|--------|-------------|
| `src/sal/telemetry_router.py` | ✅ Implemented (M1 PoC) | TelemetryRouter, DeSciChannel, ClinicalChannel, ClinicalSessionKey |
| `src/sal/cognitive_shield_v2.py` | ✅ Implemented (M1 PoC) | Step 11 integration point documented |
| `src/ethos/ethos_consent.py` | 🔧 Extend | Add `DESCI` and `CLINICAL` ConsentScope values |
| `src/governance/policy_validator.py` | 🔧 Extend | Validate hospital public key against Governance Node CCM |

### 8.2 Governance deliverables

| Deliverable | Owner | Dependency |
|-------------|-------|------------|
| Clinical Capability Module (CCM) v1 spec | White Branch | Milestone 1 governance |
| Hospital public key registry format | Research Committee | CCM v1 |
| DeSci federated DB node specification | White Branch | Universidad Santiago de Cali partnership |
| k-Anonymity enforcement contract template | Legal | Colombia data protection counsel |

### 8.3 Clinical validation deliverables

| Deliverable | Target | Metric |
|-------------|--------|--------|
| CDI validation study (HRV correlation) | ≥ 20 participants | r ≥ 0.70 vs. RMSSD |
| DeSci pilot donation (anonymized vectors) | ≥ 100 sessions | k-anonymity groups formed |
| Clinical stream pilot (hospital partner) | ≥ 1 Colombian hospital | ETHOS consent lifecycle validated |

---

## 9. Technical Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CPython GC residual key material | HIGH (certain in PoC) | HIGH | TPM 2.0 KEROS integration (M1.5) — mandatory for regulated deployment |
| Hospital network latency affecting Clinical stream | MEDIUM | MEDIUM | Non-blocking emission queue; dropped frames are acceptable (monitoring, not life-critical) |
| Federated DB k-anonymity bypass | LOW | HIGH | Governance Node CCM contract; local k-anonymity pre-filter as defense-in-depth |
| DeSci dataset re-identification via spectral bins | LOW | HIGH | White Branch annual entropy analysis; bins are lossy — review if AI re-ID capability advances |
| X25519 key compromise at hospital | LOW | HIGH | Key TTL (4h) limits exposure window; KEROS TPM prevents client-side compromise |
| ETHOS veto not reaching TelemetryRouter | LOW | CRITICAL | Router subscribes to state machine — zeroization is triggered by state, not by caller convention |

---

## 10. Technology Horizon: Sovereign Telemetry in 2030–2040

The following section documents the technology trajectory that informs the STL design decisions. These are not implementation commitments — they are the environmental assumptions that make the architecture viable at scale.

### 10.1 Edge hardware convergence

Current (2025): Cortex Protocol runs on mobile hardware (smartphone NPU, external BLE sensors). TPM 2.0 is standard on laptops; rare on mobile.

Near-term (2027–2029): ARM TrustZone + eSE (embedded Secure Element) becomes standard on flagship smartphones. Wearable SoCs (Qualcomm QCC5xxx, Nordic nRF9161) begin incorporating hardware secure enclaves. The KEROS layer transitions from simulated to hardware-backed transparently.

Medium-term (2030–2033): Neural interface wearables (next-generation Muse, OpenBCI successors, EarEEG form factors) incorporate TPM-equivalent secure silicon at the sensor level. The sensor-to-SAL Challenge-Response handshake operates entirely in hardware — no software simulation required.

Long-term (2035+): Implantable neural interfaces (BCI grade II) will generate continuous, high-bandwidth biometric streams. The STL architecture is designed to scale to this scenario: the DeSci projection pipeline is band-limited by design (8 bins regardless of input dimensionality), and the Clinical channel AEAD scales to arbitrary plaintext length.

### 10.2 Post-quantum cryptography migration path

X25519 is vulnerable to Harvest-Now-Decrypt-Later (HNDL) attacks if a sufficiently powerful quantum computer becomes available. The STL is designed with a migration path:

- **Milestone 2 (2027):** Hybrid key establishment: X25519 + ML-KEM-768 (FIPS 203 / CRYSTALS-Kyber). Both classical and post-quantum shared secrets are combined via HKDF. Backward-compatible with existing hospital infrastructure.
- **Milestone 3 (2029+):** Pure ML-KEM-768 once hospital infrastructure and regulatory guidance align with NIST PQC standards. ChaCha20-Poly1305 is post-quantum secure for symmetric encryption — no change required.

### 10.3 Federated learning integration

The DeSci channel, once validated across ≥ 3 federated nodes, becomes the substrate for privacy-preserving federated CDI refinement:

```
Edge device:
  Local CDI gradient computation (on anonymized vectors only)
  → Differential privacy noise injection (ε-DP, δ-DP per Governance Node spec)
  → Gradient upload via DeSci channel

Federated aggregator (university node):
  FedAvg over ε-DP gradients
  → Updated CDI model (weights, thresholds)
  → Signed CCM update package → Governance Node → client

No raw biometric data leaves the device at any point.
```

This is the technical path by which the CDI evolves from a static threshold system (M0) to a population-calibrated adaptive model (M3+) without violating individual privacy.

### 10.4 Neuro-rights regulatory convergence

Colombia (Ley 2217/2022 proposal), Chile (Constitutional reform 2021), EU (AI Act 2024), and emerging IEEE P2510 standards are converging on a common framework: biometric data generated by neural interfaces is a special category of personal data with enhanced protections. The STL architecture is designed to be the technical implementation reference for this framework:

- **ETHOS** implements the consent model required by Art. 9 GDPR and Ley 1581.
- **Zeroization** implements the technical measure for Art. 17 GDPR (right to erasure).
- **DeSci anonymization** satisfies the data minimization principle across all frameworks.
- **KEROS TPM attestation** provides the hardware-rooted audit trail required for forensic review under clinical negligence or data breach investigation.

---

## 11. Open Questions for White Branch Review

The following questions require clinical and governance input before Milestone 1 code is promoted to production:

1. **Clinical stream TTL:** Is 4 hours the correct session key lifetime for continuous monitoring? Longer TTL = better UX; shorter = better security. Requires clinical workflow analysis.

2. **DeSci donation granularity:** Should spectral bins be 8 or 16? More bins = richer research signal; fewer = stronger anonymization. Requires Privacy Impact Assessment.

3. **k-Anonymity threshold:** Is k=5 sufficient for Colombian regulatory context, or does Ley 1581 require k≥10 for health data? Requires legal review.

4. **CDI WARNING → Clinical channel behavior:** Current design keeps Clinical active during WARNING (medical priority). Is this correct? A stressed but monitored patient may not want their cardiologist to see sympathetic activation data continuously. Requires clinical ethics review.

5. **Federated DB jurisdiction:** Where should the Universidad Santiago de Cali federated node be hosted? Colombian health data sovereignty requires data to remain in-country. Requires legal and infrastructure review.

---

*This document is a living specification. All threshold values, cryptographic parameters, and regulatory interpretations are subject to White Branch review and must be versioned when changed. Changes to cryptographic primitives require a formal security review.*

*Document ID: ROADMAP-CLINICAL-001 | Version: 1.0-draft | Last updated: 2026-05-17*
