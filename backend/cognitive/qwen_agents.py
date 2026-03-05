"""
Qwen Sub-Agent System
========================
Each Qwen model runs as a specialized, independent agent with:
- Background processing (daemon threads)
- Multi-threading (ThreadPoolExecutor per agent)
- Task queue (priority queue with backpressure)
- 9-layer coding pipeline integration (8 original + contract enforcement)
- Structured AI-to-AI communication (no NLP between agents)
- Progress tracking and Genesis key provenance

Agents:
  CodeAgent   (qwen3:32b)  — code generation, structured output, fixes
  ReasonAgent (qwen3:30b)  — deep analysis, architecture, planning
  FastAgent   (qwen3:14b)  — triage, classification, summaries, synthesis

The agents collaborate via structured messages (GraceMessage/GraceResponse),
not NLP. Human-readable text is generated only at the output boundary.
"""

import asyncio
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from queue import PriorityQueue, Empty
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    CODE = "code"
    REASON = "reason"
    FAST = "fast"


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    task_id: str
    prompt: str
    role: AgentRole
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    use_pipeline: bool = False
    execution_allowed: bool = False
    project_folder: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0
    progress: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.priority.value < other.priority.value


class QwenAgent:
    """
    A single Qwen model running as an independent agent.
    Has its own thread pool, task queue, and background worker.
    """

    def __init__(self, role: AgentRole, max_workers: int = 2):
        self.role = role
        self.task_map = {
            AgentRole.CODE: "code",
            AgentRole.REASON: "reason",
            AgentRole.FAST: "fast",
        }
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"qwen-{role.value}",
        )
        self._queue: PriorityQueue = PriorityQueue(maxsize=100)
        self._tasks: Dict[str, AgentTask] = {}
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._stats = {
            "total_tasks": 0, "completed": 0, "failed": 0,
            "total_duration_ms": 0, "avg_duration_ms": 0,
        }

    def start(self):
        """Start the background worker thread."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True,
            name=f"qwen-agent-{self.role.value}",
        )
        self._worker_thread.start()
        logger.info(f"[QwenAgent:{self.role.value}] started")

    def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self._pool.shutdown(wait=False)
        logger.info(f"[QwenAgent:{self.role.value}] stopped")

    def submit(self, task: AgentTask) -> str:
        """Submit a task to this agent's queue. Returns task_id."""
        task.role = self.role
        with self._lock:
            self._tasks[task.task_id] = task
            self._stats["total_tasks"] += 1
        self._queue.put(task)
        logger.info(f"[QwenAgent:{self.role.value}] task queued: {task.task_id}")
        return task.task_id

    def submit_sync(self, task: AgentTask) -> AgentTask:
        """Submit and wait for result. Blocks the caller."""
        task.role = self.role
        with self._lock:
            self._tasks[task.task_id] = task
            self._stats["total_tasks"] += 1
        self._execute_task(task)
        return task

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "role": self.role.value,
                "running": self._running,
                "queue_size": self._queue.qsize(),
                "active_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
                "stats": dict(self._stats),
            }

    def _worker_loop(self):
        """Background worker that processes tasks from the queue."""
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
                future = self._pool.submit(self._execute_task, task)
                future.add_done_callback(lambda f: self._on_task_done(f, task))
            except Empty:
                continue
            except Exception as e:
                logger.error(f"[QwenAgent:{self.role.value}] worker error: {e}")

    def _execute_task(self, task: AgentTask):
        """Execute a single task — runs in thread pool."""
        start = time.time()
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()

        try:
            if task.use_pipeline:
                task.result = self._run_with_pipeline(task)
            else:
                task.result = self._run_direct(task)

            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)[:500]
            logger.error(f"[QwenAgent:{self.role.value}] task {task.task_id} failed: {e}")

        task.completed_at = datetime.now(timezone.utc).isoformat()
        task.duration_ms = round((time.time() - start) * 1000, 1)

        with self._lock:
            if task.status == TaskStatus.COMPLETED:
                self._stats["completed"] += 1
            else:
                self._stats["failed"] += 1
            self._stats["total_duration_ms"] += task.duration_ms
            total = self._stats["completed"] + self._stats["failed"]
            self._stats["avg_duration_ms"] = round(self._stats["total_duration_ms"] / total, 1) if total > 0 else 0

        self._track_genesis(task)

    def _run_direct(self, task: AgentTask) -> Dict[str, Any]:
        """Direct LLM call — fast path, no pipeline overhead."""
        from llm_orchestrator.factory import get_ai_mode_client

        client = get_ai_mode_client(self.task_map[self.role])
        system = task.context.get("system_prompt", "")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": task.prompt})

        response = client.chat(messages=messages, temperature=0.3)
        if isinstance(response, dict):
            text = response.get("message", {}).get("content", "") if "message" in response else response.get("response", str(response))
        else:
            text = str(response)

        return {"response": text, "model": self.task_map[self.role], "method": "direct"}

    def _run_with_pipeline(self, task: AgentTask) -> Dict[str, Any]:
        """Run through the full 9-layer coding pipeline (8 + contract enforcement)."""
        from core.coding_pipeline import get_coding_pipeline

        pipeline = get_coding_pipeline()

        task.progress = {"phase": "pipeline", "layer": 0, "status": "starting"}

        run_id = pipeline.run_background(task.prompt, {
            "project_folder": task.project_folder,
            "execution_allowed": task.execution_allowed,
        })

        task.progress["run_id"] = run_id
        task.progress["phase"] = "running"

        timeout = 300
        start = time.time()
        while time.time() - start < timeout:
            progress = pipeline.progress.get(run_id)
            if progress:
                task.progress.update({
                    "percent": progress.get("percent", 0),
                    "current_layer": progress.get("current_layer", 0),
                    "current_layer_name": progress.get("current_layer_name", ""),
                    "completed_chunks": progress.get("completed_chunks", 0),
                    "total_chunks": progress.get("total_chunks", 0),
                })
                if progress.get("status") in ("passed", "failed", "plan_rejected", "budget_exceeded"):
                    break
            time.sleep(2)

        final = pipeline.progress.get(run_id)

        if not final or final.get("status") not in ("passed", "failed", "plan_rejected", "budget_exceeded"):
            return {"status": "timeout", "run_id": run_id, "progress": task.progress}

        result = {
            "status": final.get("status"),
            "run_id": run_id,
            "pipeline": final,
            "method": "9_layer_pipeline",
        }

        if final.get("status") == "passed" and task.execution_allowed:
            contract_result = self._run_layer_9_contract(task, final)
            result["contract"] = contract_result
            result["method"] = "9_layer_pipeline"

        return result

    def _run_layer_9_contract(self, task: AgentTask, pipeline_result: dict) -> Dict[str, Any]:
        """Layer 9: Contract enforcement on pipeline output."""
        try:
            from core.grace_protocol import (
                GraceMessage, OperationType, OutputMode, route_message,
            )

            msg = GraceMessage(
                operation=OperationType.CODE_REVIEW,
                source=f"qwen_agent.{self.role.value}",
                target="contract_enforcer",
                payload={
                    "pipeline_run_id": pipeline_result.get("run_id", ""),
                    "component": "pipeline_output",
                    "code": str(pipeline_result.get("layers_completed", "")),
                },
                output_mode=OutputMode.AI,
                execution_allowed=task.execution_allowed,
            )
            response = route_message(msg)
            return response.to_dict()
        except Exception as e:
            return {"error": str(e), "stage": "layer_9_contract"}

    def _on_task_done(self, future: Future, task: AgentTask):
        try:
            future.result()
        except Exception as e:
            logger.error(f"[QwenAgent:{self.role.value}] callback error: {e}")

    def _track_genesis(self, task: AgentTask):
        try:
            from api._genesis_tracker import track
            track(
                key_type="agent_task",
                what=f"Agent {self.role.value}: {task.status.value} — {task.prompt[:60]}",
                who=f"qwen_agent.{self.role.value}",
                how="background" if task.use_pipeline else "direct",
                tags=["agent", self.role.value, task.status.value],
            )
        except Exception:
            pass


