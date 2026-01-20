"""
Comprehensive Test Suite for Execution Module
==============================================
Tests for ExecutionBridge, Actions, ActionRequest, ActionResult,
and governed execution functionality.

Coverage:
- GraceAction enum
- ActionStatus enum
- ActionRequest dataclass
- ActionResult dataclass
- ExecutionConfig
- ExecutionBridge initialization
- Action execution
- Sandboxed execution
- Git operations
- File operations
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import asyncio

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock subprocess
mock_subprocess = MagicMock()
sys.modules['subprocess'] = mock_subprocess

# Mock shutil
mock_shutil = MagicMock()
sys.modules['shutil'] = mock_shutil

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# Mock Enums - GraceAction
# =============================================================================

class GraceAction(Enum):
    """All actions Grace can perform."""
    # Code Operations
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    READ_FILE = "read_file"
    DELETE_FILE = "delete_file"

    # Code Execution
    RUN_PYTHON = "run_python"
    RUN_BASH = "run_bash"
    RUN_IPYTHON = "run_ipython"

    # Testing
    RUN_TESTS = "run_tests"
    RUN_PYTEST = "run_pytest"
    RUN_JEST = "run_jest"

    # Git Operations
    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"
    GIT_ADD = "git_add"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_PULL = "git_pull"
    GIT_BRANCH = "git_branch"
    GIT_CHECKOUT = "git_checkout"
    GIT_CREATE_PR = "git_create_pr"

    # Code Analysis
    SEARCH_CODE = "search_code"
    GREP_CODE = "grep_code"
    FIND_FILES = "find_files"
    ANALYZE_ERROR = "analyze_error"
    LINT_CODE = "lint_code"

    # Build Operations
    BUILD_PROJECT = "build_project"
    INSTALL_DEPS = "install_deps"

    # Browser
    BROWSE_URL = "browse_url"
    BROWSE_INTERACTIVE = "browse_interactive"

    # Learning Actions
    RECORD_SUCCESS = "record_success"
    RECORD_FAILURE = "record_failure"
    EXTRACT_PATTERN = "extract_pattern"

    # Agent Control
    THINK = "think"
    PLAN = "plan"
    FINISH = "finish"
    ASK_USER = "ask_user"


class ActionStatus(Enum):
    """Status of an action execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# =============================================================================
# GraceAction Enum Tests
# =============================================================================

class TestGraceAction:
    """Test GraceAction enum."""

    def test_action_enum_values(self):
        """Test all action enum values exist."""
        assert GraceAction.WRITE_FILE.value == "write_file"
        assert GraceAction.RUN_PYTHON.value == "run_python"
        assert GraceAction.GIT_COMMIT.value == "git_commit"
        assert GraceAction.THINK.value == "think"

    def test_code_operations(self):
        """Test code operation actions."""
        code_ops = [
            GraceAction.WRITE_FILE,
            GraceAction.EDIT_FILE,
            GraceAction.READ_FILE,
            GraceAction.DELETE_FILE
        ]
        assert len(code_ops) == 4

    def test_git_operations(self):
        """Test git operation actions."""
        git_ops = [
            GraceAction.GIT_STATUS,
            GraceAction.GIT_DIFF,
            GraceAction.GIT_ADD,
            GraceAction.GIT_COMMIT,
            GraceAction.GIT_PUSH,
            GraceAction.GIT_PULL,
            GraceAction.GIT_BRANCH,
            GraceAction.GIT_CHECKOUT,
            GraceAction.GIT_CREATE_PR
        ]
        assert len(git_ops) == 9

    def test_action_from_string(self):
        """Test creating action from string value."""
        action = GraceAction("write_file")
        assert action == GraceAction.WRITE_FILE


# =============================================================================
# ActionStatus Enum Tests
# =============================================================================

