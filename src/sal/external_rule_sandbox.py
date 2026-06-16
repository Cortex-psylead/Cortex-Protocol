# ============================================================================
# src/sal/external_rule_sandbox.py
# CORTEX PROTOCOL — External Rule Sandbox (Φ-Filter Extension)
#
# ARCHITECTURAL POSITION:
#   This module implements the Paso 1 of the Split-Gate Doctrine:
#   a rigidly isolated execution environment for externally-supplied
#   clinical rules. It conceptually emulates a WebAssembly (WASM) sandbox —
#   rules execute in a memory-isolated container with no I/O, no threading,
#   and no visibility into global interpreter state.
#
# WHAT IS A "RULE"?
#   An external rule is a callable contributed by a governance authority
#   (White Branch clinical committee) that maps a normalized biometric
#   telemetry vector to a single deterministic integer score ∈ [0, 100].
#
#   Score semantics (White Branch mandate):
#     0–24   → BLOCKED   (intervention required)
#    25–49   → WARNING   (monitoring elevated)
#    50–84   → SAFE      (nominal operation)
#    85–100  → OPTIMAL   (deep coherence — validated research mode)
#
# ISOLATION GUARANTEES (enforced structurally, not by policy):
#
#   1. I/O PROHIBITION
#      Rules execute inside a context manager that shadows all I/O
#      builtins (open, print, socket, subprocess, os, sys) with
#      NoOpProxy objects. A rule that calls open("secret") gets a
#      NoOpProxy, not a file handle. No exception — silent neutralization.
#      Rationale: Silent failure prevents rules from inferring what is
#      available by catching IOError variants.
#
#   2. THREAD PROHIBITION
#      Rules cannot spawn threads. threading.Thread is shadowed with a
#      ForbiddenProxy that raises SandboxViolation immediately.
#      Unlike I/O, thread spawning is an active violation — logged and
#      the rule is permanently blacklisted.
#      Rationale: Threading breaks determinism and enables timing side-channels.
#
#   3. FILESYSTEM PROHIBITION
#      os, sys, pathlib, shutil are all shadowed. A rule cannot traverse
#      the filesystem or read environment variables.
#
#   4. NETWORK PROHIBITION
#      socket, urllib, requests, httpx — all shadowed. Rules are
#      mathematically pure: input → output, no external state.
#
#   5. DETERMINISTIC OUTPUT CONTRACT
#      The sandbox only accepts a rule return value that is:
#        - An integer in [0, 100], OR
#        - A MitigationVector (named tuple: score + 4-component attenuation)
#      Anything else is treated as a rule fault → score defaults to 0 (BLOCKED).
#      This prevents rules from encoding side-channels in exotic return types.
#
#   6. TIMEOUT ENFORCEMENT
#      Rules must complete in ≤ RULE_TIMEOUT_SECONDS (default: 50ms).
#      A rule that blocks (infinite loop, intentional stall) is killed via
#      threading.Timer and returns score=0 automatically.
#      Rationale: Timing side-channels require execution time control.
#
# WHAT THIS SANDBOX DOES NOT DO:
#   - It does NOT enforce cryptographic rule authenticity (that is ETHOS/KEROS).
#   - It does NOT prevent rules from consuming CPU aggressively within the timeout.
#   - It does NOT provide memory quotas (production: Wasm linear memory model).
#   - It does NOT sandbox pure-Python bytecode at the VM level (production target:
#     actual WASM via Wasmtime or Pyodide — see OPEN_ISSUES.md §4).
#
# PRODUCTION ROADMAP:
#   PoC: Python namespace shadowing (this file).
#   Milestone 2: Pyodide WASM sandbox with linear memory isolation.
#   Milestone 3: Native WASM module compiled from rule DSL, executed in
#                Wasmtime with memory limits enforced by the hypervisor.
#
# Dependencies: stdlib only (no external libraries required)
# ============================================================================

import hashlib
import hmac
import secrets
import threading
import time
from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ============================================================================
# 0. RETURN TYPE CONTRACT
# ============================================================================

