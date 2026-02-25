"""
Tests for Grace Todos API

Comprehensive tests for autonomous task management system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Import the module to test
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
            genesis_id="G-TEST-001"
        )
        assert task.title == "Test Task"
        assert task.id.startswith("GT-")
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.MEDIUM
        assert task.task_type == TaskType.AUTONOMOUS
        assert task.progress == 0

    def test_grace_task_with_all_fields(self):
        """Test creating a GraceTask with all fields"""
        task = GraceTask(
            title="Complex Task",
            description="Complex task description",
            genesis_id="G-TEST-002",
            status=TaskStatus.RUNNING,
            priority=TaskPriority.CRITICAL,
            task_type=TaskType.USER_REQUEST,
            assigned_to="user-123",
            assigned_agent="GA-001",
            parent_task_id="GT-parent",
            progress=50,
            tags=["urgent", "frontend"],
            required_capabilities=["python", "react"]
        )
        assert task.status == TaskStatus.RUNNING
        assert task.priority == TaskPriority.CRITICAL
        assert task.progress == 50
        assert "urgent" in task.tags
        assert "python" in task.required_capabilities

    def test_user_requirement_creation(self):
        """Test creating a UserRequirement"""
        req = UserRequirement(
            title="New Feature Request",
            description="Build a new dashboard",
            genesis_id="G-USER-001",
            requester_name="Aaron"
        )
        assert req.title == "New Feature Request"
        assert req.id.startswith("GR-")
        assert req.genesis_id == "G-USER-001"
        assert req.requester_name == "Aaron"
        assert req.status == "pending"

    def test_team_member_creation(self):
        """Test creating a TeamMember"""
        member = TeamMember(
            name="John Developer",
            genesis_id="G-JOHN-001",
            role="developer",
            skills=["python", "javascript", "react"]
        )
        assert member.name == "John Developer"
        assert member.id.startswith("GM-")
        assert "python" in member.skills
        assert member.current_load == 0
        assert member.max_concurrent_tasks == 5

    def test_grace_agent_creation(self):
        """Test creating a GraceAgent"""
        agent = GraceAgent(
            name="Test Agent",
            agent_type=AgentType.CODING,
            capabilities=["python", "api_design"],
            max_concurrent=10
        )
        assert agent.name == "Test Agent"
        assert agent.id.startswith("GA-")
        assert agent.agent_type == AgentType.CODING
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
            action_type="execute",
            target_id="GT-123",
            description="Executing task"
        )
        assert action.action_type == "execute"
        assert action.target_id == "GT-123"
        assert action.id.startswith("GAA-")
        assert action.status == "pending"
        assert action.initiated_by == "grace"

    def test_action_with_result(self):
        """Test action with result"""
        action = AutonomousAction(
            action_type="complete",
            target_id="GT-456",
            description="Task completed",
            status="completed",
            result={"success": True, "output": "Done"}
        )
        assert action.status == "completed"
        assert action.result["success"] is True


class TestTaskBoard:
    """Test TaskBoard model"""

    def test_task_board_creation(self):
        """Test creating a TaskBoard"""
        board = TaskBoard(
            title="Sprint Board",
            genesis_id="G-SPRINT-001"
        )
        assert board.title == "Sprint Board"
        assert board.id.startswith("GB-")
        assert "queued" in board.columns
        assert "completed" in board.columns

    def test_board_with_tasks(self):
        """Test board with tasks in columns"""
        board = TaskBoard(
            title="Test Board",
            genesis_id="G-TEST-001",
            columns={
                "queued": ["GT-001", "GT-002"],
                "running": ["GT-003"],
                "completed": []
            }
        )
        assert len(board.columns["queued"]) == 2
        assert len(board.columns["running"]) == 1


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
            genesis_id="G-TEST"
        )
        tasks[task.id] = task
        assert task.id in tasks
        assert tasks[task.id].title == "Storage Test"

    def test_add_requirement_to_storage(self):
        """Test adding a requirement to storage"""
        req = UserRequirement(
            title="Storage Requirement",
            description="Test requirement storage",
            genesis_id="G-TEST",
            requester_name="Tester"
        )
        requirements[req.id] = req
        assert req.id in requirements

    def test_add_team_member_to_storage(self):
        """Test adding a team member to storage"""
        member = TeamMember(
            name="Storage Tester",
            genesis_id="G-TESTER",
            role="tester",
            skills=["testing"]
        )
        team_members[member.id] = member
        assert member.id in team_members


class TestTaskOperations:
    """Test task operations"""

    def test_task_status_transitions(self):
        """Test valid status transitions"""
        task = GraceTask(
            title="Transition Test",
            description="Testing transitions",
            genesis_id="G-TEST"
        )
        # Initial status is queued
        assert task.status == TaskStatus.QUEUED

        # Transition to running
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # Transition to completed
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 100

    def test_task_progress_validation(self):
        """Test progress stays within bounds"""
        task = GraceTask(
            title="Progress Test",
            description="Testing progress",
            genesis_id="G-TEST",
            progress=50
        )
        assert 0 <= task.progress <= 100

    def test_sub_task_relationship(self):
        """Test parent-child task relationship"""
        parent = GraceTask(
            title="Parent Task",
            description="Parent task",
            genesis_id="G-TEST"
        )
        child = GraceTask(
            title="Child Task",
            description="Child task",
            genesis_id="G-TEST",
            parent_task_id=parent.id
        )
        parent.sub_tasks.append(child.id)

        assert child.parent_task_id == parent.id
        assert child.id in parent.sub_tasks

    def test_task_dependency_tracking(self):
        """Test task dependencies"""
        task1 = GraceTask(
            title="First Task",
            description="Must complete first",
            genesis_id="G-TEST"
        )
        task2 = GraceTask(
            title="Second Task",
            description="Depends on first",
            genesis_id="G-TEST",
            dependencies=[task1.id]
        )
        assert task1.id in task2.dependencies


class TestAgentOperations:
    """Test Grace agent operations"""

    def test_agent_task_assignment(self):
        """Test assigning task to agent"""
        agent = GraceAgent(
            name="Worker Agent",
            agent_type=AgentType.CODING,
            capabilities=["python"]
        )
        task_id = "GT-test-001"
        agent.current_tasks.append(task_id)

        assert task_id in agent.current_tasks
        assert agent.status == "idle"  # Status not auto-updated

    def test_agent_capacity_check(self):
        """Test agent capacity limits"""
        agent = GraceAgent(
            name="Capacity Agent",
            agent_type=AgentType.ANALYSIS,
            capabilities=["analysis"],
            max_concurrent=2
        )
        # Add tasks up to capacity
        agent.current_tasks.extend(["GT-001", "GT-002"])
        assert len(agent.current_tasks) == agent.max_concurrent

    def test_agent_capability_matching(self):
        """Test matching agent capabilities to task requirements"""
        agent = GraceAgent(
            name="Skilled Agent",
            agent_type=AgentType.CODING,
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
            genesis_id="G-SKILL",
            role="developer",
            skills=["python", "react", "postgresql"]
        )
        required_skills = ["python", "react"]
        match_count = len(set(member.skills) & set(required_skills))
        assert match_count == 2

    def test_member_workload_calculation(self):
        """Test calculating member workload"""
        member = TeamMember(
            name="Busy Member",
            genesis_id="G-BUSY",
            role="developer",
            skills=["python"],
            current_load=75,
            max_concurrent_tasks=5
        )
        member.assigned_tasks = ["GT-001", "GT-002", "GT-003"]
        utilization = (len(member.assigned_tasks) / member.max_concurrent_tasks) * 100
        assert utilization == 60  # 3/5 = 60%


class TestRequirementOperations:
    """Test requirement operations"""

    def test_requirement_task_generation(self):
        """Test generating tasks from requirement"""
        req = UserRequirement(
            title="Feature Request",
            description="Build new feature",
            genesis_id="G-REQ",
            requester_name="Product Manager"
        )
        # Simulate task generation
        generated_tasks = ["GT-001", "GT-002"]
        req.generated_tasks = generated_tasks

        assert len(req.generated_tasks) == 2
        assert req.status == "pending"

    def test_requirement_acceptance(self):
        """Test accepting a requirement"""
        req = UserRequirement(
            title="Accepted Request",
            description="This will be accepted",
            genesis_id="G-REQ",
            requester_name="Manager"
        )
        req.status = "accepted"
        assert req.status == "accepted"


class TestProcessingMode:
    """Test ProcessingMode enum"""

    def test_all_modes_exist(self):
        """Test all processing modes exist"""
        expected = ["sequential", "parallel", "background", "scheduled", "priority"]
        for mode in expected:
            assert hasattr(ProcessingMode, mode.upper())


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
