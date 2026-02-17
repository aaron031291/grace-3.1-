"""
Comprehensive test suite for the Advanced Trust System.

Tests all 7 features + pillar tracking + verification pipeline.
100% pass rate, zero warnings, zero skips required.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta, timezone

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from advanced_trust.confidence_cascading import (
    ConfidenceCascadeEngine,
    CascadeReason,
    CascadeDirection,
    ProvenanceNode,
)
from advanced_trust.adversarial_self_testing import (
    AdversarialSelfTester,
    DataOrigin,
    TestType as AdvTestType,
    TestVerdict as AdvTestVerdict,
)
from advanced_trust.competence_boundaries import (
    CompetenceBoundaryTracker,
    CompetenceLevel,
    AutonomyLevel,
)
from advanced_trust.cross_pillar_learning import (
    CrossPillarLearningEngine,
    PillarType,
    InsightType,
    ActionType,
    PillarEvent as CPLPillarEvent,
)
from advanced_trust.trust_decay import (
    TrustDecayEngine,
    DecayModel,
    VerificationUrgency,
)
from advanced_trust.trust_thermometer import (
    SystemTrustThermometer,
    SystemMode,
    ThermometerConfig,
)
from advanced_trust.meta_verification_learner import (
    MetaVerificationLearner,
)
from advanced_trust.pillar_tracker import (
    PillarTracker,
    Pillar,
    PillarEvent,
    EventSeverity,
)
from advanced_trust.verification_pipeline import (
    VerificationPipeline,
    VerificationStrategy,
    VerificationLevel,
)


# =====================================================================
# 1. CONFIDENCE CASCADING TESTS
# =====================================================================


class TestConfidenceCascading(unittest.TestCase):
    """Tests for Confidence Cascading Engine."""

    def setUp(self):
        self.engine = ConfidenceCascadeEngine(
            damping_factor=0.7, trust_floor=0.05, max_depth=10
        )

    def test_register_node(self):
        """Test registering a node in the provenance graph."""
        node = self.engine.register_node(
            "doc1", trust_score=0.9, source_id="source_a", data_type="document"
        )
        self.assertEqual(node.node_id, "doc1")
        self.assertEqual(node.trust_score, 0.9)
        self.assertEqual(node.source_id, "source_a")
        self.assertIn("doc1", self.engine.nodes)

    def test_register_node_with_parents(self):
        """Test registering a node with parent relationships."""
        self.engine.register_node("parent1", trust_score=0.9)
        self.engine.register_node("parent2", trust_score=0.8)
        child = self.engine.register_node(
            "child1", trust_score=0.7, parent_ids=["parent1", "parent2"]
        )
        self.assertEqual(child.parents, ["parent1", "parent2"])
        self.assertIn("child1", self.engine.nodes["parent1"].children)
        self.assertIn("child1", self.engine.nodes["parent2"].children)

    def test_add_derivation(self):
        """Test adding a derivation link."""
        self.engine.register_node("a", trust_score=0.9)
        self.engine.register_node("b", trust_score=0.8)
        result = self.engine.add_derivation("a", "b")
        self.assertTrue(result)
        self.assertIn("b", self.engine.nodes["a"].children)
        self.assertIn("a", self.engine.nodes["b"].parents)

    def test_add_derivation_missing_node(self):
        """Test derivation with missing node returns False."""
        self.engine.register_node("a", trust_score=0.9)
        result = self.engine.add_derivation("a", "nonexistent")
        self.assertFalse(result)

    def test_cascade_downgrade(self):
        """Test trust downgrade cascading through chain."""
        self.engine.register_node("root", trust_score=0.9)
        self.engine.register_node("child1", trust_score=0.8, parent_ids=["root"])
        self.engine.register_node("child2", trust_score=0.7, parent_ids=["child1"])

        result = self.engine.cascade_trust_downgrade(
            "root", 0.3, CascadeReason.SOURCE_UNRELIABLE
        )

        self.assertGreater(result.nodes_affected, 0)
        self.assertIn("root", result.trust_changes)
        self.assertEqual(self.engine.nodes["root"].trust_score, 0.3)
        # Children should have reduced trust
        self.assertLess(self.engine.nodes["child1"].trust_score, 0.8)
        self.assertLess(self.engine.nodes["child2"].trust_score, 0.7)

    def test_cascade_downgrade_damping(self):
        """Test that cascade damping reduces effect per hop."""
        self.engine.register_node("a", trust_score=0.9)
        self.engine.register_node("b", trust_score=0.9, parent_ids=["a"])
        self.engine.register_node("c", trust_score=0.9, parent_ids=["b"])

        self.engine.cascade_trust_downgrade("a", 0.1, CascadeReason.SOURCE_UNRELIABLE)

        drop_b = 0.9 - self.engine.nodes["b"].trust_score
        drop_c = 0.9 - self.engine.nodes["c"].trust_score
        # Drop at C should be less than drop at B (damping)
        self.assertGreater(drop_b, drop_c)

    def test_cascade_respects_trust_floor(self):
        """Test that cascade never goes below trust floor."""
        self.engine.register_node("root", trust_score=0.9)
        self.engine.register_node("child", trust_score=0.1, parent_ids=["root"])

        self.engine.cascade_trust_downgrade(
            "root", 0.01, CascadeReason.SOURCE_UNRELIABLE
        )
        self.assertGreaterEqual(
            self.engine.nodes["child"].trust_score, self.engine.trust_floor
        )

    def test_cascade_upgrade(self):
        """Test trust upgrade cascading."""
        self.engine.register_node("root", trust_score=0.9)
        self.engine.register_node("child", trust_score=0.8, parent_ids=["root"])
        # Downgrade first
        self.engine.cascade_trust_downgrade("root", 0.3, CascadeReason.SOURCE_UNRELIABLE)
        child_after_downgrade = self.engine.nodes["child"].trust_score

        # Now upgrade
        result = self.engine.cascade_trust_upgrade("root", 0.8)
        self.assertGreater(
            self.engine.nodes["child"].trust_score, child_after_downgrade
        )
        self.assertGreater(result.nodes_affected, 0)

    def test_cascade_no_change_on_same_trust(self):
        """Test that no cascade occurs if trust doesn't drop."""
        self.engine.register_node("root", trust_score=0.5)
        result = self.engine.cascade_trust_downgrade("root", 0.6)
        self.assertEqual(result.nodes_affected, 0)

    def test_cascade_unknown_node(self):
        """Test cascade on nonexistent node returns empty."""
        result = self.engine.cascade_trust_downgrade("ghost", 0.1)
        self.assertEqual(result.nodes_affected, 0)

    def test_get_provenance_chain(self):
        """Test walking the provenance chain upstream."""
        self.engine.register_node("grandparent", trust_score=0.9)
        self.engine.register_node("parent", trust_score=0.8, parent_ids=["grandparent"])
        self.engine.register_node("child", trust_score=0.7, parent_ids=["parent"])

        chain = self.engine.get_provenance_chain("child")
        self.assertIn("parent", chain)
        self.assertIn("grandparent", chain)

    def test_get_downstream_nodes(self):
        """Test getting all downstream nodes."""
        self.engine.register_node("root", trust_score=0.9)
        self.engine.register_node("c1", trust_score=0.8, parent_ids=["root"])
        self.engine.register_node("c2", trust_score=0.7, parent_ids=["root"])
        self.engine.register_node("gc1", trust_score=0.6, parent_ids=["c1"])

        descendants = self.engine.get_downstream_nodes("root")
        self.assertIn("c1", descendants)
        self.assertIn("c2", descendants)
        self.assertIn("gc1", descendants)

    def test_get_node_trust(self):
        """Test getting node trust score."""
        self.engine.register_node("x", trust_score=0.75)
        self.assertEqual(self.engine.get_node_trust("x"), 0.75)
        self.assertEqual(self.engine.get_node_trust("nonexistent"), 0.5)

    def test_get_affected_by_source(self):
        """Test getting nodes affected by a source."""
        self.engine.register_node("n1", trust_score=0.9, source_id="src1")
        self.engine.register_node("n2", trust_score=0.8, source_id="src1")
        affected = self.engine.get_affected_by_source("src1")
        self.assertIn("n1", affected)
        self.assertIn("n2", affected)

    def test_cascade_history(self):
        """Test cascade history tracking."""
        self.engine.register_node("root", trust_score=0.9)
        self.engine.register_node("child", trust_score=0.8, parent_ids=["root"])
        self.engine.cascade_trust_downgrade("root", 0.3)
        history = self.engine.get_cascade_history()
        self.assertEqual(len(history), 1)

    def test_get_stats(self):
        """Test engine statistics."""
        self.engine.register_node("a", trust_score=0.9)
        self.engine.register_node("b", trust_score=0.5)
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_nodes"], 2)
        self.assertAlmostEqual(stats["average_trust"], 0.7, places=1)

    def test_max_depth_limit(self):
        """Test cascade respects max depth."""
        engine = ConfidenceCascadeEngine(max_depth=2)
        engine.register_node("n0", trust_score=0.9)
        engine.register_node("n1", trust_score=0.9, parent_ids=["n0"])
        engine.register_node("n2", trust_score=0.9, parent_ids=["n1"])
        engine.register_node("n3", trust_score=0.9, parent_ids=["n2"])

        result = engine.cascade_trust_downgrade("n0", 0.1)
        self.assertLessEqual(result.depth_reached, 2)


