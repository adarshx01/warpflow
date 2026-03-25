"""Encryption helpers for protecting user secrets at rest."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()


def _build_fernet() -> Fernet:
    """Build a deterministic Fernet key from configured secrets."""
    raw = (settings.SECRETS_ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


_FERNET = _build_fernet()


def encrypt_value(value: str) -> str:
    if not value:
        return value
    token = _FERNET.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"enc:{token}"


def decrypt_value(value: str | None) -> str | None:
    if value is None:
        return None
    if not value:
        return value
    if not value.startswith("enc:"):
        # Backward compatibility for already-stored plaintext values.
        return value

    token = value[4:]
    try:
        return _FERNET.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored secret. Check server encryption key configuration.",
        ) from exc
