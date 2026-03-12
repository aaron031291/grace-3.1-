import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def main():
    orchestrator = get_llm_orchestrator()
    
    prompt = """
    A user has proposed a revolutionary architecture that translates natural language (NLP) into a deterministic "Braille-like" spatial bitmask array, and then runs all autonomous execution strictly via classical, deterministic mathematical topology (e.g., bitwise matching) instead of probabilistic vector similarity.
    
    The user is now asking: "Can we build this into a programming language?"
    
    The idea is to design a new programming language (let's call it "BrailleScript" or "Spindle") where the syntax itself compiles directly into these spatial bitmasks, and the language runtime executes purely via bitwise arithmetic and geometric overlays.
    
    Please provide a consensus evaluation of creating a new programming language based on this NLP + Braille bitmask + Deterministic Reasoning paradigm. What would its core features be? What would the compiler look like? What are the theoretical computer science implications of a language whose primary data structure is a composable semantic bitmask rather than traditional variables, floats, or objects?
    """
    
    print("Sending query to LLM Orchestrator (Consensus Mode) regarding a Braille-based Programming Language...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    print("\n" + "="*50)
    print("CONSENSUS RESULT - BRAILLE PROGRAMMING LANGUAGE:")
    print("="*50)
    if result.success:
        print(result.content.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        print("Task failed.")
        print("Audit trail:", result.audit_trail)

if __name__ == "__main__":
    main()
