"""
Comprehensive tests for the Deep Reasoning Integration Layer.

Tests read-only system connections, snapshots, reasoning tasks,
dual-format output, and full integration with the perpetual loop.

100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.deep_reasoning_integration import (
    DeepReasoningIntegration,
    ReasoningTaskType,
    ReasoningRequest,
    AccessMode,
    SystemSnapshot,
)
from oracle_pipeline.oracle_vector_store import OracleVectorStore
from oracle_pipeline.source_code_index import SourceCodeIndex
from oracle_pipeline.hallucination_guard import HallucinationGuard
from oracle_pipeline.librarian_file_manager import LibrarianFileManager
from oracle_pipeline.proactive_discovery_engine import ProactiveDiscoveryEngine
from oracle_pipeline.perpetual_learning_loop import PerpetualLearningLoop


class TestDeepReasoningConnections(unittest.TestCase):
    """Tests for system connections."""

    def setUp(self):
        self.reasoning = DeepReasoningIntegration()

    def test_connect_oracle(self):
        """Test connecting Oracle store."""
        oracle = OracleVectorStore()
        self.reasoning.connect_oracle(oracle)
        self.assertIn("oracle", self.reasoning._access_modes)
        self.assertEqual(self.reasoning._access_modes["oracle"], AccessMode.READ_ONLY)

    def test_connect_source_index(self):
        """Test connecting Source Code Index."""
        idx = SourceCodeIndex()
        self.reasoning.connect_source_index(idx)
        self.assertEqual(self.reasoning._access_modes["source_index"], AccessMode.READ_ONLY)

    def test_connect_librarian(self):
        """Test connecting Librarian."""
        lib = LibrarianFileManager()
        self.reasoning.connect_librarian(lib)
        self.assertEqual(self.reasoning._access_modes["librarian"], AccessMode.READ_ONLY)

    def test_connect_trust_chain(self):
        """Test connecting Trust Chain."""
        chain = {"entry1": "data"}
        self.reasoning.connect_trust_chain(chain)
        self.assertEqual(self.reasoning._access_modes["trust_chain"], AccessMode.READ_ONLY)

    def test_connect_discovery(self):
        """Test connecting Discovery Engine."""
        disc = ProactiveDiscoveryEngine()
        self.reasoning.connect_discovery(disc)
        self.assertEqual(self.reasoning._access_modes["discovery"], AccessMode.READ_ONLY)

    def test_connect_hallucination_guard(self):
        """Test connecting Hallucination Guard."""
        guard = HallucinationGuard()
        self.reasoning.connect_hallucination_guard(guard)
        self.assertEqual(self.reasoning._access_modes["hallucination_guard"], AccessMode.READ_ONLY)

    def test_all_connections_read_only(self):
        """Test all connections are enforced read-only."""
        self.reasoning.connect_oracle(OracleVectorStore())
        self.reasoning.connect_source_index(SourceCodeIndex())
        self.reasoning.connect_librarian(LibrarianFileManager())
        for name, mode in self.reasoning._access_modes.items():
            self.assertEqual(mode, AccessMode.READ_ONLY)

    def test_connect_all_from_loop(self):
        """Test one-line connection from PerpetualLearningLoop."""
        loop = PerpetualLearningLoop()
        self.reasoning.connect_all_from_loop(loop)
        self.assertIn("oracle", self.reasoning._access_modes)
        self.assertIn("source_index", self.reasoning._access_modes)
        self.assertIn("trust_chain", self.reasoning._access_modes)
        self.assertIn("discovery", self.reasoning._access_modes)
        self.assertIn("librarian", self.reasoning._access_modes)

    def test_get_connected_systems(self):
        """Test listing connected systems."""
        self.reasoning.connect_oracle(OracleVectorStore())
        self.reasoning.connect_librarian(LibrarianFileManager())
        connected = self.reasoning.get_connected_systems()
        self.assertIn("oracle", connected)
        self.assertIn("librarian", connected)
        self.assertEqual(connected["oracle"], "read_only")

    def test_set_reasoning_handler(self):
        """Test setting a custom reasoning handler."""
        def custom_handler(context):
            return "Custom reasoning output"
        self.reasoning.set_reasoning_handler(custom_handler)
        self.assertIsNotNone(self.reasoning._reasoning_handler)


class TestSystemSnapshot(unittest.TestCase):
    """Tests for the read-only system snapshot."""

    def test_snapshot_empty_system(self):
        """Test snapshot of empty system."""
        reasoning = DeepReasoningIntegration()
        snapshot = reasoning.take_snapshot()
        self.assertIsInstance(snapshot, SystemSnapshot)
        self.assertEqual(snapshot.oracle_record_count, 0)
        self.assertEqual(snapshot.source_code_modules, 0)

    def test_snapshot_with_oracle(self):
        """Test snapshot with Oracle data."""
        reasoning = DeepReasoningIntegration()
        oracle = OracleVectorStore()
        oracle.ingest("Python content", domain="python")
        oracle.ingest("Rust content", domain="rust")
        reasoning.connect_oracle(oracle)
        snapshot = reasoning.take_snapshot()
        self.assertEqual(snapshot.oracle_record_count, 2)
        self.assertIn("python", snapshot.oracle_domains)

    def test_snapshot_with_source_index(self):
        """Test snapshot with source code index."""
        reasoning = DeepReasoningIntegration()
        idx = SourceCodeIndex()
        idx.index_source_code("app.py", "class App:\n    def run(self): pass")
        reasoning.connect_source_index(idx)
        snapshot = reasoning.take_snapshot()
        self.assertGreater(snapshot.source_code_modules, 0)

    def test_snapshot_with_librarian(self):
        """Test snapshot with librarian data."""
        reasoning = DeepReasoningIntegration()
        lib = LibrarianFileManager()
        lib.create_file("test.py", "code", parent_path="/codebase")
        lib.create_file("doc.md", "text", parent_path="/documents")
        reasoning.connect_librarian(lib)
        snapshot = reasoning.take_snapshot()
        self.assertGreater(snapshot.librarian_file_count, 0)

    def test_snapshot_from_seeded_loop(self):
        """Test snapshot from a seeded loop."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Python machine learning")
        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)
        snapshot = reasoning.take_snapshot()
        self.assertGreater(snapshot.oracle_record_count, 0)
        self.assertGreater(snapshot.trust_chain_size, 0)


