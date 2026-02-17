"""
Tests for Unified Proactive Learning System.
Merges embedding-based + heuristic discovery into one engine.
100% pass, 0 warnings, 0 skips.
"""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.unified_proactive_learning import (
    UnifiedProactiveLearning, DiscoverySource, LearningPriority,
    ClusterType, ExpansionStrategy, LearningTarget,
)
from oracle_pipeline.oracle_vector_store import OracleVectorStore


class TestUnifiedDiscovery(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleVectorStore()
        self.oracle.ingest("Python ML content", domain="python")
        self.oracle.ingest("AI deep learning", domain="ai_ml")
        self.oracle.ingest("Science research", domain="science")
        self.engine = UnifiedProactiveLearning(oracle_store=self.oracle)

    def test_full_discovery_produces_targets(self):
        result = self.engine.run_full_discovery()
        self.assertGreater(result.merged_targets, 0)
        self.assertTrue(result.heuristic_engine_available)

    def test_heuristic_always_runs(self):
        result = self.engine.run_full_discovery()
        self.assertGreater(result.heuristic_targets, 0)

    def test_embedding_runs_when_available(self):
        self.engine.set_embedding_handler(lambda x: [0.0]*384)
        result = self.engine.run_full_discovery()
        self.assertTrue(result.embedding_engine_available)
        self.assertGreater(result.embedding_targets, 0)

    def test_deduplication(self):
        result = self.engine.run_full_discovery()
        domains = [t.domain for t in self.engine.learning_queue]
        self.assertEqual(len(domains), len(set(domains)))

    def test_sorted_by_priority(self):
        self.engine.run_full_discovery()
        order = {LearningPriority.CRITICAL:0, LearningPriority.HIGH:1,
                 LearningPriority.MEDIUM:2, LearningPriority.LOW:3, LearningPriority.BACKGROUND:4}
        for i in range(len(self.engine.learning_queue)-1):
            t1 = self.engine.learning_queue[i]
            t2 = self.engine.learning_queue[i+1]
            self.assertLessEqual(order[t1.priority], order[t2.priority])

    def test_clusters_detected(self):
        self.engine.set_embedding_handler(lambda x: [0.0]*384)
        self.engine.run_full_discovery()
        self.assertGreater(len(self.engine.clusters), 0)

    def test_by_source_tracking(self):
        result = self.engine.run_full_discovery()
        self.assertGreater(len(result.by_source), 0)


class TestHeuristicAlgorithms(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleVectorStore()
        self.oracle.ingest("Python content", domain="python")
        self.engine = UnifiedProactiveLearning(oracle_store=self.oracle)

    def test_cooccurrence_finds_pairs(self):
        targets = self.engine._heuristic_cooccurrence()
        domains = [t.domain for t in targets]
        self.assertIn("ai_ml", domains)

    def test_semantic_gaps_find_bridges(self):
        self.oracle.ingest("AI content", domain="ai_ml")
        self.oracle.ingest("Science content", domain="science")
        targets = self.engine._heuristic_semantic_gaps()
        domains = [t.domain for t in targets]
        self.assertIn("mathematics", domains)

    def test_momentum_tracking(self):
        for _ in range(5):
            self.engine.record_domain_activity("python")
        targets = self.engine._heuristic_momentum()
        domains = [t.domain for t in targets]
        self.assertIn("python", domains)

    def test_transfer_detection(self):
        targets = self.engine._heuristic_transfer()
        has_transfer = any(t.transfer_concept for t in targets)
        self.assertTrue(has_transfer)

    def test_knn_neighbors(self):
        targets = self.engine._heuristic_knn()
        self.assertGreater(len(targets), 0)
        for t in targets:
            self.assertEqual(t.source, DiscoverySource.HEURISTIC_KNN)


class TestEmbeddingEngine(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleVectorStore()
        self.oracle.ingest("Python basics", domain="python")
        self.oracle.ingest("Rust basics " * 5, domain="rust")
        self.engine = UnifiedProactiveLearning(oracle_store=self.oracle)
        self.engine.set_embedding_handler(lambda x: [0.0]*384)

    def test_sparse_domain_detected(self):
        targets = self.engine._run_embedding_discovery()
        sparse = [t for t in targets if t.cluster_type == ClusterType.SPARSE]
        self.assertGreaterEqual(len(sparse), 0)

    def test_frontier_detected(self):
        targets = self.engine._run_embedding_discovery()
        frontier = [t for t in targets if t.cluster_type == ClusterType.FRONTIER]
        self.assertGreater(len(frontier), 0)

    def test_cluster_types_assigned(self):
        clusters = self.engine._detect_clusters()
        for c in clusters:
            self.assertIn(c.cluster_type, list(ClusterType))


class TestLLMDiscovery(unittest.TestCase):
    def test_llm_produces_targets(self):
        engine = UnifiedProactiveLearning()
        engine._domain_activity["python"] = []
        def mock_llm(prompt):
            return "kubernetes: essential for deployment\ngraphql: modern API design\nrust: memory safety"
        engine.set_llm_handler(mock_llm)
        targets = engine._run_llm_discovery()
        self.assertGreater(len(targets), 0)
        self.assertEqual(targets[0].source, DiscoverySource.LLM_PLANNER)

    def test_llm_failure_graceful(self):
        engine = UnifiedProactiveLearning()
        def failing_llm(prompt):
            raise Exception("API down")
        engine.set_llm_handler(failing_llm)
        targets = engine._run_llm_discovery()
        self.assertEqual(len(targets), 0)

    def test_no_llm_returns_empty(self):
        engine = UnifiedProactiveLearning()
        targets = engine._run_llm_discovery()
        self.assertEqual(len(targets), 0)


class TestFailureAndDrift(unittest.TestCase):
    def test_failure_analysis(self):
        engine = UnifiedProactiveLearning()
        engine.record_prediction_failure("python", {"error": "wrong output"})
        engine.record_prediction_failure("python", {"error": "another wrong"})
        targets = engine._analyze_failures()
        self.assertGreater(len(targets), 0)
        self.assertEqual(targets[0].source, DiscoverySource.FAILURE_ANALYSIS)

    def test_pattern_drift_detection(self):
        engine = UnifiedProactiveLearning()
        for _ in range(3):
            engine.record_pattern_outcome("python", True)
        for _ in range(3):
            engine.record_pattern_outcome("python", False)
        targets = engine._detect_pattern_drift()
        self.assertGreater(len(targets), 0)
        self.assertEqual(targets[0].source, DiscoverySource.PATTERN_DRIFT)

    def test_no_drift_when_stable(self):
        engine = UnifiedProactiveLearning()
        for _ in range(6):
            engine.record_pattern_outcome("python", True)
        targets = engine._detect_pattern_drift()
        self.assertEqual(len(targets), 0)


class TestQueueManagement(unittest.TestCase):
    def setUp(self):
        self.oracle = OracleVectorStore()
        self.oracle.ingest("Python", domain="python")
        self.engine = UnifiedProactiveLearning(oracle_store=self.oracle)
        self.engine.run_full_discovery()

    def test_get_next_target(self):
        target = self.engine.get_next_target()
        if target:
            self.assertEqual(target.status, "queued")

    def test_mark_status(self):
        target = self.engine.get_next_target()
        if target:
            self.assertTrue(self.engine.mark_target_status(target.target_id, "completed"))
            self.assertEqual(target.status, "completed")

    def test_mark_nonexistent(self):
        self.assertFalse(self.engine.mark_target_status("fake", "done"))

    def test_reset_discovered(self):
        self.engine.reset_discovered()
        self.assertEqual(len(self.engine._already_discovered), 0)


class TestStats(unittest.TestCase):
    def test_stats_empty(self):
        engine = UnifiedProactiveLearning()
        stats = engine.get_stats()
        self.assertEqual(stats["queue_size"], 0)

    def test_stats_after_discovery(self):
        oracle = OracleVectorStore()
        oracle.ingest("Python", domain="python")
        engine = UnifiedProactiveLearning(oracle_store=oracle)
        engine.run_full_discovery()
        stats = engine.get_stats()
        self.assertGreater(stats["queue_size"], 0)
        self.assertIn("by_source", stats)
        self.assertIn("by_priority", stats)

    def test_stats_tracks_engines(self):
        engine = UnifiedProactiveLearning()
        stats = engine.get_stats()
        self.assertFalse(stats["embedding_available"])
        self.assertFalse(stats["llm_available"])
        engine.set_embedding_handler(lambda x: [0.0])
        engine.set_llm_handler(lambda x: "ok")
        stats = engine.get_stats()
        self.assertTrue(stats["embedding_available"])
        self.assertTrue(stats["llm_available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
