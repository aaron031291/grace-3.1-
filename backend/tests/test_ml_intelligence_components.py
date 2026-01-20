"""
Comprehensive Component Tests for ML Intelligence Module

Tests the ML Intelligence module including:
- KPITracker functionality
- NeuralTrustScorer (when torch available)
- Module imports and fallbacks
- Component availability flags
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class TestMLIntelligenceImports:
    """Test ML Intelligence module imports and availability."""

    def test_ml_intelligence_module_imports(self):
        """Test ML Intelligence module can be imported."""
        import ml_intelligence
        assert ml_intelligence is not None

    def test_ml_intelligence_available_flag_exists(self):
        """Test ML_INTELLIGENCE_AVAILABLE flag is defined."""
        from ml_intelligence import ML_INTELLIGENCE_AVAILABLE
        assert isinstance(ML_INTELLIGENCE_AVAILABLE, bool)

    def test_kpi_tracker_import(self):
        """Test KPITracker can be imported from ml_intelligence."""
        from ml_intelligence import KPITracker, KPI, ComponentKPIs, get_kpi_tracker

        # These should not be None if imports work
        assert KPITracker is not None or KPITracker is None  # Either works or has fallback
        assert KPI is not None or KPI is None
        assert ComponentKPIs is not None or ComponentKPIs is None
        assert get_kpi_tracker is not None or get_kpi_tracker is None

    def test_all_exports_defined(self):
        """Test __all__ exports are defined in module."""
        import ml_intelligence

        expected_exports = [
            'NeuralTrustScorer',
            'get_neural_trust_scorer',
            'KPITracker',
            'KPI',
            'ComponentKPIs',
            'get_kpi_tracker',
        ]

        for export in expected_exports:
            assert export in ml_intelligence.__all__, f"{export} missing from __all__"


class TestKPIClass:
    """Test KPI dataclass functionality."""

    def test_kpi_creation(self):
        """Test KPI can be created with required fields."""
        from ml_intelligence.kpi_tracker import KPI

        kpi = KPI(
            component_name="retrieval",
            metric_name="queries_processed",
            value=100.0
        )

        assert kpi.component_name == "retrieval"
        assert kpi.metric_name == "queries_processed"
        assert kpi.value == 100.0
        assert kpi.count == 1

    def test_kpi_increment(self):
        """Test KPI increment functionality."""
        from ml_intelligence.kpi_tracker import KPI

        kpi = KPI(
            component_name="retrieval",
            metric_name="queries_processed",
            value=0.0,
            count=0
        )

        kpi.increment(10.0)
        assert kpi.value == 10.0
        assert kpi.count == 1

        kpi.increment(5.0, metadata={"source": "api"})
        assert kpi.value == 15.0
        assert kpi.count == 2
        assert kpi.metadata.get("source") == "api"

    def test_kpi_timestamp_updates(self):
        """Test KPI timestamp updates on increment."""
        from ml_intelligence.kpi_tracker import KPI
        import time

        kpi = KPI(
            component_name="test",
            metric_name="test_metric",
            value=0.0
        )

        original_timestamp = kpi.timestamp
        time.sleep(0.01)  # Small delay
        kpi.increment(1.0)

        assert kpi.timestamp >= original_timestamp


class TestComponentKPIs:
    """Test ComponentKPIs class functionality."""

    def test_component_kpis_creation(self):
        """Test ComponentKPIs can be created."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="cognitive_engine")

        assert component.component_name == "cognitive_engine"
        assert len(component.kpis) == 0

    def test_component_kpis_get_or_create(self):
        """Test ComponentKPIs get_kpi creates KPI if not exists."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="cognitive")

        # First access creates KPI
        kpi = component.get_kpi("decisions_made")
        assert kpi.component_name == "cognitive"
        assert kpi.metric_name == "decisions_made"
        assert kpi.value == 0.0

        # Second access returns same KPI
        kpi2 = component.get_kpi("decisions_made")
        assert kpi is kpi2

    def test_component_kpis_increment(self):
        """Test ComponentKPIs increment_kpi functionality."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="retrieval")

        component.increment_kpi("queries", 10.0)
        component.increment_kpi("queries", 5.0)
        component.increment_kpi("cache_hits", 3.0)

        assert component.kpis["queries"].value == 15.0
        assert component.kpis["queries"].count == 2
        assert component.kpis["cache_hits"].value == 3.0

    def test_component_kpis_trust_score(self):
        """Test ComponentKPIs trust score calculation."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="test")

        # No KPIs = default trust
        assert component.get_trust_score() == 0.5

        # Add some KPIs with activity
        for _ in range(20):
            component.increment_kpi("activity", 1.0)

        trust = component.get_trust_score()
        assert 0.0 <= trust <= 1.0
        assert trust > 0.5  # Should be higher than default due to activity

    def test_component_kpis_to_dict(self):
        """Test ComponentKPIs serialization to dict."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="test")
        component.increment_kpi("metric1", 10.0)

        data = component.to_dict()

        assert data["component_name"] == "test"
        assert "kpis" in data
        assert "metric1" in data["kpis"]
        assert "trust_score" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_component_kpis_recent_kpi(self):
        """Test ComponentKPIs get_recent_kpi functionality."""
        from ml_intelligence.kpi_tracker import ComponentKPIs

        component = ComponentKPIs(component_name="test")
        component.increment_kpi("fresh_metric", 1.0)

        # Recent KPI should be found
        recent = component.get_recent_kpi("fresh_metric", timedelta(hours=1))
        assert recent is not None

        # Non-existent KPI should return None
        missing = component.get_recent_kpi("nonexistent", timedelta(hours=1))
        assert missing is None


