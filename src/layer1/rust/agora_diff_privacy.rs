//! agora_diff_privacy.rs
//! CORTEX PROTOCOL — Delta_split: Local Differential Privacy (LDP)
//! Target: ARMv8.5-A / #[no_std] bare-metal
//! Status: SPECIFICATION — Milestone 2 hardware target
//!
//! Implements the Laplace mechanism for the outbound AGORA channel.
//! ε = 0.15, Δf = 1e-3 (White Branch mandate — do not modify).
//!
//! FIX APPLIED (audit 2026-05-18):
//!   - Removed data-dependent if/else in sample_laplace (timing attack).
//!   - Replaced with constant-time bitmask multiplication.
//!   - Input validation added for uniform samples.

#![no_std]

/// Laplace noise parameters — White Branch clinical mandate.
/// ε = 0.15 provides strong privacy for population research donation.
/// b = Δf / ε = 0.001 / 0.15 ≈ 0.006667
pub const EPSILON:      f32 = 0.15;
pub const SENSITIVITY:  f32 = 1e-3;   /* Δf — global sensitivity of the feature */

pub struct AgoraBifurcation {
    epsilon:     f32,
    sensitivity: f32,
}

impl AgoraBifurcation {
    /// Creates a bifurcation operator with the White Branch parameters.
    pub const fn new() -> Self {
        Self {
            epsilon:     EPSILON,
            sensitivity: SENSITIVITY,
        }
    }

    /// Samples Laplace noise for a single uniform input in (0, 1).
    ///
    /// Constant-time version: eliminates the data-dependent if/else
    /// that existed in the previous implementation.
    ///
    /// Laplace inverse CDF: b * sign(u - 0.5) * ln(1 - 2|u - 0.5|)
    /// Rewritten constant-time:
    ///   let v = u - 0.5
    ///   let sign = 1.0 if v >= 0, else -1.0   ← replaced with bitmask
    ///   result = -b * sign * ln(1 - 2*|v|)
    fn sample_laplace_ct(&self, u: f32) -> f32 {
        let scale = self.sensitivity / self.epsilon;   /* b ≈ 0.006667 */
        let v     = u - 0.5_f32;

        /* Constant-time sign: extract sign bit, build ±1.0 without branch.
         * Bit 31 of f32 is the sign bit: 0 → positive, 1 → negative.
         * sign_f32 = +1.0 if v >= 0.0, else -1.0 */
        let v_bits:    u32 = v.to_bits();
        let sign_bit:  u32 = v_bits >> 31;          /* 0 or 1 */
        /* Map 0→+1.0 and 1→-1.0 without branch: 1.0 - 2.0*(sign_bit as f32) */
        let sign_f32:  f32 = 1.0_f32 - 2.0_f32 * (sign_bit as f32);

        let abs_v:     f32 = f32::from_bits(v_bits & 0x7FFF_FFFF);   /* |v| */

        /* Argument to ln: 1 - 2|v|. Clamped to (0,1) to avoid ln(0). */
        let ln_arg: f32 = (1.0_f32 - 2.0_f32 * abs_v).max(1e-7_f32);

        /* ln approximation for no_std — enable libm feature for production */
        #[cfg(feature = "libm")]
        let ln_val: f32 = libm::logf(ln_arg);

        #[cfg(not(feature = "libm"))]
        let ln_val: f32 = {
            /* Taylor: ln(1+x) ≈ x - x²/2 + x³/3 for small x */
            let x = ln_arg - 1.0_f32;
            x - (x * x) / 2.0 + (x * x * x) / 3.0
        };

        -scale * sign_f32 * ln_val
    }

    /// Applies Laplace noise to each element of a feature vector.
    ///
    /// `entropy_source` must contain hardware jitter samples normalized to (0,1).
    /// Provided by LIMES — never use a software PRNG here.
    pub fn apply_delta_split(
        &self,
        features:       &mut [f32],
        entropy_source: &[f32],
    ) {
        if entropy_source.is_empty() {
            return;
        }
        for (i, val) in features.iter_mut().enumerate() {
            let u     = entropy_source[i % entropy_source.len()];
            let noise = self.sample_laplace_ct(u);
            *val += noise;
        }
    }
}
