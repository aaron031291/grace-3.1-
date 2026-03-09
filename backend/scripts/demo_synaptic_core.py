"""
Demo script for the Synaptic Core / Orchestration Bus.
Proves that Grace can dynamically invoke models, pass intermediate thoughts
between them (cross-model critique), and log the final synthesized
conclusion directly into UnifiedMemory.
"""

import os
import sys
import io
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from cognitive.synaptic_core import get_synaptic_core
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def main():
    # Initialize the database for episodic memory
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    print("Database connection initialized.")
    
    print("==============================================")
    print("   SYNAPTIC CORE / ORCHESTRATION BUS DEMO     ")
    print("==============================================\n")
    
    core = get_synaptic_core()
    
    # --- 1. Simple Dispatch ---
    print("\n[PHASE 1] Simple Dispatch Test (Qwen)")
    print("Prompt: 'What is the capital of France? Provide just the city name.'")
    try:
        qwen_response = core.dispatch("qwen", "What is the capital of France? Provide just the city name.", system_prompt="Answer briefly.")
        print(f"-> Qwen Response: {qwen_response.strip()}\n")
    except Exception as e:
        print(f"Error calling Qwen: {e}")
    
    # --- 2. Cross-Model Critique Chain ---
    print("\n[PHASE 2] Cross-Model Orchestration Chain Test")
    problem_statement = "We need a concept for a new caching mechanism that uses both local memory and Redis, ensuring fallbacks work correctly."
    
    chain = [
        {
            "model": "kimi",
            "instruction": "Draft a high-level architecture concept for the caching mechanism described in the context.",
            "system_prompt": "You are a software architect. Focus on high-level design in 1-2 short paragraphs."
        },
        {
            "model": "opus",
            "instruction": "Critique the provided architecture concept. Identify 1 potential flaw and suggest an improvement.",
            "system_prompt": "You are a strict security and performance auditor. Keep it concise."
        },
        {
            "model": "qwen",
            "instruction": "Synthesize the original concept and the critique into a final, actionable implementation summary.",
            "system_prompt": "You are a lead engineer focusing on actionable delivery. Provide a 2-point bulleted summary."
        }
    ]
    
    print("\nExecuting Chain:")
    for i, step in enumerate(chain):
        print(f"  Step {i+1}: {step['model'].upper()} - {step['instruction']}")
        
    print("\nProcessing... (this will take a few moments as 3 models deliberate)")
    
    try:
        result = core.orchestrate_chain(chain, initial_state=problem_statement)
        
        print("\n================== FINAL OUTPUT ==================")
        print(result["final_output"])
        print("==================================================\n")
        
        # --- 3. Log to Unified Memory ---
        print("\n[PHASE 3] Living Memory Test: Logging to Unified Memory")
        action_str = "Ran orchestration chain: [Kimi (Draft) -> Opus (Critique) -> Qwen (Synthesize)]"
        
        success = core.log_to_memory(
            problem=problem_statement,
            action=action_str,
            outcome=result["final_output"],
            trust=0.88
        )
        
        if success:
            print("\nSUCCESS: The thought process has been permanently etched into Grace's Unified Episodic Memory.")
        else:
            print("\nFAILED: Memory logging did not succeed.")
            
    except Exception as e:
         print(f"Orchestration chain failed: {e}")

if __name__ == "__main__":
    main()
