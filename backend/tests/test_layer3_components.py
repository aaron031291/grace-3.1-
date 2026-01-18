"""
Tests for Layer 3 Governance Components (Unit Tests)

Tests individual components of the Layer 3 Quorum Verification Engine:
- TrustSource classification
- TrustAssessment
- ComponentKPI tracking
- ConstitutionalFramework
- QuorumSession and voting
- LayerEnforcement decisions
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch, AsyncMock


# ==================== TrustSource Tests ====================

@pytest.mark.unit
class TestTrustSource:
    """Test TrustSource classification."""

    def test_trust_source_enum_values(self):
        """Test all TrustSource enum values exist."""
        from governance.layer3_quorum_verification import TrustSource
        
        assert TrustSource.WHITELIST.value == "whitelist"
        assert TrustSource.INTERNAL_DATA.value == "internal_data"
        assert TrustSource.PROACTIVE_LEARNING.value == "proactive_learning"
        assert TrustSource.ORACLE.value == "oracle"
        assert TrustSource.HUMAN_TRIGGERED.value == "human_triggered"
        assert TrustSource.WEB.value == "web"
        assert TrustSource.LLM_QUERY.value == "llm_query"
        assert TrustSource.CHAT_MESSAGE.value == "chat_message"
        assert TrustSource.EXTERNAL_FILE.value == "external_file"
        assert TrustSource.UNKNOWN.value == "unknown"

    def test_trusted_sources_are_100_percent(self):
        """Test that trusted sources return 1.0 base score."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        for source in [TrustSource.WHITELIST, TrustSource.INTERNAL_DATA,
                       TrustSource.PROACTIVE_LEARNING, TrustSource.ORACLE,
                       TrustSource.HUMAN_TRIGGERED]:
            score = engine.get_source_base_score(source)
            assert score == 1.0, f"{source.value} should be 100% trusted"

    def test_verification_required_sources_lower_score(self):
        """Test that verification-required sources have lower base scores."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        verification_sources = {
            TrustSource.WEB: 0.3,
            TrustSource.LLM_QUERY: 0.5,
            TrustSource.CHAT_MESSAGE: 0.4,
            TrustSource.EXTERNAL_FILE: 0.3,
            TrustSource.UNKNOWN: 0.1
        }
        
        for source, expected_score in verification_sources.items():
            score = engine.get_source_base_score(source)
            assert score == expected_score, f"{source.value} should have score {expected_score}"


# ==================== Source Classification Tests ====================

@pytest.mark.unit
class TestSourceClassification:
    """Test source classification logic."""

    def test_classify_human_input(self):
        """Test human input classified correctly."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assert engine.classify_source("user_input") == TrustSource.HUMAN_TRIGGERED
        assert engine.classify_source("human_action") == TrustSource.HUMAN_TRIGGERED
        assert engine.classify_source("manual_entry") == TrustSource.HUMAN_TRIGGERED

    def test_classify_internal_data(self):
        """Test internal data classified correctly."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assert engine.classify_source("layer1_storage") == TrustSource.INTERNAL_DATA
        assert engine.classify_source("layer2_ooda") == TrustSource.INTERNAL_DATA
        assert engine.classify_source("internal_system") == TrustSource.INTERNAL_DATA

    def test_classify_proactive_learning(self):
        """Test proactive learning classified correctly."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assert engine.classify_source("proactive_learning") == TrustSource.PROACTIVE_LEARNING
        assert engine.classify_source("self_learned") == TrustSource.PROACTIVE_LEARNING

    def test_classify_external_sources(self):
        """Test external sources classified correctly."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assert engine.classify_source("web_api") == TrustSource.WEB
        assert engine.classify_source("http_response") == TrustSource.WEB
        assert engine.classify_source("llm_response") == TrustSource.LLM_QUERY
        assert engine.classify_source("gpt_output") == TrustSource.LLM_QUERY
        assert engine.classify_source("chat_message") == TrustSource.CHAT_MESSAGE
        assert engine.classify_source("file_upload") == TrustSource.EXTERNAL_FILE

    def test_classify_unknown(self):
        """Test unknown sources classified as UNKNOWN."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assert engine.classify_source("random_source") == TrustSource.UNKNOWN
        assert engine.classify_source("xyz123") == TrustSource.UNKNOWN

    def test_whitelist_takes_precedence(self):
        """Test that whitelisted sources return WHITELIST."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        engine.add_to_whitelist("trusted_api")
        
        assert engine.classify_source("trusted_api") == TrustSource.WHITELIST


# ==================== ComponentKPI Tests ====================

@pytest.mark.unit
class TestComponentKPI:
    """Test ComponentKPI tracking."""

    def test_kpi_initialization(self):
        """Test KPI initializes with correct defaults."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(
            component_id="test_component",
            component_name="Test Component"
        )
        
        assert kpi.component_id == "test_component"
        assert kpi.component_name == "Test Component"
        assert kpi.success_count == 0
        assert kpi.failure_count == 0
        assert kpi.total_operations == 0
        assert kpi.current_score == 0.5
        assert kpi.trend == "stable"

    def test_kpi_success_increases_score(self):
        """Test successful outcome increases KPI score."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(
            component_id="test",
            component_name="Test"
        )
        initial_score = kpi.current_score
        
        kpi.record_outcome(success=True, meets_grace_standard=True, meets_user_standard=True)
        
        assert kpi.current_score > initial_score
        assert kpi.success_count == 1
        assert kpi.failure_count == 0
        assert kpi.trend == "improving"

    def test_kpi_failure_decreases_score(self):
        """Test failed outcome decreases KPI score."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(
            component_id="test",
            component_name="Test"
        )
        initial_score = kpi.current_score
        
        kpi.record_outcome(success=False)
        
        assert kpi.current_score < initial_score
        assert kpi.success_count == 0
        assert kpi.failure_count == 1
        assert kpi.trend == "declining"

    def test_kpi_partial_standards_smaller_increase(self):
        """Test partial standards met gives smaller increase."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi_full = ComponentKPI(component_id="full", component_name="Full")
        kpi_partial = ComponentKPI(component_id="partial", component_name="Partial")
        
        kpi_full.record_outcome(success=True, meets_grace_standard=True, meets_user_standard=True)
        kpi_partial.record_outcome(success=True, meets_grace_standard=True, meets_user_standard=False)
        
        assert kpi_full.current_score > kpi_partial.current_score

    def test_kpi_score_bounds(self):
        """Test KPI score stays within 0-1 bounds."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        
        # Many successes
        for _ in range(100):
            kpi.record_outcome(success=True, meets_grace_standard=True, meets_user_standard=True)
        assert kpi.current_score <= 1.0
        
        # Many failures
        for _ in range(100):
            kpi.record_outcome(success=False)
        assert kpi.current_score >= 0.0

    def test_kpi_to_dict(self):
        """Test KPI serialization."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        kpi.record_outcome(success=True)
        
        data = kpi.to_dict()
        
        assert "component_id" in data
        assert "component_name" in data
        assert "current_score" in data
        assert "success_rate" in data
        assert "trend" in data

    def test_kpi_history_limit(self):
        """Test KPI history is limited to 100 entries."""
        from governance.layer3_quorum_verification import ComponentKPI
        
        kpi = ComponentKPI(component_id="test", component_name="Test")
        
        for _ in range(150):
            kpi.record_outcome(success=True)
        
        assert len(kpi.history) == 100


# ==================== ConstitutionalFramework Tests ====================

@pytest.mark.unit
class TestConstitutionalFramework:
    """Test ConstitutionalFramework compliance checking."""

    def test_core_principles_exist(self):
        """Test all core principles are defined."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        required_principles = [
            "transparency", "human_centricity", "trust_earned",
            "no_harm", "privacy", "accountability", "reversibility"
        ]
        
        for principle in required_principles:
            assert principle in ConstitutionalFramework.CORE_PRINCIPLES

    def test_autonomy_tiers_exist(self):
        """Test autonomy tiers are defined."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        assert 0 in ConstitutionalFramework.AUTONOMY_TIERS
        assert 1 in ConstitutionalFramework.AUTONOMY_TIERS
        assert 2 in ConstitutionalFramework.AUTONOMY_TIERS
        assert 3 in ConstitutionalFramework.AUTONOMY_TIERS

    def test_compliance_check_with_reasoning(self):
        """Test compliant action with reasoning passes."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "type": "file_read",
            "reasoning": "Reading file for code analysis"
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant is True
        assert len(violations) == 0

    def test_compliance_check_missing_reasoning(self):
        """Test action without reasoning fails transparency."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "type": "file_modify"
            # Missing reasoning
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant is False
        assert any("transparency" in v for v in violations)

    def test_compliance_check_critical_without_rollback(self):
        """Test critical action without rollback plan fails."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "type": "database_delete",
            "risk_level": "critical",
            "reasoning": "Deleting old records"
            # Missing rollback_plan
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant is False
        assert any("reversibility" in v for v in violations)

    def test_compliance_check_privacy_violation(self):
        """Test privacy violation detection."""
        from governance.layer3_quorum_verification import ConstitutionalFramework
        
        action = {
            "type": "data_access",
            "accesses_user_data": True,
            "reasoning": "Accessing user data"
            # Missing privacy_justified
        }
        
        compliant, violations = ConstitutionalFramework.check_compliance(action)
        
        assert compliant is False
        assert any("privacy" in v for v in violations)


