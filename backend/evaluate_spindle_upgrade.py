import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def run_upgrade_query():
    orchestrator = get_llm_orchestrator()
    if not orchestrator:
        print("Failed to initialize LLM Orchestrator.")
        return
        
    prompt = """
    We have successfully built the Spindle/Braille MVP, a deterministic bitmask physics engine that blocks LLM hallucinations from executing. 
    
    Now we need the strategic upgrade path. Please answer the following questions comprehensively:
    
    1. What is the upgrade to this MVP? How do we go beyond this and harden the system to make the current weaknesses (like the hardcoded 64-bit limit and lack of error recovery) much more robust?
    2. Can we get Qwen to code this Spindle logic for us automatically now? How do we push this throughout Grace's entire system so we are fully production-ready to build Grace *using* Spindle rules?
    3. The goal is to type into the front-end and just "build, build, build" leveraging CPU power predictably. How do we achieve that loop? What are the next highest leverage points to build?
    4. Crucially: Are there any existing libraries, algorithms, ML models, DL models, or formal verification systems (like Z3, AST parsing, Semantic Hashing, TLA+, or constraint solvers) that we can re-engineer, reverse-engineer, or repurpose to accelerate this? We want to avoid reinventing the wheel if math/logic solvers already exist that can be wired into Grace.
    """
    
    print("Executing upgrade query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        context_documents=[
            "c:/Users/aaron/Desktop/grace-3.1--Aaron-new2/backend/cognitive/braille_compiler.py"
        ]
    )
    
    print("Writing results...")
    with open("consensus_upgrade_output.md", "w", encoding="utf-8") as f:
        f.write(result.content)
    print("Done. Output saved to consensus_upgrade_output.md")

if __name__ == "__main__":
    run_upgrade_query()
