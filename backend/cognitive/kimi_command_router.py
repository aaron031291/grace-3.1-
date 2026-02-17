"""
Kimi Command Router

Routes Kimi's decisions to the appropriate execution path:
- Direct command execution: Kimi executes commands via the execution bridge
- Coding task delegation: Kimi hands off coding tasks to the coding agent
- Reasoning tasks: Kimi handles directly, results are tracked
- Hybrid tasks: Split between Kimi and coding agent

Architecture:
    User -> Kimi (reasoning/command) -> Command Router
                                         |
                                         |--> Direct Execution (commands, git, shell)
                                         |--> Coding Agent (code writing, refactoring, testing)
                                         |--> Hybrid (Kimi plans, coding agent implements)
                                         |
                                         +--> ALL paths tracked by LLM Interaction Tracker

The router classifies each request and routes it accordingly,
while ensuring every interaction is recorded for learning.
"""

import logging
import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from cognitive.llm_interaction_tracker import (
    LLMInteractionTracker,
    get_llm_interaction_tracker,
)
from models.llm_tracking_models import (
    InteractionType,
    InteractionOutcome,
    TaskDelegationType,
)

logger = logging.getLogger(__name__)


class RouteDecision(str, Enum):
    """Where a task should be routed."""
    KIMI_DIRECT = "kimi_direct"
    CODING_AGENT = "coding_agent"
    HYBRID = "hybrid"
    GRACE_AUTONOMOUS = "grace_autonomous"


@dataclass
class RoutedTask:
    """A task with routing decision."""
    task_id: str
    original_request: str
    route: RouteDecision
    task_type: str
    classification_confidence: float
    reasoning: str

    coding_subtasks: List[Dict[str, Any]] = field(default_factory=list)
    command_subtasks: List[Dict[str, Any]] = field(default_factory=list)

    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionResult:
    """Result of a routed task execution."""
    task_id: str
    route_taken: RouteDecision
    success: bool
    output: str = ""
    error: Optional[str] = None

    coding_results: List[Dict[str, Any]] = field(default_factory=list)
    command_results: List[Dict[str, Any]] = field(default_factory=list)

    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)

    duration_ms: float = 0.0
    interaction_ids: List[str] = field(default_factory=list)

    patterns_matched: List[str] = field(default_factory=list)
    learning_signals: List[Dict[str, Any]] = field(default_factory=list)


