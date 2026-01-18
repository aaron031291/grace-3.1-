"""
Secure Hashing for GRACE

Provides secure hashing implementations:
- Password hashing with Argon2id
- Content integrity hashing (SHA-256, SHA-3)
- HMAC for message authentication
- Hash verification utilities
"""

import hashlib
import hmac
import base64
import logging
from typing import Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from .random import SaltGenerator, generate_salt

logger = logging.getLogger(__name__)


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_384 = "sha3_384"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"


@dataclass
class Argon2Config:
    """Configuration for Argon2id password hashing."""
    time_cost: int = 3
    memory_cost: int = 65536
    parallelism: int = 4
    hash_length: int = 32
    salt_length: int = 16


class PasswordHasher:
    """Secure password hashing using Argon2id."""
    
    ALGORITHM_PREFIX = "$argon2id$"
    
    def __init__(self, config: Optional[Argon2Config] = None):
        self.config = config or Argon2Config()
        self._argon2_available = False
        try:
            import argon2
            self._hasher = argon2.PasswordHasher(
                time_cost=self.config.time_cost,
                memory_cost=self.config.memory_cost,
                parallelism=self.config.parallelism,
                hash_len=self.config.hash_length,
                salt_len=self.config.salt_length,
            )
            self._argon2_available = True
        except ImportError:
            logger.warning("argon2-cffi not available, using PBKDF2 fallback")
            self._hasher = None
    
    def hash(self, password: str) -> str:
        """Hash a password using Argon2id."""
        if not password:
            raise ValueError("Password cannot be empty")
        
        if self._argon2_available and self._hasher:
            return self._hasher.hash(password)
        else:
            return self._pbkdf2_hash(password)
    
    def verify(self, password: str, hash_str: str) -> bool:
        """Verify a password against a hash."""
        if not password or not hash_str:
            return False
        
        try:
            if hash_str.startswith(self.ALGORITHM_PREFIX):
                if self._argon2_available and self._hasher:
                    self._hasher.verify(hash_str, password)
                    return True
                else:
                    return False
            elif hash_str.startswith("$pbkdf2$"):
                return self._pbkdf2_verify(password, hash_str)
            else:
                return False
        except Exception:
            return False
    
    def needs_rehash(self, hash_str: str) -> bool:
        """Check if a hash needs to be rehashed with updated parameters."""
        if self._argon2_available and self._hasher:
            try:
                return self._hasher.check_needs_rehash(hash_str)
            except Exception:
                return True
        return not hash_str.startswith("$pbkdf2$")
    
    def _pbkdf2_hash(self, password: str) -> str:
        """Fallback PBKDF2 hashing."""
        salt = SaltGenerator.generate_pbkdf2_salt()
        iterations = 600000
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations,
            dklen=self.config.hash_length
        )
        salt_b64 = base64.b64encode(salt).decode('ascii')
        hash_b64 = base64.b64encode(hash_bytes).decode('ascii')
        return f"$pbkdf2${iterations}${salt_b64}${hash_b64}"
    
    def _pbkdf2_verify(self, password: str, hash_str: str) -> bool:
        """Verify PBKDF2 hash."""
        try:
            parts = hash_str.split('$')
            if len(parts) != 5 or parts[1] != 'pbkdf2':
                return False
            iterations = int(parts[2])
            salt = base64.b64decode(parts[3])
            stored_hash = base64.b64decode(parts[4])
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations,
                dklen=len(stored_hash)
            )
            return hmac.compare_digest(stored_hash, computed_hash)
        except Exception:
            return False


