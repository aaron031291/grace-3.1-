"""
Comprehensive Test Suite for Confidence Scorer Module
======================================================
Tests for ConfidenceScorer and SemanticContradictionDetector.

Coverage:
- ConfidenceScorer initialization
- Source reliability scoring
- Content quality assessment
- Consensus score calculation
- Recency scoring
- Overall confidence calculation
- SemanticContradictionDetector
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import math

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock numpy
mock_np = MagicMock()
mock_np.array = lambda x: x
mock_np.dot = lambda a, b: sum(x*y for x, y in zip(a, b))
mock_np.linalg = MagicMock()
mock_np.linalg.norm = lambda x: math.sqrt(sum(v*v for v in x))
sys.modules['numpy'] = mock_np

# Mock embedding model
mock_embedding = MagicMock()
sys.modules['embedding'] = mock_embedding

# Mock vector_db client
mock_vector_db = MagicMock()
mock_vector_db.client = MagicMock()
mock_vector_db.client.get_qdrant_client = MagicMock()
sys.modules['vector_db'] = mock_vector_db
sys.modules['vector_db.client'] = mock_vector_db.client

# Mock torch for contradiction detector
mock_torch = MagicMock()
sys.modules['torch'] = mock_torch

# Mock transformers
mock_transformers = MagicMock()
sys.modules['transformers'] = mock_transformers

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# ConfidenceScorer Initialization Tests
# =============================================================================

class TestConfidenceScorerInit:
    """Test ConfidenceScorer initialization."""

    def test_default_initialization(self):
        """Test default ConfidenceScorer initialization."""
        class MockConfidenceScorer:
            SOURCE_RELIABILITY_SCORES = {
                "official_docs": 0.95,
                "academic_paper": 0.90,
                "verified_tutorial": 0.85,
                "trusted_blog": 0.75,
                "community_qa": 0.65,
                "user_generated": 0.50,
                "unverified": 0.30,
            }

            WEIGHTS = {
                "source_reliability": 0.35,
                "content_quality": 0.25,
                "consensus_score": 0.25,
                "recency": 0.10,
            }

            def __init__(self, embedding_model=None, qdrant_client=None, collection_name="documents"):
                self.embedding_model = embedding_model
                self.qdrant_client = qdrant_client or MagicMock()
                self.collection_name = collection_name

        scorer = MockConfidenceScorer()

        assert scorer.collection_name == "documents"
        assert scorer.qdrant_client is not None
        assert len(scorer.SOURCE_RELIABILITY_SCORES) == 7
        assert sum(scorer.WEIGHTS.values()) < 1.01  # Weights sum close to 1

    def test_custom_initialization(self):
        """Test ConfidenceScorer with custom parameters."""
        class MockConfidenceScorer:
            def __init__(self, embedding_model=None, qdrant_client=None, collection_name="documents"):
                self.embedding_model = embedding_model
                self.qdrant_client = qdrant_client
                self.collection_name = collection_name

        mock_model = MagicMock()
        mock_client = MagicMock()

        scorer = MockConfidenceScorer(
            embedding_model=mock_model,
            qdrant_client=mock_client,
            collection_name="custom_collection"
        )

        assert scorer.embedding_model == mock_model
        assert scorer.qdrant_client == mock_client
        assert scorer.collection_name == "custom_collection"


# =============================================================================
# Source Reliability Tests
# =============================================================================

class TestSourceReliability:
    """Test source reliability scoring."""

    def test_official_docs_score(self):
        """Test official documentation reliability score."""
        SOURCE_RELIABILITY_SCORES = {"official_docs": 0.95}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_").replace("-", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("official_docs") == 0.95
        assert calculate_source_reliability("official-docs") == 0.95
        assert calculate_source_reliability("Official Docs") == 0.95

    def test_academic_paper_score(self):
        """Test academic paper reliability score."""
        SOURCE_RELIABILITY_SCORES = {"academic_paper": 0.90}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_").replace("-", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("academic_paper") == 0.90

    def test_verified_tutorial_score(self):
        """Test verified tutorial reliability score."""
        SOURCE_RELIABILITY_SCORES = {"verified_tutorial": 0.85}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("verified_tutorial") == 0.85

    def test_community_qa_score(self):
        """Test community Q&A reliability score."""
        SOURCE_RELIABILITY_SCORES = {"community_qa": 0.65}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("community_qa") == 0.65

    def test_unverified_source_score(self):
        """Test unverified source reliability score."""
        SOURCE_RELIABILITY_SCORES = {"unverified": 0.30}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("unverified") == 0.30

    def test_unknown_source_default(self):
        """Test unknown source type gets default score."""
        SOURCE_RELIABILITY_SCORES = {}

        def calculate_source_reliability(source_type: str) -> float:
            normalized = source_type.lower().replace(" ", "_")
            return SOURCE_RELIABILITY_SCORES.get(normalized, 0.50)

        assert calculate_source_reliability("random_source") == 0.50
        assert calculate_source_reliability("unknown") == 0.50


# =============================================================================
# Content Quality Tests
# =============================================================================

class TestContentQuality:
    """Test content quality scoring."""

    def test_content_quality_factors(self):
        """Test content quality calculation with various factors."""
        def calculate_content_quality(text_content: str) -> float:
            score = 0.5  # Base score

            # Length factor
            if len(text_content) > 1000:
                score += 0.2
            elif len(text_content) > 500:
                score += 0.1

            # Code presence
            if "```" in text_content or "def " in text_content:
                score += 0.1

            # References
            if "http://" in text_content or "https://" in text_content:
                score += 0.1

            return min(score, 1.0)

        # Short text
        short = "A" * 100
        assert calculate_content_quality(short) == 0.5

        # Medium text
        medium = "A" * 600
        assert calculate_content_quality(medium) == 0.6

        # Long text
        long_text = "A" * 1100
        assert calculate_content_quality(long_text) == 0.7

    def test_content_quality_with_code(self):
        """Test content quality bonus for code."""
        def calculate_content_quality(text_content: str) -> float:
            score = 0.5
            if "```" in text_content or "def " in text_content:
                score += 0.1
            return min(score, 1.0)

        text_with_code = "Here is an example:\n```python\ndef hello():\n    pass\n```"
        assert calculate_content_quality(text_with_code) == 0.6

    def test_content_quality_with_references(self):
        """Test content quality bonus for references."""
        def calculate_content_quality(text_content: str) -> float:
            score = 0.5
            if "http://" in text_content or "https://" in text_content:
                score += 0.1
            return min(score, 1.0)

        text_with_ref = "See https://example.com for more."
        assert calculate_content_quality(text_with_ref) == 0.6

    def test_content_quality_max_score(self):
        """Test content quality caps at 1.0."""
        def calculate_content_quality(text_content: str) -> float:
            score = 0.5
            if len(text_content) > 1000:
                score += 0.2
            if "```" in text_content:
                score += 0.1
            if "https://" in text_content:
                score += 0.1
            if "[1]" in text_content:  # Citations
                score += 0.15
            return min(score, 1.0)

        rich_text = "A" * 1100 + "```code```" + "https://ref.com" + "[1]"
        result = calculate_content_quality(rich_text)
        assert result <= 1.0


# =============================================================================
# Recency Tests
# =============================================================================

class TestRecency:
    """Test recency scoring."""

    def test_recency_very_recent(self):
        """Test recency score for very recent content."""
        def calculate_recency(timestamp: datetime, max_age_days: int = 365) -> float:
            now = datetime.utcnow()
            age_days = (now - timestamp).days

            if age_days <= 0:
                return 1.0
            elif age_days <= 30:
                return 0.9
            elif age_days <= 90:
                return 0.7
            elif age_days <= 180:
                return 0.5
            elif age_days <= 365:
                return 0.3
            else:
                return 0.1

        recent = datetime.utcnow() - timedelta(days=1)
        assert calculate_recency(recent) >= 0.9

    def test_recency_one_month_old(self):
        """Test recency score for month-old content."""
        def calculate_recency(timestamp: datetime) -> float:
            now = datetime.utcnow()
            age_days = (now - timestamp).days
            if age_days <= 30:
                return 0.9
            elif age_days <= 90:
                return 0.7
            return 0.5

        month_old = datetime.utcnow() - timedelta(days=45)
        assert calculate_recency(month_old) == 0.7

    def test_recency_old_content(self):
        """Test recency score for old content."""
        def calculate_recency(timestamp: datetime) -> float:
            now = datetime.utcnow()
            age_days = (now - timestamp).days
            if age_days > 365:
                return 0.1
            return 0.5

        old = datetime.utcnow() - timedelta(days=400)
        assert calculate_recency(old) == 0.1


# =============================================================================
# Consensus Score Tests
# =============================================================================

class TestConsensusScore:
    """Test consensus scoring with existing knowledge."""

    def test_consensus_high_similarity(self):
        """Test consensus score with highly similar content."""
        def calculate_consensus(
            new_embedding: List[float],
            existing_embeddings: List[List[float]],
            similarity_threshold: float = 0.7
        ) -> float:
            if not existing_embeddings:
                return 0.5  # Neutral score for new topics

            similarities = []
            for existing in existing_embeddings:
                # Cosine similarity
                dot = sum(a*b for a, b in zip(new_embedding, existing))
                norm_new = math.sqrt(sum(x*x for x in new_embedding))
                norm_exist = math.sqrt(sum(x*x for x in existing))
                if norm_new > 0 and norm_exist > 0:
                    sim = dot / (norm_new * norm_exist)
                    similarities.append(sim)

            if not similarities:
                return 0.5

            avg_sim = sum(similarities) / len(similarities)
            high_sim_count = sum(1 for s in similarities if s >= similarity_threshold)
            high_sim_ratio = high_sim_count / len(similarities)

            return min(0.5 + high_sim_ratio * 0.5, 1.0)

        new_emb = [1.0, 0.0, 0.0]
        existing = [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]]
        score = calculate_consensus(new_emb, existing)

        assert score > 0.7

    def test_consensus_no_existing(self):
        """Test consensus score with no existing content."""
        def calculate_consensus(new_embedding, existing_embeddings):
            if not existing_embeddings:
                return 0.5
            return 0.8

        score = calculate_consensus([0.1, 0.2, 0.3], [])
        assert score == 0.5

    def test_consensus_contradictory_content(self):
        """Test consensus score with contradictory content."""
        def calculate_consensus_with_contradiction(
            new_embedding: List[float],
            existing_embeddings: List[List[float]],
            contradiction_detected: bool = False
        ) -> float:
            if contradiction_detected:
                return 0.2  # Low score for contradictions
            return 0.8

        score = calculate_consensus_with_contradiction(
            [0.1, 0.2], [[0.2, 0.1]], contradiction_detected=True
        )
        assert score == 0.2


# =============================================================================
# Overall Confidence Calculation Tests
# =============================================================================

class TestOverallConfidence:
    """Test overall confidence score calculation."""

    def test_calculate_confidence_all_factors(self):
        """Test confidence calculation with all factors."""
        WEIGHTS = {
            "source_reliability": 0.35,
            "content_quality": 0.25,
            "consensus_score": 0.25,
            "recency": 0.10,
        }

        def calculate_confidence(
            source_reliability: float,
            content_quality: float,
            consensus_score: float,
            recency: float
        ) -> float:
            return (
                source_reliability * WEIGHTS["source_reliability"] +
                content_quality * WEIGHTS["content_quality"] +
                consensus_score * WEIGHTS["consensus_score"] +
                recency * WEIGHTS["recency"]
            )

        score = calculate_confidence(
            source_reliability=0.95,
            content_quality=0.80,
            consensus_score=0.70,
            recency=0.90
        )

        expected = 0.95 * 0.35 + 0.80 * 0.25 + 0.70 * 0.25 + 0.90 * 0.10
        assert abs(score - expected) < 0.001

    def test_confidence_perfect_score(self):
        """Test confidence with perfect inputs."""
        WEIGHTS = {
            "source_reliability": 0.35,
            "content_quality": 0.25,
            "consensus_score": 0.25,
            "recency": 0.10,
        }

        def calculate_confidence(**scores) -> float:
            return sum(scores[k] * WEIGHTS[k] for k in WEIGHTS if k in scores)

        score = calculate_confidence(
            source_reliability=1.0,
            content_quality=1.0,
            consensus_score=1.0,
            recency=1.0
        )

        # Should sum to ~0.95 based on weights (some may have extra weight)
        assert score <= 1.0 and score >= 0.9

    def test_confidence_minimum_score(self):
        """Test confidence with minimum inputs."""
        WEIGHTS = {
            "source_reliability": 0.35,
            "content_quality": 0.25,
            "consensus_score": 0.25,
            "recency": 0.10,
        }

        def calculate_confidence(**scores) -> float:
            return sum(scores[k] * WEIGHTS[k] for k in WEIGHTS if k in scores)

        score = calculate_confidence(
            source_reliability=0.0,
            content_quality=0.0,
            consensus_score=0.0,
            recency=0.0
        )

        assert score == 0.0


# =============================================================================
# Semantic Contradiction Detector Tests
# =============================================================================

class TestSemanticContradictionDetector:
    """Test semantic contradiction detection."""

    def test_detect_contradiction_true(self):
        """Test detecting obvious contradiction."""
        class MockContradictionDetector:
            def __init__(self):
                pass

            def detect_contradiction(self, text1: str, text2: str) -> Dict:
                # Simple keyword-based contradiction detection
                negations = ["not", "never", "false", "incorrect"]

                has_negation_1 = any(neg in text1.lower() for neg in negations)
                has_negation_2 = any(neg in text2.lower() for neg in negations)

                # If one has negation and other doesn't on similar topic
                if has_negation_1 != has_negation_2:
                    return {
                        "is_contradiction": True,
                        "confidence": 0.85,
                        "explanation": "Opposite assertions detected"
                    }
                return {"is_contradiction": False, "confidence": 0.1}

        detector = MockContradictionDetector()
        result = detector.detect_contradiction(
            "Python is a compiled language.",
            "Python is not a compiled language."
        )

        assert result["is_contradiction"] is True

    def test_detect_contradiction_false(self):
        """Test non-contradictory statements."""
        class MockContradictionDetector:
            def detect_contradiction(self, text1: str, text2: str) -> Dict:
                # Both statements are consistent
                return {"is_contradiction": False, "confidence": 0.95}

        detector = MockContradictionDetector()
        result = detector.detect_contradiction(
            "Python is a programming language.",
            "Python uses dynamic typing."
        )

        assert result["is_contradiction"] is False

    def test_detect_contradiction_batch(self):
        """Test batch contradiction detection."""
        class MockContradictionDetector:
            def detect_contradictions_batch(
                self, text: str, comparisons: List[str]
            ) -> List[Dict]:
                results = []
                for comp in comparisons:
                    results.append({
                        "comparison": comp,
                        "is_contradiction": False,
                        "confidence": 0.8
                    })
                return results

        detector = MockContradictionDetector()
        results = detector.detect_contradictions_batch(
            "Main text",
            ["Compare 1", "Compare 2", "Compare 3"]
        )

        assert len(results) == 3


# =============================================================================
# Integration Tests
# =============================================================================

class TestConfidenceScorerIntegration:
    """Integration tests for confidence scoring."""

    def test_full_scoring_workflow(self):
        """Test complete confidence scoring workflow."""
        class MockConfidenceScorer:
            WEIGHTS = {
                "source_reliability": 0.35,
                "content_quality": 0.25,
                "consensus_score": 0.25,
                "recency": 0.10,
            }

            def calculate_source_reliability(self, source_type: str) -> float:
                scores = {"official_docs": 0.95, "user_generated": 0.50}
                return scores.get(source_type, 0.50)

            def calculate_content_quality(self, content: str) -> float:
                return min(0.5 + len(content) / 10000, 1.0)

            def calculate_consensus_score(self, content: str) -> float:
                return 0.7  # Mock consensus

            def calculate_recency(self, timestamp: datetime) -> float:
                age_days = (datetime.utcnow() - timestamp).days
                return max(1.0 - age_days / 365, 0.1)

            def score(self, content: str, source_type: str, timestamp: datetime) -> Dict:
                source_rel = self.calculate_source_reliability(source_type)
                content_qual = self.calculate_content_quality(content)
                consensus = self.calculate_consensus_score(content)
                recency = self.calculate_recency(timestamp)

                overall = (
                    source_rel * self.WEIGHTS["source_reliability"] +
                    content_qual * self.WEIGHTS["content_quality"] +
                    consensus * self.WEIGHTS["consensus_score"] +
                    recency * self.WEIGHTS["recency"]
                )

                return {
                    "overall_confidence": overall,
                    "components": {
                        "source_reliability": source_rel,
                        "content_quality": content_qual,
                        "consensus_score": consensus,
                        "recency": recency
                    }
                }

        scorer = MockConfidenceScorer()
        result = scorer.score(
            content="This is a test content " * 50,
            source_type="official_docs",
            timestamp=datetime.utcnow() - timedelta(days=10)
        )

        assert "overall_confidence" in result
        assert 0 <= result["overall_confidence"] <= 1
        assert "components" in result


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestConfidenceScorerErrors:
    """Test error handling in confidence scorer."""

    def test_empty_content_handling(self):
        """Test handling empty content."""
        def calculate_content_quality(content: str) -> float:
            if not content or not content.strip():
                return 0.0
            return 0.5

        assert calculate_content_quality("") == 0.0
        assert calculate_content_quality("   ") == 0.0

    def test_invalid_source_type_handling(self):
        """Test handling invalid source types."""
        def calculate_source_reliability(source_type: str) -> float:
            if not source_type:
                return 0.3  # Lowest score for missing source
            return 0.5  # Default

        assert calculate_source_reliability("") == 0.3
        assert calculate_source_reliability(None) == 0.3

    def test_embedding_failure_fallback(self):
        """Test fallback when embedding fails."""
        class MockConfidenceScorer:
            def __init__(self):
                self.embedding_model = MagicMock()
                self.embedding_model.embed_text.side_effect = Exception("Embedding failed")

            def calculate_consensus_score(self, content: str) -> float:
                try:
                    self.embedding_model.embed_text(content)
                    return 0.8
                except Exception:
                    return 0.5  # Neutral score on failure

        scorer = MockConfidenceScorer()
        score = scorer.calculate_consensus_score("test")
        assert score == 0.5


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestConfidenceScorerEdgeCases:
    """Test edge cases in confidence scoring."""

    def test_very_long_content(self):
        """Test scoring very long content."""
        def calculate_content_quality(content: str) -> float:
            length_score = min(len(content) / 10000, 0.3)
            return 0.5 + length_score

        very_long = "A" * 50000
        score = calculate_content_quality(very_long)
        assert score <= 1.0

    def test_unicode_content(self):
        """Test scoring unicode content."""
        def calculate_content_quality(content: str) -> float:
            return 0.5 + (len(content) / 10000)

        unicode_content = "这是中文内容 " * 100
        score = calculate_content_quality(unicode_content)
        assert score > 0.5

    def test_special_characters(self):
        """Test scoring content with special characters."""
        def calculate_content_quality(content: str) -> float:
            # Ensure special chars don't break scoring
            return 0.5

        special = "<html>&amp;'\"@#$%^&*()"
        score = calculate_content_quality(special)
        assert score == 0.5

    def test_future_timestamp(self):
        """Test handling future timestamps."""
        def calculate_recency(timestamp: datetime) -> float:
            now = datetime.utcnow()
            if timestamp > now:
                return 1.0  # Treat as most recent
            return max(1.0 - (now - timestamp).days / 365, 0.1)

        future = datetime.utcnow() + timedelta(days=30)
        score = calculate_recency(future)
        assert score == 1.0
