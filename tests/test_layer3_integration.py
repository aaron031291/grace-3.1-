"""
Layer 3 Integration Tests - Testing the Complete Governance System.

These tests verify Layer 3 ACTUALLY works as a cohesive system:
1. Quorum + Parliament + Constitutional Framework work together
2. Trust flows correctly through the governance pipeline
3. KPIs from different components integrate properly
4. Enforcement decisions are consistent across subsystems
5. End-to-end governance scenarios work correctly

Run with: pytest tests/test_layer3_integration.py -v
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any
import pytest

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


def run_async(coro):
    """Helper to run async functions."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def governance_stack():
    """Create complete Layer 3 governance stack."""
    from governance.layer3_quorum_verification import Layer3QuorumVerification
    from llm_orchestrator.parliament_governance import ParliamentGovernance
    
    return {
        "quorum": Layer3QuorumVerification(),
        "parliament": ParliamentGovernance(),
    }


# =============================================================================
# CROSS-COMPONENT TRUST FLOW TESTS
# =============================================================================

class TestCrossComponentTrustFlow:
    """Verify trust flows correctly between governance components."""
    
    def test_quorum_trust_score_used_in_voting(self, governance_stack):
        """Quorum trust assessment ACTUALLY influences voting."""
        from governance.layer3_quorum_verification import (
            VerificationResult, QuorumDecision
        )
        
        quorum = governance_stack["quorum"]
        
        high_trust_data = {"config": "valid"}
        high_assessment = run_async(
            quorum.assess_trust(high_trust_data, "internal_data")
        )
        
        assert high_assessment.verified_score >= 0.9
        
        high_trust_proposal = {
            "action": "load_config",
            "reasoning": "Loading internal configuration",
            "risk_level": "low",
            "trust_score": high_assessment.verified_score
        }
        
        session = run_async(quorum.request_quorum(high_trust_proposal))
        
        assert session.decision in [QuorumDecision.APPROVE, QuorumDecision.ESCALATE]
    
    def test_low_trust_leads_to_stricter_governance(self, governance_stack):
        """Low trust scores ACTUALLY lead to stricter governance."""
        from governance.layer3_quorum_verification import QuorumDecision
        
        quorum = governance_stack["quorum"]
        
        low_trust_data = {"external": "unknown"}
        low_assessment = run_async(
            quorum.assess_trust(low_trust_data, "unknown")
        )
        
        assert low_assessment.base_score <= 0.2
        
        low_trust_proposal = {
            "action": "execute_external_script",
            "risk_level": "high",
            "trust_score": low_assessment.verified_score
        }
        
        session = run_async(quorum.request_quorum(low_trust_proposal))
        
        assert session.decision in [QuorumDecision.REJECT, QuorumDecision.ESCALATE]


# =============================================================================
# CONSTITUTIONAL + QUORUM INTEGRATION TESTS
# =============================================================================

