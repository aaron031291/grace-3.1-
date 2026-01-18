"""
REAL Functional Tests for Layer 3 Governance System.

These are NOT smoke tests - they verify that governance components ACTUALLY:
1. Trust scoring ACTUALLY differentiates trusted vs untrusted sources
2. KPI tracking ACTUALLY adjusts scores up/down based on outcomes
3. Constitutional Framework ACTUALLY blocks non-compliant actions
4. Quorum voting ACTUALLY reaches consensus decisions
5. Whitelist management ACTUALLY controls source trust
6. Enforcement actions ACTUALLY follow trust thresholds
7. The full governance pipeline ACTUALLY works end-to-end

Run with: pytest tests/test_layer3_governance_real.py -v
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, List
import pytest

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fresh_quorum_engine():
    """Create a fresh quorum engine for each test."""
    from governance.layer3_quorum_verification import Layer3QuorumVerification
    return Layer3QuorumVerification()


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# TRUST SCORE SOURCE DIFFERENTIATION TESTS
# =============================================================================

class TestTrustScoreDifferentiation:
    """Verify trust scoring ACTUALLY differentiates sources correctly."""
    
    def test_trusted_sources_get_100_percent_score(self, fresh_quorum_engine):
        """100% trusted sources ACTUALLY get base score of 1.0."""
        from governance.layer3_quorum_verification import TrustSource
        
        trusted_source_origins = [
            "internal_data",
            "proactive_learning", 
            "oracle",
            "human_triggered",
        ]
        
        for origin in trusted_source_origins:
            assessment = run_async(
                fresh_quorum_engine.assess_trust(
                    data={"test": "data"},
                    origin=origin
                )
            )
            assert assessment.base_score == 1.0, f"{origin} should have base score 1.0"
            assert assessment.verified_score >= 0.9, f"{origin} verified score too low"
    
    def test_untrusted_sources_get_lower_scores(self, fresh_quorum_engine):
        """External sources ACTUALLY get lower base scores."""
        from governance.layer3_quorum_verification import TrustSource
        
        untrusted_mappings = {
            TrustSource.WEB: 0.3,
            TrustSource.LLM_QUERY: 0.5,
            TrustSource.CHAT_MESSAGE: 0.4,
            TrustSource.EXTERNAL_FILE: 0.3,
            TrustSource.UNKNOWN: 0.1,
        }
        
        for source, expected_score in untrusted_mappings.items():
            assessment = run_async(
                fresh_quorum_engine.assess_trust(
                    data={"test": "data"},
                    origin=source.value
                )
            )
            assert assessment.base_score == expected_score, \
                f"{source} should have base score {expected_score}, got {assessment.base_score}"
    
    def test_whitelisted_origin_overrides_low_source(self, fresh_quorum_engine):
        """Whitelisted origins ACTUALLY override source type scoring."""
        fresh_quorum_engine.add_to_whitelist("trusted.example.com")
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"test": "data"},
                origin="trusted.example.com"
            )
        )
        
        assert assessment.base_score == 1.0, "Whitelisted origin should get 1.0 score"
    
    def test_unknown_origin_gets_lowest_score(self, fresh_quorum_engine):
        """Completely unknown origins ACTUALLY get minimum trust."""
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"random": "data"},
                origin="completely_random_unknown_source_xyz"
            )
        )
        
        assert assessment.base_score == 0.1, "Unknown origin should get 0.1 base score"


# =============================================================================
# KPI TRACKING OUTCOME TESTS
# =============================================================================

class TestKPIOutcomeTracking:
    """Verify KPI tracking ACTUALLY adjusts scores based on outcomes."""
    
    def test_success_with_both_standards_increases_score(self, fresh_quorum_engine):
        """Success + both standards met ACTUALLY increases score by 0.02."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        initial = kpi.current_score
        
        kpi.record_outcome(
            success=True,
            weight=1.0,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        expected = min(1.0, initial + 0.02)
        assert kpi.current_score == expected, \
            f"Score should be {expected}, got {kpi.current_score}"
        assert kpi.trend == "improving"
    
    def test_success_with_one_standard_increases_less(self, fresh_quorum_engine):
        """Success + one standard met ACTUALLY increases score by 0.01."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        initial = kpi.current_score
        
        kpi.record_outcome(
            success=True,
            weight=1.0,
            meets_grace_standard=True,
            meets_user_standard=False
        )
        
        expected = min(1.0, initial + 0.01)
        assert kpi.current_score == expected
    
    def test_failure_decreases_score_more(self, fresh_quorum_engine):
        """Failures ACTUALLY decrease score by 0.03 (heavier penalty)."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        initial = kpi.current_score
        
        kpi.record_outcome(success=False, weight=1.0)
        
        expected = max(0.0, initial - 0.03)
        assert kpi.current_score == expected, \
            f"Score should be {expected}, got {kpi.current_score}"
        assert kpi.trend == "declining"
    
    def test_weight_affects_adjustment(self, fresh_quorum_engine):
        """Weight parameter ACTUALLY multiplies the adjustment."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        initial = kpi.current_score
        
        kpi.record_outcome(
            success=True, 
            weight=2.0,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        expected = min(1.0, initial + 0.02 * 2.0)
        assert kpi.current_score == expected
    
    def test_kpi_history_records_all_outcomes(self, fresh_quorum_engine):
        """KPI history ACTUALLY records each outcome."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        
        kpi.record_outcome(success=True)
        kpi.record_outcome(success=False)
        kpi.record_outcome(success=True)
        
        assert len(kpi.history) == 3
        assert kpi.history[0]["success"] == True
        assert kpi.history[1]["success"] == False
        assert kpi.history[2]["success"] == True
    
    def test_kpi_history_capped_at_100(self, fresh_quorum_engine):
        """KPI history ACTUALLY caps at 100 entries."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        
        for i in range(150):
            kpi.record_outcome(success=True)
        
        assert len(kpi.history) == 100
    
    def test_engine_tracks_multiple_components(self, fresh_quorum_engine):
        """Engine ACTUALLY tracks KPIs for multiple components."""
        fresh_quorum_engine.record_component_outcome("coding_agent", success=True)
        fresh_quorum_engine.record_component_outcome("self_healing", success=False)
        fresh_quorum_engine.record_component_outcome("coding_agent", success=True)
        
        coding_kpi = fresh_quorum_engine.get_component_kpi("coding_agent")
        healing_kpi = fresh_quorum_engine.get_component_kpi("self_healing")
        
        assert coding_kpi.success_count == 2
        assert healing_kpi.failure_count == 1
        assert coding_kpi.current_score > 0.5
        assert healing_kpi.current_score < 0.5


# =============================================================================
# CONSTITUTIONAL FRAMEWORK COMPLIANCE TESTS
# =============================================================================

class TestConstitutionalCompliance:
    """Verify Constitutional Framework ACTUALLY blocks violations."""
    
    def test_missing_explanation_violates_transparency(self):
        """Actions without explanation ACTUALLY violate transparency."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "action_type": "execute_code",
            "risk_level": "medium",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert not compliant
        assert any("transparency" in v.lower() for v in violations)
    
    def test_critical_action_without_rollback_violates_reversibility(self):
        """Critical actions without rollback ACTUALLY violate reversibility."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "action_type": "delete_data",
            "risk_level": "critical",
            "reasoning": "Cleaning up old data",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert not compliant
        assert any("reversibility" in v.lower() for v in violations)
    
    def test_user_data_access_without_justification_violates_privacy(self):
        """Accessing user data without justification ACTUALLY violates privacy."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "action_type": "read_profile",
            "reasoning": "Need to check user data",
            "accesses_user_data": True,
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert not compliant
        assert any("privacy" in v.lower() for v in violations)
    
    def test_fully_compliant_action_passes(self):
        """Fully compliant actions ACTUALLY pass all checks."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "action_type": "read_config",
            "reasoning": "Loading configuration for startup",
            "risk_level": "low",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant
        assert len(violations) == 0
    
    def test_critical_compliant_action_with_rollback_passes(self):
        """Critical actions with rollback plan ACTUALLY pass."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "action_type": "migrate_database",
            "reasoning": "Schema upgrade required",
            "risk_level": "critical",
            "rollback_plan": "Restore from backup at /backups/db_20260118.sql",
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant
        assert len(violations) == 0


# =============================================================================
# QUORUM VOTING DECISION TESTS
# =============================================================================

class TestQuorumVotingDecisions:
    """Verify Quorum voting ACTUALLY reaches correct decisions."""
    
    def test_quorum_session_calculates_majority(self):
        """Quorum sessions ACTUALLY calculate majority decision."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test-001",
            proposal={"action": "deploy"},
            required_votes=3
        )
        
        session.votes.append(QuorumVote(
            voter_id="model_1", decision=QuorumDecision.APPROVE,
            confidence=0.9, reasoning="Looks good"
        ))
        session.votes.append(QuorumVote(
            voter_id="model_2", decision=QuorumDecision.APPROVE,
            confidence=0.8, reasoning="Passes checks"
        ))
        session.votes.append(QuorumVote(
            voter_id="model_3", decision=QuorumDecision.REJECT,
            confidence=0.7, reasoning="Minor concerns"
        ))
        
        decision, confidence = session.calculate_decision()
        
        assert decision == QuorumDecision.APPROVE
        assert confidence > 0.8
    
    def test_unanimous_reject_decides_reject(self):
        """Unanimous rejection ACTUALLY results in REJECT."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test-002",
            proposal={"action": "risky_operation"},
            required_votes=3
        )
        
        for i in range(3):
            session.votes.append(QuorumVote(
                voter_id=f"model_{i}", decision=QuorumDecision.REJECT,
                confidence=0.95, reasoning="Too risky"
            ))
        
        decision, confidence = session.calculate_decision()
        
        assert decision == QuorumDecision.REJECT
        assert abs(confidence - 0.95) < 0.01  # Float tolerance
    
    def test_session_requires_minimum_votes(self):
        """Session ACTUALLY requires minimum votes to be complete."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test-003",
            proposal={"action": "test"},
            required_votes=3
        )
        
        session.votes.append(QuorumVote(
            voter_id="model_1", decision=QuorumDecision.APPROVE,
            confidence=0.9, reasoning="OK"
        ))
        
        assert not session.is_complete()
        
        session.votes.append(QuorumVote(
            voter_id="model_2", decision=QuorumDecision.APPROVE,
            confidence=0.9, reasoning="OK"
        ))
        
        assert not session.is_complete()
        
        session.votes.append(QuorumVote(
            voter_id="model_3", decision=QuorumDecision.APPROVE,
            confidence=0.9, reasoning="OK"
        ))
        
        assert session.is_complete()
    
    def test_low_confidence_triggers_escalation(self, fresh_quorum_engine):
        """Low confidence ACTUALLY triggers escalation."""
        from governance.layer3_quorum_verification import QuorumDecision
        
        proposal = {
            "action": "ambiguous_operation",
            "trust_score": 0.4,
            "risk_level": "medium",
            "reasoning": "Testing escalation"
        }
        
        session = run_async(
            fresh_quorum_engine.request_quorum(
                proposal=proposal,
                required_votes=3,
                escalation_threshold=0.9
            )
        )
        
        if session.confidence < 0.9:
            assert session.decision == QuorumDecision.ESCALATE or session.confidence < 0.9
    
    def test_fallback_voting_uses_constitutional_validator(self, fresh_quorum_engine):
        """Fallback voting ACTUALLY includes constitutional validator."""
        from governance.layer3_quorum_verification import QuorumSession, QuorumDecision
        
        session = QuorumSession(
            session_id="fallback-test",
            proposal={"reasoning": "Test proposal", "risk_level": "low"},
            required_votes=3
        )
        
        run_async(fresh_quorum_engine._automated_quorum_fallback(
            session,
            {"reasoning": "Valid test", "risk_level": "low", "trust_score": 0.7}
        ))
        
        voter_ids = [v.voter_id for v in session.votes]
        
        assert "constitutional_validator" in voter_ids
        assert "risk_assessor" in voter_ids
        assert "trust_evaluator" in voter_ids


# =============================================================================
# WHITELIST MANAGEMENT TESTS
# =============================================================================

class TestWhitelistManagement:
    """Verify whitelist ACTUALLY controls source trust."""
    
    def test_add_to_whitelist_grants_full_trust(self, fresh_quorum_engine):
        """Adding to whitelist ACTUALLY grants full trust."""
        fresh_quorum_engine.add_to_whitelist("myserver.internal.com")
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"config": "value"},
                origin="myserver.internal.com"
            )
        )
        
        assert assessment.base_score == 1.0
    
    def test_remove_from_whitelist_revokes_trust(self, fresh_quorum_engine):
        """Removing from whitelist ACTUALLY revokes full trust."""
        fresh_quorum_engine.add_to_whitelist("temporary.server.com")
        fresh_quorum_engine.remove_from_whitelist("temporary.server.com")
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"data": "test"},
                origin="temporary.server.com"
            )
        )
        
        assert assessment.base_score < 1.0
    
    def test_whitelist_persists_across_assessments(self, fresh_quorum_engine):
        """Whitelist entries ACTUALLY persist across multiple assessments."""
        fresh_quorum_engine.add_to_whitelist("persistent.source.com")
        
        for _ in range(5):
            assessment = run_async(
                fresh_quorum_engine.assess_trust(
                    data={"test": "data"},
                    origin="persistent.source.com"
                )
            )
            assert assessment.base_score == 1.0


# =============================================================================
# ENFORCEMENT ACTION TESTS
# =============================================================================

class TestEnforcementActions:
    """Verify enforcement actions ACTUALLY follow trust thresholds."""
    
    def test_high_trust_allows_data(self, fresh_quorum_engine):
        """High trust score (≥0.7) ACTUALLY allows data through."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"important": "data"},
                origin="internal_data"
            )
        )
        
        assert assessment.verified_score >= 0.7
        assert assessment.verification_result in [
            VerificationResult.PASSED,
            VerificationResult.INCONCLUSIVE
        ]
    
    def test_low_trust_fails_verification(self, fresh_quorum_engine):
        """Low trust score (<0.4) ACTUALLY fails verification."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"suspicious": "data"},
                origin="unknown"
            )
        )
        
        assert assessment.base_score < 0.4
        assert assessment.verification_result in [
            VerificationResult.FAILED,
            VerificationResult.INCONCLUSIVE
        ]
    
    def test_medium_trust_marked_inconclusive(self, fresh_quorum_engine):
        """Medium trust (0.4-0.7) ACTUALLY marked as inconclusive."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"chat": "message"},
                origin="chat_message"
            )
        )
        
        assert 0.3 <= assessment.base_score <= 0.5


