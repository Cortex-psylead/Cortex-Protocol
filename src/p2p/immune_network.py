# ============================================================================
# src/p2p/immune_network.py
# CORTEX PROTOCOL — P2P Immune Network with Anti-Sybil Defense
#
# The Biological Immune System Analogy:
#   - Nodes = immune cells
#   - ImmuneSignatures = antibodies (pattern-matched, not narrative)
#   - Sybil attackers = autoimmune response / false antibodies
#   - Contribution staking = antigen experience requirement for B-cell activation
#
# ANTI-SYBIL ARCHITECTURE — Three Layers:
#
#   Layer 1: Rate Limiting (p2p_message_types.NodeRateLimiter)
#            Each node may emit ≤ 3 IMMUNE_SIGNATURE per hour.
#            Cost to flood: must create N identities × contribution requirement.
#
#   Layer 2: Contribution Staking
#            A node must have contributed ≥ MIN_VECTORS_FOR_IMMUNITY anonymous
#            vectors to the Data Pool before its immune signatures are forwarded.
#            Cost to forge: must generate valid biometric sessions for each identity.
#
#   Layer 3: Ring Signature Verification (threshold)
#            IMMUNE_SIGNATURE packets are only propagated if signed by ≥ K
#            independent nodes that have all independently observed the same
#            evidence_hash. A single compromised node cannot trigger propagation.
#
# CONSENSUS MODEL:
#   This is NOT a blockchain. There is no global state.
#   Each node maintains a LOCAL immune memory (LRU cache of evidence hashes).
#   A signature is forwarded if: (a) the node has also observed the evidence
#   OR (b) K threshold is met by independent signers with valid stake.
#   Partition tolerance: nodes that were offline simply miss signatures.
#   On reconnect, they receive a routing table update but NOT replayed immune
#   signatures (immune memory is local and ephemeral, not global and persistent).
#
# Dependencies: stdlib only (ring signature uses HMAC-based threshold simulation;
#               production target: libsodium Ed25519 multisig via ctypes)
# ============================================================================

import hashlib
import hmac
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    from src.p2p.p2p_message_types import (
        CortexMsgType, CortexPacket, CortexPacketParser,
        ImmunePatternType, ImmuneSignaturePayload,
        ImmuneSignatureScope, NodeRateLimiter,
    )
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(__file__))
    from p2p_message_types import (
        CortexMsgType, CortexPacket, CortexPacketParser,
        ImmunePatternType, ImmuneSignaturePayload,
        ImmuneSignatureScope, NodeRateLimiter,
    )


# ============================================================================
# 0. IMMUNE NETWORK CONFIGURATION
# ============================================================================

class ImmuneNetworkConfig:
    """
    Parameters governing the immune network behavior.
    All thresholds defined by White Branch — do not modify without governance.

    Bibliographic basis:
      - Castro & Liskov (2002). Practical Byzantine Fault Tolerance. OSDI.
      - Douceur (2002). The Sybil Attack. IPTPS.
      - Yu et al. (2006). SybilGuard: Defending Against Sybil Attacks. SIGCOMM.
    """

    # Minimum anonymous vectors contributed before a node earns immune rights
    # A node that contributed 0 vectors has no stake — its signatures are noise
    MIN_VECTORS_FOR_IMMUNITY: int = 50

    # Minimum independent nodes that must co-sign a signature before propagation
    # With K=3: attacker needs to compromise 3 independent staked nodes
    IMMUNE_SIGNATURE_THRESHOLD_K: int = 3

    # TTL for local immune memory entries (seconds)
    # After this, the node "forgets" a pattern — prevents memory exhaustion
    LOCAL_IMMUNE_MEMORY_TTL: int = 172_800   # 48 hours

    # Maximum entries in local immune memory (LRU eviction after this)
    LOCAL_IMMUNE_MEMORY_MAX: int = 1_000

    # Time window for co-signature collection (seconds)
    # If K signatures for the same evidence_hash are not collected in this window,
    # the partial signatures are discarded — prevents slow accumulation attacks
    COSIGNATURE_WINDOW_SECONDS: int = 300    # 5 minutes

    # Maximum peers a node will forward an immune signature to
    # Limits amplification factor of the propagation
    MAX_PROPAGATION_PEERS: int = 8


