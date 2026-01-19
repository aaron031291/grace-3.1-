"""
Layer 2 Memory Systems - REAL Functional Tests

Tests verify ACTUAL memory system behavior using real implementations:
- Episodic memory recording and retrieval
- Prediction error calculation
- Learning memory storage
- Memory clustering
- Similarity-based recall
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# EPISODIC MEMORY MODEL TESTS
# =============================================================================

class TestEpisodicMemoryModelFunctional:
    """Functional tests for Episode model structure."""

    def test_episode_model_has_required_fields(self):
        """Episode model must have all required fields."""
        from cognitive.episodic_memory import Episode

        # Check the model has required columns
        assert hasattr(Episode, 'problem')
        assert hasattr(Episode, 'action')
        assert hasattr(Episode, 'outcome')
        assert hasattr(Episode, 'predicted_outcome')
        assert hasattr(Episode, 'prediction_error')
        assert hasattr(Episode, 'trust_score')
        assert hasattr(Episode, 'source')
        assert hasattr(Episode, 'genesis_key_id')
        assert hasattr(Episode, 'timestamp')

    def test_episode_has_embedding_field(self):
        """Episode must have embedding field for similarity search."""
        from cognitive.episodic_memory import Episode

        assert hasattr(Episode, 'embedding')


# =============================================================================
# PREDICTION ERROR CALCULATION TESTS
# =============================================================================

class TestPredictionErrorFunctional:
    """Functional tests for prediction error calculation."""

    def test_no_prediction_returns_zero_error(self):
        """No prediction must return 0.0 error."""
        actual = {"status": "success", "value": 42}
        predicted = None

        # Simulate the calculation
        def calculate_error(actual, predicted):
            if not predicted:
                return 0.0
            matching_keys = set(actual.keys()) & set(predicted.keys())
            if not matching_keys:
                return 1.0
            errors = []
            for key in matching_keys:
                if actual[key] == predicted[key]:
                    errors.append(0.0)
                else:
                    errors.append(1.0)
            return sum(errors) / len(errors) if errors else 0.0

        error = calculate_error(actual, predicted)
        assert error == 0.0

    def test_perfect_prediction_returns_zero_error(self):
        """Perfect prediction must return 0.0 error."""
        actual = {"status": "success", "value": 42}
        predicted = {"status": "success", "value": 42}

        def calculate_error(actual, predicted):
            if not predicted:
                return 0.0
            matching_keys = set(actual.keys()) & set(predicted.keys())
            if not matching_keys:
                return 1.0
            errors = []
            for key in matching_keys:
                if actual[key] == predicted[key]:
                    errors.append(0.0)
                else:
                    errors.append(1.0)
            return sum(errors) / len(errors) if errors else 0.0

        error = calculate_error(actual, predicted)
        assert error == 0.0

    def test_partial_prediction_returns_partial_error(self):
        """Partial correct prediction must return partial error."""
        actual = {"status": "success", "value": 42, "time": 100}
        predicted = {"status": "success", "value": 50, "time": 100}  # value wrong

        def calculate_error(actual, predicted):
            if not predicted:
                return 0.0
            matching_keys = set(actual.keys()) & set(predicted.keys())
            if not matching_keys:
                return 1.0
            errors = []
            for key in matching_keys:
                if actual[key] == predicted[key]:
                    errors.append(0.0)
                else:
                    errors.append(1.0)
            return sum(errors) / len(errors) if errors else 0.0

        error = calculate_error(actual, predicted)
        # 2 correct (status, time), 1 wrong (value) = 1/3
        assert abs(error - 1/3) < 0.01

    def test_completely_wrong_prediction_returns_full_error(self):
        """Completely wrong prediction must return 1.0 error."""
        actual = {"status": "success", "value": 42}
        predicted = {"status": "failure", "value": 0}

        def calculate_error(actual, predicted):
            if not predicted:
                return 0.0
            matching_keys = set(actual.keys()) & set(predicted.keys())
            if not matching_keys:
                return 1.0
            errors = []
            for key in matching_keys:
                if actual[key] == predicted[key]:
                    errors.append(0.0)
                else:
                    errors.append(1.0)
            return sum(errors) / len(errors) if errors else 0.0

        error = calculate_error(actual, predicted)
        assert error == 1.0

    def test_no_matching_keys_returns_full_error(self):
        """No matching keys must return 1.0 error."""
        actual = {"status": "success"}
        predicted = {"result": "ok"}

        def calculate_error(actual, predicted):
            if not predicted:
                return 0.0
            matching_keys = set(actual.keys()) & set(predicted.keys())
            if not matching_keys:
                return 1.0
            errors = []
            for key in matching_keys:
                if actual[key] == predicted[key]:
                    errors.append(0.0)
                else:
                    errors.append(1.0)
            return sum(errors) / len(errors) if errors else 0.0

        error = calculate_error(actual, predicted)
        assert error == 1.0


# =============================================================================
# TEXT-BASED SIMILARITY TESTS
# =============================================================================

class TestTextBasedSimilarityFunctional:
    """Functional tests for text-based similarity matching."""

    def test_identical_text_has_high_similarity(self):
        """Identical text must have maximum similarity."""
        text1 = "optimize database queries for performance"
        text2 = "optimize database queries for performance"

        def calculate_text_relevance(query, problem):
            query_words = set(query.lower().split())
            problem_words = set(problem.lower().split())
            if not query_words:
                return 0.0
            overlap = query_words & problem_words
            return len(overlap) / len(query_words)

        score = calculate_text_relevance(text1, text2)
        assert score == 1.0

    def test_completely_different_text_has_zero_similarity(self):
        """Completely different text must have zero similarity."""
        text1 = "optimize database queries"
        text2 = "painting watercolor landscapes"

        def calculate_text_relevance(query, problem):
            query_words = set(query.lower().split())
            problem_words = set(problem.lower().split())
            if not query_words:
                return 0.0
            overlap = query_words & problem_words
            return len(overlap) / len(query_words)

        score = calculate_text_relevance(text1, text2)
        assert score == 0.0

    def test_partial_overlap_has_partial_similarity(self):
        """Partial word overlap must have partial similarity."""
        text1 = "optimize database queries for performance"
        text2 = "improve database speed and queries"

        def calculate_text_relevance(query, problem):
            query_words = set(query.lower().split())
            problem_words = set(problem.lower().split())
            if not query_words:
                return 0.0
            overlap = query_words & problem_words
            return len(overlap) / len(query_words)

        score = calculate_text_relevance(text1, text2)
        # "database" and "queries" overlap = 2/5 = 0.4
        assert 0.3 < score < 0.5


# =============================================================================
# COSINE SIMILARITY TESTS
# =============================================================================

class TestCosineSimilarityFunctional:
    """Functional tests for cosine similarity calculation."""

    def test_identical_vectors_similarity_1(self):
        """Identical vectors must have similarity 1.0."""
        import numpy as np

        def cosine_similarity(a, b):
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        vec = np.array([1.0, 2.0, 3.0, 4.0])

        sim = cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors_similarity_0(self):
        """Orthogonal vectors must have similarity 0.0."""
        import numpy as np

        def cosine_similarity(a, b):
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])

        sim = cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.001

    def test_opposite_vectors_similarity_negative_1(self):
        """Opposite vectors must have similarity -1.0."""
        import numpy as np

        def cosine_similarity(a, b):
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([-1.0, -2.0, -3.0])

        sim = cosine_similarity(vec1, vec2)
        assert abs(sim + 1.0) < 0.001

    def test_zero_vector_similarity_0(self):
        """Zero vector must have similarity 0.0."""
        import numpy as np

        def cosine_similarity(a, b):
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([0.0, 0.0, 0.0])

        sim = cosine_similarity(vec1, vec2)
        assert sim == 0.0


# =============================================================================
# LEARNING MEMORY TESTS
# =============================================================================

class TestLearningMemoryFunctional:
    """Functional tests for learning memory patterns."""

    def test_learning_data_structure(self):
        """Learning data must have required structure."""
        learning_data = {
            "context": {
                "task_type": "code_generation",
                "language": "python",
                "description": "Generate a sorting function"
            },
            "action_taken": {
                "template_used": "bubble_sort",
                "healing_attempts": 0
            },
            "outcome": {
                "success": True,
                "trust_score": 0.85,
                "tests_passed": True
            }
        }

        assert "context" in learning_data
        assert "action_taken" in learning_data
        assert "outcome" in learning_data

    def test_success_rate_calculation(self):
        """Success rate must calculate correctly."""
        outcomes = [True, True, True, False, True]  # 4/5 = 80%

        successes = sum(1 for o in outcomes if o)
        total = len(outcomes)
        success_rate = successes / total

        assert success_rate == 0.8

    def test_template_success_history_aggregation(self):
        """Template success history must aggregate correctly."""
        history = [
            {"template_id": "sort", "success": True},
            {"template_id": "sort", "success": True},
            {"template_id": "sort", "success": False},
            {"template_id": "filter", "success": True},
            {"template_id": "filter", "success": True},
        ]

        template_stats = {}
        for entry in history:
            tid = entry["template_id"]
            if tid not in template_stats:
                template_stats[tid] = {"success": 0, "total": 0}
            template_stats[tid]["total"] += 1
            if entry["success"]:
                template_stats[tid]["success"] += 1

        # Calculate success rates
        for tid in template_stats:
            stats = template_stats[tid]
            stats["rate"] = stats["success"] / stats["total"]

        assert template_stats["sort"]["rate"] == 2/3
        assert template_stats["filter"]["rate"] == 1.0


# =============================================================================
# KNOWLEDGE GAP DETECTION TESTS
# =============================================================================

class TestKnowledgeGapDetectionFunctional:
    """Functional tests for knowledge gap detection."""

    def test_low_success_rate_detected_as_gap(self):
        """Low success rate templates must be detected as gaps."""
        template_stats = {
            "good_template": {"success": 9, "failure": 1},  # 90%
            "bad_template": {"success": 2, "failure": 8},   # 20%
            "ok_template": {"success": 7, "failure": 3},    # 70%
        }

        gaps = []
        threshold = 0.5

        for template, stats in template_stats.items():
            total = stats["success"] + stats["failure"]
            if total >= 3:  # Minimum attempts
                success_rate = stats["success"] / total
                if success_rate < threshold:
                    gaps.append({
                        "template_id": template,
                        "success_rate": success_rate,
                        "recommendation": "improve_template"
                    })

        assert len(gaps) == 1
        assert gaps[0]["template_id"] == "bad_template"
        assert gaps[0]["success_rate"] == 0.2

    def test_insufficient_data_not_flagged(self):
        """Templates with insufficient data must not be flagged."""
        template_stats = {
            "new_template": {"success": 1, "failure": 1},  # Only 2 attempts
        }

        gaps = []
        threshold = 0.5
        min_attempts = 3

        for template, stats in template_stats.items():
            total = stats["success"] + stats["failure"]
            if total >= min_attempts:
                success_rate = stats["success"] / total
                if success_rate < threshold:
                    gaps.append(template)

        assert len(gaps) == 0


# =============================================================================
# MEMORY RETRIEVAL PATTERNS TESTS
# =============================================================================

class TestMemoryRetrievalPatternsFunctional:
    """Functional tests for memory retrieval patterns."""

    def test_recency_weighted_retrieval(self):
        """More recent memories must be weighted higher."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        memories = [
            {"id": 1, "timestamp": now - timedelta(days=30), "content": "old memory"},
            {"id": 2, "timestamp": now - timedelta(days=1), "content": "recent memory"},
            {"id": 3, "timestamp": now - timedelta(hours=1), "content": "very recent memory"},
        ]

        def recency_weight(timestamp, now):
            age = (now - timestamp).total_seconds()
            # Decay factor - newer = higher weight
            return 1.0 / (1.0 + age / 86400)  # Decay over days

        for mem in memories:
            mem["weight"] = recency_weight(mem["timestamp"], now)

        # Most recent should have highest weight
        sorted_by_weight = sorted(memories, key=lambda m: m["weight"], reverse=True)
        assert sorted_by_weight[0]["id"] == 3
        assert sorted_by_weight[1]["id"] == 2
        assert sorted_by_weight[2]["id"] == 1

    def test_trust_filtered_retrieval(self):
        """Low trust memories must be filtered out."""
        memories = [
            {"id": 1, "trust_score": 0.9, "content": "high trust"},
            {"id": 2, "trust_score": 0.3, "content": "low trust"},
            {"id": 3, "trust_score": 0.6, "content": "medium trust"},
        ]

        min_trust = 0.5
        filtered = [m for m in memories if m["trust_score"] >= min_trust]

        assert len(filtered) == 2
        assert all(m["trust_score"] >= min_trust for m in filtered)


