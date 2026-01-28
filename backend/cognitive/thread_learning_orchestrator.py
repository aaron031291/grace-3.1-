"""
Thread-Based Learning Subagent System

Windows-compatible version using threading instead of multiprocessing.

Architecture:
- Master Thread: Orchestrates learning subagents
- Study Subagents: Autonomous concept extraction (multi-thread)
- Practice Subagents: Skill execution and validation (multi-thread)
- Mirror Subagent: Self-reflection and gap identification (dedicated thread)
- Result Collector Thread: Collects results from all subagents

All subagents run independently in background threads with IPC via queues.
"""

import threading
from queue import Queue, Empty
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

# Import shared types from multiprocessing version
from .learning_subagent_system import (
    TaskType, MessageType, LearningTask, Message
)

logger = logging.getLogger(__name__)


# ======================================================================
# Base Subagent (runs in separate thread)
# ======================================================================

class BaseThreadSubagent:
    """
    Base class for all learning subagents (thread-based).

    Each subagent runs in its own thread with:
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

        # Thread-safe state tracking
        self.is_running = False
        self.tasks_processed = 0
        self.tasks_failed = 0
        self._lock = threading.Lock()

        # Thread handle
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start subagent in separate thread."""
        self.is_running = True
        self.thread = threading.Thread(
            target=self._run,
            name=f"Subagent-{self.agent_id}",
            daemon=True
        )
        self.thread.start()
        logger.info(f"[{self.agent_id}] Subagent started (Thread: {self.thread.name})")

    def stop(self, timeout: int = 10):
        """Stop subagent gracefully."""
        if self.thread and self.thread.is_alive():
            # Signal shutdown
            self.is_running = False
            self.task_queue.put(Message(
                msg_type=MessageType.SHUTDOWN,
                sender="master",
                timestamp=time.time(),
                data={}
            ).to_dict())

            # Wait for graceful shutdown
            self.thread.join(timeout=timeout)

            if self.thread.is_alive():
                logger.warning(f"[{self.agent_id}] Thread still alive after timeout")

        logger.info(f"[{self.agent_id}] Subagent stopped")

    def _run(self):
        """Main execution loop (runs in separate thread)."""
        logger.info(f"[{self.agent_id}] Execution loop started")

        try:
            self._initialize()

            while self.is_running:
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

                except Empty:
                    # No tasks, send heartbeat
                    if self.is_running:
                        self._send_heartbeat()
                    continue

                except Exception as e:
                    logger.error(f"[{self.agent_id}] Error in loop: {e}")
                    import traceback
                    traceback.print_exc()
                    with self._lock:
                        self.tasks_failed += 1

        finally:
            self._cleanup()
            self.is_running = False
            logger.info(f"[{self.agent_id}] Execution loop ended")

    def _initialize(self):
        """Initialize resources (override in subclass)."""
        pass

    def _cleanup(self):
        """Cleanup resources (override in subclass)."""
        pass

    def _process_task(self, task: LearningTask):
        """Process a task (override in subclass)."""
        # Default handler for unimplemented task types; keep thread alive and surface failure.
        task.status = "failed"
        task.error = f"Unhandled task type for base subagent: {task.task_type}"
        task.assigned_to = self.agent_id
        task.started_at = task.started_at or time.time()
        task.completed_at = time.time()
        with self._lock:
            self.tasks_failed += 1
        logger.warning(f"[{self.agent_id}] {task.error}")
        try:
            self._send_result(task)
        except Exception:
            logger.exception(f"[{self.agent_id}] Failed to send result for unhandled task")

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
                "tasks_processed": self.tasks_processed,
                "tasks_failed": self.tasks_failed,
                "is_running": self.is_running
            }
        ).to_dict())


# ======================================================================
# Study Subagent (extracts concepts from training materials)
# ======================================================================

