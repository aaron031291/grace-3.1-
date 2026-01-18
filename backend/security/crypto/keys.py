"""
Key Management for GRACE

Provides comprehensive key management:
- RSA key pair generation (2048, 4096 bit)
- ECDSA key generation (P-256, P-384)
- Key storage with encryption
- Key rotation policies
- Key escrow for recovery
- HSM integration interface
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, Union, Protocol
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib

from .random import SecureRandom, generate_salt
from .hashing import hash_sha256

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """Supported key types."""
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    ECDSA_P256 = "ecdsa_p256"
    ECDSA_P384 = "ecdsa_p384"
    AES_128 = "aes_128"
    AES_256 = "aes_256"
    HMAC_256 = "hmac_256"
    HMAC_512 = "hmac_512"


class KeyUsage(Enum):
    """Key usage purposes."""
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    KEY_WRAPPING = "key_wrapping"
    AUTHENTICATION = "authentication"
    KEY_AGREEMENT = "key_agreement"


class KeyStatus(Enum):
    """Key lifecycle status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPROMISED = "compromised"
    EXPIRED = "expired"
    PENDING_ROTATION = "pending_rotation"
    DESTROYED = "destroyed"


@dataclass
class KeyMetadata:
    """Metadata for a cryptographic key."""
    key_id: str
    key_type: KeyType
    usage: KeyUsage
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: KeyStatus = KeyStatus.ACTIVE
    version: int = 1
    algorithm: str = ""
    fingerprint: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    rotation_policy: Optional[str] = None


@dataclass
class KeyPair:
    """Container for a key pair."""
    public_key: bytes
    private_key: bytes
    metadata: KeyMetadata


@dataclass
class SymmetricKey:
    """Container for a symmetric key."""
    key: bytes
    metadata: KeyMetadata


class HSMInterface(Protocol):
    """Protocol for HSM integration."""
    
    def generate_key(self, key_type: KeyType, key_id: str) -> str:
        """Generate a key in the HSM."""
        ...
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        """Sign data using a key in the HSM."""
        ...
    
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify a signature using a key in the HSM."""
        ...
    
    def encrypt(self, key_id: str, data: bytes) -> bytes:
        """Encrypt data using a key in the HSM."""
        ...
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt data using a key in the HSM."""
        ...
    
    def wrap_key(self, wrapping_key_id: str, key_to_wrap: bytes) -> bytes:
        """Wrap a key for export."""
        ...
    
    def unwrap_key(self, wrapping_key_id: str, wrapped_key: bytes) -> bytes:
        """Unwrap an imported key."""
        ...


