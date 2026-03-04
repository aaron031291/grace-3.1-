"""
Grace Agent

The complete software engineering agent that combines Grace's cognitive
systems with execution capabilities to solve real programming tasks.

This is the main agent loop that:
1. Understands tasks using RAG
2. Plans approach using OODA
3. Executes using the execution bridge
4. Learns from outcomes
5. Iterates until complete
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

from execution.bridge import ExecutionBridge, ExecutionConfig, get_execution_bridge
from execution.actions import (
    GraceAction,
    ActionRequest,
    ActionResult,
    ActionStatus,
    create_action,
)
from execution.feedback import FeedbackProcessor, get_feedback_processor, LearningSignal

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for the Grace Agent."""

    # Execution settings
    max_iterations: int = 50
    timeout_per_action: int = 300
    workspace_dir: str = None

    # Cognitive settings
    confidence_threshold: float = 0.5
    use_rag: bool = True
    use_memory: bool = True

    # Safety settings
    require_confirmation_for_git: bool = True
    require_confirmation_for_delete: bool = True
    auto_commit: bool = False
    test_before_commit: bool = True

    # Learning settings
    learn_from_execution: bool = True
    min_confidence_for_pattern: float = 0.6


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    summary: str = ""
    output: str = ""
    error: Optional[str] = None

    # Actions taken
    actions_executed: int = 0
    actions_succeeded: int = 0
    actions_failed: int = 0

    # Files affected
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)

    # Learning
    patterns_learned: int = 0
    trust_delta: float = 0.0

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "summary": self.summary,
            "output": self.output,
            "error": self.error,
            "actions_executed": self.actions_executed,
            "actions_succeeded": self.actions_succeeded,
            "actions_failed": self.actions_failed,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "patterns_learned": self.patterns_learned,
            "trust_delta": self.trust_delta,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class GraceAgent:
    """
    Grace's Software Engineering Agent.

    Combines:
    - RAG retrieval for knowledge
    - OODA loop for decision making
    - Execution bridge for actions
    - Feedback processor for learning

    Usage:
        agent = GraceAgent()
        result = await agent.solve_task("Fix the bug in auth.py")
    """

    def __init__(
        self,
        config: AgentConfig = None,
        retriever=None,
        llm_client=None,
        genesis_tracker=None,
    ):
        self.config = config or AgentConfig()
        self.retriever = retriever  # Grace's RAG retriever
        self.llm = llm_client  # LLM for reasoning
        self.genesis = genesis_tracker  # Genesis Keys

        # Execution components
        exec_config = ExecutionConfig(
            workspace_dir=self.config.workspace_dir,
            timeout=self.config.timeout_per_action,
        )
        self.execution = get_execution_bridge(config=exec_config, genesis_tracker=genesis_tracker)
        self.feedback = get_feedback_processor()

        # State
        self.current_task: Optional[str] = None
        self.action_history: List[Tuple[ActionRequest, ActionResult]] = []
        self.context: Dict[str, Any] = {}

    async def solve_task(
        self,
        task: str,
        context: Dict[str, Any] = None,
        on_action: Callable[[ActionRequest, ActionResult], None] = None,
    ) -> TaskResult:
        """
        Main entry point: solve a software engineering task.

        Args:
            task: Natural language description of the task
            context: Additional context (files, constraints, etc.)
            on_action: Callback for each action (for UI updates)

        Returns:
            TaskResult with summary, files affected, etc.
        """
        task_id = f"TASK-{uuid.uuid4().hex[:12]}"
        self.current_task = task
        self.context = context or {}
        self.action_history = []

        logger.info(f"Starting task {task_id}: {task[:100]}...")

        result = TaskResult(task_id=task_id, status=TaskStatus.PLANNING)

        try:
            # Phase 1: Understand the task
            understanding = await self._understand_task(task)
            logger.info(f"Task understanding: {understanding.get('summary', 'N/A')}")

            # Phase 2: Create plan
            result.status = TaskStatus.PLANNING
            plan = await self._create_plan(task, understanding)
            logger.info(f"Created plan with {len(plan.get('steps', []))} steps")

            # Phase 3: Execute plan
            result.status = TaskStatus.EXECUTING
            iteration = 0

            while iteration < self.config.max_iterations:
                iteration += 1

                # Decide next action
                next_action = await self._decide_next_action(plan, self.action_history)

                if next_action is None:
                    # No more actions needed
                    break

                if next_action.action_type == GraceAction.FINISH:
                    # Task complete
                    break

                # Execute action
                action_result = await self.execution.execute(next_action)
                self.action_history.append((next_action, action_result))
                result.actions_executed += 1

                # Track success/failure
                if action_result.success:
                    result.actions_succeeded += 1
                else:
                    result.actions_failed += 1

                # Track files
                result.files_created.extend(action_result.files_created)
                result.files_modified.extend(action_result.files_modified)
                result.files_deleted.extend(action_result.files_deleted)

                # Callback for UI
                if on_action:
                    on_action(next_action, action_result)

                # Learn from result
                if self.config.learn_from_execution:
                    signals = await self.feedback.process(next_action, action_result)
                    result.patterns_learned += len(signals)
                    result.trust_delta += action_result.trust_delta

                # Check if we should continue
                if action_result.status == ActionStatus.FAILURE:
                    # Analyze failure and potentially adjust plan
                    should_continue = await self._handle_failure(action_result, plan)
                    if not should_continue:
                        result.status = TaskStatus.FAILED
                        result.error = action_result.error
                        break

            # Phase 4: Finalize
            if result.status == TaskStatus.EXECUTING:
                result.status = TaskStatus.COMPLETED

            result.summary = await self._create_summary(task, result)
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            logger.info(
                f"Task {task_id} completed: {result.status.value} "
                f"({result.actions_executed} actions, {result.duration_seconds:.1f}s)"
            )

            return result

        except Exception as e:
            logger.exception(f"Task {task_id} failed with error")
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            return result

    async def _understand_task(self, task: str) -> Dict[str, Any]:
        """
        Understand the task using RAG and context analysis.
        """
        understanding = {
            "task": task,
            "task_type": self._classify_task(task),
            "entities": [],
            "context": [],
            "constraints": [],
        }

        # Use RAG to find relevant context
        if self.config.use_rag and self.retriever:
            try:
                # Retrieve relevant documents
                results = await self._retrieve_context(task)
                understanding["context"] = results
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

        # Extract entities (files, functions, etc.) from task
        understanding["entities"] = self._extract_entities(task)

        # Generate summary using LLM if available
        if self.llm:
            understanding["summary"] = await self._generate_understanding_summary(task, understanding)
        else:
            understanding["summary"] = f"Task: {task[:200]}"

        return understanding

    def _classify_task(self, task: str) -> str:
        """Classify the type of task."""
        task_lower = task.lower()

        if any(w in task_lower for w in ["fix", "bug", "error", "issue", "broken"]):
            return "bug_fix"
        elif any(w in task_lower for w in ["add", "create", "implement", "new", "feature"]):
            return "feature"
        elif any(w in task_lower for w in ["refactor", "clean", "improve", "optimize"]):
            return "refactor"
        elif any(w in task_lower for w in ["test", "testing", "coverage"]):
            return "testing"
        elif any(w in task_lower for w in ["document", "readme", "comment"]):
            return "documentation"
        elif any(w in task_lower for w in ["review", "check", "analyze"]):
            return "review"
        else:
            return "general"

    def _extract_entities(self, task: str) -> List[Dict[str, str]]:
        """Extract file names, function names, etc. from task."""
        entities = []

        # Simple pattern matching for common entities
        import re

        # File paths
        file_patterns = re.findall(r'[\w/\\]+\.\w+', task)
        for f in file_patterns:
            entities.append({"type": "file", "value": f})

        # Function/method names (word followed by parentheses)
        func_patterns = re.findall(r'\b(\w+)\s*\(', task)
        for f in func_patterns:
            if f not in ["if", "for", "while", "with", "def", "class"]:
                entities.append({"type": "function", "value": f})

        # Class names (capitalized words)
        class_patterns = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\b', task)
        for c in class_patterns:
            if len(c) > 2:
                entities.append({"type": "class", "value": c})

        return entities

    async def _retrieve_context(self, task: str) -> List[Dict[str, Any]]:
        """Retrieve relevant context using RAG."""
        if not self.retriever:
            return []

        try:
            # Use existing Grace retriever
            results = self.retriever.retrieve(task, top_k=5)
            return [
                {
                    "content": r.get("content", "")[:1000],
                    "source": r.get("source", "unknown"),
                    "score": r.get("score", 0),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")
            return []

    async def _generate_understanding_summary(
        self,
        task: str,
        understanding: Dict[str, Any],
    ) -> str:
        """Generate a summary of task understanding using LLM."""
        # Simplified - in production, use the LLM
        return f"Task type: {understanding['task_type']}, Entities: {len(understanding['entities'])}"

    async def _create_plan(
        self,
        task: str,
        understanding: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create an execution plan for the task.
        """
        task_type = understanding.get("task_type", "general")

        # Create plan based on task type
        plan = {
            "goal": task,
            "task_type": task_type,
            "steps": [],
            "current_step": 0,
        }

        # Generate steps based on task type
        if task_type == "bug_fix":
            plan["steps"] = [
                {"action": "read_relevant_files", "description": "Read the relevant code"},
                {"action": "understand_bug", "description": "Understand the bug"},
                {"action": "write_fix", "description": "Write the fix"},
                {"action": "run_tests", "description": "Run tests to verify"},
                {"action": "finish", "description": "Complete task"},
            ]
        elif task_type == "feature":
            plan["steps"] = [
                {"action": "understand_requirements", "description": "Understand what to build"},
                {"action": "read_existing_code", "description": "Read existing code structure"},
                {"action": "write_code", "description": "Write the new code"},
                {"action": "write_tests", "description": "Write tests"},
                {"action": "run_tests", "description": "Run tests"},
                {"action": "finish", "description": "Complete task"},
            ]
        elif task_type == "refactor":
            plan["steps"] = [
                {"action": "read_code", "description": "Read code to refactor"},
                {"action": "run_tests", "description": "Run tests (baseline)"},
                {"action": "refactor", "description": "Refactor the code"},
                {"action": "run_tests", "description": "Run tests (verify)"},
                {"action": "finish", "description": "Complete task"},
            ]
        else:
            plan["steps"] = [
                {"action": "analyze", "description": "Analyze the task"},
                {"action": "execute", "description": "Execute required actions"},
                {"action": "verify", "description": "Verify the result"},
                {"action": "finish", "description": "Complete task"},
            ]

        return plan

    async def _decide_next_action(
        self,
        plan: Dict[str, Any],
        history: List[Tuple[ActionRequest, ActionResult]],
    ) -> Optional[ActionRequest]:
        """
        Decide the next action based on plan and history.

        This is where the OODA loop happens:
        - Observe: Look at history and current state
        - Orient: Understand where we are in the plan
        - Decide: Choose the next action
        - Act: Return the action to execute
        """
        # Check if we're done
        if plan["current_step"] >= len(plan["steps"]):
            return create_action(
                GraceAction.FINISH,
                {"result": "Task completed", "summary": "All steps executed"},
            )

        current_step = plan["steps"][plan["current_step"]]
        step_action = current_step.get("action", "")

        # Get last result
        last_result = history[-1][1] if history else None

        # Decide based on step type and state
        if step_action == "read_relevant_files" or step_action == "read_code" or step_action == "read_existing_code":
            # Find files to read from entities or task
            entities = [e for e in self.context.get("entities", []) if e["type"] == "file"]
            if entities:
                file_path = entities[0]["value"]
            else:
                # Default to searching
                return create_action(
                    GraceAction.FIND_FILES,
                    {"pattern": "*.py", "path": "."},
                    reasoning="Finding relevant files",
                )

            plan["current_step"] += 1
            return create_action(
                GraceAction.READ_FILE,
                {"path": file_path},
                reasoning=f"Reading {file_path}",
            )

        elif step_action == "run_tests":
            plan["current_step"] += 1
            return create_action(
                GraceAction.RUN_TESTS,
                {"test_path": ".", "test_framework": "auto"},
                reasoning="Running tests",
            )

        elif step_action == "finish":
            return create_action(
                GraceAction.FINISH,
                {"result": "completed", "summary": "Task finished"},
            )

        else:
            # Generic step - use THINK to progress
            plan["current_step"] += 1
            return create_action(
                GraceAction.THINK,
                {"thought": f"Executing step: {current_step.get('description', step_action)}"},
                reasoning=f"Processing step {plan['current_step']}",
            )

    async def _handle_failure(
        self,
        result: ActionResult,
        plan: Dict[str, Any],
    ) -> bool:
        """
        Handle a failed action.

        Returns True if we should continue, False if we should abort.
        """
        logger.warning(f"Action failed: {result.error}")

        # Analyze the failure
        error = result.error or ""

        # Recoverable errors
        if "not found" in error.lower():
            # File/command not found - might be able to continue
            return True
        elif "permission" in error.lower():
            # Permission error - usually can't recover
            return False
        elif "timeout" in error.lower():
            # Timeout - might work with different approach
            return True

        # Default: continue if we haven't failed too many times
        recent_failures = sum(
            1 for _, r in self.action_history[-5:]
            if r.status == ActionStatus.FAILURE
        )
        return recent_failures < 3

    async def _create_summary(self, task: str, result: TaskResult) -> str:
        """Create a summary of the task execution."""
        lines = [
            f"Task: {task[:100]}",
            f"Status: {result.status.value}",
            f"Actions: {result.actions_executed} ({result.actions_succeeded} succeeded, {result.actions_failed} failed)",
        ]

        if result.files_created:
            lines.append(f"Files created: {', '.join(result.files_created[:5])}")
        if result.files_modified:
            lines.append(f"Files modified: {', '.join(result.files_modified[:5])}")

        if result.error:
            lines.append(f"Error: {result.error[:200]}")

        return "\n".join(lines)

    # ==================== Convenience Methods ====================

    async def write_code(
        self,
        file_path: str,
        specification: str,
    ) -> TaskResult:
        """Write code to a file based on specification."""
        return await self.solve_task(
            f"Write code to {file_path}: {specification}",
            context={"target_file": file_path},
        )

    async def fix_bug(
        self,
        description: str,
        file_path: Optional[str] = None,
    ) -> TaskResult:
        """Fix a bug based on description."""
        task = f"Fix bug: {description}"
        if file_path:
            task += f" in {file_path}"
        return await self.solve_task(task)

    async def run_tests(
        self,
        test_path: str = ".",
    ) -> TaskResult:
        """Run tests and report results."""
        return await self.solve_task(f"Run tests in {test_path}")

    async def refactor(
        self,
        file_path: str,
        description: str,
    ) -> TaskResult:
        """Refactor code based on description."""
        return await self.solve_task(
            f"Refactor {file_path}: {description}",
            context={"target_file": file_path},
        )


# Import for type hints
from typing import Tuple
