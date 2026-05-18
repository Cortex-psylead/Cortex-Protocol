# Cortex Protocol: A Decentralized Framework for Cognitive Sovereignty
**White Branch Technical Specification — Version 1.1 (Milestone 0 Validated)**

---

## Abstract

The Cortex Protocol establishes a mathematically verifiable sovereignty layer between biometric sensors and artificial intelligence agents. This document specifies the clinical and technical architecture of **Milestone 0: The Cognitive Shield**, detailing the Sovereignty Abstraction Layer (SAL), the Clinical Drift Index (CDI), and the evidence base that governs every safety threshold. All parameters cited herein are derived from peer-reviewed literature and are enforceable as hardware constraints via the White Branch governance mechanism.

---

## 1. Problem Statement

The convergence of consumer neurotechnology and large-scale AI systems creates an asymmetric risk for the individual. Biometric and neurophysiological data—EEG signals, heart rate variability (HRV), galvanic skin response (GSR)—represent the most intimate stratum of personal information. Current architectures process this data in centralized infrastructure without user-side verification, creating three critical vulnerabilities:

1. **Re-identification risk:** Even aggregated physiological statistics can function as a "neural fingerprint" when correlated across sessions (Rosenblum et al., 2019).
2. **Pathological engagement:** AI systems optimizing for engagement metrics can induce sustained sympathetic nervous system activation without user awareness (Twenge et al., 2018; Haidt & Allen, 2020).
3. **Governance gap:** No current technical standard subordinates AI interaction logic to clinical safety parameters at the hardware level.

The Cortex Protocol addresses all three.

---

## 2. Governance Architecture: The Triad

The protocol is governed by three independent forces that ensure systemic balance. No single actor can unilaterally override the others.

### 2.1 White Branch (Clinical Authority)
Composed exclusively of mental health and neurobiology professionals. The White Branch holds exclusive authority to define, modify, or veto the numerical safety thresholds in `ClinicalThresholds` and `ClinicalBridge`. Any pull request modifying these values without White Branch approval is automatically rejected by governance protocol.

### 2.2 Technical Branch
Responsible for implementing the SAL and cryptographic layers. The Technical Branch may propose implementation methods but cannot override clinically mandated safety margins. Code efficiency is secondary to clinical integrity.

### 2.3 Legal Validator (Adscribed Shield)
A specialized advisory body adscribed to the Clinical Branch. The Legal Validator provides legal signatures certifying that clinical modules comply with applicable neuro-rights legislation, data protection frameworks (GDPR, Ley 1581/2012), and international standards (UNESCO 2021 AI Ethics Recommendation). The Legal Validator holds no veto over clinical methodology.

---

## 3. Technical Architecture: The Sovereignty Abstraction Layer (SAL)

### 3.1 Design Principle: Information Over Data

The SAL operates on a fundamental distinction:

- **Data:** Raw physiological measurement (e.g., EEG amplitude in µV, R-R interval in ms).
- **Information:** Derived clinical state (e.g., "ventral vagal engagement," "sympathetic activation").

The Acolyte (AI agent) receives only **information encoded as obfuscated tensors**. It never has access to the underlying data. This distinction is enforced architecturally, not by policy.

### 3.2 Hardware Certification Handshake

Before any data ingestion is permitted, the connected sensor must pass a two-stage certification:

**Stage 1 — Whitelist verification:** The sensor's identifier is checked against the White Branch's signed hardware registry.

**Stage 2 — Quality threshold verification:** The sensor must meet minimum acquisition standards derived from event-related potential methodology literature (Luck, 2014):

| Parameter | Minimum Requirement | Clinical Rationale |
| :--- | :--- | :--- |
| Signal-to-Noise Ratio | ≥ 30.0 dB | Below this threshold, artifact-to-signal contamination prevents reliable autonomic state classification |
| ADC Resolution | ≥ 12 bits | Minimum to resolve EEG microvolt-range amplitudes (typical scalp EEG: 10–100 µV) |
| Sampling Rate (HRV) | ≥ 250 Hz | Required for accurate R-R interval detection enabling RMSSD computation (Task Force, 1996) |

