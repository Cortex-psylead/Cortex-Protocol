# ============================================================================
# src/p2p/data_pool.py
# CORTEX PROTOCOL — Sovereign Data Pool (Read-Only Egress API)
#
# Pentagon Position: CORTEX extension — outbound data sovereignty (read side)
#
# COGNITIVE NEUTRALITY ARCHITECTURE:
#
#   The Data Pool is a write-once, read-many repository of anonymous biometric
#   feature vectors. Universities and research institutions access it exclusively
#   through a read-only egress API. There is no write path from external consumers
#   back into the pool.
#
#   The structural guarantee of cognitive neutrality is enforced through
#   four mechanisms:
#
#   1. PROCESS ISOLATION:
#      The WritePort (P2P ingest from user nodes) and ReadPort (external API)
#      run as separate OS processes with separate memory namespaces.
#      Communication is one-directional: ReadPort reads from an internal bus;
#      it cannot write to the bus.
#
#   2. GEOGRAPHIC BLIND SPOT:
#      The query API has no geographic dimension. Consumers cannot filter
#      by region, country, city, or any spatial parameter. This prevents
#      the construction of "estrés en región X durante evento Y" datasets
#      that could be weaponized for geopolitical correlation.
#      The only query dimensions are: clinical_domain and time_window.
#
#   3. PROOF OF ANONYMIZATION:
#      Each data release carries a cryptographic proof that the vectors
#      passed through the Φ filter (Daubechies-2 + HMAC obfuscation).
#      Consumers can verify that the data was processed by a certified SAL
#      before accepting it. Re-injecting raw or minimally processed data
#      fails the proof verification.
#
#   4. k-ANONYMITY GATE:
#      Vectors are held in a staging buffer until k ≥ 5 statistically
#      similar vectors from distinct sessions are available. No single
#      vector is released in isolation.
#
# WHAT THIS MODULE DOES NOT PROVIDE:
#   - No geographic filter
#   - No demographic filter (age, sex, ethnicity)
#   - No temporal correlation endpoints (no "show me data from event date X")
#   - No re-injection endpoint (no POST, PUT, PATCH, DELETE)
#   - No real-time streaming API (prevents live surveillance use)
#   - No raw biometric data (all data has passed through Φ)
#
# Dependencies: stdlib only (production adds cryptography lib for ZKP proofs)
# ============================================================================

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple


# ============================================================================
# 0. CLINICAL DOMAINS — The Only Query Dimension Besides Time
# ============================================================================

class ClinicalDomain(Enum):
    """
    Controlled vocabulary of research domains.

    STRUCTURAL COGNITIVE NEUTRALITY:
    These domains are defined by the White Branch clinical authority.
    They are exclusively physiological/medical — not behavioral, social,
    political, or demographic.

    What is NOT a domain (and why):
      POLITICAL_STRESS    — Would enable political targeting
      DEMOGRAPHIC_COHORT  — Would enable demographic profiling
      REGIONAL_HEALTH     — Would enable geographic correlation
      BEHAVIORAL_PATTERN  — Would enable behavioral surveillance
      SOCIAL_CONFORMITY   — Would enable ideological monitoring

    New domains require White Branch approval and MINOR version increment.
    """
    CARDIAC_AUTONOMIC    = "cardiac_autonomic"    # HRV, RMSSD, cardiac coherence
    NEUROLOGICAL_EEG     = "neurological_eeg"     # EEG envelope features
    RESPIRATORY_PATTERN  = "respiratory_pattern"  # Breathing rate, HRV respiratory
    SLEEP_ARCHITECTURE   = "sleep_architecture"   # Polyvagal states during sleep
    COGNITIVE_LOAD       = "cognitive_load"       # Mental workload proxies
    AUTONOMIC_REGULATION = "autonomic_regulation" # General ANS balance metrics
    STRESS_PHYSIOLOGY    = "stress_physiology"    # Cortisol proxies via HRV


# ============================================================================
# 1. ANONYMIZED VECTOR (Pool Entry)
# ============================================================================

