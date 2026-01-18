"""
Encryption Services for GRACE

Provides comprehensive encryption:
- Symmetric encryption (AES-256-GCM)
- Asymmetric encryption (RSA-OAEP)
- Envelope encryption for large data
- Field-level encryption
- Searchable encryption
- Format-preserving encryption for PII
"""

import os
import base64
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .random import SecureRandom, NonceGenerator, IVGenerator
from .hashing import hash_sha256, HMACAuthenticator

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    RSA_OAEP_SHA256 = "rsa-oaep-sha256"


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes
    tag: Optional[bytes] = None
    algorithm: str = "aes-256-gcm"
    key_id: Optional[str] = None
    version: int = 1
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
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
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """Deserialize from bytes."""
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
    
    def to_base64(self) -> str:
        """Encode to base64 for transmission."""
        return base64.b64encode(self.to_bytes()).decode('ascii')
    
    @classmethod
    def from_base64(cls, data: str) -> 'EncryptedData':
        """Decode from base64."""
        return cls.from_bytes(base64.b64decode(data))


class AESGCMEncryptor:
    """AES-256-GCM encryption."""
    
    KEY_SIZE = 32
    NONCE_SIZE = 12
    TAG_SIZE = 16
    
    def __init__(self, key: bytes):
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        self.key = key
        self._crypto_available = False
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            self._aesgcm = AESGCM(key)
            self._crypto_available = True
        except ImportError:
            logger.warning("cryptography library not available, using fallback")
            self._aesgcm = None
    
    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> EncryptedData:
        """Encrypt data with AES-256-GCM."""
        nonce = NonceGenerator.generate_aes_gcm_nonce()
        
        if self._crypto_available and self._aesgcm:
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
            return EncryptedData(
                ciphertext=ciphertext[:-self.TAG_SIZE],
                nonce=nonce,
                tag=ciphertext[-self.TAG_SIZE:],
                algorithm=EncryptionAlgorithm.AES_256_GCM.value,
            )
        else:
            encrypted = self._fallback_encrypt(plaintext, nonce)
            return EncryptedData(
                ciphertext=encrypted,
                nonce=nonce,
                tag=hashlib.sha256(nonce + encrypted).digest()[:self.TAG_SIZE],
                algorithm="aes-256-gcm-fallback",
            )
    
    def decrypt(self, encrypted: EncryptedData, associated_data: Optional[bytes] = None) -> bytes:
        """Decrypt AES-256-GCM encrypted data."""
        if self._crypto_available and self._aesgcm:
            ciphertext_with_tag = encrypted.ciphertext + (encrypted.tag or b'')
            return self._aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, associated_data)
        else:
            return self._fallback_decrypt(encrypted.ciphertext, encrypted.nonce)
    
    def _fallback_encrypt(self, plaintext: bytes, nonce: bytes) -> bytes:
        """Fallback XOR-based encryption (NOT secure, for testing only)."""
        key_stream = hashlib.pbkdf2_hmac('sha256', self.key, nonce, 1000, dklen=len(plaintext))
        return bytes(a ^ b for a, b in zip(plaintext, key_stream))
    
    def _fallback_decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Fallback XOR-based decryption."""
        return self._fallback_encrypt(ciphertext, nonce)


class RSAEncryptor:
    """RSA-OAEP encryption."""
    
    def __init__(self, public_key: Optional[bytes] = None, private_key: Optional[bytes] = None):
        self.public_key = public_key
        self.private_key = private_key
        self._crypto_available = False
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            self._backend = default_backend()
            self._crypto_available = True
            if public_key:
                self._pub_key = serialization.load_pem_public_key(public_key, self._backend)
            else:
                self._pub_key = None
            if private_key:
                self._priv_key = serialization.load_pem_private_key(private_key, None, self._backend)
            else:
                self._priv_key = None
        except ImportError:
            logger.error("cryptography library required for RSA encryption")
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data with RSA-OAEP."""
        if not self._crypto_available:
            raise RuntimeError("cryptography library required")
        if not self._pub_key:
            raise ValueError("Public key required for encryption")
        
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        return self._pub_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt RSA-OAEP encrypted data."""
        if not self._crypto_available:
            raise RuntimeError("cryptography library required")
        if not self._priv_key:
            raise ValueError("Private key required for decryption")
        
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        return self._priv_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )


class EnvelopeEncryptor:
    """Envelope encryption for large data."""
    
    DEK_SIZE = 32
    
    def __init__(self, kek: bytes):
        """Initialize with Key Encryption Key (KEK)."""
        self.kek = kek
        self.kek_encryptor = AESGCMEncryptor(kek)
    
    def encrypt(self, plaintext: bytes) -> Tuple[bytes, EncryptedData]:
        """Encrypt data using envelope encryption."""
        dek = SecureRandom.bytes(self.DEK_SIZE)
        data_encryptor = AESGCMEncryptor(dek)
        encrypted_data = data_encryptor.encrypt(plaintext)
        encrypted_dek = self.kek_encryptor.encrypt(dek)
        return encrypted_dek.to_bytes(), encrypted_data
    
    def decrypt(self, encrypted_dek: bytes, encrypted_data: EncryptedData) -> bytes:
        """Decrypt envelope encrypted data."""
        dek_container = EncryptedData.from_bytes(encrypted_dek)
        dek = self.kek_encryptor.decrypt(dek_container)
        data_encryptor = AESGCMEncryptor(dek)
        return data_encryptor.decrypt(encrypted_data)
    
    def encrypt_to_bytes(self, plaintext: bytes) -> bytes:
        """Encrypt and combine into single bytes output."""
        encrypted_dek, encrypted_data = self.encrypt(plaintext)
        dek_len = len(encrypted_dek).to_bytes(4, 'big')
        return dek_len + encrypted_dek + encrypted_data.to_bytes()
    
    def decrypt_from_bytes(self, data: bytes) -> bytes:
        """Decrypt from combined bytes."""
        dek_len = int.from_bytes(data[:4], 'big')
        encrypted_dek = data[4:4 + dek_len]
        encrypted_data = EncryptedData.from_bytes(data[4 + dek_len:])
        return self.decrypt(encrypted_dek, encrypted_data)


class FieldEncryptor:
    """Field-level encryption for structured data."""
    
    def __init__(self, key: bytes):
        self.encryptor = AESGCMEncryptor(key)
        self._sensitive_fields: set = set()
    
    def mark_sensitive(self, *fields: str):
        """Mark fields as sensitive for encryption."""
        self._sensitive_fields.update(fields)
    
    def encrypt_field(self, value: Any) -> str:
        """Encrypt a single field value."""
        if value is None:
            return None
        serialized = json.dumps(value).encode('utf-8')
        encrypted = self.encryptor.encrypt(serialized)
        return f"ENC:{encrypted.to_base64()}"
    
    def decrypt_field(self, encrypted_value: str) -> Any:
        """Decrypt a single field value."""
        if not encrypted_value or not encrypted_value.startswith("ENC:"):
            return encrypted_value
        encrypted_data = EncryptedData.from_base64(encrypted_value[4:])
        decrypted = self.encryptor.decrypt(encrypted_data)
        return json.loads(decrypted.decode('utf-8'))
    
    def encrypt_document(self, document: Dict[str, Any], fields: Optional[list] = None) -> Dict[str, Any]:
        """Encrypt sensitive fields in a document."""
        fields_to_encrypt = set(fields) if fields else self._sensitive_fields
        result = document.copy()
        for field in fields_to_encrypt:
            if field in result:
                result[field] = self.encrypt_field(result[field])
        return result
    
    def decrypt_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt all encrypted fields in a document."""
        result = document.copy()
        for key, value in result.items():
            if isinstance(value, str) and value.startswith("ENC:"):
                result[key] = self.decrypt_field(value)
        return result


