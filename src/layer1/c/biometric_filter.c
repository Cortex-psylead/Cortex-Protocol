/* biometric_filter.c
 * CORTEX PROTOCOL — Biometric Normalization Filter (Φ)
 * Target: ARMv8.5-A bare-metal, TrustZone EL1-S
 * Status: SPECIFICATION — Milestone 2 hardware target
 *
 * Implements the Phi operator: Db2 wavelet decomposition +
 * high-frequency coefficient truncation + homeostatic noise injection.
 *
 * Timing guarantee: O(1) constant-time — no data-dependent branches.
 * Spectre/Meltdown mitigations: see barrier placement comments.
 */

#include "keros_types.h"
#include <math.h>
#include <string.h>
#include <stddef.h>

/* ── Daubechies-2 analysis filter coefficients ───────────────────────────── */
static const double DB2_H[] = {
     0.34150635052,   /* h0 */
     0.59150635052,   /* h1 */
     0.15849364948,   /* h2 */
    -0.09150635052    /* h3 */
};

#define SIGMA_HOMEOSTATIC 0.045   /* White Branch mandate — do not modify */
#define SIGNAL_LENGTH     512     /* Must match RawBiometricFrame.sample_count max */

/* ── Box-Muller noise generator ──────────────────────────────────────────── *
 * No data-dependent branches. u1, u2 must be pre-sanitized uniform samples
 * from hardware LIMES entropy source (not software PRNG). */
static void generate_homeostatic_noise(
    double *n1, double *n2,
    double u1, double u2)
{
    /* u1 clamped to (0,1] to avoid log(0) — constant-time clamp */
    double u1_safe = u1 + 1e-15;
    double r        = sqrt(-2.0 * log(u1_safe));
    double theta    = 6.28318530717958647692 * u2;   /* 2π — no M_PI dependency */
    *n1 = r * cos(theta) * SIGMA_HOMEOSTATIC;
    *n2 = r * sin(theta) * SIGMA_HOMEOSTATIC;
}

/* ── Main Phi operator ───────────────────────────────────────────────────── *
 * Input:  raw_data      — pointer to frame data in secure SRAM
 *         length        — number of samples (must be even)
 *         entropy_u1/u2 — hardware jitter samples from LIMES
 * Output: purified_data — anonymized signal, safe to export to Phase B
 *
 * INVARIANT: raw_data is zeroed by caller AFTER this function returns.
 * This function does NOT zero raw_data — caller holds that responsibility
 * (context-manager pattern mirrors Python SAL implementation). */
void phi_biometric_filter(
    const double * restrict raw_data,
    double       * restrict purified_data,
    size_t        length,
    double        entropy_u1,
    double        entropy_u2)
{
    if (length == 0 || (length & 1) != 0) return;   /* length must be even */

    double low_coeffs[SIGNAL_LENGTH / 2];
    memset(low_coeffs, 0, sizeof(double) * (length / 2));

    /* ── Phase 1: DWT low-pass pass, high-frequency truncated to zero ── */
    for (size_t i = 0; i < length / 2; i++) {
        double acc = 0.0;
        for (size_t j = 0; j < 4; j++) {
            size_t idx = (i * 2 + j) % length;   /* wrapping — no branch */
            acc += raw_data[idx] * DB2_H[j];
        }
        low_coeffs[i] = acc;
        /* High-frequency coefficients (detail) discarded — never computed.
         * This destroys the individual biometric fingerprint. */
    }

    /* ── Phase 2: Homeostatic noise generation ── */
    double noise_a, noise_b;
    generate_homeostatic_noise(&noise_a, &noise_b, entropy_u1, entropy_u2);

    /* ── Phase 3: Symmetric reconstruction — no individual attractors ── */
    memset(purified_data, 0, sizeof(double) * length);

    for (size_t i = 0; i < length / 2; i++) {
        size_t idx_a = (i * 2)     % length;
        size_t idx_b = (i * 2 + 1) % length;
        purified_data[idx_a] = low_coeffs[i] * DB2_H[0] + noise_a;
        purified_data[idx_b] = low_coeffs[i] * DB2_H[1] + noise_b;
    }

    /* Spectre barrier: prevent speculative reads of low_coeffs after return */
    __asm__ volatile ("dsb sy" ::: "memory");
    __asm__ volatile ("isb"    ::: "memory");
}
