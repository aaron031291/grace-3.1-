"""
GRACE Security Module

Provides comprehensive security features:
- Rate limiting
- Security headers
- CORS configuration
- Input validation
- Session management
- Security event logging
- Constitutional governance
- Autonomy tier management
- KPI-driven governance metrics
- SLA enforcement
- Compliance standards
"""

import logging

_logger = logging.getLogger(__name__)

# Import config
try:
    from .config import SecurityConfig, get_security_config
except ImportError as e:
    _logger.warning(f"Could not import config: {e}")
    SecurityConfig = None
    get_security_config = None

# Import middleware
try:
    from .middleware import (
        SecurityHeadersMiddleware,
        RateLimitMiddleware,
        CSRFMiddleware,
        AuthenticationMiddleware,
        InputSanitizationMiddleware,
    )
except ImportError as e:
    _logger.warning(f"Could not import middleware: {e}")
    SecurityHeadersMiddleware = None
    RateLimitMiddleware = None
    CSRFMiddleware = None
    AuthenticationMiddleware = None
    InputSanitizationMiddleware = None

# Import validators
try:
    from .validators import InputValidator, sanitize_input
except ImportError as e:
    _logger.warning(f"Could not import validators: {e}")
    InputValidator = None
    sanitize_input = None

# Import logging
try:
    from .logging import SecurityLogger, log_security_event
except ImportError as e:
    _logger.warning(f"Could not import logging: {e}")
    SecurityLogger = None
    log_security_event = None

# Import governance
try:
    from .governance import (
        # Constitutional Rules
        ConstitutionalRule,
        ConstitutionalRuleMeta,
        CONSTITUTIONAL_RULES,
        # Autonomy Tiers
        AutonomyTier,
        AutonomyTierConfig,
        AUTONOMY_TIERS,
        # SLA Definitions
        SLATier,
        SLAConfig,
        SLA_CONFIGS,
        # Action Trust Matrix
        ActionCategory,
        ActionTrustRequirement,
        ACTION_TRUST_MATRIX,
        # Capability Earning
        CapabilityProgress,
        ApprovalRecord,
        ViolationEscalation,
        TrustDecayConfig,
        QuarantinedResource,
        # Compliance Standards
        ComplianceStandard,
        ComplianceRequirement,
        COMPLIANCE_REQUIREMENTS,
        # Governance Metrics
        GovernanceMetrics,
        GovernanceKPI,
        MetricSample,
        # Governance Dataclasses
        GovernanceContext,
        GovernanceViolation,
        GovernanceDecision,
        PolicyRule,
        # Engine and Connector
        GovernanceEngine,
        GovernanceConnector,
        # Global accessors
        get_governance_engine,
        get_governance_connector,
        reset_governance,
        # Convenience function
        evaluate_governance,
    )
except ImportError as e:
    _logger.warning(f"Could not import governance: {e}")
    ConstitutionalRule = None
    ConstitutionalRuleMeta = None
    CONSTITUTIONAL_RULES = {}
    AutonomyTier = None
    AutonomyTierConfig = None
    AUTONOMY_TIERS = {}
    SLATier = None
    SLAConfig = None
    SLA_CONFIGS = {}
    ActionCategory = None
    ActionTrustRequirement = None
    ACTION_TRUST_MATRIX = {}
    CapabilityProgress = None
    ApprovalRecord = None
    ViolationEscalation = None
    TrustDecayConfig = None
    QuarantinedResource = None
    ComplianceStandard = None
    ComplianceRequirement = None
    COMPLIANCE_REQUIREMENTS = {}
    GovernanceMetrics = None
    GovernanceKPI = None
    MetricSample = None
    GovernanceContext = None
    GovernanceViolation = None
    GovernanceDecision = None
    PolicyRule = None
    GovernanceEngine = None
    GovernanceConnector = None
    get_governance_engine = None
    get_governance_connector = None
    reset_governance = None
    evaluate_governance = None

__all__ = [
    # Config
    "SecurityConfig",
    "get_security_config",
    # Middleware
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "CSRFMiddleware",
    "AuthenticationMiddleware",
    "InputSanitizationMiddleware",
    # Validators
    "InputValidator",
    "sanitize_input",
    # Logging
    "SecurityLogger",
    "log_security_event",
    # Governance - Constitutional Rules
    "ConstitutionalRule",
    "ConstitutionalRuleMeta",
    "CONSTITUTIONAL_RULES",
    # Governance - Autonomy Tiers
    "AutonomyTier",
    "AutonomyTierConfig",
    "AUTONOMY_TIERS",
    # Governance - SLA
    "SLATier",
    "SLAConfig",
    "SLA_CONFIGS",
    # Governance - Action Trust Matrix
    "ActionCategory",
    "ActionTrustRequirement",
    "ACTION_TRUST_MATRIX",
    # Governance - Capability Earning
    "CapabilityProgress",
    "ApprovalRecord",
    "ViolationEscalation",
    "TrustDecayConfig",
    "QuarantinedResource",
    # Governance - Compliance
    "ComplianceStandard",
    "ComplianceRequirement",
    "COMPLIANCE_REQUIREMENTS",
    # Governance - Metrics
    "GovernanceMetrics",
    "GovernanceKPI",
    "MetricSample",
    # Governance - Dataclasses
    "GovernanceContext",
    "GovernanceViolation",
    "GovernanceDecision",
    "PolicyRule",
    # Governance - Engine
    "GovernanceEngine",
    "GovernanceConnector",
    "get_governance_engine",
    "get_governance_connector",
    "reset_governance",
    "evaluate_governance",
]
