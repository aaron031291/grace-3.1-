"""
Comprehensive Component Tests for Mirror Self-Modeling System

Tests the Mirror Self-Modeling system that provides:
- Self-observation via Genesis Keys
- Behavioral pattern detection
- Learning progress analysis
- Improvement suggestions
- Self-awareness scoring
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from collections import defaultdict

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class TestPatternType:
    """Test PatternType constants."""

    def test_pattern_type_constants(self):
        """Test all PatternType constants are defined."""
        from cognitive.mirror_self_modeling import PatternType

        assert PatternType.REPEATED_FAILURE == "repeated_failure"
        assert PatternType.SUCCESS_SEQUENCE == "success_sequence"
        assert PatternType.LEARNING_PLATEAU == "learning_plateau"
        assert PatternType.EFFICIENCY_DROP == "efficiency_drop"
        assert PatternType.ANOMALOUS_BEHAVIOR == "anomalous_behavior"
        assert PatternType.IMPROVEMENT_OPPORTUNITY == "improvement_opportunity"


class TestMirrorSelfModelingSystem:
    """Test MirrorSelfModelingSystem functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        return session

    @pytest.fixture
    def mock_memory_learner(self):
        """Create a mock memory mesh learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_mirror_system_initialization(self, mock_session, mock_memory_learner):
        """Test MirrorSelfModelingSystem can be initialized."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(
                session=mock_session,
                observation_window_hours=24,
                min_pattern_occurrences=3
            )

            assert mirror.session == mock_session
            assert mirror.observation_window_hours == 24
            assert mirror.min_pattern_occurrences == 3
            assert mirror.behavioral_patterns == []
            assert mirror.improvement_suggestions == []

    def test_mirror_system_observe_recent_operations(self, mock_session, mock_memory_learner):
        """Test MirrorSelfModelingSystem observes recent operations."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        from models.genesis_key_models import GenesisKey, GenesisKeyType

        # Create mock Genesis Keys with valid enum values
        mock_gk1 = MagicMock()
        mock_gk1.key_type = GenesisKeyType.AI_RESPONSE  # Valid enum value
        mock_gk2 = MagicMock()
        mock_gk2.key_type = GenesisKeyType.ERROR  # Valid enum value

        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_gk1, mock_gk2]

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(
                session=mock_session,
                observation_window_hours=24
            )

            observation = mirror.observe_recent_operations()

            assert "timestamp" in observation
            assert "total_operations" in observation
            assert observation["total_operations"] == 2
            assert "operations_by_type" in observation

    def test_mirror_system_detect_behavioral_patterns(self, mock_session, mock_memory_learner):
        """Test MirrorSelfModelingSystem detects behavioral patterns."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(
                session=mock_session,
                observation_window_hours=24
            )

            # Mock the internal methods
            mirror._detect_repeated_failures = MagicMock(return_value=[])
            mirror._detect_success_sequences = MagicMock(return_value=[])
            mirror._detect_learning_plateaus = MagicMock(return_value=[])
            mirror._detect_efficiency_drops = MagicMock(return_value=[])
            mirror._detect_improvement_opportunities = MagicMock(return_value=[])

            patterns = mirror.detect_behavioral_patterns()

            assert isinstance(patterns, list)
            mirror._detect_repeated_failures.assert_called_once()
            mirror._detect_learning_plateaus.assert_called_once()
            mirror._detect_improvement_opportunities.assert_called_once()

    def test_mirror_system_build_self_model(self, mock_session, mock_memory_learner):
        """Test MirrorSelfModelingSystem builds self-model."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(
                session=mock_session,
                observation_window_hours=24
            )

            # Mock dependencies
            mirror.observe_recent_operations = MagicMock(return_value={
                "total_operations": 10,
                "operations_by_type": {"decision": 5, "error": 2}
            })
            mirror.detect_behavioral_patterns = MagicMock(return_value=[])
            mirror._analyze_learning_progress = MagicMock(return_value={
                "total_examples": 50,
                "avg_confidence": 0.75,
                "success_rate": 0.8,
                "topics_studied": 5
            })
            mirror._generate_improvement_suggestions = MagicMock(return_value=[])
            mirror._calculate_self_awareness_score = MagicMock(return_value=0.65)

            self_model = mirror.build_self_model()

            assert "timestamp" in self_model
            assert "operations_observed" in self_model
            assert "behavioral_patterns" in self_model
            assert "learning_progress" in self_model
            assert "improvement_suggestions" in self_model
            assert "self_awareness_score" in self_model


class TestLearningProgressAnalysis:
    """Test learning progress analysis functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_analyze_learning_progress_empty(self, mock_session, mock_memory_learner):
        """Test _analyze_learning_progress with no examples."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            progress = mirror._analyze_learning_progress()

            assert progress["total_examples"] == 0
            assert progress["avg_confidence"] == 0.0
            assert progress["success_rate"] == 0.0
            assert progress["topics_studied"] == 0

    def test_analyze_learning_progress_with_examples(self, mock_session, mock_memory_learner):
        """Test _analyze_learning_progress with learning examples."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        from cognitive.learning_memory import LearningExample

        # Create mock learning examples
        examples = []
        for i in range(5):
            ex = MagicMock(spec=LearningExample)
            ex.outcome_quality = 0.8
            ex.example_type = f"type_{i % 2}"
            ex.trust_score = 0.7 + (i * 0.05)
            ex.actual_output = {"success": True} if i % 2 == 0 else {}
            examples.append(ex)

        mock_session.query.return_value.filter.return_value.all.return_value = examples

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            progress = mirror._analyze_learning_progress()

            assert progress["total_examples"] == 5
            assert progress["avg_confidence"] > 0
            assert "topics_studied" in progress


