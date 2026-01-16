"""
Autonomous Task Scheduler for Grace OS
========================================

Enables Grace to:
1. Schedule and execute tasks autonomously
2. Manage up to 10 parallel background jobs
3. Process voice and NLP commands
4. Notify users of progress ("Hey Omar, I'm adding self-updater module – hold tight")
5. Learn from task outcomes
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid
import threading
from collections import deque

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """Task priority levels."""
    CRITICAL = 0   # Immediate execution
    HIGH = 1       # Execute ASAP
    NORMAL = 2     # Standard priority
    LOW = 3        # Background/batch
    IDLE = 4       # Only when nothing else


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of autonomous tasks."""
    CODE_GENERATION = "code_generation"
    HEALING = "healing"
    REFACTOR = "refactor"
    TEST = "test"
    BUILD = "build"
    DEPLOY = "deploy"
    RESEARCH = "research"
    LEARNING = "learning"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


@dataclass
class ScheduledTask:
    """A task scheduled for autonomous execution."""
    task_id: str
    task_type: TaskType
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    genesis_key_id: Optional[str] = None

    # Execution details
    handler: Optional[str] = None  # Handler function name
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_contract_id: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 600  # 10 minutes default

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 - 1.0
    progress_message: str = ""

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # Notifications
    notify_on_complete: bool = True
    notify_on_error: bool = True
    notification_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "genesis_key_id": self.genesis_key_id,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error": self.error
        }


@dataclass
class TaskNotification:
    """A notification about task status."""
    notification_id: str
    task_id: str
    message: str
    notification_type: str  # info, warning, error, success
    timestamp: datetime = field(default_factory=datetime.utcnow)
    read: bool = False
    voice_message: Optional[str] = None  # TTS-friendly version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "task_id": self.task_id,
            "message": self.message,
            "type": self.notification_type,
            "timestamp": self.timestamp.isoformat(),
            "read": self.read,
            "voice_message": self.voice_message
        }


