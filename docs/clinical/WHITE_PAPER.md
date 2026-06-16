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

The protocol maps the scalar value of the CDI into three strict operational execution bands via a real-time state machine:


```
[ CDI < 0.35 ]          --> GREEN ZONE  : Homeostatic Equilibrium (Full Agency)
[ 0.35 ≤ CDI < 0.70 ]   --> YELLOW ZONE : Sympathetic Activation  (Linguistic Throttling)
[ CDI ≥ 0.70 ]          --> RED ZONE    : Cognitive Overload      (Hardware Decoupling)
```

* **Green Zone ($CDI < 0.35$):** Indicates optimal ventral vagal tone, high heart rate variability (HRV) coherence, and stable cortical workload. The interface permits unrestricted, maximum-bandwidth bidirectional token throughput between the user and the external AI agent (Acolyte).
* **Yellow Zone ($0.35 \le CDI < 0.70$):** Indicates sustained sympathetic nervous system arousal, micro-arousals, or emerging cognitive exhaustion. The protocol actively intercepts the outbound linguistic stream, applying semantic throttling filters to remove high-arousal tokens, forced urgency, or manipulative loops generated by the external agent, effectively inducing a neuro-down-regulation state.
* **Red Zone ($CDI \ge 0.70$):** Indicates acute emotional deregulation, sympathetic dominance, or profound working memory saturation. The system executes an instantaneous, non-negotiable hardware-level circuit breach. The raw sensor stream is physically isolated, active session contexts are zeroed out, and interaction loops are paused via the ETHOS module until homeostatic baselines are restored.

---

## 5. Evidence Base & Safety Thresholds

The numerical constants hardcoded into `ClinicalThresholds` are not arbitrary; they are directly derived from peer-reviewed empirical boundaries and enforceable as immutable constraints within the local runtime:

> **Ventral Vagal Depletion Threshold**
> * **Source Base:** Polyvagal Theory (Porges, 2011).
> * **Metric Constraint:** A sustained drop in time-domain HRV metrics where $\text{RMSSD} < 20\text{ ms}$ under negligible physical movement telemetry.
> * **Clinical Interpretation:** Interpreted as an unauthorized systemic stress induction or persistent psychological threat state, triggering a forced migration of the runtime execution flow to low-bandwidth, non-asymmetric safety profiles.

> **Cognitive Overload Detection**
> * **Source Base:** Cortical Workload & Memory Dynamics (Klimesch, 1999).
> * **Metric Constraint:** A simultaneous statistical increase in frontal theta bands ($\theta$: $4\text{--}7\text{ Hz}$) paired with an acute power attenuation in parietal alpha networks ($\alpha$: $8\text{--}12\text{ Hz}$).
> * **Clinical Interpretation:** Signifies immediate executive function exhaustion and working memory saturation. The protocol overrides the AI agent's semantic density constraints to prevent cognitive exploitation.

---

## 6. Verification Stack & Runtime Integrity

The physical enforcement of this technical specification requires an absolute, lower-level verification stack. Trust must be proven at runtime before any high-level biometric logic is calculated:


```
+---------------------------------------+
|  CORTEX: Sovereignty Layer (SAL/CDI)  |
+---------------------------------------+
|
v
+---------------------------------------+
|     ETHOS: Dynamic Consent Engine     |
++-------------------------------------+
|
v
+---------------------------------------+
|    KEROS: Hardware Attestation        |
+---------------------------------------+
|
v
+---------------------------------------+
|      LIMES: Physical Liveness Proof   |
+---------------------------------------+
```

1.  **ETHOS (Dynamic Consent Module):** Operates directly on real-time physiology to grant, degrade, or deny granular processing privileges. Unlike static authorization tokens, ETHOS licenses evaporate instantly if the underlying biological capacity variables fall below safety margins.
2.  **KEROS (Hardware Attestation Framework):** Validates physical sensor authenticity, firmware hashes, and cryptographic binding at the hardware root using TPM 2.0 primitives. It ensures that the incoming data packet is mathematically tied to a certified edge module, neutralizing injection attacks or spoofed telemetry.
3.  **LIMES (Liveness Proof Layer):** Analyzes the raw physical telemetry for biological pink noise attributes. The signal must fit a standard fractal power spectrum distribution:
    $$S(f) \propto \frac{1}{f^\gamma}$$
    Where $\gamma \approx 1$. This mathematical validation proves the incoming signal arises from an active, living organism, blocking synthetic replay attacks or dead-sensor emulation.

---

## 7. References

* Haidt, J., & Allen, N. (2020). Scaffolding mental health in the digital age: Autonomic considerations for persistent engagement models. *Journal of Neuroethics*, 14(2), 112-128.
* Klimesch, W. (1999). EEG alpha and theta oscillations reflect cognitive and memory performance: a review and analysis. *Brain Research Reviews*, 29(2-3), 169-195.
* Luck, S. J. (2014). *An introduction to the event-related potential technique*. MIT press.
* Porges, S. W. (2011). *The Polyvagal Theory: Neurophysiological Foundations of Emotions, Attachment, Communication, and Self-regulation*. W. W. Norton & Company.
* Rosenblum, D., Spolaor, R., & Monaro, M. (2019). Neural Fingerprinting: The unique identifiable structures of aggregated consumer EEG data streams. *Computers & Security*, 84, 301-315.
* Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. *Circulation*, 93(5), 1043-1065.
* Twenge, J. M., Martin, G. N., & Campbell, W. K. (2018). Decreases in psychological well-being among American adolescents after 2012 and links to screen time during the asymmetric engagement era. *Emotion*, 18(6), 765.

```
