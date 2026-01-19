"""
Tests for Layer 3 Governance Integration (End-to-End Tests)

Tests the complete Layer 3 system working together:
- Trust assessment pipeline
- Quorum decision flow
- Layer enforcement integration
- KPI tracking across operations
- API endpoint integration
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch, AsyncMock


# ==================== Layer3QuorumVerification Integration Tests ====================

@pytest.mark.integration
class TestLayer3QuorumEngine:
    """Integration tests for Layer3QuorumVerification engine."""

    def test_engine_initialization(self):
        """Test engine initializes with default KPIs."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        assert engine.component_kpis is not None
        assert len(engine.component_kpis) > 0
        assert "coding_agent" in engine.component_kpis
        assert "self_healing" in engine.component_kpis
        assert "knowledge_base" in engine.component_kpis

    def test_get_quorum_engine_singleton(self):
        """Test get_quorum_engine returns singleton."""
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine1 = get_quorum_engine()
        engine2 = get_quorum_engine()
        
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_assess_trust_human_input(self):
        """Test trust assessment for human input (100% trusted)."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource, VerificationResult
        )
        
        engine = Layer3QuorumVerification()
        
        assessment = await engine.assess_trust(
            data="User typed this message",
            origin="human_triggered",
            genesis_key_id=None
        )
        
        assert assessment.source == TrustSource.HUMAN_TRIGGERED
        assert assessment.base_score == 1.0
        assert assessment.verified_score == 1.0
        assert assessment.verification_result == VerificationResult.PASSED
        assert assessment.quorum_approved is True

    @pytest.mark.asyncio
    async def test_assess_trust_web_source(self):
        """Test trust assessment for web source (requires verification)."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assessment = await engine.assess_trust(
            data={"response": "API data"},
            origin="web_api",
            genesis_key_id=None,
            correlation_check=False,  # Skip for unit test
            timesense_validate=False
        )
        
        assert assessment.source == TrustSource.WEB
        assert assessment.base_score == 0.3
        # Verified score depends on verification results

    @pytest.mark.asyncio
    async def test_assess_trust_internal_data(self):
        """Test trust assessment for internal data (100% trusted)."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource, VerificationResult
        )
        
        engine = Layer3QuorumVerification()
        
        assessment = await engine.assess_trust(
            data={"layer1": "fact"},
            origin="layer1_storage",
            genesis_key_id="GK-123"
        )
        
        assert assessment.source == TrustSource.INTERNAL_DATA
        assert assessment.verified_score == 1.0
        assert assessment.verification_result == VerificationResult.PASSED

    @pytest.mark.asyncio
    async def test_assess_trust_oracle(self):
        """Test trust assessment for oracle data (100% trusted)."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource, VerificationResult
        )
        
        engine = Layer3QuorumVerification()
        
        assessment = await engine.assess_trust(
            data="Oracle validated response",
            origin="oracle_system",
            genesis_key_id=None
        )
        
        assert assessment.source == TrustSource.ORACLE
        assert assessment.verified_score == 1.0
        assert assessment.verification_result == VerificationResult.PASSED

    @pytest.mark.asyncio
    async def test_assess_trust_llm_query(self):
        """Test trust assessment for LLM query (requires verification)."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource
        )
        
        engine = Layer3QuorumVerification()
        
        assessment = await engine.assess_trust(
            data="LLM generated code",
            origin="llm_response",
            genesis_key_id=None,
            correlation_check=False,
            timesense_validate=False
        )
        
        assert assessment.source == TrustSource.LLM_QUERY
        assert assessment.base_score == 0.5

    @pytest.mark.asyncio
    async def test_assess_trust_whitelisted_source(self):
        """Test whitelisted source gets 100% trust."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, TrustSource, VerificationResult
        )
        
        engine = Layer3QuorumVerification()
        engine.add_to_whitelist("my_trusted_api")
        
        assessment = await engine.assess_trust(
            data="API response",
            origin="my_trusted_api",
            genesis_key_id=None
        )
        
        assert assessment.source == TrustSource.WHITELIST
        assert assessment.verified_score == 1.0
        assert assessment.verification_result == VerificationResult.PASSED

    def test_record_component_outcome_updates_kpi(self):
        """Test recording outcomes updates component KPIs."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        initial_score = engine.component_kpis["coding_agent"].current_score
        
        engine.record_component_outcome(
            component_id="coding_agent",
            success=True,
            meets_grace_standard=True,
            meets_user_standard=True
        )
        
        assert engine.component_kpis["coding_agent"].current_score > initial_score

    def test_record_outcome_creates_new_component(self):
        """Test recording outcome for new component creates it."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        engine.record_component_outcome(
            component_id="new_component",
            success=True
        )
        
        assert "new_component" in engine.component_kpis

    def test_get_all_kpis(self):
        """Test getting all component KPIs."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        kpis = engine.get_all_kpis()
        
        assert isinstance(kpis, dict)
        assert len(kpis) > 0
        assert all("current_score" in v for v in kpis.values())

    def test_get_governance_status(self):
        """Test getting overall governance status."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        status = engine.get_governance_status()
        
        assert "governance_health" in status
        assert "component_kpis" in status
        assert "trust_verification" in status
        assert "quorum_sessions" in status
        assert "constitutional_framework" in status
        assert "whitelist_size" in status