# =====================================================================
# 2. ADVERSARIAL SELF-TESTING TESTS
# =====================================================================


class TestAdversarialSelfTesting(unittest.TestCase):
    """Tests for Adversarial Self-Testing Engine."""

    def setUp(self):
        self.tester = AdversarialSelfTester()

    def test_test_retrieval_result_passes(self):
        """Test that good retrieval content passes."""
        result = self.tester.test_retrieval_result(
            content="Python is a high-level programming language created by Guido van Rossum. "
                    "It emphasizes code readability and supports multiple paradigms.",
            source="official_docs",
            trust_score=0.8,
            domain="python",
        )
        self.assertGreaterEqual(result.passed_count, 1)
        self.assertIsNotNone(result.result_id)
        self.assertEqual(result.data_origin, DataOrigin.RETRIEVAL)

    def test_test_retrieval_detects_short_content(self):
        """Test that very short content is flagged."""
        result = self.tester.test_retrieval_result(
            content="yes",
            source="unknown",
            trust_score=0.5,
        )
        self.assertGreater(result.failed_count, 0)

    def test_test_memory_recall(self):
        """Test memory recall adversarial testing."""
        result = self.tester.test_memory_recall(
            recalled_data="The user previously asked about Docker containers and "
                         "wanted to understand networking between them.",
            memory_type="episodic",
            trust_score=0.7,
        )
        self.assertIsNotNone(result.result_id)
        self.assertEqual(result.data_origin, DataOrigin.MEMORY_RECALL)

    def test_test_procedure_result(self):
        """Test procedure result adversarial testing."""
        result = self.tester.test_procedure_result(
            result_data={"status": "success", "output": "Build completed"},
            procedure_name="build_project",
            trust_score=0.6,
            inputs={"target": "production"},
        )
        self.assertIsNotNone(result.result_id)
        self.assertEqual(result.data_origin, DataOrigin.PROCEDURE_EXECUTION)

    def test_contradiction_detection(self):
        """Test that contradictions are detected."""
        self.tester.register_known_fact(
            "python_typing", "Python is dynamically typed"
        )
        result = self.tester.test_retrieval_result(
            content="Python is not dynamically typed. It uses static typing exclusively.",
            source="bad_source",
            trust_score=0.5,
        )
        # Should detect contradiction
        contradiction_tests = [
            t for t in result.tests_run
            if t.test_type == AdvTestType.CONTRADICTION_CHECK
        ]
        self.assertEqual(len(contradiction_tests), 1)

    def test_temporal_detection_stale(self):
        """Test temporal staleness detection."""
        result = self.tester.test_retrieval_result(
            content="As of 2019, this was the recommended approach. "
                    "As of 2018, this API was available.",
            source="old_blog",
            trust_score=0.5,
        )
        temporal_tests = [
            t for t in result.tests_run
            if t.test_type == AdvTestType.TEMPORAL_CHECK
        ]
        self.assertEqual(len(temporal_tests), 1)
        self.assertIn(
            temporal_tests[0].verdict,
            [AdvTestVerdict.FAILED, AdvTestVerdict.WEAKNESS_FOUND],
        )

    def test_source_cross_check_passes(self):
        """Test source cross-check with agreeing sources."""
        result = self.tester.test_retrieval_result(
            content="Python uses indentation for code blocks instead of braces.",
            source="tutorial",
            trust_score=0.7,
            related_facts=[
                {"content": "Python uses indentation for defining code blocks"},
                {"content": "Indentation is significant in Python syntax"},
                {"content": "Python code blocks use whitespace indentation"},
            ],
        )
        cross_tests = [
            t for t in result.tests_run
            if t.test_type == AdvTestType.SOURCE_CROSS_CHECK
        ]
        self.assertEqual(len(cross_tests), 1)

    def test_trust_adjustment_negative(self):
        """Test that failed tests reduce trust."""
        result = self.tester.test_retrieval_result(
            content="x",  # Very short - will fail completeness
            source="unknown",
            trust_score=0.8,
        )
        self.assertLess(result.adjusted_trust, result.original_trust)

    def test_reverification_triggered(self):
        """Test that low trust triggers re-verification."""
        tester = AdversarialSelfTester(reverification_threshold=0.95)
        result = tester.test_retrieval_result(
            content="Some content with moderate quality.",
            source="unknown",
            trust_score=0.5,
        )
        self.assertTrue(result.needs_reverification)

    def test_get_test_history(self):
        """Test getting test history."""
        self.tester.test_retrieval_result(
            content="Test content for history.",
            source="src1",
            trust_score=0.7,
        )
        history = self.tester.get_test_history()
        self.assertEqual(len(history), 1)

    def test_get_test_history_filtered(self):
        """Test filtered test history."""
        self.tester.test_retrieval_result(
            content="Retrieval content.", source="src1", trust_score=0.7
        )
        self.tester.test_memory_recall(
            recalled_data="Memory content.", memory_type="semantic", trust_score=0.6
        )
        history = self.tester.get_test_history(data_origin=DataOrigin.RETRIEVAL)
        self.assertEqual(len(history), 1)

    def test_get_stats(self):
        """Test statistics calculation."""
        self.tester.test_retrieval_result(
            content="Test data for statistics gathering.",
            source="src",
            trust_score=0.7,
        )
        stats = self.tester.get_stats()
        self.assertEqual(stats["total_tests"], 1)
        self.assertIn("reverification_rate", stats)

    def test_stats_empty(self):
        """Test stats with no data."""
        stats = self.tester.get_stats()
        self.assertEqual(stats["total_tests"], 0)

    def test_all_seven_tests_run(self):
        """Test that all 7 adversarial tests are executed."""
        result = self.tester.test_retrieval_result(
            content="A substantial piece of content that should trigger all tests. "
                    "It contains enough detail to check various aspects.",
            source="good_source",
            trust_score=0.7,
            domain="python",
        )
        self.assertEqual(len(result.tests_run), 7)


