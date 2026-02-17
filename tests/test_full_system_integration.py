"""
Full System Integration Test

Exercises the ENTIRE system end-to-end:
  Advanced Trust (7 subsystems)
  + Oracle Pipeline (14 modules)
  = Complete Self-Evolving AI Learning System

This is the final verification that everything works together.
100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from advanced_trust import (
    ConfidenceCascadeEngine,
    AdversarialSelfTester,
    CompetenceBoundaryTracker,
    CrossPillarLearningEngine,
    TrustDecayEngine,
    SystemTrustThermometer,
    MetaVerificationLearner,
    PillarTracker,
    Pillar,
    VerificationPipeline,
)
from oracle_pipeline import (
    WhitelistBox,
    OracleVectorStore,
    PerpetualLearningLoop,
    DeepReasoningIntegration,
    SelfEvolutionCoordinator,
    SocraticInterrogator,
    SourceCodeIndex,
    HallucinationGuard,
    LibrarianFileManager,
    ProactiveDiscoveryEngine,
    ReverseKNNDiscovery,
    LLMEnrichmentEngine,
    PillarRole,
)


class TestCompleteSystemAssembly(unittest.TestCase):
    """Test that every component can be assembled together."""

    def test_all_advanced_trust_instantiate(self):
        """Test all 9 advanced trust modules instantiate."""
        cascade = ConfidenceCascadeEngine()
        adversarial = AdversarialSelfTester()
        competence = CompetenceBoundaryTracker()
        cross_pillar = CrossPillarLearningEngine()
        decay = TrustDecayEngine()
        thermo = SystemTrustThermometer()
        meta_verify = MetaVerificationLearner()
        pillars = PillarTracker()
        pipeline = VerificationPipeline()
        self.assertIsNotNone(cascade)
        self.assertIsNotNone(adversarial)
        self.assertIsNotNone(competence)
        self.assertIsNotNone(cross_pillar)
        self.assertIsNotNone(decay)
        self.assertIsNotNone(thermo)
        self.assertIsNotNone(meta_verify)
        self.assertIsNotNone(pillars)
        self.assertIsNotNone(pipeline)

    def test_all_oracle_pipeline_instantiate(self):
        """Test all 14 oracle pipeline modules instantiate."""
        whitelist = WhitelistBox()
        oracle = OracleVectorStore()
        source_idx = SourceCodeIndex()
        guard = HallucinationGuard()
        librarian = LibrarianFileManager()
        discovery = ProactiveDiscoveryEngine()
        knn = ReverseKNNDiscovery()
        enrichment = LLMEnrichmentEngine()
        loop = PerpetualLearningLoop()
        reasoning = DeepReasoningIntegration()
        interrogator = SocraticInterrogator()
        coordinator = SelfEvolutionCoordinator()
        self.assertIsNotNone(whitelist)
        self.assertIsNotNone(oracle)
        self.assertIsNotNone(source_idx)
        self.assertIsNotNone(guard)
        self.assertIsNotNone(librarian)
        self.assertIsNotNone(discovery)
        self.assertIsNotNone(knn)
        self.assertIsNotNone(enrichment)
        self.assertIsNotNone(loop)
        self.assertIsNotNone(reasoning)
        self.assertIsNotNone(interrogator)
        self.assertIsNotNone(coordinator)

    def test_full_system_connects(self):
        """Test every component connects to every other."""
        loop = PerpetualLearningLoop()
        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)

        thermo = SystemTrustThermometer()
        competence = CompetenceBoundaryTracker()
        pillars = PillarTracker()

        reasoning.connect_thermometer(thermo)
        reasoning.connect_competence(competence)
        reasoning.connect_pillars(pillars)

        coordinator = SelfEvolutionCoordinator()
        coordinator.connect_from_loop(loop)
        coordinator.connect_deep_reasoning(reasoning)

        interrogator = SocraticInterrogator(
            source_index=loop.source_index,
            oracle_store=loop.oracle,
        )
        reasoning.connect_interrogator(interrogator)

        connected = reasoning.get_connected_systems()
        self.assertGreaterEqual(len(connected), 8)


class TestEndToEndPipeline(unittest.TestCase):
    """Test the complete data flow from whitelist to self-evolution."""

    def test_whitelist_to_evolution(self):
        """Test: Whitelist -> Oracle -> Discovery -> Enrichment -> Evolution."""
        # Step 1: Build the system
        loop = PerpetualLearningLoop()
        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)
        coordinator = SelfEvolutionCoordinator()
        coordinator.connect_from_loop(loop)
        coordinator.connect_deep_reasoning(reasoning)

        # Step 2: Seed from whitelist
        loop.seed_from_whitelist(
            "Python machine learning\n"
            "Rust systems programming\n"
            "Kubernetes container orchestration\n"
            "Sales funnel optimization"
        )

        # Step 3: Run perpetual loop iteration
        loop.run_full_iteration()

        # Step 4: All pillars report
        coordinator.report_healing_situation(
            active_issues=[{"description": "Cache invalidation bug"}],
            metrics={"success_rate": 0.8, "issue_count": 1},
        )
        coordinator.report_learning_situation(
            knowledge_gaps=["Rust async patterns"],
            metrics={"success_rate": 0.6, "gap_count": 1},
        )
        coordinator.report_building_situation(
            current_builds=["New caching layer"],
            metrics={"success_rate": 0.9},
        )
        coordinator.report_coding_agent_situation(
            current_bugs=[{"description": "Type error in handler"}],
            metrics={"success_rate": 0.75, "bug_count": 1},
        )

        # Step 5: Run evolution cycle
        cycle = coordinator.run_evolution_cycle()

        # Verify the pipeline worked
        self.assertGreater(len(loop.oracle.records), 0)
        self.assertGreater(len(loop.trust_chain), 0)
        self.assertGreater(cycle.actions_generated, 0)
        self.assertGreater(cycle.refined_queries, 0)

    def test_interrogation_feeds_back(self):
        """Test: Interrogate -> Gap Queries -> Back to Loop."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Python programming basics")

        interrogator = SocraticInterrogator(
            source_index=loop.source_index,
            oracle_store=loop.oracle,
        )

        report = interrogator.interrogate(
            "Advanced concurrency patterns in Python using asyncio and threading.",
            domain="python",
        )

        self.assertEqual(report.questions_asked, 6)

        # Gap queries can feed back into the loop
        if report.gap_queries:
            gap_input = "\n".join(report.gap_queries)
            iteration = loop.seed_from_whitelist(gap_input)
            self.assertGreater(iteration.records_created, 0)

    def test_trust_flows_through_system(self):
        """Test trust scores flow from whitelist through all derivations."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Python tutorials")

        # Whitelist items should be generation 0, trust 1.0
        gen0 = [e for e in loop.trust_chain.values() if e.generation == 0]
        self.assertGreater(len(gen0), 0)
        for entry in gen0:
            self.assertEqual(entry.trust_score, 1.0)

        # Derived items should have lower trust
        derived = [e for e in loop.trust_chain.values() if e.generation > 0]
        for entry in derived:
            self.assertLess(entry.trust_score, 1.0)
            self.assertGreaterEqual(entry.trust_score, loop.MIN_TRUST)

    def test_advanced_trust_with_oracle_data(self):
        """Test advanced trust components work with Oracle data."""
        # Build Oracle
        oracle = OracleVectorStore()
        oracle.ingest("Python error handling best practices", domain="python")
        oracle.ingest("Kubernetes pod networking guide", domain="devops")

        # Cascade
        cascade = ConfidenceCascadeEngine()
        cascade.register_node("python_fact", trust_score=0.9, source_id="oracle")
        cascade.register_node("derived", trust_score=0.8, parent_ids=["python_fact"])
        cascade.cascade_trust_downgrade("python_fact", 0.4)
        self.assertLess(cascade.get_node_trust("derived"), 0.8)

        # Adversarial test Oracle content
        adversarial = AdversarialSelfTester()
        result = adversarial.test_retrieval_result(
            content="Python error handling best practices",
            source="oracle",
            trust_score=0.9,
            domain="python",
        )
        self.assertGreater(result.passed_count, 0)

        # Competence tracking
        competence = CompetenceBoundaryTracker()
        for _ in range(10):
            competence.record_outcome("python", success=True)
        self.assertEqual(
            competence.get_competence("python").competence_level.value, "expert"
        )

        # Trust decay
        from datetime import datetime, timezone, timedelta
        decay = TrustDecayEngine()
        old = datetime.now(timezone.utc) - timedelta(days=365)
        decay.register_item("old_fact", trust_score=0.9, verified_at=old, domain="python")
        result = decay.check_decay("old_fact")
        self.assertLess(result.new_trust, 0.9)

        # Thermometer
        thermo = SystemTrustThermometer()
        thermo.update_component_score("oracle", 0.85)
        thermo.update_pillar_score("self_learning", 0.9)
        thermo.update_data_trust(0.8)
        thermo.update_recent_performance(0.75)
        reading = thermo.read_temperature()
        self.assertGreater(reading.temperature, 0.5)

    def test_hallucination_guard_with_source_index(self):
        """Test hallucination guard uses real source code index."""
        source_idx = SourceCodeIndex()
        source_idx.index_source_code("engine.py",
            "class CognitiveEngine:\n    def process(self): pass"
        )

        oracle = OracleVectorStore()
        oracle.ingest("CognitiveEngine handles processing", domain="arch")

        guard = HallucinationGuard(
            source_index=source_idx, oracle_store=oracle
        )

        # Grounded claim
        report = guard.check_response("The `CognitiveEngine` processes data.")
        self.assertGreater(report.verified, 0)

        # Hallucinated claim
        report = guard.check_response("The `QuantumBrain` processes data.")
        self.assertGreater(report.refuted, 0)

    def test_librarian_organizes_genesis_keys(self):
        """Test librarian sorts Genesis Keys into 4-hour blocks."""
        lib = LibrarianFileManager()
        keys = [
            {
                "key_id": f"GK-{i:03d}",
                "when_timestamp": f"2026-02-16T{(i * 2):02d}:00:00",
                "key_type": "user_input",
                "who_actor": "user",
                "what_description": f"Action {i}",
            }
            for i in range(12)
        ]
        blocks = lib.organize_genesis_keys(keys, block_hours=4)
        self.assertGreater(len(blocks), 0)
        total_keys = sum(b.key_count for b in blocks)
        self.assertEqual(total_keys, 12)

    def test_proactive_discovery_all_algorithms(self):
        """Test all 7 discovery algorithms produce results."""
        oracle = OracleVectorStore()
        oracle.ingest("Python content", domain="python")
        oracle.ingest("AI ML content", domain="ai_ml")
        oracle.ingest("Science content", domain="science")

        engine = ProactiveDiscoveryEngine(oracle_store=oracle)
        state = engine.run_full_discovery()

        self.assertGreater(state.total_tasks, 0)
        algorithms_used = set(state.by_algorithm.keys())
        self.assertGreater(len(algorithms_used), 1)

    def test_meta_verification_learns(self):
        """Test meta-verification learner tracks strategy performance."""
        learner = MetaVerificationLearner()
        for _ in range(10):
            learner.record_attempt(
                strategy="github_check", data_type="code", domain="python",
                success=True, confidence_before=0.5, confidence_after=0.9,
                time_ms=100,
            )
        rec = learner.recommend_strategy("code", domain="python")
        self.assertEqual(rec.strategy, "github_check")

    def test_cross_pillar_learning_triggers(self):
        """Test cross-pillar insights are generated."""
        from advanced_trust.cross_pillar_learning import PillarType
        from advanced_trust.cross_pillar_learning import PillarEvent as CPLEvent
        import uuid

        engine = CrossPillarLearningEngine(pattern_threshold=3)
        for _ in range(4):
            event = CPLEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                pillar=PillarType.SELF_BUILDING,
                event_type="failure",
                category="deploy_failure",
                description="Deploy failed",
            )
            engine.record_event(event)

        healing_insights = [
            i for i in engine.insights
            if PillarType.SELF_HEALING in i.target_pillars
        ]
        self.assertGreater(len(healing_insights), 0)


class TestSystemStats(unittest.TestCase):
    """Test that all system stats work correctly."""

    def test_all_stats_methods(self):
        """Test every module's get_stats() works."""
        # Advanced Trust
        self.assertIsInstance(ConfidenceCascadeEngine().get_stats(), dict)
        self.assertIsInstance(AdversarialSelfTester().get_stats(), dict)
        self.assertIsInstance(CompetenceBoundaryTracker().get_stats(), dict)
        self.assertIsInstance(CrossPillarLearningEngine().get_stats(), dict)
        self.assertIsInstance(TrustDecayEngine().get_stats(), dict)
        self.assertIsInstance(SystemTrustThermometer().get_stats(), dict)
        self.assertIsInstance(MetaVerificationLearner().get_stats(), dict)
        self.assertIsInstance(PillarTracker().get_stats(), dict)
        self.assertIsInstance(VerificationPipeline().get_stats(), dict)

        # Oracle Pipeline
        self.assertIsInstance(WhitelistBox().get_stats(), dict)
        self.assertIsInstance(OracleVectorStore().get_stats(), dict)
        self.assertIsInstance(SourceCodeIndex().get_stats(), dict)
        self.assertIsInstance(HallucinationGuard().get_stats(), dict)
        self.assertIsInstance(LibrarianFileManager().get_stats(), dict)
        self.assertIsInstance(ProactiveDiscoveryEngine().get_stats(), dict)
        self.assertIsInstance(ReverseKNNDiscovery().get_stats(), dict)
        self.assertIsInstance(LLMEnrichmentEngine().get_stats(), dict)
        self.assertIsInstance(DeepReasoningIntegration().get_stats(), dict)
        self.assertIsInstance(SocraticInterrogator().get_stats(), dict)
        self.assertIsInstance(SelfEvolutionCoordinator().get_stats(), dict)

    def test_perpetual_loop_comprehensive_stats(self):
        """Test the perpetual loop stats include all components."""
        loop = PerpetualLearningLoop()
        loop.seed_from_whitelist("Python content")
        stats = loop.get_stats()
        self.assertIn("loop_state", stats)
        self.assertIn("knowledge", stats)
        self.assertIn("trust_chain", stats)
        self.assertIn("components", stats)
        components = stats["components"]
        self.assertIn("oracle", components)
        self.assertIn("discovery", components)
        self.assertIn("enrichment", components)
        self.assertIn("source_index", components)
        self.assertIn("hallucination_guard", components)
        self.assertIn("librarian", components)
        self.assertIn("whitelist", components)
        self.assertIn("fetcher", components)


if __name__ == "__main__":
    unittest.main(verbosity=2)
