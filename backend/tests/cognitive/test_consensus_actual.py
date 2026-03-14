import pytest
from backend.cognitive.consensus_engine import layer2_consensus, ModelResponse, layer4_verify

def test_layer2_consensus_logic(monkeypatch):
    """Verify consensus synthesis parsing logic."""
    responses = [
        ModelResponse(model_id="kimi", model_name="Kimi", response="Yes, x is 42.", latency_ms=10),
        ModelResponse(model_id="opus", model_name="Opus", response="x seems to be 42 but could be 43.", latency_ms=15)
    ]
    
    # Mock LLM client
    class MockClient:
        def generate(self, *args, **kwargs):
            return "## Agreements\n- x is likely 42\n## Disagreements\n- Could be 43\n## Consensus\nAnswer is 42."
            
    import backend.cognitive.consensus_engine as ce
    monkeypatch.setattr(ce, "_get_client", lambda x: MockClient())
    
    consensus_text, agreements, disagreements = layer2_consensus("What is x?", responses)
    assert len(agreements) == 1
    assert "x is likely 42" in agreements[0]
    assert len(disagreements) == 1
    assert "Could be 43" in disagreements[0]
    assert "Answer is 42" in consensus_text

def test_layer4_verify_logic(monkeypatch):
    """Verify verification mechanisms block risky code / hallucinations."""
    
    # Mock trust engine and Z3 pipeline to avoid LLM calls
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

    from backend.cognitive.consensus_engine import layer4_verify
    # Good response
    res1 = layer4_verify("The sky is blue.", "What color is the sky?")
    assert "trust_score" in res1
    
    # Bad response (short + AI apology)
    res2 = layer4_verify("As an AI, I don't have answer", "test")
    assert res2["passed"] is False
    assert len(res2["hallucination_flags"]) > 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
