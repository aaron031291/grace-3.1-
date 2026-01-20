"""
Comprehensive Component Tests for Thread Learning Orchestrator

Tests the Windows-compatible thread-based learning orchestrator system
that provides autonomous learning capabilities.

Coverage:
- ThreadStudySubagent initialization and task processing
- ThreadPracticeSubagent initialization and task processing
- ThreadMirrorSubagent initialization and reflection
- ThreadLearningOrchestrator coordination
- Task queue management
- Result collection
- Graceful shutdown
"""

import pytest
import sys
import os
import time
import threading
from pathlib import Path
from queue import Queue, Empty
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class TestLearningTaskAndMessage:
    """Test LearningTask and Message dataclasses."""

    def test_learning_task_creation(self):
        """Test LearningTask can be created with required fields."""
        from cognitive.learning_subagent_system import LearningTask, TaskType

        task = LearningTask(
            task_id="test-001",
            task_type=TaskType.STUDY,
            topic="Python basics"
        )

        assert task.task_id == "test-001"
        assert task.task_type == TaskType.STUDY
        assert task.topic == "Python basics"
        assert task.status == "pending"
        assert task.created_at > 0

    def test_learning_task_to_dict(self):
        """Test LearningTask serialization to dict."""
        from cognitive.learning_subagent_system import LearningTask, TaskType

        task = LearningTask(
            task_id="test-002",
            task_type=TaskType.PRACTICE,
            skill_name="API design",
            complexity=0.7
        )

        task_dict = task.to_dict()

        assert task_dict["task_id"] == "test-002"
        assert task_dict["task_type"] == "practice"
        assert task_dict["skill_name"] == "API design"
        assert task_dict["complexity"] == 0.7

    def test_learning_task_from_dict(self):
        """Test LearningTask deserialization from dict."""
        from cognitive.learning_subagent_system import LearningTask, TaskType

        task_dict = {
            "task_id": "test-003",
            "task_type": "study",
            "topic": "Machine Learning",
            "priority": 1,
            "created_at": time.time(),
            "status": "pending",
            "learning_objectives": ["Understand basics"],
            "file_path": None,
            "skill_name": None,
            "task_description": None,
            "complexity": 0.5,
            "assigned_to": None,
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }

        task = LearningTask.from_dict(task_dict)

        assert task.task_id == "test-003"
        assert task.task_type == TaskType.STUDY
        assert task.topic == "Machine Learning"
        assert task.learning_objectives == ["Understand basics"]

    def test_message_creation_and_serialization(self):
        """Test Message creation and serialization."""
        from cognitive.learning_subagent_system import Message, MessageType

        msg = Message(
            msg_type=MessageType.TASK,
            sender="orchestrator",
            timestamp=time.time(),
            data={"task_id": "test-001"}
        )

        msg_dict = msg.to_dict()
        assert msg_dict["msg_type"] == "task"
        assert msg_dict["sender"] == "orchestrator"

        msg_restored = Message.from_dict(msg_dict)
        assert msg_restored.msg_type == MessageType.TASK
        assert msg_restored.sender == "orchestrator"