class SearchableEncryption:
    """Searchable encryption using deterministic encryption for search tokens."""
    
    def __init__(self, key: bytes, search_key: bytes):
        self.encryptor = AESGCMEncryptor(key)
        self.search_key = search_key
    
    def _generate_search_token(self, value: str) -> str:
        """Generate a deterministic search token."""
        import hmac
        normalized = value.lower().strip()
        token = hmac.new(self.search_key, normalized.encode('utf-8'), 'sha256').hexdigest()[:32]
        return f"SRCH:{token}"
    
    def encrypt_searchable(self, value: str) -> Tuple[str, str]:
        """Encrypt value and generate search token."""
        encrypted = self.encryptor.encrypt(value.encode('utf-8'))
        search_token = self._generate_search_token(value)
        return encrypted.to_base64(), search_token
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt searchable encrypted value."""
        encrypted_data = EncryptedData.from_base64(encrypted)
        return self.encryptor.decrypt(encrypted_data).decode('utf-8')
    
    def generate_search_query(self, search_value: str) -> str:
        """Generate search token for querying."""
        return self._generate_search_token(search_value)


class FormatPreservingEncryptor:
    """Format-preserving encryption for PII."""
    
    NUMERIC = "0123456789"
    ALPHA_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ALPHA_LOWER = "abcdefghijklmnopqrstuvwxyz"
    
    def __init__(self, key: bytes, tweak: bytes = b''):
        self.key = key
        self.tweak = tweak
    
    def _feistel_round(self, data: list, round_key: bytes, alphabet: str, encrypt: bool = True) -> list:
        """Single Feistel round - balanced Feistel network."""
        import hmac
        n = len(alphabet)
        mid = len(data) // 2
        left, right = data[:mid], data[mid:]
        
        # F function: hash the right half with round key
        right_bytes = ''.join(alphabet[i] for i in right).encode('utf-8')
        f_output = hmac.new(round_key, right_bytes + self.tweak, 'sha256').digest()
        
        # XOR left with F(right) - for encrypt add, for decrypt subtract
        if encrypt:
            new_left = [(left[i] + f_output[i % len(f_output)]) % n for i in range(len(left))]
        else:
            new_left = [(left[i] - f_output[i % len(f_output)]) % n for i in range(len(left))]
        
        # Swap: new state is (right, new_left)
        return right + new_left
    
    def _encrypt_with_alphabet(self, plaintext: str, alphabet: str, rounds: int = 10) -> str:
        """Encrypt preserving character set using unbalanced Feistel for odd lengths."""
        import hmac
        if not plaintext:
            return plaintext
        
        char_to_idx = {c: i for i, c in enumerate(alphabet)}
        n = len(alphabet)
        data = [char_to_idx.get(c, 0) for c in plaintext]
        
        # For odd-length data, use unbalanced split
        mid = len(data) // 2
        
        for round_num in range(rounds):
            round_key = hmac.new(self.key, round_num.to_bytes(4, 'big'), 'sha256').digest()
            left, right = data[:mid], data[mid:]
            
            # F function on right half
            right_bytes = ''.join(alphabet[i] for i in right).encode('utf-8')
            f_output = hmac.new(round_key, right_bytes + self.tweak, 'sha256').digest()
            
            # Modify left
            new_left = [(left[i] + f_output[i % len(f_output)]) % n for i in range(len(left))]
            
            # Swap halves
            data = right + new_left
        
        return ''.join(alphabet[i] for i in data)
    
    def _decrypt_with_alphabet(self, ciphertext: str, alphabet: str, rounds: int = 10) -> str:
        """Decrypt preserving character set - reverse the Feistel network."""
        import hmac
        if not ciphertext:
            return ciphertext
        
        char_to_idx = {c: i for i, c in enumerate(alphabet)}
        n = len(alphabet)
        data = [char_to_idx.get(c, 0) for c in ciphertext]
        
        # Same split as encrypt
        total_len = len(data)
        left_len = total_len // 2
        right_len = total_len - left_len
        
        # Reverse rounds
        for round_num in range(rounds - 1, -1, -1):
            round_key = hmac.new(self.key, round_num.to_bytes(4, 'big'), 'sha256').digest()
            
            # After encrypt swap: data = (right, new_left)
            # So first right_len elements are original right, rest are modified left
            right = data[:right_len]
            new_left = data[right_len:]
            
            # Compute F(right) to reverse the modification
            right_bytes = ''.join(alphabet[i] for i in right).encode('utf-8')
            f_output = hmac.new(round_key, right_bytes + self.tweak, 'sha256').digest()
            
            # Recover original left
            left = [(new_left[i] - f_output[i % len(f_output)]) % n for i in range(len(new_left))]
            
            # Restore original order: (left, right)
            data = left + right
        
        return ''.join(alphabet[i] for i in data)
    
    def encrypt_ssn(self, ssn: str) -> str:
        """Encrypt SSN preserving format XXX-XX-XXXX."""
        parts = ssn.replace('-', '')
        if len(parts) != 9 or not parts.isdigit():
            raise ValueError("Invalid SSN format")
        encrypted = self._encrypt_with_alphabet(parts, self.NUMERIC)
        return f"{encrypted[:3]}-{encrypted[3:5]}-{encrypted[5:]}"
    
    def decrypt_ssn(self, encrypted_ssn: str) -> str:
        """Decrypt SSN."""
        parts = encrypted_ssn.replace('-', '')
        decrypted = self._decrypt_with_alphabet(parts, self.NUMERIC)
        return f"{decrypted[:3]}-{decrypted[3:5]}-{decrypted[5:]}"
    
    def encrypt_credit_card(self, cc_number: str) -> str:
        """Encrypt credit card number preserving format."""
        digits = cc_number.replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) < 13:
            raise ValueError("Invalid credit card format")
        encrypted = self._encrypt_with_alphabet(digits, self.NUMERIC)
        return ' '.join(encrypted[i:i+4] for i in range(0, len(encrypted), 4))
    
    def decrypt_credit_card(self, encrypted_cc: str) -> str:
        """Decrypt credit card number."""
        digits = encrypted_cc.replace(' ', '').replace('-', '')
        decrypted = self._decrypt_with_alphabet(digits, self.NUMERIC)
        return ' '.join(decrypted[i:i+4] for i in range(0, len(decrypted), 4))
    
    def encrypt_phone(self, phone: str) -> str:
        """Encrypt phone number preserving format."""
        digits = ''.join(c for c in phone if c.isdigit())
        encrypted = self._encrypt_with_alphabet(digits, self.NUMERIC)
        result = list(phone)
        digit_idx = 0
        for i, c in enumerate(result):
            if c.isdigit():
                result[i] = encrypted[digit_idx]
                digit_idx += 1
        return ''.join(result)
    
    def decrypt_phone(self, encrypted_phone: str) -> str:
        """Decrypt phone number."""
        digits = ''.join(c for c in encrypted_phone if c.isdigit())
        decrypted = self._decrypt_with_alphabet(digits, self.NUMERIC)
        result = list(encrypted_phone)
        digit_idx = 0
        for i, c in enumerate(result):
            if c.isdigit():
                result[i] = decrypted[digit_idx]
                digit_idx += 1
        return ''.join(result)


class EncryptionService:
    """High-level encryption service."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or SecureRandom.bytes(32)
        self._encryptors: Dict[str, AESGCMEncryptor] = {}
        self._audit_callback = None
    
    def set_audit_callback(self, callback):
        """Set callback for audit logging."""
        self._audit_callback = callback
    
    def _audit(self, action: str, details: Optional[Dict] = None):
        """Log an audit event."""
        if self._audit_callback:
            self._audit_callback({
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {},
            })
    
    def get_encryptor(self, key_id: str = "default") -> AESGCMEncryptor:
        """Get or create an encryptor for a key ID."""
        if key_id not in self._encryptors:
            derived_key = hashlib.pbkdf2_hmac(
                'sha256',
                self.master_key,
                key_id.encode('utf-8'),
                100000,
                dklen=32
            )
            self._encryptors[key_id] = AESGCMEncryptor(derived_key)
        return self._encryptors[key_id]
    
    def encrypt(self, plaintext: Union[bytes, str], key_id: str = "default") -> str:
        """Encrypt data and return base64 string."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        encryptor = self.get_encryptor(key_id)
        encrypted = encryptor.encrypt(plaintext)
        encrypted.key_id = key_id
        self._audit("encrypt", {"key_id": key_id, "size": len(plaintext)})
        return encrypted.to_base64()
    
    def decrypt(self, ciphertext: str) -> bytes:
        """Decrypt base64 encoded ciphertext."""
        encrypted = EncryptedData.from_base64(ciphertext)
        key_id = encrypted.key_id or "default"
        encryptor = self.get_encryptor(key_id)
        result = encryptor.decrypt(encrypted)
        self._audit("decrypt", {"key_id": key_id})
        return result
    
    def encrypt_file(self, input_path: str, output_path: str, key_id: str = "default"):
        """Encrypt a file."""
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        encrypted = self.encrypt(plaintext, key_id)
        with open(output_path, 'w') as f:
            f.write(encrypted)
        self._audit("encrypt_file", {"input": input_path, "output": output_path})
    
    def decrypt_file(self, input_path: str, output_path: str):
        """Decrypt a file."""
        with open(input_path, 'r') as f:
            ciphertext = f.read()
        plaintext = self.decrypt(ciphertext)
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        self._audit("decrypt_file", {"input": input_path, "output": output_path})


def encrypt_aes_gcm(key: bytes, plaintext: bytes) -> EncryptedData:
    """Convenience function: AES-GCM encryption."""
    return AESGCMEncryptor(key).encrypt(plaintext)


def decrypt_aes_gcm(key: bytes, encrypted: EncryptedData) -> bytes:
    """Convenience function: AES-GCM decryption."""
    return AESGCMEncryptor(key).decrypt(encrypted)


def encrypt_envelope(kek: bytes, plaintext: bytes) -> bytes:
    """Convenience function: Envelope encryption."""
    return EnvelopeEncryptor(kek).encrypt_to_bytes(plaintext)


def decrypt_envelope(kek: bytes, ciphertext: bytes) -> bytes:
    """Convenience function: Envelope decryption."""
    return EnvelopeEncryptor(kek).decrypt_from_bytes(ciphertext)
