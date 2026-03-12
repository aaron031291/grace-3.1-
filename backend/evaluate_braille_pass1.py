import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def run_pass_1():
    print("==================================================")
    print(" RUNNING BRAILLE MVP - PASS 1 (CODE REVIEW)")
    print("==================================================")
    
    with open("cognitive/braille_compiler.py", "r") as f:
        code = f.read()
        
    prompt = f"""
    The development team has built Iteration 1 (MVP) of the Braille Deterministic Architecture, integrating NLP to JSON compilation, 32-bit dict mapping, and Topological Guard execution.

    Here is the code for the MVP (`backend/cognitive/braille_compiler.py`):
    ```python
    {code}
    ```

    Please review this MVP architecture as the Consensus Mechanism. 
    1. Does this successfully implement the NLP-to-Bitmask translation + Bitwise execution theory?
    2. What are the immediate gaps or blind spots in this Pass 1 implementation that the human/agent team should fix in Iteration 2? (Identify maximum 3 actionable things).
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
        with open("pass1_review.txt", "w") as f:
            f.write(result.content.encode('cp1252', errors='replace').decode('cp1252'))
        print("Pass 1 successful. Output saved to pass1_review.txt")
    else:
        print("Pass 1 task failed.")

if __name__ == "__main__":
    run_pass_1()
