## Asynchronous Architecture: Solving the Biological-AI Latency Asymmetry

**Document ID: ARCH-ASYNC-001 | Version: 1.0**
**Relates to:** [ARCHITECTURE.md](ARCHITECTURE.md) — extends the Sovereignty Loop section.

---

## The Problem: Speed Asymmetry

The Cortex Protocol mediates between two systems that operate at fundamentally different timescales:

| System | Timescale | Example |
| :--- | :--- | :--- |
| AI agent (Acolyte) | Milliseconds | Token generation, inference, response |
| Biometric sensor (HRV, GSR) | Seconds | Heart rate update, HRV window calculation |
| Governance Node validation | Minutes to hours | Policy snapshot refresh |

**If the AI pipeline waits for synchronous biometric validation on every request, the system becomes unusable.** A 2-second HRV update cycle would introduce 2-second latency into every AI interaction. At scale, this collapses the user experience and defeats the protocol's purpose.

This is a known architectural constraint, not an oversight. This document specifies the required solution.

---

## The Solution: Three Non-Negotiable Design Decisions

### Decision 1 — Separated Threads (Async Processing)

The AI pipeline and the biometric reader run in completely independent threads or processes. They never block each other.

```
Thread A: Biometric Reader
  Sensor → Feature Extraction → CDI Update → State Buffer Write

Thread B: AI Pipeline
  User Request → State Buffer Read → Acolyte → Response

Thread A and Thread B NEVER call each other directly.
Communication happens ONLY through the State Buffer.
```

This separation is architectural law. Any implementation that introduces synchronous coupling between Thread A and Thread B violates the protocol's latency requirements.

### Decision 2 — Local Biological State Buffer

The system maintains a local, in-memory state object that the AI pipeline can read with zero network latency. The biometric thread updates it asynchronously in the background.

**Required structure of the State Buffer:**

```python
@dataclass
class BiometricStateBuffer:
    status: str           # "SAFE" | "WARNING" | "BLOCKED"
    polyvagal_state: str  # "ventral_vagal" | "sympathetic" | "dorsal_vagal"
    coherency_index: float
    timestamp: float      # Unix timestamp of last real sensor reading
    sensor_hmac: bytes    # HMAC(status + timestamp, sensor_session_key)
    ttl_seconds: int = 5  # State expires if sensor goes silent

    def is_valid(self) -> bool:
        """
        Two conditions must BOTH be true for state to be trusted:
        1. Timestamp is recent (sensor is alive)
        2. HMAC is valid (state was written by authenticated sensor thread)
        If either fails → treat as BLOCKED (safe-fail, not fail-open)
        """
        if time.time() - self.timestamp > self.ttl_seconds:
            return False  # Sensor silent — fail safe
        expected_hmac = hmac.new(
            SENSOR_SESSION_KEY,
            f"{self.status}{self.timestamp}".encode(),
            hashlib.sha256
        ).digest()
        return hmac.compare_digest(expected_hmac, self.sensor_hmac)
```

**Critical constraint:** Only the authenticated biometric thread may write to the State Buffer. The AI pipeline is read-only. This must be enforced at the process level, not by convention.

### Decision 3 — Local Policy Snapshot

Clinical thresholds and CDI rules are downloaded once per day from the active Governance Node as a cryptographically signed package. All validation runs locally — no network round-trip per request.

**Required snapshot structure:**

```json
{
  "version": 42,
  "issued_at": 1748000000,
  "expires_at": 1748086400,
  "issuer_node": "governance-node-usc-cali",
  "thresholds": {
    "bridge_std_limit": 0.5,
    "bridge_p75_limit": 0.7,
    "bridge_max_limit": 0.9,
    "max_coherency_sum_per_minute": 2.5,
    "hard_block_violations": 3,
    "soft_block_violations": 5
  },
  "signature": "<GPG signature of above content>"
}
```

**Validation rules for the snapshot:**
- Reject if GPG signature is invalid.
- Reject if `version` is lower than the last accepted version (prevents replay attacks with older, less restrictive policies).
- Reject if `expires_at` has passed.
- On rejection, continue using the last valid snapshot. Do not fail open.

---

## Known Vulnerabilities — Developers Must Address These

These are not theoretical. They are exploitable if not resolved.

### Vulnerability 1 — State Buffer Injection (Critical)

**Attack:** A malicious process writes `status = "SAFE"` directly to the State Buffer, bypassing the biometric thread entirely.

**Mitigation:** The HMAC in the State Buffer (Decision 2 above) makes this detectable. The AI pipeline must always call `is_valid()` before trusting the state. A forged state cannot produce a valid HMAC without the sensor session key.

**Additional mitigation:** On Linux/macOS, the state buffer process should use OS-level memory protection (e.g., `mprotect` with write restriction for the AI process). On mobile, use the platform's Secure Enclave for the sensor session key.

### Vulnerability 2 — Silent Sensor Failure (Critical)

**Attack / failure mode:** The sensor disconnects or stops transmitting. The State Buffer retains the last state indefinitely. If that state was `SAFE`, the AI continues operating without any biometric oversight.

