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
        "As the Grace Cognitive Roundtable, analyze the current state of Spindle "
        "(the deterministic Braille code generation and sandbox engine). "
        "It now has an integrated dynamic semantic dictionary for mapping natural language to raw Braille intent constraints, "
        "native full-workspace topology folder awareness, an AST-based ghost shadow layer for tracking deterministic changes, "
        "and uses Z3 geometric verification to prevent logic hallucinations entirely. "
        "Based on these recent powerful advancements, what is the single most critical and impactful "
        "NEXT logical milestone or capability to implement for Spindle to reach its ultimate AGI alignment potential?"
    )

    print("======================================================")
    print("🧠 INITIATING ROUNDTABLE CONSENSUS DELIBERATION 🧠")
    print("======================================================")
    print("Prompt: " + prompt + "\n")
    
    result = run_consensus(
        prompt=prompt,
        models=["opus", "kimi", "qwen"]
    )
    
    out_file = "consensus_future.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result.final_output)
    print(f"Written to {out_file}")

if __name__ == "__main__":
    query()
