import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
try:
    from execution.bridge import ExecutionBridge, ExecutionConfig
except ImportError:
    try:
        from bridge import ExecutionBridge, ExecutionConfig
    except ImportError:
        ExecutionBridge = None
        ExecutionConfig = None
try:
    from execution.actions import GraceAction, ActionRequest, ActionResult, ActionStatus
except ImportError:
    try:
        from actions import GraceAction, ActionRequest, ActionResult, ActionStatus
    except ImportError:
        # Make optional
        GraceAction = None
        ActionRequest = None
        ActionResult = None
        ActionStatus = None
from security.governance import GovernanceEngine, GovernanceContext, GovernanceDecision, AutonomyTier, get_governance_engine
from layer1.message_bus import Layer1MessageBus, ComponentType, get_message_bus

logger = logging.getLogger(__name__)

# Action governance mapping - maps action types to governance requirements
ACTION_GOVERNANCE_MAP: Dict[Any, Dict[str, Any]] = {}


class GovernedExecutionBridge:
    """
    Execution bridge with constitutional governance integration.

    Every action passes through governance evaluation before execution.
    Provides:
    - Constitutional rule enforcement
    - Autonomy tier checking
    - Policy evaluation
    - Audit trail via message bus
    - Metrics recording
    """

    def __init__(
        self,
        config: ExecutionConfig = None,
        genesis_tracker=None,
        governance_engine: GovernanceEngine = None,
        message_bus: Layer1MessageBus = None,
    ):
        # Underlying execution bridge
        self._bridge = ExecutionBridge(config=config, genesis_tracker=genesis_tracker)

        # Governance integration
        self.governance = governance_engine or get_governance_engine()
        self.message_bus = message_bus or get_message_bus()

        # Track governance decisions
        self._governance_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000

        # Stats
        self._stats = {
            "total_actions": 0,
            "allowed": 0,
            "blocked": 0,
            "pending_approval": 0,
            "avg_governance_time_ms": 0.0,
        }

        logger.info("[GOVERNED-BRIDGE] Initialized with governance integration")

    async def execute(self, action: ActionRequest) -> ActionResult:
        """
        Execute an action with governance checks.

        Flow:
        1. Build governance context from action
        2. Evaluate against constitutional rules
        3. Check autonomy tier constraints
        4. Apply policy rules
        5. If allowed, execute via underlying bridge
        6. Record metrics and publish events
        """
        self._stats["total_actions"] += 1
        start_time = time.time()

        # Build governance context
        context = self._build_governance_context(action)

        # Evaluate governance
        decision = await self.governance.evaluate(context)
        governance_time_ms = (time.time() - start_time) * 1000

        # Update rolling average
        self._update_avg_governance_time(governance_time_ms)

        # Log governance decision
        self._log_governance_decision(action, decision, governance_time_ms)

        # Publish governance event
        await self._publish_governance_event(action, decision)

        # Handle decision
        if not decision.allowed:
            if decision.required_approvals:
                # Pending approval
                self._stats["pending_approval"] += 1
                return self._create_blocked_result(
                    action,
                    f"Action requires approval: {', '.join(decision.required_approvals)}",
                    decision
                )
            else:
                # Blocked
                self._stats["blocked"] += 1
                violation_summary = "; ".join(
                    v.description for v in decision.violations[:3]
                )
                return self._create_blocked_result(
                    action,
                    f"Action blocked by governance: {violation_summary}",
                    decision
                )

        # Allowed - execute via underlying bridge
        self._stats["allowed"] += 1

        try:
            result = await self._bridge.execute(action)

            # Record metrics
            if self.governance.metrics:
                self.governance.metrics.record_operation(
                    success=result.success,
                    operation=action.action_type.value
                )
                self.governance.metrics.record_latency(
                    result.execution_time * 1000,
                    operation=action.action_type.value
                )

            # Adjust trust based on result
            if result.success:
                self.governance.adjust_trust_score(0.001)
            elif result.failed:
                self.governance.adjust_trust_score(-0.005)

            return result

        except Exception as e:
            logger.exception(f"[GOVERNED-BRIDGE] Execution failed: {e}")

            # Record failure
            if self.governance.metrics:
                self.governance.metrics.record_operation(
                    success=False,
                    operation=action.action_type.value
                )

            self.governance.adjust_trust_score(-0.01)

            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
            )

    def _build_governance_context(self, action: ActionRequest) -> GovernanceContext:
        """Build governance context from action request."""
        # Get governance mapping for action type
        # Get governance mapping for this action type
        if GraceAction and action.action_type:
            mapping = ACTION_GOVERNANCE_MAP.get(action.action_type, {
            "action_type": "unknown",
            "impact_scope": "local",
            "is_reversible": True,
            "financial_impact": 0.0,
        })

        # Build target resource from action parameters
        target_resource = self._extract_target_resource(action)

        # Check for potential risks in metadata
        metadata = {
            "action_id": action.action_id,
            "confidence": action.confidence,
            "reasoning": action.reasoning,
            "parameters": action.parameters,
        }

        # Flag potential harm patterns
        if action.action_type == GraceAction.RUN_BASH:
            command = action.parameters.get("command", "")
            if any(dangerous in command for dangerous in ["rm -rf", "sudo", "chmod 777"]):
                metadata["potential_harm_to_humans"] = False  # System harm, not human
                metadata["bypasses_safety_check"] = True

        return GovernanceContext(
            context_id=action.action_id,
            action_type=mapping["action_type"],
            actor_id="grace_agent",
            actor_type="ai",
            target_resource=target_resource,
            impact_scope=mapping["impact_scope"],
            is_reversible=mapping["is_reversible"],
            financial_impact=mapping["financial_impact"],
            metadata=metadata,
        )

    def _extract_target_resource(self, action: ActionRequest) -> str:
        """Extract target resource from action parameters."""
        params = action.parameters

        # Try common parameter names
        if "path" in params:
            return params["path"]
        if "file" in params:
            return params["file"]
        if "command" in params:
            return f"bash:{params['command'][:50]}"
        if "code" in params:
            return f"python:{len(params['code'])}chars"
        if "test_path" in params:
            return params["test_path"]
        if "pattern" in params:
            return f"search:{params['pattern']}"

        return action.action_type.value

    def _create_blocked_result(
        self,
        action: ActionRequest,
        message: str,
        decision: GovernanceDecision
    ) -> ActionResult:
        """Create a blocked action result."""
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.CANCELLED,
            error=message,
            data={
                "governance_decision_id": decision.decision_id,
                "autonomy_tier": decision.autonomy_tier.value,
                "violations": [v.description for v in decision.violations],
                "warnings": decision.warnings,
                "required_approvals": decision.required_approvals,
            },
            learnable=False,
            trust_delta=-0.01,  # Slight trust penalty for blocked action
        )

    def _log_governance_decision(
        self,
        action: ActionRequest,
        decision: GovernanceDecision,
        governance_time_ms: float
    ):
        """Log governance decision for audit."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "decision_id": decision.decision_id,
            "allowed": decision.allowed,
            "autonomy_tier": decision.autonomy_tier.value,
            "violations_count": len(decision.violations),
            "governance_time_ms": governance_time_ms,
        }
        self._governance_log.append(entry)

        # Keep log bounded
        if len(self._governance_log) > self._max_log_size:
            self._governance_log = self._governance_log[-self._max_log_size:]

    def _update_avg_governance_time(self, governance_time_ms: float):
        """Update rolling average governance evaluation time."""
        current_avg = self._stats["avg_governance_time_ms"]
        total = self._stats["total_actions"]

        # Rolling average
        self._stats["avg_governance_time_ms"] = (
            (current_avg * (total - 1) + governance_time_ms) / total
        )

    async def _publish_governance_event(
        self,
        action: ActionRequest,
        decision: GovernanceDecision
    ):
        """Publish governance event to message bus."""
        try:
            await self.message_bus.publish(
                topic="execution.governance",
                payload={
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "decision_id": decision.decision_id,
                    "allowed": decision.allowed,
                    "autonomy_tier": decision.autonomy_tier.value,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                from_component=ComponentType.COGNITIVE_ENGINE,
                priority=7 if not decision.allowed else 5,
            )
        except Exception as e:
            logger.warning(f"[GOVERNED-BRIDGE] Failed to publish event: {e}")

    # ==========================================================================
    # PASSTHROUGH METHODS
    # ==========================================================================

    @property
    def config(self) -> ExecutionConfig:
        """Get execution config."""
        return self._bridge.config

    @property
    def action_history(self):
        """Get action history from underlying bridge."""
        return self._bridge.action_history

    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats."""
        return {
            **self._stats,
            "governance": self.governance.get_stats(),
            "current_tier": self.governance._current_tier.value,
            "trust_score": self.governance._trust_score,
        }

    def get_governance_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent governance decisions."""
        return self._governance_log[-limit:]


# =============================================================================
# SINGLETON
# =============================================================================

_governed_bridge: Optional[GovernedExecutionBridge] = None


def get_governed_execution_bridge(
    config: ExecutionConfig = None,
    genesis_tracker=None,
) -> GovernedExecutionBridge:
    """Get or create the governed execution bridge singleton."""
    global _governed_bridge
    if _governed_bridge is None:
        _governed_bridge = GovernedExecutionBridge(
            config=config,
            genesis_tracker=genesis_tracker,
        )
        logger.info("[GOVERNED-BRIDGE] Created global governed bridge")
    return _governed_bridge


def reset_governed_bridge():
    """Reset governed bridge (for testing)."""
    global _governed_bridge
    _governed_bridge = None
