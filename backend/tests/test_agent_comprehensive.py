"""
Comprehensive Test Suite for Grace Agent Module
================================================
Tests for the GraceAgent class and related components.

Coverage:
- TaskStatus enum
- AgentConfig dataclass
- TaskResult dataclass
- GraceAgent class methods
- Task classification
- Entity extraction
- Plan creation
- Action decision making
- Failure handling
- Convenience methods
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import uuid

# Import the module under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.grace_agent import (
    TaskStatus,
    AgentConfig,
    TaskResult,
    GraceAgent,
)


# =============================================================================
# TaskStatus Enum Tests
# =============================================================================

class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        expected = ['PENDING', 'PLANNING', 'EXECUTING', 'BLOCKED',
                    'COMPLETED', 'FAILED', 'CANCELLED']
        for status in expected:
            assert hasattr(TaskStatus, status)

    def test_status_values(self):
        """Test status string values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PLANNING.value == "planning"
        assert TaskStatus.EXECUTING.value == "executing"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_status_comparison(self):
        """Test status equality comparison."""
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.COMPLETED

    def test_status_iteration(self):
        """Test iterating over statuses."""
        statuses = list(TaskStatus)
        assert len(statuses) == 7


# =============================================================================
# AgentConfig Tests
# =============================================================================

class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AgentConfig()
        assert config.max_iterations == 50
        assert config.timeout_per_action == 300
        assert config.workspace_dir is None
        assert config.confidence_threshold == 0.5
        assert config.use_rag is True
        assert config.use_memory is True
        assert config.require_confirmation_for_git is True
        assert config.require_confirmation_for_delete is True
        assert config.auto_commit is False
        assert config.test_before_commit is True
        assert config.learn_from_execution is True
        assert config.min_confidence_for_pattern == 0.6

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AgentConfig(
            max_iterations=100,
            timeout_per_action=600,
            workspace_dir="/custom/path",
            confidence_threshold=0.8,
            use_rag=False,
            auto_commit=True,
        )
        assert config.max_iterations == 100
        assert config.timeout_per_action == 600
        assert config.workspace_dir == "/custom/path"
        assert config.confidence_threshold == 0.8
        assert config.use_rag is False
        assert config.auto_commit is True

    def test_safety_settings(self):
        """Test safety configuration settings."""
        # Default safe settings
        config = AgentConfig()
        assert config.require_confirmation_for_git is True
        assert config.require_confirmation_for_delete is True

        # Relaxed settings
        unsafe_config = AgentConfig(
            require_confirmation_for_git=False,
            require_confirmation_for_delete=False,
        )
        assert unsafe_config.require_confirmation_for_git is False
        assert unsafe_config.require_confirmation_for_delete is False

    def test_learning_settings(self):
        """Test learning configuration settings."""
        config = AgentConfig(
            learn_from_execution=False,
            min_confidence_for_pattern=0.9,
        )
        assert config.learn_from_execution is False
        assert config.min_confidence_for_pattern == 0.9


# =============================================================================
# TaskResult Tests
# =============================================================================

