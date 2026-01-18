"""
GRACE Zero-Trust Identity Verification

Implements continuous identity verification with:
- Continuous authentication (re-verify on sensitive operations)
- Device fingerprinting and binding
- Session risk scoring
- Step-up authentication triggers
- Identity federation (SAML, OIDC, OAuth2)

All identity decisions are logged to the immutable audit system.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class FederationType(str, Enum):
    """Identity federation types."""
    SAML = "saml"
    OIDC = "oidc"
    OAUTH2 = "oauth2"
    LOCAL = "local"


class StepUpTrigger(str, Enum):
    """Triggers for step-up authentication."""
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PAYMENT_ACTION = "payment_action"
    CONFIGURATION_CHANGE = "configuration_change"
    NEW_DEVICE = "new_device"
    UNUSUAL_LOCATION = "unusual_location"
    HIGH_RISK_SCORE = "high_risk_score"
    SESSION_AGE = "session_age"
    MFA_REQUIRED = "mfa_required"
    ADMIN_ACTION = "admin_action"


@dataclass
class DeviceFingerprint:
    """Device fingerprint for binding sessions to devices."""
    fingerprint_id: str
    user_agent: str
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    platform: Optional[str] = None
    canvas_hash: Optional[str] = None
    webgl_hash: Optional[str] = None
    audio_hash: Optional[str] = None
    fonts_hash: Optional[str] = None
    plugins_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    trust_score: float = 0.5
    is_known_device: bool = False
    
    def compute_hash(self) -> str:
        """Compute a stable hash of the device fingerprint."""
        components = [
            self.user_agent or "",
            self.screen_resolution or "",
            self.timezone or "",
            self.language or "",
            self.platform or "",
            self.canvas_hash or "",
            self.webgl_hash or "",
        ]
        fingerprint_str = "|".join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
    
    def similarity_score(self, other: "DeviceFingerprint") -> float:
        """Calculate similarity between two fingerprints (0.0 to 1.0)."""
        if not other:
            return 0.0
        
        matching = 0
        total = 0
        
        comparisons = [
            (self.user_agent, other.user_agent),
            (self.screen_resolution, other.screen_resolution),
            (self.timezone, other.timezone),
            (self.language, other.language),
            (self.platform, other.platform),
            (self.canvas_hash, other.canvas_hash),
            (self.webgl_hash, other.webgl_hash),
        ]
        
        for a, b in comparisons:
            if a and b:
                total += 1
                if a == b:
                    matching += 1
        
        return matching / total if total > 0 else 0.0


@dataclass
class SessionRiskScore:
    """Risk score for a session with contributing factors."""
    score: float  # 0.0 (low risk) to 1.0 (high risk)
    factors: Dict[str, float] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    requires_step_up: bool = False
    step_up_reason: Optional[StepUpTrigger] = None
    
    @property
    def risk_level(self) -> str:
        """Human-readable risk level."""
        if self.score < 0.25:
            return "low"
        elif self.score < 0.50:
            return "medium"
        elif self.score < 0.75:
            return "high"
        else:
            return "critical"
    
    def add_factor(self, name: str, value: float, weight: float = 1.0):
        """Add a risk factor."""
        self.factors[name] = value * weight
        self._recalculate()
    
    def _recalculate(self):
        """Recalculate overall score from factors."""
        if self.factors:
            self.score = min(1.0, sum(self.factors.values()) / len(self.factors))


@dataclass
class IdentityFederationProvider:
    """Configuration for identity federation provider."""
    provider_id: str
    name: str
    federation_type: FederationType
    issuer: str
    client_id: str
    client_secret: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    enabled: bool = True
    metadata_url: Optional[str] = None  # For OIDC discovery
    saml_metadata: Optional[str] = None  # For SAML
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding secrets)."""
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "federation_type": self.federation_type.value,
            "issuer": self.issuer,
            "client_id": self.client_id,
            "scopes": self.scopes,
            "enabled": self.enabled,
        }


@dataclass
class VerificationResult:
    """Result of identity verification."""
    verified: bool
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    risk_score: Optional[SessionRiskScore] = None
    requires_step_up: bool = False
    step_up_triggers: List[StepUpTrigger] = field(default_factory=list)
    device_fingerprint: Optional[DeviceFingerprint] = None
    federation_provider: Optional[str] = None
    error_message: Optional[str] = None
    verified_at: datetime = field(default_factory=datetime.utcnow)


