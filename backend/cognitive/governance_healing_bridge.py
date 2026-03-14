"""
cognitive/governance_healing_bridge.py
───────────────────────────────────────────────────────────────────────
Governance → Self-Healing Bridge  (Phase 3.1)

Connects the Trust Engine + Confidence Scorer (Phase 2) to the
Self-Healing pipeline (Phase 1) so that governance decisions
automatically trigger healing actions.

Design (per Aaron's three-system architecture):
  System 1: Governance (Trust + Confidence + KPIs)
  System 2: Self-Healing (Error Pipeline + Deterministic Healer + Coding Agent)
  System 3: Self-Mirroring (Telemetry + Behavioral Patterns)

This bridge makes System 1 → System 2 integration real:
  - When trust < 90 AND confidence >= 60 → trigger self-healing
  - Different trust thresholds trigger different healing strategies
  - Confidence acts as a noise filter (don't heal on uncertain data)
  - All triggers are logged for provenance via Genesis Keys
  - Events published on event bus for visibility

Trust → Healing Strategy:
  trust >= 90                          → no action (healthy)
  70 <= trust < 90  AND conf >= 60     → self_healing (light: cache flush, reconnect)
  50 <= trust < 70  AND conf >= 60     → coding_agent (write a fix)
  trust < 50        AND conf >= 60     → escalate to human + emergency healing
  ANY trust         AND conf < 60      → skip (data too noisy to act on)

Runs as a background thread, polling every 60 seconds.
Uses TimeSense to adapt polling interval (faster during business hours).
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────
TRUST_HEALTHY_THRESHOLD = 90       # trust >= 90 → no action needed
TRUST_HEALING_THRESHOLD = 70       # 70-89 → light self-healing
TRUST_CODING_AGENT_THRESHOLD = 50  # 50-69 → coding agent fix
CONFIDENCE_MIN_THRESHOLD = 60.0    # minimum confidence to act on signal
POLL_INTERVAL_S = 60               # default polling interval
COOLDOWN_S = 300                   # 5 min cooldown per component after trigger


class GovernanceHealingBridge:
    """
    Bridges governance trust scores to self-healing actions.

    Monitors Trust Engine component scores. When trust drops below
    threshold AND confidence is high enough to trust the signal,
    triggers the appropriate healing action automatically.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cooldowns: Dict[str, float] = {}  # component_id → last_trigger_time
        self._trigger_history: List[Dict[str, Any]] = []
        self._max_history = 200
        self._total_triggers = 0
        self._total_skipped_low_confidence = 0
        self._total_healed = 0
        self._lock = threading.Lock()

    # ── Start / Stop ──────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the governance healing monitor loop."""
        if self._running:
            logger.info("[GOV-HEAL] Already running")
            return False
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="grace-gov-heal-bridge",
        )
        self._thread.start()
        logger.info("[GOV-HEAL] ✅ Governance → Self-Healing bridge started (poll every %ds)", POLL_INTERVAL_S)
        return True

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("[GOV-HEAL] Bridge stopped")

    # ── Main Monitor Loop ─────────────────────────────────────────────

    def _monitor_loop(self):
        """Background loop: poll trust scores and trigger healing when needed."""
        time.sleep(15)  # let startup settle
        while self._running:
            try:
                self._evaluate_all_components()
            except Exception as e:
                logger.error("[GOV-HEAL] Monitor cycle error: %s", e)

            # Adapt interval using TimeSense
            interval = self._get_adaptive_interval()
            time.sleep(interval)

    def _get_adaptive_interval(self) -> int:
        """Use TimeSense to adapt polling interval."""
        try:
            from cognitive.time_sense import TimeSense
            ctx = TimeSense.now_context()
            if ctx.get("period") == "late_night":
                return 180  # 3 min at night
            if ctx.get("is_business_hours"):
                return 30   # 30s during business hours
        except Exception:
            pass
        return POLL_INTERVAL_S

    # ── Core Evaluation Logic ─────────────────────────────────────────

    def _evaluate_all_components(self):
        """Check all tracked components and trigger healing as needed."""
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
        except Exception as e:
            logger.debug("[GOV-HEAL] Trust engine unavailable: %s", e)
            return

        system_trust = te.get_system_trust()
        components = system_trust.get("components", {})

        if not components:
            return  # no data yet

        triggered = []
        for comp_id, comp_data in components.items():
            trust = comp_data.get("trust", 0.0)

            # Skip healthy components
            if trust >= TRUST_HEALTHY_THRESHOLD:
                continue

            # Check confidence
            conf = te.get_confidence(comp_id)
            confidence = conf.get("confidence", 0.0)

            if confidence < CONFIDENCE_MIN_THRESHOLD:
                self._total_skipped_low_confidence += 1
                logger.debug(
                    "[GOV-HEAL] %s trust=%.1f but confidence=%.1f < %.1f — skipping (noisy signal)",
                    comp_id, trust, confidence, CONFIDENCE_MIN_THRESHOLD,
                )
                continue

            # Check cooldown
            if self._in_cooldown(comp_id):
                continue

            # Determine healing strategy
            strategy = self._determine_strategy(trust)

            # Execute the trigger
            result = self._trigger_healing(comp_id, comp_data, trust, confidence, strategy)
            if result:
                triggered.append(result)

        # Publish summary event if any triggers fired
        if triggered:
            try:
                from cognitive.event_bus import publish_async
                publish_async("governance.healing_triggered", {
                    "components_triggered": len(triggered),
                    "details": triggered,
                    "system_trust": system_trust.get("system_trust", 0.0),
                }, source="governance_healing_bridge")
            except Exception:
                pass

    def _determine_strategy(self, trust: float) -> str:
        """Map trust score to healing strategy."""
        if trust >= TRUST_HEALING_THRESHOLD:
            return "self_healing"       # 70-89: light healing
        elif trust >= TRUST_CODING_AGENT_THRESHOLD:
            return "coding_agent"       # 50-69: write a fix
        else:
            return "human_escalation"   # <50: emergency + human

    def _in_cooldown(self, comp_id: str) -> bool:
        """Check if component is in cooldown (recently triggered)."""
        with self._lock:
            last = self._cooldowns.get(comp_id, 0)
            return (time.monotonic() - last) < COOLDOWN_S

    def _set_cooldown(self, comp_id: str):
        """Set cooldown timer for a component."""
        with self._lock:
            self._cooldowns[comp_id] = time.monotonic()

    # ── Trigger Execution ─────────────────────────────────────────────

    def _trigger_healing(
        self,
        comp_id: str,
        comp_data: Dict,
        trust: float,
        confidence: float,
        strategy: str,
    ) -> Optional[Dict[str, Any]]:
        """Execute the healing trigger for a component."""
        logger.info(
            "[GOV-HEAL] 🔧 Triggering %s for '%s' (trust=%.1f, confidence=%.1f)",
            strategy, comp_id, trust, confidence,
        )

        result = {
            "component": comp_id,
            "trust": trust,
            "confidence": confidence,
            "strategy": strategy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "healed": False,
            "detail": "",
        }

        try:
            if strategy == "self_healing":
                result.update(self._execute_self_healing(comp_id, trust, confidence))
            elif strategy == "coding_agent":
                result.update(self._execute_coding_agent(comp_id, trust, confidence, comp_data))
            elif strategy == "human_escalation":
                result.update(self._execute_human_escalation(comp_id, trust, confidence))
        except Exception as e:
            result["detail"] = f"Trigger failed: {e}"
            logger.error("[GOV-HEAL] Trigger execution error for %s: %s", comp_id, e)

        # Record result
        self._set_cooldown(comp_id)
        self._total_triggers += 1
        if result.get("healed"):
            self._total_healed += 1

        with self._lock:
            self._trigger_history.append(result)
            if len(self._trigger_history) > self._max_history:
                self._trigger_history = self._trigger_history[-self._max_history:]

        # Publish event for this specific trigger
        try:
            from cognitive.event_bus import publish_async
            publish_async("governance.component_healing", result, source="governance_healing_bridge")
        except Exception:
            pass

        # Record in trust engine KPI
        try:
            from cognitive.trust_engine import get_trust_engine
            get_trust_engine().record_kpi(comp_id, "governance_healing_triggered")
        except Exception:
            pass

        # Genesis key tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"Governance healing: {strategy} for {comp_id} (trust={trust:.1f}, conf={confidence:.1f})",
                how="GovernanceHealingBridge._trigger_healing",
                output_data=result,
                tags=["governance", "healing", strategy, comp_id],
            )
        except Exception:
            pass

        return result

    def _execute_self_healing(self, comp_id: str, trust: float, confidence: float) -> Dict:
        """Light self-healing: cache flush, connection reset, probe services."""
        actions = []

        # 1. Try trust engine's own remediation
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
            remediation = te.trigger_remediation(comp_id)
            if remediation.get("action") != "none":
                actions.append(f"Trust remediation: {remediation.get('action')}")
        except Exception as e:
            actions.append(f"Trust remediation skipped: {e}")

        # 2. Report to error pipeline as a governance-detected issue
        try:
            from self_healing.error_pipeline import get_error_pipeline
            get_error_pipeline().handle(
                exc=RuntimeError(f"Governance: {comp_id} trust={trust:.1f} below threshold"),
                context={
                    "source": "governance_healing_bridge",
                    "trust": trust,
                    "confidence": confidence,
                    "strategy": "self_healing",
                },
                module="governance",
                function=comp_id,
            )
            actions.append("Error pipeline notified")
        except Exception as e:
            actions.append(f"Error pipeline notify failed: {e}")

        # 3. Run diagnostic check on the specific component
        try:
            from cognitive.autonomous_diagnostics import AutonomousDiagnostics
            diag = AutonomousDiagnostics.get_instance()
            diag_result = diag.on_error(
                error_type="governance_trust_drop",
                error_message=f"Component {comp_id} trust dropped to {trust:.1f}",
                component=comp_id,
                context={"trust": trust, "confidence": confidence},
            )
            if diag_result.get("auto_fixed"):
                actions.append("Diagnostic auto-fix applied")
        except Exception as e:
            actions.append(f"Diagnostic check skipped: {e}")

        healed = any("applied" in a or "notified" in a for a in actions)
        return {"healed": healed, "detail": " | ".join(actions)}

    def _execute_coding_agent(self, comp_id: str, trust: float, confidence: float, comp_data: Dict) -> Dict:
        """Medium severity: submit coding agent task to investigate and fix."""
        try:
            from api.autonomous_loop_api import submit_coding_task
            task_id = submit_coding_task(
                instructions=(
                    f"Governance alert: component '{comp_id}' has trust score {trust:.1f}/100 "
                    f"(confidence: {confidence:.1f}/100). Investigate why this component's "
                    f"output quality is degraded and apply fixes.\n"
                    f"Component trend: {comp_data.get('trend', 'unknown')}\n"
                    f"Remediation type suggested: coding_agent"
                ),
                context={
                    "component": comp_id,
                    "trust": trust,
                    "confidence": confidence,
                    "trend": comp_data.get("trend", "unknown"),
                    "source": "governance_healing_bridge",
                },
                priority=3,
                error_class="governance",
                origin="governance_healing_bridge",
            )
            return {
                "healed": True,
                "detail": f"Coding agent task {task_id} submitted for {comp_id}",
            }
        except Exception as e:
            return {"healed": False, "detail": f"Coding agent unavailable: {e}"}

    def _execute_human_escalation(self, comp_id: str, trust: float, confidence: float) -> Dict:
        """Critical: trust < 50 — escalate to human + attempt emergency healing."""
        actions = []

        # 1. Fire human alert
        try:
            from cognitive.notification_system import get_notifications
            get_notifications().alert(
                title=f"🚨 Critical: {comp_id} trust at {trust:.1f}",
                message=(
                    f"Component '{comp_id}' has critically low trust ({trust:.1f}/100) "
                    f"with high confidence ({confidence:.1f}/100). "
                    f"Human review required."
                ),
                severity="critical",
            )
            actions.append("Human alert sent")
        except Exception as e:
            actions.append(f"Human alert failed: {e}")

        # 2. Still attempt emergency healing
        try:
            from cognitive.trust_engine import get_trust_engine
            get_trust_engine().trigger_remediation(comp_id)
            actions.append("Emergency remediation triggered")
        except Exception as e:
            actions.append(f"Emergency remediation failed: {e}")

        # 3. Submit to coding agent with highest priority
        try:
            from api.autonomous_loop_api import submit_coding_task
            submit_coding_task(
                instructions=(
                    f"CRITICAL: Component '{comp_id}' trust at {trust:.1f}/100. "
                    f"This is a governance escalation. Investigate and fix urgently."
                ),
                context={
                    "component": comp_id,
                    "trust": trust,
                    "confidence": confidence,
                    "source": "governance_healing_bridge",
                    "severity": "critical",
                },
                priority=1,  # highest
                error_class="governance_critical",
                origin="governance_healing_bridge",
            )
            actions.append("Critical coding agent task submitted")
        except Exception as e:
            actions.append(f"Critical coding task failed: {e}")

        # 4. Record in genesis as error
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what=f"CRITICAL trust drop: {comp_id} at {trust:.1f}",
                how="GovernanceHealingBridge.human_escalation",
                output_data={"trust": trust, "confidence": confidence},
                tags=["governance", "critical", comp_id],
                is_error=True,
            )
        except Exception:
            pass

        return {"healed": False, "detail": " | ".join(actions), "escalated": True}

    # ── Status / Dashboard ────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status for API/dashboard."""
        with self._lock:
            recent = self._trigger_history[-10:] if self._trigger_history else []
        return {
            "running": self._running,
            "total_triggers": self._total_triggers,
            "total_healed": self._total_healed,
            "total_skipped_low_confidence": self._total_skipped_low_confidence,
            "recent_triggers": recent,
            "thresholds": {
                "trust_healthy": TRUST_HEALTHY_THRESHOLD,
                "trust_healing": TRUST_HEALING_THRESHOLD,
                "trust_coding_agent": TRUST_CODING_AGENT_THRESHOLD,
                "confidence_min": CONFIDENCE_MIN_THRESHOLD,
                "cooldown_s": COOLDOWN_S,
            },
        }

    def get_trigger_history(self, limit: int = 50) -> List[Dict]:
        """Return recent trigger history."""
        with self._lock:
            return list(reversed(self._trigger_history[-limit:]))

    def force_evaluate(self) -> Dict[str, Any]:
        """Manually trigger an evaluation cycle (for API/testing)."""
        try:
            self._evaluate_all_components()
            return {"status": "evaluated", "triggers": self._total_triggers}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ── Singleton ─────────────────────────────────────────────────────────
_bridge: Optional[GovernanceHealingBridge] = None


def get_governance_healing_bridge() -> GovernanceHealingBridge:
    global _bridge
    if _bridge is None:
        _bridge = GovernanceHealingBridge()
    return _bridge
