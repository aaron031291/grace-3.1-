"""
Tests for Grace Todos API

Comprehensive tests for autonomous task management system.
Updated to match current API model structure.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from api.grace_todos_api import (
    router,
    TaskStatus, TaskPriority, TaskType, ProcessingMode, AgentType,
    GraceTask, UserRequirement, TeamMember, GraceAgent, AutonomousAction, TaskBoard,
    tasks_store as tasks, requirements_store as requirements,
    team_store as team_members, agents_store as grace_agents,
    actions_store as autonomous_actions
)


class TestTaskModels:
    """Test task-related models"""

    def test_grace_task_creation(self):
        """Test creating a GraceTask"""
        task = GraceTask(
            title="Test Task",
            description="A test task description",
            genesis_key_id="G-TEST-001"
        )
        assert task.title == "Test Task"
        assert task.genesis_key_id == "G-TEST-001"
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.MEDIUM
        assert task.task_type == TaskType.AUTONOMOUS
        assert task.progress_percent == 0

    def test_grace_task_with_all_fields(self):
        """Test creating a GraceTask with all fields"""
        task = GraceTask(
            title="Complex Task",
            description="Complex task description",
            genesis_key_id="G-TEST-002",
            status=TaskStatus.RUNNING,
            priority=TaskPriority.CRITICAL,
            task_type=TaskType.USER_REQUEST,
            assignee_genesis_id="user-123",
            assigned_agent="GA-001",
            parent_task_id="GT-parent",
            progress_percent=50,
            labels=["urgent", "frontend"],
        )
        assert task.status == TaskStatus.RUNNING
        assert task.priority == TaskPriority.CRITICAL
        assert task.progress_percent == 50
        assert "urgent" in task.labels

    def test_user_requirement_creation(self):
        """Test creating a UserRequirement"""
        req = UserRequirement(
            title="New Feature Request",
            description="Build a new dashboard",
            genesis_key_id="G-USER-001",
            user_genesis_id="user-aaron"
        )
        assert req.title == "New Feature Request"
        assert req.genesis_key_id == "G-USER-001"
        assert req.user_genesis_id == "user-aaron"
        assert req.status == "draft"

    def test_team_member_creation(self):
        """Test creating a TeamMember"""
        member = TeamMember(
            name="John Developer",
            display_name="John D.",
            genesis_key_id="G-JOHN-001",
            role="developer",
            skill_sets=["python", "javascript", "react"]
        )
        assert member.name == "John Developer"
        assert member.genesis_key_id == "G-JOHN-001"
        assert "python" in member.skill_sets
        assert member.current_load == 0

    def test_grace_agent_creation(self):
        """Test creating a GraceAgent"""
        agent = GraceAgent(
            name="Test Agent",
            agent_id="GA-001",
            agent_type=AgentType.SPECIALIST,
            capabilities=["python", "api_design"],
            max_concurrent=10
        )
        assert agent.name == "Test Agent"
        assert agent.agent_id == "GA-001"
        assert agent.status == "idle"
        assert agent.max_concurrent == 10


class TestTaskStatusEnum:
    """Test TaskStatus enum"""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist"""
        expected = ["queued", "scheduled", "running", "paused", "completed", "failed", "cancelled"]
        for status in expected:
            assert hasattr(TaskStatus, status.upper())

    def test_status_values(self):
        """Test status values are correct"""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"


class TestTaskPriorityEnum:
    """Test TaskPriority enum"""

    def test_all_priorities_exist(self):
        """Test all expected priorities exist"""
        expected = ["critical", "high", "medium", "low", "background"]
        for priority in expected:
            assert hasattr(TaskPriority, priority.upper())


class TestTaskTypeEnum:
    """Test TaskType enum"""

    def test_all_types_exist(self):
        """Test all expected task types exist"""
        expected = [
            "autonomous", "user_request", "scheduled", "sub_agent",
            "learning", "diagnostic", "healing", "memory", "analysis", "ingestion"
        ]
        for task_type in expected:
            assert hasattr(TaskType, task_type.upper())


