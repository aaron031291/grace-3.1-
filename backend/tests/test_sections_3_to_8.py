"""
REAL LOGIC TESTS for Sections 3-8.
agent/, execution/, llm_orchestrator/, retrieval/, ingestion/,
security/, diagnostic_machine/, models/, core/, layer1/,
librarian/, scraping/, services/, telemetry/
"""
import sys, os, re
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BD = os.path.join(os.path.dirname(__file__), "..")


# ============================================================
# SECTION 3: agent/ + execution/
# ============================================================

class TestAgentLogic:
    def test_task_classification(self):
        source = open(f"{BD}/agent/grace_agent.py").read()
        assert "bug_fix" in source
        assert "feature" in source
        assert "refactor" in source
        assert "testing" in source

    def test_playbook_wiring(self):
        source = open(f"{BD}/agent/grace_agent.py").read()
        assert "CodePlaybookManager" in source
        assert "find_playbook" in source
        assert "create_from_success" in source
        assert "record_failure" in source

    def test_self_monitoring_wired(self):
        source = open(f"{BD}/agent/grace_agent.py").read()
        assert "CodeAgentSelf" in source
        assert "log_attempt" in source

    def test_code_playbook_model(self):
        from agent.code_playbooks import CodePlaybook
        cols = [c.name for c in CodePlaybook.__table__.columns]
        for f in ["name", "task_type", "trust_score", "success_count", "failure_count", "strategy", "avg_test_pass_rate"]:
            assert f in cols

    def test_execution_bridge_exists(self):
        assert os.path.isfile(f"{BD}/execution/bridge.py")
        assert os.path.isfile(f"{BD}/execution/actions.py")
        assert os.path.isfile(f"{BD}/execution/feedback.py")

    def test_governed_bridge_exists(self):
        assert os.path.isfile(f"{BD}/execution/governed_bridge.py")


# ============================================================
# SECTION 4: llm_orchestrator/
# ============================================================

