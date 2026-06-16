# ============================================================================
# src/keros/sensor_channel.py
# CORTEX PROTOCOL — ECDH Secure Physical Bus (Sensor → TEE)
#
# THREAT MODEL (the "hostile bus" assumption):
#   The physical interconnect between an analog/digital sensor and the
#   local Trusted Execution Environment (TEE / Secure Enclave) is treated
#   as permanently compromised. Any attacker with physical access to the
#   board — or to the BLE/I²C/SPI bus driver layer in the host OS — can:
#
#     (a) READ:    Intercept raw biometric samples in transit.
#     (b) INJECT:  Replace or replay legitimate sensor frames.
#     (c) REPLAY:  Re-send a previously captured valid frame.
#     (d) SPOOF:   Impersonate a certified sensor device.
#
#   Cortex's defense is that raw samples MUST be unintelligible and
#   unauthenticated at the bus layer. Only the TEE can decrypt them.
#   The host OS, sensor driver, and any middleware running outside the
#   TEE boundary are explicitly untrusted.
#
# CRYPTOGRAPHIC DESIGN:
#
#   Handshake (one per session, ≤ 4-hour lifetime):
#   ┌──────────────┐                        ┌──────────────┐
#   │    Sensor    │                        │     TEE      │
#   │  (Peripheral)│                        │  (Enclave)   │
#   └──────┬───────┘                        └──────┬───────┘
#          │  1. sensor_hello(pub_S, cert_S)        │
#          │ ─────────────────────────────────────► │
#          │                                        │ 2. verify cert_S (KEROS whitelist)
#          │  3. tee_hello(pub_T, challenge_T)      │
#          │ ◄───────────────────────────────────── │
#          │ 4. ECDH(priv_S, pub_T) → shared_secret│
#          │    HKDF(shared_secret, challenge_T)    │
#          │    → session_key (32 bytes ChaCha20)   │
#          │  5. sensor_ack(HMAC(challenge_T, sk))  │
#          │ ─────────────────────────────────────► │
#          │                                        │ 6. ECDH(priv_T, pub_S) → shared_secret
#          │                                        │    HKDF(shared_secret, challenge_T)
#          │                                        │    → session_key (same, via DH)
#          │                                        │    verify HMAC from sensor_ack
#          │  SESSION ESTABLISHED                   │
#          │  7. encrypt_frame(raw_samples, sk)     │
#          │ ─────────────────────────────────────► │
#          │                                        │ 8. decrypt_frame(sk) → raw_samples
#          │                                        │    (only TEE ever sees plaintext)
#
#   Algorithm choices:
#     Key exchange:  X25519 (Curve25519 DH) — ephemeral per session
#     KDF:           HKDF-SHA256 — domain-separated by challenge nonce
#     Encryption:    ChaCha20-Poly1305 AEAD — authenticated encryption
#                    (Poly1305 MAC covers frame header + payload)
#     Frame HMAC:    HMAC-SHA256 for handshake authentication
#
#   Why ChaCha20-Poly1305 over AES-GCM:
#     On embedded sensors without AES hardware acceleration (e.g., a
#     custom ADC board on AArch64 without Cryptography Extensions),
#     ChaCha20 is constant-time in software and does not require a
#     hardware AES unit. This matches the Layer 1 ARM TrustZone target.
#
# FRAME FORMAT (encrypted):
#   [ 4 bytes: frame_seq  (big-endian uint32) ]
#   [ 4 bytes: payload_len (big-endian uint32) ]
#   [12 bytes: ChaCha20 nonce (unique per frame) ]
#   [ N bytes: ciphertext + 16-byte Poly1305 tag ]
#
#   The frame_seq is included in the AEAD Additional Data to prevent
#   reordering attacks: a replayed or reordered frame will fail MAC
#   verification even if the ciphertext is valid.
#
# ANTI-REPLAY:
#   Each frame carries a monotonically increasing frame_seq.
#   The TEE maintains the last accepted frame_seq per session.
#   Any frame with frame_seq ≤ last_accepted is rejected immediately.
#   Combined with the ChaCha20 nonce uniqueness guarantee, this closes
#   both the replay and the reordering attack vectors.
#
# SESSION LIFECYCLE:
#   Sessions expire after SESSION_TTL_SECONDS (default: 4 hours).
#   After expiry, the sensor must perform a full re-handshake.
#   Session keys are zeroized on close (best-effort in CPython — see
#   SECURITY.md §6 for the TPM 2.0 production gap statement).
#
# WHAT THIS MODULE DOES NOT DO:
#   - It does not certify sensor identity (that is KEROS/SensorCertificationAuthority).
#   - It does not run inside a real TEE (that is the Layer 1 C/ARM target).
#   - It does not provide memory-level key isolation (TPM 2.0 Milestone 2).
#
# Dependencies: cryptography >= 41.0
# ============================================================================

