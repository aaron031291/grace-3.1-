"""
Tests for consensus scoring in LLM Collaboration Hub.

Tests the calculate_consensus_scores() method and related functionality.
"""

import pytest
import sys
sys.path.insert(0, 'backend')

from backend.llm_orchestrator.llm_collaboration import LLMCollaborationHub


@pytest.fixture
def hub():
    """Create a LLMCollaborationHub instance for testing."""
    return LLMCollaborationHub()


class TestAgreementCalculation:
    """Test agreement calculation scenarios."""

    def test_all_same_responses_100_percent_agreement(self, hub):
        """All identical responses should yield 100% agreement."""
        responses = [
            {"content": "The answer is 42", "model": "model_a", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "The answer is 42", "model": "model_b", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "The answer is 42", "model": "model_c", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "The answer is 42", "model": "model_d", "confidence": 0.9, "historical_accuracy": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["agreement_rate"] == 1.0
        assert len(result["response_groups"]) == 1
        assert result["vote_distribution"]["response_1"] == 4

    def test_split_responses_50_percent_agreement(self, hub):
        """Two equally sized groups should yield 50% agreement."""
        responses = [
            {"content": "The sky is blue and water is wet", "model": "model_a", "confidence": 0.8, "historical_accuracy": 0.7},
            {"content": "The sky is blue and water is wet", "model": "model_b", "confidence": 0.8, "historical_accuracy": 0.7},
            {"content": "Cats meow and dogs bark loudly", "model": "model_c", "confidence": 0.8, "historical_accuracy": 0.7},
            {"content": "Cats meow and dogs bark loudly", "model": "model_d", "confidence": 0.8, "historical_accuracy": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["agreement_rate"] == 0.5
        assert len(result["response_groups"]) == 2

    def test_one_outlier_75_percent_agreement(self, hub):
        """Three agreeing and one outlier should yield 75% agreement."""
        responses = [
            {"content": "Python is a programming language used for web development", "model": "model_a", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "Python is a programming language used for web development", "model": "model_b", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "Python is a programming language used for web development", "model": "model_c", "confidence": 0.9, "historical_accuracy": 0.8},
            {"content": "Bananas are yellow tropical fruits grown in warm climates", "model": "model_d", "confidence": 0.5, "historical_accuracy": 0.5},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["agreement_rate"] == 0.75
        assert len(result["response_groups"]) == 2
        assert result["vote_distribution"]["response_1"] == 3


class TestResponseGrouping:
    """Test response grouping functionality."""

    def test_similar_responses_grouped_together(self, hub):
        """Similar responses should be grouped together."""
        responses = [
            {"content": "The function returns true when input is valid", "model": "model_a", "confidence": 0.8},
            {"content": "The function returns true when the input is valid", "model": "model_b", "confidence": 0.8},
            {"content": "Something completely different about cats", "model": "model_c", "confidence": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses, similarity_threshold=0.7)
        
        assert len(result["response_groups"]) == 2
        group_sizes = [len(g["members"]) for g in result["response_groups"]]
        assert 2 in group_sizes
        assert 1 in group_sizes

    def test_different_responses_separate_groups(self, hub):
        """Completely different responses should be in separate groups."""
        responses = [
            {"content": "Alpha beta gamma", "model": "model_a", "confidence": 0.8},
            {"content": "One two three", "model": "model_b", "confidence": 0.8},
            {"content": "Red blue green", "model": "model_c", "confidence": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses, similarity_threshold=0.7)
        
        assert len(result["response_groups"]) == 3
        for group in result["response_groups"]:
            assert len(group["members"]) == 1

    def test_threshold_affects_grouping(self, hub):
        """Similarity threshold should affect grouping behavior."""
        responses = [
            {"content": "The answer is approximately 42", "model": "model_a", "confidence": 0.8},
            {"content": "The answer is roughly 42", "model": "model_b", "confidence": 0.8},
            {"content": "The answer is about 42", "model": "model_c", "confidence": 0.8},
        ]
        
        result_strict = hub.calculate_consensus_scores(responses, similarity_threshold=0.95)
        result_loose = hub.calculate_consensus_scores(responses, similarity_threshold=0.5)
        
        assert len(result_strict["response_groups"]) >= len(result_loose["response_groups"])


class TestConfidenceWeighting:
    """Test confidence weighting in consensus scoring."""

    def test_higher_confidence_gets_more_weight(self, hub):
        """Higher confidence responses should have more weight in tie-breaking."""
        responses = [
            {"content": "Answer A", "model": "model_a", "confidence": 0.95, "historical_accuracy": 0.9},
            {"content": "Answer B", "model": "model_b", "confidence": 0.3, "historical_accuracy": 0.3},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == "Answer A"
        assert result["individual_scores"]["model_a"]["confidence"] == 0.95
        assert result["individual_scores"]["model_b"]["confidence"] == 0.3

    def test_low_confidence_has_less_impact(self, hub):
        """Low confidence responses should have less impact on consensus."""
        responses = [
            {"content": "High confidence answer", "model": "model_a", "confidence": 0.95, "historical_accuracy": 0.9},
            {"content": "Low confidence answer", "model": "model_b", "confidence": 0.1, "historical_accuracy": 0.2},
            {"content": "Low confidence answer", "model": "model_c", "confidence": 0.1, "historical_accuracy": 0.2},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == "High confidence answer"

    def test_historical_accuracy_affects_weight(self, hub):
        """Historical accuracy should contribute to weighting."""
        responses = [
            {"content": "Expert answer", "model": "expert", "confidence": 0.7, "historical_accuracy": 0.95},
            {"content": "Novice answer", "model": "novice", "confidence": 0.7, "historical_accuracy": 0.2},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["individual_scores"]["expert"]["historical_accuracy"] == 0.95
        assert result["individual_scores"]["novice"]["historical_accuracy"] == 0.2


class TestWinningResponseSelection:
    """Test winning response selection logic."""

    def test_most_votes_wins(self, hub):
        """Response with most votes should win."""
        responses = [
            {"content": "Popular answer", "model": "model_a", "confidence": 0.7},
            {"content": "Popular answer", "model": "model_b", "confidence": 0.7},
            {"content": "Popular answer", "model": "model_c", "confidence": 0.7},
            {"content": "Minority answer", "model": "model_d", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == "Popular answer"
        assert result["agreement_rate"] == 0.75

    def test_ties_broken_by_confidence(self, hub):
        """Ties should be broken by weighted confidence score."""
        responses = [
            {"content": "Answer A", "model": "model_a", "confidence": 0.9, "historical_accuracy": 0.9},
            {"content": "Answer B", "model": "model_b", "confidence": 0.3, "historical_accuracy": 0.3},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == "Answer A"

    def test_weighted_score_determines_winner(self, hub):
        """Combined weight (confidence + accuracy) should determine winner in ties."""
        responses = [
            {"content": "Answer A", "model": "model_a", "confidence": 0.8, "historical_accuracy": 0.8},
            {"content": "Answer B", "model": "model_b", "confidence": 0.4, "historical_accuracy": 0.4},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == "Answer A"


class TestOutputFormat:
    """Test output format of calculate_consensus_scores."""

    def test_returns_consensus_score_0_to_1(self, hub):
        """consensus_score should be between 0 and 1."""
        responses = [
            {"content": "Test", "model": "model_a", "confidence": 0.8},
            {"content": "Test", "model": "model_b", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "consensus_score" in result
        assert 0.0 <= result["consensus_score"] <= 1.0

    def test_returns_agreement_rate(self, hub):
        """Result should contain agreement_rate."""
        responses = [
            {"content": "Test", "model": "model_a", "confidence": 0.8},
            {"content": "Test", "model": "model_b", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "agreement_rate" in result
        assert isinstance(result["agreement_rate"], float)

    def test_returns_winning_response(self, hub):
        """Result should contain winning_response."""
        responses = [
            {"content": "Winner content", "model": "model_a", "confidence": 0.9},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "winning_response" in result
        assert result["winning_response"] == "Winner content"

    def test_returns_vote_distribution(self, hub):
        """Result should contain vote_distribution dict."""
        responses = [
            {"content": "A", "model": "model_a", "confidence": 0.8},
            {"content": "A", "model": "model_b", "confidence": 0.8},
            {"content": "B", "model": "model_c", "confidence": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "vote_distribution" in result
        assert isinstance(result["vote_distribution"], dict)
        total_votes = sum(result["vote_distribution"].values())
        assert total_votes == 3

    def test_returns_participating_models(self, hub):
        """Result should contain participating_models list."""
        responses = [
            {"content": "Test", "model": "gpt-4", "confidence": 0.8},
            {"content": "Test", "model": "claude-3", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "participating_models" in result
        assert "gpt-4" in result["participating_models"]
        assert "claude-3" in result["participating_models"]

    def test_returns_individual_scores(self, hub):
        """Result should contain individual_scores per model."""
        responses = [
            {"content": "Test", "model": "model_a", "confidence": 0.8, "historical_accuracy": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "individual_scores" in result
        assert "model_a" in result["individual_scores"]
        assert "confidence" in result["individual_scores"]["model_a"]
        assert "historical_accuracy" in result["individual_scores"]["model_a"]

    def test_returns_response_groups(self, hub):
        """Result should contain response_groups list."""
        responses = [
            {"content": "Test A", "model": "model_a", "confidence": 0.8},
            {"content": "Test B", "model": "model_b", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert "response_groups" in result
        assert isinstance(result["response_groups"], list)
        for group in result["response_groups"]:
            assert "group_id" in group
            assert "members" in group
            assert "representative" in group


class TestEdgeCases:
    """Test edge cases for consensus scoring."""

    def test_single_response(self, hub):
        """Single response should be handled correctly."""
        responses = [
            {"content": "Only answer", "model": "solo_model", "confidence": 0.85, "historical_accuracy": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["agreement_rate"] == 1.0
        assert result["winning_response"] == "Only answer"
        assert len(result["response_groups"]) == 1
        assert len(result["participating_models"]) == 1

    def test_empty_responses(self, hub):
        """Empty response list should be handled gracefully."""
        responses = []
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["consensus_score"] == 0.0
        assert result["agreement_rate"] == 0.0
        assert result["winning_response"] == ""
        assert result["vote_distribution"] == {}
        assert result["participating_models"] == []

    def test_all_different_responses(self, hub):
        """All different responses should each be in separate groups."""
        responses = [
            {"content": "Quantum mechanics explains particle behavior at atomic scales", "model": "model_a", "confidence": 0.7},
            {"content": "The French Revolution began in 1789 with the storming of Bastille", "model": "model_b", "confidence": 0.7},
            {"content": "Photosynthesis converts sunlight into chemical energy in plants", "model": "model_c", "confidence": 0.7},
            {"content": "JavaScript is commonly used for frontend web development", "model": "model_d", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert len(result["response_groups"]) == 4
        assert result["agreement_rate"] == 0.25

    def test_missing_confidence_uses_default(self, hub):
        """Missing confidence should use default value."""
        responses = [
            {"content": "No confidence", "model": "model_a"},
            {"content": "No confidence", "model": "model_b"},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["individual_scores"]["model_a"]["confidence"] == 0.5
        assert result["individual_scores"]["model_b"]["confidence"] == 0.5

    def test_missing_historical_accuracy_uses_default(self, hub):
        """Missing historical_accuracy should use default value."""
        responses = [
            {"content": "No accuracy", "model": "model_a", "confidence": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["individual_scores"]["model_a"]["historical_accuracy"] == 0.5

    def test_empty_content_responses(self, hub):
        """Empty content should be handled."""
        responses = [
            {"content": "", "model": "model_a", "confidence": 0.8},
            {"content": "", "model": "model_b", "confidence": 0.8},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert result["winning_response"] == ""
        assert len(result["response_groups"]) >= 1

    def test_model_name_generated_if_missing(self, hub):
        """Model name should be generated if not provided."""
        responses = [
            {"content": "Test", "confidence": 0.8},
            {"content": "Test", "confidence": 0.7},
        ]
        
        result = hub.calculate_consensus_scores(responses)
        
        assert len(result["participating_models"]) == 2
        assert "model_0" in result["participating_models"]
        assert "model_1" in result["participating_models"]


class TestTextSimilarityHelper:
    """Test the _calculate_text_similarity helper method."""

    def test_identical_texts_return_1(self, hub):
        """Identical texts should return similarity of 1.0."""
        similarity = hub._calculate_text_similarity("hello world", "hello world")
        assert similarity == 1.0

    def test_completely_different_texts_return_low(self, hub):
        """Completely different texts should return low similarity."""
        similarity = hub._calculate_text_similarity("abc", "xyz")
        assert similarity < 0.5

    def test_similar_texts_return_high(self, hub):
        """Similar texts should return high similarity."""
        similarity = hub._calculate_text_similarity(
            "The quick brown fox",
            "The quick brown dog"
        )
        assert similarity > 0.7

    def test_empty_text_returns_0(self, hub):
        """Empty text should return 0 similarity."""
        assert hub._calculate_text_similarity("", "text") == 0.0
        assert hub._calculate_text_similarity("text", "") == 0.0
        assert hub._calculate_text_similarity("", "") == 0.0

    def test_case_insensitive(self, hub):
        """Similarity should be case insensitive."""
        similarity = hub._calculate_text_similarity("HELLO", "hello")
        assert similarity == 1.0


class TestGroupSimilarResponsesHelper:
    """Test the _group_similar_responses helper method."""

    def test_groups_identical_responses(self, hub):
        """Identical responses should be grouped together."""
        contents = ["same", "same", "same"]
        models = ["a", "b", "c"]
        
        groups = hub._group_similar_responses(contents, models, threshold=0.8)
        
        assert len(groups) == 1
        assert len(groups[0]["members"]) == 3

    def test_separates_different_responses(self, hub):
        """Different responses should be in separate groups."""
        contents = ["alpha", "beta", "gamma"]
        models = ["a", "b", "c"]
        
        groups = hub._group_similar_responses(contents, models, threshold=0.8)
        
        assert len(groups) == 3

    def test_empty_contents_returns_empty(self, hub):
        """Empty contents should return empty groups."""
        groups = hub._group_similar_responses([], [], threshold=0.8)
        assert groups == []


class TestIntraGroupSimilarityHelper:
    """Test the _calculate_intra_group_similarity helper method."""

    def test_single_group_perfect_similarity(self, hub):
        """Single group with one member has perfect similarity."""
        groups = [{"members": ["a"], "avg_similarity": 1.0}]
        
        result = hub._calculate_intra_group_similarity(groups)
        
        assert result == 1.0

    def test_empty_groups_returns_0(self, hub):
        """Empty groups should return 0."""
        result = hub._calculate_intra_group_similarity([])
        assert result == 0.0

    def test_weighted_by_group_size(self, hub):
        """Larger groups should have more weight."""
        groups = [
            {"members": ["a", "b", "c"], "avg_similarity": 0.9},
            {"members": ["d"], "avg_similarity": 0.5},
        ]
        
        result = hub._calculate_intra_group_similarity(groups)
        
        expected = (0.9 * 3 + 0.5 * 1) / 4
        assert abs(result - expected) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
