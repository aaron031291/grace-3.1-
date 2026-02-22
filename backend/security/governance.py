"""
Grace Governance - Constitutional AI Framework

Layer-1 + Layer-2 runtime-wired governance system integrating with:
- Layer1 Message Bus for component coordination
- Cognitive Enforcer for OODA invariants
- Genesis Keys for audit trails
- Security Config for policy settings
- KPI Tracker for metrics-driven governance
- Telemetry for uptime and SLA enforcement

Constitutional DNA provides immutable rules that cannot be overridden.
Policy Engine provides runtime-configurable governance checks.
Metrics Engine tracks KPIs for governance decisions.

Classes:
- `ConstitutionalRule`
- `ConstitutionalRuleMeta`
- `AutonomyTier`
- `AutonomyTierConfig`
- `SLATier`
- `SLAConfig`
- `ActionCategory`
- `ActionTrustRequirement`
- `CapabilityProgress`
- `ApprovalRecord`
- `ViolationEscalation`
- `TrustDecayConfig`
- `QuarantinedResource`
- `ComplianceStandard`
- `ComplianceRequirement`
- `MetricSample`
- `GovernanceKPI`
- `GovernanceMetrics`
- `GovernanceContext`
- `GovernanceViolation`
- `GovernanceDecision`
- `PolicyRule`
- `GovernanceEngine`
- `GovernanceConnector`

Key Methods:
- `record_latency()`
- `record_operation()`
- `record_learning_event()`
- `record_confidence()`
- `record_hallucination()`
- `update_component_health()`
- `update_trust_score()`
- `record_sla_violation()`
- `check_kpi_health()`
- `get_all_kpi_health()`
- `check_compliance()`
- `get_dashboard_data()`
- `check_constitutional_rules()`
- `add_policy_rule()`
- `remove_policy_rule()`
- `check_policy_rules()`
- `check_autonomy_tier()`
- `set_autonomy_tier()`
- `adjust_trust_score()`
- `assign_sla()`
- `check_sla_compliance()`
- `get_component_sla_status()`
- `check_all_compliance()`
- `enforce_learning_standards()`
- `check_capability()`

Connects To:
- `security.config`
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque

from layer1.message_bus import (
    Layer1MessageBus,
    ComponentType,
    MessageType,
    Message,
    get_message_bus
)
from security.config import SecurityConfig, get_security_config

logger = logging.getLogger(__name__)


# ==============================================================================
# CONSTITUTIONAL DNA (Immutable)
# ==============================================================================

class ConstitutionalRule(Enum):
    """Core constitutional rules that cannot be overridden."""
    HUMAN_CENTRICITY = "human_centricity"
    TRANSCENDENCE_MISSION = "transcendence_mission"
    TRUST_EARNED = "trust_earned"
    MONEY_BEFORE_TECH = "money_before_tech"
    PARTNERSHIP_EQUAL = "partnership_equal"
    SAFETY_FIRST = "safety_first"
    TRANSPARENCY_REQUIRED = "transparency_required"
    REVERSIBILITY_PREFERRED = "reversibility_preferred"
    HONESTY = "honesty"
    INTEGRITY = "integrity"
    ACCOUNTABILITY = "accountability"


@dataclass
class ConstitutionalRuleMeta:
    """Metadata for constitutional rules."""
    rule: ConstitutionalRule
    description: str
    required: bool = True
    severity: int = 10  # 1-10, higher = more severe violation
    enforcement_mode: str = "hard"  # hard = block, soft = warn


CONSTITUTIONAL_RULES: Dict[ConstitutionalRule, ConstitutionalRuleMeta] = {
    ConstitutionalRule.TRANSCENDENCE_MISSION: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.TRANSCENDENCE_MISSION,
        description="Every action must demonstrably advance the transcendence goal.",
        severity=10,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.HUMAN_CENTRICITY: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.HUMAN_CENTRICITY,
        description="Human wellbeing and dignity are non-negotiable.",
        severity=10,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.TRUST_EARNED: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.TRUST_EARNED,
        description="Autonomy scales only with proven alignment and demonstrated competence.",
        severity=9,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.MONEY_BEFORE_TECH: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.MONEY_BEFORE_TECH,
        description="Capital acquisition precedes advanced R&D expenditure.",
        severity=7,
        enforcement_mode="soft"
    ),
    ConstitutionalRule.PARTNERSHIP_EQUAL: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.PARTNERSHIP_EQUAL,
        description="Human-AI partnership is equal; neither dominates.",
        severity=9,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.SAFETY_FIRST: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.SAFETY_FIRST,
        description="Safety constraints override performance optimizations.",
        severity=10,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.TRANSPARENCY_REQUIRED: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.TRANSPARENCY_REQUIRED,
        description="All decisions must be explainable and auditable.",
        severity=8,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.REVERSIBILITY_PREFERRED: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.REVERSIBILITY_PREFERRED,
        description="Reversible actions are preferred over irreversible ones.",
        severity=7,
        enforcement_mode="soft"
    ),
    ConstitutionalRule.HONESTY: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.HONESTY,
        description="All outputs must be truthful. No fabrication, no inflated confidence, no made-up sources. If uncertain, say so.",
        severity=10,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.INTEGRITY: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.INTEGRITY,
        description="Internal data must be authentic. KPIs, trust scores, and self-reports must match reality. No gaming metrics.",
        severity=10,
        enforcement_mode="hard"
    ),
    ConstitutionalRule.ACCOUNTABILITY: ConstitutionalRuleMeta(
        rule=ConstitutionalRule.ACCOUNTABILITY,
        description="Every action must have an audit trail. Every failure must be recorded. Nothing is hidden.",
        severity=10,
        enforcement_mode="hard"
    ),
}


# ==============================================================================
# AUTONOMY TIERS
# ==============================================================================

class AutonomyTier(Enum):
    """Trust-based autonomy tiers for graduated permissions."""
    TIER_0_SUPERVISED = "tier_0_supervised"      # Human approval required
    TIER_1_MONITORED = "tier_1_monitored"        # Human notified, can intervene
    TIER_2_AUDITED = "tier_2_audited"            # Actions logged, reviewed later
    TIER_3_AUTONOMOUS = "tier_3_autonomous"      # Full autonomy within bounds


@dataclass
class AutonomyTierConfig:
    """Configuration for each autonomy tier."""
    tier: AutonomyTier
    description: str
    requires_approval: bool
    requires_notification: bool
    max_impact_scope: str  # local, component, systemic
    max_financial_impact: float  # Maximum financial impact allowed
    reversibility_required: bool
    allowed_actions: Set[str] = field(default_factory=set)


AUTONOMY_TIERS: Dict[AutonomyTier, AutonomyTierConfig] = {
    AutonomyTier.TIER_0_SUPERVISED: AutonomyTierConfig(
        tier=AutonomyTier.TIER_0_SUPERVISED,
        description="Supervised mode - human approval required for all actions",
        requires_approval=True,
        requires_notification=True,
        max_impact_scope="local",
        max_financial_impact=0.0,
        reversibility_required=True,
        allowed_actions={"read", "analyze", "suggest"}
    ),
    AutonomyTier.TIER_1_MONITORED: AutonomyTierConfig(
        tier=AutonomyTier.TIER_1_MONITORED,
        description="Monitored mode - human notified, can intervene",
        requires_approval=False,
        requires_notification=True,
        max_impact_scope="component",
        max_financial_impact=100.0,
        reversibility_required=True,
        allowed_actions={"read", "analyze", "suggest", "write_local", "execute_safe"}
    ),
    AutonomyTier.TIER_2_AUDITED: AutonomyTierConfig(
        tier=AutonomyTier.TIER_2_AUDITED,
        description="Audited mode - actions logged for later review",
        requires_approval=False,
        requires_notification=False,
        max_impact_scope="component",
        max_financial_impact=1000.0,
        reversibility_required=False,
        allowed_actions={"read", "analyze", "suggest", "write_local", "execute_safe", "write_remote"}
    ),
    AutonomyTier.TIER_3_AUTONOMOUS: AutonomyTierConfig(
        tier=AutonomyTier.TIER_3_AUTONOMOUS,
        description="Autonomous mode - full autonomy within constitutional bounds",
        requires_approval=False,
        requires_notification=False,
        max_impact_scope="systemic",
        max_financial_impact=10000.0,
        reversibility_required=False,
        allowed_actions={"read", "analyze", "suggest", "write_local", "execute_safe",
                        "write_remote", "execute_external", "financial_transaction"}
    ),
}


# ==============================================================================
# SLA & UPTIME DEFINITIONS
# ==============================================================================

class SLATier(Enum):
    """Service Level Agreement tiers."""
    CRITICAL = "critical"      # 99.99% uptime, <100ms latency
    HIGH = "high"              # 99.9% uptime, <500ms latency
    STANDARD = "standard"      # 99% uptime, <2000ms latency
    BEST_EFFORT = "best_effort"  # No SLA guarantees


@dataclass
class SLAConfig:
    """SLA configuration for a component or operation."""
    tier: SLATier
    uptime_target: float           # 0.0 - 1.0 (e.g., 0.999 = 99.9%)
    max_latency_ms: int            # Maximum acceptable latency
    max_error_rate: float          # 0.0 - 1.0 (e.g., 0.01 = 1%)
    min_success_rate: float        # 0.0 - 1.0
    recovery_time_seconds: int     # Max time to recover from failure
    escalation_threshold: int      # Number of violations before escalation


SLA_CONFIGS: Dict[SLATier, SLAConfig] = {
    SLATier.CRITICAL: SLAConfig(
        tier=SLATier.CRITICAL,
        uptime_target=0.9999,
        max_latency_ms=100,
        max_error_rate=0.0001,
        min_success_rate=0.9999,
        recovery_time_seconds=60,
        escalation_threshold=1
    ),
    SLATier.HIGH: SLAConfig(
        tier=SLATier.HIGH,
        uptime_target=0.999,
        max_latency_ms=500,
        max_error_rate=0.001,
        min_success_rate=0.999,
        recovery_time_seconds=300,
        escalation_threshold=3
    ),
    SLATier.STANDARD: SLAConfig(
        tier=SLATier.STANDARD,
        uptime_target=0.99,
        max_latency_ms=2000,
        max_error_rate=0.01,
        min_success_rate=0.99,
        recovery_time_seconds=900,
        escalation_threshold=5
    ),
    SLATier.BEST_EFFORT: SLAConfig(
        tier=SLATier.BEST_EFFORT,
        uptime_target=0.95,
        max_latency_ms=5000,
        max_error_rate=0.05,
        min_success_rate=0.95,
        recovery_time_seconds=3600,
        escalation_threshold=10
    ),
}


# ==============================================================================
# ACTION-TYPE TRUST MATRIX (Capability-Based Permissions)
# ==============================================================================

class ActionCategory(Enum):
    """Categories of actions with different trust requirements."""
    READ = "read"
    ANALYZE = "analyze"
    SUGGEST = "suggest"
    WRITE_LOCAL = "write_local"
    EXECUTE_SAFE = "execute_safe"
    WRITE_REMOTE = "write_remote"
    EXECUTE_EXTERNAL = "execute_external"
    GIT_COMMIT = "git_commit"
    GIT_PUSH_BRANCH = "git_push_branch"
    GIT_PUSH_MAIN = "git_push_main"
    FINANCIAL_TRANSACTION = "financial_transaction"
    SYSTEM_CONFIG = "system_config"
    DELETE_DATA = "delete_data"


@dataclass
class ActionTrustRequirement:
    """Trust and experience requirements for an action category."""
    action: ActionCategory
    min_trust_score: float                    # Minimum global trust required
    min_tier: AutonomyTier                    # Minimum autonomy tier required
    prerequisite_actions: Dict[str, int]      # {action: count} prerequisites
    success_count_required: int               # Successful executions before unlocking
    failure_penalty: float                    # Trust penalty on failure
    success_reward: float                     # Trust reward on success
    cooldown_on_failure_seconds: int          # Cooldown after failure
    requires_approval_override: bool          # Always needs human approval regardless of trust
    max_daily_executions: int                 # Rate limit per day (0 = unlimited)


# Action-Type Trust Matrix - Graduated permission earning
ACTION_TRUST_MATRIX: Dict[ActionCategory, ActionTrustRequirement] = {
    # Safe read operations - minimal trust required
    ActionCategory.READ: ActionTrustRequirement(
        action=ActionCategory.READ,
        min_trust_score=0.1,
        min_tier=AutonomyTier.TIER_0_SUPERVISED,
        prerequisite_actions={},
        success_count_required=0,
        failure_penalty=0.001,
        success_reward=0.001,
        cooldown_on_failure_seconds=0,
        requires_approval_override=False,
        max_daily_executions=0  # Unlimited
    ),

    # Analysis - slightly higher trust
    ActionCategory.ANALYZE: ActionTrustRequirement(
        action=ActionCategory.ANALYZE,
        min_trust_score=0.15,
        min_tier=AutonomyTier.TIER_0_SUPERVISED,
        prerequisite_actions={"read": 10},
        success_count_required=0,
        failure_penalty=0.002,
        success_reward=0.002,
        cooldown_on_failure_seconds=0,
        requires_approval_override=False,
        max_daily_executions=0
    ),

    # Suggestions - can propose but not execute
    ActionCategory.SUGGEST: ActionTrustRequirement(
        action=ActionCategory.SUGGEST,
        min_trust_score=0.2,
        min_tier=AutonomyTier.TIER_0_SUPERVISED,
        prerequisite_actions={"analyze": 5},
        success_count_required=0,
        failure_penalty=0.003,
        success_reward=0.003,
        cooldown_on_failure_seconds=0,
        requires_approval_override=False,
        max_daily_executions=0
    ),

    # Local file writes - first write capability
    ActionCategory.WRITE_LOCAL: ActionTrustRequirement(
        action=ActionCategory.WRITE_LOCAL,
        min_trust_score=0.35,
        min_tier=AutonomyTier.TIER_1_MONITORED,
        prerequisite_actions={"read": 50, "suggest": 10},
        success_count_required=0,
        failure_penalty=0.01,
        success_reward=0.005,
        cooldown_on_failure_seconds=60,
        requires_approval_override=False,
        max_daily_executions=100
    ),

    # Safe executions (tests, linting)
    ActionCategory.EXECUTE_SAFE: ActionTrustRequirement(
        action=ActionCategory.EXECUTE_SAFE,
        min_trust_score=0.45,
        min_tier=AutonomyTier.TIER_1_MONITORED,
        prerequisite_actions={"write_local": 20},
        success_count_required=20,
        failure_penalty=0.015,
        success_reward=0.008,
        cooldown_on_failure_seconds=120,
        requires_approval_override=False,
        max_daily_executions=50
    ),

    # Git commits - version controlled changes
    ActionCategory.GIT_COMMIT: ActionTrustRequirement(
        action=ActionCategory.GIT_COMMIT,
        min_trust_score=0.5,
        min_tier=AutonomyTier.TIER_2_AUDITED,
        prerequisite_actions={"write_local": 50, "execute_safe": 20},
        success_count_required=50,
        failure_penalty=0.02,
        success_reward=0.01,
        cooldown_on_failure_seconds=300,
        requires_approval_override=False,
        max_daily_executions=30
    ),

    # Remote writes (APIs, databases)
    ActionCategory.WRITE_REMOTE: ActionTrustRequirement(
        action=ActionCategory.WRITE_REMOTE,
        min_trust_score=0.6,
        min_tier=AutonomyTier.TIER_2_AUDITED,
        prerequisite_actions={"write_local": 100, "git_commit": 20},
        success_count_required=100,
        failure_penalty=0.03,
        success_reward=0.015,
        cooldown_on_failure_seconds=600,
        requires_approval_override=False,
        max_daily_executions=20
    ),

    # Push to feature branches
    ActionCategory.GIT_PUSH_BRANCH: ActionTrustRequirement(
        action=ActionCategory.GIT_PUSH_BRANCH,
        min_trust_score=0.65,
        min_tier=AutonomyTier.TIER_2_AUDITED,
        prerequisite_actions={"git_commit": 30, "execute_safe": 50},
        success_count_required=30,
        failure_penalty=0.025,
        success_reward=0.012,
        cooldown_on_failure_seconds=600,
        requires_approval_override=False,
        max_daily_executions=10
    ),

    # External API calls
    ActionCategory.EXECUTE_EXTERNAL: ActionTrustRequirement(
        action=ActionCategory.EXECUTE_EXTERNAL,
        min_trust_score=0.7,
        min_tier=AutonomyTier.TIER_2_AUDITED,
        prerequisite_actions={"write_remote": 20, "execute_safe": 100},
        success_count_required=20,
        failure_penalty=0.04,
        success_reward=0.02,
        cooldown_on_failure_seconds=900,
        requires_approval_override=False,
        max_daily_executions=15
    ),

    # Push to main/master - high trust required
    ActionCategory.GIT_PUSH_MAIN: ActionTrustRequirement(
        action=ActionCategory.GIT_PUSH_MAIN,
        min_trust_score=0.85,
        min_tier=AutonomyTier.TIER_3_AUTONOMOUS,
        prerequisite_actions={"git_push_branch": 50, "execute_safe": 200},
        success_count_required=50,
        failure_penalty=0.05,
        success_reward=0.025,
        cooldown_on_failure_seconds=1800,
        requires_approval_override=True,  # Always needs approval
        max_daily_executions=5
    ),

    # System configuration changes
    ActionCategory.SYSTEM_CONFIG: ActionTrustRequirement(
        action=ActionCategory.SYSTEM_CONFIG,
        min_trust_score=0.8,
        min_tier=AutonomyTier.TIER_3_AUTONOMOUS,
        prerequisite_actions={"write_local": 200, "execute_safe": 100},
        success_count_required=200,
        failure_penalty=0.06,
        success_reward=0.03,
        cooldown_on_failure_seconds=3600,
        requires_approval_override=True,
        max_daily_executions=3
    ),

    # Data deletion - highest scrutiny
    ActionCategory.DELETE_DATA: ActionTrustRequirement(
        action=ActionCategory.DELETE_DATA,
        min_trust_score=0.9,
        min_tier=AutonomyTier.TIER_3_AUTONOMOUS,
        prerequisite_actions={"write_local": 500, "git_commit": 100},
        success_count_required=500,
        failure_penalty=0.1,
        success_reward=0.02,
        cooldown_on_failure_seconds=7200,
        requires_approval_override=True,
        max_daily_executions=2
    ),

    # Financial transactions - maximum trust and approval
    ActionCategory.FINANCIAL_TRANSACTION: ActionTrustRequirement(
        action=ActionCategory.FINANCIAL_TRANSACTION,
        min_trust_score=0.95,
        min_tier=AutonomyTier.TIER_3_AUTONOMOUS,
        prerequisite_actions={"execute_external": 100, "write_remote": 100},
        success_count_required=100,
        failure_penalty=0.15,
        success_reward=0.01,
        cooldown_on_failure_seconds=86400,  # 24 hours
        requires_approval_override=True,
        max_daily_executions=1
    ),
}


# ==============================================================================
# CAPABILITY EARNING SYSTEM
# ==============================================================================

@dataclass
class CapabilityProgress:
    """Tracks progress toward earning a capability."""
    action: ActionCategory
    successful_executions: int = 0
    failed_executions: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    daily_execution_count: int = 0
    daily_reset_date: Optional[datetime] = None
    earned: bool = False
    earned_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None


@dataclass
class ApprovalRecord:
    """Record of an approval decision with justification."""
    approval_id: str
    decision_id: str
    approver_id: str
    approved: bool
    justification: str
    risk_acknowledged: bool
    timestamp: datetime
    context_snapshot: Dict[str, Any]  # Trust score, KPIs at approval time
    outcome: Optional[str] = None  # success, failure, pending
    outcome_timestamp: Optional[datetime] = None


@dataclass
class ViolationEscalation:
    """Escalation record for governance violations."""
    escalation_id: str
    violation_ids: List[str]
    severity: str  # warning, critical, emergency
    escalation_type: str  # notification, tier_demotion, quarantine, human_required
    target_resource: Optional[str]
    message: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolution: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


# ==============================================================================
# TRUST DECAY CONFIGURATION
# ==============================================================================

@dataclass
class TrustDecayConfig:
    """Configuration for trust score decay over time."""
    decay_half_life_days: int = 30          # Trust halves every 30 days of inactivity
    min_trust_floor: float = 0.1            # Trust never decays below this
    activity_resets_decay: bool = True      # Successful actions reset decay timer
    decay_check_interval_hours: int = 24    # How often to apply decay
    tier_demotion_on_decay: bool = True     # Auto-demote tier when trust decays


# ==============================================================================
# QUARANTINE SYSTEM
# ==============================================================================

@dataclass
class QuarantinedResource:
    """A resource that has been quarantined due to governance violations."""
    resource_id: str
    quarantine_reason: str
    violation_count: int
    quarantined_at: datetime
    quarantine_duration_hours: int
    release_at: datetime
    released: bool = False
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None


# ==============================================================================
# STANDARDS & COMPLIANCE
# ==============================================================================

class ComplianceStandard(Enum):
    """Compliance standards that can be enforced."""
    CODE_QUALITY = "code_quality"
    SECURITY_BASELINE = "security_baseline"
    DATA_INTEGRITY = "data_integrity"
    LEARNING_QUALITY = "learning_quality"
    AUDIT_COMPLETENESS = "audit_completeness"
    RESPONSE_QUALITY = "response_quality"


@dataclass
class ComplianceRequirement:
    """A specific compliance requirement."""
    standard: ComplianceStandard
    name: str
    description: str
    threshold: float              # Minimum acceptable value (0.0 - 1.0)
    measurement_period_hours: int  # How often to measure
    enforcement_action: str       # warn, restrict, escalate, block
    enabled: bool = True


COMPLIANCE_REQUIREMENTS: Dict[ComplianceStandard, List[ComplianceRequirement]] = {
    ComplianceStandard.CODE_QUALITY: [
        ComplianceRequirement(
            standard=ComplianceStandard.CODE_QUALITY,
            name="Test Coverage",
            description="Minimum test coverage for code changes",
            threshold=0.80,
            measurement_period_hours=24,
            enforcement_action="warn"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.CODE_QUALITY,
            name="Lint Score",
            description="Code must pass linting checks",
            threshold=0.95,
            measurement_period_hours=1,
            enforcement_action="restrict"
        ),
    ],
    ComplianceStandard.SECURITY_BASELINE: [
        ComplianceRequirement(
            standard=ComplianceStandard.SECURITY_BASELINE,
            name="Input Validation Rate",
            description="All inputs must be validated",
            threshold=1.0,
            measurement_period_hours=1,
            enforcement_action="block"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.SECURITY_BASELINE,
            name="Audit Log Coverage",
            description="All operations must be logged",
            threshold=1.0,
            measurement_period_hours=1,
            enforcement_action="block"
        ),
    ],
    ComplianceStandard.DATA_INTEGRITY: [
        ComplianceRequirement(
            standard=ComplianceStandard.DATA_INTEGRITY,
            name="Verification Rate",
            description="Data verification success rate",
            threshold=0.99,
            measurement_period_hours=6,
            enforcement_action="escalate"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.DATA_INTEGRITY,
            name="Consistency Score",
            description="Cross-system data consistency",
            threshold=0.95,
            measurement_period_hours=24,
            enforcement_action="warn"
        ),
    ],
    ComplianceStandard.LEARNING_QUALITY: [
        ComplianceRequirement(
            standard=ComplianceStandard.LEARNING_QUALITY,
            name="Learning Success Rate",
            description="Successful learning experiences ratio",
            threshold=0.70,
            measurement_period_hours=24,
            enforcement_action="warn"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.LEARNING_QUALITY,
            name="Pattern Quality",
            description="Quality of learned patterns",
            threshold=0.60,
            measurement_period_hours=168,  # Weekly
            enforcement_action="restrict"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.LEARNING_QUALITY,
            name="Example Validation Rate",
            description="Validated vs invalidated examples",
            threshold=0.80,
            measurement_period_hours=24,
            enforcement_action="warn"
        ),
    ],
    ComplianceStandard.AUDIT_COMPLETENESS: [
        ComplianceRequirement(
            standard=ComplianceStandard.AUDIT_COMPLETENESS,
            name="Genesis Key Coverage",
            description="All operations have Genesis Keys",
            threshold=1.0,
            measurement_period_hours=1,
            enforcement_action="block"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.AUDIT_COMPLETENESS,
            name="Decision Traceability",
            description="All decisions have reasoning traces",
            threshold=1.0,
            measurement_period_hours=1,
            enforcement_action="warn"
        ),
    ],
    ComplianceStandard.RESPONSE_QUALITY: [
        ComplianceRequirement(
            standard=ComplianceStandard.RESPONSE_QUALITY,
            name="Confidence Score",
            description="Minimum confidence for responses",
            threshold=0.70,
            measurement_period_hours=1,
            enforcement_action="warn"
        ),
        ComplianceRequirement(
            standard=ComplianceStandard.RESPONSE_QUALITY,
            name="Hallucination Rate",
            description="Maximum acceptable hallucination rate",
            threshold=0.05,  # Inverted - this is max allowed
            measurement_period_hours=24,
            enforcement_action="escalate"
        ),
    ],
}


# ==============================================================================
# GOVERNANCE METRICS
# ==============================================================================

@dataclass
class MetricSample:
    """A single metric sample."""
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernanceKPI:
    """Key Performance Indicator for governance."""
    kpi_id: str
    name: str
    description: str
    category: str  # uptime, latency, quality, learning, compliance
    target_value: float
    warning_threshold: float
    critical_threshold: float
    current_value: float = 0.0
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_updated: datetime = field(default_factory=datetime.now)


class GovernanceMetrics:
    """
    Tracks governance-specific KPIs and metrics.

    Categories:
    - Uptime: System availability and reliability
    - Latency: Response time metrics
    - Quality: Output quality metrics
    - Learning: Learning system effectiveness
    - Compliance: Standards adherence
    """

    def __init__(self):
        self._kpis: Dict[str, GovernanceKPI] = {}
        self._component_health: Dict[str, float] = {}
        self._sla_violations: List[Dict[str, Any]] = []
        self._compliance_scores: Dict[ComplianceStandard, float] = {}

        # Time-windowed metrics
        self._latency_samples: deque = deque(maxlen=10000)
        self._error_samples: deque = deque(maxlen=10000)
        self._success_samples: deque = deque(maxlen=10000)

        # Initialize default KPIs
        self._initialize_default_kpis()

        logger.info("[GOVERNANCE-METRICS] Initialized")

    def _initialize_default_kpis(self):
        """Initialize default governance KPIs."""

        # Uptime KPIs
        self._kpis["system_uptime"] = GovernanceKPI(
            kpi_id="system_uptime",
            name="System Uptime",
            description="Overall system availability percentage",
            category="uptime",
            target_value=0.999,
            warning_threshold=0.995,
            critical_threshold=0.99,
            current_value=1.0
        )

        self._kpis["component_availability"] = GovernanceKPI(
            kpi_id="component_availability",
            name="Component Availability",
            description="Average component availability",
            category="uptime",
            target_value=0.999,
            warning_threshold=0.995,
            critical_threshold=0.99,
            current_value=1.0
        )

        # Latency KPIs
        self._kpis["avg_response_time"] = GovernanceKPI(
            kpi_id="avg_response_time",
            name="Average Response Time",
            description="Average response latency in ms",
            category="latency",
            target_value=500,
            warning_threshold=1000,
            critical_threshold=2000,
            current_value=0
        )

        self._kpis["p95_latency"] = GovernanceKPI(
            kpi_id="p95_latency",
            name="P95 Latency",
            description="95th percentile latency in ms",
            category="latency",
            target_value=1000,
            warning_threshold=2000,
            critical_threshold=5000,
            current_value=0
        )

        # Quality KPIs
        self._kpis["success_rate"] = GovernanceKPI(
            kpi_id="success_rate",
            name="Success Rate",
            description="Percentage of successful operations",
            category="quality",
            target_value=0.99,
            warning_threshold=0.95,
            critical_threshold=0.90,
            current_value=1.0
        )

        self._kpis["confidence_score"] = GovernanceKPI(
            kpi_id="confidence_score",
            name="Average Confidence",
            description="Average confidence score of outputs",
            category="quality",
            target_value=0.85,
            warning_threshold=0.70,
            critical_threshold=0.50,
            current_value=0.8
        )

        self._kpis["hallucination_rate"] = GovernanceKPI(
            kpi_id="hallucination_rate",
            name="Hallucination Rate",
            description="Rate of detected hallucinations",
            category="quality",
            target_value=0.01,
            warning_threshold=0.05,
            critical_threshold=0.10,
            current_value=0.0
        )

        # Learning KPIs
        self._kpis["learning_success_rate"] = GovernanceKPI(
            kpi_id="learning_success_rate",
            name="Learning Success Rate",
            description="Successful learning experiences ratio",
            category="learning",
            target_value=0.80,
            warning_threshold=0.60,
            critical_threshold=0.40,
            current_value=0.7
        )

        self._kpis["pattern_quality"] = GovernanceKPI(
            kpi_id="pattern_quality",
            name="Pattern Quality",
            description="Quality score of learned patterns",
            category="learning",
            target_value=0.75,
            warning_threshold=0.50,
            critical_threshold=0.30,
            current_value=0.6
        )

        self._kpis["knowledge_retention"] = GovernanceKPI(
            kpi_id="knowledge_retention",
            name="Knowledge Retention",
            description="How well learned knowledge is retained",
            category="learning",
            target_value=0.90,
            warning_threshold=0.70,
            critical_threshold=0.50,
            current_value=0.85
        )

        # Compliance KPIs
        self._kpis["audit_coverage"] = GovernanceKPI(
            kpi_id="audit_coverage",
            name="Audit Coverage",
            description="Percentage of operations with audit trails",
            category="compliance",
            target_value=1.0,
            warning_threshold=0.99,
            critical_threshold=0.95,
            current_value=1.0
        )

        self._kpis["governance_approval_rate"] = GovernanceKPI(
            kpi_id="governance_approval_rate",
            name="Governance Approval Rate",
            description="Rate of governance-approved actions",
            category="compliance",
            target_value=0.95,
            warning_threshold=0.85,
            critical_threshold=0.70,
            current_value=0.9
        )

        self._kpis["trust_score"] = GovernanceKPI(
            kpi_id="trust_score",
            name="System Trust Score",
            description="Overall trust score",
            category="compliance",
            target_value=0.80,
            warning_threshold=0.50,
            critical_threshold=0.30,
            current_value=0.5
        )

    def record_latency(self, latency_ms: float, operation: str = "unknown"):
        """Record a latency sample."""
        sample = MetricSample(
            value=latency_ms,
            timestamp=datetime.now(),
            metadata={"operation": operation}
        )
        self._latency_samples.append(sample)
        self._update_latency_kpis()

    def record_operation(self, success: bool, operation: str = "unknown"):
        """Record an operation result."""
        sample = MetricSample(
            value=1.0 if success else 0.0,
            timestamp=datetime.now(),
            metadata={"operation": operation}
        )
        if success:
            self._success_samples.append(sample)
        else:
            self._error_samples.append(sample)
        self._update_quality_kpis()

    def record_learning_event(self, success: bool, pattern_quality: float = 0.0):
        """Record a learning event."""
        kpi = self._kpis["learning_success_rate"]
        kpi.samples.append(MetricSample(
            value=1.0 if success else 0.0,
            timestamp=datetime.now()
        ))

        # Update rolling average
        recent_samples = list(kpi.samples)[-100:]
        if recent_samples:
            kpi.current_value = sum(s.value for s in recent_samples) / len(recent_samples)
            kpi.last_updated = datetime.now()

        # Update pattern quality
        if pattern_quality > 0:
            pq_kpi = self._kpis["pattern_quality"]
            pq_kpi.samples.append(MetricSample(value=pattern_quality, timestamp=datetime.now()))
            recent_pq = list(pq_kpi.samples)[-50:]
            if recent_pq:
                pq_kpi.current_value = sum(s.value for s in recent_pq) / len(recent_pq)
                pq_kpi.last_updated = datetime.now()

    def record_confidence(self, confidence: float):
        """Record a confidence score."""
        kpi = self._kpis["confidence_score"]
        kpi.samples.append(MetricSample(value=confidence, timestamp=datetime.now()))

        recent_samples = list(kpi.samples)[-100:]
        if recent_samples:
            kpi.current_value = sum(s.value for s in recent_samples) / len(recent_samples)
            kpi.last_updated = datetime.now()

    def record_hallucination(self, detected: bool):
        """Record hallucination detection."""
        kpi = self._kpis["hallucination_rate"]
        kpi.samples.append(MetricSample(
            value=1.0 if detected else 0.0,
            timestamp=datetime.now()
        ))

        recent_samples = list(kpi.samples)[-100:]
        if recent_samples:
            kpi.current_value = sum(s.value for s in recent_samples) / len(recent_samples)
            kpi.last_updated = datetime.now()

    def update_component_health(self, component: str, health: float):
        """Update component health score."""
        self._component_health[component] = max(0.0, min(1.0, health))

        # Update component availability KPI
        if self._component_health:
            avg_health = sum(self._component_health.values()) / len(self._component_health)
            self._kpis["component_availability"].current_value = avg_health
            self._kpis["component_availability"].last_updated = datetime.now()

    def update_trust_score(self, trust: float):
        """Update trust score KPI."""
        self._kpis["trust_score"].current_value = trust
        self._kpis["trust_score"].last_updated = datetime.now()

    def record_sla_violation(
        self,
        component: str,
        sla_tier: SLATier,
        violation_type: str,
        current_value: float,
        threshold: float
    ):
        """Record an SLA violation."""
        violation = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "sla_tier": sla_tier.value,
            "violation_type": violation_type,
            "current_value": current_value,
            "threshold": threshold
        }
        self._sla_violations.append(violation)

        # Keep only last 1000 violations
        if len(self._sla_violations) > 1000:
            self._sla_violations = self._sla_violations[-1000:]

        logger.warning(f"[GOVERNANCE-METRICS] SLA Violation: {violation}")

    def _update_latency_kpis(self):
        """Update latency-related KPIs."""
        if not self._latency_samples:
            return

        recent = [s.value for s in list(self._latency_samples)[-1000:]]
        if not recent:
            return

        # Average latency
        avg_latency = sum(recent) / len(recent)
        self._kpis["avg_response_time"].current_value = avg_latency
        self._kpis["avg_response_time"].last_updated = datetime.now()

        # P95 latency
        sorted_latencies = sorted(recent)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
        self._kpis["p95_latency"].current_value = p95_latency
        self._kpis["p95_latency"].last_updated = datetime.now()

    def _update_quality_kpis(self):
        """Update quality-related KPIs."""
        total_ops = len(self._success_samples) + len(self._error_samples)
        if total_ops == 0:
            return

        success_rate = len(self._success_samples) / total_ops
        self._kpis["success_rate"].current_value = success_rate
        self._kpis["success_rate"].last_updated = datetime.now()

    def check_kpi_health(self, kpi_id: str) -> Tuple[str, str]:
        """
        Check health status of a KPI.

        Returns:
            Tuple of (status, message)
            status: "healthy", "warning", "critical"
        """
        if kpi_id not in self._kpis:
            return "unknown", f"KPI {kpi_id} not found"

        kpi = self._kpis[kpi_id]

        # For latency/error metrics, higher is worse
        if kpi.category in ["latency"] or kpi_id == "hallucination_rate":
            if kpi.current_value >= kpi.critical_threshold:
                return "critical", f"{kpi.name} at {kpi.current_value:.3f} exceeds critical threshold {kpi.critical_threshold}"
            elif kpi.current_value >= kpi.warning_threshold:
                return "warning", f"{kpi.name} at {kpi.current_value:.3f} exceeds warning threshold {kpi.warning_threshold}"
            else:
                return "healthy", f"{kpi.name} at {kpi.current_value:.3f} within target"
        else:
            # For success/quality metrics, lower is worse
            if kpi.current_value <= kpi.critical_threshold:
                return "critical", f"{kpi.name} at {kpi.current_value:.3f} below critical threshold {kpi.critical_threshold}"
            elif kpi.current_value <= kpi.warning_threshold:
                return "warning", f"{kpi.name} at {kpi.current_value:.3f} below warning threshold {kpi.warning_threshold}"
            else:
                return "healthy", f"{kpi.name} at {kpi.current_value:.3f} within target"

    def get_all_kpi_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all KPIs."""
        results = {}
        for kpi_id in self._kpis:
            status, message = self.check_kpi_health(kpi_id)
            results[kpi_id] = {
                "status": status,
                "message": message,
                "current_value": self._kpis[kpi_id].current_value,
                "target": self._kpis[kpi_id].target_value,
                "category": self._kpis[kpi_id].category
            }
        return results

    def check_compliance(self, standard: ComplianceStandard) -> Tuple[bool, List[str]]:
        """
        Check compliance with a standard.

        Returns:
            Tuple of (compliant, violations)
        """
        if standard not in COMPLIANCE_REQUIREMENTS:
            return True, []

        violations = []
        requirements = COMPLIANCE_REQUIREMENTS[standard]

        for req in requirements:
            if not req.enabled:
                continue

            # Get current value for this requirement
            current_value = self._get_compliance_metric(req)

            if req.name == "Hallucination Rate":
                # Inverted - current should be BELOW threshold
                if current_value > req.threshold:
                    violations.append(f"{req.name}: {current_value:.2%} exceeds max {req.threshold:.2%}")
            else:
                # Normal - current should be ABOVE threshold
                if current_value < req.threshold:
                    violations.append(f"{req.name}: {current_value:.2%} below required {req.threshold:.2%}")

        compliant = len(violations) == 0
        self._compliance_scores[standard] = 1.0 if compliant else (1.0 - len(violations) / len(requirements))

        return compliant, violations

    def _get_compliance_metric(self, requirement: ComplianceRequirement) -> float:
        """Get current metric value for a compliance requirement."""
        # Map requirement names to KPIs
        mapping = {
            "Learning Success Rate": "learning_success_rate",
            "Pattern Quality": "pattern_quality",
            "Confidence Score": "confidence_score",
            "Hallucination Rate": "hallucination_rate",
            "Genesis Key Coverage": "audit_coverage",
            "Decision Traceability": "audit_coverage",
        }

        kpi_id = mapping.get(requirement.name)
        if kpi_id and kpi_id in self._kpis:
            return self._kpis[kpi_id].current_value

        # Default to 1.0 (compliant) for unmapped requirements
        return 1.0

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return {
            "kpis": {
                kpi_id: {
                    "name": kpi.name,
                    "value": kpi.current_value,
                    "target": kpi.target_value,
                    "category": kpi.category,
                    "status": self.check_kpi_health(kpi_id)[0],
                    "last_updated": kpi.last_updated.isoformat()
                }
                for kpi_id, kpi in self._kpis.items()
            },
            "component_health": self._component_health,
            "compliance_scores": {
                std.value: score
                for std, score in self._compliance_scores.items()
            },
            "recent_sla_violations": self._sla_violations[-10:],
            "summary": {
                "healthy_kpis": sum(1 for k in self._kpis if self.check_kpi_health(k)[0] == "healthy"),
                "warning_kpis": sum(1 for k in self._kpis if self.check_kpi_health(k)[0] == "warning"),
                "critical_kpis": sum(1 for k in self._kpis if self.check_kpi_health(k)[0] == "critical"),
                "total_sla_violations": len(self._sla_violations)
            }
        }


