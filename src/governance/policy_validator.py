# ============================================================================
# src/governance/policy_validator.py
# Governance Node: Local Policy Snapshot Validation
# Implements ARCHITECTURE-ASYNC.md (Decision 3)
# ============================================================================

import json
import time
from typing import Dict, Optional
import hashlib
import hmac


class PolicySnapshot:
    """Immutable, versioned, cryptographically signed policy snapshot."""
    def __init__(self, data: Dict, signature: bytes, public_key: bytes):
        self.data = data
        self.signature = signature
        self.public_key = public_key
        # Sort keys to ensure deterministic JSON serialization
        self._hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).digest()

    def verify(self) -> bool:
        """Verifies the GPG‑style signature (simulated with HMAC for PoC)."""
        expected = hmac.new(self.public_key, self._hash, hashlib.sha256).digest()
        return hmac.compare_digest(expected, self.signature)

    @property
    def version(self) -> int:
        return self.data.get("version", 0)

    @property
    def expires_at(self) -> float:
        return self.data.get("expires_at", 0)

    @property
    def thresholds(self) -> Dict:
        return self.data.get("thresholds", {})


class PolicyValidator:
    """
    Validates, stores, and applies policy snapshots from Governance Nodes.
    Enforces monotonic version numbers and expiry.
    """

    def __init__(self):
        self._active_snapshot: Optional[PolicySnapshot] = None
        self._last_version = 0
        self._storage_path = "./policy_cache.json"

    def load_snapshot(self, snapshot_data: Dict, signature: bytes, public_key: bytes) -> bool:
        """
        Load and validate a new snapshot. Replaces active snapshot if valid and newer.
        Returns True if the snapshot was accepted.
        """
        snapshot = PolicySnapshot(snapshot_data, signature, public_key)

        if not snapshot.verify():
            print("[GOV] Invalid signature – snapshot rejected")
            return False

        if snapshot.version <= self._last_version:
            print(f"[GOV] Replay attempt: version {snapshot.version} ≤ {self._last_version}")
            return False

        if snapshot.expires_at < time.time():
            print("[GOV] Snapshot expired")
            return False

        self._active_snapshot = snapshot
        self._last_version = snapshot.version
        print(f"[GOV] Snapshot v{snapshot.version} activated (expires at {snapshot.expires_at})")
        return True

    def get_threshold(self, key: str, default=None):
        """Retrieve a threshold from the active snapshot, or default if none active."""
        if self._active_snapshot is None:
            return default
        return self._active_snapshot.thresholds.get(key, default)

    def is_active(self) -> bool:
        """Returns True if a valid, non‑expired snapshot is active."""
        return (self._active_snapshot is not None and
                self._active_snapshot.expires_at > time.time())
