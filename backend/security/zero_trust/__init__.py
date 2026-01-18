"""
GRACE Zero-Trust Security Framework

Implements "Never Trust, Always Verify" principles:
- Identity verification with continuous authentication
- Security context enrichment and risk scoring
- Policy-as-code engine for conditional access
- Multi-factor authentication (TOTP, WebAuthn, backup codes)
- Threat detection with self-healing response
- Network security (IP filtering, geo-blocking, mTLS)

All security decisions are logged to the immutable audit system.
"""

import logging

_logger = logging.getLogger(__name__)

# Identity verification
try:
    from .identity import (
        IdentityVerifier,
        DeviceFingerprint,
        SessionRiskScore,
        StepUpTrigger,
        IdentityFederationProvider,
        FederationType,
        get_identity_verifier,
    )
except ImportError as e:
    _logger.warning(f"Could not import identity: {e}")
    IdentityVerifier = None
    DeviceFingerprint = None
    SessionRiskScore = None
    StepUpTrigger = None
    IdentityFederationProvider = None
    FederationType = None
    get_identity_verifier = None

# Security context
try:
    from .context import (
        SecurityContext,
        RequestContextEnricher,
        RiskScoreCalculator,
        AnomalyDetector,
        ContextAwarePolicyDecision,
        get_context_enricher,
        get_anomaly_detector,
    )
except ImportError as e:
    _logger.warning(f"Could not import context: {e}")
    SecurityContext = None
    RequestContextEnricher = None
    RiskScoreCalculator = None
    AnomalyDetector = None
    ContextAwarePolicyDecision = None
    get_context_enricher = None
    get_anomaly_detector = None

# Policy engine
try:
    from .policy_engine import (
        PolicyEngine,
        Policy,
        PolicyCondition,
        PolicyAction,
        PolicyEvaluationResult,
        PolicyVersion,
        get_policy_engine,
    )
except ImportError as e:
    _logger.warning(f"Could not import policy_engine: {e}")
    PolicyEngine = None
    Policy = None
    PolicyCondition = None
    PolicyAction = None
    PolicyEvaluationResult = None
    PolicyVersion = None
    get_policy_engine = None

# Multi-factor authentication
try:
    from .mfa import (
        MFAManager,
        TOTPProvider,
        WebAuthnProvider,
        BackupCodeProvider,
        MFAEnrollment,
        MFAChallenge,
        AdaptiveMFA,
        get_mfa_manager,
    )
except ImportError as e:
    _logger.warning(f"Could not import mfa: {e}")
    MFAManager = None
    TOTPProvider = None
    WebAuthnProvider = None
    BackupCodeProvider = None
    MFAEnrollment = None
    MFAChallenge = None
    AdaptiveMFA = None
    get_mfa_manager = None

# Threat detection
try:
    from .threat_detection import (
        ThreatDetector,
        BruteForceDetector,
        CredentialStuffingDetector,
        SessionHijackingDetector,
        ImpossibleTravelDetector,
        APIAbuseDetector,
        ThreatResponse,
        ThreatSeverity,
        get_threat_detector,
    )
except ImportError as e:
    _logger.warning(f"Could not import threat_detection: {e}")
    ThreatDetector = None
    BruteForceDetector = None
    CredentialStuffingDetector = None
    SessionHijackingDetector = None
    ImpossibleTravelDetector = None
    APIAbuseDetector = None
    ThreatResponse = None
    ThreatSeverity = None
    get_threat_detector = None

# Network security
try:
    from .network import (
        NetworkSecurity,
        IPFilter,
        GeoBlocker,
        RequestSigner,
        MutualTLSValidator,
        get_network_security,
    )
except ImportError as e:
    _logger.warning(f"Could not import network: {e}")
    NetworkSecurity = None
    IPFilter = None
    GeoBlocker = None
    RequestSigner = None
    MutualTLSValidator = None
    get_network_security = None


__all__ = [
    # Identity
    "IdentityVerifier",
    "DeviceFingerprint",
    "SessionRiskScore",
    "StepUpTrigger",
    "IdentityFederationProvider",
    "FederationType",
    "get_identity_verifier",
    # Context
    "SecurityContext",
    "RequestContextEnricher",
    "RiskScoreCalculator",
    "AnomalyDetector",
    "ContextAwarePolicyDecision",
    "get_context_enricher",
    "get_anomaly_detector",
    # Policy Engine
    "PolicyEngine",
    "Policy",
    "PolicyCondition",
    "PolicyAction",
    "PolicyEvaluationResult",
    "PolicyVersion",
    "get_policy_engine",
    # MFA
    "MFAManager",
    "TOTPProvider",
    "WebAuthnProvider",
    "BackupCodeProvider",
    "MFAEnrollment",
    "MFAChallenge",
    "AdaptiveMFA",
    "get_mfa_manager",
    # Threat Detection
    "ThreatDetector",
    "BruteForceDetector",
    "CredentialStuffingDetector",
    "SessionHijackingDetector",
    "ImpossibleTravelDetector",
    "APIAbuseDetector",
    "ThreatResponse",
    "ThreatSeverity",
    "get_threat_detector",
    # Network
    "NetworkSecurity",
    "IPFilter",
    "GeoBlocker",
    "RequestSigner",
    "MutualTLSValidator",
    "get_network_security",
]
