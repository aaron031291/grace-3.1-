import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.qwen_agents import (
    AgentRole, TaskPriority, TaskStatus, AgentTask, QwenAgent, QwenAgentPool
)

def test_agent_task_sorting():
    t1 = AgentTask("1", "p", AgentRole.CODE, priority=TaskPriority.HIGH)
    t2 = AgentTask("2", "p", AgentRole.CODE, priority=TaskPriority.CRITICAL)
    t3 = AgentTask("3", "p", AgentRole.CODE, priority=TaskPriority.NORMAL)
    
    tasks = [t1, t3, t2]
    tasks.sort()
    
    assert tasks[0].task_id == "2" # CRITICAL
    assert tasks[1].task_id == "1" # HIGH
    assert tasks[2].task_id == "3" # NORMAL

def test_qwen_agent_submit():
    agent = QwenAgent(AgentRole.FAST)
    task = AgentTask("t1", "test prompt", AgentRole.FAST)
    agent.submit(task)
    
    assert agent._queue.qsize() == 1
    assert "t1" in agent._tasks
    
def test_qwen_agent_execute_task_error():
    agent = QwenAgent(AgentRole.REASON)
    task = AgentTask("t1", "fail", AgentRole.REASON)
    
    # Mock to raise error
    agent._run_direct = MagicMock(side_effect=ValueError("Test error"))
    
    agent._execute_task(task)
    
    assert task.status == TaskStatus.FAILED
    assert "Test error" in task.error
    assert agent._stats["failed"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
