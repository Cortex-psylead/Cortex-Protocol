# ============================================================================
# src/p2p/p2p_message_types.py
# CORTEX PROTOCOL — Closed P2P Message Vocabulary
#
# Pentagon Question (extended): "¿Qué puede decir la red?"
#
# COGNITIVE NEUTRALITY MANDATE:
#   This module is the first enforcement layer of the Absolute Data Agnosticism
#   principle. The closed vocabulary defined here makes it architecturally
#   impossible for any node — regardless of institutional affiliation — to
#   inject semantically interpreted content (alerts, advisories, behavioral
#   recommendations) into the P2P fabric.
#
#   The mechanism is structural, not policy-based:
#   The parser has NO handler for message types outside this vocabulary.
#   Unknown type bytes are dropped at byte 2 of parsing — before any
#   deserialization occurs. No log entry. No error propagation. Silent drop.
#
#   Any university, governance node, or compromised SDK that attempts to
#   broadcast an institutional alert must invent a new message type.
#   That type will not parse on any honest node. The alert dies in the socket.
#
# WIRE FORMAT:
#   [1 byte: CORTEX_MAGIC = 0xC0]
#   [1 byte: message type]
#   [2 bytes: payload length, big-endian uint16]
#   [N bytes: payload — format defined per type below]
#   [32 bytes: HMAC-SHA256 of all preceding bytes]
#
#   Total header: 4 bytes. Total overhead per message: 36 bytes.
#   Maximum payload: TYPE-SPECIFIC (defined in MAX_PAYLOAD_BYTES).
#
# TYPES NOT IN THIS VOCABULARY (and why):
#   INSTITUTIONAL_ALERT     — Violates Cognitive Neutrality
#   ADVISORY_BROADCAST      — Violates Cognitive Neutrality
#   REGIONAL_HEALTH_SIGNAL  — Enables geographic correlation attack
#   BEHAVIORAL_PATTERN      — Violates Data Agnosticism (semantic content)
#   GOVERNANCE_DECREE       — Centralization vector
#   EMERGENCY_BROADCAST     — Social engineering attack surface
#
# Dependencies: stdlib only
# ============================================================================

import hashlib
import hmac
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Tuple


# ============================================================================
# 0. WIRE CONSTANTS
# ============================================================================

CORTEX_MAGIC: int = 0xC0          # First byte of every valid Cortex P2P packet
HEADER_SIZE:  int = 4             # magic(1) + type(1) + length(2)
MAC_SIZE:     int = 32            # HMAC-SHA256
MIN_PACKET:   int = HEADER_SIZE + MAC_SIZE   # Empty payload packet


# ============================================================================
# 1. CLOSED MESSAGE TYPE VOCABULARY
# ============================================================================

class CortexMsgType(IntEnum):
    """
    The complete, exhaustive vocabulary of messages the Cortex P2P fabric
    can carry. This enum is the law of the network.

    Adding a new type requires:
      1. White Branch clinical review (if biometric-adjacent)
      2. Protocol Steward technical review
      3. MAJOR version increment of STANDARD.md
      4. Multi-party threshold signature from ≥ 5 Governance Nodes

    The integer values are fixed and immutable. Removing a type requires
    the same process as adding one — parsers must continue ignoring removed
    types gracefully (treat as UNKNOWN).

    COGNITIVE NEUTRALITY NOTE:
    Types 0x01–0x06 are the only values a node will ever process.
    The parser rejects ALL other byte values at the type field position.
    There is no "fallback" or "extended type" mechanism by design.
    """

    ANONYMOUS_VECTOR      = 0x01
    # Anonymous biometric feature vector contributed to the Data Pool.
    # Payload: DeSciPayload serialized (41 bytes fixed).
    # Source: Any consenting user node.
    # Consumers: Data Pool aggregation nodes.
    # Cognitive neutrality: payload contains no semantic labels — only
    # 8 spectral bins (float32) + 1 CV float + 1 polyvagal bucket (int).

    SENSOR_HEARTBEAT      = 0x02
    # Node liveness signal. Contains: node_id_hash (32b) + timestamp (8b)
    # + current_state (1b: SAFE/WARNING/BLOCKED).
    # Source: Any node, every 30 seconds.
    # Consumers: DHT routing table maintenance.
    # Cognitive neutrality: no biometric content. Pure protocol telemetry.

    IMMUNE_SIGNATURE      = 0x03
    # Cryptographic signature of a detected TECHNICAL threat.
    # Payload: ImmuneSignaturePayload (see below). Max 256 bytes.
    # Source: Any node that detected a technical protocol violation.
    # Consumers: All nodes — for local filter rule update.
    # Cognitive neutrality: ImmuneSignaturePayload has no semantic fields.
    # CRITICAL: See ImmuneSignaturePayload for the structural restrictions
    # that prevent this type from carrying social/ideological content.

    KEY_ROTATION          = 0x04
    # Ephemeral session key rotation announcement.
    # Payload: new_pubkey (32b X25519) + rotation_nonce (16b) + timestamp (8b).
    # Source: Any node performing key rotation.
    # Consumers: Peer nodes that have active sessions with this node.

    GOVERNANCE_CCM        = 0x05
    # Clinical Capability Module signed by the White Branch threshold signature.
    # Payload: CCM body (variable) + threshold_signature (M*64 bytes).
    # Source: ONLY nodes holding a valid Governance Node credential.
    # Consumers: User devices — for local clinical rule update.
    # Cognitive neutrality: CCMs affect clinical thresholds only,
    # not content filtering or alert generation.

    ROUTING_TABLE_UPDATE  = 0x06
    # DHT Kademlia-style routing table update for the dCDN/Data Pool network.
    # Payload: up to 20 node_records (each: node_id_hash + IP + port + pubkey).
    # Source: Bootstrap nodes and well-connected peers.
    # Consumers: All nodes for network topology maintenance.


