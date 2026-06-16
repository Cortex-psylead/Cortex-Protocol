# ROADMAP-CLINICAL.md
# Cortex Protocol — Sovereign Dual-Channel Telemetry Architecture
**Specification Version:** 1.1-draft  
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
| :--- | :--- | :--- | :--- |
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
Step 4a-4c: Phase A extraction → Hilbert analytical envelope descriptors [μ_A, σ²_A, S_A, K_A, H_sp]
Step 4d:    LIMES liveness verification & KEROS attestation handshake
Step 4e:    Phase B projection → Cryptographic manifold M(F) + Laplacian noise η (ε-DP)
Step 5:     Raw frame zeroed (context manager)
Step 6-7:   CDI update & mathematical mapping calculation → ETHOS boundary check
Step 8-9:   Baseline update → BiometricStateMachine transition
Step 10:    Audit log append
────────────────────────────────────────────────────────────────────────────────────
Step 11:    TelemetryRouter.route()  ← STL ENTRY POINT
├── DeSciChannel.emit()     [if DESCI consent active]
└── ClinicalChannel.emit() [if CLINICAL consent active]
```
### 2.2 Pentagon compliance
The STL does not add a new Pentagon vertex. It extends CORTEX's sovereignty question — *"who controls the data flow?"* — into the outbound direction. The boundaries are:
- **ETHOS** owns all consent decisions (which channels are active, when they are revoked based on physiological capacity).
- **KEROS** owns all key material (TPM 2.0 attestation seals, session key generation in Secure Enclave).
- **CORTEX / STL** owns routing logic only — it constructs payloads and delegates to transport adapters.
- **GOVERNANCE** validates all downstream endpoints (hospital public keys, federated DB certificates) via signed snapshots before they are registered by the White Branch.
---
## 3. DeSci Channel — Anonymous Research Donation
### 3.1 Purpose
The DeSci channel enables users to voluntarily donate anonymized biometric feature vectors to federated, open-access research databases maintained by partner universities (initial target: Universidad Santiago de Cali, Colombia) for validation of the Clinical Drift Index (CDI) across diverse populations.
### 3.2 Privacy model: mathematical anonymization
The DeSci channel applies a two-stage lossy projection before any data leaves the device:
**Stage 1 — Phase A feature derivation** (already performed by SAL):
Raw oscillations are processed via Hilbert transform to derive the complex analytic signal $Z(t) = x(t) + i\hat{x}(t) = A(t)e^{i\phi(t)}$. The resulting vector isolates the 5 foundational mathematical descriptors:
```
raw_signal → Hilbert transform envelope A(t) → [μ_A, σ²_A, S_A, K_A, H_sp] (5 floats)
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
- Session identifiers or cryptographic signatures.
- Timestamps (only a monotonic sequence counter with no epoch reference).
- Sensor identifiers or hardware fingerprints.
- Any KEROS cryptographic attestation material.
- IP addresses or network metadata (stripped at transport layer).
### 3.3 k-Anonymity enforcement (federated node responsibility)
The receiving federated database node is contractually required (Governance Node CCM specification) to enforce k-anonymity $\ge 100$ before any vector is queryable: a submitted vector is held in a staging buffer until at least 100 statistically similar vectors from distinct sessions have been received. The Cortex Protocol client does not implement k-anonymity locally — it is a federated node obligation.
### 3.4 Data structure
```python
@dataclass
class DeSciPayload:
    spectral_entropy_bins: np.ndarray  # shape (8,), float32
    rmssd_aggregate_cv:    float        # rolling coherency CV
    polyvagal_bucket:      int          # 0=ventral, 1=sympathetic, 2=dorsal
    sequence_counter:      int          # monotonic, no epoch
    schema_version:        str          # "desci-v1.1"
```
Binary serialization: [4-byte counter][32-byte bins][4-byte CV][1-byte bucket] = 41 bytes per frame.
### 3.5 Channel lifecycle
```
ETHOS.request_consent(DESCI) → DeSciChannel.ACTIVE
                                  ↓ (CDI ≥ 0.35: YELLOW ZONE)
                              DeSciChannel.SUSPENDED  (data quality insufficient)
                                  ↓ (CDI < 0.35: GREEN ZONE)
                              DeSciChannel.ACTIVE
                                  ↓ (CDI ≥ 0.70: RED ZONE or ETHOS veto)
                              DeSciChannel.CLOSED  ──→ no further emission possible
```
CLOSED is a terminal state. Re-opening requires a new, explicit ETHOS consent grant under strict cognitive homeostatic evaluation.
## 4. Clinical Channel — E2EE Telemedicine Stream
### 4.1 Purpose
The Clinical channel enables real-time physiological monitoring by a validated medical provider (hospital, GP, specialist) using the user's encrypted biometric features. The medical provider can integrate the stream into their clinical information system for preventive monitoring, chronic condition management, or therapeutic support.
### 4.2 Privacy model: pseudonymized E2EE
The Clinical channel applies **pseudonymization** (not anonymization) — the medical provider can identify the patient within a session via their own clinical records, but:
 * The Cortex Protocol never transmits patient identity. The linking of session data to patient identity is done within the hospital system, not in the stream.
 * Each session uses a fresh random **session pseudonym** (16-byte random token). If the session key is zeroized, the pseudonym rotates — the next session is cryptographically unlinkable to the previous one.
 * All biometric content is **end-to-end encrypted** using the hospital's public key. The Cortex Protocol client, the transport adapter, and all intermediary nodes are unable to decrypt the payload.
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
      info=b"cortex-clinical-stream-v1.1"
  ).derive(shared)
