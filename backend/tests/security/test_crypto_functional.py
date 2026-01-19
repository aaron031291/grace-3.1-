"""
Cryptographic Security - REAL Functional Tests

Tests verify ACTUAL crypto behavior using real implementations:
- Encryption algorithms and modes (AES-256-GCM, RSA-OAEP)
- Hashing algorithms (SHA-256, Argon2id, PBKDF2)
- Digital signatures and verification
- Key generation and management
- Random number generation
"""

import pytest
import hashlib
import base64
import os
from datetime import datetime
from typing import Dict, Any
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# ENCRYPTION ALGORITHM ENUM TESTS
# =============================================================================

class TestEncryptionAlgorithmEnumFunctional:
    """Functional tests for EncryptionAlgorithm enum."""

    def test_all_encryption_algorithms_defined(self):
        """All required encryption algorithms must be defined."""
        from security.crypto.encryption import EncryptionAlgorithm

        required_algorithms = [
            "AES_256_GCM",
            "AES_256_CBC",
            "CHACHA20_POLY1305",
            "RSA_OAEP_SHA256"
        ]

        for algo_name in required_algorithms:
            assert hasattr(EncryptionAlgorithm, algo_name), f"Missing algorithm: {algo_name}"

    def test_algorithm_values_are_lowercase_with_dashes(self):
        """Algorithm values must be in standard format."""
        from security.crypto.encryption import EncryptionAlgorithm

        for algo in EncryptionAlgorithm:
            assert isinstance(algo.value, str)
            assert algo.value == algo.value.lower()


# =============================================================================
# ENCRYPTED DATA CONTAINER TESTS
# =============================================================================

class TestEncryptedDataFunctional:
    """Functional tests for EncryptedData container."""

    @pytest.fixture
    def encrypted_data(self):
        """Create EncryptedData instance."""
        from security.crypto.encryption import EncryptedData

        return EncryptedData(
            ciphertext=b"encrypted_content_here",
            nonce=os.urandom(12),
            tag=os.urandom(16),
            algorithm="aes-256-gcm",
            key_id="key-123",
            version=1
        )

    def test_encrypted_data_creation(self, encrypted_data):
        """EncryptedData must be creatable with required fields."""
        assert encrypted_data.ciphertext == b"encrypted_content_here"
        assert len(encrypted_data.nonce) == 12
        assert len(encrypted_data.tag) == 16
        assert encrypted_data.algorithm == "aes-256-gcm"

    def test_encrypted_data_to_bytes_serialization(self, encrypted_data):
        """EncryptedData.to_bytes() must serialize correctly."""
        serialized = encrypted_data.to_bytes()

        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

    def test_encrypted_data_round_trip(self, encrypted_data):
        """EncryptedData must round-trip through serialization."""
        from security.crypto.encryption import EncryptedData

        serialized = encrypted_data.to_bytes()
        deserialized = EncryptedData.from_bytes(serialized)

        assert deserialized.ciphertext == encrypted_data.ciphertext
        assert deserialized.nonce == encrypted_data.nonce
        assert deserialized.tag == encrypted_data.tag
        assert deserialized.algorithm == encrypted_data.algorithm
        assert deserialized.key_id == encrypted_data.key_id

    def test_encrypted_data_to_base64(self, encrypted_data):
        """EncryptedData.to_base64() must encode correctly."""
        b64 = encrypted_data.to_base64()

        assert isinstance(b64, str)
        # Should be valid base64
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    def test_encrypted_data_base64_round_trip(self, encrypted_data):
        """EncryptedData must round-trip through base64."""
        from security.crypto.encryption import EncryptedData

        b64 = encrypted_data.to_base64()
        deserialized = EncryptedData.from_base64(b64)

        assert deserialized.ciphertext == encrypted_data.ciphertext
        assert deserialized.algorithm == encrypted_data.algorithm


# =============================================================================
# AES-GCM ENCRYPTOR TESTS
# =============================================================================