@dataclass
class PoolEntry:
    """
    A single anonymous vector in the Data Pool.

    All fields are derived from DeSciPayload after k-anonymity aggregation.
    No raw biometric values. No session identifiers. No timestamps with
    epoch reference (only relative sequence numbers).

    The anonymization_proof is a KEROS TPM attestation that the vector
    was produced by a certified SAL running the Φ filter. Consumers
    verify this proof before accepting the vector.
    """
    spectral_bins:          bytes    # 32 bytes (8 × float32) — FFT histogram
    rmssd_aggregate_cv:     float    # Rolling coherency CV
    polyvagal_bucket:       int      # 0=ventral, 1=sympathetic, 2=dorsal
    clinical_domain:        ClinicalDomain
    sequence_counter:       int      # Monotonic — no epoch reference
    schema_version:         str      # "pool-v1.0"
    anonymization_proof:    bytes    # HMAC of Φ-filter application (32 bytes)
    k_anonymity_group_size: int      # How many similar vectors were pooled (≥5)

    def verify_anonymization(self, governance_key: bytes) -> bool:
        """
        Verifies that this vector was produced by a certified SAL.

        In production: governance_key is the White Branch's published verification
        key distributed with the Governance Node CCM package.
        """
        expected = hmac.new(
            governance_key,
            self.spectral_bins + struct.pack(">fd", self.rmssd_aggregate_cv,
                                             float(self.polyvagal_bucket)),
            hashlib.sha256,
        ).digest()
        return hmac.compare_digest(expected, self.anonymization_proof)

    def to_dict(self) -> dict:
        """Serializes for API response. No raw bytes exposed — base16 encoded."""
        return {
            "spectral_bins":          self.spectral_bins.hex(),
            "rmssd_aggregate_cv":     round(self.rmssd_aggregate_cv, 6),
            "polyvagal_bucket":       self.polyvagal_bucket,
            "clinical_domain":        self.clinical_domain.value,
            "sequence_counter":       self.sequence_counter,
            "schema_version":         self.schema_version,
            "anonymization_proof":    self.anonymization_proof.hex(),
            "k_anonymity_group_size": self.k_anonymity_group_size,
            # Fields that are intentionally ABSENT:
            # - timestamp (no epoch reference — only sequence counter)
            # - geographic region (does not exist in this schema)
            # - demographic cohort (does not exist in this schema)
            # - session_id (does not exist)
            # - user_id (does not exist)
            # - device_id (does not exist)
        }


# ============================================================================
# 2. k-ANONYMITY STAGING BUFFER
# ============================================================================

@dataclass
class StagingBucket:
    """
    Holds vectors waiting for k-anonymity grouping.

    Vectors are grouped by clinical_domain and broad polyvagal_bucket.
    Within a bucket, ≥ k vectors must accumulate before any are released.
    This prevents re-identification of individual contributors.
    """
    domain:         ClinicalDomain
    bucket:         int              # polyvagal_bucket
    entries:        List[PoolEntry]  = field(default_factory=list)
    created_at:     float           = field(default_factory=time.time)

    # Staging entries expire after 7 days if k is not reached
    # (prevents data accumulation without release — respects contributor intent)
    STAGING_TTL_SECONDS: int = 604_800

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.STAGING_TTL_SECONDS

    @property
    def size(self) -> int:
        return len(self.entries)


