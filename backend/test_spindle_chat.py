import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def run_test():
    print("Testing Spindle Integration with Chat and LLM Autonomy...")
    
    # Initialize DB for sandbox test
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
    except Exception as e:
        print(f"DB Setup error: {e}")
        pass
    
    # 1. Simulate IDE natural language request OR Frontend Chat request
    from ide_bridge import on_command
    user_input = "Create a simple python function that adds two numbers"
    
    # This should hit the Spindle Builder Pipeline (QwenCodingNet)
    result = on_command(user_input=user_input)
    
    # The result should contain the geometric AST compilation status
    print("\nResult Data:")
    
    if "error" in result:
        print(f"FAIL: Test Failed: {result.get('error')}")
    else:
        status = result.get('status')
        test_result = result.get('test_result', {})
        
        # Check if the Spindle compiler returned PASS for the topology check
        if status in ["completed", "deployed"] and test_result.get('passed') == True:
            print(f"SUCCESS: Test Passed: Natural Language Request geometrically compiled successfully!")
            print(f"Status: {status}")
            print(f"Trust Score: {test_result.get('trust_score')}")
        else:
            print(f"FAIL: Test Failed: Spindle execution didn't pass.")
            print(f"Compile result payload: {test_result}")
            print(f"Full Request Result: {result}")

if __name__ == "__main__":
    run_test()
