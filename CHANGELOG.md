# CHANGELOG — Cortex Protocol

All notable changes are documented here in reverse chronological order.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v0.5.1] — 2026-06-15

### Closed backlog items from v0.5.0 (J3)

**[J3.1] TelemetryRouter.ingest_from_bridge() — IMPLEMENTED**

The bridge method connecting `bus_to_sal_bridge` payloads to the telemetry
routing layer is now fully implemented with the following validations:

- Required key schema enforcement (raises `ValueError` on missing fields)
- Timestamp freshness window: ±5.0 seconds from local clock
  (returns `{"reason": "timestamp_out_of_window"}` on violation)
- Feature shape enforcement: `np.ndarray` of shape `(5,)` required
- Polyvagal state whitelist: only the three canonical SAL labels accepted
- Replay attack prevention: per-sensor monotone `frame_seq` counter
  (returns `{"reason": "replay_attack"}` on non-monotone sequence)

**[J3.2] SensorCertificationAuthority ↔ CognitiveShield ECDH link — CLOSED**

`CognitiveShield.register_sensor()` now executes a full X25519 ECDH handshake,
simulating the TEE-Sensor secure channel end-to-end in the Python PoC.

Three new methods added to `SensorCertificationAuthority`:
- `perform_ecdh_handshake(sensor_id, sensor_ephemeral_pub, tee_private_key, challenge)`
  — TEE-side DH key exchange + HKDF session key derivation
- `verify_sensor_ack(session_key, challenge, sensor_ack)`
  — HMAC-SHA256 ACK verification (proves sensor holds matching private key)
- `full_handshake(sensor_id, sensor_ephemeral_pub, sensor_ack, tee_private_key, challenge)`
  — Combined entry point: ECDH + ACK verification in one call

The registration flow:
1. Whitelist membership check
2. Hardware spec verification (SNR ≥ 30 dB, bits ≥ 12)
3. TEE generates ephemeral X25519 keypair; challenge issued
4. Sensor side derives shared secret, computes HMAC-SHA256 ACK
5. `full_handshake()` verifies ACK; on success, sensor_hash is stored
   in `_certified_sensors`

**[J3.3] Test suite expansion 70 → 92+ formal vectors — DONE**

Test suite restructured into 8 named groups with explicit vector ranges:

| Group | Vectors | Coverage |
|-------|---------|----------|
| A | 1–20  | ECDH handshake structure + rejection of unknown sensor |
| B | 21–40 | HKDF session key mathematical correctness |
| C | 41–60 | Full handshake with valid + invalid ACK |
| D | 61–75 | TelemetryRouter schema validation (5 sub-cases) |
| E | 76–85 | Replay protection (4 sub-cases: same, lower, sequential) |
| F | 86–90 | DriftDetector hard block lifecycle (5 assertions) |
| G | 91    | ClinicalBridge std violation |
| H | 92    | ClinicalBridge max violation |

### Bug fixes

**[BF-01] AnonymousTensorFactory.obfuscate() — numpy RuntimeWarning**

Previous code:
```python
noise = np.frombuffer(combined_entropy[:features.nbytes], dtype=np.float32).astype(np.float64)
```

Raw HMAC bytes interpreted as `float32` produce denormal/invalid IEEE 754
values, triggering `RuntimeWarning: invalid value encountered in cast`.

Fix applied:
```python
uint64_values = struct.unpack(f">{n}Q", combined_entropy[:n * 8])
noise = np.array(uint64_values, dtype=np.float64) / float(2**64)
```

`struct.unpack('>5Q')` extracts 5 unsigned 64-bit integers from the first
40 bytes of the 64-byte HMAC buffer. Dividing by 2^64 normalizes to
`[0.0, 1.0)`. Semantically equivalent to the previous approach — still
HMAC-keyed noise — but produces valid floating-point values with no
warnings or potential NaN/inf contamination.

**[BF-02] DriftDetector test vector count (was 3, corrected to 5)**

Previous test asserted that 3 calls to `add_reading(1.0)` trigger the
hard block. This was incorrect. Trace of the correct behavior:

| Reading | window_sum | hard_violations | blocked |
|---------|-----------|-----------------|---------|
| 1       | 1.0       | 0               | False   |
| 2       | 2.0       | 0               | False   |
| 3       | 3.0 > 2.5 | 1               | False (warning) |
| 4       | 4.0 > 2.5 | 2               | False (warning) |
| 5       | 5.0 > 2.5 | 3               | **True** (HARD BLOCK) |

The clinical logic (HARD_BLOCK_VIOLATIONS = 3) is correct and unchanged.
Only the test assertion was wrong. Corrected to require 5 readings.

### Remaining open items (carried to v0.5.2)

- **[J3.4]** `requirements.txt`: add `scipy>=1.11,<2.0` version pin
- **[OI-007]** CPython heap persistence — mlock partial only (TPM 2.0: M1.5)
- **[OI-sandbox]** Python namespace isolation, not true WASM (target: M2)
- **[OI-bus]** Physical ADC pin layer not covered by ECDH (target: M1.5)

---

## [v0.5.0] — 2026-05 (baseline)

### Added
- `GOVERNANCE-NODES.md` — University Node Governance Specification
  - Four Core Invariants as constitutional backbone
  - Formal admission process (IRB + GPG requirements)
  - Node termination, succession, key compromise protocol
  - Regional Compliance Module (RCM) framework
- `external_rule_sandbox.py` — WASM-conceptual isolated rule executor
- `sensor_channel.py` — ECDH X25519 + ChaCha20-Poly1305 AEAD bus encryption
- `bus_to_sal_bridge.py` — integration pipeline
- `state_buffer_secure.py` — secure memory with real `mlock(2)` and ctypes zeroing

### Changed
- `docs/ROADMAP.md` — Removed all specific institution/jurisdiction references;
  fully permissionless-entry neutral standard

### Test count
- 70 tests, 0 failures

---

## [v0.4.5] — 2025 (codebase freeze)

Codebase frozen at this version to avoid scope creep before clinical outreach.

### Added
- `state_buffer_secure.py` with real `mlock(2)` integration
- `sensor_channel.py` with ECDH X25519 + ChaCha20-Poly1305 AEAD
- `bus_to_sal_bridge.py` integration pipeline
- `external_rule_sandbox.py` WASM-conceptual sandbox
- `NEUTRALITY.md` canonical architecture doctrine
- `HARDWARE_STATUS.md` honest hardware simulation documentation

### Security audit
- 14 findings identified and resolved (see SECURITY.md audit log)

---

*Cortex Protocol CHANGELOG — maintained by Protocol Stewards.*
*Clinical patches require White Branch review before release.*