class ContentHasher:
    """Content integrity hashing."""
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self.algorithm = algorithm
    
    def hash(self, data: Union[bytes, str]) -> str:
        """Hash content and return hex digest."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self._get_hasher().update(data).hexdigest()
    
    def hash_bytes(self, data: Union[bytes, str]) -> bytes:
        """Hash content and return raw bytes."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self._get_hasher().update(data).digest()
    
    def hash_file(self, filepath: str, chunk_size: int = 8192) -> str:
        """Hash a file's contents."""
        hasher = self._get_hasher()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def hash_stream(self, stream, chunk_size: int = 8192) -> str:
        """Hash data from a stream."""
        hasher = self._get_hasher()
        while chunk := stream.read(chunk_size):
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            hasher.update(chunk)
        return hasher.hexdigest()
    
    def verify(self, data: Union[bytes, str], expected_hash: str) -> bool:
        """Verify content against expected hash."""
        computed = self.hash(data)
        return hmac.compare_digest(computed.lower(), expected_hash.lower())
    
    def verify_file(self, filepath: str, expected_hash: str) -> bool:
        """Verify file content against expected hash."""
        computed = self.hash_file(filepath)
        return hmac.compare_digest(computed.lower(), expected_hash.lower())
    
    def _get_hasher(self):
        """Get the appropriate hasher instance."""
        algo_name = self.algorithm.value
        if algo_name.startswith('sha3_'):
            return hashlib.new(algo_name)
        elif algo_name == 'blake2b':
            return hashlib.blake2b()
        elif algo_name == 'blake2s':
            return hashlib.blake2s()
        else:
            return hashlib.new(algo_name)


class HMACAuthenticator:
    """HMAC-based message authentication."""
    
    def __init__(self, key: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        if not key or len(key) < 16:
            raise ValueError("HMAC key must be at least 16 bytes")
        self.key = key
        self.algorithm = algorithm
    
    def sign(self, message: Union[bytes, str]) -> str:
        """Create HMAC signature for a message."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return hmac.new(
            self.key,
            message,
            self.algorithm.value
        ).hexdigest()
    
    def sign_bytes(self, message: Union[bytes, str]) -> bytes:
        """Create HMAC signature as bytes."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return hmac.new(
            self.key,
            message,
            self.algorithm.value
        ).digest()
    
    def verify(self, message: Union[bytes, str], signature: str) -> bool:
        """Verify HMAC signature."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        expected = self.sign(message)
        return hmac.compare_digest(expected, signature)
    
    def verify_bytes(self, message: Union[bytes, str], signature: bytes) -> bool:
        """Verify HMAC signature (bytes)."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        expected = self.sign_bytes(message)
        return hmac.compare_digest(expected, signature)
    
    @staticmethod
    def generate_key(length: int = 32) -> bytes:
        """Generate a secure HMAC key."""
        return generate_salt(length)


class HashVerifier:
    """Utility class for hash verification."""
    
    @staticmethod
    def verify_sha256(data: Union[bytes, str], expected: str) -> bool:
        """Verify SHA-256 hash."""
        hasher = ContentHasher(HashAlgorithm.SHA256)
        return hasher.verify(data, expected)
    
    @staticmethod
    def verify_sha3_256(data: Union[bytes, str], expected: str) -> bool:
        """Verify SHA3-256 hash."""
        hasher = ContentHasher(HashAlgorithm.SHA3_256)
        return hasher.verify(data, expected)
    
    @staticmethod
    def verify_blake2b(data: Union[bytes, str], expected: str) -> bool:
        """Verify BLAKE2b hash."""
        hasher = ContentHasher(HashAlgorithm.BLAKE2B)
        return hasher.verify(data, expected)
    
    @staticmethod
    def constant_time_compare(a: Union[bytes, str], b: Union[bytes, str]) -> bool:
        """Constant-time comparison to prevent timing attacks."""
        if isinstance(a, str):
            a = a.encode('utf-8')
        if isinstance(b, str):
            b = b.encode('utf-8')
        return hmac.compare_digest(a, b)


def hash_sha256(data: Union[bytes, str]) -> str:
    """Convenience function: SHA-256 hash."""
    return ContentHasher(HashAlgorithm.SHA256).hash(data)


def hash_sha3_256(data: Union[bytes, str]) -> str:
    """Convenience function: SHA3-256 hash."""
    return ContentHasher(HashAlgorithm.SHA3_256).hash(data)


def hash_password(password: str) -> str:
    """Convenience function: Hash a password."""
    return PasswordHasher().hash(password)


def verify_password(password: str, hash_str: str) -> bool:
    """Convenience function: Verify a password."""
    return PasswordHasher().verify(password, hash_str)


def create_hmac(key: bytes, message: Union[bytes, str]) -> str:
    """Convenience function: Create HMAC."""
    return HMACAuthenticator(key).sign(message)


def verify_hmac(key: bytes, message: Union[bytes, str], signature: str) -> bool:
    """Convenience function: Verify HMAC."""
    return HMACAuthenticator(key).verify(message, signature)