class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_default_values(self):
        """Test default TaskResult values."""
        result = TaskResult(task_id="TEST-001", status=TaskStatus.PENDING)
        assert result.task_id == "TEST-001"
        assert result.status == TaskStatus.PENDING
        assert result.summary == ""
        assert result.output == ""
        assert result.error is None
        assert result.actions_executed == 0
        assert result.actions_succeeded == 0
        assert result.actions_failed == 0
        assert result.files_created == []
        assert result.files_modified == []
        assert result.files_deleted == []
        assert result.patterns_learned == 0
        assert result.trust_delta == 0.0
        assert result.duration_seconds == 0.0

    def test_task_result_with_files(self):
        """Test TaskResult with file tracking."""
        result = TaskResult(
            task_id="TEST-002",
            status=TaskStatus.COMPLETED,
            files_created=["new_file.py"],
            files_modified=["existing.py"],
            files_deleted=["old_file.py"],
        )
        assert result.files_created == ["new_file.py"]
        assert result.files_modified == ["existing.py"]
        assert result.files_deleted == ["old_file.py"]

    def test_task_result_with_actions(self):
        """Test TaskResult with action counts."""
        result = TaskResult(
            task_id="TEST-003",
            status=TaskStatus.COMPLETED,
            actions_executed=10,
            actions_succeeded=8,
            actions_failed=2,
        )
        assert result.actions_executed == 10
        assert result.actions_succeeded == 8
        assert result.actions_failed == 2

    def test_task_result_with_error(self):
        """Test TaskResult with error."""
        result = TaskResult(
            task_id="TEST-004",
            status=TaskStatus.FAILED,
            error="Something went wrong",
        )
        assert result.status == TaskStatus.FAILED
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """Test TaskResult serialization."""
        result = TaskResult(
            task_id="TEST-005",
            status=TaskStatus.COMPLETED,
            summary="Task completed successfully",
            actions_executed=5,
            actions_succeeded=5,
            patterns_learned=3,
            trust_delta=0.1,
        )
        data = result.to_dict()

        assert data["task_id"] == "TEST-005"
        assert data["status"] == "completed"
        assert data["summary"] == "Task completed successfully"
        assert data["actions_executed"] == 5
        assert data["actions_succeeded"] == 5
        assert data["patterns_learned"] == 3
        assert data["trust_delta"] == 0.1
        assert "started_at" in data
        assert data["completed_at"] is None  # Not completed yet

    def test_to_dict_with_timestamps(self):
        """Test TaskResult serialization with timestamps."""
        now = datetime.utcnow()
        result = TaskResult(
            task_id="TEST-006",
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now + timedelta(seconds=10),
            duration_seconds=10.0,
        )
        data = result.to_dict()

        assert data["started_at"] == now.isoformat()
        assert data["completed_at"] == (now + timedelta(seconds=10)).isoformat()
        assert data["duration_seconds"] == 10.0


# =============================================================================
# GraceAgent Initialization Tests
# =============================================================================

class TestGraceAgentInit:
    """Test GraceAgent initialization."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def test_default_init(self, mock_feedback, mock_bridge):
        """Test default agent initialization."""
        mock_bridge.return_value = Mock()
        mock_feedback.return_value = Mock()

        agent = GraceAgent()

        assert agent.config is not None
        assert isinstance(agent.config, AgentConfig)
        assert agent.retriever is None
        assert agent.llm is None
        assert agent.genesis is None
        assert agent.current_task is None
        assert agent.action_history == []
        assert agent.context == {}

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def test_custom_config_init(self, mock_feedback, mock_bridge):
        """Test agent with custom config."""
        mock_bridge.return_value = Mock()
        mock_feedback.return_value = Mock()

        config = AgentConfig(max_iterations=10, use_rag=False)
        agent = GraceAgent(config=config)

        assert agent.config.max_iterations == 10
        assert agent.config.use_rag is False

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def test_init_with_components(self, mock_feedback, mock_bridge):
        """Test agent with external components."""
        mock_bridge.return_value = Mock()
        mock_feedback.return_value = Mock()

        mock_retriever = Mock()
        mock_llm = Mock()
        mock_genesis = Mock()

        agent = GraceAgent(
            retriever=mock_retriever,
            llm_client=mock_llm,
            genesis_tracker=mock_genesis,
        )

        assert agent.retriever == mock_retriever
        assert agent.llm == mock_llm
        assert agent.genesis == mock_genesis


# =============================================================================
# Task Classification Tests
# =============================================================================

class TestTaskClassification:
    """Test task type classification."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()

    def test_classify_bug_fix_tasks(self):
        """Test classification of bug fix tasks."""
        bug_tasks = [
            "Fix the bug in authentication",
            "There's an error in the login page",
            "The upload feature is broken",
            "Fix this issue with the API",
        ]
        for task in bug_tasks:
            assert self.agent._classify_task(task) == "bug_fix"

    def test_classify_feature_tasks(self):
        """Test classification of feature tasks."""
        feature_tasks = [
            "Add a new dashboard component",
            "Create a user profile page",
            "Implement the search functionality",
            "Build a new notification system",
        ]
        for task in feature_tasks:
            assert self.agent._classify_task(task) == "feature"

    def test_classify_refactor_tasks(self):
        """Test classification of refactor tasks."""
        refactor_tasks = [
            "Refactor the database module",
            "Clean up the utility functions",
            "Improve the code structure",
            "Optimize the query performance",
        ]
        for task in refactor_tasks:
            assert self.agent._classify_task(task) == "refactor"

    def test_classify_testing_tasks(self):
        """Test classification of testing tasks."""
        # Note: Some tasks might match other keywords first
        # Testing classification specifically for 'test' keyword
        assert self.agent._classify_task("Run all tests") == "testing"
        assert self.agent._classify_task("Testing the module") == "testing"

    def test_classify_documentation_tasks(self):
        """Test classification of documentation tasks."""
        # Note: Tasks with 'Add' match feature first
        assert self.agent._classify_task("Document the API") == "documentation"
        assert self.agent._classify_task("Update readme file") == "documentation"

    def test_classify_review_tasks(self):
        """Test classification of review tasks."""
        review_tasks = [
            "Review the PR changes",
            "Check the code quality",
            "Analyze the performance metrics",
        ]
        for task in review_tasks:
            assert self.agent._classify_task(task) == "review"

    def test_classify_general_tasks(self):
        """Test classification of general tasks."""
        general_tasks = [
            "Update the configuration",
            "Deploy to staging",
            "Run the migration",
        ]
        for task in general_tasks:
            assert self.agent._classify_task(task) == "general"