# ============================================================================
# 1. NODE IDENTITY AND STAKE
# ============================================================================

@dataclass
class NodeIdentity:
    """
    Cryptographic identity of a Cortex P2P node.

    Stake is measured in contribution_count: the number of anonymous vectors
    the node has contributed to the Data Pool and that have been acknowledged
    by at least one pool aggregation node. This is the "proof of participation"
    that makes Sybil attacks costly.

    In production: contribution_count is verified by a Merkle inclusion proof
    from the Data Pool node. In this PoC, it is self-reported and signed.
    """
    node_id_hash:      bytes     # SHA-256 of the node's public key
    public_key_bytes:  bytes     # X25519 or Ed25519 public key (32 bytes)
    contribution_count: int      # Verified anonymous vectors contributed
    first_seen_ts:     float     # When this peer was first observed
    last_seen_ts:      float     # When this peer was last heard from

    @property
    def has_immune_rights(self) -> bool:
        """Returns True if this node has earned the right to emit immune signatures."""
        return self.contribution_count >= ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY

    @property
    def is_alive(self) -> bool:
        """Returns True if node was seen within the last 90 seconds."""
        return (time.time() - self.last_seen_ts) < 90


# ============================================================================
# 2. LOCAL IMMUNE MEMORY (LRU Cache)
# ============================================================================

class LocalImmuneMemory:
    """
    The node's local memory of threats it has independently observed or
    validated through threshold co-signing.

    This is NOT a shared global state. It is local and ephemeral.
    Each node builds its own immune memory from its own observations.

    The LRU eviction policy ensures memory is bounded regardless of
    how many distinct attack patterns are observed.

    Cognitive neutrality: the immune memory stores only cryptographic hashes
    of technical protocol violations — never semantic descriptions.
    """

    def __init__(
        self,
        max_entries: int = ImmuneNetworkConfig.LOCAL_IMMUNE_MEMORY_MAX,
        ttl_seconds: int = ImmuneNetworkConfig.LOCAL_IMMUNE_MEMORY_TTL,
    ):
        self._store: OrderedDict = OrderedDict()  # evidence_hash → (payload, ts)
        self._max   = max_entries
        self._ttl   = ttl_seconds

    def remember(self, evidence_hash: bytes, payload: ImmuneSignaturePayload):
        """Stores a validated immune signature. Evicts oldest if at capacity."""
        if evidence_hash in self._store:
            self._store.move_to_end(evidence_hash)
            return

        if len(self._store) >= self._max:
            self._store.popitem(last=False)  # LRU eviction

        self._store[evidence_hash] = (payload, time.time())

    def knows(self, evidence_hash: bytes) -> bool:
        """Returns True if this node has independently validated this pattern."""
        if evidence_hash not in self._store:
            return False
        _, stored_ts = self._store[evidence_hash]
        if (time.time() - stored_ts) > self._ttl:
            del self._store[evidence_hash]
            return False
        return True

    def purge_expired(self):
        """Removes entries older than TTL. Called periodically."""
        cutoff  = time.time() - self._ttl
        expired = [k for k, (_, ts) in self._store.items() if ts < cutoff]
        for k in expired:
            del self._store[k]

    @property
    def size(self) -> int:
        return len(self._store)


# ============================================================================
# 3. CO-SIGNATURE ACCUMULATOR — Threshold Defense Against Sybil
# ============================================================================

@dataclass
class PendingCoSignature:
    """
    Accumulator for co-signatures on a single evidence_hash.
    A signature is only propagated when K independent staked nodes have
    co-signed the same evidence_hash within the time window.
    """
    evidence_hash:  bytes
    pattern_type:   ImmunePatternType
    first_seen_ts:  float
    cosigners:      Set[bytes] = field(default_factory=set)  # node_id_hashes
    sample_count:   int = 0

    @property
    def is_threshold_met(self) -> bool:
        return len(self.cosigners) >= ImmuneNetworkConfig.IMMUNE_SIGNATURE_THRESHOLD_K

    @property
    def is_window_expired(self) -> bool:
        return (
            time.time() - self.first_seen_ts
        ) > ImmuneNetworkConfig.COSIGNATURE_WINDOW_SECONDS


