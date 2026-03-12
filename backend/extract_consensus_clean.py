import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def run_clean():
    orchestrator = get_llm_orchestrator()
    prompt = """
    We have built the finalized Braille Deterministic Engine MVP (Spindle language) and wired it into Grace's Action Router. 
    It translates LLM intents into a strict 64-bit spatial bitmask and evaluates it using deterministic bitwise physics to block hallucinations.
    
    Please provide a final concise validation and answer:
    1. What are the critical holes or gaps in this deterministic system right now? Where are the weaknesses?
    2. If this is wired into the front-end, can a user just talk to Grace and have Grace build exactly what is needed, assuming the user understands the system flow?
    3. The user asked: "If I use LLMs externally (on my phone) to internalize my thought process and bring it back into Grace, is that the best way? Or can I just use Grace's own consensus mechanism to build Grace?" Which approach is better?
    4. The user is shocked that it might be this simple to solve hallucinations using spatial bitmasks instead of neural networks. What are the caveats?
    """
    
    print("Executing task...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        context_documents=[
            "c:/Users/aaron/Desktop/grace-3.1--Aaron-new2/backend/cognitive/braille_compiler.py"
        ]
    )
    
    print("Writing to file...")
    with open("clean_output.md", "w", encoding="utf-8") as f:
        f.write(result.content)
    print("Done.")

if __name__ == "__main__":
    run_clean()