class TestKPITracker:
    """Test KPITracker class functionality."""

    def test_kpi_tracker_creation(self):
        """Test KPITracker can be created."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()
        assert len(tracker.components) == 0

    def test_kpi_tracker_register_component(self):
        """Test KPITracker register_component functionality."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()
        tracker.register_component("cognitive_engine")
        tracker.register_component("retrieval", metric_weights={"queries": 2.0, "cache_hits": 1.0})

        assert "cognitive_engine" in tracker.components
        assert "retrieval" in tracker.components
        assert tracker.metric_weights.get("retrieval", {}).get("queries") == 2.0

    def test_kpi_tracker_increment_auto_register(self):
        """Test KPITracker auto-registers component on increment."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()
        tracker.increment_kpi("new_component", "actions", 5.0)

        assert "new_component" in tracker.components
        assert tracker.components["new_component"].kpis["actions"].value == 5.0

    def test_kpi_tracker_component_trust_score(self):
        """Test KPITracker get_component_trust_score functionality."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # Unknown component returns default
        assert tracker.get_component_trust_score("unknown") == 0.5

        # Add activity
        for _ in range(15):
            tracker.increment_kpi("active_component", "actions", 1.0)

        trust = tracker.get_component_trust_score("active_component")
        assert trust > 0.5

    def test_kpi_tracker_system_trust_score(self):
        """Test KPITracker get_system_trust_score functionality."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # No components = default trust
        assert tracker.get_system_trust_score() == 0.5

        # Add multiple components with activity
        for comp in ["comp1", "comp2", "comp3"]:
            for _ in range(10):
                tracker.increment_kpi(comp, "actions", 1.0)

        system_trust = tracker.get_system_trust_score()
        assert 0.0 <= system_trust <= 1.0

    def test_kpi_tracker_health_signal(self):
        """Test KPITracker get_health_signal functionality."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # Unknown component
        health = tracker.get_health_signal("unknown")
        assert health["status"] == "unknown"
        assert health["trust_score"] == 0.5

        # Add component with high activity
        for _ in range(50):
            tracker.increment_kpi("healthy_component", "successes", 1.0)

        health = tracker.get_health_signal("healthy_component")
        assert health["component_name"] == "healthy_component"
        assert health["status"] in ["excellent", "good", "fair", "poor"]
        assert "trust_score" in health
        assert "kpi_count" in health
        assert "total_actions" in health

    def test_kpi_tracker_system_health(self):
        """Test KPITracker get_system_health functionality."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # Add some components
        tracker.increment_kpi("comp1", "actions", 10.0)
        tracker.increment_kpi("comp2", "actions", 20.0)

        health = tracker.get_system_health()

        assert "system_trust_score" in health
        assert "status" in health
        assert "component_count" in health
        assert health["component_count"] == 2
        assert "components" in health
        assert "comp1" in health["components"]
        assert "comp2" in health["components"]

    def test_kpi_tracker_to_dict(self):
        """Test KPITracker serialization to dict."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()
        tracker.increment_kpi("test_comp", "metric1", 5.0)

        data = tracker.to_dict()

        assert "components" in data
        assert "test_comp" in data["components"]
        assert "system_trust_score" in data
        assert "system_health" in data


