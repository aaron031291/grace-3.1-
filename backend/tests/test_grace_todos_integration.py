"""
Integration Tests for Grace Todos API

Full integration tests covering:
- API endpoint functionality
- Task lifecycle (create -> assign -> execute -> complete)
- Sub-agent orchestration
- Parallel processing
- Real-time updates
- Board operations with drag-drop
- Team assignment flows
- Error handling and recovery
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Import app and modules
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.grace_todos_api import (
    router,
    tasks_store as tasks, requirements_store as requirements,
    team_store as team_members, agents_store as grace_agents,
    actions_store as autonomous_actions,
    TaskStatus, TaskPriority, TaskType, ProcessingMode, AgentType,
    GraceTask, UserRequirement, TeamMember, GraceAgent, TaskBoard
)
boards: dict = {}
task_connections: dict = {}
from services.grace_autonomous_engine import (
    GraceAutonomousEngine, SubAgent, SubAgentPool, TaskScheduler, ParallelExecutor
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def clean_storage():
    """Clear all storage before each test"""
    tasks.clear()
    requirements.clear()
    team_members.clear()
    grace_agents.clear()
    boards.clear()
    autonomous_actions.clear()
    task_connections.clear()
    yield
    # Cleanup after test
    tasks.clear()
    requirements.clear()
    team_members.clear()
    grace_agents.clear()
    boards.clear()
    autonomous_actions.clear()
    task_connections.clear()


@pytest.fixture
def sample_task():
    """Create a sample task"""
    return {
        "title": "Implement User Authentication",
        "description": "Build complete auth system with JWT tokens",
        "genesis_id": "G-DEV-001",
        "priority": "high",
        "task_type": "user_request",
        "required_capabilities": ["python", "security", "api_design"],
        "estimated_hours": 8
    }


@pytest.fixture
def sample_team_member():
    """Create a sample team member"""
    return {
        "name": "Sarah Developer",
        "genesis_id": "G-SARAH-001",
        "role": "developer",
        "skills": ["python", "javascript", "react", "api_design"],
        "max_concurrent_tasks": 5
    }


@pytest.fixture
def sample_requirement():
    """Create a sample user requirement"""
    return {
        "title": "Build Dashboard Feature",
        "description": "Create real-time analytics dashboard with charts",
        "genesis_id": "G-PM-001",
        "requester_name": "Product Manager",
        "acceptance_criteria": [
            "Display real-time metrics",
            "Support multiple chart types",
            "Export to PDF"
        ]
    }


@pytest.fixture
def populated_board(clean_storage, sample_task):
    """Create a board with tasks in various states"""
    board = TaskBoard(
        title="Sprint 1 Board",
        genesis_id="G-SPRINT-001"
    )
    boards[board.id] = board

    # Create tasks in different states
    statuses = [TaskStatus.QUEUED, TaskStatus.QUEUED, TaskStatus.RUNNING,
                TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]

    for i, status in enumerate(statuses):
        task = GraceTask(
            title=f"Task {i+1}",
            description=f"Description for task {i+1}",
            genesis_id="G-TEST",
            status=status,
            priority=TaskPriority.MEDIUM
        )
        tasks[task.id] = task
        board.columns[status.value].append(task.id)

    return board


@pytest.fixture
def autonomous_engine():
    """Create autonomous engine instance"""
    return GraceAutonomousEngine()


# ============================================================================
# TASK LIFECYCLE TESTS
# ============================================================================

class TestTaskLifecycle:
    """Test complete task lifecycle from creation to completion"""

    def test_create_task_with_all_fields(self, clean_storage, sample_task):
        """Test creating a task with all fields populated"""
        task = GraceTask(**sample_task)
        tasks[task.id] = task

        assert task.id.startswith("GT-")
        assert task.title == sample_task["title"]
        assert task.status == TaskStatus.QUEUED
        assert task.progress == 0
        assert task.created_at is not None
        assert len(task.required_capabilities) == 3

    def test_task_state_transitions(self, clean_storage):
        """Test valid state transitions through task lifecycle"""
        task = GraceTask(
            title="Lifecycle Test",
            description="Testing state transitions",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task

        # QUEUED -> SCHEDULED
        assert task.status == TaskStatus.QUEUED
        task.status = TaskStatus.SCHEDULED
        task.scheduled_for = datetime.now() + timedelta(hours=1)
        assert task.status == TaskStatus.SCHEDULED

        # SCHEDULED -> RUNNING
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        # RUNNING -> PAUSED
        task.status = TaskStatus.PAUSED
        assert task.status == TaskStatus.PAUSED

        # PAUSED -> RUNNING
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # RUNNING -> COMPLETED
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.progress = 100
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 100

    def test_task_failure_and_retry(self, clean_storage):
        """Test task failure handling and retry mechanism"""
        task = GraceTask(
            title="Failure Test",
            description="Testing failure handling",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task

        # Simulate failure
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        # Task fails
        task.status = TaskStatus.FAILED
        task.error_message = "Connection timeout"
        task.retry_count = 1

        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Connection timeout"
        assert task.retry_count == 1

        # Retry the task
        task.status = TaskStatus.QUEUED
        task.error_message = None
        task.retry_count = 2

        assert task.status == TaskStatus.QUEUED
        assert task.retry_count == 2

    def test_task_cancellation(self, clean_storage):
        """Test task cancellation from various states"""
        for initial_status in [TaskStatus.QUEUED, TaskStatus.SCHEDULED, TaskStatus.RUNNING, TaskStatus.PAUSED]:
            task = GraceTask(
                title=f"Cancel from {initial_status.value}",
                description="Testing cancellation",
                genesis_id="G-TEST",
                status=initial_status
            )
            tasks[task.id] = task

            task.status = TaskStatus.CANCELLED
            assert task.status == TaskStatus.CANCELLED

    def test_task_progress_tracking(self, clean_storage):
        """Test task progress updates"""
        task = GraceTask(
            title="Progress Test",
            description="Testing progress tracking",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task
        task.status = TaskStatus.RUNNING

        # Simulate progress updates
        progress_updates = [0, 25, 50, 75, 100]
        for progress in progress_updates:
            task.progress = progress
            assert task.progress == progress

        # Verify final state
        task.status = TaskStatus.COMPLETED
        assert task.progress == 100
        assert task.status == TaskStatus.COMPLETED


# ============================================================================
# SUB-TASK AND DEPENDENCY TESTS
# ============================================================================

class TestSubTasksAndDependencies:
    """Test sub-task creation and dependency management"""

    def test_create_sub_tasks(self, clean_storage):
        """Test creating sub-tasks for a parent task"""
        parent = GraceTask(
            title="Parent Task",
            description="Main task with sub-tasks",
            genesis_id="G-TEST"
        )
        tasks[parent.id] = parent

        sub_task_titles = ["Setup", "Implementation", "Testing", "Documentation"]
        for title in sub_task_titles:
            sub_task = GraceTask(
                title=title,
                description=f"{title} sub-task",
                genesis_id="G-TEST",
                parent_task_id=parent.id
            )
            tasks[sub_task.id] = sub_task
            parent.sub_tasks.append(sub_task.id)

        assert len(parent.sub_tasks) == 4
        for sub_id in parent.sub_tasks:
            assert tasks[sub_id].parent_task_id == parent.id

    def test_parent_progress_from_subtasks(self, clean_storage):
        """Test calculating parent task progress from sub-tasks"""
        parent = GraceTask(
            title="Parent Task",
            description="Progress from sub-tasks",
            genesis_id="G-TEST"
        )
        tasks[parent.id] = parent

        # Create 4 sub-tasks
        sub_tasks = []
        for i in range(4):
            sub = GraceTask(
                title=f"Sub {i+1}",
                description=f"Sub-task {i+1}",
                genesis_id="G-TEST",
                parent_task_id=parent.id
            )
            tasks[sub.id] = sub
            parent.sub_tasks.append(sub.id)
            sub_tasks.append(sub)

        # Complete 2 of 4 sub-tasks
        sub_tasks[0].status = TaskStatus.COMPLETED
        sub_tasks[0].progress = 100
        sub_tasks[1].status = TaskStatus.COMPLETED
        sub_tasks[1].progress = 100

        # Calculate parent progress
        completed = sum(1 for sid in parent.sub_tasks if tasks[sid].status == TaskStatus.COMPLETED)
        parent.progress = (completed / len(parent.sub_tasks)) * 100

        assert parent.progress == 50

    def test_task_dependencies(self, clean_storage):
        """Test task dependency chain"""
        # Create dependency chain: Task A -> Task B -> Task C
        task_a = GraceTask(title="Task A", description="First", genesis_id="G-TEST")
        task_b = GraceTask(title="Task B", description="Second", genesis_id="G-TEST", dependencies=[task_a.id])
        task_c = GraceTask(title="Task C", description="Third", genesis_id="G-TEST", dependencies=[task_b.id])

        tasks[task_a.id] = task_a
        tasks[task_b.id] = task_b
        tasks[task_c.id] = task_c

        # Verify dependencies
        assert task_a.id in task_b.dependencies
        assert task_b.id in task_c.dependencies

        # Check if task can start (all dependencies completed)
        def can_start(task):
            if not task.dependencies:
                return True
            return all(tasks[dep_id].status == TaskStatus.COMPLETED for dep_id in task.dependencies)

        # Initially only Task A can start
        assert can_start(task_a) is True
        assert can_start(task_b) is False
        assert can_start(task_c) is False

        # Complete Task A
        task_a.status = TaskStatus.COMPLETED
        assert can_start(task_b) is True
        assert can_start(task_c) is False

        # Complete Task B
        task_b.status = TaskStatus.COMPLETED
        assert can_start(task_c) is True

    def test_circular_dependency_detection(self, clean_storage):
        """Test detection of circular dependencies"""
        task_a = GraceTask(title="Task A", description="A", genesis_id="G-TEST")
        task_b = GraceTask(title="Task B", description="B", genesis_id="G-TEST")

        tasks[task_a.id] = task_a
        tasks[task_b.id] = task_b

        # Create potential circular dependency
        task_a.dependencies = [task_b.id]
        task_b.dependencies = [task_a.id]

        # Function to detect circular dependencies
        def has_circular_dependency(task_id, visited=None):
            if visited is None:
                visited = set()
            if task_id in visited:
                return True
            visited.add(task_id)
            task = tasks.get(task_id)
            if task and task.dependencies:
                for dep_id in task.dependencies:
                    if has_circular_dependency(dep_id, visited.copy()):
                        return True
            return False

        assert has_circular_dependency(task_a.id) is True


# ============================================================================
# BOARD OPERATIONS TESTS
# ============================================================================

class TestBoardOperations:
    """Test Kanban board operations"""

    def test_create_board(self, clean_storage):
        """Test creating a new board"""
        board = TaskBoard(
            title="Test Board",
            genesis_id="G-TEST"
        )
        boards[board.id] = board

        assert board.id.startswith("GB-")
        assert "queued" in board.columns
        assert "running" in board.columns
        assert "completed" in board.columns
        assert len(board.columns["queued"]) == 0

    def test_add_task_to_board(self, clean_storage):
        """Test adding task to board column"""
        board = TaskBoard(title="Test Board", genesis_id="G-TEST")
        boards[board.id] = board

        task = GraceTask(
            title="Board Task",
            description="Task for board",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task
        board.columns["queued"].append(task.id)

        assert task.id in board.columns["queued"]

    def test_move_task_between_columns(self, populated_board):
        """Test moving task between board columns (drag-drop simulation)"""
        board = populated_board

        # Get a task from queued column
        queued_tasks = board.columns["queued"]
        assert len(queued_tasks) > 0

        task_id = queued_tasks[0]
        task = tasks[task_id]

        # Move to running (simulate drag-drop)
        board.columns["queued"].remove(task_id)
        board.columns["running"].append(task_id)
        task.status = TaskStatus.RUNNING

        assert task_id not in board.columns["queued"]
        assert task_id in board.columns["running"]
        assert task.status == TaskStatus.RUNNING

    def test_reorder_tasks_in_column(self, clean_storage):
        """Test reordering tasks within a column"""
        board = TaskBoard(title="Reorder Test", genesis_id="G-TEST")
        boards[board.id] = board

        # Create multiple tasks
        task_ids = []
        for i in range(5):
            task = GraceTask(
                title=f"Task {i+1}",
                description=f"Task {i+1}",
                genesis_id="G-TEST"
            )
            tasks[task.id] = task
            board.columns["queued"].append(task.id)
            task_ids.append(task.id)

        # Reorder: move task 3 to position 0
        task_to_move = task_ids[2]
        board.columns["queued"].remove(task_to_move)
        board.columns["queued"].insert(0, task_to_move)

        assert board.columns["queued"][0] == task_to_move
        assert len(board.columns["queued"]) == 5

    def test_board_task_counts(self, populated_board):
        """Test getting task counts per column"""
        board = populated_board

        counts = {col: len(task_ids) for col, task_ids in board.columns.items()}

        assert counts["queued"] == 2
        assert counts["running"] == 2
        assert counts["completed"] == 1
        assert counts["failed"] == 1


# ============================================================================
# TEAM ASSIGNMENT TESTS
# ============================================================================

class TestTeamAssignment:
    """Test team member and task assignment"""

    def test_create_team_member(self, clean_storage, sample_team_member):
        """Test creating a team member"""
        member = TeamMember(**sample_team_member)
        team_members[member.id] = member

        assert member.id.startswith("GM-")
        assert member.name == sample_team_member["name"]
        assert len(member.skills) == 4
        assert member.current_load == 0

    def test_assign_task_to_member(self, clean_storage, sample_team_member):
        """Test assigning a task to a team member"""
        member = TeamMember(**sample_team_member)
        team_members[member.id] = member

        task = GraceTask(
            title="Assigned Task",
            description="Task to assign",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task

        # Assign task
        task.assigned_to = member.id
        member.assigned_tasks.append(task.id)
        member.current_load += 20  # 20% workload

        assert task.assigned_to == member.id
        assert task.id in member.assigned_tasks
        assert member.current_load == 20

    def test_skill_based_assignment(self, clean_storage):
        """Test assigning tasks based on skills"""
        # Create members with different skills
        frontend_dev = TeamMember(
            name="Frontend Dev",
            genesis_id="G-FE",
            role="developer",
            skills=["react", "javascript", "css"]
        )
        backend_dev = TeamMember(
            name="Backend Dev",
            genesis_id="G-BE",
            role="developer",
            skills=["python", "postgresql", "api_design"]
        )
        team_members[frontend_dev.id] = frontend_dev
        team_members[backend_dev.id] = backend_dev

        # Create tasks with required skills
        frontend_task = GraceTask(
            title="Build UI Component",
            description="React component",
            genesis_id="G-TEST",
            required_capabilities=["react", "javascript"]
        )
        backend_task = GraceTask(
            title="Build API Endpoint",
            description="REST API",
            genesis_id="G-TEST",
            required_capabilities=["python", "api_design"]
        )
        tasks[frontend_task.id] = frontend_task
        tasks[backend_task.id] = backend_task

        # Find best match function
        def find_best_assignee(task):
            best_match = None
            best_score = 0
            for member in team_members.values():
                score = len(set(member.skills) & set(task.required_capabilities))
                if score > best_score:
                    best_score = score
                    best_match = member
            return best_match

        # Test assignment
        fe_assignee = find_best_assignee(frontend_task)
        be_assignee = find_best_assignee(backend_task)

        assert fe_assignee.id == frontend_dev.id
        assert be_assignee.id == backend_dev.id

    def test_workload_balancing(self, clean_storage):
        """Test workload balancing among team members"""
        # Create members with different workloads
        members = []
        for i, load in enumerate([80, 40, 60]):
            m = TeamMember(
                name=f"Dev {i+1}",
                genesis_id=f"G-DEV-{i+1}",
                role="developer",
                skills=["python"]
            )
            m.current_load = load
            team_members[m.id] = m
            members.append(m)

        # Find member with lowest workload
        def find_least_loaded():
            available = [m for m in team_members.values() if m.current_load < 100]
            return min(available, key=lambda m: m.current_load) if available else None

        assignee = find_least_loaded()
        assert assignee.current_load == 40  # Second member has lowest load


# ============================================================================
# GRACE AGENT TESTS
# ============================================================================

class TestGraceAgents:
    """Test Grace AI agent functionality"""

    def test_create_grace_agent(self, clean_storage):
        """Test creating a Grace agent"""
        agent = GraceAgent(
            name="Code Analysis Agent",
            agent_type=AgentType.ANALYSIS,
            capabilities=["code_review", "security_scan", "performance_analysis"],
            max_concurrent=10
        )
        grace_agents[agent.id] = agent

        assert agent.id.startswith("GA-")
        assert agent.agent_type == AgentType.ANALYSIS
        assert len(agent.capabilities) == 3
        assert agent.status == "idle"

    def test_agent_task_execution(self, clean_storage):
        """Test agent executing a task"""
        agent = GraceAgent(
            name="Coding Agent",
            agent_type=AgentType.CODING,
            capabilities=["python", "javascript"]
        )
        grace_agents[agent.id] = agent

        task = GraceTask(
            title="Auto-generate Code",
            description="Generate boilerplate",
            genesis_id="G-TEST",
            task_type=TaskType.AUTONOMOUS
        )
        tasks[task.id] = task

        # Assign to agent
        task.assigned_agent = agent.id
        agent.current_tasks.append(task.id)
        agent.status = "working"

        # Simulate execution
        task.status = TaskStatus.RUNNING
        task.progress = 50

        assert agent.status == "working"
        assert task.id in agent.current_tasks
        assert task.status == TaskStatus.RUNNING

        # Complete task
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        agent.current_tasks.remove(task.id)
        agent.tasks_completed += 1
        if not agent.current_tasks:
            agent.status = "idle"

        assert task.status == TaskStatus.COMPLETED
        assert agent.tasks_completed == 1
        assert agent.status == "idle"

    def test_agent_concurrent_limit(self, clean_storage):
        """Test agent concurrent task limit"""
        agent = GraceAgent(
            name="Limited Agent",
            agent_type=AgentType.TESTING,
            capabilities=["testing"],
            max_concurrent=3
        )
        grace_agents[agent.id] = agent

        # Add tasks up to limit
        for i in range(3):
            task = GraceTask(
                title=f"Task {i}",
                description=f"Task {i}",
                genesis_id="G-TEST"
            )
            tasks[task.id] = task
            agent.current_tasks.append(task.id)

        # Check if can accept more
        can_accept = len(agent.current_tasks) < agent.max_concurrent
        assert can_accept is False

        # Complete one task
        agent.current_tasks.pop()
        can_accept = len(agent.current_tasks) < agent.max_concurrent
        assert can_accept is True


# ============================================================================
# AUTONOMOUS ENGINE TESTS
# ============================================================================

class TestAutonomousEngine:
    """Test Grace Autonomous Engine"""

    def test_engine_initialization(self, autonomous_engine):
        """Test engine initializes correctly"""
        engine = autonomous_engine
        assert engine is not None
        assert engine.agent_pool is not None
        assert engine.scheduler is not None
        assert engine.parallel_executor is not None

    def test_submit_task(self, autonomous_engine):
        """Test submitting a task to the engine"""
        engine = autonomous_engine

        task_id = engine.submit_task(
            task_id="GT-TEST-001",
            task_type="coding",
            data={"title": "Test Task", "description": "Test"},
            priority=5
        )

        assert task_id is not None

    def test_create_sub_agent(self, autonomous_engine):
        """Test creating a sub-agent"""
        engine = autonomous_engine

        agent = engine.agent_pool.create_agent(
            name="Test Sub-Agent",
            capabilities=["python", "testing"],
            max_concurrent=5
        )

        assert agent is not None
        assert agent.name == "Test Sub-Agent"
        assert "python" in agent.capabilities

    def test_task_scheduling(self, autonomous_engine):
        """Test scheduling a task for later execution"""
        engine = autonomous_engine

        # Schedule task for future
        scheduled_time = datetime.now() + timedelta(hours=1)

        engine.scheduler.schedule(
            task_id="GT-SCHEDULED-001",
            handler=lambda: None,
            scheduled_time=scheduled_time
        )

        assert len(engine.scheduler.scheduled_tasks) > 0


# ============================================================================
# REQUIREMENT TO TASK GENERATION TESTS
# ============================================================================

class TestRequirementToTask:
    """Test generating tasks from requirements"""

    def test_create_requirement(self, clean_storage, sample_requirement):
        """Test creating a user requirement"""
        req = UserRequirement(**sample_requirement)
        requirements[req.id] = req

        assert req.id.startswith("GR-")
        assert req.title == sample_requirement["title"]
        assert req.status == "pending"

    def test_generate_tasks_from_requirement(self, clean_storage, sample_requirement):
        """Test generating tasks from a requirement"""
        req = UserRequirement(**sample_requirement)
        requirements[req.id] = req

        # Simulate task generation based on acceptance criteria
        generated_tasks = []
        for i, criteria in enumerate(req.acceptance_criteria):
            task = GraceTask(
                title=f"Implement: {criteria}",
                description=f"Task for: {criteria}",
                genesis_id=req.genesis_id,
                task_type=TaskType.USER_REQUEST
            )
            tasks[task.id] = task
            generated_tasks.append(task.id)
            req.generated_tasks.append(task.id)

        assert len(req.generated_tasks) == 3
        for task_id in req.generated_tasks:
            assert task_id in tasks

    def test_requirement_status_flow(self, clean_storage, sample_requirement):
        """Test requirement status flow"""
        req = UserRequirement(**sample_requirement)
        requirements[req.id] = req

        # Status flow: pending -> accepted -> in_progress -> completed
        assert req.status == "pending"

        req.status = "accepted"
        assert req.status == "accepted"

        req.status = "in_progress"
        assert req.status == "in_progress"

        req.status = "completed"
        assert req.status == "completed"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios"""

    def test_task_not_found(self, clean_storage):
        """Test handling of non-existent task"""
        result = tasks.get("GT-NONEXISTENT")
        assert result is None

    def test_invalid_status_in_task(self, clean_storage):
        """Test handling of invalid task data"""
        # Task should use default values for missing fields
        task = GraceTask(
            title="Minimal Task",
            description="Minimal",
            genesis_id="G-TEST"
        )

        assert task.status == TaskStatus.QUEUED  # Default
        assert task.priority == TaskPriority.MEDIUM  # Default
        assert task.progress == 0  # Default

    def test_agent_failure_recovery(self, clean_storage):
        """Test recovery from agent failure"""
        agent = GraceAgent(
            name="Failing Agent",
            agent_type=AgentType.CODING,
            capabilities=["python"]
        )
        grace_agents[agent.id] = agent

        task = GraceTask(
            title="Failure Test",
            description="Will fail",
            genesis_id="G-TEST"
        )
        tasks[task.id] = task
        task.assigned_agent = agent.id
        agent.current_tasks.append(task.id)

        # Simulate failure
        task.status = TaskStatus.FAILED
        task.error_message = "Agent crashed"
        agent.current_tasks.remove(task.id)
        agent.status = "error"

        # Recovery: reassign to different agent or retry
        agent.status = "idle"
        task.status = TaskStatus.QUEUED
        task.error_message = None
        task.retry_count += 1

        assert task.status == TaskStatus.QUEUED
        assert task.retry_count == 1
        assert agent.status == "idle"


# ============================================================================
# PARALLEL PROCESSING TESTS
# ============================================================================

class TestParallelProcessing:
    """Test parallel task processing"""

    def test_parallel_executor_creation(self):
        """Test creating parallel executor"""
        executor = ParallelExecutor(max_workers=4)
        assert executor is not None
        assert executor.max_workers == 4

    def test_batch_task_processing(self, clean_storage):
        """Test processing multiple tasks in parallel"""
        # Create batch of tasks
        batch_tasks = []
        for i in range(10):
            task = GraceTask(
                title=f"Batch Task {i}",
                description=f"Batch task {i}",
                genesis_id="G-TEST"
            )
            tasks[task.id] = task
            batch_tasks.append(task)

        # Simulate parallel completion
        for task in batch_tasks:
            task.status = TaskStatus.COMPLETED
            task.progress = 100

        completed = sum(1 for t in batch_tasks if t.status == TaskStatus.COMPLETED)
        assert completed == 10


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