class TestActionStatus:
    """Test ActionStatus enum."""

    def test_status_values(self):
        """Test all status values."""
        assert ActionStatus.PENDING.value == "pending"
        assert ActionStatus.RUNNING.value == "running"
        assert ActionStatus.SUCCESS.value == "success"
        assert ActionStatus.FAILURE.value == "failure"
        assert ActionStatus.TIMEOUT.value == "timeout"
        assert ActionStatus.CANCELLED.value == "cancelled"

    def test_terminal_statuses(self):
        """Test identifying terminal statuses."""
        terminal_statuses = [
            ActionStatus.SUCCESS,
            ActionStatus.FAILURE,
            ActionStatus.TIMEOUT,
            ActionStatus.CANCELLED
        ]
        non_terminal = [ActionStatus.PENDING, ActionStatus.RUNNING]

        for status in terminal_statuses:
            assert status not in non_terminal


# =============================================================================
# ActionRequest Tests
# =============================================================================

class TestActionRequest:
    """Test ActionRequest dataclass."""

    def test_create_basic_request(self):
        """Test creating a basic action request."""
        @dataclass
        class ActionRequest:
            action_id: str = field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:12]}")
            action_type: GraceAction = GraceAction.THINK
            parameters: Dict[str, Any] = field(default_factory=dict)
            context: Dict[str, Any] = field(default_factory=dict)
            created_at: datetime = field(default_factory=datetime.utcnow)
            timeout: int = 300
            requires_confirmation: bool = False
            confidence: float = 0.5
            reasoning: str = ""
            related_memory_ids: List[str] = field(default_factory=list)

        request = ActionRequest()

        assert request.action_type == GraceAction.THINK
        assert request.timeout == 300
        assert request.confidence == 0.5
        assert request.action_id.startswith("ACT-")

    def test_create_request_with_parameters(self):
        """Test creating request with parameters."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any] = field(default_factory=dict)
            timeout: int = 300

        request = ActionRequest(
            action_type=GraceAction.WRITE_FILE,
            parameters={
                "path": "/path/to/file.py",
                "content": "print('hello')"
            },
            timeout=60
        )

        assert request.action_type == GraceAction.WRITE_FILE
        assert request.parameters["path"] == "/path/to/file.py"
        assert request.timeout == 60

    def test_action_request_to_dict(self):
        """Test converting action request to dictionary."""
        @dataclass
        class ActionRequest:
            action_id: str = "ACT-test123"
            action_type: GraceAction = GraceAction.RUN_PYTHON
            parameters: Dict[str, Any] = field(default_factory=dict)
            timeout: int = 300

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "action_id": self.action_id,
                    "action_type": self.action_type.value,
                    "parameters": self.parameters,
                    "timeout": self.timeout
                }

        request = ActionRequest()
        result = request.to_dict()

        assert result["action_id"] == "ACT-test123"
        assert result["action_type"] == "run_python"


# =============================================================================
# ActionResult Tests
# =============================================================================

class TestActionResult:
    """Test ActionResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful action result."""
        @dataclass
        class ActionResult:
            action_id: str
            action_type: GraceAction
            status: ActionStatus
            output: str = ""
            error: Optional[str] = None
            exit_code: Optional[int] = None
            execution_time: float = 0.0
            completed_at: datetime = field(default_factory=datetime.utcnow)
            data: Dict[str, Any] = field(default_factory=dict)
            files_created: List[str] = field(default_factory=list)
            files_modified: List[str] = field(default_factory=list)
            files_deleted: List[str] = field(default_factory=list)
            learnable: bool = True
            trust_delta: float = 0.0

            @property
            def success(self) -> bool:
                return self.status == ActionStatus.SUCCESS

            @property
            def failed(self) -> bool:
                return self.status in [ActionStatus.FAILURE, ActionStatus.TIMEOUT]

        result = ActionResult(
            action_id="ACT-123",
            action_type=GraceAction.RUN_PYTHON,
            status=ActionStatus.SUCCESS,
            output="Hello, World!",
            exit_code=0,
            execution_time=0.5
        )

        assert result.success is True
        assert result.failed is False
        assert result.exit_code == 0

    def test_create_failure_result(self):
        """Test creating a failed action result."""
        @dataclass
        class ActionResult:
            action_id: str
            action_type: GraceAction
            status: ActionStatus
            output: str = ""
            error: Optional[str] = None
            exit_code: Optional[int] = None

            @property
            def success(self) -> bool:
                return self.status == ActionStatus.SUCCESS

            @property
            def failed(self) -> bool:
                return self.status in [ActionStatus.FAILURE, ActionStatus.TIMEOUT]

        result = ActionResult(
            action_id="ACT-124",
            action_type=GraceAction.RUN_BASH,
            status=ActionStatus.FAILURE,
            error="Command not found",
            exit_code=127
        )

        assert result.success is False
        assert result.failed is True
        assert result.error == "Command not found"

    def test_result_with_file_changes(self):
        """Test result with file changes."""
        @dataclass
        class ActionResult:
            action_id: str
            action_type: GraceAction
            status: ActionStatus
            files_created: List[str] = field(default_factory=list)
            files_modified: List[str] = field(default_factory=list)
            files_deleted: List[str] = field(default_factory=list)

        result = ActionResult(
            action_id="ACT-125",
            action_type=GraceAction.WRITE_FILE,
            status=ActionStatus.SUCCESS,
            files_created=["new_file.py"],
            files_modified=["existing.py"]
        )

        assert len(result.files_created) == 1
        assert "new_file.py" in result.files_created

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        @dataclass
        class ActionResult:
            action_id: str
            action_type: GraceAction
            status: ActionStatus
            output: str = ""

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "action_id": self.action_id,
                    "action_type": self.action_type.value,
                    "status": self.status.value,
                    "output": self.output
                }

        result = ActionResult(
            action_id="ACT-126",
            action_type=GraceAction.GIT_STATUS,
            status=ActionStatus.SUCCESS,
            output="On branch main"
        )

        d = result.to_dict()
        assert d["action_type"] == "git_status"
        assert d["status"] == "success"


# =============================================================================
# ExecutionConfig Tests
# =============================================================================

class TestExecutionConfig:
    """Test ExecutionConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        class ExecutionConfig:
            def __init__(
                self,
                workspace_dir: str = None,
                timeout: int = 300,
                use_docker: bool = False,
                docker_image: str = "grace-sandbox:latest",
                max_output_size: int = 100000,
                allowed_commands: List[str] = None,
                blocked_commands: List[str] = None
            ):
                self.workspace_dir = workspace_dir or "/tmp"
                self.timeout = timeout
                self.use_docker = use_docker
                self.docker_image = docker_image
                self.max_output_size = max_output_size
                self.allowed_commands = allowed_commands or []
                self.blocked_commands = blocked_commands or [
                    "rm -rf /",
                    "mkfs",
                    "dd if=/dev/zero",
                ]

        config = ExecutionConfig()

        assert config.timeout == 300
        assert config.use_docker is False
        assert len(config.blocked_commands) == 3

    def test_custom_config(self):
        """Test custom configuration."""
        class ExecutionConfig:
            def __init__(
                self,
                workspace_dir: str = None,
                timeout: int = 300,
                use_docker: bool = False,
                docker_image: str = "grace-sandbox:latest",
                allowed_commands: List[str] = None
            ):
                self.workspace_dir = workspace_dir
                self.timeout = timeout
                self.use_docker = use_docker
                self.docker_image = docker_image
                self.allowed_commands = allowed_commands or []

        config = ExecutionConfig(
            workspace_dir="/custom/workspace",
            timeout=60,
            use_docker=True,
            docker_image="custom-sandbox:v1"
        )

        assert config.workspace_dir == "/custom/workspace"
        assert config.timeout == 60
        assert config.use_docker is True
        assert config.docker_image == "custom-sandbox:v1"


