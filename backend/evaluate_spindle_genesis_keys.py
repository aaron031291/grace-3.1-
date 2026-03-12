import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

def query_consensus():
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    orchestrator = get_llm_orchestrator()

    prompt = """
    We have just completed the Spindle AGI alignment engine (Z3 formal verification) and the World Model API (Causal Graph integration).
    
    The user wants your formal consensus and review on two critical points:
    
    1. Spindle Integration: 
       - Are you fully happy with Spindle? 
       - Have we pushed it as far as we can? 
       - Is Spindle fully integrated with the whole system? If not, what specific gaps remain?
       
    2. Genesis Key Coverage:
       - Does every single thing in the system that requires a Genesis Key have one?
       - We need to assess model components, APIs, databases, Python files, modules, components, brains, etc. — EVERYTHING that has been created.
       - Where are we missing Genesis Keys? Provide specific components or architectures that need them.
       
    Be completely honest. If we are missing Genesis Keys somewhere, list the components. If Spindle needs more wiring, outline exactly where.
    """

    print("Executing Spindle and Genesis Key query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL, # Trigger multi-LLM consensus
        require_consensus=True,
        require_verification=True,
        require_grounding=True
    )

    print("Writing results...")
    with open("consensus_spindle_gkeys_output.md", "w", encoding="utf-8") as f:
        f.write("### Consensus Engine Evaluation: Spindle & Genesis Keys\n\n")
        f.write(result.content if result.success else f"Task Failed: {result.error_message}\n")

    print("Done. Output saved to consensus_spindle_gkeys_output.md")

if __name__ == "__main__":
    query_consensus()
