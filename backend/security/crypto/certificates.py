"""
Certificate Management for GRACE

Provides comprehensive certificate handling:
- Self-signed certificate generation
- CSR generation
- Certificate validation
- Certificate chain verification
- Certificate expiration monitoring
- OCSP/CRL checking
"""

import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .hashing import hash_sha256

logger = logging.getLogger(__name__)


class CertificateType(Enum):
    """Certificate types."""
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    END_ENTITY = "end_entity"
    CODE_SIGNING = "code_signing"
    CLIENT_AUTH = "client_auth"
    SERVER_AUTH = "server_auth"


class CertificateStatus(Enum):
    """Certificate validation status."""
    VALID = "valid"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"
    REVOKED = "revoked"
    UNKNOWN = "unknown"
    CHAIN_INVALID = "chain_invalid"
    SIGNATURE_INVALID = "signature_invalid"


class KeyUsage(Enum):
    """X.509 key usage extensions."""
    DIGITAL_SIGNATURE = "digitalSignature"
    NON_REPUDIATION = "nonRepudiation"
    KEY_ENCIPHERMENT = "keyEncipherment"
    DATA_ENCIPHERMENT = "dataEncipherment"
    KEY_AGREEMENT = "keyAgreement"
    KEY_CERT_SIGN = "keyCertSign"
    CRL_SIGN = "cRLSign"


class ExtendedKeyUsage(Enum):
    """X.509 extended key usage."""
    SERVER_AUTH = "serverAuth"
    CLIENT_AUTH = "clientAuth"
    CODE_SIGNING = "codeSigning"
    EMAIL_PROTECTION = "emailProtection"
    TIME_STAMPING = "timeStamping"
    OCSP_SIGNING = "OCSPSigning"


@dataclass
class CertificateSubject:
    """Certificate subject/issuer information."""
    common_name: str
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    email: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {"CN": self.common_name}
        if self.organization:
            result["O"] = self.organization
        if self.organizational_unit:
            result["OU"] = self.organizational_unit
        if self.country:
            result["C"] = self.country
        if self.state:
            result["ST"] = self.state
        if self.locality:
            result["L"] = self.locality
        if self.email:
            result["emailAddress"] = self.email
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CertificateSubject':
        """Create from dictionary."""
        return cls(
            common_name=data.get("CN", ""),
            organization=data.get("O"),
            organizational_unit=data.get("OU"),
            country=data.get("C"),
            state=data.get("ST"),
            locality=data.get("L"),
            email=data.get("emailAddress"),
        )


@dataclass
class CertificateInfo:
    """Certificate information."""
    serial_number: str
    subject: CertificateSubject
    issuer: CertificateSubject
    not_before: datetime
    not_after: datetime
    public_key: bytes
    signature: bytes
    signature_algorithm: str
    key_usage: List[KeyUsage] = field(default_factory=list)
    extended_key_usage: List[ExtendedKeyUsage] = field(default_factory=list)
    is_ca: bool = False
    path_length: Optional[int] = None
    san: List[str] = field(default_factory=list)
    fingerprint_sha256: str = ""
    version: int = 3
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "serial_number": self.serial_number,
            "subject": self.subject.to_dict(),
            "issuer": self.issuer.to_dict(),
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "public_key": base64.b64encode(self.public_key).decode('ascii'),
            "signature": base64.b64encode(self.signature).decode('ascii'),
            "signature_algorithm": self.signature_algorithm,
            "key_usage": [ku.value for ku in self.key_usage],
            "extended_key_usage": [eku.value for eku in self.extended_key_usage],
            "is_ca": self.is_ca,
            "path_length": self.path_length,
            "san": self.san,
            "fingerprint_sha256": self.fingerprint_sha256,
            "version": self.version,
        }


