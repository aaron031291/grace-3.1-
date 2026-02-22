"""
Grace Action Definitions

Defines all actions Grace can take in the execution environment.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


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

    # Browser (for web testing)
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


@dataclass
class ActionRequest:
    """Request to execute an action."""

    action_id: str = field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:12]}")
    action_type: GraceAction = GraceAction.THINK
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    timeout: int = 300  # seconds
    requires_confirmation: bool = False

    # Cognitive context
    confidence: float = 0.5
    reasoning: str = ""
    related_memory_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "timeout": self.timeout,
            "requires_confirmation": self.requires_confirmation,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "related_memory_ids": self.related_memory_ids,
        }


@dataclass
class ActionResult:
    """Result of an action execution."""

    action_id: str
    action_type: GraceAction
    status: ActionStatus
    output: str = ""
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)

    # Structured results (action-specific)
    data: Dict[str, Any] = field(default_factory=dict)

    # Files affected
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)

    # For learning
    learnable: bool = True
    trust_delta: float = 0.0  # How much this affects trust

    @property
    def success(self) -> bool:
        return self.status == ActionStatus.SUCCESS

    @property
    def failed(self) -> bool:
        return self.status in [ActionStatus.FAILURE, ActionStatus.TIMEOUT]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "completed_at": self.completed_at.isoformat(),
            "data": self.data,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "success": self.success,
            "learnable": self.learnable,
            "trust_delta": self.trust_delta,
        }


# Action-specific parameter schemas
ACTION_SCHEMAS = {
    GraceAction.WRITE_FILE: {
        "required": ["path", "content"],
        "optional": ["overwrite"],
    },
    GraceAction.EDIT_FILE: {
        "required": ["path", "old_content", "new_content"],
        "optional": ["replace_all"],
    },
    GraceAction.READ_FILE: {
        "required": ["path"],
        "optional": ["start_line", "end_line"],
    },
    GraceAction.RUN_PYTHON: {
        "required": ["code"],
        "optional": ["timeout"],
    },
    GraceAction.RUN_BASH: {
        "required": ["command"],
        "optional": ["working_dir", "timeout"],
    },
    GraceAction.RUN_TESTS: {
        "required": ["test_path"],
        "optional": ["test_framework", "verbose"],
    },
    GraceAction.GIT_COMMIT: {
        "required": ["message"],
        "optional": ["files"],
    },
    GraceAction.SEARCH_CODE: {
        "required": ["pattern"],
        "optional": ["path", "file_type"],
    },
    GraceAction.THINK: {
        "required": ["thought"],
        "optional": [],
    },
    GraceAction.PLAN: {
        "required": ["goal"],
        "optional": ["steps"],
    },
    GraceAction.FINISH: {
        "required": ["result"],
        "optional": ["summary"],
    },
}


def validate_action_parameters(action_type: GraceAction, parameters: Dict[str, Any]) -> bool:
    """Validate that required parameters are present."""
    schema = ACTION_SCHEMAS.get(action_type)
    if not schema:
        return True  # No schema defined, allow any parameters

    required = schema.get("required", [])
    for param in required:
        if param not in parameters:
            return False
    return True


def create_action(
    action_type: GraceAction,
    parameters: Dict[str, Any],
    confidence: float = 0.5,
    reasoning: str = "",
    **kwargs
) -> ActionRequest:
    """Factory function to create validated action requests."""
    if not validate_action_parameters(action_type, parameters):
        raise ValueError(f"Missing required parameters for {action_type}")

    return ActionRequest(
        action_type=action_type,
        parameters=parameters,
        confidence=confidence,
        reasoning=reasoning,
        **kwargs
    )
