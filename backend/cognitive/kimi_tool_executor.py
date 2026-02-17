"""
Kimi Tool Executor

Kimi is NOT just intelligence -- Kimi is a tool-using agent that can
execute across ALL of Grace's system capabilities.

This module maps every system tool surface to Kimi's execution ability:

TOOL CATEGORIES:
  1. FILE OPERATIONS     - read, write, edit, delete, search files
  2. CODE EXECUTION      - run python, bash, tests
  3. GIT OPERATIONS      - status, diff, add, commit, push, PR
  4. DIAGNOSTICS         - health checks, healing cycles, sensor data
  5. INGESTION           - ingest documents, manage knowledge base
  6. LEARNING            - trigger study, practice, extract patterns
  7. SCRAPING            - scrape URLs, crawl sites
  8. DEPLOYMENT          - CI/CD, build, deploy
  9. MONITORING          - system health, metrics, telemetry
  10. TASK MANAGEMENT    - todos, planning, Notion sync
  11. KNOWLEDGE BASE     - query, update, manage KB
  12. AUTONOMOUS ACTIONS  - trigger rules, schedule actions
  13. SANDBOX LAB        - propose experiments, run trials
  14. GOVERNANCE         - check policies, evaluate actions
  15. VOICE              - STT/TTS processing
  16. LLM ORCHESTRATION  - multi-model debate, consensus, delegation

Every tool execution is tracked by the LLM Interaction Tracker.
Every outcome feeds the Pattern Learner for dependency reduction.
"""

import logging
import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from cognitive.llm_interaction_tracker import get_llm_interaction_tracker

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """All tool categories Kimi can execute."""
    FILE_OPS = "file_operations"
    CODE_EXEC = "code_execution"
    GIT_OPS = "git_operations"
    DIAGNOSTICS = "diagnostics"
    INGESTION = "ingestion"
    LEARNING = "learning"
    SCRAPING = "scraping"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    TASK_MGMT = "task_management"
    KNOWLEDGE_BASE = "knowledge_base"
    AUTONOMOUS = "autonomous_actions"
    SANDBOX = "sandbox_lab"
    GOVERNANCE = "governance"
    VOICE = "voice"
    LLM_ORCHESTRATION = "llm_orchestration"
    RETRIEVAL = "retrieval"
    COGNITIVE = "cognitive"
    CODEBASE = "codebase"
    SECURITY = "security"


@dataclass
class ToolDefinition:
    """Definition of a tool Kimi can call."""
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    required_params: List[str]
    optional_params: List[str]
    risk_level: str  # low, medium, high, critical
    requires_confirmation: bool = False
    api_endpoint: Optional[str] = None
    internal_handler: Optional[str] = None


@dataclass
class ToolCall:
    """A single tool invocation by Kimi."""
    call_id: str
    tool_id: str
    tool_name: str
    category: ToolCategory
    parameters: Dict[str, Any]
    reasoning: str
    called_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ToolResult:
    """Result of a tool call."""
    call_id: str
    tool_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    files_affected: List[str] = field(default_factory=list)


# ==========================================================================
# TOOL REGISTRY - Every tool Kimi can use
# ==========================================================================