@dataclass
class CSRInfo:
    """Certificate Signing Request information."""
    subject: CertificateSubject
    public_key: bytes
    signature: bytes
    signature_algorithm: str
    san: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Certificate validation result."""
    status: CertificateStatus
    message: str = ""
    expires_in_days: Optional[int] = None
    chain_length: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


class CertificateGenerator:
    """Generate X.509 certificates."""
    
    def __init__(self):
        self._crypto_available = False
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa, ec
            from cryptography.hazmat.backends import default_backend
            from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
            self._crypto_available = True
        except ImportError:
            logger.warning("cryptography library not available for certificate generation")
    
    def generate_self_signed(
        self,
        subject: CertificateSubject,
        private_key: bytes,
        validity_days: int = 365,
        key_usage: Optional[List[KeyUsage]] = None,
        extended_key_usage: Optional[List[ExtendedKeyUsage]] = None,
        is_ca: bool = False,
        san: Optional[List[str]] = None,
    ) -> Tuple[bytes, CertificateInfo]:
        """Generate a self-signed certificate."""
        if not self._crypto_available:
            raise RuntimeError("cryptography library required")
        
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        
        priv_key = serialization.load_pem_private_key(private_key, None, default_backend())
        pub_key = priv_key.public_key()
        
        name = self._build_name(subject)
        
        now = datetime.utcnow()
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(name)
        builder = builder.issuer_name(name)
        builder = builder.public_key(pub_key)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + timedelta(days=validity_days))
        
        ku_flags = self._build_key_usage(key_usage, is_ca)
        builder = builder.add_extension(ku_flags, critical=True)
        
        builder = builder.add_extension(
            x509.BasicConstraints(ca=is_ca, path_length=0 if is_ca else None),
            critical=True
        )
        
        if extended_key_usage:
            eku_oids = self._get_eku_oids(extended_key_usage)
            builder = builder.add_extension(
                x509.ExtendedKeyUsage(eku_oids),
                critical=False
            )
        
        if san:
            san_entries = self._build_san(san)
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_entries),
                critical=False
            )
        
        certificate = builder.sign(priv_key, hashes.SHA256(), default_backend())
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        
        cert_info = CertificateInfo(
            serial_number=str(certificate.serial_number),
            subject=subject,
            issuer=subject,
            not_before=certificate.not_valid_before_utc if hasattr(certificate, 'not_valid_before_utc') else certificate.not_valid_before,
            not_after=certificate.not_valid_after_utc if hasattr(certificate, 'not_valid_after_utc') else certificate.not_valid_after,
            public_key=pub_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            signature=certificate.signature,
            signature_algorithm="sha256WithRSAEncryption",
            key_usage=key_usage or [],
            extended_key_usage=extended_key_usage or [],
            is_ca=is_ca,
            san=san or [],
            fingerprint_sha256=hash_sha256(cert_pem),
        )
        
        return cert_pem, cert_info
    
    def generate_csr(
        self,
        subject: CertificateSubject,
        private_key: bytes,
        san: Optional[List[str]] = None,
    ) -> Tuple[bytes, CSRInfo]:
        """Generate a Certificate Signing Request."""
        if not self._crypto_available:
            raise RuntimeError("cryptography library required")
        
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        
        priv_key = serialization.load_pem_private_key(private_key, None, default_backend())
        
        name = self._build_name(subject)
        
        builder = x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(name)
        
        if san:
            san_entries = self._build_san(san)
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_entries),
                critical=False
            )
        
        csr = builder.sign(priv_key, hashes.SHA256(), default_backend())
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        
        csr_info = CSRInfo(
            subject=subject,
            public_key=csr.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            signature=csr.signature,
            signature_algorithm="sha256WithRSAEncryption",
            san=san or [],
        )
        
        return csr_pem, csr_info
    
    def sign_csr(
        self,
        csr_pem: bytes,
        ca_cert_pem: bytes,
        ca_private_key: bytes,
        validity_days: int = 365,
        is_ca: bool = False,
    ) -> bytes:
        """Sign a CSR with a CA certificate."""
        if not self._crypto_available:
            raise RuntimeError("cryptography library required")
        
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        
        csr = x509.load_pem_x509_csr(csr_pem, default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
        ca_key = serialization.load_pem_private_key(ca_private_key, None, default_backend())
        
        now = datetime.utcnow()
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(csr.subject)
        builder = builder.issuer_name(ca_cert.subject)
        builder = builder.public_key(csr.public_key())
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + timedelta(days=validity_days))
        
        builder = builder.add_extension(
            x509.BasicConstraints(ca=is_ca, path_length=None),
            critical=True
        )
        
        for extension in csr.extensions:
            builder = builder.add_extension(extension.value, extension.critical)
        
        certificate = builder.sign(ca_key, hashes.SHA256(), default_backend())
        return certificate.public_bytes(serialization.Encoding.PEM)
    
    def _build_name(self, subject: CertificateSubject):
        """Build X.509 name from subject."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        
        attrs = [x509.NameAttribute(NameOID.COMMON_NAME, subject.common_name)]
        if subject.organization:
            attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, subject.organization))
        if subject.organizational_unit:
            attrs.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, subject.organizational_unit))
        if subject.country:
            attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, subject.country))
        if subject.state:
            attrs.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, subject.state))
        if subject.locality:
            attrs.append(x509.NameAttribute(NameOID.LOCALITY_NAME, subject.locality))
        if subject.email:
            attrs.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, subject.email))
        return x509.Name(attrs)
    
    def _build_key_usage(self, key_usage: Optional[List[KeyUsage]], is_ca: bool):
        """Build key usage extension."""
        from cryptography import x509
        
        if is_ca:
            return x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False,
            )
        
        flags = {
            "digital_signature": False,
            "key_cert_sign": False,
            "crl_sign": False,
            "key_encipherment": False,
            "data_encipherment": False,
            "key_agreement": False,
            "content_commitment": False,
            "encipher_only": False,
            "decipher_only": False,
        }
        
        if key_usage:
            for ku in key_usage:
                if ku == KeyUsage.DIGITAL_SIGNATURE:
                    flags["digital_signature"] = True
                elif ku == KeyUsage.NON_REPUDIATION:
                    flags["content_commitment"] = True
                elif ku == KeyUsage.KEY_ENCIPHERMENT:
                    flags["key_encipherment"] = True
                elif ku == KeyUsage.DATA_ENCIPHERMENT:
                    flags["data_encipherment"] = True
                elif ku == KeyUsage.KEY_AGREEMENT:
                    flags["key_agreement"] = True
                elif ku == KeyUsage.KEY_CERT_SIGN:
                    flags["key_cert_sign"] = True
                elif ku == KeyUsage.CRL_SIGN:
                    flags["crl_sign"] = True
        else:
            flags["digital_signature"] = True
            flags["key_encipherment"] = True
        
        return x509.KeyUsage(**flags)
    
    def _get_eku_oids(self, extended_key_usage: List[ExtendedKeyUsage]):
        """Get extended key usage OIDs."""
        from cryptography.x509.oid import ExtendedKeyUsageOID
        
        oid_map = {
            ExtendedKeyUsage.SERVER_AUTH: ExtendedKeyUsageOID.SERVER_AUTH,
            ExtendedKeyUsage.CLIENT_AUTH: ExtendedKeyUsageOID.CLIENT_AUTH,
            ExtendedKeyUsage.CODE_SIGNING: ExtendedKeyUsageOID.CODE_SIGNING,
            ExtendedKeyUsage.EMAIL_PROTECTION: ExtendedKeyUsageOID.EMAIL_PROTECTION,
            ExtendedKeyUsage.TIME_STAMPING: ExtendedKeyUsageOID.TIME_STAMPING,
            ExtendedKeyUsage.OCSP_SIGNING: ExtendedKeyUsageOID.OCSP_SIGNING,
        }
        return [oid_map[eku] for eku in extended_key_usage if eku in oid_map]
    
    def _build_san(self, san: List[str]):
        """Build Subject Alternative Name entries."""
        from cryptography import x509
        import ipaddress
        
        entries = []
        for name in san:
            if name.startswith("DNS:"):
                entries.append(x509.DNSName(name[4:]))
            elif name.startswith("IP:"):
                entries.append(x509.IPAddress(ipaddress.ip_address(name[3:])))
            elif name.startswith("email:"):
                entries.append(x509.RFC822Name(name[6:]))
            else:
                entries.append(x509.DNSName(name))
        return entries