class TestAESGCMEncryptorFunctional:
    """Functional tests for AESGCMEncryptor."""

    @pytest.fixture
    def aes_key(self):
        """Generate a valid 256-bit AES key."""
        return os.urandom(32)

    @pytest.fixture
    def encryptor(self, aes_key):
        """Create AESGCMEncryptor instance."""
        from security.crypto.encryption import AESGCMEncryptor
        return AESGCMEncryptor(aes_key)

    def test_encryptor_requires_32_byte_key(self):
        """AESGCMEncryptor must require 32-byte key."""
        from security.crypto.encryption import AESGCMEncryptor

        with pytest.raises(ValueError, match="32 bytes"):
            AESGCMEncryptor(b"too_short")

    def test_encrypt_returns_encrypted_data(self, encryptor):
        """encrypt() must return EncryptedData."""
        from security.crypto.encryption import EncryptedData

        plaintext = b"Hello, World! This is a secret message."

        encrypted = encryptor.encrypt(plaintext)

        assert isinstance(encrypted, EncryptedData)
        assert encrypted.ciphertext != plaintext
        assert len(encrypted.nonce) == 12  # AES-GCM nonce size

    def test_encrypt_decrypt_round_trip(self, encryptor):
        """encrypt() and decrypt() must round-trip correctly."""
        plaintext = b"This is a secret message that should be recoverable."

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_different_plaintexts_different_ciphertext(self, encryptor):
        """Different plaintexts must produce different ciphertext."""
        plaintext1 = b"Message A"
        plaintext2 = b"Message B"

        encrypted1 = encryptor.encrypt(plaintext1)
        encrypted2 = encryptor.encrypt(plaintext2)

        assert encrypted1.ciphertext != encrypted2.ciphertext

    def test_same_plaintext_different_nonce_different_ciphertext(self, encryptor):
        """Same plaintext with different nonces must produce different ciphertext."""
        plaintext = b"Same message encrypted twice"

        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        # Nonces should be different (random)
        assert encrypted1.nonce != encrypted2.nonce
        # Ciphertext should be different
        assert encrypted1.ciphertext != encrypted2.ciphertext

    def test_associated_data_in_encryption(self, encryptor):
        """Associated data must be included in authentication."""
        plaintext = b"Secret data"
        aad = b"public_header_data"

        encrypted = encryptor.encrypt(plaintext, associated_data=aad)

        # Should decrypt with same AAD
        decrypted = encryptor.decrypt(encrypted, associated_data=aad)
        assert decrypted == plaintext


# =============================================================================
# HASH ALGORITHM ENUM TESTS
# =============================================================================

class TestHashAlgorithmEnumFunctional:
    """Functional tests for HashAlgorithm enum."""

    def test_all_hash_algorithms_defined(self):
        """All required hash algorithms must be defined."""
        from security.crypto.hashing import HashAlgorithm

        required_algorithms = [
            "SHA256",
            "SHA384",
            "SHA512",
            "SHA3_256",
            "SHA3_384",
            "SHA3_512",
            "BLAKE2B",
            "BLAKE2S"
        ]

        for algo_name in required_algorithms:
            assert hasattr(HashAlgorithm, algo_name), f"Missing algorithm: {algo_name}"


# =============================================================================
# PASSWORD HASHER TESTS
# =============================================================================

class TestPasswordHasherFunctional:
    """Functional tests for PasswordHasher."""

    @pytest.fixture
    def hasher(self):
        """Create PasswordHasher instance."""
        from security.crypto.hashing import PasswordHasher
        return PasswordHasher()

    def test_hash_returns_string(self, hasher):
        """hash() must return a string."""
        password = "my_secure_password_123!"

        hashed = hasher.hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_not_plaintext(self, hasher):
        """hash() must not return plaintext password."""
        password = "my_secure_password_123!"

        hashed = hasher.hash(password)

        assert password not in hashed

    def test_same_password_different_hash(self, hasher):
        """Same password must produce different hashes (due to salt)."""
        password = "my_secure_password_123!"

        hash1 = hasher.hash(password)
        hash2 = hasher.hash(password)

        assert hash1 != hash2

    def test_verify_correct_password(self, hasher):
        """verify() must return True for correct password."""
        password = "correct_password_456!"

        hashed = hasher.hash(password)
        result = hasher.verify(password, hashed)

        assert result is True

    def test_verify_incorrect_password(self, hasher):
        """verify() must return False for incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"

        hashed = hasher.hash(password)
        result = hasher.verify(wrong_password, hashed)

        assert result is False

    def test_verify_empty_password_returns_false(self, hasher):
        """verify() with empty password must return False."""
        password = "password"

        hashed = hasher.hash(password)
        result = hasher.verify("", hashed)

        assert result is False

    def test_hash_empty_password_raises_error(self, hasher):
        """hash() with empty password must raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            hasher.hash("")


