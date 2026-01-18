"""
Encryption Utilities for GRACE Secrets Management

Provides:
- AES-256-GCM encryption at rest
- Key derivation with Argon2
- Envelope encryption pattern
- HSM support for secure key storage
- Field-level encryption for database columns
"""

import os
import json
import base64
import hashlib
import logging
import struct
from typing import Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography library not available - encryption disabled")

try:
    from argon2 import PasswordHasher
    from argon2.low_level import hash_secret_raw, Type
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    logger.warning("argon2-cffi library not available - using PBKDF2 fallback")


class EncryptionError(Exception):
    """Base encryption error."""
    pass


class DecryptionError(Exception):
    """Decryption failed error."""
    pass


class KeyDerivationError(Exception):
    """Key derivation failed error."""
    pass


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes
    algorithm: str = "aes-256-gcm"
    version: int = 1
    key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    associated_data: Optional[bytes] = None
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        header = struct.pack(
            '>BH12s',
            self.version,
            len(self.ciphertext),
            self.nonce
        )
        return header + self.ciphertext
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedData":
        """Deserialize from bytes."""
        version, ct_len, nonce = struct.unpack('>BH12s', data[:15])
        ciphertext = data[15:15 + ct_len]
        return cls(
            ciphertext=ciphertext,
            nonce=nonce,
            version=version
        )
    
    def to_base64(self) -> str:
        """Encode as base64 string."""
        return base64.urlsafe_b64encode(self.to_bytes()).decode('utf-8')
    
    @classmethod
    def from_base64(cls, data: str) -> "EncryptedData":
        """Decode from base64 string."""
        return cls.from_bytes(base64.urlsafe_b64decode(data))