class TestImprovementSuggestions:
    """Test improvement suggestion generation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_generate_improvement_suggestions_from_failures(self, mock_session, mock_memory_learner):
        """Test improvement suggestions from repeated failures."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem, PatternType

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            patterns = [
                {
                    "pattern_type": PatternType.REPEATED_FAILURE,
                    "topic": "error_handling",
                    "occurrences": 5,
                    "recommendation": "Review error handling approach"
                }
            ]

            learning_analysis = {"total_examples": 10}

            suggestions = mirror._generate_improvement_suggestions(patterns, learning_analysis)

            assert len(suggestions) == 1
            assert suggestions[0]["priority"] == "high"
            assert suggestions[0]["category"] == "failure_resolution"
            assert suggestions[0]["action"] == "restudy_and_practice"

    def test_generate_improvement_suggestions_from_plateaus(self, mock_session, mock_memory_learner):
        """Test improvement suggestions from learning plateaus."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem, PatternType

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            patterns = [
                {
                    "pattern_type": PatternType.LEARNING_PLATEAU,
                    "topic": "advanced_python",
                    "occurrences": 3,
                    "recommendation": "Needs more practice"
                }
            ]

            suggestions = mirror._generate_improvement_suggestions(patterns, {})

            assert len(suggestions) == 1
            assert suggestions[0]["priority"] == "medium"
            assert suggestions[0]["category"] == "skill_development"
            assert suggestions[0]["action"] == "intensive_practice"

    def test_suggestions_sorted_by_priority(self, mock_session, mock_memory_learner):
        """Test that suggestions are sorted by priority."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem, PatternType

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            patterns = [
                {
                    "pattern_type": PatternType.IMPROVEMENT_OPPORTUNITY,
                    "topic": "optimization",
                    "occurrences": 2,
                    "recommendation": "Low priority"
                },
                {
                    "pattern_type": PatternType.REPEATED_FAILURE,
                    "topic": "critical_bug",
                    "occurrences": 5,
                    "recommendation": "High priority"
                },
                {
                    "pattern_type": PatternType.LEARNING_PLATEAU,
                    "topic": "medium_issue",
                    "occurrences": 3,
                    "recommendation": "Medium priority"
                }
            ]

            suggestions = mirror._generate_improvement_suggestions(patterns, {})

            # Should be sorted: high, medium, low
            assert suggestions[0]["priority"] == "high"
            assert suggestions[1]["priority"] == "medium"
            assert suggestions[2]["priority"] == "low"


class TestSelfAwarenessScore:
    """Test self-awareness score calculation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_self_awareness_score_calculation(self, mock_session, mock_memory_learner):
        """Test self-awareness score calculation."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            patterns = [{"type": "test"} for _ in range(10)]
            learning_analysis = {
                "total_examples": 50,
                "success_rate": 0.8,
                "topics_studied": 10
            }

            score = mirror._calculate_self_awareness_score(patterns, learning_analysis)

            assert 0.0 <= score <= 1.0

    def test_self_awareness_score_increases_with_patterns(self, mock_session, mock_memory_learner):
        """Test that more patterns increases self-awareness score."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            learning_analysis = {
                "total_examples": 50,
                "success_rate": 0.8,
                "topics_studied": 10
            }

            score_few = mirror._calculate_self_awareness_score(
                [{"type": "test"}],
                learning_analysis
            )

            score_many = mirror._calculate_self_awareness_score(
                [{"type": "test"} for _ in range(15)],
                learning_analysis
            )

            assert score_many >= score_few


class TestAnalyzeRecentOperations:
    """Test analyze_recent_operations method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_analyze_recent_operations_returns_opportunities(self, mock_session, mock_memory_learner):
        """Test analyze_recent_operations returns improvement opportunities."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            # Mock build_self_model
            mirror.build_self_model = MagicMock(return_value={
                "operations_observed": 100,
                "self_awareness_score": 0.7
            })
            mirror.improvement_suggestions = [
                {
                    "priority": "high",
                    "category": "failure_resolution",
                    "topic": "error_handling",
                    "action": "study",
                    "reason": "Multiple failures",
                    "evidence_count": 5
                }
            ]
            mirror.behavioral_patterns = [{"type": "test"}]

            result = mirror.analyze_recent_operations(limit=100)

            assert "operations_analyzed" in result
            assert "patterns_detected" in result
            assert "improvement_opportunities" in result
            assert "self_awareness_score" in result

    def test_analyze_recent_operations_generates_seed_opportunities(self, mock_session, mock_memory_learner):
        """Test that seed opportunities are generated when no patterns exist."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            # Mock with empty suggestions
            mirror.build_self_model = MagicMock(return_value={
                "operations_observed": 0,
                "self_awareness_score": 0.3
            })
            mirror.improvement_suggestions = []
            mirror.behavioral_patterns = []

            result = mirror.analyze_recent_operations()

            # Should have seed opportunities when empty
            assert len(result["improvement_opportunities"]) > 0


