"""
demo_synergy.py
Demonstrates the 3-Pillar Autonomous Synergy Upgrade:
1. Cognitive: Trust-Driven Feedback Loop (Maker-Checker)
2. Memory: Active Resilience (Auto-healing event trigger)
3. Autonomy: Dynamic Resource Arbitration (Risk-based routing)
"""

import os
import sys
import io

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from cognitive.consensus_pipeline import get_consensus_pipeline
from cognitive.unified_memory import get_unified_memory
from llm_orchestrator.factory import get_llm_for_task
import time
from dotenv import load_dotenv

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("==============================================")
    print("      GRACE 3.1 AUTONOMOUS SYNERGY DEMO       ")
    print("==============================================\n")
    
    # Load env and init DB
    load_dotenv(os.path.join(backend_dir, ".env"))
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    # --- DEMO 1: Dynamic Resource Arbitration ---
    print("\n--- [DEMO 1] Dynamic Resource Arbitration ---")
    print("Simulating LLM routing based on Task Risk...\n")
    
    low_risk = "Write a quick greeting message for a user login screen."
    high_risk = "Analyze this firewall architecture schema for zero-day vulnerabilities."
    
    print("Requesting LLM for LOW RISK task...")
    low_client = get_llm_for_task(task_description=low_risk)
    print(f"-> Routed to: {low_client.__class__.__name__}")
    
    print("\nRequesting LLM for HIGH RISK task...")
    high_client = get_llm_for_task(task_description=high_risk)
    print(f"-> Routed to: {high_client.__class__.__name__}")
    
    time.sleep(2)
    
    # --- DEMO 2: Cognitive Trust-Driven Loop ---
    print("\n\n--- [DEMO 2] Cognitive Trust-Driven Feedback Loop ---")
    print("Simulating Qwen (Maker) drafting code and Opus (Checker) critiquing it...\n")
    
    pipeline = get_consensus_pipeline()
    instruction = "Write a python function that calculates the nth fibonacci number. Make it intentionally terrible and inefficient."
    
    print(f"Instruction: {instruction}")
    print("Running Pipeline (this may take a minute). Watch the terminal logs for the back-and-forth critique!\n")
    
    try:
        result = pipeline.run_maker_checker(instruction=instruction, maker_model="qwen", checker_model="opus", max_iterations=2)
        print("\n[Final Approved Draft]")
        print(result["final_output"])
    except Exception as e:
        print(f"Pipeline error: {e}")
        
    time.sleep(2)

    # --- DEMO 3: Active Memory Resilience ---
    print("\n\n--- [DEMO 3] Active Memory Resilience ---")
    print("Simulating repeated failures of 'genesis_qdran' to trigger Active Resilience Auto-Healing.\n")
    
    memory = get_unified_memory()
    
    # Force 3 failures to trigger the event
    for i in range(3):
        print(f"Logging episode {i+1}: 'genesis_qdran' failure...")
        memory.store_episode(
            problem=f"Task {i}",
            action="preprocess_quantum",
            outcome="Exception: connection refused to genesis_qdran",
            trust=0.0,
            source="genesis_qdran",
            trust_coin="VVT_PLATINUM_COIN"
        )
    
    print("\nMemory logged. The Active Resilience hook analyzed the memory and should have dispatched a self-healing event.")
    print("Check grace.log for '[ACTIVE-RESILIENCE] Detected 3 repeated failures for module genesis_qdran. Dispatching self-healing event.'")
    
    print("\n==============================================")
    print("                  DEMO COMPLETE               ")
    print("==============================================\n")

if __name__ == "__main__":
    main()