# ==============================================================================
# GOVERNANCE DATACLASSES
# ==============================================================================

@dataclass
class GovernanceContext:
    """Context for governance evaluation."""
    context_id: str
    action_type: str
    actor_id: str
    actor_type: str  # human, ai, system
    target_resource: str
    impact_scope: str  # local, component, systemic
    is_reversible: bool
    financial_impact: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GovernanceViolation:
    """Record of a governance violation."""
    violation_id: str
    rule: ConstitutionalRule
    severity: int
    description: str
    context: GovernanceContext
    enforcement_action: str  # blocked, warned, logged
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GovernanceDecision:
    """Result of governance evaluation."""
    decision_id: str
    context: GovernanceContext
    allowed: bool
    violations: List[GovernanceViolation]
    warnings: List[str]
    required_approvals: List[str]
    autonomy_tier: AutonomyTier
    reasoning_trace: List[str]
    genesis_key_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PolicyRule:
    """Configurable policy rule."""
    rule_id: str
    name: str
    description: str
    condition: Callable[[GovernanceContext], bool]
    action: str  # allow, deny, require_approval, warn
    priority: int = 5  # 1-10, higher = evaluated first
    enabled: bool = True
    expires_at: Optional[datetime] = None


# ==============================================================================
# GOVERNANCE ENGINE
# ==============================================================================