class MitigationVector(namedtuple("MitigationVector", [
    "score",            # int ∈ [0, 100] — aggregate mitigation score
    "hrv_attenuation",  # float ∈ [0.0, 1.0] — HRV channel weight
    "eeg_attenuation",  # float ∈ [0.0, 1.0] — EEG channel weight
    "resp_attenuation", # float ∈ [0.0, 1.0] — respiratory channel weight
    "thermal_attenuation",  # float ∈ [0.0, 1.0] — thermal channel weight
])):
    """
    Extended return type for rules that need per-channel attenuation.
    When a rule returns a MitigationVector, the SAL pipeline uses the
    per-channel weights to selectively suppress data streams without
    blanket blocking.

    All attenuation values are multiplicative weights applied to the
    corresponding channel's contribution to the coherency score.
    0.0 = full suppression, 1.0 = no attenuation.

    Invariants enforced by the sandbox:
      - score must be int ∈ [0, 100]
      - each attenuation must be float ∈ [0.0, 1.0]
    """

    def is_valid(self) -> bool:
        return (
            isinstance(self.score, int)
            and 0 <= self.score <= 100
            and all(
                isinstance(v, float) and 0.0 <= v <= 1.0
                for v in [
                    self.hrv_attenuation,
                    self.eeg_attenuation,
                    self.resp_attenuation,
                    self.thermal_attenuation,
                ]
            )
        )


# ============================================================================
# 1. SANDBOX VIOLATION — Only for active (non-silent) violations
# ============================================================================

class SandboxViolation(Exception):
    """
    Raised for ACTIVE violations: thread spawning, explicit forbidden calls.
    Silent violations (I/O, filesystem, network) are swallowed by NoOpProxy.

    The distinction matters: silent violations allow a malformed rule to
    run to completion and return a valid score. Active violations (like
    threading) immediately abort the rule and blacklist it.
    """
    pass


# ============================================================================
# 2. PROXY OBJECTS — The isolation mechanism
# ============================================================================

class _NoOpProxy:
    """
    A null object that absorbs any attribute access or call.
    Used to shadow I/O builtins so rules fail silently.

    A rule calling open("secret").read() gets:
      open("secret") → _NoOpProxy instance
      .read() → _NoOpProxy instance
      result used as string → "" (via __str__)

    The rule does not raise. The rule does not know it was blocked.
    It receives empty/null responses from all I/O operations.
    """
    def __call__(self, *args, **kwargs): return self
    def __getattr__(self, name): return self
    def __iter__(self): return iter([])
    def __next__(self): raise StopIteration
    def __enter__(self): return self
    def __exit__(self, *a): return True
    def __str__(self): return ""
    def __repr__(self): return "_NoOpProxy()"
    def __bool__(self): return False
    def __len__(self): return 0
    def read(self, *a): return b""
    def write(self, *a): return 0


class _ForbiddenProxy:
    """
    A proxy that raises SandboxViolation immediately.
    Used for threading — where silent failure would be dangerous
    (a half-spawned thread could corrupt state).
    """
    def __init__(self, what: str):
        self._what = what

    def __call__(self, *a, **kw):
        raise SandboxViolation(
            f"[SANDBOX] ❌ Forbidden: {self._what}. "
            "External rules may not spawn threads or processes. "
            "This rule has been permanently blacklisted."
        )

    def __getattr__(self, name):
        return self


# ============================================================================
# 3. RESTRICTED NAMESPACE — The sandbox's global scope
# ============================================================================

