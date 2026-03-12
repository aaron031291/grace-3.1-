import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def run_pass_2():
    print("==================================================")
    print(" RUNNING BRAILLE MVP - PASS 2 (CODE REVIEW)")
    print("==================================================")
    
    with open("cognitive/braille_compiler.py", "r") as f:
        code = f.read()
        
    prompt = f"""
    The development team has moved to Iteration 2 of the Braille Deterministic Architecture, addressing your feedback on privilege isolation and edge cases.

    Here is the Iteration 2 code for the MVP (`backend/cognitive/braille_compiler.py`):
    ```python
    {code}
    ```

    Please review this Iteration 2 code as the Consensus Mechanism. 
    1. Does this successfully fix the gap regarding Privilege Escalation from Iteration 1?
    2. Does returning strict Error Topology Codes (like "E02_PRIV_ESCALATION") make the engine safer?
    3. What is the FINAL critical gap or blind spot needed for Iteration 3 to make this engine robust enough for production deployment within a closed agent loop? (Identify max 2 actionable things).
    """
    
    orchestrator = get_llm_orchestrator()
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    if result.success:
        with open("pass2_review.txt", "w") as f:
            f.write(result.content.encode('cp1252', errors='replace').decode('cp1252'))
        print("Pass 2 successful. Output saved to pass2_review.txt")
    else:
        print("Pass 2 task failed.")

if __name__ == "__main__":
    run_pass_2()