class KeyDerivation:
    """
    Key derivation utilities.
    
    Supports Argon2id (preferred) with PBKDF2 fallback.
    """
    
    DEFAULT_SALT_SIZE = 16
    DEFAULT_KEY_SIZE = 32
    
    ARGON2_TIME_COST = 3
    ARGON2_MEMORY_COST = 65536
    ARGON2_PARALLELISM = 4
    
    PBKDF2_ITERATIONS = 600000
    
    @classmethod
    def derive_key(
        cls,
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        key_size: int = DEFAULT_KEY_SIZE
    ) -> Tuple[bytes, bytes]:
        """
        Derive a key from password using Argon2id or PBKDF2.
        
        Args:
            password: Password or passphrase
            salt: Optional salt (generated if not provided)
            key_size: Desired key size in bytes
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if salt is None:
            salt = os.urandom(cls.DEFAULT_SALT_SIZE)
        
        if ARGON2_AVAILABLE:
            return cls._derive_argon2(password, salt, key_size)
        else:
            return cls._derive_pbkdf2(password, salt, key_size)
    
    @classmethod
    def _derive_argon2(
        cls,
        password: bytes,
        salt: bytes,
        key_size: int
    ) -> Tuple[bytes, bytes]:
        """Derive key using Argon2id."""
        try:
            key = hash_secret_raw(
                secret=password,
                salt=salt,
                time_cost=cls.ARGON2_TIME_COST,
                memory_cost=cls.ARGON2_MEMORY_COST,
                parallelism=cls.ARGON2_PARALLELISM,
                hash_len=key_size,
                type=Type.ID
            )
            return key, salt
        except Exception as e:
            raise KeyDerivationError(f"Argon2 key derivation failed: {e}")
    
    @classmethod
    def _derive_pbkdf2(
        cls,
        password: bytes,
        salt: bytes,
        key_size: int
    ) -> Tuple[bytes, bytes]:
        """Derive key using PBKDF2-SHA256 (fallback)."""
        if not CRYPTOGRAPHY_AVAILABLE:
            raise KeyDerivationError("No cryptographic library available")
        
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=key_size,
                salt=salt,
                iterations=cls.PBKDF2_ITERATIONS,
                backend=default_backend()
            )
            key = kdf.derive(password)
            return key, salt
        except Exception as e:
            raise KeyDerivationError(f"PBKDF2 key derivation failed: {e}")
    
    @classmethod
    def derive_key_from_components(
        cls,
        *components: bytes,
        context: bytes = b"grace-key-derivation"
    ) -> bytes:
        """
        Derive a key from multiple components using HKDF-like construction.
        
        Useful for combining multiple key shares or deriving sub-keys.
        """
        combined = b''.join(components) + context
        return hashlib.sha256(combined).digest()


class AESGCMEncryption:
    """
    AES-256-GCM authenticated encryption.
    
    Provides:
    - Confidentiality (encryption)
    - Integrity (authentication tag)
    - Associated data authentication
    """
    
    KEY_SIZE = 32
    NONCE_SIZE = 12
    TAG_SIZE = 16
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with optional key.
        
        Args:
            key: 32-byte AES key (generated if not provided)
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise EncryptionError("cryptography library not available")
        
        if key is None:
            key = os.urandom(self.KEY_SIZE)
        elif len(key) != self.KEY_SIZE:
            raise EncryptionError(f"Key must be {self.KEY_SIZE} bytes")
        
        self._key = key
        self._cipher = AESGCM(key)
    
    @property
    def key(self) -> bytes:
        """Get the encryption key."""
        return self._key
    
    def encrypt(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None
    ) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data (AAD)
            
        Returns:
            EncryptedData container
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        nonce = os.urandom(self.NONCE_SIZE)
        
        try:
            ciphertext = self._cipher.encrypt(nonce, plaintext, associated_data)
            return EncryptedData(
                ciphertext=ciphertext,
                nonce=nonce,
                algorithm="aes-256-gcm",
                associated_data=associated_data
            )
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(
        self,
        encrypted: EncryptedData,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            encrypted: EncryptedData container
            associated_data: Must match AAD used during encryption
            
        Returns:
            Decrypted plaintext bytes
        """
        aad = associated_data or encrypted.associated_data
        
        try:
            return self._cipher.decrypt(
                encrypted.nonce,
                encrypted.ciphertext,
                aad
            )
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_string(
        self,
        plaintext: str,
        associated_data: Optional[bytes] = None
    ) -> str:
        """Encrypt string and return base64-encoded result."""
        encrypted = self.encrypt(plaintext, associated_data)
        return encrypted.to_base64()
    
    def decrypt_string(
        self,
        ciphertext: str,
        associated_data: Optional[bytes] = None
    ) -> str:
        """Decrypt base64-encoded ciphertext to string."""
        encrypted = EncryptedData.from_base64(ciphertext)
        return self.decrypt(encrypted, associated_data).decode('utf-8')