# ==================== LayerEnforcement Integration Tests ====================

@pytest.mark.integration
class TestLayerEnforcementIntegration:
    """Integration tests for LayerEnforcement."""

    def test_enforcement_initialization(self):
        """Test enforcement layer initializes correctly."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        
        assert enforcement.stats["total_enforced"] == 0
        assert enforcement.stats["allowed"] == 0
        assert enforcement.stats["blocked"] == 0

    def test_get_layer_enforcement_singleton(self):
        """Test get_layer_enforcement returns singleton."""
        from governance.layer_enforcement import get_layer_enforcement
        
        # Reset for test
        import governance.layer_enforcement as le
        le._enforcement = None
        
        e1 = get_layer_enforcement()
        e2 = get_layer_enforcement()
        
        assert e1 is e2

    @pytest.mark.asyncio
    async def test_enforce_layer1_human_input_allowed(self):
        """Test human input to Layer 1 is allowed."""
        from governance.layer_enforcement import (
            LayerEnforcement, EnforcementAction
        )
        
        enforcement = LayerEnforcement()
        
        decision = await enforcement.enforce_layer1_ingestion(
            data="User message",
            origin="user_input",
            input_type="chat",
            user_id="user-123"
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.trust_score == 1.0
        assert decision.verification_passed is True

    @pytest.mark.asyncio
    async def test_enforce_layer1_external_api(self):
        """Test external API to Layer 1 requires verification."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        
        decision = await enforcement.enforce_layer1_ingestion(
            data={"api": "response"},
            origin="external_api",
            input_type="api",
            user_id=None
        )
        
        # Should not be 100% trusted
        assert decision.trust_score < 1.0

    @pytest.mark.asyncio
    async def test_enforce_layer1_file_upload(self):
        """Test file upload enforcement."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        
        decision = await enforcement.enforce_layer1_ingestion(
            data={"filename": "test.txt", "size": 1024},
            origin="file_upload",
            input_type="upload",
            user_id="user-123"
        )
        
        # File uploads from users should be processed
        assert decision.action.value in ["allow", "quarantine"]

    @pytest.mark.asyncio
    async def test_enforce_layer2_processing_with_user(self):
        """Test Layer 2 processing with user ID is trusted."""
        from governance.layer_enforcement import (
            LayerEnforcement, EnforcementAction
        )
        
        enforcement = LayerEnforcement()
        
        decision = await enforcement.enforce_layer2_processing(
            intent="Analyze this code",
            observations={"files": ["main.py"]},
            context={"project": "test"},
            user_id="user-123"
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.trust_score >= 0.7

    @pytest.mark.asyncio
    async def test_enforce_layer2_autonomous(self):
        """Test Layer 2 autonomous processing."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        
        decision = await enforcement.enforce_layer2_processing(
            intent="Self-healing action",
            observations={"error": "import failed"},
            context={},
            user_id=None  # Autonomous
        )
        
        # Should still be processed (internal is trusted)
        assert decision.trust_score >= 0.7

    @pytest.mark.asyncio
    async def test_enforcement_stats_tracking(self):
        """Test enforcement statistics are tracked."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        initial_total = enforcement.stats["total_enforced"]
        
        await enforcement.enforce_layer1_ingestion(
            data="test",
            origin="human",
            input_type="chat",
            user_id="user-1"
        )
        
        assert enforcement.stats["total_enforced"] == initial_total + 1
        assert enforcement.stats["layer1_enforced"] > 0

    def test_get_enforcement_stats(self):
        """Test getting enforcement statistics."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        
        stats = enforcement.get_enforcement_stats()
        
        assert "total_enforced" in stats
        assert "allowed" in stats
        assert "blocked" in stats
        assert "quarantined" in stats
        assert "escalated" in stats
        assert "allow_rate" in stats
        assert "layer1_enforced" in stats
        assert "layer2_enforced" in stats