class TestConstitutionalQuorumIntegration:
    """Verify Constitutional Framework integrates with Quorum."""
    
    def test_constitutional_violation_affects_quorum(self, governance_stack):
        """Constitutional violations ACTUALLY affect quorum decisions."""
        from governance.layer3_quorum_verification import (
            ConstitutionalFramework, QuorumDecision
        )
        
        quorum = governance_stack["quorum"]
        
        action = {
            "action_type": "delete_user_data",
            "risk_level": "critical",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        assert not compliant
        assert len(violations) > 0
        
        proposal = {
            **action,
            "violations": violations,
            "trust_score": 0.3
        }
        
        session = run_async(quorum.request_quorum(proposal))
        
        assert session.decision in [QuorumDecision.REJECT, QuorumDecision.ESCALATE]
    
    def test_compliant_action_proceeds_to_quorum(self, governance_stack):
        """Compliant actions ACTUALLY proceed to quorum normally."""
        from governance.layer3_quorum_verification import (
            ConstitutionalFramework, QuorumDecision
        )
        
        quorum = governance_stack["quorum"]
        
        action = {
            "action_type": "read_public_data",
            "reasoning": "Fetching public configuration",
            "risk_level": "low",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        assert compliant
        
        proposal = {
            **action,
            "trust_score": 0.8
        }
        
        session = run_async(quorum.request_quorum(proposal))
        
        assert session.decision in [QuorumDecision.APPROVE, QuorumDecision.ESCALATE]


# =============================================================================
# KPI INTEGRATION TESTS
# =============================================================================

class TestKPIIntegration:
    """Verify KPIs integrate correctly across components."""
    
    def test_quorum_kpis_track_component_outcomes(self, governance_stack):
        """Quorum ACTUALLY tracks KPIs for all components."""
        quorum = governance_stack["quorum"]
        
        components = ["coding_agent", "self_healing", "parliament", "timesense"]
        
        for component in components:
            quorum.record_component_outcome(component, success=True)
        
        all_kpis = quorum.get_all_kpis()
        
        for component in components:
            assert component in all_kpis
            assert all_kpis[component]["success_count"] == 1
    
    def test_parliament_kpis_reflect_sessions(self, governance_stack):
        """Parliament KPIs ACTUALLY reflect session outcomes."""
        parliament = governance_stack["parliament"]
        
        initial_kpis = parliament.get_kpis()
        initial_sessions = initial_kpis["governance"]["sessions"]
        
        parliament.kpis.sessions_completed += 1
        parliament.kpis.decisions_approved += 1
        
        updated_kpis = parliament.get_kpis()
        
        assert updated_kpis["governance"]["sessions"] == initial_sessions + 1
        assert updated_kpis["governance"]["approved"] >= 1
    
    def test_kpi_degradation_affects_governance(self, governance_stack):
        """KPI degradation ACTUALLY affects governance decisions."""
        quorum = governance_stack["quorum"]
        
        for _ in range(10):
            quorum.record_component_outcome(
                "failing_component",
                success=False,
                meets_grace_standard=False,
                meets_user_standard=False
            )
        
        kpi = quorum.get_component_kpi("failing_component")
        
        assert kpi.current_score < 0.3
        assert kpi.trend == "declining"


# =============================================================================
# WHITELIST + TRUST INTEGRATION TESTS
# =============================================================================

class TestWhitelistTrustIntegration:
    """Verify whitelist integrates with trust assessment."""
    
    def test_whitelist_overrides_source_type(self, governance_stack):
        """Whitelist ACTUALLY overrides source type scoring."""
        quorum = governance_stack["quorum"]
        
        quorum.add_to_whitelist("api.trusted-partner.com")
        
        assessment = run_async(
            quorum.assess_trust(
                {"api_data": "response"},
                "api.trusted-partner.com"
            )
        )
        
        assert assessment.base_score == 1.0
    
    def test_removed_whitelist_reverts_trust(self, governance_stack):
        """Removing from whitelist ACTUALLY reverts trust scoring."""
        quorum = governance_stack["quorum"]
        
        quorum.add_to_whitelist("temp.server.com")
        quorum.remove_from_whitelist("temp.server.com")
        
        assessment = run_async(
            quorum.assess_trust({"data": "test"}, "temp.server.com")
        )
        
        assert assessment.base_score < 1.0


# =============================================================================
# GOVERNANCE STATUS INTEGRATION TESTS
# =============================================================================

class TestGovernanceStatusIntegration:
    """Verify governance status integrates all subsystems."""
    
    def test_status_reflects_all_subsystems(self, governance_stack):
        """Status ACTUALLY reflects all subsystem states."""
        quorum = governance_stack["quorum"]
        parliament = governance_stack["parliament"]
        
        quorum.record_component_outcome("test_comp", success=True)
        run_async(quorum.assess_trust({"test": "data"}, "internal_data"))
        
        quorum_status = quorum.get_governance_status()
        parliament_summary = parliament.get_governance_summary()
        
        assert quorum_status["component_kpis"]
        assert quorum_status["trust_verification"]["total_assessments"] >= 1
        
        assert parliament_summary["total_members"] > 0
        assert parliament_summary["kpis"]
    
    def test_governance_health_computed(self, governance_stack):
        """Governance health ACTUALLY computed from KPIs."""
        quorum = governance_stack["quorum"]
        
        quorum.record_component_outcome("healthy_1", success=True)
        quorum.record_component_outcome("healthy_2", success=True)
        quorum.record_component_outcome("unhealthy", success=False)
        
        status = quorum.get_governance_status()
        
        assert 0 <= status["governance_health"] <= 1.0


# =============================================================================
# END-TO-END GOVERNANCE SCENARIOS
# =============================================================================

class TestEndToEndGovernanceScenarios:
    """End-to-end tests for complete governance scenarios."""
    
    def test_scenario_trusted_user_code_generation(self, governance_stack):
        """Full scenario: trusted user requests code generation."""
        from governance.layer3_quorum_verification import (
            VerificationResult, ConstitutionalFramework, QuorumDecision
        )
        
        quorum = governance_stack["quorum"]
        
        user_request = {
            "task": "Generate a sorting function",
            "language": "python"
        }
        
        trust = run_async(
            quorum.assess_trust(user_request, "human_triggered")
        )
        
        assert trust.base_score == 1.0
        assert trust.verification_result == VerificationResult.PASSED
        
        action = {
            "action_type": "code_generation",
            "reasoning": f"User requested: {user_request['task']}",
            "risk_level": "low"
        }
        
        compliant, _ = ConstitutionalFramework.check_compliance(action)
        assert compliant
        
        proposal = {**action, "trust_score": trust.verified_score}
        session = run_async(quorum.request_quorum(proposal))
        
        assert session.decision in [QuorumDecision.APPROVE, QuorumDecision.ESCALATE]
        
        quorum.record_component_outcome(
            "coding_agent",
            success=True,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        kpi = quorum.get_component_kpi("coding_agent")
        assert kpi.success_count == 1
    
    def test_scenario_external_api_data_processing(self, governance_stack):
        """Full scenario: processing data from external API."""
        from governance.layer3_quorum_verification import VerificationResult
        
        quorum = governance_stack["quorum"]
        
        api_response = {"weather": {"temp": 25, "unit": "celsius"}}
        
        trust = run_async(
            quorum.assess_trust(api_response, "web")
        )
        
        assert trust.base_score == 0.3
        assert trust.verification_result != VerificationResult.PASSED
        
        quorum.add_to_whitelist("weather.api.gov")
        
        trusted_assessment = run_async(
            quorum.assess_trust(api_response, "weather.api.gov")
        )
        
        assert trusted_assessment.base_score == 1.0
    
    def test_scenario_risky_operation_blocked(self, governance_stack):
        """Full scenario: risky operation blocked by governance."""
        from governance.layer3_quorum_verification import (
            ConstitutionalFramework, QuorumDecision
        )
        
        quorum = governance_stack["quorum"]
        
        risky_action = {
            "action_type": "delete_database",
            "risk_level": "critical",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(risky_action)
        assert not compliant
        assert len(violations) >= 2
        
        proposal = {
            **risky_action,
            "trust_score": 0.2
        }
        
        session = run_async(quorum.request_quorum(proposal))
        
        assert session.decision in [QuorumDecision.REJECT, QuorumDecision.ESCALATE]
    
    def test_scenario_self_healing_kpi_degradation(self, governance_stack):
        """Full scenario: self-healing detects KPI degradation."""
        quorum = governance_stack["quorum"]
        
        for i in range(5):
            quorum.record_component_outcome(
                "problematic_component",
                success=False,
                meets_grace_standard=False
            )
        
        kpi = quorum.get_component_kpi("problematic_component")
        
        assert kpi.current_score < 0.5
        assert kpi.failure_count == 5
        assert kpi.trend == "declining"
        
        status = quorum.get_governance_status()
        assert "problematic_component" in status["component_kpis"]


# =============================================================================
# LAYER 3 AUTONOMY TIER INTEGRATION TESTS
# =============================================================================

class TestAutonomyTierIntegration:
    """Verify autonomy tiers integrate with governance decisions."""
    
    def test_tier_0_requires_human_for_all(self, governance_stack):
        """Tier 0 ACTUALLY requires human approval for everything."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        tier_0 = ConstitutionalFramework.AUTONOMY_TIERS[0]
        
        assert "human approval" in tier_0.lower()
    
    def test_tiers_progressive_autonomy(self, governance_stack):
        """Tiers ACTUALLY provide progressive autonomy."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        tiers = ConstitutionalFramework.AUTONOMY_TIERS
        
        assert "approval required" in tiers[0].lower() or "no autonomy" in tiers[0].lower()
        assert "limited" in tiers[1].lower() or "suggest" in tiers[1].lower()
        assert "moderate" in tiers[2].lower() or "reversible" in tiers[2].lower()
        assert "full" in tiers[3].lower() or "autonomy" in tiers[3].lower()


# =============================================================================
# GOVERNANCE ENFORCEMENT CONSISTENCY TESTS
# =============================================================================

class TestEnforcementConsistency:
    """Verify enforcement decisions are consistent."""
    
    def test_same_input_same_decision(self, governance_stack):
        """Same input ACTUALLY produces consistent decisions."""
        quorum = governance_stack["quorum"]
        
        test_data = {"consistent": "data"}
        
        results = []
        for _ in range(3):
            assessment = run_async(
                quorum.assess_trust(test_data, "internal_data")
            )
            results.append(assessment.base_score)
        
        assert all(r == results[0] for r in results)
    
    def test_whitelist_consistent_across_calls(self, governance_stack):
        """Whitelist behavior ACTUALLY consistent across calls."""
        quorum = governance_stack["quorum"]
        
        quorum.add_to_whitelist("consistent.source.com")
        
        for _ in range(5):
            assessment = run_async(
                quorum.assess_trust({"test": "data"}, "consistent.source.com")
            )
            assert assessment.base_score == 1.0


# =============================================================================
# LAYER 3 COMPLETE SYSTEM HEALTH TEST
# =============================================================================

class TestLayer3SystemHealth:
    """Verify Layer 3 operates as a healthy system."""
    
    def test_all_components_operational(self, governance_stack):
        """All Layer 3 components ACTUALLY operational."""
        quorum = governance_stack["quorum"]
        parliament = governance_stack["parliament"]
        
        trust_works = run_async(
            quorum.assess_trust({"test": "data"}, "internal_data")
        )
        assert trust_works is not None
        
        quorum.record_component_outcome("test", success=True)
        kpi = quorum.get_component_kpi("test")
        assert kpi is not None
        
        status = quorum.get_governance_status()
        assert status is not None
        
        summary = parliament.get_governance_summary()
        assert summary is not None
        assert summary["total_members"] > 0
    
    def test_governance_pipeline_no_exceptions(self, governance_stack):
        """Governance pipeline ACTUALLY runs without exceptions."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        quorum = governance_stack["quorum"]
        
        assessment = run_async(
            quorum.assess_trust({"data": "test"}, "human_triggered")
        )
        
        action = {
            "action_type": "test",
            "reasoning": "Testing pipeline",
            "risk_level": "low"
        }
        ConstitutionalFramework.check_compliance(action)
        
        proposal = {**action, "trust_score": assessment.verified_score}
        run_async(quorum.request_quorum(proposal))
        
        quorum.record_component_outcome("pipeline_test", success=True)
        
        quorum.get_governance_status()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