class EnvelopeEncryption:
    """
    Envelope encryption pattern.
    
    Uses a Key Encryption Key (KEK) to wrap Data Encryption Keys (DEK).
    This allows:
    - Efficient key rotation (only re-wrap DEKs, not re-encrypt data)
    - Separation of key management from data encryption
    - Support for HSM-protected KEKs
    """
    
    def __init__(
        self,
        kek: Optional[bytes] = None,
        kek_provider: Optional["KeyProvider"] = None
    ):
        """
        Initialize envelope encryption.
        
        Args:
            kek: Key Encryption Key (32 bytes)
            kek_provider: Optional key provider for HSM support
        """
        if kek_provider:
            self._kek_provider = kek_provider
            self._kek = None
        elif kek:
            self._kek = kek
            self._kek_provider = None
        else:
            self._kek = os.urandom(32)
            self._kek_provider = None
    
    def _get_kek(self) -> bytes:
        """Get the Key Encryption Key."""
        if self._kek_provider:
            return self._kek_provider.get_key()
        return self._kek
    
    def wrap_key(self, dek: bytes, key_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Wrap a Data Encryption Key with the KEK.
        
        Args:
            dek: Data Encryption Key to wrap
            key_id: Optional identifier for the wrapped key
            
        Returns:
            Wrapped key envelope
        """
        kek_cipher = AESGCMEncryption(self._get_kek())
        
        aad = key_id.encode() if key_id else None
        encrypted = kek_cipher.encrypt(dek, aad)
        
        return {
            "wrapped_key": base64.urlsafe_b64encode(encrypted.ciphertext).decode(),
            "nonce": base64.urlsafe_b64encode(encrypted.nonce).decode(),
            "key_id": key_id,
            "algorithm": "aes-256-gcm",
            "wrapped_at": datetime.utcnow().isoformat()
        }
    
    def unwrap_key(self, envelope: Dict[str, Any]) -> bytes:
        """
        Unwrap a Data Encryption Key.
        
        Args:
            envelope: Wrapped key envelope
            
        Returns:
            Unwrapped DEK bytes
        """
        kek_cipher = AESGCMEncryption(self._get_kek())
        
        key_id = envelope.get("key_id")
        aad = key_id.encode() if key_id else None
        
        encrypted = EncryptedData(
            ciphertext=base64.urlsafe_b64decode(envelope["wrapped_key"]),
            nonce=base64.urlsafe_b64decode(envelope["nonce"]),
            associated_data=aad
        )
        
        return kek_cipher.decrypt(encrypted, aad)
    
    def encrypt_with_envelope(
        self,
        plaintext: Union[str, bytes],
        key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Encrypt data using envelope encryption.
        
        Generates a new DEK, encrypts data, then wraps the DEK.
        
        Returns:
            Dictionary with wrapped key and encrypted data
        """
        dek = os.urandom(32)
        data_cipher = AESGCMEncryption(dek)
        
        encrypted_data = data_cipher.encrypt(plaintext)
        wrapped_key = self.wrap_key(dek, key_id)
        
        return {
            "wrapped_key": wrapped_key,
            "ciphertext": base64.urlsafe_b64encode(encrypted_data.ciphertext).decode(),
            "nonce": base64.urlsafe_b64encode(encrypted_data.nonce).decode(),
            "algorithm": "envelope-aes-256-gcm"
        }
    
    def decrypt_with_envelope(self, envelope: Dict[str, Any]) -> bytes:
        """
        Decrypt data using envelope encryption.
        
        Unwraps the DEK, then decrypts the data.
        """
        dek = self.unwrap_key(envelope["wrapped_key"])
        data_cipher = AESGCMEncryption(dek)
        
        encrypted = EncryptedData(
            ciphertext=base64.urlsafe_b64decode(envelope["ciphertext"]),
            nonce=base64.urlsafe_b64decode(envelope["nonce"])
        )
        
        return data_cipher.decrypt(encrypted)


class KeyProvider(ABC):
    """Abstract base class for key providers (HSM, KMS, etc.)."""
    
    @abstractmethod
    def get_key(self, key_id: Optional[str] = None) -> bytes:
        """Get a key from the provider."""
        pass
    
    @abstractmethod
    def wrap_key(self, key: bytes, key_id: Optional[str] = None) -> bytes:
        """Wrap a key using the provider's master key."""
        pass
    
    @abstractmethod
    def unwrap_key(self, wrapped_key: bytes, key_id: Optional[str] = None) -> bytes:
        """Unwrap a key using the provider's master key."""
        pass


class SoftwareKeyProvider(KeyProvider):
    """Software-based key provider using local encrypted storage."""
    
    def __init__(
        self,
        master_key: Optional[bytes] = None,
        key_file: Optional[str] = None
    ):
        if master_key:
            self._master_key = master_key
        elif key_file and os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self._master_key = f.read()
        else:
            self._master_key = os.urandom(32)
            if key_file:
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(self._master_key)
                os.chmod(key_file, 0o600)
        
        self._cipher = AESGCMEncryption(self._master_key)
    
    def get_key(self, key_id: Optional[str] = None) -> bytes:
        """Get the master key."""
        return self._master_key
    
    def wrap_key(self, key: bytes, key_id: Optional[str] = None) -> bytes:
        """Wrap a key with the master key."""
        encrypted = self._cipher.encrypt(key, key_id.encode() if key_id else None)
        return encrypted.to_bytes()
    
    def unwrap_key(self, wrapped_key: bytes, key_id: Optional[str] = None) -> bytes:
        """Unwrap a key with the master key."""
        encrypted = EncryptedData.from_bytes(wrapped_key)
        return self._cipher.decrypt(encrypted, key_id.encode() if key_id else None)


class HSMKeyProvider(KeyProvider):
    """
    HSM-based key provider using PKCS#11.
    
    Requires PyKCS11 library and properly configured HSM.
    """
    
    def __init__(
        self,
        library_path: str,
        slot_id: int = 0,
        pin: str = "",
        key_label: str = "grace-master-key"
    ):
        self._library_path = library_path
        self._slot_id = slot_id
        self._pin = pin
        self._key_label = key_label
        self._session = None
        self._pkcs11 = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize PKCS#11 connection."""
        try:
            from PyKCS11 import PyKCS11Lib
            
            self._pkcs11 = PyKCS11Lib()
            self._pkcs11.load(self._library_path)
            
            slot = self._pkcs11.getSlotList(tokenPresent=True)[self._slot_id]
            self._session = self._pkcs11.openSession(
                slot,
                2  # CKF_RW_SESSION | CKF_SERIAL_SESSION
            )
            
            if self._pin:
                self._session.login(self._pin)
            
            logger.info(f"HSM initialized: slot={self._slot_id}, label={self._key_label}")
            
        except ImportError:
            logger.error("PyKCS11 library not available")
            raise EncryptionError("PyKCS11 library required for HSM support")
        except Exception as e:
            logger.error(f"HSM initialization failed: {e}")
            raise EncryptionError(f"HSM initialization failed: {e}")
    
    def get_key(self, key_id: Optional[str] = None) -> bytes:
        """Get a key from HSM (not recommended - keys should stay in HSM)."""
        raise EncryptionError("HSM keys should not be exported")
    
    def wrap_key(self, key: bytes, key_id: Optional[str] = None) -> bytes:
        """Wrap a key using HSM."""
        try:
            from PyKCS11 import CKM_AES_KEY_WRAP, CKA_LABEL, CKO_SECRET_KEY
            
            master_key = self._find_key(self._key_label)
            if not master_key:
                raise EncryptionError("Master key not found in HSM")
            
            mechanism = (CKM_AES_KEY_WRAP,)
            wrapped = self._session.wrapKey(master_key, key, mechanism)
            return bytes(wrapped)
            
        except Exception as e:
            raise EncryptionError(f"HSM key wrap failed: {e}")
    
    def unwrap_key(self, wrapped_key: bytes, key_id: Optional[str] = None) -> bytes:
        """Unwrap a key using HSM."""
        try:
            from PyKCS11 import CKM_AES_KEY_WRAP, CKA_CLASS, CKO_SECRET_KEY
            
            master_key = self._find_key(self._key_label)
            if not master_key:
                raise EncryptionError("Master key not found in HSM")
            
            mechanism = (CKM_AES_KEY_WRAP,)
            template = [(CKA_CLASS, CKO_SECRET_KEY)]
            
            unwrapped = self._session.unwrapKey(
                master_key,
                wrapped_key,
                mechanism,
                template
            )
            
            return bytes(unwrapped)
            
        except Exception as e:
            raise EncryptionError(f"HSM key unwrap failed: {e}")
    
    def _find_key(self, label: str):
        """Find a key in HSM by label."""
        from PyKCS11 import CKA_LABEL, CKA_CLASS, CKO_SECRET_KEY
        
        template = [
            (CKA_CLASS, CKO_SECRET_KEY),
            (CKA_LABEL, label)
        ]
        
        keys = self._session.findObjects(template)
        return keys[0] if keys else None
    
    def __del__(self):
        """Clean up HSM session."""
        if self._session:
            try:
                self._session.logout()
                self._session.closeSession()
            except Exception:
                pass


class FieldEncryption:
    """
    Field-level encryption for database columns.
    
    Provides transparent encryption/decryption for sensitive fields
    while maintaining searchability for non-sensitive portions.
    """
    
    ENCRYPTED_PREFIX = "enc:v1:"
    
    def __init__(
        self,
        encryption: Optional[AESGCMEncryption] = None,
        key: Optional[bytes] = None
    ):
        """
        Initialize field encryption.
        
        Args:
            encryption: Optional AESGCMEncryption instance
            key: Optional encryption key (generates new if not provided)
        """
        if encryption:
            self._encryption = encryption
        elif key:
            self._encryption = AESGCMEncryption(key)
        else:
            self._encryption = AESGCMEncryption()
    
    def encrypt_field(
        self,
        value: Any,
        field_name: Optional[str] = None
    ) -> str:
        """
        Encrypt a field value.
        
        Args:
            value: Value to encrypt (will be JSON serialized)
            field_name: Optional field name for AAD
            
        Returns:
            Encrypted string with prefix
        """
        json_value = json.dumps(value)
        aad = field_name.encode() if field_name else None
        encrypted = self._encryption.encrypt(json_value, aad)
        return f"{self.ENCRYPTED_PREFIX}{encrypted.to_base64()}"
    
    def decrypt_field(
        self,
        encrypted_value: str,
        field_name: Optional[str] = None
    ) -> Any:
        """
        Decrypt a field value.
        
        Args:
            encrypted_value: Encrypted string with prefix
            field_name: Optional field name for AAD
            
        Returns:
            Decrypted and deserialized value
        """
        if not encrypted_value.startswith(self.ENCRYPTED_PREFIX):
            return encrypted_value
        
        ciphertext = encrypted_value[len(self.ENCRYPTED_PREFIX):]
        encrypted = EncryptedData.from_base64(ciphertext)
        
        aad = field_name.encode() if field_name else None
        decrypted = self._encryption.decrypt(encrypted, aad)
        
        return json.loads(decrypted.decode('utf-8'))
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted."""
        return isinstance(value, str) and value.startswith(self.ENCRYPTED_PREFIX)
    
    def encrypt_dict(
        self,
        data: Dict[str, Any],
        fields_to_encrypt: set
    ) -> Dict[str, Any]:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary with values
            fields_to_encrypt: Set of field names to encrypt
            
        Returns:
            Dictionary with encrypted fields
        """
        result = {}
        for key, value in data.items():
            if key in fields_to_encrypt and value is not None:
                result[key] = self.encrypt_field(value, key)
            else:
                result[key] = value
        return result
    
    def decrypt_dict(
        self,
        data: Dict[str, Any],
        fields_to_decrypt: Optional[set] = None
    ) -> Dict[str, Any]:
        """
        Decrypt fields in a dictionary.
        
        Args:
            data: Dictionary with encrypted values
            fields_to_decrypt: Optional set of field names (decrypts all if None)
            
        Returns:
            Dictionary with decrypted fields
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and self.is_encrypted(value):
                if fields_to_decrypt is None or key in fields_to_decrypt:
                    result[key] = self.decrypt_field(value, key)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result


def create_encryption_key() -> bytes:
    """Generate a new 256-bit encryption key."""
    return os.urandom(32)


def derive_key_from_password(
    password: str,
    salt: Optional[bytes] = None
) -> Tuple[bytes, bytes]:
    """
    Derive an encryption key from a password.
    
    Returns:
        Tuple of (key, salt)
    """
    return KeyDerivation.derive_key(password, salt)


def get_key_provider(
    hsm_enabled: bool = False,
    hsm_library: str = "",
    hsm_slot: int = 0,
    hsm_pin: str = "",
    master_key_path: str = ""
) -> KeyProvider:
    """
    Get appropriate key provider based on configuration.
    
    Args:
        hsm_enabled: Whether to use HSM
        hsm_library: Path to PKCS#11 library
        hsm_slot: HSM slot ID
        hsm_pin: HSM PIN
        master_key_path: Path for software key storage
        
    Returns:
        KeyProvider instance
    """
    if hsm_enabled and hsm_library:
        return HSMKeyProvider(
            library_path=hsm_library,
            slot_id=hsm_slot,
            pin=hsm_pin
        )
    else:
        return SoftwareKeyProvider(key_file=master_key_path)
