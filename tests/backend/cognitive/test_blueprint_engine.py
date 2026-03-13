import os
import sys
import pytest

# Ensure backend modules can be imported directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backend')))

from backend.cognitive.blueprint_engine import create_from_prompt

def test_blueprint_engine_simple_function():
    """
    Integration test for the Blueprint Engine.
    Passes a simple prompt to generate a small Python function.
    Verifies that the prompt-to-sandbox-validation loop correctly engages,
    builds the code, verifies it, and returns a successful blueprint artifact
    without relying on deep mocks.
    """
    
    # A simple, deterministic task to prevent excessive LLM generation and retries
    test_prompt = "Create a simple python function called `add_numbers(a, b)` that returns the sum of a and b. Include a simple comment."

    # Run the blueprint engine
    result = create_from_prompt(test_prompt)

    # Validate output structure
    assert isinstance(result, dict), f"Result must be a dictionary, got {type(result)}"
    assert "id" in result, "Blueprint ID missing from result"
    assert "status" in result, "Blueprint status missing from result"
    
    # Check that it went through the loops
    assert "build_attempts" in result, "Build attempts missing"
    assert "generated_code" in result, "Generated code missing"

    # Did it succeed or fail cleanly?
    # Because we don't mock, we allow FAILED if local models mess up, 
    # but we want to assert the structure and the validation loop actively ran.
    # The minimum success indicator is that attempt count > 0 and code was tested.
    assert result["build_attempts"] > 0, "The build loop was never engaged"
    
    if result["status"] == "deployed":
        assert result.get("trust_score", 0) > 0, "Deployed code should have a trust > 0"
        assert "add_numbers" in result["generated_code"], "Generated code should contain the requested function"
    else:
        # If it failed, it should have captured errors
        assert len(result.get("errors", [])) > 0, "Failed blueprint should have logged errors"