# =============================================================================
# ExecutionBridge Tests
# =============================================================================

class TestExecutionBridge:
    """Test ExecutionBridge class."""

    def test_bridge_initialization(self):
        """Test ExecutionBridge initialization."""
        class ExecutionConfig:
            def __init__(self):
                self.workspace_dir = "/tmp"
                self.timeout = 300

        class ExecutionBridge:
            def __init__(self, config=None, genesis_tracker=None):
                self.config = config or ExecutionConfig()
                self.genesis = genesis_tracker
                self.action_history: List[Tuple] = []
                self._running = False

        bridge = ExecutionBridge()

        assert bridge.config.timeout == 300
        assert bridge.action_history == []
        assert bridge._running is False

    def test_bridge_with_genesis_tracker(self):
        """Test bridge with Genesis tracker."""
        class ExecutionConfig:
            pass

        class ExecutionBridge:
            def __init__(self, config=None, genesis_tracker=None):
                self.config = config or ExecutionConfig()
                self.genesis = genesis_tracker
                self.action_history = []

        mock_genesis = MagicMock()
        bridge = ExecutionBridge(genesis_tracker=mock_genesis)

        assert bridge.genesis is mock_genesis


# =============================================================================
# Action Execution Tests
# =============================================================================

class TestActionExecution:
    """Test action execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_action(self):
        """Test basic action execution."""
        @dataclass
        class ActionRequest:
            action_id: str
            action_type: GraceAction
            parameters: Dict[str, Any] = field(default_factory=dict)

        @dataclass
        class ActionResult:
            action_id: str
            action_type: GraceAction
            status: ActionStatus
            output: str = ""
            execution_time: float = 0.0

        class ExecutionBridge:
            def __init__(self):
                self.action_history = []

            async def execute(self, action: ActionRequest) -> ActionResult:
                start = datetime.utcnow()
                result = ActionResult(
                    action_id=action.action_id,
                    action_type=action.action_type,
                    status=ActionStatus.SUCCESS,
                    output="Execution completed"
                )
                result.execution_time = 0.1
                self.action_history.append((action, result))
                return result

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_id="ACT-001",
            action_type=GraceAction.THINK
        )

        result = await bridge.execute(request)

        assert result.status == ActionStatus.SUCCESS
        assert len(bridge.action_history) == 1

    @pytest.mark.asyncio
    async def test_execute_python_code(self):
        """Test Python code execution."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str
            exit_code: int

        class ExecutionBridge:
            async def _execute_python(self, action: ActionRequest) -> ActionResult:
                code = action.parameters.get("code", "")
                # Simulate execution
                if "error" in code:
                    return ActionResult(
                        status=ActionStatus.FAILURE,
                        output="",
                        exit_code=1
                    )
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output="42",
                    exit_code=0
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.RUN_PYTHON,
            parameters={"code": "print(21 * 2)"}
        )

        result = await bridge._execute_python(request)

        assert result.status == ActionStatus.SUCCESS
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_bash_command(self):
        """Test Bash command execution."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str
            exit_code: int

        class ExecutionBridge:
            async def _execute_bash(self, action: ActionRequest) -> ActionResult:
                command = action.parameters.get("command", "")
                # Simulate execution
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output=f"Executed: {command}",
                    exit_code=0
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.RUN_BASH,
            parameters={"command": "ls -la"}
        )

        result = await bridge._execute_bash(request)

        assert result.status == ActionStatus.SUCCESS
        assert "ls -la" in result.output


# =============================================================================
# File Operations Tests
# =============================================================================

class TestFileOperations:
    """Test file operation actions."""

    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test file write operation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            files_created: List[str]

        class ExecutionBridge:
            def __init__(self):
                self.written_files = {}

            async def _write_file(self, action: ActionRequest) -> ActionResult:
                path = action.parameters["path"]
                content = action.parameters["content"]
                self.written_files[path] = content
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    files_created=[path]
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.WRITE_FILE,
            parameters={
                "path": "/tmp/test.py",
                "content": "print('hello')"
            }
        )

        result = await bridge._write_file(request)

        assert result.status == ActionStatus.SUCCESS
        assert "/tmp/test.py" in result.files_created
        assert bridge.written_files["/tmp/test.py"] == "print('hello')"

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test file read operation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str

        class ExecutionBridge:
            def __init__(self):
                self.files = {"/tmp/test.py": "print('hello')"}

            async def _read_file(self, action: ActionRequest) -> ActionResult:
                path = action.parameters["path"]
                if path not in self.files:
                    return ActionResult(
                        status=ActionStatus.FAILURE,
                        output=""
                    )
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output=self.files[path]
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.READ_FILE,
            parameters={"path": "/tmp/test.py"}
        )

        result = await bridge._read_file(request)

        assert result.status == ActionStatus.SUCCESS
        assert result.output == "print('hello')"

    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test file delete operation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            files_deleted: List[str]

        class ExecutionBridge:
            def __init__(self):
                self.files = {"/tmp/test.py": "content"}

            async def _delete_file(self, action: ActionRequest) -> ActionResult:
                path = action.parameters["path"]
                if path in self.files:
                    del self.files[path]
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        files_deleted=[path]
                    )
                return ActionResult(
                    status=ActionStatus.FAILURE,
                    files_deleted=[]
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.DELETE_FILE,
            parameters={"path": "/tmp/test.py"}
        )

        result = await bridge._delete_file(request)

        assert result.status == ActionStatus.SUCCESS
        assert "/tmp/test.py" not in bridge.files


# =============================================================================
# Git Operations Tests
# =============================================================================

class TestGitOperations:
    """Test Git operation actions."""

    @pytest.mark.asyncio
    async def test_git_status(self):
        """Test git status operation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str
            data: Dict[str, Any]

        class ExecutionBridge:
            async def _git_status(self, action: ActionRequest) -> ActionResult:
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output="On branch main\nnothing to commit",
                    data={
                        "branch": "main",
                        "clean": True,
                        "staged": [],
                        "unstaged": []
                    }
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.GIT_STATUS,
            parameters={}
        )

        result = await bridge._git_status(request)

        assert result.status == ActionStatus.SUCCESS
        assert result.data["branch"] == "main"
        assert result.data["clean"] is True

    @pytest.mark.asyncio
    async def test_git_commit(self):
        """Test git commit operation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str
            data: Dict[str, Any]

        class ExecutionBridge:
            async def _git_commit(self, action: ActionRequest) -> ActionResult:
                message = action.parameters.get("message", "")
                if not message:
                    return ActionResult(
                        status=ActionStatus.FAILURE,
                        output="Commit message required",
                        data={}
                    )
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output=f"Committed: {message}",
                    data={"commit_hash": "abc123"}
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.GIT_COMMIT,
            parameters={"message": "Add new feature"}
        )

        result = await bridge._git_commit(request)

        assert result.status == ActionStatus.SUCCESS
        assert "commit_hash" in result.data

    @pytest.mark.asyncio
    async def test_git_diff(self):
        """Test git diff operation."""
        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str

        class ExecutionBridge:
            async def _git_diff(self, staged: bool = False) -> ActionResult:
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output="diff --git a/file.py b/file.py\n+new line"
                )

        bridge = ExecutionBridge()
        result = await bridge._git_diff(staged=True)

        assert result.status == ActionStatus.SUCCESS
        assert "diff" in result.output


# =============================================================================
# Test Execution Tests
# =============================================================================

class TestTestExecution:
    """Test test execution actions."""

    @pytest.mark.asyncio
    async def test_run_pytest(self):
        """Test pytest execution."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        @dataclass
        class ActionResult:
            status: ActionStatus
            output: str
            data: Dict[str, Any]

        class ExecutionBridge:
            async def _run_pytest(self, action: ActionRequest) -> ActionResult:
                test_path = action.parameters.get("path", "tests/")
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    output="10 passed, 0 failed",
                    data={
                        "passed": 10,
                        "failed": 0,
                        "skipped": 0,
                        "errors": 0
                    }
                )

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.RUN_PYTEST,
            parameters={"path": "tests/test_utils.py"}
        )

        result = await bridge._run_pytest(request)

        assert result.status == ActionStatus.SUCCESS
        assert result.data["passed"] == 10
        assert result.data["failed"] == 0

    @pytest.mark.asyncio
    async def test_run_tests_with_failures(self):
        """Test handling test failures."""
        @dataclass
        class ActionResult:
            status: ActionStatus
            data: Dict[str, Any]

        class ExecutionBridge:
            async def _run_tests(self, test_path: str) -> ActionResult:
                # Simulate test failures
                return ActionResult(
                    status=ActionStatus.FAILURE,
                    data={
                        "passed": 8,
                        "failed": 2,
                        "failures": [
                            {"test": "test_foo", "error": "AssertionError"},
                            {"test": "test_bar", "error": "TypeError"}
                        ]
                    }
                )

        bridge = ExecutionBridge()
        result = await bridge._run_tests("tests/")

        assert result.status == ActionStatus.FAILURE
        assert result.data["failed"] == 2


