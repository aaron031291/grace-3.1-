import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cognitive.consensus_actuation import get_actuation_gateway

def run_tests():
    gateway = get_actuation_gateway()
    
    print("--- Test 1: Authorized Dry Run (Code Mutation) ---")
    payload_1 = {
        "action_type": "submit_coding_task",
        "params": {
            "instructions": "Fix the frontend CSS",
            "dry_run": "true"
        },
        "rationale": "Testing dry run."
    }
    res_1 = gateway.execute_action(payload_1, "test_context", 0.9)
    print(res_1, "\n")
    
    print("--- Test 2: Unauthorized Non-Dry Run (Code Mutation) ---")
    payload_2 = {
        "action_type": "submit_coding_task",
        "params": {
            "instructions": "Fix the frontend CSS",
            "dry_run": "false"  # Should be blocked
        },
        "rationale": "Testing lack of dry run."
    }
    res_2 = gateway.execute_action(payload_2, "test_context", 0.9)
    print(res_2, "\n")
    
    print("--- Test 3: Unauthorized Command (Shell) ---")
    payload_3 = {
        "action_type": "execute_shell_command",
        "params": {
            "command": "rm -rf /"
        },
        "rationale": "Testing blocked command."
    }
    res_3 = gateway.execute_action(payload_3, "test_context", 0.9)
    print(res_3, "\n")
    
    print("--- Test 4: Insufficient Trust Score ---")
    payload_4 = {
        "action_type": "execute_shell_command",
        "params": {
            "command": "ls"
        },
        "rationale": "Testing trust threshold."
    }
    res_4 = gateway.execute_action(payload_4, "test_context", 0.1) # Risk is too high
    print(res_4, "\n")
    
if __name__ == "__main__":
    run_tests()