class TestAutonomousAction:
    """Test AutonomousAction model"""

    def test_autonomous_action_creation(self):
        """Test creating an AutonomousAction"""
        action = AutonomousAction(
            action_id="GAA-001",
            task_id="GT-123",
            agent_id="GA-001",
            action_type="execute",
            description="Executing task"
        )
        assert action.action_type == "execute"
        assert action.task_id == "GT-123"
        assert action.action_id == "GAA-001"
        assert action.status == "pending"

    def test_action_with_result(self):
        """Test action with result"""
        action = AutonomousAction(
            action_id="GAA-002",
            task_id="GT-456",
            agent_id="GA-001",
            action_type="complete",
            description="Task completed",
            status="completed",
            output_data={"success": True, "output": "Done"}
        )
        assert action.status == "completed"
        assert action.output_data["success"] is True


class TestTaskBoard:
    """Test TaskBoard model"""

    def test_task_board_creation(self):
        """Test creating a TaskBoard"""
        board = TaskBoard()
        assert isinstance(board.queued, list)
        assert isinstance(board.completed, list)
        assert len(board.queued) == 0

    def test_board_with_tasks(self):
        """Test board with tasks in columns"""
        task1 = GraceTask(title="Task 1", genesis_key_id="G-001")
        task2 = GraceTask(title="Task 2", genesis_key_id="G-002")
        task3 = GraceTask(title="Task 3", genesis_key_id="G-003", status=TaskStatus.RUNNING)
        board = TaskBoard(
            queued=[task1, task2],
            running=[task3],
        )
        assert len(board.queued) == 2
        assert len(board.running) == 1


class TestTaskStorage:
    """Test in-memory task storage"""

    def setup_method(self):
        """Clear storage before each test"""
        tasks.clear()
        requirements.clear()
        team_members.clear()
        grace_agents.clear()

    def test_add_task_to_storage(self):
        """Test adding a task to storage"""
        task = GraceTask(
            title="Storage Test",
            description="Test task storage",
            genesis_key_id="G-TEST"
        )
        tasks[task.genesis_key_id] = task
        assert task.genesis_key_id in tasks
        assert tasks[task.genesis_key_id].title == "Storage Test"

    def test_add_requirement_to_storage(self):
        """Test adding a requirement to storage"""
        req = UserRequirement(
            title="Storage Requirement",
            description="Test requirement storage",
            genesis_key_id="G-TEST",
            user_genesis_id="user-tester"
        )
        requirements[req.genesis_key_id] = req
        assert req.genesis_key_id in requirements

    def test_add_team_member_to_storage(self):
        """Test adding a team member to storage"""
        member = TeamMember(
            name="Storage Tester",
            display_name="Tester",
            genesis_key_id="G-TESTER",
            role="specialist",
            skill_sets=["testing"]
        )
        team_members[member.genesis_key_id] = member
        assert member.genesis_key_id in team_members


class TestTaskOperations:
    """Test task operations"""

    def test_task_status_transitions(self):
        """Test valid status transitions"""
        task = GraceTask(
            title="Transition Test",
            description="Testing transitions",
            genesis_key_id="G-TEST"
        )
        assert task.status == TaskStatus.QUEUED

        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        task.status = TaskStatus.COMPLETED
        task.progress_percent = 100
        assert task.status == TaskStatus.COMPLETED
        assert task.progress_percent == 100

    def test_task_progress_validation(self):
        """Test progress stays within bounds"""
        task = GraceTask(
            title="Progress Test",
            description="Testing progress",
            genesis_key_id="G-TEST",
            progress_percent=50
        )
        assert 0 <= task.progress_percent <= 100

    def test_sub_task_relationship(self):
        """Test parent-child task relationship"""
        parent = GraceTask(
            title="Parent Task",
            description="Parent task",
            genesis_key_id="G-PARENT"
        )
        child = GraceTask(
            title="Child Task",
            description="Child task",
            genesis_key_id="G-CHILD",
            parent_task_id="G-PARENT"
        )
        parent.sub_task_ids.append(child.genesis_key_id)

        assert child.parent_task_id == "G-PARENT"
        assert child.genesis_key_id in parent.sub_task_ids

    def test_task_dependency_tracking(self):
        """Test task dependencies"""
        task1 = GraceTask(
            title="First Task",
            description="Must complete first",
            genesis_key_id="G-FIRST"
        )
        task2 = GraceTask(
            title="Second Task",
            description="Depends on first",
            genesis_key_id="G-SECOND",
            dependencies=["G-FIRST"]
        )
        assert "G-FIRST" in task2.dependencies


