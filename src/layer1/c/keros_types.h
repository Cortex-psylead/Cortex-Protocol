/* keros_types.h
 * CORTEX PROTOCOL — Layer 1: Secure Enclave Type Definitions
 * Target: ARMv8.5-A (Snapdragon 8 Gen 1) / TrustZone EL1-S
 * Status: SPECIFICATION — Not yet validated on real hardware (Milestone 2)
 *
 * NOTE: These types target production bare-metal deployment.
 * Current PoC implementation is in src/keros/keros_seal.py (Python).
 * This C layer is the Milestone 2 hardware target.
 */

#ifndef KEROS_TYPES_H
#define KEROS_TYPES_H

#include <stdint.h>

#define METRIC_ID_LEN    32
#define FALCON_SIG_LEN   690    /* Falcon-512 signature bytes */
#define MAX_THRESHOLDS   3      /* HRV, Pupillary, Alpha Band */

/* Clinical threshold bounds — injected from White Branch snapshot.
 * Stored in .tee_ro_clinical_thresholds (read-only secured region).
 * Values are dimensionless normalized integers (scaled by 1e6). */
typedef struct __attribute__((aligned(8))) {
    uint8_t  metric_id[METRIC_ID_LEN]; /* "BIOMETRIC_HRV", "LATENCY_PUPILLARY", "NEURAL_ALPHA" */
    uint64_t u_min;                    /* Lower homeostatic bound */
    uint64_t u_max;                    /* Upper homeostatic bound */
    uint8_t  literature_hash[32];      /* SHA-256 of peer-reviewed citation */
} ClinicalThreshold;

/* Governance snapshot metadata.
 * Validity: max 12 months from emission (Article 12). */
typedef struct __attribute__((aligned(8))) {
    uint64_t         version;
    uint64_t         timestamp_emission;
    uint64_t         timestamp_expiration;   /* emission + 31,536,000 seconds */
    uint64_t         threshold_count;
    ClinicalThreshold thresholds[MAX_THRESHOLDS];
} SnapshotMetadata;

/* Full executable snapshot with post-quantum signature.
 * Authenticated by Falcon-512 quorum from active Governance Nodes. */
typedef struct __attribute__((aligned(8))) {
    SnapshotMetadata metadata;
    uint8_t          signature_falcon[FALCON_SIG_LEN];
    uint64_t         signature_len;
} ExecutableSnapshot;

/* Biometric frame — lives ONLY in volatile memory.
 * Must be zeroed immediately after Phase A feature extraction.
 * Never exits the SAL boundary. */
typedef struct __attribute__((aligned(64))) {  /* Cache-line aligned */
    uint8_t  sensor_id_hash[32];   /* SHA-256 of certified sensor ID */
    uint64_t timestamp_capture;    /* Hardware RTC timestamp */
    float    raw_samples[512];     /* Raw ADC samples — ephemeral */
    uint32_t sample_count;
    uint8_t  _pad[4];              /* Explicit padding — no compiler surprises */
} RawBiometricFrame;

#endif /* KEROS_TYPES_H */
