"""Fernet-based encryption for sensitive credentials (DB passwords, LLM API keys)."""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_fernet_key

_fernet = Fernet(get_fernet_key())


def encrypt(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None for empty/None input."""
    if plaintext is None or plaintext == "":
        return None
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str | None) -> str | None:
    """Decrypt a token. Returns None for empty/None input or invalid tokens."""
    if not token:
        return None
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None


def mask(value: str | None, visible: int = 4) -> str:
    """Mask a secret for display, keeping only the last `visible` characters."""
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]
