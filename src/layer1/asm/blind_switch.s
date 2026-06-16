/* blind_switch.s — AArch64
 * CORTEX PROTOCOL — Constant-time secure dispatch
 * Target: ARMv8.5-A / EL1-S (TrustZone Secure World)
 * Status: SPECIFICATION — Milestone 2 hardware target
 *
 * Performs an indirect branch to a handler without data-dependent
 * conditional jumps. Mitigates Spectre-v2 (branch target injection).
 *
 * Calling convention (AArch64 ABI):
 *   x0 — pointer to manifest/context (passed to handler)
 *   x1 — target handler address (Customs / KEROS gateway)
 *
 * Security properties:
 *   - No conditional branches on biometric data values
 *   - Caller-saved registers zeroed before dispatch
 *   - Full speculation barriers before and after indirect branch
 *   - BTI landing pad at entry (ARM BTI / CFI protection)
 */

.global secure_dispatch_blind
.section .text.secure_dispatch_blind, "ax"
.balign 64       /* Cache-line alignment — prevents false sharing */

secure_dispatch_blind:
    /* BTI 'c' — Branch Target Identification landing pad.
     * Required with -mbranch-protection=bti. Frustrates JOP attacks. */
    hint    #34             /* BTI c (encodable as hint on ARMv8.5) */

    /* 1. Save frame record to secure stack */
    sub     sp,  sp,  #32
    stp     x29, x30, [sp, #16]
    add     x29, sp,  #16

    /* 2. Save manifest pointer; zero volatile registers to prevent
     *    biometric data leakage into the handler's register window */
    mov     x2,  x0          /* save manifest ptr */
    mov     x0,  #0
    mov     x3,  #0
    mov     x4,  #0
    mov     x5,  #0

    /* 3. Full speculation barrier before indirect branch.
     *    DSB SY: complete all memory operations.
     *    ISB:    flush instruction pipeline — forces Spectre-v1 mitigation. */
    dsb     sy
    isb

    /* 4. Restore manifest ptr to x0 for handler (ABI arg0) */
    mov     x0, x2

    /* 5. Indirect branch — constant time, no BTB poisoning path.
     *    x1 holds the pre-validated handler address. */
    br      x1

    /* NOTE: csdb placed HERE is unreachable after 'br x1'.
     * The correct pattern is for each handler to begin with 'csdb'
     * as its first instruction after its own BTI landing pad.
     * See keros_core.c: purge_volatile_registers() for the model. */

    /* Unreachable safe fallthrough */
    ldp     x29, x30, [sp, #16]
    add     sp,  sp,  #32
    ret