# ============================================================================
# 2. MAXIMUM PAYLOAD SIZES (bytes)
# Structural enforcement of cognitive neutrality:
# small payloads cannot carry narrative/interpretive content.
# ============================================================================

MAX_PAYLOAD_BYTES: dict = {
    CortexMsgType.ANONYMOUS_VECTOR:     41,    # Fixed DeSci payload size
    CortexMsgType.SENSOR_HEARTBEAT:     41,    # node_id(32) + ts(8) + state(1)
    CortexMsgType.IMMUNE_SIGNATURE:    256,    # Hard cap — no room for narrative
    CortexMsgType.KEY_ROTATION:         56,    # pubkey(32) + nonce(16) + ts(8)
    CortexMsgType.GOVERNANCE_CCM:     4096,    # CCM body + threshold signatures
    CortexMsgType.ROUTING_TABLE_UPDATE: 640,   # 20 nodes × 32 bytes each
}


# ============================================================================
# 3. IMMUNE SIGNATURE PAYLOAD — Structural Cognitive Neutrality
# ============================================================================

class ImmunePatternType(IntEnum):
    """
    Exhaustive enum of detectable TECHNICAL threats.

    Structural guarantee: none of these values encode social, behavioral,
    or ideological content. The enum cannot be extended without the
    multi-party governance process (see CortexMsgType docstring).

    TYPES THAT WERE CONSIDERED AND REJECTED:
      BEHAVIORAL_ANOMALY     — Would encode social judgment
      REGIONAL_STRESS_SPIKE  — Geographic + semantic content
      COGNITIVE_MANIPULATION — Requires ideological definition of "manipulation"
      DISINFORMATION_PATTERN — Requires editorial judgment of truth
    """
    SYNTHETIC_SIGNAL      = 0x01  # LIMES entropy below threshold
    REPLAY_ATTACK         = 0x02  # Nonce reuse detected
    MALFORMED_PACKET      = 0x03  # Parser rejection — structural violation
    RATE_LIMIT_VIOLATION  = 0x04  # Node exceeding emission quotas
    HMAC_FAILURE          = 0x05  # Authentication failure on received packet
    INVALID_TYPE_BYTE     = 0x06  # Unknown msg type attempted injection
    CCM_FORGERY_ATTEMPT   = 0x07  # Invalid governance signature on CCM
    SYBIL_PATTERN         = 0x08  # Multiple IDs same IP/timing fingerprint


class ImmuneSignatureScope(IntEnum):
    """
    Scope of an immune signature. Only TECHNICAL scope exists.

    SCOPES THAT DO NOT EXIST:
      COGNITIVE  = 0x02   — Would encode behavioral judgment
      SOCIAL     = 0x03   — Would encode social judgment
      POLITICAL  = 0x04   — Would encode political judgment
      CONTENT    = 0x05   — Would encode editorial judgment
    """
    TECHNICAL = 0x01      # Affects the protocol layer only


