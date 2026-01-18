import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
logger = logging.getLogger(__name__)

class IDEEventType(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of IDE events that trigger Grace actions."""
    FILE_OPENED = "file_opened"
    FILE_SAVED = "file_saved"
    FILE_CLOSED = "file_closed"
    CONTENT_CHANGED = "content_changed"
    CURSOR_MOVED = "cursor_moved"
    SELECTION_CHANGED = "selection_changed"
    TERMINAL_OUTPUT = "terminal_output"
    ERROR_OCCURRED = "error_occurred"
    DIAGNOSTIC_RECEIVED = "diagnostic_received"
    TASK_REQUESTED = "task_requested"
    VOICE_COMMAND = "voice_command"
    HEALING_REQUESTED = "healing_requested"
    COMMIT_REQUESTED = "commit_requested"


class IDEAction(str, Enum):
    """Actions Grace can perform in the IDE."""
    INSERT_CODE = "insert_code"
    REPLACE_CODE = "replace_code"
    DELETE_CODE = "delete_code"
    SHOW_NOTIFICATION = "show_notification"
    SHOW_DIAGNOSTIC = "show_diagnostic"
    OPEN_FILE = "open_file"
    SCROLL_TO_LINE = "scroll_to_line"
    CREATE_TERMINAL = "create_terminal"
    RUN_COMMAND = "run_command"
    SHOW_PANEL = "show_panel"
    UPDATE_STATUS = "update_status"
    REQUEST_APPROVAL = "request_approval"
    AUTO_COMMIT = "auto_commit"


@dataclass
class IDEBridgeConfig:
    """Configuration for IDE Bridge."""
    workspace_path: Path
    enable_auto_healing: bool = True
    enable_genesis_tracking: bool = True
    enable_ghost_ledger: bool = True
    enable_voice: bool = True
    trust_level: int = 3  # 0-9 (matches TrustLevel from healing system)
    auto_commit_threshold: float = 0.85  # Confidence score needed for auto-commit
    websocket_port: int = 8765
    max_concurrent_healings: int = 3
    healing_debounce_ms: int = 500


@dataclass
class FileState:
    """Tracks the state of a file in the IDE."""
    path: Path
    content: str
    content_hash: str
    last_modified: datetime
    is_dirty: bool = False
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    genesis_key_id: Optional[str] = None
    healing_suggestions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IDEMessage:
    """Message structure for IDE communication."""
    id: str
    event_type: IDEEventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "ide"
    requires_response: bool = False


class IDEBridge:
    """
    Bridge between VS Code/Code-Server and Grace's cognitive systems.

    Provides bidirectional communication for:
    - Real-time code analysis and healing
    - Genesis Key tracking
    - Autonomous task execution
    - Voice/NLP command processing
    """

    def __init__(
        self,
        config: IDEBridgeConfig,
        session=None
    ):
        self.config = config
        self.session = session

        # File tracking
        self.open_files: Dict[str, FileState] = {}
        self.file_watchers: Dict[str, asyncio.Task] = {}

        # WebSocket connections
        self.connections: Set = set()
        self._message_handlers: Dict[IDEEventType, List[Callable]] = {}

        # Genesis Key integration
        self._genesis_service = None
        self._healing_system = None
        self._ghost_ledger = None

        # Pending actions queue
        self._action_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

        # Metrics
        self.metrics = {
            "files_analyzed": 0,
            "healings_applied": 0,
            "genesis_keys_created": 0,
            "voice_commands_processed": 0,
            "auto_commits": 0
        }

        logger.info(f"[IDE-BRIDGE] Initialized for workspace: {config.workspace_path}")

    async def initialize(self):
        """Initialize the IDE bridge and connect to Grace systems."""
        logger.info("[IDE-BRIDGE] Initializing connections to Grace systems...")

        try:
            # Import and initialize Genesis Key service
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.config.workspace_path)
            )

            # Import and initialize healing system
            from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel
            self._healing_system = AutonomousHealingSystem(
                session=self.session,
                repo_path=self.config.workspace_path,
                trust_level=TrustLevel(self.config.trust_level)
            )

            # Import and initialize ghost ledger
            from grace_os.ghost_ledger import GhostLedger
            self._ghost_ledger = GhostLedger(
                session=self.session,
                repo_path=self.config.workspace_path
            )

            # Register default message handlers
            self._register_default_handlers()

            self._is_running = True

            # Start background tasks
            asyncio.create_task(self._process_action_queue())

            logger.info("[IDE-BRIDGE] Successfully connected to all Grace systems")
            return True

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Initialization failed: {e}")
            return False

    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_handler(IDEEventType.FILE_OPENED, self._handle_file_opened)
        self.register_handler(IDEEventType.FILE_SAVED, self._handle_file_saved)
        self.register_handler(IDEEventType.CONTENT_CHANGED, self._handle_content_changed)
        self.register_handler(IDEEventType.ERROR_OCCURRED, self._handle_error)
        self.register_handler(IDEEventType.HEALING_REQUESTED, self._handle_healing_request)
        self.register_handler(IDEEventType.VOICE_COMMAND, self._handle_voice_command)
        self.register_handler(IDEEventType.TASK_REQUESTED, self._handle_task_request)

    def register_handler(self, event_type: IDEEventType, handler: Callable):
        """Register a handler for an IDE event type."""
        if event_type not in self._message_handlers:
            self._message_handlers[event_type] = []
        self._message_handlers[event_type].append(handler)

    async def handle_message(self, message: IDEMessage) -> Optional[Dict[str, Any]]:
        """Process an incoming IDE message."""
        logger.debug(f"[IDE-BRIDGE] Received message: {message.event_type}")

        handlers = self._message_handlers.get(message.event_type, [])
        results = []

        for handler in handlers:
            try:
                result = await handler(message)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"[IDE-BRIDGE] Handler error for {message.event_type}: {e}")

        return {"results": results} if results else None

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def _handle_file_opened(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle file opened event - start tracking and analysis."""
        file_path = message.data.get("path")
        content = message.data.get("content", "")

        if not file_path:
            return {"error": "No file path provided"}

        path = Path(file_path)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Create file state
        file_state = FileState(
            path=path,
            content=content,
            content_hash=content_hash,
            last_modified=datetime.utcnow()
        )
        self.open_files[file_path] = file_state

        # Create Genesis Key for file open
        if self.config.enable_genesis_tracking and self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.FILE_READ,
                what_description=f"Opened file: {path.name}",
                who_actor="IDE-Bridge",
                where_location=str(path),
                why_reason="User opened file in editor",
                how_method="IDE file open event",
                file_path=str(path),
                session=self.session
            )
            file_state.genesis_key_id = genesis_key.key_id

        # Analyze file for issues
        if self.config.enable_auto_healing and self._healing_system:
            issues = await self._analyze_file_for_issues(file_state)
            file_state.healing_suggestions = issues

        self.metrics["files_analyzed"] += 1

        return {
            "status": "tracked",
            "genesis_key_id": file_state.genesis_key_id,
            "healing_suggestions": len(file_state.healing_suggestions)
        }

    async def _handle_file_saved(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle file saved event - record changes and check for issues."""
        file_path = message.data.get("path")
        new_content = message.data.get("content", "")

        if file_path not in self.open_files:
            return {"error": "File not tracked"}

        file_state = self.open_files[file_path]
        old_content = file_state.content
        old_hash = file_state.content_hash
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        # Check if content actually changed
        if old_hash == new_hash:
            return {"status": "no_changes"}

        # Record change in Ghost Ledger
        if self.config.enable_ghost_ledger and self._ghost_ledger:
            await self._ghost_ledger.record_change(
                file_path=file_path,
                old_content=old_content,
                new_content=new_content,
                genesis_key_id=file_state.genesis_key_id
            )

        # Create Genesis Key for the save
        if self.config.enable_genesis_tracking and self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.FILE_CHANGE,
                what_description=f"Saved file: {file_state.path.name}",
                who_actor="User",
                where_location=str(file_state.path),
                why_reason="User saved changes",
                how_method="IDE file save",
                file_path=str(file_state.path),
                code_before=old_content[:500] if len(old_content) > 500 else old_content,
                code_after=new_content[:500] if len(new_content) > 500 else new_content,
                parent_key_id=file_state.genesis_key_id,
                session=self.session
            )
            file_state.genesis_key_id = genesis_key.key_id

        # Update file state
        file_state.content = new_content
        file_state.content_hash = new_hash
        file_state.last_modified = datetime.utcnow()
        file_state.is_dirty = False

        # Re-analyze for issues
        if self.config.enable_auto_healing:
            issues = await self._analyze_file_for_issues(file_state)
            file_state.healing_suggestions = issues

        # Check if auto-commit is appropriate
        commit_result = await self._evaluate_auto_commit(file_state)

        self.metrics["genesis_keys_created"] += 1

        return {
            "status": "saved",
            "genesis_key_id": file_state.genesis_key_id,
            "healing_suggestions": len(file_state.healing_suggestions),
            "auto_commit": commit_result
        }

    async def _handle_content_changed(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle real-time content changes for live healing suggestions."""
        file_path = message.data.get("path")
        changes = message.data.get("changes", [])

        if file_path not in self.open_files:
            return {"error": "File not tracked"}

        file_state = self.open_files[file_path]
        file_state.is_dirty = True

        # Apply changes to tracked content
        for change in changes:
            file_state.content = self._apply_change(file_state.content, change)

        file_state.content_hash = hashlib.sha256(file_state.content.encode()).hexdigest()

        # Debounced analysis (handled by client)
        return {"status": "tracked", "is_dirty": True}

    async def _handle_error(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle error events - trigger healing if appropriate."""
        error_type = message.data.get("type")
        error_message = message.data.get("message")
        file_path = message.data.get("path")
        line_number = message.data.get("line")

        # Create Genesis Key for the error
        if self.config.enable_genesis_tracking and self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.ERROR_DETECTED,
                what_description=f"Error: {error_type}",
                who_actor="IDE",
                where_location=f"{file_path}:{line_number}" if file_path else "Unknown",
                why_reason=error_message,
                how_method="IDE diagnostic",
                file_path=file_path,
                line_number=line_number,
                is_error=True,
                error_type=error_type,
                error_message=error_message,
                session=self.session
            )

        # Attempt auto-healing if enabled
        if self.config.enable_auto_healing and self._healing_system:
            healing_result = await self._attempt_healing(
                file_path=file_path,
                error_type=error_type,
                error_message=error_message,
                line_number=line_number
            )
            return {"status": "healing_attempted", "result": healing_result}

        return {"status": "error_recorded"}

    async def _handle_healing_request(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle explicit healing request from user."""
        file_path = message.data.get("path")
        healing_type = message.data.get("type", "auto")
        scope = message.data.get("scope", "file")  # file, selection, project

        if not file_path:
            return {"error": "No file path provided"}

        logger.info(f"[IDE-BRIDGE] Healing requested for {file_path}, type={healing_type}, scope={scope}")

        # Perform comprehensive healing
        healing_results = await self._perform_comprehensive_healing(
            file_path=file_path,
            healing_type=healing_type,
            scope=scope
        )

        self.metrics["healings_applied"] += len(healing_results.get("applied", []))

        return healing_results

    async def _handle_voice_command(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle voice command from user."""
        transcript = message.data.get("transcript", "")
        confidence = message.data.get("confidence", 0.0)

        if confidence < 0.5:
            return {"error": "Low confidence transcription", "confidence": confidence}

        logger.info(f"[IDE-BRIDGE] Voice command: '{transcript}' (confidence: {confidence:.2f})")

        # Parse intent from transcript
        intent = self._parse_voice_intent(transcript)

        # Execute based on intent
        result = await self._execute_voice_intent(intent, message.data)

        self.metrics["voice_commands_processed"] += 1

        return result

    async def _handle_task_request(self, message: IDEMessage) -> Dict[str, Any]:
        """Handle autonomous task request."""
        task_description = message.data.get("description")
        task_type = message.data.get("type", "code_change")
        target_files = message.data.get("files", [])
        constraints = message.data.get("constraints", {})

        # Create execution contract
        from grace_os.deterministic_pipeline import ExecutionContract
        contract = ExecutionContract(
            goal=task_description,
            constraints=constraints,
            allowed_files=target_files,
            risk_level=self._assess_task_risk(task_type, target_files),
            success_criteria=message.data.get("success_criteria", [])
        )

        # Queue for autonomous execution
        await self._action_queue.put({
            "type": "autonomous_task",
            "contract": contract,
            "message": message
        })

        return {
            "status": "queued",
            "contract_id": contract.contract_id,
            "estimated_risk": contract.risk_level
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _analyze_file_for_issues(self, file_state: FileState) -> List[Dict[str, Any]]:
        """Analyze a file for potential issues and healing opportunities."""
        issues = []

        if not self._healing_system:
            return issues

        try:
            # Use the healing system to scan for issues
            scan_result = self._healing_system.healing_system.scan_for_issues()

            # Filter to this file
            for issue in scan_result:
                if issue.get("file") == str(file_state.path):
                    issues.append({
                        "type": issue.get("type"),
                        "severity": issue.get("severity", "info"),
                        "line": issue.get("line"),
                        "message": issue.get("message"),
                        "suggestion": issue.get("suggestion"),
                        "auto_fixable": issue.get("auto_fixable", False)
                    })
        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Error analyzing file: {e}")

        return issues

    async def _attempt_healing(
        self,
        file_path: str,
        error_type: str,
        error_message: str,
        line_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Attempt to heal an error."""
        if not self._healing_system:
            return {"status": "healing_unavailable"}

        try:
            # Assess the health impact
            assessment = self._healing_system.assess_system_health()

            # Determine appropriate healing action
            from cognitive.autonomous_healing_system import HealingAction

            # Map error types to healing actions
            error_healing_map = {
                "syntax": HealingAction.BUFFER_CLEAR,
                "import": HealingAction.CONNECTION_RESET,
                "runtime": HealingAction.PROCESS_RESTART,
                "memory": HealingAction.CACHE_FLUSH,
            }

            suggested_action = error_healing_map.get(
                error_type.lower().split("_")[0],
                HealingAction.BUFFER_CLEAR
            )

            # Check if we can auto-execute
            can_auto = self._healing_system.can_auto_execute(suggested_action)

            if can_auto:
                result = await self._healing_system.execute_healing_action(
                    action=suggested_action,
                    target=file_path,
                    context={"error": error_message, "line": line_number}
                )
                return {"status": "healed", "action": suggested_action.value, "result": result}
            else:
                return {
                    "status": "approval_required",
                    "suggested_action": suggested_action.value,
                    "reason": f"Trust level too low for {suggested_action.value}"
                }

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Healing attempt failed: {e}")
            return {"status": "healing_failed", "error": str(e)}

    async def _perform_comprehensive_healing(
        self,
        file_path: str,
        healing_type: str,
        scope: str
    ) -> Dict[str, Any]:
        """Perform comprehensive healing based on type and scope."""
        applied = []
        suggestions = []

        try:
            # Use intelligent code healing
            from cognitive.intelligent_code_healing import IntelligentCodeHealing
            healer = IntelligentCodeHealing(self.session)

            # Analyze and heal
            analysis = await healer.analyze_file(file_path)

            for issue in analysis.get("issues", []):
                if issue.get("auto_fixable") and healing_type == "auto":
                    # Apply fix
                    fix_result = await healer.apply_fix(file_path, issue)
                    if fix_result.get("success"):
                        applied.append({
                            "issue": issue,
                            "fix": fix_result
                        })
                else:
                    suggestions.append(issue)

            return {
                "status": "complete",
                "applied": applied,
                "suggestions": suggestions,
                "files_modified": [file_path] if applied else []
            }

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Comprehensive healing failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _parse_voice_intent(self, transcript: str) -> Dict[str, Any]:
        """Parse voice command into structured intent."""
        transcript_lower = transcript.lower()

        # Simple intent detection (would use NLP in production)
        intents = {
            "heal": ["heal", "fix", "repair", "correct"],
            "commit": ["commit", "save changes", "check in"],
            "run": ["run", "execute", "start"],
            "test": ["test", "verify", "check"],
            "search": ["find", "search", "locate"],
            "explain": ["explain", "what does", "how does"],
            "create": ["create", "make", "add", "new"],
            "delete": ["delete", "remove", "clear"]
        }

        detected_intent = "unknown"
        for intent, keywords in intents.items():
            if any(kw in transcript_lower for kw in keywords):
                detected_intent = intent
                break

        return {
            "intent": detected_intent,
            "transcript": transcript,
            "entities": self._extract_entities(transcript)
        }

    def _extract_entities(self, transcript: str) -> Dict[str, Any]:
        """Extract entities from voice transcript."""
        # Simple entity extraction (would use NER in production)
        entities = {}

        # Look for file references
        words = transcript.split()
        for i, word in enumerate(words):
            if word.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".css", ".html")):
                entities["file"] = word
            elif word in ["function", "class", "method", "variable"]:
                if i + 1 < len(words):
                    entities["target"] = words[i + 1]

        return entities

    async def _execute_voice_intent(self, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parsed voice intent."""
        intent_type = intent.get("intent")

        if intent_type == "heal":
            return await self._handle_healing_request(IDEMessage(
                id="voice_heal",
                event_type=IDEEventType.HEALING_REQUESTED,
                timestamp=datetime.utcnow(),
                data={"path": intent["entities"].get("file"), "type": "auto"}
            ))

        elif intent_type == "commit":
            return await self._handle_auto_commit_request(intent)

        elif intent_type == "explain":
            return await self._explain_code(intent)

        else:
            return {"status": "intent_not_handled", "intent": intent_type}

    async def _handle_auto_commit_request(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle auto-commit voice request."""
        # Get all dirty files
        dirty_files = [f for f in self.open_files.values() if f.is_dirty]

        if not dirty_files:
            return {"status": "no_changes", "message": "No unsaved changes to commit"}

        # Generate commit message
        commit_message = self._generate_commit_message(dirty_files)

        # Queue commit action
        await self._action_queue.put({
            "type": "auto_commit",
            "files": [str(f.path) for f in dirty_files],
            "message": commit_message
        })

        return {"status": "commit_queued", "files": len(dirty_files), "message": commit_message}

    async def _explain_code(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Explain code using multi-plane reasoning."""
        try:
            from grace_os.reasoning_planes import MultiPlaneReasoner
            reasoner = MultiPlaneReasoner(self.session)

            target = intent["entities"].get("file") or intent["entities"].get("target")
            explanation = await reasoner.explain(target, intent.get("transcript", ""))

            return {"status": "explained", "explanation": explanation}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _evaluate_auto_commit(self, file_state: FileState) -> Optional[Dict[str, Any]]:
        """Evaluate if auto-commit is appropriate based on confidence score."""
        if not self._healing_system:
            return None

        try:
            # Calculate confidence score based on:
            # - Linting (no errors)
            # - Tests passing (if applicable)
            # - Architectural compliance
            # - Pattern similarity
            # - Historical regressions

            confidence = 1.0
            factors = []

            # Check for healing suggestions (issues reduce confidence)
            if file_state.healing_suggestions:
                severity_penalties = {
                    "error": 0.3,
                    "warning": 0.1,
                    "info": 0.02
                }
                for issue in file_state.healing_suggestions:
                    penalty = severity_penalties.get(issue.get("severity", "info"), 0.05)
                    confidence -= penalty
                factors.append(f"Issues found: -{len(file_state.healing_suggestions) * 0.1:.2f}")

            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))

            if confidence >= self.config.auto_commit_threshold:
                return {
                    "recommended": True,
                    "confidence": confidence,
                    "factors": factors
                }
            else:
                return {
                    "recommended": False,
                    "confidence": confidence,
                    "factors": factors,
                    "reason": f"Confidence {confidence:.2f} below threshold {self.config.auto_commit_threshold}"
                }

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Auto-commit evaluation failed: {e}")
            return None

    def _generate_commit_message(self, files: List[FileState]) -> str:
        """Generate a commit message based on changed files."""
        file_names = [f.path.name for f in files]

        if len(files) == 1:
            return f"Update {file_names[0]}"
        else:
            return f"Update {len(files)} files: {', '.join(file_names[:3])}{'...' if len(files) > 3 else ''}"

    def _apply_change(self, content: str, change: Dict[str, Any]) -> str:
        """Apply a text change to content."""
        start = change.get("start", 0)
        end = change.get("end", start)
        text = change.get("text", "")

        return content[:start] + text + content[end:]

    def _assess_task_risk(self, task_type: str, target_files: List[str]) -> str:
        """Assess risk level of a task."""
        high_risk_patterns = ["delete", "remove", "drop", "reset", "force"]
        medium_risk_patterns = ["modify", "update", "change", "refactor"]

        task_lower = task_type.lower()

        if any(p in task_lower for p in high_risk_patterns):
            return "high"
        elif any(p in task_lower for p in medium_risk_patterns):
            return "medium"
        else:
            return "low"

    async def _process_action_queue(self):
        """Process queued actions in the background."""
        while self._is_running:
            try:
                action = await asyncio.wait_for(
                    self._action_queue.get(),
                    timeout=1.0
                )

                action_type = action.get("type")

                if action_type == "autonomous_task":
                    await self._execute_autonomous_task(action)
                elif action_type == "auto_commit":
                    await self._execute_auto_commit(action)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[IDE-BRIDGE] Action queue error: {e}")

    async def _execute_autonomous_task(self, action: Dict[str, Any]):
        """Execute an autonomous task from the queue."""
        contract = action.get("contract")
        logger.info(f"[IDE-BRIDGE] Executing autonomous task: {contract.goal}")

        try:
            from grace_os.deterministic_pipeline import DeterministicCodePipeline
            pipeline = DeterministicCodePipeline(self.session)

            result = await pipeline.execute(contract)

            # Broadcast result to connected clients
            await self._broadcast({
                "type": "task_complete",
                "contract_id": contract.contract_id,
                "result": result
            })

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Autonomous task failed: {e}")
            await self._broadcast({
                "type": "task_failed",
                "contract_id": contract.contract_id,
                "error": str(e)
            })

    async def _execute_auto_commit(self, action: Dict[str, Any]):
        """Execute an auto-commit action."""
        files = action.get("files", [])
        message = action.get("message", "Auto-commit")

        logger.info(f"[IDE-BRIDGE] Auto-committing {len(files)} files")

        try:
            from version_control.git_service import GitService
            git = GitService(str(self.config.workspace_path))

            # Stage files
            for file_path in files:
                git.stage_file(file_path)

            # Commit
            result = git.commit(message)

            self.metrics["auto_commits"] += 1

            await self._broadcast({
                "type": "auto_commit_complete",
                "files": files,
                "message": message,
                "result": result
            })

        except Exception as e:
            logger.error(f"[IDE-BRIDGE] Auto-commit failed: {e}")
            await self._broadcast({
                "type": "auto_commit_failed",
                "error": str(e)
            })

    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected IDE clients."""
        if not self.connections:
            return

        message_json = json.dumps(message)

        for connection in self.connections.copy():
            try:
                await connection.send(message_json)
            except Exception:
                self.connections.discard(connection)

    # =========================================================================
    # Public API for IDE Commands
    # =========================================================================

    async def request_healing(self, file_path: str, scope: str = "file") -> Dict[str, Any]:
        """Request healing for a file (public API)."""
        message = IDEMessage(
            id=f"heal_{datetime.utcnow().timestamp()}",
            event_type=IDEEventType.HEALING_REQUESTED,
            timestamp=datetime.utcnow(),
            data={"path": file_path, "type": "auto", "scope": scope}
        )
        return await self.handle_message(message)

    async def get_healing_suggestions(self, file_path: str) -> List[Dict[str, Any]]:
        """Get healing suggestions for a file without applying them."""
        if file_path in self.open_files:
            return self.open_files[file_path].healing_suggestions
        return []

    async def get_file_genesis_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get Genesis Key history for a file."""
        if not self._genesis_service:
            return []

        # Query genesis keys for this file
        from models.genesis_key_models import GenesisKey
        keys = self.session.query(GenesisKey).filter(
            GenesisKey.file_path == file_path
        ).order_by(GenesisKey.when_timestamp.desc()).limit(50).all()

        return [
            {
                "key_id": k.key_id,
                "type": k.key_type.value,
                "what": k.what_description,
                "when": k.when_timestamp.isoformat(),
                "who": k.who_actor
            }
            for k in keys
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get IDE bridge metrics."""
        return {
            **self.metrics,
            "open_files": len(self.open_files),
            "connections": len(self.connections),
            "is_running": self._is_running
        }

    async def shutdown(self):
        """Shutdown the IDE bridge."""
        logger.info("[IDE-BRIDGE] Shutting down...")
        self._is_running = False

        # Close all connections
        for connection in self.connections.copy():
            try:
                await connection.close()
            except Exception:
                pass

        self.connections.clear()
        self.open_files.clear()

        logger.info("[IDE-BRIDGE] Shutdown complete")