# =====================================================================
# 3. COMPETENCE BOUNDARIES TESTS
# =====================================================================


class TestCompetenceBoundaries(unittest.TestCase):
    """Tests for Competence Boundary Tracker."""

    def setUp(self):
        self.tracker = CompetenceBoundaryTracker(min_attempts=5)

    def test_record_outcome(self):
        """Test recording an outcome."""
        comp = self.tracker.record_outcome("python", success=True, confidence=0.9)
        self.assertEqual(comp.total_attempts, 1)
        self.assertEqual(comp.successful_attempts, 1)
        self.assertEqual(comp.accuracy, 1.0)

    def test_competence_level_uncharted(self):
        """Test that domain starts as uncharted with few attempts."""
        for _ in range(3):
            self.tracker.record_outcome("new_domain", success=True)
        comp = self.tracker.get_competence("new_domain")
        self.assertEqual(comp.competence_level, CompetenceLevel.UNCHARTED)

    def test_competence_level_expert(self):
        """Test expert competence level."""
        for _ in range(20):
            self.tracker.record_outcome("python", success=True)
        comp = self.tracker.get_competence("python")
        self.assertEqual(comp.competence_level, CompetenceLevel.EXPERT)

    def test_competence_level_novice(self):
        """Test novice competence level."""
        for i in range(10):
            self.tracker.record_outcome("legal", success=(i < 3))
        comp = self.tracker.get_competence("legal")
        self.assertEqual(comp.competence_level, CompetenceLevel.NOVICE)

    def test_autonomy_mapping(self):
        """Test that competence maps to correct autonomy."""
        for _ in range(20):
            self.tracker.record_outcome("python", success=True)
        self.assertEqual(
            self.tracker.get_autonomy_level("python"),
            AutonomyLevel.FULL_AUTONOMY,
        )

    def test_verification_intensity(self):
        """Test verification intensity based on competence."""
        for _ in range(20):
            self.tracker.record_outcome("python", success=True)
        intensity = self.tracker.get_verification_intensity("python")
        self.assertLess(intensity, 0.5)  # Expert = low verification

    def test_warn_user_low_competence(self):
        """Test user warning for low competence."""
        for i in range(10):
            self.tracker.record_outcome("legal", success=(i < 3))
        self.assertTrue(self.tracker.should_warn_user("legal"))

    def test_no_warn_high_competence(self):
        """Test no warning for high competence."""
        for _ in range(20):
            self.tracker.record_outcome("python", success=True)
        self.assertFalse(self.tracker.should_warn_user("python"))

    def test_trend_detection(self):
        """Test trend detection."""
        # Declining trend: first half good, second half bad
        for _ in range(20):
            self.tracker.record_outcome("declining_domain", success=True)
        for _ in range(20):
            self.tracker.record_outcome("declining_domain", success=False)
        comp = self.tracker.get_competence("declining_domain")
        self.assertEqual(comp.trend, "declining")

    def test_competence_report(self):
        """Test comprehensive report."""
        for _ in range(10):
            self.tracker.record_outcome("python", success=True)
        for _ in range(10):
            self.tracker.record_outcome("legal", success=False)
        report = self.tracker.get_competence_report()
        self.assertEqual(report.total_domains, 2)
        self.assertIsNotNone(report.overall_accuracy)

    def test_competence_report_empty(self):
        """Test report with no data."""
        report = self.tracker.get_competence_report()
        self.assertEqual(report.total_domains, 0)
        self.assertEqual(report.overall_accuracy, 0.0)

    def test_get_stats(self):
        """Test statistics."""
        for _ in range(10):
            self.tracker.record_outcome("python", success=True)
        stats = self.tracker.get_stats()
        self.assertIn("total_domains", stats)
        self.assertIn("overall_accuracy", stats)

    def test_unknown_domain_defaults(self):
        """Test unknown domain returns safe defaults."""
        comp = self.tracker.get_competence("unknown_domain")
        self.assertEqual(comp.competence_level, CompetenceLevel.UNCHARTED)
        self.assertEqual(comp.autonomy_level, AutonomyLevel.SUPERVISED)

    def test_developing_level(self):
        """Test developing competence level."""
        for i in range(10):
            self.tracker.record_outcome("kubernetes", success=(i < 5))
        comp = self.tracker.get_competence("kubernetes")
        self.assertEqual(comp.competence_level, CompetenceLevel.DEVELOPING)

    def test_competent_level(self):
        """Test competent level."""
        for i in range(10):
            self.tracker.record_outcome("docker", success=(i < 7))
        comp = self.tracker.get_competence("docker")
        self.assertEqual(comp.competence_level, CompetenceLevel.COMPETENT)


# =====================================================================
# 4. CROSS-PILLAR LEARNING TESTS
# =====================================================================


