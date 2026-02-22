"""
Grace Autonomous Engine

Core engine for autonomous task execution:
- Sub-agents management
- Multi-threading and parallel processing
- Background task processing
- Task scheduling and prioritization
- Distributed execution
- Self-healing and recovery
"""

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import heapq
import logging
import traceback
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GraceAutonomousEngine")


# ============================================================================
# Types and Enums
# ============================================================================

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BACKGROUND = "background"
    DISTRIBUTED = "distributed"
    STREAMING = "streaming"


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ExecutionContext:
    """Context passed to task executors"""
    task_id: str
    parent_task_id: Optional[str] = None
    genesis_key_id: Optional[str] = None
    user_id: Optional[str] = None
    memory_context: Dict[str, Any] = field(default_factory=dict)
    execution_params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """Result from task execution"""
    task_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0
    sub_results: List['TaskResult'] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledTask:
    """Task scheduled for future execution"""
    task_id: str
    scheduled_time: datetime
    handler: Callable
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    recurring: bool = False
    interval_seconds: Optional[int] = None

    def __lt__(self, other):
        if self.scheduled_time == other.scheduled_time:
            return self.priority.value < other.priority.value
        return self.scheduled_time < other.scheduled_time


# ============================================================================
# Sub-Agent System
# ============================================================================

class SubAgent:
    """Individual sub-agent for task execution"""

    def __init__(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str] = None,
        max_concurrent: int = 1
    ):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities or []
        self.max_concurrent = max_concurrent
        self.status = AgentStatus.IDLE
        self.current_tasks: Set[str] = set()
        self.task_queue: List[str] = []
        self.completed_count = 0
        self.failed_count = 0
        self.total_processing_time_ms = 0
        self._lock = threading.Lock()

    @property
    def is_available(self) -> bool:
        return len(self.current_tasks) < self.max_concurrent

    @property
    def current_load(self) -> float:
        return len(self.current_tasks) / self.max_concurrent if self.max_concurrent > 0 else 0

    @property
    def success_rate(self) -> float:
        total = self.completed_count + self.failed_count
        return self.completed_count / total if total > 0 else 1.0

    @property
    def avg_processing_time_ms(self) -> float:
        total = self.completed_count + self.failed_count
        return self.total_processing_time_ms / total if total > 0 else 0

    def can_handle(self, task_capabilities: List[str]) -> bool:
        """Check if agent can handle task based on capabilities"""
        if not task_capabilities:
            return True
        return bool(set(task_capabilities) & set(self.capabilities))

    def assign_task(self, task_id: str) -> bool:
        """Assign a task to this agent"""
        with self._lock:
            if not self.is_available:
                self.task_queue.append(task_id)
                return False
            self.current_tasks.add(task_id)
            self.status = AgentStatus.BUSY
            return True

    def complete_task(self, task_id: str, success: bool, duration_ms: int):
        """Mark a task as completed"""
        with self._lock:
            self.current_tasks.discard(task_id)
            if success:
                self.completed_count += 1
            else:
                self.failed_count += 1
            self.total_processing_time_ms += duration_ms

            # Process queued tasks
            if self.task_queue and self.is_available:
                next_task = self.task_queue.pop(0)
                self.current_tasks.add(next_task)
            elif not self.current_tasks:
                self.status = AgentStatus.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "current_load": self.current_load,
            "success_rate": self.success_rate,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "queued_tasks": len(self.task_queue)
        }