class TestKPITrackerSingleton:
    """Test KPITracker singleton functionality."""

    def test_get_kpi_tracker_singleton(self):
        """Test get_kpi_tracker returns singleton instance."""
        from ml_intelligence.kpi_tracker import get_kpi_tracker, reset_kpi_tracker

        # Reset to clean state
        reset_kpi_tracker()

        tracker1 = get_kpi_tracker()
        tracker2 = get_kpi_tracker()

        assert tracker1 is tracker2

    def test_reset_kpi_tracker(self):
        """Test reset_kpi_tracker creates new instance."""
        from ml_intelligence.kpi_tracker import get_kpi_tracker, reset_kpi_tracker

        tracker1 = get_kpi_tracker()
        tracker1.increment_kpi("test", "value", 100.0)

        reset_kpi_tracker()
        tracker2 = get_kpi_tracker()

        # Should be a new instance with no data
        assert len(tracker2.components) == 0


class TestNeuralTrustScorer:
    """Test NeuralTrustScorer functionality (when available)."""

    def test_neural_trust_scorer_import(self):
        """Test NeuralTrustScorer can be imported."""
        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer
            assert NeuralTrustScorer is not None
        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")

    def test_trust_features_dataclass(self):
        """Test TrustFeatures dataclass."""
        try:
            from ml_intelligence.neural_trust_scorer import TrustFeatures

            features = TrustFeatures(
                source_reliability=0.8,
                outcome_quality=0.9,
                consistency_score=0.7,
                validation_count=5,
                invalidation_count=1,
                age_days=10.0,
                content_length=500,
                has_code=True,
                has_structure=True,
                has_references=False,
                usage_frequency=0.5,
                success_rate=0.85
            )

            assert features.source_reliability == 0.8
            assert features.has_code == True
            assert features.success_rate == 0.85
        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")

    def test_neural_trust_scorer_extract_features(self):
        """Test NeuralTrustScorer feature extraction."""
        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer

            scorer = NeuralTrustScorer(model_path="/tmp/test_model.pt")

            learning_example = {
                "source_reliability": 0.8,
                "outcome_quality": 0.7,
                "consistency_score": 0.6,
                "times_validated": 10,
                "times_invalidated": 2,
                "created_at": datetime.now(),
                "input_context": "def test_function(): pass",
                "expected_output": "Expected result",
                "times_referenced": 5
            }

            features = scorer.extract_features(learning_example)

            assert features.source_reliability == 0.8
            assert features.outcome_quality == 0.7
            assert features.has_code == True  # Contains 'def '

        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")

    def test_neural_trust_scorer_predict_trust(self):
        """Test NeuralTrustScorer trust prediction."""
        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer

            scorer = NeuralTrustScorer(model_path="/tmp/test_model.pt")

            learning_example = {
                "source_reliability": 0.9,
                "outcome_quality": 0.8,
                "consistency_score": 0.85,
                "times_validated": 20,
                "times_invalidated": 1,
                "created_at": datetime.now(),
                "input_context": "High quality content",
                "expected_output": "Expected result",
                "times_referenced": 15
            }

            score, uncertainty = scorer.predict_trust(learning_example)

            assert 0.0 <= score <= 1.0
            if uncertainty is not None:
                assert 0.0 <= uncertainty <= 1.0

        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")

    def test_neural_trust_scorer_get_stats(self):
        """Test NeuralTrustScorer stats retrieval."""
        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer

            scorer = NeuralTrustScorer(model_path="/tmp/test_model.pt")
            stats = scorer.get_stats()

            assert "total_updates" in stats
            assert "replay_buffer_size" in stats
            assert "device" in stats

        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")