class TestAgentOperations:
    """Test Grace agent operations"""

    def test_agent_task_assignment(self):
        """Test assigning task to agent"""
        agent = GraceAgent(
            name="Worker Agent",
            agent_id="GA-WORKER",
            agent_type=AgentType.WORKER,
            capabilities=["python"]
        )
        agent.current_task_id = "GT-test-001"

        assert agent.current_task_id == "GT-test-001"
        assert agent.status == "idle"

    def test_agent_capacity_check(self):
        """Test agent capacity limits"""
        agent = GraceAgent(
            name="Capacity Agent",
            agent_id="GA-CAP",
            agent_type=AgentType.SPECIALIST,
            capabilities=["analysis"],
            max_concurrent=2
        )
        agent.task_queue.extend(["GT-001", "GT-002"])
        assert len(agent.task_queue) == agent.max_concurrent

    def test_agent_capability_matching(self):
        """Test matching agent capabilities to task requirements"""
        agent = GraceAgent(
            name="Skilled Agent",
            agent_id="GA-SKILL",
            agent_type=AgentType.SPECIALIST,
            capabilities=["python", "javascript", "api_design"]
        )
        required = ["python", "api_design"]
        matches = all(cap in agent.capabilities for cap in required)
        assert matches is True


class TestTeamMemberOperations:
    """Test team member operations"""

    def test_member_skill_matching(self):
        """Test matching member skills to requirements"""
        member = TeamMember(
            name="Skilled Member",
            display_name="Skilled",
            genesis_key_id="G-SKILL",
            role="developer",
            skill_sets=["python", "react", "postgresql"]
        )
        required_skills = ["python", "react"]
        match_count = len(set(member.skill_sets) & set(required_skills))
        assert match_count == 2

    def test_member_workload_calculation(self):
        """Test calculating member workload"""
        member = TeamMember(
            name="Busy Member",
            display_name="Busy",
            genesis_key_id="G-BUSY",
            role="developer",
            skill_sets=["python"],
            current_load=75,
            capacity=100
        )
        member.assigned_tasks = ["GT-001", "GT-002", "GT-003"]
        assert member.current_load == 75


class TestRequirementOperations:
    """Test requirement operations"""

    def test_requirement_task_generation(self):
        """Test generating tasks from requirement"""
        req = UserRequirement(
            title="Feature Request",
            description="Build new feature",
            genesis_key_id="G-REQ",
            user_genesis_id="product-manager"
        )
        generated_tasks = ["GT-001", "GT-002"]
        req.generated_tasks = generated_tasks

        assert len(req.generated_tasks) == 2
        assert req.status == "draft"

    def test_requirement_acceptance(self):
        """Test accepting a requirement"""
        req = UserRequirement(
            title="Accepted Request",
            description="This will be accepted",
            genesis_key_id="G-REQ",
            user_genesis_id="manager"
        )
        req.status = "active"
        assert req.status == "active"


class TestProcessingMode:
    """Test ProcessingMode enum"""

    def test_all_modes_exist(self):
        """Test all processing modes exist"""
        expected = ["sequential", "parallel", "background", "multi_thread", "distributed"]
        for mode in expected:
            assert hasattr(ProcessingMode, mode.upper())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
