import pytest
import os
from collections import namedtuple
from pathlib import Path

from backend.cognitive.blueprint_engine import Blueprint, create_from_prompt, _save_blueprint

def test_blueprint_create_from_prompt_success(monkeypatch, tmp_path):
    import backend.cognitive.blueprint_engine as be
    monkeypatch.setattr(be, "BLUEPRINTS_DIR", tmp_path)
    
    # Mock design
    def mock_design(prompt, bp):
        return {
            "architecture": "MVC",
            "functions": [],
            "dependencies": [],
            "success_criteria": [],
            "consensus_score": 0.9
        }
    monkeypatch.setattr(be, "_design_blueprint", mock_design)
    
    # Mock build
    def mock_build(bp, attempt):
        return "def foo(): pass"
    monkeypatch.setattr(be, "_build_from_blueprint", mock_build)
    
    # Mock test (pass on first try)
    def mock_test(code):
        return {"passed": True, "trust_score": 0.95}
    monkeypatch.setattr(be, "_test_code", mock_test)
    
    # Mock track
    monkeypatch.setattr(be, "_track_blueprint", lambda bp, status: None)
    
    # Mock retry
    monkeypatch.setattr(be, "_retry_with_revised_blueprint", lambda bp: None)
    
    res = create_from_prompt("Make a generic thing")
    
    assert res["result"] == "SUCCESS"
    assert res["status"] == "deployed"
    assert res["consensus_score"] == 0.9
    assert res["trust_score"] == 0.95
    assert "Make a generic thing" in res["task"]

def test_blueprint_create_from_prompt_retry_fail(monkeypatch, tmp_path):
    import backend.cognitive.blueprint_engine as be
    monkeypatch.setattr(be, "BLUEPRINTS_DIR", tmp_path)
    monkeypatch.setattr(be, "MAX_QWEN_RETRIES", 2)
    monkeypatch.setattr(be, "MAX_BLUEPRINT_REVISIONS", 0) # don't recurse
    
    monkeypatch.setattr(be, "_design_blueprint", lambda p, b: {"architecture": "Test"})
    monkeypatch.setattr(be, "_build_from_blueprint", lambda b, a: "def bad(): syntax error")
    monkeypatch.setattr(be, "_test_code", lambda c: {"passed": False, "error": "Syntax Error"})
    monkeypatch.setattr(be, "_track_blueprint", lambda bp, status: None)
    
    res = create_from_prompt("Make a bad thing")
    
    # Should exhaust retries and fail
    assert res["status"] == "failed"
    assert len(res["errors"]) == 2 # 2 retries
    assert "Syntax Error" in res["errors"][0]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
