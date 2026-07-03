"""Fernet encryption for source tokens stored at rest.

Uses ``settings.TOKEN_ENCRYPTION_KEY`` when set. In development, falls
back to an ephemeral key generated at import time (with a warning) —
tokens encrypted with it become unreadable after a restart.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings

logger = logging.getLogger(__name__)

if settings.TOKEN_ENCRYPTION_KEY:
    _fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())
else:
    logger.warning(
        "TOKEN_ENCRYPTION_KEY is not set — using an ephemeral key. "
        "Stored source tokens will be unreadable after a restart."
    )
    _fernet = Fernet(Fernet.generate_key())


def encrypt_token(token: str) -> str:
    """Encrypt a plaintext token for storage."""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored token.

    Raises:
        ValueError: If the ciphertext cannot be decrypted (wrong or
            rotated key).
    """
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Cannot decrypt stored token — TOKEN_ENCRYPTION_KEY changed?"
        ) from exc