class IdentityVerifier:
    """
    Zero-Trust Identity Verifier
    
    Implements continuous authentication with:
    - Session validation
    - Device binding
    - Risk-based step-up authentication
    - Identity federation support
    """
    
    def __init__(
        self,
        step_up_threshold: float = 0.6,
        session_timeout_minutes: int = 30,
        max_session_age_hours: int = 24,
        device_binding_enabled: bool = True,
        continuous_auth_interval_minutes: int = 5,
    ):
        self.step_up_threshold = step_up_threshold
        self.session_timeout_minutes = session_timeout_minutes
        self.max_session_age_hours = max_session_age_hours
        self.device_binding_enabled = device_binding_enabled
        self.continuous_auth_interval_minutes = continuous_auth_interval_minutes
        
        # Storage (use Redis/database in production)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._devices: Dict[str, Dict[str, DeviceFingerprint]] = {}  # user_id -> device_id -> fingerprint
        self._federation_providers: Dict[str, IdentityFederationProvider] = {}
        self._step_up_completions: Dict[str, datetime] = {}  # session_id -> completion time
        
        # Sensitive operations that require step-up
        self._sensitive_operations: Set[str] = {
            "delete_data",
            "export_data",
            "change_password",
            "update_mfa",
            "grant_admin",
            "modify_policy",
            "access_secrets",
            "deploy_code",
        }
        
        logger.info("[ZERO-TRUST-IDENTITY] Identity verifier initialized")
    
    def verify_identity(
        self,
        session_id: str,
        user_id: str,
        device_fingerprint: Optional[DeviceFingerprint] = None,
        operation: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Verify identity with continuous authentication.
        
        Returns verification result with risk assessment.
        """
        try:
            # Check session exists
            session = self._sessions.get(session_id)
            if not session:
                self._audit_verification(
                    user_id=user_id,
                    session_id=session_id,
                    result=False,
                    reason="Session not found",
                )
                return VerificationResult(
                    verified=False,
                    error_message="Invalid session",
                )
            
            # Check session belongs to user
            if session.get("user_id") != user_id:
                self._audit_verification(
                    user_id=user_id,
                    session_id=session_id,
                    result=False,
                    reason="Session user mismatch",
                )
                return VerificationResult(
                    verified=False,
                    error_message="Session does not belong to user",
                )
            
            # Check session expiration
            expires_at = session.get("expires_at")
            if expires_at and datetime.utcnow() > expires_at:
                self._audit_verification(
                    user_id=user_id,
                    session_id=session_id,
                    result=False,
                    reason="Session expired",
                )
                return VerificationResult(
                    verified=False,
                    error_message="Session expired",
                )
            
            # Check session age
            created_at = session.get("created_at")
            if created_at:
                age = datetime.utcnow() - created_at
                if age > timedelta(hours=self.max_session_age_hours):
                    self._audit_verification(
                        user_id=user_id,
                        session_id=session_id,
                        result=False,
                        reason="Session too old",
                    )
                    return VerificationResult(
                        verified=False,
                        error_message="Session exceeded maximum age",
                    )
            
            # Calculate risk score
            risk_score = self._calculate_session_risk(
                session=session,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                request_context=request_context,
            )
            
            # Check device binding
            device_verified = True
            if self.device_binding_enabled and device_fingerprint:
                device_verified = self._verify_device_binding(
                    user_id=user_id,
                    session=session,
                    device_fingerprint=device_fingerprint,
                )
                if not device_verified:
                    risk_score.add_factor("device_mismatch", 0.4)
            
            # Determine step-up requirements
            step_up_triggers = self._get_step_up_triggers(
                operation=operation,
                risk_score=risk_score,
                session=session,
                device_fingerprint=device_fingerprint,
            )
            
            requires_step_up = len(step_up_triggers) > 0
            
            # Check if step-up was recently completed
            if requires_step_up:
                last_step_up = self._step_up_completions.get(session_id)
                if last_step_up:
                    time_since = datetime.utcnow() - last_step_up
                    if time_since < timedelta(minutes=5):
                        requires_step_up = False
                        step_up_triggers = []
            
            # Update session activity
            session["last_activity"] = datetime.utcnow()
            
            result = VerificationResult(
                verified=True,
                user_id=user_id,
                session_id=session_id,
                risk_score=risk_score,
                requires_step_up=requires_step_up,
                step_up_triggers=step_up_triggers,
                device_fingerprint=device_fingerprint,
                federation_provider=session.get("federation_provider"),
            )
            
            self._audit_verification(
                user_id=user_id,
                session_id=session_id,
                result=True,
                risk_score=risk_score.score,
                requires_step_up=requires_step_up,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[ZERO-TRUST-IDENTITY] Verification error: {e}")
            self._audit_verification(
                user_id=user_id,
                session_id=session_id,
                result=False,
                reason=str(e),
            )
            return VerificationResult(
                verified=False,
                error_message=f"Verification error: {str(e)}",
            )
    
    def create_session(
        self,
        user_id: str,
        device_fingerprint: Optional[DeviceFingerprint] = None,
        federation_provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new verified session."""
        session_id = f"ZT-{secrets.token_urlsafe(32)}"
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=self.session_timeout_minutes),
            "last_activity": datetime.utcnow(),
            "device_fingerprint_hash": device_fingerprint.compute_hash() if device_fingerprint else None,
            "federation_provider": federation_provider,
            "metadata": metadata or {},
            "continuous_auth_last": datetime.utcnow(),
        }
        
        self._sessions[session_id] = session
        
        # Bind device if provided
        if device_fingerprint:
            self._bind_device(user_id, device_fingerprint)
        
        self._audit_session_created(user_id, session_id, federation_provider)
        
        logger.info(f"[ZERO-TRUST-IDENTITY] Session created for user {user_id[:8]}...")
        return session_id
    
    def invalidate_session(self, session_id: str, reason: str = "logout"):
        """Invalidate a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._audit_session_invalidated(
                user_id=session.get("user_id"),
                session_id=session_id,
                reason=reason,
            )
            logger.info(f"[ZERO-TRUST-IDENTITY] Session invalidated: {reason}")
    
    def complete_step_up(self, session_id: str, method: str):
        """Record successful step-up authentication."""
        self._step_up_completions[session_id] = datetime.utcnow()
        
        session = self._sessions.get(session_id)
        if session:
            self._audit_step_up_completed(
                user_id=session.get("user_id"),
                session_id=session_id,
                method=method,
            )
        
        logger.info(f"[ZERO-TRUST-IDENTITY] Step-up completed for session {session_id[:16]}...")
    
    def register_federation_provider(self, provider: IdentityFederationProvider):
        """Register an identity federation provider."""
        self._federation_providers[provider.provider_id] = provider
        logger.info(f"[ZERO-TRUST-IDENTITY] Federation provider registered: {provider.name}")
    
    def get_federation_provider(self, provider_id: str) -> Optional[IdentityFederationProvider]:
        """Get a federation provider by ID."""
        return self._federation_providers.get(provider_id)
    
    def list_federation_providers(self) -> List[Dict[str, Any]]:
        """List all enabled federation providers."""
        return [
            p.to_dict()
            for p in self._federation_providers.values()
            if p.enabled
        ]
    
    def _calculate_session_risk(
        self,
        session: Dict[str, Any],
        device_fingerprint: Optional[DeviceFingerprint],
        ip_address: Optional[str],
        request_context: Optional[Dict[str, Any]],
    ) -> SessionRiskScore:
        """Calculate risk score for the session."""
        risk = SessionRiskScore(score=0.0)
        
        # Session age factor
        created_at = session.get("created_at")
        if created_at:
            age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
            if age_hours > self.max_session_age_hours * 0.75:
                risk.add_factor("session_age", 0.3)
        
        # Last activity factor (idle sessions are riskier)
        last_activity = session.get("last_activity")
        if last_activity:
            idle_minutes = (datetime.utcnow() - last_activity).total_seconds() / 60
            if idle_minutes > self.session_timeout_minutes * 0.5:
                risk.add_factor("session_idle", 0.2)
        
        # Device trust factor
        if device_fingerprint:
            if not device_fingerprint.is_known_device:
                risk.add_factor("unknown_device", 0.3)
            elif device_fingerprint.trust_score < 0.5:
                risk.add_factor("low_trust_device", 0.2)
        else:
            risk.add_factor("no_device_info", 0.1)
        
        # Request context factors
        if request_context:
            if request_context.get("is_tor"):
                risk.add_factor("tor_exit_node", 0.4)
            if request_context.get("is_vpn"):
                risk.add_factor("vpn_detected", 0.1)
            if request_context.get("is_proxy"):
                risk.add_factor("proxy_detected", 0.2)
        
        # Check if step-up is required
        if risk.score >= self.step_up_threshold:
            risk.requires_step_up = True
            risk.step_up_reason = StepUpTrigger.HIGH_RISK_SCORE
        
        return risk
    
    def _verify_device_binding(
        self,
        user_id: str,
        session: Dict[str, Any],
        device_fingerprint: DeviceFingerprint,
    ) -> bool:
        """Verify device matches session binding."""
        session_device_hash = session.get("device_fingerprint_hash")
        if not session_device_hash:
            return True  # No binding to verify
        
        current_hash = device_fingerprint.compute_hash()
        if session_device_hash == current_hash:
            return True
        
        # Check if device is known for this user
        user_devices = self._devices.get(user_id, {})
        for known_device in user_devices.values():
            if device_fingerprint.similarity_score(known_device) > 0.8:
                return True
        
        return False
    
    def _bind_device(self, user_id: str, device_fingerprint: DeviceFingerprint):
        """Bind a device to a user."""
        if user_id not in self._devices:
            self._devices[user_id] = {}
        
        device_hash = device_fingerprint.compute_hash()
        device_fingerprint.is_known_device = True
        self._devices[user_id][device_hash] = device_fingerprint
    
    def _get_step_up_triggers(
        self,
        operation: Optional[str],
        risk_score: SessionRiskScore,
        session: Dict[str, Any],
        device_fingerprint: Optional[DeviceFingerprint],
    ) -> List[StepUpTrigger]:
        """Determine step-up authentication triggers."""
        triggers = []
        
        # High risk score
        if risk_score.score >= self.step_up_threshold:
            triggers.append(StepUpTrigger.HIGH_RISK_SCORE)
        
        # Sensitive operation
        if operation and operation in self._sensitive_operations:
            triggers.append(StepUpTrigger.SENSITIVE_DATA_ACCESS)
        
        # New device
        if device_fingerprint and not device_fingerprint.is_known_device:
            triggers.append(StepUpTrigger.NEW_DEVICE)
        
        # Session age
        created_at = session.get("created_at")
        if created_at:
            age = datetime.utcnow() - created_at
            if age > timedelta(hours=self.max_session_age_hours * 0.8):
                triggers.append(StepUpTrigger.SESSION_AGE)
        
        # Continuous auth interval
        last_auth = session.get("continuous_auth_last")
        if last_auth:
            since_auth = datetime.utcnow() - last_auth
            if since_auth > timedelta(minutes=self.continuous_auth_interval_minutes * 6):
                triggers.append(StepUpTrigger.MFA_REQUIRED)
        
        return triggers
    
    def _audit_verification(
        self,
        user_id: str,
        session_id: str,
        result: bool,
        reason: Optional[str] = None,
        risk_score: Optional[float] = None,
        requires_step_up: bool = False,
    ):
        """Audit identity verification to immutable log."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.SECURITY_ALERT if not result else ImmutableAuditType.DATA_ACCESS,
                    action_description=f"Identity verification: {'success' if result else 'failed'}",
                    actor_type="security",
                    actor_id="zero-trust-identity",
                    session_id=session_id,
                    severity="warning" if not result else "info",
                    component="zero_trust.identity",
                    context={
                        "user_id": user_id,
                        "result": result,
                        "reason": reason,
                        "risk_score": risk_score,
                        "requires_step_up": requires_step_up,
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-IDENTITY] Audit logging failed: {e}")
    
    def _audit_session_created(
        self,
        user_id: str,
        session_id: str,
        federation_provider: Optional[str],
    ):
        """Audit session creation."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.USER_LOGIN,
                    action_description=f"Zero-trust session created",
                    actor_type="user",
                    actor_id=user_id,
                    session_id=session_id,
                    severity="info",
                    component="zero_trust.identity",
                    context={
                        "federation_provider": federation_provider,
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-IDENTITY] Audit logging failed: {e}")
    
    def _audit_session_invalidated(
        self,
        user_id: str,
        session_id: str,
        reason: str,
    ):
        """Audit session invalidation."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.USER_LOGOUT,
                    action_description=f"Zero-trust session invalidated: {reason}",
                    actor_type="user",
                    actor_id=user_id,
                    session_id=session_id,
                    severity="info",
                    component="zero_trust.identity",
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-IDENTITY] Audit logging failed: {e}")
    
    def _audit_step_up_completed(
        self,
        user_id: str,
        session_id: str,
        method: str,
    ):
        """Audit step-up authentication completion."""
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
                    action_description=f"Step-up authentication completed via {method}",
                    actor_type="user",
                    actor_id=user_id,
                    session_id=session_id,
                    severity="info",
                    component="zero_trust.identity",
                    context={"method": method},
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-IDENTITY] Audit logging failed: {e}")


# Singleton instance
_identity_verifier: Optional[IdentityVerifier] = None


def get_identity_verifier() -> IdentityVerifier:
    """Get the identity verifier singleton."""
    global _identity_verifier
    if _identity_verifier is None:
        _identity_verifier = IdentityVerifier()
    return _identity_verifier
