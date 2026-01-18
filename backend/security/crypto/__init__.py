"""
GRACE Cryptographic Security System

Comprehensive cryptographic services including:
- Secure random generation
- Hashing (SHA-256, SHA-3, Argon2id)
- Key management (RSA, ECDSA, AES)
- Encryption (AES-GCM, RSA-OAEP, envelope)
- Digital signatures
- Certificate management
- Data integrity (Merkle trees, tamper detection)
"""

import logging

_logger = logging.getLogger(__name__)

# Random generation
try:
    from .random import (
        SecureRandom,
        TokenGenerator,
        NonceGenerator,
        SaltGenerator,
        IVGenerator,
        generate_secure_bytes,
        generate_token,
        generate_nonce,
        generate_salt,
    )
except ImportError as e:
    _logger.warning(f"Could not import random: {e}")
    SecureRandom = None
    TokenGenerator = None
    NonceGenerator = None
    SaltGenerator = None
    IVGenerator = None
    generate_secure_bytes = None
    generate_token = None
    generate_nonce = None
    generate_salt = None

# Hashing
try:
    from .hashing import (
        HashAlgorithm,
        Argon2Config,
        PasswordHasher,
        ContentHasher,
        HMACAuthenticator,
        HashVerifier,
        hash_sha256,
        hash_sha3_256,
        hash_password,
        verify_password,
        create_hmac,
        verify_hmac,
    )
except ImportError as e:
    _logger.warning(f"Could not import hashing: {e}")
    HashAlgorithm = None
    Argon2Config = None
    PasswordHasher = None
    ContentHasher = None
    HMACAuthenticator = None
    HashVerifier = None
    hash_sha256 = None
    hash_sha3_256 = None
    hash_password = None
    verify_password = None
    create_hmac = None
    verify_hmac = None

# Key management
try:
    from .keys import (
        KeyType,
        KeyUsage,
        KeyStatus,
        KeyMetadata,
        KeyPair,
        SymmetricKey,
        HSMInterface,
        SoftwareHSM,
        KeyGenerator,
        RotationPolicy,
        KeyRotationManager,
        KeyEscrow,
        KeyStore,
        KeyManager,
    )
except ImportError as e:
    _logger.warning(f"Could not import keys: {e}")
    KeyType = None
    KeyUsage = None
    KeyStatus = None
    KeyMetadata = None
    KeyPair = None
    SymmetricKey = None
    HSMInterface = None
    SoftwareHSM = None
    KeyGenerator = None
    RotationPolicy = None
    KeyRotationManager = None
    KeyEscrow = None
    KeyStore = None
    KeyManager = None

# Encryption
try:
    from .encryption import (
        EncryptionAlgorithm,
        EncryptedData,
        AESGCMEncryptor,
        RSAEncryptor,
        EnvelopeEncryptor,
        FieldEncryptor,
        SearchableEncryption,
        FormatPreservingEncryptor,
        EncryptionService,
        encrypt_aes_gcm,
        decrypt_aes_gcm,
        encrypt_envelope,
        decrypt_envelope,
    )
except ImportError as e:
    _logger.warning(f"Could not import encryption: {e}")
    EncryptionAlgorithm = None
    EncryptedData = None
    AESGCMEncryptor = None
    RSAEncryptor = None
    EnvelopeEncryptor = None
    FieldEncryptor = None
    SearchableEncryption = None
    FormatPreservingEncryptor = None
    EncryptionService = None
    encrypt_aes_gcm = None
    decrypt_aes_gcm = None
    encrypt_envelope = None
    decrypt_envelope = None

# Digital signatures
try:
    from .signing import (
        SignatureAlgorithm,
        SignatureStatus,
        Signature,
        SignedDocument,
        VerificationResult,
        DocumentSigner,
        CodeSigner,
        MultiPartySigner,
        AuditLogSigner,
        TimestampService,
        sign_document,
        verify_signature,
    )
except ImportError as e:
    _logger.warning(f"Could not import signing: {e}")
    SignatureAlgorithm = None
    SignatureStatus = None
    Signature = None
    SignedDocument = None
    VerificationResult = None
    DocumentSigner = None
    CodeSigner = None
    MultiPartySigner = None
    AuditLogSigner = None
    TimestampService = None
    sign_document = None
    verify_signature = None