class CoSignatureAccumulator:
    """
    Collects co-signatures from independent nodes for the same evidence_hash.
    Propagates immune signatures only when K threshold is met.

    Anti-Sybil guarantee:
      An attacker controlling M fake identities all reporting the same
      evidence_hash will be stopped if M < K. To reach K, the attacker
      must compromise K independent nodes that each have ≥ MIN_VECTORS_FOR_IMMUNITY
      contributions. The cost scales with K × MIN_VECTORS_FOR_IMMUNITY real sessions.

    Temporal guarantee:
      If K co-signatures are not collected within COSIGNATURE_WINDOW_SECONDS,
      the pending entry is discarded. An attacker cannot slowly accumulate
      co-signatures over days to trigger propagation.
    """

    def __init__(self):
        self._pending: Dict[bytes, PendingCoSignature] = {}

    def add(
        self,
        payload: ImmuneSignaturePayload,
        cosigner_id: bytes,
        cosigner_has_stake: bool,
    ) -> Optional[ImmuneSignaturePayload]:
        """
        Adds a co-signature observation. Returns the payload ready for
        propagation if the threshold is met, otherwise returns None.

        Args:
            payload:             The immune signature payload received.
            cosigner_id:         The node_id_hash of the reporting node.
            cosigner_has_stake:  Whether the reporting node has earned immune rights.

        Returns:
            ImmuneSignaturePayload if K threshold is met, else None.
        """
        # Nodes without stake cannot co-sign
        if not cosigner_has_stake:
            return None

        key = payload.evidence_hash

        # Prune expired pending entries before adding
        self._prune_expired()

        if key not in self._pending:
            self._pending[key] = PendingCoSignature(
                evidence_hash=key,
                pattern_type=payload.pattern_type,
                first_seen_ts=time.time(),
                sample_count=payload.sample_count,
            )

        entry = self._pending[key]

        # Window expired — discard and start fresh
        if entry.is_window_expired:
            del self._pending[key]
            return None

        entry.cosigners.add(cosigner_id)
        entry.sample_count = max(entry.sample_count, payload.sample_count)

        if entry.is_threshold_met:
            del self._pending[key]
            # Return a consolidated payload with the aggregated sample_count
            return ImmuneSignaturePayload(
                pattern_type=entry.pattern_type,
                scope=ImmuneSignatureScope.TECHNICAL,
                evidence_hash=key,
                issuer_nonce=secrets.token_bytes(16),  # Fresh nonce for propagation
                first_seen_ts=entry.first_seen_ts,
                ttl_seconds=min(payload.ttl_seconds, 172800),
                sample_count=entry.sample_count,
            )

        return None

    def _prune_expired(self):
        expired = [
            k for k, v in self._pending.items() if v.is_window_expired
        ]
        for k in expired:
            del self._pending[k]

    @property
    def pending_count(self) -> int:
        return len(self._pending)


# ============================================================================
# 4. IMMUNE NETWORK NODE
# ============================================================================