# ==================== QuorumSession Tests ====================

@pytest.mark.unit
class TestQuorumSession:
    """Test QuorumSession voting logic."""

    def test_quorum_session_creation(self):
        """Test quorum session initialization."""
        from governance.layer3_quorum_verification import QuorumSession
        
        session = QuorumSession(
            session_id="test-123",
            proposal={"action": "deploy"},
            required_votes=3
        )
        
        assert session.session_id == "test-123"
        assert session.required_votes == 3
        assert len(session.votes) == 0
        assert session.decision is None

    def test_quorum_is_complete(self):
        """Test quorum completion check."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test",
            proposal={},
            required_votes=2
        )
        
        assert session.is_complete() is False
        
        session.votes.append(QuorumVote(
            voter_id="model1",
            decision=QuorumDecision.APPROVE,
            confidence=0.9,
            reasoning="Looks good"
        ))
        
        assert session.is_complete() is False
        
        session.votes.append(QuorumVote(
            voter_id="model2",
            decision=QuorumDecision.APPROVE,
            confidence=0.8,
            reasoning="Approved"
        ))
        
        assert session.is_complete() is True

    def test_quorum_calculate_decision_approve(self):
        """Test quorum decision calculation with majority approve."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test",
            proposal={},
            required_votes=3
        )
        
        session.votes = [
            QuorumVote("m1", QuorumDecision.APPROVE, 0.9, "yes"),
            QuorumVote("m2", QuorumDecision.APPROVE, 0.8, "yes"),
            QuorumVote("m3", QuorumDecision.REJECT, 0.6, "no"),
        ]
        
        decision, confidence = session.calculate_decision()
        
        assert decision == QuorumDecision.APPROVE
        assert abs(confidence - 0.85) < 0.01  # Average of 0.9 and 0.8 (with floating point tolerance)

    def test_quorum_calculate_decision_reject(self):
        """Test quorum decision calculation with majority reject."""
        from governance.layer3_quorum_verification import (
            QuorumSession, QuorumVote, QuorumDecision
        )
        
        session = QuorumSession(
            session_id="test",
            proposal={},
            required_votes=3
        )
        
        session.votes = [
            QuorumVote("m1", QuorumDecision.REJECT, 0.9, "no"),
            QuorumVote("m2", QuorumDecision.REJECT, 0.7, "no"),
            QuorumVote("m3", QuorumDecision.APPROVE, 0.5, "yes"),
        ]
        
        decision, confidence = session.calculate_decision()
        
        assert decision == QuorumDecision.REJECT

    def test_quorum_empty_votes_rejects(self):
        """Test empty quorum defaults to reject."""
        from governance.layer3_quorum_verification import QuorumSession, QuorumDecision
        
        session = QuorumSession(
            session_id="test",
            proposal={},
            required_votes=3
        )
        
        decision, confidence = session.calculate_decision()
        
        assert decision == QuorumDecision.REJECT
        assert confidence == 0.0


