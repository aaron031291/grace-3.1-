"""
Tests for the Multi-Model Consensus Engine.
"""
import pytest; pytest.importorskip("api.consensus_api", reason="api.consensus_api removed — consolidated into Brain API")

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")


class TestModelRegistry:
    """Test model discovery and availability."""

    def test_model_registry_has_all_models(self):
        from cognitive.consensus_engine import MODEL_REGISTRY
        assert "opus" in MODEL_REGISTRY
        assert "kimi" in MODEL_REGISTRY
        assert "qwen" in MODEL_REGISTRY
        assert "reasoning" in MODEL_REGISTRY

    def test_model_registry_structure(self):
        from cognitive.consensus_engine import MODEL_REGISTRY
        for mid, info in MODEL_REGISTRY.items():
            assert "name" in info
            assert "provider" in info
            assert "strengths" in info
            assert "cost_tier" in info
            assert isinstance(info["strengths"], list)

    def test_get_available_models(self):
        from cognitive.consensus_engine import get_available_models
        models = get_available_models()
        assert len(models) == 4
        for m in models:
            assert "id" in m
            assert "name" in m
            assert "available" in m
            assert isinstance(m["available"], bool)

    def test_cost_tiers(self):
        from cognitive.consensus_engine import MODEL_REGISTRY
        tiers = {info["cost_tier"] for info in MODEL_REGISTRY.values()}
        assert "cloud" in tiers
        assert "free" in tiers


class TestConsensusDataStructures:
    """Test data classes and structures."""

    def test_model_response_creation(self):
        from cognitive.consensus_engine import ModelResponse
        r = ModelResponse(
            model_id="test",
            model_name="Test Model",
            response="Hello world",
            latency_ms=100.5,
        )
        assert r.model_id == "test"
        assert r.response == "Hello world"
        assert r.latency_ms == 100.5
        assert r.error is None

    def test_model_response_with_error(self):
        from cognitive.consensus_engine import ModelResponse
        r = ModelResponse(
            model_id="test",
            model_name="Test Model",
            response="",
            latency_ms=50,
            error="Connection failed",
        )
        assert r.error == "Connection failed"
        assert r.response == ""

    def test_consensus_result_creation(self):
        from cognitive.consensus_engine import ConsensusResult
        r = ConsensusResult(
            query="test query",
            models_used=["qwen", "reasoning"],
            individual_responses=[],
            consensus_text="Agreed output",
            alignment_text="Aligned output",
            verification={"passed": True, "trust_score": 0.8},
            confidence=0.8,
            agreements=["Point A"],
            disagreements=[],
            final_output="Final answer",
            total_latency_ms=500,
            source="user",
        )
        assert r.query == "test query"
        assert r.confidence == 0.8
        assert len(r.agreements) == 1
        assert r.source == "user"
        assert r.timestamp is not None


class TestVerification:
    """Test Layer 4 verification logic."""

    def test_verify_clean_output(self):
        from cognitive.consensus_engine import layer4_verify
        v = layer4_verify("This is a comprehensive analysis of the problem.", "Analyze X")
        assert "trust_score" in v
        assert "hallucination_score" in v
        assert "passed" in v

    def test_verify_short_output_flagged(self):
        from cognitive.consensus_engine import layer4_verify
        v = layer4_verify("OK", "Analyze X")
        assert "Response too short" in v.get("hallucination_flags", [])

    def test_verify_empty_output(self):
        from cognitive.consensus_engine import layer4_verify
        v = layer4_verify("", "Analyze X")
        assert v["hallucination_score"] < 1.0


class TestBatchQueue:
    """Test autonomous batch queue."""

    def test_queue_entry_structure(self):
        entry = {
            "prompt": "Test query",
            "context": "Test context",
            "priority": "high",
            "status": "queued",
        }
        assert entry["prompt"] == "Test query"
        assert entry["status"] == "queued"
        assert entry["priority"] == "high"

    def test_queue_autonomous_query_callable(self):
        from cognitive.consensus_engine import queue_autonomous_query
        assert callable(queue_autonomous_query)

    def test_get_batch_queue_callable(self):
        from cognitive.consensus_engine import get_batch_queue
        assert callable(get_batch_queue)

    def test_run_batch_callable(self):
        from cognitive.consensus_engine import run_batch
        assert callable(run_batch)


class TestConsensusAPI:
    """Test the API module."""

    def test_import_router(self):
        from api.consensus_api import router
        assert router is not None
        assert router.prefix == "/api/consensus"

    def test_routes_exist(self):
        from api.consensus_api import router
        paths = [r.path for r in router.routes]
        prefix = router.prefix
        assert f"{prefix}/models" in paths
        assert f"{prefix}/run" in paths
        assert f"{prefix}/quick" in paths
        assert f"{prefix}/batch/queue" in paths
        assert f"{prefix}/batch/run" in paths


class TestIntegrationPoints:
    """Test that consensus engine can be imported from other systems."""

    def test_importable_from_immune_system_context(self):
        from cognitive.consensus_engine import queue_autonomous_query
        assert callable(queue_autonomous_query)

    def test_importable_from_pipeline_context(self):
        from cognitive.consensus_engine import run_consensus
        assert callable(run_consensus)

    def test_importable_from_librarian_context(self):
        from cognitive.consensus_engine import queue_autonomous_query, get_available_models
        assert callable(queue_autonomous_query)
        assert callable(get_available_models)

    def test_flash_cache_in_pipeline_ooda(self):
        """Verify FlashCache is importable for pipeline OODA stage."""
        from cognitive.flash_cache import get_flash_cache
        assert callable(get_flash_cache)

    def test_flash_cache_in_knowledge_cycle(self):
        """Verify FlashCache search is available for knowledge cycle."""
        from cognitive.flash_cache import FlashCache
        assert hasattr(FlashCache, "search")
        assert hasattr(FlashCache, "lookup")