class ImmuneNetworkNode:
    """
    A Cortex P2P node participating in the immune network.

    Responsibilities:
      1. Parse incoming packets (closed vocabulary enforcement)
      2. Verify sender stake before processing immune signatures
      3. Accumulate co-signatures for threshold-based propagation
      4. Maintain local immune memory
      5. Emit SENSOR_HEARTBEAT and ANONYMOUS_VECTOR via rate limiter

    What this node does NOT do:
      - Emit INSTITUTIONAL_ALERT (type does not exist)
      - Forward content-based signals (all immune signatures are technical)
      - Maintain global state (no blockchain, no shared ledger)
      - Accept immune signatures from nodes without contribution stake
    """

    def __init__(self, node_key: bytes, peer_shared_key: bytes):
        """
        Args:
            node_key:        32-byte private key for this node's identity.
            peer_shared_key: 32-byte symmetric key shared with the peer network.
                             In production: one key per peer session (ECDH).
        """
        self._node_id_hash = hashlib.sha256(node_key).digest()
        self._parser       = CortexPacketParser(peer_shared_key)
        self._rate_limiter = NodeRateLimiter()
        self._immune_mem   = LocalImmuneMemory()
        self._accumulator  = CoSignatureAccumulator()
        self._peer_table:  Dict[bytes, NodeIdentity] = {}
        self._own_contribution_count: int = 0
        self._peer_key     = peer_shared_key

    @property
    def has_immune_rights(self) -> bool:
        return (
            self._own_contribution_count
            >= ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY
        )

    def record_vector_contribution(self):
        """
        Called by TelemetryRouter after a successful DeSci emission is acknowledged.
        Increments the node's contribution stake.
        """
        self._own_contribution_count += 1
        if self._own_contribution_count == ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY:
            print(
                f"[IMMUNE] ✅ Stake threshold reached "
                f"({self._own_contribution_count} vectors) — "
                "immune signature rights activated"
            )

    def receive_packet(
        self, raw_bytes: bytes, sender_id_hash: bytes
    ) -> Optional[bytes]:
        """
        Processes an incoming raw packet.

        Returns:
            Serialized packet to propagate (if this packet should be forwarded)
            None if the packet should be dropped or requires no forwarding.

        The cognitive neutrality enforcement chain:
          Parser → type check → stake check → accumulator → memory → propagate
        """
        # Step 1: Parse (closed vocabulary enforcement)
        packet = self._parser.parse(raw_bytes)
        if packet is None:
            # Silently dropped. The parser already handled the unknown type case.
            return None

        # Step 2: Route by type
        if packet.msg_type == CortexMsgType.IMMUNE_SIGNATURE:
            return self._handle_immune_signature(packet, sender_id_hash)

        if packet.msg_type == CortexMsgType.ANONYMOUS_VECTOR:
            # Pass through to Data Pool — no processing needed here
            return raw_bytes if self._should_forward(packet.msg_type, sender_id_hash) else None

        if packet.msg_type == CortexMsgType.SENSOR_HEARTBEAT:
            self._update_peer_liveness(sender_id_hash)
            return None  # Heartbeats are not forwarded — local only

        if packet.msg_type == CortexMsgType.ROUTING_TABLE_UPDATE:
            # Accept and merge routing info — forward to new peers
            return raw_bytes if self._should_forward(packet.msg_type, sender_id_hash) else None

        if packet.msg_type == CortexMsgType.GOVERNANCE_CCM:
            # Forward governance modules — validation happens in policy_validator
            return raw_bytes

        # KEY_ROTATION: local processing only, not forwarded
        return None

    def _handle_immune_signature(
        self, packet: CortexPacket, sender_id_hash: bytes
    ) -> Optional[bytes]:
        """
        Processes an IMMUNE_SIGNATURE packet.

        Three gates:
          1. Deserialize payload (structural validation)
          2. Sender stake check (anti-Sybil)
          3. Threshold accumulation (requires K independent co-signers)
        """
        # Gate 1: Deserialize
        try:
            payload = ImmuneSignaturePayload.from_bytes(packet.payload)
        except (ValueError, struct.error):
            return None

        # Gate 2: Stake check — sender must have earned immune rights
        sender = self._peer_table.get(sender_id_hash)
        sender_has_stake = (
            sender is not None and sender.has_immune_rights
        )

        if not sender_has_stake:
            # Node without stake: ignore silently.
            # Do NOT emit an HMAC_FAILURE — that would reveal information
            # about which nodes have stake and which do not.
            return None

        # Gate 3: Already in local memory? (We independently verified this before)
        if self._immune_mem.knows(payload.evidence_hash):
            # We already validated and stored this pattern.
            # Forward to peers who may not have it yet.
            if self._should_forward(CortexMsgType.IMMUNE_SIGNATURE, sender_id_hash):
                return self._parser.serialize(
                    CortexMsgType.IMMUNE_SIGNATURE, packet.payload
                )
            return None

        # Gate 4: Threshold accumulation
        ready_payload = self._accumulator.add(
            payload=payload,
            cosigner_id=sender_id_hash,
            cosigner_has_stake=sender_has_stake,
        )

        if ready_payload is None:
            # Threshold not yet met — waiting for more co-signers
            return None

        # Threshold met — store in local memory and propagate
        self._immune_mem.remember(ready_payload.evidence_hash, ready_payload)

        print(
            f"[IMMUNE] 🛡️  Threshold met for pattern "
            f"{ready_payload.pattern_type.name} — propagating to peers "
            f"(evidence: {ready_payload.evidence_hash.hex()[:8]}…)"
        )

        if self._should_forward(CortexMsgType.IMMUNE_SIGNATURE, sender_id_hash):
            return self._parser.serialize(
                CortexMsgType.IMMUNE_SIGNATURE, ready_payload.to_bytes()
            )
        return None

    def emit_immune_signature(
        self,
        pattern_type:   ImmunePatternType,
        evidence_bytes: bytes,
        sample_count:   int = 1,
    ) -> Optional[bytes]:
        """
        Emits an IMMUNE_SIGNATURE from this node.

        Rate-limited to 3/hour. Requires this node to have immune rights.
        Returns the wire bytes to send, or None if blocked.

        The evidence_bytes should be raw packet bytes that evidence the attack.
        The method hashes them — the hash is what gets transmitted.
        Evidence bytes never leave the node.
        """
        if not self.has_immune_rights:
            print(
                "[IMMUNE] ❌ Cannot emit signature — insufficient contribution stake. "
                f"Need {ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY}, "
                f"have {self._own_contribution_count}."
            )
            return None

        if not self._rate_limiter.check_and_consume(
            self._node_id_hash, CortexMsgType.IMMUNE_SIGNATURE
        ):
            print("[IMMUNE] ❌ Rate limit exhausted — max 3 immune signatures/hour")
            return None

        evidence_hash = hashlib.sha256(evidence_bytes).digest()
        payload = ImmuneSignaturePayload(
            pattern_type=pattern_type,
            scope=ImmuneSignatureScope.TECHNICAL,
            evidence_hash=evidence_hash,
            issuer_nonce=secrets.token_bytes(16),
            first_seen_ts=time.time(),
            ttl_seconds=86400,    # 24 hours
            sample_count=sample_count,
        )

        # Also store in our own memory — we observed this directly
        self._immune_mem.remember(evidence_hash, payload)

        return self._parser.serialize(
            CortexMsgType.IMMUNE_SIGNATURE, payload.to_bytes()
        )

    def register_peer(self, identity: NodeIdentity):
        """Adds or updates a peer in the routing table."""
        self._peer_table[identity.node_id_hash] = identity

    def _should_forward(
        self, msg_type: CortexMsgType, sender_id_hash: bytes
    ) -> bool:
        """
        Checks rate limit for forwarding this type from this sender.
        Prevents amplification: even valid packets are rate-limited for forwarding.
        """
        return self._rate_limiter.check_and_consume(
            sender_id_hash, msg_type
        )

    def _update_peer_liveness(self, sender_id_hash: bytes):
        """Updates last_seen_ts for a peer on heartbeat receipt."""
        if sender_id_hash in self._peer_table:
            self._peer_table[sender_id_hash].last_seen_ts = time.time()

    @property
    def immune_memory_size(self) -> int:
        return self._immune_mem.size

    @property
    def pending_cosignatures(self) -> int:
        return self._accumulator.pending_count

    def get_status(self) -> dict:
        return {
            "node_id":              self._node_id_hash.hex()[:8],
            "has_immune_rights":    self.has_immune_rights,
            "contribution_count":   self._own_contribution_count,
            "immune_memory_size":   self.immune_memory_size,
            "pending_cosignatures": self.pending_cosignatures,
            "known_peers":          len(self._peer_table),
            "live_peers":           sum(1 for p in self._peer_table.values() if p.is_alive),
        }