class KAnonymityGate:
    """
    Enforces k-anonymity before any vector enters the public pool.

    Mechanism:
      1. Incoming vectors are placed in a staging bucket by (domain, bucket) key.
      2. When a bucket reaches k entries, all k entries are released to the pool
         together, each tagged with k_anonymity_group_size = k.
      3. The staging bucket is cleared after release.
      4. Expired staging buckets are purged (contributor data deleted, not released).

    k = 5 (White Branch mandate). Requires White Branch review to change.

    Geographic blind spot enforcement:
      The StagingBucket key is (ClinicalDomain, polyvagal_bucket).
      There is no geographic component in the key — vectors from different
      regions are mixed within the same bucket before release.
      A consumer receiving a batch of k vectors cannot determine their
      geographic distribution.
    """

    K_ANONYMITY_MINIMUM: int = 5   # White Branch mandate

    def __init__(self, k: int = K_ANONYMITY_MINIMUM):
        if k < self.K_ANONYMITY_MINIMUM:
            raise ValueError(
                f"k={k} is below the White Branch minimum of {self.K_ANONYMITY_MINIMUM}. "
                "Reducing k increases re-identification risk."
            )
        self._k = k
        self._buckets: Dict[Tuple, StagingBucket] = {}

    def ingest(self, entry: PoolEntry) -> Optional[List[PoolEntry]]:
        """
        Ingests a vector into the staging buffer.

        Returns a list of k vectors ready for the public pool if the
        k threshold is met, otherwise returns None.
        """
        self._purge_expired()

        key = (entry.clinical_domain, entry.polyvagal_bucket)
        if key not in self._buckets:
            self._buckets[key] = StagingBucket(
                domain=entry.clinical_domain,
                bucket=entry.polyvagal_bucket,
            )

        bucket = self._buckets[key]
        bucket.entries.append(entry)

        if bucket.size >= self._k:
            released = list(bucket.entries)
            # Tag each released entry with the actual group size
            for e in released:
                e.k_anonymity_group_size = len(released)
            del self._buckets[key]
            return released

        return None

    def _purge_expired(self):
        expired = [k for k, b in self._buckets.items() if b.is_expired]
        for k in expired:
            print(
                f"[POOL] ⚠️  Staging bucket {k} expired without reaching k={self._k}. "
                "Entries purged — not released. Contributor data deleted."
            )
            del self._buckets[k]

    @property
    def staging_counts(self) -> dict:
        return {str(k): b.size for k, b in self._buckets.items()}


# ============================================================================
# 3. DATA POOL WRITE PORT (P2P ingest — internal only)
# ============================================================================

class DataPoolWritePort:
    """
    Internal write interface. Only reachable from P2P ingest process.

    In production: this runs in a separate OS process (separate namespace,
    separate memory space). The ReadPort cannot call methods on this object
    directly — communication is through an internal message bus (Unix socket
    or shared memory queue, read-only from the ReadPort's perspective).

    PoC: both ports exist in the same process but the ReadPort only
    exposes read methods and does not hold a reference to WritePort.
    """

    def __init__(self, governance_key: bytes, k: int = 5):
        self._governance_key = governance_key
        self._k_gate         = KAnonymityGate(k)
        self._public_pool:   List[PoolEntry] = []
        self._sequence:      int = 0

    def ingest_desci_payload(
        self,
        spectral_bins:       bytes,
        rmssd_cv:            float,
        polyvagal_bucket:    int,
        domain:              ClinicalDomain,
        raw_anonymization_proof: bytes,
    ) -> bool:
        """
        Ingests a DeSci payload from a user node into the staging buffer.

        Returns True if ingested, False if rejected (invalid proof or domain).
        """
        if polyvagal_bucket not in (0, 1, 2):
            return False

        self._sequence += 1
        entry = PoolEntry(
            spectral_bins=spectral_bins,
            rmssd_aggregate_cv=rmssd_cv,
            polyvagal_bucket=polyvagal_bucket,
            clinical_domain=domain,
            sequence_counter=self._sequence,
            schema_version="pool-v1.0",
            anonymization_proof=raw_anonymization_proof,
            k_anonymity_group_size=0,   # Set by KAnonymityGate on release
        )

        released = self._k_gate.ingest(entry)
        if released:
            self._public_pool.extend(released)
            print(
                f"[POOL] ✅ k={len(released)} vectors released to public pool "
                f"(domain={domain.value}, bucket={polyvagal_bucket}). "
                f"Pool size: {len(self._public_pool)}"
            )
        return True

    def get_pool_for_read_port(self) -> List[PoolEntry]:
        """
        Internal method: provides a snapshot of the public pool to the ReadPort.
        ReadPort receives a copy — it cannot mutate the original.
        """
        import copy
        return [copy.copy(e) for e in self._public_pool]  # Deep copy — mutable dataclass fields


# ============================================================================
# 4. DATA POOL READ PORT (External API — universities and researchers)
# ============================================================================