# =============================================================================
# Entity Extraction Tests
# =============================================================================

class TestEntityExtraction:
    """Test entity extraction from task descriptions."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()

    def test_extract_file_paths(self):
        """Test extraction of file paths."""
        task = "Fix the bug in auth.py and utils/helpers.py"
        entities = self.agent._extract_entities(task)

        file_entities = [e for e in entities if e["type"] == "file"]
        file_values = [e["value"] for e in file_entities]

        assert "auth.py" in file_values
        assert "utils/helpers.py" in file_values

    def test_extract_function_names(self):
        """Test extraction of function names."""
        task = "The calculate_total() function has a bug"
        entities = self.agent._extract_entities(task)

        func_entities = [e for e in entities if e["type"] == "function"]
        func_values = [e["value"] for e in func_entities]

        assert "calculate_total" in func_values

    def test_extract_class_names(self):
        """Test extraction of class names."""
        task = "Refactor the UserService and AuthManager classes"
        entities = self.agent._extract_entities(task)

        class_entities = [e for e in entities if e["type"] == "class"]
        class_values = [e["value"] for e in class_entities]

        assert "UserService" in class_values
        assert "AuthManager" in class_values

    def test_extract_mixed_entities(self):
        """Test extraction of mixed entity types."""
        task = "Fix the process_data() method in DataProcessor class in processor.py"
        entities = self.agent._extract_entities(task)

        assert any(e["type"] == "file" and "processor.py" in e["value"] for e in entities)
        assert any(e["type"] == "function" and "process_data" in e["value"] for e in entities)
        assert any(e["type"] == "class" and "DataProcessor" in e["value"] for e in entities)

    def test_extract_no_entities(self):
        """Test extraction when no entities present."""
        task = "improve the system"
        entities = self.agent._extract_entities(task)

        # May have some entities but no specific files/functions
        file_entities = [e for e in entities if e["type"] == "file"]
        assert len(file_entities) == 0

    def test_filter_keywords(self):
        """Test that Python keywords are filtered out."""
        task = "if the for loop while iterating with clause"
        entities = self.agent._extract_entities(task)

        func_entities = [e for e in entities if e["type"] == "function"]
        func_values = [e["value"] for e in func_entities]

        # These should be filtered
        assert "if" not in func_values
        assert "for" not in func_values
        assert "while" not in func_values
        assert "with" not in func_values


# =============================================================================
# Plan Creation Tests
# =============================================================================

class TestPlanCreation:
    """Test plan creation for different task types."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()

    @pytest.mark.asyncio
    async def test_bug_fix_plan(self):
        """Test plan creation for bug fix tasks."""
        understanding = {"task_type": "bug_fix"}
        plan = await self.agent._create_plan("Fix the bug", understanding)

        assert plan["task_type"] == "bug_fix"
        assert len(plan["steps"]) == 5
        assert plan["current_step"] == 0

        step_actions = [s["action"] for s in plan["steps"]]
        assert "read_relevant_files" in step_actions
        assert "understand_bug" in step_actions
        assert "write_fix" in step_actions
        assert "run_tests" in step_actions
        assert "finish" in step_actions

    @pytest.mark.asyncio
    async def test_feature_plan(self):
        """Test plan creation for feature tasks."""
        understanding = {"task_type": "feature"}
        plan = await self.agent._create_plan("Add new feature", understanding)

        assert plan["task_type"] == "feature"
        assert len(plan["steps"]) == 6

        step_actions = [s["action"] for s in plan["steps"]]
        assert "understand_requirements" in step_actions
        assert "read_existing_code" in step_actions
        assert "write_code" in step_actions
        assert "write_tests" in step_actions

    @pytest.mark.asyncio
    async def test_refactor_plan(self):
        """Test plan creation for refactor tasks."""
        understanding = {"task_type": "refactor"}
        plan = await self.agent._create_plan("Refactor code", understanding)

        assert plan["task_type"] == "refactor"
        assert len(plan["steps"]) == 5

        # Should run tests before and after refactor
        step_actions = [s["action"] for s in plan["steps"]]
        assert step_actions.count("run_tests") == 2

    @pytest.mark.asyncio
    async def test_general_plan(self):
        """Test plan creation for general tasks."""
        understanding = {"task_type": "general"}
        plan = await self.agent._create_plan("Do something", understanding)

        assert plan["task_type"] == "general"
        assert len(plan["steps"]) == 4

        step_actions = [s["action"] for s in plan["steps"]]
        assert "analyze" in step_actions
        assert "execute" in step_actions
        assert "verify" in step_actions
        assert "finish" in step_actions