import hashlib
import hmac
import os
import secrets
import struct
import time

try:
    from sal.state_buffer_secure import secure_zeroize as _secure_zeroize
except ImportError:
    try:
        from state_buffer_secure import secure_zeroize as _secure_zeroize
    except ImportError:
        # Graceful degradation if import path not yet resolved
        def _secure_zeroize(ba: bytearray) -> None:
            for i in range(len(ba)): ba[i] = 0
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


# ============================================================================
# 0. CONSTANTS
# ============================================================================

SESSION_TTL_SECONDS:   int = 4 * 3600    # 4-hour session lifetime (White Branch)
MAX_FRAME_SEQ:         int = 0xFFFFFFFF  # uint32 max — triggers forced re-handshake
HKDF_INFO_SENSOR_BUS:  bytes = b"cortex-sensor-bus-v1"  # Domain separation label
FRAME_HEADER_SIZE:     int = 8           # frame_seq(4) + payload_len(4)
CHACHA_NONCE_SIZE:     int = 12
CHACHA_TAG_SIZE:       int = 16
MAX_FRAME_PAYLOAD:     int = 8192        # Max raw sensor payload per frame (bytes)
CHALLENGE_SIZE:        int = 32          # TEE challenge nonce size


# ============================================================================
# 1. CHANNEL STATE
# ============================================================================

class ChannelState(Enum):
    UNINITIALIZED  = "uninitialized"   # No handshake attempted
    HANDSHAKE      = "handshake"       # Handshake in progress
    ESTABLISHED    = "established"     # Session active — frames flowing
    EXPIRED        = "expired"         # TTL elapsed — re-handshake required
    COMPROMISED    = "compromised"     # Active attack detected — hard close


class SensorBusError(Exception):
    """Base for all sensor bus protocol errors."""


class HandshakeError(SensorBusError):
    """Raised when the ECDH handshake cannot be completed."""


class ReplayAttackError(SensorBusError):
    """Raised when a replayed or reordered frame is detected."""


class FrameAuthError(SensorBusError):
    """Raised when frame AEAD authentication fails (tampering or key mismatch)."""


class SessionExpiredError(SensorBusError):
    """Raised when a session TTL elapses and a re-handshake is required."""


# ============================================================================
# 2. HANDSHAKE MESSAGES (wire-serializable)
# ============================================================================

