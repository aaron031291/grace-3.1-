import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from dotenv import load_dotenv

def query_consensus_final_steps():
    load_dotenv()
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    orchestrator = get_llm_orchestrator()

    prompt = """
    We have successfully implemented the final 3 stages to make Spindle production-ready based on your previous guidance:

    1. Qwen Z3 Pipeline: Automated the generation of Z3 constraints via Qwen, translating natural language directly to `z3.Implies(...)` formal Python code.
    2. Execution Sandbox: Added a subprocess sandbox to execute and verify the LLM-generated Z3 constraints isolated from the main Grace runtime.
    3. Frontend Real-Time Feedback API: Created a FastAPI router endpoint to pipe mathematical UNSAT proofs from the Z3 SMT Solver back to the UI.

    Spindle is now a formally verified theorem proving safety engine.

    Question:
    What is the exact next highest-leverage step we should take to fully integrate this into the Grace architecture and reach AGI capabilities?

    Consider:
    1. Should we start hooking Spindle up to the self-healing and autonomous coding agents so they cannot hallucinate destructive actions?
    2. Should we start storing these formally verified constraints in Magma Memory so they persist?
    3. What is the most critical missing component holding Grace back right now?

    Be extremely specific, prioritize ruthlessly, and provide clear architectural guidance.
    """

    print("Executing Final Steps query task with Consensus Engine...")
    result = orchestrator.execute_task(
        prompt=prompt,
        task_type=TaskType.GENERAL, # Trigger multi-LLM consensus
        require_consensus=True,
        require_verification=True,
        require_grounding=True
    )

    print("Writing results...")
    with open("consensus_final_steps_output.md", "w", encoding="utf-8") as f:
        f.write("### Consensus Engine Evaluation: Final Steps for Spindle\n\n")
        f.write(result.content if result.success else f"Task Failed: {result.error_message}\n")

    print("Done. Output saved to consensus_final_steps_output.md")

if __name__ == "__main__":
    query_consensus_final_steps()
