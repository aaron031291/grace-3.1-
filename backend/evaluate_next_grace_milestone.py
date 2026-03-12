import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

def query_consensus_agi_steps():
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    orchestrator = get_llm_orchestrator()

    prompt = """
    We have successfully implemented everything you requested for the Spindle AGI alignment engine:

    1. Z3 SMT Solver & 256-bit HDC: The core physics engine is now mathematically verified using formal theorem proving.
    2. Automation & Sandboxing: Qwen dynamically generates Z3 constraints, which are verified in an isolated execution sandbox.
    3. Magma Memory Persistence: The Z3 `SAT/UNSAT` formal proofs are permanently written to Magma memory.
    4. Autonomous Feedback Loops: The Qwen Training Pipeline reads failed math proofs from Magma to prevent hallucination, and the Autonomous Healing Agent queries the Spindle solver before executing any destructive operations.

    Spindle is essentially complete and wired into the core intelligence layers.

    Question:
    What is the exact next highest-leverage architectural milestone we should tackle for the Grace OS as a whole to push towards AGI?

    We have handled deterministic physics (Spindle). What is the next major bottleneck?
    Consider:
    1. Should we focus on the Diagnostic Machine and KPI Trust Scoring?
    2. Should we focus on Proactive / Self-Driving Mission Generation?
    3. Should we focus on the World Model API?

    Be extremely specific, prioritize ruthlessly, and provide clear architectural guidance. Focus on what is missing from the CURRENT state of Grace.
    """

    print("Executing Next Grace Milestone query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL, # Trigger multi-LLM consensus
        require_consensus=True,
        require_verification=True,
        require_grounding=True
    )

    print("Writing results...")
    with open("consensus_agi_steps_output.md", "w", encoding="utf-8") as f:
        f.write("### Consensus Engine Evaluation: Next Grace Milestone\n\n")
        f.write(result.content if result.success else f"Task Failed: {result.error_message}\n")

    print("Done. Output saved to consensus_agi_steps_output.md")

if __name__ == "__main__":
    query_consensus_agi_steps()