```
The info string binds the derived key to this protocol context, preventing cross-context key reuse.
#### Payload encryption: ChaCha20-Poly1305 AEAD
```
For each clinical frame:
  nonce      = secrets.token_bytes(12)  # 96-bit random nonce per frame
  plaintext  = phase_a_features.tobytes() + struct.pack(">d", timestamp)
  ciphertext = ChaCha20Poly1305(derived_key).encrypt(nonce, plaintext, aad=None)
  wire_frame = nonce + ciphertext  # [12 bytes nonce][N+16 bytes AEAD ciphertext]
```
ChaCha20-Poly1305 provides both confidentiality and authentication. The AEAD tag (16 bytes) detects any tampering in transit.
## 5. Zeroization Protocol — The Sovereignty Enforcement Mechanism
### 5.1 Definition
**Zeroization** is the deterministic destruction of session key material, rendering all previously transmitted clinical data undecryptable and severing the hospital's ability to receive new frames. It is the primary neuro-rights enforcement action at the data level.
Zeroization is triggered by any of the following events:

| Event | Trigger | Scope |
| :--- | :--- | :--- |
| CDI hard block | BiometricStateMachine → "BLOCKED" (CDI ≥ 0.70) | Clinical + DeSci |
| ETHOS veto (physiological) | ConsentCapacity → NONE | Clinical + DeSci |
| User explicit veto | ETHOS.revoke_consent(CLINICAL) | Clinical only |
| Key TTL expiry | time.time() - created_at > KEY_TTL_SECONDS | Clinical only |
| Judicial Kill Switch | CognitiveShield.destroy_session() | Clinical + DeSci + audit log |

### 5.2 Zeroization sequence
The sequence is strictly ordered. All steps execute before ClinicalChannel returns to the caller:
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
Python bytes objects are immutable and may persist in the CPython GC heap until collected. The zeroization above overwrites the bytearray copy but cannot guarantee the original bytes object from the HKDF output is collected immediately.
**Production mitigation (Enforceable via Rust native layers):** The _derived_key must be isolated within the bare-metal Rust module layer or stored in a TPM 2.0 Secure Enclave via KEROS. The derived key never enters the Python heap — all encryption operations are performed inside the native cryptographic layer, and zeroization is a hardware execution call. This eliminates the GC residue problem entirely.
## 6. Consent Scopes — ETHOS Extension
Milestone 1 adds two new ConsentScope values to EthosEngine:
```python
class ConsentScope(Enum):
    BIOMETRIC = "biometric"      # existing — M0
    ACOLYTE   = "acolyte"        # existing — M0
    AUDIO     = "audio"          # existing — M0
    LOCATION  = "location"       # existing — M0
    DESCI     = "desci"          # NEW — M1: anonymous research donation
    CLINICAL  = "clinical"       # NEW — M1: E2EE hospital telemedicine