# Certificate management
try:
    from .certificates import (
        CertificateType,
        CertificateStatus,
        KeyUsage as CertKeyUsage,
        ExtendedKeyUsage,
        CertificateSubject,
        CertificateInfo,
        CSRInfo,
        ValidationResult as CertValidationResult,
        CertificateGenerator,
        CertificateValidator,
        CertificateMonitor,
        RevocationChecker,
        generate_self_signed_cert,
        validate_certificate,
        generate_csr,
    )
except ImportError as e:
    _logger.warning(f"Could not import certificates: {e}")
    CertificateType = None
    CertificateStatus = None
    CertKeyUsage = None
    ExtendedKeyUsage = None
    CertificateSubject = None
    CertificateInfo = None
    CSRInfo = None
    CertValidationResult = None
    CertificateGenerator = None
    CertificateValidator = None
    CertificateMonitor = None
    RevocationChecker = None
    generate_self_signed_cert = None
    validate_certificate = None
    generate_csr = None

# Integrity
try:
    from .integrity import (
        MerkleNode,
        MerkleProof,
        MerkleTree,
        ContentAddressableStorage,
        TamperEvent,
        TamperDetector,
        AuditEntry,
        ImmutableAuditIntegration,
        create_merkle_tree,
        verify_merkle_proof,
        detect_tampering,
    )
except ImportError as e:
    _logger.warning(f"Could not import integrity: {e}")
    MerkleNode = None
    MerkleProof = None
    MerkleTree = None
    ContentAddressableStorage = None
    TamperEvent = None
    TamperDetector = None
    AuditEntry = None
    ImmutableAuditIntegration = None
    create_merkle_tree = None
    verify_merkle_proof = None
    detect_tampering = None

__all__ = [
    # Random
    "SecureRandom",
    "TokenGenerator",
    "NonceGenerator",
    "SaltGenerator",
    "IVGenerator",
    "generate_secure_bytes",
    "generate_token",
    "generate_nonce",
    "generate_salt",
    # Hashing
    "HashAlgorithm",
    "Argon2Config",
    "PasswordHasher",
    "ContentHasher",
    "HMACAuthenticator",
    "HashVerifier",
    "hash_sha256",
    "hash_sha3_256",
    "hash_password",
    "verify_password",
    "create_hmac",
    "verify_hmac",
    # Keys
    "KeyType",
    "KeyUsage",
    "KeyStatus",
    "KeyMetadata",
    "KeyPair",
    "SymmetricKey",
    "HSMInterface",
    "SoftwareHSM",
    "KeyGenerator",
    "RotationPolicy",
    "KeyRotationManager",
    "KeyEscrow",
    "KeyStore",
    "KeyManager",
    # Encryption
    "EncryptionAlgorithm",
    "EncryptedData",
    "AESGCMEncryptor",
    "RSAEncryptor",
    "EnvelopeEncryptor",
    "FieldEncryptor",
    "SearchableEncryption",
    "FormatPreservingEncryptor",
    "EncryptionService",
    "encrypt_aes_gcm",
    "decrypt_aes_gcm",
    "encrypt_envelope",
    "decrypt_envelope",
    # Signing
    "SignatureAlgorithm",
    "SignatureStatus",
    "Signature",
    "SignedDocument",
    "VerificationResult",
    "DocumentSigner",
    "CodeSigner",
    "MultiPartySigner",
    "AuditLogSigner",
    "TimestampService",
    "sign_document",
    "verify_signature",
    # Certificates
    "CertificateType",
    "CertificateStatus",
    "CertKeyUsage",
    "ExtendedKeyUsage",
    "CertificateSubject",
    "CertificateInfo",
    "CSRInfo",
    "CertValidationResult",
    "CertificateGenerator",
    "CertificateValidator",
    "CertificateMonitor",
    "RevocationChecker",
    "generate_self_signed_cert",
    "validate_certificate",
    "generate_csr",
    # Integrity
    "MerkleNode",
    "MerkleProof",
    "MerkleTree",
    "ContentAddressableStorage",
    "TamperEvent",
    "TamperDetector",
    "AuditEntry",
    "ImmutableAuditIntegration",
    "create_merkle_tree",
    "verify_merkle_proof",
    "detect_tampering",
]
