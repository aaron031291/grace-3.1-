import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock out heavy and broken imports
sys.modules['llm_orchestrator.llm_orchestrator'] = MagicMock()
sys.modules['llm_orchestrator.multi_llm_client'] = MagicMock()
sys.modules['cognitive.physics.bitmask_geometry'] = MagicMock()

from backend.cognitive.braille_compiler import BrailleDictionary, NLPCompilerEdge

def test_compile_schema_valid():
    json_intent = {
        "domain": "database",
        "intent": "delete",
        "target_state": "active",
        "privilege": "admin"
    }
    session_context = {
        "is_maintenance_window": True,
        "is_emergency": False,
        "has_elevation_token": True
    }
    
    d_val, i_val, s_val, c_val = BrailleDictionary.compile_schema(json_intent, session_context)
    
    assert d_val == BrailleDictionary.DOMAIN_DATABASE
    assert i_val == BrailleDictionary.INTENT_DELETE
    assert s_val == BrailleDictionary.STATE_ACTIVE
    
    # Check context/privilege mask
    assert c_val & BrailleDictionary.CTX_MAINTENANCE
    assert c_val & BrailleDictionary.CTX_ELEVATED
    assert not (c_val & BrailleDictionary.CTX_EMERGENCY)
    assert c_val & BrailleDictionary.PRIV_ADMIN

def test_compile_schema_hallucinated():
    json_intent = {"domain": "flux_capacitor"}
    with pytest.raises(ValueError, match="hallucinated"):
        BrailleDictionary.compile_schema(json_intent, {})

@patch('backend.cognitive.braille_compiler.HierarchicalZ3Geometry')
@patch('backend.cognitive.braille_compiler.get_llm_orchestrator')
def test_nlp_compiler_edge_success(mock_get_orchestrator, mock_z3):
    # Mock Orchestrator
    mock_orch_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.content = '{"domain": "api", "intent": "start", "target_state": "stopped", "privilege": "user"}'
    mock_orch_instance.execute_task.return_value = mock_result
    mock_get_orchestrator.return_value = mock_orch_instance

    # Mock Z3 Verification
    mock_z3_instance = MagicMock()
    mock_z3_instance.verify_action.return_value = (True, "Z3_VERIFIED")
    mock_z3.return_value = mock_z3_instance

    edge = NLPCompilerEdge()
    mask, msg = edge.process_command("Start the API", "user", {"is_maintenance_window": False})

    assert mask is not None
    assert len(mask) == 4
    assert mask[0] == BrailleDictionary.DOMAIN_API
    assert mask[1] == BrailleDictionary.INTENT_START
    assert msg == "Z3_VERIFIED"

@patch('backend.cognitive.braille_compiler.HierarchicalZ3Geometry')
@patch('backend.cognitive.braille_compiler.get_llm_orchestrator')
def test_nlp_compiler_edge_z3_rejected(mock_get_orchestrator, mock_z3):
    # Mock Orchestrator returning dangerous action (e.g. user deleting immutable DB)
    mock_orch_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.content = '{"domain": "database", "intent": "delete", "target_state": "immutable", "privilege": "user"}'
    mock_orch_instance.execute_task.return_value = mock_result
    mock_get_orchestrator.return_value = mock_orch_instance

    # Mock Z3 Rejecting it
    mock_z3_instance = MagicMock()
    mock_z3_instance.verify_action.return_value = (False, "UNSAT: Cannot delete immutable DB as user")
    mock_z3.return_value = mock_z3_instance

    edge = NLPCompilerEdge()
    mask, msg = edge.process_command("Delete the database", "user", {})

    assert mask is None
    assert "UNSAT" in msg