class ThreadStudySubagent(BaseThreadSubagent):
    """
    Autonomous study subagent (thread-based).

    Runs independently to:
    - Extract concepts from training materials
    - Store in Layer 1 with trust scores
    - Identify focus areas
    """

    def _initialize(self):
        """Initialize database, retriever, and active learning system."""
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

        # Initialize the active learning system
        self._learning_system = None  # Lazy initialization per session

        logger.info(f"[{self.agent_id}] Study subagent initialized")

    def _get_learning_system(self, session):
        """Get or create learning system instance."""
        from cognitive.active_learning_system import GraceActiveLearningSystem
        return GraceActiveLearningSystem(
            session=session,
            retriever=self.retriever,
            knowledge_base_path=self.knowledge_base_path
        )

    def _process_task(self, task: LearningTask):
        """Process study task."""
        if task.task_type != TaskType.STUDY:
            logger.warning(f"[{self.agent_id}] Received non-study task: {task.task_type}")
            return

        try:
            task.status = "processing"
            task.started_at = time.time()

            logger.info(f"[{self.agent_id}] Processing study task: {task.topic}")

            # Get session
            session = self.session_factory()

            try:
                # Get active learning system
                learning_system = self._get_learning_system(session)

                # Extract concepts from topic/file
                if task.file_path:
                    # Study from file - extract topic from file path
                    file_topic = Path(task.file_path).stem.replace('_', ' ').replace('-', ' ')
                    result = learning_system.study_topic(
                        topic=file_topic,
                        learning_objectives=task.learning_objectives or [f"Learn from {task.file_path}"],
                        max_materials=10
                    )
                elif task.topic:
                    # Study topic using active learning system
                    result = learning_system.study_topic(
                        topic=task.topic,
                        learning_objectives=task.learning_objectives or [f"Learn about {task.topic}"],
                        max_materials=10
                    )
                else:
                    raise ValueError("Task must have file_path or topic")

                task.status = "completed"
                task.completed_at = time.time()
                task.result = {
                    "concepts_extracted": result.get("concepts_learned", 0),
                    "materials_studied": result.get("materials_studied", 0),
                    "focus_areas": result.get("focus_areas", []),
                    "examples_stored": result.get("examples_stored", 0),
                    "prefetched_topics": result.get("prefetched_topics", [])
                }

                with self._lock:
                    self.tasks_processed += 1

                logger.info(
                    f"[{self.agent_id}] Study completed: {result.get('concepts_learned', 0)} concepts, "
                    f"{result.get('examples_stored', 0)} examples stored"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"[{self.agent_id}] Task failed: {e}")
            import traceback
            traceback.print_exc()
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            with self._lock:
                self.tasks_failed += 1

        finally:
            self._send_result(task)


# ======================================================================
# Practice Subagent (validates skills)
# ======================================================================

class ThreadPracticeSubagent(BaseThreadSubagent):
    """
    Autonomous practice subagent (thread-based).

    Runs independently to:
    - Execute practice tasks
    - Validate skills
    - Update trust scores
    """

    def _initialize(self):
        """Initialize database, retriever, and learning system."""
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

    def _get_learning_system(self, session):
        """Get or create learning system instance."""
        from cognitive.active_learning_system import GraceActiveLearningSystem
        return GraceActiveLearningSystem(
            session=session,
            retriever=self.retriever,
            knowledge_base_path=self.knowledge_base_path
        )

    def _process_task(self, task: LearningTask):
        """Process practice task."""
        if task.task_type != TaskType.PRACTICE:
            logger.warning(f"[{self.agent_id}] Received non-practice task: {task.task_type}")
            return

        try:
            task.status = "processing"
            task.started_at = time.time()

            logger.info(f"[{self.agent_id}] Processing practice task: {task.skill_name}")

            # Get session
            session = self.session_factory()

            try:
                # Get learning system
                learning_system = self._get_learning_system(session)

                # Create task dict for practice
                practice_task = {
                    "description": task.task_description or f"Practice {task.skill_name}",
                    "complexity": task.complexity or 0.5,
                    "requirements": []
                }

                # Practice skill using active learning system
                result = learning_system.practice_skill(
                    skill_name=task.skill_name or "general",
                    task=practice_task,
                    sandbox_context={}
                )

                task.status = "completed"
                task.completed_at = time.time()
                task.result = {
                    "outcome": result.get("outcome", {}),
                    "success": result.get("success", False),
                    "approach": result.get("approach", {}),
                    "feedback": result.get("feedback", "")
                }

                with self._lock:
                    self.tasks_processed += 1

                logger.info(
                    f"[{self.agent_id}] Practice completed: "
                    f"{'SUCCESS' if result.get('success') else 'NEEDS_WORK'}"
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"[{self.agent_id}] Task failed: {e}")
            import traceback
            traceback.print_exc()
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            with self._lock:
                self.tasks_failed += 1

        finally:
            self._send_result(task)


# ======================================================================
# Mirror Subagent (self-reflection)
# ======================================================================

class ThreadMirrorSubagent(BaseThreadSubagent):
    """
    Mirror subagent for self-reflection (thread-based).

    Runs independently to:
    - Analyze learning patterns
    - Identify gaps
    - Generate improvement suggestions
    """

    def _initialize(self):
        """Initialize mirror system."""
        from database.session import get_session_factory
        from cognitive.mirror_self_modeling import get_mirror_system

        self.session_factory = get_session_factory()
        session = self.session_factory()
        self.mirror_system = get_mirror_system(session)

        logger.info(f"[{self.agent_id}] Mirror subagent initialized")

    def _process_task(self, task: LearningTask):
        """Process mirror task."""
        try:
            task.status = "processing"
            task.started_at = time.time()

            logger.info(f"[{self.agent_id}] Processing reflection task")

            # Build self-model which includes patterns and suggestions
            self_model = self.mirror_system.build_self_model()

            # Extract patterns and improvement suggestions
            analysis = {
                "behavioral_patterns": self_model.get("behavioral_patterns", {}),
                "learning_progress": self_model.get("learning_progress", {}),
                "improvement_suggestions": self_model.get("improvement_suggestions", []),
                "self_awareness_score": self_model.get("self_awareness_score", 0.0),
                "operations_observed": self_model.get("operations_observed", 0)
            }

            task.status = "completed"
            task.completed_at = time.time()
            task.result = analysis

            with self._lock:
                self.tasks_processed += 1

        except Exception as e:
            logger.error(f"[{self.agent_id}] Task failed: {e}")
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            with self._lock:
                self.tasks_failed += 1

        finally:
            self._send_result(task)


