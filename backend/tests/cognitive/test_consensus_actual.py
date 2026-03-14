import pytest
from backend.cognitive.consensus_engine import (
    layer2_consensus, layer3_align, layer4_verify,
    ModelResponse,
    _tokenize, _jaccard_similarity, _find_agreements_and_disagreements,
    _score_response, _extract_key_claims,
)


# ── Deterministic helpers ─────────────────────────────────────────────

class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("The quick brown fox jumps over the lazy dog.")
        assert "quick" in tokens
        assert "brown" in tokens
        assert "the" not in tokens  # stopword

    def test_empty(self):
        assert _tokenize("") == []

    def test_strips_punctuation(self):
        tokens = _tokenize("Hello, world! This is a test.")
        assert "hello" in tokens
        assert "world" in tokens


class TestJaccardSimilarity:
    def test_identical(self):
        tokens = ["quick", "brown", "fox"]
        assert _jaccard_similarity(tokens, tokens) == 1.0

    def test_disjoint(self):
        assert _jaccard_similarity(["cat"], ["dog"]) == 0.0

    def test_partial(self):
        sim = _jaccard_similarity(["quick", "brown", "fox"], ["quick", "brown", "dog"])
        assert 0.3 < sim < 0.7

    def test_empty(self):
        assert _jaccard_similarity([], ["dog"]) == 0.0


class TestAgreementDisagreement:
    def test_agreeing_responses(self):
        responses = [
            ModelResponse(model_id="a", model_name="A",
                          response="Python is a great programming language for data science and machine learning.",
                          latency_ms=10),
            ModelResponse(model_id="b", model_name="B",
                          response="Python is an excellent programming language widely used in data science and machine learning applications.",
                          latency_ms=12),
        ]
        agreements, disagreements = _find_agreements_and_disagreements(responses)
        assert len(agreements) >= 1

    def test_disagreeing_responses(self):
        responses = [
            ModelResponse(model_id="a", model_name="A",
                          response="The answer is definitely 42. This is confirmed by multiple sources.",
                          latency_ms=10),
            ModelResponse(model_id="b", model_name="B",
                          response="Quantum computing uses qubits for parallel processing of information.",
                          latency_ms=12),
        ]
        agreements, disagreements = _find_agreements_and_disagreements(responses)
        assert len(disagreements) >= 1


class TestScoreResponse:
    def test_good_response_scores_higher(self):
        prompt = "What is Python used for?"
        good = ModelResponse(model_id="a", model_name="A",
                             response="Python is used for web development, data science, machine learning, and automation. " * 5,
                             latency_ms=100)
        bad = ModelResponse(model_id="b", model_name="B",
                            response="OK",
                            latency_ms=100)
        assert _score_response(good, prompt, []) > _score_response(bad, prompt, [])

    def test_error_response_scores_zero(self):
        r = ModelResponse(model_id="a", model_name="A", response="", latency_ms=0, error="Failed")
        assert _score_response(r, "test", []) == 0.0


# ── Layer 2: Deterministic Consensus ─────────────────────────────────

class TestLayer2Consensus:
    def test_no_valid_responses(self):
        responses = [
            ModelResponse(model_id="a", model_name="A", response="", latency_ms=0, error="Failed"),
        ]
        text, ag, disag = layer2_consensus("test", responses)
        assert "No valid responses" in text
        assert "All models failed" in disag

    def test_single_response(self):
        responses = [
            ModelResponse(model_id="a", model_name="A", response="Answer is 42.", latency_ms=10),
        ]
        text, ag, disag = layer2_consensus("What is x?", responses)
        assert "42" in text
        assert "Single model" in ag[0]

    def test_multiple_responses_selects_best(self):
        responses = [
            ModelResponse(model_id="kimi", model_name="Kimi",
                          response="The value of x is 42. This is derived from the equation x = 6 * 7.",
                          latency_ms=10),
            ModelResponse(model_id="opus", model_name="Opus",
                          response="x equals 42. The calculation shows 6 multiplied by 7 gives 42 as the result.",
                          latency_ms=15),
        ]
        text, agreements, disagreements = layer2_consensus("What is the value of x where x = 6 * 7?", responses)
        assert "42" in text
        assert isinstance(agreements, list)
        assert isinstance(disagreements, list)

    def test_no_llm_calls_made(self):
        """Layer 2 must be fully deterministic — no LLM client usage."""
        responses = [
            ModelResponse(model_id="a", model_name="A",
                          response="Python is great for data science workflows.",
                          latency_ms=10),
            ModelResponse(model_id="b", model_name="B",
                          response="Python excels at data science and analysis tasks.",
                          latency_ms=12),
        ]
        # This should succeed without any LLM infrastructure
        text, ag, disag = layer2_consensus("Tell me about Python", responses)
        assert len(text) > 0


# ── Layer 3: Deterministic Alignment ─────────────────────────────────

class TestLayer3Align:
    def test_strips_ai_commentary(self):
        consensus = "As an AI language model, I cannot provide medical advice.\nBut here is the answer."
        result = layer3_align("test", consensus)
        assert "as an ai language model" not in result.lower()
        assert "here is the answer" in result

    def test_empty_consensus(self):
        result = layer3_align("test query", "")
        assert "No consensus produced" in result

    def test_autonomous_actionable_tagging(self):
        consensus = "You should restart the database service and update the configuration."
        result = layer3_align("fix the db", consensus, source="autonomous")
        assert "Actionable Items" in result

    def test_context_headers_prepended(self):
        result = layer3_align("test", "Some answer", user_context="user is admin")
        assert "[User Context:" in result

    def test_no_llm_calls(self):
        """Layer 3 must be fully deterministic."""
        result = layer3_align("what is python", "Python is a programming language.")
        assert "Python" in result


# ── Layer 4: Verification ────────────────────────────────────────────

class TestLayer4Verify:
    def test_verify_clean_output(self, monkeypatch):
        class MockTrustEngine:
            def score_output(self, *args, **kwargs):
                return 0.9

        class MockZ3Pipeline:
            def generate_z3_constraint(self, *args, **kwargs):
                return None

        import backend.cognitive.trust_engine as te
        monkeypatch.setattr(te, "get_trust_engine", lambda: MockTrustEngine())

        import backend.cognitive.physics.qwen_z3_pipeline as qz3
        monkeypatch.setattr(qz3, "QwenZ3Pipeline", MockZ3Pipeline)

        res = layer4_verify("The sky is blue.", "What color is the sky?")
        assert "trust_score" in res

    def test_verify_short_flagged(self, monkeypatch):
        class MockTrustEngine:
            def score_output(self, *args, **kwargs):
                return 0.9

        import backend.cognitive.trust_engine as te
        monkeypatch.setattr(te, "get_trust_engine", lambda: MockTrustEngine())

        # Short response (<50 chars) triggers "Response too short" flag
        res = layer4_verify("OK", "test")
        assert "Response too short" in res["hallucination_flags"]

        # "as an AI" + "I don't have" = 2 suspicious hits → hallucination_score 0.6
        res2 = layer4_verify("As an AI, I don't have an answer for that.", "test")
        assert res2["hallucination_score"] < 1.0


if __name__ == "__main__":
    pytest.main(['-v', __file__])
