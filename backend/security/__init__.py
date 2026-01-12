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

from .config import SecurityConfig, get_security_config
from .middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from .validators import InputValidator, sanitize_input
from .logging import SecurityLogger, log_security_event
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

__all__ = [
    # Config
    "SecurityConfig",
    "get_security_config",
    # Middleware
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
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
