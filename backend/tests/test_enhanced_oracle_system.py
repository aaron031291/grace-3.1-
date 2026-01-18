"""
Tests for Enhanced Oracle Intelligence System

Tests:
1. Unified Oracle Hub - ingestion from all sources
2. Reverse KNN Learning - gap detection and expansion
3. Enhanced Oracle Memory - calibration, correlation, priority
4. Enhanced Proactive Learning - LLM orchestration, targets
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path


# =============================================================================
# UNIFIED ORACLE HUB TESTS
# =============================================================================

class TestUnifiedOracleHub:
    """Tests for the Unified Oracle Hub."""
    
    def test_hub_initialization(self):
        """Test hub can be initialized."""
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        assert hub is not None
        assert hasattr(hub, 'ingest')
        assert hasattr(hub, 'get_stats')
    
    def test_intelligence_source_enum(self):
        """Test all intelligence sources are defined."""
        from oracle_intelligence.unified_oracle_hub import IntelligenceSource
        
        expected_sources = [
            'ai_research', 'github_pulls', 'stackoverflow', 'sandbox_insights',
            'templates', 'learning_memory', 'whitelist', 'internal_updates',
            'librarian', 'pattern', 'web_knowledge', 'documentation', 'user_feedback'
        ]
        
        actual_sources = [s.value for s in IntelligenceSource]
        for expected in expected_sources:
            assert expected in actual_sources, f"Missing source: {expected}"
    
    def test_intelligence_item_creation(self):
        """Test IntelligenceItem can be created."""
        from oracle_intelligence.unified_oracle_hub import IntelligenceItem, IntelligenceSource
        
        item = IntelligenceItem(
            item_id="TEST-001",
            source=IntelligenceSource.AI_RESEARCH,
            title="Test Item",
            content="Test content",
            confidence=0.8,
            tags=["test"]
        )
        
        assert item.item_id == "TEST-001"
        assert item.source == IntelligenceSource.AI_RESEARCH
        assert item.confidence == 0.8
        
        # Test to_dict
        data = item.to_dict()
        assert data["item_id"] == "TEST-001"
        assert data["source"] == "ai_research"
    
    @pytest.mark.asyncio
    async def test_hub_ingest_item(self):
        """Test ingesting an item through the hub."""
        from oracle_intelligence.unified_oracle_hub import (
            get_oracle_hub, IntelligenceItem, IntelligenceSource
        )
        
        hub = get_oracle_hub()
        
        item = IntelligenceItem(
            item_id=f"TEST-{uuid.uuid4().hex[:8]}",
            source=IntelligenceSource.TEMPLATES,
            title="Test Template",
            content="def hello(): pass",
            confidence=0.9,
            tags=["test", "template"]
        )
        
        result = await hub.ingest(item)
        
        assert result["status"] in ["success", "skipped"]
    
    @pytest.mark.asyncio
    async def test_hub_ingest_from_sandbox(self):
        """Test sandbox ingestion method."""
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        
        result = await hub.ingest_from_sandbox(
            experiment_id="EXP-TEST-001",
            experiment_name="Test Experiment",
            results={"accuracy": 0.95},
            lessons_learned=["Lesson 1", "Lesson 2"],
            success=True
        )
        
        assert result["status"] in ["success", "skipped"]
    
    @pytest.mark.asyncio
    async def test_hub_ingest_from_template(self):
        """Test template ingestion method."""
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        
        result = await hub.ingest_from_template(
            template_name="Test Pattern",
            pattern_type="api_handler",
            code_example="@app.get('/test')\ndef test(): pass",
            description="A test API pattern",
            category="backend"
        )
        
        assert result["status"] in ["success", "skipped"]
    
    def test_hub_stats(self):
        """Test getting hub statistics."""
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        stats = hub.get_stats()
        
        assert "total_ingested" in stats
        assert "successful" in stats
        assert "by_source" in stats
    
    def test_hub_status(self):
        """Test getting hub status."""
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        status = hub.get_status()
        
        assert "status" in status
        assert "export_path" in status


# =============================================================================
# ENHANCED ORACLE MEMORY TESTS
# =============================================================================

class TestEnhancedOracleMemory:
    """Tests for Enhanced Oracle Memory."""
    
    def test_memory_initialization(self):
        """Test memory can be initialized."""
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        assert memory is not None
        assert memory.storage_path.exists()
    
    def test_unified_memory_item_creation(self):
        """Test UnifiedMemoryItem creation and properties."""
        from oracle_intelligence.enhanced_oracle_memory import (
            UnifiedMemoryItem, MemoryItemType
        )
        
        item = UnifiedMemoryItem(
            memory_id="MEM-001",
            item_type=MemoryItemType.RESEARCH,
            title="Test Research",
            content="Test content for research",
            raw_confidence=0.75,
            impact_score=0.8,
            tags=["test"]
        )
        
        # Test properties
        assert item.freshness > 0.99  # Just created, should be fresh
        assert item.priority_score > 0
        
        # Test to_dict
        data = item.to_dict()
        assert data["memory_id"] == "MEM-001"
        assert data["type"] == "research"
    
    def test_memory_item_freshness_decay(self):
        """Test freshness decays over time."""
        from oracle_intelligence.enhanced_oracle_memory import (
            UnifiedMemoryItem, MemoryItemType
        )
        
        # Create item from 60 days ago
        old_item = UnifiedMemoryItem(
            memory_id="MEM-OLD",
            item_type=MemoryItemType.PATTERN,
            title="Old Pattern",
            content="Old content",
            created_at=datetime.utcnow() - timedelta(days=60),
            freshness_half_life_days=30.0
        )
        
        # Freshness should be ~0.25 (2 half-lives)
        assert old_item.freshness < 0.3
        assert old_item.freshness > 0.1
    
    def test_memory_item_version_tracking(self):
        """Test version tracking on updates."""
        from oracle_intelligence.enhanced_oracle_memory import (
            UnifiedMemoryItem, MemoryItemType
        )
        
        item = UnifiedMemoryItem(
            memory_id="MEM-VERSION",
            item_type=MemoryItemType.INSIGHT,
            title="Versioned Item",
            content="Original content",
            raw_confidence=0.5
        )
        
        assert item.version == 1
        
        item.update_version("Updated content", 0.7)
        
        assert item.version == 2
        assert item.content == "Updated content"
        assert len(item.previous_versions) == 1
    
    @pytest.mark.asyncio
    async def test_memory_store_item(self):
        """Test storing an item in memory."""
        from oracle_intelligence.enhanced_oracle_memory import (
            get_enhanced_oracle_memory, UnifiedMemoryItem, MemoryItemType
        )
        
        memory = get_enhanced_oracle_memory()
        
        item = UnifiedMemoryItem(
            memory_id=f"MEM-{uuid.uuid4().hex[:8]}",
            item_type=MemoryItemType.RESEARCH,
            title="Store Test",
            content="Content to store",
            raw_confidence=0.8,
            tags=["test", "store"]
        )
        
        stored = await memory.store(item)
        
        assert stored.memory_id == item.memory_id
        assert stored.impact_score > 0  # Impact computed
    
    def test_calibrator_initialization(self):
        """Test confidence calibrator initialization."""
        from oracle_intelligence.enhanced_oracle_memory import ConfidenceCalibrator
        
        calibrator = ConfidenceCalibrator(n_buckets=10)
        
        assert calibrator.n_buckets == 10
        assert calibrator.bucket_width == 0.1
    
    def test_calibrator_record_outcome(self):
        """Test recording outcomes for calibration."""
        from oracle_intelligence.enhanced_oracle_memory import ConfidenceCalibrator
        
        calibrator = ConfidenceCalibrator()
        
        # Record some outcomes
        for _ in range(10):
            calibrator.record_outcome("pattern", 0.8, True)
        for _ in range(5):
            calibrator.record_outcome("pattern", 0.8, False)
        
        # Check bucket
        bucket_idx = calibrator.get_bucket_index(0.8)
        bucket = calibrator._buckets["pattern"][bucket_idx]
        
        assert bucket.n == 15
        assert bucket.n_correct == 10
        assert abs(bucket.accuracy - 0.666) < 0.01
    
    def test_calibrator_ece(self):
        """Test Expected Calibration Error computation."""
        from oracle_intelligence.enhanced_oracle_memory import ConfidenceCalibrator
        
        calibrator = ConfidenceCalibrator()
        
        # Perfect calibration: 80% predicted, 80% accurate
        for _ in range(100):
            calibrator.record_outcome("test", 0.8, True)
        for _ in range(25):
            calibrator.record_outcome("test", 0.8, False)
        
        ece = calibrator.compute_ece("test")
        
        # ECE should be low for well-calibrated predictions
        assert ece < 0.1
    
    def test_memory_priority_queue(self):
        """Test priority queue ordering."""
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        
        priority_items = memory.get_priority_items(limit=5)
        
        # Should return a list (may be empty if no items)
        assert isinstance(priority_items, list)
    
    def test_memory_expansion_targets(self):
        """Test getting expansion targets."""
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        
        targets = memory.get_expansion_targets()
        
        assert isinstance(targets, list)
    
    def test_memory_stats(self):
        """Test memory statistics."""
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        stats = memory.get_stats()
        
        assert "total_items" in stats
        assert "calibration" in stats
        assert "correlation" in stats
        assert "by_type" in stats


# =============================================================================
# REVERSE KNN LEARNING TESTS
# =============================================================================

class TestReverseKNNLearning:
    """Tests for Reverse KNN Learning."""
    
    def test_rknn_initialization(self):
        """Test RKNN can be initialized."""
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        assert rknn is not None
        assert hasattr(rknn, 'analyze_knowledge_landscape')
    
    def test_knowledge_cluster_types(self):
        """Test cluster type enum."""
        from oracle_intelligence.reverse_knn_learning import KnowledgeClusterType
        
        types = [t.value for t in KnowledgeClusterType]
        
        assert "dense" in types
        assert "sparse" in types
        assert "frontier" in types
        assert "isolated" in types
    
    def test_expansion_strategies(self):
        """Test expansion strategy enum."""
        from oracle_intelligence.reverse_knn_learning import ExpansionStrategy
        
        strategies = [s.value for s in ExpansionStrategy]
        
        assert "depth" in strategies
        assert "breadth" in strategies
        assert "gap_fill" in strategies
        assert "frontier" in strategies
    
    def test_knowledge_cluster_dataclass(self):
        """Test KnowledgeCluster dataclass."""
        from oracle_intelligence.reverse_knn_learning import (
            KnowledgeCluster, KnowledgeClusterType
        )
        
        cluster = KnowledgeCluster(
            cluster_id="CLUSTER-001",
            cluster_type=KnowledgeClusterType.SPARSE,
            centroid_topic="error handling",
            member_count=5,
            avg_confidence=0.7,
            topics=["error", "exception", "handling"],
            sources=["github", "stackoverflow"],
            gap_score=0.6
        )
        
        assert cluster.cluster_id == "CLUSTER-001"
        assert cluster.gap_score == 0.6
        
        data = cluster.to_dict()
        assert data["type"] == "sparse"
    
    def test_expansion_query_dataclass(self):
        """Test ExpansionQuery dataclass."""
        from oracle_intelligence.reverse_knn_learning import (
            ExpansionQuery, ExpansionStrategy
        )
        
        query = ExpansionQuery(
            query_id="EXPAND-001",
            source="github",
            query_text="error handling best practices",
            cluster_id="CLUSTER-001",
            strategy=ExpansionStrategy.GAP_FILL,
            priority=0.8,
            expected_relevance=0.7
        )
        
        assert query.query_id == "EXPAND-001"
        assert query.priority == 0.8
        assert not query.executed
    
    @pytest.mark.asyncio
    async def test_rknn_generate_queries(self):
        """Test generating expansion queries."""
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        
        queries = await rknn.generate_expansion_queries(max_queries=5)
        
        assert isinstance(queries, list)
    
    def test_rknn_stats(self):
        """Test RKNN statistics."""
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        stats = rknn.get_stats()
        
        assert "clusters_analyzed" in stats
        assert "gaps_identified" in stats
        assert "expansions_executed" in stats
    
    def test_rknn_start_stop(self):
        """Test starting and stopping proactive learning."""
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        
        # Start
        result = rknn.start_proactive_learning()
        assert result["status"] in ["started", "already_running"]
        
        # Stop
        result = rknn.stop_proactive_learning()
        assert result["status"] == "stopped"


# =============================================================================
# ENHANCED PROACTIVE LEARNING TESTS
# =============================================================================

class TestEnhancedProactiveLearning:
    """Tests for Enhanced Proactive Learning."""
    
    def test_learning_initialization(self):
        """Test learning system can be initialized."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        
        learning = get_enhanced_proactive_learning()
        assert learning is not None
    
    def test_learning_modes(self):
        """Test learning mode enum."""
        from oracle_intelligence.enhanced_proactive_learning import LearningMode
        
        modes = [m.value for m in LearningMode]
        
        assert "evidence_gap" in modes
        assert "uncertainty" in modes
        assert "staleness" in modes
        assert "pattern_drift" in modes
        assert "failure" in modes
        assert "cross" in modes
        assert "frontier" in modes
    
    def test_learning_target_dataclass(self):
        """Test LearningTarget dataclass."""
        from oracle_intelligence.enhanced_proactive_learning import (
            LearningTarget, LearningMode
        )
        
        target = LearningTarget(
            target_id="TARGET-001",
            mode=LearningMode.EVIDENCE_GAP,
            query="async error handling",
            sources=["github", "stackoverflow"],
            priority=0.8,
            evidence_needed=["code examples", "best practices"]
        )
        
        assert target.target_id == "TARGET-001"
        assert target.mode == LearningMode.EVIDENCE_GAP
        
        data = target.to_dict()
        assert data["mode"] == "evidence_gap"
    
    def test_llm_plan_dataclass(self):
        """Test LLMPlan dataclass."""
        from oracle_intelligence.enhanced_proactive_learning import LLMPlan
        
        plan = LLMPlan(
            plan_id="PLAN-001",
            objective="Fill knowledge gap on caching",
            queries=["caching strategies", "cache invalidation"],
            sources=["github", "documentation"],
            expected_evidence=["code examples"]
        )
        
        assert plan.plan_id == "PLAN-001"
        assert len(plan.queries) == 2
    
    @pytest.mark.asyncio
    async def test_generate_learning_targets(self):
        """Test generating learning targets."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        learning = get_enhanced_proactive_learning(enhanced_memory=memory)
        
        targets = await learning.generate_learning_targets()
        
        assert isinstance(targets, list)
    
    def test_record_prediction_failure(self):
        """Test recording a failed prediction."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        
        learning = get_enhanced_proactive_learning()
        
        learning.record_prediction_failure(
            memory_id="MEM-FAIL-001",
            title="Failed Prediction",
            predicted_confidence=0.9,
            actual_outcome="The prediction was wrong",
            impact=0.7
        )
        
        assert len(learning._failed_predictions) > 0
    
    def test_record_pattern_outcome(self):
        """Test recording a pattern outcome."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        
        learning = get_enhanced_proactive_learning()
        
        learning.record_pattern_outcome(
            pattern_id="PATTERN-001",
            description="try-except pattern",
            success=True
        )
        
        assert "PATTERN-001" in learning._pattern_history
    
    def test_learning_stats(self):
        """Test learning statistics."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        
        learning = get_enhanced_proactive_learning()
        stats = learning.get_stats()
        
        assert "targets_generated" in stats
        assert "targets_executed" in stats
        assert "knowledge_added" in stats
        assert "llm_plans" in stats
    
    def test_learning_start_stop(self):
        """Test starting and stopping continuous learning."""
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        
        learning = get_enhanced_proactive_learning()
        
        # Start
        result = learning.start_continuous_learning()
        assert result["status"] in ["started", "already_running"]
        
        # Stop
        result = learning.stop_continuous_learning()
        assert result["status"] == "stopped"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestOracleSystemIntegration:
    """Integration tests for the complete Oracle system."""
    
    @pytest.mark.asyncio
    async def test_full_ingestion_flow(self):
        """Test complete flow: Hub → Memory → Learning."""
        from oracle_intelligence.unified_oracle_hub import (
            get_oracle_hub, IntelligenceItem, IntelligenceSource
        )
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        hub = get_oracle_hub()
        memory = get_enhanced_oracle_memory()
        
        # Ingest through hub
        item = IntelligenceItem(
            item_id=f"INTEG-{uuid.uuid4().hex[:8]}",
            source=IntelligenceSource.GITHUB_PULLS,
            title="Integration Test Item",
            content="Testing the full flow from ingestion to memory",
            confidence=0.85,
            tags=["integration", "test"]
        )
        
        result = await hub.ingest(item)
        assert result["status"] in ["success", "skipped"]
    
    @pytest.mark.asyncio
    async def test_evidence_chain_retrieval(self):
        """Test multi-hop evidence chain retrieval."""
        from oracle_intelligence.enhanced_oracle_memory import (
            get_enhanced_oracle_memory, UnifiedMemoryItem, MemoryItemType
        )
        
        memory = get_enhanced_oracle_memory()
        
        # Store some items first
        for i in range(3):
            item = UnifiedMemoryItem(
                memory_id=f"CHAIN-{i}",
                item_type=MemoryItemType.RESEARCH,
                title=f"Error Handling Research {i}",
                content=f"Content about error handling patterns {i}",
                raw_confidence=0.7 + i * 0.1,
                tags=["error", "handling", "test"]
            )
            await memory.store(item)
        
        # Build evidence chain
        chain = await memory.retrieve_evidence_chain(
            query="error handling",
            max_hops=2
        )
        
        assert chain is not None
        assert chain.chain_id.startswith("CHAIN-")
    
    def test_calibration_persistence(self):
        """Test calibration state can be saved and loaded."""
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        
        # Record some outcomes
        memory.calibrator.record_outcome("test_type", 0.7, True)
        memory.calibrator.record_outcome("test_type", 0.7, False)
        
        # Save state
        memory.save_state()
        
        # Check files exist
        assert (memory.storage_path / "calibration.json").exists()
    
    @pytest.mark.asyncio
    async def test_outcome_feedback_loop(self):
        """Test that recording outcomes updates calibration."""
        from oracle_intelligence.enhanced_oracle_memory import (
            get_enhanced_oracle_memory, UnifiedMemoryItem, MemoryItemType
        )
        
        memory = get_enhanced_oracle_memory()
        
        # Store an item
        item = UnifiedMemoryItem(
            memory_id=f"FEEDBACK-{uuid.uuid4().hex[:8]}",
            item_type=MemoryItemType.INSIGHT,
            title="Feedback Test",
            content="Testing feedback loop",
            raw_confidence=0.8
        )
        stored = await memory.store(item)
        
        # Record outcome
        await memory.record_outcome(
            memory_id=stored.memory_id,
            was_correct=True,
            actual_outcome="Prediction was correct"
        )
        
        # Check outcome was recorded
        assert memory._stats["outcomes_recorded"] > 0


# =============================================================================
# RUN TESTS
# =============================================================================

def run_all_tests():
    """Run all tests and print summary."""
    import sys
    
    print("=" * 60)
    print("ENHANCED ORACLE SYSTEM TESTS")
    print("=" * 60)
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    return exit_code


if __name__ == "__main__":
    run_all_tests()