class SubAgentPool:
    """Pool of sub-agents for distributed execution"""

    def __init__(self, max_agents: int = 10):
        self.max_agents = max_agents
        self.agents: Dict[str, SubAgent] = {}
        self._lock = threading.Lock()

    def create_agent(
        self,
        name: str,
        capabilities: List[str] = None,
        max_concurrent: int = 1
    ) -> SubAgent:
        """Create a new sub-agent"""
        with self._lock:
            if len(self.agents) >= self.max_agents:
                raise RuntimeError("Maximum agent limit reached")

            agent_id = f"SA-{uuid.uuid4().hex[:8].upper()}"
            agent = SubAgent(agent_id, name, capabilities, max_concurrent)
            self.agents[agent_id] = agent
            logger.info(f"Created sub-agent: {agent_id} ({name})")
            return agent

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        return self.agents.get(agent_id)

    def get_best_agent(self, required_capabilities: List[str] = None) -> Optional[SubAgent]:
        """Get the best available agent for a task"""
        available_agents = [
            a for a in self.agents.values()
            if a.is_available and a.can_handle(required_capabilities or [])
        ]

        if not available_agents:
            return None

        # Sort by load (prefer less loaded) then by success rate
        available_agents.sort(key=lambda a: (a.current_load, -a.success_rate))
        return available_agents[0]

    def get_all_agents(self) -> List[SubAgent]:
        return list(self.agents.values())

    def remove_agent(self, agent_id: str):
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                logger.info(f"Removed sub-agent: {agent_id}")

    def get_stats(self) -> Dict[str, Any]:
        agents = list(self.agents.values())
        return {
            "total_agents": len(agents),
            "idle_agents": len([a for a in agents if a.status == AgentStatus.IDLE]),
            "busy_agents": len([a for a in agents if a.status == AgentStatus.BUSY]),
            "total_completed": sum(a.completed_count for a in agents),
            "total_failed": sum(a.failed_count for a in agents),
            "avg_success_rate": sum(a.success_rate for a in agents) / len(agents) if agents else 0
        }


# ============================================================================
# Task Scheduler
# ============================================================================