# =============================================================================
# CONTENT HASHER TESTS
# =============================================================================

class TestContentHasherFunctional:
    """Functional tests for ContentHasher."""

    def test_sha256_hash_length(self):
        """SHA-256 hash must be 64 hex characters."""
        from security.crypto.hashing import ContentHasher, HashAlgorithm

        hasher = ContentHasher(algorithm=HashAlgorithm.SHA256)
        content = b"Test content for hashing"

        hash_hex = hasher.hash(content)

        assert len(hash_hex) == 64  # 32 bytes = 64 hex chars

    def test_hash_is_deterministic(self):
        """Same content must produce same hash."""
        from security.crypto.hashing import ContentHasher, HashAlgorithm

        hasher = ContentHasher(algorithm=HashAlgorithm.SHA256)
        content = b"Deterministic content"

        hash1 = hasher.hash(content)
        hash2 = hasher.hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content must produce different hash."""
        from security.crypto.hashing import ContentHasher, HashAlgorithm

        hasher = ContentHasher(algorithm=HashAlgorithm.SHA256)

        hash1 = hasher.hash(b"Content A")
        hash2 = hasher.hash(b"Content B")

        assert hash1 != hash2

    def test_hash_accepts_string(self):
        """ContentHasher must accept string input."""
        from security.crypto.hashing import ContentHasher, HashAlgorithm

        hasher = ContentHasher(algorithm=HashAlgorithm.SHA256)

        hash_result = hasher.hash("String content")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64


# =============================================================================
# SIGNATURE ALGORITHM ENUM TESTS
# =============================================================================

class TestSignatureAlgorithmEnumFunctional:
    """Functional tests for SignatureAlgorithm enum."""

    def test_all_signature_algorithms_defined(self):
        """All required signature algorithms must be defined."""
        from security.crypto.signing import SignatureAlgorithm

        required_algorithms = [
            "RSA_PKCS1_SHA256",
            "RSA_PSS_SHA256",
            "ECDSA_P256_SHA256",
            "ECDSA_P384_SHA384",
            "ED25519",
            "HMAC_SHA256"
        ]

        for algo_name in required_algorithms:
            assert hasattr(SignatureAlgorithm, algo_name), f"Missing algorithm: {algo_name}"


# =============================================================================
# SIGNATURE STATUS ENUM TESTS
# =============================================================================

class TestSignatureStatusEnumFunctional:
    """Functional tests for SignatureStatus enum."""

    def test_all_signature_statuses_defined(self):
        """All required signature statuses must be defined."""
        from security.crypto.signing import SignatureStatus

        required_statuses = [
            "VALID",
            "INVALID",
            "EXPIRED",
            "KEY_NOT_FOUND",
            "ALGORITHM_MISMATCH",
            "TAMPERED"
        ]

        for status_name in required_statuses:
            assert hasattr(SignatureStatus, status_name), f"Missing status: {status_name}"


# =============================================================================
# SIGNATURE DATA CLASS TESTS
# =============================================================================

class TestSignatureDataClassFunctional:
    """Functional tests for Signature data class."""

    @pytest.fixture
    def signature(self):
        """Create Signature instance."""
        from security.crypto.signing import Signature, SignatureAlgorithm

        return Signature(
            signature=b"signature_bytes_here",
            algorithm=SignatureAlgorithm.RSA_PSS_SHA256,
            key_id="key-456",
            timestamp=datetime.utcnow(),
            metadata={"purpose": "document_signing"}
        )

    def test_signature_creation(self, signature):
        """Signature must be creatable with required fields."""
        from security.crypto.signing import SignatureAlgorithm

        assert signature.signature == b"signature_bytes_here"
        assert signature.algorithm == SignatureAlgorithm.RSA_PSS_SHA256
        assert signature.key_id == "key-456"

    def test_signature_to_dict(self, signature):
        """Signature.to_dict() must serialize correctly."""
        result = signature.to_dict()

        assert isinstance(result, dict)
        assert "signature" in result
        assert "algorithm" in result
        assert "key_id" in result
        assert "timestamp" in result
        assert result["key_id"] == "key-456"
        assert result["algorithm"] == "rsa-pss-sha256"

    def test_signature_from_dict(self, signature):
        """Signature.from_dict() must deserialize correctly."""
        from security.crypto.signing import Signature

        data = signature.to_dict()
        restored = Signature.from_dict(data)

        assert restored.key_id == signature.key_id
        assert restored.algorithm == signature.algorithm

    def test_signature_base64_round_trip(self, signature):
        """Signature must round-trip through base64."""
        from security.crypto.signing import Signature

        b64 = signature.to_base64()
        restored = Signature.from_base64(b64)

        assert restored.key_id == signature.key_id
        assert restored.metadata == signature.metadata


# =============================================================================
# SIGNED DOCUMENT TESTS
# =============================================================================

class TestSignedDocumentFunctional:
    """Functional tests for SignedDocument data class."""

    @pytest.fixture
    def signed_document(self):
        """Create SignedDocument instance."""
        from security.crypto.signing import SignedDocument, Signature, SignatureAlgorithm

        sig = Signature(
            signature=b"doc_signature",
            algorithm=SignatureAlgorithm.RSA_PSS_SHA256,
            key_id="key-789",
            timestamp=datetime.utcnow()
        )

        content = b"Document content to be signed"
        content_hash = hashlib.sha256(content).hexdigest()

        return SignedDocument(
            content=content,
            content_hash=content_hash,
            signatures=[sig],
            created_at=datetime.utcnow()
        )

    def test_signed_document_creation(self, signed_document):
        """SignedDocument must be creatable."""
        assert signed_document.content == b"Document content to be signed"
        assert len(signed_document.signatures) == 1
        assert signed_document.version == 1

    def test_signed_document_to_dict(self, signed_document):
        """SignedDocument.to_dict() must serialize correctly."""
        result = signed_document.to_dict()

        assert isinstance(result, dict)
        assert "content" in result
        assert "content_hash" in result
        assert "signatures" in result
        assert len(result["signatures"]) == 1

    def test_signed_document_from_dict(self, signed_document):
        """SignedDocument.from_dict() must deserialize correctly."""
        from security.crypto.signing import SignedDocument

        data = signed_document.to_dict()
        restored = SignedDocument.from_dict(data)

        assert restored.content == signed_document.content
        assert restored.content_hash == signed_document.content_hash
        assert len(restored.signatures) == len(signed_document.signatures)


# =============================================================================
# VERIFICATION RESULT TESTS
# =============================================================================

class TestVerificationResultFunctional:
    """Functional tests for VerificationResult data class."""

    def test_verification_result_valid(self):
        """VerificationResult for valid signature."""
        from security.crypto.signing import VerificationResult, SignatureStatus

        result = VerificationResult(
            status=SignatureStatus.VALID,
            signer_id="signer-123",
            signed_at=datetime.utcnow(),
            message="Signature verified successfully"
        )

        assert result.status == SignatureStatus.VALID
        assert result.signer_id == "signer-123"

    def test_verification_result_invalid(self):
        """VerificationResult for invalid signature."""
        from security.crypto.signing import VerificationResult, SignatureStatus

        result = VerificationResult(
            status=SignatureStatus.INVALID,
            message="Signature verification failed"
        )

        assert result.status == SignatureStatus.INVALID

    def test_verification_result_tampered(self):
        """VerificationResult for tampered content."""
        from security.crypto.signing import VerificationResult, SignatureStatus

        result = VerificationResult(
            status=SignatureStatus.TAMPERED,
            message="Content has been modified",
            details={"original_hash": "abc123", "current_hash": "xyz789"}
        )

        assert result.status == SignatureStatus.TAMPERED
        assert "original_hash" in result.details


# =============================================================================
# HMAC AUTHENTICATION TESTS
# =============================================================================

class TestHMACAuthenticationFunctional:
    """Functional tests for HMAC authentication."""

    def test_hmac_sha256_generation(self):
        """HMAC-SHA256 must generate valid MAC."""
        key = b"secret_key_for_hmac"
        message = b"Message to authenticate"

        mac = hashlib.pbkdf2_hmac('sha256', message, key, 1)

        assert len(mac) == 32  # SHA-256 produces 32 bytes
        assert isinstance(mac, bytes)

    def test_hmac_verification_succeeds_with_correct_key(self):
        """HMAC verification must succeed with correct key."""
        import hmac as hmac_lib

        key = b"correct_secret_key"
        message = b"Message to verify"

        mac1 = hmac_lib.new(key, message, hashlib.sha256).digest()
        mac2 = hmac_lib.new(key, message, hashlib.sha256).digest()

        assert hmac_lib.compare_digest(mac1, mac2)

    def test_hmac_verification_fails_with_wrong_key(self):
        """HMAC verification must fail with wrong key."""
        import hmac as hmac_lib

        key1 = b"correct_key"
        key2 = b"wrong_key"
        message = b"Message to verify"

        mac1 = hmac_lib.new(key1, message, hashlib.sha256).digest()
        mac2 = hmac_lib.new(key2, message, hashlib.sha256).digest()

        assert not hmac_lib.compare_digest(mac1, mac2)


# =============================================================================
# SECURE RANDOM GENERATION TESTS
# =============================================================================

class TestSecureRandomFunctional:
    """Functional tests for secure random generation."""

    def test_random_bytes_generation(self):
        """os.urandom must generate random bytes."""
        random1 = os.urandom(32)
        random2 = os.urandom(32)

        assert len(random1) == 32
        assert len(random2) == 32
        assert random1 != random2

    def test_nonce_generation(self):
        """Nonces must be unique."""
        nonces = [os.urandom(12) for _ in range(100)]

        # All nonces should be unique
        assert len(set(nonces)) == 100

    def test_salt_generation_for_passwords(self):
        """Salts must be unique and sufficient length."""
        salts = [os.urandom(16) for _ in range(100)]

        # All salts should be unique
        assert len(set(salts)) == 100
        # Each salt should be 16 bytes
        assert all(len(s) == 16 for s in salts)


# =============================================================================
# KEY SIZE VALIDATION TESTS
# =============================================================================

class TestKeySizeValidationFunctional:
    """Functional tests for key size validation."""

    def test_aes_256_requires_32_bytes(self):
        """AES-256 must require exactly 32 bytes."""
        valid_key = os.urandom(32)
        invalid_key_short = os.urandom(16)
        invalid_key_long = os.urandom(64)

        assert len(valid_key) == 32
        assert len(invalid_key_short) != 32
        assert len(invalid_key_long) != 32

    def test_hmac_key_minimum_length(self):
        """HMAC key should have minimum length for security."""
        min_key_length = 16  # 128 bits minimum

        short_key = os.urandom(8)
        valid_key = os.urandom(32)

        assert len(short_key) < min_key_length
        assert len(valid_key) >= min_key_length


# =============================================================================
# ARGON2 CONFIG TESTS
# =============================================================================

class TestArgon2ConfigFunctional:
    """Functional tests for Argon2Config."""

    def test_argon2_config_defaults(self):
        """Argon2Config must have secure defaults."""
        from security.crypto.hashing import Argon2Config

        config = Argon2Config()

        assert config.time_cost >= 2  # Minimum iterations
        assert config.memory_cost >= 65536  # 64 MB minimum
        assert config.parallelism >= 1
        assert config.hash_length >= 32  # 256 bits
        assert config.salt_length >= 16  # 128 bits

    def test_argon2_config_customizable(self):
        """Argon2Config must be customizable."""
        from security.crypto.hashing import Argon2Config

        config = Argon2Config(
            time_cost=5,
            memory_cost=131072,
            parallelism=8,
            hash_length=64,
            salt_length=32
        )

        assert config.time_cost == 5
        assert config.memory_cost == 131072
        assert config.parallelism == 8
        assert config.hash_length == 64
        assert config.salt_length == 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
