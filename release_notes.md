## 🚀 Cortex Protocol v0.5.2-alpha.1 — Hardware Abstraction Layer

Esta versión marca la transición oficial del protocolo de un entorno de simulación pura (`NumPy` sine-waves) a la ingesta de telemetría bio-sensorial en tiempo real mediante hardware real o sintético.

### 🧠 Cambios Principales
* **Capa de Abstracción de Sensores:** Implementación de la clase base abstracta `BiometricSensorAdapter` para estandarizar futuras integraciones de hardware (EEG, ECG, PPG).
* **Adaptador BrainFlow Integrado:** Conexión end-to-end con la arquitectura de BrainFlow, permitiendo el procesamiento de tramas biométricas nativas de dispositivos como OpenBCI Cyton, Muse 2 y Neurosity Crown.
* **Procesamiento en Fase A:** Extracción matemática automatizada de características clínicas en tiempo real utilizando la envolvente de Hilbert (`scipy.signal.hilbert`), mapeando directamente los vectores al enrutador de telemetría (`TelemetryRouter`) bajo los umbrales de la Teoría Polivagal.

### 🧪 Pruebas y Estabilidad
* Cobertura de pruebas unitarias completada con éxito utilizando la tarjeta virtual `BoardIds.SYNTHETIC_BOARD` de BrainFlow para garantizar la viabilidad en entornos de Integración Continua (CI).
* Incremento monotónico estricto de secuencias de tramas (`frame_seq`) para mitigar ataques de replicación en el puente de datos.

### 👥 Contribuyentes en este lanzamiento
* @JhonAndry (Architecture & Review)
* @mayoka0 (Core Implementation & Tests)
* **Claude Opus 4.8** (AI Co-Author — Pair Programming Support)

---
*Nota: Este es un pre-lanzamiento de desarrollo correspondiente al Milestone 1 (Clinical Validation). No está destinado aún para entornos de producción clínica de mainnet.*