class CertificateValidator:
    """Validate X.509 certificates."""
    
    def __init__(self):
        self._crypto_available = False
        try:
            from cryptography import x509
            self._crypto_available = True
        except ImportError:
            logger.warning("cryptography library not available")
    
    def validate(self, cert_pem: bytes) -> ValidationResult:
        """Validate a certificate."""
        if not self._crypto_available:
            return ValidationResult(
                status=CertificateStatus.UNKNOWN,
                message="cryptography library not available",
            )
        
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        try:
            cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
        except Exception as e:
            return ValidationResult(
                status=CertificateStatus.UNKNOWN,
                message=f"Failed to parse certificate: {e}",
            )
        
        now = datetime.utcnow()
        not_before = cert.not_valid_before_utc if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before
        not_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
        
        if now < not_before:
            return ValidationResult(
                status=CertificateStatus.NOT_YET_VALID,
                message=f"Certificate not valid until {not_before}",
            )
        
        if now > not_after:
            return ValidationResult(
                status=CertificateStatus.EXPIRED,
                message=f"Certificate expired on {not_after}",
            )
        
        expires_in = (not_after - now).days
        
        return ValidationResult(
            status=CertificateStatus.VALID,
            message="Certificate is valid",
            expires_in_days=expires_in,
        )
    
    def validate_chain(self, cert_chain: List[bytes]) -> ValidationResult:
        """Validate a certificate chain."""
        if not cert_chain:
            return ValidationResult(
                status=CertificateStatus.CHAIN_INVALID,
                message="Empty certificate chain",
            )
        
        if not self._crypto_available:
            return ValidationResult(
                status=CertificateStatus.UNKNOWN,
                message="cryptography library not available",
            )
        
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        for i, cert_pem in enumerate(cert_chain):
            result = self.validate(cert_pem)
            if result.status != CertificateStatus.VALID:
                result.details["failed_at_index"] = i
                return result
        
        for i in range(len(cert_chain) - 1):
            cert = x509.load_pem_x509_certificate(cert_chain[i], default_backend())
            issuer_cert = x509.load_pem_x509_certificate(cert_chain[i + 1], default_backend())
            
            if cert.issuer != issuer_cert.subject:
                return ValidationResult(
                    status=CertificateStatus.CHAIN_INVALID,
                    message=f"Chain broken at index {i}: issuer mismatch",
                    chain_length=len(cert_chain),
                )
        
        return ValidationResult(
            status=CertificateStatus.VALID,
            message="Certificate chain is valid",
            chain_length=len(cert_chain),
        )