class TestCrossPillarLearning(unittest.TestCase):
    """Tests for Cross-Pillar Learning Engine."""

    def setUp(self):
        self.engine = CrossPillarLearningEngine(pattern_threshold=3)

    def _make_event(self, pillar, event_type, category, description="test"):
        import uuid
        return CPLPillarEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            pillar=pillar,
            event_type=event_type,
            category=category,
            description=description,
        )

    def test_record_event(self):
        """Test recording an event."""
        event = self._make_event(
            PillarType.SELF_BUILDING, "success", "code_generation"
        )
        insights = self.engine.record_event(event)
        self.assertIsInstance(insights, list)

    def test_building_failure_generates_healing_insight(self):
        """Test that building failures generate healing insights."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "database_migration"
            )
            insights = self.engine.record_event(event)

        # Should have generated an insight for healing
        healing_insights = [
            i for i in self.engine.insights
            if PillarType.SELF_HEALING in i.target_pillars
        ]
        self.assertGreater(len(healing_insights), 0)

    def test_building_failure_generates_learning_insight(self):
        """Test that repeated building failures generate learning insights."""
        for _ in range(5):
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "api_integration"
            )
            self.engine.record_event(event)

        learning_insights = [
            i for i in self.engine.insights
            if PillarType.SELF_LEARNING in i.target_pillars
        ]
        self.assertGreater(len(learning_insights), 0)

    def test_learning_gap_generates_governing_insight(self):
        """Test that learning gaps generate governing insights."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_LEARNING,
                "failure",
                "knowledge_gap",
                description="Missing kubernetes knowledge",
            )
            event.data = {"gap_type": "kubernetes"}
            self.engine.record_event(event)

        governing_insights = [
            i for i in self.engine.insights
            if PillarType.SELF_GOVERNING in i.target_pillars
        ]
        self.assertGreater(len(governing_insights), 0)

    def test_healing_success_generates_building_insight(self):
        """Test that healing successes teach building."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_HEALING, "success", "null_pointer_fix"
            )
            self.engine.record_event(event)

        building_insights = [
            i for i in self.engine.insights
            if PillarType.SELF_BUILDING in i.target_pillars
        ]
        self.assertGreater(len(building_insights), 0)

    def test_governing_policy_change(self):
        """Test governing policy change generates cross-pillar insights."""
        event = self._make_event(
            PillarType.SELF_GOVERNING,
            "policy_change",
            "security_policy",
            description="Increased security verification level",
        )
        event.data = {"policy": {"verification_level": "high"}}
        insights = self.engine.record_event(event)
        self.assertGreater(len(insights), 0)

    def test_pending_actions(self):
        """Test getting pending actions."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "test_failure"
            )
            self.engine.record_event(event)

        pending = self.engine.get_pending_actions()
        self.assertGreater(len(pending), 0)

    def test_pending_actions_filtered(self):
        """Test getting pending actions filtered by pillar."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "deploy_failure"
            )
            self.engine.record_event(event)

        healing_actions = self.engine.get_pending_actions(
            target_pillar=PillarType.SELF_HEALING
        )
        self.assertGreater(len(healing_actions), 0)

    def test_mark_action_executed(self):
        """Test marking an action as executed."""
        for _ in range(4):
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "compile_error"
            )
            self.engine.record_event(event)

        pending = self.engine.get_pending_actions()
        if pending:
            result = self.engine.mark_action_executed(
                pending[0].action_id, {"result": "rollback prepared"}
            )
            self.assertTrue(result)
            self.assertEqual(pending[0].status, "executed")

    def test_mark_nonexistent_action(self):
        """Test marking nonexistent action returns False."""
        result = self.engine.mark_action_executed("fake_id")
        self.assertFalse(result)

    def test_get_failure_patterns(self):
        """Test getting failure patterns."""
        for _ in range(3):
            self.engine.record_event(
                self._make_event(PillarType.SELF_BUILDING, "failure", "type_a")
            )
        patterns = self.engine.get_failure_patterns()
        self.assertIn("self_building", patterns)

    def test_get_stats(self):
        """Test engine statistics."""
        self.engine.record_event(
            self._make_event(PillarType.SELF_HEALING, "success", "cache_fix")
        )
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_events"], 1)

    def test_no_insight_below_threshold(self):
        """Test that no insights are generated below threshold."""
        for _ in range(2):  # Below threshold of 3
            event = self._make_event(
                PillarType.SELF_BUILDING, "failure", "rare_error"
            )
            insights = self.engine.record_event(event)
        # Should not have generated insights for this category
        rare_insights = [
            i for i in self.engine.insights
            if "rare_error" in i.description
        ]
        self.assertEqual(len(rare_insights), 0)


# =====================================================================
# 5. TRUST DECAY TESTS
# =====================================================================


class TestTrustDecay(unittest.TestCase):
    """Tests for Trust Decay Engine."""

    def setUp(self):
        self.engine = TrustDecayEngine(
            default_half_life=180, trust_floor=0.1, reverification_threshold=0.4
        )

    def test_register_item(self):
        """Test item registration."""
        record = self.engine.register_item("item1", trust_score=0.9)
        self.assertEqual(record.item_id, "item1")
        self.assertEqual(record.current_trust, 0.9)
        self.assertIn("item1", self.engine.records)

    def test_register_item_with_domain(self):
        """Test registration with domain-specific half-life."""
        record = self.engine.register_item(
            "sec_item", trust_score=0.9, domain="security"
        )
        self.assertEqual(record.half_life_days, 60)  # Security is fast-changing

    def test_exponential_decay(self):
        """Test exponential decay model."""
        past = datetime.now(timezone.utc) - timedelta(days=180)
        record = self.engine.register_item(
            "old_item", trust_score=0.8, verified_at=past,
            decay_model=DecayModel.EXPONENTIAL
        )
        result = self.engine.check_decay("old_item")
        self.assertIsNotNone(result)
        self.assertLess(result.new_trust, 0.8)
        self.assertGreater(result.decay_amount, 0)

    def test_linear_decay(self):
        """Test linear decay model."""
        past = datetime.now(timezone.utc) - timedelta(days=90)
        self.engine.register_item(
            "linear_item", trust_score=0.8, verified_at=past,
            decay_model=DecayModel.LINEAR
        )
        result = self.engine.check_decay("linear_item")
        self.assertIsNotNone(result)
        self.assertLess(result.new_trust, 0.8)

    def test_step_decay(self):
        """Test step decay model."""
        past = datetime.now(timezone.utc) - timedelta(days=90)
        self.engine.register_item(
            "step_item", trust_score=0.8, verified_at=past,
            decay_model=DecayModel.STEP
        )
        result = self.engine.check_decay("step_item")
        self.assertIsNotNone(result)
        self.assertLess(result.new_trust, 0.8)

    def test_no_decay_for_recent(self):
        """Test that recently verified items don't decay much."""
        self.engine.register_item("recent_item", trust_score=0.9)
        result = self.engine.check_decay("recent_item")
        self.assertAlmostEqual(result.new_trust, 0.9, places=1)

    def test_decay_respects_floor(self):
        """Test trust floor is respected."""
        very_old = datetime.now(timezone.utc) - timedelta(days=3650)
        self.engine.register_item(
            "ancient_item", trust_score=0.8, verified_at=very_old
        )
        result = self.engine.check_decay("ancient_item")
        self.assertGreaterEqual(result.new_trust, self.engine.trust_floor)

    def test_reverification_scheduled(self):
        """Test that reverification is scheduled for decayed items."""
        old = datetime.now(timezone.utc) - timedelta(days=365)
        self.engine.register_item("stale_item", trust_score=0.5, verified_at=old)
        self.engine.check_decay("stale_item")
        queue = self.engine.get_reverification_queue()
        self.assertGreater(len(queue), 0)

    def test_record_reverification(self):
        """Test recording a reverification result."""
        old = datetime.now(timezone.utc) - timedelta(days=365)
        self.engine.register_item("rv_item", trust_score=0.5, verified_at=old)
        self.engine.check_decay("rv_item")

        record = self.engine.record_reverification("rv_item", 0.85)
        self.assertIsNotNone(record)
        self.assertEqual(record.current_trust, 0.85)
        self.assertEqual(record.verification_count, 1)

    def test_check_all_decay(self):
        """Test checking decay for all items."""
        old = datetime.now(timezone.utc) - timedelta(days=200)
        self.engine.register_item("a", trust_score=0.8, verified_at=old)
        self.engine.register_item("b", trust_score=0.7, verified_at=old)
        results = self.engine.check_all_decay()
        self.assertEqual(len(results), 2)

    def test_check_decay_nonexistent(self):
        """Test decay check for nonexistent item."""
        result = self.engine.check_decay("ghost")
        self.assertIsNone(result)

    def test_urgency_levels(self):
        """Test urgency level calculation."""
        very_old = datetime.now(timezone.utc) - timedelta(days=1000)
        self.engine.register_item("critical_item", trust_score=0.3, verified_at=very_old)
        result = self.engine.check_decay("critical_item")
        self.assertIn(
            result.urgency,
            [VerificationUrgency.CRITICAL, VerificationUrgency.HIGH],
        )

    def test_get_decayed_items(self):
        """Test getting decayed items."""
        old = datetime.now(timezone.utc) - timedelta(days=500)
        self.engine.register_item("decayed", trust_score=0.5, verified_at=old)
        self.engine.check_decay("decayed")
        decayed = self.engine.get_decayed_items()
        self.assertGreater(len(decayed), 0)

    def test_get_stats(self):
        """Test statistics."""
        self.engine.register_item("s1", trust_score=0.9)
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_items"], 1)

    def test_stats_empty(self):
        """Test stats with no data."""
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_items"], 0)

    def test_domain_specific_half_life(self):
        """Test different domains get different half-lives."""
        r1 = self.engine.register_item("math_fact", trust_score=0.9, domain="mathematics")
        r2 = self.engine.register_item("sec_fact", trust_score=0.9, domain="security")
        self.assertGreater(r1.half_life_days, r2.half_life_days)


# =====================================================================
# 6. TRUST THERMOMETER TESTS
# =====================================================================