**Mitigation:** The TTL field in the State Buffer (5 seconds default). If the biometric thread has not written a fresh state within TTL, `is_valid()` returns False, which the Circuit Breaker treats as BLOCKED. Silence equals block — never silence equals safe.

### Vulnerability 3 — Policy Snapshot Replay Attack (High)

**Attack:** An attacker captures a valid snapshot with permissive thresholds (e.g., from a period before thresholds were tightened) and re-injects it.

**Mitigation:** The monotonic `version` field. The client stores the last accepted version number in persistent local storage. Any snapshot with a lower or equal version number to the currently active one is rejected, even if the signature is valid.

### Vulnerability 4 — Race Condition on State Buffer Write/Read (Medium)

**Attack / failure mode:** The biometric thread writes `BLOCKED` to the buffer at the exact moment the AI thread reads `SAFE` — the AI reads stale state.

**Mitigation:** Use atomic operations for the status field. In Python: `threading.Event` or `asyncio.Lock` wrapping the buffer write. The window of vulnerability without this is microseconds — small but nonzero and exploitable under high-frequency sensor updates.

---

## Required Design Patterns

These are not suggestions. They are the implementation contract for any developer building on this architecture.

### Pattern 1 — Circuit Breaker (Primary Safety Mechanism)

Wraps every call to the Acolyte. If the State Buffer is invalid, expired, or BLOCKED, the Circuit Breaker opens and the request never reaches the AI.

```python
class BiometricCircuitBreaker:
    """
    Three states:
    CLOSED  → normal operation, buffer valid and SAFE
    OPEN    → blocked, buffer invalid/expired/BLOCKED
    HALF-OPEN → testing recovery after a block period
    """

    def __init__(self, state_buffer: BiometricStateBuffer):
        self.buffer = state_buffer
        self._circuit = "CLOSED"

    def call(self, acolyte_fn, *args, **kwargs):
        if not self.buffer.is_valid():
            self._circuit = "OPEN"
            raise BiometricStateExpiredError(
                "Sensor data expired or invalid — safe fail engaged"
            )

        if self.buffer.status == "BLOCKED":
            self._circuit = "OPEN"
            raise CDIBlockError(
                f"CDI threshold exceeded — polyvagal state: "
                f"{self.buffer.polyvagal_state}"
            )

        self._circuit = "CLOSED"
        return acolyte_fn(*args, **kwargs)
```

### Pattern 2 — Observer with Unidirectional Channel

The biometric thread publishes state change events to a channel. The AI thread subscribes passively. No direct calls between threads in either direction.

```
Biometric Thread  →  [Event Queue]  →  State Buffer
AI Thread         ←reads only from←   State Buffer

Rule: AI Thread NEVER writes to State Buffer.
Rule: State Buffer NEVER calls AI Thread.
Rule: Biometric Thread NEVER calls AI Thread directly.
```

This eliminates circular dependencies and makes the system's behavior under concurrency easy to reason about.

### Pattern 3 — Snapshot Pattern for Policies

The daily policy snapshot is treated as an immutable versioned object. It is never mutated in memory. When a new snapshot arrives:

1. Validate the new snapshot (signature, version, expiry).
2. If valid, create a new snapshot object.
3. Atomic swap: replace the reference to the active snapshot.
4. Keep the previous snapshot in memory during a grace period for in-flight sessions.
5. Discard the previous snapshot after the grace period.

No session ever operates on a partially-updated policy set.

### Pattern 4 — CQRS for the Audit Log

The session audit log uses Command Query Responsibility Segregation:

- **Write side (Commands):** append-only, immutable. Biometric events, CDI decisions, block events, consent changes are written here and never modified.
- **Read side (Queries):** indexed projections of the write log for fast queries by the user or forensic review.

This satisfies the STANDARD.md audit log requirements and ensures that any security incident is fully reconstructible.

---

## Implementation Checklist for Developers

Before submitting a pull request that touches the async pipeline, verify:

- [ ] Biometric thread and AI thread have zero direct calls between them
- [ ] State Buffer writes are atomic and protected from concurrent access
- [ ] State Buffer `is_valid()` checks both HMAC and TTL before returning trusted state
- [ ] Circuit Breaker is the sole entry point to Acolyte invocation
- [ ] Sensor silence (TTL expiry) defaults to BLOCKED, not SAFE
- [ ] Policy snapshot validation checks: GPG signature, version monotonicity, expiry
- [ ] Audit log is append-only on the write side
- [ ] No network call occurs in the synchronous AI request path

---

## Relationship to Other Documents

| Document | Relationship |
| :--- | :--- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Parent document — this extends the Sovereignty Loop section |
| [STANDARD.md](STANDARD.md) | Section 2.1 (SAL data boundary) and 2.8 (audit log) impose requirements implemented here |
| [MODULE-ISOLATION.md](MODULE-ISOLATION.md) | Thread isolation rules extend the module isolation model |
| [SECURITY.md](SECURITY.md) | Vulnerabilities 1–4 above are additions to the threat model |

---

*ARCHITECTURE-ASYNC.md v1.0 — Protocol Stewards.*
*Any modification to the Circuit Breaker behavior or State Buffer structure requires White Branch review if it affects CDI threshold enforcement.*
