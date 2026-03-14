import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.cognitive.live_integration import (
    ComponentCandidate,
    IntegrationStage,
    CitizenshipLevel,
    integrate_component,
    _stage_syntax,
    _stage_analyse,
    _stage_trust,
    _stage_citizenship
)

def test_stage_syntax_valid():
    code = '''
class MyClass:
    def do_work(self):
        pass

def helper():
    import json
    return True
'''
    cand = ComponentCandidate("test.py", code, "hash")
    cand = _stage_syntax(cand)
    
    assert cand.stage == IntegrationStage.SYNTAX_OK
    assert "MyClass" in cand.classes
    assert "helper" in cand.functions
    assert not cand.errors

def test_stage_syntax_invalid():
    code = '''
def bad_syntax()
    pass
'''
    cand = ComponentCandidate("test.py", code, "hash")
    cand = _stage_syntax(cand)
    
    assert cand.stage == IntegrationStage.FAILED
    assert len(cand.errors) > 0

def test_stage_analyse():
    code = '''
"""
This is a test module for handling data processing.
"""
class Processor:
    def process_data(self):
        pass
        
def search_items():
    pass

def fix_errors():
    pass
'''
    cand = ComponentCandidate("test.py", code, "hash")
    cand = _stage_syntax(cand)
    cand = _stage_analyse(cand)
    
    assert cand.stage == IntegrationStage.ANALYSED
    assert "This is a test module" in cand.purpose
    assert "search" in cand.capabilities
    assert "healing" in cand.capabilities

def test_stage_trust_and_citizenship():
    import sys
    sys.modules["cognitive.trust_engine"] = MagicMock()
    cand = ComponentCandidate("test.py", "", "hash")
    cand.purpose = "Good purpose with long detailed explanation to boost score."
    cand.functions = ["test_func", "do_thing"]
    cand.imports = ["cognitive.memory", "json"]
    
    cand = _stage_trust(cand)
    assert cand.stage == IntegrationStage.TRUST_SCORED
    assert cand.trust_score > 0.4
    
    cand = _stage_citizenship(cand)
    assert cand.citizenship in [CitizenshipLevel.VISITOR, CitizenshipLevel.RESIDENT, CitizenshipLevel.CITIZEN]

@patch("backend.cognitive.live_integration._LEDGER_PATH", new=Path(tempfile.gettempdir()) / "test_ledger.json")
def test_integrate_component_end_to_end():
    import sys
    sys.modules["cognitive.adaptive_test_generator"] = MagicMock()
    sys.modules["cognitive.unified_memory"] = MagicMock()
    sys.modules["cognitive.flash_cache"] = MagicMock()
    
    # Use a dummy Python snippet directly without needing to touch disk
    code = '''
"""
Smart test component.
"""
def search_things():
    pass
'''
    with patch("backend.cognitive.live_integration._stage_register", lambda c: c):
        with patch("backend.cognitive.live_integration._stage_compass", lambda c: c):
            res = integrate_component("dummy.py", source_code=code)
            
            assert "syntax_ok" in res["stage"] or "live" in res["stage"] or res["stage"] in ("registered", "discovered", "analysed", "trust_scored", "compass_mapped")
            assert "search" in res["capabilities"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
