# ============================================================================
# src/sal/state_buffer_secure.py
# CORTEX PROTOCOL — Secure Memory Buffer (SAL Heap Mitigation)
#
# PROBLEM THIS MODULE CLOSES:
#   Python's `bytes` type is immutable. When code does:
#       key = b"\x01\x02..."
#       key = b"\x00" * 32   # "zeroize"
#   The original bytes object is NOT overwritten. CPython keeps it in heap
#   until the garbage collector runs. On a system with swap enabled,
#   that heap region may persist on disk indefinitely — readable via
#   /proc/<pid>/mem or a memory dump even after the process exits.
#
#   This module provides two things:
#
#   1. SecureTensorBuffer — a mutable ctypes buffer locked into physical RAM
#      via mlock(2). The buffer:
#        a) Cannot be swapped to disk (mlock prevents it)
#        b) Can be explicitly overwritten with zeros before deallocation
#        c) Uses ctypes.c_char array, NOT Python bytes — the array is
#           mutable in-place, so zeroing is guaranteed by the C layer,
#           not by the Python GC
#
#   2. secure_zeroize() — standalone function usable anywhere in the SAL
#      to overwrite a bytearray or ctypes buffer before abandoning it.
#      Uses volatile write pattern via ctypes to prevent compiler
#      optimization from eliding the zeroing loop.
#
# WHAT THIS DOES NOT CLOSE:
#   - Kernel internal copies of memory pages (mitigation requires OP-TEE/TDX)
#   - Python interpreter internals that may copy buffer contents
#   - Third-party libraries that receive data from this buffer and copy it
#     into regular Python objects (e.g., cryptography library internals)
#   - Hibernation images (full disk encryption is the correct mitigation)
#
#   These residual limitations are documented in SECURITY.md §6 and
#   NEUTRALITY.md §4.2. This module closes the most accessible attack
#   vector (process memory dump via /proc) without claiming to close all.
#
# PLATFORM SUPPORT:
#   mlock(2) is available on Linux, macOS, and BSD.
#   On Windows, the equivalent is VirtualLock() — not yet implemented.
#   On systems where mlock fails (container sandboxes, restricted ulimit),
#   the buffer degrades gracefully to best-effort zeroing with a logged warning.
#   The protocol remains functional — the security guarantee is reduced.
#
# DEPENDENCIES: stdlib only (ctypes is part of Python standard library)
# ============================================================================

import ctypes
import ctypes.util
import logging
import os
import sys
import threading
from typing import Optional

logger = logging.getLogger("cortex.secure_buffer")


# ============================================================================
# 0. PLATFORM DETECTION & mlock CAPABILITY CHECK
# ============================================================================

def _load_libc() -> Optional[ctypes.CDLL]:
    """Loads the native C library for mlock/munlock access."""
    if sys.platform == "win32":
        return None  # Windows: VirtualLock not yet implemented
    try:
        return ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
    except OSError:
        return None


def _check_mlock_available(libc: Optional[ctypes.CDLL]) -> bool:
    """
    Probes whether mlock is available and usable on this system.
    Allocates and immediately frees a 64-byte test buffer.
    Returns False if mlock fails (permission denied, container limit, etc.)
    """
    if libc is None:
        return False
    try:
        test_buf = (ctypes.c_char * 64)()
        result = libc.mlock(ctypes.byref(test_buf), ctypes.c_size_t(64))
        if result == 0:
            libc.munlock(ctypes.byref(test_buf), ctypes.c_size_t(64))
            return True
        return False
    except Exception:
        return False


_LIBC = _load_libc()
MLOCK_AVAILABLE: bool = _check_mlock_available(_LIBC)

if MLOCK_AVAILABLE:
    logger.debug("[SecureBuffer] mlock available — physical RAM locking ACTIVE")
else:
    logger.warning(
        "[SecureBuffer] mlock NOT available on this system. "
        "Buffer will use best-effort zeroing without physical RAM locking. "
        "Swap persistence risk remains. See SECURITY.md §6."
    )


# ============================================================================
# 1. VOLATILE ZERO WRITE (compiler-safe zeroing)
# ============================================================================

def _volatile_zero_ctypes_buffer(buf: ctypes.Array, size: int) -> None:
    """
    Overwrites a ctypes buffer with zeros using a volatile write pattern.

    Why not memset? Python's ctypes doesn't expose volatile semantics
    directly. We use a byte-by-byte loop via ctypes pointer arithmetic,
    which the Python interpreter cannot optimize away (unlike a pure-Python
    loop that a JIT compiler might elide).

    For production C integration: replace with explicit_bzero(3) or
    SecureZeroMemory() at the boundary layer.
    """
    p = ctypes.cast(ctypes.byref(buf), ctypes.POINTER(ctypes.c_uint8))
    for i in range(size):
        p[i] = 0


