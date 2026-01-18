"""
Cryptographically Secure Random Generation for GRACE

Provides secure random number generation for:
- Token generation
- Nonce generation
- Salt generation
- IV generation
"""

import secrets
import os
import string
import struct
from typing import Optional
from datetime import datetime


class SecureRandom:
    """Cryptographically secure random generator."""
    
    @staticmethod
    def bytes(length: int) -> bytes:
        """Generate cryptographically secure random bytes."""
        if length <= 0:
            raise ValueError("Length must be positive")
        return secrets.token_bytes(length)
    
    @staticmethod
    def hex(length: int) -> str:
        """Generate cryptographically secure random hex string."""
        if length <= 0:
            raise ValueError("Length must be positive")
        return secrets.token_hex(length)
    
    @staticmethod
    def urlsafe(length: int) -> str:
        """Generate URL-safe base64-encoded random string."""
        if length <= 0:
            raise ValueError("Length must be positive")
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def integer(min_val: int, max_val: int) -> int:
        """Generate cryptographically secure random integer in range [min_val, max_val]."""
        if min_val > max_val:
            raise ValueError("min_val must be <= max_val")
        return secrets.randbelow(max_val - min_val + 1) + min_val
    
    @staticmethod
    def choice(sequence):
        """Select a random element from a sequence."""
        if not sequence:
            raise ValueError("Sequence cannot be empty")
        return secrets.choice(sequence)
    
    @staticmethod
    def shuffle(sequence: list) -> list:
        """Cryptographically secure shuffle of a list (returns new list)."""
        result = sequence.copy()
        for i in range(len(result) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            result[i], result[j] = result[j], result[i]
        return result


class TokenGenerator:
    """Secure token generation for various purposes."""
    
    DEFAULT_TOKEN_LENGTH = 32
    DEFAULT_API_KEY_LENGTH = 32
    DEFAULT_SESSION_LENGTH = 64
    DEFAULT_RESET_TOKEN_LENGTH = 48
    
    @staticmethod
    def generate_token(length: int = DEFAULT_TOKEN_LENGTH, prefix: str = "") -> str:
        """Generate a secure random token."""
        token = secrets.token_urlsafe(length)
        return f"{prefix}{token}" if prefix else token
    
    @staticmethod
    def generate_api_key(prefix: str = "grace_") -> str:
        """Generate a secure API key with prefix."""
        return f"{prefix}{secrets.token_urlsafe(TokenGenerator.DEFAULT_API_KEY_LENGTH)}"
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session identifier."""
        return secrets.token_urlsafe(TokenGenerator.DEFAULT_SESSION_LENGTH)
    
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate a secure password reset token."""
        return secrets.token_urlsafe(TokenGenerator.DEFAULT_RESET_TOKEN_LENGTH)
    
    @staticmethod
    def generate_verification_code(length: int = 6, numeric_only: bool = True) -> str:
        """Generate a verification code (e.g., for 2FA)."""
        if numeric_only:
            return ''.join(secrets.choice(string.digits) for _ in range(length))
        alphabet = string.ascii_uppercase + string.digits
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_uuid_v4() -> str:
        """Generate a cryptographically random UUID v4."""
        random_bytes = secrets.token_bytes(16)
        random_bytes = bytearray(random_bytes)
        random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40
        random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80
        hex_str = random_bytes.hex()
        return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"


class NonceGenerator:
    """Secure nonce generation for cryptographic operations."""
    
    AES_GCM_NONCE_SIZE = 12
    CHACHA20_NONCE_SIZE = 12
    DEFAULT_NONCE_SIZE = 16
    
    _counter = 0
    _instance_id = None
    
    @classmethod
    def _get_instance_id(cls) -> bytes:
        """Get unique instance identifier for this process."""
        if cls._instance_id is None:
            cls._instance_id = secrets.token_bytes(8)
        return cls._instance_id
    
    @classmethod
    def generate_nonce(cls, size: int = DEFAULT_NONCE_SIZE) -> bytes:
        """Generate a cryptographically secure nonce."""
        return secrets.token_bytes(size)
    
    @classmethod
    def generate_counter_nonce(cls, size: int = DEFAULT_NONCE_SIZE) -> bytes:
        """Generate a nonce using counter mode for guaranteed uniqueness."""
        cls._counter += 1
        timestamp = int(datetime.utcnow().timestamp() * 1000000)
        counter_bytes = struct.pack('>Q', cls._counter)
        timestamp_bytes = struct.pack('>Q', timestamp)
        instance_id = cls._get_instance_id()
        combined = counter_bytes + timestamp_bytes + instance_id
        combined_padded = combined[:size] if len(combined) >= size else combined + secrets.token_bytes(size - len(combined))
        return combined_padded[:size]
    
    @classmethod
    def generate_aes_gcm_nonce(cls) -> bytes:
        """Generate a 12-byte nonce for AES-GCM."""
        return cls.generate_nonce(cls.AES_GCM_NONCE_SIZE)
    
    @classmethod
    def generate_chacha20_nonce(cls) -> bytes:
        """Generate a 12-byte nonce for ChaCha20-Poly1305."""
        return cls.generate_nonce(cls.CHACHA20_NONCE_SIZE)


class SaltGenerator:
    """Secure salt generation for password hashing and key derivation."""
    
    DEFAULT_SALT_SIZE = 16
    ARGON2_SALT_SIZE = 16
    BCRYPT_SALT_SIZE = 16
    PBKDF2_SALT_SIZE = 16
    SCRYPT_SALT_SIZE = 32
    
    @staticmethod
    def generate_salt(size: int = DEFAULT_SALT_SIZE) -> bytes:
        """Generate a cryptographically secure salt."""
        return secrets.token_bytes(size)
    
    @staticmethod
    def generate_argon2_salt() -> bytes:
        """Generate salt for Argon2 password hashing."""
        return secrets.token_bytes(SaltGenerator.ARGON2_SALT_SIZE)
    
    @staticmethod
    def generate_bcrypt_salt() -> bytes:
        """Generate salt for bcrypt password hashing."""
        return secrets.token_bytes(SaltGenerator.BCRYPT_SALT_SIZE)
    
    @staticmethod
    def generate_pbkdf2_salt() -> bytes:
        """Generate salt for PBKDF2 key derivation."""
        return secrets.token_bytes(SaltGenerator.PBKDF2_SALT_SIZE)
    
    @staticmethod
    def generate_scrypt_salt() -> bytes:
        """Generate salt for scrypt key derivation."""
        return secrets.token_bytes(SaltGenerator.SCRYPT_SALT_SIZE)


class IVGenerator:
    """Initialization vector generation for encryption."""
    
    AES_CBC_IV_SIZE = 16
    AES_CTR_IV_SIZE = 16
    AES_GCM_IV_SIZE = 12
    
    @staticmethod
    def generate_iv(size: int) -> bytes:
        """Generate a cryptographically secure IV."""
        return secrets.token_bytes(size)
    
    @staticmethod
    def generate_aes_cbc_iv() -> bytes:
        """Generate a 16-byte IV for AES-CBC."""
        return secrets.token_bytes(IVGenerator.AES_CBC_IV_SIZE)
    
    @staticmethod
    def generate_aes_ctr_iv() -> bytes:
        """Generate a 16-byte IV for AES-CTR."""
        return secrets.token_bytes(IVGenerator.AES_CTR_IV_SIZE)
    
    @staticmethod
    def generate_aes_gcm_iv() -> bytes:
        """Generate a 12-byte IV for AES-GCM."""
        return secrets.token_bytes(IVGenerator.AES_GCM_IV_SIZE)


def generate_secure_bytes(length: int) -> bytes:
    """Convenience function: Generate secure random bytes."""
    return SecureRandom.bytes(length)


def generate_token(length: int = 32, prefix: str = "") -> str:
    """Convenience function: Generate a secure token."""
    return TokenGenerator.generate_token(length, prefix)


def generate_nonce(size: int = 16) -> bytes:
    """Convenience function: Generate a secure nonce."""
    return NonceGenerator.generate_nonce(size)


def generate_salt(size: int = 16) -> bytes:
    """Convenience function: Generate a secure salt."""
    return SaltGenerator.generate_salt(size)
