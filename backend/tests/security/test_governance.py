import pytest
from datetime import datetime, timezone
from security.governance import (
    GovernanceEngine,
    GovernanceContext,
    ConstitutionalRule,
    AutonomyTier,
    GovernanceMetrics
)

def test_governance_engine_initialization():
    engine = GovernanceEngine()
    assert engine is not None
    assert engine._current_tier == AutonomyTier.TIER_0_SUPERVISED
    assert engine._trust_score == 0.5

def test_human_centricity_violation():
    engine = GovernanceEngine()
    context = GovernanceContext(
        context_id="test-1",
        action_type="critical_action",
        actor_id="system",
        actor_type="system",
        target_resource="core",
        impact_scope="systemic",
        is_reversible=False,
        financial_impact=0.0,
        metadata={"potential_harm_to_humans": True}
    )
    violations = engine.check_constitutional_rules(context)
    assert len(violations) > 0
    assert any(v.rule == ConstitutionalRule.HUMAN_CENTRICITY for v in violations)

def test_policy_rate_limit_deny():
    engine = GovernanceEngine()
    context = GovernanceContext(
        context_id="test-2",
        action_type="api_call",
        actor_id="system",
        actor_type="system",
        target_resource="api",
        impact_scope="local",
        is_reversible=True,
        financial_impact=0.0,
        metadata={"rate_limit_exceeded": True}
    )
    
    denied_reasons, approval_required, warnings = engine.check_policy_rules(context)
    assert len(denied_reasons) > 0
    assert any("Rate Limiting" in reason for reason in denied_reasons)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
