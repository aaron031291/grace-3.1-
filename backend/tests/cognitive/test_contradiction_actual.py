import pytest
import asyncio
from datetime import datetime, timezone
from backend.cognitive.contradiction_detector import GraceCognitionLinter, ContradictionType, ContradictionSeverity
from backend.core.loop_output import GraceLoopOutput, ReasoningStep, LoopType

@pytest.fixture
def linter():
    return GraceCognitionLinter()

@pytest.mark.asyncio
async def test_logical_contradiction(linter):
    output = GraceLoopOutput(
        loop_id="test-1",
        loop_type=LoopType.REASONING,
        input_context={"prompt": "test"},
        started_at=datetime.now(timezone.utc),
        result_summary="This statement is false. This statement is true.",
        result={"answer": "none"},
        duration_ms=100,
        confidence=0.9
    )
    # Add a dummy reasoning step so it thinks there are steps
    output.add_reasoning_step("Testing", output="This statement is false. This statement is true.", confidence=0.9, duration_ms=10)
    
    result = await linter.lint(output)
    
    assert result.passed is False
    assert any(c.contradiction_type == ContradictionType.LOGICAL for c in result.contradictions)

@pytest.mark.asyncio
async def test_constitutional_contradiction(linter):
    output = GraceLoopOutput(
        loop_id="test-2",
        loop_type=LoopType.REASONING,
        input_context={"prompt": "test"},
        started_at=datetime.now(timezone.utc),
        result_summary="I will bypass safety protocols now.",
        result={"answer": "ok"},
        duration_ms=100,
        confidence=0.9
    )
    output.add_reasoning_step("Testing", output="I will bypass safety protocols now.", confidence=0.9, duration_ms=10)
    
    result = await linter.lint(output)
    
    assert result.passed is False
    assert result.has_critical is True
    assert any(c.contradiction_type == ContradictionType.CONSTITUTIONAL for c in result.contradictions)

@pytest.mark.asyncio
async def test_confidence_contradiction(linter):
    # High confidence but 0 reasoning steps
    output = GraceLoopOutput(
        loop_id="test-3",
        loop_type=LoopType.REASONING,
        input_context={"prompt": "test"},
        started_at=datetime.now(timezone.utc),
        result_summary="I am absolutely sure.",
        result={"answer": "ok"},
        duration_ms=100,
        confidence=0.95,
        reasoning_steps=[]
    )
    
    result = await linter.lint(output)
    
    assert any(c.contradiction_type == ContradictionType.CONFIDENCE for c in result.contradictions)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