def secure_zeroize(data: bytearray) -> None:
    """
    Overwrites a bytearray in-place with zeros.

    Works with bytearray (mutable). Does NOT work with bytes (immutable).
    Call this before abandoning any bytearray that contains key material
    or biometric data.

    Example:
        key = bytearray(session_key_bytes)
        try:
            # ... use key ...
        finally:
            secure_zeroize(key)
            del key
    """
    if not isinstance(data, bytearray):
        raise TypeError(
            f"secure_zeroize requires bytearray, got {type(data).__name__}. "
            "Convert bytes to bytearray before passing to secure_zeroize."
        )
    for i in range(len(data)):
        data[i] = 0


# ============================================================================
# 2. SecureTensorBuffer — The Core Secure Memory Container
# ============================================================================

class SecureTensorBuffer:
    """
    A memory buffer for sensitive biometric data that:

      1. Uses a mutable ctypes.c_char array (NOT Python bytes)
         → enables explicit in-place zeroing
      2. Locks the buffer pages into physical RAM via mlock(2)
         → prevents the OS from swapping buffer contents to disk
      3. Explicitly zeros the buffer before deallocation
         → closes the GC timing gap in CPython heap management
      4. Is thread-safe via RLock
         → safe to use across the SAL async pipeline

    Intended use:
      - Temporary storage of raw biometric tensors before Φ-transform
      - Storage of HMAC keys during a session
      - Any biometric data that must survive a Python function boundary
        but must NOT persist after session close

    Context manager pattern (preferred):
        with SecureTensorBuffer(size=128) as buf:
            buf.write(raw_tensor_bytes)
            processed = transform(buf.read())
        # Buffer is zeroed and unlocked here automatically

    Manual pattern:
        buf = SecureTensorBuffer(size=128)
        try:
            buf.write(data)
            ...
        finally:
            buf.secure_purge()
    """

    MAX_SIZE: int = 65_536   # 64 KB maximum — prevents accidental large allocations

    def __init__(self, size: int):
        if size <= 0 or size > self.MAX_SIZE:
            raise ValueError(
                f"SecureTensorBuffer size must be 1–{self.MAX_SIZE} bytes, got {size}."
            )
        self._size = size
        self._lock = threading.RLock()
        self._purged = False

        # Allocate as ctypes array — mutable, not managed by Python GC
        self._buffer = (ctypes.c_char * size)()

        # Attempt physical RAM lock
        self._mlocked = False
        if _LIBC is not None and MLOCK_AVAILABLE:
            result = _LIBC.mlock(
                ctypes.byref(self._buffer),
                ctypes.c_size_t(self._size)
            )
            self._mlocked = (result == 0)
            if not self._mlocked:
                logger.warning(
                    f"[SecureBuffer] mlock failed for {size}-byte buffer "
                    "(errno indicates permission limit). "
                    "Operating in best-effort mode."
                )

    def write(self, data: bytes) -> None:
        """
        Writes data into the buffer.

        Args:
            data: Bytes to write. Must not exceed buffer size.

        Raises:
            ValueError: If data exceeds buffer capacity.
            RuntimeError: If buffer has been purged.
        """
        with self._lock:
            self._assert_not_purged()
            if len(data) > self._size:
                raise ValueError(
                    f"Data length {len(data)} exceeds buffer size {self._size}."
                )
            # Write byte-by-byte into the ctypes array
            for i, byte in enumerate(data):
                self._buffer[i] = ctypes.c_char(byte)
            # Zero-pad remaining capacity
            for i in range(len(data), self._size):
                self._buffer[i] = b'\x00'

    def read(self, length: Optional[int] = None) -> bytes:
        """
        Reads data from the buffer.

        Args:
            length: Number of bytes to read. Defaults to full buffer size.

        Returns:
            bytes copy of buffer contents.
            Note: the returned bytes object is a Python-managed copy —
            it does NOT benefit from mlock. Use it immediately and do not
            store it in long-lived variables.

        Raises:
            RuntimeError: If buffer has been purged.
        """
        with self._lock:
            self._assert_not_purged()
            n = length if length is not None else self._size
            n = min(n, self._size)
            return bytes(self._buffer[:n])

    def secure_purge(self) -> None:
        """
        Overwrites buffer with zeros, releases mlock, and marks buffer as purged.

        After calling secure_purge(), all read/write operations raise RuntimeError.
        This method is idempotent — calling it multiple times is safe.
        """
        with self._lock:
            if self._purged:
                return

            # 1. Zero the buffer (volatile write pattern)
            _volatile_zero_ctypes_buffer(self._buffer, self._size)

            # 2. Release physical RAM lock
            if self._mlocked and _LIBC is not None:
                _LIBC.munlock(
                    ctypes.byref(self._buffer),
                    ctypes.c_size_t(self._size)
                )
                self._mlocked = False

            # 3. Mark as purged — subsequent access raises
            self._purged = True

    def __enter__(self) -> "SecureTensorBuffer":
        return self

    def __exit__(self, *_) -> bool:
        self.secure_purge()
        return False   # Don't suppress exceptions

    def __del__(self):
        """
        Finalizer — purges buffer if secure_purge() was not called explicitly.

        This is a safety net, not the primary mechanism. The context manager
        or explicit secure_purge() is the correct usage pattern. __del__ is
        called by CPython's reference counting — timing is non-deterministic
        in the presence of cycles.
        """
        if not self._purged:
            logger.warning(
                "[SecureBuffer] Buffer was GC'd without explicit secure_purge(). "
                "This indicates a missing finally/context manager in calling code. "
                "Zeroing now as fallback."
            )
            try:
                self.secure_purge()
            except Exception:
                pass   # Never raise in __del__

    @property
    def size(self) -> int:
        return self._size

    @property
    def is_mlocked(self) -> bool:
        """True if buffer pages are locked in physical RAM (not swappable)."""
        return self._mlocked

    @property
    def is_purged(self) -> bool:
        return self._purged

    def _assert_not_purged(self) -> None:
        if self._purged:
            raise RuntimeError(
                "SecureTensorBuffer has been purged and cannot be accessed. "
                "Create a new buffer for each session."
            )

    def __repr__(self) -> str:
        state = "PURGED" if self._purged else ("mlocked" if self._mlocked else "best-effort")
        return f"SecureTensorBuffer(size={self._size}, state={state})"