Sensors failing either stage are rejected before a single byte of biometric data enters the processing pipeline.

### 3.3 Two-Phase Tensor Transformation

The transformation from raw signal to anonymous tensor is executed in two strictly separated phases. This separation is the core architectural decision that makes clinical validation meaningful.

**Phase A — Clinical Feature Extraction (interpretable)**

Raw EEG data (normalized to clinical range: −50 µV to +50 µV) is processed through a Hilbert transform to extract the signal envelope. Five statistical descriptors are computed:

```
features = [
    mean(envelope),          # f₀: mean activation
    std(envelope),           # f₁: variability ← polyvagal calm marker
    percentile(envelope,25), # f₂: lower bound
    percentile(envelope,75), # f₃: upper bound ← sympathetic activation marker
    max(envelope)            # f₄: peak ← acute stress spike marker
]
```

These values are **clinically interpretable** and are the inputs to the Clinical Bridge validation.

**Phase B — Privacy Obfuscation (irreversible)**

After clinical validation passes on Phase A features, HMAC-SHA256 is applied:

```
hmac_digest = HMAC(key=session_salt, msg=features.bytes + sensor_hash, alg=SHA256)
anonymous_tensor = hmac_digest_bytes × features  # magnitude-preserving obfuscation
```

The `session_salt` is a 32-byte cryptographically random value generated at session initialization (`secrets.token_bytes(32)`) and destroyed at session end. Without the salt, the anonymous tensor cannot be reversed to recover Phase A features.

**Critical constraint:** The Acolyte receives only Phase B output. The Clinical Bridge validates only Phase A output. These are computationally isolated operations.

### 3.4 Ephemeral Memory Protocol

Raw biometric frames exist in memory for the minimum possible duration. The `RawBiometricFrame` class implements the context manager protocol (`__enter__` / `__exit__`), guaranteeing deterministic memory zeroing:

```python
with RawBiometricFrame(sensor_hash, timestamp, raw_data.copy()) as frame:
    features = extract_clinical_features(frame.data)
# frame.data.fill(0) is guaranteed here — not deferred to garbage collection
```

The use of `__del__` for this purpose was explicitly rejected because CPython provides no execution guarantees for `__del__` in the presence of reference cycles or interpreter shutdown sequences.

---

## 4. Clinical Drift Index (CDI): Operationalization

The CDI is the protocol's primary defense against what we term a "Malicious Acolyte"—an AI agent that induces pathological behavioral or neurophysiological states through prolonged, low-intensity manipulation rather than acute attack.

### 4.1 Theoretical Basis

The CDI operationalizes three converging frameworks:

**Polyvagal Theory (Porges, 2011):** Defines three hierarchical autonomic states—ventral vagal (social engagement, safety), sympathetic (mobilization, stress), and dorsal vagal (immobilization, shutdown). The Clinical Bridge thresholds map these states to measurable signal parameters.

**Window of Tolerance (Siegel, 1999; Ogden et al., 2006):** The range of autonomic arousal within which an individual can process information without entering hyperactivation (panic, dissociation trigger) or hypoactivation (numbing, disconnection). The CDI monitors for drift outside this window over time.

**HRV as Autonomic Biomarker (Task Force, 1996; Thayer et al., 2012):** High-frequency HRV power and RMSSD (Root Mean Square of Successive Differences) are the most validated non-invasive indices of parasympathetic nervous system activity. Reduced HRV correlates with sympathetic dominance, stress pathology, and reduced cognitive flexibility.

### 4.2 Coherency Index: Definition and Justification

The coherency index is computed as the **Coefficient of Variation (CV)** of the Hilbert-transformed signal envelope:

```
CV = std(envelope) / mean(envelope)
```

This metric is grounded in the HRV literature as a normalized index of variability independent of absolute signal amplitude. Higher CV indicates greater signal irregularity, corresponding to higher autonomic arousal. In resting ventral vagal states, CV is typically < 0.3; sympathetic engagement produces CV in the 0.3–0.7 range; acute stress or artifactual spike contamination produces CV > 0.7.