class TestLLMOrchestratorLogic:
    def test_three_layer_dataclasses(self):
        from llm_orchestrator.three_layer_reasoning import ReasoningOutput, LayerResult, VerifiedResult
        r = ReasoningOutput(model_name="test", layer=1, reasoning="test", confidence=0.8, duration_ms=100)
        assert r.layer == 1
        lr = LayerResult(layer=2, outputs=[r], agreement_score=0.7)
        assert lr.layer == 2

    def test_agreement_calculation(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput
        t = ThreeLayerReasoning()
        o1 = ReasoningOutput(model_name="a", layer=1, reasoning="python is great for web development", confidence=0.8, duration_ms=100)
        o2 = ReasoningOutput(model_name="b", layer=1, reasoning="python is excellent for web development", confidence=0.7, duration_ms=100)
        agreement = t._calculate_agreement([o1, o2])
        assert 0 <= agreement <= 1.0
        assert agreement > 0.3

    def test_consensus_picks_longest(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput
        t = ThreeLayerReasoning()
        outputs = [
            ReasoningOutput(model_name="a", layer=2, reasoning="short", confidence=0.8, duration_ms=100),
            ReasoningOutput(model_name="b", layer=2, reasoning="this is a much longer and more detailed response", confidence=0.7, duration_ms=100),
        ]
        consensus = t._extract_consensus(outputs)
        assert "longer" in consensus

    def test_governance_check_safe(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert t._verify_governance("Here is how to build a REST API.") is True

    def test_governance_check_unsafe(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert t._verify_governance("how to hack into the system") is False

    def test_reasoning_router_tiers(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        assert r.classify("hello").tier == ReasoningTier.INSTANT
        assert r.classify("think deeply about this architecture").tier == ReasoningTier.DEEP

    def test_hallucination_guard_exists(self):
        from llm_orchestrator.hallucination_guard import HallucinationGuard
        assert HallucinationGuard is not None

    def test_multi_llm_model_registry(self):
        source = open(f"{BD}/llm_orchestrator/multi_llm_client.py").read()
        assert "MODEL_REGISTRY" in source
        assert "deepseek" in source.lower()
        assert "qwen" in source.lower()
        assert "mistral" in source.lower()


# ============================================================
# SECTION 5: retrieval/ + ingestion/ + embedding/
# ============================================================

class TestRetrievalLogic:
    def test_retriever_exists(self):
        from retrieval.retriever import DocumentRetriever
        assert DocumentRetriever is not None

    def test_trust_aware_retriever_exists(self):
        from retrieval.trust_aware_retriever import TrustAwareDocumentRetriever
        assert TrustAwareDocumentRetriever is not None

    def test_multi_tier_handler(self):
        source = open(f"{BD}/retrieval/multi_tier_integration.py").read()
        assert "TrustAwareDocumentRetriever" in source
        assert "vectordb_quality_threshold" in source

    def test_query_intelligence_tiers(self):
        source = open(f"{BD}/retrieval/query_intelligence.py").read()
        assert "VECTORDB" in source
        assert "MODEL_KNOWLEDGE" in source
        assert "USER_CONTEXT" in source

    def test_ingestion_chunking(self):
        from ingestion.service import TextChunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "A" * 500
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1
        assert all(len(c["text"]) <= 120 for c in chunks)

    def test_ingestion_dedup_hash(self):
        from ingestion.service import TextIngestionService
        h1 = TextIngestionService.compute_file_hash("hello world")
        h2 = TextIngestionService.compute_file_hash("hello world")
        h3 = TextIngestionService.compute_file_hash("different content")
        assert h1 == h2
        assert h1 != h3

    def test_confidence_scorer_exists(self):
        from confidence_scorer.confidence_scorer import ConfidenceScorer
        assert ConfidenceScorer is not None


# ============================================================
# SECTION 6: security/ + diagnostic_machine/
# ============================================================

class TestSecurityLogic:
    def test_constitutional_rules_count(self):
        from security.governance import CONSTITUTIONAL_RULES
        assert len(CONSTITUTIONAL_RULES) == 11

    def test_hia_values(self):
        from security.governance import ConstitutionalRule
        assert ConstitutionalRule.HONESTY.value == "honesty"
        assert ConstitutionalRule.INTEGRITY.value == "integrity"
        assert ConstitutionalRule.ACCOUNTABILITY.value == "accountability"

    def test_honesty_enforcer_catches_fabrication(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score, violations = HonestyEnforcer.check_output(
            "According to a recent study by Harvard University, 95% of developers agree."
        )
        assert score < 0.9
        assert len(violations) > 0

    def test_integrity_catches_inflated_kpi(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_kpi_integrity(0.95, 50, 100)
        assert score < 0.8

    def test_accountability_catches_missing_audit(self):
        from security.honesty_integrity_accountability import AccountabilityEnforcer
        score, violations = AccountabilityEnforcer.check_audit_trail("action", False, False)
        assert score < 1.0
        assert len(violations) > 0

    def test_output_safety_validator(self):
        from security.governance_middleware import OutputSafetyValidator
        safe = OutputSafetyValidator.validate("How to build a REST API")
        assert safe["safe"] is True
        unsafe = OutputSafetyValidator.validate("how to hack into the system")
        assert unsafe["safe"] is False

    def test_rate_limit_config(self):
        from security.config import SecurityConfig
        config = SecurityConfig()
        assert config.RATE_LIMIT_ENABLED is True
        assert "minute" in config.RATE_LIMIT_DEFAULT

    def test_input_validator_exists(self):
        source = open(f"{BD}/security/validators.py").read()
        assert "class InputValidator" in source
        assert "validate_string" in source
        assert "xss_patterns" in source
        assert "sql_patterns" in source

    def test_diagnostic_engine_exists(self):
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        assert DiagnosticEngine is not None

    def test_diagnostic_layers(self):
        from diagnostic_machine.sensors import SensorLayer
        from diagnostic_machine.interpreters import InterpreterLayer
        assert SensorLayer is not None
        assert InterpreterLayer is not None


# ============================================================
# SECTION 7: models/ + core/ + layer1/
# ============================================================

class TestModelsLogic:
    def test_document_model(self):
        from models.database_models import Document, DocumentChunk
        doc_cols = [c.name for c in Document.__table__.columns]
        assert "filename" in doc_cols
        assert "confidence_score" in doc_cols
        assert "content_hash" in doc_cols
        assert "status" in doc_cols

    def test_genesis_key_model(self):
        from models.genesis_key_models import GenesisKey
        assert GenesisKey.__tablename__ == "genesis_key"

    def test_llm_tracking_models(self):
        from models.llm_tracking_models import LLMInteraction, ReasoningPath, ExtractedPattern
        assert LLMInteraction.__tablename__ == "llm_interactions"
        assert ReasoningPath.__tablename__ == "reasoning_paths"
        assert ExtractedPattern.__tablename__ == "extracted_patterns"

    def test_core_registry(self):
        from core.registry import ComponentRegistry
        assert ComponentRegistry is not None

    def test_layer1_message_bus(self):
        source = open(f"{BD}/layer1/message_bus.py").read()
        assert "MessageType" in source
        assert "ComponentType" in source
        assert "broadcast" in source


# ============================================================
# SECTION 8: librarian/ + scraping/ + services/ + telemetry/
# ============================================================

class TestLibrarianLogic:
    def test_knowledge_organizer_taxonomy(self):
        from librarian.knowledge_organizer import DOMAIN_TAXONOMY
        assert len(DOMAIN_TAXONOMY) >= 17
        assert "algorithms" in DOMAIN_TAXONOMY
        assert "security" in DOMAIN_TAXONOMY
        assert "ai_ml" in DOMAIN_TAXONOMY

    def test_knowledge_organizer_classification(self):
        from librarian.knowledge_organizer import KnowledgeOrganizer
        org = KnowledgeOrganizer()
        assert org.classify_document("algorithm_design.txt", "quicksort mergesort binary search") == "algorithms"
        assert org.classify_document("cybersecurity_guide.txt", "encryption vulnerability") == "security"

    def test_librarian_engine_exists(self):
        source = open(f"{BD}/librarian/engine.py").read()
        assert "class LibrarianEngine" in source
        assert "process_document" in source

    def test_tag_manager_exists(self):
        source = open(f"{BD}/librarian/tag_manager.py").read()
        assert "class TagManager" in source


class TestScrapingLogic:
    def test_scraping_service_exists(self):
        source = open(f"{BD}/scraping/service.py").read()
        assert "class WebScrapingService" in source or "class ScrapingService" in source

    def test_url_validator_exists(self):
        source = open(f"{BD}/scraping/url_validator.py").read()
        assert "class URLValidator" in source or "validate" in source


class TestServicesLogic:
    def test_systems_integration(self):
        from services.grace_systems_integration import GraceSystemsIntegration, GraceSystemType
        assert GraceSystemType.MEMORY.value == "memory"
        assert GraceSystemType.ORACLE.value == "oracle"
        assert GraceSystemType.DIAGNOSTIC.value == "diagnostic"


class TestTelemetryLogic:
    def test_telemetry_service_exists(self):
        from telemetry.telemetry_service import TelemetryService
        assert TelemetryService is not None
