"""
GRACE Secrets Management System

Enterprise-grade secrets management with:
- Multi-backend vault (Local, HashiCorp, AWS, Azure)
- AES-256-GCM encryption at rest
- Argon2 key derivation
- Automatic secret rotation
- HSM support
- Immutable audit logging
"""

from .encryption import (
    AESGCMEncryption,
    EncryptedData,
    EncryptionError,
    DecryptionError,
    KeyDerivation,
    KeyDerivationError,
    EnvelopeEncryption,
    FieldEncryption,
    KeyProvider,
    SoftwareKeyProvider,
    HSMKeyProvider,
    create_encryption_key,
    derive_key_from_password,
    get_key_provider,
)

from .rotation import (
    SecretRotator,
    RotationScheduler,
    RotationPolicy,
    RotationRecord,
    RotationStatus,
    SecretType,
    SecretVersion,
    RotationHook,
    PreRotationValidator,
    PostRotationPropagator,
    get_secret_rotator,
    get_rotation_scheduler,
)

from .config import (
    SecretsConfig,
    get_secrets_config,
)

from .vault import (
    SecretsVault,
    SecretsBackend,
    LocalEncryptedBackend,
    HashiCorpVaultBackend,
    AWSSecretsBackend,
    AzureKeyVaultBackend,
    SecretEntry,
    SecretMetadata,
    get_secrets_vault,
)

__all__ = [
    # Encryption
    "AESGCMEncryption",
    "EncryptedData",
    "EncryptionError",
    "DecryptionError",
    "KeyDerivation",
    "KeyDerivationError",
    "EnvelopeEncryption",
    "FieldEncryption",
    "KeyProvider",
    "SoftwareKeyProvider",
    "HSMKeyProvider",
    "create_encryption_key",
    "derive_key_from_password",
    "get_key_provider",
    # Rotation
    "SecretRotator",
    "RotationScheduler",
    "RotationPolicy",
    "RotationRecord",
    "RotationStatus",
    "SecretType",
    "SecretVersion",
    "RotationHook",
    "PreRotationValidator",
    "PostRotationPropagator",
    "get_secret_rotator",
    "get_rotation_scheduler",
    # Config
    "SecretsConfig",
    "get_secrets_config",
    # Vault
    "SecretsVault",
    "SecretsBackend",
    "LocalEncryptedBackend",
    "HashiCorpVaultBackend",
    "AWSSecretsBackend",
    "AzureKeyVaultBackend",
    "SecretEntry",
    "SecretMetadata",
    "get_secrets_vault",
]
