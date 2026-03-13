import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.cognitive.ghost_memory import GhostMemory, get_ghost_memory

@pytest.fixture
def ghost(tmp_path):
    gm = GhostMemory()
    # Patch playbook dir for saving safely
    with patch('backend.cognitive.ghost_memory.PLAYBOOK_DIR', tmp_path):
        yield gm

def test_start_and_append(ghost):
    ghost.start_task("Test task")
    assert ghost.get_stats()["active_task"] is True
    
    ghost.append("code", "print('hello')")
    ghost.append("success", "Worked")
    
    stats = ghost.get_stats()
    assert stats["total_turns"] == 3  # task_start + code + success
    assert stats["error_free_turns"] == 3
    
    # Error resets error_free_turns
    ghost.append("error", "SyntaxError")
    assert ghost.get_stats()["error_free_turns"] == 0
    assert ghost.get_stats()["total_turns"] == 4

def test_cache_bounds(ghost):
    ghost.start_task("Test task")
    for i in range(250):
        ghost.append("code", f"statement {i}")
        
    stats = ghost.get_stats()
    assert stats["cache_size"] == 150  # 1..201 -> 100, plus next 49 appends + 1 for task_start = 150
    assert stats["total_turns"] == 251

def test_get_context(ghost):
    ghost.start_task("Test task")
    ghost.append("info", "Small chunk")
    for _ in range(5):
        ghost.append("info", "A" * 1000)  # Huge chunk
    
    context = ghost.get_context(max_tokens=100)
    # The max_tokens filter will truncate
    assert "Small chunk" not in context  # Might be pushed out by the big text slice
    # 'A' * 10000 sliced to 200 chars in log
    assert len(context) > 0

def test_is_task_done(ghost):
    ghost.start_task("Test task")
    assert ghost.is_task_done() is False
    
    # needs 6 error_free_turns and 3 total_turns
    for _ in range(5):
        ghost.append("pass", "ok")
        
    assert ghost.is_task_done() is True

@patch('api._genesis_tracker.track')  # Mock genesis tracker
def test_complete_task(mock_track, ghost):
    ghost.start_task("Testing completion")
    ghost.append("code", "def foo(): pass")
    ghost.append("success", "Great")
    
    # This invokes reflection and saves to PLAYBOOK_DIR
    res = ghost.complete_task()
    
    assert res["reflection"]["pattern_name"] == "clean_success"
    assert res["reflection"]["errors_encountered"] == 0
    assert ghost.get_stats()["active_task"] is False
    
def test_evolve_playbook(ghost, tmp_path):
    # Create 3 fake playbooks with the same pattern_name
    for i in range(3):
        fake_data = {
            "pattern_name": "clean_success",
            "confidence": 0.5 + (i * 0.1),
            "errors": 0
        }
        (tmp_path / f"clean_success_{i}.json").write_text(json.dumps(fake_data))
        
    res = ghost.evolve_playbook()
    
    assert res["patterns_total"] == 1
    assert res["merged"] == 1
    
    # Check that merged playbook exists
    merged_file = tmp_path / "clean_success_merged.json"
    assert merged_file.exists()
    
    data = json.loads(merged_file.read_text())
    assert data["merged_count"] == 3
    assert data["confidence"] == 0.7  # highest of 0.5, 0.6, 0.7
