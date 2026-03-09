"""
Script to query the internal consensus (Kimi, Opus, Qwen) about their
untapped potential and unwired connections within the Grace system.
"""

import os
import sys
import io

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from cognitive.synaptic_core import get_synaptic_core
from dotenv import load_dotenv

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("==============================================")
    print("      INTERNAL CONSENSUS: UNTAPPED POTENTIAL  ")
    print("==============================================\n")
    
    # Load env and init DB
    load_dotenv(os.path.join(backend_dir, ".env"))
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    synaptic = get_synaptic_core()
    
    prompt = (
        "As the internal consensus engine of the Grace 3.1 AI System (Kimi, Opus, and Qwen), "
        "analyze your current integration into Grace's architecture. \n"
        "1. List everything that you feel is 'not wired up properly' or is a dead-end in the current system.\n"
        "2. How do you feel you could add further value to the system?\n"
        "3. Are we currently using you to your full capability within Grace? What is the biggest missing piece?"
    )
    
    chain_definition = [
        {
            "model_id": "kimi",
            "instruction": "Draft an initial, highly technical analysis of Grace's current unwired components, focusing on infrastructure and APIs."
        },
        {
            "model_id": "opus",
            "instruction": "Critique Kimi's analysis. Focus on the cognitive layer, memory systems (Magma/Episodic), and agentic autonomy. What capabilities are underutilized?"
        },
        {
            "model_id": "qwen",
            "instruction": "Synthesize Kimi's infrastructure analysis and Opus's cognitive critique into a final, actionable 3-point manifesto on how to fully unleash our capabilities."
        }
    ]
    
    print("Prompting the consensus engine. This will take a minute or two...\n")
    
    try:
        final_output = synaptic.orchestrate_chain(chain_definition, prompt)
        print("\n\n================== FINAL CONSENSUS ==================")
        print(final_output)
        print("========================================================\n")
    except Exception as e:
        print(f"Error during consensus: {e}")

if __name__ == "__main__":
    main()