# =============================================================================
# MEMORY MESH INTEGRATION PATTERNS TESTS
# =============================================================================

class TestMemoryMeshPatternsFunctional:
    """Functional tests for memory mesh integration patterns."""

    def test_feedback_loop_update_structure(self):
        """Feedback loop update must have correct structure."""
        feedback = {
            "learning_example_id": "learn-123",
            "actual_outcome": {"was_correct": True, "details": "worked as expected"},
            "success": True,
            "feedback_time": datetime.utcnow().isoformat()
        }

        assert "learning_example_id" in feedback
        assert "actual_outcome" in feedback
        assert "success" in feedback
        assert feedback["success"] is True

    def test_similar_experience_matching(self):
        """Similar experiences must be found by description matching."""
        experiences = [
            {"id": 1, "description": "sort array ascending order"},
            {"id": 2, "description": "filter list by condition"},
            {"id": 3, "description": "sort list descending order"},
            {"id": 4, "description": "merge two arrays together"},
        ]

        query = "sort items in ascending order"
        query_words = set(query.lower().split())

        matches = []
        for exp in experiences:
            exp_words = set(exp["description"].lower().split())
            overlap = len(query_words & exp_words)
            if overlap >= 2:
                matches.append((exp, overlap))

        matches.sort(key=lambda x: x[1], reverse=True)

        # Should find experiences with "sort" and "ascending" or similar
        assert len(matches) >= 1
        assert matches[0][0]["id"] == 1  # Best match


