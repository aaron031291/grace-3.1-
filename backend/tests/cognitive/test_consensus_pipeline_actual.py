import pytest
from backend.cognitive.consensus_pipeline import ConsensusPipeline

def test_maker_checker_loop_immediate_approval(monkeypatch):
    """Test when checker immediately approves the maker's output."""
    class MockSynaptic:
        def dispatch(self, model_id, prompt):
            if "checker" in prompt.lower():
                return "APPROVED"
            return "This is my initial draft."
        
        def log_to_memory(self, *args, **kwargs):
            pass

    import backend.cognitive.consensus_pipeline as cp
    monkeypatch.setattr(cp, "get_synaptic_core", lambda: MockSynaptic())

    pipeline = ConsensusPipeline()
    result = pipeline.run_maker_checker("Write a function", max_iterations=3)
    
    assert result["final_output"] == "This is my initial draft."
    assert result["iterations"] == 1
    # history has maker's first draft, checker's review (approved)
    assert len(result["history"]) == 2

def test_maker_checker_loop_with_revision(monkeypatch):
    """Test when checker requires a revision before approval."""
    call_count = {"maker": 0, "checker": 0}
    
    class MockSynaptic:
        def dispatch(self, model_id, prompt):
            if model_id == "opus": # checker
                call_count["checker"] += 1
                if call_count["checker"] == 1:
                    return "Need more detail on error handling."
                return "APPROVED"
            else: # maker
                call_count["maker"] += 1
                if call_count["maker"] == 1:
                    return "Draft 1"
                return "Draft 2 with error handling."
                
        def log_to_memory(self, *args, **kwargs):
            pass

    import backend.cognitive.consensus_pipeline as cp
    monkeypatch.setattr(cp, "get_synaptic_core", lambda: MockSynaptic())

    pipeline = ConsensusPipeline()
    result = pipeline.run_maker_checker("Write a function", maker_model="qwen", checker_model="opus", max_iterations=3)
    
    assert result["final_output"] == "Draft 2 with error handling."
    assert result["iterations"] == 2
    # Draft 1 -> Critique 1 -> Draft 2 -> Critique 2 (APPROVED) -> Exit
    assert len(result["history"]) == 4

if __name__ == "__main__":
    pytest.main(['-v', __file__])
