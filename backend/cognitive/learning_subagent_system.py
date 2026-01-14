"""
Multi-Process Learning Subagent System

Complete autonomous learning architecture running as independent processes.

Architecture:
- Master Process: Orchestrates learning subagents
- Study Subagents: Autonomous concept extraction (multi-process)
- Practice Subagents: Skill execution and validation (multi-process)
- Mirror Subagent: Self-reflection and gap identification (dedicated process)
- Trust Scorer Subagent: Continuous trust score updates (dedicated process)
- Predictive Context Subagent: Pre-fetching and caching (dedicated process)

All subagents run independently in background with IPC via queues.
"""

import multiprocessing as mp
from multiprocessing import Process, Queue, Value, Manager, Lock
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import signal
import sys
from enum import Enum

from sqlalchemy.orm import Session
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


# ======================================================================
# Task and Message Types
# ======================================================================

class TaskType(Enum):
    """Types of learning tasks."""
    INGEST = "ingest"
    STUDY = "study"
    PRACTICE = "practice"
    REFLECT = "reflect"
    UPDATE_TRUST = "update_trust"
    PREFETCH = "prefetch"


class MessageType(Enum):
    """IPC message types."""
    TASK = "task"
    RESULT = "result"
    STATUS = "status"
    SHUTDOWN = "shutdown"
    HEARTBEAT = "heartbeat"