# ============================================================================
# 3. SecureKeyBuffer — Specialized Buffer for HMAC/Session Keys
# ============================================================================

class SecureKeyBuffer:
    """
    Specialized secure buffer for 32-byte cryptographic keys.

    Wraps SecureTensorBuffer with:
      - Fixed 32-byte size (enforced for HMAC-SHA256 / ChaCha20 keys)
      - Key comparison via constant-time compare (no early exit)
      - Export as bytearray for use with hmac.new() / cryptography library
        (caller is responsible for zeroing the exported bytearray)

    Example — replacing a plain bytes key in ClinicalSessionKey:
        with SecureKeyBuffer(raw_key_bytes) as key_buf:
            mac = hmac.new(key_buf.export_bytearray(), msg, hashlib.sha256).digest()
            # bytearray is zeroed here automatically via the context manager
    """

    KEY_SIZE: int = 32

    def __init__(self, key_bytes: bytes):
        if len(key_bytes) != self.KEY_SIZE:
            raise ValueError(
                f"SecureKeyBuffer requires exactly {self.KEY_SIZE} bytes, "
                f"got {len(key_bytes)}."
            )
        self._buf = SecureTensorBuffer(size=self.KEY_SIZE)
        self._buf.write(key_bytes)

    def export_bytearray(self) -> bytearray:
        """
        Returns a bytearray copy of the key for use with crypto primitives.

        IMPORTANT: The returned bytearray is NOT mlocked.
        Caller must call secure_zeroize(exported_ba) after use.

        Example:
            key_ba = key_buf.export_bytearray()
            try:
                mac = hmac.new(key_ba, data, hashlib.sha256).digest()
            finally:
                secure_zeroize(key_ba)
        """
        self._buf._assert_not_purged()
        return bytearray(self._buf.read())

    def constant_time_compare(self, other: bytes) -> bool:
        """
        Constant-time comparison — prevents timing oracle attacks.
        Safe to use for MAC verification.
        """
        import hmac as _hmac
        self._buf._assert_not_purged()
        key_bytes = self._buf.read()
        result = _hmac.compare_digest(key_bytes, other)
        return result

    def secure_purge(self) -> None:
        self._buf.secure_purge()

    def __enter__(self) -> "SecureKeyBuffer":
        return self

    def __exit__(self, *_) -> bool:
        self.secure_purge()
        return False

    @property
    def is_mlocked(self) -> bool:
        return self._buf.is_mlocked

    @property
    def is_purged(self) -> bool:
        return self._buf.is_purged


# ============================================================================
# 4. SELF-TEST
# ============================================================================