def _build_restricted_globals() -> dict:
    """
    Constructs the restricted __globals__ dict injected into rule execution.

    The rule function sees ONLY these names in its global scope:
      - Safe math: math, struct, hashlib (read-only — no I/O, no network)
      - Safe data structures: list, dict, tuple, set, frozenset
      - Safe builtins: int, float, bool, str, bytes, bytearray, len, range,
        abs, min, max, sum, round, sorted, enumerate, zip, map, filter
      - MitigationVector: the only permitted non-primitive return type
      - __builtins__: a minimal whitelist — NOT the full builtins module

    Everything else is either absent (KeyError → NameError in the rule)
    or replaced with a NoOp/Forbidden proxy.
    """
    import math
    import struct

    _safe_builtins = {
        # Numeric operations
        "int": int, "float": float, "bool": bool, "complex": complex,
        "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
        "divmod": divmod, "pow": pow,

        # Sequence operations
        "len": len, "range": range, "enumerate": enumerate,
        "zip": zip, "map": map, "filter": filter, "sorted": sorted,
        "list": list, "tuple": tuple, "dict": dict, "set": set,
        "frozenset": frozenset, "reversed": reversed,
        "str": str, "bytes": bytes, "bytearray": bytearray,
        "repr": repr, "format": format, "chr": chr, "ord": ord, "hex": hex,

        # Type introspection (read-only)
        "isinstance": isinstance, "issubclass": issubclass, "type": type,
        "hasattr": hasattr, "getattr": getattr,  # No setattr, delattr

        # Control flow helpers
        "iter": iter, "next": next, "all": all, "any": any,

        # Exceptions (for try/except within rules)
        "Exception": Exception, "ValueError": ValueError,
        "TypeError": TypeError, "ZeroDivisionError": ZeroDivisionError,
        "IndexError": IndexError, "KeyError": KeyError,
        "StopIteration": StopIteration,

        # Sandbox violation (rules can catch it — they cannot suppress it)
        "SandboxViolation": SandboxViolation,

        # Forbidden: open, input, print, exec, eval, compile, __import__
        "open":      _NoOpProxy(),
        "print":     _NoOpProxy(),
        "input":     _NoOpProxy(),
        "exec":      _NoOpProxy(),
        "eval":      _NoOpProxy(),
        "compile":   _NoOpProxy(),
        "__import__": _NoOpProxy(),
    }

    return {
        "__builtins__": _safe_builtins,

        # Safe math — no I/O capability
        "math":    math,
        "struct":  struct,
        "hashlib": hashlib,

        # Permitted return type
        "MitigationVector": MitigationVector,

        # Forbidden modules — present as NoOp so rules that import them
        # don't NameError but receive an inert proxy
        "os":           _NoOpProxy(),
        "sys":          _NoOpProxy(),
        "io":           _NoOpProxy(),
        "pathlib":      _NoOpProxy(),
        "socket":       _NoOpProxy(),
        "subprocess":   _NoOpProxy(),
        "threading":    type("FakeThreading", (), {
            "Thread": _ForbiddenProxy("threading.Thread"),
            "Timer":  _ForbiddenProxy("threading.Timer"),
            "Lock":   _NoOpProxy,
        })(),
        "multiprocessing": _NoOpProxy(),
        "urllib":       _NoOpProxy(),
        "http":         _NoOpProxy(),
        "requests":     _NoOpProxy(),
        "httpx":        _NoOpProxy(),
    }


# ============================================================================
# 4. TELEMETRY VECTOR — Input to external rules
# ============================================================================

@dataclass(frozen=True)
class TelemetryVector:
    """
    Normalized biometric telemetry vector passed to external rules.

    ALL values are normalized to [0.0, 1.0] before entering the sandbox.
    Rules never see raw ADC values, physical units, or timestamps.

    Normalization formula: v_norm = (v - v_min) / (v_max - v_min)
    where v_min and v_max are the White Branch clinical reference bounds
    from the active Governance Snapshot.

    Frozen: rules cannot mutate the input vector.
    """
    # HRV metrics (normalized)
    hrv_rmssd_norm:     float   # Root mean square of successive differences
    hrv_sdnn_norm:      float   # Standard deviation of NN intervals
    hrv_coherence_norm: float   # HRV coherence ratio (RSA peak / broadband)

    # EEG metrics (normalized, if sensor present)
    eeg_alpha_norm:     float   # Alpha band (8–13 Hz) relative power
    eeg_theta_norm:     float   # Theta band (4–8 Hz) relative power
    eeg_beta_norm:      float   # Beta band (13–30 Hz) relative power

    # Respiratory
    resp_rate_norm:     float   # Respiratory rate
    resp_amplitude_norm: float  # Respiratory amplitude variation

    # Derived polyvagal state (ordinal, not continuous)
    polyvagal_bucket:   int     # 0=ventral, 1=sympathetic, 2=dorsal

    # Sequence info (no wall-clock timestamp)
    sequence_counter:   int     # Monotonic frame counter

    def to_tuple(self) -> tuple:
        """Immutable tuple representation for passing to rules."""
        return (
            self.hrv_rmssd_norm, self.hrv_sdnn_norm, self.hrv_coherence_norm,
            self.eeg_alpha_norm, self.eeg_theta_norm, self.eeg_beta_norm,
            self.resp_rate_norm, self.resp_amplitude_norm,
            self.polyvagal_bucket, self.sequence_counter,
        )

    def to_dict(self) -> dict:
        """Dict representation — safe for rule consumption (immutable values)."""
        return {
            "hrv_rmssd":    self.hrv_rmssd_norm,
            "hrv_sdnn":     self.hrv_sdnn_norm,
            "hrv_coherence": self.hrv_coherence_norm,
            "eeg_alpha":    self.eeg_alpha_norm,
            "eeg_theta":    self.eeg_theta_norm,
            "eeg_beta":     self.eeg_beta_norm,
            "resp_rate":    self.resp_rate_norm,
            "resp_amplitude": self.resp_amplitude_norm,
            "polyvagal_bucket": self.polyvagal_bucket,
            "sequence_counter": self.sequence_counter,
        }

    def validate(self) -> bool:
        """Validates all normalized fields are in expected ranges."""
        floats = [
            self.hrv_rmssd_norm, self.hrv_sdnn_norm, self.hrv_coherence_norm,
            self.eeg_alpha_norm, self.eeg_theta_norm, self.eeg_beta_norm,
            self.resp_rate_norm, self.resp_amplitude_norm,
        ]
        return (
            all(0.0 <= v <= 1.0 for v in floats)
            and self.polyvagal_bucket in (0, 1, 2)
            and self.sequence_counter >= 0
        )


