import pytest
import sys
from unittest.mock import MagicMock, patch
from backend.cognitive.pipeline import CognitivePipeline, PipelineContext, _classify_prompt

def test_classify_prompt():
    assert _classify_prompt("delete all files") == "destructive"
    assert _classify_prompt("fix the error") == "bug_fix"
    assert _classify_prompt("write a new function") == "code_generation"
    assert _classify_prompt("explain how this works") == "question"
    assert _classify_prompt("hello world") == "general"

def test_pipeline_ooda_stage():
    pipeline = CognitivePipeline()
    ctx = PipelineContext(prompt="fix the broken function")
    
    # Mock systems to avoid real execution
    sys.modules["settings"] = MagicMock()
    sys.modules["database.session"] = MagicMock()
    
    pipeline._stage_ooda(ctx)
    
    assert "ooda" in ctx.stages_passed
    assert ctx.ooda["prompt_type"] == "bug_fix"
    assert ctx.ooda["approach"] == "direct"

def test_pipeline_ambiguity_stage():
    pipeline = CognitivePipeline()
    ctx = PipelineContext(prompt="test prompt")
    ctx.ooda = {"file_count": 0, "approach": "direct"}
    
    pipeline._stage_ambiguity(ctx)
    
    assert "ambiguity" in ctx.stages_passed
    assert ctx.ambiguity["has_blocking"] is True

def test_pipeline_invariants_stage():
    pipeline = CognitivePipeline()
    ctx = PipelineContext(prompt="fix bugs")
    # Simulate missing OODA
    pipeline._stage_invariants(ctx)
    
    assert "invariants" in ctx.stages_passed
    assert ctx.invariants["valid"] is True
    assert "ooda_incomplete: OODA observation not completed" in ctx.invariants["warnings"]

@patch("backend.cognitive.pipeline.CognitivePipeline._stage_generate")
def test_pipeline_run_flow(mock_generate):
    pipeline = CognitivePipeline()
    
    ctx = pipeline.run("write a test", skip_stages=["generate", "contradiction", "hallucination", "genesis", "trust_post"])
    
    assert "time_sense" in ctx.stages_passed or "time_sense" in ctx.stages_failed
    assert "ooda" in ctx.stages_passed or "ooda" in ctx.stages_failed
    assert "ambiguity" in ctx.stages_passed or "ambiguity" in ctx.stages_failed
    assert "invariants" in ctx.stages_passed or "invariants" in ctx.stages_failed
    assert mock_generate.call_count == 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