# ======================================================================
# Thread-Based Master Orchestrator
# ======================================================================

class ThreadLearningOrchestrator:
    """
    Master thread-based orchestrator that coordinates all learning subagents.

    Architecture:
    - Spawns multiple study subagents (multi-thread)
    - Spawns multiple practice subagents (multi-thread)
    - Spawns mirror subagent (dedicated thread)
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

        # Thread-safe shared state
        self.shared_state = {}
        self._state_lock = threading.Lock()

        # Task queues (thread-safe queues)
        self.study_queue = Queue()
        self.practice_queue = Queue()
        self.mirror_queue = Queue()

        # Result queue (all subagents send results here)
        self.result_queue = Queue()

        # Subagents
        self.study_agents: List[ThreadStudySubagent] = []
        self.practice_agents: List[ThreadPracticeSubagent] = []
        self.mirror_agent: Optional[ThreadMirrorSubagent] = None

        # Create study subagents
        for i in range(num_study_agents):
            agent = ThreadStudySubagent(
                agent_id=f"study-{i+1}",
                task_queue=self.study_queue,
                result_queue=self.result_queue,
                shared_state=self.shared_state,
                knowledge_base_path=knowledge_base_path
            )
            self.study_agents.append(agent)

        # Create practice subagents
        for i in range(num_practice_agents):
            agent = ThreadPracticeSubagent(
                agent_id=f"practice-{i+1}",
                task_queue=self.practice_queue,
                result_queue=self.result_queue,
                shared_state=self.shared_state,
                knowledge_base_path=knowledge_base_path
            )
            self.practice_agents.append(agent)

        # Create mirror subagent
        self.mirror_agent = ThreadMirrorSubagent(
            agent_id="mirror",
            task_queue=self.mirror_queue,
            result_queue=self.result_queue,
            shared_state=self.shared_state,
            knowledge_base_path=knowledge_base_path
        )

        # Statistics
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self._stats_lock = threading.Lock()

        # Result collector thread
        self.result_collector_thread: Optional[threading.Thread] = None
        self._collector_running = False

        logger.info(
            f"[ORCHESTRATOR] Initialized with {num_study_agents} study agents, "
            f"{num_practice_agents} practice agents, 1 mirror agent (thread-based)"
        )

    def start(self):
        """Start all subagents."""
        logger.info("[ORCHESTRATOR] Starting all subagents (thread-based)...")

        for agent in self.study_agents:
            agent.start()

        for agent in self.practice_agents:
            agent.start()

        self.mirror_agent.start()

        # Start result collector thread
        self._collector_running = True
        self.result_collector_thread = threading.Thread(
            target=self._collect_results,
            name="ResultCollector",
            daemon=True
        )
        self.result_collector_thread.start()

        logger.info("[ORCHESTRATOR] All subagents started (thread-based)")

    def stop(self):
        """Stop all subagents."""
        logger.info("[ORCHESTRATOR] Stopping all subagents...")

        # Stop result collector
        self._collector_running = False
        if self.result_collector_thread:
            self.result_collector_thread.join(timeout=5)

        # Stop all subagents
        for agent in self.study_agents:
            agent.stop()

        for agent in self.practice_agents:
            agent.stop()

        self.mirror_agent.stop()

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

        with self._stats_lock:
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

        with self._stats_lock:
            self.total_tasks_submitted += 1

        logger.info(f"[ORCHESTRATOR] Practice task submitted: {skill_name}")
        return task.task_id

    def _collect_results(self):
        """Collect results from all subagents (runs in separate thread)."""
        logger.info("[RESULT-COLLECTOR] Started")

        while self._collector_running:
            try:
                msg_dict = self.result_queue.get(timeout=5)
                msg = Message.from_dict(msg_dict)

                if msg.msg_type == MessageType.RESULT:
                    task = LearningTask.from_dict(msg.data)
                    with self._stats_lock:
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

            except Empty:
                continue
            except Exception as e:
                logger.error(f"[RESULT-COLLECTOR] Error: {e}")

        logger.info("[RESULT-COLLECTOR] Stopped")

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
            "total_tasks_completed": self.total_tasks_completed,
            "implementation": "thread-based"
        }
