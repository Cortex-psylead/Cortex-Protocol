//! matrix_inspector.rs
//! CORTEX PROTOCOL — LIMES: Silicon Entropy Validation
//! Target: ARMv8.5-A / #[no_std] bare-metal EL1-S
//! Status: SPECIFICATION — Milestone 2 hardware target
//!
//! Validates hardware clock jitter entropy to reject synthetic telemetry.
//! Shannon entropy calculated over nibble histogram of jitter samples.
//!
//! FIX APPLIED (audit 2026-05-18):
//!   - Shannon entropy formula corrected: uses p * ln(p) / ln(2), not p*(p-1)
//!   - libm::log2f used for no_std float log (feature = "libm")
//!   - Constant-time histogram loop: no data-dependent branches

#![no_std]

use core::sync::atomic::{AtomicU32, Ordering};

/* Minimum Shannon entropy in bits for a 256-sample, 16-bucket histogram.
 * At true hardware jitter, expect H ≥ 3.5 bits over nibble distribution.
 * Threshold calibrated by White Branch — do not modify without peer review. */
const MIN_SHANNON_ENTROPY_BITS: f32 = 3.5;

const POOL_SIZE:    usize = 256;
const NUM_BUCKETS:  usize = 16;    /* 4-bit nibble space */

pub struct MatrixInspector {
    entropy_pool: [u32; POOL_SIZE],
    write_ptr:    usize,
}

impl MatrixInspector {
    /// Creates a new inspector with zeroed pool.
    pub const fn new() -> Self {
        Self {
            entropy_pool: [0u32; POOL_SIZE],
            write_ptr:    0,
        }
    }

    /// Ingests a hardware jitter sample (constant-time write, no branch on value).
    pub fn push_jitter_sample(&mut self, sample: u32) {
        let index = self.write_ptr & (POOL_SIZE - 1);   /* bitmask, no branch */
        self.entropy_pool[index] = sample;
        self.write_ptr = self.write_ptr.wrapping_add(1);
    }

    /// Validates pool entropy against MIN_SHANNON_ENTROPY_BITS.
    ///
    /// Returns `true` if entropy is sufficient (biological origin likely).
    /// Returns `false` if entropy is below threshold (synthetic injection suspected).
    ///
    /// Algorithm: Shannon H = -Σ p_i * log2(p_i) over nibble histogram.
    /// Uses libm::log2f for no_std compatibility.
    pub fn verify_silicon_entropy(&self) -> bool {
        let mut counts = [0u32; NUM_BUCKETS];
        let total      = POOL_SIZE as f32;

        /* Build nibble frequency histogram — no data-dependent branches */
        for &sample in self.entropy_pool.iter() {
            let bucket = (sample & 0x0F) as usize;   /* low nibble, 0–15 */
            counts[bucket] = counts[bucket].saturating_add(1);
        }

        /* Shannon entropy: H = -Σ p_i * log2(p_i) */
        let mut entropy: f32 = 0.0;
        for &count in counts.iter() {
            if count > 0 {
                let p = (count as f32) / total;
                /* libm::log2f is available in no_std via the 'libm' crate.
                 * Add to Cargo.toml: libm = { version = "0.2", default-features = false } */
                #[cfg(feature = "libm")]
                {
                    entropy -= p * libm::log2f(p);
                }
                /* Fallback: ln(x)/ln(2) approximation for environments without libm */
                #[cfg(not(feature = "libm"))]
                {
                    /* Taylor: ln(1+x) ≈ x - x²/2 + x³/3 for |x| < 1
                     * This is an approximation — enable libm feature for production */
                    let x    = p - 1.0;
                    let ln_p = x - (x * x) / 2.0 + (x * x * x) / 3.0;
                    let log2_p = ln_p / 0.693_147_2_f32;   /* ln(2) */
                    entropy -= p * log2_p;
                }
            }
        }

        entropy >= MIN_SHANNON_ENTROPY_BITS
    }
}

/* ── Global biological shield state ─────────────────────────────────────── */

pub const STATE_SOMA_SAFE:       u32 = 0x00000001;
pub const STATE_HOMEOSTASIS_LOCK: u32 = 0x00000003;
pub const STATE_DUMMY_CONTAINMENT: u32 = 0x0000007F;

pub static BIOLOGICAL_SHIELD_STATE: AtomicU32 =
    AtomicU32::new(STATE_DUMMY_CONTAINMENT);   /* fail-safe initial state */

/// Evaluates system integrity and updates the biological shield state.
///
/// Called from the FIQ handler after each sensor window.
/// Returns the new shield state value.
#[no_mangle]
pub extern "C" fn evaluate_system_integrity(inspector: &MatrixInspector) -> u32 {
    if !inspector.verify_silicon_entropy() {
        /* Entropy below threshold — possible synthetic signal injection.
         * Transition to HOMEOSTASIS_LOCK and return DUMMY state. */
        BIOLOGICAL_SHIELD_STATE.store(STATE_HOMEOSTASIS_LOCK, Ordering::SeqCst);
        return STATE_DUMMY_CONTAINMENT;
    }

    /* Entropy valid — transition to SAFE if currently in LOCK state */
    let current = BIOLOGICAL_SHIELD_STATE.load(Ordering::SeqCst);
    if current == STATE_HOMEOSTASIS_LOCK {
        /* Do not auto-recover from LOCK — biometric ResProtocol required.
         * This prevents an attacker from momentarily injecting valid entropy
         * to unlock the system. Recovery is handled by resuscitation_kernel. */
        return STATE_DUMMY_CONTAINMENT;
    }

    BIOLOGICAL_SHIELD_STATE.store(STATE_SOMA_SAFE, Ordering::SeqCst);
    STATE_SOMA_SAFE
}
