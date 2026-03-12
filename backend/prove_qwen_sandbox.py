import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
from cognitive.physics.z3_sandbox import Z3Sandbox

def test_qwen_sandbox():
    print("\n========== SPINDLE QWEN SANDBOX TEST ==========")
    pipeline = QwenZ3Pipeline()
    sandbox = Z3Sandbox()
    
    test_rule = "Standard users cannot delete active databases."
    print(f"\n[PHASE 1] Asking Qwen to Generate Formal Proof for: '{test_rule}'")
    
    z3_code = pipeline.generate_z3_constraint(test_rule)
    
    if not z3_code:
        print("[FAILED] Pipeline returned no code.")
        return
        
    print(f"\n[PHASE 2] Qwen Output:\n{z3_code}")
    print("\n[PHASE 3] Executing in Z3 subprocess sandbox...")
    
    success, output = sandbox.test_generated_constraint(z3_code)
    
    if success:
        print(f"[PASSED] Sandbox verified the logic: {output}")
    else:
        print(f"[FAILED] Sandbox rejected the logic: {output}")

if __name__ == "__main__":
    test_qwen_sandbox()