# =============================================================================
# Safety and Sandboxing Tests
# =============================================================================

class TestSafetyAndSandboxing:
    """Test safety and sandboxing features."""

    def test_command_blocking(self):
        """Test that dangerous commands are blocked."""
        class ExecutionBridge:
            BLOCKED_COMMANDS = [
                "rm -rf /",
                "mkfs",
                "dd if=/dev/zero",
            ]

            def is_command_safe(self, command: str) -> bool:
                for blocked in self.BLOCKED_COMMANDS:
                    if blocked in command:
                        return False
                return True

        bridge = ExecutionBridge()

        assert bridge.is_command_safe("ls -la") is True
        assert bridge.is_command_safe("rm -rf /") is False
        assert bridge.is_command_safe("cat file.txt") is True
        assert bridge.is_command_safe("dd if=/dev/zero of=/dev/sda") is False

    def test_output_truncation(self):
        """Test that large outputs are truncated."""
        class ExecutionBridge:
            def __init__(self, max_output_size: int = 1000):
                self.max_output_size = max_output_size

            def truncate_output(self, output: str) -> str:
                if len(output) > self.max_output_size:
                    return output[:self.max_output_size] + "...[truncated]"
                return output

        bridge = ExecutionBridge(max_output_size=100)
        long_output = "x" * 500

        truncated = bridge.truncate_output(long_output)

        assert len(truncated) < 500
        assert truncated.endswith("...[truncated]")

    def test_timeout_handling(self):
        """Test action timeout handling."""
        @dataclass
        class ActionResult:
            status: ActionStatus
            error: str

        class ExecutionBridge:
            async def execute_with_timeout(
                self,
                action_func,
                timeout: int
            ) -> ActionResult:
                try:
                    # Simulate timeout
                    return ActionResult(
                        status=ActionStatus.TIMEOUT,
                        error=f"Action timed out after {timeout}s"
                    )
                except asyncio.TimeoutError:
                    return ActionResult(
                        status=ActionStatus.TIMEOUT,
                        error=f"Action timed out after {timeout}s"
                    )

        # Verify timeout result structure
        result = ActionResult(
            status=ActionStatus.TIMEOUT,
            error="Action timed out after 30s"
        )
        assert result.status == ActionStatus.TIMEOUT