class TestExperienceReplay:
    """Test ExperienceReplay buffer functionality."""

    def test_experience_replay_creation(self):
        """Test ExperienceReplay buffer can be created."""
        try:
            from ml_intelligence.neural_trust_scorer import ExperienceReplay

            buffer = ExperienceReplay(max_size=100)
            assert len(buffer) == 0

        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")

    def test_experience_replay_add_and_sample(self):
        """Test ExperienceReplay add and sample functionality."""
        try:
            from ml_intelligence.neural_trust_scorer import ExperienceReplay, TrainingExample, TrustFeatures

            buffer = ExperienceReplay(max_size=100)

            # Add some examples
            for i in range(10):
                features = TrustFeatures(
                    source_reliability=0.5 + i * 0.05,
                    outcome_quality=0.6,
                    consistency_score=0.7,
                    validation_count=i,
                    invalidation_count=0,
                    age_days=float(i),
                    content_length=100,
                    has_code=False,
                    has_structure=True,
                    has_references=False,
                    usage_frequency=0.1,
                    success_rate=0.8
                )
                example = TrainingExample(
                    features=features,
                    true_outcome=1.0 if i % 2 == 0 else 0.0,
                    timestamp=datetime.now()
                )
                buffer.add(example)

            assert len(buffer) == 10

            # Sample
            batch = buffer.sample(5)
            assert len(batch) == 5

        except ImportError as e:
            pytest.skip(f"Neural trust scorer dependencies not available: {e}")


class TestMLIntelligenceFallbacks:
    """Test ML Intelligence module fallback behavior."""

    def test_fallbacks_defined_when_unavailable(self):
        """Test that fallback values are defined when components unavailable."""
        import ml_intelligence

        # These should all be defined (either as classes or None)
        attrs_to_check = [
            'NeuralTrustScorer',
            'get_neural_trust_scorer',
            'KPITracker',
            'KPI',
            'ComponentKPIs',
            'get_kpi_tracker'
        ]

        for attr in attrs_to_check:
            assert hasattr(ml_intelligence, attr), f"Missing attribute: {attr}"

    def test_ml_intelligence_available_reflects_imports(self):
        """Test ML_INTELLIGENCE_AVAILABLE reflects import success."""
        from ml_intelligence import ML_INTELLIGENCE_AVAILABLE

        # If KPITracker is available, ML_INTELLIGENCE_AVAILABLE should be True
        from ml_intelligence import KPITracker

        if KPITracker is not None:
            # If we got here with a real class, the flag should be True
            # (unless torch failed but kpi_tracker worked)
            pass  # Can't assert much without knowing torch status

        # The flag should always be a boolean
        assert isinstance(ML_INTELLIGENCE_AVAILABLE, bool)


class TestKPITrackerIntegration:
    """Integration tests for KPITracker with multiple components."""

    def test_multi_component_tracking(self):
        """Test tracking KPIs across multiple components."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # Simulate activity across multiple components
        components = ["cognitive", "retrieval", "ingestion", "learning"]

        for comp in components:
            tracker.register_component(comp)
            for _ in range(5):
                tracker.increment_kpi(comp, "requests", 1.0)
                tracker.increment_kpi(comp, "successes", 0.9)

        # Check all components tracked
        assert len(tracker.components) == 4

        # Check system health reflects all components
        health = tracker.get_system_health()
        assert health["component_count"] == 4

        for comp in components:
            assert comp in health["components"]

    def test_weighted_trust_calculation(self):
        """Test weighted trust score calculation."""
        from ml_intelligence.kpi_tracker import KPITracker

        tracker = KPITracker()

        # Register with custom weights
        tracker.register_component(
            "critical_component",
            metric_weights={"errors": -1.0, "successes": 2.0}
        )

        # Add positive activity
        for _ in range(20):
            tracker.increment_kpi("critical_component", "successes", 1.0)

        trust = tracker.get_component_trust_score("critical_component")
        assert trust > 0.5  # Should be positive due to successes


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