# ==================== TrustAssessment Tests ====================

@pytest.mark.unit
class TestTrustAssessment:
    """Test TrustAssessment data structure."""

    def test_trust_assessment_creation(self):
        """Test TrustAssessment initialization."""
        from governance.layer3_quorum_verification import (
            TrustAssessment, TrustSource, VerificationResult
        )
        
        assessment = TrustAssessment(
            assessment_id="test-123",
            source=TrustSource.WEB,
            base_score=0.3,
            verified_score=0.6,
            verification_result=VerificationResult.PASSED
        )
        
        assert assessment.assessment_id == "test-123"
        assert assessment.source == TrustSource.WEB
        assert assessment.base_score == 0.3
        assert assessment.verified_score == 0.6
        assert assessment.verification_result == VerificationResult.PASSED

    def test_trust_assessment_to_dict(self):
        """Test TrustAssessment serialization."""
        from governance.layer3_quorum_verification import (
            TrustAssessment, TrustSource, VerificationResult
        )
        
        assessment = TrustAssessment(
            assessment_id="test",
            source=TrustSource.HUMAN_TRIGGERED,
            base_score=1.0,
            verified_score=1.0,
            verification_result=VerificationResult.PASSED,
            genesis_key_id="GK-123",
            correlation_sources=["layer1", "layer2"],
            timesense_validated=True
        )
        
        data = assessment.to_dict()
        
        assert data["assessment_id"] == "test"
        assert data["source"] == "human_triggered"
        assert data["base_score"] == 1.0
        assert data["verified_score"] == 1.0
        assert data["verification_result"] == "passed"
        assert data["genesis_key_id"] == "GK-123"
        assert "correlation_sources" in data
        assert "timestamp" not in data  # Should be "created_at"


