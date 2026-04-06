"""Cryptographic helpers for AutonomicLab auth."""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

# Static app secret — baked into binary.  Provides defence-in-depth so
# casual users cannot simply read/edit the database with a text editor.
_APP_SECRET = b"AutonomicLab-2026-GAT-secret-xK9mP2"
_SALT       = b"autonomiclab-salt-v1"


def _derive_key() -> bytes:
    """Derive a Fernet key from the app secret (same on all machines)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(_APP_SECRET))


_FERNET = Fernet(_derive_key())


def encrypt_bytes(data: bytes) -> bytes:
    return _FERNET.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _FERNET.decrypt(token)


def mac_hash() -> str:
    """Return SHA-256 hex of the primary MAC address."""
    mac = uuid.getnode()
    raw = mac.to_bytes(6, "big")
    return hashlib.sha256(raw + _APP_SECRET).hexdigest()


def guest_sign(mac_h: str, remaining: int) -> str:
    """HMAC-SHA256 signature for the guest counter file."""
    key  = hashlib.sha256(_APP_SECRET + mac_h.encode()).digest()
    msg  = f"{mac_h}:{remaining}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def guest_verify(mac_h: str, remaining: int, sig: str) -> bool:
    expected = guest_sign(mac_h, remaining)
    return hmac.compare_digest(expected, sig)