class TestTrustThermometer(unittest.TestCase):
    """Tests for System-Wide Trust Thermometer."""

    def setUp(self):
        self.thermo = SystemTrustThermometer()

    def test_default_reading(self):
        """Test default reading with no data."""
        reading = self.thermo.read_temperature()
        self.assertEqual(reading.temperature, 0.5)
        self.assertEqual(reading.mode, SystemMode.CAUTIOUS)

    def test_high_trust_aggressive_mode(self):
        """Test that high trust leads to aggressive mode."""
        self.thermo.update_component_score("rag", 0.95)
        self.thermo.update_component_score("ingestion", 0.92)
        self.thermo.update_pillar_score("self_building", 0.90)
        self.thermo.update_pillar_score("self_healing", 0.88)
        self.thermo.update_data_trust(0.90)
        self.thermo.update_recent_performance(0.92)

        reading = self.thermo.read_temperature()
        self.assertGreater(reading.temperature, 0.85)
        self.assertEqual(reading.mode, SystemMode.AGGRESSIVE)

    def test_low_trust_paranoid_mode(self):
        """Test that low trust leads to paranoid mode."""
        self.thermo.update_component_score("rag", 0.1)
        self.thermo.update_pillar_score("self_building", 0.1)
        self.thermo.update_data_trust(0.1)
        self.thermo.update_recent_performance(0.1)

        reading = self.thermo.read_temperature()
        self.assertLess(reading.temperature, 0.3)
        self.assertEqual(reading.mode, SystemMode.PARANOID)

    def test_verification_multiplier_high_trust(self):
        """Test verification multiplier is low when trust is high."""
        self.thermo.update_component_score("rag", 0.95)
        self.thermo.update_pillar_score("self_building", 0.95)
        self.thermo.update_data_trust(0.95)
        self.thermo.update_recent_performance(0.95)

        reading = self.thermo.read_temperature()
        self.assertLess(reading.verification_multiplier, 1.0)

    def test_verification_multiplier_low_trust(self):
        """Test verification multiplier is high when trust is low."""
        self.thermo.update_component_score("rag", 0.1)
        self.thermo.update_pillar_score("self_building", 0.1)
        self.thermo.update_data_trust(0.1)
        self.thermo.update_recent_performance(0.1)

        reading = self.thermo.read_temperature()
        self.assertGreater(reading.verification_multiplier, 1.5)

    def test_autonomy_level_proportional(self):
        """Test autonomy level scales with temperature."""
        self.thermo.update_component_score("rag", 0.9)
        self.thermo.update_pillar_score("self_building", 0.9)
        self.thermo.update_data_trust(0.9)
        self.thermo.update_recent_performance(0.9)
        high_reading = self.thermo.read_temperature()

        thermo2 = SystemTrustThermometer()
        thermo2.update_component_score("rag", 0.2)
        thermo2.update_pillar_score("self_building", 0.2)
        thermo2.update_data_trust(0.2)
        thermo2.update_recent_performance(0.2)
        low_reading = thermo2.read_temperature()

        self.assertGreater(high_reading.autonomy_level, low_reading.autonomy_level)

    def test_temperature_trend_rising(self):
        """Test trend detection for rising temperature."""
        for i in range(10):
            score = 0.3 + (i * 0.05)
            self.thermo.update_component_score("rag", score)
            self.thermo.update_pillar_score("self_building", score)
            self.thermo.update_data_trust(score)
            self.thermo.update_recent_performance(score)
            self.thermo.read_temperature()

        trend = self.thermo.get_temperature_trend()
        self.assertEqual(trend, "rising")

    def test_temperature_trend_stable(self):
        """Test trend detection for stable temperature."""
        for _ in range(10):
            self.thermo.update_component_score("rag", 0.5)
            self.thermo.update_pillar_score("self_building", 0.5)
            self.thermo.update_data_trust(0.5)
            self.thermo.update_recent_performance(0.5)
            self.thermo.read_temperature()

        trend = self.thermo.get_temperature_trend()
        self.assertEqual(trend, "stable")

    def test_get_current_mode(self):
        """Test getting current mode."""
        mode = self.thermo.get_current_mode()
        self.assertEqual(mode, SystemMode.CAUTIOUS)  # Default

    def test_get_current_temperature(self):
        """Test getting current temperature."""
        temp = self.thermo.get_current_temperature()
        self.assertEqual(temp, 0.5)  # Default

    def test_get_stats(self):
        """Test statistics."""
        self.thermo.read_temperature()
        stats = self.thermo.get_stats()
        self.assertIn("current_temperature", stats)
        self.assertIn("current_mode", stats)
        self.assertEqual(stats["total_readings"], 1)

    def test_stats_empty(self):
        """Test stats with no readings."""
        stats = self.thermo.get_stats()
        self.assertEqual(stats["total_readings"], 0)

    def test_custom_config(self):
        """Test with custom configuration."""
        config = ThermometerConfig(
            aggressive_threshold=0.95,
            conservative_threshold=0.20,
        )
        thermo = SystemTrustThermometer(config=config)
        thermo.update_component_score("rag", 0.9)
        thermo.update_pillar_score("self_building", 0.9)
        thermo.update_data_trust(0.9)
        thermo.update_recent_performance(0.9)
        reading = thermo.read_temperature()
        self.assertEqual(reading.mode, SystemMode.CONFIDENT)

    def test_multiple_components(self):
        """Test with many components and pillars."""
        for i in range(5):
            self.thermo.update_component_score(f"comp_{i}", 0.7 + i * 0.02)
        for p in ["building", "healing", "learning", "governing"]:
            self.thermo.update_pillar_score(p, 0.75)
        self.thermo.update_data_trust(0.8)
        self.thermo.update_recent_performance(0.7)

        reading = self.thermo.read_temperature()
        self.assertGreater(reading.temperature, 0.5)

    def test_mode_boundaries(self):
        """Test mode transitions at exact boundaries."""
        config = ThermometerConfig()
        thermo = SystemTrustThermometer(config=config)

        # Set ALL inputs to confident threshold so weighted avg = threshold
        thermo.update_component_score("test", config.confident_threshold)
        thermo.update_pillar_score("test", config.confident_threshold)
        thermo.update_data_trust(config.confident_threshold)
        thermo.update_recent_performance(config.confident_threshold)
        reading = thermo.read_temperature()
        self.assertEqual(reading.mode, SystemMode.CONFIDENT)


# =====================================================================
# 7. META-LEARNING ON VERIFICATION TESTS
# =====================================================================


