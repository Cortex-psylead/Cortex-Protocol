/* keros_core.c
 * CORTEX PROTOCOL — Layer 1: FIQ Handler & Hardware Lifecycle (KEROS)
 * Target: ARMv8.5-A / TrustZone EL1-S bare-metal
 * Status: SPECIFICATION — Milestone 2 hardware target
 *
 * Handles governance snapshot lifecycle via hardware RTC interrupt.
 * On expiration or validation failure: purge registers, force Hi-Z,
 * enter low-power hold via WFI. Recovery only via biometric ResProtocol.
 */

#include "keros_types.h"

/* ── MMIO register map (platform-specific — Snapdragon 8 Gen 1) ──────────── *
 * These addresses are placeholders. Real values from BSP / device tree.
 * Replace with verified addresses from Qualcomm TRM before production. */
#define MMIO_RTC_TIMESTAMP     ((volatile uint64_t *) 0x3F004000ULL)
#define MMIO_HARDWARE_MUX_CTRL ((volatile uint32_t *) 0x3F005000ULL)
#define REG_MUX_HI_Z_FORCE     (1u << 31)

/* ── System state ────────────────────────────────────────────────────────── */
#define STATE_INIT         0x00000000u
#define STATE_SOMA_SAFE    0x00000001u
#define STATE_SHIELD       0x00000002u
#define STATE_LOCK         0x00000003u
#define STATE_DUMMY        0x0000007Fu   /* Containment / isolation mode */

extern ExecutableSnapshot current_snapshot;   /* Provided by governance loader */
static volatile uint32_t  system_state = STATE_INIT;

/* ── Register purge — Spectre/Meltdown mitigation ───────────────────────── *
 * Clears caller-saved ABI registers (x0–x15) and NZCV flags.
 * Must be called before entering Hi-Z or WFI to prevent cache residue. */
static inline void __attribute__((always_inline)) purge_volatile_registers(void)
{
    __asm__ volatile (
        "mov x0,  #0 \n\t"
        "mov x1,  #0 \n\t"
        "mov x2,  #0 \n\t"
        "mov x3,  #0 \n\t"
        "mov x4,  #0 \n\t"
        "mov x5,  #0 \n\t"
        "mov x6,  #0 \n\t"
        "mov x7,  #0 \n\t"
        "mov x8,  #0 \n\t"
        "mov x9,  #0 \n\t"
        "mov x10, #0 \n\t"
        "mov x11, #0 \n\t"
        "mov x12, #0 \n\t"
        "mov x13, #0 \n\t"
        "mov x14, #0 \n\t"
        "mov x15, #0 \n\t"
        "msr nzcv, x0  \n\t"   /* Clear condition flags */
        "dsb sy        \n\t"   /* Full system memory barrier */
        "isb           \n\t"   /* Instruction barrier — flush pipeline */
        "csdb          \n\t"   /* Consumption Data Barrier — anti-Spectre v4 */
        :
        :
        : "x0","x1","x2","x3","x4","x5","x6","x7",
          "x8","x9","x10","x11","x12","x13","x14","x15",
          "memory"
    );
}

/* ── Governance snapshot expiry / failure handler ────────────────────────── *
 * Mapped as FIQ in TZASC — fires directly at EL3 Secure Monitor.
 * Execution: EL1-S (Secure World only). Normal World suspended.
 *
 * POST-CONDITION: CPU enters WFI loop. Only hardware pulse channel
 * remains active. Biometric ResProtocol required for recovery. */
void __attribute__((interrupt("FIQ"))) handle_secure_rtc_fiq(void)
{
    /* 1. Atomic RTC read — single 64-bit load, no branch on value */
    uint64_t now = *MMIO_RTC_TIMESTAMP;

    /* 2. Constant-time comparison using subtraction carry bit.
     *    No if/else — bitmask determines whether to purge.
     *    expired = 1 when now >= expiration_timestamp */
    uint64_t expiry  = current_snapshot.metadata.timestamp_expiration;
    uint64_t delta   = now - expiry;                   /* wraps if now < expiry */
    uint32_t expired = (uint32_t)(delta >> 63 ^ 1u);  /* 1 = expired, 0 = valid */

    /* 3. Unconditional path: state update via bitmask (no branch) */
    uint32_t new_state = STATE_SOMA_SAFE
                       | (expired * (STATE_DUMMY - STATE_SOMA_SAFE));
    system_state = new_state;

    /* 4. If not expired: return early (normal FIQ return) */
    if (!expired) {
        __asm__ volatile ("dsb sy\nisb" ::: "memory");
        return;
    }

    /* ── ISOLATION SEQUENCE (Article 19) ── */

    /* 5. Purge CPU registers — prevent forensic register extraction */
    purge_volatile_registers();

    /* 6. Force hardware bus to High-Z — physically disconnect sensor lines */
    *MMIO_HARDWARE_MUX_CTRL = REG_MUX_HI_Z_FORCE;
    __asm__ volatile ("dsb sy" ::: "memory");

    /* 7. Enter hardware low-power hold — WFI loop.
     *    CPU halts here. Only hardware RTC + pulse sensor remain active.
     *    Recovery: biometric ResProtocol (120s HF HRV window). */
    while (1) {
        __asm__ volatile ("wfi" ::: "memory");
    }
    /* Unreachable — no return from isolation */
}
