import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from queue import Queue, Empty
import threading
import time
import hashlib
from sqlalchemy.orm import Session
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from database.session import initialize_session_factory
from cognitive.active_learning_system import GraceActiveLearningSystem
from retrieval.retriever import DocumentRetriever
from embedding import get_embedding_model
class LearningTask:
    logger = logging.getLogger(__name__)
    """A learning task for Grace to process."""
    task_id: str
    task_type: str  # "study", "practice", "ingest"
    file_path: Optional[str] = None
    topic: Optional[str] = None
    learning_objectives: List[str] = field(default_factory=list)
    priority: int = 5  # 1 (highest) to 10 (lowest)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class LearningProgress:
    """Track Grace's learning progress."""
    total_files_processed: int = 0
    total_concepts_learned: int = 0
    total_practice_sessions: int = 0
    active_topics: Set[str] = field(default_factory=set)
    last_learning_time: Optional[datetime] = None
    files_in_queue: int = 0
    learning_velocity: float = 0.0  # concepts per hour


class FileMonitorHandler(FileSystemEventHandler):
    """
    Monitors knowledge base for new files.

    When new files are detected, automatically triggers:
    1. File ingestion
    2. Concept extraction (study)
    3. Knowledge storage in Layer 1
    """

    def __init__(self, learning_queue: Queue, knowledge_base_path: Path):
        self.learning_queue = learning_queue
        self.knowledge_base_path = knowledge_base_path
        self.processed_files: Set[str] = set()

        # Track file hashes to avoid re-processing
        self.file_hashes: Dict[str, str] = {}

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash to detect changes."""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    def _is_valid_training_file(self, file_path: Path) -> bool:
        """Check if file is valid training material."""
        valid_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.py', '.json'}
        return file_path.suffix.lower() in valid_extensions

    def on_created(self, event: FileSystemEvent):
        """Handle new file creation."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self._is_valid_training_file(file_path):
            return

        # Calculate hash
        file_hash = self._get_file_hash(file_path)

        # Check if already processed
        if str(file_path) in self.processed_files:
            logger.debug(f"File already processed: {file_path}")
            return

        logger.info(f"[PROACTIVE] New training file detected: {file_path.name}")

        # Create learning task
        task = LearningTask(
            task_id=f"new_file_{file_hash[:8]}",
            task_type="ingest_and_study",
            file_path=str(file_path),
            priority=1,  # High priority for new files
            created_at=datetime.utcnow()
        )

        # Add to learning queue
        self.learning_queue.put(task)
        self.processed_files.add(str(file_path))
        self.file_hashes[str(file_path)] = file_hash

        logger.info(f"[PROACTIVE] Learning task queued: {file_path.name}")

    def on_modified(self, event: FileSystemEvent):
        """Handle file modifications."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self._is_valid_training_file(file_path):
            return

        # Calculate new hash
        new_hash = self._get_file_hash(file_path)
        old_hash = self.file_hashes.get(str(file_path))

        # Only re-process if content actually changed
        if old_hash and new_hash != old_hash:
            logger.info(f"[PROACTIVE] Training file updated: {file_path.name}")

            task = LearningTask(
                task_id=f"updated_file_{new_hash[:8]}",
                task_type="ingest_and_study",
                file_path=str(file_path),
                priority=2,  # High priority for updates
                created_at=datetime.utcnow()
            )

            self.learning_queue.put(task)
            self.file_hashes[str(file_path)] = new_hash


class ProactiveLearningSubagent:
    """
    Autonomous learning subagent.

    Runs independently in background, processing learning tasks
    from the queue without blocking main application.
    """

    def __init__(
        self,
        agent_id: str,
        learning_queue: Queue,
        knowledge_base_path: Path,
        max_concurrent_tasks: int = 2
    ):
        self.agent_id = agent_id
        self.learning_queue = learning_queue
        self.knowledge_base_path = knowledge_base_path
        self.max_concurrent_tasks = max_concurrent_tasks

        # Task executor
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)

        # Running state
        self.is_running = False
        self.current_tasks: Dict[str, LearningTask] = {}

        # Statistics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_concepts_learned = 0

        logger.info(f"[SUBAGENT-{agent_id}] Initialized (max_concurrent={max_concurrent_tasks})")

    def start(self):
        """Start the subagent."""
        self.is_running = True
        logger.info(f"[SUBAGENT-{self.agent_id}] Starting background learning...")

        # Start processing loop in background thread
        processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name=f"LearningAgent-{self.agent_id}"
        )
        processing_thread.start()

    def stop(self):
        """Stop the subagent."""
        logger.info(f"[SUBAGENT-{self.agent_id}] Stopping...")
        self.is_running = False
        self.executor.shutdown(wait=True)

    def _processing_loop(self):
        """Main processing loop - runs continuously in background."""
        logger.info(f"[SUBAGENT-{self.agent_id}] Processing loop started")

        while self.is_running:
            try:
                # Get task from queue (non-blocking with timeout)
                try:
                    task = self.learning_queue.get(timeout=5)
                except Empty:
                    # No tasks available, continue loop
                    continue

                # Check if we have capacity
                while len(self.current_tasks) >= self.max_concurrent_tasks:
                    time.sleep(1)

                # Process task in thread pool
                logger.info(f"[SUBAGENT-{self.agent_id}] Processing task: {task.task_id}")
                future = self.executor.submit(self._process_task, task)
                self.current_tasks[task.task_id] = task

                # Clean up completed tasks
                self._cleanup_completed_tasks()

            except Exception as e:
                logger.error(f"[SUBAGENT-{self.agent_id}] Error in processing loop: {e}")
                import traceback
                traceback.print_exc()

        logger.info(f"[SUBAGENT-{self.agent_id}] Processing loop stopped")

    def _process_task(self, task: LearningTask):
        """Process a single learning task."""
        task.status = "processing"
        start_time = time.time()

        try:
            logger.info(f"[SUBAGENT-{self.agent_id}] Starting: {task.task_type} - {task.task_id}")

            if task.task_type == "ingest_and_study":
                result = self._ingest_and_study(task)
            elif task.task_type == "study":
                result = self._study_topic(task)
            elif task.task_type == "practice":
                result = self._practice_skill(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            task.result = result
            task.status = "completed"
            self.tasks_completed += 1

            # Track concepts learned
            if "concepts_learned" in result:
                self.total_concepts_learned += result["concepts_learned"]

            elapsed = time.time() - start_time
            logger.info(
                f"[SUBAGENT-{self.agent_id}] Completed: {task.task_id} "
                f"in {elapsed:.1f}s (concepts: {result.get('concepts_learned', 0)})"
            )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.tasks_failed += 1
            logger.error(f"[SUBAGENT-{self.agent_id}] Task failed: {task.task_id} - {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Remove from current tasks
            self.current_tasks.pop(task.task_id, None)
            self.learning_queue.task_done()

    def _ingest_and_study(self, task: LearningTask) -> Dict[str, Any]:
        """
        Ingest a new file and study its contents.

        NOW ROUTES THROUGH LAYER 1 for complete integration!
        """
        from ingestion.service import TextIngestionService
        from file_manager.file_handler import extract_file_text
        from models.database_models import Document
        from genesis.layer1_integration import get_layer1_integration

        file_path = Path(task.file_path)

        logger.info(f"[SUBAGENT-{self.agent_id}] Ingesting via Layer 1: {file_path.name}")

        # 1. Extract text
        result = extract_file_text(str(file_path))
        if isinstance(result, tuple):
            text, error = result
            if error:
                raise Exception(f"Extraction error: {error}")
        else:
            text = result

        # 2. Read file bytes for Layer 1
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        # 3. ROUTE THROUGH LAYER 1 (creates Genesis Key + triggers autonomous actions)
        session_factory = initialize_session_factory()
        db = session_factory()

        try:
            layer1 = get_layer1_integration(session=db)

            # Process file through Layer 1 pipeline
            layer1_result = layer1.process_file_upload(
                file_content=file_bytes,
                file_name=file_path.name,
                file_type=file_path.suffix,
                user_id="system",
                metadata={
                    "source": "proactive_learning_subagent",
                    "agent_id": self.agent_id,
                    "auto_ingested": True
                }
            )

            logger.info(
                f"[SUBAGENT-{self.agent_id}] File processed through Layer 1: "
                f"Genesis Key = {layer1_result.get('genesis_key_id')}"
            )

            # 4. Now ingest into vector database (if not already done)
            doc = Document(
                file_path=str(file_path.relative_to(self.knowledge_base_path)),
                text_content=text,
                char_count=len(text)
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            embedding_model = get_embedding_model()
            ingestion_service = TextIngestionService(embedding_model=embedding_model)

            asyncio.run(ingestion_service.ingest_text(
                text=text,
                metadata={"source": str(file_path), "genesis_key": layer1_result.get('genesis_key_id')},
                document_id=doc.id
            ))

            logger.info(f"[SUBAGENT-{self.agent_id}] Ingested: {file_path.name} (doc_id={doc.id})")

            # 5. Study the content (extract concepts)
            topic = self._infer_topic_from_path(file_path)

            learning_system = GraceActiveLearningSystem(
                session=db,
                retriever=DocumentRetriever(
                    collection_name="documents",
                    embedding_model=embedding_model
                ),
                knowledge_base_path=self.knowledge_base_path
            )

            study_result = learning_system.study_topic(
                topic=topic,
                learning_objectives=[f"Learn from {file_path.name}"],
                max_materials=1  # Just this file
            )

            logger.info(
                f"[SUBAGENT-{self.agent_id}] Studied: {topic} - "
                f"{study_result.get('concepts_learned', 0)} concepts learned"
            )

            return {
                "file_path": str(file_path),
                "document_id": doc.id,
                "topic": topic,
                "concepts_learned": study_result.get("concepts_learned", 0),
                "genesis_key_id": layer1_result.get('genesis_key_id'),
                "layer1_integrated": True,
                "ingested": True,
                "studied": True
            }

        finally:
            db.close()

    def _study_topic(self, task: LearningTask) -> Dict[str, Any]:
        """Study a topic from training materials."""
        session_factory = initialize_session_factory()
        db = session_factory()

        try:
            embedding_model = get_embedding_model()
            learning_system = GraceActiveLearningSystem(
                session=db,
                retriever=DocumentRetriever(
                    collection_name="documents",
                    embedding_model=embedding_model
                ),
                knowledge_base_path=self.knowledge_base_path
            )

            result = learning_system.study_topic(
                topic=task.topic,
                learning_objectives=task.learning_objectives,
                max_materials=10
            )

            return result

        finally:
            db.close()

    def _practice_skill(self, task: LearningTask) -> Dict[str, Any]:
        """Practice a skill."""
        session_factory = initialize_session_factory()
        db = session_factory()

        try:
            embedding_model = get_embedding_model()
            learning_system = GraceActiveLearningSystem(
                session=db,
                retriever=DocumentRetriever(
                    collection_name="documents",
                    embedding_model=embedding_model
                ),
                knowledge_base_path=self.knowledge_base_path
            )

            # Practice implementation would go here
            # For now, return placeholder
            return {
                "skill": task.topic,
                "practiced": True
            }

        finally:
            db.close()

    def _infer_topic_from_path(self, file_path: Path) -> str:
        """Infer learning topic from file path and name."""
        # Use parent folder name as topic
        parent = file_path.parent.name

        # Common topic mappings
        topic_mappings = {
            "ai research": "AI and machine learning",
            "backend": "Backend development",
            "frontend": "Frontend development",
            "databases": "Database design",
            "testing": "Testing and TDD",
            "python": "Python programming",
            "api": "API design",
            "architecture": "Software architecture"
        }

        parent_lower = parent.lower()
        for key, topic in topic_mappings.items():
            if key in parent_lower:
                return topic

        # Default: use file name without extension
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()

    def _cleanup_completed_tasks(self):
        """Remove completed tasks from tracking."""
        completed = [
            task_id for task_id, task in self.current_tasks.items()
            if task.status in ("completed", "failed")
        ]
        for task_id in completed:
            self.current_tasks.pop(task_id, None)

    def get_status(self) -> Dict[str, Any]:
        """Get subagent status."""
        return {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "current_tasks": len(self.current_tasks),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_concepts_learned": self.total_concepts_learned,
            "success_rate": (
                self.tasks_completed / (self.tasks_completed + self.tasks_failed)
                if (self.tasks_completed + self.tasks_failed) > 0 else 0
            )
        }


class ProactiveLearningOrchestrator:
    """
    Orchestrates proactive learning system.

    Manages:
    - File system monitoring
    - Learning task queue
    - Multiple learning subagents
    - Progress tracking
    """

    def __init__(
        self,
        knowledge_base_path: Path,
        num_subagents: int = 2,
        max_concurrent_per_agent: int = 2
    ):
        self.knowledge_base_path = knowledge_base_path
        self.num_subagents = num_subagents
        self.max_concurrent_per_agent = max_concurrent_per_agent

        # Learning task queue
        self.learning_queue = Queue()

        # File system monitor
        self.file_handler = FileMonitorHandler(
            learning_queue=self.learning_queue,
            knowledge_base_path=knowledge_base_path
        )
        self.observer = Observer()

        # Subagents
        self.subagents: List[ProactiveLearningSubagent] = []
        for i in range(num_subagents):
            agent = ProactiveLearningSubagent(
                agent_id=f"agent-{i+1}",
                learning_queue=self.learning_queue,
                knowledge_base_path=knowledge_base_path,
                max_concurrent_tasks=max_concurrent_per_agent
            )
            self.subagents.append(agent)

        # Progress tracking
        self.progress = LearningProgress()
        self.start_time = None

        logger.info(
            f"[ORCHESTRATOR] Initialized with {num_subagents} subagents "
            f"({max_concurrent_per_agent} concurrent tasks each)"
        )

    def start(self):
        """Start proactive learning system."""
        logger.info("[ORCHESTRATOR] Starting proactive learning system...")

        self.start_time = datetime.utcnow()

        # Start file monitoring
        self.observer.schedule(
            self.file_handler,
            str(self.knowledge_base_path),
            recursive=True
        )
        self.observer.start()
        logger.info(f"[ORCHESTRATOR] Monitoring: {self.knowledge_base_path}")

        # Start all subagents
        for agent in self.subagents:
            agent.start()

        logger.info(
            f"[ORCHESTRATOR] System online with {self.num_subagents} learning agents"
        )

    def stop(self):
        """Stop proactive learning system."""
        logger.info("[ORCHESTRATOR] Stopping proactive learning system...")

        # Stop file monitoring
        self.observer.stop()
        self.observer.join()

        # Stop all subagents
        for agent in self.subagents:
            agent.stop()

        logger.info("[ORCHESTRATOR] System stopped")

    def add_learning_task(
        self,
        task_type: str,
        topic: Optional[str] = None,
        learning_objectives: Optional[List[str]] = None,
        file_path: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """
        Manually add a learning task to the queue.

        Returns task_id for tracking.
        """
        task_id = f"{task_type}_{datetime.utcnow().timestamp()}"

        task = LearningTask(
            task_id=task_id,
            task_type=task_type,
            topic=topic,
            learning_objectives=learning_objectives or [],
            file_path=file_path,
            priority=priority
        )

        self.learning_queue.put(task)
        logger.info(f"[ORCHESTRATOR] Task queued: {task_id} (priority={priority})")

        return task_id

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        # Aggregate subagent stats
        total_completed = sum(agent.tasks_completed for agent in self.subagents)
        total_failed = sum(agent.tasks_failed for agent in self.subagents)
        total_concepts = sum(agent.total_concepts_learned for agent in self.subagents)

        # Calculate learning velocity
        if self.start_time:
            hours_running = (datetime.utcnow() - self.start_time).total_seconds() / 3600
            learning_velocity = total_concepts / hours_running if hours_running > 0 else 0
        else:
            learning_velocity = 0

        return {
            "status": "running" if self.subagents[0].is_running else "stopped",
            "num_subagents": self.num_subagents,
            "queue_size": self.learning_queue.qsize(),
            "total_tasks_completed": total_completed,
            "total_tasks_failed": total_failed,
            "total_concepts_learned": total_concepts,
            "learning_velocity_per_hour": round(learning_velocity, 2),
            "uptime_hours": (
                (datetime.utcnow() - self.start_time).total_seconds() / 3600
                if self.start_time else 0
            ),
            "subagents": [agent.get_status() for agent in self.subagents]
        }