class TestTriggerImprovementActions:
    """Test trigger_improvement_actions method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_trigger_improvement_actions_with_orchestrator(self, mock_session, mock_memory_learner):
        """Test trigger_improvement_actions with learning orchestrator."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            mirror.improvement_suggestions = [
                {
                    "priority": "high",
                    "action": "restudy_and_practice",
                    "topic": "error_handling",
                    "evidence_count": 5
                }
            ]

            mock_orchestrator = MagicMock()
            mock_orchestrator.submit_study_task.return_value = "task-001"

            result = mirror.trigger_improvement_actions(learning_orchestrator=mock_orchestrator)

            assert result["actions_triggered"] == 1
            mock_orchestrator.submit_study_task.assert_called_once()

    def test_trigger_improvement_actions_without_orchestrator(self, mock_session, mock_memory_learner):
        """Test trigger_improvement_actions without orchestrator does nothing."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            mirror.improvement_suggestions = [
                {
                    "priority": "high",
                    "action": "restudy_and_practice",
                    "topic": "error_handling",
                    "evidence_count": 5
                }
            ]

            result = mirror.trigger_improvement_actions(learning_orchestrator=None)

            assert result["actions_triggered"] == 0


class TestMirrorStatus:
    """Test get_mirror_status method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_get_mirror_status(self, mock_session, mock_memory_learner):
        """Test get_mirror_status returns correct structure."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(
                session=mock_session,
                observation_window_hours=48
            )

            mirror.behavioral_patterns = [{"type": "test1"}, {"type": "test2"}]
            mirror.improvement_suggestions = [
                {"priority": "high", "topic": "t1"},
                {"priority": "medium", "topic": "t2"},
                {"priority": "high", "topic": "t3"}
            ]

            status = mirror.get_mirror_status()

            assert status["patterns_detected"] == 2
            assert status["improvement_suggestions"] == 3
            assert status["observation_window_hours"] == 48
            assert status["high_priority_suggestions"] == 2


class TestGlobalMirrorSystem:
    """Test global mirror system singleton."""

    def test_get_mirror_system_creates_instance(self):
        """Test get_mirror_system creates instance."""
        from cognitive.mirror_self_modeling import get_mirror_system, _mirror_system
        import cognitive.mirror_self_modeling as mirror_module

        mock_session = MagicMock()

        with patch.object(mirror_module, '_mirror_system', None):
            with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner'):
                mirror = get_mirror_system(session=mock_session)
                assert mirror is not None


class TestCountPatternsByType:
    """Test _count_patterns_by_type helper method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def mock_memory_learner(self):
        """Create mock memory learner."""
        learner = MagicMock()
        learner.get_learning_suggestions.return_value = {
            "knowledge_gaps": [],
            "high_value_topics": []
        }
        return learner

    def test_count_patterns_by_type(self, mock_session, mock_memory_learner):
        """Test _count_patterns_by_type correctly counts pattern types."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem, PatternType

        with patch('cognitive.mirror_self_modeling.get_memory_mesh_learner', return_value=mock_memory_learner):
            mirror = MirrorSelfModelingSystem(session=mock_session)

            patterns = [
                {"pattern_type": PatternType.REPEATED_FAILURE},
                {"pattern_type": PatternType.REPEATED_FAILURE},
                {"pattern_type": PatternType.LEARNING_PLATEAU},
                {"pattern_type": PatternType.IMPROVEMENT_OPPORTUNITY},
            ]

            counts = mirror._count_patterns_by_type(patterns)

            assert counts[PatternType.REPEATED_FAILURE] == 2
            assert counts[PatternType.LEARNING_PLATEAU] == 1
            assert counts[PatternType.IMPROVEMENT_OPPORTUNITY] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
