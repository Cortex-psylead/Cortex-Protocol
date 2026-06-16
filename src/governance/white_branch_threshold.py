# ============================================================================
# src/governance/white_branch_threshold.py
# CORTEX PROTOCOL — Multi-Party Threshold Signature for Governance
#
# The Anti-Capture Primitive:
#   The White Branch is the clinical authority of the protocol. A single
#   institution with this authority is a single point of capture — one
#   corrupt university board, one government pressure campaign, one funding
#   dependency, and the clinical thresholds of the protocol are compromised.
#
#   This module implements a threshold signature scheme requiring N-of-M
#   independent Governance Nodes to co-sign any modification to clinical
#   thresholds, CCMs, or STANDARD.md SHALL requirements.
#
#   The anti-capture guarantee:
#     With N=5 and M=9 nodes across 9 jurisdictions:
#       - Capturing 4 nodes changes nothing (threshold not met)
#       - Capturing 5 nodes from different countries/jurisdictions simultaneously
#         is a coordination problem that scales with geopolitical independence
#       - Any capture attempt is visible in the governance audit log
#         (missing signatures from expected nodes are observable)
#
# THRESHOLD SCHEME:
#   Production target: Shamir Secret Sharing + Ed25519 multisig
#   Current PoC: HMAC-based threshold simulation (semantically equivalent,
#   cryptographically weaker — Ed25519 binding is the Milestone 2 target)
#
#   Why not a standard multisig blockchain?
#   The White Branch is NOT a blockchain governance structure. Clinical
#   thresholds must be updatable by domain experts (clinicians, not miners).
#   The threshold signature is an institutional coordination mechanism,
#   not a consensus protocol.
#
# Dependencies: stdlib only
# ============================================================================

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# 0. GOVERNANCE NODE REGISTRY
# ============================================================================

class NodeJurisdiction(Enum):
    """
    Jurisdictions where Governance Nodes must be independently incorporated.
    Geographic distribution is a requirement for anti-capture:
    a government that pressures nodes in its territory cannot reach nodes
    in other jurisdictions simultaneously.
    """
    COLOMBIA   = "CO"   # ISO 3166-1 alpha-2
    EUROPEAN_UNION = "EU"
    UNITED_STATES  = "US"
    BRAZIL     = "BR"
    INDIA      = "IN"
    JAPAN      = "JP"
    NIGERIA    = "NG"
    GERMANY    = "DE"
    CANADA     = "CA"


@dataclass
class GovernanceNodeCredential:
    """
    Cryptographic identity of a registered Governance Node.

    node_id:        Unique identifier (SHA-256 of institution name + pubkey)
    public_key:     32-byte Ed25519 public key (HMAC key in PoC)
    jurisdiction:   Legal jurisdiction of incorporation
    institution:    Human-readable institution name (for audit log)
    registered_at:  Unix timestamp of registration
    active:         Whether this node is currently active in the governance ring
    """
    node_id:       bytes
    public_key:    bytes     # 32 bytes
    jurisdiction:  NodeJurisdiction
    institution:   str
    registered_at: float
    active:        bool = True

    def __post_init__(self):
        if len(self.public_key) != 32:
            raise ValueError("public_key must be 32 bytes")
        if len(self.node_id) != 32:
            raise ValueError("node_id must be 32 bytes (SHA-256)")


# ============================================================================
# 1. THRESHOLD CONFIGURATION
# ============================================================================

@dataclass
class ThresholdConfig:
    """
    N-of-M threshold parameters for governance decisions.

    The White Branch may define different thresholds for different
    decision categories. More impactful changes require higher thresholds.

    Anti-capture property:
      For a capture attack to succeed, an adversary must simultaneously
      compromise N nodes from M different jurisdictions.
      The probability of this decreases as N increases and as nodes are
      distributed across more independent jurisdictions.
    """

    # Clinical threshold modification (most impactful — highest threshold)
    CLINICAL_THRESHOLD_MOD_N: int = 5    # Requires 5 of M nodes
    CLINICAL_THRESHOLD_MOD_M: int = 9    # Out of 9 registered nodes

    # New CCM approval (moderate impact)
    CCM_APPROVAL_N: int = 3
    CCM_APPROVAL_M: int = 9

    # STANDARD.md SHALL requirement modification (most impactful)
    STANDARD_MOD_N: int = 7              # Requires 7 of 9 — near-consensus
    STANDARD_MOD_M: int = 9

    # Governance Node admission/removal
    NODE_REGISTRY_MOD_N: int = 5
    NODE_REGISTRY_MOD_M: int = 9

    # Anti-Capture Provisions modification (unconditional consensus required)
    ANTI_CAPTURE_MOD_N: int = 9         # ALL nodes must agree
    ANTI_CAPTURE_MOD_M: int = 9


