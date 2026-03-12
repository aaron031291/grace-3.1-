import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import ide_bridge

def run_verification():
    print("==================================================")
    print("🧪 INITIATING IDE BRIDGE VERIFICATION TEST 🧪")
    print("==================================================")
    
    # 1. Test the passive File Save Hook
    print("\n[TEST 1] Triggering IDE on_save...")
    test_file = "C:/Users/aaron/Desktop/grace-3.1--Aaron-new2/backend/models/braille_node.py"
    try:
        ide_bridge.on_save(test_file)
        print("✅ on_save invoked successfully (fires async passive context).")
    except Exception as e:
        print(f"❌ on_save failed: {e}")

    # 2. Test the active Command Hook
    print("\n[TEST 2] Triggering IDE on_command ('Explain the new braille node model')...")
    # This command targets the Brain API -> Spindle -> queries Sandbox Braille AST
    try:
        result = ide_bridge.on_command("Explain the new BrailleSandboxNode database model and how the genesis_key handles deterministic dots.")
        print("\n[Spindle Output Returned to IDE]:")
        
        if "error" in result:
            print(f"❌ Verification Failed. API returned error: {result['error']}")
            print("💡 TIP: Ensure the Grace API (app.py) is running on localhost:8000!")
        else:
            print(json.dumps(result, indent=2))
            print("\n✅ Verification Successful! Bridge is communicating perfectly with Spindle and the Sandbox.")
    except Exception as e:
        print(f"❌ on_command failed: {e}")

if __name__ == "__main__":
    run_verification()
