import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

def run_final_validation():
    print("========== RUNNING FINAL CONSENSUS VALIDATION ON BRAILLE/SPINDLE ==========")
    
    orchestrator = get_llm_orchestrator()
    if not orchestrator:
        print("Failed to initialize LLM Orchestrator.")
        return
        
    prompt = """
    We have just built the finalized Braille Deterministic Engine (Spindle language) MVP and wired it into Grace's Action Router. 
    It translates fuzzy LLM intents into a strict 64-bit spatial bitmask and evaluates it using deterministic bitwise physics to block LLM hallucinations and invalid state transitions.
    
    Please perform a final validation and answer the following questions from the user:
    1. Validate what we've just built. Are there any critical holes or gaps in this deterministic system right now? Where are the weaknesses in the bitwise architecture?
    2. If this is wired into the front-end now, can a user just talk to Grace and have Grace build exactly what is needed, as long as the user understands the system flow and Spindle logic?
    3. Interacting externally vs internally: "If I use LLMs externally (e.g. on my phone) to internalize my thought process and bring it back into Grace, is that the best way? Or can I just use Grace's own consensus mechanism to build Grace?" Which approach is better for interacting with this new deterministic architecture?
    4. Test the concept from different perspectives. Is it really this simple to solve the hallucination problem using spatial bitmasks instead of neural networks? The user is shocked that it might be this simple. What are the caveats and blind spots?
    """
    
    print("Sending final validation task to the Consensus Engine. This may take a minute...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL,
        require_consensus=True,
        context_documents=[
            "c:/Users/aaron/Desktop/grace-3.1--Aaron-new2/backend/cognitive/braille_compiler.py",
            "c:/Users/aaron/Desktop/grace-3.1--Aaron-new2/backend/diagnostic_machine/action_router.py"
        ]
    )
    
    if result and getattr(result, 'success', False):
        print("\n--- FINAL CONSENSUS FEEDBACK ---\n")
        print(result.content)
    else:
        print("\nConsensus validation failed to run.")

if __name__ == "__main__":
    run_final_validation()
