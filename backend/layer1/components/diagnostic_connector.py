"""
Diagnostic Engine Connector for Layer 1 Message Bus.
Provides diagnostic and health monitoring through Layer 1.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

DIAGNOSTIC_ENGINE_AVAILABLE = False
try:
    from diagnostic_machine.diagnostic_engine import (
        DiagnosticEngine,
        get_diagnostic_engine,
        TriggerSource,
        EngineState,
        DiagnosticCycle,
    )
    DIAGNOSTIC_ENGINE_AVAILABLE = True
except ImportError:
    DiagnosticEngine = None
    get_diagnostic_engine = None
    TriggerSource = None
    EngineState = None
    DiagnosticCycle = None

try:
    from layer1.message_bus import (
        Layer1MessageBus,
        Message,
        ComponentType,
        MessageType,
        get_message_bus,
    )
except ImportError:
    Layer1MessageBus = None
    Message = None
    ComponentType = None
    MessageType = None
    get_message_bus = None


class DiagnosticConnector:
    """
    Connector for Diagnostic Engine integration with Layer 1.

    Provides:
    - Diagnostic cycle execution
    - System health monitoring
    - Issue analysis and detection
    - Automatic error response
    - Healing coordination
    """

    def __init__(
        self,
        message_bus: Optional["Layer1MessageBus"] = None,
        engine: Optional["DiagnosticEngine"] = None,
    ):
        if not DIAGNOSTIC_ENGINE_AVAILABLE:
            raise ImportError("Diagnostic Engine not available")

        self.message_bus = message_bus or get_message_bus()
        self.engine = engine or get_diagnostic_engine()
        self.enabled = True
        self._recent_issues: List[Dict[str, Any]] = []
        self._max_recent_issues = 100

        self.message_bus.register_component(
            ComponentType.DIAGNOSTIC_ENGINE,
            self
        )
        logger.info("[DIAGNOSTIC-CONNECTOR] Registered with message bus")

        self._register_request_handlers()
        self._subscribe_to_events()
        self._register_autonomous_actions()
        self._register_engine_callbacks()

    def _register_request_handlers(self):
        """Register request handlers with message bus."""
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "run_diagnostics",
            self._handle_run_diagnostics,
        )
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "get_health",
            self._handle_get_health,
        )
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "analyze_issue",
            self._handle_analyze_issue,
        )
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "diagnostic.get_stats",
            self._handle_get_stats,
        )
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "diagnostic.run_proactive_scan",
            self._handle_run_proactive_scan,
        )
        self.message_bus.register_request_handler(
            ComponentType.DIAGNOSTIC_ENGINE,
            "diagnostic.get_recent_cycles",
            self._handle_get_recent_cycles,
        )

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        self.message_bus.subscribe(
            "error.detected",
            self._on_error_detected,
        )
        self.message_bus.subscribe(
            "healing.requested",
            self._on_healing_requested,
        )
        self.message_bus.subscribe(
            "*.failure",
            self._on_component_failure,
        )
        self.message_bus.subscribe(
            "*.error",
            self._on_component_error,
        )

    def _register_autonomous_actions(self):
        """Register autonomous actions for diagnostic triggers."""
        self.message_bus.register_autonomous_action(
            trigger_event="system.startup",
            action=self._auto_run_startup_diagnostics,
            component=ComponentType.DIAGNOSTIC_ENGINE,
            description="Run diagnostics on system startup",
        )
        self.message_bus.register_autonomous_action(
            trigger_event="component.unhealthy",
            action=self._auto_analyze_unhealthy_component,
            component=ComponentType.DIAGNOSTIC_ENGINE,
            description="Auto-analyze unhealthy components",
        )
        self.message_bus.register_autonomous_action(
            trigger_event="cicd.pipeline_failed",
            action=self._auto_trigger_cicd_diagnostics,
            component=ComponentType.DIAGNOSTIC_ENGINE,
            description="Auto-trigger diagnostics on CI/CD failure",
        )

    def _register_engine_callbacks(self):
        """Register callbacks with the diagnostic engine."""
        try:
            self.engine._on_cycle_complete.append(self._on_cycle_complete_callback)
            self.engine._on_alert.append(self._on_alert_callback)
            self.engine._on_heal.append(self._on_heal_callback)
        except Exception as e:
            logger.debug(f"[DIAGNOSTIC-CONNECTOR] Could not register engine callbacks: {e}")

    def _on_cycle_complete_callback(self, cycle: "DiagnosticCycle"):
        """Callback when diagnostic cycle completes."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._publish_cycle_complete(cycle))
            else:
                loop.run_until_complete(self._publish_cycle_complete(cycle))
        except Exception as e:
            logger.debug(f"[DIAGNOSTIC-CONNECTOR] Cycle callback error: {e}")

    async def _publish_cycle_complete(self, cycle: "DiagnosticCycle"):
        """Publish cycle completion event."""
        await self.message_bus.publish(
            topic="diagnostic.cycle_complete",
            payload={
                "cycle_id": cycle.cycle_id,
                "trigger_source": cycle.trigger_source.value if cycle.trigger_source else None,
                "success": cycle.success,
                "duration_ms": cycle.total_duration_ms,
                "health_status": cycle.judgement.health.status.value if cycle.judgement else None,
            },
            from_component=ComponentType.DIAGNOSTIC_ENGINE,
        )

    def _on_alert_callback(self, cycle: "DiagnosticCycle"):
        """Callback when alert is raised."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._publish_alert(cycle))
        except Exception:
            pass

    async def _publish_alert(self, cycle: "DiagnosticCycle"):
        """Publish alert event."""
        await self.message_bus.publish(
            topic="diagnostic.alert_raised",
            payload={
                "cycle_id": cycle.cycle_id,
                "action_type": cycle.action_decision.action_type.value if cycle.action_decision else None,
                "reason": cycle.action_decision.reason if cycle.action_decision else None,
            },
            from_component=ComponentType.DIAGNOSTIC_ENGINE,
        )

    def _on_heal_callback(self, cycle: "DiagnosticCycle"):
        """Callback when healing is triggered."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._publish_heal(cycle))
        except Exception:
            pass

    async def _publish_heal(self, cycle: "DiagnosticCycle"):
        """Publish healing event."""
        await self.message_bus.publish(
            topic="diagnostic.healing_triggered",
            payload={
                "cycle_id": cycle.cycle_id,
                "healing_actions": cycle.action_decision.healing_actions if cycle.action_decision else [],
            },
            from_component=ComponentType.DIAGNOSTIC_ENGINE,
        )

    async def _handle_run_diagnostics(self, message: Message) -> Dict[str, Any]:
        """Handle run diagnostics request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        trigger_source_str = message.payload.get("trigger_source", "api")

        try:
            trigger_source = TriggerSource(trigger_source_str) if trigger_source_str else TriggerSource.API

            cycle = self.engine.run_cycle(trigger_source)

            result = {
                "success": cycle.success,
                "cycle_id": cycle.cycle_id,
                "trigger_source": cycle.trigger_source.value,
                "duration_ms": cycle.total_duration_ms,
            }

            if cycle.judgement:
                result["health"] = {
                    "status": cycle.judgement.health.status.value,
                    "score": cycle.judgement.health.score,
                    "issues_count": len(cycle.judgement.health.issues) if cycle.judgement.health.issues else 0,
                }

            if cycle.action_decision:
                result["action"] = {
                    "type": cycle.action_decision.action_type.value,
                    "reason": cycle.action_decision.reason,
                }

            await self.message_bus.publish(
                topic="diagnostic.issue_detected" if result.get("health", {}).get("issues_count", 0) > 0 else "diagnostic.health_report",
                payload=result,
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )

            return result

        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Run diagnostics failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_health(self, message: Message) -> Dict[str, Any]:
        """Handle get health request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        component_name = message.payload.get("component")

        try:
            stats = self.engine.stats

            health_data = {
                "success": True,
                "engine_state": self.engine.state.value,
                "total_cycles": stats.total_cycles,
                "successful_cycles": stats.successful_cycles,
                "failed_cycles": stats.failed_cycles,
                "uptime_seconds": stats.uptime_seconds,
                "last_cycle": stats.last_cycle_timestamp.isoformat() if stats.last_cycle_timestamp else None,
            }

            recent_cycles = self.engine._recent_cycles[-5:] if hasattr(self.engine, '_recent_cycles') else []
            if recent_cycles:
                last_cycle = recent_cycles[-1]
                if last_cycle.judgement:
                    health_data["current_health"] = {
                        "status": last_cycle.judgement.health.status.value,
                        "score": last_cycle.judgement.health.score,
                    }

            await self.message_bus.publish(
                topic="diagnostic.health_report",
                payload=health_data,
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )

            return health_data

        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Get health failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_analyze_issue(self, message: Message) -> Dict[str, Any]:
        """Handle analyze issue request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        issue_type = message.payload.get("issue_type")
        error_message = message.payload.get("error_message")
        component = message.payload.get("component")
        context = message.payload.get("context", {})

        try:
            cycle = self.engine.run_cycle(TriggerSource.API)

            analysis = {
                "success": True,
                "cycle_id": cycle.cycle_id,
                "issue_type": issue_type,
                "component": component,
            }

            if cycle.judgement:
                analysis["health_status"] = cycle.judgement.health.status.value
                analysis["health_score"] = cycle.judgement.health.score

                if cycle.judgement.forensic_analysis:
                    analysis["root_cause"] = cycle.judgement.forensic_analysis.get("root_cause")
                    analysis["recommendations"] = cycle.judgement.forensic_analysis.get("recommendations", [])

            if cycle.action_decision:
                analysis["recommended_action"] = cycle.action_decision.action_type.value
                analysis["action_reason"] = cycle.action_decision.reason

            self._recent_issues.append({
                "timestamp": datetime.utcnow().isoformat(),
                "issue_type": issue_type,
                "component": component,
                "analysis": analysis,
            })
            if len(self._recent_issues) > self._max_recent_issues:
                self._recent_issues.pop(0)

            await self.message_bus.publish(
                topic="diagnostic.issue_detected",
                payload=analysis,
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )

            return analysis

        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Analyze issue failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_stats(self, message: Message) -> Dict[str, Any]:
        """Handle get stats request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        try:
            stats = self.engine.stats
            return {
                "success": True,
                "engine_state": self.engine.state.value,
                "total_cycles": stats.total_cycles,
                "successful_cycles": stats.successful_cycles,
                "failed_cycles": stats.failed_cycles,
                "total_alerts": stats.total_alerts,
                "total_healing_actions": stats.total_healing_actions,
                "total_freeze_events": stats.total_freeze_events,
                "average_cycle_duration_ms": stats.average_cycle_duration_ms,
                "uptime_seconds": stats.uptime_seconds,
            }
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Get stats failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_run_proactive_scan(self, message: Message) -> Dict[str, Any]:
        """Handle run proactive scan request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        auto_heal = message.payload.get("auto_heal", False)

        try:
            result = self.engine.run_proactive_scan(auto_heal=auto_heal)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Proactive scan failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_recent_cycles(self, message: Message) -> Dict[str, Any]:
        """Handle get recent cycles request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        limit = message.payload.get("limit", 10)

        try:
            recent = self.engine._recent_cycles[-limit:] if hasattr(self.engine, '_recent_cycles') else []

            cycles = []
            for cycle in recent:
                cycle_data = {
                    "cycle_id": cycle.cycle_id,
                    "trigger_source": cycle.trigger_source.value if cycle.trigger_source else None,
                    "success": cycle.success,
                    "duration_ms": cycle.total_duration_ms,
                    "timestamp": cycle.cycle_start.isoformat() if cycle.cycle_start else None,
                }
                if cycle.judgement:
                    cycle_data["health_status"] = cycle.judgement.health.status.value
                cycles.append(cycle_data)

            return {"success": True, "cycles": cycles}
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Get recent cycles failed: {e}")
            return {"success": False, "error": str(e)}

    async def _on_error_detected(self, message: Message):
        """Handle error detected event - auto-analyze."""
        if not self.enabled:
            return

        error_type = message.payload.get("error_type")
        component = message.payload.get("component")
        error_message = message.payload.get("message")

        logger.info(f"[DIAGNOSTIC-CONNECTOR] Auto-analyzing error: {error_type} from {component}")

        try:
            cycle = self.engine.run_cycle(TriggerSource.SENSOR_FLAG)

            await self.message_bus.publish(
                topic="diagnostic.issue_detected",
                payload={
                    "trigger": "error.detected",
                    "error_type": error_type,
                    "component": component,
                    "cycle_id": cycle.cycle_id,
                    "health_status": cycle.judgement.health.status.value if cycle.judgement else "unknown",
                },
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Auto-analyze error failed: {e}")

    async def _on_healing_requested(self, message: Message):
        """Handle healing requested event - trigger healing cycle."""
        if not self.enabled:
            return

        component = message.payload.get("component")
        issue_type = message.payload.get("issue_type")

        logger.info(f"[DIAGNOSTIC-CONNECTOR] Healing requested for {component}: {issue_type}")

        try:
            cycle = self.engine.run_cycle(TriggerSource.API)

            await self.message_bus.publish(
                topic="diagnostic.health_report",
                payload={
                    "trigger": "healing.requested",
                    "component": component,
                    "cycle_id": cycle.cycle_id,
                    "action_taken": cycle.action_decision.action_type.value if cycle.action_decision else None,
                },
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Healing trigger failed: {e}")

    async def _on_component_failure(self, message: Message):
        """Handle component failure events."""
        if not self.enabled:
            return

        topic_parts = message.topic.split(".")
        component = topic_parts[0] if topic_parts else "unknown"

        logger.debug(f"[DIAGNOSTIC-CONNECTOR] Component failure detected: {component}")

        self._recent_issues.append({
            "timestamp": datetime.utcnow().isoformat(),
            "issue_type": "component_failure",
            "component": component,
            "topic": message.topic,
        })

    async def _on_component_error(self, message: Message):
        """Handle component error events."""
        if not self.enabled:
            return

        topic_parts = message.topic.split(".")
        component = topic_parts[0] if topic_parts else "unknown"

        logger.debug(f"[DIAGNOSTIC-CONNECTOR] Component error detected: {component}")

        self._recent_issues.append({
            "timestamp": datetime.utcnow().isoformat(),
            "issue_type": "component_error",
            "component": component,
            "topic": message.topic,
        })

    async def _auto_run_startup_diagnostics(self, message: Message):
        """Autonomous action: run diagnostics on startup."""
        if not self.enabled:
            return

        logger.info("[DIAGNOSTIC-CONNECTOR] Running startup diagnostics...")

        try:
            cycle = self.engine.run_cycle(TriggerSource.MANUAL)

            await self.message_bus.publish(
                topic="diagnostic.health_report",
                payload={
                    "trigger": "system.startup",
                    "cycle_id": cycle.cycle_id,
                    "health_status": cycle.judgement.health.status.value if cycle.judgement else "unknown",
                    "health_score": cycle.judgement.health.score if cycle.judgement else 0,
                },
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Startup diagnostics failed: {e}")

    async def _auto_analyze_unhealthy_component(self, message: Message):
        """Autonomous action: analyze unhealthy component."""
        if not self.enabled:
            return

        component = message.payload.get("component")
        reason = message.payload.get("reason")

        logger.info(f"[DIAGNOSTIC-CONNECTOR] Analyzing unhealthy component: {component}")

        try:
            cycle = self.engine.run_cycle(TriggerSource.SENSOR_FLAG)

            await self.message_bus.publish(
                topic="diagnostic.issue_detected",
                payload={
                    "trigger": "component.unhealthy",
                    "component": component,
                    "reason": reason,
                    "cycle_id": cycle.cycle_id,
                },
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] Unhealthy component analysis failed: {e}")

    async def _auto_trigger_cicd_diagnostics(self, message: Message):
        """Autonomous action: trigger diagnostics on CI/CD failure."""
        if not self.enabled:
            return

        pipeline_id = message.payload.get("pipeline_id")
        failure_reason = message.payload.get("reason")

        logger.info(f"[DIAGNOSTIC-CONNECTOR] CI/CD failure diagnostics: {pipeline_id}")

        try:
            cycle = self.engine.trigger_from_cicd(pipeline_id)

            await self.message_bus.publish(
                topic="diagnostic.issue_detected",
                payload={
                    "trigger": "cicd.pipeline_failed",
                    "pipeline_id": pipeline_id,
                    "failure_reason": failure_reason,
                    "cycle_id": cycle.cycle_id,
                },
                from_component=ComponentType.DIAGNOSTIC_ENGINE,
            )
        except Exception as e:
            logger.error(f"[DIAGNOSTIC-CONNECTOR] CI/CD diagnostics failed: {e}")


def create_diagnostic_connector(
    message_bus: Optional["Layer1MessageBus"] = None,
    engine: Optional["DiagnosticEngine"] = None,
) -> DiagnosticConnector:
    """
    Factory function to create Diagnostic connector.

    Args:
        message_bus: Layer 1 message bus instance
        engine: DiagnosticEngine instance (optional)

    Returns:
        DiagnosticConnector instance

    Raises:
        ImportError: If Diagnostic Engine is not available
    """
    if not DIAGNOSTIC_ENGINE_AVAILABLE:
        raise ImportError("Diagnostic Engine not available")

    return DiagnosticConnector(message_bus=message_bus, engine=engine)