class TaskScheduler:
    """Scheduler for delayed and recurring tasks"""

    def __init__(self):
        self._schedule: List[ScheduledTask] = []
        self._schedule_lock = threading.Lock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

    def schedule(
        self,
        task_id: str,
        handler: Callable,
        delay_seconds: float = 0,
        scheduled_time: datetime = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        recurring: bool = False,
        interval_seconds: int = None,
        args: tuple = (),
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Schedule a task for execution"""
        if scheduled_time is None:
            scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)

        scheduled_task = ScheduledTask(
            task_id=task_id,
            scheduled_time=scheduled_time,
            handler=handler,
            priority=priority,
            recurring=recurring,
            interval_seconds=interval_seconds,
            args=args,
            kwargs=kwargs or {}
        )

        with self._schedule_lock:
            heapq.heappush(self._schedule, scheduled_task)

        logger.info(f"Scheduled task {task_id} for {scheduled_time}")
        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        with self._schedule_lock:
            original_len = len(self._schedule)
            self._schedule = [t for t in self._schedule if t.task_id != task_id]
            heapq.heapify(self._schedule)
            return len(self._schedule) < original_len

    def start(self):
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info("Task scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Task scheduler stopped")

    def _run_scheduler(self):
        """Main scheduler loop"""
        while self._running:
            now = datetime.now()

            with self._schedule_lock:
                tasks_to_execute = []

                while self._schedule and self._schedule[0].scheduled_time <= now:
                    task = heapq.heappop(self._schedule)
                    tasks_to_execute.append(task)

                    # Reschedule recurring tasks
                    if task.recurring and task.interval_seconds:
                        new_task = ScheduledTask(
                            task_id=task.task_id,
                            scheduled_time=now + timedelta(seconds=task.interval_seconds),
                            handler=task.handler,
                            args=task.args,
                            kwargs=task.kwargs,
                            priority=task.priority,
                            recurring=True,
                            interval_seconds=task.interval_seconds
                        )
                        heapq.heappush(self._schedule, new_task)

            # Execute tasks outside the lock
            for task in tasks_to_execute:
                try:
                    task.handler(*task.args, **task.kwargs)
                except Exception as e:
                    logger.error(f"Error executing scheduled task {task.task_id}: {e}")

            # Sleep a bit before next check
            asyncio.run(asyncio.sleep(0.1))

    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks"""
        with self._schedule_lock:
            return [
                {
                    "task_id": t.task_id,
                    "scheduled_time": t.scheduled_time.isoformat(),
                    "priority": t.priority.value,
                    "recurring": t.recurring
                }
                for t in self._schedule
            ]


# ============================================================================
# Parallel Executor
# ============================================================================

class ParallelExecutor:
    """Executor for parallel and background task processing"""

    def __init__(self, max_threads: int = 10, max_processes: int = 4):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        self.process_pool = ProcessPoolExecutor(max_workers=max_processes)
        self._active_futures: Dict[str, Any] = {}
        self._results: Dict[str, TaskResult] = {}
        self._lock = threading.Lock()

    def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        handler: Callable,
        timeout: float = None
    ) -> List[TaskResult]:
        """Execute multiple tasks in parallel using threads"""
        futures = {}

        for task in tasks:
            task_id = task.get("task_id", str(uuid.uuid4()))
            future = self.thread_pool.submit(
                self._execute_with_tracking,
                task_id,
                handler,
                task
            )
            futures[task_id] = future
            self._active_futures[task_id] = future

        results = []
        for task_id, future in futures.items():
            try:
                result = future.result(timeout=timeout)
                results.append(result)
            except Exception as e:
                results.append(TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e)
                ))
            finally:
                with self._lock:
                    self._active_futures.pop(task_id, None)

        return results

    def execute_background(
        self,
        task_id: str,
        handler: Callable,
        args: tuple = (),
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Execute a task in background"""
        future = self.thread_pool.submit(
            self._execute_with_tracking,
            task_id,
            handler,
            *(args or ()),
            **(kwargs or {})
        )

        with self._lock:
            self._active_futures[task_id] = future

        return task_id

    def execute_cpu_intensive(
        self,
        task_id: str,
        handler: Callable,
        args: tuple = (),
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Execute CPU-intensive task in process pool"""
        future = self.process_pool.submit(handler, *args, **(kwargs or {}))

        with self._lock:
            self._active_futures[task_id] = future

        return task_id

    def _execute_with_tracking(
        self,
        task_id: str,
        handler: Callable,
        *args,
        **kwargs
    ) -> TaskResult:
        """Execute a task with timing and error tracking"""
        start_time = datetime.now()

        try:
            result_data = handler(*args, **kwargs)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            result = TaskResult(
                task_id=task_id,
                success=True,
                data=result_data,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result = TaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
            logger.error(f"Task {task_id} failed: {e}\n{traceback.format_exc()}")

        with self._lock:
            self._results[task_id] = result

        return result

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a completed task"""
        return self._results.get(task_id)

    def is_complete(self, task_id: str) -> bool:
        """Check if a task is complete"""
        future = self._active_futures.get(task_id)
        if future:
            return future.done()
        return task_id in self._results

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task"""
        future = self._active_futures.get(task_id)
        if future:
            return future.cancel()
        return False

    def get_active_count(self) -> int:
        """Get count of active tasks"""
        return len(self._active_futures)

    def shutdown(self, wait: bool = True):
        """Shutdown the executor"""
        self.thread_pool.shutdown(wait=wait)
        self.process_pool.shutdown(wait=wait)


# ============================================================================
# Main Autonomous Engine
# ============================================================================

class GraceAutonomousEngine:
    """
    Main Grace Autonomous Engine

    Coordinates:
    - Sub-agent pool for distributed execution
    - Task scheduling for delayed/recurring tasks
    - Parallel executor for concurrent processing
    - Priority queue for task ordering
    - Self-healing and recovery
    """

    def __init__(
        self,
        max_agents: int = 10,
        max_threads: int = 10,
        max_processes: int = 4
    ):
        self.agent_pool = SubAgentPool(max_agents)
        self.scheduler = TaskScheduler()
        self.executor = ParallelExecutor(max_threads, max_processes)

        # Task tracking
        self._task_queue: List[tuple] = []  # (priority, task_id, task_data)
        self._active_tasks: Dict[str, Dict] = {}
        self._completed_tasks: Dict[str, TaskResult] = {}
        self._task_handlers: Dict[str, Callable] = {}

        # Metrics
        self._metrics = defaultdict(int)
        self._start_time = datetime.now()

        # State
        self._running = False
        self._lock = threading.Lock()

        logger.info("Grace Autonomous Engine initialized")

    def start(self):
        """Start the autonomous engine"""
        if self._running:
            return

        self._running = True
        self.scheduler.start()

        # Create default agents
        self.agent_pool.create_agent(
            "Main Agent",
            capabilities=["general", "analysis", "execution"],
            max_concurrent=3
        )
        self.agent_pool.create_agent(
            "Learning Agent",
            capabilities=["learning", "memory", "patterns"],
            max_concurrent=2
        )
        self.agent_pool.create_agent(
            "Diagnostic Agent",
            capabilities=["diagnostic", "healing", "monitoring"],
            max_concurrent=2
        )

        logger.info("Grace Autonomous Engine started")

    def stop(self):
        """Stop the autonomous engine"""
        self._running = False
        self.scheduler.stop()
        self.executor.shutdown(wait=True)
        logger.info("Grace Autonomous Engine stopped")

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type"""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    def submit_task(
        self,
        task_id: str,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        required_capabilities: List[str] = None,
        scheduled_time: datetime = None,
        dependencies: List[str] = None
    ) -> str:
        """Submit a task for execution"""
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "data": data,
            "priority": priority,
            "execution_mode": execution_mode,
            "required_capabilities": required_capabilities or [],
            "dependencies": dependencies or [],
            "submitted_at": datetime.now(),
            "status": "queued"
        }

        with self._lock:
            if scheduled_time and scheduled_time > datetime.now():
                # Schedule for later
                self.scheduler.schedule(
                    task_id=task_id,
                    handler=lambda: self._process_task(task_data),
                    scheduled_time=scheduled_time,
                    priority=priority
                )
                task_data["status"] = "scheduled"
            elif dependencies:
                # Check dependencies
                pending_deps = [d for d in dependencies if d not in self._completed_tasks]
                if pending_deps:
                    # Queue with dependencies
                    heapq.heappush(self._task_queue, (priority.value, task_id, task_data))
                    task_data["status"] = "waiting_dependencies"
                else:
                    self._execute_task(task_data)
            else:
                self._execute_task(task_data)

            self._active_tasks[task_id] = task_data
            self._metrics["tasks_submitted"] += 1

        logger.info(f"Submitted task {task_id} ({task_type}) - {task_data['status']}")
        return task_id

    def _execute_task(self, task_data: Dict[str, Any]):
        """Execute a task based on its execution mode"""
        task_id = task_data["task_id"]
        task_type = task_data["task_type"]
        execution_mode = task_data["execution_mode"]

        handler = self._task_handlers.get(task_type, self._default_handler)

        task_data["status"] = "running"
        task_data["started_at"] = datetime.now()

        if execution_mode == ExecutionMode.PARALLEL:
            self.executor.execute_background(task_id, handler, (task_data,))
        elif execution_mode == ExecutionMode.BACKGROUND:
            self.executor.execute_background(task_id, handler, (task_data,))
        elif execution_mode == ExecutionMode.DISTRIBUTED:
            # Find best agent and assign
            agent = self.agent_pool.get_best_agent(task_data.get("required_capabilities"))
            if agent:
                agent.assign_task(task_id)
                task_data["assigned_agent"] = agent.agent_id
            self.executor.execute_background(task_id, handler, (task_data,))
        else:
            # Sequential - run directly
            self._process_task(task_data)

    def _process_task(self, task_data: Dict[str, Any]):
        """Process a single task"""
        task_id = task_data["task_id"]
        task_type = task_data["task_type"]
        start_time = datetime.now()

        try:
            handler = self._task_handlers.get(task_type, self._default_handler)
            result_data = handler(task_data)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result = TaskResult(
                task_id=task_id,
                success=True,
                data=result_data,
                duration_ms=duration_ms
            )

            task_data["status"] = "completed"
            self._metrics["tasks_completed"] += 1

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result = TaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

            task_data["status"] = "failed"
            task_data["error"] = str(e)
            self._metrics["tasks_failed"] += 1
            logger.error(f"Task {task_id} failed: {e}")

        with self._lock:
            self._completed_tasks[task_id] = result
            self._active_tasks.pop(task_id, None)

            # Check for dependent tasks
            self._process_dependency_queue()

            # Update agent if assigned
            if "assigned_agent" in task_data:
                agent = self.agent_pool.get_agent(task_data["assigned_agent"])
                if agent:
                    agent.complete_task(task_id, result.success, result.duration_ms)

        return result

    def _default_handler(self, task_data: Dict[str, Any]) -> Any:
        """Default task handler"""
        logger.info(f"Executing task with default handler: {task_data['task_id']}")
        return {"status": "completed", "data": task_data.get("data")}

    def _process_dependency_queue(self):
        """Process tasks waiting on dependencies"""
        new_queue = []

        for priority, task_id, task_data in self._task_queue:
            pending_deps = [
                d for d in task_data.get("dependencies", [])
                if d not in self._completed_tasks
            ]

            if not pending_deps:
                self._execute_task(task_data)
            else:
                new_queue.append((priority, task_id, task_data))

        self._task_queue = new_queue
        heapq.heapify(self._task_queue)

    def create_sub_task(
        self,
        parent_task_id: str,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = None
    ) -> str:
        """Create a sub-task under a parent task"""
        sub_task_id = f"{parent_task_id}-SUB-{uuid.uuid4().hex[:6].upper()}"

        parent = self._active_tasks.get(parent_task_id)
        if parent and priority is None:
            priority = parent.get("priority", TaskPriority.MEDIUM)

        return self.submit_task(
            task_id=sub_task_id,
            task_type=task_type,
            data=data,
            priority=priority or TaskPriority.MEDIUM,
            execution_mode=ExecutionMode.PARALLEL
        )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        if task_id in self._completed_tasks:
            result = self._completed_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "completed" if result.success else "failed",
                "result": result.data,
                "error": result.error,
                "duration_ms": result.duration_ms
            }
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "tasks_submitted": self._metrics["tasks_submitted"],
            "tasks_completed": self._metrics["tasks_completed"],
            "tasks_failed": self._metrics["tasks_failed"],
            "active_tasks": len(self._active_tasks),
            "queued_tasks": len(self._task_queue),
            "completion_rate": self._metrics["tasks_completed"] / max(1, self._metrics["tasks_submitted"]),
            "agent_stats": self.agent_pool.get_stats(),
            "executor_active": self.executor.get_active_count(),
            "scheduled_tasks": len(self.scheduler.get_scheduled_tasks())
        }

    def scale(self, max_agents: int = None, max_threads: int = None):
        """Scale the engine capacity"""
        if max_agents:
            self.agent_pool.max_agents = max_agents
        if max_threads:
            # Would need to recreate executor for this
            pass
        logger.info(f"Scaled engine: max_agents={max_agents}, max_threads={max_threads}")


# ============================================================================
# Singleton Instance
# ============================================================================

_engine_instance: Optional[GraceAutonomousEngine] = None


def get_autonomous_engine() -> GraceAutonomousEngine:
    """Get or create the singleton autonomous engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = GraceAutonomousEngine()
        _engine_instance.start()
    return _engine_instance
