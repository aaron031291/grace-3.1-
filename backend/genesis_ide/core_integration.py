"""
Genesis IDE Core Integration
============================

Central orchestrator that connects ALL Grace systems into the IDE:
- Layer 1/2 Intelligence
- Cognitive Framework (OODA)
- Genesis Key Tracking
- Ghost Ledger
- Self-Healing
- Librarian
- File Manager
- Version Control
- CI/CD Pipeline
- Autonomous Actions
- VectorDB Learning

Everything is trackable, traceable, and learns from outcomes.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import json
import uuid

logger = logging.getLogger(__name__)


@dataclass
class IDESession:
    """Represents an IDE session with full tracking."""
    session_id: str
    started_at: datetime
    user_id: Optional[str] = None
    workspace_path: Optional[Path] = None
    active_files: List[str] = field(default_factory=list)
    genesis_keys_created: int = 0
    actions_performed: int = 0
    healings_applied: int = 0
    mutations_tracked: int = 0
    parent_genesis_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "user_id": self.user_id,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "active_files": self.active_files,
            "genesis_keys_created": self.genesis_keys_created,
            "actions_performed": self.actions_performed,
            "healings_applied": self.healings_applied,
            "mutations_tracked": self.mutations_tracked,
            "parent_genesis_key": self.parent_genesis_key
        }


class GenesisIDECore:
    """
    Core integration layer for Genesis IDE.

    Orchestrates all Grace systems to provide a fully intelligent,
    self-healing, self-improving IDE experience.
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()

        # Current IDE session
        self._ide_session: Optional[IDESession] = None

        # Connected systems (lazy initialized)
        self._layer1: Optional[Any] = None
        self._layer2: Optional[Any] = None
        self._cognitive: Optional[Any] = None
        self._genesis_service: Optional[Any] = None
        self._ghost_ledger: Optional[Any] = None
        self._healing_system: Optional[Any] = None
        self._librarian: Optional[Any] = None
        self._file_manager: Optional[Any] = None
        self._version_control: Optional[Any] = None
        self._cicd_pipeline: Optional[Any] = None
        self._scheduler: Optional[Any] = None
        self._vector_db: Optional[Any] = None
        self._failure_learning: Optional[Any] = None
        self._mutation_tracker: Optional[Any] = None
        self._self_updater: Optional[Any] = None
        self._ide_bridge: Optional[Any] = None

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Metrics
        self.metrics = {
            "sessions_started": 0,
            "total_actions": 0,
            "genesis_keys_created": 0,
            "healings_applied": 0,
            "failures_learned": 0,
            "mutations_tracked": 0,
            "self_updates": 0
        }

        logger.info("[GENESIS-IDE] Core initialized")

    async def initialize(self) -> bool:
        """
        Initialize all connected systems.

        This connects Genesis IDE to the entire Grace ecosystem.
        """
        logger.info("[GENESIS-IDE] Initializing all systems...")

        try:
            # Layer 1 Intelligence (Universal Input/Output)
            from genesis_ide.layer_intelligence import Layer1Intelligence
            self._layer1 = Layer1Intelligence(self.session, self.repo_path)
            await self._layer1.initialize()

            # Layer 2 Intelligence (Cognitive Processing)
            from genesis_ide.layer_intelligence import Layer2Intelligence
            self._layer2 = Layer2Intelligence(self.session, self.repo_path)
            await self._layer2.initialize()

            # Cognitive Framework
            from genesis_ide.cognitive_ide import CognitiveIDEFramework
            self._cognitive = CognitiveIDEFramework(self.session, self.repo_path)

            # Genesis Key Service
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            # Ghost Ledger
            from grace_os.ghost_ledger import GhostLedger
            self._ghost_ledger = GhostLedger(
                session=self.session,
                repo_path=self.repo_path
            )

            # Self-Healing System
            from cognitive.autonomous_healing_system import AutonomousHealingSystem
            self._healing_system = AutonomousHealingSystem(
                session=self.session,
                repo_path=self.repo_path
            )

            # Librarian
            try:
                from librarian.librarian_service import LibrarianService
                self._librarian = LibrarianService(self.session)
            except Exception as e:
                logger.warning(f"[GENESIS-IDE] Librarian not available: {e}")

            # File Manager
            try:
                from file_manager.file_intelligence import FileIntelligence
                self._file_manager = FileIntelligence(
                    session=self.session,
                    repo_path=str(self.repo_path)
                )
            except Exception as e:
                logger.warning(f"[GENESIS-IDE] File Manager not available: {e}")

            # Version Control
            try:
                from version_control.git_service import GitService
                self._version_control = GitService(str(self.repo_path))
            except Exception as e:
                logger.warning(f"[GENESIS-IDE] Version Control not available: {e}")

            # CI/CD Pipeline
            try:
                from genesis.autonomous_cicd_engine import AutonomousCICDEngine
                self._cicd_pipeline = AutonomousCICDEngine(self.session, self.repo_path)
            except Exception as e:
                logger.warning(f"[GENESIS-IDE] CI/CD Pipeline not available: {e}")

            # Autonomous Scheduler
            from grace_os.autonomous_scheduler import AutonomousTaskScheduler
            self._scheduler = AutonomousTaskScheduler(
                session=self.session,
                repo_path=self.repo_path
            )
            await self._scheduler.start()

            # VectorDB for Learning
            try:
                from vector_db.qdrant_client import QdrantClient
                self._vector_db = QdrantClient()
            except Exception as e:
                logger.warning(f"[GENESIS-IDE] VectorDB not available: {e}")

            # Failure Learning System
            from genesis_ide.failure_learning import FailureLearningSystem
            self._failure_learning = FailureLearningSystem(
                session=self.session,
                vector_db=self._vector_db
            )

            # Mutation Tracker
            from genesis_ide.mutation_tracker import MutationTracker
            self._mutation_tracker = MutationTracker(
                session=self.session,
                genesis_service=self._genesis_service,
                git_service=self._version_control
            )

            # Self-Updater
            from genesis_ide.self_updater import SelfUpdater
            self._self_updater = SelfUpdater(
                session=self.session,
                repo_path=self.repo_path,
                genesis_service=self._genesis_service
            )

            # IDE Bridge (connects to VS Code/Code-Server)
            from grace_os.ide_bridge import IDEBridge, IDEBridgeConfig
            config = IDEBridgeConfig(workspace_path=self.repo_path)
            self._ide_bridge = IDEBridge(config, self.session)
            await self._ide_bridge.initialize()

            logger.info("[GENESIS-IDE] All systems initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[GENESIS-IDE] Initialization failed: {e}")
            return False

    # =========================================================================
    # Session Management
    # =========================================================================

    async def start_session(
        self,
        user_id: Optional[str] = None,
        workspace_path: Optional[Path] = None
    ) -> IDESession:
        """Start a new IDE session with full tracking."""
        self._ide_session = IDESession(
            session_id=f"SESSION-{uuid.uuid4().hex[:12]}",
            started_at=datetime.utcnow(),
            user_id=user_id,
            workspace_path=workspace_path or self.repo_path
        )

        # Create parent genesis key for session
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.SESSION_STARTED,
                what_description=f"IDE Session started: {self._ide_session.session_id}",
                who_actor=user_id or "Anonymous",
                where_location=str(workspace_path or self.repo_path),
                why_reason="User started IDE session",
                how_method="GenesisIDECore.start_session",
                session_id=self._ide_session.session_id,
                session=self.session
            )
            self._ide_session.parent_genesis_key = genesis_key.key_id

        self.metrics["sessions_started"] += 1

        logger.info(f"[GENESIS-IDE] Session started: {self._ide_session.session_id}")

        return self._ide_session

    async def end_session(self) -> Dict[str, Any]:
        """End the current IDE session."""
        if not self._ide_session:
            return {"error": "No active session"}

        session = self._ide_session
        session_summary = session.to_dict()

        # Create closing genesis key
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            self._genesis_service.create_key(
                key_type=GenesisKeyType.SESSION_ENDED,
                what_description=f"IDE Session ended: {session.session_id}",
                who_actor=session.user_id or "Anonymous",
                where_location=str(session.workspace_path),
                why_reason="User ended IDE session",
                how_method="GenesisIDECore.end_session",
                parent_key_id=session.parent_genesis_key,
                context_data=session_summary,
                session=self.session
            )

        # Persist ghost ledger
        if self._ghost_ledger:
            await self._ghost_ledger.persist()

        self._ide_session = None

        logger.info(f"[GENESIS-IDE] Session ended: {session.session_id}")

        return session_summary

    # =========================================================================
    # Unified Action Interface
    # =========================================================================

    async def execute_action(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        source: str = "user"
    ) -> Dict[str, Any]:
        """
        Execute any action through the unified interface.

        All actions are:
        1. Logged with Genesis Keys
        2. Tracked for mutations
        3. Stored for learning
        4. Subject to cognitive processing
        """
        action_id = f"ACTION-{uuid.uuid4().hex[:8]}"

        logger.debug(f"[GENESIS-IDE] Executing action {action_id}: {action_type}")

        # Create genesis key for action
        genesis_key = None
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.ACTION_EXECUTED,
                what_description=f"Action: {action_type}",
                who_actor=source,
                where_location=str(self.repo_path),
                why_reason=parameters.get("reason", "User requested action"),
                how_method="GenesisIDECore.execute_action",
                parent_key_id=self._ide_session.parent_genesis_key if self._ide_session else None,
                context_data={"action_type": action_type, "parameters": parameters},
                session=self.session
            )

            if self._ide_session:
                self._ide_session.genesis_keys_created += 1
                self._ide_session.actions_performed += 1

        self.metrics["total_actions"] += 1
        self.metrics["genesis_keys_created"] += 1

        try:
            # Route to appropriate handler
            result = await self._route_action(action_type, parameters, genesis_key)

            # Track mutations if file changes occurred
            if result.get("files_changed"):
                await self._track_mutations(result["files_changed"], genesis_key)

            return {
                "success": True,
                "action_id": action_id,
                "genesis_key_id": genesis_key.key_id if genesis_key else None,
                "result": result
            }

        except Exception as e:
            logger.error(f"[GENESIS-IDE] Action {action_id} failed: {e}")

            # Store failure for learning
            if self._failure_learning:
                await self._failure_learning.record_failure(
                    action_type=action_type,
                    parameters=parameters,
                    error=str(e),
                    genesis_key_id=genesis_key.key_id if genesis_key else None
                )

            return {
                "success": False,
                "action_id": action_id,
                "genesis_key_id": genesis_key.key_id if genesis_key else None,
                "error": str(e)
            }

    async def _route_action(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        genesis_key: Any
    ) -> Dict[str, Any]:
        """Route action to appropriate handler."""
        # Healing actions
        if action_type.startswith("heal_"):
            return await self._handle_healing_action(action_type, parameters)

        # File actions
        elif action_type.startswith("file_"):
            return await self._handle_file_action(action_type, parameters)

        # Code generation actions
        elif action_type.startswith("generate_"):
            return await self._handle_generation_action(action_type, parameters)

        # Search actions
        elif action_type.startswith("search_"):
            return await self._handle_search_action(action_type, parameters)

        # Test/Build actions
        elif action_type in ["run_tests", "run_build", "run_lint"]:
            return await self._handle_build_action(action_type, parameters)

        # Version control actions
        elif action_type.startswith("git_"):
            return await self._handle_git_action(action_type, parameters)

        # Librarian actions
        elif action_type.startswith("librarian_"):
            return await self._handle_librarian_action(action_type, parameters)

        # Learning actions
        elif action_type.startswith("learn_"):
            return await self._handle_learning_action(action_type, parameters)

        # Self-update action
        elif action_type == "self_update":
            return await self._handle_self_update(parameters)

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def _handle_healing_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle healing actions."""
        if not self._healing_system:
            return {"error": "Healing system not available"}

        if action_type == "heal_file":
            file_path = parameters.get("file_path")
            if not file_path:
                return {"error": "file_path required"}

            # Use IDE bridge for healing
            if self._ide_bridge:
                result = await self._ide_bridge.request_healing(file_path)
                if self._ide_session:
                    self._ide_session.healings_applied += 1
                self.metrics["healings_applied"] += 1
                return result

        elif action_type == "heal_project":
            assessment = self._healing_system.assess_system_health()
            return assessment

        elif action_type == "heal_check":
            return self._healing_system.assess_system_health()

        return {"error": f"Unknown healing action: {action_type}"}

    async def _handle_file_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle file actions with full tracking."""
        if action_type == "file_read":
            file_path = parameters.get("file_path")
            if not file_path:
                return {"error": "file_path required"}

            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            content = path.read_text()
            return {"content": content, "lines": len(content.splitlines())}

        elif action_type == "file_write":
            file_path = parameters.get("file_path")
            content = parameters.get("content", "")

            if not file_path:
                return {"error": "file_path required"}

            path = Path(file_path)

            # Get old content for ghost ledger
            old_content = path.read_text() if path.exists() else ""

            # Write new content
            path.write_text(content)

            # Record in ghost ledger
            if self._ghost_ledger:
                await self._ghost_ledger.record_change(
                    file_path=file_path,
                    old_content=old_content,
                    new_content=content,
                    source="user"
                )

            return {"files_changed": [file_path], "success": True}

        elif action_type == "file_create":
            file_path = parameters.get("file_path")
            content = parameters.get("content", "")

            if not file_path:
                return {"error": "file_path required"}

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

            return {"files_changed": [file_path], "created": True}

        return {"error": f"Unknown file action: {action_type}"}

    async def _handle_generation_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle code generation actions."""
        from grace_os.deterministic_pipeline import DeterministicCodePipeline, ExecutionContract

        pipeline = DeterministicCodePipeline(self.session, self.repo_path)
        await pipeline.initialize()

        contract = ExecutionContract(
            goal=parameters.get("description", ""),
            allowed_files=parameters.get("files", ["*"]),
            constraints=parameters.get("constraints", {}),
            risk_level=parameters.get("risk_level", "low")
        )

        result = await pipeline.execute(contract)
        return result.to_dict()

    async def _handle_search_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle search actions using multi-plane reasoning."""
        from grace_os.reasoning_planes import MultiPlaneReasoner

        reasoner = MultiPlaneReasoner(self.session, self.repo_path)
        await reasoner.initialize()

        query = parameters.get("query", "")
        target = parameters.get("target")

        result = await reasoner.reason(
            query=query,
            target_path=target
        )

        return result

    async def _handle_build_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle build/test actions."""
        import subprocess

        if action_type == "run_tests":
            test_path = parameters.get("path", ".")
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }

        elif action_type == "run_lint":
            result = subprocess.run(
                ["python", "-m", "flake8", "."],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.repo_path)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }

        return {"error": f"Unknown build action: {action_type}"}

    async def _handle_git_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle version control actions."""
        if not self._version_control:
            return {"error": "Version control not available"}

        if action_type == "git_status":
            return self._version_control.get_status()

        elif action_type == "git_commit":
            message = parameters.get("message", "Auto-commit")
            files = parameters.get("files", [])

            # Stage files
            for file_path in files:
                self._version_control.stage_file(file_path)

            # Commit
            result = self._version_control.commit(message)
            return result

        elif action_type == "git_diff":
            return self._version_control.get_diff()

        return {"error": f"Unknown git action: {action_type}"}

    async def _handle_librarian_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle librarian actions."""
        if not self._librarian:
            return {"error": "Librarian not available"}

        if action_type == "librarian_search":
            query = parameters.get("query", "")
            return await self._librarian.search(query)

        elif action_type == "librarian_ingest":
            file_path = parameters.get("file_path")
            return await self._librarian.ingest_document(file_path)

        return {"error": f"Unknown librarian action: {action_type}"}

    async def _handle_learning_action(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle learning actions."""
        if action_type == "learn_from_feedback":
            feedback = parameters.get("feedback", "")
            example = parameters.get("example")

            # Store in learning memory
            if self._failure_learning:
                return await self._failure_learning.store_learning(
                    feedback=feedback,
                    example=example
                )

        elif action_type == "learn_status":
            return self._failure_learning.get_learning_status() if self._failure_learning else {}

        return {"error": f"Unknown learning action: {action_type}"}

    async def _handle_self_update(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle self-update action."""
        if not self._self_updater:
            return {"error": "Self-updater not available"}

        update_type = parameters.get("type", "patch")
        description = parameters.get("description", "")

        result = await self._self_updater.perform_update(
            update_type=update_type,
            description=description
        )

        self.metrics["self_updates"] += 1

        return result

    async def _track_mutations(
        self,
        files_changed: List[str],
        genesis_key: Any
    ):
        """Track file mutations after genesis key creation."""
        if not self._mutation_tracker:
            return

        for file_path in files_changed:
            await self._mutation_tracker.track_mutation(
                file_path=file_path,
                genesis_key_id=genesis_key.key_id if genesis_key else None
            )

            if self._ide_session:
                self._ide_session.mutations_tracked += 1

        self.metrics["mutations_tracked"] += len(files_changed)

    # =========================================================================
    # Layer 1/2 Integration
    # =========================================================================

    async def process_input(
        self,
        input_text: str,
        input_type: str = "text",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process input through Layer 1 (Universal Input).

        Routes to appropriate processor based on input type and content.
        """
        if not self._layer1:
            return {"error": "Layer 1 not initialized"}

        # Process through Layer 1
        layer1_result = await self._layer1.process_input(
            input_text=input_text,
            input_type=input_type,
            context=context
        )

        # If cognitive processing needed, pass to Layer 2
        if layer1_result.get("requires_cognition"):
            layer2_result = await self._layer2.process(
                intent=layer1_result.get("intent"),
                entities=layer1_result.get("entities"),
                context=context
            )
            return {**layer1_result, "cognitive_result": layer2_result}

        return layer1_result

    async def get_cognitive_insight(
        self,
        query: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get cognitive insight using multi-plane reasoning."""
        if not self._cognitive:
            return {"error": "Cognitive framework not initialized"}

        return await self._cognitive.analyze(query, context)

    # =========================================================================
    # Status & Metrics
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get full IDE status."""
        return {
            "session": self._ide_session.to_dict() if self._ide_session else None,
            "systems": {
                "layer1": self._layer1 is not None,
                "layer2": self._layer2 is not None,
                "cognitive": self._cognitive is not None,
                "genesis": self._genesis_service is not None,
                "ghost_ledger": self._ghost_ledger is not None,
                "healing": self._healing_system is not None,
                "librarian": self._librarian is not None,
                "file_manager": self._file_manager is not None,
                "version_control": self._version_control is not None,
                "cicd": self._cicd_pipeline is not None,
                "scheduler": self._scheduler is not None,
                "vector_db": self._vector_db is not None,
                "failure_learning": self._failure_learning is not None,
                "mutation_tracker": self._mutation_tracker is not None,
                "self_updater": self._self_updater is not None
            },
            "metrics": self.metrics,
            "scheduler_status": self._scheduler.get_status() if self._scheduler else None
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        return {
            **self.metrics,
            "scheduler": self._scheduler.get_metrics() if self._scheduler else {},
            "healing": self._healing_system.get_statistics() if hasattr(self._healing_system, 'get_statistics') else {},
            "ghost_ledger": self._ghost_ledger.get_statistics() if self._ghost_ledger else {}
        }

    async def shutdown(self):
        """Shutdown all systems gracefully."""
        logger.info("[GENESIS-IDE] Shutting down...")

        # End session if active
        if self._ide_session:
            await self.end_session()

        # Stop scheduler
        if self._scheduler:
            await self._scheduler.stop()

        # Stop IDE bridge
        if self._ide_bridge:
            await self._ide_bridge.shutdown()

        # Persist ghost ledger
        if self._ghost_ledger:
            await self._ghost_ledger.persist()

        logger.info("[GENESIS-IDE] Shutdown complete")