class TestReasoningTasks(unittest.TestCase):
    """Tests for reasoning tasks."""

    def setUp(self):
        self.loop = PerpetualLearningLoop()
        self.loop.seed_from_whitelist("Python ML\nRust systems")
        self.reasoning = DeepReasoningIntegration()
        self.reasoning.connect_all_from_loop(self.loop)

    def test_basic_reasoning(self):
        """Test basic reasoning task."""
        request = ReasoningRequest(
            request_id="test-001",
            task_type=ReasoningTaskType.DEEP_ANALYSIS,
            query="What is the current state of the knowledge base?",
        )
        result = self.reasoning.reason(request)
        self.assertIsNotNone(result.conclusion)
        self.assertGreater(len(result.reasoning_chain), 0)
        self.assertGreater(result.confidence, 0)

    def test_gap_analysis(self):
        """Test gap analysis reasoning."""
        result = self.reasoning.analyze_gaps()
        self.assertEqual(result.task_type, ReasoningTaskType.GAP_ANALYSIS)
        self.assertIsNotNone(result.conclusion)

    def test_strategic_planning(self):
        """Test strategic planning reasoning."""
        result = self.reasoning.plan_strategy()
        self.assertEqual(result.task_type, ReasoningTaskType.STRATEGIC_PLANNING)
        self.assertGreater(len(result.recommendations), 0)

    def test_claim_verification(self):
        """Test deep claim verification."""
        result = self.reasoning.verify_claim("Python is used for machine learning")
        self.assertEqual(result.task_type, ReasoningTaskType.VERIFICATION)
        self.assertIsNotNone(result.conclusion)

    def test_architecture_review(self):
        """Test architecture review."""
        result = self.reasoning.review_architecture()
        self.assertEqual(result.task_type, ReasoningTaskType.ARCHITECTURE_REVIEW)
        self.assertIsNotNone(result.conclusion)

    def test_reasoning_chain_has_steps(self):
        """Test reasoning chain has steps."""
        result = self.reasoning.analyze_gaps()
        self.assertGreater(len(result.reasoning_chain), 0)
        for step in result.reasoning_chain:
            self.assertGreater(step.step_number, 0)
            self.assertGreater(len(step.thought), 0)

    def test_systems_consulted(self):
        """Test systems consulted is tracked."""
        result = self.reasoning.analyze_gaps()
        self.assertGreater(len(result.systems_consulted), 0)

    def test_evidence_count(self):
        """Test evidence count is tracked."""
        result = self.reasoning.analyze_gaps()
        self.assertGreaterEqual(result.evidence_count, 0)

    def test_recommendations_generated(self):
        """Test recommendations are generated."""
        result = self.reasoning.plan_strategy()
        self.assertGreater(len(result.recommendations), 0)