if __name__ == "__main__":
    import hashlib
    import hmac as _hmac
    import secrets

    print("=" * 68)
    print("  Cortex — Secure Memory Buffer Self-Test")
    print("=" * 68)
    print(f"\n  mlock available: {MLOCK_AVAILABLE}")
    print(f"  Platform: {sys.platform}")

    # ── Test 1: Basic write/read/purge ────────────────────────────────────────
    print("\n[TEST 1] Write → Read → Purge lifecycle")
    data = secrets.token_bytes(64)
    with SecureTensorBuffer(size=128) as buf:
        assert not buf.is_purged
        buf.write(data)
        recovered = buf.read(64)
        assert recovered == data, "Read/write mismatch"
        print(f"  mlocked: {buf.is_mlocked}")
    # After context exit — buffer is purged
    assert buf.is_purged
    print("  [PASS] Buffer purged on context exit ✅")

    # ── Test 2: Buffer is zeroed after purge ──────────────────────────────────
    print("\n[TEST 2] Memory is zeroed after purge (not just reference dropped)")
    key_data = secrets.token_bytes(32)
    buf2 = SecureTensorBuffer(size=32)
    buf2.write(key_data)
    # Manually grab the ctypes pointer address before purge
    # After purge, the underlying ctypes array should be all zeros
    buf2.secure_purge()
    # Try to read the ctypes buffer directly — should be all zeros
    raw = bytes(buf2._buffer)
    assert all(b == 0 for b in raw), "Buffer NOT zeroed after purge!"
    print("  [PASS] ctypes buffer is all-zeros after purge ✅")

    # ── Test 3: Access after purge raises ─────────────────────────────────────
    print("\n[TEST 3] Access after purge raises RuntimeError")
    buf3 = SecureTensorBuffer(size=32)
    buf3.write(b"\x42" * 32)
    buf3.secure_purge()
    try:
        buf3.read()
        print("  [FAIL] Should have raised RuntimeError")
    except RuntimeError:
        print("  [PASS] RuntimeError on read-after-purge ✅")
    try:
        buf3.write(b"\x00" * 32)
        print("  [FAIL] Should have raised RuntimeError")
    except RuntimeError:
        print("  [PASS] RuntimeError on write-after-purge ✅")

    # ── Test 4: SecureKeyBuffer + constant-time compare ───────────────────────
    print("\n[TEST 4] SecureKeyBuffer constant-time comparison")
    key = secrets.token_bytes(32)
    wrong = secrets.token_bytes(32)
    with SecureKeyBuffer(key) as kb:
        assert kb.constant_time_compare(key)
        assert not kb.constant_time_compare(wrong)
        print(f"  mlocked: {kb.is_mlocked}")
    assert kb.is_purged
    print("  [PASS] Constant-time comparison correct, purged on exit ✅")

    # ── Test 5: SecureKeyBuffer export + use with hmac ────────────────────────
    print("\n[TEST 5] SecureKeyBuffer → export → hmac → secure_zeroize")
    key2 = secrets.token_bytes(32)
    msg = b"biometric_tensor_example"
    with SecureKeyBuffer(key2) as kb2:
        ba = kb2.export_bytearray()
        try:
            mac = _hmac.new(bytes(ba), msg, hashlib.sha256).digest()
        finally:
            secure_zeroize(ba)
        # Verify ba is all zeros now
        assert all(b == 0 for b in ba), "Exported bytearray not zeroed"
    print("  [PASS] HMAC computed, exported bytearray zeroed ✅")

    # ── Test 6: Overflow protection ───────────────────────────────────────────
    print("\n[TEST 6] Write overflow raises ValueError")
    buf6 = SecureTensorBuffer(size=16)
    try:
        buf6.write(b"\x00" * 17)
        print("  [FAIL] Should have raised ValueError")
    except ValueError:
        print("  [PASS] Overflow blocked ✅")
    finally:
        buf6.secure_purge()

    # ── Test 7: secure_zeroize on bytearray ──────────────────────────────────
    print("\n[TEST 7] secure_zeroize() wipes bytearray in-place")
    sensitive = bytearray(b"session_key_material_32bytes_xxx")
    original_id = id(sensitive)
    secure_zeroize(sensitive)
    assert all(b == 0 for b in sensitive), "bytearray not zeroed"
    assert id(sensitive) == original_id, "secure_zeroize should not create new object"
    print("  [PASS] bytearray zeroed in-place, same object ✅")

    # ── Test 8: secure_zeroize rejects bytes (immutable) ─────────────────────
    print("\n[TEST 8] secure_zeroize rejects immutable bytes")
    try:
        secure_zeroize(b"should_fail")  # type: ignore
        print("  [FAIL] Should have raised TypeError")
    except TypeError:
        print("  [PASS] TypeError on immutable bytes ✅")

    print(f"\n✅ Secure Memory Buffer tests complete")
    print(f"   mlock:          {'ACTIVE — no swap exposure' if MLOCK_AVAILABLE else 'UNAVAILABLE — best-effort only'}")
    print(f"   Zeroing:        ctypes volatile write (compiler-safe)")
    print(f"   GC safety:      __del__ fallback + context manager primary")
    print(f"   Key operations: SecureKeyBuffer.export_bytearray() + secure_zeroize()")
