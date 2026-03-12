import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

def query_consensus_next_steps():
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    orchestrator = get_llm_orchestrator()

    prompt = """
    We have successfully implemented the first two highest-leverage priorities you recommended for the Spindle architecture:
    1. Z3 SMT Solver Integration: We replaced manual topological conditionals with formal theorem proving via Z3.
    2. HDC Bitmask Scaling: We migrated the single 64-bit integer to a 256-bit hierarchical array (Domain, Intent, State, Context).

    The core physics engine is now formally verifiable.

    Question:
    What is the exact next highest-leverage step we should take to make Spindle production-ready and fully autonomous across Grace?

    Specifically, address:
    1. How should we build the pipeline for Qwen to automatically write these Z3 Spindle constraints?
    2. Should we tackle the Sandbox Execution interface next?
    3. What is the missing link between this backend engine and the user's front-end experience?

    Be extremely specific, prioritize ruthlessly, and provide clear architectural guidance.
    """

    print("Executing Next Steps query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL, # Trigger multi-LLM consensus
        require_consensus=True,
        require_verification=True,
        require_grounding=True
    )

    print("Writing results...")
    with open("consensus_next_steps_output.md", "w", encoding="utf-8") as f:
        f.write("### Consensus Engine Evaluation: Next Steps for Spindle\n\n")
        f.write(result.content if result.success else f"Task Failed: {result.error_message}\n")

    print("Done. Output saved to consensus_next_steps_output.md")

if __name__ == "__main__":
    query_consensus_next_steps()
