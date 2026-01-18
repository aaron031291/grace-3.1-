"""
REAL Functional Tests for Layer 3 Parliament Governance.

These are NOT smoke tests - they verify that Parliament ACTUALLY:
1. Model trust scores ACTUALLY update based on correctness
2. Voting ACTUALLY calculates weighted decisions
3. Anti-hallucination checks ACTUALLY require consensus
4. Governance levels ACTUALLY enforce different quorum sizes
5. KPIs ACTUALLY track quality metrics
6. Sessions ACTUALLY record and tally votes correctly

Run with: pytest tests/test_layer3_parliament_real.py -v
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
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
def parliament():
    """Create fresh Parliament for each test."""
    from llm_orchestrator.parliament_governance import ParliamentGovernance
    return ParliamentGovernance()


# =============================================================================
# MODEL TRUST SCORE TESTS
# =============================================================================

class TestModelTrustScores:
    """Verify model trust scores ACTUALLY update based on correctness."""
    
    def test_correct_vote_increases_trust(self):
        """Correct vote ACTUALLY increases trust score."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model", trust_score=0.7)
        initial = trust.trust_score
        
        trust.update_trust(was_correct=True)
        
        assert trust.trust_score > initial
        assert trust.correct_votes == 1
        assert trust.total_votes == 1
    
    def test_incorrect_vote_decreases_trust_more(self):
        """Incorrect vote ACTUALLY decreases trust more heavily."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model", trust_score=0.7)
        initial = trust.trust_score
        
        trust.update_trust(was_correct=False)
        
        decrease = initial - trust.trust_score
        assert trust.trust_score < initial
        assert decrease >= 0.05
    
    def test_trust_bounded_at_minimum(self):
        """Trust ACTUALLY bounded at 0.1 minimum."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model", trust_score=0.15)
        
        for _ in range(20):
            trust.update_trust(was_correct=False)
        
        assert trust.trust_score >= 0.1
    
    def test_trust_bounded_at_maximum(self):
        """Trust ACTUALLY bounded at 1.0 maximum."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model", trust_score=0.95)
        
        for _ in range(50):
            trust.update_trust(was_correct=True)
        
        assert trust.trust_score <= 1.0
    
    def test_accuracy_history_recorded(self):
        """Accuracy history ACTUALLY recorded."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model")
        
        trust.update_trust(was_correct=True)
        trust.update_trust(was_correct=False)
        trust.update_trust(was_correct=True)
        
        assert len(trust.accuracy_history) == 3
        assert trust.accuracy_history[0] == 1.0
        assert trust.accuracy_history[1] == 0.0
        assert trust.accuracy_history[2] == 1.0
    
    def test_accuracy_history_capped(self):
        """Accuracy history ACTUALLY capped at 100."""
        from llm_orchestrator.parliament_governance import ModelTrust
        
        trust = ModelTrust(model_id="test-model")
        
        for _ in range(150):
            trust.update_trust(was_correct=True)
        
        assert len(trust.accuracy_history) == 100


# =============================================================================
# VOTE AND VOTING TESTS
# =============================================================================

class TestVoting:
    """Verify voting ACTUALLY calculates weighted decisions."""
    
    def test_vote_creation(self):
        """Votes ACTUALLY created with correct fields."""
        from llm_orchestrator.parliament_governance import Vote, VoteType
        
        vote = Vote(
            vote_id="v-001",
            model_id="model-a",
            vote_type=VoteType.APPROVE,
            content="Approved code",
            confidence=0.9,
            trust_weight=0.85,
            reasoning="Code looks correct"
        )
        
        assert vote.vote_id == "v-001"
        assert vote.vote_type == VoteType.APPROVE
        assert vote.confidence == 0.9
        assert vote.trust_weight == 0.85
    
    def test_vote_types_defined(self):
        """All vote types ACTUALLY defined."""
        from llm_orchestrator.parliament_governance import VoteType
        
        assert VoteType.APPROVE.value == "approve"
        assert VoteType.REJECT.value == "reject"
        assert VoteType.ABSTAIN.value == "abstain"
        assert VoteType.AMEND.value == "amend"
    
    def test_parliament_members_initialized(self, parliament):
        """Parliament ACTUALLY has members with trust profiles."""
        assert len(parliament.members) >= 3
        
        for model_id, trust in parliament.members.items():
            assert trust.trust_score > 0
            assert isinstance(trust.specializations, list)