# ==================== VerificationResult Tests ====================

@pytest.mark.unit
class TestVerificationResult:
    """Test VerificationResult enum."""

    def test_verification_result_values(self):
        """Test all VerificationResult values."""
        from governance.layer3_quorum_verification import VerificationResult
        
        assert VerificationResult.PASSED.value == "passed"
        assert VerificationResult.FAILED.value == "failed"
        assert VerificationResult.INCONCLUSIVE.value == "inconclusive"
        assert VerificationResult.PENDING.value == "pending"


# ==================== EnforcementAction Tests ====================

@pytest.mark.unit
class TestEnforcementAction:
    """Test EnforcementAction enum."""

    def test_enforcement_action_values(self):
        """Test all EnforcementAction values."""
        from governance.layer_enforcement import EnforcementAction
        
        assert EnforcementAction.ALLOW.value == "allow"
        assert EnforcementAction.BLOCK.value == "block"
        assert EnforcementAction.QUARANTINE.value == "quarantine"
        assert EnforcementAction.ESCALATE.value == "escalate"


# ==================== EnforcementDecision Tests ====================

@pytest.mark.unit
class TestEnforcementDecision:
    """Test EnforcementDecision data structure."""

    def test_enforcement_decision_creation(self):
        """Test EnforcementDecision initialization."""
        from governance.layer_enforcement import EnforcementDecision, EnforcementAction
        
        decision = EnforcementDecision(
            action=EnforcementAction.ALLOW,
            trust_score=0.85,
            source_classification="human_triggered",
            verification_passed=True,
            reasoning="Trust verified"
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.trust_score == 0.85
        assert decision.source_classification == "human_triggered"
        assert decision.verification_passed is True

    def test_enforcement_decision_to_dict(self):
        """Test EnforcementDecision serialization."""
        from governance.layer_enforcement import EnforcementDecision, EnforcementAction
        
        decision = EnforcementDecision(
            action=EnforcementAction.BLOCK,
            trust_score=0.2,
            source_classification="unknown",
            verification_passed=False,
            reasoning="Low trust score",
            constitutional_compliant=False,
            violations=["privacy violation"]
        )
        
        data = decision.to_dict()
        
        assert data["action"] == "block"
        assert data["trust_score"] == 0.2
        assert data["verification_passed"] is False
        assert data["constitutional_compliant"] is False
        assert "privacy violation" in data["violations"]


# ==================== Whitelist Tests ====================

@pytest.mark.unit
class TestWhitelist:
    """Test whitelist management."""

    def test_add_to_whitelist(self):
        """Test adding source to whitelist."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        engine.add_to_whitelist("trusted_source")
        
        assert "trusted_source" in engine.whitelist

    def test_remove_from_whitelist(self):
        """Test removing source from whitelist."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        engine.add_to_whitelist("temp_source")
        
        engine.remove_from_whitelist("temp_source")
        
        assert "temp_source" not in engine.whitelist

    def test_whitelist_affects_classification(self):
        """Test whitelist affects source classification."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        # Before whitelist
        assert engine.classify_source("custom_api") == TrustSource.UNKNOWN
        
        # After whitelist
        engine.add_to_whitelist("custom_api")
        assert engine.classify_source("custom_api") == TrustSource.WHITELIST
