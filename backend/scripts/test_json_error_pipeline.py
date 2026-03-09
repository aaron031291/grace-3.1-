"""
Test script to generate a corrupt Genesis Key JSON file and attempt to read it,
proving that the new kb_integration -> ErrorPipeline connection works.
"""

import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from genesis.kb_integration import get_kb_integration
from self_healing.error_pipeline import get_error_pipeline

def main():
    print("==============================================")
    print("   JSON CORRUPTION -> ERROR PIPELINE DEMO     ")
    print("==============================================\n")
    
    # Init DB to ensure systems load
    from dotenv import load_dotenv
    load_dotenv(os.path.join(backend_dir, ".env"))
    
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    
    # Wake up the error pipeline background thread
    ep = get_error_pipeline()
    kb = get_kb_integration()
    
    # 1. Create a corrupt JSON file in the KB directly
    user_id = "test_corruption_user"
    user_folder = os.path.join(kb.genesis_key_path, user_id)
    os.makedirs(user_folder, exist_ok=True)
    
    corrupt_file_path = os.path.join(user_folder, "keys_test.json")
    print(f"1. Creating corrupted JSON file at: {corrupt_file_path}")
    with open(corrupt_file_path, 'w') as f:
        f.write('{"keys": [{"key_id": "123", "what": "half_finished", ') # Missing closing brace
        
    # 2. Force the KB system to interact with it
    print("\n2. Writing a new Genesis Key to the corrupted file...")
    dummy_key = {
        "user_id": user_id,
        "key_type": "test_event",
        "what": "Testing JSON corruption recovery",
        "timestamp": "2026-03-09T12:00:00Z"
    }
    
    # This will trigger the JSONDecodeError, which should now hit the ErrorPipeline
    kb._write_key_to_file(corrupt_file_path, dummy_key)
    
    print("\n3. Waiting 5 seconds for Error Pipeline background thread to process the exception...")
    time.sleep(5)
    
    print("\nCheck the grace.log or terminal output to confirm the Error Pipeline classified the JSONDecodeError and escalated it!")

if __name__ == "__main__":
    main()
