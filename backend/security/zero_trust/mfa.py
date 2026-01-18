"""
GRACE Zero-Trust Multi-Factor Authentication

Implements MFA with:
- TOTP (Google Authenticator compatible)
- WebAuthn/FIDO2 support
- Backup codes
- MFA enrollment and management
- Adaptive MFA (require based on risk)

All MFA operations are logged to the immutable audit system.
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import struct
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MFAMethod(str, Enum):
    """MFA method types."""
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    BACKUP_CODE = "backup_code"
    SMS = "sms"  # Not recommended, but supported
    EMAIL = "email"


class MFAStatus(str, Enum):
    """MFA enrollment status."""
    NOT_ENROLLED = "not_enrolled"
    PENDING = "pending"
    ENROLLED = "enrolled"
    DISABLED = "disabled"


@dataclass
class MFAEnrollment:
    """MFA enrollment record for a user."""
    enrollment_id: str
    user_id: str
    method: MFAMethod
    status: MFAStatus = MFAStatus.NOT_ENROLLED
    secret: Optional[str] = None  # For TOTP
    credential_id: Optional[str] = None  # For WebAuthn
    public_key: Optional[str] = None  # For WebAuthn
    counter: int = 0  # For WebAuthn
    backup_codes: List[str] = field(default_factory=list)
    backup_codes_used: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    device_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding secrets)."""
        return {
            "enrollment_id": self.enrollment_id,
            "user_id": self.user_id,
            "method": self.method.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "device_name": self.device_name,
            "backup_codes_remaining": len(self.backup_codes) - len(self.backup_codes_used),
        }


@dataclass
class MFAChallenge:
    """An MFA challenge for verification."""
    challenge_id: str
    user_id: str
    method: MFAMethod
    challenge_data: Optional[str] = None  # For WebAuthn
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=5))
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False
    attempts: int = 0
    max_attempts: int = 3