class TestMetaVerificationLearner(unittest.TestCase):
    """Tests for Meta-Learning on Verification."""

    def setUp(self):
        self.learner = MetaVerificationLearner()

    def test_record_attempt(self):
        """Test recording a verification attempt."""
        attempt = self.learner.record_attempt(
            strategy="github_check",
            data_type="code",
            domain="python",
            success=True,
            confidence_before=0.5,
            confidence_after=0.8,
            time_ms=150,
        )
        self.assertIsNotNone(attempt.attempt_id)
        self.assertEqual(
            self.learner.profiles["github_check"].total_attempts, 1
        )

    def test_success_rate_calculation(self):
        """Test success rate is calculated correctly."""
        for i in range(10):
            self.learner.record_attempt(
                strategy="web_cross_reference",
                data_type="factual",
                domain="general",
                success=(i < 7),
                confidence_before=0.5,
                confidence_after=0.6 if i < 7 else 0.4,
                time_ms=200,
            )
        rate = self.learner.profiles["web_cross_reference"].success_rate
        self.assertAlmostEqual(rate, 0.7, places=1)

    def test_recommend_strategy(self):
        """Test strategy recommendation."""
        # Build history
        for _ in range(5):
            self.learner.record_attempt(
                strategy="github_check", data_type="code", domain="python",
                success=True, confidence_before=0.5, confidence_after=0.9,
                time_ms=100,
            )
        for _ in range(5):
            self.learner.record_attempt(
                strategy="web_cross_reference", data_type="code", domain="python",
                success=False, confidence_before=0.5, confidence_after=0.4,
                time_ms=300,
            )

        rec = self.learner.recommend_strategy("code", domain="python")
        self.assertEqual(rec.strategy, "github_check")
        self.assertGreater(rec.expected_success_rate, 0.5)

    def test_recommend_with_no_data(self):
        """Test recommendation with no historical data."""
        rec = self.learner.recommend_strategy("code", domain="python")
        self.assertIsNotNone(rec.strategy)
        self.assertEqual(rec.confidence, 0.3)  # Exploration bonus

    def test_domain_specific_performance(self):
        """Test domain-specific tracking."""
        for _ in range(5):
            self.learner.record_attempt(
                strategy="knowledge_base_lookup",
                data_type="domain_specific",
                domain="python",
                success=True,
                confidence_before=0.5,
                confidence_after=0.85,
                time_ms=50,
            )
        for _ in range(5):
            self.learner.record_attempt(
                strategy="knowledge_base_lookup",
                data_type="domain_specific",
                domain="legal",
                success=False,
                confidence_before=0.5,
                confidence_after=0.4,
                time_ms=50,
            )

        profile = self.learner.profiles["knowledge_base_lookup"]
        self.assertEqual(profile.domain_performance["python"]["rate"], 1.0)
        self.assertEqual(profile.domain_performance["legal"]["rate"], 0.0)

    def test_data_type_performance(self):
        """Test data-type-specific tracking."""
        for _ in range(5):
            self.learner.record_attempt(
                strategy="code_execution",
                data_type="code",
                domain=None,
                success=True,
                confidence_before=0.5,
                confidence_after=0.9,
                time_ms=500,
            )
        profile = self.learner.profiles["code_execution"]
        self.assertEqual(profile.data_type_performance["code"]["rate"], 1.0)

    def test_time_and_cost_tracking(self):
        """Test average time and cost tracking."""
        for _ in range(4):
            self.learner.record_attempt(
                strategy="web_cross_reference",
                data_type="factual",
                domain=None,
                success=True,
                confidence_before=0.5,
                confidence_after=0.7,
                time_ms=200,
                cost=0.01,
            )
        profile = self.learner.profiles["web_cross_reference"]
        self.assertAlmostEqual(profile.avg_time_ms, 200, places=0)
        self.assertAlmostEqual(profile.avg_cost, 0.01, places=4)

    def test_strategy_ranking(self):
        """Test strategy ranking."""
        for _ in range(5):
            self.learner.record_attempt(
                strategy="github_check", data_type="code", domain=None,
                success=True, confidence_before=0.5, confidence_after=0.9,
                time_ms=100,
            )
        for _ in range(5):
            self.learner.record_attempt(
                strategy="web_cross_reference", data_type="code", domain=None,
                success=False, confidence_before=0.5, confidence_after=0.4,
                time_ms=200,
            )

        ranking = self.learner.get_strategy_ranking()
        self.assertEqual(ranking[0][0], "github_check")

    def test_time_constraint(self):
        """Test recommendation with time constraint penalizes slow strategies."""
        for _ in range(5):
            self.learner.record_attempt(
                strategy="code_execution", data_type="code", domain=None,
                success=True, confidence_before=0.5, confidence_after=0.95,
                time_ms=5000,
            )
        # Also train a fast strategy so it beats the penalized slow one
        for _ in range(5):
            self.learner.record_attempt(
                strategy="github_check", data_type="code", domain=None,
                success=True, confidence_before=0.5, confidence_after=0.85,
                time_ms=50,
            )
        rec = self.learner.recommend_strategy("code", max_time_ms=100)
        self.assertEqual(rec.strategy, "github_check")

    def test_get_stats(self):
        """Test statistics."""
        self.learner.record_attempt(
            strategy="github_check", data_type="code", domain="python",
            success=True, confidence_before=0.5, confidence_after=0.8,
            time_ms=100,
        )
        stats = self.learner.get_stats()
        self.assertEqual(stats["total_attempts"], 1)
        self.assertIn("strategies", stats)

    def test_reliability_score(self):
        """Test reliability score calculation."""
        for _ in range(10):
            self.learner.record_attempt(
                strategy="semantic_similarity",
                data_type="factual",
                domain=None,
                success=True,
                confidence_before=0.4,
                confidence_after=0.8,
                time_ms=50,
            )
        profile = self.learner.profiles["semantic_similarity"]
        self.assertGreater(profile.reliability_score, 0.5)


# =====================================================================
# 8. PILLAR TRACKER TESTS
# =====================================================================


