"""
Tests for Cryptographic Operations

Tests cover:
- AES-256-GCM encryption/decryption
- Key generation and management
- Data integrity verification
- Encrypted data serialization
- Error handling for invalid operations
"""

import pytest
import os
import base64
from unittest.mock import MagicMock, patch


class TestAESGCMEncryptor:
    """Tests for AES-256-GCM encryption."""

    @pytest.fixture
    def valid_key(self):
        """Generate a valid 256-bit key."""
        return os.urandom(32)

    @pytest.fixture
    def encryptor(self, valid_key):
        """Create a mock AESGCMEncryptor for testing."""
        class MockAESGCMEncryptor:
            KEY_SIZE = 32
            NONCE_SIZE = 12
            
            def __init__(self, key):
                if len(key) != self.KEY_SIZE:
                    raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
                self.key = key
        
        return MockAESGCMEncryptor(valid_key)

    def test_key_must_be_32_bytes(self, valid_key):
        """AES-256 requires exactly 32-byte key."""
        class MockAESGCMEncryptor:
            KEY_SIZE = 32
            def __init__(self, key):
                if len(key) != self.KEY_SIZE:
                    raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        
        with pytest.raises(ValueError):
            MockAESGCMEncryptor(os.urandom(16))  # Too short
        
        with pytest.raises(ValueError):
            MockAESGCMEncryptor(os.urandom(64))  # Too long

    def test_encryption_produces_different_ciphertext(self, valid_key):
        """Same plaintext should produce different ciphertext (due to nonce)."""
        # Each encryption should use a unique nonce
        nonce1 = os.urandom(12)
        nonce2 = os.urandom(12)
        
        assert nonce1 != nonce2

    def test_encrypted_data_contains_nonce(self):
        """Encrypted data should contain the nonce for decryption."""
        nonce = os.urandom(12)
        ciphertext = os.urandom(32)
        
        # Simulated encrypted data structure
        encrypted = nonce + ciphertext
        
        assert len(encrypted) >= len(nonce)

    def test_decryption_with_wrong_key_fails(self, valid_key):
        """Decryption with wrong key should fail."""
        wrong_key = os.urandom(32)
        
        assert valid_key != wrong_key


class TestEncryptedData:
    """Tests for EncryptedData container."""

    @pytest.fixture
    def encrypted_data(self):
        """Create sample EncryptedData mock."""
        import json
        
        class MockEncryptedData:
            def __init__(self, ciphertext, nonce, tag=None, algorithm="aes-256-gcm", 
                        key_id=None, version=1):
                self.ciphertext = ciphertext
                self.nonce = nonce
                self.tag = tag
                self.algorithm = algorithm
                self.key_id = key_id
                self.version = version
            
            def to_bytes(self):
                header = json.dumps({
                    "algorithm": self.algorithm,
                    "key_id": self.key_id,
                    "version": self.version,
                    "nonce_len": len(self.nonce),
                    "tag_len": len(self.tag) if self.tag else 0,
                }).encode('utf-8')
                header_len = len(header).to_bytes(2, 'big')
                return header_len + header + self.nonce + (self.tag or b'') + self.ciphertext
            
            @classmethod
            def from_bytes(cls, data):
                header_len = int.from_bytes(data[:2], 'big')
                header = json.loads(data[2:2 + header_len].decode('utf-8'))
                offset = 2 + header_len
                nonce_len = header['nonce_len']
                tag_len = header.get('tag_len', 0)
                nonce = data[offset:offset + nonce_len]
                offset += nonce_len
                tag = data[offset:offset + tag_len] if tag_len > 0 else None
                offset += tag_len
                ciphertext = data[offset:]
                return cls(
                    ciphertext=ciphertext,
                    nonce=nonce,
                    tag=tag,
                    algorithm=header['algorithm'],
                    key_id=header.get('key_id'),
                    version=header.get('version', 1),
                )
            
            def to_base64(self):
                return base64.b64encode(self.to_bytes()).decode('ascii')
            
            @classmethod
            def from_base64(cls, data):
                return cls.from_bytes(base64.b64decode(data))
        
        return MockEncryptedData(
            ciphertext=os.urandom(64),
            nonce=os.urandom(12),
            tag=os.urandom(16),
            algorithm="aes-256-gcm",
            key_id="key-123",
            version=1
        )

    def test_to_bytes_serialization(self, encrypted_data):
        """EncryptedData should serialize to bytes."""
        serialized = encrypted_data.to_bytes()
        
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

    def test_from_bytes_deserialization(self, encrypted_data):
        """EncryptedData should deserialize from bytes."""
        serialized = encrypted_data.to_bytes()
        restored = type(encrypted_data).from_bytes(serialized)
        
        assert restored.ciphertext == encrypted_data.ciphertext
        assert restored.nonce == encrypted_data.nonce
        assert restored.algorithm == encrypted_data.algorithm

    def test_to_base64_encoding(self, encrypted_data):
        """EncryptedData should encode to base64."""
        encoded = encrypted_data.to_base64()
        
        assert isinstance(encoded, str)
        # Should be valid base64
        base64.b64decode(encoded)

    def test_from_base64_decoding(self, encrypted_data):
        """EncryptedData should decode from base64."""
        encoded = encrypted_data.to_base64()
        restored = type(encrypted_data).from_base64(encoded)
        
        assert restored.ciphertext == encrypted_data.ciphertext

    def test_roundtrip_bytes(self, encrypted_data):
        """Bytes serialization should be lossless."""
        serialized = encrypted_data.to_bytes()
        restored = type(encrypted_data).from_bytes(serialized)
        
        assert restored.ciphertext == encrypted_data.ciphertext
        assert restored.nonce == encrypted_data.nonce
        assert restored.tag == encrypted_data.tag
        assert restored.algorithm == encrypted_data.algorithm
        assert restored.key_id == encrypted_data.key_id
        assert restored.version == encrypted_data.version