TOOL_REGISTRY: Dict[str, ToolDefinition] = {

    # ---- FILE OPERATIONS ----
    "read_file": ToolDefinition(
        tool_id="read_file", name="Read File",
        description="Read contents of a file by path",
        category=ToolCategory.FILE_OPS,
        parameters={"path": "str", "start_line": "int?", "end_line": "int?"},
        required_params=["path"], optional_params=["start_line", "end_line"],
        risk_level="low", api_endpoint="/agent/execute",
        internal_handler="execution_bridge.read_file",
    ),
    "write_file": ToolDefinition(
        tool_id="write_file", name="Write File",
        description="Write content to a file (creates or overwrites)",
        category=ToolCategory.FILE_OPS,
        parameters={"path": "str", "content": "str", "overwrite": "bool?"},
        required_params=["path", "content"], optional_params=["overwrite"],
        risk_level="medium", api_endpoint="/agent/execute",
        internal_handler="execution_bridge.write_file",
    ),
    "edit_file": ToolDefinition(
        tool_id="edit_file", name="Edit File",
        description="Edit file by replacing old content with new content",
        category=ToolCategory.FILE_OPS,
        parameters={"path": "str", "old_content": "str", "new_content": "str"},
        required_params=["path", "old_content", "new_content"], optional_params=[],
        risk_level="medium", api_endpoint="/agent/execute",
        internal_handler="execution_bridge.edit_file",
    ),
    "delete_file": ToolDefinition(
        tool_id="delete_file", name="Delete File",
        description="Delete a file",
        category=ToolCategory.FILE_OPS,
        parameters={"path": "str"},
        required_params=["path"], optional_params=[],
        risk_level="high", requires_confirmation=True,
        internal_handler="execution_bridge.delete_file",
    ),
    "find_files": ToolDefinition(
        tool_id="find_files", name="Find Files",
        description="Find files matching a glob pattern",
        category=ToolCategory.FILE_OPS,
        parameters={"pattern": "str", "path": "str?"},
        required_params=["pattern"], optional_params=["path"],
        risk_level="low", internal_handler="execution_bridge.find_files",
    ),
    "search_code": ToolDefinition(
        tool_id="search_code", name="Search Code",
        description="Search for patterns in code using ripgrep",
        category=ToolCategory.FILE_OPS,
        parameters={"pattern": "str", "path": "str?", "file_type": "str?"},
        required_params=["pattern"], optional_params=["path", "file_type"],
        risk_level="low", internal_handler="execution_bridge.search_code",
    ),

    # ---- CODE EXECUTION ----
    "run_python": ToolDefinition(
        tool_id="run_python", name="Run Python",
        description="Execute Python code in a sandboxed environment",
        category=ToolCategory.CODE_EXEC,
        parameters={"code": "str", "timeout": "int?"},
        required_params=["code"], optional_params=["timeout"],
        risk_level="medium", internal_handler="execution_bridge.run_python",
    ),
    "run_bash": ToolDefinition(
        tool_id="run_bash", name="Run Bash Command",
        description="Execute a shell command",
        category=ToolCategory.CODE_EXEC,
        parameters={"command": "str", "working_dir": "str?", "timeout": "int?"},
        required_params=["command"], optional_params=["working_dir", "timeout"],
        risk_level="medium", internal_handler="execution_bridge.run_bash",
    ),
    "run_tests": ToolDefinition(
        tool_id="run_tests", name="Run Tests",
        description="Run test suite with auto-detected framework",
        category=ToolCategory.CODE_EXEC,
        parameters={"test_path": "str?", "framework": "str?", "verbose": "bool?"},
        required_params=[], optional_params=["test_path", "framework", "verbose"],
        risk_level="low", internal_handler="execution_bridge.run_tests",
    ),
    "lint_code": ToolDefinition(
        tool_id="lint_code", name="Lint Code",
        description="Run linter on code files",
        category=ToolCategory.CODE_EXEC,
        parameters={"path": "str", "linter": "str?"},
        required_params=["path"], optional_params=["linter"],
        risk_level="low", internal_handler="execution_bridge.lint_code",
    ),

    # ---- GIT OPERATIONS ----
    "git_status": ToolDefinition(
        tool_id="git_status", name="Git Status",
        description="Get current git status (staged, unstaged, untracked)",
        category=ToolCategory.GIT_OPS,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", internal_handler="execution_bridge.git_status",
    ),
    "git_diff": ToolDefinition(
        tool_id="git_diff", name="Git Diff",
        description="Show changes between working tree and index",
        category=ToolCategory.GIT_OPS,
        parameters={"staged": "bool?"},
        required_params=[], optional_params=["staged"],
        risk_level="low", internal_handler="execution_bridge.git_diff",
    ),
    "git_add": ToolDefinition(
        tool_id="git_add", name="Git Add",
        description="Stage files for commit",
        category=ToolCategory.GIT_OPS,
        parameters={"files": "list[str]?"},
        required_params=[], optional_params=["files"],
        risk_level="low", internal_handler="execution_bridge.git_add",
    ),
    "git_commit": ToolDefinition(
        tool_id="git_commit", name="Git Commit",
        description="Create a git commit with message",
        category=ToolCategory.GIT_OPS,
        parameters={"message": "str"},
        required_params=["message"], optional_params=[],
        risk_level="medium", internal_handler="execution_bridge.git_commit",
    ),
    "git_push": ToolDefinition(
        tool_id="git_push", name="Git Push",
        description="Push commits to remote repository",
        category=ToolCategory.GIT_OPS,
        parameters={"remote": "str?", "branch": "str?"},
        required_params=[], optional_params=["remote", "branch"],
        risk_level="high", requires_confirmation=True,
        internal_handler="execution_bridge.git_push",
    ),

    # ---- DIAGNOSTICS ----
    "run_diagnostic": ToolDefinition(
        tool_id="run_diagnostic", name="Run Diagnostic Cycle",
        description="Trigger a full 4-layer diagnostic cycle (sensors->interpreters->judgement->action)",
        category=ToolCategory.DIAGNOSTICS,
        parameters={"trigger": "str?"},
        required_params=[], optional_params=["trigger"],
        risk_level="low", api_endpoint="/diagnostic/cycle",
    ),
    "health_check": ToolDefinition(
        tool_id="health_check", name="System Health Check",
        description="Check overall system health status",
        category=ToolCategory.DIAGNOSTICS,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", api_endpoint="/health/detailed",
    ),
    "trigger_healing": ToolDefinition(
        tool_id="trigger_healing", name="Trigger Self-Healing",
        description="Trigger self-healing for a detected issue",
        category=ToolCategory.DIAGNOSTICS,
        parameters={"issue_type": "str", "target": "str?"},
        required_params=["issue_type"], optional_params=["target"],
        risk_level="medium", api_endpoint="/diagnostic/heal",
    ),

    # ---- INGESTION ----
    "ingest_file": ToolDefinition(
        tool_id="ingest_file", name="Ingest File",
        description="Ingest a file into the knowledge base with chunking and embedding",
        category=ToolCategory.INGESTION,
        parameters={"file_path": "str", "category": "str?", "metadata": "dict?"},
        required_params=["file_path"], optional_params=["category", "metadata"],
        risk_level="low", api_endpoint="/ingest/file",
    ),
    "ingest_url": ToolDefinition(
        tool_id="ingest_url", name="Ingest URL",
        description="Scrape and ingest content from a URL",
        category=ToolCategory.INGESTION,
        parameters={"url": "str", "depth": "int?"},
        required_params=["url"], optional_params=["depth"],
        risk_level="low", api_endpoint="/scrape/url",
    ),
    "ingest_directory": ToolDefinition(
        tool_id="ingest_directory", name="Ingest Directory",
        description="Ingest all files in a directory recursively",
        category=ToolCategory.INGESTION,
        parameters={"directory": "str", "extensions": "list[str]?"},
        required_params=["directory"], optional_params=["extensions"],
        risk_level="low", api_endpoint="/file-ingest/directory",
    ),

    # ---- LEARNING ----
    "trigger_study": ToolDefinition(
        tool_id="trigger_study", name="Trigger Study Session",
        description="Start a learning study session on a topic",
        category=ToolCategory.LEARNING,
        parameters={"topic": "str", "objectives": "list[str]?"},
        required_params=["topic"], optional_params=["objectives"],
        risk_level="low", api_endpoint="/autonomous-learning/study",
    ),
    "trigger_practice": ToolDefinition(
        tool_id="trigger_practice", name="Trigger Practice",
        description="Practice a skill in the sandbox",
        category=ToolCategory.LEARNING,
        parameters={"skill": "str", "complexity": "float?"},
        required_params=["skill"], optional_params=["complexity"],
        risk_level="low", api_endpoint="/autonomous-learning/practice",
    ),
    "extract_patterns": ToolDefinition(
        tool_id="extract_patterns", name="Extract Learning Patterns",
        description="Extract patterns from recent LLM interactions for autonomous use",
        category=ToolCategory.LEARNING,
        parameters={"time_window_hours": "int?"},
        required_params=[], optional_params=["time_window_hours"],
        risk_level="low", api_endpoint="/llm-learning/patterns/extract",
    ),
    "get_learning_progress": ToolDefinition(
        tool_id="get_learning_progress", name="Get Learning Progress",
        description="Check overall learning progress and autonomy readiness",
        category=ToolCategory.LEARNING,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", api_endpoint="/llm-learning/progress",
    ),

    # ---- SCRAPING ----
    "scrape_url": ToolDefinition(
        tool_id="scrape_url", name="Scrape URL",
        description="Scrape content from a web URL",
        category=ToolCategory.SCRAPING,
        parameters={"url": "str", "selector": "str?", "depth": "int?"},
        required_params=["url"], optional_params=["selector", "depth"],
        risk_level="low", api_endpoint="/scrape/url",
    ),

    # ---- DEPLOYMENT ----
    "trigger_cicd": ToolDefinition(
        tool_id="trigger_cicd", name="Trigger CI/CD Pipeline",
        description="Trigger a CI/CD pipeline run",
        category=ToolCategory.DEPLOYMENT,
        parameters={"pipeline": "str?", "branch": "str?"},
        required_params=[], optional_params=["pipeline", "branch"],
        risk_level="high", requires_confirmation=True,
        api_endpoint="/api/cicd/trigger",
    ),
    "build_project": ToolDefinition(
        tool_id="build_project", name="Build Project",
        description="Build the project (npm build, pip install, etc.)",
        category=ToolCategory.DEPLOYMENT,
        parameters={"project_path": "str?", "command": "str?"},
        required_params=[], optional_params=["project_path", "command"],
        risk_level="medium", internal_handler="execution_bridge.build_project",
    ),
    "install_deps": ToolDefinition(
        tool_id="install_deps", name="Install Dependencies",
        description="Install project dependencies",
        category=ToolCategory.DEPLOYMENT,
        parameters={"manager": "str?", "packages": "list[str]?"},
        required_params=[], optional_params=["manager", "packages"],
        risk_level="medium", internal_handler="execution_bridge.install_deps",
    ),

    # ---- MONITORING ----
    "get_system_metrics": ToolDefinition(
        tool_id="get_system_metrics", name="Get System Metrics",
        description="Get current system metrics (CPU, memory, response times)",
        category=ToolCategory.MONITORING,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", api_endpoint="/monitoring/metrics",
    ),
    "get_telemetry": ToolDefinition(
        tool_id="get_telemetry", name="Get Telemetry",
        description="Get system telemetry data",
        category=ToolCategory.MONITORING,
        parameters={"time_range": "str?"},
        required_params=[], optional_params=["time_range"],
        risk_level="low", api_endpoint="/telemetry/summary",
    ),
    "get_kpis": ToolDefinition(
        tool_id="get_kpis", name="Get KPI Dashboard",
        description="Get KPI dashboard with all tracked metrics",
        category=ToolCategory.MONITORING,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", api_endpoint="/kpi/dashboard",
    ),

    # ---- TASK MANAGEMENT ----
    "create_todo": ToolDefinition(
        tool_id="create_todo", name="Create Todo",
        description="Create a new task/todo item",
        category=ToolCategory.TASK_MGMT,
        parameters={"title": "str", "description": "str?", "priority": "str?"},
        required_params=["title"], optional_params=["description", "priority"],
        risk_level="low", api_endpoint="/api/grace-todos/create",
    ),
    "list_todos": ToolDefinition(
        tool_id="list_todos", name="List Todos",
        description="List current tasks/todos",
        category=ToolCategory.TASK_MGMT,
        parameters={"status": "str?"},
        required_params=[], optional_params=["status"],
        risk_level="low", api_endpoint="/api/grace-todos/list",
    ),
    "start_planning": ToolDefinition(
        tool_id="start_planning", name="Start Planning Workflow",
        description="Start the Grace planning workflow (concept to execution)",
        category=ToolCategory.TASK_MGMT,
        parameters={"concept": "str", "context": "dict?"},
        required_params=["concept"], optional_params=["context"],
        risk_level="low", api_endpoint="/api/grace-planning/start",
    ),

    # ---- KNOWLEDGE BASE ----
    "query_knowledge": ToolDefinition(
        tool_id="query_knowledge", name="Query Knowledge Base",
        description="Query the knowledge base using semantic search",
        category=ToolCategory.KNOWLEDGE_BASE,
        parameters={"query": "str", "top_k": "int?", "filters": "dict?"},
        required_params=["query"], optional_params=["top_k", "filters"],
        risk_level="low", api_endpoint="/retrieve/query",
    ),
    "get_document": ToolDefinition(
        tool_id="get_document", name="Get Document",
        description="Retrieve a specific document from the knowledge base",
        category=ToolCategory.KNOWLEDGE_BASE,
        parameters={"document_id": "str"},
        required_params=["document_id"], optional_params=[],
        risk_level="low", api_endpoint="/retrieve/document",
    ),

    # ---- AUTONOMOUS ACTIONS ----
    "queue_action": ToolDefinition(
        tool_id="queue_action", name="Queue Autonomous Action",
        description="Queue an autonomous action for execution",
        category=ToolCategory.AUTONOMOUS,
        parameters={"action_type": "str", "context": "dict?", "priority": "str?"},
        required_params=["action_type"], optional_params=["context", "priority"],
        risk_level="medium", api_endpoint="/api/autonomous/queue",
    ),

    # ---- SANDBOX LAB ----
    "propose_experiment": ToolDefinition(
        tool_id="propose_experiment", name="Propose Experiment",
        description="Propose a self-improvement experiment in the sandbox",
        category=ToolCategory.SANDBOX,
        parameters={"name": "str", "description": "str", "type": "str", "motivation": "str"},
        required_params=["name", "description", "type", "motivation"],
        optional_params=[],
        risk_level="low", api_endpoint="/sandbox-lab/experiments/propose",
    ),

    # ---- GOVERNANCE ----
    "check_governance": ToolDefinition(
        tool_id="check_governance", name="Check Governance",
        description="Check if an action is allowed by governance policies",
        category=ToolCategory.GOVERNANCE,
        parameters={"action_type": "str", "target": "str?", "impact": "str?"},
        required_params=["action_type"], optional_params=["target", "impact"],
        risk_level="low", api_endpoint="/governance/evaluate",
    ),

    # ---- LLM ORCHESTRATION ----
    "llm_task": ToolDefinition(
        tool_id="llm_task", name="Execute LLM Task",
        description="Execute a task using the multi-LLM orchestration system",
        category=ToolCategory.LLM_ORCHESTRATION,
        parameters={"prompt": "str", "task_type": "str?", "model": "str?"},
        required_params=["prompt"], optional_params=["task_type", "model"],
        risk_level="low", api_endpoint="/llm/task",
    ),
    "llm_debate": ToolDefinition(
        tool_id="llm_debate", name="Start LLM Debate",
        description="Have multiple LLMs debate a topic",
        category=ToolCategory.LLM_ORCHESTRATION,
        parameters={"topic": "str", "positions": "list[str]?"},
        required_params=["topic"], optional_params=["positions"],
        risk_level="low", api_endpoint="/llm/collaborate/debate",
    ),

    # ---- RETRIEVAL ----
    "rag_query": ToolDefinition(
        tool_id="rag_query", name="RAG Query",
        description="Query with retrieval-augmented generation",
        category=ToolCategory.RETRIEVAL,
        parameters={"query": "str", "top_k": "int?"},
        required_params=["query"], optional_params=["top_k"],
        risk_level="low", api_endpoint="/retrieve/query",
    ),

    # ---- CODEBASE ----
    "browse_codebase": ToolDefinition(
        tool_id="browse_codebase", name="Browse Codebase",
        description="Browse the codebase file tree",
        category=ToolCategory.CODEBASE,
        parameters={"path": "str?"},
        required_params=[], optional_params=["path"],
        risk_level="low", api_endpoint="/codebase/tree",
    ),
    "analyze_code": ToolDefinition(
        tool_id="analyze_code", name="Analyze Code",
        description="Analyze a code file for structure, complexity, and issues",
        category=ToolCategory.CODEBASE,
        parameters={"path": "str"},
        required_params=["path"], optional_params=[],
        risk_level="low", api_endpoint="/codebase/analyze",
    ),

    # ---- COGNITIVE ----
    "get_cognitive_state": ToolDefinition(
        tool_id="get_cognitive_state", name="Get Cognitive State",
        description="Get Grace's current cognitive state (OODA phase, confidence, etc.)",
        category=ToolCategory.COGNITIVE,
        parameters={},
        required_params=[], optional_params=[],
        risk_level="low", api_endpoint="/cognitive/state",
    ),
    "get_dependency_metrics": ToolDefinition(
        tool_id="get_dependency_metrics", name="Get LLM Dependency Metrics",
        description="Check how much Grace depends on LLMs and progress toward autonomy",
        category=ToolCategory.COGNITIVE,
        parameters={"period_hours": "int?"},
        required_params=[], optional_params=["period_hours"],
        risk_level="low", api_endpoint="/llm-learning/dependency/metrics",
    ),
}


