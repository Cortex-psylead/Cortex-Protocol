# 📖 Cortex Protocol — Official Lexicon
**Bilingual Glossary of Proprietary and Scientific Terms**
*Version 1.1 — Maintained by the White Branch*

This document is the authoritative reference for all terminology used across Cortex Protocol documentation and code. Definitions are **operational**: they specify not just what a term means, but how it functions within the protocol.

---

## Part I — Proprietary Concepts (Cortex Original)

**White Branch** *(ES: Rama Blanca / Tribunal de Ética)*
The sovereign governing body of the protocol. Composed exclusively of licensed mental health and neuroscience professionals. The White Branch holds unilateral authority to define, modify, or veto any numerical safety threshold in the protocol. No technical implementation may override a White Branch clinical mandate. *See: [GOVERNANCE.md](GOVERNANCE.md)*

**Acolyte** *(ES: Acólito)*
Any external AI agent, model, or software system that interacts with a user's data stream through the Cortex Protocol. The Acolyte is a *guest* in the user's cognitive space. It receives only anonymized tensors (Phase B output); it never has access to raw biometric values, Phase A clinical features, or the session salt. A "Malicious Acolyte" is one that—intentionally or through optimization pressure—induces pathological neurophysiological states in the user.

**Sovereignty Abstraction Layer (SAL)** *(ES: Capa de Abstracción de Soberanía)*
The technical core of the protocol. A hardware-agnostic software layer that sits between biometric sensors and the Acolyte. The SAL is responsible for: sensor certification, ephemeral data handling, two-phase tensor transformation, Clinical Bridge enforcement, and session audit logging. All raw biometric data that enters the SAL is transformed or destroyed before exiting it.

**Clinical Drift Index (CDI)** *(ES: Índice de Deriva Clínica)*
The protocol's quantitative immune system against pathological AI-induced neurophysiological drift. The CDI monitors the Coefficient of Variation (CV) of the biometric signal envelope across sessions. It employs dual detection: an absolute clinical threshold (hard violations) and a personal Z-score baseline (soft violations). When violation thresholds are exceeded, the CDI issues an automatic protocol block. *See: [WHITE_PAPER.md §4](WHITE_PAPER.md)*

**Coherency Index** *(ES: Índice de Coherencia)*
The primary metric computed by the CDI. Defined as the Coefficient of Variation (CV = std/mean) of the Hilbert-transformed biometric signal envelope. A CV < 0.3 corresponds to ventral vagal (calm) states; CV 0.3–0.7 to sympathetic engagement; CV ≥ 0.7 to sympathetic surge or dorsal vagal states. Not to be confused with EEG coherence (inter-channel phase synchrony), which is a distinct measure.

**Cognitive Shield** *(ES: Escudo Cognitivo)*
The active operational state of the protocol when all defense mechanisms are simultaneously engaged: SAL tensor transformation, Clinical Bridge per-frame validation, and CDI temporal monitoring. The Cognitive Shield is the product delivered by Milestone 0.

**Clinical Bridge** *(ES: Puente Clínico)*
A per-frame validation gate that runs on Phase A clinical features *before* privacy obfuscation. The Clinical Bridge applies Polyvagal Theory-derived thresholds (std ≤ 0.5, p75 ≤ 0.7, max ≤ 0.9 of the normalized envelope) to determine whether the current biometric state is within the Window of Tolerance. A frame failing the Clinical Bridge is blocked before the Acolyte receives it.

**Clinical Capability Module (CCM)** *(ES: Módulo de Capacidad Clínica)*
A discrete, independently certifiable unit of protocol functionality (e.g., the HRV monitoring module, the sensory load management module). Each CCM must carry a cryptographic signature from an authorized Governance Node before it can access protected hardware resources. Unsigned CCMs are refused by the SAL.

**Phase A / Phase B Transformation** *(ES: Transformación Fase A / Fase B)*
The two-step pipeline for converting raw biometric data into anonymous tensors. Phase A extracts five clinically interpretable statistical features from the signal (mean, std, p25, p75, max of the Hilbert envelope). Phase B applies HMAC-SHA256 with the session salt to produce the anonymous tensor delivered to the Acolyte. The Clinical Bridge operates on Phase A. The Acolyte operates on Phase B. These are architecturally isolated operations.

**Governance Node** *(ES: Nodo de Gobernanza)*
An independent institutional entity (university faculty, professional association, research center) authorized to issue cryptographically signed Clinical Capability Modules. Governance Nodes are the enforcement mechanism for the White Branch's clinical mandates at runtime. A Governance Node has no commercial relationship with any hardware vendor.

**Judicial Kill Switch** *(ES: Interruptor Judicial)*
A session destruction mechanism that cryptographically invalidates all session data: the session salt is replaced with a new random value, the audit log is cleared, and all ephemeral tensors become permanently inaccessible. Planned for full legal auditability in Milestone 1. In Milestone 0, implemented as `destroy_session()`.

**Malicious Acolyte** *(ES: Acólito Maligno)*
An AI agent—whether through deliberate design or emergent optimization—that produces sustained neurophysiological states outside the user's Window of Tolerance. The CDI's soft threshold (Z-score baseline monitoring) is specifically designed to detect Malicious Acolyte behavior that operates below the level of acute clinical thresholds.