class QwenAgentPool:
    """
    Manages all 3 Qwen agents. Provides:
    - Parallel multi-agent execution
    - Background task submission
    - Coordinated agent collaboration
    - 9-layer pipeline routing for code tasks
    """

    def __init__(self):
        self.agents = {
            AgentRole.CODE: QwenAgent(AgentRole.CODE, max_workers=2),
            AgentRole.REASON: QwenAgent(AgentRole.REASON, max_workers=2),
            AgentRole.FAST: QwenAgent(AgentRole.FAST, max_workers=2),
        }
        self._coordination_pool = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="agent-coord",
        )
        self._started = False

    def start_all(self):
        """Start all agent background workers."""
        if self._started:
            return
        for agent in self.agents.values():
            agent.start()
        self._started = True
        logger.info("[AgentPool] All 3 Qwen agents started")

    def stop_all(self):
        """Stop all agents."""
        for agent in self.agents.values():
            agent.stop()
        self._coordination_pool.shutdown(wait=False)
        self._started = False

    def submit_background(
        self,
        prompt: str,
        role: AgentRole = AgentRole.CODE,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_pipeline: bool = False,
        execution_allowed: bool = False,
        project_folder: str = "",
        context: Dict[str, Any] = None,
    ) -> str:
        """Submit a task for background processing. Returns task_id immediately."""
        task = AgentTask(
            task_id=f"AGENT-{uuid.uuid4().hex[:8]}",
            prompt=prompt,
            role=role,
            priority=priority,
            use_pipeline=use_pipeline,
            execution_allowed=execution_allowed,
            project_folder=project_folder,
            context=context or {},
        )
        if not self._started:
            self.start_all()
        return self.agents[role].submit(task)

    def run_parallel(
        self,
        prompt: str,
        roles: Optional[List[AgentRole]] = None,
        context: Dict[str, Any] = None,
        timeout: float = 120,
    ) -> Dict[str, Any]:
        """
        Run the prompt across multiple agents in parallel (multi-threaded).
        Returns results from all agents.
        """
        if roles is None:
            roles = [AgentRole.CODE, AgentRole.REASON, AgentRole.FAST]

        futures = {}
        for role in roles:
            task = AgentTask(
                task_id=f"PAR-{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                role=role,
                context=context or {},
            )
            future = self._coordination_pool.submit(
                self.agents[role].submit_sync, task,
            )
            futures[role] = (future, task)

        results = {}
        for role, (future, task) in futures.items():
            try:
                completed_task = future.result(timeout=timeout)
                results[role.value] = {
                    "task_id": completed_task.task_id,
                    "status": completed_task.status.value,
                    "result": completed_task.result,
                    "duration_ms": completed_task.duration_ms,
                }
            except Exception as e:
                results[role.value] = {
                    "task_id": task.task_id,
                    "status": "error",
                    "error": str(e)[:200],
                }

        return results

    def run_pipeline_with_agents(
        self,
        prompt: str,
        execution_allowed: bool = False,
        project_folder: str = "",
    ) -> str:
        """
        Run the 9-layer coding pipeline using the code agent.
        Background processing — returns task_id for progress tracking.
        """
        return self.submit_background(
            prompt=prompt,
            role=AgentRole.CODE,
            priority=TaskPriority.HIGH,
            use_pipeline=True,
            execution_allowed=execution_allowed,
            project_folder=project_folder,
        )

    def run_collaborative(
        self,
        prompt: str,
        context: Dict[str, Any] = None,
        execution_allowed: bool = False,
    ) -> Dict[str, Any]:
        """
        Collaborative multi-agent workflow:
        1. FastAgent triages and classifies
        2. All 3 agents process in parallel (multi-threaded)
        3. ReasonAgent synthesizes results
        4. Contract enforcement on code output
        """
        ctx = context or {}

        triage_task = AgentTask(
            task_id=f"TRIAGE-{uuid.uuid4().hex[:8]}",
            prompt=f"Classify: INTENT|URGENCY|NEEDS_CODE|NEEDS_REASONING\n{prompt[:500]}",
            role=AgentRole.FAST,
            context={"system_prompt": "Respond with exactly: INTENT|URGENCY|NEEDS_CODE(yes/no)|NEEDS_REASONING(yes/no)"},
        )
        triage_result = self.agents[AgentRole.FAST].submit_sync(triage_task)
        triage_text = triage_result.result.get("response", "") if triage_result.result else ""

        parallel_results = self.run_parallel(prompt, context=ctx)

        synthesis_input = ""
        for role_name, res in parallel_results.items():
            if res.get("result", {}).get("response"):
                synthesis_input += f"\n[{role_name.upper()} MODEL]: {res['result']['response'][:1500]}\n"

        if not synthesis_input:
            return {
                "response": "All agents failed to produce output.",
                "triage": triage_text,
                "agent_results": parallel_results,
            }

        synthesis_task = AgentTask(
            task_id=f"SYNTH-{uuid.uuid4().hex[:8]}",
            prompt=(
                f"Synthesize these model outputs into one coherent response.\n"
                f"User question: {prompt}\n{synthesis_input}"
            ),
            role=AgentRole.REASON,
            context={
                "system_prompt": (
                    "Merge the specialized model outputs. Prefer code from CODE model, "
                    "reasoning from REASON model, conciseness from FAST model."
                )
            },
        )
        synthesis_result = self.agents[AgentRole.REASON].submit_sync(synthesis_task)

        code_output = parallel_results.get("code", {}).get("result", {}).get("response", "")
        contract_result = None
        if code_output and execution_allowed:
            try:
                from core.grace_protocol import (
                    GraceMessage, OperationType, OutputMode, route_message,
                )
                msg = GraceMessage(
                    operation=OperationType.CODE_REVIEW,
                    source="agent_pool",
                    target="contract_enforcer",
                    payload={"code": code_output, "component": "collaborative_output"},
                    output_mode=OutputMode.AI,
                )
                contract_result = route_message(msg).to_dict()
            except Exception:
                pass

        return {
            "response": synthesis_result.result.get("response", "") if synthesis_result.result else "",
            "triage": triage_text,
            "agent_results": {
                k: {"status": v.get("status"), "duration_ms": v.get("duration_ms")}
                for k, v in parallel_results.items()
            },
            "contract": contract_result,
            "timing": {
                "triage_ms": triage_result.duration_ms,
                "parallel_ms": max(
                    r.get("duration_ms", 0) for r in parallel_results.values()
                ),
                "synthesis_ms": synthesis_result.duration_ms,
            },
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID (searches all agents)."""
        for agent in self.agents.values():
            task = agent.get_task(task_id)
            if task:
                return {
                    "task_id": task.task_id,
                    "role": task.role.value,
                    "status": task.status.value,
                    "progress": task.progress,
                    "result": task.result if task.status == TaskStatus.COMPLETED else None,
                    "error": task.error,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "duration_ms": task.duration_ms,
                }
        return None

    def get_pool_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        return {
            "started": self._started,
            "agents": {
                role.value: agent.get_status()
                for role, agent in self.agents.items()
            },
        }


_pool: Optional[QwenAgentPool] = None


def get_agent_pool() -> QwenAgentPool:
    """Get singleton agent pool."""
    global _pool
    if _pool is None:
        _pool = QwenAgentPool()
    return _pool