```
Consent for DESCI and CLINICAL is:
 * Independent of BIOMETRIC consent — a user can enable the Acolyte (BIOMETRIC) without donating to research (DESCI) or enabling hospital monitoring (CLINICAL).
 * Revocable independently — revoking CLINICAL does not affect DESCI.
 * Subject to the same physiological capacity gate as all other ETHOS consents: ConsentCapacity.NONE prevents new consent grants and triggers auto-revocation of active CLINICAL consents.
## 7. Regulatory Compliance Framework
### 7.1 Colombia — Ley 1581/2012 (Habeas Data) + Ley 1751/2015 (Derecho a la Salud)

| Requirement | STL Mechanism |
| :--- | :--- |
| Autorización previa y expresa | ETHOS consent gate with explicit request_consent(CLINICAL) |
| Datos sensibles (biométricos, salud) | E2EE — only hospital can decrypt; SAL never transmits cleartext raw signals |
| Derecho de supresión | Key zeroization = instant data access revocation |
| Finalidad determinada | Separate consent scopes for DESCI vs CLINICAL | <br> ### 7.2 European Union — GDPR Article 9 (Special Category Data) + Article 17 (Right to Erasure)
| Requirement | STL Mechanism |
| :--- | :--- |
| Explicit consent for health data | ETHOS double-confirmation for LIMITED capacity grants |
| Data minimization | DeSci projection is non-invertible; Clinical transmits only feature vectors |
| Right to erasure | Zeroization severs access; session pseudonym rotation prevents correlation |
| Technical measures (Art. 32) | X25519 + ChaCha20-Poly1305 + KEROS TPM attestation | <br> ## 8. Technical Risk Register
| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| CPython GC residual key material | HIGH (certain in Python PoC) | HIGH | Pure Rust cryptography integration (M1.1) or TPM 2.0 KEROS hardware binding |
| Hospital network latency affecting Clinical stream | MEDIUM | MEDIUM | Non-blocking emission queue; dropped frames are acceptable (monitoring, not life-critical) |
| Federated DB k-anonymity bypass | LOW | HIGH | Governance Node CCM contract; local k-anonymity pre-filter as defense-in-depth |
| DeSci dataset re-identification via spectral bins | LOW | HIGH | White Branch annual entropy analysis; bins are lossy — review if AI re-ID capability advances |
| ETHOS veto not reaching TelemetryRouter | LOW | CRITICAL | Router subscribes directly to state machine — zeroization is triggered by state changes, not by caller convention |

## 9. Technology Horizon: Sovereign Telemetry in 2030–2040
### 9.1 Post-quantum cryptography migration path
X25519 is vulnerable to Harvest-Now-Decrypt-Later (HNDL) attacks if a sufficiently powerful quantum computer becomes available. The STL is designed with a migration path:
 * **Milestone 2:** Hybrid key establishment: X25519 + ML-KEM-768 (FIPS 203 / CRYSTALS-Kyber). Both classical and post-quantum shared secrets are combined via HKDF. Backward-compatible with existing hospital infrastructure.
 * **Milestone 3:** Pure ML-KEM-768 once hospital infrastructure and regulatory guidance align with NIST PQC standards. ChaCha20-Poly1305 is post-quantum secure for symmetric encryption — no change required.
### 9.2 Federated learning integration
The DeSci channel, once validated across \ge 3 federated nodes, becomes the substrate for privacy-preserving federated CDI refinement:
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
This is the technical path by which the CDI evolves from a static threshold system to a population-calibrated adaptive model without violating individual privacy.
*Document ID: ROADMAP-CLINICAL-001 | Version: 1.1-draft | Last updated: 2026-06-16*
```
```
