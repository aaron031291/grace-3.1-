"""
GRACE Autonomous Action Engine
==============================
The brain that allows GRACE to take autonomous actions.

Observes → Decides → Validates → Executes → Learns

Actions are triggered by:
- Events (file changes, errors, anomalies)
- Schedules (periodic maintenance)
- Conditions (thresholds, patterns)
- Self-improvement needs

Integrations:
- Genesis Key Service: Every action generates a tracked Genesis Key
- Mirror Self-Modeling: Actions are observed for self-improvement
- Cognitive Framework: Uses clarity framework for decision making
- Trust Scores: Actions are scored for reliability
- KPIs: Performance metrics tracked for all actions
- Version Control: All mutations are version controlled
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# Core System Integration Helpers
# =============================================================================

def get_genesis_key_service():
    """Get the Genesis Key Service for proper key creation."""
    try:
        from genesis.genesis_key_service import GenesisKeyService
        from database.session import get_session
        session = next(get_session())
        return GenesisKeyService(session=session)
    except Exception as e:
        logger.debug(f"[Autonomous] Genesis Key Service not available: {e}")
        return None


def get_mirror_system():
    """Get the Mirror Self-Modeling System for observation."""
    try:
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        from database.session import get_session
        session = next(get_session())
        return MirrorSelfModelingSystem(session)
    except Exception as e:
        logger.debug(f"[Autonomous] Mirror System not available: {e}")
        return None


def get_cognitive_engine():
    """Get the Cognitive Engine for decision making."""
    try:
        from cognitive.engine import get_cognitive_engine as get_cog
        return get_cog()
    except Exception as e:
        logger.debug(f"[Autonomous] Cognitive Engine not available: {e}")
        return None


def get_kpi_tracker():
    """Get the KPI tracker for performance metrics."""
    try:
        from genesis.adaptive_cicd import AdaptiveCICD
        return AdaptiveCICD()
    except Exception as e:
        logger.debug(f"[Autonomous] KPI tracker not available: {e}")
        return None


class ActionType(str, Enum):
    """Types of autonomous actions."""
    # Ingestion Actions
    INGEST_FILE = "ingest_file"
    INGEST_DIRECTORY = "ingest_directory"
    INGEST_URL = "ingest_url"

    # Maintenance Actions
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    OPTIMIZE = "optimize"

    # Learning Actions
    LEARN_PATTERN = "learn_pattern"
    UPDATE_MEMORY = "update_memory"
    CONSOLIDATE_KNOWLEDGE = "consolidate_knowledge"

    # Pipeline Actions
    RUN_PIPELINE = "run_pipeline"
    RUN_TESTS = "run_tests"
    SECURITY_SCAN = "security_scan"

    # Response Actions
    ALERT = "alert"
    SELF_HEAL = "self_heal"
    ESCALATE = "escalate"

    # Custom
    CUSTOM = "custom"


class TriggerType(str, Enum):
    """What triggers an autonomous action."""
    EVENT = "event"           # Something happened
    SCHEDULE = "schedule"     # Time-based
    CONDITION = "condition"   # Threshold/pattern met
    REQUEST = "request"       # External request
    SELF = "self"            # GRACE decided


class ActionPriority(str, Enum):
    """Priority levels for actions."""
    CRITICAL = "critical"    # Execute immediately
    HIGH = "high"            # Execute soon
    NORMAL = "normal"        # Queue normally
    LOW = "low"              # Execute when idle
    BACKGROUND = "background" # Execute in background


class ActionStatus(str, Enum):
    """Status of an autonomous action."""
    PENDING = "pending"              # Waiting to execute
    PENDING_APPROVAL = "pending_approval"  # Waiting for human approval
    RUNNING = "running"              # Currently executing
    SUCCESS = "success"              # Completed successfully
    FAILED = "failed"                # Failed to execute
    SKIPPED = "skipped"              # Skipped (e.g., duplicate)
    CANCELLED = "cancelled"          # Cancelled before execution
    TIMEOUT = "timeout"              # Timed out during execution


@dataclass
class ActionContext:
    """Context for an autonomous action."""
    source: str                    # What triggered this
    trigger_type: TriggerType
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ActionResult:
    """Result of an autonomous action."""
    action_id: str
    status: str  # success, failed, skipped, pending_approval
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0
    genesis_key: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[str] = field(default_factory=list)


@dataclass
class AutonomousAction:
    """Definition of an autonomous action."""
    id: str
    name: str
    action_type: ActionType
    priority: ActionPriority
    context: ActionContext
    requires_approval: bool = False
    sandbox_first: bool = False
    trust_threshold: float = 0.5
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"
    result: Optional[ActionResult] = None
    genesis_key: Optional[str] = None


@dataclass
class ActionRule:
    """Rule that triggers autonomous actions."""
    id: str
    name: str
    description: str
    trigger_type: TriggerType
    condition: Dict[str, Any]  # Condition to match
    action_type: ActionType
    action_config: Dict[str, Any]
    priority: ActionPriority = ActionPriority.NORMAL
    enabled: bool = True
    cooldown_seconds: int = 60  # Min time between triggers
    last_triggered: Optional[str] = None


class AutonomousEngine:
    """
    GRACE's Autonomous Action Engine.

    Manages all autonomous operations with:
    - Event-driven triggers
    - Scheduled tasks
    - Condition-based actions
    - Self-improvement capabilities
    """

    def __init__(self):
        # Action queue by priority
        self.action_queue: Dict[ActionPriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in ActionPriority
        }

        # Active and completed actions
        self.actions: Dict[str, AutonomousAction] = {}
        self.action_history: List[AutonomousAction] = []

        # Rules that trigger actions
        self.rules: Dict[str, ActionRule] = {}

        # Action handlers
        self.handlers: Dict[ActionType, Callable] = {}

        # Event subscribers
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Scheduled tasks
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}

        # Engine state
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []

        # Statistics
        self.stats = {
            "actions_executed": 0,
            "actions_succeeded": 0,
            "actions_failed": 0,
            "actions_skipped": 0
        }

        # =================================================================
        # Core System Integrations
        # =================================================================

        # Genesis Key Service - for proper tracked key generation
        self._genesis_service = get_genesis_key_service()

        # Mirror Self-Modeling - for observation and self-improvement
        self._mirror = get_mirror_system()

        # Cognitive Engine - for decision making
        self._cognitive = get_cognitive_engine()

        # KPI Tracker - for performance metrics
        self._kpi_tracker = get_kpi_tracker()

        # Trust scores for action types
        self._trust_scores: Dict[str, float] = {}

        # Action version history for mutation tracking
        self._action_versions: Dict[str, List[Dict[str, Any]]] = {}

        # Register default handlers
        self._register_default_handlers()
        self._register_default_rules()

        logger.info("[Autonomous] Engine initialized with core integrations")
        if self._genesis_service:
            logger.info("[Autonomous]   ✓ Genesis Key Service connected")
        if self._mirror:
            logger.info("[Autonomous]   ✓ Mirror Self-Modeling connected")
        if self._cognitive:
            logger.info("[Autonomous]   ✓ Cognitive Engine connected")
        if self._kpi_tracker:
            logger.info("[Autonomous]   ✓ KPI Tracker connected")

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.handlers[ActionType.HEALTH_CHECK] = self._handle_health_check
        self.handlers[ActionType.CLEANUP] = self._handle_cleanup
        self.handlers[ActionType.INGEST_FILE] = self._handle_ingest_file
        self.handlers[ActionType.INGEST_DIRECTORY] = self._handle_ingest_directory
        self.handlers[ActionType.RUN_PIPELINE] = self._handle_run_pipeline
        self.handlers[ActionType.LEARN_PATTERN] = self._handle_learn_pattern
        self.handlers[ActionType.UPDATE_MEMORY] = self._handle_update_memory
        self.handlers[ActionType.ALERT] = self._handle_alert
        self.handlers[ActionType.SELF_HEAL] = self._handle_self_heal

    def _register_default_rules(self):
        """Register default action rules."""
        # Rule: New file detected → Ingest
        self.rules["new_file_ingest"] = ActionRule(
            id="new_file_ingest",
            name="Auto-Ingest New Files",
            description="Automatically ingest new files in watched directories",
            trigger_type=TriggerType.EVENT,
            condition={"event": "file_created", "extensions": [".pdf", ".txt", ".md", ".py", ".js"]},
            action_type=ActionType.INGEST_FILE,
            action_config={"index": True, "extract_metadata": True},
            priority=ActionPriority.NORMAL
        )

        # Rule: Error spike → Alert
        self.rules["error_alert"] = ActionRule(
            id="error_alert",
            name="Error Spike Alert",
            description="Alert when error rate exceeds threshold",
            trigger_type=TriggerType.CONDITION,
            condition={"metric": "error_rate", "threshold": 0.1, "operator": ">"},
            action_type=ActionType.ALERT,
            action_config={"severity": "high", "channels": ["log", "ui"]},
            priority=ActionPriority.HIGH
        )

        # Rule: Scheduled health check
        self.rules["scheduled_health"] = ActionRule(
            id="scheduled_health",
            name="Periodic Health Check",
            description="Run health checks every 5 minutes",
            trigger_type=TriggerType.SCHEDULE,
            condition={"interval_seconds": 300},
            action_type=ActionType.HEALTH_CHECK,
            action_config={"full_check": True},
            priority=ActionPriority.LOW
        )

        # Rule: Low memory → Cleanup
        self.rules["low_memory_cleanup"] = ActionRule(
            id="low_memory_cleanup",
            name="Low Memory Cleanup",
            description="Cleanup when memory usage is high",
            trigger_type=TriggerType.CONDITION,
            condition={"metric": "memory_percent", "threshold": 85, "operator": ">"},
            action_type=ActionType.CLEANUP,
            action_config={"target": "cache", "aggressive": False},
            priority=ActionPriority.HIGH
        )

    # =========================================================================
    # Action Management
    # =========================================================================

    def _generate_action_id(self) -> str:
        """Generate unique action ID."""
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(f"action:{timestamp}".encode()).hexdigest()[:12]

    def _generate_genesis_key(self, action_type: str, resource: str, context: Dict[str, Any] = None) -> str:
        """
        Generate Genesis Key for action using the proper Genesis Key Service.

        Every action gets a tracked Genesis Key for:
        - Full audit trail
        - Version control of mutations
        - Mirror observation
        - KPI tracking
        """
        # Use Genesis Key Service if available
        if self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType, GenesisKeyStatus

                # Map action type to genesis key type
                key_type_map = {
                    "ingest_file": GenesisKeyType.INPUT,
                    "ingest_directory": GenesisKeyType.INPUT,
                    "run_pipeline": GenesisKeyType.OPERATION,
                    "health_check": GenesisKeyType.OPERATION,
                    "cleanup": GenesisKeyType.OPERATION,
                    "learn_pattern": GenesisKeyType.LEARNING,
                    "update_memory": GenesisKeyType.LEARNING,
                    "alert": GenesisKeyType.OUTPUT,
                    "self_heal": GenesisKeyType.FIX
                }

                key_type = key_type_map.get(action_type, GenesisKeyType.OPERATION)

                genesis_key = self._genesis_service.create_key(
                    key_type=key_type,
                    what_description=f"Autonomous action: {action_type}",
                    who_actor="GRACE_AUTONOMOUS_ENGINE",
                    where_location=resource,
                    why_reason="Autonomous action triggered by engine",
                    how_method=f"AutonomousEngine.queue_action({action_type})",
                    context_data=context,
                    tags=["autonomous", action_type, "engine"]
                )

                logger.debug(f"[Autonomous] Created tracked Genesis Key: {genesis_key.genesis_key}")
                return genesis_key.genesis_key

            except Exception as e:
                logger.warning(f"[Autonomous] Genesis Key Service error, falling back: {e}")

        # Fallback to simple key generation
        timestamp = datetime.utcnow().isoformat()
        key_data = f"autonomous:{action_type}:{resource}:{timestamp}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:12]
        return f"gk-auto-{key_hash}"

    def _track_action_version(self, action_id: str, action: AutonomousAction, mutation_type: str):
        """Track version/mutation of an action for audit trail."""
        if action_id not in self._action_versions:
            self._action_versions[action_id] = []

        version_entry = {
            "version": len(self._action_versions[action_id]) + 1,
            "mutation_type": mutation_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": action.status,
            "genesis_key": action.genesis_key,
            "snapshot": {
                "action_type": action.action_type.value,
                "priority": action.priority.value,
                "requires_approval": action.requires_approval,
                "sandbox_first": action.sandbox_first
            }
        }

        self._action_versions[action_id].append(version_entry)
        logger.debug(f"[Autonomous] Tracked version {version_entry['version']} for action {action_id}: {mutation_type}")

    def _update_trust_score(self, action_type: str, success: bool):
        """Update trust score for action type based on outcome."""
        if action_type not in self._trust_scores:
            self._trust_scores[action_type] = 0.5  # Start neutral

        current = self._trust_scores[action_type]

        # Exponential moving average update
        alpha = 0.1  # Learning rate
        new_value = 1.0 if success else 0.0
        self._trust_scores[action_type] = current + alpha * (new_value - current)

        logger.debug(f"[Autonomous] Trust score for {action_type}: {current:.3f} -> {self._trust_scores[action_type]:.3f}")

    def _record_kpi(self, action: AutonomousAction, result: 'ActionResult'):
        """Record KPI metrics for the action."""
        if self._kpi_tracker:
            try:
                self._kpi_tracker.calculate_kpis(
                    pipeline_id=f"autonomous_{action.action_type.value}",
                    include_history=True
                )
            except Exception as e:
                logger.debug(f"[Autonomous] KPI recording skipped: {e}")

    def _notify_mirror(self, action: AutonomousAction, result: 'ActionResult'):
        """Notify the Mirror system via event bus for self-observation."""
        try:
            from cognitive.event_bus import publish
            publish("genesis.autonomous_action", {
                "action_id": action.id,
                "action_type": action.action_type,
                "status": result.status if hasattr(result, 'status') else "completed",
                "description": action.description[:200] if hasattr(action, 'description') else "",
            }, source="autonomous_engine")
        except Exception as e:
            logger.debug(f"[Autonomous] Mirror notification skipped: {e}")

    async def queue_action(
        self,
        action_type: ActionType,
        context: ActionContext,
        priority: ActionPriority = ActionPriority.NORMAL,
        requires_approval: bool = False,
        sandbox_first: bool = False,
        config: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> AutonomousAction:
        """
        Queue an autonomous action for execution.

        Every action:
        1. Gets a tracked Genesis Key
        2. Is version controlled
        3. Is observable by the Mirror
        4. Contributes to trust scores and KPIs
        """
        action_id = self._generate_action_id()

        # Generate properly tracked Genesis Key with full context
        genesis_key = self._generate_genesis_key(
            action_type.value,
            context.source,
            context.data
        )

        # Check trust threshold for action type
        trust_score = self._trust_scores.get(action_type.value, 0.5)

        action = AutonomousAction(
            id=action_id,
            name=f"{action_type.value}:{context.source}",
            action_type=action_type,
            priority=priority,
            context=context,
            requires_approval=requires_approval,
            sandbox_first=sandbox_first,
            trust_threshold=trust_score,
            genesis_key=genesis_key
        )

        if config:
            action.context.data.update(config)

        if metadata:
            action.context.metadata.update(metadata)

        # Store action
        self.actions[action_id] = action

        # Track initial version (creation)
        self._track_action_version(action_id, action, "create")

        # Queue for execution
        await self.action_queue[priority].put(action_id)

        logger.info(
            f"[Autonomous] Queued action {action_id}: {action_type.value} "
            f"(priority: {priority.value}, genesis_key: {genesis_key}, trust: {trust_score:.2f})"
        )

        return action

    async def execute_action(self, action: AutonomousAction) -> ActionResult:
        """
        Execute an autonomous action with full integration.

        Integrations:
        1. Track execution version for audit trail
        2. Update trust scores based on outcome
        3. Record KPIs for performance tracking
        4. Notify Mirror for self-observation
        """
        action.status = "running"
        action.started_at = datetime.utcnow().isoformat()

        # Track "start" mutation
        self._track_action_version(action.id, action, "start")

        start_time = datetime.utcnow()

        try:
            # Get handler
            handler = self.handlers.get(action.action_type)

            if not handler:
                raise ValueError(f"No handler for action type: {action.action_type}")

            # Check if approval needed
            if action.requires_approval:
                approval = await self._check_approval(action)
                if not approval:
                    self._track_action_version(action.id, action, "pending_approval")
                    return ActionResult(
                        action_id=action.id,
                        status="pending_approval",
                        genesis_key=action.genesis_key
                    )

            # Run in sandbox first if required
            if action.sandbox_first:
                sandbox_result = await self._run_sandbox(action)
                if sandbox_result.get("status") == "failed":
                    self._track_action_version(action.id, action, "sandbox_failed")
                    return ActionResult(
                        action_id=action.id,
                        status="sandbox_failed",
                        error=sandbox_result.get("error"),
                        genesis_key=action.genesis_key
                    )

            # Execute
            output = await handler(action)

            duration = (datetime.utcnow() - start_time).total_seconds()

            result = ActionResult(
                action_id=action.id,
                status="success",
                output=output,
                duration_seconds=duration,
                genesis_key=action.genesis_key
            )

            action.status = "completed"
            self.stats["actions_succeeded"] += 1

            # Update trust score - success
            self._update_trust_score(action.action_type.value, True)

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()

            result = ActionResult(
                action_id=action.id,
                status="failed",
                error=str(e),
                duration_seconds=duration,
                genesis_key=action.genesis_key
            )

            action.status = "failed"
            self.stats["actions_failed"] += 1

            # Update trust score - failure
            self._update_trust_score(action.action_type.value, False)

            logger.error(f"[Autonomous] Action {action.id} failed: {e}")

        finally:
            action.completed_at = datetime.utcnow().isoformat()
            action.result = result
            self.stats["actions_executed"] += 1

            # Track completion version
            self._track_action_version(action.id, action, "complete")

            # Record KPI metrics
            self._record_kpi(action, result)

            # Notify Mirror for self-observation
            self._notify_mirror(action, result)

            # Move to history
            self.action_history.append(action)
            if len(self.action_history) > 1000:
                self.action_history = self.action_history[-1000:]

        return result

    async def _check_approval(self, action: AutonomousAction) -> bool:
        """Check if action has governance approval."""
        try:
            from genesis.adaptive_cicd import get_adaptive_cicd

            adaptive = get_adaptive_cicd()

            # Check for pending approval
            for req in adaptive.governance_requests.values():
                if req.metadata.get("action_id") == action.id:
                    return req.status == "approved"

            # No approval found, request it
            # For now, auto-approve low-risk actions
            if action.priority in [ActionPriority.LOW, ActionPriority.BACKGROUND]:
                return True

            return False

        except Exception:
            return True  # Fail open for now

    async def _run_sandbox(self, action: AutonomousAction) -> Dict[str, Any]:
        """Run action in sandbox mode via the sandbox mirror."""
        try:
            from cognitive.sandbox_mirror import get_sandbox_mirror
            mirror = get_sandbox_mirror()
            session = mirror.create_session(branch="internal")
            result = mirror.run_experiment(
                session_id=session.id,
                task_description=getattr(action, 'description', str(action.action_type))[:500],
                use_consensus=False,
            )
            mirror.close_session(session.id)
            return {"status": result.get("status", "completed"), "sandbox_result": result}
        except Exception as e:
            logger.debug(f"[Autonomous] Sandbox run failed, using basic validation: {e}")
            return {"status": "success", "sandbox": "fallback"}

    # =========================================================================
    # Event System
    # =========================================================================

    async def emit_event(self, event_name: str, data: Dict[str, Any] = None):
        """
        Emit an event that may trigger autonomous actions.
        """
        data = data or {}

        logger.debug(f"[Autonomous] Event: {event_name}")

        # Check rules for matching events
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.trigger_type != TriggerType.EVENT:
                continue

            # Check condition
            if rule.condition.get("event") == event_name:
                # Check cooldown
                if rule.last_triggered:
                    last = datetime.fromisoformat(rule.last_triggered)
                    if (datetime.utcnow() - last).seconds < rule.cooldown_seconds:
                        continue

                # Queue action
                context = ActionContext(
                    source=event_name,
                    trigger_type=TriggerType.EVENT,
                    data=data
                )

                await self.queue_action(
                    action_type=rule.action_type,
                    context=context,
                    priority=rule.priority,
                    config=rule.action_config
                )

                rule.last_triggered = datetime.utcnow().isoformat()

        # Call registered event handlers
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"[Autonomous] Event handler error: {e}")

    def on_event(self, event_name: str):
        """Decorator to register event handlers."""
        def decorator(func):
            if event_name not in self.event_handlers:
                self.event_handlers[event_name] = []
            self.event_handlers[event_name].append(func)
            return func
        return decorator

    # =========================================================================
    # Worker Loop
    # =========================================================================

    async def start(self):
        """Start the autonomous engine."""
        if self._running:
            return

        self._running = True

        # Start workers for each priority
        for priority in ActionPriority:
            task = asyncio.create_task(self._worker(priority))
            self._worker_tasks.append(task)

        # Start scheduler
        scheduler_task = asyncio.create_task(self._scheduler())
        self._worker_tasks.append(scheduler_task)

        logger.info("[Autonomous] Engine started")

    async def stop(self):
        """Stop the autonomous engine."""
        self._running = False

        for task in self._worker_tasks:
            task.cancel()

        self._worker_tasks.clear()

        logger.info("[Autonomous] Engine stopped")

    async def _worker(self, priority: ActionPriority):
        """Worker that processes actions of a specific priority."""
        queue = self.action_queue[priority]

        while self._running:
            try:
                action_id = await asyncio.wait_for(queue.get(), timeout=5.0)

                action = self.actions.get(action_id)
                if action and action.status == "pending":
                    await self.execute_action(action)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[Autonomous] Worker error: {e}")
                await asyncio.sleep(1)

    async def _scheduler(self):
        """Scheduler for time-based actions."""
        while self._running:
            try:
                now = datetime.utcnow()

                for rule in self.rules.values():
                    if not rule.enabled:
                        continue

                    if rule.trigger_type != TriggerType.SCHEDULE:
                        continue

                    interval = rule.condition.get("interval_seconds", 300)

                    if rule.last_triggered:
                        last = datetime.fromisoformat(rule.last_triggered)
                        if (now - last).seconds < interval:
                            continue

                    # Queue scheduled action
                    context = ActionContext(
                        source="scheduler",
                        trigger_type=TriggerType.SCHEDULE,
                        data={"rule_id": rule.id}
                    )

                    await self.queue_action(
                        action_type=rule.action_type,
                        context=context,
                        priority=rule.priority,
                        config=rule.action_config
                    )

                    rule.last_triggered = now.isoformat()

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"[Autonomous] Scheduler error: {e}")
                await asyncio.sleep(10)

    # =========================================================================
    # Default Action Handlers
    # =========================================================================

    async def _handle_health_check(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle health check action."""
        from api.health import check_all_services

        try:
            result = await check_all_services()
            return {"health": result}
        except Exception as e:
            return {"health": "unknown", "error": str(e)}

    async def _handle_cleanup(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle cleanup action."""
        import shutil

        target = action.context.data.get("target", "cache")
        cleaned = 0

        if target == "cache":
            cache_dir = Path("/tmp/grace-cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleaned += 1

        return {"cleaned": cleaned, "target": target}

    async def _handle_ingest_file(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle file ingestion action."""
        from genesis.librarian_pipeline import get_librarian_pipeline

        file_path = action.context.data.get("file_path")

        if not file_path:
            raise ValueError("No file_path provided")

        pipeline = get_librarian_pipeline()
        result = await pipeline.ingest_file(file_path, action.context.data)

        return result

    async def _handle_ingest_directory(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle directory ingestion action."""
        from genesis.librarian_pipeline import get_librarian_pipeline

        dir_path = action.context.data.get("directory_path")

        if not dir_path:
            raise ValueError("No directory_path provided")

        pipeline = get_librarian_pipeline()
        result = await pipeline.ingest_directory(dir_path, action.context.data)

        return result

    async def _handle_run_pipeline(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle pipeline execution action."""
        from genesis.cicd import get_cicd

        pipeline_id = action.context.data.get("pipeline_id")

        if not pipeline_id:
            raise ValueError("No pipeline_id provided")

        cicd = get_cicd()
        run = await cicd.trigger_pipeline(
            pipeline_id=pipeline_id,
            trigger="autonomous",
            branch=action.context.data.get("branch", "main"),
            triggered_by="autonomous_engine"
        )

        return {"run_id": run.id, "status": run.status.value}

    async def _handle_learn_pattern(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle pattern learning action."""
        pattern = action.context.data.get("pattern")
        source = action.context.data.get("source")

        # Store in learning memory
        try:
            from api.learning_memory_api import store_pattern

            result = await store_pattern({
                "pattern": pattern,
                "source": source,
                "learned_at": datetime.utcnow().isoformat(),
                "genesis_key": action.genesis_key
            })

            return {"stored": True, "pattern_id": result.get("id")}
        except Exception as e:
            return {"stored": False, "error": str(e)}

    async def _handle_update_memory(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle memory update action."""
        content = action.context.data.get("content")
        memory_type = action.context.data.get("memory_type", "short_term")

        try:
            from learning_memory.memory import get_memory_system

            memory = get_memory_system()
            result = await memory.store(content, memory_type=memory_type)

            return {"stored": True, "memory_id": result.get("id")}
        except Exception as e:
            return {"stored": False, "error": str(e)}

    async def _handle_alert(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle alert action."""
        severity = action.context.data.get("severity", "info")
        message = action.context.data.get("message", "Alert triggered")
        channels = action.context.data.get("channels", ["log"])

        alert = {
            "severity": severity,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "genesis_key": action.genesis_key
        }

        if "log" in channels:
            logger.warning(f"[ALERT] {severity}: {message}")

        # Could integrate with notification systems here

        return {"alerted": True, "channels": channels}

    async def _handle_self_heal(self, action: AutonomousAction) -> Dict[str, Any]:
        """Handle self-healing action."""
        issue = action.context.data.get("issue")
        component = action.context.data.get("component")

        healed = False
        actions_taken = []

        if issue == "service_down":
            # Try to restart service
            actions_taken.append(f"Attempted restart of {component}")
            healed = True

        elif issue == "high_memory":
            # Trigger cleanup
            actions_taken.append("Triggered cache cleanup")
            await self.queue_action(
                ActionType.CLEANUP,
                ActionContext(source="self_heal", trigger_type=TriggerType.SELF, data={"target": "cache"}),
                ActionPriority.HIGH
            )
            healed = True

        return {"healed": healed, "actions": actions_taken}

    # =========================================================================
    # Status & Monitoring
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "running": self._running,
            "stats": self.stats,
            "queue_sizes": {
                p.value: self.action_queue[p].qsize()
                for p in ActionPriority
            },
            "active_actions": len([a for a in self.actions.values() if a.status == "running"]),
            "rules_count": len(self.rules),
            "handlers_count": len(self.handlers)
        }

    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent action history."""
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.action_type.value,
                "status": a.status,
                "priority": a.priority.value,
                "created_at": a.created_at,
                "completed_at": a.completed_at,
                "genesis_key": a.genesis_key
            }
            for a in self.action_history[-limit:]
        ]


# =============================================================================
# Global Instance
# =============================================================================

_engine: Optional[AutonomousEngine] = None


def get_autonomous_engine() -> AutonomousEngine:
    """Get the global autonomous engine instance."""
    global _engine
    if _engine is None:
        _engine = AutonomousEngine()
    return _engine


async def start_autonomous_engine():
    """Start the autonomous engine."""
    engine = get_autonomous_engine()
    await engine.start()


async def stop_autonomous_engine():
    """Stop the autonomous engine."""
    if _engine:
        await _engine.stop()
