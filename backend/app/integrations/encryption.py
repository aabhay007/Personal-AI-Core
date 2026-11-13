"""Encryption utilities for database credentials and external API tokens."""
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet_key() -> bytes:
    """Derive a URL-safe 32-byte base64 encoded key from settings.SECRET_KEY."""
    raw_hash = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(raw_hash)


def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """Encrypt a secret string (e.g. database password or API token)."""
    if not plain_text:
        return None
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted secret string."""
    if not cipher_text:
        return None
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback if text was stored unencrypted or corrupted
        return cipher_text


def mask_secret(secret: Optional[str]) -> Optional[str]:
    """Return a masked representation for API responses without disclosing sensitive data."""
    if not secret:
        return None
    return "••••••••"