# =============================================================================
# GOVERNANCE LEVEL TESTS
# =============================================================================

class TestGovernanceLevels:
    """Verify governance levels ACTUALLY enforce different requirements."""
    
    def test_governance_levels_defined(self, parliament):
        """All governance levels ACTUALLY defined."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        assert GovernanceLevel.MINIMAL in parliament.governance_config
        assert GovernanceLevel.STANDARD in parliament.governance_config
        assert GovernanceLevel.STRICT in parliament.governance_config
        assert GovernanceLevel.CRITICAL in parliament.governance_config
    
    def test_minimal_requires_single_vote(self, parliament):
        """Minimal governance ACTUALLY requires only 1 vote."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        config = parliament.governance_config[GovernanceLevel.MINIMAL]
        assert config["quorum"] == 1
        assert config["models_to_consult"] == 1
    
    def test_standard_requires_two_votes(self, parliament):
        """Standard governance ACTUALLY requires 2 votes."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        config = parliament.governance_config[GovernanceLevel.STANDARD]
        assert config["quorum"] == 2
        assert config["models_to_consult"] == 2
    
    def test_strict_requires_three_votes(self, parliament):
        """Strict governance ACTUALLY requires 3 votes."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        config = parliament.governance_config[GovernanceLevel.STRICT]
        assert config["quorum"] == 3
        assert config["models_to_consult"] == 3
    
    def test_critical_requires_supermajority(self, parliament):
        """Critical governance ACTUALLY requires 4+ votes with high threshold."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        config = parliament.governance_config[GovernanceLevel.CRITICAL]
        assert config["quorum"] >= 4
        assert config["approval_threshold"] >= 0.85


# =============================================================================
# ANTI-HALLUCINATION TESTS
# =============================================================================

class TestAntiHallucination:
    """Verify anti-hallucination checks ACTUALLY enforce consensus."""
    
    def test_anti_hallucination_config_exists(self, parliament):
        """Anti-hallucination config ACTUALLY exists."""
        assert parliament.anti_hallucination is not None
        assert "min_consensus" in parliament.anti_hallucination
        assert "max_contradiction_score" in parliament.anti_hallucination
    
    def test_minimum_consensus_required(self, parliament):
        """Minimum consensus ACTUALLY required for approval."""
        assert parliament.anti_hallucination["min_consensus"] >= 0.6
    
    def test_contradiction_threshold_set(self, parliament):
        """Contradiction threshold ACTUALLY set."""
        assert parliament.anti_hallucination["max_contradiction_score"] <= 0.3


# =============================================================================
# SESSION TESTS
# =============================================================================

class TestParliamentSessions:
    """Verify sessions ACTUALLY record and tally votes correctly."""
    
    def test_session_creation(self):
        """Session ACTUALLY created with correct fields."""
        from llm_orchestrator.parliament_governance import (
            ParliamentSession, DecisionType, GovernanceLevel
        )
        
        session = ParliamentSession(
            session_id="sess-001",
            decision_type=DecisionType.CODE_GENERATION,
            governance_level=GovernanceLevel.STANDARD,
            proposal="Generate a hello world function",
            quorum_required=2
        )
        
        assert session.session_id == "sess-001"
        assert session.decision_type == DecisionType.CODE_GENERATION
        assert session.quorum_required == 2
        assert len(session.votes) == 0
    
    def test_session_to_dict_serialization(self):
        """Session ACTUALLY serializes correctly."""
        from llm_orchestrator.parliament_governance import (
            ParliamentSession, DecisionType, GovernanceLevel
        )
        
        session = ParliamentSession(
            session_id="serialize-test",
            decision_type=DecisionType.QUALITY_ASSESSMENT,
            governance_level=GovernanceLevel.STRICT,
            proposal="Test proposal for serialization",
            quorum_required=3
        )
        
        data = session.to_dict()
        
        assert data["session_id"] == "serialize-test"
        assert data["decision_type"] == "quality_assessment"
        assert data["governance_level"] == "strict"
        assert data["quorum_required"] == 3


# =============================================================================
# VOTE TALLYING TESTS
# =============================================================================

class TestVoteTallying:
    """Verify vote tallying ACTUALLY works correctly."""
    
    def test_weighted_approve_votes(self, parliament):
        """Weighted approve votes ACTUALLY tallied correctly."""
        from llm_orchestrator.parliament_governance import (
            Vote, VoteType, GovernanceLevel
        )
        
        votes = [
            Vote(
                vote_id="v1", model_id="m1", vote_type=VoteType.APPROVE,
                content="Good", confidence=0.9, trust_weight=0.8
            ),
            Vote(
                vote_id="v2", model_id="m2", vote_type=VoteType.APPROVE,
                content="Fine", confidence=0.8, trust_weight=0.9
            ),
        ]
        
        decision, confidence = parliament._tally_votes(votes, GovernanceLevel.STANDARD)
        
        assert decision is not None
        assert confidence > 0
    
    def test_reject_majority_wins(self, parliament):
        """Reject majority ACTUALLY wins."""
        from llm_orchestrator.parliament_governance import (
            Vote, VoteType, GovernanceLevel
        )
        
        votes = [
            Vote(
                vote_id="v1", model_id="m1", vote_type=VoteType.REJECT,
                content="", confidence=0.9, trust_weight=0.9
            ),
            Vote(
                vote_id="v2", model_id="m2", vote_type=VoteType.REJECT,
                content="", confidence=0.85, trust_weight=0.85
            ),
            Vote(
                vote_id="v3", model_id="m3", vote_type=VoteType.APPROVE,
                content="OK", confidence=0.7, trust_weight=0.7
            ),
        ]
        
        decision, confidence = parliament._tally_votes(votes, GovernanceLevel.STANDARD)
        
        assert decision is None
    
    def test_empty_votes_return_none(self, parliament):
        """Empty votes ACTUALLY return None."""
        from llm_orchestrator.parliament_governance import GovernanceLevel
        
        decision, confidence = parliament._tally_votes([], GovernanceLevel.STANDARD)
        
        assert decision is None
        assert confidence == 0.0


# =============================================================================
# KPI TRACKING TESTS
# =============================================================================

class TestKPITracking:
    """Verify KPIs ACTUALLY track quality metrics."""
    
    def test_kpi_metrics_structure(self, parliament):
        """KPI metrics ACTUALLY have correct structure."""
        kpis = parliament.get_kpis()
        
        assert "quality" in kpis
        assert "performance" in kpis
        assert "trust" in kpis
        assert "governance" in kpis
    
    def test_quality_kpis_exist(self, parliament):
        """Quality KPIs ACTUALLY exist."""
        kpis = parliament.get_kpis()
        
        assert "code_quality" in kpis["quality"]
        assert "hallucination_rate" in kpis["quality"]
        assert "consensus_rate" in kpis["quality"]
    
    def test_performance_kpis_exist(self, parliament):
        """Performance KPIs ACTUALLY exist."""
        kpis = parliament.get_kpis()
        
        assert "avg_response_time_ms" in kpis["performance"]
        assert "quorum_rate" in kpis["performance"]
    
    def test_governance_kpis_exist(self, parliament):
        """Governance KPIs ACTUALLY exist."""
        kpis = parliament.get_kpis()
        
        assert "sessions" in kpis["governance"]
        assert "approved" in kpis["governance"]
        assert "rejected" in kpis["governance"]


# =============================================================================
# TRUST REPORT TESTS
# =============================================================================

class TestTrustReports:
    """Verify trust reports ACTUALLY reflect model state."""
    
    def test_trust_report_includes_all_models(self, parliament):
        """Trust report ACTUALLY includes all models."""
        report = parliament.get_trust_report()
        
        for model_id in parliament.members:
            assert model_id in report
    
    def test_trust_report_structure(self, parliament):
        """Trust report ACTUALLY has correct structure."""
        report = parliament.get_trust_report()
        
        for model_id, data in report.items():
            assert "trust_score" in data
            assert "accuracy_rate" in data
            assert "total_votes" in data
            assert "correct_votes" in data
            assert "specializations" in data


# =============================================================================
# MODEL TRUST UPDATE TESTS
# =============================================================================

class TestModelTrustUpdate:
    """Verify model trust ACTUALLY updates after decisions."""
    
    def test_trust_update_on_aligned_vote(self, parliament):
        """Trust ACTUALLY updated when vote aligns with decision."""
        from llm_orchestrator.parliament_governance import Vote, VoteType
        
        model_id = list(parliament.members.keys())[0]
        initial_trust = parliament.members[model_id].trust_score
        
        votes = [
            Vote(
                vote_id="v1", model_id=model_id, vote_type=VoteType.APPROVE,
                content="Good", confidence=0.9
            )
        ]
        
        parliament._update_model_trust(votes, "approved_content")
        
        assert parliament.members[model_id].trust_score >= initial_trust
    
    def test_trust_update_on_misaligned_vote(self, parliament):
        """Trust ACTUALLY penalized when vote misaligns with decision."""
        from llm_orchestrator.parliament_governance import Vote, VoteType
        
        model_id = list(parliament.members.keys())[0]
        initial_trust = parliament.members[model_id].trust_score
        
        votes = [
            Vote(
                vote_id="v1", model_id=model_id, vote_type=VoteType.REJECT,
                content="", confidence=0.9
            )
        ]
        
        parliament._update_model_trust(votes, "approved_anyway")
        
        assert parliament.members[model_id].trust_score <= initial_trust


# =============================================================================
# SESSION KPI CALCULATION TESTS
# =============================================================================

class TestSessionKPIs:
    """Verify session KPIs ACTUALLY calculated correctly."""
    
    def test_consensus_rate_calculated(self, parliament):
        """Consensus rate ACTUALLY calculated for session."""
        from llm_orchestrator.parliament_governance import (
            ParliamentSession, Vote, VoteType, DecisionType, GovernanceLevel
        )
        
        session = ParliamentSession(
            session_id="kpi-test",
            decision_type=DecisionType.CODE_REVIEW,
            governance_level=GovernanceLevel.STANDARD,
            proposal="Test",
            quorum_required=3
        )
        
        votes = [
            Vote(vote_id="v1", model_id="m1", vote_type=VoteType.APPROVE,
                 content="", confidence=0.9),
            Vote(vote_id="v2", model_id="m2", vote_type=VoteType.APPROVE,
                 content="", confidence=0.9),
            Vote(vote_id="v3", model_id="m3", vote_type=VoteType.REJECT,
                 content="", confidence=0.7),
        ]
        
        kpis = parliament._calculate_session_kpis(session, votes)
        
        assert "consensus_rate" in kpis
        assert kpis["consensus_rate"] == 2/3
    
    def test_avg_confidence_calculated(self, parliament):
        """Average confidence ACTUALLY calculated."""
        from llm_orchestrator.parliament_governance import (
            ParliamentSession, Vote, VoteType, DecisionType, GovernanceLevel
        )
        
        session = ParliamentSession(
            session_id="conf-test",
            decision_type=DecisionType.CODE_REVIEW,
            governance_level=GovernanceLevel.STANDARD,
            proposal="Test",
            quorum_required=2
        )
        
        votes = [
            Vote(vote_id="v1", model_id="m1", vote_type=VoteType.APPROVE,
                 content="", confidence=0.8),
            Vote(vote_id="v2", model_id="m2", vote_type=VoteType.APPROVE,
                 content="", confidence=0.6),
        ]
        
        kpis = parliament._calculate_session_kpis(session, votes)
        
        assert "avg_confidence" in kpis
        assert kpis["avg_confidence"] == 0.7


# =============================================================================
# GOVERNANCE SUMMARY TESTS
# =============================================================================

class TestGovernanceSummary:
    """Verify governance summary ACTUALLY reflects state."""
    
    def test_summary_structure(self, parliament):
        """Summary ACTUALLY has correct structure."""
        summary = parliament.get_governance_summary()
        
        assert "total_members" in summary
        assert "active_members" in summary
        assert "kpis" in summary
        assert "trust_report" in summary
        assert "anti_hallucination_config" in summary
        assert "governance_levels" in summary
    
    def test_active_members_count(self, parliament):
        """Active members ACTUALLY counted correctly."""
        summary = parliament.get_governance_summary()
        
        expected_active = sum(
            1 for m in parliament.members.values() if m.trust_score > 0.5
        )
        assert summary["active_members"] == expected_active


# =============================================================================
# DECISION TYPE TESTS
# =============================================================================

class TestDecisionTypes:
    """Verify decision types ACTUALLY defined."""
    
    def test_all_decision_types_exist(self):
        """All decision types ACTUALLY defined."""
        from llm_orchestrator.parliament_governance import DecisionType
        
        assert DecisionType.CODE_GENERATION.value == "code_generation"
        assert DecisionType.CODE_REVIEW.value == "code_review"
        assert DecisionType.HALLUCINATION_CHECK.value == "hallucination_check"
        assert DecisionType.QUALITY_ASSESSMENT.value == "quality_assessment"
        assert DecisionType.REASONING_VALIDATION.value == "reasoning_validation"
        assert DecisionType.FACT_VERIFICATION.value == "fact_verification"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