# ==================== Quorum Request Integration Tests ====================

@pytest.mark.integration
class TestQuorumRequestIntegration:
    """Integration tests for quorum decision requests."""

    @pytest.mark.asyncio
    async def test_request_quorum_basic(self):
        """Test basic quorum request."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        session = await engine.request_quorum(
            proposal={
                "type": "code_deploy",
                "risk_level": "medium",
                "trust_score": 0.8
            },
            required_votes=3
        )
        
        assert session.session_id is not None
        assert session.proposal is not None
        # Decision made by fallback voting
        assert session.decision is not None

    @pytest.mark.asyncio
    async def test_request_quorum_low_confidence_escalates(self):
        """Test low confidence quorum escalates."""
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification, QuorumDecision
        )
        
        engine = Layer3QuorumVerification()
        
        session = await engine.request_quorum(
            proposal={
                "type": "critical_action",
                "risk_level": "critical",
                "trust_score": 0.3  # Low trust
            },
            required_votes=3,
            escalation_threshold=0.9  # High threshold
        )
        
        # Low trust should cause escalation or rejection
        assert session.decision in [QuorumDecision.ESCALATE, QuorumDecision.REJECT]


# ==================== API Integration Tests ====================

@pytest.mark.api
class TestGovernanceAPIIntegration:
    """Integration tests for Governance API endpoints."""

    def test_get_governance_status_endpoint(self, client):
        """Test /governance/status endpoint."""
        response = client.get("/governance/status")
        assert response.status_code == 200, f"Governance status failed: {response.text}"
        data = response.json()
        assert "success" in data
        if data.get("success"):
            assert "governance" in data, "Response must include governance data"

    def test_get_all_kpis_endpoint(self, client):
        """Test /governance/kpi/all endpoint."""
        response = client.get("/governance/kpi/all")
        assert response.status_code == 200, f"Get all KPIs failed: {response.text}"
        data = response.json()
        assert "success" in data
        assert data["success"] is True, "KPI endpoint should return success"

    def test_get_constitutional_principles_endpoint(self, client):
        """Test /governance/constitutional/principles endpoint."""
        response = client.get("/governance/constitutional/principles")
        assert response.status_code == 200, f"Get principles failed: {response.text}"
        data = response.json()
        assert "success" in data
        assert "principles" in data, "Response must include principles"

    def test_trust_assessment_endpoint(self, client):
        """Test /governance/trust/assess endpoint."""
        response = client.post("/governance/trust/assess", json={
            "data": "Test data to assess",
            "origin": "human_triggered",
            "correlation_check": False,
            "timesense_validate": False
        })
        assert response.status_code == 200, f"Trust assessment failed: {response.text}"
        data = response.json()
        assert "success" in data
        # Human triggered should be trusted
        if "trust_score" in data:
            assert data["trust_score"] >= 0.7

    def test_record_kpi_endpoint(self, client):
        """Test /governance/kpi/record endpoint."""
        response = client.post("/governance/kpi/record", json={
            "component_id": "test_component",
            "success": True,
            "meets_grace_standard": True,
            "meets_user_standard": True
        })
        assert response.status_code == 200, f"Record KPI failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_whitelist_add_endpoint(self, client):
        """Test /governance/whitelist/add endpoint."""
        response = client.post("/governance/whitelist/add", json={
            "source": "test_trusted_source"
        })
        assert response.status_code == 200, f"Add whitelist failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_constitutional_check_endpoint(self, client):
        """Test /governance/constitutional/check endpoint."""
        response = client.post("/governance/constitutional/check", json={
            "type": "test_action",
            "reasoning": "Testing compliance check"
        })
        assert response.status_code == 200, f"Constitutional check failed: {response.text}"
        data = response.json()
        assert "compliant" in data, "Response must include compliant field"


# ==================== Cross-Layer Integration Tests ====================

@pytest.mark.integration
class TestCrossLayerIntegration:
    """Test Layer 3 integration with Layer 1 and Layer 2."""

    @pytest.mark.asyncio
    async def test_full_trust_flow_human_to_layer1(self):
        """Test complete trust flow from human input through Layer 1."""
        from governance.layer_enforcement import enforce_layer1, EnforcementAction
        
        decision = await enforce_layer1(
            data="User's question about code",
            origin="user_input",
            input_type="chat",
            user_id="user-123",
            metadata={"session": "test"}
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.source_classification == "human_triggered"
        assert decision.trust_score == 1.0
        assert decision.constitutional_compliant is True

    @pytest.mark.asyncio
    async def test_full_trust_flow_external_to_layer1(self):
        """Test complete trust flow from external source through Layer 1."""
        from governance.layer_enforcement import enforce_layer1
        
        decision = await enforce_layer1(
            data={"api_response": "external data"},
            origin="external_api",
            input_type="api",
            user_id=None,
            metadata=None
        )
        
        # External data should have lower trust
        assert decision.trust_score < 1.0
        # Action depends on verification
        assert decision.action.value in ["allow", "quarantine", "block"]

    @pytest.mark.asyncio
    async def test_full_trust_flow_layer2_processing(self):
        """Test complete trust flow through Layer 2."""
        from governance.layer_enforcement import enforce_layer2, EnforcementAction
        
        decision = await enforce_layer2(
            intent="Analyze code quality",
            observations={"files": ["main.py"], "metrics": {"loc": 500}},
            context={"project": "grace"},
            user_id="user-123"
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.trust_score >= 0.7

    @pytest.mark.asyncio
    async def test_kpi_updates_from_enforcement(self):
        """Test KPIs are updated from enforcement decisions."""
        from governance.layer_enforcement import LayerEnforcement
        from governance.layer3_quorum_verification import get_quorum_engine
        
        enforcement = LayerEnforcement()
        await enforcement.initialize()
        
        # Get initial KPI
        engine = get_quorum_engine()
        initial_kb_score = engine.component_kpis.get("knowledge_base")
        
        # Enforce Layer 1 (should update knowledge_base KPI)
        await enforcement.enforce_layer1_ingestion(
            data="test data",
            origin="human_triggered",
            input_type="chat",
            user_id="user-1"
        )
        
        # KPI should be tracked
        assert enforcement.stats["layer1_enforced"] > 0


# ==================== Error Handling Tests ====================

@pytest.mark.integration
class TestLayer3ErrorHandling:
    """Test error handling in Layer 3."""

    @pytest.mark.asyncio
    async def test_assess_trust_handles_missing_dependencies(self):
        """Test trust assessment handles missing dependencies gracefully."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        # Should not raise even if dependencies fail
        assessment = await engine.assess_trust(
            data="test",
            origin="web",
            genesis_key_id=None,
            correlation_check=True,  # May fail internally
            timesense_validate=True  # May fail internally
        )
        
        assert assessment is not None
        assert assessment.source is not None

    @pytest.mark.asyncio
    async def test_enforcement_handles_quorum_engine_failure(self):
        """Test enforcement handles quorum engine failure."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        enforcement._quorum_engine = None  # Simulate failure
        
        # Should use fallback scoring
        decision = await enforcement.enforce_layer1_ingestion(
            data="test",
            origin="human_triggered",
            input_type="chat",
            user_id="user-1"
        )
        
        assert decision is not None
        assert decision.action is not None

    def test_kpi_handles_invalid_component(self):
        """Test KPI operations handle invalid component gracefully."""
        from governance.layer3_quorum_verification import Layer3QuorumVerification
        
        engine = Layer3QuorumVerification()
        
        # Getting non-existent component returns None
        kpi = engine.get_component_kpi("nonexistent_component")
        assert kpi is None
        
        # Recording creates it
        engine.record_component_outcome("new_component", success=True)
        kpi = engine.get_component_kpi("new_component")
        assert kpi is not None
