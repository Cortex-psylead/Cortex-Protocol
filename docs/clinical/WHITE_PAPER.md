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

Raw EEG data (normalized to clinical range: −50 µV to +50 µV) is processed through a Hilbert transform to extract the signal envelope. Five statistical descriptors are computed from the analytical signal envelope $A(t)$ derived from the complex signal $Z(t) = x(t) + i\hat{x}(t) = A(t)e^{i\phi(t)}$:

1. **Mean Envelope Amplitude ($\mu_A$):** Establishes the baseline tonic magnitude of cortical activation.
2. **Envelope Variance ($\sigma^2_A$):** Measures sudden phasic bursts and micro-arousals.
3. **Skewness ($S_A$):** Quantifies structural asymmetry in neuro-oscillatory bursts.
4. **Kurtosis ($K_A$):** Captures transient spike noise and rapid anomalies.
5. **Spectral Entropy ($H_{sp}$):** Evaluates the chaotic complexity and raw information density of the local cortical field.

**Phase B — Obfuscation & Tensor Mapping (non-interpretable)**

Once the interpretable clinical feature vector $F = [\mu_A, \sigma^2_A, S_A, K_A, H_{sp}]$ is assembled, it is immediately subjected to an irreversible mathematical projection before leaving the local memory space:

$$T = \mathcal{M}(F) + \eta$$

Where $\mathcal{M}$ represents a non-linear cryptographic manifold mapping onto a latent hypersphere, and $\eta$ is a calibrated noise vector drawn from a Laplacian distribution:

$$\eta \sim \text{Lap}\left(0, \frac{\Delta \mathcal{M}}{\epsilon}\right)$$

This injection guarantees $\epsilon$-differential privacy. The resulting obfuscated tensor $T$ contains mathematically optimal variance to signal state changes (e.g., high cognitive strain) to the external AI agent, but strips away the distinct high-fidelity physiological variances that constitute a personal re-identifiable neural fingerprint.

---

## 4. The Clinical Drift Index (CDI)

The Clinical Drift Index (CDI) is the foundational real-time metric utilized by the Cognitive Shield to evaluate autonomic and cortical displacement. Rather than relying on a single biomarker, the CDI synthesizes central nervous system activity (EEG spectral power ratios) and autonomic nervous system tone (root mean square of successive differences, or RMSSD, derived from HRV).

The index is computed continuously using a sliding window via the following formal mapping:

$$CDI = \alpha \left( \frac{\text{RMSSD}_{\text{base}} - \text{RMSSD}_{\text{curr}}}{\text{RMSSD}_{\text{base}}} \right) + \beta \left( \frac{\text{Power}_{\theta}}{\text{Power}_{\beta}} \right)_{\text{norm}}$$

Where $\alpha$ and $\beta$ represent clinically validated coefficients weighted by the White Branch based on user baseline constraints.

### 4.1 Boundary Enforcement Zones

The protocol maps the scalar value of the CDI into three strict operational execution bands:

[ CDI < 0.35 ]  --> GREEN ZONE: Homeostatic Equilibrium (Full Agency)
[ 0.35 ≤ CDI < 0.70 ] --> YELLOW ZONE: Sympathetic Activation (Linguistic Throttling)
[ CDI ≥ 0.70 ]  --> RED ZONE: Cognitive/Emotional Overload (Hardware Decoupling)

- **Green Zone (CDI < 0.35):** Indicates optimal ventral vagal tone and stable cognitive loading. The interface permits unrestricted bidirectional throughput.
- **Yellow Zone (0.35 ≤ CDI < 0.70):** Indicates sustained sympathetic arousal or emerging cognitive exhaustion. The protocol actively restricts high-arousal semantic tokens generated by the external AI agent to induce a down-regulation state.
- **Red Zone (CDI ≥ 0.70):** Indicates acute emotional deregulation or profound working memory saturation. The system executes a non-negotiable circuit breach, isolating the sensor stream and pausing active interaction loops via the ETHOS module.

---

## 5. Evidence Base & Safety Thresholds

The numerical constants hardcoded into `ClinicalThresholds` are directly derived from peer-reviewed empirical boundaries:

1. **Ventral Vagal Depletion Threshold:** Grounded firmly in Polyvagal Theory (Porges, 2011). A sustained drop in time-domain HRV metrics (RMSSD below 20 ms) under negligible physical movement is interpreted as an unauthorized systemic stress induction, shifting the execution flow to safe state constraints.
2. **Cognitive Overload Detection:** Grounded in standard EEG cognitive workload indices (Klimesch, 1999). A simultaneous increase in frontal theta bands (4 to 7 Hz) paired with an acute drop in parietal alpha networks (8 to 12 Hz) signals executive function exhaustion, overriding the AI agent's semantic density constraints.

---

## 6. Verification Stack & Runtime Integrity

The physical enforcement of this document requires three lower-level sub-protocols to validate runtime trust before processing any logic:

- **ETHOS (Dynamic Consent Module):** Operates on real-time physiology to grant or deny granular processing privileges based on immediate capacity metrics rather than static licenses.
- **KEROS (Hardware Attestation Framework):** Validates sensor authenticity and cryptographic binding using TPM 2.0 cryptographic primitives, neutralizing data spoofing.
- **LIMES (Liveness Proof Layer):** Analyzes the raw physical telemetry for biological 1/f spectral noise attributes, verifying that the input signal arises from a living organism and blocking synthetic replay attacks.
