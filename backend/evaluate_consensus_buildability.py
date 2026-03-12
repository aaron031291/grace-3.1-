import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def main():
    orchestrator = get_llm_orchestrator()
    
    prompt = """
    A user has proposed the "Braille Spatial Bitmask" architecture:
    1. LLM translates Natural Language -> 256-bit Spatial Bitmask.
    2. Bitwise Logic Gate verifies the bitmask topological validity.
    3. Action Router/Neuro-Symbolic Reasoner executes purely via Bitwise operations.

    The user is asking a pragmatic engineering question: "Is this fully buildable with current LLMs?"
    
    Can current LLMs (like GPT-4, Claude 3.5, Gemini 1.5, or Qwen) reliably output 256-bit binary masks with zero errors in formatting and schema alignment? What are the immediate bottlenecks to actually writing the code for this tomorrow? How hard is it to build the dictionary/schema that the LLM uses for translation? Can we use structured JSON schemas or function calling to force the LLMs into this bitmask output?
    
    Please provide a brutally honest, engineering-focused consensus on whether a small team could successfully build this NLP compiler edge right now with off-the-shelf LLMs.
    """
    
    print("Sending query to LLM Orchestrator (Consensus Mode) regarding buildability...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        require_verification=False,
        require_grounding=False
    )
    
    print("\n" + "="*50)
    print("CONSENSUS RESULT - BUILDABILITY ASSESSMENT:")
    print("="*50)
    if result.success:
        print(result.content.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        print("Task failed.")
        print("Audit trail:", result.audit_trail)

if __name__ == "__main__":
    main()