class AutonomousTaskScheduler:
    """
    Autonomous task scheduler with parallel execution.

    Features:
    - Up to 10 concurrent background jobs
    - Priority-based scheduling
    - Voice/NLP command integration
    - Progress notifications
    - Learning from outcomes
    """

    MAX_CONCURRENT_JOBS = 10

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None,
        enable_voice_notifications: bool = True
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.enable_voice_notifications = enable_voice_notifications

        # Task queues
        self.pending_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks: deque = deque(maxlen=100)  # Keep last 100

        # Execution
        self._task_handlers: Dict[str, Callable] = {}
        self._running_futures: Dict[str, asyncio.Task] = {}
        self._is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Notifications
        self.notifications: deque = deque(maxlen=50)
        self._notification_handlers: List[Callable] = []

        # Metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }

        # Register default handlers
        self._register_default_handlers()

        logger.info("[SCHEDULER] Autonomous task scheduler initialized")

    def _register_default_handlers(self):
        """Register default task handlers."""

        async def handle_code_generation(task: ScheduledTask) -> Dict[str, Any]:
            from grace_os.deterministic_pipeline import DeterministicCodePipeline, ExecutionContract
            pipeline = DeterministicCodePipeline(self.session, self.repo_path)
            await pipeline.initialize()

            contract = ExecutionContract(
                goal=task.description,
                allowed_files=task.parameters.get("files", ["*"]),
                constraints=task.parameters.get("constraints", {}),
                risk_level=task.parameters.get("risk_level", "low")
            )

            result = await pipeline.execute(contract)
            return result.to_dict()

        async def handle_healing(task: ScheduledTask) -> Dict[str, Any]:
            from cognitive.autonomous_healing_system import AutonomousHealingSystem
            healer = AutonomousHealingSystem(self.session, self.repo_path)
            assessment = healer.assess_system_health()
            return assessment

        async def handle_test(task: ScheduledTask) -> Dict[str, Any]:
            import subprocess
            test_path = task.parameters.get("path", ".")
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }

        async def handle_research(task: ScheduledTask) -> Dict[str, Any]:
            from grace_os.reasoning_planes import MultiPlaneReasoner
            reasoner = MultiPlaneReasoner(self.session, self.repo_path)
            await reasoner.initialize()

            result = await reasoner.reason(
                query=task.description,
                target_path=task.parameters.get("target")
            )
            return result

        async def handle_learning(task: ScheduledTask) -> Dict[str, Any]:
            from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator
            orchestrator = ContinuousLearningOrchestrator(self.session)
            # Trigger a learning cycle
            result = await orchestrator.run_learning_cycle()
            return result

        self.register_handler(TaskType.CODE_GENERATION, handle_code_generation)
        self.register_handler(TaskType.HEALING, handle_healing)
        self.register_handler(TaskType.TEST, handle_test)
        self.register_handler(TaskType.RESEARCH, handle_research)
        self.register_handler(TaskType.LEARNING, handle_learning)

    def register_handler(self, task_type: TaskType, handler: Callable):
        """Register a handler for a task type."""
        self._task_handlers[task_type.value] = handler

    def register_notification_handler(self, handler: Callable):
        """Register a handler for notifications (e.g., voice output)."""
        self._notification_handlers.append(handler)

    # =========================================================================
    # Task Management
    # =========================================================================

    def schedule_task(
        self,
        task_type: TaskType,
        description: str,
        parameters: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_for: Optional[datetime] = None,
        depends_on: List[str] = None,
        timeout_seconds: int = 600,
        notify: bool = True,
        notification_message: Optional[str] = None
    ) -> ScheduledTask:
        """
        Schedule a task for autonomous execution.

        Args:
            task_type: Type of task
            description: What the task does
            parameters: Task parameters
            priority: Execution priority
            scheduled_for: When to execute (None = ASAP)
            depends_on: Task IDs this depends on
            timeout_seconds: Max execution time
            notify: Whether to notify on completion
            notification_message: Custom notification message

        Returns:
            The scheduled task
        """
        task = ScheduledTask(
            task_id=f"TASK-{uuid.uuid4().hex[:12]}",
            task_type=task_type,
            description=description,
            priority=priority,
            parameters=parameters or {},
            scheduled_for=scheduled_for or datetime.utcnow(),
            depends_on=depends_on or [],
            timeout_seconds=timeout_seconds,
            notify_on_complete=notify,
            notification_message=notification_message
        )

        # Create Genesis Key for task
        try:
            from genesis.genesis_key_service import GenesisKeyService
            from models.genesis_key_models import GenesisKeyType

            genesis_service = GenesisKeyService(self.session, str(self.repo_path))
            genesis_key = genesis_service.create_key(
                key_type=GenesisKeyType.TASK_STARTED,
                what_description=f"Scheduled task: {description[:100]}",
                who_actor="AutonomousScheduler",
                why_reason=f"Task type: {task_type.value}",
                how_method="Autonomous scheduling",
                context_data={"task_id": task.task_id, "parameters": parameters},
                session=self.session
            )
            task.genesis_key_id = genesis_key.key_id
        except Exception as e:
            logger.warning(f"[SCHEDULER] Could not create genesis key: {e}")

        self.pending_tasks[task.task_id] = task
        task.status = TaskStatus.QUEUED

        logger.info(f"[SCHEDULER] Scheduled task {task.task_id}: {description[:50]}...")

        # Notify about scheduling
        self._create_notification(
            task.task_id,
            f"Task scheduled: {description[:50]}...",
            "info",
            voice_message=f"I'm scheduling a new task: {description[:50]}"
        )

        return task

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task."""
        if task_id in self.pending_tasks:
            task = self.pending_tasks.pop(task_id)
            task.status = TaskStatus.CANCELLED
            self.completed_tasks.append(task)
            return True

        if task_id in self.running_tasks:
            # Cancel the running future
            if task_id in self._running_futures:
                self._running_futures[task_id].cancel()
                del self._running_futures[task_id]

            task = self.running_tasks.pop(task_id)
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            self.completed_tasks.append(task)

            self._create_notification(
                task_id,
                f"Task cancelled: {task.description[:50]}...",
                "warning"
            )
            return True

        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        if task_id in self.pending_tasks:
            return self.pending_tasks[task_id]
        if task_id in self.running_tasks:
            return self.running_tasks[task_id]
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tasks grouped by status."""
        return {
            "pending": [t.to_dict() for t in self.pending_tasks.values()],
            "running": [t.to_dict() for t in self.running_tasks.values()],
            "completed": [t.to_dict() for t in self.completed_tasks]
        }

    # =========================================================================
    # Execution Engine
    # =========================================================================

    async def start(self):
        """Start the scheduler."""
        if self._is_running:
            return

        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("[SCHEDULER] Scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self._is_running = False

        # Cancel all running tasks
        for task_id in list(self._running_futures.keys()):
            self._running_futures[task_id].cancel()

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("[SCHEDULER] Scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._is_running:
            try:
                # Check for tasks ready to run
                await self._dispatch_ready_tasks()

                # Clean up completed futures
                self._cleanup_futures()

                # Wait before next check
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SCHEDULER] Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _dispatch_ready_tasks(self):
        """Dispatch tasks that are ready to run."""
        now = datetime.utcnow()

        # Sort pending tasks by priority
        ready_tasks = sorted(
            [
                t for t in self.pending_tasks.values()
                if t.status == TaskStatus.QUEUED
                and (t.scheduled_for is None or t.scheduled_for <= now)
                and self._dependencies_met(t)
            ],
            key=lambda t: t.priority.value
        )

        # Dispatch up to max concurrent
        available_slots = self.MAX_CONCURRENT_JOBS - len(self.running_tasks)

        for task in ready_tasks[:available_slots]:
            await self._execute_task(task)

    def _dependencies_met(self, task: ScheduledTask) -> bool:
        """Check if all dependencies are completed."""
        for dep_id in task.depends_on:
            dep_task = self.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def _execute_task(self, task: ScheduledTask):
        """Execute a task."""
        # Move to running
        del self.pending_tasks[task.task_id]
        self.running_tasks[task.task_id] = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()

        # Get handler
        handler = self._task_handlers.get(task.task_type.value)

        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.task_type.value}"
            task.completed_at = datetime.utcnow()
            del self.running_tasks[task.task_id]
            self.completed_tasks.append(task)
            return

        # Create async task
        async def run_with_timeout():
            try:
                return await asyncio.wait_for(
                    handler(task),
                    timeout=task.timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task timed out after {task.timeout_seconds}s")

        future = asyncio.create_task(run_with_timeout())
        self._running_futures[task.task_id] = future

        # Handle completion
        future.add_done_callback(
            lambda f: asyncio.create_task(self._on_task_complete(task.task_id, f))
        )

        # Notify start
        voice_msg = task.notification_message or f"I'm starting work on: {task.description[:50]}"
        self._create_notification(
            task.task_id,
            f"Task started: {task.description[:50]}...",
            "info",
            voice_message=voice_msg
        )

    async def _on_task_complete(self, task_id: str, future: asyncio.Task):
        """Handle task completion."""
        if task_id not in self.running_tasks:
            return

        task = self.running_tasks.pop(task_id)
        task.completed_at = datetime.utcnow()

        try:
            result = future.result()
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.progress = 1.0

            # Update metrics
            self.metrics["tasks_completed"] += 1
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.metrics["total_execution_time"] += execution_time
            self.metrics["average_execution_time"] = (
                self.metrics["total_execution_time"] / self.metrics["tasks_completed"]
            )

            # Notify success
            if task.notify_on_complete:
                voice_msg = f"Done! {task.description[:30]} completed successfully."
                self._create_notification(
                    task_id,
                    f"Task completed: {task.description[:50]}...",
                    "success",
                    voice_message=voice_msg
                )

            # Update genesis key
            self._update_genesis_key(task, success=True)

            # Store success in learning memory
            await self._store_task_outcome(task, success=True)

        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.metrics["tasks_failed"] += 1

            # Notify failure
            if task.notify_on_error:
                voice_msg = f"Unfortunately, the task {task.description[:30]} ran into an issue: {str(e)[:50]}"
                self._create_notification(
                    task_id,
                    f"Task failed: {task.description[:50]}... Error: {str(e)}",
                    "error",
                    voice_message=voice_msg
                )

            # Update genesis key
            self._update_genesis_key(task, success=False, error=str(e))

            # Store failure in learning memory (for VectorDB)
            await self._store_task_outcome(task, success=False)

        finally:
            self.completed_tasks.append(task)
            if task_id in self._running_futures:
                del self._running_futures[task_id]

    def _cleanup_futures(self):
        """Clean up completed futures."""
        to_remove = []
        for task_id, future in self._running_futures.items():
            if future.done():
                to_remove.append(task_id)

        for task_id in to_remove:
            if task_id in self._running_futures:
                del self._running_futures[task_id]

    def _update_genesis_key(self, task: ScheduledTask, success: bool, error: str = None):
        """Update genesis key with task outcome."""
        if not task.genesis_key_id:
            return

        try:
            from genesis.genesis_key_service import GenesisKeyService
            from models.genesis_key_models import GenesisKeyType

            genesis_service = GenesisKeyService(self.session, str(self.repo_path))
            genesis_service.create_key(
                key_type=GenesisKeyType.TASK_COMPLETED if success else GenesisKeyType.ERROR_DETECTED,
                what_description=f"Task {'completed' if success else 'failed'}: {task.description[:80]}",
                who_actor="AutonomousScheduler",
                why_reason="Task execution completed",
                how_method="Autonomous execution",
                is_error=not success,
                error_message=error,
                parent_key_id=task.genesis_key_id,
                context_data={
                    "task_id": task.task_id,
                    "result": task.result if success else None,
                    "execution_time": (task.completed_at - task.started_at).total_seconds() if task.started_at else 0
                },
                session=self.session
            )
        except Exception as e:
            logger.warning(f"[SCHEDULER] Could not update genesis key: {e}")

    async def _store_task_outcome(self, task: ScheduledTask, success: bool):
        """Store task outcome in VectorDB for learning."""
        try:
            # Store in VectorDB for learning from failures
            from vector_db.qdrant_client import QdrantClient
            from embedding.embedder import get_embedder

            embedder = get_embedder()
            client = QdrantClient()

            # Create embedding from task description and outcome
            text = f"Task: {task.description}\nType: {task.task_type.value}\nOutcome: {'success' if success else 'failure'}"
            if task.error:
                text += f"\nError: {task.error}"

            embedding = await embedder.embed(text)

            # Store in appropriate collection
            collection = "task_successes" if success else "task_failures"

            await client.upsert(
                collection_name=collection,
                points=[{
                    "id": task.task_id,
                    "vector": embedding,
                    "payload": {
                        "task_type": task.task_type.value,
                        "description": task.description,
                        "parameters": task.parameters,
                        "error": task.error,
                        "genesis_key_id": task.genesis_key_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }]
            )

            logger.debug(f"[SCHEDULER] Stored task outcome in VectorDB: {task.task_id}")

        except Exception as e:
            logger.warning(f"[SCHEDULER] Could not store task outcome: {e}")

    # =========================================================================
    # Notifications
    # =========================================================================

    def _create_notification(
        self,
        task_id: str,
        message: str,
        notification_type: str,
        voice_message: str = None
    ):
        """Create a notification."""
        notification = TaskNotification(
            notification_id=f"NOTIF-{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            message=message,
            notification_type=notification_type,
            voice_message=voice_message or message
        )

        self.notifications.append(notification)

        # Call notification handlers
        for handler in self._notification_handlers:
            try:
                handler(notification)
            except Exception as e:
                logger.warning(f"[SCHEDULER] Notification handler error: {e}")

        # Voice notification
        if self.enable_voice_notifications and voice_message:
            asyncio.create_task(self._speak_notification(voice_message))

    async def _speak_notification(self, message: str):
        """Speak a notification via TTS."""
        try:
            from api.voice_api import text_to_speech
            await text_to_speech(message)
        except Exception as e:
            logger.debug(f"[SCHEDULER] Could not speak notification: {e}")

    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications."""
        if unread_only:
            return [n.to_dict() for n in self.notifications if not n.read]
        return [n.to_dict() for n in self.notifications]

    def mark_notification_read(self, notification_id: str):
        """Mark a notification as read."""
        for notification in self.notifications:
            if notification.notification_id == notification_id:
                notification.read = True
                break

    # =========================================================================
    # Voice/NLP Integration
    # =========================================================================

    async def process_voice_command(self, transcript: str) -> Dict[str, Any]:
        """Process a voice command and schedule appropriate task."""
        transcript_lower = transcript.lower()

        # Parse intent
        if any(kw in transcript_lower for kw in ["heal", "fix", "repair"]):
            task = self.schedule_task(
                task_type=TaskType.HEALING,
                description=f"Heal issues: {transcript}",
                priority=TaskPriority.HIGH,
                notification_message=f"Got it! I'll fix those issues for you."
            )
            return {"scheduled": True, "task": task.to_dict()}

        elif any(kw in transcript_lower for kw in ["test", "run tests", "check"]):
            task = self.schedule_task(
                task_type=TaskType.TEST,
                description=f"Run tests: {transcript}",
                priority=TaskPriority.NORMAL,
                notification_message=f"Running the tests now."
            )
            return {"scheduled": True, "task": task.to_dict()}

        elif any(kw in transcript_lower for kw in ["create", "add", "make", "generate"]):
            task = self.schedule_task(
                task_type=TaskType.CODE_GENERATION,
                description=transcript,
                priority=TaskPriority.NORMAL,
                notification_message=f"I'm working on creating that for you."
            )
            return {"scheduled": True, "task": task.to_dict()}

        elif any(kw in transcript_lower for kw in ["research", "find out", "investigate"]):
            task = self.schedule_task(
                task_type=TaskType.RESEARCH,
                description=transcript,
                priority=TaskPriority.LOW,
                notification_message=f"I'll research that and get back to you."
            )
            return {"scheduled": True, "task": task.to_dict()}

        else:
            return {
                "scheduled": False,
                "message": "I'm not sure what you want me to do. Try saying things like 'heal the code' or 'run the tests'."
            }

    async def natural_language_schedule(
        self,
        description: str,
        urgency: str = "normal"
    ) -> ScheduledTask:
        """Schedule a task from natural language description."""
        # Determine task type from description
        description_lower = description.lower()

        if any(kw in description_lower for kw in ["fix", "heal", "repair", "bug"]):
            task_type = TaskType.HEALING
        elif any(kw in description_lower for kw in ["test", "verify", "check"]):
            task_type = TaskType.TEST
        elif any(kw in description_lower for kw in ["refactor", "clean", "improve"]):
            task_type = TaskType.REFACTOR
        elif any(kw in description_lower for kw in ["build", "compile"]):
            task_type = TaskType.BUILD
        elif any(kw in description_lower for kw in ["deploy", "release"]):
            task_type = TaskType.DEPLOY
        elif any(kw in description_lower for kw in ["learn", "teach", "train"]):
            task_type = TaskType.LEARNING
        elif any(kw in description_lower for kw in ["create", "add", "generate", "make"]):
            task_type = TaskType.CODE_GENERATION
        else:
            task_type = TaskType.CUSTOM

        # Determine priority
        priority_map = {
            "urgent": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "normal": TaskPriority.NORMAL,
            "low": TaskPriority.LOW
        }
        priority = priority_map.get(urgency.lower(), TaskPriority.NORMAL)

        return self.schedule_task(
            task_type=task_type,
            description=description,
            priority=priority,
            notification_message=f"I'm on it! Working on: {description[:50]}"
        )

    # =========================================================================
    # Metrics & Status
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "is_running": self._is_running,
            "pending_tasks": len(self.pending_tasks),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "available_slots": self.MAX_CONCURRENT_JOBS - len(self.running_tasks),
            "metrics": self.metrics,
            "notifications": len([n for n in self.notifications if not n.read])
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics."""
        return {
            **self.metrics,
            "task_type_distribution": self._get_task_type_distribution(),
            "average_wait_time": self._calculate_average_wait_time(),
            "success_rate": self._calculate_success_rate()
        }

    def _get_task_type_distribution(self) -> Dict[str, int]:
        """Get distribution of task types."""
        distribution = {}
        for task in list(self.completed_tasks) + list(self.running_tasks.values()):
            t = task.task_type.value
            distribution[t] = distribution.get(t, 0) + 1
        return distribution

    def _calculate_average_wait_time(self) -> float:
        """Calculate average wait time from queue to start."""
        wait_times = []
        for task in self.completed_tasks:
            if task.started_at and task.created_at:
                wait_time = (task.started_at - task.created_at).total_seconds()
                wait_times.append(wait_time)

        return sum(wait_times) / len(wait_times) if wait_times else 0.0

    def _calculate_success_rate(self) -> float:
        """Calculate task success rate."""
        completed = self.metrics["tasks_completed"]
        failed = self.metrics["tasks_failed"]
        total = completed + failed

        return completed / total if total > 0 else 1.0