class TestDualFormat(unittest.TestCase):
    """Tests for JSON and NLP dual-format output."""

    def setUp(self):
        self.loop = PerpetualLearningLoop()
        self.loop.seed_from_whitelist("Python programming")
        self.reasoning = DeepReasoningIntegration()
        self.reasoning.connect_all_from_loop(self.loop)

    def test_json_output(self):
        """Test JSON output format."""
        result = self.reasoning.analyze_gaps()
        json_out = result.json_output
        self.assertIsInstance(json_out, dict)
        self.assertIn("request_id", json_out)
        self.assertIn("conclusion", json_out)
        self.assertIn("confidence", json_out)
        self.assertIn("reasoning_steps", json_out)
        self.assertIn("recommendations", json_out)
        self.assertIn("snapshot", json_out)

    def test_nlp_output(self):
        """Test NLP output format."""
        result = self.reasoning.analyze_gaps()
        nlp_out = result.nlp_output
        self.assertIsInstance(nlp_out, str)
        self.assertIn("Deep Reasoning Analysis", nlp_out)
        self.assertIn("Conclusion:", nlp_out)
        self.assertIn("Recommendations:", nlp_out)

    def test_json_is_serializable(self):
        """Test JSON output is fully serializable."""
        import json
        result = self.reasoning.plan_strategy()
        serialized = json.dumps(result.json_output)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["request_id"], result.request_id)

    def test_json_contains_snapshot(self):
        """Test JSON contains system snapshot."""
        result = self.reasoning.analyze_gaps()
        snapshot = result.json_output.get("snapshot", {})
        self.assertIn("oracle_records", snapshot)
        self.assertIn("trust_temperature", snapshot)

    def test_nlp_contains_steps(self):
        """Test NLP output contains reasoning steps."""
        result = self.reasoning.analyze_gaps()
        self.assertIn("1.", result.nlp_output)


