import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cognitive.corrigible_plan import get_corrigible_plan
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

def test_autonomy():
    print("==================================================")
    print("🤖 INITIATING CORRIGIBLE-PLAN AUTONOMY TEST 🤖")
    print("==================================================")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
    except Exception as e:
        print(f"DB Init error (handled): {e}")

    corrigible = get_corrigible_plan()

    print("\n[1] Spindle triggers an autonomous background action...")
    print("    Simulated Trigger: 'Integrity Check Failed'")
    
    result = corrigible.draft_autonomous_action("Integrity Check Failed")
    
    if result and result["status"] == "provably_safe":
        print("\n✅ VERIFICATION SUCCESS: Autonomous Action geometrically validated within Entropy limits!")
        print(f"    Action Selected: {result['action_type']}")
        print(f"    Raw Constraint Intent: {result['braille_intent']}")
        print(f"    Shadow AST Delta Draft: {result['ast_mask']}")
    else:
        print("\n❌ VERIFICATION FAILED: Z3 Proof failed or timed out.")

if __name__ == "__main__":
    test_autonomy()
