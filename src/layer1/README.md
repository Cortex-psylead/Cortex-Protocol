# Layer 1 — Bare-Metal Firmware Specification

**Status:** SPECIFICATION — Target: Milestone 2 (hardware validation)

This directory contains the bare-metal firmware specification for the Cortex Protocol
Sovereignty Abstraction Layer running in ARM TrustZone EL1-S.

## Target Platform

- **CPU:** ARMv8.5-A (Snapdragon 8 Gen 1 reference platform)
- **Security:** TrustZone EL1-S (Secure World only execution)
- **Memory:** Secure SRAM (KEROS-mapped, access-controlled)

## Files

| File | Language | Purpose |
|------|----------|---------|
| `c/keros_types.h` | C | Secure enclave data structures |
| `c/keros_core.c` | C | FIQ handler + Hi-Z isolation sequence |
| `c/biometric_filter.c` | C | Phi operator: Db2 wavelet + Box-Muller noise |
| `rust/matrix_inspector.rs` | Rust | LIMES: Shannon entropy validation |
| `rust/agora_diff_privacy.rs` | Rust | LDP: Laplace mechanism (constant-time) |
| `asm/blind_switch.s` | AArch64 ASM | Constant-time secure dispatch |

## Build

Layer 1 is a specification only. No build system is provided until Milestone 2
when the first hardware platform is selected and validated.

Target toolchain:
- C: `aarch64-none-elf-gcc` with `-march=armv8.5-a+sve -mabi=lp64`
- Rust: `cargo build --target aarch64-unknown-none --no-std`
- ASM: `aarch64-none-elf-as`

## Known Limitations

All Layer 1 code exists only in the Python PoC simulation. The following are
NOT implemented until Milestone 2:
- Real ARM TrustZone EL1-S context
- TPM 2.0 attestation
- Hardware LIMES entropy source
- Physical bus ECDH encryption (logical only in current PoC)
