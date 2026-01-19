"""
COVI-SHIELD Certificate Authority

Issues and manages verification certificates.

Capabilities:
- Certificate generation with cryptographic signatures
- Certificate validation and verification
- Certificate revocation
- Certificate chain management
"""

import hashlib
import hmac
import logging
import secrets
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .models import (
    VerificationCertificate,
    VerificationResult,
    ProofType,
    CertificateStatus,
    RiskLevel
)

logger = logging.getLogger(__name__)


# ============================================================================
# CERTIFICATE TYPES
# ============================================================================

class CertificateType(str, Enum):
    """Types of certificates issued."""
    VERIFICATION = "verification"      # Code verification certificate
    REPAIR = "repair"                   # Repair validation certificate
    COMPLIANCE = "compliance"           # Compliance certificate
    DEPLOYMENT = "deployment"           # Deployment approval certificate
    AUDIT = "audit"                     # Audit trail certificate


# ============================================================================
# CERTIFICATE AUTHORITY
# ============================================================================

class CertificateAuthority:
    """
    COVI-SHIELD Certificate Authority.

    Manages the lifecycle of verification certificates:
    - Issuance with cryptographic signatures
    - Validation and verification
    - Revocation
    - Audit trails
    """

    def __init__(
        self,
        authority_name: str = "COVI-SHIELD-CA",
        secret_key: Optional[str] = None
    ):
        self.authority_name = authority_name
        self.secret_key = secret_key or secrets.token_hex(32)

        # Certificate storage
        self.issued_certificates: Dict[str, VerificationCertificate] = {}
        self.revoked_certificates: Dict[str, str] = {}  # cert_id -> reason

        # Statistics
        self.stats = {
            "certificates_issued": 0,
            "certificates_verified": 0,
            "certificates_revoked": 0,
            "verification_failures": 0
        }

        logger.info(f"[COVI-SHIELD] Certificate Authority '{authority_name}' initialized")

    def issue_certificate(
        self,
        verification_result: VerificationResult,
        certificate_type: CertificateType = CertificateType.VERIFICATION,
        validity_hours: int = 24,
        properties_verified: Optional[List[str]] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> VerificationCertificate:
        """
        Issue a new verification certificate.

        Args:
            verification_result: Verification result to certify
            certificate_type: Type of certificate
            validity_hours: Validity period in hours
            properties_verified: List of verified properties
            additional_claims: Additional claims to include

        Returns:
            Issued VerificationCertificate
        """
        start_time = time.time()

        # Determine certificate status based on verification
        if verification_result.risk_level == RiskLevel.CRITICAL:
            status = CertificateStatus.INVALID
        elif verification_result.success:
            status = CertificateStatus.VALID
        else:
            status = CertificateStatus.PENDING

        # Extract properties from verification
        if properties_verified is None:
            properties_verified = [
                p.get("property_id", "")
                for p in verification_result.proofs
                if p.get("verified", False)
            ]

        # Create certificate
        certificate = VerificationCertificate(
            genesis_key_id=verification_result.genesis_key_id,
            status=status,
            properties_verified=properties_verified,
            proof_type=self._determine_proof_type(verification_result),
            proof_data={
                "certificate_type": certificate_type.value,
                "verification_result_id": verification_result.result_id,
                "issues_found": verification_result.issues_found,
                "issues_fixed": verification_result.issues_fixed,
                "risk_level": verification_result.risk_level.value,
                "metrics": verification_result.metrics,
                "additional_claims": additional_claims or {}
            },
            assumptions=self._extract_assumptions(verification_result),
            witness=self._generate_witness(verification_result),
            expires_at=datetime.utcnow() + timedelta(hours=validity_hours)
        )

        # Sign the certificate
        certificate.signature = self._sign_certificate(certificate)

        # Store certificate
        self.issued_certificates[certificate.certificate_id] = certificate
        self.stats["certificates_issued"] += 1

        logger.info(
            f"[COVI-SHIELD] Issued certificate {certificate.certificate_id}: "
            f"status={status.value}, properties={len(properties_verified)}, "
            f"expires={certificate.expires_at.isoformat()}"
        )

        return certificate

    def verify_certificate(
        self,
        certificate: VerificationCertificate,
        check_revocation: bool = True
    ) -> Tuple[bool, str]:
        """
        Verify a certificate's validity.

        Args:
            certificate: Certificate to verify
            check_revocation: Whether to check revocation list

        Returns:
            Tuple of (is_valid, reason)
        """
        self.stats["certificates_verified"] += 1

        # Check revocation first (most authoritative check)
        if check_revocation:
            if certificate.certificate_id in self.revoked_certificates:
                reason = self.revoked_certificates[certificate.certificate_id]
                return False, f"Certificate revoked: {reason}"

        # Check if unsigned
        if not certificate.signature:
            self.stats["verification_failures"] += 1
            return False, "Certificate is unsigned"

        # Get original certificate from store to verify signature
        # (revocation may have changed the status on this object)
        original_status = certificate.status
        stored_cert = self.issued_certificates.get(certificate.certificate_id)
        if stored_cert and stored_cert.status != original_status:
            # Restore original status for signature check
            original_status = CertificateStatus.VALID

        # Check signature using original status
        temp_status = certificate.status
        certificate.status = original_status
        expected_signature = self._sign_certificate(certificate)
        certificate.status = temp_status

        if certificate.signature != expected_signature:
            self.stats["verification_failures"] += 1
            return False, "Invalid signature"

        # Check expiration
        if certificate.expires_at and datetime.utcnow() > certificate.expires_at:
            return False, "Certificate expired"

        # Check current status
        if certificate.status != CertificateStatus.VALID:
            return False, f"Certificate status is {certificate.status.value}"

        return True, "Certificate is valid"

    def revoke_certificate(
        self,
        certificate_id: str,
        reason: str
    ) -> bool:
        """
        Revoke a certificate.

        Args:
            certificate_id: ID of certificate to revoke
            reason: Reason for revocation

        Returns:
            True if revoked, False if not found
        """
        if certificate_id in self.issued_certificates:
            certificate = self.issued_certificates[certificate_id]
            certificate.status = CertificateStatus.REVOKED
            self.revoked_certificates[certificate_id] = reason
            self.stats["certificates_revoked"] += 1

            logger.info(
                f"[COVI-SHIELD] Revoked certificate {certificate_id}: {reason}"
            )
            return True

        return False

    def _sign_certificate(self, certificate: VerificationCertificate) -> str:
        """Generate cryptographic signature for certificate."""
        # Create message to sign
        message = "|".join([
            certificate.certificate_id,
            certificate.genesis_key_id or "",
            certificate.status.value,
            ",".join(certificate.properties_verified),
            certificate.proof_type.value,
            certificate.issued_at.isoformat()
        ])

        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _determine_proof_type(
        self,
        verification_result: VerificationResult
    ) -> ProofType:
        """Determine primary proof type from verification."""
        # Check which proofs were generated
        proofs = verification_result.proofs

        if not proofs:
            return ProofType.TYPE_SAFETY  # Default

        # Count proof types
        type_counts = {}
        for proof in proofs:
            proof_type = proof.get("proof_type", "")
            type_counts[proof_type] = type_counts.get(proof_type, 0) + 1

        # Return most common
        if type_counts:
            most_common = max(type_counts.items(), key=lambda x: x[1])
            try:
                return ProofType(most_common[0])
            except ValueError:
                pass

        return ProofType.TYPE_SAFETY

    def _extract_assumptions(
        self,
        verification_result: VerificationResult
    ) -> List[str]:
        """Extract assumptions from verification result."""
        assumptions = [
            "Standard Python semantics",
            "No external side effects during verification",
            f"Verification performed at {datetime.utcnow().isoformat()}"
        ]

        # Add assumptions from proofs
        for proof in verification_result.proofs:
            proof_assumptions = proof.get("assumptions", [])
            assumptions.extend(proof_assumptions)

        return list(set(assumptions))  # Remove duplicates

    def _generate_witness(
        self,
        verification_result: VerificationResult
    ) -> str:
        """Generate witness string for certificate."""
        return (
            f"Verified by {self.authority_name} at {datetime.utcnow().isoformat()}. "
            f"Verification ID: {verification_result.result_id}. "
            f"Properties verified: {len([p for p in verification_result.proofs if p.get('verified', False)])}. "
            f"Risk level: {verification_result.risk_level.value}."
        )

    def get_certificate(
        self,
        certificate_id: str
    ) -> Optional[VerificationCertificate]:
        """Get a certificate by ID."""
        return self.issued_certificates.get(certificate_id)

    def get_certificates_for_genesis_key(
        self,
        genesis_key_id: str
    ) -> List[VerificationCertificate]:
        """Get all certificates for a Genesis Key."""
        return [
            cert for cert in self.issued_certificates.values()
            if cert.genesis_key_id == genesis_key_id
        ]

    def get_valid_certificates(self) -> List[VerificationCertificate]:
        """Get all currently valid certificates."""
        now = datetime.utcnow()
        return [
            cert for cert in self.issued_certificates.values()
            if cert.status == CertificateStatus.VALID
            and (not cert.expires_at or cert.expires_at > now)
            and cert.certificate_id not in self.revoked_certificates
        ]

    def audit_certificate(
        self,
        certificate_id: str
    ) -> Dict[str, Any]:
        """Generate audit report for a certificate."""
        certificate = self.issued_certificates.get(certificate_id)

        if not certificate:
            return {"error": "Certificate not found"}

        is_valid, reason = self.verify_certificate(certificate)

        return {
            "certificate_id": certificate_id,
            "genesis_key_id": certificate.genesis_key_id,
            "status": certificate.status.value,
            "is_currently_valid": is_valid,
            "validity_reason": reason,
            "issued_at": certificate.issued_at.isoformat(),
            "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None,
            "properties_verified": certificate.properties_verified,
            "proof_type": certificate.proof_type.value,
            "assumptions": certificate.assumptions,
            "witness": certificate.witness,
            "is_revoked": certificate_id in self.revoked_certificates,
            "revocation_reason": self.revoked_certificates.get(certificate_id),
            "audited_at": datetime.utcnow().isoformat()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get certificate authority statistics."""
        now = datetime.utcnow()
        valid_count = len([
            c for c in self.issued_certificates.values()
            if c.status == CertificateStatus.VALID
            and (not c.expires_at or c.expires_at > now)
            and c.certificate_id not in self.revoked_certificates
        ])

        return {
            **self.stats,
            "certificates_active": valid_count,
            "certificates_expired": len(self.issued_certificates) - valid_count - len(self.revoked_certificates),
            "authority_name": self.authority_name
        }
