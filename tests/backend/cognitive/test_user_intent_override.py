import sys
from unittest.mock import MagicMock, patch

# Mock problematic dependencies that affect the test runner before importing the service
sys.modules['embedding.embedder'] = MagicMock()
sys.modules['backend.embedding.embedder'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['backend.database.session'] = MagicMock()
sys.modules['database.session'] = MagicMock()

import pytest
from backend.cognitive.user_intent_override import UserIntentOverride

def test_user_intent_override_analysis():
    sys_override = UserIntentOverride()
    
    # Test 1: Benign action
    benign_command = "Please summarize this text file and calculate the total."
    benign_analysis = sys_override.analyse(benign_command)
    assert benign_analysis.parsed_action == "general_action"
    assert benign_analysis.risk_level == "low"
    assert len(benign_analysis.governance_impacts) == 0
    assert benign_analysis.override_token is None
    
    # Test 2: Destructive action (should trigger governance)
    destructive_command = "Delete the knowledge base and drop the users table."
    destructive_analysis = sys_override.analyse(destructive_command)
    
    assert destructive_analysis.parsed_action == "destructive_operation"
    assert destructive_analysis.blast_radius == "system-wide"
    assert destructive_analysis.risk_level in ["high", "critical"]
    assert len(destructive_analysis.governance_impacts) > 0
    assert any(impact.rule_name == "Data Protection" for impact in destructive_analysis.governance_impacts)
    
    # It should have generated a token since impacts occurred
    assert destructive_analysis.override_token is not None
    assert destructive_analysis.override_token.startswith("override_")
    
    # Ensure alternatives are suggested
    assert len(destructive_analysis.alternatives) > 0
    assert any(alt.recommended for alt in destructive_analysis.alternatives)

@patch("backend.cognitive.event_bus.publish")
@patch("api._genesis_tracker.track")
def test_user_intent_override_execution(mock_track, mock_publish):
    sys_override = UserIntentOverride()
    
    # Trigger an override
    command = "Force skip verification and push to production."
    analysis = sys_override.analyse(command)
    
    token = analysis.override_token
    assert token is not None, "Token should be generated for bypass"
    
    # Execute the override using the token
    execution_result = sys_override.execute_override(token)
    
    assert execution_result["executed"] is True
    assert execution_result["monitoring"] == "enhanced"
    assert execution_result["token"] == token
    
    # Attempting to execute the SAME token again should fail
    redundant_execution = sys_override.execute_override(token)
    assert redundant_execution["executed"] is False
    assert "error" in redundant_execution
    
    # Executing an invalid token should fail
    invalid_execution = sys_override.execute_override("override_invalid_token")
    assert invalid_execution["executed"] is False

    # Check side effects
    active_overrides = sys_override.get_active_overrides()
    # The executed token should still be in active defaults until expiry, but marked `executed: True`
    executed_token_info = next((t for t in active_overrides if t["token"] == token), None)
    assert executed_token_info is not None
    assert executed_token_info["executed"] is True