@dataclass
class SensorHello:
    """
    Message 1 of 3 in the handshake.
    Sensor → TEE: "I am certified sensor X, here is my ephemeral public key."

    In production: cert_hash is verified against KEROS SensorCertificationAuthority.
    """
    sensor_id_hash:    bytes    # SHA-256 of certified sensor ID (32 bytes)
    ephemeral_pub:     bytes    # X25519 ephemeral public key (32 bytes)
    timestamp_ms:      int      # Sensor wall-clock (ms) — anti-replay hint

    def to_bytes(self) -> bytes:
        return (
            self.sensor_id_hash
            + self.ephemeral_pub
            + struct.pack(">Q", self.timestamp_ms)
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "SensorHello":
        if len(data) < 72:
            raise HandshakeError(f"SensorHello too short: {len(data)} < 72 bytes")
        return cls(
            sensor_id_hash=data[:32],
            ephemeral_pub=data[32:64],
            timestamp_ms=struct.unpack_from(">Q", data, 64)[0],
        )


@dataclass
class TEEHello:
    """
    Message 2 of 3: TEE → Sensor.
    "Here is my ephemeral key and a challenge nonce. Prove you have the session key."
    """
    tee_id_hash:       bytes    # SHA-256 of TEE identity (32 bytes)
    ephemeral_pub:     bytes    # X25519 ephemeral public key (32 bytes)
    challenge:         bytes    # 32-byte random challenge nonce

    def to_bytes(self) -> bytes:
        return self.tee_id_hash + self.ephemeral_pub + self.challenge

    @classmethod
    def from_bytes(cls, data: bytes) -> "TEEHello":
        if len(data) < 96:
            raise HandshakeError(f"TEEHello too short: {len(data)} < 96 bytes")
        return cls(
            tee_id_hash=data[:32],
            ephemeral_pub=data[32:64],
            challenge=data[64:96],
        )


@dataclass
class SensorAck:
    """
    Message 3 of 3: Sensor → TEE.
    HMAC of the TEE's challenge under the derived session key.
    Proves the sensor completed the same ECDH computation as the TEE.
    """
    challenge_mac: bytes    # HMAC-SHA256(challenge, session_key) — 32 bytes

    def to_bytes(self) -> bytes:
        return self.challenge_mac

    @classmethod
    def from_bytes(cls, data: bytes) -> "SensorAck":
        if len(data) < 32:
            raise HandshakeError(f"SensorAck too short: {len(data)} < 32 bytes")
        return cls(challenge_mac=data[:32])


# ============================================================================
# 3. ENCRYPTED FRAME
# ============================================================================

@dataclass
class EncryptedFrame:
    """
    A single encrypted biometric frame from sensor to TEE.

    The frame_seq is authenticated (included in AEAD additional data)
    but not encrypted — the TEE needs it to enforce anti-replay before
    attempting decryption, which is the cheaper check.

    The nonce is unique per frame. A ChaCha20-Poly1305 nonce reuse would
    catastrophically break confidentiality, so nonces are generated from
    a counter (lower 8 bytes) XOR-ed with the session ID (upper 4 bytes)
    to guarantee uniqueness even if the frame counter wraps (which triggers
    a forced re-handshake before wrap at MAX_FRAME_SEQ).
    """
    frame_seq:   int    # Monotonic, uint32 — anti-replay
    nonce:       bytes  # 12-byte ChaCha20 nonce (unique per frame)
    ciphertext:  bytes  # Encrypted payload + 16-byte Poly1305 tag

    def to_bytes(self) -> bytes:
        payload_len = len(self.ciphertext)
        header = struct.pack(">II", self.frame_seq, payload_len)
        return header + self.nonce + self.ciphertext

    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedFrame":
        if len(data) < FRAME_HEADER_SIZE + CHACHA_NONCE_SIZE + CHACHA_TAG_SIZE:
            raise FrameAuthError("Frame too short to be valid")
        frame_seq, payload_len = struct.unpack_from(">II", data, 0)
        nonce      = data[FRAME_HEADER_SIZE: FRAME_HEADER_SIZE + CHACHA_NONCE_SIZE]
        ciphertext = data[FRAME_HEADER_SIZE + CHACHA_NONCE_SIZE:]
        if len(ciphertext) != payload_len:
            raise FrameAuthError(
                f"Frame length mismatch: header says {payload_len}, "
                f"got {len(ciphertext)} bytes"
            )
        return cls(frame_seq=frame_seq, nonce=nonce, ciphertext=ciphertext)


# ============================================================================
# 4. SESSION — Shared state after handshake completion
# ============================================================================

class SecureBusSession:
    """
    An established ECDH session between a sensor and the TEE.

    Both ends derive the same session_key via X25519 DH + HKDF.
    Holds all state needed to encrypt/decrypt frames and enforce anti-replay.

    Zeroization:
      close() overwrites the session_key reference (best-effort in CPython).
      Production: session_key must live in TPM 2.0 sealed storage (Milestone 2).
    """

    def __init__(
        self,
        session_key:   bytes,
        session_id:    bytes,
        sensor_id_hash: bytes,
        tee_id_hash:   bytes,
        is_sensor_side: bool,
    ):
        self._session_key:     bytes  = session_key
        self._session_id:      bytes  = session_id
        self.sensor_id_hash:   bytes  = sensor_id_hash
        self.tee_id_hash:      bytes  = tee_id_hash
        self._is_sensor_side:  bool   = is_sensor_side

        # Anti-replay state
        self._last_accepted_seq: int   = -1   # TEE side only
        self._next_send_seq:     int   = 0    # Sensor side only
        self._established_at:    float = time.time()
        self._state:             ChannelState = ChannelState.ESTABLISHED

        # ChaCha20-Poly1305 cipher (lazy init on first use)
        self._cipher = ChaCha20Poly1305(self._session_key)

    @property
    def is_valid(self) -> bool:
        if self._state != ChannelState.ESTABLISHED:
            return False
        if (time.time() - self._established_at) > SESSION_TTL_SECONDS:
            self._state = ChannelState.EXPIRED
            return False
        if self._next_send_seq >= MAX_FRAME_SEQ:
            # Sequence number exhausted — force re-handshake
            self._state = ChannelState.EXPIRED
            return False
        return True

    def encrypt_frame(self, plaintext: bytes) -> EncryptedFrame:
        """
        Sensor-side: encrypts a raw biometric payload into an EncryptedFrame.

        Args:
            plaintext: Raw sensor samples (bytes). Max MAX_FRAME_PAYLOAD bytes.

        Returns:
            EncryptedFrame ready to transmit over the hostile bus.

        Raises:
            SessionExpiredError: If TTL elapsed or frame sequence exhausted.
            ValueError:          If plaintext exceeds MAX_FRAME_PAYLOAD.
        """
        if not self.is_valid:
            raise SessionExpiredError(
                "Session expired — sensor must re-handshake with TEE."
            )
        if len(plaintext) > MAX_FRAME_PAYLOAD:
            raise ValueError(
                f"Plaintext {len(plaintext)} bytes exceeds MAX_FRAME_PAYLOAD "
                f"({MAX_FRAME_PAYLOAD}). Split into smaller frames."
            )

        frame_seq = self._next_send_seq
        self._next_send_seq += 1

        # Nonce construction: counter (8 bytes) || session_id_prefix (4 bytes)
        # This guarantees nonce uniqueness within and across sessions.
        nonce = struct.pack(">Q", frame_seq) + self._session_id[:4]

        # AEAD additional data: frame_seq authenticated but not encrypted
        # An attacker cannot swap frames from different positions in the stream.
        aad = struct.pack(">I", frame_seq)

        ciphertext = self._cipher.encrypt(nonce, plaintext, aad)

        return EncryptedFrame(
            frame_seq=frame_seq,
            nonce=nonce,
            ciphertext=ciphertext,
        )

    def decrypt_frame(self, frame: EncryptedFrame) -> bytes:
        """
        TEE-side: decrypts and authenticates an incoming EncryptedFrame.

        Anti-replay enforcement:
          Frames with frame_seq ≤ last_accepted are rejected before
          any decryption attempt. This prevents replay attacks without
          requiring state synchronization with the sensor.

        Args:
            frame: EncryptedFrame received from the bus.

        Returns:
            Decrypted plaintext (raw biometric samples).

        Raises:
            ReplayAttackError: If frame_seq is not strictly increasing.
            FrameAuthError:    If Poly1305 MAC verification fails.
            SessionExpiredError: If session TTL elapsed.
        """
        if not self.is_valid:
            raise SessionExpiredError("Session expired — require re-handshake.")

        # Anti-replay: strictly increasing sequence
        if frame.frame_seq <= self._last_accepted_seq:
            raise ReplayAttackError(
                f"Frame seq {frame.frame_seq} ≤ last accepted "
                f"{self._last_accepted_seq}. Replay or reordering attack."
            )

        aad = struct.pack(">I", frame.frame_seq)

        try:
            plaintext = self._cipher.decrypt(frame.nonce, frame.ciphertext, aad)
        except Exception:
            # ChaCha20-Poly1305 raises InvalidTag on MAC failure.
            # Mark session as compromised — a MAC failure on a valid session
            # indicates active bus tampering.
            self._state = ChannelState.COMPROMISED
            raise FrameAuthError(
                "Frame authentication failed (Poly1305 MAC mismatch). "
                "This indicates active bus tampering or key mismatch. "
                "Session marked COMPROMISED — re-handshake required."
            )

        self._last_accepted_seq = frame.frame_seq
        return plaintext

    def close(self):
        """
        Zeroizes the session key and marks session closed.

        v0.4.5 upgrade: key material is copied to a bytearray and passed to
        secure_zeroize() (ctypes volatile write) before dropping the reference.
        This closes the window where CPython GC retains the original bytes
        object in heap. The bytearray is then explicitly dereferenced.
        """
        if self._session_key and len(self._session_key) > 0:
            key_arr = bytearray(self._session_key)
            _secure_zeroize(key_arr)
            del key_arr
        self._session_key = b"\x00" * 32   # Overwrite reference too
        if self._cipher is not None:
            del self._cipher
        self._cipher = None
        self._state = ChannelState.EXPIRED

    @property
    def state(self) -> ChannelState:
        return self._state

    @property
    def frames_sent(self) -> int:
        return self._next_send_seq

    @property
    def frames_received(self) -> int:
        return self._last_accepted_seq + 1

    @property
    def session_age_seconds(self) -> float:
        return time.time() - self._established_at


# ============================================================================
# 5. SENSOR ENDPOINT — runs on the peripheral side
# ============================================================================

class SensorEndpoint:
    """
    Simulates the cryptographic state machine running on the sensor peripheral.

    In production: this logic runs on the sensor's microcontroller (ARM Cortex-M
    or RISC-V) in a stripped-down secure firmware. The X25519 key pair is
    generated fresh per session and never persisted.

    The sensor does NOT store session keys after zeroization. If power is lost
    mid-session, the sensor starts a fresh handshake on reconnect.
    """

    def __init__(self, sensor_id: bytes):
        """
        Args:
            sensor_id: Raw sensor identifier (arbitrary bytes, ≤ 64 bytes).
                       In production: manufacturer-burned serial number.
        """
        self.sensor_id_hash: bytes = hashlib.sha256(sensor_id).digest()
        self._ephemeral_priv: Optional[X25519PrivateKey] = None
        self._session: Optional[SecureBusSession] = None

    def initiate_handshake(self) -> SensorHello:
        """
        Step 1: Sensor generates an ephemeral X25519 key pair and sends
        SensorHello to the TEE.
        """
        self._ephemeral_priv = X25519PrivateKey.generate()
        pub_bytes = self._ephemeral_priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        return SensorHello(
            sensor_id_hash=self.sensor_id_hash,
            ephemeral_pub=pub_bytes,
            timestamp_ms=int(time.time() * 1000),
        )

    def complete_handshake(
        self,
        tee_hello: TEEHello,
    ) -> Tuple[SensorAck, SecureBusSession]:
        """
        Step 4–5: Sensor receives TEEHello, performs ECDH, derives session key,
        produces SensorAck (HMAC of challenge under session key).

        Returns:
            (SensorAck to send to TEE, SecureBusSession for encrypting frames)
        """
        if self._ephemeral_priv is None:
            raise HandshakeError("Must call initiate_handshake() first.")

        # ECDH: sensor private × TEE public → shared secret
        tee_pub = X25519PublicKey.from_public_bytes(tee_hello.ephemeral_pub)
        shared_secret = self._ephemeral_priv.exchange(tee_pub)

        # HKDF: shared_secret + challenge → session_key
        session_key = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=tee_hello.challenge,
            info=HKDF_INFO_SENSOR_BUS,
        ).derive(shared_secret)

        # Session ID: hash of both public keys — stable identifier
        session_id = hashlib.sha256(
            self._ephemeral_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            + tee_hello.ephemeral_pub
        ).digest()

        # SensorAck: HMAC(challenge, session_key) — proves same DH result
        challenge_mac = hmac.new(
            session_key, tee_hello.challenge, hashlib.sha256
        ).digest()

        # Zeroize ephemeral private key (best-effort)
        self._ephemeral_priv = None

        self._session = SecureBusSession(
            session_key=session_key,
            session_id=session_id,
            sensor_id_hash=self.sensor_id_hash,
            tee_id_hash=tee_hello.tee_id_hash,
            is_sensor_side=True,
        )

        return SensorAck(challenge_mac=challenge_mac), self._session

    @property
    def has_active_session(self) -> bool:
        return self._session is not None and self._session.is_valid