@dataclass
class LearningTask:
    """Learning task that can be serialized across processes."""
    task_id: str
    task_type: TaskType
    priority: int = 5
    created_at: float = 0.0

    # Task-specific data
    file_path: Optional[str] = None
    topic: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    skill_name: Optional[str] = None
    task_description: Optional[str] = None
    complexity: float = 0.5

    # Tracking
    status: str = "pending"
    assigned_to: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self):
        """Convert to dictionary for IPC."""
        d = asdict(self)
        d['task_type'] = self.task_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary."""
        data['task_type'] = TaskType(data['task_type'])
        return cls(**data)


@dataclass
class Message:
    """IPC message between processes."""
    msg_type: MessageType
    sender: str
    timestamp: float
    data: Dict[str, Any]

    def to_dict(self):
        d = asdict(self)
        d['msg_type'] = self.msg_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict):
        data['msg_type'] = MessageType(data['msg_type'])
        return cls(**data)


# ======================================================================
# Base Subagent (runs in separate process)
# ======================================================================

class BaseSubagent:
    """
    Base class for all learning subagents.

    Each subagent runs in its own process with:
    - Input queue for tasks
    - Output queue for results
    - Shared state for coordination
    - Independent execution loop
    """

    def __init__(
        self,
        agent_id: str,
        task_queue: Queue,
        result_queue: Queue,
        shared_state: Dict,
        knowledge_base_path: str
    ):
        self.agent_id = agent_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.shared_state = shared_state
        self.knowledge_base_path = Path(knowledge_base_path)

        self.is_running = Value('b', False)
        self.tasks_processed = Value('i', 0)
        self.tasks_failed = Value('i', 0)

        # Process handle
        self.process: Optional[Process] = None

    def start(self):
        """Start subagent in separate process."""
        self.process = Process(
            target=self._run,
            name=f"Subagent-{self.agent_id}",
            daemon=True
        )
        self.process.start()
        logger.info(f"[{self.agent_id}] Subagent started (PID: {self.process.pid})")

    def stop(self, timeout: int = 10):
        """Stop subagent gracefully."""
        if self.process and self.process.is_alive():
            # Send shutdown signal
            self.task_queue.put(Message(
                msg_type=MessageType.SHUTDOWN,
                sender="master",
                timestamp=time.time(),
                data={}
            ).to_dict())

            # Wait for graceful shutdown
            self.process.join(timeout=timeout)

            if self.process.is_alive():
                logger.warning(f"[{self.agent_id}] Force terminating...")
                self.process.terminate()
                self.process.join(timeout=2)

        logger.info(f"[{self.agent_id}] Subagent stopped")

    def _run(self):
        """Main execution loop (runs in separate process)."""
        self.is_running.value = True
        logger.info(f"[{self.agent_id}] Execution loop started")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            self._initialize()

            while self.is_running.value:
                try:
                    # Get task from queue (with timeout)
                    msg_dict = self.task_queue.get(timeout=5)
                    msg = Message.from_dict(msg_dict)

                    if msg.msg_type == MessageType.SHUTDOWN:
                        logger.info(f"[{self.agent_id}] Shutdown signal received")
                        break

                    elif msg.msg_type == MessageType.TASK:
                        task = LearningTask.from_dict(msg.data)
                        self._process_task(task)

                except mp.queues.Empty:
                    # No tasks, send heartbeat
                    self._send_heartbeat()
                    continue

                except Exception as e:
                    logger.error(f"[{self.agent_id}] Error in loop: {e}")
                    import traceback
                    traceback.print_exc()

        finally:
            self._cleanup()
            self.is_running.value = False
            logger.info(f"[{self.agent_id}] Execution loop ended")

    def _initialize(self):
        """Initialize resources (override in subclass)."""
        pass

    def _cleanup(self):
        """Cleanup resources (override in subclass)."""
        pass

    def _process_task(self, task: LearningTask):
        """Process a task (override in subclass)."""
        raise NotImplementedError

    def _send_result(self, task: LearningTask):
        """Send task result back to master."""
        self.result_queue.put(Message(
            msg_type=MessageType.RESULT,
            sender=self.agent_id,
            timestamp=time.time(),
            data=task.to_dict()
        ).to_dict())

    def _send_heartbeat(self):
        """Send heartbeat to master."""
        self.result_queue.put(Message(
            msg_type=MessageType.HEARTBEAT,
            sender=self.agent_id,
            timestamp=time.time(),
            data={
                "tasks_processed": self.tasks_processed.value,
                "tasks_failed": self.tasks_failed.value,
                "is_running": self.is_running.value
            }
        ).to_dict())

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"[{self.agent_id}] Signal {signum} received")
        self.is_running.value = False


# ======================================================================
# Study Subagent (extracts concepts from training materials)
# ======================================================================

class StudySubagent(BaseSubagent):
    """
    Autonomous study subagent.

    Runs independently to:
    - Extract concepts from training materials
    - Store in Layer 1 with trust scores
    - Identify focus areas
    """

    def _initialize(self):
        """Initialize database and retriever."""
        from database.session import get_session_factory
        from embedding import get_embedding_model
        from retrieval.retriever import DocumentRetriever
        from cognitive.active_learning_system import GraceActiveLearningSystem

        self.session_factory = get_session_factory()
        self.embedding_model = get_embedding_model()
        self.retriever = DocumentRetriever(
            collection_name="documents",
            embedding_model=self.embedding_model
        )

        logger.info(f"[{self.agent_id}] Study subagent initialized")

    def _process_task(self, task: LearningTask):
        """Process study task."""
        if task.task_type != TaskType.STUDY:
            task.error = f"Invalid task type: {task.task_type}"
            task.status = "failed"
            self.tasks_failed.value += 1
            self._send_result(task)
            return

        task.status = "processing"
        task.assigned_to = self.agent_id
        task.started_at = time.time()

        session = self.session_factory()

        try:
            from cognitive.active_learning_system import GraceActiveLearningSystem

            learning_system = GraceActiveLearningSystem(
                session=session,
                retriever=self.retriever,
                knowledge_base_path=self.knowledge_base_path
            )

            result = learning_system.study_topic(
                topic=task.topic,
                learning_objectives=task.learning_objectives or [],
                max_materials=10
            )

            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            self.tasks_processed.value += 1

            logger.info(
                f"[{self.agent_id}] Studied '{task.topic}': "
                f"{result.get('concepts_learned', 0)} concepts in "
                f"{task.completed_at - task.started_at:.1f}s"
            )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed.value += 1
            logger.error(f"[{self.agent_id}] Study failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            session.close()
            self._send_result(task)


# ======================================================================
# Practice Subagent (executes skills in sandbox)
# ======================================================================

class PracticeSubagent(BaseSubagent):
    """
    Autonomous practice subagent.

    Runs independently to:
    - Execute skill tasks in sandbox
    - Observe outcomes
    - Update operational confidence
    """

    def _initialize(self):
        """Initialize practice environment."""
        from database.session import get_session_factory
        from embedding import get_embedding_model
        from retrieval.retriever import DocumentRetriever

        self.session_factory = get_session_factory()
        self.embedding_model = get_embedding_model()
        self.retriever = DocumentRetriever(
            collection_name="documents",
            embedding_model=self.embedding_model
        )

        logger.info(f"[{self.agent_id}] Practice subagent initialized")

    def _process_task(self, task: LearningTask):
        """Process practice task."""
        if task.task_type != TaskType.PRACTICE:
            task.error = f"Invalid task type: {task.task_type}"
            task.status = "failed"
            self.tasks_failed.value += 1
            self._send_result(task)
            return

        task.status = "processing"
        task.assigned_to = self.agent_id
        task.started_at = time.time()

        session = self.session_factory()

        try:
            from cognitive.active_learning_system import GraceActiveLearningSystem

            learning_system = GraceActiveLearningSystem(
                session=session,
                retriever=self.retriever,
                knowledge_base_path=self.knowledge_base_path
            )

            practice_task = {
                "description": task.task_description,
                "complexity": task.complexity
            }

            result = learning_system.practice_skill(
                skill_name=task.skill_name,
                task=practice_task,
                sandbox_context={}
            )

            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            self.tasks_processed.value += 1

            logger.info(
                f"[{self.agent_id}] Practiced '{task.skill_name}': "
                f"{'SUCCESS' if result.get('outcome', {}).get('success') else 'FAILED'} "
                f"in {task.completed_at - task.started_at:.1f}s"
            )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed.value += 1
            logger.error(f"[{self.agent_id}] Practice failed: {e}")

        finally:
            session.close()
            self._send_result(task)


# ======================================================================
# Mirror Subagent (self-reflection and gap identification)
# ======================================================================

class MirrorSubagent(BaseSubagent):
    """
    Autonomous mirror subagent for self-reflection.

    Observes practice outcomes and identifies knowledge gaps.
    Triggers proactive study when gaps detected.
    """

    def _initialize(self):
        """Initialize mirror."""
        from database.session import get_session_factory
        self.session_factory = get_session_factory()
        logger.info(f"[{self.agent_id}] Mirror subagent initialized")

    def _process_task(self, task: LearningTask):
        """Process reflection task."""
        if task.task_type != TaskType.REFLECT:
            task.error = f"Invalid task type: {task.task_type}"
            task.status = "failed"
            self.tasks_failed.value += 1
            self._send_result(task)
            return

        task.status = "processing"
        task.assigned_to = self.agent_id
        task.started_at = time.time()

        try:
            # Analyze practice outcome
            practice_result = task.result or {}
            outcome = practice_result.get('outcome', {})

            gaps = []

            if not outcome.get('success'):
                # Identify what went wrong
                gaps.append({
                    "topic": task.skill_name,
                    "reason": outcome.get('feedback', 'Unknown failure'),
                    "needs_study": True,
                    "priority": 2
                })

            task.result = {
                "gaps_identified": gaps,
                "reflection": "Mirror observed practice outcome",
                "proactive_actions": [
                    f"Study {gap['topic']}" for gap in gaps
                ]
            }

            task.status = "completed"
            task.completed_at = time.time()
            self.tasks_processed.value += 1

            if gaps:
                logger.info(
                    f"[{self.agent_id}] Identified {len(gaps)} knowledge gaps "
                    f"from practice of '{task.skill_name}'"
                )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed.value += 1
            logger.error(f"[{self.agent_id}] Reflection failed: {e}")

        finally:
            self._send_result(task)


# ======================================================================
# Master Orchestrator (coordinates all subagents)
# ======================================================================

class LearningOrchestrator:
    """
    Master process that coordinates all learning subagents.

    Architecture:
    - Spawns multiple study subagents (multi-process)
    - Spawns multiple practice subagents (multi-process)
    - Spawns mirror subagent (dedicated process)
    - Manages task distribution
    - Collects results
    - Monitors health
    """

    def __init__(
        self,
        knowledge_base_path: str,
        num_study_agents: int = 3,
        num_practice_agents: int = 2
    ):
        self.knowledge_base_path = knowledge_base_path

        # Multiprocessing setup
        mp.set_start_method('spawn', force=True)
        self.manager = Manager()

        # Shared state
        self.shared_state = self.manager.dict()

        # Task queues (one per subagent type)
        self.study_queue = Queue()
        self.practice_queue = Queue()
        self.mirror_queue = Queue()

        # Result queue (all subagents send results here)
        self.result_queue = Queue()

        # Subagents
        self.study_agents: List[StudySubagent] = []
        self.practice_agents: List[PracticeSubagent] = []
        self.mirror_agent: Optional[MirrorSubagent] = None

        # Create study subagents
        for i in range(num_study_agents):
            agent = StudySubagent(
                agent_id=f"study-{i+1}",
                task_queue=self.study_queue,
                result_queue=self.result_queue,
                shared_state=self.shared_state,
                knowledge_base_path=knowledge_base_path
            )
            self.study_agents.append(agent)

        # Create practice subagents
        for i in range(num_practice_agents):
            agent = PracticeSubagent(
                agent_id=f"practice-{i+1}",
                task_queue=self.practice_queue,
                result_queue=self.result_queue,
                shared_state=self.shared_state,
                knowledge_base_path=knowledge_base_path
            )
            self.practice_agents.append(agent)

        # Create mirror subagent
        self.mirror_agent = MirrorSubagent(
            agent_id="mirror",
            task_queue=self.mirror_queue,
            result_queue=self.result_queue,
            shared_state=self.shared_state,
            knowledge_base_path=knowledge_base_path
        )

        # Statistics
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0

        logger.info(
            f"[ORCHESTRATOR] Initialized with {num_study_agents} study agents, "
            f"{num_practice_agents} practice agents, 1 mirror agent"
        )

    def start(self):
        """Start all subagents."""
        logger.info("[ORCHESTRATOR] Starting all subagents...")

        for agent in self.study_agents:
            agent.start()

        for agent in self.practice_agents:
            agent.start()

        self.mirror_agent.start()

        # Start result collector
        self.result_collector = Process(
            target=self._collect_results,
            daemon=True
        )
        self.result_collector.start()

        logger.info("[ORCHESTRATOR] All subagents started")

    def stop(self):
        """Stop all subagents."""
        logger.info("[ORCHESTRATOR] Stopping all subagents...")

        for agent in self.study_agents:
            agent.stop()

        for agent in self.practice_agents:
            agent.stop()

        self.mirror_agent.stop()

        if self.result_collector:
            self.result_collector.terminate()

        logger.info("[ORCHESTRATOR] All subagents stopped")

    def submit_study_task(self, topic: str, learning_objectives: List[str], priority: int = 5) -> str:
        """Submit study task to available study subagent."""
        task = LearningTask(
            task_id=f"study-{self.total_tasks_submitted}",
            task_type=TaskType.STUDY,
            topic=topic,
            learning_objectives=learning_objectives,
            priority=priority
        )

        self.study_queue.put(Message(
            msg_type=MessageType.TASK,
            sender="orchestrator",
            timestamp=time.time(),
            data=task.to_dict()
        ).to_dict())

        self.total_tasks_submitted += 1
        logger.info(f"[ORCHESTRATOR] Study task submitted: {topic}")
        return task.task_id

    def submit_practice_task(self, skill_name: str, task_description: str, complexity: float = 0.5) -> str:
        """Submit practice task to available practice subagent."""
        task = LearningTask(
            task_id=f"practice-{self.total_tasks_submitted}",
            task_type=TaskType.PRACTICE,
            skill_name=skill_name,
            task_description=task_description,
            complexity=complexity
        )

        self.practice_queue.put(Message(
            msg_type=MessageType.TASK,
            sender="orchestrator",
            timestamp=time.time(),
            data=task.to_dict()
        ).to_dict())

        self.total_tasks_submitted += 1
        logger.info(f"[ORCHESTRATOR] Practice task submitted: {skill_name}")
        return task.task_id

    def _collect_results(self):
        """Collect results from all subagents (runs in separate process)."""
        logger.info("[RESULT-COLLECTOR] Started")

        while True:
            try:
                msg_dict = self.result_queue.get(timeout=5)
                msg = Message.from_dict(msg_dict)

                if msg.msg_type == MessageType.RESULT:
                    task = LearningTask.from_dict(msg.data)
                    self.total_tasks_completed += 1

                    logger.info(
                        f"[RESULT-COLLECTOR] Task completed: {task.task_id} "
                        f"(status={task.status})"
                    )

                    # If practice failed, trigger mirror reflection
                    if task.task_type == TaskType.PRACTICE and task.status == "completed":
                        if not task.result.get('outcome', {}).get('success'):
                            reflect_task = LearningTask(
                                task_id=f"reflect-{task.task_id}",
                                task_type=TaskType.REFLECT,
                                skill_name=task.skill_name,
                                result=task.result
                            )

                            self.mirror_queue.put(Message(
                                msg_type=MessageType.TASK,
                                sender="result-collector",
                                timestamp=time.time(),
                                data=reflect_task.to_dict()
                            ).to_dict())

                elif msg.msg_type == MessageType.HEARTBEAT:
                    pass  # Just monitoring

            except mp.queues.Empty:
                continue
            except Exception as e:
                logger.error(f"[RESULT-COLLECTOR] Error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "total_subagents": len(self.study_agents) + len(self.practice_agents) + 1,
            "study_agents": len(self.study_agents),
            "practice_agents": len(self.practice_agents),
            "study_queue_size": self.study_queue.qsize(),
            "practice_queue_size": self.practice_queue.qsize(),
            "mirror_queue_size": self.mirror_queue.qsize(),
            "total_tasks_submitted": self.total_tasks_submitted,
            "total_tasks_completed": self.total_tasks_completed
        }
