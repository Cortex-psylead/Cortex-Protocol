# 🧠 Clinical-Technical Bridge: Evidence-Based Protocols for Cortex Protocol

This document establishes the scientific foundation for the **Clinical Capability Modules (CCM)** within the Cortex Protocol. It serves as the official reference for **Ethical Governance Nodes** to validate and sign the digital constraints that govern local AI agents.
Every agent seeking "Cortex-Certified" status must implement the hardware-agnostic boundaries defined here to ensure the user's **Cognitive Sovereignty** across any computing environment.
---

## 🌐 About this Document / Acerca de este documento

**[English]** This bridge ensures that technical execution never bypasses clinical safety. It translates peer-reviewed psychological and physiological research into enforceable hardware constraints. By using the Cortex Protocol, developers agree to subject their local AI agents to these evidence-based margins.

**[Español]** Este puente asegura que la ejecución técnica nunca ignore la seguridad clínica. Traduce investigaciones psicológicas y fisiológicas revisadas por pares en restricciones de hardware ejecutables. Al utilizar el Protocolo Cortex, los desarrolladores aceptan someter sus agentes de IA locales a estos márgenes basados en 
evidencia.

---
## 📐 The Governance Framework
The protocol remains independent of specific hardware vendors, focusing on **compute capabilities** (GPU, NPU, DSP) rather than specific models.
- **Clinical Basis:** Validated science behind the intervention.
- **Protocol Margins:** Specific values that the **Cortex SDK** must enforce.
- **Hardware Abstraction (SAL):** How these margins translate to local execution (Mobile, Desktop, or Server).
- **Sovereignty Mandate:** Non-negotiable privacy and safety limits enforced by the Protocol.
---
## ❤️ Module 1: HRV & Cardiac Coherence (Autonomic Regulation)
### Clinical Basis
Heart Rate Variability (HRV) is the primary non-invasive biomarker of autonomic nervous system balance. The Cortex Protocol prioritizes **parasympathetic dominance** as a requirement for ethical AI interaction.
### Protocol Margins for Agents

| Parameter | Value | Enforced by Protocol |
| :--- | :--- | :--- |
| Optimal breath rate | 5.5 breaths/min | YES |
| Sampling rate for HRV | ≥ 250 Hz | YES |
| Real-time analysis | Local Inference | MANDATORY |

### Hardware Mapping via SAL
- **Local Processing:** HRV analysis must execute on the device's local compute units (GPU, NPU, or CPU).
- **Sovereignty Requirement:** Raw heartbeat data is **ephemeral**. The protocol prohibits the storage or transmission of raw R-R intervals to external servers.
---
## 🛡️ Module 2: Sensory Load Management & Cognitive Shielding
### Clinical Basis
Based on validated sensory integration theories and **Polyvagal Theory**, the protocol recognized that environmental stimuli can trigger threat responses. The protocol acts as a "buffer" between the environment and the user's neurological state.
### Protocol Margins (The "Cognitive Shield")
- **Audio Attenuation:** Preemptive reduction of high-decibel spikes detected via local sensors.
- **Visual Hygiene:** Hardware-level adjustment of light temperature and flicker frequency based on clinical safety thresholds.
### Hardware Mapping via SAL
- **Compute Agnosticism:** The protocol utilizes any available local acceleration (Discrete GPU, Integrated NPU, or High-Performance DSP) to process sensory data in real-time.
- **Universal Deployment:** Whether running on a mobile chipset, a high-end desktop, or a localized workstation, the safety margins remain identical.
---
## 🔬 Module 3: Validation Roadmap — Coherency Index (CV) as an HRV/RMSSD Proxy

### Clinical Basis
The Clinical Drift Index's Coherency Index (CV = std/mean of the Hilbert-transformed signal envelope) is the single largest unvalidated scientific claim in the protocol (see DISCLAIMER.md §4.2, WHITE_PAPER.md §7.3). It is grounded in general HRV literature (Shaffer & Ginsberg, 2017) as a normalized variability metric, but has not been directly validated against RMSSD computed from real R-R intervals using this specific implementation.