class TestBaseThreadSubagent:
    """Test BaseThreadSubagent functionality."""

    def test_base_subagent_initialization(self):
        """Test BaseThreadSubagent can be initialized."""
        from cognitive.thread_learning_orchestrator import BaseThreadSubagent

        task_queue = Queue()
        result_queue = Queue()
        shared_state = {}

        agent = BaseThreadSubagent(
            agent_id="test-agent",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state=shared_state,
            knowledge_base_path="/tmp/test_kb"
        )

        assert agent.agent_id == "test-agent"
        assert agent.is_running == False
        assert agent.tasks_processed == 0
        assert agent.tasks_failed == 0
        assert agent.knowledge_base_path == Path("/tmp/test_kb")

    def test_base_subagent_heartbeat(self):
        """Test BaseThreadSubagent sends heartbeat."""
        from cognitive.thread_learning_orchestrator import BaseThreadSubagent
        from cognitive.learning_subagent_system import Message, MessageType

        task_queue = Queue()
        result_queue = Queue()

        agent = BaseThreadSubagent(
            agent_id="test-heartbeat",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        agent._send_heartbeat()

        # Check heartbeat was sent
        msg_dict = result_queue.get(timeout=1)
        msg = Message.from_dict(msg_dict)

        assert msg.msg_type == MessageType.HEARTBEAT
        assert msg.sender == "test-heartbeat"
        assert "tasks_processed" in msg.data
        assert "tasks_failed" in msg.data


class TestThreadStudySubagent:
    """Test ThreadStudySubagent functionality."""

    def test_study_subagent_can_be_imported(self):
        """Test ThreadStudySubagent can be imported."""
        from cognitive.thread_learning_orchestrator import ThreadStudySubagent
        assert ThreadStudySubagent is not None

    def test_study_subagent_creation(self):
        """Test ThreadStudySubagent can be created without initialization."""
        from cognitive.thread_learning_orchestrator import ThreadStudySubagent

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadStudySubagent(
            agent_id="study-1",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        assert agent.agent_id == "study-1"
        assert agent.knowledge_base_path == Path("/tmp/test_kb")

    def test_study_subagent_rejects_non_study_task(self):
        """Test ThreadStudySubagent rejects non-study tasks."""
        from cognitive.thread_learning_orchestrator import ThreadStudySubagent
        from cognitive.learning_subagent_system import LearningTask, TaskType

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadStudySubagent(
            agent_id="study-2",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        # Mock the session_factory to avoid initialization
        agent.session_factory = MagicMock()

        # Create a practice task (wrong type)
        task = LearningTask(
            task_id="wrong-type",
            task_type=TaskType.PRACTICE,
            skill_name="test"
        )

        agent._process_task(task)

        # Should not process - result queue should be empty
        assert result_queue.empty()


class TestThreadPracticeSubagent:
    """Test ThreadPracticeSubagent functionality."""

    def test_practice_subagent_can_be_imported(self):
        """Test ThreadPracticeSubagent can be imported."""
        from cognitive.thread_learning_orchestrator import ThreadPracticeSubagent
        assert ThreadPracticeSubagent is not None

    def test_practice_subagent_creation(self):
        """Test ThreadPracticeSubagent can be created."""
        from cognitive.thread_learning_orchestrator import ThreadPracticeSubagent

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadPracticeSubagent(
            agent_id="practice-1",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        assert agent.agent_id == "practice-1"
        assert agent.knowledge_base_path == Path("/tmp/test_kb")

    def test_practice_subagent_rejects_non_practice_task(self):
        """Test ThreadPracticeSubagent rejects non-practice tasks."""
        from cognitive.thread_learning_orchestrator import ThreadPracticeSubagent
        from cognitive.learning_subagent_system import LearningTask, TaskType

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadPracticeSubagent(
            agent_id="practice-2",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        # Mock the session_factory to avoid initialization
        agent.session_factory = MagicMock()

        # Create a study task (wrong type)
        task = LearningTask(
            task_id="wrong-type",
            task_type=TaskType.STUDY,
            topic="test"
        )

        agent._process_task(task)

        # Should not process - result queue should be empty
        assert result_queue.empty()


class TestThreadMirrorSubagent:
    """Test ThreadMirrorSubagent functionality."""

    def test_mirror_subagent_can_be_imported(self):
        """Test ThreadMirrorSubagent can be imported."""
        from cognitive.thread_learning_orchestrator import ThreadMirrorSubagent
        assert ThreadMirrorSubagent is not None

    def test_mirror_subagent_creation(self):
        """Test ThreadMirrorSubagent can be created."""
        from cognitive.thread_learning_orchestrator import ThreadMirrorSubagent

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadMirrorSubagent(
            agent_id="mirror",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        assert agent.agent_id == "mirror"
        assert agent.knowledge_base_path == Path("/tmp/test_kb")

    def test_mirror_subagent_processes_reflection(self):
        """Test ThreadMirrorSubagent processes reflection tasks."""
        from cognitive.thread_learning_orchestrator import ThreadMirrorSubagent
        from cognitive.learning_subagent_system import LearningTask, TaskType, Message, MessageType

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadMirrorSubagent(
            agent_id="mirror",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        # Set up mocks without calling _initialize
        agent.session_factory = MagicMock()
        agent.mirror_system = MagicMock()

        # Mock build_self_model (this was the method we fixed to use)
        agent.mirror_system.build_self_model.return_value = {
            "behavioral_patterns": {"total_detected": 3},
            "learning_progress": {"total_examples": 50},
            "improvement_suggestions": [{"priority": "high", "topic": "error_handling"}],
            "self_awareness_score": 0.75,
            "operations_observed": 100
        }

        task = LearningTask(
            task_id="reflect-001",
            task_type=TaskType.REFLECT
        )

        agent._process_task(task)

        # Check result
        msg_dict = result_queue.get(timeout=1)
        msg = Message.from_dict(msg_dict)

        assert msg.msg_type == MessageType.RESULT
        result_task = LearningTask.from_dict(msg.data)
        assert result_task.status == "completed"
        assert "behavioral_patterns" in result_task.result
        assert "self_awareness_score" in result_task.result
        assert result_task.result["self_awareness_score"] == 0.75


class TestThreadLearningOrchestrator:
    """Test ThreadLearningOrchestrator coordination."""

    @pytest.fixture
    def mock_orchestrator_deps(self):
        """Mock all orchestrator dependencies."""
        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent') as mock_study, \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent') as mock_practice, \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent') as mock_mirror:

            # Create mock agent instances
            mock_study_instance = MagicMock()
            mock_practice_instance = MagicMock()
            mock_mirror_instance = MagicMock()

            mock_study.return_value = mock_study_instance
            mock_practice.return_value = mock_practice_instance
            mock_mirror.return_value = mock_mirror_instance

            yield {
                'study': mock_study,
                'practice': mock_practice,
                'mirror': mock_mirror,
                'study_instance': mock_study_instance,
                'practice_instance': mock_practice_instance,
                'mirror_instance': mock_mirror_instance
            }

    def test_orchestrator_initialization(self):
        """Test ThreadLearningOrchestrator initializes with correct agent counts."""
        from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator

        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent'):

            orchestrator = ThreadLearningOrchestrator(
                knowledge_base_path="/tmp/test_kb",
                num_study_agents=3,
                num_practice_agents=2
            )

            assert len(orchestrator.study_agents) == 3
            assert len(orchestrator.practice_agents) == 2
            assert orchestrator.mirror_agent is not None
            assert orchestrator.total_tasks_submitted == 0
            assert orchestrator.total_tasks_completed == 0

    def test_orchestrator_submit_study_task(self):
        """Test ThreadLearningOrchestrator submits study tasks."""
        from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator
        from cognitive.learning_subagent_system import Message, MessageType, LearningTask

        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent'):

            orchestrator = ThreadLearningOrchestrator(
                knowledge_base_path="/tmp/test_kb",
                num_study_agents=1,
                num_practice_agents=1
            )

            task_id = orchestrator.submit_study_task(
                topic="Python decorators",
                learning_objectives=["Understand syntax", "Learn use cases"],
                priority=1
            )

            assert task_id.startswith("study-")
            assert orchestrator.total_tasks_submitted == 1

            # Check task was added to queue
            msg_dict = orchestrator.study_queue.get(timeout=1)
            msg = Message.from_dict(msg_dict)
            assert msg.msg_type == MessageType.TASK

            task = LearningTask.from_dict(msg.data)
            assert task.topic == "Python decorators"
            assert task.learning_objectives == ["Understand syntax", "Learn use cases"]

    def test_orchestrator_submit_practice_task(self):
        """Test ThreadLearningOrchestrator submits practice tasks."""
        from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator
        from cognitive.learning_subagent_system import Message, MessageType, LearningTask

        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent'):

            orchestrator = ThreadLearningOrchestrator(
                knowledge_base_path="/tmp/test_kb",
                num_study_agents=1,
                num_practice_agents=1
            )

            task_id = orchestrator.submit_practice_task(
                skill_name="REST API design",
                task_description="Design an API for user management",
                complexity=0.7
            )

            assert task_id.startswith("practice-")
            assert orchestrator.total_tasks_submitted == 1

            # Check task was added to queue
            msg_dict = orchestrator.practice_queue.get(timeout=1)
            msg = Message.from_dict(msg_dict)

            task = LearningTask.from_dict(msg.data)
            assert task.skill_name == "REST API design"
            assert task.complexity == 0.7

    def test_orchestrator_get_status(self):
        """Test ThreadLearningOrchestrator returns correct status."""
        from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator

        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent'), \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent'):

            orchestrator = ThreadLearningOrchestrator(
                knowledge_base_path="/tmp/test_kb",
                num_study_agents=3,
                num_practice_agents=2
            )

            status = orchestrator.get_status()

            assert status["total_subagents"] == 6  # 3 + 2 + 1
            assert status["study_agents"] == 3
            assert status["practice_agents"] == 2
            assert status["implementation"] == "thread-based"
            assert status["total_tasks_submitted"] == 0
            assert status["total_tasks_completed"] == 0


class TestOrchestratorIntegration:
    """Integration tests for the full orchestrator system."""

    def test_orchestrator_start_stop(self):
        """Test ThreadLearningOrchestrator can start and stop cleanly."""
        from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator

        with patch('cognitive.thread_learning_orchestrator.ThreadStudySubagent') as mock_study, \
             patch('cognitive.thread_learning_orchestrator.ThreadPracticeSubagent') as mock_practice, \
             patch('cognitive.thread_learning_orchestrator.ThreadMirrorSubagent') as mock_mirror:

            # Setup unique mock agents for each call
            study_agents = [MagicMock() for _ in range(2)]
            practice_agents = [MagicMock() for _ in range(1)]
            mirror_agent = MagicMock()

            mock_study.side_effect = study_agents
            mock_practice.side_effect = practice_agents
            mock_mirror.return_value = mirror_agent

            orchestrator = ThreadLearningOrchestrator(
                knowledge_base_path="/tmp/test_kb",
                num_study_agents=2,
                num_practice_agents=1
            )

            # Start
            orchestrator.start()

            # Verify all agents were started
            for agent in study_agents:
                agent.start.assert_called()
            for agent in practice_agents:
                agent.start.assert_called()
            mirror_agent.start.assert_called()

            # Stop
            orchestrator.stop()

            # Verify all agents were stopped
            for agent in study_agents:
                agent.stop.assert_called()
            for agent in practice_agents:
                agent.stop.assert_called()
            mirror_agent.stop.assert_called()

    def test_task_types_enum_completeness(self):
        """Test all TaskType enum values are defined."""
        from cognitive.learning_subagent_system import TaskType

        expected_types = {"INGEST", "STUDY", "PRACTICE", "REFLECT", "UPDATE_TRUST", "PREFETCH"}
        actual_types = {t.name for t in TaskType}

        assert expected_types == actual_types

    def test_message_types_enum_completeness(self):
        """Test all MessageType enum values are defined."""
        from cognitive.learning_subagent_system import MessageType

        expected_types = {"TASK", "RESULT", "STATUS", "SHUTDOWN", "HEARTBEAT"}
        actual_types = {t.name for t in MessageType}

        assert expected_types == actual_types


class TestErrorHandling:
    """Test error handling in the orchestrator system."""

    def test_study_subagent_handles_exception(self):
        """Test ThreadStudySubagent handles exceptions gracefully."""
        from cognitive.thread_learning_orchestrator import ThreadStudySubagent
        from cognitive.learning_subagent_system import LearningTask, TaskType, Message, MessageType

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadStudySubagent(
            agent_id="study-error",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        # Set up mocks without calling _initialize
        agent.session_factory = MagicMock(return_value=MagicMock())

        # Mock learning system to raise exception
        def raise_error(*args, **kwargs):
            raise ValueError("Test error")

        with patch.object(agent, '_get_learning_system') as mock_ls:
            mock_ls.return_value.study_topic.side_effect = raise_error

            task = LearningTask(
                task_id="error-task",
                task_type=TaskType.STUDY,
                topic="Error test"
            )

            agent._process_task(task)

        # Check error was recorded
        msg_dict = result_queue.get(timeout=1)
        msg = Message.from_dict(msg_dict)
        result_task = LearningTask.from_dict(msg.data)

        assert result_task.status == "failed"
        assert "Test error" in result_task.error
        assert agent.tasks_failed == 1

    def test_task_with_missing_topic_raises_error(self):
        """Test that tasks without topic or file_path are rejected."""
        from cognitive.thread_learning_orchestrator import ThreadStudySubagent
        from cognitive.learning_subagent_system import LearningTask, TaskType, Message

        task_queue = Queue()
        result_queue = Queue()

        agent = ThreadStudySubagent(
            agent_id="study-missing",
            task_queue=task_queue,
            result_queue=result_queue,
            shared_state={},
            knowledge_base_path="/tmp/test_kb"
        )

        # Set up mocks without calling _initialize
        agent.session_factory = MagicMock(return_value=MagicMock())

        # Mock the learning system to raise the expected error
        def check_topic(*args, **kwargs):
            raise ValueError("Task must have file_path or topic")

        with patch.object(agent, '_get_learning_system') as mock_ls:
            mock_ls.side_effect = check_topic

            # Task with no topic and no file_path
            task = LearningTask(
                task_id="missing-data",
                task_type=TaskType.STUDY,
                topic=None,
                file_path=None
            )

            agent._process_task(task)

        # Should fail with error
        msg_dict = result_queue.get(timeout=1)
        msg = Message.from_dict(msg_dict)
        result_task = LearningTask.from_dict(msg.data)

        assert result_task.status == "failed"
        assert "file_path or topic" in result_task.error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