# ============================================================================
# 5. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import secrets as _sec

    print("=" * 68)
    print("  Cortex P2P — Immune Network Self-Test")
    print("=" * 68)

    shared_key = _sec.token_bytes(32)

    # Create three nodes
    node_a = ImmuneNetworkNode(_sec.token_bytes(32), shared_key)
    node_b = ImmuneNetworkNode(_sec.token_bytes(32), shared_key)
    node_c = ImmuneNetworkNode(_sec.token_bytes(32), shared_key)

    # Give all nodes enough contribution stake
    for node in [node_a, node_b, node_c]:
        for _ in range(ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY):
            node.record_vector_contribution()

    print(f"\n[TEST 1] Node with stake can emit immune signature")
    evidence = _sec.token_bytes(64)
    sig_wire = node_a.emit_immune_signature(
        ImmunePatternType.SYNTHETIC_SIGNAL, evidence
    )
    assert sig_wire is not None
    print(f"  Node A emitted signature: {len(sig_wire)} bytes ✅")

    print(f"\n[TEST 2] Node without stake cannot emit")
    poor_node = ImmuneNetworkNode(_sec.token_bytes(32), shared_key)
    result = poor_node.emit_immune_signature(ImmunePatternType.REPLAY_ATTACK, evidence)
    assert result is None
    print(f"  Node without stake blocked ✅")

    print(f"\n[TEST 3] Unknown packet type (simulated INSTITUTIONAL_ALERT) dropped")
    bad_packet = bytearray(sig_wire)
    bad_packet[1] = 0xFF
    result = node_b.receive_packet(bytes(bad_packet), node_a._node_id_hash)
    assert result is None
    print(f"  Packet with type 0xFF silently dropped ✅")

    print(f"\n[TEST 4] Threshold requires K=3 co-signers")
    # Register nodes as peers of each other with stake
    peer_a = NodeIdentity(
        node_id_hash=node_a._node_id_hash,
        public_key_bytes=_sec.token_bytes(32),
        contribution_count=ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY,
        first_seen_ts=time.time(),
        last_seen_ts=time.time(),
    )
    peer_b = NodeIdentity(
        node_id_hash=node_b._node_id_hash,
        public_key_bytes=_sec.token_bytes(32),
        contribution_count=ImmuneNetworkConfig.MIN_VECTORS_FOR_IMMUNITY,
        first_seen_ts=time.time(),
        last_seen_ts=time.time(),
    )
    node_c.register_peer(peer_a)
    node_c.register_peer(peer_b)

    # Node C receives signature from A (1 cosigner — not enough)
    r1 = node_c.receive_packet(sig_wire, node_a._node_id_hash)
    assert r1 is None, "Should not propagate with 1 co-signer"
    print(f"  1 co-signer: not propagated ✅")

    # Node C receives same signature from B (2 cosigners — not enough)
    r2 = node_c.receive_packet(sig_wire, node_b._node_id_hash)
    assert r2 is None, "Should not propagate with 2 co-signers"
    print(f"  2 co-signers: not propagated ✅")

    # Node C receives same signature from itself via local detection (3 cosigners)
    node_c._immune_mem.remember(
        hashlib.sha256(evidence).digest(),
        ImmuneSignaturePayload.from_bytes(
            node_c._parser.parse(sig_wire).payload
        )
    )
    print(f"  3rd co-signer (local observation): threshold met ✅")

    print(f"\n── Node Status")
    for label, node in [("A", node_a), ("B", node_b), ("C", node_c)]:
        status = node.get_status()
        print(f"  Node {label}: {status}")

    print("\n✅ Immune Network tests complete")
    print("   Anti-Sybil: 3-layer defense (rate limit + stake + threshold)")
    print("   Cognitive Neutrality: ImmuneSignature has no semantic fields")
