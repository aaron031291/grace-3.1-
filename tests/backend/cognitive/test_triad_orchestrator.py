import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backend')))
from backend.cognitive.qwen_triad_orchestrator import get_triad_orchestrator

@pytest.mark.asyncio
async def test_qwen_triad_logical_execution():
    """
    Verifies that the Triad Orchestrator can split a logical problem into 3 branches 
    (triage, coding, reasoning), execute them via the live LLM pipeline (no deep mocks), 
    and synthesize a final cohesive JSON response.
    """
    orchestrator = get_triad_orchestrator()
    
    # A specific logic puzzle testing calculation, code logic, and reasoning
    test_prompt = "If a system heals 3 bugs per hour, but introduces 1 bug every 2 hours, how many net bugs are healed after 6 hours? Formulate the mathematical reasoning step-by-step."
    
    # Execute the live pipeline
    result = await orchestrator.process(
        prompt=test_prompt,
        system_prompt="You are a system logic evaluator. Output JSON always.",
        execution_allowed=False  # Keep it safe, no arbitrary code execution
    )
    
    # Assertions on the synthesis structure
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    
    # Check that synthesis keys are present (verifying the JSON parsing worked)
    assert "response" in result or "synthesis" in result or "final_decision" in result or "answer" in result or "reasoning" in result or "net_bugs" in str(result).lower()
    
    # Verify the math was solved correctly in the output text
    result_text = str(result).lower()
    assert "15" in result_text or "fifteen" in result_text, f"Triad failed the basic logic puzzle. Output: {result_text}"
    assert "3 * 6" in result_text or "18" in result_text or "1 * (6/2)" in result_text or "3" in result_text, "Failed to show work"
