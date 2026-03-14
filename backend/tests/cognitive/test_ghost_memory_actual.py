import pytest
import time
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.cognitive.ghost_memory import GhostMemory, get_ghost_memory

@pytest.fixture
def mock_playbook_dir(tmp_path, monkeypatch):
    playbook_dir = tmp_path / "ghost_playbook"
    import backend.cognitive.ghost_memory as gm
    monkeypatch.setattr(gm, "PLAYBOOK_DIR", playbook_dir)
    return playbook_dir

@pytest.fixture
def ghost_mem(mock_playbook_dir):
    # Reset singleton
    GhostMemory._instance = None
    gm = get_ghost_memory()
    return gm

def test_ghost_memory_singleton():
    gm1 = get_ghost_memory()
    gm2 = get_ghost_memory()
    assert gm1 is gm2

def test_start_and_append_task(ghost_mem):
    ghost_mem.start_task("Test task")
    assert ghost_mem._task_id.startswith("ghost_")
    assert ghost_mem._total_turns == 1 # start_task appends one
    assert ghost_mem._error_free_turns == 1
    
    ghost_mem.append("success", "step 1 completed")
    assert ghost_mem._total_turns == 2
    assert ghost_mem._error_free_turns == 2
    
    ghost_mem.append("error", "something went wrong")
    assert ghost_mem._total_turns == 3
    assert ghost_mem._error_free_turns == 0 # reset on error

def test_get_context(ghost_mem):
    ghost_mem.start_task("Context task")
    ghost_mem.append("info", "Information")
    context = ghost_mem.get_context(max_tokens=100)
    assert "[task_start] Context task" in context
    assert "[info] Information" in context

def test_is_task_done(ghost_mem):
    ghost_mem.start_task("Done task")
    
    # Needs >= 6 error free turns and >= 3 total turns
    for _ in range(5):
        ghost_mem.append("success", "progress")
        
    assert ghost_mem.is_task_done() is True
    
    ghost_mem.append("error", "fail")
    assert ghost_mem.is_task_done() is False

@patch("backend.cognitive.ghost_memory.track", create=True)
@patch("backend.cognitive.ghost_memory.get_unified_memory", create=True)
def test_complete_task(mock_get_unified_memory, mock_track, ghost_mem):
    ghost_mem.start_task("Complete task")
    ghost_mem.append("success", "step 1")
    
    result = ghost_mem.complete_task()
    
    assert "reflection" in result
    assert result["turns"] == 2
    assert result["reflection"]["task"] == "Complete task"
    assert result["reflection"]["pattern_name"] == "clean_success"
    
    # Should have cleared cache
    assert len(ghost_mem._cache) == 0

def test_reflect_patterns(ghost_mem):
    ghost_mem.start_task("Pattern task")
    ghost_mem.append("error", "fail 1")
    ghost_mem.append("error", "fail 2")
    reflection = ghost_mem._reflect()
    assert reflection["pattern_name"] == "struggled_success"
    
    ghost_mem.start_task("Pattern task 2")
    ghost_mem.append("error", "fail 1")
    ghost_mem.append("success", "fix 1")
    ghost_mem.append("success", "fix 2")
    reflection = ghost_mem._reflect()
    assert reflection["pattern_name"] == "recovered_success"

def test_evolve_playbook(ghost_mem, mock_playbook_dir):
    mock_playbook_dir.mkdir(parents=True, exist_ok=True)
    
    # Create 3 similar patterns to trigger merge
    for i in range(3):
        data = {
            "pattern_name": "clean_success",
            "confidence": 0.8 + (i * 0.05),
            "task": f"Task {i}"
        }
        (mock_playbook_dir / f"clean_success_{i}.json").write_text(json.dumps(data))
        
    stats = ghost_mem.evolve_playbook()
    
    assert stats["patterns_total"] == 1
    assert stats["merged"] == 1
    
    merged_file = mock_playbook_dir / "clean_success_merged.json"
    assert merged_file.exists()
    
    merged_data = json.loads(merged_file.read_text())
    assert merged_data["merged_count"] == 3
    assert merged_data["confidence"] == 0.9  # highest
    assert merged_data["avg_confidence"] == pytest.approx(0.85)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