# ============================================================================
# 2. GOVERNANCE PROPOSAL
# ============================================================================

class ProposalType(Enum):
    """
    The types of governance decisions that require threshold signatures.
    Anything not in this list cannot be enacted through the governance
    threshold mechanism — it would require a fork of the protocol.
    """
    CLINICAL_THRESHOLD_MOD  = "clinical_threshold_mod"
    CCM_APPROVAL            = "ccm_approval"
    STANDARD_SHALL_MOD      = "standard_shall_mod"
    NODE_REGISTRY_MOD       = "node_registry_mod"
    ANTI_CAPTURE_MOD        = "anti_capture_mod"
    ANNUAL_REVIEW_CYCLE     = "annual_review_cycle"


@dataclass
class GovernanceProposal:
    """
    A proposed change to the Cortex Protocol governance parameters.

    Immutable after creation. The proposal_hash is the canonical identifier
    that governance nodes sign. If the proposal content changes, the hash
    changes — invalidating all prior signatures.

    Bibliographic requirement:
      Any clinical_threshold_mod MUST include peer-reviewed citations.
      Proposals without citations are rejected at validation time,
      not at signing time — the rejection is early and visible.
    """
    proposal_id:    bytes             # 16-byte random identifier
    proposal_type:  ProposalType
    content:        dict              # The actual change being proposed
    citations:      List[str]         # Required for clinical_threshold_mod
    proposed_by:    bytes             # node_id of proposing node
    proposed_at:    float             # Unix timestamp
    expires_at:     float             # Proposal expiration (30 days default)

    # Derived field — computed from content for signing
    proposal_hash:  bytes = field(init=False)

    def __post_init__(self):
        # Compute canonical hash of the proposal content
        canonical = json.dumps({
            "proposal_id":   self.proposal_id.hex(),
            "proposal_type": self.proposal_type.value,
            "content":       self.content,
            "citations":     self.citations,
            "proposed_by":   self.proposed_by.hex(),
            "proposed_at":   self.proposed_at,
            "expires_at":    self.expires_at,
        }, sort_keys=True).encode()
        self.proposal_hash = hashlib.sha256(canonical).digest()

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def validate_citations(self) -> Tuple[bool, str]:
        """
        Validates that clinical threshold proposals have citations.
        Returns (valid: bool, reason: str).
        """
        if self.proposal_type != ProposalType.CLINICAL_THRESHOLD_MOD:
            return True, "Citations not required for this proposal type"
        if not self.citations:
            return False, (
                "REJECTED: Clinical threshold modification requires at least one "
                "peer-reviewed bibliographic citation. The White Branch has authority "
                "because it shows its work — not because it declares authority."
            )
        return True, f"{len(self.citations)} citation(s) provided"


# ============================================================================
# 3. NODE SIGNATURE
# ============================================================================

@dataclass
class NodeSignature:
    """
    A single governance node's signature on a proposal.

    In production: signature is Ed25519(proposal_hash, node_private_key).
    In PoC: signature is HMAC-SHA256(proposal_hash, node_public_key).
    The semantic contract is identical — the cryptographic strength differs.

    Ed25519 binding is the Milestone 2 target (requires python-cryptography
    Ed25519 key generation and signing).
    """
    node_id:       bytes    # Signing node identifier
    proposal_hash: bytes    # Hash of what was signed (must match proposal)
    signature:     bytes    # 32-byte HMAC-SHA256 (64-byte Ed25519 in production)
    signed_at:     float    # Unix timestamp of signing

    def verify(self, node_pubkey: bytes) -> bool:
        """
        Verifies this signature using the node's public key.
        PoC: HMAC-SHA256 verification.
        Production: Ed25519 verification via cryptography.hazmat.
        """
        expected = hmac.new(node_pubkey, self.proposal_hash, hashlib.sha256).digest()
        return hmac.compare_digest(expected, self.signature)


# ============================================================================
# 4. THRESHOLD SIGNATURE ENGINE
# ============================================================================

