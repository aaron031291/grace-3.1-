import pytest
import time
from queue import Empty
from backend.cognitive.learning_subagent_system import Message, MessageType
from backend.cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator, ThreadStudySubagent

def test_thread_learning_orchestrator():
    orchestrator = ThreadLearningOrchestrator(knowledge_base_path="dummy_path", num_study_agents=1, num_practice_agents=0)
    
    # We won't start the threads to avoid hanging tests, just submit a task and check the queue
    task_id = orchestrator.submit_study_task("quantum computing", ["learn basics"])
    assert task_id.startswith("study-")
    
    # Check that it made it to the queue
    msg_dict = orchestrator.study_queue.get(timeout=1)
    msg = Message.from_dict(msg_dict)
    assert msg.msg_type == MessageType.TASK
    assert msg.data["topic"] == "quantum computing"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