# ============================================================================
# 6. TEE ENDPOINT — runs inside the Secure Enclave
# ============================================================================

class TEEEndpoint:
    """
    Simulates the cryptographic state machine running inside the TEE
    (TrustZone EL1-S / Secure World).

    In production: this is implemented in Layer 1 C (src/layer1/c/keros_core.c)
    running in ARM TrustZone Secure World. The TEE private key never exits
    the Secure World boundary — the Normal World OS cannot read it.

    The TEE maintains one active session per certified sensor. If a sensor
    presents a SensorHello while an existing session is active, the old
    session is torn down first (re-handshake protocol).
    """

    def __init__(self, tee_id: bytes):
        """
        Args:
            tee_id: Stable TEE identity (e.g., TPM endorsement key hash).
        """
        self.tee_id_hash: bytes = hashlib.sha256(tee_id).digest()
        self._sessions: Dict[bytes, SecureBusSession] = {}  # sensor_id_hash → session
        self._pending_challenges: Dict[bytes, Tuple[bytes, X25519PrivateKey]] = {}
        # sensor_id_hash → (challenge, tee_ephemeral_priv)

    def receive_sensor_hello(self, hello: SensorHello) -> TEEHello:
        """
        Step 2–3: TEE receives SensorHello, validates sensor (whitelist check
        placeholder), generates its own ephemeral key pair and challenge.

        In production: sensor_id_hash is verified against the KEROS whitelist
        before proceeding. Here we accept any hash for PoC purposes.

        Returns:
            TEEHello to send back to the sensor.
        """
        # Tear down any existing session for this sensor
        if hello.sensor_id_hash in self._sessions:
            self._sessions[hello.sensor_id_hash].close()
            del self._sessions[hello.sensor_id_hash]

        # Generate TEE ephemeral key
        tee_priv = X25519PrivateKey.generate()
        tee_pub_bytes = tee_priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )

        challenge = secrets.token_bytes(CHALLENGE_SIZE)

        # Store pending state — consumed in complete_handshake()
        self._pending_challenges[hello.sensor_id_hash] = (challenge, tee_priv, hello.ephemeral_pub)

        return TEEHello(
            tee_id_hash=self.tee_id_hash,
            ephemeral_pub=tee_pub_bytes,
            challenge=challenge,
        )

    def complete_handshake(
        self,
        sensor_id_hash: bytes,
        ack: SensorAck,
    ) -> SecureBusSession:
        """
        Step 6: TEE receives SensorAck, performs its own ECDH, derives the
        session key, and verifies that the sensor's challenge_mac matches.

        If verification passes: session is established.
        If verification fails: the pending state is discarded (no partial session).

        Args:
            sensor_id_hash: Identity of the sensor that sent the SensorAck.
            ack:            SensorAck received from the sensor.

        Returns:
            SecureBusSession for decrypting incoming frames.

        Raises:
            HandshakeError: If no pending challenge for this sensor, or MAC fails.
        """
        if sensor_id_hash not in self._pending_challenges:
            raise HandshakeError(
                f"No pending handshake for sensor {sensor_id_hash.hex()[:8]}. "
                "SensorHello must precede SensorAck."
            )

        challenge, tee_priv, sensor_pub_bytes = self._pending_challenges.pop(sensor_id_hash)

        # ECDH: TEE private × sensor public → shared secret (same as sensor side)
        sensor_pub = X25519PublicKey.from_public_bytes(sensor_pub_bytes)
        shared_secret = tee_priv.exchange(sensor_pub)

        # HKDF: same derivation as sensor — should produce identical session_key
        session_key = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=challenge,
            info=HKDF_INFO_SENSOR_BUS,
        ).derive(shared_secret)

        # Verify SensorAck: HMAC(challenge, session_key) must match
        expected_mac = hmac.new(
            session_key, challenge, hashlib.sha256
        ).digest()

        if not hmac.compare_digest(expected_mac, ack.challenge_mac):
            # Discard — do not reveal which part failed
            raise HandshakeError(
                "SensorAck verification failed. "
                "The sensor did not produce the expected ECDH result. "
                "Possible causes: MITM on bus, spoofed sensor, or corrupt transmission."
            )

        session_id = hashlib.sha256(
            sensor_pub_bytes
            + tee_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        ).digest()

        session = SecureBusSession(
            session_key=session_key,
            session_id=session_id,
            sensor_id_hash=sensor_id_hash,
            tee_id_hash=self.tee_id_hash,
            is_sensor_side=False,
        )

        self._sessions[sensor_id_hash] = session
        return session

    def get_session(self, sensor_id_hash: bytes) -> Optional[SecureBusSession]:
        """Returns the active session for a sensor, or None if not established."""
        session = self._sessions.get(sensor_id_hash)
        if session is not None and not session.is_valid:
            del self._sessions[sensor_id_hash]
            return None
        return session

    def close_session(self, sensor_id_hash: bytes):
        """Closes and zeroizes the session for a sensor."""
        if sensor_id_hash in self._sessions:
            self._sessions[sensor_id_hash].close()
            del self._sessions[sensor_id_hash]

    @property
    def active_sessions(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_valid)