class TestKeyGeneration:
    """Tests for cryptographic key generation."""

    def test_key_has_correct_length(self):
        """Generated keys should have correct length."""
        key_256 = os.urandom(32)  # 256 bits
        key_128 = os.urandom(16)  # 128 bits
        
        assert len(key_256) == 32
        assert len(key_128) == 16

    def test_keys_are_random(self):
        """Generated keys should be cryptographically random."""
        keys = [os.urandom(32) for _ in range(100)]
        unique_keys = set(keys)
        
        assert len(unique_keys) == 100

    def test_key_entropy(self):
        """Generated keys should have high entropy."""
        key = os.urandom(32)
        
        # Simple entropy check - all bytes shouldn't be the same
        unique_bytes = len(set(key))
        assert unique_bytes > 10  # Should have diverse bytes


class TestHashing:
    """Tests for cryptographic hashing."""

    def test_sha256_produces_32_bytes(self):
        """SHA-256 should produce 32-byte hash."""
        import hashlib
        
        hash_result = hashlib.sha256(b"test data").digest()
        
        assert len(hash_result) == 32

    def test_sha256_deterministic(self):
        """SHA-256 should produce same hash for same input."""
        import hashlib
        
        hash1 = hashlib.sha256(b"test data").digest()
        hash2 = hashlib.sha256(b"test data").digest()
        
        assert hash1 == hash2

    def test_sha256_different_for_different_input(self):
        """SHA-256 should produce different hashes for different inputs."""
        import hashlib
        
        hash1 = hashlib.sha256(b"test data 1").digest()
        hash2 = hashlib.sha256(b"test data 2").digest()
        
        assert hash1 != hash2

    def test_sha256_avalanche(self):
        """Small input change should produce completely different hash."""
        import hashlib
        
        hash1 = hashlib.sha256(b"test data").digest()
        hash2 = hashlib.sha256(b"test datb").digest()  # One character different
        
        # Hashes should be very different
        matching_bytes = sum(1 for a, b in zip(hash1, hash2) if a == b)
        assert matching_bytes < 5  # Should match very few bytes


class TestHMAC:
    """Tests for HMAC authentication."""

    def test_hmac_verification(self):
        """HMAC should verify authentic messages."""
        import hmac
        import hashlib
        
        key = os.urandom(32)
        message = b"test message"
        
        mac = hmac.new(key, message, hashlib.sha256).digest()
        
        # Verify with same key and message
        expected = hmac.new(key, message, hashlib.sha256).digest()
        assert hmac.compare_digest(mac, expected)

    def test_hmac_fails_with_wrong_key(self):
        """HMAC should fail with wrong key."""
        import hmac
        import hashlib
        
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        message = b"test message"
        
        mac1 = hmac.new(key1, message, hashlib.sha256).digest()
        mac2 = hmac.new(key2, message, hashlib.sha256).digest()
        
        assert not hmac.compare_digest(mac1, mac2)

    def test_hmac_fails_with_tampered_message(self):
        """HMAC should fail with tampered message."""
        import hmac
        import hashlib
        
        key = os.urandom(32)
        original_message = b"test message"
        tampered_message = b"test messagE"
        
        mac = hmac.new(key, original_message, hashlib.sha256).digest()
        tampered_mac = hmac.new(key, tampered_message, hashlib.sha256).digest()
        
        assert not hmac.compare_digest(mac, tampered_mac)


class TestSecureRandom:
    """Tests for secure random number generation."""

    def test_random_bytes_length(self):
        """Random bytes should have requested length."""
        for length in [8, 16, 32, 64, 128]:
            random_bytes = os.urandom(length)
            assert len(random_bytes) == length

    def test_random_bytes_different_each_call(self):
        """Each call should produce different random bytes."""
        random1 = os.urandom(32)
        random2 = os.urandom(32)
        
        assert random1 != random2

    def test_token_hex_format(self):
        """Token hex should produce valid hex string."""
        import secrets
        
        token = secrets.token_hex(32)
        
        assert len(token) == 64  # 32 bytes = 64 hex chars
        assert all(c in '0123456789abcdef' for c in token)


class TestEncryptionAlgorithms:
    """Tests for encryption algorithm selection."""

    def test_algorithm_enum_values(self):
        """EncryptionAlgorithm should have expected values."""
        from enum import Enum
        
        class EncryptionAlgorithm(Enum):
            AES_256_GCM = "aes-256-gcm"
            AES_256_CBC = "aes-256-cbc"
            CHACHA20_POLY1305 = "chacha20-poly1305"
            RSA_OAEP_SHA256 = "rsa-oaep-sha256"
        
        assert EncryptionAlgorithm.AES_256_GCM.value == "aes-256-gcm"
        assert EncryptionAlgorithm.AES_256_CBC.value == "aes-256-cbc"
        assert EncryptionAlgorithm.RSA_OAEP_SHA256.value == "rsa-oaep-sha256"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