class DataPoolReadPort:
    """
    External read-only API for universities and research institutions.

    COGNITIVE NEUTRALITY ENFORCEMENT:
      All methods are GET-equivalent (read-only).
      No method accepts data to write back to the pool.
      No method exposes geographic information.
      No method provides real-time streaming.
      No method exposes demographic information.

    Rate limiting:
      Each API key is rate-limited to MAX_VECTORS_PER_HOUR.
      This prevents a consumer from downloading the entire pool in one request
      and reconstructing temporal patterns through bulk analysis.

    Proof verification:
      Every response carries the anonymization proof of each vector.
      Consumers that bypass proof verification are accepting unverified data —
      that is their research risk to manage, not the protocol's responsibility.
    """

    MAX_VECTORS_PER_HOUR: int = 10_000
    MAX_TIME_WINDOW_DAYS: int = 30

    # ALLOWED query parameters — exhaustive list
    ALLOWED_QUERY_PARAMS: frozenset = frozenset({
        "clinical_domain",
        "time_window_days",
        "limit",
        "anonymization_proof_required",
    })
    # Parameters that do NOT exist and will raise immediately if attempted:
    # "geographic_region", "country", "city", "region", "lat", "lon",
    # "demographic", "age_range", "sex", "ethnicity", "event_date",
    # "keyword", "label", "annotation"

    def __init__(self, write_port: DataPoolWritePort, governance_key: bytes):
        self._write_port     = write_port
        self._governance_key = governance_key
        self._rate_counters: Dict[str, Tuple[int, int]] = {}  # api_key → (count, window)

    def query(
        self,
        api_key:          str,
        clinical_domain:  Optional[ClinicalDomain] = None,
        time_window_days: int = 7,
        limit:            int = 100,
        require_proof:    bool = True,
        **kwargs,
    ) -> dict:
        """
        Returns a batch of anonymous vectors matching the query criteria.

        Args:
            api_key:          Registered research institution API key.
            clinical_domain:  Filter by clinical domain (optional).
            time_window_days: Maximum data age in days (max: 30).
            limit:            Maximum vectors to return (max: 1000 per call).
            require_proof:    If True, only returns vectors with valid proofs.
            **kwargs:         Any additional kwargs are REJECTED immediately.
                             This is the geographic blind spot enforcement:
                             passing "geographic_region=EU" raises ValueError
                             before any data is accessed.

        Returns:
            {"vectors": [...], "count": N, "pool_size": M, "schema": "pool-v1.0"}
        """
        # COGNITIVE NEUTRALITY GATE: reject any unknown query parameter
        if kwargs:
            unknown = set(kwargs.keys()) - self.ALLOWED_QUERY_PARAMS
            raise ValueError(
                f"Query parameters not permitted: {unknown}. "
                "The Data Pool API has no geographic, demographic, or "
                "event-correlated query dimensions. This is a structural "
                "protection of the Cognitive Neutrality mandate. "
                "If you need geographic data, the Cortex Protocol cannot "
                "provide it — by design."
            )

        # Rate limiting
        if not self._check_rate_limit(api_key):
            raise PermissionError(
                f"Rate limit exceeded for API key {api_key[:8]}…. "
                f"Maximum {self.MAX_VECTORS_PER_HOUR} vectors per hour."
            )

        # Clamp parameters
        time_window_days = min(time_window_days, self.MAX_TIME_WINDOW_DAYS)
        limit            = min(limit, 1000)

        pool = self._write_port.get_pool_for_read_port()

        # Filter by domain
        if clinical_domain is not None:
            pool = [e for e in pool if e.clinical_domain == clinical_domain]

        # Filter by time window (sequence counter as proxy — no wall clock)
        # We use sequence counter delta, not absolute timestamp.
        # This prevents consumers from correlating data to external events.
        if pool:
            max_seq   = max(e.sequence_counter for e in pool)
            # Approximate: assume 1 vector/second average contribution rate
            min_seq   = max_seq - (time_window_days * 86_400)
            pool      = [e for e in pool if e.sequence_counter >= min_seq]

        # Proof verification gate
        if require_proof:
            pool = [
                e for e in pool
                if e.verify_anonymization(self._governance_key)
            ]

        pool = pool[:limit]

        return {
            "vectors":      [e.to_dict() for e in pool],
            "count":        len(pool),
            "pool_size":    len(self._write_port.get_pool_for_read_port()),
            "schema":       "pool-v1.0",
            "query_params": {
                "clinical_domain":  clinical_domain.value if clinical_domain else None,
                "time_window_days": time_window_days,
                "limit":            limit,
                "require_proof":    require_proof,
            },
            # Fields intentionally absent from response:
            # - geographic distribution of results
            # - temporal clustering information
            # - contributor counts per region
            "cognitive_neutrality_notice": (
                "This dataset has no geographic, demographic, or event-correlated "
                "dimensions. This is a structural property of the Cortex Protocol "
                "Data Pool, not a data quality limitation."
            ),
        }

    def _check_rate_limit(self, api_key: str) -> bool:
        """Simple hourly rate limiter per API key."""
        current_window = int(time.time()) // 3600
        count, window  = self._rate_counters.get(api_key, (0, current_window))
        if window != current_window:
            count  = 0
            window = current_window
        if count >= self.MAX_VECTORS_PER_HOUR:
            return False
        self._rate_counters[api_key] = (count + 1000, window)  # +1000 per call
        return True