# ==========================================================================
# KIMI TOOL EXECUTOR
# ==========================================================================

class KimiToolExecutor:
    """
    Kimi's hands. Every tool in Grace's system, callable by Kimi.

    This is NOT intelligence -- this is tool execution. Kimi decides
    WHAT to do (intelligence), and this executor does it (tool use).

    Usage:
        executor = KimiToolExecutor(session)

        # List available tools
        tools = executor.list_tools()

        # Call a tool
        result = await executor.call_tool("run_bash", {"command": "ls -la"})

        # Call with tracking
        result = await executor.call_tool(
            "ingest_file",
            {"file_path": "/data/doc.pdf"},
            reasoning="User asked to add this document to knowledge base"
        )
    """

    def __init__(
        self,
        session: Session,
        execution_bridge=None,
        confirm_high_risk: bool = True,
    ):
        self.session = session
        self.execution_bridge = execution_bridge
        self.confirm_high_risk = confirm_high_risk
        self.tracker = get_llm_interaction_tracker(session)

        self._call_history: List[Dict[str, Any]] = []
        self._stats = {
            "total_calls": 0,
            "successful": 0,
            "failed": 0,
            "by_category": {},
            "by_tool": {},
        }

        logger.info(
            f"[KIMI-TOOLS] Tool executor initialized with "
            f"{len(TOOL_REGISTRY)} tools across "
            f"{len(set(t.category for t in TOOL_REGISTRY.values()))} categories"
        )

    def list_tools(
        self,
        category: Optional[str] = None,
        include_high_risk: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List all available tools, optionally filtered by category.

        This is what Kimi calls to know what tools are available.
        """
        tools = []
        for tool_id, tool_def in TOOL_REGISTRY.items():
            if category and tool_def.category.value != category:
                continue
            if not include_high_risk and tool_def.risk_level in ("high", "critical"):
                continue

            tools.append({
                "tool_id": tool_def.tool_id,
                "name": tool_def.name,
                "description": tool_def.description,
                "category": tool_def.category.value,
                "parameters": tool_def.parameters,
                "required_params": tool_def.required_params,
                "risk_level": tool_def.risk_level,
                "requires_confirmation": tool_def.requires_confirmation,
            })

        return tools

    def list_categories(self) -> List[Dict[str, Any]]:
        """List all tool categories with counts."""
        category_counts = {}
        for tool_def in TOOL_REGISTRY.values():
            cat = tool_def.category.value
            if cat not in category_counts:
                category_counts[cat] = {"count": 0, "tools": []}
            category_counts[cat]["count"] += 1
            category_counts[cat]["tools"].append(tool_def.tool_id)

        return [
            {"category": cat, **info}
            for cat, info in sorted(category_counts.items())
        ]

    def get_tool_schema(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get the full schema for a specific tool."""
        tool_def = TOOL_REGISTRY.get(tool_id)
        if not tool_def:
            return None

        return {
            "tool_id": tool_def.tool_id,
            "name": tool_def.name,
            "description": tool_def.description,
            "category": tool_def.category.value,
            "parameters": tool_def.parameters,
            "required_params": tool_def.required_params,
            "optional_params": tool_def.optional_params,
            "risk_level": tool_def.risk_level,
            "requires_confirmation": tool_def.requires_confirmation,
            "api_endpoint": tool_def.api_endpoint,
        }

    async def call_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        reasoning: str = "",
        session_id: Optional[str] = None,
        skip_tracking: bool = False,
    ) -> ToolResult:
        """
        Execute a tool call.

        This is the main entry point for Kimi to use ANY tool in the system.

        Args:
            tool_id: Which tool to call (from TOOL_REGISTRY)
            parameters: Tool parameters
            reasoning: Why Kimi is calling this tool
            session_id: Session ID for grouping calls
            skip_tracking: Skip LLM interaction tracking

        Returns:
            ToolResult with output or error
        """
        start_time = time.time()

        tool_def = TOOL_REGISTRY.get(tool_id)
        if not tool_def:
            return ToolResult(
                call_id=f"CALL-{uuid.uuid4().hex[:12]}",
                tool_id=tool_id,
                success=False,
                error=f"Unknown tool: {tool_id}. Use list_tools() to see available tools.",
            )

        call_id = f"CALL-{uuid.uuid4().hex[:12]}"

        missing = [p for p in tool_def.required_params if p not in parameters]
        if missing:
            return ToolResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=f"Missing required parameters: {missing}",
            )

        if tool_def.requires_confirmation and self.confirm_high_risk:
            logger.warning(
                f"[KIMI-TOOLS] High-risk tool {tool_id} called. "
                f"Confirmation required. Reason: {reasoning}"
            )

        self._stats["total_calls"] += 1
        cat = tool_def.category.value
        self._stats["by_category"][cat] = self._stats["by_category"].get(cat, 0) + 1
        self._stats["by_tool"][tool_id] = self._stats["by_tool"].get(tool_id, 0) + 1

        try:
            if tool_def.internal_handler and self.execution_bridge:
                result = await self._execute_via_bridge(tool_def, parameters)
            elif tool_def.api_endpoint:
                result = await self._execute_via_api(tool_def, parameters)
            else:
                result = await self._execute_generic(tool_def, parameters)

            duration_ms = (time.time() - start_time) * 1000

            tool_result = ToolResult(
                call_id=call_id,
                tool_id=tool_id,
                success=True,
                output=result,
                duration_ms=duration_ms,
            )

            self._stats["successful"] += 1

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"[KIMI-TOOLS] Tool {tool_id} failed: {e}")

            tool_result = ToolResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

            self._stats["failed"] += 1

        if not skip_tracking:
            self.tracker.record_interaction(
                prompt=f"Tool call: {tool_id}({parameters})",
                response=str(tool_result.output)[:2000] if tool_result.output else str(tool_result.error),
                model_used="kimi",
                interaction_type="command_execution",
                delegation_type="kimi_direct",
                outcome="success" if tool_result.success else "failure",
                confidence_score=0.9 if tool_result.success else 0.3,
                duration_ms=duration_ms,
                commands_executed=[tool_id],
                error_message=tool_result.error,
                session_id=session_id,
                metadata={
                    "tool_id": tool_id,
                    "tool_category": tool_def.category.value,
                    "parameters": parameters,
                    "reasoning": reasoning,
                },
            )

        self._call_history.append({
            "call_id": call_id,
            "tool_id": tool_id,
            "category": tool_def.category.value,
            "success": tool_result.success,
            "duration_ms": duration_ms,
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return tool_result

    async def call_tools_parallel(
        self,
        calls: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls in parallel.

        Useful when Kimi needs to gather information from multiple
        sources simultaneously.

        Args:
            calls: List of {"tool_id": str, "parameters": dict, "reasoning": str}
            session_id: Session ID for grouping

        Returns:
            List of ToolResults in same order as calls
        """
        tasks = [
            self.call_tool(
                tool_id=call["tool_id"],
                parameters=call.get("parameters", {}),
                reasoning=call.get("reasoning", ""),
                session_id=session_id,
            )
            for call in calls
        ]

        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _execute_via_bridge(
        self,
        tool_def: ToolDefinition,
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute tool through the execution bridge."""
        from execution.actions import GraceAction, create_action

        action_map = {
            "execution_bridge.read_file": GraceAction.READ_FILE,
            "execution_bridge.write_file": GraceAction.WRITE_FILE,
            "execution_bridge.edit_file": GraceAction.EDIT_FILE,
            "execution_bridge.delete_file": GraceAction.DELETE_FILE,
            "execution_bridge.run_python": GraceAction.RUN_PYTHON,
            "execution_bridge.run_bash": GraceAction.RUN_BASH,
            "execution_bridge.run_tests": GraceAction.RUN_TESTS,
            "execution_bridge.git_status": GraceAction.GIT_STATUS,
            "execution_bridge.git_diff": GraceAction.GIT_DIFF,
            "execution_bridge.git_add": GraceAction.GIT_ADD,
            "execution_bridge.git_commit": GraceAction.GIT_COMMIT,
            "execution_bridge.search_code": GraceAction.SEARCH_CODE,
            "execution_bridge.find_files": GraceAction.FIND_FILES,
            "execution_bridge.lint_code": GraceAction.LINT_CODE,
            "execution_bridge.build_project": GraceAction.BUILD_PROJECT,
            "execution_bridge.install_deps": GraceAction.INSTALL_DEPS,
            "execution_bridge.git_push": GraceAction.GIT_PUSH,
        }

        handler = tool_def.internal_handler
        action_type = action_map.get(handler)

        if not action_type:
            raise ValueError(f"No action mapping for handler: {handler}")

        action = create_action(
            action_type,
            parameters,
            reasoning=f"Kimi tool call: {tool_def.name}",
        )

        result = await self.execution_bridge.execute(action)

        if result.success:
            return {
                "output": result.output,
                "data": result.data,
                "files_created": result.files_created,
                "files_modified": result.files_modified,
                "execution_time": result.execution_time,
            }
        else:
            raise RuntimeError(result.error or "Tool execution failed")

    async def _execute_via_api(
        self,
        tool_def: ToolDefinition,
        parameters: Dict[str, Any],
    ) -> Any:
        """
        Execute tool by recording the API call intent.

        In a full deployment, this would make an HTTP call to the endpoint.
        For now, we record the intent so the system can execute it.
        """
        return {
            "api_endpoint": tool_def.api_endpoint,
            "parameters": parameters,
            "tool": tool_def.name,
            "status": "recorded",
            "note": (
                f"Tool call to {tool_def.api_endpoint} recorded. "
                "Connect to HTTP client for live execution."
            ),
        }

    async def _execute_generic(
        self,
        tool_def: ToolDefinition,
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute a generic tool (fallback)."""
        return {
            "tool": tool_def.name,
            "parameters": parameters,
            "status": "recorded",
            "note": "No specific handler; tool call recorded for tracking.",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        total = self._stats["total_calls"]
        return {
            **self._stats,
            "success_rate": (
                self._stats["successful"] / total if total > 0 else 0
            ),
            "total_tools_available": len(TOOL_REGISTRY),
            "total_categories": len(set(t.category for t in TOOL_REGISTRY.values())),
            "recent_calls": self._call_history[-10:],
        }


_executor_instance: Optional[KimiToolExecutor] = None


def get_kimi_tool_executor(
    session: Session,
    execution_bridge=None,
) -> KimiToolExecutor:
    """Get or create the Kimi tool executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = KimiToolExecutor(
            session=session,
            execution_bridge=execution_bridge,
        )
    return _executor_instance