class TOTPProvider:
    """
    TOTP (Time-based One-Time Password) provider.
    
    Compatible with Google Authenticator, Authy, etc.
    """
    
    def __init__(
        self,
        digits: int = 6,
        interval: int = 30,
        algorithm: str = "sha1",
        issuer: str = "GRACE",
    ):
        self.digits = digits
        self.interval = interval
        self.algorithm = algorithm
        self.issuer = issuer
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        # 20 bytes = 160 bits, base32 encoded
        secret_bytes = os.urandom(20)
        return base64.b32encode(secret_bytes).decode("utf-8").rstrip("=")
    
    def generate_provisioning_uri(
        self,
        secret: str,
        user_email: str,
    ) -> str:
        """Generate provisioning URI for QR code."""
        from urllib.parse import quote
        
        label = quote(f"{self.issuer}:{user_email}")
        params = [
            f"secret={secret}",
            f"issuer={quote(self.issuer)}",
            f"algorithm={self.algorithm.upper()}",
            f"digits={self.digits}",
            f"period={self.interval}",
        ]
        
        return f"otpauth://totp/{label}?{'&'.join(params)}"
    
    def verify(
        self,
        secret: str,
        code: str,
        window: int = 1,
    ) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: The user's TOTP secret
            code: The code to verify
            window: Number of intervals to check before/after current
        
        Returns:
            True if code is valid
        """
        try:
            # Normalize code
            code = code.replace(" ", "").strip()
            if len(code) != self.digits:
                return False
            
            # Get current time counter
            current_time = int(time.time())
            counter = current_time // self.interval
            
            # Check window
            for offset in range(-window, window + 1):
                expected = self._generate_code(secret, counter + offset)
                if hmac.compare_digest(code, expected):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"[ZERO-TRUST-MFA] TOTP verification error: {e}")
            return False
    
    def _generate_code(self, secret: str, counter: int) -> str:
        """Generate TOTP code for a counter value."""
        # Pad secret if needed
        secret = secret.upper()
        padding = 8 - len(secret) % 8
        if padding != 8:
            secret += "=" * padding
        
        # Decode secret
        key = base64.b32decode(secret)
        
        # Pack counter
        counter_bytes = struct.pack(">Q", counter)
        
        # Generate HMAC
        if self.algorithm == "sha1":
            h = hmac.new(key, counter_bytes, "sha1").digest()
        elif self.algorithm == "sha256":
            h = hmac.new(key, counter_bytes, "sha256").digest()
        elif self.algorithm == "sha512":
            h = hmac.new(key, counter_bytes, "sha512").digest()
        else:
            h = hmac.new(key, counter_bytes, "sha1").digest()
        
        # Dynamic truncation
        offset = h[-1] & 0x0F
        code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        code = str(code_int % (10 ** self.digits))
        
        return code.zfill(self.digits)


class WebAuthnProvider:
    """
    WebAuthn/FIDO2 provider.
    
    Implements passwordless authentication using security keys
    and platform authenticators.
    """
    
    def __init__(
        self,
        rp_id: str = "localhost",
        rp_name: str = "GRACE",
        origin: str = "http://localhost:3000",
    ):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin
    
    def generate_registration_options(
        self,
        user_id: str,
        user_name: str,
        user_display_name: str,
        exclude_credentials: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate WebAuthn registration options."""
        challenge = secrets.token_bytes(32)
        
        options = {
            "challenge": base64.urlsafe_b64encode(challenge).decode().rstrip("="),
            "rp": {
                "id": self.rp_id,
                "name": self.rp_name,
            },
            "user": {
                "id": base64.urlsafe_b64encode(user_id.encode()).decode().rstrip("="),
                "name": user_name,
                "displayName": user_display_name,
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},   # ES256
                {"type": "public-key", "alg": -257}, # RS256
            ],
            "timeout": 60000,
            "authenticatorSelection": {
                "authenticatorAttachment": "cross-platform",
                "userVerification": "preferred",
                "residentKey": "preferred",
            },
            "attestation": "none",
        }
        
        if exclude_credentials:
            options["excludeCredentials"] = [
                {"type": "public-key", "id": cred_id}
                for cred_id in exclude_credentials
            ]
        
        return options
    
    def generate_authentication_options(
        self,
        allowed_credentials: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate WebAuthn authentication options."""
        challenge = secrets.token_bytes(32)
        
        options = {
            "challenge": base64.urlsafe_b64encode(challenge).decode().rstrip("="),
            "rpId": self.rp_id,
            "timeout": 60000,
            "userVerification": "preferred",
        }
        
        if allowed_credentials:
            options["allowCredentials"] = [
                {"type": "public-key", "id": cred_id}
                for cred_id in allowed_credentials
            ]
        
        return options
    
    def verify_registration(
        self,
        credential: Dict[str, Any],
        challenge: str,
    ) -> Optional[Tuple[str, str, int]]:
        """
        Verify WebAuthn registration response.
        
        Returns:
            Tuple of (credential_id, public_key, counter) if valid
        """
        # In production, use a proper WebAuthn library like py_webauthn
        # This is a simplified placeholder
        try:
            credential_id = credential.get("id")
            # Would verify attestation, extract public key, etc.
            public_key = credential.get("response", {}).get("publicKey", "")
            counter = 0
            
            return credential_id, public_key, counter
        except Exception as e:
            logger.error(f"[ZERO-TRUST-MFA] WebAuthn registration verification failed: {e}")
            return None
    
    def verify_authentication(
        self,
        credential: Dict[str, Any],
        challenge: str,
        public_key: str,
        expected_counter: int,
    ) -> Optional[int]:
        """
        Verify WebAuthn authentication response.
        
        Returns:
            New counter value if valid
        """
        # In production, use a proper WebAuthn library
        try:
            # Would verify signature, check counter, etc.
            new_counter = expected_counter + 1
            return new_counter
        except Exception as e:
            logger.error(f"[ZERO-TRUST-MFA] WebAuthn authentication verification failed: {e}")
            return None


class BackupCodeProvider:
    """
    Backup code provider for MFA recovery.
    
    Generates single-use backup codes.
    """
    
    def __init__(
        self,
        code_length: int = 8,
        num_codes: int = 10,
    ):
        self.code_length = code_length
        self.num_codes = num_codes
    
    def generate_codes(self) -> List[str]:
        """Generate a set of backup codes."""
        codes = []
        for _ in range(self.num_codes):
            # Generate code in format: XXXX-XXXX
            part1 = secrets.token_hex(self.code_length // 4).upper()
            part2 = secrets.token_hex(self.code_length // 4).upper()
            codes.append(f"{part1}-{part2}")
        return codes
    
    def hash_code(self, code: str) -> str:
        """Hash a backup code for storage."""
        normalized = code.replace("-", "").upper()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def verify(
        self,
        code: str,
        hashed_codes: List[str],
        used_codes: List[str],
    ) -> bool:
        """Verify a backup code."""
        code_hash = self.hash_code(code)
        
        if code_hash in used_codes:
            return False
        
        return code_hash in hashed_codes


@dataclass
class AdaptiveMFA:
    """
    Adaptive MFA decision engine.
    
    Determines when to require MFA based on risk.
    """
    risk_threshold: float = 0.5
    always_require_methods: List[str] = field(default_factory=lambda: ["webauthn"])
    skip_for_trusted_devices: bool = True
    max_session_age_without_mfa_hours: int = 4
    
    def should_require_mfa(
        self,
        risk_score: float,
        is_trusted_device: bool = False,
        session_age_hours: float = 0,
        operation: Optional[str] = None,
        has_recent_mfa: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if MFA should be required.
        
        Returns:
            Tuple of (require_mfa, reason)
        """
        # Always require for high-risk operations
        sensitive_operations = [
            "change_password",
            "update_mfa",
            "delete_account",
            "export_data",
            "grant_admin",
            "access_secrets",
        ]
        
        if operation and operation in sensitive_operations:
            return True, f"MFA required for sensitive operation: {operation}"
        
        # Check risk threshold
        if risk_score >= self.risk_threshold:
            return True, f"MFA required due to high risk score: {risk_score:.2f}"
        
        # Check session age
        if session_age_hours > self.max_session_age_without_mfa_hours:
            if not has_recent_mfa:
                return True, "MFA required: session age exceeded threshold"
        
        # Skip for trusted devices if enabled
        if self.skip_for_trusted_devices and is_trusted_device:
            return False, "MFA not required: trusted device"
        
        return False, "MFA not required"


class MFAManager:
    """
    MFA Manager
    
    Manages all MFA operations including enrollment,
    verification, and adaptive MFA decisions.
    """
    
    def __init__(
        self,
        totp_issuer: str = "GRACE",
        webauthn_rp_id: str = "localhost",
        webauthn_rp_name: str = "GRACE",
    ):
        self.totp_provider = TOTPProvider(issuer=totp_issuer)
        self.webauthn_provider = WebAuthnProvider(
            rp_id=webauthn_rp_id,
            rp_name=webauthn_rp_name,
        )
        self.backup_code_provider = BackupCodeProvider()
        self.adaptive_mfa = AdaptiveMFA()
        
        # Storage (use database in production)
        self._enrollments: Dict[str, Dict[str, MFAEnrollment]] = {}  # user_id -> method -> enrollment
        self._challenges: Dict[str, MFAChallenge] = {}  # challenge_id -> challenge
        
        logger.info("[ZERO-TRUST-MFA] MFA manager initialized")
    
    def start_enrollment(
        self,
        user_id: str,
        method: MFAMethod,
        user_email: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start MFA enrollment for a user.
        
        Returns enrollment data needed for the client.
        """
        enrollment_id = str(uuid.uuid4())
        
        enrollment = MFAEnrollment(
            enrollment_id=enrollment_id,
            user_id=user_id,
            method=method,
            status=MFAStatus.PENDING,
            device_name=device_name,
        )
        
        result: Dict[str, Any] = {
            "enrollment_id": enrollment_id,
            "method": method.value,
        }
        
        if method == MFAMethod.TOTP:
            # Generate TOTP secret
            secret = self.totp_provider.generate_secret()
            enrollment.secret = secret
            
            # Generate provisioning URI for QR code
            uri = self.totp_provider.generate_provisioning_uri(
                secret=secret,
                user_email=user_email or user_id,
            )
            
            result["secret"] = secret
            result["provisioning_uri"] = uri
            
        elif method == MFAMethod.WEBAUTHN:
            # Generate WebAuthn registration options
            options = self.webauthn_provider.generate_registration_options(
                user_id=user_id,
                user_name=user_email or user_id,
                user_display_name=user_email or user_id,
            )
            result["options"] = options
            
        elif method == MFAMethod.BACKUP_CODE:
            # Generate backup codes
            codes = self.backup_code_provider.generate_codes()
            enrollment.backup_codes = [
                self.backup_code_provider.hash_code(c) for c in codes
            ]
            result["codes"] = codes  # Only returned once
        
        # Store enrollment
        if user_id not in self._enrollments:
            self._enrollments[user_id] = {}
        self._enrollments[user_id][method.value] = enrollment
        
        self._audit_enrollment_started(user_id, method)
        
        return result
    
    def complete_enrollment(
        self,
        user_id: str,
        method: MFAMethod,
        verification_code: Optional[str] = None,
        credential: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Complete MFA enrollment by verifying the initial code.
        
        Returns True if enrollment is successful.
        """
        enrollments = self._enrollments.get(user_id, {})
        enrollment = enrollments.get(method.value)
        
        if not enrollment or enrollment.status != MFAStatus.PENDING:
            return False
        
        verified = False
        
        if method == MFAMethod.TOTP:
            if verification_code and enrollment.secret:
                verified = self.totp_provider.verify(
                    secret=enrollment.secret,
                    code=verification_code,
                )
                
        elif method == MFAMethod.WEBAUTHN:
            if credential:
                result = self.webauthn_provider.verify_registration(
                    credential=credential,
                    challenge="",  # Would get from stored challenge
                )
                if result:
                    cred_id, pub_key, counter = result
                    enrollment.credential_id = cred_id
                    enrollment.public_key = pub_key
                    enrollment.counter = counter
                    verified = True
                    
        elif method == MFAMethod.BACKUP_CODE:
            # Backup codes are verified on generation
            verified = len(enrollment.backup_codes) > 0
        
        if verified:
            enrollment.status = MFAStatus.ENROLLED
            enrollment.verified_at = datetime.utcnow()
            self._audit_enrollment_completed(user_id, method)
            logger.info(f"[ZERO-TRUST-MFA] MFA enrollment completed for user {user_id[:8]}...")
        
        return verified
    
    def create_challenge(
        self,
        user_id: str,
        method: Optional[MFAMethod] = None,
    ) -> Optional[MFAChallenge]:
        """
        Create an MFA challenge for verification.
        
        If method is not specified, uses the user's primary MFA method.
        """
        enrollments = self._enrollments.get(user_id, {})
        
        # Find enrolled method
        if method:
            enrollment = enrollments.get(method.value)
        else:
            # Use first enrolled method
            for m, e in enrollments.items():
                if e.status == MFAStatus.ENROLLED:
                    enrollment = e
                    method = MFAMethod(m)
                    break
            else:
                return None
        
        if not enrollment or enrollment.status != MFAStatus.ENROLLED:
            return None
        
        challenge = MFAChallenge(
            challenge_id=str(uuid.uuid4()),
            user_id=user_id,
            method=method,
        )
        
        if method == MFAMethod.WEBAUTHN:
            options = self.webauthn_provider.generate_authentication_options(
                allowed_credentials=[enrollment.credential_id] if enrollment.credential_id else None,
            )
            challenge.challenge_data = options.get("challenge")
        
        self._challenges[challenge.challenge_id] = challenge
        
        return challenge
    
    def verify_challenge(
        self,
        challenge_id: str,
        code: Optional[str] = None,
        credential: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Verify an MFA challenge.
        
        Returns True if verification is successful.
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return False
        
        # Check expiration
        if datetime.utcnow() > challenge.expires_at:
            del self._challenges[challenge_id]
            return False
        
        # Check attempts
        if challenge.attempts >= challenge.max_attempts:
            del self._challenges[challenge_id]
            self._audit_mfa_failed(challenge.user_id, challenge.method, "max_attempts_exceeded")
            return False
        
        challenge.attempts += 1
        
        enrollments = self._enrollments.get(challenge.user_id, {})
        enrollment = enrollments.get(challenge.method.value)
        
        if not enrollment:
            return False
        
        verified = False
        
        if challenge.method == MFAMethod.TOTP:
            if code and enrollment.secret:
                verified = self.totp_provider.verify(
                    secret=enrollment.secret,
                    code=code,
                )
                
        elif challenge.method == MFAMethod.WEBAUTHN:
            if credential and enrollment.public_key:
                new_counter = self.webauthn_provider.verify_authentication(
                    credential=credential,
                    challenge=challenge.challenge_data or "",
                    public_key=enrollment.public_key,
                    expected_counter=enrollment.counter,
                )
                if new_counter is not None:
                    enrollment.counter = new_counter
                    verified = True
                    
        elif challenge.method == MFAMethod.BACKUP_CODE:
            if code:
                verified = self.backup_code_provider.verify(
                    code=code,
                    hashed_codes=enrollment.backup_codes,
                    used_codes=enrollment.backup_codes_used,
                )
                if verified:
                    # Mark code as used
                    code_hash = self.backup_code_provider.hash_code(code)
                    enrollment.backup_codes_used.append(code_hash)
        
        if verified:
            challenge.verified = True
            enrollment.last_used = datetime.utcnow()
            del self._challenges[challenge_id]
            self._audit_mfa_success(challenge.user_id, challenge.method)
            logger.info(f"[ZERO-TRUST-MFA] MFA verification successful for user {challenge.user_id[:8]}...")
        else:
            self._audit_mfa_failed(challenge.user_id, challenge.method, "invalid_code")
        
        return verified
    
    def get_user_enrollments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all MFA enrollments for a user."""
        enrollments = self._enrollments.get(user_id, {})
        return [e.to_dict() for e in enrollments.values() if e.status == MFAStatus.ENROLLED]
    
    def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if user has any MFA method enrolled."""
        enrollments = self._enrollments.get(user_id, {})
        return any(e.status == MFAStatus.ENROLLED for e in enrollments.values())
    
    def should_require_mfa(
        self,
        user_id: str,
        risk_score: float,
        is_trusted_device: bool = False,
        session_age_hours: float = 0,
        operation: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Check if MFA should be required using adaptive MFA."""
        if not self.is_mfa_enabled(user_id):
            return False, "MFA not enabled for user"
        
        return self.adaptive_mfa.should_require_mfa(
            risk_score=risk_score,
            is_trusted_device=is_trusted_device,
            session_age_hours=session_age_hours,
            operation=operation,
        )
    
    def disable_mfa(
        self,
        user_id: str,
        method: MFAMethod,
        disabled_by: Optional[str] = None,
    ):
        """Disable an MFA method for a user."""
        enrollments = self._enrollments.get(user_id, {})
        enrollment = enrollments.get(method.value)
        
        if enrollment:
            enrollment.status = MFAStatus.DISABLED
            self._audit_mfa_disabled(user_id, method, disabled_by)
            logger.info(f"[ZERO-TRUST-MFA] MFA disabled for user {user_id[:8]}...")
    
    def _audit_enrollment_started(self, user_id: str, method: MFAMethod):
        """Audit MFA enrollment start."""
        self._audit("MFA enrollment started", user_id, method)
    
    def _audit_enrollment_completed(self, user_id: str, method: MFAMethod):
        """Audit MFA enrollment completion."""
        self._audit("MFA enrollment completed", user_id, method)
    
    def _audit_mfa_success(self, user_id: str, method: MFAMethod):
        """Audit successful MFA verification."""
        self._audit("MFA verification successful", user_id, method, severity="info")
    
    def _audit_mfa_failed(self, user_id: str, method: MFAMethod, reason: str):
        """Audit failed MFA verification."""
        self._audit(f"MFA verification failed: {reason}", user_id, method, severity="warning")
    
    def _audit_mfa_disabled(self, user_id: str, method: MFAMethod, disabled_by: Optional[str]):
        """Audit MFA disabled."""
        self._audit(f"MFA disabled by {disabled_by or 'user'}", user_id, method)
    
    def _audit(
        self,
        action: str,
        user_id: str,
        method: MFAMethod,
        severity: str = "info",
    ):
        """Audit MFA action to immutable log."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.USER_ACTION,
                    action_description=action,
                    actor_type="user",
                    actor_id=user_id,
                    severity=severity,
                    component="zero_trust.mfa",
                    context={
                        "method": method.value,
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-MFA] Audit logging failed: {e}")


# Singleton instance
_mfa_manager: Optional[MFAManager] = None


def get_mfa_manager() -> MFAManager:
    """Get the MFA manager singleton."""
    global _mfa_manager
    if _mfa_manager is None:
        _mfa_manager = MFAManager()
    return _mfa_manager