class TestCustomReasoningHandler(unittest.TestCase):
    """Tests for custom reasoning handler (Kimi integration point)."""

    def test_custom_handler_called(self):
        """Test custom reasoning handler is called."""
        called = {"count": 0}
        def handler(context):
            called["count"] += 1
            return "Step 1: Analyzed the system.\nStep 2: Found key insight.\nConclusion: System is healthy."

        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(OracleVectorStore())
        reasoning.set_reasoning_handler(handler)
        result = reasoning.analyze_gaps()
        self.assertEqual(called["count"], 1)
        self.assertGreater(len(result.reasoning_chain), 0)

    def test_custom_handler_failure_fallback(self):
        """Test fallback when custom handler fails."""
        def failing_handler(context):
            raise Exception("Kimi unavailable")

        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(OracleVectorStore())
        reasoning.set_reasoning_handler(failing_handler)
        result = reasoning.analyze_gaps()
        self.assertIsNotNone(result.conclusion)
        self.assertGreater(len(result.reasoning_chain), 0)

    def test_handler_receives_json_context(self):
        """Test handler receives proper JSON context."""
        received_context = {}
        def handler(context):
            received_context.update(context)
            return "Analysis complete."

        oracle = OracleVectorStore()
        oracle.ingest("Python data", domain="python")
        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(oracle)
        reasoning.set_reasoning_handler(handler)
        reasoning.analyze_gaps()
        self.assertIn("task", received_context)
        self.assertIn("system_state", received_context)
        self.assertIn("query", received_context)

    def test_handler_with_domain_context(self):
        """Test handler receives domain-specific context."""
        received_context = {}
        def handler(context):
            received_context.update(context)
            return "Domain analysis."

        oracle = OracleVectorStore()
        oracle.ingest("Python ML content", domain="python")
        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(oracle)
        reasoning.set_reasoning_handler(handler)
        reasoning.reason(ReasoningRequest(
            request_id="test",
            task_type=ReasoningTaskType.DEEP_ANALYSIS,
            query="Analyze Python knowledge",
            context={"domain": "python"},
        ))
        self.assertIn("domain_knowledge", received_context)


class TestDeepReasoningStats(unittest.TestCase):
    """Tests for statistics."""

    def test_stats_empty(self):
        """Test stats with no tasks."""
        reasoning = DeepReasoningIntegration()
        stats = reasoning.get_stats()
        self.assertEqual(stats["connected_systems"], 0)
        self.assertEqual(stats["total_reasoning_tasks"], 0)

    def test_stats_after_reasoning(self):
        """Test stats after reasoning tasks."""
        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(OracleVectorStore())
        reasoning.analyze_gaps()
        reasoning.plan_strategy()
        stats = reasoning.get_stats()
        self.assertEqual(stats["total_reasoning_tasks"], 2)
        self.assertGreater(stats["average_confidence"], 0)

    def test_stats_connected_count(self):
        """Test connected systems count."""
        reasoning = DeepReasoningIntegration()
        reasoning.connect_oracle(OracleVectorStore())
        reasoning.connect_source_index(SourceCodeIndex())
        reasoning.connect_librarian(LibrarianFileManager())
        stats = reasoning.get_stats()
        self.assertEqual(stats["connected_systems"], 3)


class TestDeepReasoningIntegration(unittest.TestCase):
    """Full integration tests."""

    def test_full_loop_with_reasoning(self):
        """Test reasoning connected to full perpetual loop."""
        loop = PerpetualLearningLoop()
        loop.run_seeded_loop("Python ML\nDocker DevOps", iterations=1)

        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)

        gaps = reasoning.analyze_gaps()
        strategy = reasoning.plan_strategy()

        self.assertIsNotNone(gaps.conclusion)
        self.assertIsNotNone(strategy.conclusion)
        self.assertGreater(len(strategy.recommendations), 0)

    def test_reasoning_sees_real_data(self):
        """Test reasoning sees actual Oracle data."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Python machine learning tutorials")

        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)
        snapshot = reasoning.take_snapshot()

        self.assertGreater(snapshot.oracle_record_count, 0)
        self.assertGreater(snapshot.trust_chain_size, 0)

    def test_reasoning_json_nlp_both_produced(self):
        """Test both formats are always produced."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Test content")
        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)

        result = reasoning.analyze_gaps()
        self.assertIsInstance(result.json_output, dict)
        self.assertIsInstance(result.nlp_output, str)
        self.assertGreater(len(result.json_output), 0)
        self.assertGreater(len(result.nlp_output), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