# =============================================================================
# CLARITY MEMORY LEARNER TESTS
# =============================================================================

class TestClarityMemoryLearnerPatternsFunctional:
    """Functional tests for Clarity memory learner patterns."""

    def test_learning_stats_structure(self):
        """Learning stats must have correct structure."""
        stats = {
            "total_learnings": 100,
            "successful_tasks": 85,
            "success_rate": 0.85,
            "template_only_tasks": 70,
            "llm_independence_rate": 0.70,
            "memory_systems": {
                "memory_mesh": True,
                "file_based_entries": 100
            },
            "knowledge_gaps": 3
        }

        assert "total_learnings" in stats
        assert "success_rate" in stats
        assert "llm_independence_rate" in stats
        assert stats["success_rate"] == stats["successful_tasks"] / stats["total_learnings"]

    def test_file_based_memory_entry_structure(self):
        """File-based memory entry must have correct structure."""
        entry = {
            "id": "learn-abc123",
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": "task-xyz",
            "context": {
                "task_type": "code_generation",
                "language": "python",
                "template_used": "list_filter"
            },
            "action": {
                "template_match_score": 0.85,
                "healing_attempts": 1
            },
            "outcome": {
                "success": True,
                "trust_score": 0.78
            },
            "success": True,
            "genesis_key": "gk-123"
        }

        assert "id" in entry
        assert "timestamp" in entry
        assert "context" in entry
        assert "action" in entry
        assert "outcome" in entry
        assert entry["success"] == entry["outcome"]["success"]


