import pytest
import sys
import queue
from pathlib import Path
from unittest.mock import MagicMock, patch
from backend.cognitive.proactive_learner import (
    LearningTask,
    FileMonitorHandler,
    ProactiveLearningSubagent,
    ProactiveLearningOrchestrator
)

def test_file_monitor_handler():
    q = queue.Queue()
    kb_path = Path("/tmp/kb")
    handler = FileMonitorHandler(q, kb_path)
    
    # Mock file hash
    handler._get_file_hash = MagicMock(return_value="mockhash123")
    
    # Event mock
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/kb/test.py"
    
    # Test on_created
    handler.on_created(event)
    assert q.qsize() == 1
    task = q.get()
    assert task.task_type == "ingest_and_study"
    assert "mockhash" in task.task_id
    assert str(Path("/tmp/kb/test.py")) in handler.processed_files

def test_learner_subagent_run_loop():
    q = queue.Queue()
    agent = ProactiveLearningSubagent("agent-test", q, Path("/tmp"))
    
    task = LearningTask("t1", "study", topic="backend")
    agent._study_topic = MagicMock(return_value={"concepts_learned": 5})
    
    # Push task directly and call process
    q.put(task)
    agent.current_tasks[task.task_id] = task
    agent._process_task(task)
    
    assert agent.tasks_completed == 1
    assert agent.total_concepts_learned == 5
    assert task.status == "completed"

def test_orchestrator_add_task():
    orch = ProactiveLearningOrchestrator(Path("/tmp"), num_subagents=1)
    task_id = orch.add_learning_task("practice", topic="python", priority=1)
    
    assert orch.learning_queue.qsize() == 1
    task = orch.learning_queue.get()
    assert task.task_id == task_id
    assert task.topic == "python"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