class SoftwareHSM:
    """Software-based HSM simulation for development/testing."""
    
    def __init__(self):
        self._keys: Dict[str, bytes] = {}
    
    def generate_key(self, key_type: KeyType, key_id: str) -> str:
        if key_type in (KeyType.AES_128, KeyType.AES_256):
            key_size = 16 if key_type == KeyType.AES_128 else 32
            self._keys[key_id] = SecureRandom.bytes(key_size)
        else:
            self._keys[key_id] = SecureRandom.bytes(32)
        return key_id
    
    def sign(self, key_id: str, data: bytes) -> bytes:
        import hmac
        key = self._keys.get(key_id)
        if not key:
            raise KeyError(f"Key not found: {key_id}")
        return hmac.new(key, data, 'sha256').digest()
    
    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        import hmac
        expected = self.sign(key_id, data)
        return hmac.compare_digest(expected, signature)
    
    def encrypt(self, key_id: str, data: bytes) -> bytes:
        key = self._keys.get(key_id)
        if not key:
            raise KeyError(f"Key not found: {key_id}")
        return bytes([a ^ b for a, b in zip(data, (key * ((len(data) // len(key)) + 1))[:len(data)])])
    
    def decrypt(self, key_id: str, ciphertext: bytes) -> bytes:
        return self.encrypt(key_id, ciphertext)
    
    def wrap_key(self, wrapping_key_id: str, key_to_wrap: bytes) -> bytes:
        return self.encrypt(wrapping_key_id, key_to_wrap)
    
    def unwrap_key(self, wrapping_key_id: str, wrapped_key: bytes) -> bytes:
        return self.decrypt(wrapping_key_id, wrapped_key)


class KeyGenerator:
    """Generate cryptographic keys."""
    
    @staticmethod
    def generate_rsa_keypair(key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate RSA key pair."""
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return public_pem, private_pem
        except ImportError:
            logger.error("cryptography library not available")
            raise RuntimeError("cryptography library required for RSA key generation")
    
    @staticmethod
    def generate_ecdsa_keypair(curve: str = "P-256") -> Tuple[bytes, bytes]:
        """Generate ECDSA key pair."""
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            curve_map = {
                "P-256": ec.SECP256R1(),
                "P-384": ec.SECP384R1(),
                "P-521": ec.SECP521R1(),
            }
            
            if curve not in curve_map:
                raise ValueError(f"Unsupported curve: {curve}")
            
            private_key = ec.generate_private_key(curve_map[curve], default_backend())
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return public_pem, private_pem
        except ImportError:
            logger.error("cryptography library not available")
            raise RuntimeError("cryptography library required for ECDSA key generation")
    
    @staticmethod
    def generate_symmetric_key(key_size: int = 32) -> bytes:
        """Generate a symmetric key."""
        return SecureRandom.bytes(key_size)
    
    @staticmethod
    def generate_hmac_key(key_size: int = 32) -> bytes:
        """Generate an HMAC key."""
        return SecureRandom.bytes(key_size)
    
    @staticmethod
    def derive_key(password: str, salt: bytes, length: int = 32, iterations: int = 600000) -> bytes:
        """Derive a key from a password using PBKDF2."""
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=length)


@dataclass
class RotationPolicy:
    """Key rotation policy configuration."""
    name: str
    max_age_days: int
    max_operations: Optional[int] = None
    auto_rotate: bool = True
    notify_before_days: int = 7
    grace_period_days: int = 30


class KeyRotationManager:
    """Manage key rotation policies."""
    
    DEFAULT_POLICIES = {
        "signing": RotationPolicy("signing", max_age_days=365, auto_rotate=True),
        "encryption": RotationPolicy("encryption", max_age_days=90, auto_rotate=True),
        "session": RotationPolicy("session", max_age_days=1, auto_rotate=True),
        "api_key": RotationPolicy("api_key", max_age_days=30, auto_rotate=False),
    }
    
    def __init__(self):
        self.policies = dict(self.DEFAULT_POLICIES)
    
    def add_policy(self, policy: RotationPolicy):
        """Add a rotation policy."""
        self.policies[policy.name] = policy
    
    def get_policy(self, name: str) -> Optional[RotationPolicy]:
        """Get a rotation policy by name."""
        return self.policies.get(name)
    
    def check_rotation_needed(self, metadata: KeyMetadata) -> bool:
        """Check if a key needs rotation."""
        if metadata.status != KeyStatus.ACTIVE:
            return False
        
        policy = self.policies.get(metadata.rotation_policy or "")
        if not policy:
            return False
        
        age = datetime.utcnow() - metadata.created_at
        return age.days >= policy.max_age_days
    
    def get_rotation_deadline(self, metadata: KeyMetadata) -> Optional[datetime]:
        """Get when a key must be rotated."""
        policy = self.policies.get(metadata.rotation_policy or "")
        if not policy:
            return None
        return metadata.created_at + timedelta(days=policy.max_age_days)


class KeyEscrow:
    """Key escrow for recovery purposes."""
    
    def __init__(self, threshold: int = 2, shares: int = 3):
        self.threshold = threshold
        self.shares = shares
        self._escrow_keys: Dict[str, list] = {}
    
    def escrow_key(self, key_id: str, key: bytes) -> list:
        """Split a key into shares for escrow."""
        shares = self._split_key(key, self.shares, self.threshold)
        self._escrow_keys[key_id] = shares
        return [base64.b64encode(s).decode('ascii') for s in shares]
    
    def recover_key(self, key_id: str, shares: list) -> bytes:
        """Recover a key from shares."""
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares to recover key")
        share_bytes = [base64.b64decode(s) if isinstance(s, str) else s for s in shares]
        return self._combine_shares(share_bytes)
    
    def _split_key(self, key: bytes, n: int, k: int) -> list:
        """Simple XOR-based key splitting (for demonstration)."""
        shares = []
        for i in range(n - 1):
            share = SecureRandom.bytes(len(key))
            shares.append(share)
        last_share = key
        for share in shares:
            last_share = bytes(a ^ b for a, b in zip(last_share, share))
        shares.append(last_share)
        return shares
    
    def _combine_shares(self, shares: list) -> bytes:
        """Combine shares to recover key."""
        result = shares[0]
        for share in shares[1:]:
            result = bytes(a ^ b for a, b in zip(result, share))
        return result


class KeyStore:
    """Secure key storage with encryption."""
    
    def __init__(self, storage_path: Optional[str] = None, master_key: Optional[bytes] = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.master_key = master_key or SecureRandom.bytes(32)
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._hsm: Optional[HSMInterface] = None
    
    def set_hsm(self, hsm: HSMInterface):
        """Set HSM for hardware-backed operations."""
        self._hsm = hsm
    
    def store_key(self, key: Union[KeyPair, SymmetricKey], encrypt: bool = True) -> str:
        """Store a key securely."""
        key_id = key.metadata.key_id
        
        if isinstance(key, KeyPair):
            key_data = {
                "type": "keypair",
                "public_key": base64.b64encode(key.public_key).decode('ascii'),
                "private_key": base64.b64encode(
                    self._encrypt_key(key.private_key) if encrypt else key.private_key
                ).decode('ascii'),
                "encrypted": encrypt,
                "metadata": self._serialize_metadata(key.metadata),
            }
        else:
            key_data = {
                "type": "symmetric",
                "key": base64.b64encode(
                    self._encrypt_key(key.key) if encrypt else key.key
                ).decode('ascii'),
                "encrypted": encrypt,
                "metadata": self._serialize_metadata(key.metadata),
            }
        
        self._keys[key_id] = key_data
        self._persist()
        logger.info(f"Stored key: {key_id}")
        return key_id
    
    def get_key(self, key_id: str) -> Optional[Union[KeyPair, SymmetricKey]]:
        """Retrieve a key by ID."""
        key_data = self._keys.get(key_id)
        if not key_data:
            return None
        
        metadata = self._deserialize_metadata(key_data["metadata"])
        
        if key_data["type"] == "keypair":
            private_key = base64.b64decode(key_data["private_key"])
            if key_data["encrypted"]:
                private_key = self._decrypt_key(private_key)
            return KeyPair(
                public_key=base64.b64decode(key_data["public_key"]),
                private_key=private_key,
                metadata=metadata,
            )
        else:
            key = base64.b64decode(key_data["key"])
            if key_data["encrypted"]:
                key = self._decrypt_key(key)
            return SymmetricKey(key=key, metadata=metadata)
    
    def delete_key(self, key_id: str, secure: bool = True):
        """Delete a key from storage."""
        if key_id in self._keys:
            if secure:
                self._keys[key_id]["metadata"]["status"] = KeyStatus.DESTROYED.value
            del self._keys[key_id]
            self._persist()
            logger.info(f"Deleted key: {key_id}")
    
    def list_keys(self) -> list:
        """List all stored key IDs and metadata."""
        return [
            {"key_id": kid, "metadata": kdata["metadata"]}
            for kid, kdata in self._keys.items()
        ]
    
    def _encrypt_key(self, key: bytes) -> bytes:
        """Encrypt a key for storage."""
        import hmac
        nonce = SecureRandom.bytes(16)
        cipher_key = hashlib.pbkdf2_hmac('sha256', self.master_key, nonce, 10000, dklen=32)
        encrypted = bytes(a ^ b for a, b in zip(key, (cipher_key * ((len(key) // 32) + 1))[:len(key)]))
        mac = hmac.new(cipher_key, nonce + encrypted, 'sha256').digest()[:16]
        return nonce + mac + encrypted
    
    def _decrypt_key(self, encrypted: bytes) -> bytes:
        """Decrypt a stored key."""
        import hmac
        nonce = encrypted[:16]
        stored_mac = encrypted[16:32]
        ciphertext = encrypted[32:]
        cipher_key = hashlib.pbkdf2_hmac('sha256', self.master_key, nonce, 10000, dklen=32)
        expected_mac = hmac.new(cipher_key, nonce + ciphertext, 'sha256').digest()[:16]
        if not hmac.compare_digest(stored_mac, expected_mac):
            raise ValueError("Key decryption failed: invalid MAC")
        return bytes(a ^ b for a, b in zip(ciphertext, (cipher_key * ((len(ciphertext) // 32) + 1))[:len(ciphertext)]))
    
    def _serialize_metadata(self, metadata: KeyMetadata) -> dict:
        """Serialize key metadata."""
        return {
            "key_id": metadata.key_id,
            "key_type": metadata.key_type.value,
            "usage": metadata.usage.value,
            "created_at": metadata.created_at.isoformat(),
            "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
            "status": metadata.status.value,
            "version": metadata.version,
            "algorithm": metadata.algorithm,
            "fingerprint": metadata.fingerprint,
            "tags": metadata.tags,
            "rotation_policy": metadata.rotation_policy,
        }
    
    def _deserialize_metadata(self, data: dict) -> KeyMetadata:
        """Deserialize key metadata."""
        return KeyMetadata(
            key_id=data["key_id"],
            key_type=KeyType(data["key_type"]),
            usage=KeyUsage(data["usage"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=KeyStatus(data["status"]),
            version=data.get("version", 1),
            algorithm=data.get("algorithm", ""),
            fingerprint=data.get("fingerprint", ""),
            tags=data.get("tags", {}),
            rotation_policy=data.get("rotation_policy"),
        )
    
    def _persist(self):
        """Persist keys to storage."""
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self._keys, f, indent=2)


class KeyManager:
    """High-level key management interface."""
    
    def __init__(self, store: Optional[KeyStore] = None):
        self.store = store or KeyStore()
        self.rotation_manager = KeyRotationManager()
        self.escrow = KeyEscrow()
        self._audit_callback = None
    
    def set_audit_callback(self, callback):
        """Set callback for audit logging."""
        self._audit_callback = callback
    
    def _audit(self, action: str, key_id: str, details: Optional[Dict] = None):
        """Log an audit event."""
        if self._audit_callback:
            self._audit_callback({
                "action": action,
                "key_id": key_id,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {},
            })
    
    def generate_rsa_keypair(
        self,
        key_id: str,
        key_size: int = 2048,
        usage: KeyUsage = KeyUsage.SIGNING,
        rotation_policy: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> KeyPair:
        """Generate and store an RSA key pair."""
        key_type = KeyType.RSA_2048 if key_size == 2048 else KeyType.RSA_4096
        public_key, private_key = KeyGenerator.generate_rsa_keypair(key_size)
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type,
            usage=usage,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
            algorithm=f"RSA-{key_size}",
            fingerprint=hash_sha256(public_key)[:16],
            rotation_policy=rotation_policy,
        )
        
        keypair = KeyPair(public_key=public_key, private_key=private_key, metadata=metadata)
        self.store.store_key(keypair)
        self._audit("generate_rsa_keypair", key_id, {"key_size": key_size})
        return keypair
    
    def generate_ecdsa_keypair(
        self,
        key_id: str,
        curve: str = "P-256",
        usage: KeyUsage = KeyUsage.SIGNING,
        rotation_policy: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> KeyPair:
        """Generate and store an ECDSA key pair."""
        key_type = KeyType.ECDSA_P256 if curve == "P-256" else KeyType.ECDSA_P384
        public_key, private_key = KeyGenerator.generate_ecdsa_keypair(curve)
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type,
            usage=usage,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
            algorithm=f"ECDSA-{curve}",
            fingerprint=hash_sha256(public_key)[:16],
            rotation_policy=rotation_policy,
        )
        
        keypair = KeyPair(public_key=public_key, private_key=private_key, metadata=metadata)
        self.store.store_key(keypair)
        self._audit("generate_ecdsa_keypair", key_id, {"curve": curve})
        return keypair
    
    def generate_symmetric_key(
        self,
        key_id: str,
        key_size: int = 32,
        usage: KeyUsage = KeyUsage.ENCRYPTION,
        rotation_policy: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> SymmetricKey:
        """Generate and store a symmetric key."""
        key_type = KeyType.AES_128 if key_size == 16 else KeyType.AES_256
        key = KeyGenerator.generate_symmetric_key(key_size)
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=key_type,
            usage=usage,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
            algorithm=f"AES-{key_size * 8}",
            fingerprint=hash_sha256(key)[:16],
            rotation_policy=rotation_policy,
        )
        
        sym_key = SymmetricKey(key=key, metadata=metadata)
        self.store.store_key(sym_key)
        self._audit("generate_symmetric_key", key_id, {"key_size": key_size})
        return sym_key
    
    def rotate_key(self, key_id: str) -> Optional[str]:
        """Rotate a key, creating a new version."""
        old_key = self.store.get_key(key_id)
        if not old_key:
            return None
        
        new_key_id = f"{key_id}_v{old_key.metadata.version + 1}"
        old_key.metadata.status = KeyStatus.INACTIVE
        
        if isinstance(old_key, KeyPair):
            if old_key.metadata.key_type in (KeyType.RSA_2048, KeyType.RSA_4096):
                key_size = 2048 if old_key.metadata.key_type == KeyType.RSA_2048 else 4096
                new_key = self.generate_rsa_keypair(
                    new_key_id,
                    key_size=key_size,
                    usage=old_key.metadata.usage,
                    rotation_policy=old_key.metadata.rotation_policy,
                )
            else:
                curve = "P-256" if old_key.metadata.key_type == KeyType.ECDSA_P256 else "P-384"
                new_key = self.generate_ecdsa_keypair(
                    new_key_id,
                    curve=curve,
                    usage=old_key.metadata.usage,
                    rotation_policy=old_key.metadata.rotation_policy,
                )
        else:
            key_size = 16 if old_key.metadata.key_type == KeyType.AES_128 else 32
            new_key = self.generate_symmetric_key(
                new_key_id,
                key_size=key_size,
                usage=old_key.metadata.usage,
                rotation_policy=old_key.metadata.rotation_policy,
            )
        
        new_key.metadata.version = old_key.metadata.version + 1
        self._audit("rotate_key", key_id, {"new_key_id": new_key_id})
        return new_key_id
    
    def get_key(self, key_id: str) -> Optional[Union[KeyPair, SymmetricKey]]:
        """Get a key by ID."""
        return self.store.get_key(key_id)
    
    def escrow_key(self, key_id: str) -> list:
        """Put a key in escrow for recovery."""
        key = self.store.get_key(key_id)
        if not key:
            raise KeyError(f"Key not found: {key_id}")
        
        if isinstance(key, KeyPair):
            shares = self.escrow.escrow_key(key_id, key.private_key)
        else:
            shares = self.escrow.escrow_key(key_id, key.key)
        
        self._audit("escrow_key", key_id, {"shares_created": len(shares)})
        return shares