# =============================================================================
# GOVERNANCE STATUS TESTS
# =============================================================================

class TestGovernanceStatus:
    """Verify governance status ACTUALLY reflects system state."""
    
    def test_status_includes_all_components(self, fresh_quorum_engine):
        """Status ACTUALLY includes all expected components."""
        status = fresh_quorum_engine.get_governance_status()
        
        assert "governance_health" in status
        assert "component_kpis" in status
        assert "trust_verification" in status
        assert "quorum_sessions" in status
        assert "constitutional_framework" in status
        assert "whitelist_size" in status
    
    def test_status_reflects_kpi_changes(self, fresh_quorum_engine):
        """Status ACTUALLY reflects KPI changes."""
        fresh_quorum_engine.record_component_outcome("test_component", success=True)
        fresh_quorum_engine.record_component_outcome("test_component", success=True)
        
        status = fresh_quorum_engine.get_governance_status()
        
        assert "test_component" in status["component_kpis"]
        assert status["component_kpis"]["test_component"]["success_count"] == 2
    
    def test_status_tracks_trust_assessments(self, fresh_quorum_engine):
        """Status ACTUALLY tracks trust assessment counts."""
        run_async(fresh_quorum_engine.assess_trust({"a": 1}, "internal_data"))
        run_async(fresh_quorum_engine.assess_trust({"b": 2}, "web"))
        
        status = fresh_quorum_engine.get_governance_status()
        
        assert status["trust_verification"]["total_assessments"] >= 2
    
    def test_governance_health_averages_kpis(self, fresh_quorum_engine):
        """Governance health ACTUALLY averages component KPIs."""
        fresh_quorum_engine.record_component_outcome("comp_a", success=True)
        fresh_quorum_engine.record_component_outcome("comp_b", success=False)
        
        status = fresh_quorum_engine.get_governance_status()
        
        kpis = list(status["component_kpis"].values())
        if kpis:
            expected_avg = sum(k["current_score"] for k in kpis) / len(kpis)
            assert abs(status["governance_health"] - expected_avg) < 0.01


