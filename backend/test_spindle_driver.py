import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ide_bridge import on_command
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def run_test():
    print("Testing IDE Bridge Spindle Compilation...")
    
    # Initialize DB for sandbox test
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
        
        # Seed test node
        from database.session import session_scope
        from database.models.braille_node import BrailleSandboxNode
        with session_scope() as session:
            node = session.query(BrailleSandboxNode).filter(BrailleSandboxNode.file_path == "math_funcs.py").first()
            if not node:
                session.add(BrailleSandboxNode(file_path="math_funcs.py", ast_content="", genesis_key="test_001", master_loop="test_loop"))
                session.commit()
    except Exception as e:
        print(f"DB Setup error: {e}")
        pass
    
    # Simulate an incoming code change from IDE
    user_input = "Implement fibonacci function"
    src = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)
"""
    file_path = "math_funcs.py"
    
    result = on_command(user_input=user_input, file_path=file_path, src=src)
    
    if "error" in result:
        print(f"❌ Test Failed: {result['error']}")
    elif result.get("success"):
        print(f"✅ Test Passed: Geometric Verification Succeeded.")
        print(f"Genesis Key: {result.get('genesis_key')}")
        print(f"Changes Tracked in Ghost Shadow: {result.get('changes_count')}")
    else:
        print(f"❌ Test Failed: Unexpected Result - {result}")

if __name__ == "__main__":
    run_test()
