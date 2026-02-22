"""
Data Encryption at Rest

Encrypts sensitive data before storing in database.
Decrypts on retrieval. Uses Fernet symmetric encryption.

Sensitive fields: API keys, passwords, PII, tokens.
Non-sensitive fields: facts, procedures, rules, metrics.

Usage:
    from security.encryption import encrypt_value, decrypt_value
    encrypted = encrypt_value("sensitive data")
    original = decrypt_value(encrypted)
"""

import os
import logging
import base64
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Get or create Fernet cipher."""
    global _fernet
    if _fernet is not None:
        return _fernet

    try:
        from cryptography.fernet import Fernet

        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            # Generate from a deterministic seed (not ideal for production,
            # but works without external config)
            seed = os.getenv("SECRET_KEY", "grace-os-default-seed-change-in-production")
            key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
            logger.warning("[ENCRYPT] Using derived encryption key. Set ENCRYPTION_KEY env var for production.")

        _fernet = Fernet(key if isinstance(key, bytes) else key.encode() if len(key) == 44 else base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))
        return _fernet

    except ImportError:
        logger.warning("[ENCRYPT] cryptography package not installed. Using base64 fallback (NOT secure for production).")
        return None


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    if not value:
        return value

    fernet = _get_fernet()
    if fernet:
        try:
            return "ENC:" + fernet.encrypt(value.encode()).decode()
        except Exception as e:
            logger.warning(f"[ENCRYPT] Encryption failed: {e}")

    # Fallback: base64 encoding (NOT secure, just obfuscation)
    return "B64:" + base64.b64encode(value.encode()).decode()


def decrypt_value(value: str) -> str:
    """Decrypt a previously encrypted value."""
    if not value:
        return value

    if value.startswith("ENC:"):
        fernet = _get_fernet()
        if fernet:
            try:
                return fernet.decrypt(value[4:].encode()).decode()
            except Exception as e:
                logger.warning(f"[ENCRYPT] Decryption failed: {e}")
                return value
    elif value.startswith("B64:"):
        try:
            return base64.b64decode(value[4:].encode()).decode()
        except Exception:
            return value

    return value


def is_encrypted(value: str) -> bool:
    """Check if a value is already encrypted."""
    return value and (value.startswith("ENC:") or value.startswith("B64:"))