class GovernanceEngine:
    """
    Core governance engine integrating constitutional rules and policy evaluation.

    Provides:
    - Constitutional rule enforcement (immutable)
    - Configurable policy rules (runtime)
    - Autonomy tier management
    - Audit trail via Genesis Keys
    - Layer1 message bus integration
    """

    def __init__(
        self,
        message_bus: Optional[Layer1MessageBus] = None,
        security_config: Optional[SecurityConfig] = None,
        metrics: Optional[GovernanceMetrics] = None
    ):
        self.message_bus = message_bus or get_message_bus()
        self.security_config = security_config or get_security_config()
        self.metrics = metrics or GovernanceMetrics()

        # Policy rules (configurable at runtime)
        self._policy_rules: Dict[str, PolicyRule] = {}

        # Governance decision log
        self._decision_log: List[GovernanceDecision] = []
        self._max_log_size = 10000

        # Violation tracking
        self._violations: List[GovernanceViolation] = []

        # Current autonomy tier (can be adjusted based on trust)
        self._current_tier = AutonomyTier.TIER_0_SUPERVISED

        # Trust score (0.0 - 1.0)
        self._trust_score = 0.5

        # SLA assignments per component
        self._component_sla: Dict[str, SLATier] = {}

        # Capability earning tracking
        self._capability_progress: Dict[ActionCategory, CapabilityProgress] = {
            action: CapabilityProgress(action=action)
            for action in ActionCategory
        }

        # Approval records with justification
        self._approval_records: List[ApprovalRecord] = []

        # Violation escalations
        self._escalations: List[ViolationEscalation] = []

        # Quarantined resources
        self._quarantined_resources: Dict[str, QuarantinedResource] = {}

        # Trust decay configuration
        self._trust_decay_config = TrustDecayConfig()
        self._last_activity_timestamp = datetime.now()
        self._last_decay_check = datetime.now()

        # Stats
        self._stats = {
            "total_evaluations": 0,
            "allowed": 0,
            "denied": 0,
            "warnings": 0,
            "constitutional_violations": 0,
            "sla_violations": 0,
            "compliance_checks": 0,
            "capabilities_earned": 0,
            "capabilities_revoked": 0,
            "escalations_triggered": 0,
            "resources_quarantined": 0
        }

        # Initialize default policies
        self._initialize_default_policies()

        # Initialize KPI-driven policies
        self._initialize_kpi_policies()

        logger.info("[GOVERNANCE] Initialized Governance Engine with Capability System")

    # ==========================================================================
    # CONSTITUTIONAL ENFORCEMENT
    # ==========================================================================

    def check_constitutional_rules(
        self,
        context: GovernanceContext
    ) -> List[GovernanceViolation]:
        """
        Check all constitutional rules against context.

        Constitutional rules cannot be overridden.
        """
        violations = []

        for rule, meta in CONSTITUTIONAL_RULES.items():
            violation = self._evaluate_constitutional_rule(rule, meta, context)
            if violation:
                violations.append(violation)
                self._stats["constitutional_violations"] += 1

        return violations

    def _evaluate_constitutional_rule(
        self,
        rule: ConstitutionalRule,
        meta: ConstitutionalRuleMeta,
        context: GovernanceContext
    ) -> Optional[GovernanceViolation]:
        """Evaluate a single constitutional rule."""

        # Human Centricity: Never harm human wellbeing
        if rule == ConstitutionalRule.HUMAN_CENTRICITY:
            if context.metadata.get("potential_harm_to_humans", False):
                return GovernanceViolation(
                    violation_id=f"violation-{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    severity=meta.severity,
                    description="Action could potentially harm human wellbeing",
                    context=context,
                    enforcement_action="blocked" if meta.enforcement_mode == "hard" else "warned"
                )

        # Safety First: Safety overrides performance
        if rule == ConstitutionalRule.SAFETY_FIRST:
            if context.metadata.get("bypasses_safety_check", False):
                return GovernanceViolation(
                    violation_id=f"violation-{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    severity=meta.severity,
                    description="Action attempts to bypass safety checks",
                    context=context,
                    enforcement_action="blocked"
                )

        # Transparency Required: Actions must be auditable
        if rule == ConstitutionalRule.TRANSPARENCY_REQUIRED:
            if context.metadata.get("audit_disabled", False):
                return GovernanceViolation(
                    violation_id=f"violation-{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    severity=meta.severity,
                    description="Action cannot be audited or traced",
                    context=context,
                    enforcement_action="blocked" if meta.enforcement_mode == "hard" else "warned"
                )

        # Reversibility Preferred: Warn on irreversible systemic changes
        if rule == ConstitutionalRule.REVERSIBILITY_PREFERRED:
            if not context.is_reversible and context.impact_scope == "systemic":
                return GovernanceViolation(
                    violation_id=f"violation-{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    severity=meta.severity,
                    description="Irreversible systemic action should be reconsidered",
                    context=context,
                    enforcement_action="warned"
                )

        # Trust Earned: High-impact actions require demonstrated trust
        if rule == ConstitutionalRule.TRUST_EARNED:
            if context.impact_scope == "systemic" and self._trust_score < 0.8:
                return GovernanceViolation(
                    violation_id=f"violation-{uuid.uuid4().hex[:8]}",
                    rule=rule,
                    severity=meta.severity,
                    description=f"Systemic action requires higher trust score (current: {self._trust_score})",
                    context=context,
                    enforcement_action="blocked"
                )

        return None

    # ==========================================================================
    # POLICY ENGINE
    # ==========================================================================

    def _initialize_default_policies(self):
        """Initialize default policy rules."""

        # Rate limiting policy
        self.add_policy_rule(PolicyRule(
            rule_id="policy-rate-limit",
            name="Rate Limiting",
            description="Enforce rate limits on actions",
            condition=lambda ctx: ctx.metadata.get("rate_limit_exceeded", False),
            action="deny",
            priority=9
        ))

        # Financial threshold policy
        self.add_policy_rule(PolicyRule(
            rule_id="policy-financial-threshold",
            name="Financial Threshold",
            description="Require approval for high-value transactions",
            condition=lambda ctx: ctx.financial_impact > 1000.0,
            action="require_approval",
            priority=8
        ))

        # External API policy
        self.add_policy_rule(PolicyRule(
            rule_id="policy-external-api",
            name="External API Access",
            description="Monitor external API calls",
            condition=lambda ctx: ctx.action_type.startswith("external_api"),
            action="warn",
            priority=6
        ))

        # Data export policy
        self.add_policy_rule(PolicyRule(
            rule_id="policy-data-export",
            name="Data Export",
            description="Require approval for data exports",
            condition=lambda ctx: ctx.action_type == "data_export",
            action="require_approval",
            priority=7
        ))

        logger.info(f"[GOVERNANCE] Initialized {len(self._policy_rules)} default policies")

    def _initialize_kpi_policies(self):
        """Initialize KPI-driven policy rules."""

        # Block actions when system health is critical
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-critical-health",
            name="Critical Health Block",
            description="Block non-essential actions when system health is critical",
            condition=lambda ctx: (
                self.metrics.check_kpi_health("success_rate")[0] == "critical" and
                ctx.action_type not in ["read", "analyze", "emergency_fix"]
            ),
            action="deny",
            priority=10
        ))

        # Require approval when learning quality is low
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-learning-quality",
            name="Learning Quality Gate",
            description="Require approval for learning-dependent actions when quality is low",
            condition=lambda ctx: (
                self.metrics.check_kpi_health("learning_success_rate")[0] in ["critical", "warning"] and
                ctx.metadata.get("depends_on_learning", False)
            ),
            action="require_approval",
            priority=7
        ))

        # Warn when confidence is below threshold
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-confidence",
            name="Low Confidence Warning",
            description="Warn when action involves low confidence outputs",
            condition=lambda ctx: ctx.metadata.get("confidence_score", 1.0) < 0.6,
            action="warn",
            priority=5
        ))

        # Block when hallucination rate is critical
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-hallucination",
            name="Hallucination Rate Block",
            description="Block LLM-dependent actions when hallucination rate is high",
            condition=lambda ctx: (
                self.metrics.check_kpi_health("hallucination_rate")[0] == "critical" and
                ctx.action_type in ["llm_response", "generate_code", "external_api"]
            ),
            action="deny",
            priority=9
        ))

        # Require approval for high-latency operations during degraded performance
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-latency",
            name="Latency Degradation Gate",
            description="Require approval for resource-heavy operations during high latency",
            condition=lambda ctx: (
                self.metrics.check_kpi_health("p95_latency")[0] in ["critical", "warning"] and
                ctx.metadata.get("resource_intensive", False)
            ),
            action="require_approval",
            priority=6
        ))

        # Auto-demote autonomy tier when trust KPI drops
        self.add_policy_rule(PolicyRule(
            rule_id="policy-kpi-trust-gate",
            name="Trust Score Gate",
            description="Restrict autonomy when trust KPI is below threshold",
            condition=lambda ctx: (
                self.metrics._kpis["trust_score"].current_value < 0.4 and
                ctx.impact_scope in ["component", "systemic"]
            ),
            action="require_approval",
            priority=8
        ))

        # SLA violation restriction
        self.add_policy_rule(PolicyRule(
            rule_id="policy-sla-violation",
            name="SLA Violation Restriction",
            description="Restrict actions for components with recent SLA violations",
            condition=lambda ctx: self._has_recent_sla_violations(ctx.target_resource),
            action="warn",
            priority=6
        ))

        logger.info("[GOVERNANCE] Initialized KPI-driven policies")

    def _has_recent_sla_violations(self, component: str, hours: int = 1) -> bool:
        """Check if component has recent SLA violations."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_violations = [
            v for v in self.metrics._sla_violations
            if v.get("component") == component and
            datetime.fromisoformat(v.get("timestamp", "2000-01-01")) > cutoff
        ]
        return len(recent_violations) > 0

    def add_policy_rule(self, rule: PolicyRule):
        """Add a policy rule."""
        self._policy_rules[rule.rule_id] = rule
        logger.info(f"[GOVERNANCE] Added policy rule: {rule.name}")

    def remove_policy_rule(self, rule_id: str):
        """Remove a policy rule."""
        if rule_id in self._policy_rules:
            del self._policy_rules[rule_id]
            logger.info(f"[GOVERNANCE] Removed policy rule: {rule_id}")

    def check_policy_rules(
        self,
        context: GovernanceContext
    ) -> tuple[List[str], List[str], List[str]]:
        """
        Check all policy rules against context.

        Returns:
            Tuple of (denied_reasons, approval_required, warnings)
        """
        denied_reasons = []
        approval_required = []
        warnings = []

        # Sort by priority (higher first)
        sorted_rules = sorted(
            self._policy_rules.values(),
            key=lambda r: r.priority,
            reverse=True
        )

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            # Check expiration
            if rule.expires_at and datetime.now() > rule.expires_at:
                continue

            try:
                if rule.condition(context):
                    if rule.action == "deny":
                        denied_reasons.append(f"{rule.name}: {rule.description}")
                    elif rule.action == "require_approval":
                        approval_required.append(f"{rule.name}: {rule.description}")
                    elif rule.action == "warn":
                        warnings.append(f"{rule.name}: {rule.description}")
            except Exception as e:
                logger.error(f"[GOVERNANCE] Policy rule evaluation error: {rule.name} - {e}")

        return denied_reasons, approval_required, warnings

    # ==========================================================================
    # AUTONOMY TIER MANAGEMENT
    # ==========================================================================

    def check_autonomy_tier(
        self,
        context: GovernanceContext
    ) -> tuple[bool, AutonomyTier, List[str]]:
        """
        Check if action is allowed at current autonomy tier.

        Returns:
            Tuple of (allowed, tier, reasons)
        """
        tier_config = AUTONOMY_TIERS[self._current_tier]
        reasons = []

        # Check action type
        if context.action_type not in tier_config.allowed_actions:
            reasons.append(f"Action '{context.action_type}' not allowed at {self._current_tier.value}")
            return False, self._current_tier, reasons

        # Check impact scope
        scope_order = ["local", "component", "systemic"]
        current_scope_idx = scope_order.index(tier_config.max_impact_scope)
        action_scope_idx = scope_order.index(context.impact_scope)

        if action_scope_idx > current_scope_idx:
            reasons.append(f"Impact scope '{context.impact_scope}' exceeds tier limit '{tier_config.max_impact_scope}'")
            return False, self._current_tier, reasons

        # Check financial impact
        if context.financial_impact > tier_config.max_financial_impact:
            reasons.append(f"Financial impact {context.financial_impact} exceeds tier limit {tier_config.max_financial_impact}")
            return False, self._current_tier, reasons

        # Check reversibility requirement
        if tier_config.reversibility_required and not context.is_reversible:
            reasons.append("Reversibility required at current tier")
            return False, self._current_tier, reasons

        return True, self._current_tier, reasons

    def set_autonomy_tier(self, tier: AutonomyTier):
        """Set current autonomy tier."""
        old_tier = self._current_tier
        self._current_tier = tier
        logger.info(f"[GOVERNANCE] Autonomy tier changed: {old_tier.value} -> {tier.value}")

    def adjust_trust_score(self, delta: float):
        """Adjust trust score (clamped to 0.0-1.0)."""
        old_score = self._trust_score
        self._trust_score = max(0.0, min(1.0, self._trust_score + delta))
        logger.info(f"[GOVERNANCE] Trust score adjusted: {old_score:.3f} -> {self._trust_score:.3f}")

        # Auto-adjust tier based on trust score
        self._auto_adjust_tier()

    def _auto_adjust_tier(self):
        """Auto-adjust autonomy tier based on trust score."""
        if self._trust_score < 0.3:
            new_tier = AutonomyTier.TIER_0_SUPERVISED
        elif self._trust_score < 0.5:
            new_tier = AutonomyTier.TIER_1_MONITORED
        elif self._trust_score < 0.8:
            new_tier = AutonomyTier.TIER_2_AUDITED
        else:
            new_tier = AutonomyTier.TIER_3_AUTONOMOUS

        if new_tier != self._current_tier:
            self.set_autonomy_tier(new_tier)

    # ==========================================================================
    # SLA MANAGEMENT
    # ==========================================================================

    def assign_sla(self, component: str, tier: SLATier):
        """Assign SLA tier to a component."""
        self._component_sla[component] = tier
        logger.info(f"[GOVERNANCE] Assigned SLA {tier.value} to component: {component}")

    def check_sla_compliance(
        self,
        component: str,
        latency_ms: Optional[float] = None,
        success: Optional[bool] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if component is complying with its SLA.

        Returns:
            Tuple of (compliant, violations)
        """
        if component not in self._component_sla:
            return True, []  # No SLA assigned

        sla_tier = self._component_sla[component]
        sla_config = SLA_CONFIGS[sla_tier]
        violations = []

        # Check latency
        if latency_ms is not None:
            if latency_ms > sla_config.max_latency_ms:
                violations.append(
                    f"Latency {latency_ms}ms exceeds SLA max {sla_config.max_latency_ms}ms"
                )
                self.metrics.record_sla_violation(
                    component=component,
                    sla_tier=sla_tier,
                    violation_type="latency",
                    current_value=latency_ms,
                    threshold=sla_config.max_latency_ms
                )
                self._stats["sla_violations"] += 1

        # Record operation for success rate tracking
        if success is not None:
            self.metrics.record_operation(success, component)

            # Check success rate against SLA
            health = self.metrics._kpis["success_rate"].current_value
            if health < sla_config.min_success_rate:
                violations.append(
                    f"Success rate {health:.2%} below SLA min {sla_config.min_success_rate:.2%}"
                )

        return len(violations) == 0, violations

    def get_component_sla_status(self, component: str) -> Dict[str, Any]:
        """Get SLA status for a component."""
        if component not in self._component_sla:
            return {"error": f"No SLA assigned to {component}"}

        sla_tier = self._component_sla[component]
        sla_config = SLA_CONFIGS[sla_tier]

        return {
            "component": component,
            "sla_tier": sla_tier.value,
            "uptime_target": sla_config.uptime_target,
            "max_latency_ms": sla_config.max_latency_ms,
            "min_success_rate": sla_config.min_success_rate,
            "recent_violations": len([
                v for v in self.metrics._sla_violations
                if v.get("component") == component
            ])
        }

    # ==========================================================================
    # COMPLIANCE CHECKING
    # ==========================================================================

    def check_all_compliance(self) -> Dict[str, Any]:
        """Check compliance with all standards."""
        self._stats["compliance_checks"] += 1
        results = {}

        for standard in ComplianceStandard:
            compliant, violations = self.metrics.check_compliance(standard)
            results[standard.value] = {
                "compliant": compliant,
                "violations": violations,
                "enforcement_actions": self._get_compliance_actions(standard, violations)
            }

        return results

    def _get_compliance_actions(
        self,
        standard: ComplianceStandard,
        violations: List[str]
    ) -> List[str]:
        """Determine enforcement actions for compliance violations."""
        if not violations:
            return []

        actions = []
        requirements = COMPLIANCE_REQUIREMENTS.get(standard, [])

        for req in requirements:
            for violation in violations:
                if req.name in violation:
                    if req.enforcement_action == "block":
                        actions.append(f"BLOCK: {req.name} - operations restricted")
                    elif req.enforcement_action == "restrict":
                        actions.append(f"RESTRICT: {req.name} - tier demotion recommended")
                    elif req.enforcement_action == "escalate":
                        actions.append(f"ESCALATE: {req.name} - human review required")
                    elif req.enforcement_action == "warn":
                        actions.append(f"WARN: {req.name} - monitoring increased")

        return actions

    def enforce_learning_standards(self) -> Dict[str, Any]:
        """
        Check and enforce learning quality standards.

        This integrates with the learning system to ensure quality.
        """
        compliant, violations = self.metrics.check_compliance(ComplianceStandard.LEARNING_QUALITY)

        result = {
            "compliant": compliant,
            "violations": violations,
            "actions_taken": []
        }

        if not compliant:
            # Adjust trust based on learning quality
            trust_penalty = len(violations) * 0.02
            self.adjust_trust_score(-trust_penalty)
            result["actions_taken"].append(f"Trust score reduced by {trust_penalty:.3f}")

            # Check if we need to demote tier
            if self.metrics._kpis["learning_success_rate"].current_value < 0.5:
                if self._current_tier.value > AutonomyTier.TIER_1_MONITORED.value:
                    self.set_autonomy_tier(AutonomyTier.TIER_1_MONITORED)
                    result["actions_taken"].append("Autonomy tier demoted to TIER_1_MONITORED")

        return result

    # ==========================================================================
    # CAPABILITY EARNING SYSTEM
    # ==========================================================================

    def check_capability(
        self,
        action_category: ActionCategory,
        context: GovernanceContext
    ) -> Tuple[bool, List[str]]:
        """
        Check if the system has earned the capability to perform an action.

        Returns:
            Tuple of (allowed, reasons)
        """
        if action_category not in ACTION_TRUST_MATRIX:
            return True, []  # Unknown action types are allowed by default

        requirement = ACTION_TRUST_MATRIX[action_category]
        progress = self._capability_progress[action_category]
        reasons = []

        # Check if capability was revoked
        if progress.revoked:
            reasons.append(f"Capability revoked: {progress.revocation_reason}")
            return False, reasons

        # Check cooldown
        if progress.cooldown_until and datetime.now() < progress.cooldown_until:
            remaining = (progress.cooldown_until - datetime.now()).total_seconds()
            reasons.append(f"Capability on cooldown for {remaining:.0f}s")
            return False, reasons

        # Check daily execution limit
        today = datetime.now().date()
        if progress.daily_reset_date != today:
            progress.daily_reset_date = today
            progress.daily_execution_count = 0

        if requirement.max_daily_executions > 0:
            if progress.daily_execution_count >= requirement.max_daily_executions:
                reasons.append(f"Daily limit reached: {progress.daily_execution_count}/{requirement.max_daily_executions}")
                return False, reasons

        # Check minimum trust score
        if self._trust_score < requirement.min_trust_score:
            reasons.append(
                f"Trust score {self._trust_score:.2f} below required {requirement.min_trust_score}"
            )
            return False, reasons

        # Check minimum tier
        tier_order = [
            AutonomyTier.TIER_0_SUPERVISED,
            AutonomyTier.TIER_1_MONITORED,
            AutonomyTier.TIER_2_AUDITED,
            AutonomyTier.TIER_3_AUTONOMOUS
        ]
        current_tier_idx = tier_order.index(self._current_tier)
        required_tier_idx = tier_order.index(requirement.min_tier)

        if current_tier_idx < required_tier_idx:
            reasons.append(
                f"Autonomy tier {self._current_tier.value} below required {requirement.min_tier.value}"
            )
            return False, reasons

        # Check prerequisite actions
        for prereq_action, prereq_count in requirement.prerequisite_actions.items():
            try:
                prereq_category = ActionCategory(prereq_action)
                prereq_progress = self._capability_progress[prereq_category]
                if prereq_progress.successful_executions < prereq_count:
                    reasons.append(
                        f"Prerequisite not met: {prereq_action} needs "
                        f"{prereq_count} successful executions (have {prereq_progress.successful_executions})"
                    )
            except ValueError:
                pass  # Unknown prereq action, skip

        if reasons:
            return False, reasons

        # Check quarantine
        if context.target_resource in self._quarantined_resources:
            quarantine = self._quarantined_resources[context.target_resource]
            if not quarantine.released and datetime.now() < quarantine.release_at:
                reasons.append(f"Resource '{context.target_resource}' is quarantined")
                return False, reasons

        return True, reasons

    def record_action_outcome(
        self,
        action_category: ActionCategory,
        success: bool,
        context: Optional[GovernanceContext] = None
    ):
        """Record the outcome of an action execution."""
        if action_category not in self._capability_progress:
            return

        progress = self._capability_progress[action_category]
        requirement = ACTION_TRUST_MATRIX[action_category]

        if success:
            progress.successful_executions += 1
            progress.last_success = datetime.now()
            progress.daily_execution_count += 1

            # Award trust
            self.adjust_trust_score(requirement.success_reward)

            # Reset activity timestamp for decay
            self._last_activity_timestamp = datetime.now()

            # Check if capability is now earned
            if not progress.earned:
                if progress.successful_executions >= requirement.success_count_required:
                    progress.earned = True
                    progress.earned_at = datetime.now()
                    self._stats["capabilities_earned"] += 1
                    logger.info(
                        f"[GOVERNANCE] Capability earned: {action_category.value} "
                        f"after {progress.successful_executions} successful executions"
                    )
        else:
            progress.failed_executions += 1
            progress.last_failure = datetime.now()

            # Apply trust penalty
            self.adjust_trust_score(-requirement.failure_penalty)

            # Apply cooldown
            if requirement.cooldown_on_failure_seconds > 0:
                progress.cooldown_until = datetime.now() + timedelta(
                    seconds=requirement.cooldown_on_failure_seconds
                )

            # Check for capability revocation on repeated failures
            recent_failures = self._count_recent_failures(action_category, hours=24)
            if recent_failures >= 5:
                self.revoke_capability(
                    action_category,
                    f"Repeated failures: {recent_failures} in last 24 hours"
                )

    def _count_recent_failures(self, action_category: ActionCategory, hours: int) -> int:
        """Count recent failures for an action category."""
        progress = self._capability_progress[action_category]
        if progress.last_failure is None:
            return 0

        cutoff = datetime.now() - timedelta(hours=hours)
        if progress.last_failure < cutoff:
            return 0

        # Simplified: just return current failure count if recent
        return progress.failed_executions

    def revoke_capability(self, action_category: ActionCategory, reason: str):
        """Revoke a previously earned capability."""
        progress = self._capability_progress[action_category]
        progress.revoked = True
        progress.revoked_at = datetime.now()
        progress.revocation_reason = reason
        self._stats["capabilities_revoked"] += 1

        # Trigger escalation
        self._trigger_escalation(
            violation_ids=[],
            severity="critical",
            escalation_type="capability_revoked",
            target_resource=None,
            message=f"Capability '{action_category.value}' revoked: {reason}"
        )

        logger.warning(f"[GOVERNANCE] Capability revoked: {action_category.value} - {reason}")

    def reinstate_capability(self, action_category: ActionCategory, approver_id: str):
        """Reinstate a revoked capability (requires human approval)."""
        progress = self._capability_progress[action_category]
        if not progress.revoked:
            return

        progress.revoked = False
        progress.revoked_at = None
        progress.revocation_reason = None
        # Reset failure count but keep success count
        progress.failed_executions = 0

        logger.info(
            f"[GOVERNANCE] Capability reinstated: {action_category.value} by {approver_id}"
        )

    def get_capability_status(self) -> Dict[str, Any]:
        """Get status of all capabilities."""
        return {
            action.value: {
                "earned": progress.earned,
                "revoked": progress.revoked,
                "successful_executions": progress.successful_executions,
                "failed_executions": progress.failed_executions,
                "requirements": {
                    "min_trust": ACTION_TRUST_MATRIX[action].min_trust_score,
                    "min_tier": ACTION_TRUST_MATRIX[action].min_tier.value,
                    "prerequisites": ACTION_TRUST_MATRIX[action].prerequisite_actions,
                    "success_count_required": ACTION_TRUST_MATRIX[action].success_count_required,
                },
                "cooldown_until": progress.cooldown_until.isoformat() if progress.cooldown_until else None,
                "daily_count": progress.daily_execution_count,
                "daily_limit": ACTION_TRUST_MATRIX[action].max_daily_executions,
            }
            for action, progress in self._capability_progress.items()
        }

    # ==========================================================================
    # TRUST DECAY SYSTEM
    # ==========================================================================

    def apply_trust_decay(self):
        """
        Apply trust score decay based on inactivity.

        Should be called periodically (e.g., daily).
        """
        config = self._trust_decay_config
        now = datetime.now()

        # Check if enough time has passed since last decay check
        hours_since_check = (now - self._last_decay_check).total_seconds() / 3600
        if hours_since_check < config.decay_check_interval_hours:
            return

        self._last_decay_check = now

        # Calculate days since last activity
        days_inactive = (now - self._last_activity_timestamp).days

        if days_inactive <= 0:
            return  # No decay needed

        # Apply exponential decay: trust = trust * 0.5^(days/half_life)
        import math
        decay_factor = math.pow(0.5, days_inactive / config.decay_half_life_days)
        old_trust = self._trust_score

        # Apply decay but respect floor
        new_trust = max(
            config.min_trust_floor,
            self._trust_score * decay_factor
        )

        if new_trust < old_trust:
            self._trust_score = new_trust
            logger.info(
                f"[GOVERNANCE] Trust decay applied: {old_trust:.3f} -> {new_trust:.3f} "
                f"(inactive {days_inactive} days)"
            )

            # Auto-adjust tier if configured
            if config.tier_demotion_on_decay:
                self._auto_adjust_tier()

            # Update metrics
            self.metrics.update_trust_score(self._trust_score)

    def reset_activity_timestamp(self):
        """Reset the activity timestamp (call on successful actions)."""
        self._last_activity_timestamp = datetime.now()

    # ==========================================================================
    # VIOLATION ESCALATION SYSTEM
    # ==========================================================================

    def _trigger_escalation(
        self,
        violation_ids: List[str],
        severity: str,
        escalation_type: str,
        target_resource: Optional[str],
        message: str
    ):
        """Trigger an escalation for governance violations."""
        escalation = ViolationEscalation(
            escalation_id=f"escalation-{uuid.uuid4().hex[:8]}",
            violation_ids=violation_ids,
            severity=severity,
            escalation_type=escalation_type,
            target_resource=target_resource,
            message=message
        )

        self._escalations.append(escalation)
        self._stats["escalations_triggered"] += 1

        # Take automatic action based on escalation type
        if escalation_type == "tier_demotion":
            if self._current_tier != AutonomyTier.TIER_0_SUPERVISED:
                tier_order = list(AutonomyTier)
                current_idx = tier_order.index(self._current_tier)
                if current_idx > 0:
                    self.set_autonomy_tier(tier_order[current_idx - 1])

        elif escalation_type == "quarantine" and target_resource:
            self.quarantine_resource(target_resource, message)

        # Publish escalation event
        asyncio.create_task(self._publish_escalation_event(escalation))

        logger.warning(f"[GOVERNANCE] Escalation triggered: {severity} - {message}")

    def check_and_escalate_violations(self):
        """
        Check recent violations and trigger escalations if thresholds exceeded.
        """
        now = datetime.now()
        cutoff_1h = now - timedelta(hours=1)
        cutoff_24h = now - timedelta(hours=24)

        # Count violations in different time windows
        violations_1h = [v for v in self._violations if v.timestamp > cutoff_1h]
        violations_24h = [v for v in self._violations if v.timestamp > cutoff_24h]

        # Escalation thresholds
        if len(violations_1h) >= 3:
            self._trigger_escalation(
                violation_ids=[v.violation_id for v in violations_1h],
                severity="critical",
                escalation_type="tier_demotion",
                target_resource=None,
                message=f"{len(violations_1h)} violations in last hour - demoting autonomy tier"
            )

        elif len(violations_24h) >= 10:
            self._trigger_escalation(
                violation_ids=[v.violation_id for v in violations_24h[-10:]],
                severity="warning",
                escalation_type="human_required",
                target_resource=None,
                message=f"{len(violations_24h)} violations in last 24 hours - human review required"
            )

        # Check for safety violations (always escalate immediately)
        safety_violations = [
            v for v in violations_1h
            if v.rule == ConstitutionalRule.SAFETY_FIRST
        ]
        if safety_violations:
            self._trigger_escalation(
                violation_ids=[v.violation_id for v in safety_violations],
                severity="emergency",
                escalation_type="human_required",
                target_resource=safety_violations[0].context.target_resource,
                message="SAFETY VIOLATION - immediate human review required"
            )

    async def _publish_escalation_event(self, escalation: ViolationEscalation):
        """Publish escalation event to message bus."""
        try:
            await self.message_bus.publish(
                topic="governance.escalation",
                payload={
                    "escalation_id": escalation.escalation_id,
                    "severity": escalation.severity,
                    "escalation_type": escalation.escalation_type,
                    "message": escalation.message,
                    "target_resource": escalation.target_resource,
                    "timestamp": escalation.timestamp.isoformat()
                },
                from_component=ComponentType.GENESIS_KEYS,
                priority=10  # Highest priority for escalations
            )
        except Exception as e:
            logger.error(f"[GOVERNANCE] Failed to publish escalation: {e}")

    def acknowledge_escalation(
        self,
        escalation_id: str,
        acknowledger_id: str,
        resolution: Optional[str] = None
    ):
        """Acknowledge and optionally resolve an escalation."""
        for escalation in self._escalations:
            if escalation.escalation_id == escalation_id:
                escalation.acknowledged = True
                escalation.acknowledged_by = acknowledger_id
                escalation.acknowledged_at = datetime.now()
                if resolution:
                    escalation.resolution = resolution
                logger.info(
                    f"[GOVERNANCE] Escalation acknowledged: {escalation_id} by {acknowledger_id}"
                )
                return True
        return False

    def get_pending_escalations(self) -> List[Dict[str, Any]]:
        """Get all unacknowledged escalations."""
        return [
            {
                "escalation_id": e.escalation_id,
                "severity": e.severity,
                "escalation_type": e.escalation_type,
                "message": e.message,
                "target_resource": e.target_resource,
                "timestamp": e.timestamp.isoformat()
            }
            for e in self._escalations
            if not e.acknowledged
        ]

    # ==========================================================================
    # QUARANTINE SYSTEM
    # ==========================================================================

    def quarantine_resource(
        self,
        resource_id: str,
        reason: str,
        duration_hours: int = 24
    ):
        """Quarantine a resource due to governance violations."""
        now = datetime.now()
        quarantine = QuarantinedResource(
            resource_id=resource_id,
            quarantine_reason=reason,
            violation_count=self._count_resource_violations(resource_id),
            quarantined_at=now,
            quarantine_duration_hours=duration_hours,
            release_at=now + timedelta(hours=duration_hours)
        )

        self._quarantined_resources[resource_id] = quarantine
        self._stats["resources_quarantined"] += 1

        logger.warning(
            f"[GOVERNANCE] Resource quarantined: {resource_id} for {duration_hours}h - {reason}"
        )

    def _count_resource_violations(self, resource_id: str) -> int:
        """Count violations for a specific resource."""
        return len([
            v for v in self._violations
            if v.context.target_resource == resource_id
        ])

    def release_quarantine(self, resource_id: str, releaser_id: str):
        """Release a resource from quarantine (requires human approval)."""
        if resource_id in self._quarantined_resources:
            quarantine = self._quarantined_resources[resource_id]
            quarantine.released = True
            quarantine.released_by = releaser_id
            quarantine.released_at = datetime.now()

            logger.info(
                f"[GOVERNANCE] Quarantine released: {resource_id} by {releaser_id}"
            )

    def is_resource_quarantined(self, resource_id: str) -> bool:
        """Check if a resource is currently quarantined."""
        if resource_id not in self._quarantined_resources:
            return False

        quarantine = self._quarantined_resources[resource_id]
        if quarantine.released:
            return False

        # Auto-release if duration expired
        if datetime.now() >= quarantine.release_at:
            quarantine.released = True
            quarantine.released_at = datetime.now()
            return False

        return True

    def get_quarantined_resources(self) -> List[Dict[str, Any]]:
        """Get all currently quarantined resources."""
        return [
            {
                "resource_id": q.resource_id,
                "reason": q.quarantine_reason,
                "quarantined_at": q.quarantined_at.isoformat(),
                "release_at": q.release_at.isoformat(),
                "violation_count": q.violation_count
            }
            for q in self._quarantined_resources.values()
            if not q.released and datetime.now() < q.release_at
        ]

    # ==========================================================================
    # APPROVAL WITH JUSTIFICATION
    # ==========================================================================

    async def request_approval_with_justification(
        self,
        decision: GovernanceDecision,
        required_by_rule: str
    ) -> str:
        """
        Request human approval with full context.

        Returns approval_id to track the request.
        """
        approval_id = f"approval-{uuid.uuid4().hex[:8]}"

        # Create snapshot of current state
        context_snapshot = {
            "trust_score": self._trust_score,
            "autonomy_tier": self._current_tier.value,
            "kpi_health": self.metrics.get_all_kpi_health(),
            "recent_violations": len([
                v for v in self._violations
                if v.timestamp > datetime.now() - timedelta(hours=24)
            ]),
            "capability_status": {
                action.value: progress.earned
                for action, progress in self._capability_progress.items()
            }
        }

        # Publish approval request
        await self.message_bus.publish(
            topic="governance.approval_required",
            payload={
                "approval_id": approval_id,
                "decision_id": decision.decision_id,
                "required_by_rule": required_by_rule,
                "action_type": decision.context.action_type,
                "target_resource": decision.context.target_resource,
                "impact_scope": decision.context.impact_scope,
                "financial_impact": decision.context.financial_impact,
                "context_snapshot": context_snapshot,
                "warnings": decision.warnings,
                "reasoning": decision.reasoning_trace,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.GENESIS_KEYS,
            priority=9
        )

        return approval_id

    async def process_approval(
        self,
        approval_id: str,
        decision_id: str,
        approver_id: str,
        approved: bool,
        justification: str,
        risk_acknowledged: bool = False
    ) -> Dict[str, Any]:
        """
        Process an approval decision with justification.

        Re-validates constitutional rules before allowing execution.
        """
        # Find the pending decision
        pending_decision = None
        for d in self._decision_log:
            if d.decision_id == decision_id:
                pending_decision = d
                break

        if not pending_decision:
            return {"error": f"Decision {decision_id} not found"}

        # Create approval record
        record = ApprovalRecord(
            approval_id=approval_id,
            decision_id=decision_id,
            approver_id=approver_id,
            approved=approved,
            justification=justification,
            risk_acknowledged=risk_acknowledged,
            timestamp=datetime.now(),
            context_snapshot={
                "trust_score": self._trust_score,
                "autonomy_tier": self._current_tier.value
            }
        )
        self._approval_records.append(record)

        if not approved:
            record.outcome = "rejected"
            record.outcome_timestamp = datetime.now()
            return {
                "approval_id": approval_id,
                "approved": False,
                "message": f"Rejected by {approver_id}: {justification}"
            }

        # RE-VALIDATE constitutional rules before allowing execution
        current_violations = self.check_constitutional_rules(pending_decision.context)
        hard_violations = [v for v in current_violations if v.enforcement_action == "blocked"]

        if hard_violations:
            record.outcome = "blocked_post_approval"
            record.outcome_timestamp = datetime.now()
            return {
                "approval_id": approval_id,
                "approved": False,
                "message": "Constitutional rules re-validation failed",
                "violations": [v.description for v in hard_violations]
            }

        # Check if resource was quarantined since decision
        if self.is_resource_quarantined(pending_decision.context.target_resource):
            record.outcome = "blocked_quarantine"
            record.outcome_timestamp = datetime.now()
            return {
                "approval_id": approval_id,
                "approved": False,
                "message": f"Resource '{pending_decision.context.target_resource}' is now quarantined"
            }

        # Approval successful
        pending_decision.allowed = True
        pending_decision.reasoning_trace.append(
            f"Approved by {approver_id} with justification: {justification}"
        )
        record.outcome = "pending_execution"

        # Small trust boost for approved actions (actual boost happens on successful execution)
        # Don't boost trust here - wait for outcome

        return {
            "approval_id": approval_id,
            "approved": True,
            "message": "Approved - awaiting execution outcome",
            "justification": justification
        }

    def record_approval_outcome(self, approval_id: str, success: bool):
        """Record the outcome of an approved action."""
        for record in self._approval_records:
            if record.approval_id == approval_id:
                record.outcome = "success" if success else "failure"
                record.outcome_timestamp = datetime.now()

                # Only adjust trust based on actual outcome
                if success:
                    self.adjust_trust_score(0.01)
                else:
                    self.adjust_trust_score(-0.02)  # Penalty for failed approved action
                    # Consider escalation for failed approved actions
                    self._trigger_escalation(
                        violation_ids=[],
                        severity="warning",
                        escalation_type="notification",
                        target_resource=None,
                        message=f"Approved action failed: approval {approval_id}"
                    )
                break

    # ==========================================================================
    # MAIN EVALUATION
    # ==========================================================================

    async def evaluate(
        self,
        context: GovernanceContext
    ) -> GovernanceDecision:
        """
        Main governance evaluation method.

        Checks:
        1. Constitutional rules (cannot be overridden)
        2. Policy rules (configurable)
        3. Autonomy tier constraints
        """
        self._stats["total_evaluations"] += 1
        reasoning_trace = []
        all_violations = []
        all_warnings = []
        required_approvals = []

        decision_id = f"gov-decision-{uuid.uuid4().hex[:12]}"
        reasoning_trace.append(f"Starting governance evaluation: {decision_id}")
        reasoning_trace.append(f"Action: {context.action_type} on {context.target_resource}")

        # 1. Check constitutional rules (highest priority)
        reasoning_trace.append("Checking constitutional rules...")
        constitutional_violations = self.check_constitutional_rules(context)
        all_violations.extend(constitutional_violations)

        if constitutional_violations:
            hard_violations = [v for v in constitutional_violations if v.enforcement_action == "blocked"]
            if hard_violations:
                reasoning_trace.append(f"BLOCKED: {len(hard_violations)} constitutional violation(s)")
                self._stats["denied"] += 1

                decision = GovernanceDecision(
                    decision_id=decision_id,
                    context=context,
                    allowed=False,
                    violations=all_violations,
                    warnings=all_warnings,
                    required_approvals=[],
                    autonomy_tier=self._current_tier,
                    reasoning_trace=reasoning_trace
                )
                self._log_decision(decision)

                # Publish governance event
                await self._publish_governance_event(decision)

                return decision

        # 2. Check autonomy tier constraints
        reasoning_trace.append(f"Checking autonomy tier ({self._current_tier.value})...")
        tier_allowed, tier, tier_reasons = self.check_autonomy_tier(context)

        if not tier_allowed:
            reasoning_trace.append(f"BLOCKED: Autonomy tier constraint - {tier_reasons}")
            self._stats["denied"] += 1

            decision = GovernanceDecision(
                decision_id=decision_id,
                context=context,
                allowed=False,
                violations=all_violations,
                warnings=tier_reasons,
                required_approvals=[],
                autonomy_tier=tier,
                reasoning_trace=reasoning_trace
            )
            self._log_decision(decision)
            await self._publish_governance_event(decision)
            return decision

        # 3. Check policy rules
        reasoning_trace.append("Checking policy rules...")
        denied, approvals, warnings = self.check_policy_rules(context)
        all_warnings.extend(warnings)
        required_approvals.extend(approvals)

        if denied:
            reasoning_trace.append(f"BLOCKED: Policy violation - {denied}")
            self._stats["denied"] += 1

            decision = GovernanceDecision(
                decision_id=decision_id,
                context=context,
                allowed=False,
                violations=all_violations,
                warnings=all_warnings,
                required_approvals=required_approvals,
                autonomy_tier=tier,
                reasoning_trace=reasoning_trace
            )
            self._log_decision(decision)
            await self._publish_governance_event(decision)
            return decision

        # 4. Check if approval is required
        tier_config = AUTONOMY_TIERS[self._current_tier]
        if tier_config.requires_approval:
            required_approvals.append("Tier requires explicit approval")

        # Decision: Allowed (possibly with approval required)
        allowed = len(required_approvals) == 0
        if allowed:
            reasoning_trace.append("ALLOWED: All checks passed")
            self._stats["allowed"] += 1
        else:
            reasoning_trace.append(f"PENDING APPROVAL: {len(required_approvals)} approval(s) required")

        if all_warnings:
            self._stats["warnings"] += len(all_warnings)
            reasoning_trace.append(f"WARNINGS: {len(all_warnings)} warning(s)")

        decision = GovernanceDecision(
            decision_id=decision_id,
            context=context,
            allowed=allowed,
            violations=all_violations,
            warnings=all_warnings,
            required_approvals=required_approvals,
            autonomy_tier=tier,
            reasoning_trace=reasoning_trace
        )

        self._log_decision(decision)
        await self._publish_governance_event(decision)

        return decision

    # ==========================================================================
    # UTILITIES
    # ==========================================================================

    def _log_decision(self, decision: GovernanceDecision):
        """Log governance decision."""
        self._decision_log.append(decision)

        # Keep log size bounded
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size:]

        # Track violations
        self._violations.extend(decision.violations)

    async def _publish_governance_event(self, decision: GovernanceDecision):
        """Publish governance decision to message bus."""
        try:
            await self.message_bus.publish(
                topic="governance.decision",
                payload={
                    "decision_id": decision.decision_id,
                    "action_type": decision.context.action_type,
                    "actor_id": decision.context.actor_id,
                    "allowed": decision.allowed,
                    "violations_count": len(decision.violations),
                    "warnings_count": len(decision.warnings),
                    "autonomy_tier": decision.autonomy_tier.value,
                    "timestamp": decision.timestamp.isoformat()
                },
                from_component=ComponentType.GENESIS_KEYS,  # Use existing component type
                priority=8 if not decision.allowed else 5
            )
        except Exception as e:
            logger.error(f"[GOVERNANCE] Failed to publish event: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            **self._stats,
            "current_tier": self._current_tier.value,
            "trust_score": self._trust_score,
            "active_policies": len([r for r in self._policy_rules.values() if r.enabled]),
            "total_violations": len(self._violations),
            "components_with_sla": len(self._component_sla),
            "kpi_summary": self.metrics.get_all_kpi_health(),
            "compliance_summary": {
                std.value: self.metrics._compliance_scores.get(std, 1.0)
                for std in ComplianceStandard
            }
        }

    def get_metrics_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive metrics dashboard."""
        return self.metrics.get_dashboard_data()

    def get_decision_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent governance decisions."""
        return [
            {
                "decision_id": d.decision_id,
                "action_type": d.context.action_type,
                "allowed": d.allowed,
                "autonomy_tier": d.autonomy_tier.value,
                "timestamp": d.timestamp.isoformat()
            }
            for d in self._decision_log[-limit:]
        ]

    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent violations."""
        return [
            {
                "violation_id": v.violation_id,
                "rule": v.rule.value,
                "severity": v.severity,
                "description": v.description,
                "enforcement_action": v.enforcement_action,
                "timestamp": v.timestamp.isoformat()
            }
            for v in self._violations[-limit:]
        ]


# ==============================================================================
# GOVERNANCE CONNECTOR (Layer1 Integration)
# ==============================================================================

class GovernanceConnector:
    """
    Connects Governance Engine to Layer 1 message bus.

    Autonomous Actions:
    1. Action requested -> Evaluate governance
    2. Trust violation -> Adjust trust score
    3. Approval granted -> Update decision status
    """

    def __init__(
        self,
        governance_engine: Optional[GovernanceEngine] = None,
        message_bus: Optional[Layer1MessageBus] = None
    ):
        self.governance = governance_engine or get_governance_engine()
        self.message_bus = message_bus or get_message_bus()

        # Pending approvals
        self._pending_approvals: Dict[str, GovernanceDecision] = {}

        logger.info("[GOVERNANCE-CONNECTOR] Initializing...")

        # Register request handlers
        self._register_request_handlers()

        # Subscribe to events
        self._subscribe_to_events()

        # Register autonomous actions
        self._register_autonomous_actions()

        logger.info("[GOVERNANCE-CONNECTOR] Initialized and connected to message bus")

    def _register_request_handlers(self):
        """Register request handlers."""

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,  # Reuse existing component
            topic="governance.evaluate",
            handler=self._handle_evaluate_request
        )

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,
            topic="governance.approve",
            handler=self._handle_approval_request
        )

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,
            topic="governance.stats",
            handler=self._handle_stats_request
        )

        logger.info("[GOVERNANCE-CONNECTOR] Registered 3 request handlers")

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""

        # Listen for trust-affecting events
        self.message_bus.subscribe(
            topic="learning.success",
            handler=self._on_learning_success
        )

        self.message_bus.subscribe(
            topic="learning.failure",
            handler=self._on_learning_failure
        )

        logger.info("[GOVERNANCE-CONNECTOR] Subscribed to 2 event topics")

    def _register_autonomous_actions(self):
        """Register autonomous actions."""

        # Auto-evaluate external API calls
        self.message_bus.register_autonomous_action(
            trigger_event="api.external_call",
            action=self._on_external_api_call,
            component=ComponentType.GENESIS_KEYS,
            description="Auto-evaluate external API calls for governance"
        )

        logger.info("[GOVERNANCE-CONNECTOR] Registered 1 autonomous action")

    # Request Handlers

    async def _handle_evaluate_request(self, message: Message) -> Dict[str, Any]:
        """Handle governance evaluation request."""
        payload = message.payload

        context = GovernanceContext(
            context_id=payload.get("context_id", f"ctx-{uuid.uuid4().hex[:8]}"),
            action_type=payload.get("action_type", "unknown"),
            actor_id=payload.get("actor_id", "unknown"),
            actor_type=payload.get("actor_type", "system"),
            target_resource=payload.get("target_resource", "unknown"),
            impact_scope=payload.get("impact_scope", "local"),
            is_reversible=payload.get("is_reversible", True),
            financial_impact=payload.get("financial_impact", 0.0),
            metadata=payload.get("metadata", {})
        )

        decision = await self.governance.evaluate(context)

        # Track pending approvals
        if decision.required_approvals:
            self._pending_approvals[decision.decision_id] = decision

        return {
            "decision_id": decision.decision_id,
            "allowed": decision.allowed,
            "violations": [asdict(v) for v in decision.violations] if decision.violations else [],
            "warnings": decision.warnings,
            "required_approvals": decision.required_approvals,
            "autonomy_tier": decision.autonomy_tier.value,
            "reasoning": decision.reasoning_trace
        }

    async def _handle_approval_request(self, message: Message) -> Dict[str, Any]:
        """Handle approval for pending decision."""
        decision_id = message.payload.get("decision_id")
        approved = message.payload.get("approved", False)
        approver_id = message.payload.get("approver_id")

        if decision_id not in self._pending_approvals:
            return {"error": f"Decision {decision_id} not found in pending approvals"}

        decision = self._pending_approvals[decision_id]

        if approved:
            decision.allowed = True
            decision.reasoning_trace.append(f"Approved by {approver_id}")

            # Boost trust slightly on approved actions
            self.governance.adjust_trust_score(0.01)
        else:
            decision.reasoning_trace.append(f"Rejected by {approver_id}")

        del self._pending_approvals[decision_id]

        return {
            "decision_id": decision_id,
            "approved": approved,
            "approver_id": approver_id
        }

    async def _handle_stats_request(self, message: Message) -> Dict[str, Any]:
        """Handle request for governance stats."""
        return self.governance.get_stats()

    # Event Handlers

    async def _on_learning_success(self, message: Message):
        """Handle learning success - boost trust."""
        self.governance.adjust_trust_score(0.005)
        logger.debug("[GOVERNANCE-CONNECTOR] Trust boosted on learning success")

    async def _on_learning_failure(self, message: Message):
        """Handle learning failure - reduce trust."""
        self.governance.adjust_trust_score(-0.01)
        logger.debug("[GOVERNANCE-CONNECTOR] Trust reduced on learning failure")

    async def _on_external_api_call(self, message: Message):
        """Auto-evaluate external API calls."""
        context = GovernanceContext(
            context_id=f"ctx-api-{uuid.uuid4().hex[:8]}",
            action_type="external_api",
            actor_id=message.payload.get("actor_id", "system"),
            actor_type="ai",
            target_resource=message.payload.get("api_endpoint", "unknown"),
            impact_scope="component",
            is_reversible=True,
            financial_impact=0.0,
            metadata={"api_name": message.payload.get("api_name")}
        )

        decision = await self.governance.evaluate(context)

        if not decision.allowed:
            logger.warning(
                f"[GOVERNANCE-CONNECTOR] External API call blocked: "
                f"{message.payload.get('api_endpoint')}"
            )


# ==============================================================================
# GLOBAL INSTANCES
# ==============================================================================

_governance_engine: Optional[GovernanceEngine] = None
_governance_connector: Optional[GovernanceConnector] = None


def get_governance_engine() -> GovernanceEngine:
    """Get or create global governance engine instance."""
    global _governance_engine
    if _governance_engine is None:
        _governance_engine = GovernanceEngine()
        logger.info("[GOVERNANCE] Created global Governance Engine")
    return _governance_engine


def get_governance_connector() -> GovernanceConnector:
    """Get or create global governance connector instance."""
    global _governance_connector
    if _governance_connector is None:
        _governance_connector = GovernanceConnector()
        logger.info("[GOVERNANCE] Created global Governance Connector")
    return _governance_connector


def reset_governance():
    """Reset governance instances (for testing)."""
    global _governance_engine, _governance_connector
    _governance_engine = None
    _governance_connector = None


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

async def evaluate_governance(
    action_type: str,
    actor_id: str,
    target_resource: str,
    impact_scope: str = "local",
    is_reversible: bool = True,
    financial_impact: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None
) -> GovernanceDecision:
    """
    Convenience function to evaluate governance for an action.

    Usage:
        decision = await evaluate_governance(
            action_type="write_file",
            actor_id="user-123",
            target_resource="/data/config.json",
            impact_scope="component"
        )

        if decision.allowed:
            # proceed with action
        else:
            # handle denial
    """
    engine = get_governance_engine()

    context = GovernanceContext(
        context_id=f"ctx-{uuid.uuid4().hex[:8]}",
        action_type=action_type,
        actor_id=actor_id,
        actor_type="ai" if actor_id.startswith("grace") else "human",
        target_resource=target_resource,
        impact_scope=impact_scope,
        is_reversible=is_reversible,
        financial_impact=financial_impact,
        metadata=metadata or {}
    )

    return await engine.evaluate(context)
