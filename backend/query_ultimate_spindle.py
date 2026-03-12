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
    We have successfully implemented the Spindle AGI alignment engine. 
    It now has:
    1. Z3 SMT Solver for Formal Verification of 256-bit HDC.
    2. Autonomous Hallucination Blocking (via NLPCompilerEdge and Z3Sandbox).
    3. Magma Memory Persistence of SAT/UNSAT proofs for Qwen learning.
    4. Real-World Causal Awareness (WorldModelIngestor mapping external data to Causal Graphs, and Spindle blocking actions based on that graph).
    5. Neural-Symbolic Error Middleware (Catching physical graph rejections and suggesting neural alternatives).
    6. Universal Genesis Key Traceability for every component.

    The user asks: "What is the furthest we can take Spindle that is implementable?"

    Give a strictly technical, implementable roadmap for the absolute ceiling of what Spindle could become in the Grace OS. 
    Do not give vague sci-fi concepts. Give concrete software engineering milestones (e.g., specific math integrations, specific hardware-level bounds, specific new algorithms like TLA+ or Coq integration, continuous runtime verification, etc.)
    Provide 3-4 concrete, extremely advanced, but implementable next steps to push Spindle to its absolute limit as an AGI safety mechanism.
    """

    print("Executing Ultimate Spindle query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL, # Trigger multi-LLM consensus
        require_consensus=True,
        require_verification=True,
        require_grounding=True
    )

    print("Writing results...")
    with open("consensus_ultimate_spindle_output.md", "w", encoding="utf-8") as f:
        f.write("### Consensus Engine Evaluation: Ultimate Spindle Limits\n\n")
        f.write(result.content if result.success else f"Task Failed: {result.error_message}\n")

    print("Done. Output saved to consensus_ultimate_spindle_output.md")

if __name__ == "__main__":
    query_consensus()