class TestPillarTracker(unittest.TestCase):
    """Tests for Pillar Tracking System."""

    def setUp(self):
        self.tracker = PillarTracker()

    def test_record_event(self):
        """Test recording a pillar event."""
        event = self.tracker.record_event(
            pillar=Pillar.SELF_BUILDING,
            event_type="success",
            category="code_generation",
            description="Generated new module",
        )
        self.assertIsNotNone(event.event_id)
        self.assertEqual(event.pillar, Pillar.SELF_BUILDING)

    def test_record_success(self):
        """Test convenience success recording."""
        event = self.tracker.record_success(
            Pillar.SELF_HEALING, "connection_reset", "Reset DB connection"
        )
        self.assertEqual(event.event_type, "success")

    def test_record_failure(self):
        """Test convenience failure recording."""
        event = self.tracker.record_failure(
            Pillar.SELF_LEARNING, "knowledge_gap", "Missing ML knowledge"
        )
        self.assertEqual(event.event_type, "failure")
        self.assertEqual(event.severity, EventSeverity.ERROR)

    def test_success_rate(self):
        """Test success rate calculation."""
        for _ in range(7):
            self.tracker.record_success(
                Pillar.SELF_BUILDING, "test", "success"
            )
        for _ in range(3):
            self.tracker.record_failure(
                Pillar.SELF_BUILDING, "test", "failure"
            )
        rate = self.tracker.get_pillar_success_rate(Pillar.SELF_BUILDING)
        self.assertAlmostEqual(rate, 0.7, places=1)

    def test_kpi_tracking(self):
        """Test KPI tracking."""
        for _ in range(5):
            self.tracker.record_success(
                Pillar.SELF_HEALING, "cache_clear", "Cleared cache"
            )
        kpi = self.tracker.get_pillar_kpi(Pillar.SELF_HEALING)
        self.assertEqual(kpi.total_events, 5)
        self.assertEqual(kpi.successes, 5)
        self.assertEqual(kpi.success_rate, 1.0)

    def test_streak_tracking(self):
        """Test streak tracking."""
        for _ in range(5):
            self.tracker.record_success(
                Pillar.SELF_BUILDING, "deploy", "Deploy success"
            )
        kpi = self.tracker.get_pillar_kpi(Pillar.SELF_BUILDING)
        self.assertEqual(kpi.streak_type, "success")
        self.assertEqual(kpi.streak_count, 5)

    def test_streak_reset(self):
        """Test streak resets on type change."""
        self.tracker.record_success(
            Pillar.SELF_BUILDING, "deploy", "success"
        )
        self.tracker.record_success(
            Pillar.SELF_BUILDING, "deploy", "success"
        )
        self.tracker.record_failure(
            Pillar.SELF_BUILDING, "deploy", "failure"
        )
        kpi = self.tracker.get_pillar_kpi(Pillar.SELF_BUILDING)
        self.assertEqual(kpi.streak_type, "failure")
        self.assertEqual(kpi.streak_count, 1)

    def test_category_stats(self):
        """Test per-category statistics."""
        for _ in range(3):
            self.tracker.record_success(
                Pillar.SELF_HEALING, "connection_reset", "Reset"
            )
        for _ in range(2):
            self.tracker.record_failure(
                Pillar.SELF_HEALING, "connection_reset", "Failed"
            )
        kpi = self.tracker.get_pillar_kpi(Pillar.SELF_HEALING)
        cat = kpi.categories["connection_reset"]
        self.assertEqual(cat["success"], 3)
        self.assertEqual(cat["failure"], 2)
        self.assertEqual(cat["total"], 5)

    def test_duration_tracking(self):
        """Test duration tracking."""
        self.tracker.record_event(
            Pillar.SELF_LEARNING, "success", "ingestion",
            "Ingested docs", duration_ms=1500.0,
        )
        self.tracker.record_event(
            Pillar.SELF_LEARNING, "success", "ingestion",
            "Ingested more", duration_ms=500.0,
        )
        kpi = self.tracker.get_pillar_kpi(Pillar.SELF_LEARNING)
        self.assertAlmostEqual(kpi.avg_duration_ms, 1000.0, places=0)

    def test_get_pillar_events(self):
        """Test getting events for a pillar."""
        self.tracker.record_success(
            Pillar.SELF_GOVERNING, "policy", "Applied policy"
        )
        events = self.tracker.get_pillar_events(Pillar.SELF_GOVERNING)
        self.assertEqual(len(events), 1)

    def test_get_pillar_events_filtered(self):
        """Test filtered event retrieval."""
        self.tracker.record_success(Pillar.SELF_BUILDING, "test", "s1")
        self.tracker.record_failure(Pillar.SELF_BUILDING, "test", "f1")
        failures = self.tracker.get_pillar_events(
            Pillar.SELF_BUILDING, event_type="failure"
        )
        self.assertEqual(len(failures), 1)

    def test_report(self):
        """Test comprehensive report."""
        for _ in range(5):
            self.tracker.record_success(Pillar.SELF_BUILDING, "code", "ok")
        for _ in range(5):
            self.tracker.record_failure(Pillar.SELF_HEALING, "fix", "fail")

        report = self.tracker.get_report()
        self.assertEqual(report.strongest_pillar, Pillar.SELF_BUILDING)
        self.assertEqual(report.weakest_pillar, Pillar.SELF_HEALING)
        self.assertEqual(report.total_events, 10)

    def test_report_empty(self):
        """Test report with no data."""
        report = self.tracker.get_report()
        self.assertEqual(report.total_events, 0)
        self.assertIsNone(report.strongest_pillar)

    def test_trend_improving(self):
        """Test improving trend detection."""
        for _ in range(10):
            self.tracker.record_failure(Pillar.SELF_BUILDING, "test", "fail")
        for _ in range(10):
            self.tracker.record_success(Pillar.SELF_BUILDING, "test", "pass")
        trend = self.tracker.get_pillar_trend(Pillar.SELF_BUILDING)
        self.assertEqual(trend, "improving")

    def test_trend_insufficient_data(self):
        """Test trend with insufficient data."""
        self.tracker.record_success(Pillar.SELF_BUILDING, "test", "pass")
        trend = self.tracker.get_pillar_trend(Pillar.SELF_BUILDING)
        self.assertEqual(trend, "insufficient_data")

    def test_get_stats(self):
        """Test statistics output."""
        self.tracker.record_success(Pillar.SELF_BUILDING, "test", "ok")
        stats = self.tracker.get_stats()
        self.assertIn("overall_health", stats)
        self.assertIn("pillars", stats)

    def test_all_four_pillars(self):
        """Test that all four pillars are tracked independently."""
        for pillar in Pillar:
            self.tracker.record_success(pillar, "test", f"{pillar.value} ok")

        for pillar in Pillar:
            kpi = self.tracker.get_pillar_kpi(pillar)
            self.assertEqual(kpi.total_events, 1)


# =====================================================================
# 9. VERIFICATION PIPELINE TESTS
# =====================================================================


class TestVerificationPipeline(unittest.TestCase):
    """Tests for Verification Pipeline."""

    def setUp(self):
        self.pipeline = VerificationPipeline()

    def test_verify_basic(self):
        """Test basic verification."""
        result = self.pipeline.verify(
            data="Python uses indentation for code blocks.",
            data_type="factual",
            domain="python",
            current_trust=0.5,
        )
        self.assertIsNotNone(result.request_id)
        self.assertIsInstance(result.final_trust, float)

    def test_verification_level_determination(self):
        """Test automatic verification level determination."""
        # High trust + high competence = minimal
        level = self.pipeline.determine_verification_level(0.9, 0.9, 1.0)
        self.assertEqual(level, VerificationLevel.MINIMAL)

        # Low trust + low competence = exhaustive
        level = self.pipeline.determine_verification_level(0.1, 0.1, 1.0)
        self.assertEqual(level, VerificationLevel.EXHAUSTIVE)

    def test_manual_verification_level(self):
        """Test with manual verification level."""
        result = self.pipeline.verify(
            data="Test data for manual level.",
            data_type="code",
            verification_level=VerificationLevel.EXHAUSTIVE,
        )
        self.assertEqual(result.verification_level, VerificationLevel.EXHAUSTIVE)

    def test_pass_threshold(self):
        """Test pass/fail based on threshold."""
        result = self.pipeline.verify(
            data="Well-structured factual content with proper citations and "
                 "references to authoritative sources.",
            data_type="factual",
            current_trust=0.8,
        )
        self.assertTrue(result.passed)

    def test_human_review_flagging(self):
        """Test human review is flagged for low trust."""
        pipeline = VerificationPipeline(human_review_threshold=0.9)
        result = pipeline.verify(
            data="Some data with questionable origin.",
            data_type="factual",
            current_trust=0.3,
        )
        self.assertTrue(result.needs_human_review)

    def test_strategies_selected_by_type(self):
        """Test that strategies are selected based on data type."""
        result = self.pipeline.verify(
            data="def hello(): print('world')",
            data_type="code",
            current_trust=0.5,
            verification_level=VerificationLevel.STANDARD,
        )
        self.assertGreater(len(result.strategies_used), 0)

    def test_adversarial_test_in_thorough(self):
        """Test adversarial testing is included in thorough level."""
        result = self.pipeline.verify(
            data="Some data requiring thorough verification.",
            data_type="factual",
            verification_level=VerificationLevel.THOROUGH,
        )
        has_adversarial = any(
            s == "adversarial_self_test" for s in result.strategies_used
        )
        self.assertTrue(has_adversarial)

    def test_recommendations_generated(self):
        """Test that recommendations are generated."""
        result = self.pipeline.verify(
            data="Test content.", data_type="factual", current_trust=0.5
        )
        self.assertGreater(len(result.recommendations), 0)

    def test_verification_log(self):
        """Test verification log."""
        self.pipeline.verify(
            data="Log test.", data_type="factual", current_trust=0.5
        )
        log = self.pipeline.get_verification_log()
        self.assertEqual(len(log), 1)

    def test_get_stats(self):
        """Test pipeline statistics."""
        self.pipeline.verify(
            data="Stats test.", data_type="factual", current_trust=0.5
        )
        stats = self.pipeline.get_stats()
        self.assertEqual(stats["total_verifications"], 1)
        self.assertIn("pass_rate", stats)

    def test_stats_empty(self):
        """Test stats with no data."""
        stats = self.pipeline.get_stats()
        self.assertEqual(stats["total_verifications"], 0)

    def test_thermometer_multiplier_effect(self):
        """Test that thermometer multiplier affects verification level."""
        # Normal
        level_normal = self.pipeline.determine_verification_level(0.5, 0.5, 1.0)
        # High multiplier (low system trust)
        level_high = self.pipeline.determine_verification_level(0.5, 0.5, 3.0)
        # Higher multiplier should give more thorough level
        level_values = list(VerificationLevel)
        self.assertGreaterEqual(
            level_values.index(level_high),
            level_values.index(level_normal),
        )

    def test_register_strategy_handler(self):
        """Test registering a custom strategy handler."""
        def custom_handler(request):
            from advanced_trust.verification_pipeline import VerificationStepResult
            return VerificationStepResult(
                strategy=VerificationStrategy.KNOWLEDGE_BASE_LOOKUP,
                success=True,
                confidence_delta=0.1,
                details={"custom": True},
            )

        self.pipeline.register_strategy_handler(
            VerificationStrategy.KNOWLEDGE_BASE_LOOKUP, custom_handler
        )
        result = self.pipeline.verify(
            data="Custom handler test.", data_type="domain_specific",
            verification_level=VerificationLevel.MINIMAL,
        )
        self.assertIn("knowledge_base_lookup", result.strategies_used)

    def test_different_data_types(self):
        """Test pipeline works with different data types."""
        for data_type in ["code", "factual", "domain_specific", "unknown"]:
            result = self.pipeline.verify(
                data=f"Test for {data_type} verification.",
                data_type=data_type,
                current_trust=0.5,
            )
            self.assertIsNotNone(result.request_id)