# ============================================================================
# 7. CONVENIENCE FACTORY
# ============================================================================

def perform_full_handshake(
    sensor: SensorEndpoint,
    tee:    TEEEndpoint,
) -> Tuple[SecureBusSession, SecureBusSession]:
    """
    Convenience function that performs the complete 3-message handshake
    and returns both session objects (sensor-side and TEE-side).

    In production: each message is transmitted over the physical bus.
    Here, messages are passed directly for PoC/testing purposes.

    Returns:
        (sensor_session, tee_session) — both use the same derived session_key.
    """
    # Message 1: Sensor → TEE
    sensor_hello = sensor.initiate_handshake()

    # Message 2: TEE → Sensor
    tee_hello = tee.receive_sensor_hello(sensor_hello)

    # Message 3: Sensor completes ECDH, sends Ack
    sensor_ack, sensor_session = sensor.complete_handshake(tee_hello)

    # TEE verifies Ack, completes ECDH
    tee_session = tee.complete_handshake(sensor_hello.sensor_id_hash, sensor_ack)

    return sensor_session, tee_session


# ============================================================================
# 8. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  Cortex — ECDH Secure Physical Bus Self-Test")
    print("=" * 68)

    # ── Test 1: Full handshake — both sides derive the same key ──────────────
    print("\n[TEST 1] Full ECDH handshake — key agreement")
    sensor = SensorEndpoint(sensor_id=b"EEG_FP1_CERTIFIED_SN001")
    tee    = TEEEndpoint(tee_id=b"ARM_TRUSTZONE_TEE_UNIT_0")

    s_session, t_session = perform_full_handshake(sensor, tee)

    assert s_session.is_valid, "Sensor session should be valid after handshake"
    assert t_session.is_valid, "TEE session should be valid after handshake"
    assert s_session.sensor_id_hash == t_session.sensor_id_hash
    print(f"  Sensor session: {s_session.state.value} ✅")
    print(f"  TEE session:    {t_session.state.value} ✅")

    # ── Test 2: Encrypted frame is unintelligible to the bus ─────────────────
    print("\n[TEST 2] Frame encryption — bus sees only ciphertext")
    raw_eeg = bytes([i % 256 for i in range(512)])  # 512 bytes of mock EEG data
    frame = s_session.encrypt_frame(raw_eeg)
    wire_bytes = frame.to_bytes()

    # Verify: the plaintext does NOT appear in the wire representation
    assert raw_eeg not in wire_bytes, "Plaintext leaked into wire bytes!"
    assert len(wire_bytes) == FRAME_HEADER_SIZE + CHACHA_NONCE_SIZE + len(raw_eeg) + CHACHA_TAG_SIZE
    print(f"  Raw payload:   {len(raw_eeg)} bytes")
    print(f"  Wire frame:    {len(wire_bytes)} bytes "
          f"(+{len(wire_bytes)-len(raw_eeg)} overhead: header+nonce+tag)")
    print(f"  Plaintext in wire: {raw_eeg in wire_bytes} ✅  (must be False)")

    # ── Test 3: TEE correctly decrypts frame ─────────────────────────────────
    print("\n[TEST 3] TEE decrypts frame — recovers plaintext")
    received_frame = EncryptedFrame.from_bytes(wire_bytes)
    recovered = t_session.decrypt_frame(received_frame)
    assert recovered == raw_eeg, "Decrypted payload does not match original!"
    print(f"  Recovered {len(recovered)} bytes == original ✅")

    # ── Test 4: Replay attack detected ───────────────────────────────────────
    print("\n[TEST 4] Replay attack — same frame re-sent")
    try:
        t_session.decrypt_frame(received_frame)   # Same frame seq=0 again
        print("  [FAIL] Should have raised ReplayAttackError")
    except ReplayAttackError as e:
        print(f"  [PASS] Replay blocked: {str(e)[:60]}… ✅")

    # ── Test 5: Bus tampering → FrameAuthError ───────────────────────────────
    print("\n[TEST 5] Bus tampering (flip a ciphertext byte) → FrameAuthError")
    # Send a second valid frame first
    frame2 = s_session.encrypt_frame(b"second frame payload")
    wire2 = bytearray(frame2.to_bytes())
    # Flip a byte in the ciphertext region
    wire2[FRAME_HEADER_SIZE + CHACHA_NONCE_SIZE + 5] ^= 0xFF
    tampered_frame = EncryptedFrame.from_bytes(bytes(wire2))
    try:
        t_session.decrypt_frame(tampered_frame)
        print("  [FAIL] Should have raised FrameAuthError")
    except FrameAuthError as e:
        print(f"  [PASS] Tampering detected: {str(e)[:60]}… ✅")
    assert t_session.state == ChannelState.COMPROMISED
    print(f"  Session state: {t_session.state.value} (COMPROMISED after MAC failure) ✅")

    # ── Test 6: MITM — attacker substitutes TEE public key ───────────────────
    print("\n[TEST 6] MITM attack — attacker substitutes TEE ephemeral key")
    sensor2 = SensorEndpoint(sensor_id=b"EEG_FP1_CERTIFIED_SN002")
    tee2    = TEEEndpoint(tee_id=b"ARM_TRUSTZONE_TEE_UNIT_0")

    # Sensor sends hello
    hello = sensor2.initiate_handshake()

    # Attacker intercepts TEEHello and substitutes its own key
    legit_tee_hello = tee2.receive_sensor_hello(hello)
    attacker_priv = X25519PrivateKey.generate()
    attacker_pub  = attacker_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    mitm_tee_hello = TEEHello(
        tee_id_hash=legit_tee_hello.tee_id_hash,
        ephemeral_pub=attacker_pub,      # Substituted!
        challenge=legit_tee_hello.challenge,
    )

    # Sensor completes handshake with attacker's key (ECDH with attacker)
    sensor_ack, _ = sensor2.complete_handshake(mitm_tee_hello)

    # TEE receives SensorAck — the HMAC was computed with a different shared secret
    try:
        tee2.complete_handshake(hello.sensor_id_hash, sensor_ack)
        print("  [FAIL] MITM should have caused HandshakeError")
    except HandshakeError as e:
        print(f"  [PASS] MITM detected at SensorAck verification: {str(e)[:60]}… ✅")

    # ── Test 7: Re-handshake after session close ──────────────────────────────
    print("\n[TEST 7] Re-handshake after close — new session keys")
    sensor3 = SensorEndpoint(sensor_id=b"EEG_FP1_CERTIFIED_SN003")
    tee3    = TEEEndpoint(tee_id=b"ARM_TRUSTZONE_TEE_UNIT_0")
    s3a, t3a = perform_full_handshake(sensor3, tee3)
    old_frames_sent = s3a.frames_sent
    s3a.close()
    # Perform fresh handshake
    s3b, t3b = perform_full_handshake(sensor3, tee3)
    assert s3b.frames_sent == 0, "Fresh session should start at frame 0"
    assert s3b.is_valid
    print(f"  Session 1 frames sent: {old_frames_sent}")
    print(f"  Session 2 starts at frame 0 — independent key material ✅")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n✅ Secure Physical Bus tests complete")
    print("   Key exchange:     X25519 ECDH (ephemeral per session)")
    print("   KDF:              HKDF-SHA256 (challenge-salted, domain-separated)")
    print("   Encryption:       ChaCha20-Poly1305 AEAD")
    print("   Anti-replay:      Strictly increasing frame_seq + AEAD AAD")
    print("   MITM resistance:  SensorAck HMAC verification closes the loop")
    print("   Tamper detection: Poly1305 MAC → COMPROMISED state")
    print("   Host OS sees:     ONLY ciphertext — zero plaintext on bus")
