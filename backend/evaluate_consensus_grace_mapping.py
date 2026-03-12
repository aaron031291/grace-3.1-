import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def main():
    orchestrator = get_llm_orchestrator()
    
    prompt = """
    A user has proposed a revolutionary architecture that translates natural language (NLP) into a deterministic "Braille-like" spatial bitmask array, and then runs all autonomous execution strictly via classical, deterministic mathematical topology (e.g. bitwise matching) instead of probabilistic vector similarity.
    
    The user is asking: Can Grace's CURRENT architectural components (e.g., the OODA loop, the Sandbox Router, Neuro-Symbolic Reasoner, The Action Router, Epochs, and Magma Memory) be adapted to implement this exact NLP + Braille bitmask + Deterministic Reasoning paradigm?
    
    Please provide a consensus evaluation mapping the user's NLP/Braille architecture directly onto Grace's existing capabilities. Where does Grace already have the foundation for this? What components would need to be rewired or built from scratch to support this exact spatial bitmask execution layer?
    """
    
    print("Sending query to LLM Orchestrator (Consensus Mode) regarding Grace architectural mapping...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    print("\n" + "="*50)
    print("CONSENSUS RESULT - GRACE ARCHITECTURE MAPPING:")
    print("="*50)
    if result.success:
        print(result.content.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        print("Task failed.")
        print("Audit trail:", result.audit_trail)

if __name__ == "__main__":
    main()
