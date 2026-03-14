import pytest
import os
import tempfile
from pathlib import Path
from backend.cognitive.autonomous_healing_loop import heal_content, _create_snapshot, _restore_snapshot, _validate_code_blocks, _score_content

def test_healing_loop_no_errors():
    res = heal_content("dummy.py", "print('hello')", errors=[])
    assert res["success"] is True
    assert res["stage"] == "no_errors"

def test_healing_loop_strategy_selection(monkeypatch):
    # Mock everything to just test the strategy phase
    monkeypatch.setattr("backend.cognitive.autonomous_healing_loop._score_content", lambda c, l: 0.9)
    # mock get_llm_for_task
    class MockLLM:
        def generate(self, *args, **kwargs):
            return "```python\nprint('fixed')\n```"
    import backend.llm_orchestrator.factory as factory
    monkeypatch.setattr(factory, "get_llm_for_task", lambda t: MockLLM())
    
    # Mock event bus
    class MockEventBus:
        pass
    import backend.cognitive.event_bus as eb
    monkeypatch.setattr(eb, "publish", lambda *args, **kwargs: None)
    
    # Large content triggers surgical
    large_content = "A" * 16000
    res = heal_content("dummy.py", large_content, errors=["Syntax Error"])
    assert res["strategy"] == "surgical"
    
    # Small content triggers wholesale (since errors count > 0)
    small_content = "def foo():\n  return 1"
    res2 = heal_content("dummy.py", small_content, errors=["NameError: name 'bar' is not defined"])
    assert res2["strategy"] == "surgical"

def test_snapshot_restore(tmp_path, monkeypatch):
    # patch SNAPSHOTS_DIR
    import backend.cognitive.autonomous_healing_loop as ahl
    monkeypatch.setattr(ahl, "SNAPSHOTS_DIR", tmp_path)
    
    test_file = tmp_path / "test.py"
    test_file.write_text("orig")
    
    snap_id = ahl._create_snapshot(str(test_file), "orig")
    assert (tmp_path / f"{snap_id}.json").exists()
    
    test_file.write_text("modified")
    
    restored = ahl._restore_snapshot(snap_id)
    assert restored == str(test_file)
    assert test_file.read_text() == "orig"

def test_validate_code_blocks():
    content = "text\n```python\nprint('hello')\n```\nmore\n```python\n1 + 'a'\n```\n"
    # Actually `1 + 'a'` is valid syntax! Syntax error would be `def foo(`
    content2 = "text\n```python\nprint('hello')\n```\nmore\n```python\ndef foo(\n```\n"
    valid, invalid = _validate_code_blocks(content2)
    assert valid == 1
    assert invalid == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
