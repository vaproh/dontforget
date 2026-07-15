"""Optional per-note encryption for Better Dontforget.

Uses authenticated encryption (Fernet) with a key derived from a user passphrase
via PBKDF2-HMAC-SHA256. Plaintext is never persisted; the encrypted payload is
the salt (base64) and the Fernet token joined by ':'. Decryption with the wrong
passphrase fails closed (``cryptography.fernet.InvalidToken``).
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_PBKDF2_ITERATIONS = 200_000
_SEPARATOR = ":"


class DecryptionError(Exception):
    """Raised when a note cannot be decrypted (wrong passphrase or corrupt data)."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def encrypt(passphrase: str, plaintext: str) -> str:
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(salt).decode() + _SEPARATOR + token.decode()


def decrypt(passphrase: str, payload: str) -> str:
    if _SEPARATOR not in payload:
        raise DecryptionError("Encrypted payload is malformed.")
    salt_b64, token = payload.split(_SEPARATOR, 1)
    try:
        salt = base64.urlsafe_b64decode(salt_b64)
        key = _derive_key(passphrase, salt)
        return Fernet(key).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, KeyError) as exc:
        raise DecryptionError("Failed to decrypt note (wrong passphrase?).") from exc


def is_encrypted_payload(payload: str) -> bool:
    return _SEPARATOR in payload and len(payload) > 0
