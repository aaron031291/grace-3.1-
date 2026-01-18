"""
Layer 2 Intelligence - Comprehensive Test Suite

Tests all components and features of Layer 2 Intelligence:
1. Component Tests (Memory Mesh, RAG, Oracle, etc.)
2. Performance Tests (Caching, Parallel OBSERVE, Confidence Fusion)
3. Advanced Tests (Circuit Breaker, Auto-Tuning, Streaming, Batch)
4. Integration Tests (Full OODA cycles)
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any, List

# Import Layer 2 Intelligence
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from genesis_ide.layer_intelligence import Layer2Intelligence, IntentCategory


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def layer2():
    """Create Layer 2 Intelligence instance for testing."""
    instance = Layer2Intelligence(session=None, repo_path=Path("."))
    return instance


@pytest.fixture
def initialized_layer2():
    """Create and initialize Layer 2 Intelligence."""
    instance = Layer2Intelligence(session=None, repo_path=Path("."))
    # Mock the async initialize
    return instance


@pytest.fixture
def mock_memory_mesh():
    """Mock Memory Mesh component."""
    mesh = Mock()
    mesh.procedural_repo = Mock()
    mesh.procedural_repo.find_procedure = Mock(return_value=Mock(
        name="test_procedure",
        goal="test goal",
        trust_score=0.85,
        success_rate=0.9
    ))
    mesh.episodic_buffer = Mock()
    mesh.episodic_buffer.recall_similar = Mock(return_value=[
        Mock(problem="test problem", outcome="success", trust_score=0.8)
    ])
    return mesh


@pytest.fixture
def mock_oracle_hub():
    """Mock Oracle Hub component."""
    hub = Mock()
    hub.search_intelligence = Mock(return_value=[
        Mock(
            title="Test Pattern",
            source=Mock(value="internal"),
            confidence=0.85,
            tags=["python", "test"]
        )
    ])
    hub.get_templates_for_intent = Mock(return_value=[
        {"name": "test_template", "pattern": "def test():", "confidence": 0.9}
    ])
    hub.get_recent_learnings = Mock(return_value=[
        {"source": "internal", "insight": "Test insight", "timestamp": "2026-01-18"}
    ])
    hub._queue = []
    hub._processing = False
    hub.oracle_export_path = Path("knowledge_base/oracle")
    return hub


@pytest.fixture
def mock_rag_retriever():
    """Mock RAG Retriever component."""
    retriever = Mock()
    retriever.retrieve = Mock(return_value=[
        {"content": "Test document content", "score": 0.75, "metadata": {}}
    ])
    retriever.smart_retrieve = Mock(return_value={
        "results": [{"content": "Test content", "score": 0.8}],
        "cached": False
    })
    return retriever


# ============================================================================
# COMPONENT TESTS
# ============================================================================

class TestLayer2Initialization:
    """Test Layer 2 initialization."""
    
    def test_init_creates_instance(self, layer2):
        """Test that Layer2Intelligence initializes correctly."""
        assert layer2 is not None
        assert layer2.session is None
        assert layer2.repo_path == Path(".")
    
    def test_init_sets_defaults(self, layer2):
        """Test default values are set."""
        assert layer2._context_memory == []
        assert layer2._max_context == 20
        assert layer2.metrics["cognitive_cycles"] == 0
    
    def test_init_performance_enhancements(self, layer2):
        """Test performance enhancement attributes."""
        assert layer2._query_cache == {}
        assert layer2._cache_ttl_seconds == 300
        assert layer2._cache_max_size == 100
        assert layer2._confidence_weights is not None
        assert "memory_mesh" in layer2._confidence_weights
    
    def test_init_advanced_enhancements(self, layer2):
        """Test advanced enhancement attributes."""
        assert layer2._circuit_breaker is not None
        assert layer2._auto_tune_enabled is True
        assert layer2._fallback_chains is not None
        assert layer2._event_subscribers == []


class TestMemoryMeshIntegration:
    """Test Memory Mesh component integration."""
    
    def test_memory_mesh_attribute_exists(self, layer2):
        """Test Memory Mesh attribute exists."""
        assert hasattr(layer2, "_memory_mesh")
    
    @pytest.mark.asyncio
    async def test_memory_mesh_query(self, layer2, mock_memory_mesh):
        """Test querying Memory Mesh."""
        layer2._memory_mesh = mock_memory_mesh
        
        # Query through observe
        observations = await layer2._observe_parallel(
            intent="find procedure",
            entities={"goal": "test"},
            context={}
        )
        
        assert "memory_patterns" in observations


class TestOracleHubIntegration:
    """Test Oracle Hub component integration."""
    
    def test_oracle_hub_attribute_exists(self, layer2):
        """Test Oracle Hub attribute exists."""
        assert hasattr(layer2, "_oracle_hub")
    
    @pytest.mark.asyncio
    async def test_query_oracle(self, layer2, mock_oracle_hub):
        """Test querying Oracle Hub."""
        layer2._oracle_hub = mock_oracle_hub
        
        result = await layer2._query_oracle("test intent", {"goal": "test"})
        
        assert "patterns" in result
        assert "templates" in result
        assert "learnings" in result
    
    def test_get_oracle_status_not_connected(self, layer2):
        """Test Oracle status when not connected."""
        layer2._oracle_hub = None
        status = layer2.get_oracle_status()
        
        assert status["connected"] is False
    
    def test_get_oracle_status_connected(self, layer2, mock_oracle_hub):
        """Test Oracle status when connected."""
        layer2._oracle_hub = mock_oracle_hub
        status = layer2.get_oracle_status()
        
        assert status["connected"] is True


class TestRAGIntegration:
    """Test RAG Retriever component integration."""
    
    def test_rag_attribute_exists(self, layer2):
        """Test RAG attribute exists."""
        assert hasattr(layer2, "_rag_retriever")
        assert hasattr(layer2, "_enterprise_rag")


class TestConfidenceScorer:
    """Test Confidence Scorer component."""
    
    def test_confidence_scorer_attribute(self, layer2):
        """Test Confidence Scorer attribute exists."""
        assert hasattr(layer2, "_confidence_scorer")


class TestDiagnosticEngine:
    """Test Diagnostic Engine component."""
    
    def test_diagnostic_engine_attribute(self, layer2):
        """Test Diagnostic Engine attribute exists."""
        assert hasattr(layer2, "_diagnostic_engine")


class TestClarityFramework:
    """Test Clarity Framework component."""
    
    def test_clarity_framework_attribute(self, layer2):
        """Test Clarity Framework attribute exists."""
        assert hasattr(layer2, "_clarity_framework")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestResultCaching:
    """Test result caching functionality."""
    
    def test_cache_key_generation(self, layer2):
        """Test cache key generation."""
        key1 = layer2._get_cache_key("test intent", {"a": 1})
        key2 = layer2._get_cache_key("test intent", {"a": 1})
        key3 = layer2._get_cache_key("different intent", {"a": 1})
        
        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key
    
    def test_set_and_get_cache(self, layer2):
        """Test setting and getting cached results."""
        cache_key = "test_key"
        result = {"data": "test"}
        
        layer2._set_cached_result(cache_key, result)
        cached = layer2._get_cached_result(cache_key)
        
        assert cached == result
        assert layer2.metrics["cache_hits"] == 1
    
    def test_cache_miss(self, layer2):
        """Test cache miss."""
        cached = layer2._get_cached_result("nonexistent_key")
        
        assert cached is None
        assert layer2.metrics["cache_misses"] == 1
    
    def test_cache_expiration(self, layer2):
        """Test cache expiration."""
        cache_key = "expiring_key"
        result = {"data": "test"}
        
        layer2._set_cached_result(cache_key, result)
        
        # Manually expire by modifying cache time
        layer2._query_cache[cache_key]["_cache_time"] = (
            datetime.utcnow().timestamp() - 400  # Older than TTL
        )
        
        cached = layer2._get_cached_result(cache_key)
        assert cached is None
    
    def test_cache_max_size(self, layer2):
        """Test cache max size enforcement."""
        layer2._cache_max_size = 3
        
        for i in range(5):
            layer2._set_cached_result(f"key_{i}", {"data": i})
        
        assert len(layer2._query_cache) <= 3
    
    def test_clear_cache(self, layer2):
        """Test clearing cache."""
        layer2._set_cached_result("key1", {"data": 1})
        layer2._set_cached_result("key2", {"data": 2})
        
        layer2.clear_cache()
        
        assert len(layer2._query_cache) == 0


class TestParallelObserve:
    """Test parallel OBSERVE functionality."""
    
    @pytest.mark.asyncio
    async def test_parallel_observe_returns_observations(self, layer2):
        """Test parallel observe returns observations dict."""
        observations = await layer2._observe_parallel(
            intent="test",
            entities={},
            context={}
        )
        
        assert "intent" in observations
        assert "entities" in observations
        assert "_query_times" in observations
    
    @pytest.mark.asyncio
    async def test_parallel_observe_tracks_time(self, layer2):
        """Test parallel observe tracks query times."""
        observations = await layer2._observe_parallel(
            intent="test",
            entities={},
            context={}
        )
        
        assert layer2.metrics["parallel_queries"] >= 1
    
    @pytest.mark.asyncio
    async def test_parallel_observe_calculates_fused_confidence(self, layer2):
        """Test fused confidence calculation."""
        observations = await layer2._observe_parallel(
            intent="test",
            entities={},
            context={}
        )
        
        assert "fused_confidence" in observations


class TestConfidenceFusion:
    """Test confidence fusion functionality."""
    
    def test_fuse_empty_observations(self, layer2):
        """Test fusion with empty observations."""
        fused = layer2._fuse_confidence_scores({})
        assert fused == 0.5  # Default
    
    def test_fuse_with_memory_patterns(self, layer2):
        """Test fusion with memory patterns."""
        observations = {
            "memory_patterns": [
                {"trust_score": 0.8},
                {"trust_score": 0.9}
            ]
        }
        
        fused = layer2._fuse_confidence_scores(observations)
        assert 0 < fused <= 1
    
    def test_fuse_multiple_sources(self, layer2):
        """Test fusion with multiple sources."""
        observations = {
            "memory_patterns": [{"trust_score": 0.8}],
            "rag_context": [{"score": 0.7}],
            "oracle_intelligence": {"confidence": 0.85}
        }
        
        fused = layer2._fuse_confidence_scores(observations)
        assert 0 < fused <= 1


class TestPriorityRouting:
    """Test priority routing functionality."""
    
    def test_critical_priority(self, layer2):
        """Test critical priority detection."""
        assert layer2._determine_priority("fix security error") == "critical"
        assert layer2._determine_priority("crash in production") == "critical"
    
    def test_high_priority(self, layer2):
        """Test high priority detection."""
        assert layer2._determine_priority("fix this bug") == "high"
        assert layer2._determine_priority("issue with login") == "high"
    
    def test_normal_priority(self, layer2):
        """Test normal priority detection."""
        assert layer2._determine_priority("add new feature") == "normal"
        assert layer2._determine_priority("refactor code") == "normal"


# ============================================================================
# ADVANCED FEATURE TESTS
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initial_state(self, layer2):
        """Test initial circuit breaker state."""
        for source, cb in layer2._circuit_breaker.items():
            assert cb["state"] == "closed"
            assert cb["failures"] == 0
    
    def test_check_circuit_closed(self, layer2):
        """Test checking closed circuit."""
        should_skip = layer2._check_circuit_breaker("memory_mesh")
        assert should_skip is False
    
    def test_record_circuit_failure(self, layer2):
        """Test recording circuit failure."""
        layer2._record_circuit_failure("memory_mesh")
        
        cb = layer2._circuit_breaker["memory_mesh"]
        assert cb["failures"] == 1
        assert cb["last_failure"] is not None
    
    def test_circuit_opens_after_threshold(self, layer2):
        """Test circuit opens after failure threshold."""
        for _ in range(3):
            layer2._record_circuit_failure("memory_mesh")
        
        cb = layer2._circuit_breaker["memory_mesh"]
        assert cb["state"] == "open"
        assert layer2.metrics["circuit_breaker_trips"] >= 1
    
    def test_check_circuit_open(self, layer2):
        """Test checking open circuit."""
        layer2._circuit_breaker["memory_mesh"]["state"] = "open"
        layer2._circuit_breaker["memory_mesh"]["last_failure"] = datetime.utcnow()
        
        should_skip = layer2._check_circuit_breaker("memory_mesh")
        assert should_skip is True
    
    def test_circuit_success_resets(self, layer2):
        """Test success resets circuit."""
        layer2._circuit_breaker["memory_mesh"]["state"] = "half-open"
        
        layer2._record_circuit_success("memory_mesh")
        
        cb = layer2._circuit_breaker["memory_mesh"]
        assert cb["state"] == "closed"
        assert cb["failures"] == 0
    
    def test_reset_circuit_breaker(self, layer2):
        """Test manual reset."""
        layer2._circuit_breaker["memory_mesh"]["state"] = "open"
        layer2._circuit_breaker["memory_mesh"]["failures"] = 5
        
        layer2.reset_circuit_breaker("memory_mesh")
        
        cb = layer2._circuit_breaker["memory_mesh"]
        assert cb["state"] == "closed"
        assert cb["failures"] == 0
    
    def test_get_circuit_breaker_status(self, layer2):
        """Test getting circuit breaker status."""
        status = layer2.get_circuit_breaker_status()
        
        assert "memory_mesh" in status
        assert "state" in status["memory_mesh"]


class TestAutoTuning:
    """Test auto-tuning weights functionality."""
    
    def test_record_outcome(self, layer2):
        """Test recording outcome."""
        layer2._record_outcome(
            intent="test",
            sources_used={"memory_mesh": 1.0, "rag": 0.8},
            success=True
        )
        
        assert len(layer2._outcome_history) == 1
    
    def test_outcome_history_limit(self, layer2):
        """Test outcome history limit."""
        layer2._max_outcome_history = 5
        
        for i in range(10):
            layer2._record_outcome(f"intent_{i}", {}, True)
        
        assert len(layer2._outcome_history) <= 5
    
    def test_enable_disable_auto_tuning(self, layer2):
        """Test enabling/disabling auto-tuning."""
        layer2.enable_auto_tuning(False)
        assert layer2._auto_tune_enabled is False
        
        layer2.enable_auto_tuning(True)
        assert layer2._auto_tune_enabled is True
    
    def test_update_confidence_weight(self, layer2):
        """Test updating confidence weight."""
        original = layer2._confidence_weights["memory_mesh"]
        
        layer2.update_confidence_weight("memory_mesh", 0.25)
        
        assert layer2._confidence_weights["memory_mesh"] == 0.25
    
    def test_weight_bounds(self, layer2):
        """Test weight bounds enforcement."""
        layer2.update_confidence_weight("memory_mesh", 1.5)
        assert layer2._confidence_weights["memory_mesh"] <= 1.0
        
        layer2.update_confidence_weight("memory_mesh", -0.5)
        assert layer2._confidence_weights["memory_mesh"] >= 0.0


class TestQueryPrediction:
    """Test query prediction functionality."""
    
    def test_record_query_pattern(self, layer2):
        """Test recording query pattern."""
        layer2._record_query_pattern("key1", "key2")
        
        assert "key1" in layer2._query_patterns
        assert "key2" in layer2._query_patterns["key1"]
    
    def test_predict_next_query(self, layer2):
        """Test predicting next query."""
        # Record same pattern multiple times
        layer2._record_query_pattern("key1", "key2")
        layer2._record_query_pattern("key1", "key2")
        layer2._record_query_pattern("key1", "key3")
        
        predicted = layer2._predict_next_query("key1")
        assert predicted == "key2"  # Most common
    
    def test_predict_no_pattern(self, layer2):
        """Test prediction with no pattern."""
        predicted = layer2._predict_next_query("unknown_key")
        assert predicted is None


class TestEventStreaming:
    """Test event streaming functionality."""
    
    def test_subscribe_to_events(self, layer2):
        """Test subscribing to events."""
        callback = Mock()
        layer2.subscribe_to_events(callback)
        
        assert callback in layer2._event_subscribers
    
    def test_unsubscribe_from_events(self, layer2):
        """Test unsubscribing from events."""
        callback = Mock()
        layer2.subscribe_to_events(callback)
        layer2.unsubscribe_from_events(callback)
        
        assert callback not in layer2._event_subscribers
    
    @pytest.mark.asyncio
    async def test_emit_event(self, layer2):
        """Test emitting event."""
        received_events = []
        
        def callback(event):
            received_events.append(event)
        
        layer2.subscribe_to_events(callback)
        await layer2._emit_event("test_event", {"data": "test"})
        
        assert len(received_events) == 1
        assert received_events[0]["type"] == "test_event"
        assert layer2.metrics["streaming_events"] >= 1


class TestCrossCycleLearning:
    """Test cross-cycle learning functionality."""
    
    def test_record_cycle_pattern(self, layer2):
        """Test recording cycle pattern."""
        layer2._record_cycle_pattern(
            intent="fix bug in code",
            observations={"memory_patterns": [{"data": "test"}]},
            decision={"action": "proceed", "confidence": 0.8}
        )
        
        assert len(layer2._cycle_patterns) == 1
    
    def test_find_similar_cycles(self, layer2):
        """Test finding similar cycles."""
        layer2._record_cycle_pattern(
            intent="fix bug in authentication",
            observations={},
            decision={"action": "proceed"}
        )
        
        similar = layer2._find_similar_cycles("fix bug in login")
        # Should find some similarity due to "fix" and "bug"
    
    def test_get_cycle_learning_insights(self, layer2):
        """Test getting learning insights."""
        layer2._record_cycle_pattern(
            intent="test",
            observations={"memory_patterns": []},
            decision={"action": "proceed"}
        )
        
        insights = layer2.get_cycle_learning_insights()
        
        assert "patterns" in insights
        assert "action_distribution" in insights


class TestFallbackChains:
    """Test fallback chains functionality."""
    
    def test_fallback_chains_defined(self, layer2):
        """Test fallback chains are defined."""
        assert "memory_mesh" in layer2._fallback_chains
        assert "rag" in layer2._fallback_chains
        assert "oracle" in layer2._fallback_chains
    
    @pytest.mark.asyncio
    async def test_try_fallbacks(self, layer2):
        """Test trying fallbacks."""
        result = await layer2._try_fallbacks("memory_mesh", "test", {})
        # Should attempt fallbacks (may return None if all fail)


# ============================================================================
# PROCESSING MODE TESTS
# ============================================================================

class TestProcessFast:
    """Test fast processing mode."""
    
    @pytest.mark.asyncio
    async def test_process_fast_returns_result(self, layer2):
        """Test fast processing returns result."""
        # Mock _orient and _decide to avoid full system dependencies
        layer2._orient = AsyncMock(return_value={
            "understanding": "test",
            "concerns": [],
            "opportunities": [],
            "confidence": 0.8
        })
        layer2._decide = AsyncMock(return_value={
            "action": "proceed",
            "modifications": [],
            "warnings": [],
            "reason": "test"
        })
        
        result = await layer2.process_fast(
            intent="test intent",
            entities={},
            context={}
        )
        
        assert "observations" in result
        assert "decision" in result
        assert "priority" in result
    
    @pytest.mark.asyncio
    async def test_process_fast_uses_cache(self, layer2):
        """Test fast processing uses cache."""
        # Mock _orient and _decide
        layer2._orient = AsyncMock(return_value={"confidence": 0.8})
        layer2._decide = AsyncMock(return_value={"action": "proceed"})
        
        # First call
        result1 = await layer2.process_fast("test", {}, {})
        cache_key = result1.get("cache_key")
        
        # Second call should hit cache
        result2 = await layer2.process_fast("test", {}, {})
        
        assert layer2.metrics["cache_hits"] >= 1


class TestProcessStreaming:
    """Test streaming processing mode."""
    
    @pytest.mark.asyncio
    async def test_process_streaming_yields_phases(self, layer2):
        """Test streaming yields phase events."""
        # Mock _orient and _decide
        layer2._orient = AsyncMock(return_value={"confidence": 0.8})
        layer2._decide = AsyncMock(return_value={"action": "proceed"})
        
        phases = []
        
        async for event in layer2.process_streaming("test", {}, {}):
            phases.append(event.get("phase"))
        
        assert "started" in phases
        assert "observe_started" in phases
        assert "cycle_complete" in phases


class TestProcessBatch:
    """Test batch processing mode."""
    
    @pytest.mark.asyncio
    async def test_process_batch_multiple_intents(self, layer2):
        """Test batch processing multiple intents."""
        intents = [
            {"intent": "test 1", "entities": {}, "context": {}},
            {"intent": "test 2", "entities": {}, "context": {}},
        ]
        
        results = await layer2.process_batch(intents)
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_process_batch_handles_errors(self, layer2):
        """Test batch processing handles errors gracefully."""
        intents = [
            {"intent": "valid", "entities": {}},
            {},  # Invalid - missing intent
        ]
        
        results = await layer2.process_batch(intents)
        
        assert len(results) == 2


# ============================================================================
# METRICS TESTS
# ============================================================================

class TestMetrics:
    """Test metrics functionality."""
    
    def test_get_metrics(self, layer2):
        """Test getting basic metrics."""
        metrics = layer2.get_metrics()
        
        assert "cognitive_cycles" in metrics
        assert "decisions_made" in metrics
    
    def test_get_advanced_metrics(self, layer2):
        """Test getting advanced metrics."""
        metrics = layer2.get_advanced_metrics()
        
        assert "basic" in metrics
        assert "circuit_breaker" in metrics
        assert "cache" in metrics
        assert "auto_tuning" in metrics
        assert "cross_cycle" in metrics
        assert "fallbacks" in metrics
        assert "streaming" in metrics
    
    def test_get_source_effectiveness_report(self, layer2):
        """Test getting source effectiveness report."""
        report = layer2.get_source_effectiveness_report()
        
        assert "effectiveness_by_intent" in report
        assert "confidence_weights" in report
        assert "cache_stats" in report


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestLayer2Integration:
    """Integration tests for Layer 2 as a whole."""
    
    @pytest.mark.asyncio
    async def test_full_ooda_cycle(self, layer2):
        """Test complete OODA cycle using process_fast with mocks."""
        # Use process_fast which is more testable
        layer2._orient = AsyncMock(return_value={
            "understanding": "test",
            "concerns": [],
            "opportunities": [],
            "confidence": 0.8
        })
        layer2._decide = AsyncMock(return_value={
            "action": "proceed",
            "modifications": [],
            "warnings": [],
            "reason": "test"
        })
        
        # process_fast uses _observe_parallel internally which works without mocking
        result = await layer2.process_fast(
            intent="analyze code quality",
            entities={"file": "test.py"},
            context={}
        )
        
        assert result is not None
        assert "observations" in result
        assert "decision" in result
    
    @pytest.mark.asyncio
    async def test_multiple_cycles(self, layer2):
        """Test multiple cognitive cycles."""
        # Mock _orient and _decide
        layer2._orient = AsyncMock(return_value={"confidence": 0.8})
        layer2._decide = AsyncMock(return_value={"action": "proceed"})
        
        for i in range(3):
            result = await layer2.process_fast(f"test intent {i}", {}, {})
            assert result is not None
        
        assert layer2.metrics["parallel_queries"] >= 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, layer2):
        """Test circuit breaker works with processing."""
        # Mock _orient and _decide
        layer2._orient = AsyncMock(return_value={"confidence": 0.8})
        layer2._decide = AsyncMock(return_value={"action": "proceed"})
        
        # Open circuit
        layer2._circuit_breaker["memory_mesh"]["state"] = "open"
        layer2._circuit_breaker["memory_mesh"]["last_failure"] = datetime.utcnow()
        
        # Should still process (with fallback/skip)
        result = await layer2.process_fast("test", {}, {})
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, layer2):
        """Test caching works end-to-end."""
        # Mock _orient and _decide
        layer2._orient = AsyncMock(return_value={"confidence": 0.8})
        layer2._decide = AsyncMock(return_value={"action": "proceed"})
        
        # First call
        result1 = await layer2.process_fast("integration test", {"key": "value"}, {})
        
        # Second call - should be cached
        initial_hits = layer2.metrics["cache_hits"]
        result2 = await layer2.process_fast("integration test", {"key": "value"}, {})
        
        assert layer2.metrics["cache_hits"] > initial_hits
    
    def test_all_components_accessible(self, layer2):
        """Test all expected components are accessible."""
        components = [
            "_memory_mesh",
            "_rag_retriever",
            "_oracle_hub",
            "_world_model",
            "_diagnostic_engine",
            "_code_analyzer",
            "_librarian",
            "_mirror_system",
            "_confidence_scorer",
            "_cognitive_engine",
            "_healing_system",
            "_timesense",
            "_clarity_framework",
            "_failure_learning",
            "_mutation_tracker",
            "_self_updater",
            "_llm_orchestrator",
            "_neuro_symbolic_reasoner"
        ]
        
        for component in components:
            assert hasattr(layer2, component), f"Missing component: {component}"


# ============================================================================
# STRESS TESTS
# ============================================================================

class TestLayer2Stress:
    """Stress tests for Layer 2."""
    
    @pytest.mark.asyncio
    async def test_high_volume_caching(self, layer2):
        """Test caching under high volume."""
        for i in range(200):
            layer2._set_cached_result(f"key_{i}", {"data": i})
        
        # Should not exceed max size
        assert len(layer2._query_cache) <= layer2._cache_max_size
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, layer2):
        """Test concurrent processing."""
        intents = [{"intent": f"test {i}", "entities": {}} for i in range(10)]
        
        results = await layer2.process_batch(intents)
        
        assert len(results) == 10
    
    def test_circuit_breaker_rapid_failures(self, layer2):
        """Test circuit breaker with rapid failures."""
        for _ in range(10):
            layer2._record_circuit_failure("memory_mesh")
        
        cb = layer2._circuit_breaker["memory_mesh"]
        assert cb["state"] == "open"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