class KimiCommandRouter:
    """
    Routes Kimi's tasks to the appropriate executor.

    Kimi acts as the user-facing AI that:
    1. Understands user intent
    2. Classifies the task type
    3. Routes to the right executor:
       - Command execution (Kimi does directly)
       - Coding tasks (hands to coding agent)
       - Hybrid (Kimi plans, coding agent executes)
    4. Tracks everything for learning

    Over time, as patterns accumulate, some tasks can be handled
    by Grace autonomously without needing Kimi at all.
    """

    def __init__(
        self,
        session: Session,
        execution_bridge=None,
        coding_agent=None,
        pattern_learner=None,
    ):
        self.session = session
        self.execution_bridge = execution_bridge
        self.coding_agent = coding_agent
        self.pattern_learner = pattern_learner

        self.tracker = get_llm_interaction_tracker(session)

        self._task_history: List[RoutedTask] = []
        self._routing_stats = {
            "total_routed": 0,
            "kimi_direct": 0,
            "coding_agent": 0,
            "hybrid": 0,
            "grace_autonomous": 0,
        }

        logger.info("[KIMI-ROUTER] Command router initialized")

    def classify_and_route(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
        force_route: Optional[str] = None,
    ) -> RoutedTask:
        """
        Classify a user request and determine where to route it.

        Args:
            user_request: The user's natural language request
            context: Additional context (current files, state, etc.)
            force_route: Override routing decision

        Returns:
            RoutedTask with routing decision and subtasks
        """
        task_id = f"ROUTE-{uuid.uuid4().hex[:12]}"

        if force_route:
            route = RouteDecision(force_route)
            classification_confidence = 1.0
            reasoning = f"Forced route: {force_route}"
            task_type = self._classify_task_type(user_request)
        else:
            route, classification_confidence, reasoning = self._make_routing_decision(
                user_request, context
            )
            task_type = self._classify_task_type(user_request)

        if self.pattern_learner:
            autonomous_possible = self.pattern_learner.can_handle_autonomously(
                user_request, task_type
            )
            if autonomous_possible and classification_confidence > 0.7:
                route = RouteDecision.GRACE_AUTONOMOUS
                reasoning += " | Pattern learner indicates autonomous handling possible"

        routed_task = RoutedTask(
            task_id=task_id,
            original_request=user_request,
            route=route,
            task_type=task_type,
            classification_confidence=classification_confidence,
            reasoning=reasoning,
            context=context or {},
        )

        if route == RouteDecision.CODING_AGENT or route == RouteDecision.HYBRID:
            routed_task.coding_subtasks = self._extract_coding_subtasks(
                user_request, context
            )

        if route == RouteDecision.KIMI_DIRECT or route == RouteDecision.HYBRID:
            routed_task.command_subtasks = self._extract_command_subtasks(
                user_request, context
            )

        self._task_history.append(routed_task)
        self._routing_stats["total_routed"] += 1
        self._routing_stats[route.value] += 1

        logger.info(
            f"[KIMI-ROUTER] Routed task {task_id}: "
            f"route={route.value}, type={task_type}, "
            f"confidence={classification_confidence:.2f}"
        )

        return routed_task

    async def execute_routed_task(
        self,
        routed_task: RoutedTask,
        llm_response: Optional[str] = None,
        llm_reasoning: Optional[List[Dict[str, Any]]] = None,
    ) -> ExecutionResult:
        """
        Execute a routed task through the appropriate path.

        Args:
            routed_task: The task with routing decision
            llm_response: Kimi's response/plan for the task
            llm_reasoning: Kimi's reasoning chain

        Returns:
            ExecutionResult with all outcomes
        """
        start_time = time.time()
        result = ExecutionResult(
            task_id=routed_task.task_id,
            route_taken=routed_task.route,
        )

        interaction = self.tracker.record_interaction(
            prompt=routed_task.original_request,
            response=llm_response or "",
            model_used="kimi",
            interaction_type=self._map_task_type_to_interaction(routed_task.task_type),
            delegation_type=routed_task.route.value,
            reasoning_chain=llm_reasoning,
            confidence_score=routed_task.classification_confidence,
            context_used=routed_task.context,
        )
        result.interaction_ids.append(interaction.interaction_id)

        try:
            if routed_task.route == RouteDecision.KIMI_DIRECT:
                await self._execute_kimi_direct(routed_task, result)

            elif routed_task.route == RouteDecision.CODING_AGENT:
                await self._execute_coding_agent(routed_task, result)

            elif routed_task.route == RouteDecision.HYBRID:
                await self._execute_hybrid(routed_task, result, llm_response)

            elif routed_task.route == RouteDecision.GRACE_AUTONOMOUS:
                await self._execute_autonomous(routed_task, result)

            result.success = not bool(result.error)
            result.duration_ms = (time.time() - start_time) * 1000

            outcome = "success" if result.success else "failure"
            self.tracker.update_interaction_outcome(
                interaction_id=interaction.interaction_id,
                outcome=outcome,
                quality_score=self._assess_quality(result),
            )

        except Exception as e:
            logger.exception(f"[KIMI-ROUTER] Task {routed_task.task_id} failed")
            result.success = False
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

            self.tracker.update_interaction_outcome(
                interaction_id=interaction.interaction_id,
                outcome="failure",
                error_message=str(e),
            )

        logger.info(
            f"[KIMI-ROUTER] Task {routed_task.task_id} completed: "
            f"success={result.success}, duration={result.duration_ms:.0f}ms"
        )

        return result

    async def _execute_kimi_direct(
        self,
        task: RoutedTask,
        result: ExecutionResult,
    ):
        """
        Execute commands directly through Kimi.

        Kimi handles: shell commands, git operations, file reads,
        searches, and other non-coding tasks.
        """
        if not self.execution_bridge:
            result.output = "Execution bridge not available"
            result.error = "No execution bridge configured"
            return

        for subtask in task.command_subtasks:
            cmd_type = subtask.get("type", "bash")
            command = subtask.get("command", "")

            try:
                from execution.actions import create_action, GraceAction

                action_map = {
                    "bash": GraceAction.RUN_BASH,
                    "git_status": GraceAction.GIT_STATUS,
                    "git_diff": GraceAction.GIT_DIFF,
                    "git_add": GraceAction.GIT_ADD,
                    "git_commit": GraceAction.GIT_COMMIT,
                    "read_file": GraceAction.READ_FILE,
                    "search": GraceAction.SEARCH_CODE,
                    "find": GraceAction.FIND_FILES,
                }

                action_type = action_map.get(cmd_type, GraceAction.RUN_BASH)
                action = create_action(
                    action_type,
                    subtask.get("parameters", {"command": command}),
                    reasoning=f"Kimi direct execution: {subtask.get('description', command)}",
                )

                action_result = await self.execution_bridge.execute(action)

                result.command_results.append({
                    "subtask": subtask,
                    "success": action_result.success,
                    "output": action_result.output,
                    "error": action_result.error,
                })

                if action_result.success:
                    result.commands_executed.append(command)
                    result.output += f"\n{action_result.output}"
                else:
                    result.error = action_result.error

            except Exception as e:
                result.command_results.append({
                    "subtask": subtask,
                    "success": False,
                    "error": str(e),
                })
                result.error = str(e)

    async def _execute_coding_agent(
        self,
        task: RoutedTask,
        result: ExecutionResult,
    ):
        """
        Delegate coding task to the coding agent.

        The coding agent handles: code writing, refactoring, testing,
        bug fixing, and other code-centric tasks.
        """
        coding_record = self.tracker.record_coding_task(
            task_description=task.original_request,
            task_type=task.task_type,
            delegated_by="kimi",
            delegated_to="coding_agent",
            files_targeted=task.context.get("files", []),
        )

        if self.coding_agent:
            try:
                agent_result = await self.coding_agent.solve_task(
                    task=task.original_request,
                    context=task.context,
                )

                result.coding_results.append({
                    "task_id": agent_result.task_id,
                    "status": agent_result.status.value,
                    "summary": agent_result.summary,
                    "actions_executed": agent_result.actions_executed,
                    "files_created": agent_result.files_created,
                    "files_modified": agent_result.files_modified,
                })

                result.files_created.extend(agent_result.files_created)
                result.files_modified.extend(agent_result.files_modified)
                result.output = agent_result.summary

                self.tracker.update_coding_task(
                    task_id=coding_record.task_id,
                    outcome="success" if agent_result.status.value == "completed" else "failure",
                    files_created=agent_result.files_created,
                    files_modified=agent_result.files_modified,
                    iterations=agent_result.actions_executed,
                    duration_ms=agent_result.duration_seconds * 1000,
                )

            except Exception as e:
                result.error = str(e)
                self.tracker.update_coding_task(
                    task_id=coding_record.task_id,
                    outcome="failure",
                    error_message=str(e),
                )
        else:
            for subtask in task.coding_subtasks:
                result.coding_results.append({
                    "subtask": subtask,
                    "status": "recorded",
                    "note": "Coding agent not connected; task recorded for tracking",
                })

            self.tracker.update_coding_task(
                task_id=coding_record.task_id,
                outcome="delegated",
                reasoning_used=task.coding_subtasks,
            )

            result.output = (
                f"Coding task recorded for delegation: {task.original_request}\n"
                f"Subtasks: {len(task.coding_subtasks)}"
            )

    async def _execute_hybrid(
        self,
        task: RoutedTask,
        result: ExecutionResult,
        llm_plan: Optional[str] = None,
    ):
        """
        Execute hybrid task: Kimi plans, coding agent implements.

        This is the most common pattern for complex tasks:
        1. Kimi analyzes and creates a plan
        2. Coding agent implements each step
        3. Kimi reviews the result
        """
        if task.command_subtasks:
            await self._execute_kimi_direct(task, result)

        if task.coding_subtasks:
            await self._execute_coding_agent(task, result)

    async def _execute_autonomous(
        self,
        task: RoutedTask,
        result: ExecutionResult,
    ):
        """
        Execute task autonomously using learned patterns.

        This is the goal state: Grace handles the task without
        calling an external LLM, using patterns learned from
        previous Kimi interactions.
        """
        if self.pattern_learner:
            pattern_result = self.pattern_learner.apply_pattern(
                task.original_request,
                task.task_type,
                task.context,
            )

            if pattern_result:
                result.output = pattern_result.get("output", "")
                result.success = pattern_result.get("success", False)
                result.patterns_matched = pattern_result.get("patterns", [])

                result.learning_signals.append({
                    "type": "autonomous_execution",
                    "task_type": task.task_type,
                    "success": result.success,
                    "patterns_used": result.patterns_matched,
                })

                return

        result.output = "No autonomous patterns available for this task type"
        result.error = "Falling back to standard routing"
        result.success = False

    def _make_routing_decision(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
    ) -> Tuple[RouteDecision, float, str]:
        """
        Classify a request and decide where to route it.

        Returns:
            (route_decision, confidence, reasoning)
        """
        request_lower = request.lower()

        coding_indicators = [
            "write code", "implement", "create function", "create class",
            "refactor", "fix bug", "add feature", "modify code",
            "write test", "update the code", "change the implementation",
            "create a new file", "build a", "develop", "code this",
            "write a script", "create an api", "add endpoint",
            "fix the error in", "debug this", "optimize the code",
        ]

        command_indicators = [
            "run", "execute", "install", "deploy", "start",
            "stop", "restart", "check status", "list",
            "show me", "what is", "git status", "git diff",
            "git commit", "git push", "git pull", "npm",
            "pip install", "docker", "kubectl", "ls", "cd",
            "cat", "grep", "find", "mkdir", "rm",
        ]

        reasoning_indicators = [
            "explain", "why", "how does", "what should",
            "analyze", "review", "evaluate", "compare",
            "suggest", "recommend", "plan", "design",
            "think about", "consider", "architecture",
        ]

        hybrid_indicators = [
            "plan and implement", "design and build",
            "analyze and fix", "review and refactor",
            "create a complete", "build the entire",
            "set up", "configure and deploy",
        ]

        coding_score = sum(1 for ind in coding_indicators if ind in request_lower)
        command_score = sum(1 for ind in command_indicators if ind in request_lower)
        reasoning_score = sum(1 for ind in reasoning_indicators if ind in request_lower)
        hybrid_score = sum(1 for ind in hybrid_indicators if ind in request_lower)

        total = coding_score + command_score + reasoning_score + hybrid_score + 1

        if hybrid_score > 0 and (coding_score > 0 or command_score > 0):
            confidence = min(0.9, (hybrid_score + coding_score + command_score) / total)
            return (
                RouteDecision.HYBRID,
                confidence,
                f"Hybrid task detected (coding={coding_score}, command={command_score}, hybrid={hybrid_score})",
            )

        if coding_score > command_score and coding_score > reasoning_score:
            confidence = min(0.9, coding_score / total)
            return (
                RouteDecision.CODING_AGENT,
                confidence,
                f"Coding task detected (score={coding_score})",
            )

        if command_score > coding_score and command_score > reasoning_score:
            confidence = min(0.9, command_score / total)
            return (
                RouteDecision.KIMI_DIRECT,
                confidence,
                f"Command execution detected (score={command_score})",
            )

        if reasoning_score > 0:
            confidence = min(0.9, reasoning_score / total)
            return (
                RouteDecision.KIMI_DIRECT,
                confidence,
                f"Reasoning task detected (score={reasoning_score}), Kimi handles directly",
            )

        return (
            RouteDecision.KIMI_DIRECT,
            0.5,
            "Default routing to Kimi (no strong indicators)",
        )

    def _classify_task_type(self, request: str) -> str:
        """Classify the task type from the request."""
        request_lower = request.lower()

        type_keywords = {
            "bug_fix": ["fix", "bug", "error", "issue", "broken", "crash"],
            "feature": ["add", "create", "implement", "new", "feature", "build"],
            "refactor": ["refactor", "clean", "improve", "optimize", "restructure"],
            "testing": ["test", "spec", "coverage", "assertion"],
            "deployment": ["deploy", "release", "publish", "docker", "k8s"],
            "configuration": ["config", "setup", "install", "environment"],
            "documentation": ["document", "readme", "comment", "explain"],
            "review": ["review", "analyze", "check", "audit"],
            "debugging": ["debug", "trace", "log", "inspect"],
            "architecture": ["architecture", "design", "pattern", "structure"],
        }

        for task_type, keywords in type_keywords.items():
            if any(kw in request_lower for kw in keywords):
                return task_type

        return "general"

    def _extract_coding_subtasks(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract coding subtasks from a request."""
        subtasks = []
        task_type = self._classify_task_type(request)

        subtasks.append({
            "type": task_type,
            "description": request,
            "priority": 1,
            "files": context.get("files", []) if context else [],
        })

        return subtasks

    def _extract_command_subtasks(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract command subtasks from a request."""
        subtasks = []
        request_lower = request.lower()

        if any(kw in request_lower for kw in ["git status", "git diff", "git log"]):
            subtasks.append({
                "type": "git_status",
                "command": "git status",
                "description": "Check git status",
            })

        if any(kw in request_lower for kw in ["run test", "pytest", "npm test"]):
            subtasks.append({
                "type": "bash",
                "command": "pytest -v",
                "description": "Run tests",
            })

        if any(kw in request_lower for kw in ["install", "pip install", "npm install"]):
            subtasks.append({
                "type": "bash",
                "command": request,
                "description": "Install dependencies",
            })

        if not subtasks:
            subtasks.append({
                "type": "bash",
                "command": request,
                "description": f"Execute: {request[:100]}",
            })

        return subtasks

    def _map_task_type_to_interaction(self, task_type: str) -> str:
        """Map task type to InteractionType value."""
        mapping = {
            "bug_fix": "debugging",
            "feature": "coding_task",
            "refactor": "coding_task",
            "testing": "coding_task",
            "deployment": "command_execution",
            "configuration": "command_execution",
            "documentation": "coding_task",
            "review": "code_review",
            "debugging": "debugging",
            "architecture": "architecture",
            "general": "reasoning",
        }
        return mapping.get(task_type, "reasoning")

    def _assess_quality(self, result: ExecutionResult) -> float:
        """Assess the quality of a task execution result."""
        quality = 0.5

        if result.success:
            quality += 0.3
        else:
            quality -= 0.2

        if result.files_created or result.files_modified:
            quality += 0.1

        if result.commands_executed:
            quality += 0.05

        if result.error:
            quality -= 0.15

        return max(0.0, min(1.0, quality))

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        total = self._routing_stats["total_routed"]
        return {
            **self._routing_stats,
            "routing_distribution": {
                k: v / total if total > 0 else 0
                for k, v in self._routing_stats.items()
                if k != "total_routed"
            },
            "recent_tasks": [
                {
                    "task_id": t.task_id,
                    "route": t.route.value,
                    "type": t.task_type,
                    "confidence": t.classification_confidence,
                    "request_preview": t.original_request[:100],
                }
                for t in self._task_history[-10:]
            ],
        }


_router_instance: Optional[KimiCommandRouter] = None


def get_kimi_command_router(
    session: Session,
    execution_bridge=None,
    coding_agent=None,
    pattern_learner=None,
) -> KimiCommandRouter:
    """Get or create the Kimi command router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = KimiCommandRouter(
            session=session,
            execution_bridge=execution_bridge,
            coding_agent=coding_agent,
            pattern_learner=pattern_learner,
        )
    return _router_instance
