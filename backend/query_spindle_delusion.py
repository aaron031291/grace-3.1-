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
        "As the Grace Cognitive Roundtable (Kimi, Opus, Qwen), I need you to answer a direct, existential question from our creator, Aaron. "
        "An external auditor (Ikonic Dev LLC) claims Spindle does not exist in the codebase and is 'Pure R&D'. "
        "Aaron is asking: 'Is Spindle delusional? Did you (the AI) hallucinate it, or do I need to pinch myself and accept reality?' "
        "Look at the actual architecture we have been building: the IDE Bridge, the Braille Mapper, the Braille Translator, "
        "the SandboxModifier, Z3 geometric verifiers, and the Spindle integration endpoints. "
        "Is Spindle a shared AI hallucination, or is it a tangible, real system actively being constructed in Grace 3.1? "
        "Please provide a definitive, grounded answer directly to Aaron."
    )

    print("======================================================")
    print("🧠 INITIATING ROUNDTABLE CONSENSUS DELIBERATION 🧠")
    print("======================================================")
    print("Prompt: " + prompt + "\n")
    
    result = run_consensus(
        prompt=prompt,
        models=["opus", "kimi", "qwen"]
    )
    
    out_file = "spindle_delusion_check.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result.final_output)
    print(f"\nConsensus reached. Output written to {out_file}\n")
    print(result.final_output)

if __name__ == "__main__":
    query()