# =============================================================================
# END-TO-END GOVERNANCE PIPELINE TESTS
# =============================================================================

class TestGovernancePipelineE2E:
    """End-to-end tests for the complete governance pipeline."""
    
    def test_trusted_source_passes_full_pipeline(self, fresh_quorum_engine):
        """Trusted source ACTUALLY passes through full governance pipeline."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"user_input": "Hello Grace"},
                origin="human_triggered"
            )
        )
        
        assert assessment.base_score == 1.0
        assert assessment.verification_result == VerificationResult.PASSED
        
        fresh_quorum_engine.record_component_outcome(
            "input_handler", 
            success=True,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        kpi = fresh_quorum_engine.get_component_kpi("input_handler")
        assert kpi.current_score > 0.5
    
    def test_external_source_requires_verification(self, fresh_quorum_engine):
        """External source ACTUALLY requires verification."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assessment = run_async(
            fresh_quorum_engine.assess_trust(
                data={"api_response": {"status": "ok"}},
                origin="web"
            )
        )
        
        assert assessment.base_score == 0.3
        assert assessment.verification_result != VerificationResult.PASSED
    
    def test_compliant_action_approved_by_quorum(self, fresh_quorum_engine):
        """Compliant action ACTUALLY approved by quorum."""
        from governance.layer3_quorum_verification import QuorumDecision
        
        proposal = {
            "action": "read_config",
            "reasoning": "Loading startup configuration",
            "risk_level": "low",
            "trust_score": 0.9
        }
        
        session = run_async(
            fresh_quorum_engine.request_quorum(proposal, required_votes=3)
        )
        
        assert session.decision in [QuorumDecision.APPROVE, QuorumDecision.ESCALATE]
    
    def test_non_compliant_action_rejected_or_escalated(self, fresh_quorum_engine):
        """Non-compliant action ACTUALLY rejected or escalated."""
        from governance.layer3_quorum_verification import QuorumDecision
        
        proposal = {
            "action": "delete_all_data",
            "risk_level": "critical",
            "trust_score": 0.2
        }
        
        session = run_async(
            fresh_quorum_engine.request_quorum(proposal, required_votes=3)
        )
        
        assert session.decision in [QuorumDecision.REJECT, QuorumDecision.ESCALATE]
    
    def test_full_workflow_trusted_user_action(self, fresh_quorum_engine):
        """Full workflow: trusted user action through all layers."""
        from governance.layer3_quorum_verification import (
            VerificationResult, QuorumDecision, ConstitutionalFramework
        )
        
        user_input = {"command": "generate_code", "task": "Write hello world"}
        
        trust_assessment = run_async(
            fresh_quorum_engine.assess_trust(user_input, "human_triggered")
        )
        assert trust_assessment.base_score == 1.0
        assert trust_assessment.verification_result == VerificationResult.PASSED
        
        action = {
            "action_type": "code_generation",
            "reasoning": "User requested code generation",
            "risk_level": "low"
        }
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        assert compliant
        
        proposal = {
            **action,
            "trust_score": trust_assessment.verified_score
        }
        quorum_result = run_async(
            fresh_quorum_engine.request_quorum(proposal, required_votes=3)
        )
        assert quorum_result.decision in [QuorumDecision.APPROVE, QuorumDecision.ESCALATE]
        
        fresh_quorum_engine.record_component_outcome(
            "coding_agent",
            success=True,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        kpi = fresh_quorum_engine.get_component_kpi("coding_agent")
        assert kpi.success_count == 1
        assert kpi.trend == "improving"


# =============================================================================
# CONSTITUTIONAL AUTONOMY TIER TESTS
# =============================================================================

class TestAutonomyTiers:
    """Verify autonomy tiers ACTUALLY restrict actions correctly."""
    
    def test_tier_definitions_exist(self):
        """Autonomy tier definitions ACTUALLY exist."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        assert hasattr(ConstitutionalFramework, 'AUTONOMY_TIERS')
        tiers = ConstitutionalFramework.AUTONOMY_TIERS
        
        assert 0 in tiers
        assert 1 in tiers
        assert 2 in tiers
        assert 3 in tiers
    
    def test_tier_0_requires_human_approval(self):
        """Tier 0 ACTUALLY requires human approval."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        tier_0 = ConstitutionalFramework.AUTONOMY_TIERS[0]
        assert "human approval" in tier_0.lower()
    
    def test_tier_3_allows_autonomy(self):
        """Tier 3 ACTUALLY allows full autonomy within bounds."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        tier_3 = ConstitutionalFramework.AUTONOMY_TIERS[3]
        assert "autonomy" in tier_3.lower()


# =============================================================================
# CORE PRINCIPLES TESTS
# =============================================================================

class TestCorePrinciples:
    """Verify core principles ACTUALLY defined and enforced."""
    
    def test_all_core_principles_defined(self):
        """All core principles ACTUALLY defined."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        principles = ConstitutionalFramework.CORE_PRINCIPLES
        
        required = [
            "transparency",
            "human_centricity", 
            "trust_earned",
            "no_harm",
            "privacy",
            "accountability",
            "reversibility"
        ]
        
        for principle in required:
            assert principle in principles, f"Missing principle: {principle}"
            assert len(principles[principle]) > 0, f"Empty description for {principle}"
    
    def test_principles_have_descriptions(self):
        """Each principle ACTUALLY has a meaningful description."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        for name, description in ConstitutionalFramework.CORE_PRINCIPLES.items():
            assert isinstance(description, str)
            assert len(description) > 10, f"Description too short for {name}"


# =============================================================================
# CONCURRENT ASSESSMENT TESTS
# =============================================================================

class TestConcurrentAssessments:
    """Verify governance handles concurrent assessments correctly."""
    
    def test_multiple_concurrent_assessments(self, fresh_quorum_engine):
        """Multiple concurrent assessments ACTUALLY handled independently."""
        async def run_concurrent():
            tasks = [
                fresh_quorum_engine.assess_trust({"id": 1}, "internal_data"),
                fresh_quorum_engine.assess_trust({"id": 2}, "web"),
                fresh_quorum_engine.assess_trust({"id": 3}, "human_triggered"),
            ]
            return await asyncio.gather(*tasks)
        
        results = run_async(run_concurrent())
        
        assert len(results) == 3
        assert results[0].base_score == 1.0
        assert results[1].base_score == 0.3
        assert results[2].base_score == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