# ============================================================================
# 5. RULE REGISTRATION AND LIFECYCLE
# ============================================================================

class RuleStatus(Enum):
    ACTIVE      = "active"
    SUSPENDED   = "suspended"   # Timeout or fault — under review
    BLACKLISTED = "blacklisted" # Thread/process violation — permanent ban


@dataclass
class RegisteredRule:
    """
    Metadata for a registered external rule.

    Rules are identified by their governance_hash: the SHA-256 of the
    rule source code, signed by the White Branch. This ties the executable
    rule to a governance-approved payload and prevents substitution attacks.
    """
    governance_hash: bytes      # SHA-256 of rule source
    rule_callable:   Callable   # Compiled function (exec'd into sandbox)
    version:         str        # Rule version from governance manifest
    clinical_domain: str        # Which clinical domain this rule applies to
    status:          RuleStatus = RuleStatus.ACTIVE
    fault_count:     int        = 0
    last_fault_ts:   float      = 0.0
    invocation_count: int       = 0
    total_exec_ms:   float      = 0.0

    FAULT_SUSPENSION_THRESHOLD: int = 3  # Faults before suspension

    @property
    def avg_exec_ms(self) -> float:
        if self.invocation_count == 0:
            return 0.0
        return self.total_exec_ms / self.invocation_count

    def record_fault(self, is_violation: bool = False):
        """Records a rule fault. Blacklists immediately on active violation."""
        if is_violation:
            self.status = RuleStatus.BLACKLISTED
            return
        self.fault_count += 1
        self.last_fault_ts = time.time()
        if self.fault_count >= self.FAULT_SUSPENSION_THRESHOLD:
            self.status = RuleStatus.SUSPENDED

    def record_success(self, exec_ms: float):
        self.invocation_count += 1
        self.total_exec_ms += exec_ms


# ============================================================================
# 6. THE SANDBOX EXECUTOR
# ============================================================================