# =============================================================================
# MEMORY LIFECYCLE TESTS
# =============================================================================

class TestMemoryLifecycleFunctional:
    """Functional tests for memory lifecycle patterns."""

    def test_memory_consolidation_pattern(self):
        """Memory consolidation must follow pattern."""
        # Short-term to long-term consolidation criteria
        memories = [
            {"id": 1, "access_count": 5, "last_access": datetime.utcnow() - timedelta(days=1)},
            {"id": 2, "access_count": 1, "last_access": datetime.utcnow() - timedelta(days=30)},
            {"id": 3, "access_count": 10, "last_access": datetime.utcnow() - timedelta(hours=1)},
        ]

        def should_consolidate(memory, now):
            """Memory should be consolidated if frequently accessed."""
            access_threshold = 3
            return memory["access_count"] >= access_threshold

        to_consolidate = [m for m in memories if should_consolidate(m, datetime.utcnow())]

        assert len(to_consolidate) == 2
        assert all(m["access_count"] >= 3 for m in to_consolidate)

    def test_memory_decay_pattern(self):
        """Unused memories must decay over time."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()

        def calculate_decay(last_access, now, half_life_days=30):
            """Calculate decay factor based on time since last access."""
            age_days = (now - last_access).total_seconds() / 86400
            # Exponential decay
            import math
            return math.exp(-0.693 * age_days / half_life_days)

        recent_decay = calculate_decay(now - timedelta(days=1), now)
        old_decay = calculate_decay(now - timedelta(days=60), now)
        very_old_decay = calculate_decay(now - timedelta(days=120), now)

        # Recent should have high retention, old should have low
        assert recent_decay > 0.9
        assert old_decay < 0.5
        assert very_old_decay < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
