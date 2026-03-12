import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cognitive.consensus_engine import run_consensus
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def query():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
    except Exception:
        pass

    prompt = (
        "As the Grace Cognitive Roundtable, we need you to settle a debate. "
        "An external auditor claimed that 'Spindle', the deterministic programming language and execution engine, "
        "is 'Not In Codebase' and 'Pure R&D / greenfield,' implying it might be a hallucination or not real. "
        "Based on your knowledge of the Grace 3.1 architecture, the IDE Bridge, the Braille Mapper, the Braille Translator (AST to Braille), "
        "the SandboxModifier, and the Z3 geometric bitmask verifiers, "
        "is Spindle a hallucination, or is it real and actively being wired into the codebase? "
        "Provide a concrete, technical verdict using evidence from the actual modules."
    )

    print("======================================================")
    print("🧠 INITIATING ROUNDTABLE CONSENSUS DELIBERATION 🧠")
    print("======================================================")
    print("Prompt: " + prompt + "\n")
    
    result = run_consensus(
        prompt=prompt,
        models=["opus", "kimi", "qwen"]
    )
    
    out_file = "spindle_reality_check.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result.final_output)
    print(f"\nConsensus reached. Output written to {out_file}\n")
    print(result.final_output)

if __name__ == "__main__":
    query()