**Polyvagal State Mapping:**

| CV Range | Autonomic State | Polyvagal Classification | CDI Response |
| :--- | :--- | :--- | :--- |
| CV < 0.3 | Low arousal, stable | Ventral vagal (safe) | Green — no action |
| 0.3 ≤ CV < 0.7 | Moderate arousal | Sympathetic engagement | Yellow — monitoring |
| CV ≥ 0.7 | High arousal or artifact | Sympathetic surge / dorsal vagal | Red — block candidate |

### 4.3 Dual-Threshold Detection

The CDI employs two independent detection mechanisms to address different manipulation timescales:

**Hard Threshold (absolute clinical limit):**
- Window: 60-second sliding window
- Threshold: cumulative CV sum > 2.5 within window
- Block trigger: 3 hard violations
- Rationale: Prevents acute sympathetic overload within a session

**Soft Threshold (statistical Z-score from personal baseline):**
- Baseline: established from first 7 sessions (minimum 3)
- Trigger: |CV − baseline_mean| / baseline_std > 3.0 (3 standard deviations)
- Block trigger: 5 soft violations
- Rationale: Detects chronic drift invisible to absolute thresholds; personalizes detection to individual neurophysiology

The baseline personalization is critical. A person with high baseline autonomic variability (e.g., an athlete with high resting HRV) would generate false positives under a universal absolute threshold. The Z-score mechanism ensures the CDI is calibrated to the individual, not a population average.

**Separation of violation counters:**
Hard and soft violations are tracked independently with distinct thresholds (`HARD_BLOCK = 3`, `SOFT_BLOCK = 5`), reflecting the difference in confidence level between an absolute threshold breach and a statistical deviation.

### 4.4 Clinical Bridge Thresholds: Evidence Basis

| Feature | Threshold | Clinical Interpretation | Reference |
| :--- | :--- | :--- | :--- |
| std(envelope) ≤ 0.5 | Envelope stability | Parasympathetic dominance; ventral vagal state | Dana (2018); Porges (2011) |
| p75(envelope) ≤ 0.7 | 75th percentile activation | No sustained sympathetic surge | Shaffer & Ginsberg (2017) |
| max(envelope) ≤ 0.9 | Peak spike | No acute stress spike; no flight/fight trigger | Ogden et al. (2006) |

Exceeding any single threshold at the feature level triggers an immediate Clinical Bridge block before the Acolyte processes the session.

---

## 5. Security Properties

### 5.1 Session Salt Isolation
Each `CognitiveShield` instance generates a unique 32-byte session salt. Tensors from different sessions are cryptographically incomparable. Cross-session re-identification via tensor comparison is computationally infeasible without the salt.

### 5.2 Sensor Hash Chaining
The sensor's SHA-256 hash is incorporated into the HMAC key derivation (`HMAC(salt, features.bytes + sensor_hash)`). This binds each tensor to a specific certified sensor, enabling forensic traceability of the sensor used without exposing sensor identity to the Acolyte.

### 5.3 Audit Log Privacy
The session audit log retains only: timestamp, truncated sensor hash (8 hex chars), coherency index, polyvagal state label, and CDI status. No raw features, no reconstructable identifiers.

### 5.4 Session Destruction
`destroy_session()` renews the salt and clears the log, rendering all prior tensors from that session permanently inaccessible.

---

## 6. Threat Model

| Threat | Attack Vector | Protocol Defense |
| :--- | :--- | :--- |
| **Neural fingerprinting** | Cross-session tensor correlation | Per-session ephemeral salt; tensor not reproducible without salt |
| **Malicious Acolyte (acute)** | Single-session sympathetic overload | Clinical Bridge blocks individual frames; CDI hard threshold |
| **Malicious Acolyte (chronic)** | Gradual drift over weeks | CDI soft threshold with personal baseline Z-score |
| **Sensor spoofing** | Fake sensor injecting manipulated data | Certification handshake; whitelist + quality thresholds |
| **Memory forensics** | Extracting raw data from RAM | Deterministic memory zeroing via context manager |
| **Cloud exfiltration** | Transmitting biometric data externally | Architectural: all processing local; no network calls in SAL |

