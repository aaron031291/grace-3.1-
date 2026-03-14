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
    
    # 100 - 4 (llm source) = 96.0
    assert score_result.trust_score >= 80.0
    assert score_result.needs_remediation is False
    assert len(score_result.chunks) == 1
    assert score_result.chunks[0].score == 96.0

    # Test 2: Low trust code chunk (unbalanced parens, TODO, unsafe os.system, missing docstring, unknown source)
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
    
    # Penalties: unbalanced parens (-10), TODO (-3), os.system( (-20), missing docstring (-3), unknown source (-12)
    # 100 - 10 - 3 - 20 - 3 - 12 = 52.0
    assert bad_score_result.trust_score < 60.0
    assert bad_score_result.needs_remediation is True
    assert bad_score_result.chunks[0].score == 52.0
    
    remediation_action = engine.trigger_remediation(component_id="test_comp_2")
    assert remediation_action["action"] in ["coding_agent", "human_approval", "self_healing"]
    assert remediation_action["component"] == "test_comp_2"

def test_trust_engine_system_trust():
    engine = TrustEngine()
    
    engine.score_output("comp1", "C1", "def valid():\n  '''doc'''\n  pass")
    
    extremely_bad_code = "TODO: import os\nos.system('echo bad')\n[[[[}}}}(("
    engine.score_output("comp2", "C2", extremely_bad_code, source="unknown")
    
    stats = engine.get_system_trust()
    assert stats["component_count"] == 2
    assert "components" in stats
    assert "comp1" in stats["components"]
    assert "comp2" in stats["components"]
    assert stats["needs_attention"] >= 1

def test_trust_engine_empty_system_trust():
    """New components start at 0 and empty system returns 0."""
    engine = TrustEngine()
    stats = engine.get_system_trust()
    assert stats["system_trust"] == 0.0

def test_trust_engine_empty_chunk():
    """Empty chunks should return near-zero score."""
    engine = TrustEngine()
    score = engine._score_chunk("", "unknown")
    assert score == 5.0

def test_trust_engine_safety_penalty():
    """Safety violations carry heavy penalties."""
    engine = TrustEngine()
    unsafe = "result = eval(user_input)"
    score = engine._score_chunk(unsafe, "deterministic")
    # 100 - 20 (eval) = 80
    assert score == 80.0

def test_trust_engine_source_provenance():
    """Source provenance applies graduated penalties."""
    engine = TrustEngine()
    chunk = "This is a normal piece of text content for testing."
    deterministic = engine._score_chunk(chunk, "deterministic")
    llm = engine._score_chunk(chunk, "llm")
    unknown = engine._score_chunk(chunk, "unknown")
    assert deterministic == 100.0
    assert llm == 96.0
    assert unknown == 88.0