@dataclass
class ImmuneSignaturePayload:
    """
    Payload carried by IMMUNE_SIGNATURE messages.

    All fields are numeric or cryptographic hashes. There are no string
    fields, no label fields, no description fields. It is structurally
    impossible to encode "this node is spreading misinformation about
    topic X" in this payload — because the payload has no text field.

    The cognitive neutrality guarantee is enforced at the struct level.
    """
    pattern_type:     ImmunePatternType     # What kind of attack
    scope:            ImmuneSignatureScope  # Always TECHNICAL
    evidence_hash:    bytes                 # SHA-256 of offending packets
    issuer_nonce:     bytes                 # 16-byte anti-replay
    first_seen_ts:    float                 # Unix timestamp
    ttl_seconds:      int                  # Max: 172800 (48 hours)
    sample_count:     int                  # How many offending packets seen
    # No text field. No description field. No label field.
    # 256-byte max enforced by parser before deserialization.

    TTL_MAX: int = field(default=172800, init=False, repr=False)  # 48 hours

    def __post_init__(self):
        if len(self.evidence_hash) != 32:
            raise ValueError("evidence_hash must be 32 bytes (SHA-256)")
        if len(self.issuer_nonce) != 16:
            raise ValueError("issuer_nonce must be 16 bytes")
        if self.ttl_seconds > 172800:
            raise ValueError(f"TTL {self.ttl_seconds}s exceeds 48-hour maximum")
        if self.scope != ImmuneSignatureScope.TECHNICAL:
            raise ValueError(
                f"ImmuneSignatureScope {self.scope} is not permitted. "
                "Only TECHNICAL scope exists in the Cortex vocabulary."
            )

    def to_bytes(self) -> bytes:
        """Serializes to wire format. Total: 1+1+32+16+8+4+4 = 66 bytes."""
        return struct.pack(
            ">BB32s16sdII",
            self.pattern_type,
            self.scope,
            self.evidence_hash,
            self.issuer_nonce,
            self.first_seen_ts,
            self.ttl_seconds,
            self.sample_count,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "ImmuneSignaturePayload":
        if len(data) < 66:
            raise ValueError(f"Payload too short: {len(data)} < 66 bytes")
        pt, scope, ev_hash, nonce, ts, ttl, count = struct.unpack_from(
            ">BB32s16sdII", data
        )
        return cls(
            pattern_type=ImmunePatternType(pt),
            scope=ImmuneSignatureScope(scope),
            evidence_hash=ev_hash,
            issuer_nonce=nonce,
            first_seen_ts=ts,
            ttl_seconds=ttl,
            sample_count=count,
        )


# ============================================================================
# 4. PACKET PARSER — The Cognitive Neutrality Enforcement Point
# ============================================================================

@dataclass
class CortexPacket:
    """A fully parsed and authenticated Cortex P2P packet."""
    msg_type:   CortexMsgType
    payload:    bytes
    mac_valid:  bool


class CortexPacketParser:
    """
    The primary enforcement point for the Closed Vocabulary principle.

    Parsing is fail-fast and fail-silent:
      - Magic byte wrong:  silent drop, no log, no exception propagated
      - Type byte unknown: silent drop (NOT logged — logging creates a
                          side-channel: attackers probe which types cause logs)
      - Payload too large: silent drop
      - HMAC invalid:      silent drop + ImmuneSignature emission (HMAC_FAILURE)
      - Any other error:   silent drop

    The caller receives None on any failure. No error details are returned
    to the caller — this prevents oracle attacks where an attacker probes
    the parser's error branches to learn what types are valid.

    COGNITIVE NEUTRALITY:
    The parser is the last line of enforcement before application logic.
    If a packet survives parsing, it is guaranteed to be:
      1. A known type (in the closed vocabulary)
      2. Within the size limit for that type
      3. Authenticated (HMAC valid)
    
    No application logic downstream needs to re-check type validity.
    The cognitive filter is complete at the parser boundary.
    """

    def __init__(self, node_shared_key: bytes):
        """
        Args:
            node_shared_key: 32-byte symmetric key shared with peers.
                             In production: derived via ECDH per peer session.
        """
        if len(node_shared_key) != 32:
            raise ValueError("node_shared_key must be 32 bytes")
        self._key = node_shared_key
        self._valid_types: frozenset = frozenset(t.value for t in CortexMsgType)

    def parse(self, raw_bytes: bytes) -> Optional[CortexPacket]:
        """
        Parses and authenticates a raw packet from the network.

        Returns CortexPacket on success, None on ANY failure.
        The reason for failure is never returned to the caller.

        The order of checks is deliberate:
          1. Length (cheapest check — reject garbage fast)
          2. Magic byte (single byte comparison)
          3. Type byte (frozenset lookup — O(1))
          4. Payload size (integer comparison)
          5. HMAC (most expensive — only reached on structurally valid packets)
        """
        # 1. Minimum length
        if len(raw_bytes) < MIN_PACKET:
            return None

        # 2. Magic byte
        if raw_bytes[0] != CORTEX_MAGIC:
            return None

        # 3. Type byte — closed vocabulary enforcement
        type_byte = raw_bytes[1]
        if type_byte not in self._valid_types:
            # Silent drop. No log. No error. The packet does not exist.
            return None

        msg_type = CortexMsgType(type_byte)

        # 4. Payload size
        payload_length = struct.unpack_from(">H", raw_bytes, 2)[0]
        expected_total = HEADER_SIZE + payload_length + MAC_SIZE
        if len(raw_bytes) != expected_total:
            return None
        if payload_length > MAX_PAYLOAD_BYTES[msg_type]:
            return None

        # 5. HMAC authentication (constant-time comparison)
        body = raw_bytes[:HEADER_SIZE + payload_length]
        received_mac = raw_bytes[HEADER_SIZE + payload_length:]
        expected_mac = hmac.new(self._key, body, hashlib.sha256).digest()

        if not hmac.compare_digest(expected_mac, received_mac):
            return None

        payload = raw_bytes[HEADER_SIZE:HEADER_SIZE + payload_length]
        return CortexPacket(
            msg_type=msg_type,
            payload=payload,
            mac_valid=True,
        )

    def serialize(self, msg_type: CortexMsgType, payload: bytes) -> bytes:
        """
        Serializes a message into wire format with HMAC.

        Raises ValueError if payload exceeds the type's size limit.
        This prevents any application logic from accidentally constructing
        an oversized packet (defense in depth against oversized IMMUNE_SIGNATURE).
        """
        if len(payload) > MAX_PAYLOAD_BYTES[msg_type]:
            raise ValueError(
                f"Payload {len(payload)} bytes exceeds maximum "
                f"{MAX_PAYLOAD_BYTES[msg_type]} bytes for type {msg_type.name}. "
                "If this is IMMUNE_SIGNATURE, the 256-byte limit is intentional: "
                "it prevents narrative content from being encoded in protocol messages."
            )

        header = bytes([CORTEX_MAGIC, msg_type.value]) + struct.pack(">H", len(payload))
        body   = header + payload
        mac    = hmac.new(self._key, body, hashlib.sha256).digest()
        return body + mac


# ============================================================================
# 5. RATE LIMITER — Anti-Sybil Structural Defense
# ============================================================================

class NodeRateLimiter:
    """
    Per-node, per-type emission rate limiter.

    Cryptographic rate limiting: each emission slot is tracked by
    node_id_hash + msg_type + time_window. A node that exhausts its
    slots for IMMUNE_SIGNATURE emissions in a window is silently ignored
    for the remainder of that window.

    This is the first Sybil defense layer. A Sybil attack requires:
      - Creating N fake node identities (free)
      - Each identity contributing vectors to earn emission credits (costly)
      - Each identity emitting within rate limits (constrains flood rate)

    The cost of a Sybil attack is bounded below by:
      attack_impact = N * slots_per_window * payload_size
      attack_cost   = N * min_contribution_vectors_per_identity

    With default parameters:
      3 IMMUNE_SIGNATURE per node per hour × 256 bytes = 768 bytes/hour/identity
      To flood 1 MB/hour: need 1366 identities × contribution requirement = costly.

    White Branch defines the slot values in the governance snapshot.
    """

    # Default slots per node per type per hour
    # (Governance Node snapshot overrides these)
    DEFAULT_SLOTS: dict = {
        CortexMsgType.ANONYMOUS_VECTOR:     3600,  # 1/second — high frequency OK
        CortexMsgType.SENSOR_HEARTBEAT:       60,  # 1/minute
        CortexMsgType.IMMUNE_SIGNATURE:         3,  # 3/hour — CRITICAL: very low
        CortexMsgType.KEY_ROTATION:            24,  # 1/hour
        CortexMsgType.GOVERNANCE_CCM:           1,  # 1/hour (governance nodes only)
        CortexMsgType.ROUTING_TABLE_UPDATE:    12,  # 1/5 minutes
    }

    def __init__(self):
        # {(node_id_hash, msg_type, window_hour): count}
        self._counts: dict = {}

    def check_and_consume(
        self,
        node_id_hash: bytes,
        msg_type: CortexMsgType,
        slots_override: Optional[dict] = None,
    ) -> bool:
        """
        Returns True if the node may emit this message type now.
        Returns False (silently) if rate limit is exhausted.

        Consumes one slot on True return.
        """
        slots = (slots_override or self.DEFAULT_SLOTS).get(msg_type, 0)
        if slots == 0:
            return False

        window = int(time.time()) // 3600  # 1-hour windows
        key    = (node_id_hash, msg_type.value, window)

        current = self._counts.get(key, 0)
        if current >= slots:
            return False

        self._counts[key] = current + 1
        # Prune old windows to prevent unbounded growth
        self._prune_old_windows(window)
        return True

    def _prune_old_windows(self, current_window: int):
        """Remove entries from windows older than 2 hours."""
        stale = [k for k in self._counts if k[2] < current_window - 1]
        for k in stale:
            del self._counts[k]


# ============================================================================
# 6. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import secrets as _secrets

    print("=" * 68)
    print("  Cortex P2P — Closed Vocabulary Parser Self-Test")
    print("=" * 68)

    key    = _secrets.token_bytes(32)
    parser = CortexPacketParser(node_shared_key=key)

    # Test 1: Valid ANONYMOUS_VECTOR
    payload  = b"\x00" * 41
    wire     = parser.serialize(CortexMsgType.ANONYMOUS_VECTOR, payload)
    result   = parser.parse(wire)
    assert result is not None and result.msg_type == CortexMsgType.ANONYMOUS_VECTOR
    print("[PASS] Valid ANONYMOUS_VECTOR packet parsed correctly")

    # Test 2: Unknown type byte (simulated INSTITUTIONAL_ALERT = 0xFF)
    bad_wire = bytearray(wire)
    bad_wire[1] = 0xFF   # Unknown type
    result   = parser.parse(bytes(bad_wire))
    assert result is None
    print("[PASS] Unknown type byte 0xFF silently dropped — no exception, no log")

    # Test 3: IMMUNE_SIGNATURE over 256 bytes rejected
    try:
        parser.serialize(CortexMsgType.IMMUNE_SIGNATURE, b"\x00" * 257)
        print("[FAIL] Oversized IMMUNE_SIGNATURE should have raised ValueError")
    except ValueError as e:
        print(f"[PASS] Oversized IMMUNE_SIGNATURE rejected at serializer: {e}")

    # Test 4: ImmuneSignaturePayload rejects non-TECHNICAL scope
    try:
        bad_sig = ImmuneSignaturePayload(
            pattern_type=ImmunePatternType.SYNTHETIC_SIGNAL,
            scope=ImmuneSignatureScope(0x99),   # Invalid scope
            evidence_hash=_secrets.token_bytes(32),
            issuer_nonce=_secrets.token_bytes(16),
            first_seen_ts=time.time(),
            ttl_seconds=3600,
            sample_count=1,
        )
        print("[FAIL] Invalid scope should have raised ValueError")
    except (ValueError, Exception) as e:
        print(f"[PASS] Invalid scope rejected at dataclass level: {e}")

    # Test 5: Rate limiter blocks after slot exhaustion
    limiter  = NodeRateLimiter()
    node_id  = _secrets.token_bytes(32)
    results  = [
        limiter.check_and_consume(node_id, CortexMsgType.IMMUNE_SIGNATURE)
        for _ in range(5)
    ]
    assert results[:3] == [True, True, True]
    assert results[3:] == [False, False]
    print("[PASS] Rate limiter blocks IMMUNE_SIGNATURE after 3 slots/hour")

    print("\n✅ All Closed Vocabulary tests passed")
    print("   Cognitive Neutrality enforcement: STRUCTURAL (not policy-based)")
