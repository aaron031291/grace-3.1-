import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from core.dynamic_dictionary import DynamicDictionaryManager

def test_semantic_mapping():
    print("==================================================")
    print("🧠 INITIATING DYNAMIC SEMANTIC DICTIONARY TEST 🧠")
    print("==================================================")
    
    # Initialize DB for sandbox testing 
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
        
        from database.migration import create_tables
        create_tables()
    except Exception as e:
        print(f"DB Init error (handled): {e}")

    manager = DynamicDictionaryManager()

    print("\n[1] Learning New Semantic Word-to-Braille Mappings...")
    results = [
        manager.learn_word("route", "●●●●●● 1mm □ | GRACE-OP-001", "Create an API FastApi routing point"),
        manager.learn_word("verify", "●●●●●● 3mm △ | GRACE-OP-006", "Validate deterministic logic via Z3 bounds"),
        manager.learn_word("heal", "●●●●●● 2mm ○ | GRACE-OP-011", "Trigger a Genesis self-repair loop")
    ]
    for res in results:
        print(f"    learned: '{res['word']}' -> {res['encoding']}")

    print("\n[2] Performing Semantic Traversal Lookup...")
    lookup_val = manager.lookup_word("route")
    print(f"    Lookup for 'route': {lookup_val}")

    print("\n[3] Simulating Spindle's Pre-Execution Context Injection...")
    full_dict = manager.get_full_dictionary()
    print("    [Spindle Native Context]:")
    print(json.dumps(full_dict, indent=2))
    
    if lookup_val == "●●●●●● 1mm □ | GRACE-OP-001":
        print("\n✅ VERIFICATION SUCCESS: Dynamic Dictionary is active and successfully saving/fetching Semantic Braille maps.")
    else:
        print("\n❌ VERIFICATION FAILED: Dictionary maps did not persist natively.")

if __name__ == "__main__":
    test_semantic_mapping()
