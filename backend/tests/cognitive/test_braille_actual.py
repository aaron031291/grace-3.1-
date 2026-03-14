import pytest
import z3

from cognitive.braille_compiler import BrailleDictionary, NLPCompilerEdge
from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry

def test_braille_dictionary_compilation():
    """Verify JSON compiles correctly into BitMasks."""
    json_intent = {
        "domain": "database",
        "intent": "start",
        "target_state": "stopped",
        "privilege": "user"
    }
    
    session_context = {
        "has_elevation_token": True,
        "is_maintenance_window": False,
        "is_emergency": False
    }

    d_val, i_val, s_val, c_val = BrailleDictionary.compile_schema(json_intent, session_context)
    
    assert d_val == BrailleDictionary.DOMAIN_DATABASE
    assert i_val == BrailleDictionary.INTENT_START
    assert s_val == BrailleDictionary.STATE_STOPPED

    # Privilege 'user' gets injected into context mask along with elevation token
    expected_ctx = BrailleDictionary.CTX_ELEVATED | BrailleDictionary.PRIV_USER
    assert c_val == expected_ctx


def test_z3_hardware_geometry_logic():
    """
    Test the Spindle Next-Gen Z3 Bitmask Geometry Rules natively without LLMs.
    """
    geometry = HierarchicalZ3Geometry()
    
    # --- TEST 1: Rule P2 Valid Case ---
    # User mutating database WITH elevated context
    d_val = BrailleDictionary.DOMAIN_DATABASE
    i_val = BrailleDictionary.INTENT_START
    s_val = BrailleDictionary.STATE_STOPPED
    c_val = BrailleDictionary.PRIV_USER | BrailleDictionary.CTX_ELEVATED
    
    proof = geometry.verify_action(d_val, i_val, s_val, c_val)
    assert proof.is_valid is True, f"Failed valid proof: {proof.reason}"
    assert "Z3_SAT" in proof.reason
    assert proof.result == "SAT"
    assert proof.constraint_hash  # tamper-detection hash is populated

    # --- TEST 2: Rule P2 Invalid Case ---
    # User mutating database WITHOUT elevated context -> Should physically reject
    c_val_invalid = BrailleDictionary.PRIV_USER
    proof = geometry.verify_action(d_val, i_val, s_val, c_val_invalid)
    assert proof.is_valid is False
    assert "Z3_UNSAT" in proof.reason
    assert proof.result == "UNSAT"

    # --- TEST 3: Rule S1 Invalid Case ---
    # Cannot DELETE IMMUTABLE
    d_val = BrailleDictionary.DOMAIN_API
    i_val = BrailleDictionary.INTENT_DELETE
    s_val = BrailleDictionary.STATE_IMMUTABLE
    c_val = BrailleDictionary.PRIV_ADMIN
    proof = geometry.verify_action(d_val, i_val, s_val, c_val)
    assert proof.is_valid is False
    assert "Z3_UNSAT" in proof.reason
    assert proof.result == "UNSAT"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