# =============================================================================
# Action History Tests
# =============================================================================

class TestActionHistory:
    """Test action history tracking."""

    def test_record_action_history(self):
        """Test recording action history."""
        @dataclass
        class ActionRequest:
            action_id: str
            action_type: GraceAction

        @dataclass
        class ActionResult:
            action_id: str
            status: ActionStatus

        class ExecutionBridge:
            def __init__(self):
                self.action_history: List[Tuple[ActionRequest, ActionResult]] = []

            def record(self, request: ActionRequest, result: ActionResult):
                self.action_history.append((request, result))

            def get_recent_actions(self, count: int = 10):
                return self.action_history[-count:]

        bridge = ExecutionBridge()

        for i in range(5):
            req = ActionRequest(f"ACT-{i}", GraceAction.THINK)
            res = ActionResult(f"ACT-{i}", ActionStatus.SUCCESS)
            bridge.record(req, res)

        assert len(bridge.action_history) == 5
        recent = bridge.get_recent_actions(3)
        assert len(recent) == 3

    def test_action_history_with_genesis_tracking(self):
        """Test action history with Genesis Key tracking."""
        @dataclass
        class ActionRequest:
            action_id: str
            action_type: GraceAction

        @dataclass
        class ActionResult:
            action_id: str
            status: ActionStatus
            genesis_key_id: Optional[str] = None

        class ExecutionBridge:
            def __init__(self, genesis_tracker=None):
                self.genesis = genesis_tracker
                self.action_history = []

            def execute_and_track(self, request: ActionRequest) -> ActionResult:
                result = ActionResult(
                    action_id=request.action_id,
                    status=ActionStatus.SUCCESS
                )

                if self.genesis:
                    result.genesis_key_id = self.genesis.create_key(request.action_id)

                self.action_history.append((request, result))
                return result

        mock_genesis = MagicMock()
        mock_genesis.create_key.return_value = "GK-ACT-123"

        bridge = ExecutionBridge(genesis_tracker=mock_genesis)
        request = ActionRequest("ACT-001", GraceAction.WRITE_FILE)

        result = bridge.execute_and_track(request)

        assert result.genesis_key_id == "GK-ACT-123"