**Biological Constant** *(ES: Constante Biológica)*
The relatively static neurophysiological parameters of the human nervous system (homeostatic range, Window of Tolerance, autonomic regulatory capacity). Contrasted with the Technological Variable (exponentially increasing AI capability). The Cortex Axiom: any technology that exceeds the processing capacity or physiological tolerance of the Biological Constant is, by definition, a pathogenic agent.

---

## Part II — Integrated Scientific Foundations

**Polyvagal Theory** *(ES: Teoría Polivagal)*
*Source: Porges, S.W. (2011). The Polyvagal Theory. W.W. Norton.*
A neurophysiological framework describing three hierarchical autonomic states governed by the vagal nerve: (1) ventral vagal — social engagement, safety, calm; (2) sympathetic — mobilization, stress, fight/flight; (3) dorsal vagal — immobilization, shutdown, dissociation. In the Cortex Protocol, the Clinical Bridge thresholds are calibrated to detect transitions out of the ventral vagal state.

**Window of Tolerance** *(ES: Ventana de Tolerancia)*
*Source: Siegel, D.J. (1999). The Developing Mind. Guilford.*
The range of autonomic arousal within which an individual can process information, regulate emotion, and maintain cognitive flexibility without entering hyperactivation (panic, dissociation trigger) or hypoactivation (numbing, disconnection). The CDI monitors temporal drift outside this window across sessions.

**Heart Rate Variability (HRV)** *(ES: Variabilidad de la Frecuencia Cardíaca)*
*Source: Task Force ESC/NASPE (1996). Eur Heart J, 17(3), 354–381.*
The variation in time intervals between successive heartbeats (R-R intervals). High HRV indicates parasympathetic dominance and physiological resilience. Key metric: RMSSD (Root Mean Square of Successive Differences) — the primary time-domain HRV index for short-term parasympathetic assessment. The CDI's Coherency Index is designed as an EEG-envelope proxy for HRV-like variability assessment pending real PPG/ECG sensor integration.

**RMSSD** *(ES: Raíz Cuadrada de la Media de las Diferencias al Cuadrado Sucesivas)*
*Source: Task Force ESC/NASPE (1996).*
The standard HRV metric for parasympathetic nervous system activity. Computed as the root mean square of successive R-R interval differences. Low RMSSD values (< 20 ms in adults) indicate sympathetic dominance and elevated stress. The Coherency Index (CV) in the current implementation is an envelope-based approximation of this concept, pending direct R-R interval access from certified cardiac sensors.

**Coefficient of Variation (CV)** *(ES: Coeficiente de Variación)*
A normalized statistical measure of variability: CV = std / mean. Used in the protocol as the Coherency Index because it is dimensionless (independent of absolute signal amplitude) and correlates with autonomic variability as described in HRV literature (Shaffer & Ginsberg, 2017). A higher CV indicates greater signal irregularity and higher autonomic arousal.

**Tensor** *(ES: Tensor)*
A multidimensional mathematical object. In the protocol context, tensors are the anonymous, irreversible mathematical representations of biometric states that the Acolyte receives. A Cortex tensor carries no identifying information about the user, the raw signal amplitudes, or the sensor hardware. Its only function is to encode relative pattern information for clinical state classification.

**Differential Privacy** *(ES: Privacidad Diferencial)*
A mathematical framework (Dwork et al., 2006) that provides formal guarantees that individual data cannot be extracted from aggregate statistics or model outputs. The Cortex Protocol applies the principles of differential privacy to its tensor transformation: the Acolyte may improve its state-classification model from population-level patterns without accessing individual user data.

**Federated Learning** *(ES: Aprendizaje Federado)*
A distributed machine learning approach where model improvements are computed locally and only mathematical gradients (not raw data) are shared with a central aggregator. Planned for Phase 3 of the Cortex roadmap: Governance Nodes will aggregate gradient updates from consenting users to refine CDI baseline models population-wide without any raw biometric data leaving individual devices.

**Homeostasis** *(ES: Homeostasis)*
The dynamic self-regulatory process by which biological systems maintain internal stability within physiological limits despite external disturbances. The Cortex Protocol's operational goal is to preserve the user's neurophysiological homeostasis during AI interaction — preventing the AI system from becoming a chronic physiological stressor.

---

## Part III — Protocol Status Taxonomy

**Green State (Optimal)** *(ES: Estado Verde — Óptimo)*
CV < 0.3. User is within ventral vagal engagement. Standard Acolyte interaction permitted. No CDI warnings active.

**Yellow State (Monitoring / Damping)** *(ES: Estado Amarillo — Monitoreo)*
CV 0.3–0.7. Sympathetic engagement detected. CDI warning issued. Acolyte continues but CDI counters are incrementing. User may be notified depending on governance level setting.

**Red State (Block / Shutdown)** *(ES: Estado Rojo — Bloqueo)*
CV ≥ 0.7 or CDI hard/soft block threshold exceeded. Protocol executes automatic block. Acolyte session is suspended. User receives intervention notification. Session can only resume after CDI reset (which requires White Branch–defined cooldown protocol — to be specified in Milestone 1).

---

*This lexicon is a living document. New terms must be proposed via a `[Lexicon-Proposal]` Issue and approved by the White Branch before addition. Modifications to existing definitions that alter clinical meaning require a version increment.*