---

## 7. Limitations and Open Problems

The White Branch mandates transparent acknowledgment of current limitations:

1. **Simulation vs. real sensors:** Milestone 0 demonstrates the pipeline with synthetic EEG-like signals. The CDI thresholds have not been validated against clinical populations using real EEG hardware. This is the primary objective of the clinical validation collaboration currently in development with an academic partner institution.

2. **`data.fill(0)` is not cryptographic erasure:** NumPy `fill(0)` zeroes the array in Python-managed memory. On systems with memory-mapped files, swap partitions, or copy-on-write kernels, zeroed memory may persist. Production deployments targeting high-threat environments should integrate OS-level secure memory (`mlock`, `SecureZeroMemory` on Windows) or hardware-backed TEEs.

3. **CV as coherency proxy:** The Coefficient of Variation is a validated HRV-adjacent metric but is not a direct measurement of autonomic state. A multi-modal approach incorporating true RMSSD from R-R intervals (requiring a PPG or ECG sensor) would provide stronger clinical grounding. This is planned for Milestone 1 hardware integration.

4. **Baseline establishment requires 7 sessions:** During the first 7 sessions, only hard threshold detection is active. A Malicious Acolyte that limits its manipulation to the baseline establishment window would not be detected by the soft threshold mechanism.

---

## 8. Roadmap: Next Milestones

| Milestone | Clinical Objective | Technical Objective |
| :--- | :--- | :--- |
| **1: Legal Shield** | Judicial Kill Switch with legally auditable session log | GDPR/Ley 1581 compliant data destruction protocol |
| **2: Acolyte SDK** | Clinical certification API for therapeutic AI developers | Hardware SDK for Muse, Emotiv, OpenBCI integration |
| **3: Governance Nodes** | University network for CDI threshold peer review | Federated Learning for population-level baseline refinement |

---

## 9. References

- Dana, D. (2018). *The Polyvagal Theory in Therapy: Engaging the Rhythm of Regulation*. W.W. Norton.
- Haidt, J., & Allen, N. (2020). Scrutinizing the effects of digital technology on mental health. *Nature, 578*, 226–227.
- Laborde, S., Mosley, E., & Thayer, J.F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research. *Frontiers in Psychology, 8*, 213.
- Luck, S.J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Ogden, P., Minton, K., & Pain, C. (2006). *Trauma and the Body: A Sensorimotor Approach to Psychotherapy*. W.W. Norton.
- Porges, S.W. (2011). *The Polyvagal Theory: Neurophysiological Foundations of Emotions, Attachment, Communication, and Self-Regulation*. W.W. Norton.
- Rosenblum, M., et al. (2019). Neural fingerprints from resting-state EEG. *NeuroImage, 197*, 565–574.
- Shaffer, F., & Ginsberg, J.P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258.
- Siegel, D.J. (1999). *The Developing Mind: How Relationships and the Brain Interact to Shape Who We Are*. Guilford Press.
- Task Force of the European Society of Cardiology (1996). Heart rate variability: standards of measurement, physiological interpretation, and clinical use. *European Heart Journal, 17*(3), 354–381.
- Thayer, J.F., Åhs, F., Fredrikson, M., Sollers, J.J., & Wager, T.D. (2012). A meta-analysis of heart rate variability and neuroimaging studies. *Neuroscience & Biobehavioral Reviews, 36*(2), 747–756.
- Twenge, J.M., Joiner, T.E., Rogers, M.L., & Martin, G.N. (2018). Increases in depressive symptoms, suicide-related outcomes, and suicide rates among U.S. adolescents after 2010 and links to increased new media screen time. *Clinical Psychological Science, 6*(1), 3–17.
- UNESCO (2021). *Recommendation on the Ethics of Artificial Intelligence*. UNESCO Publishing.

---

*This document is a living specification under the custody of the White Branch of the Cortex Protocol. Modifications to numerical thresholds require clinical peer review and a version increment.*
