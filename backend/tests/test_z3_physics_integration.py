import os
import pytest

from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
from cognitive.physics.z3_sandbox import Z3Sandbox

def test_z3_pipeline_and_sandbox():
    """Test generating a Z3 constraint and verifying it in the sandbox."""
    pipeline = QwenZ3Pipeline()
    sandbox = Z3Sandbox()

    # Rule: A standard user cannot delete a database
    rule = "A standard user (PRIV_USER) cannot execute DELETE against a DOMAIN_DATABASE"
    
    constraint_code = pipeline.generate_z3_constraint(rule)
    print("--- Generated Z3 Code ---")
    print(constraint_code)
    
    assert constraint_code is not None, "Pipeline failed to generate Z3 code."
    assert "self.solver.add" in constraint_code, "Pipeline did not generate valid solver logic."

    is_valid, msg = sandbox.test_generated_constraint(constraint_code)
    print("--- Sandbox Validation ---")
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    
    assert is_valid, f"Sandbox rejected the valid constraint: {msg}"

if __name__ == "__main__":
    test_z3_pipeline_and_sandbox()