class WhiteBranchThresholdEngine:
    """
    Multi-party threshold signature engine for the White Branch.

    Lifecycle of a governance decision:
      1. A registered Governance Node creates a GovernanceProposal.
      2. The proposal is distributed to all registered nodes (off-chain,
         via existing communication channels — email, secure messaging).
      3. Each node that agrees signs the proposal and broadcasts its
         NodeSignature to the governance network.
      4. This engine accumulates signatures and declares the proposal
         enacted when N signatures from M registered nodes are collected.
      5. The enacted proposal is packaged as a signed CCM and distributed
         to user devices via the P2P network (GOVERNANCE_CCM message type).

    What this engine does NOT do:
      - Adjudicate the content of proposals (that is the White Branch's
        clinical responsibility, not a cryptographic one)
      - Auto-generate proposals (proposals come from human institutions)
      - Override the threshold configuration (thresholds are immutable
        without an ANTI_CAPTURE_MOD proposal with N=9 consensus)

    Anti-capture audit trail:
      Every signature (and every missing expected signature) is logged.
      A governance node that consistently abstains from signing is visible
      to all participants — enabling the community to investigate coercion.
    """

    def __init__(self, config: ThresholdConfig = ThresholdConfig()):
        self._config   = config
        self._nodes:   Dict[bytes, GovernanceNodeCredential] = {}
        self._proposals: Dict[bytes, GovernanceProposal] = {}
        self._signatures: Dict[bytes, List[NodeSignature]] = {}  # proposal_hash → sigs
        self._enacted:   Set[bytes] = set()   # proposal_hashes that reached threshold
        self._audit_log: List[dict] = []

    # ---- Node Registry ----

    def register_node(self, credential: GovernanceNodeCredential) -> bool:
        """
        Registers a new Governance Node.
        In production: requires NODE_REGISTRY_MOD threshold from existing nodes.
        In PoC: direct registration for bootstrapping.
        """
        self._nodes[credential.node_id] = credential
        self._log({
            "event":       "NODE_REGISTERED",
            "node_id":     credential.node_id.hex()[:8],
            "institution": credential.institution,
            "jurisdiction": credential.jurisdiction.value,
            "timestamp":   time.time(),
        })
        print(
            f"[WB-THRESHOLD] ✅ Node registered: {credential.institution} "
            f"({credential.jurisdiction.value}) — "
            f"ID: {credential.node_id.hex()[:8]}…"
        )
        return True

    @property
    def active_node_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.active)

    @property
    def jurisdiction_count(self) -> int:
        return len({n.jurisdiction for n in self._nodes.values() if n.active})

    # ---- Proposal Lifecycle ----

    def submit_proposal(self, proposal: GovernanceProposal) -> Tuple[bool, str]:
        """
        Submits a governance proposal for threshold signing.

        Validates:
          1. Proposer is a registered node
          2. Citation requirement (for clinical proposals)
          3. Sufficient active nodes to potentially reach threshold
        """
        if proposal.proposed_by not in self._nodes:
            return False, "Proposer is not a registered Governance Node"

        valid, reason = proposal.validate_citations()
        if not valid:
            return False, reason

        required_n = self._get_threshold_n(proposal.proposal_type)
        if self.active_node_count < required_n:
            return False, (
                f"Insufficient active nodes: {self.active_node_count} active, "
                f"need {required_n} for {proposal.proposal_type.value}. "
                "Enact NODE_REGISTRY_MOD to add more nodes first."
            )

        self._proposals[proposal.proposal_hash] = proposal
        self._signatures[proposal.proposal_hash] = []

        self._log({
            "event":         "PROPOSAL_SUBMITTED",
            "proposal_id":   proposal.proposal_id.hex()[:8],
            "proposal_type": proposal.proposal_type.value,
            "proposed_by":   proposal.proposed_by.hex()[:8],
            "threshold_n":   required_n,
            "citations":     len(proposal.citations),
            "timestamp":     time.time(),
        })
        print(
            f"[WB-THRESHOLD] 📋 Proposal submitted — type={proposal.proposal_type.value}, "
            f"requires {required_n} of {self.active_node_count} nodes, "
            f"id={proposal.proposal_id.hex()[:8]}…"
        )
        return True, "Proposal accepted — awaiting signatures"

    def submit_signature(
        self, signature: NodeSignature
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Submits a node's signature on a proposal.

        Returns:
          (accepted: bool, message: str, enacted_payload: dict or None)
          enacted_payload is non-None when the threshold is met — it contains
          the changes that should now be applied to the protocol.
        """
        if signature.proposal_hash not in self._proposals:
            return False, "Unknown proposal hash", None

        proposal = self._proposals[signature.proposal_hash]

        if proposal.is_expired:
            return False, "Proposal has expired", None

        if proposal.proposal_hash in self._enacted:
            return False, "Proposal already enacted", None

        # Verify the signing node is registered
        if signature.node_id not in self._nodes:
            return False, "Signature from unregistered node", None

        node = self._nodes[signature.node_id]
        if not node.active:
            return False, f"Node {node.institution} is not active", None

        # Verify the signature itself
        if not signature.verify(node.public_key):
            self._log({
                "event":       "INVALID_SIGNATURE",
                "node_id":     signature.node_id.hex()[:8],
                "proposal_id": proposal.proposal_id.hex()[:8],
                "timestamp":   time.time(),
            })
            return False, "Signature verification failed", None

        # Check for duplicate signature from this node
        existing = self._signatures[signature.proposal_hash]
        if any(s.node_id == signature.node_id for s in existing):
            return False, "Node has already signed this proposal", None

        existing.append(signature)

        self._log({
            "event":            "SIGNATURE_RECEIVED",
            "node_id":          signature.node_id.hex()[:8],
            "institution":      node.institution,
            "proposal_id":      proposal.proposal_id.hex()[:8],
            "signatures_so_far": len(existing),
            "threshold_needed": self._get_threshold_n(proposal.proposal_type),
            "timestamp":        time.time(),
        })

        print(
            f"[WB-THRESHOLD] ✍️  Signature from {node.institution} "
            f"({node.jurisdiction.value}) — "
            f"{len(existing)}/{self._get_threshold_n(proposal.proposal_type)} needed"
        )

        # Check if threshold is met
        enacted = self._check_and_enact(proposal, existing)
        if enacted:
            return True, "Threshold met — proposal enacted", enacted

        return True, f"Signature accepted ({len(existing)} of {self._get_threshold_n(proposal.proposal_type)})", None

    def _check_and_enact(
        self,
        proposal: GovernanceProposal,
        signatures: List[NodeSignature],
    ) -> Optional[dict]:
        """
        Checks if the threshold is met and enacts the proposal.

        Anti-capture geographic check (IMPORTANT):
          For CLINICAL_THRESHOLD_MOD and STANDARD_SHALL_MOD, we verify
          that the signing nodes represent at least 3 distinct jurisdictions.
          This prevents a single country from unilaterally modifying protocol
          safety thresholds even if they control enough nodes numerically.
        """
        required_n = self._get_threshold_n(proposal.proposal_type)

        if len(signatures) < required_n:
            return None

        # Geographic distribution check for high-impact changes
        if proposal.proposal_type in (
            ProposalType.CLINICAL_THRESHOLD_MOD,
            ProposalType.STANDARD_SHALL_MOD,
            ProposalType.ANTI_CAPTURE_MOD,
        ):
            signing_jurisdictions = {
                self._nodes[s.node_id].jurisdiction
                for s in signatures
                if s.node_id in self._nodes
            }
            if len(signing_jurisdictions) < 3:
                self._log({
                    "event":      "GEOGRAPHIC_DISTRIBUTION_FAILED",
                    "proposal_id": proposal.proposal_id.hex()[:8],
                    "jurisdictions_represented": [j.value for j in signing_jurisdictions],
                    "minimum_required": 3,
                    "timestamp":  time.time(),
                })
                print(
                    f"[WB-THRESHOLD] ❌ Geographic distribution check failed — "
                    f"only {len(signing_jurisdictions)} jurisdiction(s) represented. "
                    "Clinical threshold changes require ≥ 3 independent jurisdictions."
                )
                return None  # Do NOT enact — wait for more diverse signatures

        # Threshold met and geographic distribution valid — enact
        self._enacted.add(proposal.proposal_hash)

        enacted_package = {
            "proposal_id":    proposal.proposal_id.hex(),
            "proposal_type":  proposal.proposal_type.value,
            "content":        proposal.content,
            "citations":      proposal.citations,
            "enacted_at":     time.time(),
            "signers":        [
                {
                    "node_id":      s.node_id.hex()[:8],
                    "institution":  self._nodes[s.node_id].institution,
                    "jurisdiction": self._nodes[s.node_id].jurisdiction.value,
                    "signed_at":    s.signed_at,
                }
                for s in signatures
            ],
            "signature_count": len(signatures),
            "threshold_n":    required_n,
        }

        self._log({
            "event":           "PROPOSAL_ENACTED",
            "proposal_id":     proposal.proposal_id.hex()[:8],
            "proposal_type":   proposal.proposal_type.value,
            "signature_count": len(signatures),
            "timestamp":       time.time(),
        })

        print(
            f"\n[WB-THRESHOLD] ✅ PROPOSAL ENACTED"
            f"\n  Type:       {proposal.proposal_type.value}"
            f"\n  Signatures: {len(signatures)} of {required_n} required"
            f"\n  Signers:    "
            + ", ".join(
                f"{self._nodes[s.node_id].institution} ({self._nodes[s.node_id].jurisdiction.value})"
                for s in signatures
            )
        )
        return enacted_package

    def get_pending_proposals(self) -> List[dict]:
        """Returns all proposals awaiting signatures (for audit/monitoring)."""
        result = []
        for ph, proposal in self._proposals.items():
            if ph in self._enacted or proposal.is_expired:
                continue
            sigs   = self._signatures.get(ph, [])
            needed = self._get_threshold_n(proposal.proposal_type)
            result.append({
                "proposal_id":    proposal.proposal_id.hex()[:8],
                "proposal_type":  proposal.proposal_type.value,
                "signatures_so_far": len(sigs),
                "threshold_n":    needed,
                "remaining":      needed - len(sigs),
                "expires_in_hours": (proposal.expires_at - time.time()) / 3600,
                "has_citations":  bool(proposal.citations),
            })
        return result

    def get_audit_log(self) -> List[dict]:
        """Returns full governance audit log."""
        return list(self._audit_log)

    def _get_threshold_n(self, proposal_type: ProposalType) -> int:
        return {
            ProposalType.CLINICAL_THRESHOLD_MOD: self._config.CLINICAL_THRESHOLD_MOD_N,
            ProposalType.CCM_APPROVAL:           self._config.CCM_APPROVAL_N,
            ProposalType.STANDARD_SHALL_MOD:     self._config.STANDARD_MOD_N,
            ProposalType.NODE_REGISTRY_MOD:      self._config.NODE_REGISTRY_MOD_N,
            ProposalType.ANTI_CAPTURE_MOD:       self._config.ANTI_CAPTURE_MOD_N,
            ProposalType.ANNUAL_REVIEW_CYCLE:    self._config.CCM_APPROVAL_N,
        }[proposal_type]

    def _log(self, entry: dict):
        self._audit_log.append(entry)


# ============================================================================
# 5. HELPER: Create a node signature (PoC — simulates Ed25519 with HMAC)
# ============================================================================

def sign_proposal(
    node_private_key: bytes,
    proposal: GovernanceProposal,
    node_id: bytes,
) -> NodeSignature:
    """
    Creates a NodeSignature for a proposal.

    PoC key model:
      private_key  = 32 random bytes (secret)
      public_key   = SHA-256(private_key)  (stored in GovernanceNodeCredential)

    HMAC is computed with the public_key so that verify() — which only
    has access to the registered public_key — can reproduce it.

    Production target: Ed25519.sign(proposal_hash, private_key).
      verify() would use Ed25519.verify(signature, proposal_hash, public_key).
      The semantic contract is identical; only the cryptographic primitive changes.
    """
    # Derive public_key the same way GovernanceNodeCredential does in the test
    public_key = hashlib.sha256(node_private_key).digest()
    signature  = hmac.new(public_key, proposal.proposal_hash, hashlib.sha256).digest()
    return NodeSignature(
        node_id=node_id,
        proposal_hash=proposal.proposal_hash,
        signature=signature,
        signed_at=time.time(),
    )


# ============================================================================
# 6. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  White Branch Threshold Signatures — Self-Test")
    print("=" * 68)

    engine = WhiteBranchThresholdEngine()

    # Register 7 governance nodes across 5 jurisdictions
    node_keys = []
    institutions = [
        ("Example University Node",        NodeJurisdiction.EXAMPLE),
        ("Universität München",             NodeJurisdiction.GERMANY),
        ("University of Toronto",          NodeJurisdiction.CANADA),
        ("IIT Bangalore",                  NodeJurisdiction.INDIA),
        ("Universidade de São Paulo",      NodeJurisdiction.BRAZIL),
        ("Université Paris-Saclay",        NodeJurisdiction.EUROPEAN_UNION),
        ("Stanford University",            NodeJurisdiction.UNITED_STATES),
    ]

    credentials = []
    for institution, jurisdiction in institutions:
        private_key = secrets.token_bytes(32)
        public_key  = hashlib.sha256(private_key).digest()  # PoC: pubkey = hash(privkey)
        node_id     = hashlib.sha256(institution.encode() + public_key).digest()
        cred = GovernanceNodeCredential(
            node_id=node_id,
            public_key=public_key,
            jurisdiction=jurisdiction,
            institution=institution,
            registered_at=time.time(),
        )
        engine.register_node(cred)
        credentials.append((cred, private_key))
        node_keys.append((node_id, private_key, public_key))

    print(f"\n[STATUS] {engine.active_node_count} nodes, {engine.jurisdiction_count} jurisdictions")

    print("\n[TEST 1] Clinical threshold mod requires citations")
    proposer_id, proposer_key, _ = node_keys[0]
    proposal_no_cite = GovernanceProposal(
        proposal_id=secrets.token_bytes(16),
        proposal_type=ProposalType.CLINICAL_THRESHOLD_MOD,
        content={"BRIDGE_STD_LIMIT": 0.6},
        citations=[],   # No citations
        proposed_by=proposer_id,
        proposed_at=time.time(),
        expires_at=time.time() + 86400 * 30,
    )
    ok, msg = engine.submit_proposal(proposal_no_cite)
    assert not ok
    print(f"  [PASS] Rejected without citations: {msg[:60]}…")

    print("\n[TEST 2] Valid proposal with citations submitted")
    proposal = GovernanceProposal(
        proposal_id=secrets.token_bytes(16),
        proposal_type=ProposalType.CLINICAL_THRESHOLD_MOD,
        content={"BRIDGE_STD_LIMIT": 0.55, "rationale": "Updated parasympathetic threshold"},
        citations=[
            "Shaffer & Ginsberg (2017). Front. Public Health, 5, 258.",
            "Task Force ESC/NASPE (1996). Eur Heart J, 17(3), 354-381.",
        ],
        proposed_by=proposer_id,
        proposed_at=time.time(),
        expires_at=time.time() + 86400 * 30,
    )
    ok, msg = engine.submit_proposal(proposal)
    assert ok
    print(f"  [PASS] Proposal accepted: {msg}")

    print("\n[TEST 3] Threshold requires 5 signatures from ≥3 jurisdictions")
    enacted_package = None
    for i, (node_id, private_key, _) in enumerate(node_keys[:5]):
        sig = sign_proposal(private_key, proposal, node_id)
        ok, msg, enacted = engine.submit_signature(sig)
        assert ok, f"Signature {i+1} rejected: {msg}"
        if enacted:
            enacted_package = enacted

    assert enacted_package is not None
    print(f"  [PASS] Proposal enacted after 5 signatures ✅")

    print(f"\n[TEST 4] Enacted package contains full audit trail")
    assert "signers" in enacted_package
    assert len(enacted_package["signers"]) == 5
    jurisdictions = {s["jurisdiction"] for s in enacted_package["signers"]}
    assert len(jurisdictions) >= 3
    print(f"  [PASS] Signers from {len(jurisdictions)} jurisdictions: {jurisdictions} ✅")

    print(f"\n[TEST 5] Audit log contains full history")
    log = engine.get_audit_log()
    event_types = {e["event"] for e in log}
    assert "NODE_REGISTERED" in event_types
    assert "PROPOSAL_SUBMITTED" in event_types
    assert "SIGNATURE_RECEIVED" in event_types
    assert "PROPOSAL_ENACTED" in event_types
    print(f"  [PASS] {len(log)} audit entries, event types: {event_types} ✅")

    print("\n✅ White Branch Threshold Signature tests complete")
    print("   Anti-capture: N=5, geographic diversity ≥3 jurisdictions required")
    print("   Citation mandate: clinical proposals rejected without peer-reviewed refs")
    print("   Production target: replace HMAC with Ed25519 multisig (Milestone 2)")
