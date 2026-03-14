import pytest
import time
from unittest.mock import MagicMock, patch
from multiprocessing import Queue
from backend.cognitive.learning_subagent_system import (
    LearningTask,
    TaskType,
    Message,
    MessageType,
    BaseSubagent,
    StudySubagent,
    PracticeSubagent,
    MirrorSubagent,
    LearningOrchestrator
)

def test_learning_task_serialization():
    task = LearningTask(
        task_id="test_1",
        task_type=TaskType.STUDY,
        topic="test topic"
    )
    
    d = task.to_dict()
    assert d["task_id"] == "test_1"
    assert d["task_type"] == "study"
    
    task2 = LearningTask.from_dict(d)
    assert task2.task_id == "test_1"
    assert task2.task_type == TaskType.STUDY

@patch("backend.cognitive.learning_subagent_system.Process", create=True)
def test_base_subagent_start_stop(mock_process):
    task_q = Queue()
    result_q = Queue()
    
    agent = BaseSubagent(
        agent_id="test_agent",
        task_queue=task_q,
        result_queue=result_q,
        shared_state={},
        knowledge_base_path="/tmp"
    )
    
    agent.start()
    mock_process.assert_called_once()
    assert agent.process is not None
    
    agent.stop()
    # Check that a shutdown message was sent
    msg = task_q.get()
    assert msg["msg_type"] == "shutdown"

@patch("backend.database.session.get_session_factory", create=True)
@patch("backend.database.connection.DatabaseConnection", create=True)
def test_study_subagent_process_task(mock_db_conn, mock_session_factory):
    import sys
    sys.modules["cognitive.active_learning_system"] = MagicMock()
    mock_system_instance = MagicMock()
    mock_system_instance.study_topic.return_value = {"concepts_learned": 3}
    sys.modules["cognitive.active_learning_system"].GraceActiveLearningSystem.return_value = mock_system_instance
    sys.modules["embedding"] = MagicMock()
    sys.modules["retrieval.retriever"] = MagicMock()
    
    task_q = Queue()
    result_q = Queue()
    agent = StudySubagent("study-1", task_q, result_q, {}, "/tmp")
    agent._initialize()
    
    task = LearningTask(task_id="t1", task_type=TaskType.STUDY, topic="AI")
    agent._process_task(task)
    
    assert agent.tasks_processed.value == 1
    assert agent.tasks_failed.value == 0
    
    msg_dict = result_q.get()
    msg = Message.from_dict(msg_dict)
    
    assert msg.msg_type == MessageType.RESULT
    res_task = LearningTask.from_dict(msg.data)
    assert res_task.status == "completed"
    assert res_task.result["concepts_learned"] == 3

@patch("backend.database.session.get_session_factory", create=True)
@patch("backend.database.connection.DatabaseConnection", create=True)
def test_mirror_subagent_process_task(mock_db_conn, mock_session_factory):
    task_q = Queue()
    result_q = Queue()
    agent = MirrorSubagent("mirror-1", task_q, result_q, {}, "/tmp")
    agent._initialize()
    
    # Test reflecting on a failed task
    task = LearningTask(
        task_id="t1", 
        task_type=TaskType.REFLECT, 
        skill_name="driving",
        result={"outcome": {"success": False, "feedback": "crashed"}}
    )
    agent._process_task(task)
    
    assert agent.tasks_processed.value == 1
    
    msg_dict = result_q.get()
    msg = Message.from_dict(msg_dict)
    res_task = LearningTask.from_dict(msg.data)
    
    assert res_task.status == "completed"
    assert len(res_task.result["gaps_identified"]) == 1
    assert res_task.result["gaps_identified"][0]["topic"] == "driving"

@patch("backend.cognitive.learning_subagent_system.StudySubagent", create=True)
@patch("backend.cognitive.learning_subagent_system.PracticeSubagent", create=True)
@patch("backend.cognitive.learning_subagent_system.MirrorSubagent", create=True)
def test_learning_orchestrator(mock_mirror, mock_practice, mock_study):
    orchestrator = LearningOrchestrator(
        knowledge_base_path="/tmp",
        num_study_agents=1,
        num_practice_agents=1
    )
    
    assert len(orchestrator.study_agents) == 1
    assert len(orchestrator.practice_agents) == 1
    
    orchestrator.start()
    
    # Mock processes start
    mock_study.return_value.start.assert_called()
    mock_practice.return_value.start.assert_called()
    mock_mirror.return_value.start.assert_called()
    
    # Submit a task
    orchestrator.submit_study_task("Python", ["Lists"])
    
    # It should be enqueued
    assert orchestrator.study_queue.qsize() == 1
    
    orchestrator.stop()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
