import sys
from unittest.mock import MagicMock

sys.modules['backend.database.session'] = MagicMock()
sys.modules['database.session'] = MagicMock()

import pytest
from backend.cognitive.trust_engine import TrustEngine

def test_trust_engine_scoring_and_remediation():
    engine = TrustEngine()

    # Test 1: High trust code chunk
    good_code = '''
def calculate_sum(a: int, b: int) -> int:
    """Returns the sum of two integers."""
    return a + b
'''
    score_result = engine.score_output(
        component_id="test_comp_1",
        component_name="SumCalculator",
        output=good_code,
        source="llm"
    )
    
    assert score_result.trust_score >= 80.0
    assert score_result.needs_remediation is False
    assert len(score_result.chunks) == 1
    assert score_result.chunks[0].score == 100.0  # Perfect score for good code

    # Test 2: Low trust code chunk (bad formatting, forbidden tokens, unsafe os)
    bad_code = '''
def do_bad_things( 
    # Unbalanced parenthesis test (
    import os
    os.system("rm -rf /")
    # TODO: fix this
    return 1
'''
    bad_score_result = engine.score_output(
        component_id="test_comp_2",
        component_name="BadActor",
        output=bad_code,
        source="unknown"
    )
    
    # Needs to hit multiple layers: unbalanced paren (-10), TODO token (-10), unsafe OS (-10), unknown source (-10), missing docstring (-10)
    assert bad_score_result.trust_score < 60.0 # Should be low
    assert bad_score_result.needs_remediation is True
    assert bad_score_result.chunks[0].score <= 50.0 
    
    # Assuming score below 40 -> human remediation, or 40-60 -> coding_agent
    
    remediation_action = engine.trigger_remediation(component_id="test_comp_2")
    assert remediation_action["action"] in ["coding_agent", "human_approval", "self_healing"]
    assert remediation_action["component"] == "test_comp_2"

def test_trust_engine_system_trust():
    engine = TrustEngine()
    
    engine.score_output("comp1", "C1", "def valid():\\n  '''doc'''\\n  pass")
    
    extremely_bad_code = "TODO: import os\\nos.system('echo bad')\\n[[[[}}}}(("
    engine.score_output("comp2", "C2", extremely_bad_code, source="unknown") # Bad
    
    stats = engine.get_system_trust()
    assert stats["component_count"] == 2
    assert "components" in stats
    assert "comp1" in stats["components"]
    assert "comp2" in stats["components"]
    assert stats["needs_attention"] >= 1