# =============================================================================
# Failure Handling Tests
# =============================================================================

class TestFailureHandling:
    """Test failure handling in agent."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()
            self.agent.action_history = []

    @pytest.mark.asyncio
    async def test_handle_not_found_error(self):
        """Test handling of 'not found' errors - should continue."""
        mock_result = Mock()
        mock_result.error = "File not found: test.py"

        should_continue = await self.agent._handle_failure(mock_result, {})
        assert should_continue is True

    @pytest.mark.asyncio
    async def test_handle_permission_error(self):
        """Test handling of permission errors - should stop."""
        mock_result = Mock()
        mock_result.error = "Permission denied: /root/secret"

        should_continue = await self.agent._handle_failure(mock_result, {})
        assert should_continue is False

    @pytest.mark.asyncio
    async def test_handle_timeout_error(self):
        """Test handling of timeout errors - should continue."""
        mock_result = Mock()
        mock_result.error = "Operation timeout after 30s"

        should_continue = await self.agent._handle_failure(mock_result, {})
        assert should_continue is True

    @pytest.mark.asyncio
    async def test_handle_repeated_failures(self):
        """Test handling of repeated failures - should stop after 3."""
        # Mock ActionStatus
        with patch('agent.grace_agent.ActionStatus') as MockStatus:
            MockStatus.FAILURE = "FAILURE"

            # Simulate 3 recent failures
            for _ in range(3):
                mock_result = Mock()
                mock_result.status = "FAILURE"
                self.agent.action_history.append((Mock(), mock_result))

            mock_result = Mock()
            mock_result.error = "Generic error"

            should_continue = await self.agent._handle_failure(mock_result, {})
            assert should_continue is False


# =============================================================================
# Convenience Method Tests
# =============================================================================

class TestConvenienceMethods:
    """Test convenience methods."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()

    @pytest.mark.asyncio
    async def test_write_code_method(self):
        """Test write_code convenience method."""
        with patch.object(self.agent, 'solve_task', new_callable=AsyncMock) as mock_solve:
            mock_solve.return_value = TaskResult(
                task_id="TEST-001",
                status=TaskStatus.COMPLETED
            )

            result = await self.agent.write_code(
                file_path="new_module.py",
                specification="Create a utility function"
            )

            mock_solve.assert_called_once()
            call_args = mock_solve.call_args
            assert "new_module.py" in call_args[0][0]
            assert call_args[1]["context"]["target_file"] == "new_module.py"

    @pytest.mark.asyncio
    async def test_fix_bug_method(self):
        """Test fix_bug convenience method."""
        with patch.object(self.agent, 'solve_task', new_callable=AsyncMock) as mock_solve:
            mock_solve.return_value = TaskResult(
                task_id="TEST-002",
                status=TaskStatus.COMPLETED
            )

            result = await self.agent.fix_bug(
                description="Login not working",
                file_path="auth.py"
            )

            mock_solve.assert_called_once()
            call_args = mock_solve.call_args
            assert "Login not working" in call_args[0][0]
            assert "auth.py" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_run_tests_method(self):
        """Test run_tests convenience method."""
        with patch.object(self.agent, 'solve_task', new_callable=AsyncMock) as mock_solve:
            mock_solve.return_value = TaskResult(
                task_id="TEST-003",
                status=TaskStatus.COMPLETED
            )

            result = await self.agent.run_tests(test_path="./tests")

            mock_solve.assert_called_once()
            call_args = mock_solve.call_args
            assert "./tests" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_refactor_method(self):
        """Test refactor convenience method."""
        with patch.object(self.agent, 'solve_task', new_callable=AsyncMock) as mock_solve:
            mock_solve.return_value = TaskResult(
                task_id="TEST-004",
                status=TaskStatus.COMPLETED
            )

            result = await self.agent.refactor(
                file_path="legacy.py",
                description="Extract common patterns"
            )

            mock_solve.assert_called_once()
            call_args = mock_solve.call_args
            assert "legacy.py" in call_args[0][0]
            assert "Extract common patterns" in call_args[0][0]