class CertificateMonitor:
    """Monitor certificate expiration."""
    
    def __init__(self, warning_days: int = 30, critical_days: int = 7):
        self.warning_days = warning_days
        self.critical_days = critical_days
        self._certificates: Dict[str, Tuple[bytes, datetime]] = {}
        self._validator = CertificateValidator()
    
    def add_certificate(self, cert_id: str, cert_pem: bytes):
        """Add a certificate to monitor."""
        result = self._validator.validate(cert_pem)
        if result.expires_in_days is not None:
            now = datetime.utcnow()
            expires_at = now + timedelta(days=result.expires_in_days)
            self._certificates[cert_id] = (cert_pem, expires_at)
    
    def remove_certificate(self, cert_id: str):
        """Remove a certificate from monitoring."""
        self._certificates.pop(cert_id, None)
    
    def check_expiration(self) -> Dict[str, Dict[str, Any]]:
        """Check all certificates for expiration."""
        now = datetime.utcnow()
        results = {}
        
        for cert_id, (cert_pem, expires_at) in self._certificates.items():
            days_left = (expires_at - now).days
            
            if days_left < 0:
                status = "expired"
            elif days_left <= self.critical_days:
                status = "critical"
            elif days_left <= self.warning_days:
                status = "warning"
            else:
                status = "ok"
            
            results[cert_id] = {
                "status": status,
                "expires_at": expires_at.isoformat(),
                "days_remaining": days_left,
            }
        
        return results
    
    def get_expiring_soon(self) -> List[str]:
        """Get certificates expiring within warning period."""
        now = datetime.utcnow()
        warning_threshold = now + timedelta(days=self.warning_days)
        
        return [
            cert_id
            for cert_id, (_, expires_at) in self._certificates.items()
            if expires_at <= warning_threshold
        ]


class RevocationChecker:
    """Check certificate revocation status."""
    
    def __init__(self):
        self._crl_cache: Dict[str, Tuple[bytes, datetime]] = {}
        self._revoked_serials: Dict[str, set] = {}
    
    def add_crl(self, issuer_id: str, crl_data: bytes):
        """Add a CRL to the cache."""
        self._crl_cache[issuer_id] = (crl_data, datetime.utcnow())
        self._parse_crl(issuer_id, crl_data)
    
    def _parse_crl(self, issuer_id: str, crl_data: bytes):
        """Parse CRL and extract revoked serial numbers."""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            crl = x509.load_pem_x509_crl(crl_data, default_backend())
            self._revoked_serials[issuer_id] = {
                str(entry.serial_number) for entry in crl
            }
        except Exception:
            self._revoked_serials[issuer_id] = set()
    
    def is_revoked(self, cert_pem: bytes, issuer_id: str) -> Tuple[bool, str]:
        """Check if a certificate is revoked."""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
            serial = str(cert.serial_number)
            
            if issuer_id not in self._revoked_serials:
                return False, "No CRL available for issuer"
            
            if serial in self._revoked_serials[issuer_id]:
                return True, "Certificate is revoked"
            
            return False, "Certificate is not revoked"
        except Exception as e:
            return False, f"Unable to check revocation: {e}"


def generate_self_signed_cert(
    common_name: str,
    private_key: bytes,
    validity_days: int = 365,
) -> Tuple[bytes, CertificateInfo]:
    """Convenience function: Generate self-signed certificate."""
    generator = CertificateGenerator()
    subject = CertificateSubject(common_name=common_name)
    return generator.generate_self_signed(subject, private_key, validity_days)


def validate_certificate(cert_pem: bytes) -> ValidationResult:
    """Convenience function: Validate a certificate."""
    return CertificateValidator().validate(cert_pem)


def generate_csr(
    common_name: str,
    private_key: bytes,
) -> Tuple[bytes, CSRInfo]:
    """Convenience function: Generate CSR."""
    generator = CertificateGenerator()
    subject = CertificateSubject(common_name=common_name)
    return generator.generate_csr(subject, private_key)
