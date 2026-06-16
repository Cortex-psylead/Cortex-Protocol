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