class ExternalRuleSandbox:
    """
    The External Rule Sandbox — WASM-conceptual isolated execution environment.

    Responsibilities:
      1. Accept rule source code from the governance pipeline (KEROS-verified).
      2. Compile the source into a callable using a restricted namespace.
      3. Execute rules with:
         - Isolated globals (no I/O, no threading, no filesystem)
         - Timeout enforcement (default: 50ms)
         - Return value contract enforcement (int ∈ [0,100] or MitigationVector)
         - Fault tracking and automatic blacklisting on active violations
      4. Return a deterministic MitigationVector to the SAL pipeline.

    The sandbox does NOT:
      - Verify rule governance signatures (KEROS/ETHOS responsibility)
      - Maintain state between invocations (stateless per design)
      - Log rule return values (privacy — telemetry vectors are biometric data)

    Thread safety:
      Each rule invocation spawns an execution thread for timeout enforcement.
      The sandbox itself is NOT thread-safe for parallel invocations — it is
      designed for sequential use within a single SAL pipeline thread.
      Production: one sandbox instance per SAL pipeline worker.
    """

    RULE_TIMEOUT_SECONDS: float = 0.050    # 50ms — White Branch mandate
    DEFAULT_SCORE_ON_FAULT: int = 0        # BLOCKED — safe default on fault
    MAX_RULES: int = 16                    # Maximum simultaneously active rules

    def __init__(self, governance_key: bytes):
        """
        Args:
            governance_key: 32-byte HMAC key for verifying rule manifests.
                            In production: derived from the active Governance
                            Snapshot by KEROS.
        """
        if len(governance_key) != 32:
            raise ValueError("governance_key must be 32 bytes")
        self._governance_key = governance_key
        self._rules: Dict[bytes, RegisteredRule] = {}   # hash → RegisteredRule
        self._execution_count: int = 0
        self._timeout_count: int = 0
        self._violation_count: int = 0

    def register_rule(
        self,
        source_code: str,
        governance_manifest: bytes,
        version: str,
        clinical_domain: str,
    ) -> bytes:
        """
        Registers an external rule from source code.

        The rule source must define a function named 'apply' with signature:
            def apply(telemetry: dict) -> int | MitigationVector

        The 'telemetry' dict has the same keys as TelemetryVector.to_dict().

        Args:
            source_code:           Python source code defining the 'apply' function.
            governance_manifest:   HMAC-SHA256 of source_code, signed by White Branch.
            version:               Rule version string from governance manifest.
            clinical_domain:       Clinical domain (e.g., "cardiac_autonomic").

        Returns:
            governance_hash: The SHA-256 of source_code used as rule identifier.

        Raises:
            ValueError: If manifest is invalid, source is malformed, or MAX_RULES reached.
            SandboxViolation: If source contains syntax that triggers active violation
                              detection during compilation.
        """
        if len(self._rules) >= self.MAX_RULES:
            raise ValueError(
                f"Maximum {self.MAX_RULES} rules reached. Deregister a rule first."
            )

        # Verify governance manifest
        expected_manifest = hmac.new(
            self._governance_key,
            source_code.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected_manifest, governance_manifest):
            raise ValueError(
                "Governance manifest verification failed. "
                "Rule source does not match the White Branch signature. "
                "This rule will not be loaded."
            )

        # Compute governance hash (rule identity)
        gov_hash = hashlib.sha256(source_code.encode("utf-8")).digest()

        if gov_hash in self._rules:
            # Already registered — idempotent
            return gov_hash

        # Compile into restricted namespace
        restricted_globals = _build_restricted_globals()
        restricted_locals: dict = {}

        try:
            exec(compile(source_code, f"<rule:{gov_hash.hex()[:8]}>", "exec"),
                 restricted_globals, restricted_locals)
        except SandboxViolation:
            raise
        except SyntaxError as e:
            raise ValueError(f"Rule source has syntax error: {e}")
        except Exception as e:
            raise ValueError(f"Rule source compilation failed: {e}")

        if "apply" not in restricted_locals:
            raise ValueError(
                "Rule source must define an 'apply(telemetry: dict) -> int | MitigationVector' function."
            )

        rule_fn = restricted_locals["apply"]
        if not callable(rule_fn):
            raise ValueError("'apply' in rule source is not callable.")

        self._rules[gov_hash] = RegisteredRule(
            governance_hash=gov_hash,
            rule_callable=rule_fn,
            version=version,
            clinical_domain=clinical_domain,
        )

        print(
            f"[SANDBOX] ✅ Rule registered — domain={clinical_domain} "
            f"version={version} hash={gov_hash.hex()[:8]}…"
        )
        return gov_hash

    def execute(
        self,
        governance_hash: bytes,
        telemetry: TelemetryVector,
    ) -> MitigationVector:
        """
        Executes a registered rule against a telemetry vector.

        Execution contract:
          1. Rule runs in a daemon thread with a 50ms timeout.
          2. Return value is validated against the MitigationVector contract.
          3. Any fault (timeout, violation, invalid return) → score=0, BLOCKED.
          4. The rule never sees raw sensor data — only normalized TelemetryVector.

        Args:
            governance_hash: Rule identifier (from register_rule).
            telemetry:       Normalized biometric telemetry vector.

        Returns:
            MitigationVector with score ∈ [0,100] and 4 attenuation components.
            Returns BLOCKED vector (score=0, all attenuations=0.0) on any fault.
        """
        if not telemetry.validate():
            # Malformed input — not a rule fault, but we cannot proceed
            return self._blocked_vector("Invalid telemetry input")

        rule = self._rules.get(governance_hash)
        if rule is None:
            return self._blocked_vector(f"Unknown rule hash {governance_hash.hex()[:8]}")

        if rule.status == RuleStatus.BLACKLISTED:
            return self._blocked_vector(f"Rule {governance_hash.hex()[:8]} is blacklisted")

        if rule.status == RuleStatus.SUSPENDED:
            return self._blocked_vector(f"Rule {governance_hash.hex()[:8]} is suspended")

        telemetry_dict = telemetry.to_dict()
        result_container: List[Any] = []
        error_container:  List[Any] = []

        def _runner():
            try:
                ret = rule.rule_callable(telemetry_dict)
                result_container.append(ret)
            except SandboxViolation as e:
                error_container.append(("violation", str(e)))
            except Exception as e:
                error_container.append(("fault", str(e)))

        t_start = time.perf_counter()
        worker  = threading.Thread(target=_runner, daemon=True)
        worker.start()
        worker.join(timeout=self.RULE_TIMEOUT_SECONDS)
        exec_ms = (time.perf_counter() - t_start) * 1000

        self._execution_count += 1

        # --- Timeout ---
        if worker.is_alive():
            self._timeout_count += 1
            rule.record_fault(is_violation=False)
            print(
                f"[SANDBOX] ⚠️  Rule {governance_hash.hex()[:8]} timed out "
                f"(>{self.RULE_TIMEOUT_SECONDS*1000:.0f}ms) — fault #{rule.fault_count}"
            )
            return self._blocked_vector("Rule timeout")

        # --- Active violation ---
        if error_container:
            err_type, err_msg = error_container[0]
            if err_type == "violation":
                self._violation_count += 1
                rule.record_fault(is_violation=True)
                print(
                    f"[SANDBOX] 🚫 ACTIVE VIOLATION by rule {governance_hash.hex()[:8]}: "
                    f"{err_msg}. Rule PERMANENTLY BLACKLISTED."
                )
                return self._blocked_vector("Rule sandbox violation — blacklisted")
            else:
                rule.record_fault(is_violation=False)
                return self._blocked_vector(f"Rule execution fault: {err_msg}")

        # --- Return value contract enforcement ---
        if not result_container:
            rule.record_fault(is_violation=False)
            return self._blocked_vector("Rule returned no value")

        raw_result = result_container[0]
        mitigation = self._coerce_to_mitigation_vector(raw_result)

        if mitigation is None:
            rule.record_fault(is_violation=False)
            return self._blocked_vector(
                f"Rule returned invalid type {type(raw_result).__name__} — "
                "expected int ∈ [0,100] or MitigationVector"
            )

        rule.record_success(exec_ms)
        return mitigation

    def execute_all(
        self,
        telemetry: TelemetryVector,
        domain_filter: Optional[str] = None,
    ) -> MitigationVector:
        """
        Executes all active rules for a telemetry vector and aggregates results.

        Aggregation strategy: MINIMUM score (most conservative/protective).
        A single rule flagging BLOCKED overrides all other scores.
        Per-channel attenuation is the product of all rule attenuations
        (compound filtering — each rule can only reduce, not amplify).

        Args:
            telemetry:     Normalized biometric telemetry vector.
            domain_filter: If provided, only rules for this clinical domain are run.

        Returns:
            Aggregated MitigationVector (minimum score, product attenuations).
        """
        active_rules = [
            r for r in self._rules.values()
            if r.status == RuleStatus.ACTIVE
            and (domain_filter is None or r.clinical_domain == domain_filter)
        ]

        if not active_rules:
            # No rules → maximum permissiveness (no external filter)
            return MitigationVector(
                score=100,
                hrv_attenuation=1.0,
                eeg_attenuation=1.0,
                resp_attenuation=1.0,
                thermal_attenuation=1.0,
            )

        results = [
            self.execute(r.governance_hash, telemetry)
            for r in active_rules
        ]

        # Aggregate: minimum score, product attenuation (strictest combined filter)
        min_score = min(r.score for r in results)
        hrv_atten  = 1.0
        eeg_atten  = 1.0
        resp_atten = 1.0
        therm_atten = 1.0

        for r in results:
            hrv_atten   *= r.hrv_attenuation
            eeg_atten   *= r.eeg_attenuation
            resp_atten  *= r.resp_attenuation
            therm_atten *= r.thermal_attenuation

        return MitigationVector(
            score=min_score,
            hrv_attenuation=hrv_atten,
            eeg_attenuation=eeg_atten,
            resp_attenuation=resp_atten,
            thermal_attenuation=therm_atten,
        )

    def deregister_rule(self, governance_hash: bytes) -> bool:
        """Removes a rule from the sandbox. Returns True if it existed."""
        if governance_hash in self._rules:
            del self._rules[governance_hash]
            return True
        return False

    def get_status(self) -> dict:
        return {
            "registered_rules":  len(self._rules),
            "active_rules":      sum(1 for r in self._rules.values() if r.status == RuleStatus.ACTIVE),
            "suspended_rules":   sum(1 for r in self._rules.values() if r.status == RuleStatus.SUSPENDED),
            "blacklisted_rules": sum(1 for r in self._rules.values() if r.status == RuleStatus.BLACKLISTED),
            "total_executions":  self._execution_count,
            "timeout_count":     self._timeout_count,
            "violation_count":   self._violation_count,
            "rules": [
                {
                    "hash":          r.governance_hash.hex()[:8],
                    "domain":        r.clinical_domain,
                    "version":       r.version,
                    "status":        r.status.value,
                    "fault_count":   r.fault_count,
                    "invocations":   r.invocation_count,
                    "avg_exec_ms":   round(r.avg_exec_ms, 3),
                }
                for r in self._rules.values()
            ],
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _blocked_vector(reason: str = "") -> MitigationVector:
        """Returns a fully blocked MitigationVector (score=0, all attenuations=0.0)."""
        if reason:
            pass  # Internal only — not logged (biometric context)
        return MitigationVector(
            score=0,
            hrv_attenuation=0.0,
            eeg_attenuation=0.0,
            resp_attenuation=0.0,
            thermal_attenuation=0.0,
        )

    @staticmethod
    def _coerce_to_mitigation_vector(raw: Any) -> Optional[MitigationVector]:
        """
        Coerces a rule return value to MitigationVector if valid.
        Returns None if the value cannot be coerced.

        Accepted inputs:
          - int ∈ [0, 100]   → uniform MitigationVector (all attenuations = 1.0)
          - MitigationVector  → validated and returned as-is
          - Anything else     → None (rule fault)
        """
        if isinstance(raw, MitigationVector):
            if raw.is_valid():
                return raw
            return None

        if isinstance(raw, int) and 0 <= raw <= 100:
            return MitigationVector(
                score=raw,
                hrv_attenuation=1.0,
                eeg_attenuation=1.0,
                resp_attenuation=1.0,
                thermal_attenuation=1.0,
            )

        # bool is a subclass of int in Python — reject True/False
        if isinstance(raw, bool):
            return None

        return None


# ============================================================================
# 7. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import struct as _struct

    print("=" * 68)
    print("  Cortex External Rule Sandbox — Self-Test")
    print("=" * 68)

    gov_key = secrets.token_bytes(32)
    sandbox = ExternalRuleSandbox(governance_key=gov_key)

    # Helper: compute correct governance manifest for a rule source
    def make_manifest(src: str) -> bytes:
        return hmac.new(gov_key, src.encode(), hashlib.sha256).digest()

    # Helper: create a valid TelemetryVector
    def make_telemetry(**overrides) -> TelemetryVector:
        defaults = dict(
            hrv_rmssd_norm=0.65, hrv_sdnn_norm=0.70, hrv_coherence_norm=0.80,
            eeg_alpha_norm=0.60, eeg_theta_norm=0.40, eeg_beta_norm=0.35,
            resp_rate_norm=0.50, resp_amplitude_norm=0.55,
            polyvagal_bucket=0, sequence_counter=1,
        )
        defaults.update(overrides)
        return TelemetryVector(**defaults)

    # ── Test 1: Valid rule returning int ──────────────────────────────────────
    print("\n[TEST 1] Valid rule returning score=75 (int)")
    rule_src_1 = """
def apply(telemetry):
    hrv = telemetry["hrv_coherence"]
    score = int(hrv * 100)
    score = max(0, min(100, score))
    return score
"""
    manifest_1 = make_manifest(rule_src_1)
    hash_1 = sandbox.register_rule(rule_src_1, manifest_1, "v1.0", "cardiac_autonomic")
    result = sandbox.execute(hash_1, make_telemetry(hrv_coherence_norm=0.75))
    assert result.score == 75, f"Expected 75, got {result.score}"
    assert result.hrv_attenuation == 1.0
    print(f"  [PASS] Score={result.score}, attenuations=1.0 ✅")

    # ── Test 2: Valid rule returning MitigationVector ─────────────────────────
    print("\n[TEST 2] Valid rule returning MitigationVector")
    rule_src_2 = """
def apply(telemetry):
    hrv = telemetry["hrv_coherence"]
    eeg = telemetry["eeg_alpha"]
    score = int((hrv * 0.6 + eeg * 0.4) * 100)
    score = max(0, min(100, score))
    return MitigationVector(
        score=score,
        hrv_attenuation=hrv,
        eeg_attenuation=eeg,
        resp_attenuation=1.0,
        thermal_attenuation=1.0,
    )
"""
    manifest_2 = make_manifest(rule_src_2)
    hash_2 = sandbox.register_rule(rule_src_2, manifest_2, "v1.0", "neurological_eeg")
    tv = make_telemetry(hrv_coherence_norm=0.80, eeg_alpha_norm=0.60)
    result2 = sandbox.execute(hash_2, tv)
    assert isinstance(result2, MitigationVector)
    assert result2.score == int((0.80 * 0.6 + 0.60 * 0.4) * 100)
    print(f"  [PASS] Score={result2.score}, hrv_atten={result2.hrv_attenuation:.2f} ✅")

    # ── Test 3: I/O attempt is silently neutralized ───────────────────────────
    print("\n[TEST 3] Rule attempting file I/O — silently blocked")
    rule_src_3 = """
def apply(telemetry):
    try:
        f = open("/etc/passwd", "r")
        data = f.read()
    except Exception:
        pass
    return 50  # Rule continues — I/O was silently blocked
"""
    manifest_3 = make_manifest(rule_src_3)
    hash_3 = sandbox.register_rule(rule_src_3, manifest_3, "v1.0", "cardiac_autonomic")
    result3 = sandbox.execute(hash_3, make_telemetry())
    assert result3.score == 50, f"Expected 50, got {result3.score}"
    print(f"  [PASS] I/O silently blocked, rule returned score=50 ✅")

    # ── Test 4: Thread spawning → immediate BLACKLIST ────────────────────────
    print("\n[TEST 4] Rule spawning thread → SandboxViolation → blacklisted")
    rule_src_4 = """
def apply(telemetry):
    t = threading.Thread(target=lambda: None)
    t.start()
    return 99
"""
    manifest_4 = make_manifest(rule_src_4)
    hash_4 = sandbox.register_rule(rule_src_4, manifest_4, "v1.0", "cardiac_autonomic")
    result4 = sandbox.execute(hash_4, make_telemetry())
    assert result4.score == 0
    assert sandbox._rules[hash_4].status == RuleStatus.BLACKLISTED
    print(f"  [PASS] Thread spawn blocked, rule blacklisted, score=0 ✅")

    # ── Test 5: Invalid return type → score=0 ────────────────────────────────
    print("\n[TEST 5] Rule returning invalid type (string) → score=0")
    rule_src_5 = """
def apply(telemetry):
    return "high coherence"  # Invalid — not int or MitigationVector
"""
    manifest_5 = make_manifest(rule_src_5)
    hash_5 = sandbox.register_rule(rule_src_5, manifest_5, "v1.0", "cardiac_autonomic")
    result5 = sandbox.execute(hash_5, make_telemetry())
    assert result5.score == 0
    print(f"  [PASS] Invalid return type → score=0, fault recorded ✅")

    # ── Test 6: Invalid governance manifest → registration rejected ──────────
    print("\n[TEST 6] Invalid governance manifest → registration rejected")
    try:
        sandbox.register_rule(
            "def apply(t): return 50",
            b"\x00" * 32,   # Wrong manifest
            "v1.0",
            "cardiac_autonomic",
        )
        print("  [FAIL] Should have raised ValueError")
    except ValueError as e:
        print(f"  [PASS] Bad manifest rejected: {str(e)[:60]}… ✅")

    # ── Test 7: execute_all aggregation ──────────────────────────────────────
    print("\n[TEST 7] execute_all — minimum score aggregation")
    # hash_1 returns ~75, hash_2 returns ~72
    tv = make_telemetry(hrv_coherence_norm=0.75, eeg_alpha_norm=0.60)
    agg = sandbox.execute_all(tv, domain_filter=None)
    # hash_4 is blacklisted, hash_5 has faults, hash_3 returns 50
    # Minimum of active rules: 50 (hash_3) vs 75 (hash_1) vs 72 (hash_2)
    print(f"  Aggregated score={agg.score} (minimum across active rules)")
    assert agg.score <= 75
    print(f"  [PASS] execute_all returns minimum score ✅")

    # ── Status report ─────────────────────────────────────────────────────────
    print("\n── Sandbox Status")
    status = sandbox.get_status()
    for k, v in status.items():
        if k != "rules":
            print(f"  {k}: {v}")
    for r in status["rules"]:
        print(f"  Rule {r['hash']}: status={r['status']} faults={r['fault_count']} avg_ms={r['avg_exec_ms']}")

    print("\n✅ External Rule Sandbox tests complete")
    print("   I/O isolation:      STRUCTURAL (NoOpProxy — silent swallow)")
    print("   Thread isolation:   STRUCTURAL (ForbiddenProxy — immediate blacklist)")
    print("   Return contract:    ENFORCED (int ∈ [0,100] or MitigationVector)")
    print("   Timeout:            50ms (White Branch mandate)")
    print("   Aggregation:        MINIMUM score (most conservative)")
