import pytest
import json
from unittest.mock import MagicMock
from pathlib import Path
from datetime import datetime, timezone
import hashlib

from backend.cognitive.memory_mesh_snapshot import MemoryMeshSnapshot, create_memory_mesh_snapshot
from backend.cognitive.learning_memory import LearningExample, LearningPattern

def test_snapshot_creation(tmp_path):
    session = MagicMock()
    
    snapshot_dir = tmp_path / "kb"
    snapshotter = MemoryMeshSnapshot(session, snapshot_dir)
    
    # Mock data
    ex = MagicMock()
    ex.id = "lex-1"
    ex.example_type = "test_type"
    ex.input_context = "{}"
    ex.expected_output = "{}"
    ex.actual_output = "{}"
    ex.trust_score = 0.9
    ex.source_reliability = 0.8
    ex.outcome_quality = 0.7
    ex.consistency_score = 0.9
    ex.recency_weight = 1.0
    ex.source = "system"
    ex.source_user_id = None
    ex.genesis_key_id = None
    ex.times_referenced = 5
    ex.times_validated = 4
    ex.times_invalidated = 1
    ex.last_used = datetime.now(timezone.utc)
    ex.file_path = "test.py"
    ex.episodic_episode_id = None
    ex.procedure_id = None
    ex.example_metadata = "{}"
    ex.created_at = datetime.now(timezone.utc)
    ex.updated_at = datetime.now(timezone.utc)
    
    ep = MagicMock()
    ep.id = "ep-1"
    ep.problem = "p"
    ep.action = "{}"
    ep.outcome = "{}"
    ep.predicted_outcome = "{}"
    ep.prediction_error = 0.1
    ep.trust_score = 0.9
    ep.source = "test"
    ep.genesis_key_id = None
    ep.decision_id = None
    ep.timestamp = datetime.now(timezone.utc)
    ep.embedding = "[0.1]"
    ep.episode_metadata = "{}"
    ep.created_at = datetime.now(timezone.utc)
    ep.updated_at = datetime.now(timezone.utc)
    
    pr = MagicMock()
    pr.id = "pr-1"
    pr.name = "test_proc"
    pr.goal = "test"
    pr.procedure_type = "test"
    pr.steps = "[]"
    pr.preconditions = "{}"
    pr.trust_score = 0.9
    pr.success_rate = 0.8
    pr.usage_count = 10
    pr.success_count = 8
    pr.supporting_examples = "[]"
    pr.learned_from_episode_id = None
    pr.embedding = "[0.1]"
    pr.procedure_metadata = "{}"
    pr.created_at = datetime.now(timezone.utc)
    pr.updated_at = datetime.now(timezone.utc)
    
    pat = MagicMock()
    pat.id = "pat-1"
    pat.pattern_name = "test_pat"
    pat.pattern_type = "topic"
    pat.preconditions = "{}"
    pat.actions = "{}"
    pat.expected_outcomes = "{}"
    pat.trust_score = 0.9
    pat.success_rate = 0.9
    pat.sample_size = 10
    pat.supporting_examples = "[]"
    pat.times_applied = 10
    pat.times_succeeded = 9
    pat.times_failed = 1
    pat.linked_procedures = "[]"
    pat.created_at = datetime.now(timezone.utc)
    pat.updated_at = datetime.now(timezone.utc)
    
    def mock_query(model):
        m = MagicMock()
        if model.__name__ == 'LearningExample':
            m.all.return_value = [ex]
            m.count.return_value = 1
        elif model.__name__ == 'Episode':
            m.all.return_value = [ep]
            m.count.return_value = 1
        elif model.__name__ == 'Procedure':
            m.all.return_value = [pr]
            m.count.return_value = 1
        elif model.__name__ == 'LearningPattern':
            m.all.return_value = [pat]
            m.count.return_value = 1
        m.filter.return_value.count.return_value = 1
        return m
    
    session.query.side_effect = mock_query
    
    snapshot = snapshotter.create_snapshot()
    
    assert snapshot["learning_memory"]["total_examples"] == 1
    assert snapshot["episodic_memory"]["total_episodes"] == 1
    assert snapshot["procedural_memory"]["total_procedures"] == 1
    assert snapshot["pattern_memory"]["total_patterns"] == 1
    assert snapshot["statistics"]["total_memories"] == 4

def test_save_load_snapshot(tmp_path):
    session = MagicMock()
    
    snapshot_dir = tmp_path / "kb"
    snapshotter = MemoryMeshSnapshot(session, snapshot_dir)
    
    snapshot = {
        "snapshot_metadata": {
            "timestamp": "2026-03-14T11:00:00Z"
        },
        "test": "data"
    }
    
    path = snapshotter.save_snapshot(snapshot)
    assert Path(path).exists()
    
    loaded = snapshotter.load_snapshot()
    assert loaded["test"] == "data"
    
def test_compare_snapshots():
    session = MagicMock()
    snapshotter = MemoryMeshSnapshot(session, Path("test"))
    
    s1 = {
        "snapshot_metadata": {"timestamp": "t1"},
        "statistics": {
            "learning_examples": 10,
            "episodic_memories": 5,
            "procedural_memories": 2,
            "extracted_patterns": 1,
            "trust_ratio": 0.5
        }
    }
    
    s2 = {
        "snapshot_metadata": {"timestamp": "t2"},
        "statistics": {
            "learning_examples": 12, # +2
            "episodic_memories": 6,  # +1
            "procedural_memories": 3, # +1
            "extracted_patterns": 1, # +0
            "trust_ratio": 0.6       # +0.1
        }
    }
    
    diff = snapshotter.compare_snapshots(s1, s2)
    assert diff["learning_diff"]["added"] == 2
    assert diff["episodic_diff"]["added"] == 1
    assert diff["procedural_diff"]["added"] == 1
    assert diff["pattern_diff"]["added"] == 0
    assert diff["trust_quality_change"]["improvement"] == pytest.approx(0.1)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
