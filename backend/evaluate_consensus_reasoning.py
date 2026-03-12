import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def main():
    orchestrator = get_llm_orchestrator()
    
    prompt = """
    A user has proposed combining NLP, Braille-like spatial bitmasks, and Deterministic Reasoning as the foundation for Grace's architecture to eliminate hallucinations.

    Here is the proposed flow:
    1. The Translation Layer (NLP): An LLM acts purely as a translator at the ingestion edge. It reads natural language and translates it into strict Braille-like spatial tokens (semantic bitmasks). For example, it translates [Action: Restart] -> Bitmask 10010, [Target: Database Migration] -> Bitmask 01101.
    2. The Verification Layer (The Braille Matrix): Once the NLP generates the bitmasks, the probabilistic LLM is completely removed from the loop. The system runs those bit patterns through a deterministic validation filter using bitwise arithmetic (e.g., AND, XOR) to mathematically prove if the tokens logically compose according to the system's topological rules.
    3. The Execution Layer (Deterministic Reasoning Engine): If mathematically valid, Grace's reasoning engine takes over using classical deterministic logic gates (IF Bitmask X AND Bitmask Y THEN...). Finding the right recovery procedure isn't done via a floating-point vector similarity search, but through a direct spatial overlay (bitwise match) of the problem's token matrix onto the procedure's precondition matrix.

    By bounding the LLM to the translation step and forcing all reasoning and execution into the discrete mathematical space of the bitmask, the system retains the flexibility of natural language while eradicating the probabilistic hallucination risk entirely.

    Please provide a consensus evaluation of this combined architecture. Discuss its feasibility, how well it implements the goal of a hallucination-free autonomous system, and the theoretical and practical challenges of building the Execution Layer to operate strictly on these bitmasks.
    """
    
    print("Sending query to LLM Orchestrator (Consensus Mode) regarding NLP + Braille Deterministic Reasoning...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    print("\n" + "="*50)
    print("CONSENSUS RESULT - NLP + BRAILLE REASONING:")
    print("="*50)
    if result.success:
        print(result.content.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        print("Task failed.")
        print("Audit trail:", result.audit_trail)

if __name__ == "__main__":
    main()
