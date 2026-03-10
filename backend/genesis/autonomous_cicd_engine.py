"""
Autonomous CI/CD Engine
========================
The autonomous brain for GRACE's CI/CD system.

This engine:
1. Monitors system health and code changes
2. Makes intelligent decisions about when/what to test and deploy
3. Triggers pipelines autonomously based on trust scores
4. Integrates with the healing system for failure response
5. Learns from CI/CD outcomes to improve decisions

NO EXTERNAL DEPENDENCIES - Fully GRACE-native using Genesis Keys.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │              AUTONOMOUS CI/CD ENGINE                            │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
    │   │   Event     │  │  Intelligent │  │    Genesis Key     │   │
    │   │   Monitor   │→ │   Decision   │→ │    CI/CD System    │   │
    │   └─────────────┘  └─────────────┘  └─────────────────────┘   │
    │          ↑                ↑                    ↓                │
    │          │                │                    │                │
    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
    │   │   File      │  │   Healing   │  │   Learning Memory  │   │
    │   │   Watcher   │  │   System    │← │   (Feedback Loop)  │   │
    │   └─────────────┘  └─────────────┘  └─────────────────────┘   │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import os

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AutonomousTriggerType(str, Enum):
    """Types of autonomous triggers."""
    FILE_CHANGE = "file_change"
    HEALTH_CHECK = "health_check"
    SCHEDULED = "scheduled"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    ANOMALY_RESPONSE = "anomaly_response"
    HEALING_ACTION = "healing_action"
    USER_REQUEST = "user_request"
    DEPENDENCY_UPDATE = "dependency_update"
    SECURITY_SCAN = "security_scan"


class AutonomyLevel(int, Enum):
    """Autonomy levels for CI/CD actions."""
    MANUAL_ONLY = 0           # All actions require approval
    SUGGEST = 1               # Suggest actions but don't execute
    LOW_AUTONOMY = 2          # Auto-execute low-risk only
    MEDIUM_AUTONOMY = 3       # Auto-execute medium-risk
    HIGH_AUTONOMY = 4         # Auto-execute high-risk
    FULL_AUTONOMY = 5         # Full autonomous control


class ActionRisk(str, Enum):
    """Risk levels for CI/CD actions."""
    LOW = "low"               # Tests only, no deployments
    MEDIUM = "medium"         # Build artifacts, staging deployments
    HIGH = "high"             # Production deployments
    CRITICAL = "critical"     # Infrastructure changes


@dataclass
class AutonomousEvent:
    """An event that may trigger autonomous CI/CD."""
    id: str
    event_type: AutonomousTriggerType
    timestamp: str
    source: str
    payload: Dict[str, Any]
    genesis_key: Optional[str] = None
    processed: bool = False
    action_taken: Optional[str] = None


@dataclass
class AutonomousDecision:
    """A decision made by the autonomous engine."""
    decision_id: str
    event_id: str
    action: str
    risk_level: ActionRisk
    confidence: float
    reasoning: str
    approved: bool
    execution_mode: str  # auto, manual, sandbox
    genesis_key: str
    timestamp: str
    pipeline_id: Optional[str] = None
    pipeline_config: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# AUTONOMOUS CI/CD ENGINE
# =============================================================================

class AutonomousCICDEngine:
    """
    Autonomous CI/CD Engine - The brain of GRACE's CI/CD system.

    Makes intelligent decisions about:
    - When to run CI pipelines
    - Which tests to prioritize
    - When to deploy
    - How to respond to failures
    """

    def __init__(
        self,
        autonomy_level: AutonomyLevel = AutonomyLevel.MEDIUM_AUTONOMY,
        project_root: Optional[Path] = None
    ):
        self.autonomy_level = autonomy_level
        self.project_root = project_root or Path.cwd()

        # State
        self.events: Dict[str, AutonomousEvent] = {}
        self.decisions: Dict[str, AutonomousDecision] = {}
        self.learning_history: List[Dict] = []

        # Trust scores for different actions
        self.action_trust: Dict[str, float] = {
            "run_tests": 0.9,
            "run_linting": 0.95,
            "run_security_scan": 0.85,
            "build_artifacts": 0.75,
            "deploy_staging": 0.60,
            "deploy_production": 0.40,
            "rollback": 0.50,
            "infrastructure_change": 0.30
        }

        # Event handlers
        self.event_handlers: Dict[AutonomousTriggerType, List[Callable]] = {}

        # Background tasks
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None

        # Monitoring config
        self.health_check_interval = 60  # 1 minute
        self.scheduled_ci_interval = 3600  # 1 hour

        logger.info(
            f"[AutonomousCICD] Initialized with autonomy_level={autonomy_level.name}"
        )

    # =========================================================================
    # EVENT MONITORING
    # =========================================================================

    async def start(self):
        """Start the autonomous engine."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._monitor_task = asyncio.create_task(self._health_monitor_loop())
        self._scheduler_task = asyncio.create_task(self._scheduled_ci_loop())

        logger.info("[AutonomousCICD] Engine started")

    async def stop(self):
        """Stop the autonomous engine."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
        if self._scheduler_task:
            self._scheduler_task.cancel()

        logger.info("[AutonomousCICD] Engine stopped")

    async def _health_monitor_loop(self):
        """Background loop for health monitoring."""
        while self._running:
            try:
                await self._check_system_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AutonomousCICD] Health monitor error: {e}")
                await asyncio.sleep(60)

    async def _scheduled_ci_loop(self):
        """Background loop for scheduled CI runs."""
        while self._running:
            try:
                await asyncio.sleep(self.scheduled_ci_interval)
                await self._run_scheduled_ci()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AutonomousCICD] Scheduled CI error: {e}")
                await asyncio.sleep(300)

    async def _check_system_health(self):
        """Check system health and trigger CI if needed."""
        event = AutonomousEvent(
            id=self._generate_id("health"),
            event_type=AutonomousTriggerType.HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="health_monitor",
            payload={"check_type": "periodic"},
            genesis_key=self._generate_genesis_key("health_check")
        )

        await self.process_event(event)

    async def _run_scheduled_ci(self):
        """Run scheduled CI pipeline."""
        event = AutonomousEvent(
            id=self._generate_id("scheduled"),
            event_type=AutonomousTriggerType.SCHEDULED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="scheduler",
            payload={"schedule_type": "periodic"},
            genesis_key=self._generate_genesis_key("scheduled_ci")
        )

        await self.process_event(event)

    # =========================================================================
    # EVENT PROCESSING
    # =========================================================================

    async def on_file_change(
        self,
        file_path: str,
        change_type: str = "modified"
    ) -> Optional[AutonomousDecision]:
        """
        Handle file change event.

        Called when a file is created/modified/deleted.
        """
        event = AutonomousEvent(
            id=self._generate_id("file"),
            event_type=AutonomousTriggerType.FILE_CHANGE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="file_watcher",
            payload={
                "file_path": file_path,
                "change_type": change_type
            },
            genesis_key=self._generate_genesis_key("file_change")
        )

        return await self.process_event(event)

    async def on_learning_opportunity(
        self,
        topic: str,
        learning_type: str = "code_change"
    ) -> Optional[AutonomousDecision]:
        """
        Handle learning opportunity event.

        Triggers CI when GRACE has learned something new.
        """
        event = AutonomousEvent(
            id=self._generate_id("learning"),
            event_type=AutonomousTriggerType.LEARNING_OPPORTUNITY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="learning_system",
            payload={
                "topic": topic,
                "learning_type": learning_type
            },
            genesis_key=self._generate_genesis_key("learning_opportunity")
        )

        return await self.process_event(event)

    async def on_anomaly_detected(
        self,
        anomaly_type: str,
        severity: str,
        details: Dict[str, Any]
    ) -> Optional[AutonomousDecision]:
        """
        Handle anomaly detection event.

        Triggers investigation/healing CI when anomalies are detected.
        """
        event = AutonomousEvent(
            id=self._generate_id("anomaly"),
            event_type=AutonomousTriggerType.ANOMALY_RESPONSE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="anomaly_detector",
            payload={
                "anomaly_type": anomaly_type,
                "severity": severity,
                "details": details
            },
            genesis_key=self._generate_genesis_key("anomaly_response")
        )

        return await self.process_event(event)

    async def on_healing_request(
        self,
        healing_action: str,
        context: Dict[str, Any]
    ) -> Optional[AutonomousDecision]:
        """
        Handle healing request event.

        Triggers CI/CD to verify healing actions.
        """
        event = AutonomousEvent(
            id=self._generate_id("healing"),
            event_type=AutonomousTriggerType.HEALING_ACTION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="healing_system",
            payload={
                "healing_action": healing_action,
                "context": context
            },
            genesis_key=self._generate_genesis_key("healing_request")
        )

        return await self.process_event(event)

    async def process_event(
        self,
        event: AutonomousEvent
    ) -> Optional[AutonomousDecision]:
        """
        Process an autonomous event and make decision.

        This is the central decision-making function.
        """
        self.events[event.id] = event

        logger.info(
            f"[AutonomousCICD] Processing event {event.event_type.value} "
            f"from {event.source}"
        )

        # Analyze event and decide action
        action, risk, confidence, reasoning = await self._analyze_event(event)

        if action is None:
            logger.info(f"[AutonomousCICD] No action needed for event {event.id}")
            return None

        # Check if we can execute autonomously
        can_auto = self._can_execute_autonomously(risk, confidence)

        execution_mode = "auto" if can_auto else "manual"
        if risk == ActionRisk.HIGH and can_auto:
            execution_mode = "sandbox"

        # Create decision
        decision = AutonomousDecision(
            decision_id=self._generate_id("decision"),
            event_id=event.id,
            action=action,
            risk_level=risk,
            confidence=confidence,
            reasoning=reasoning,
            approved=can_auto,
            execution_mode=execution_mode,
            genesis_key=self._generate_genesis_key("decision"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pipeline_config=self._build_pipeline_config(event, action)
        )

        self.decisions[decision.decision_id] = decision
        event.processed = True

        logger.info(
            f"[AutonomousCICD] Decision: {action} "
            f"(risk={risk.value}, mode={execution_mode}, confidence={confidence:.0%})"
        )

        # Execute if approved
        if decision.approved:
            await self._execute_decision(decision)

        return decision

    async def _analyze_event(
        self,
        event: AutonomousEvent
    ) -> tuple[Optional[str], ActionRisk, float, str]:
        """
        Analyze an event and determine the appropriate action.

        Returns: (action, risk_level, confidence, reasoning)
        """
        event_type = event.event_type
        payload = event.payload

        # FILE CHANGE
        if event_type == AutonomousTriggerType.FILE_CHANGE:
            file_path = payload.get("file_path", "")

            # Determine action based on file type
            if file_path.endswith(".py"):
                if "test" in file_path.lower():
                    return (
                        "run_tests",
                        ActionRisk.LOW,
                        0.95,
                        f"Test file changed: {file_path}"
                    )
                else:
                    return (
                        "run_tests",
                        ActionRisk.LOW,
                        0.90,
                        f"Python file changed: {file_path}"
                    )
            elif file_path.endswith((".js", ".ts", ".tsx")):
                return (
                    "run_linting",
                    ActionRisk.LOW,
                    0.85,
                    f"Frontend file changed: {file_path}"
                )
            elif file_path.endswith(("requirements.txt", "package.json")):
                return (
                    "run_security_scan",
                    ActionRisk.MEDIUM,
                    0.80,
                    f"Dependency file changed: {file_path}"
                )
            elif file_path.endswith((".yml", ".yaml")):
                if "deploy" in file_path.lower() or "k8s" in file_path.lower():
                    return (
                        "build_artifacts",
                        ActionRisk.MEDIUM,
                        0.70,
                        f"Deployment config changed: {file_path}"
                    )

        # HEALTH CHECK
        elif event_type == AutonomousTriggerType.HEALTH_CHECK:
            # Check for issues that require CI response
            return await self._analyze_health_status()

        # SCHEDULED
        elif event_type == AutonomousTriggerType.SCHEDULED:
            return (
                "run_tests",
                ActionRisk.LOW,
                0.85,
                "Scheduled periodic CI run"
            )

        # ANOMALY RESPONSE
        elif event_type == AutonomousTriggerType.ANOMALY_RESPONSE:
            severity = payload.get("severity", "medium")
            anomaly_type = payload.get("anomaly_type", "unknown")

            if severity == "critical":
                return (
                    "run_tests",
                    ActionRisk.MEDIUM,
                    0.90,
                    f"Critical anomaly detected: {anomaly_type}"
                )
            elif severity == "high":
                return (
                    "run_tests",
                    ActionRisk.LOW,
                    0.85,
                    f"High severity anomaly: {anomaly_type}"
                )

        # HEALING ACTION
        elif event_type == AutonomousTriggerType.HEALING_ACTION:
            healing_action = payload.get("healing_action", "")
            return (
                "run_tests",
                ActionRisk.MEDIUM,
                0.80,
                f"Validating healing action: {healing_action}"
            )

        # LEARNING OPPORTUNITY
        elif event_type == AutonomousTriggerType.LEARNING_OPPORTUNITY:
            topic = payload.get("topic", "")
            return (
                "run_tests",
                ActionRisk.LOW,
                0.75,
                f"Learning opportunity CI: {topic}"
            )

        return (None, ActionRisk.LOW, 0.0, "No action required")

    async def _analyze_health_status(self) -> tuple[Optional[str], ActionRisk, float, str]:
        """Analyze system health and recommend action."""
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel

            # Get healing system status (if available)
            # This is a check - we don't actually run healing here
            return (
                "run_tests",
                ActionRisk.LOW,
                0.70,
                "Periodic health validation"
            )

        except Exception:
            return (
                "run_tests",
                ActionRisk.LOW,
                0.70,
                "Periodic health check (healing system unavailable)"
            )

    def _can_execute_autonomously(
        self,
        risk: ActionRisk,
        confidence: float
    ) -> bool:
        """Determine if action can be executed autonomously."""
        # Map risk levels to required autonomy levels
        risk_to_autonomy = {
            ActionRisk.LOW: AutonomyLevel.LOW_AUTONOMY,
            ActionRisk.MEDIUM: AutonomyLevel.MEDIUM_AUTONOMY,
            ActionRisk.HIGH: AutonomyLevel.HIGH_AUTONOMY,
            ActionRisk.CRITICAL: AutonomyLevel.FULL_AUTONOMY
        }

        required_level = risk_to_autonomy[risk]

        # Check autonomy level
        if self.autonomy_level < required_level:
            return False

        # Check confidence threshold
        confidence_thresholds = {
            ActionRisk.LOW: 0.60,
            ActionRisk.MEDIUM: 0.75,
            ActionRisk.HIGH: 0.85,
            ActionRisk.CRITICAL: 0.95
        }

        return confidence >= confidence_thresholds[risk]

    def _build_pipeline_config(
        self,
        event: AutonomousEvent,
        action: str
    ) -> Dict[str, Any]:
        """Build pipeline configuration based on event and action."""
        config = {
            "pipeline_id": "grace-ci",
            "trigger": event.event_type.value,
            "triggered_by": "autonomous_engine",
            "variables": {}
        }

        # Customize based on action
        if action == "run_tests":
            config["pipeline_id"] = "grace-ci"
            config["variables"]["TEST_FOCUS"] = "all"

        elif action == "run_linting":
            config["pipeline_id"] = "grace-quick"

        elif action == "run_security_scan":
            config["pipeline_id"] = "grace-ci"
            config["variables"]["SECURITY_SCAN"] = "true"

        elif action == "build_artifacts":
            config["pipeline_id"] = "grace-ci"
            config["variables"]["BUILD_ONLY"] = "true"

        # Add event context
        config["variables"]["EVENT_ID"] = event.id
        config["variables"]["EVENT_TYPE"] = event.event_type.value

        return config

    async def _execute_decision(self, decision: AutonomousDecision):
        """Execute an approved decision."""
        try:
            from genesis.cicd import get_cicd

            cicd = get_cicd()

            config = decision.pipeline_config
            pipeline_id = config.get("pipeline_id", "grace-ci")

            logger.info(
                f"[AutonomousCICD] Executing: {decision.action} "
                f"via pipeline {pipeline_id}"
            )

            # Trigger the pipeline
            run = await cicd.trigger_pipeline(
                pipeline_id=pipeline_id,
                trigger=config.get("trigger", "autonomous"),
                triggered_by=config.get("triggered_by", "autonomous_engine"),
                variables=config.get("variables", {})
            )

            decision.pipeline_id = run.id

            logger.info(
                f"[AutonomousCICD] Pipeline triggered: {run.id} "
                f"(status: {run.status.value})"
            )

            # Record for learning
            self.learning_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "decision_id": decision.decision_id,
                "action": decision.action,
                "pipeline_id": run.id,
                "risk": decision.risk_level.value,
                "confidence": decision.confidence
            })

        except Exception as e:
            logger.error(f"[AutonomousCICD] Execution failed: {e}")

    # =========================================================================
    # LEARNING & FEEDBACK
    # =========================================================================

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        details: Dict[str, Any] = None
    ):
        """Record outcome for learning."""
        decision = self.decisions.get(decision_id)
        if not decision:
            return

        # Update trust scores based on outcome
        action = decision.action
        if action in self.action_trust:
            if success:
                # Increase trust (cap at 0.99)
                self.action_trust[action] = min(
                    0.99,
                    self.action_trust[action] + 0.02
                )
            else:
                # Decrease trust (floor at 0.1)
                self.action_trust[action] = max(
                    0.1,
                    self.action_trust[action] - 0.05
                )

        self.learning_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_id": decision_id,
            "success": success,
            "details": details,
            "trust_after": self.action_trust.get(action)
        })

        logger.info(
            f"[AutonomousCICD] Recorded outcome for {decision_id}: "
            f"{'SUCCESS' if success else 'FAILURE'}"
        )

    # =========================================================================
    # MANUAL APPROVAL
    # =========================================================================

    async def approve_decision(
        self,
        decision_id: str,
        approver: str = "user"
    ) -> Optional[AutonomousDecision]:
        """Manually approve a pending decision."""
        decision = self.decisions.get(decision_id)
        if not decision:
            return None

        if decision.approved:
            return decision

        decision.approved = True
        decision.execution_mode = "manual_approved"

        logger.info(
            f"[AutonomousCICD] Decision {decision_id} approved by {approver}"
        )

        await self._execute_decision(decision)

        return decision

    async def reject_decision(
        self,
        decision_id: str,
        reason: str = "User rejected"
    ) -> Optional[AutonomousDecision]:
        """Reject a pending decision."""
        decision = self.decisions.get(decision_id)
        if not decision:
            return None

        decision.approved = False
        decision.execution_mode = "rejected"
        decision.reasoning += f" | Rejected: {reason}"

        logger.info(
            f"[AutonomousCICD] Decision {decision_id} rejected: {reason}"
        )

        return decision

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"{prefix}:{timestamp}:{len(self.events)}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def _generate_genesis_key(self, action: str) -> str:
        """Generate Genesis Key."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"autonomous_cicd:{action}:{timestamp}"
        key_hash = hashlib.sha256(data.encode()).hexdigest()[:12]
        return f"GK-acicd-{key_hash}"

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        pending_decisions = [
            d for d in self.decisions.values()
            if not d.approved and d.execution_mode == "manual"
        ]

        return {
            "running": self._running,
            "autonomy_level": self.autonomy_level.name,
            "events_processed": len([e for e in self.events.values() if e.processed]),
            "total_events": len(self.events),
            "decisions_made": len(self.decisions),
            "pending_approvals": len(pending_decisions),
            "action_trust_scores": self.action_trust,
            "learning_examples": len(self.learning_history)
        }

    def get_pending_decisions(self) -> List[AutonomousDecision]:
        """Get decisions pending approval."""
        return [
            d for d in self.decisions.values()
            if not d.approved and d.execution_mode == "manual"
        ]


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_autonomous_engine: Optional[AutonomousCICDEngine] = None


def get_autonomous_cicd_engine(
    autonomy_level: AutonomyLevel = AutonomyLevel.MEDIUM_AUTONOMY
) -> AutonomousCICDEngine:
    """Get or create global autonomous CI/CD engine."""
    global _autonomous_engine

    if _autonomous_engine is None:
        _autonomous_engine = AutonomousCICDEngine(
            autonomy_level=autonomy_level
        )

    return _autonomous_engine


async def start_autonomous_cicd():
    """Start the autonomous CI/CD engine."""
    engine = get_autonomous_cicd_engine()
    await engine.start()
    logger.info("[AutonomousCICD] Autonomous engine started")


async def stop_autonomous_cicd():
    """Stop the autonomous CI/CD engine."""
    if _autonomous_engine:
        await _autonomous_engine.stop()
    logger.info("[AutonomousCICD] Autonomous engine stopped")