### Proposed Validation Protocol

**Population:** Healthy adult volunteers, resting/seated conditions. Illustrative minimum n=30 for an initial pilot correlation (comparable to published wearable-vs-reference HRV validation studies); a fully powered confirmatory study (target n≥50, exact figure pending formal power calculation) is the Milestone 1 objective. **Sample size and success criteria below are a proposed starting point, not a finalized protocol** — they require sign-off from a clinical/biostatistics collaborator before use in any IRB-equivalent submission (see GOVERNANCE.md, Transitional Governance note).

**Reference (gold-standard) signal:** Simultaneous R-R interval acquisition via a research-grade chest strap (e.g., Polar H10) or clinical ECG, computing true RMSSD per Task Force ESC/NASPE (1996) methodology.

**Test signal:** CORTEX pipeline's Hilbert-envelope CV, computed in parallel from EEG or PPG session data on BrainFlow-supported hardware (OpenBCI Cyton, Muse 2).

**Metrics:**
- Pearson/Spearman correlation between session-level CV and session-level RMSSD.
- Bland-Altman agreement analysis.
- Sensitivity/specificity of CV-derived polyvagal state classification (ventral/sympathetic/dorsal) against RMSSD-derived reference thresholds.

**Illustrative success criterion:** r ≥ 0.6 (moderate-to-strong correlation) as a starting bar for continued use of CV as an RMSSD proxy in the Clinical Bridge. This threshold itself requires White Branch / Governance Node approval *before* the study runs, not after.

**If validation fails:** The CV proxy claim is deprecated. The Clinical Bridge and CDI thresholds are recalibrated to require direct RMSSD computation from certified cardiac sensors (≥250 Hz sampling, per STANDARD.md §2.5.1), rather than the EEG-envelope approximation.

### Status
Not started. This is the explicit Milestone 1 research question (ROADMAP.md) and the primary criterion for CORTEX reaching "Clinically Validated" conformance (STANDARD.md Part IV). Requires an independent Governance Node partner (Issue #5) for IRB-equivalent oversight and unbiased data collection.

---
## 📚 Master Reference List: The Scientific Basis
The following research forms the non-negotiable basis for the Cortex Clinical Modules:
* **Porges, S.W. (2011).** *The Polyvagal Theory: Neurophysiological Foundations of Emotions, Attachment, Communication, and Self-regulation.*
* **HeartMath Institute (2015).** *Science of the Heart, Vol. 2.*
* **Laborde, S. et al. (2017).** *HRV and cardiac vagal tone in psychophysiological research.* Frontiers in Psychology.
* **UNESCO (2021).** *Recommendation on the Ethics of Artificial Intelligence.*
* **Hancock, P.A. & Chignell, M.H. (1988).** *Mental Workload Dynamics in Adaptive Interface Design.*
* **Jirakittayakorn, N. & Wongsawat, Y. (2017).** *Brain responses to 6-Hz binaural beats.* Frontiers in Neuroscience.
---
## 🔐 The Sovereignty Mandate (Ethical Governance Rules)
1. **Zero-Cloud Biometrics:** Any module interfacing with physiological data must prove that the data path terminates at the local **Sovereignty Abstraction Layer (SAL)**.
2. **Clinical Supremacy:** In case of conflict between a commercial app logic and a Cortex Clinical Module, the **Cortex Protocol** will override the app's behavior at the hardware level.
3. **Hardware Independence:** The protocol is designed to scale from low-power mobile devices to high-performance local servers.
4. **Independent Audit:** Rulesets are issued by authorized Governance Nodes, ensuring parameters are based on science, not profit.
---
> *"The body keeps the score. The Protocol ensures the hardware respects the body."*