# =============================================================================
# Summary Creation Tests
# =============================================================================

class TestSummaryCreation:
    """Test summary creation."""

    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    def setup_method(self, method, mock_feedback=None, mock_bridge=None):
        """Set up test agent."""
        with patch('agent.grace_agent.get_execution_bridge') as mb, \
             patch('agent.grace_agent.get_feedback_processor') as mf:
            mb.return_value = Mock()
            mf.return_value = Mock()
            self.agent = GraceAgent()

    @pytest.mark.asyncio
    async def test_summary_basic(self):
        """Test basic summary creation."""
        result = TaskResult(
            task_id="TEST-001",
            status=TaskStatus.COMPLETED,
            actions_executed=5,
            actions_succeeded=4,
            actions_failed=1,
        )

        summary = await self.agent._create_summary("Fix the bug", result)

        assert "Fix the bug" in summary
        assert "completed" in summary.lower()
        assert "5" in summary
        assert "4" in summary or "succeeded" in summary

    @pytest.mark.asyncio
    async def test_summary_with_files(self):
        """Test summary with file changes."""
        result = TaskResult(
            task_id="TEST-002",
            status=TaskStatus.COMPLETED,
            actions_executed=3,
            actions_succeeded=3,
            actions_failed=0,
            files_created=["new.py"],
            files_modified=["existing.py"],
        )

        summary = await self.agent._create_summary("Add feature", result)

        assert "new.py" in summary
        assert "existing.py" in summary

    @pytest.mark.asyncio
    async def test_summary_with_error(self):
        """Test summary with error."""
        result = TaskResult(
            task_id="TEST-003",
            status=TaskStatus.FAILED,
            actions_executed=2,
            actions_succeeded=1,
            actions_failed=1,
            error="Compilation failed",
        )

        summary = await self.agent._create_summary("Build project", result)

        assert "Compilation failed" in summary


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentIntegration:
    """Integration tests for GraceAgent."""

    @pytest.mark.asyncio
    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    async def test_solve_task_complete_flow(self, mock_feedback, mock_bridge):
        """Test complete solve_task flow."""
        # Setup mocks
        mock_execution = Mock()
        mock_bridge.return_value = mock_execution
        mock_feedback.return_value = Mock()

        # Mock action result
        with patch('agent.grace_agent.ActionStatus') as MockStatus, \
             patch('agent.grace_agent.GraceAction') as MockAction, \
             patch('agent.grace_agent.create_action') as mock_create:

            MockStatus.FAILURE = "FAILURE"
            MockAction.FINISH = "FINISH"

            # Create agent
            agent = GraceAgent(config=AgentConfig(max_iterations=3))

            # Mock _understand_task
            agent._understand_task = AsyncMock(return_value={
                "task": "test task",
                "task_type": "general",
                "summary": "Test task summary",
                "entities": [],
                "context": [],
            })

            # Mock _decide_next_action to return FINISH after one iteration
            call_count = 0
            async def decide_action(plan, history):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    mock_finish = Mock()
                    mock_finish.action_type = "FINISH"
                    return mock_finish
                return None

            agent._decide_next_action = decide_action

            # Run task
            result = await agent.solve_task("Do something")

            assert result.task_id.startswith("TASK-")
            assert result.status in [TaskStatus.COMPLETED, TaskStatus.EXECUTING]

    @pytest.mark.asyncio
    @patch('agent.grace_agent.get_execution_bridge')
    @patch('agent.grace_agent.get_feedback_processor')
    async def test_solve_task_with_error(self, mock_feedback, mock_bridge):
        """Test solve_task with error handling."""
        mock_execution = Mock()
        mock_bridge.return_value = mock_execution
        mock_feedback.return_value = Mock()

        agent = GraceAgent()

        # Mock _understand_task to raise exception
        agent._understand_task = AsyncMock(side_effect=Exception("Test error"))

        result = await agent.solve_task("Fail task")

        assert result.status == TaskStatus.FAILED
        assert "Test error" in result.error
        assert result.completed_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