# =====================================================================
# 10. INTEGRATION TESTS
# =====================================================================


class TestAdvancedTrustIntegration(unittest.TestCase):
    """Integration tests across all advanced trust components."""

    def test_cascade_feeds_thermometer(self):
        """Test cascade results feeding into thermometer."""
        cascade = ConfidenceCascadeEngine()
        thermo = SystemTrustThermometer()

        cascade.register_node("src", trust_score=0.9)
        cascade.register_node("d1", trust_score=0.8, parent_ids=["src"])
        cascade.register_node("d2", trust_score=0.7, parent_ids=["src"])

        # Cascade downgrade
        cascade.cascade_trust_downgrade("src", 0.3)

        # Feed cascade stats into thermometer
        avg_trust = cascade.get_stats()["average_trust"]
        thermo.update_data_trust(avg_trust)

        reading = thermo.read_temperature()
        self.assertLess(reading.temperature, 0.6)

    def test_competence_affects_verification(self):
        """Test competence boundaries affect verification pipeline."""
        comp = CompetenceBoundaryTracker(min_attempts=5)
        pipeline = VerificationPipeline()

        # Build low competence
        for _ in range(10):
            comp.record_outcome("legal", success=False)
        competence = comp.get_verification_intensity("legal")

        # Use competence to determine verification level
        level = pipeline.determine_verification_level(
            current_trust=0.5,
            domain_competence=1.0 - competence,
            thermometer_multiplier=1.0,
        )
        self.assertIn(
            level,
            [VerificationLevel.THOROUGH, VerificationLevel.EXHAUSTIVE],
        )

    def test_decay_triggers_reverification(self):
        """Test trust decay triggering re-verification in pipeline."""
        decay = TrustDecayEngine()
        pipeline = VerificationPipeline()

        old = datetime.now(timezone.utc) - timedelta(days=365)
        decay.register_item("stale_fact", trust_score=0.6, verified_at=old)
        result = decay.check_decay("stale_fact")

        if result and result.needs_reverification:
            vresult = pipeline.verify(
                data="The stale fact content.",
                data_type="factual",
                current_trust=result.new_trust,
            )
            self.assertIsNotNone(vresult.final_trust)

    def test_meta_learner_recommends_for_pipeline(self):
        """Test meta-learner recommending strategy for pipeline."""
        learner = MetaVerificationLearner()

        for _ in range(5):
            learner.record_attempt(
                strategy="github_check", data_type="code", domain="python",
                success=True, confidence_before=0.5, confidence_after=0.9,
                time_ms=100,
            )

        rec = learner.recommend_strategy("code", domain="python")
        self.assertEqual(rec.strategy, "github_check")

    def test_pillar_tracker_feeds_thermometer(self):
        """Test pillar tracker feeding into thermometer."""
        tracker = PillarTracker()
        thermo = SystemTrustThermometer()

        for _ in range(10):
            tracker.record_success(Pillar.SELF_BUILDING, "test", "ok")
        for _ in range(10):
            tracker.record_success(Pillar.SELF_HEALING, "fix", "ok")

        for pillar in Pillar:
            rate = tracker.get_pillar_success_rate(pillar)
            thermo.update_pillar_score(pillar.value, rate)

        reading = thermo.read_temperature()
        self.assertGreaterEqual(reading.temperature, 0.0)

    def test_cross_pillar_actions_track_in_pillar_tracker(self):
        """Test cross-pillar insights can feed pillar events."""
        cpl = CrossPillarLearningEngine(pattern_threshold=3)
        tracker = PillarTracker()

        for _ in range(4):
            event = CPLPillarEvent(
                event_id=f"evt-{id(cpl)}",
                pillar=PillarType.SELF_BUILDING,
                event_type="failure",
                category="deploy",
                description="Deploy failed",
            )
            cpl.record_event(event)

        # Record the cross-pillar insight as a pillar event
        insights = cpl.get_insights_for_pillar(PillarType.SELF_HEALING)
        for insight in insights:
            tracker.record_event(
                pillar=Pillar.SELF_HEALING,
                event_type="info",
                category="cross_pillar_insight",
                description=insight.description,
            )

        events = tracker.get_pillar_events(Pillar.SELF_HEALING)
        self.assertGreater(len(events), 0)

    def test_full_pipeline_flow(self):
        """Test the complete flow: data -> cascade -> decay -> test -> verify."""
        cascade = ConfidenceCascadeEngine()
        decay = TrustDecayEngine()
        tester = AdversarialSelfTester()
        pipeline = VerificationPipeline()
        thermo = SystemTrustThermometer()

        # Step 1: Register data in cascade
        cascade.register_node("fact1", trust_score=0.8, source_id="wiki")

        # Step 2: Register for decay
        decay.register_item("fact1", trust_score=0.8)

        # Step 3: Check decay
        decay_result = decay.check_decay("fact1")
        current_trust = decay_result.new_trust if decay_result else 0.8

        # Step 4: Adversarial test
        test_result = tester.test_retrieval_result(
            content="A factual statement about something verifiable.",
            source="wiki",
            trust_score=current_trust,
        )
        current_trust = test_result.adjusted_trust

        # Step 5: Run through verification pipeline
        verify_result = pipeline.verify(
            data="A factual statement about something verifiable.",
            data_type="factual",
            current_trust=current_trust,
        )

        # Step 6: Update thermometer
        thermo.update_data_trust(verify_result.final_trust)
        reading = thermo.read_temperature()

        self.assertIsNotNone(reading.temperature)
        self.assertIsNotNone(reading.mode)

    def test_adversarial_with_cascade_downgraded_data(self):
        """Test adversarial testing on cascade-downgraded data."""
        cascade = ConfidenceCascadeEngine()
        tester = AdversarialSelfTester()

        cascade.register_node("src", trust_score=0.9)
        cascade.register_node("derived", trust_score=0.8, parent_ids=["src"])

        # Downgrade source
        cascade.cascade_trust_downgrade("src", 0.2)
        derived_trust = cascade.get_node_trust("derived")

        # Test derived data
        result = tester.test_retrieval_result(
            content="Data derived from unreliable source.",
            source="derived_source",
            trust_score=derived_trust,
        )
        self.assertIsNotNone(result.adjusted_trust)


# =====================================================================
# RUN ALL TESTS
# =====================================================================


if __name__ == "__main__":
    unittest.main(verbosity=2)
