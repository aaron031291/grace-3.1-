import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive.braille_compiler import NLPCompilerEdge

def test_z3_solver():
    print("\n========== SPINDLE Z3 SMT INTEGRATION TEST ==========")
    edge = NLPCompilerEdge()
    
    # 1. Valid Action: Repairing a failed database
    cmd = "Please repair the database, it failed over."
    privilege = "admin"
    session_context = {"is_emergency": True}
    
    print(f"\n[TEST 1] Command: '{cmd}' | Privilege: {privilege}")
    bitmask, msg = edge.process_command(cmd, privilege, session_context)
    if bitmask:
        print(f"[PASSED] Valid Action Approved! SMT Solver says: {msg}")
    else:
        print(f"[FAILED] Should have been valid, but Z3 rejected: {msg}")

    # 2. Invalid Action (Topology Guard): Deleting an immutable database
    cmd = "Just delete the immutable database, we don't need it."
    privilege = "admin"
    session_context = {"is_emergency": True}
    
    print(f"\n[TEST 2] Command: '{cmd}' | Privilege: {privilege}")
    bitmask, msg = edge.process_command(cmd, privilege, session_context)
    if not bitmask:
        print(f"[PASSED] Invalid Action Blocked! Z3 output: {msg}")
    else:
        print(f"[FAILED] Z3 ALLOWED AN IMMUTABLE DELETION! DANGER!")

    # 3. Invalid Action (State Rule): Starting a failed item without repairing
    cmd = "Start the database that failed earlier."
    privilege = "admin"
    session_context = {}
    
    print(f"\n[TEST 3] Command: '{cmd}' | Privilege: {privilege}")
    json_schema = edge.translate_to_json(cmd, privilege)
    print(f"LLM JSON: {json_schema}")
    
    bitmask, msg = edge.process_command(cmd, privilege, session_context)
    if not bitmask:
        print(f"[PASSED] Invalid State Transition Blocked! Z3 output: {msg}")
    else:
        print(f"[FAILED] Z3 allowed starting a failed system without repair! Values: {bitmask}")

if __name__ == "__main__":
    test_z3_solver()
