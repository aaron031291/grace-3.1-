import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def main():
    orchestrator = get_llm_orchestrator()
    
    prompt = """
    A user has proposed a deterministic "Braille Spatial Bitmask" architecture to eliminate LLM hallucinations. The current hallucination mitigation system in Grace (hallucination_guard.py) relies on NLP string comparisons (SequenceMatcher, DeBERTa NLI cross-encoder, Cosine Similarity, Regex). JSON schemas will also be used to mitigate natural hallucinations where possible.
    
    The user is asking the internal consensus mechanism to evaluate the following:
    
    1. Do we currently have enough internal logic in the existing hallucination guards to stop hallucinations to a very high degree (e.g., 98% or 99%)? Please review the effectiveness of the current system against the proposed deterministic bitwise architecture.
    2. If we don't currently have enough to mitigate hallucinations to that extreme dexterity, what else EXACTLY do we need to build?
    3. Are you confident that the development team can build this proposed system (or a working model/prototype of it) to play with? It doesn't have to be perfect the first time around.
    
    Please provide an honest and direct assessment.
    """
    
    print("Sending query to LLM Orchestrator (Consensus Mode) regarding hallucination guards...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    print("\n" + "="*50)
    print("CONSENSUS RESULT - HALLUCINATION GUARDS:")
    print("="*50)
    if result.success:
        print(result.content.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        print("Task failed.")
        print("Audit trail:", result.audit_trail)

if __name__ == "__main__":
    main()
