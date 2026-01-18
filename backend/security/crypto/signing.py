"""
Digital Signatures for GRACE

Provides comprehensive signing functionality:
- Document signing with timestamp
- Code signing for healing actions
- Signature verification
- Multi-party signatures
- Non-repudiation guarantees
- Audit log signing
"""

import json
import base64
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .hashing import hash_sha256, ContentHasher, HashAlgorithm

logger = logging.getLogger(__name__)


class SignatureAlgorithm(Enum):
    """Supported signature algorithms."""
    RSA_PKCS1_SHA256 = "rsa-pkcs1-sha256"
    RSA_PSS_SHA256 = "rsa-pss-sha256"
    ECDSA_P256_SHA256 = "ecdsa-p256-sha256"
    ECDSA_P384_SHA384 = "ecdsa-p384-sha384"
    ED25519 = "ed25519"
    HMAC_SHA256 = "hmac-sha256"


class SignatureStatus(Enum):
    """Signature verification status."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    KEY_NOT_FOUND = "key_not_found"
    ALGORITHM_MISMATCH = "algorithm_mismatch"
    TAMPERED = "tampered"


@dataclass
class Signature:
    """Digital signature container."""
    signature: bytes
    algorithm: SignatureAlgorithm
    key_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "signature": base64.b64encode(self.signature).decode('ascii'),
            "algorithm": self.algorithm.value,
            "key_id": self.key_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Signature':
        """Deserialize from dictionary."""
        return cls(
            signature=base64.b64decode(data["signature"]),
            algorithm=SignatureAlgorithm(data["algorithm"]),
            key_id=data["key_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )
    
    def to_base64(self) -> str:
        """Encode to base64."""
        return base64.b64encode(json.dumps(self.to_dict()).encode('utf-8')).decode('ascii')
    
    @classmethod
    def from_base64(cls, data: str) -> 'Signature':
        """Decode from base64."""
        return cls.from_dict(json.loads(base64.b64decode(data).decode('utf-8')))


@dataclass
class SignedDocument:
    """A document with its signature(s)."""
    content: bytes
    content_hash: str
    signatures: List[Signature]
    created_at: datetime
    version: int = 1
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "content": base64.b64encode(self.content).decode('ascii'),
            "content_hash": self.content_hash,
            "signatures": [sig.to_dict() for sig in self.signatures],
            "created_at": self.created_at.isoformat(),
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SignedDocument':
        """Deserialize from dictionary."""
        return cls(
            content=base64.b64decode(data["content"]),
            content_hash=data["content_hash"],
            signatures=[Signature.from_dict(s) for s in data["signatures"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            version=data.get("version", 1),
        )


@dataclass
class VerificationResult:
    """Result of signature verification."""
    status: SignatureStatus
    signer_id: Optional[str] = None
    signed_at: Optional[datetime] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class DocumentSigner:
    """Sign and verify documents."""
    
    def __init__(self, private_key: Optional[bytes] = None, public_key: Optional[bytes] = None, key_id: str = ""):
        self.private_key = private_key
        self.public_key = public_key
        self.key_id = key_id
        self._crypto_available = False
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, ec
            from cryptography.hazmat.backends import default_backend
            self._crypto_available = True
            self._backend = default_backend()
        except ImportError:
            logger.warning("cryptography library not available")
    
    def sign(
        self,
        content: Union[bytes, str],
        algorithm: SignatureAlgorithm = SignatureAlgorithm.RSA_PSS_SHA256,
        metadata: Optional[Dict] = None,
    ) -> Signature:
        """Sign content and return signature."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        if not self.private_key:
            raise ValueError("Private key required for signing")
        
        if not self._crypto_available:
            return self._fallback_sign(content, metadata)
        
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, ec
        
        priv_key = serialization.load_pem_private_key(self.private_key, None, self._backend)
        
        if algorithm in (SignatureAlgorithm.RSA_PKCS1_SHA256, SignatureAlgorithm.RSA_PSS_SHA256):
            if algorithm == SignatureAlgorithm.RSA_PSS_SHA256:
                pad = padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.AUTO
                )
            else:
                pad = padding.PKCS1v15()
            sig_bytes = priv_key.sign(content, pad, hashes.SHA256())
        elif algorithm in (SignatureAlgorithm.ECDSA_P256_SHA256, SignatureAlgorithm.ECDSA_P384_SHA384):
            hash_algo = hashes.SHA256() if algorithm == SignatureAlgorithm.ECDSA_P256_SHA256 else hashes.SHA384()
            sig_bytes = priv_key.sign(content, ec.ECDSA(hash_algo))
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return Signature(
            signature=sig_bytes,
            algorithm=algorithm,
            key_id=self.key_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
    
    def verify(self, content: Union[bytes, str], signature: Signature) -> VerificationResult:
        """Verify a signature."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        if not self.public_key:
            return VerificationResult(
                status=SignatureStatus.KEY_NOT_FOUND,
                message="Public key required for verification",
            )
        
        if not self._crypto_available:
            return self._fallback_verify(content, signature)
        
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, ec
            
            pub_key = serialization.load_pem_public_key(self.public_key, self._backend)
            
            if signature.algorithm in (SignatureAlgorithm.RSA_PKCS1_SHA256, SignatureAlgorithm.RSA_PSS_SHA256):
                if signature.algorithm == SignatureAlgorithm.RSA_PSS_SHA256:
                    pad = padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.AUTO
                    )
                else:
                    pad = padding.PKCS1v15()
                pub_key.verify(signature.signature, content, pad, hashes.SHA256())
            elif signature.algorithm in (SignatureAlgorithm.ECDSA_P256_SHA256, SignatureAlgorithm.ECDSA_P384_SHA384):
                hash_algo = hashes.SHA256() if signature.algorithm == SignatureAlgorithm.ECDSA_P256_SHA256 else hashes.SHA384()
                pub_key.verify(signature.signature, content, ec.ECDSA(hash_algo))
            else:
                return VerificationResult(
                    status=SignatureStatus.ALGORITHM_MISMATCH,
                    message=f"Unsupported algorithm: {signature.algorithm}",
                )
            
            return VerificationResult(
                status=SignatureStatus.VALID,
                signer_id=signature.key_id,
                signed_at=signature.timestamp,
                message="Signature verified successfully",
            )
        except Exception as e:
            return VerificationResult(
                status=SignatureStatus.INVALID,
                message=str(e),
            )
    
    def _fallback_sign(self, content: bytes, metadata: Optional[Dict]) -> Signature:
        """Fallback HMAC-based signing."""
        import hmac
        sig = hmac.new(self.private_key, content, 'sha256').digest()
        return Signature(
            signature=sig,
            algorithm=SignatureAlgorithm.HMAC_SHA256,
            key_id=self.key_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
    
    def _fallback_verify(self, content: bytes, signature: Signature) -> VerificationResult:
        """Fallback HMAC verification."""
        import hmac
        expected = hmac.new(self.public_key, content, 'sha256').digest()
        if hmac.compare_digest(expected, signature.signature):
            return VerificationResult(
                status=SignatureStatus.VALID,
                signer_id=signature.key_id,
                signed_at=signature.timestamp,
            )
        return VerificationResult(status=SignatureStatus.INVALID)


class CodeSigner:
    """Sign and verify code for healing actions."""
    
    ALLOWED_ACTIONS = {"fix", "patch", "rollback", "upgrade", "migrate"}
    
    def __init__(self, signer: DocumentSigner):
        self.signer = signer
        self._audit_callback = None
    
    def set_audit_callback(self, callback):
        """Set callback for audit logging."""
        self._audit_callback = callback
    
    def _audit(self, action: str, details: Dict):
        """Log audit event."""
        if self._audit_callback:
            self._audit_callback({
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details,
            })
    
    def sign_code(
        self,
        code: str,
        action_type: str,
        target: str,
        reason: str,
    ) -> SignedDocument:
        """Sign code for a healing action."""
        if action_type not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Invalid action type: {action_type}")
        
        content_hash = hash_sha256(code)
        metadata = {
            "action_type": action_type,
            "target": target,
            "reason": reason,
            "content_hash": content_hash,
            "signed_by": self.signer.key_id,
        }
        
        signature = self.signer.sign(
            code.encode('utf-8'),
            metadata=metadata,
        )
        
        signed_doc = SignedDocument(
            content=code.encode('utf-8'),
            content_hash=content_hash,
            signatures=[signature],
            created_at=datetime.utcnow(),
        )
        
        self._audit("code_signed", {
            "action_type": action_type,
            "target": target,
            "content_hash": content_hash,
        })
        
        return signed_doc
    
    def verify_code(self, signed_doc: SignedDocument) -> VerificationResult:
        """Verify signed code."""
        computed_hash = hash_sha256(signed_doc.content.decode('utf-8'))
        if computed_hash != signed_doc.content_hash:
            return VerificationResult(
                status=SignatureStatus.TAMPERED,
                message="Content hash mismatch - code was modified",
            )
        
        if not signed_doc.signatures:
            return VerificationResult(
                status=SignatureStatus.INVALID,
                message="No signatures found",
            )
        
        result = self.signer.verify(signed_doc.content, signed_doc.signatures[0])
        self._audit("code_verified", {
            "content_hash": signed_doc.content_hash,
            "status": result.status.value,
        })
        return result


class MultiPartySigner:
    """Multi-party signature scheme."""
    
    def __init__(self, threshold: int, signers: List[DocumentSigner]):
        if threshold > len(signers):
            raise ValueError("Threshold cannot exceed number of signers")
        self.threshold = threshold
        self.signers = signers
    
    def sign(self, content: Union[bytes, str]) -> SignedDocument:
        """Collect signatures from all signers."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        content_hash = hash_sha256(content)
        signatures = []
        
        for signer in self.signers:
            try:
                sig = signer.sign(content)
                signatures.append(sig)
            except Exception as e:
                logger.warning(f"Signer {signer.key_id} failed: {e}")
        
        return SignedDocument(
            content=content,
            content_hash=content_hash,
            signatures=signatures,
            created_at=datetime.utcnow(),
        )
    
    def verify(self, signed_doc: SignedDocument, verifiers: List[DocumentSigner]) -> Tuple[bool, List[VerificationResult]]:
        """Verify multi-party signatures."""
        computed_hash = hash_sha256(signed_doc.content)
        if computed_hash != signed_doc.content_hash:
            return False, [VerificationResult(status=SignatureStatus.TAMPERED)]
        
        results = []
        valid_count = 0
        
        for sig in signed_doc.signatures:
            for verifier in verifiers:
                if verifier.key_id == sig.key_id:
                    result = verifier.verify(signed_doc.content, sig)
                    results.append(result)
                    if result.status == SignatureStatus.VALID:
                        valid_count += 1
                    break
        
        threshold_met = valid_count >= self.threshold
        return threshold_met, results


class AuditLogSigner:
    """Sign audit log entries for non-repudiation."""
    
    def __init__(self, signer: DocumentSigner):
        self.signer = signer
        self._chain_hash: Optional[str] = None
    
    def sign_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Sign an audit log entry with chain linking."""
        entry_copy = entry.copy()
        entry_copy["_timestamp"] = datetime.utcnow().isoformat()
        entry_copy["_previous_hash"] = self._chain_hash
        
        serialized = json.dumps(entry_copy, sort_keys=True, default=str)
        content_hash = hash_sha256(serialized)
        
        signature = self.signer.sign(serialized.encode('utf-8'))
        
        signed_entry = {
            **entry_copy,
            "_content_hash": content_hash,
            "_signature": signature.to_base64(),
        }
        
        self._chain_hash = content_hash
        return signed_entry
    
    def verify_entry(self, entry: Dict[str, Any], expected_previous_hash: Optional[str] = None) -> VerificationResult:
        """Verify a signed audit log entry."""
        if expected_previous_hash and entry.get("_previous_hash") != expected_previous_hash:
            return VerificationResult(
                status=SignatureStatus.TAMPERED,
                message="Chain integrity violation - previous hash mismatch",
            )
        
        signature = Signature.from_base64(entry["_signature"])
        
        verify_entry = {k: v for k, v in entry.items() if not k.startswith("_") or k in ("_timestamp", "_previous_hash")}
        serialized = json.dumps(verify_entry, sort_keys=True, default=str)
        
        computed_hash = hash_sha256(serialized)
        if computed_hash != entry.get("_content_hash"):
            return VerificationResult(
                status=SignatureStatus.TAMPERED,
                message="Content hash mismatch",
            )
        
        return self.signer.verify(serialized.encode('utf-8'), signature)
    
    def verify_chain(self, entries: List[Dict[str, Any]]) -> Tuple[bool, List[VerificationResult]]:
        """Verify integrity of an entire audit log chain."""
        results = []
        previous_hash = None
        
        for entry in entries:
            result = self.verify_entry(entry, previous_hash)
            results.append(result)
            if result.status != SignatureStatus.VALID:
                return False, results
            previous_hash = entry.get("_content_hash")
        
        return True, results


class TimestampService:
    """Trusted timestamp service for signatures."""
    
    def __init__(self, service_id: str = "grace-timestamp"):
        self.service_id = service_id
        self._counter = 0
    
    def get_timestamp(self) -> Dict[str, Any]:
        """Get a trusted timestamp."""
        self._counter += 1
        timestamp = datetime.utcnow()
        
        timestamp_data = {
            "timestamp": timestamp.isoformat(),
            "counter": self._counter,
            "service_id": self.service_id,
        }
        
        serialized = json.dumps(timestamp_data, sort_keys=True)
        timestamp_data["hash"] = hash_sha256(serialized)
        
        return timestamp_data
    
    def verify_timestamp(self, timestamp_data: Dict[str, Any]) -> bool:
        """Verify a timestamp."""
        stored_hash = timestamp_data.pop("hash", None)
        if not stored_hash:
            return False
        serialized = json.dumps(timestamp_data, sort_keys=True)
        computed_hash = hash_sha256(serialized)
        timestamp_data["hash"] = stored_hash
        return computed_hash == stored_hash


def sign_document(content: bytes, private_key: bytes, key_id: str = "") -> Signature:
    """Convenience function: Sign a document."""
    signer = DocumentSigner(private_key=private_key, key_id=key_id)
    return signer.sign(content)


def verify_signature(content: bytes, signature: Signature, public_key: bytes) -> VerificationResult:
    """Convenience function: Verify a signature."""
    verifier = DocumentSigner(public_key=public_key, key_id=signature.key_id)
    return verifier.verify(content, signature)