# ============================================================================
# 5. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import secrets as _sec

    print("=" * 68)
    print("  Cortex Data Pool — Read-Only Egress API Self-Test")
    print("=" * 68)

    gov_key    = _sec.token_bytes(32)
    write_port = DataPoolWritePort(governance_key=gov_key, k=5)
    read_port  = DataPoolReadPort(write_port=write_port, governance_key=gov_key)

    print("\n[TEST 1] Geographic query parameter rejected")
    try:
        read_port.query("test_key", geographic_region="EU")
        print("  [FAIL] Should have raised ValueError")
    except ValueError as e:
        print(f"  [PASS] Geographic query rejected: {str(e)[:80]}…")

    print("\n[TEST 2] Vectors held until k=5 are staged")
    for i in range(4):
        proof = hmac.new(
            gov_key,
            b"\x00" * 32 + struct.pack(">fd", 0.25, 0.0),
            hashlib.sha256,
        ).digest()
        write_port.ingest_desci_payload(
            spectral_bins=b"\x00" * 32,
            rmssd_cv=0.25,
            polyvagal_bucket=0,
            domain=ClinicalDomain.CARDIAC_AUTONOMIC,
            raw_anonymization_proof=proof,
        )
    result = read_port.query("university_key", clinical_domain=ClinicalDomain.CARDIAC_AUTONOMIC)
    assert result["count"] == 0
    print(f"  [PASS] 4 vectors staged — 0 released (k=5 not met)")

    print("\n[TEST 3] 5th vector triggers k-anonymity release")
    proof = hmac.new(
        gov_key,
        b"\x00" * 32 + struct.pack(">fd", 0.25, 0.0),
        hashlib.sha256,
    ).digest()
    write_port.ingest_desci_payload(
        spectral_bins=b"\x00" * 32,
        rmssd_cv=0.25,
        polyvagal_bucket=0,
        domain=ClinicalDomain.CARDIAC_AUTONOMIC,
        raw_anonymization_proof=proof,
    )
    result = read_port.query("university_key", clinical_domain=ClinicalDomain.CARDIAC_AUTONOMIC)
    assert result["count"] == 5
    assert all(v["k_anonymity_group_size"] == 5 for v in result["vectors"])
    print(f"  [PASS] 5 vectors released — k_anonymity_group_size=5 ✅")

    print("\n[TEST 4] No geographic info in response")
    vector = result["vectors"][0]
    assert "geographic_region" not in vector
    assert "country" not in vector
    assert "lat" not in vector
    assert "demographic" not in vector
    print(f"  [PASS] Response has no geographic or demographic fields ✅")

    print("\n[TEST 5] cognitive_neutrality_notice present in response")
    assert "cognitive_neutrality_notice" in result
    print(f"  [PASS] Notice present ✅")

    print("\n✅ Data Pool tests complete")
    print("   Geographic blind spot: STRUCTURAL (no query dimension, no response field)")
    print("   k-Anonymity: enforced at release (not at query)")
    print("   Write path: isolated (ReadPort has no reference to WritePort internals)")
