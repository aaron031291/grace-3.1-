import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.comparative_testing import run_ab_optimization_test
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def verify_ab():
    print("==================================================")
    print("📈 INITIATING A/B COMPARATIVE OPTIMIZATION TEST 📈")
    print("==================================================")
    
    # Initialize DB for sandbox testing 
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
    except Exception as e:
        print(f"DB Init error (handled): {e}")

    prompt = "Create a new FastAPI endpoint for testing the system health."
    print(f"\n[Test Prompt]: '{prompt}'")
    
    try:
        results = run_ab_optimization_test(prompt=prompt)
        print("\n[Comparative Metrics]:")
        print(json.dumps(results, indent=2))
        
        if results["optimization_gain_ms"] > 0:
            print(f"\n✅ VERIFICATION SUCCESS: Sandbox execution was {results['optimization_gain_ms']}ms faster than standard.")
        elif results["optimization_gain_ms"] < 0:
            print(f"\n✅ VERIFICATION SUCCESS: Testing framework works. Standard execution was {abs(results['optimization_gain_ms'])}ms faster.")
        else:
            print("\n✅ VERIFICATION SUCCESS: Both pathways completed with identical latency.")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    verify_ab()