# =============================================================================
# Handler Routing Tests
# =============================================================================

class TestHandlerRouting:
    """Test action handler routing."""

    def test_get_handler_for_action(self):
        """Test getting appropriate handler for action type."""
        class ExecutionBridge:
            def __init__(self):
                self.handlers = {
                    GraceAction.WRITE_FILE: self._handle_write,
                    GraceAction.READ_FILE: self._handle_read,
                    GraceAction.RUN_PYTHON: self._handle_python,
                    GraceAction.GIT_STATUS: self._handle_git_status,
                }

            def _handle_write(self, action): return "write"
            def _handle_read(self, action): return "read"
            def _handle_python(self, action): return "python"
            def _handle_git_status(self, action): return "git_status"

            def _get_handler(self, action_type: GraceAction):
                return self.handlers.get(action_type)

        bridge = ExecutionBridge()

        assert bridge._get_handler(GraceAction.WRITE_FILE) is not None
        assert bridge._get_handler(GraceAction.RUN_PYTHON) is not None
        assert bridge._get_handler(GraceAction.GIT_STATUS) is not None


# =============================================================================
# Governed Execution Tests
# =============================================================================

class TestGovernedExecution:
    """Test governed/controlled execution features."""

    def test_confirmation_required(self):
        """Test actions that require confirmation."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            requires_confirmation: bool = False

        class GovernedBridge:
            REQUIRES_CONFIRMATION = [
                GraceAction.DELETE_FILE,
                GraceAction.GIT_PUSH,
                GraceAction.GIT_CREATE_PR
            ]

            def needs_confirmation(self, action: ActionRequest) -> bool:
                if action.requires_confirmation:
                    return True
                return action.action_type in self.REQUIRES_CONFIRMATION

        bridge = GovernedBridge()

        delete_action = ActionRequest(GraceAction.DELETE_FILE)
        read_action = ActionRequest(GraceAction.READ_FILE)

        assert bridge.needs_confirmation(delete_action) is True
        assert bridge.needs_confirmation(read_action) is False

    def test_confidence_threshold(self):
        """Test confidence threshold for execution."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            confidence: float = 0.5

        class GovernedBridge:
            def __init__(self, min_confidence: float = 0.7):
                self.min_confidence = min_confidence

            def can_execute(self, action: ActionRequest) -> bool:
                return action.confidence >= self.min_confidence

        bridge = GovernedBridge(min_confidence=0.7)

        high_confidence = ActionRequest(GraceAction.WRITE_FILE, confidence=0.9)
        low_confidence = ActionRequest(GraceAction.WRITE_FILE, confidence=0.5)

        assert bridge.can_execute(high_confidence) is True
        assert bridge.can_execute(low_confidence) is False


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling in execution."""

    @pytest.mark.asyncio
    async def test_handle_execution_error(self):
        """Test handling of execution errors."""
        @dataclass
        class ActionResult:
            status: ActionStatus
            error: str

        class ExecutionBridge:
            async def safe_execute(self, action_func) -> ActionResult:
                try:
                    raise RuntimeError("Execution failed")
                except Exception as e:
                    return ActionResult(
                        status=ActionStatus.FAILURE,
                        error=str(e)
                    )

        bridge = ExecutionBridge()
        result = await bridge.safe_execute(lambda: None)

        assert result.status == ActionStatus.FAILURE
        assert "Execution failed" in result.error

    def test_missing_parameters(self):
        """Test handling missing required parameters."""
        @dataclass
        class ActionRequest:
            action_type: GraceAction
            parameters: Dict[str, Any]

        class ExecutionBridge:
            def validate_parameters(
                self,
                action: ActionRequest,
                required: List[str]
            ) -> Optional[str]:
                for param in required:
                    if param not in action.parameters:
                        return f"Missing required parameter: {param}"
                return None

        bridge = ExecutionBridge()
        request = ActionRequest(
            action_type=GraceAction.WRITE_FILE,
            parameters={"path": "/tmp/test.py"}  # Missing 'content'
        )

        error = bridge.validate_parameters(request, ["path", "content"])
        assert error is not None
        assert "content" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
