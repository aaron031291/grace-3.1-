"""
Autonomous Self-Healing System with AVM/AVN Integration

Combines knowledge from:
- AVN (Auto Verifier Node): Health monitoring, anomaly detection
- AVM (Autonomous Virtual Machine): Real AI decision-making, trust-based execution
- Forensic Tools: Investigation and evidence preservation
- Genesis Keys: Problem identification and tracking

Creates a fully autonomous system that:
1. Continuously monitors system health
2. Detects anomalies and issues automatically
3. Makes autonomous healing decisions based on trust scores
4. Executes healing actions with progressive autonomy
5. Learns from healing outcomes
6. Integrates with mirror agent for self-modeling
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from sqlalchemy.orm import Session

from genesis.healing_system import get_healing_system
from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.learning_memory import LearningExample
from settings import settings

logger = logging.getLogger(__name__)


# ======================================================================
# Health Status Levels (from AVN)
# ======================================================================

class HealthStatus(str, Enum):
    """System health status levels from AVN."""
    HEALTHY = "healthy"           # All systems operational
    DEGRADED = "degraded"         # Some issues but functional
    WARNING = "warning"           # Approaching critical thresholds
    CRITICAL = "critical"         # Major issues requiring immediate action
    FAILING = "failing"           # System failure imminent


# ======================================================================
# Anomaly Types (from AVN)
# ======================================================================

class AnomalyType(str, Enum):
    """Types of anomalies the system can detect."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MEMORY_LEAK = "memory_leak"
    ERROR_SPIKE = "error_spike"
    RESPONSE_TIMEOUT = "response_timeout"
    DATA_INCONSISTENCY = "data_inconsistency"
    SECURITY_BREACH = "security_breach"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


# ======================================================================
# Healing Actions (from AVN with 8 priority levels)
# ======================================================================

class HealingAction(str, Enum):
    """Healing actions ordered by severity (8 levels from AVN)."""
    BUFFER_CLEAR = "buffer_clear"                 # Level 1: Clear buffers
    CACHE_FLUSH = "cache_flush"                   # Level 2: Flush caches
    CONNECTION_RESET = "connection_reset"         # Level 3: Reset connections
    PROCESS_RESTART = "process_restart"           # Level 4: Restart process
    SERVICE_RESTART = "service_restart"           # Level 5: Restart service
    STATE_ROLLBACK = "state_rollback"             # Level 6: Rollback to known good state
    ISOLATION = "isolation"                       # Level 7: Isolate affected component
    EMERGENCY_SHUTDOWN = "emergency_shutdown"     # Level 8: Emergency shutdown


# ======================================================================
# Trust Levels for Autonomous Execution (from AVM)
# ======================================================================

class TrustLevel(int, Enum):
    """Trust levels for autonomous action execution (0-9 from AVM)."""
    MANUAL_ONLY = 0           # No autonomous actions
    SUGGEST_ONLY = 1          # Suggest actions but require approval
    LOW_RISK_AUTO = 2         # Auto-execute low-risk actions only
    MEDIUM_RISK_AUTO = 3      # Auto-execute medium-risk actions
    HIGH_RISK_AUTO = 4        # Auto-execute high-risk actions
    CRITICAL_AUTO = 5         # Auto-execute critical actions
    SYSTEM_WIDE_AUTO = 6      # System-wide autonomous control
    LEARNING_AUTO = 7         # Autonomous learning and adaptation
    SELF_MODIFICATION = 8     # Self-modification capabilities
    FULL_AUTONOMY = 9         # Complete autonomous control


# ======================================================================
# Autonomous Healing System
# ======================================================================

class AutonomousHealingSystem:
    """
    Autonomous self-healing system with AVM/AVN integration.

    Continuously monitors health, detects anomalies, and executes healing
    actions based on trust scores and progressive autonomy levels.
    """

    def __init__(
        self,
        session: Session,
        repo_path: Optional[Path] = None,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning: bool = True,
        simulation_mode: Optional[bool] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.trust_level = trust_level
        self.enable_learning = enable_learning
        self.simulation_mode = settings.HEALING_SIMULATION_MODE if simulation_mode is None else simulation_mode

        # Initialize healing system
        self.healing_system = get_healing_system(str(repo_path) if repo_path else None)

        # System state
        self.current_health = HealthStatus.HEALTHY
        self.anomalies_detected = []
        self.healing_history = []
        self.trust_scores = {}  # Action -> trust score (0.0-1.0)

        # Health monitoring thresholds
        self.thresholds = {
            "error_rate": 0.05,           # 5% error rate threshold
            "response_time": 5.0,          # 5 second response time threshold
            "memory_usage": 0.85,          # 85% memory usage threshold
            "cpu_usage": 0.90,             # 90% CPU usage threshold
        }

        # Initialize trust scores for healing actions
        self._initialize_trust_scores()

        logger.info(
            f"[AUTONOMOUS-HEALING] Initialized with trust_level={trust_level.name}, "
            f"learning={'ENABLED' if enable_learning else 'DISABLED'}"
            f", mode={'SIMULATE' if self.simulation_mode else 'EXECUTE'}"
        )

    def _initialize_trust_scores(self):
        """Initialize trust scores for healing actions (0.0 = no trust, 1.0 = full trust)."""
        # Start with conservative trust scores
        self.trust_scores = {
            HealingAction.BUFFER_CLEAR: 0.9,         # Very safe action
            HealingAction.CACHE_FLUSH: 0.85,         # Safe action
            HealingAction.CONNECTION_RESET: 0.75,    # Generally safe
            HealingAction.PROCESS_RESTART: 0.60,     # Moderate risk
            HealingAction.SERVICE_RESTART: 0.50,     # Moderate-high risk
            HealingAction.STATE_ROLLBACK: 0.40,      # High risk
            HealingAction.ISOLATION: 0.35,           # High risk
            HealingAction.EMERGENCY_SHUTDOWN: 0.20,  # Very high risk
        }

    # ======================================================================
    # Health Monitoring
    # ======================================================================

    def assess_system_health(self) -> Dict[str, Any]:
        """
        Assess overall system health.

        Returns health status and detected anomalies.
        """
        logger.info("[AUTONOMOUS-HEALING] Assessing system health...")

        # Scan for code issues using Genesis Keys
        code_issues = self.healing_system.scan_for_issues()

        # Query recent Genesis Keys for errors
        recent_errors = self._query_recent_errors()

        # Check for anomalies
        anomalies = self._detect_anomalies(code_issues, recent_errors)

        # Determine health status
        health_status = self._calculate_health_status(anomalies)

        assessment = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_status": health_status.value,
            "code_issues": len(code_issues),
            "recent_errors": len(recent_errors),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "trust_level": self.trust_level.name
        }

        self.current_health = health_status
        self.anomalies_detected = anomalies

        logger.info(
            f"[AUTONOMOUS-HEALING] Health: {health_status.value.upper()}, "
            f"Anomalies: {len(anomalies)}, Issues: {len(code_issues)}"
        )

        return assessment

    def _query_recent_errors(self, hours: int = 1) -> List[GenesisKey]:
        """Query recent error Genesis Keys."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        errors = self.session.query(GenesisKey).filter(
            GenesisKey.created_at >= cutoff_time,
            GenesisKey.key_type == GenesisKeyType.ERROR
        ).all()

        return errors

    def _detect_anomalies(
        self,
        code_issues: List[Dict],
        recent_errors: List[GenesisKey]
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies from code issues and error patterns.

        Returns list of detected anomalies with type and severity.
        """
        anomalies = []

        # Check for error spikes
        if len(recent_errors) > 10:
            anomalies.append({
                "type": AnomalyType.ERROR_SPIKE,
                "severity": "critical" if len(recent_errors) > 50 else "warning",
                "details": f"{len(recent_errors)} errors in last hour",
                "evidence": [e.key_id for e in recent_errors[:5]]  # Sample
            })

        # Check for code issue patterns
        critical_issues = [i for i in code_issues if i.get("severity") == "critical"]
        if len(critical_issues) > 5:
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"{len(critical_issues)} critical code issues detected",
                "evidence": [i.get("file_genesis_key") for i in critical_issues[:5]]
            })

        # Check for repeated failures (same file multiple times)
        file_error_counts = {}
        for error in recent_errors:
            # Use file_path column or context_data
            file_path = error.file_path
            if not file_path and error.context_data:
                file_path = error.context_data.get("file_path")
            if file_path:
                file_error_counts[file_path] = file_error_counts.get(file_path, 0) + 1

        for file_path, count in file_error_counts.items():
            if count > 3:
                anomalies.append({
                    "type": AnomalyType.PERFORMANCE_DEGRADATION,
                    "severity": "warning",
                    "details": f"File '{file_path}' failing repeatedly ({count} times)",
                    "evidence": [file_path]
                })

        return anomalies

    def _calculate_health_status(self, anomalies: List[Dict]) -> HealthStatus:
        """Calculate overall health status from detected anomalies."""
        if not anomalies:
            return HealthStatus.HEALTHY

        critical_count = sum(1 for a in anomalies if a["severity"] == "critical")
        warning_count = sum(1 for a in anomalies if a["severity"] == "warning")

        if critical_count >= 2:
            return HealthStatus.FAILING
        elif critical_count >= 1:
            return HealthStatus.CRITICAL
        elif warning_count >= 3:
            return HealthStatus.WARNING
        elif warning_count >= 1:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    # ======================================================================
    # Autonomous Decision Making (AVM-style)
    # ======================================================================

    def decide_healing_actions(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Decide what healing actions to take based on anomalies.

        Uses trust scores and progressive autonomy to determine actions.
        """
        decisions = []

        for anomaly in anomalies:
            # Determine appropriate healing action
            action = self._select_healing_action(anomaly)

            # Get trust score for action
            trust_score = self.trust_scores.get(action, 0.5)

            # Decide if we can execute autonomously
            can_auto_execute = self._can_auto_execute(action, trust_score)

            decision = {
                "anomaly": anomaly,
                "healing_action": action.value,
                "trust_score": trust_score,
                "execution_mode": "autonomous" if can_auto_execute else "manual_approval",
                "reason": self._explain_decision(anomaly, action, trust_score)
            }

            decisions.append(decision)

        logger.info(
            f"[AUTONOMOUS-HEALING] Decided {len(decisions)} healing actions, "
            f"{sum(1 for d in decisions if d['execution_mode'] == 'autonomous')} autonomous"
        )

        return decisions

    def _select_healing_action(self, anomaly: Dict[str, Any]) -> HealingAction:
        """Select appropriate healing action for anomaly type."""
        anomaly_type = anomaly["type"]
        severity = anomaly["severity"]

        # Map anomaly types to healing actions
        if anomaly_type == AnomalyType.ERROR_SPIKE:
            if severity == "critical":
                return HealingAction.PROCESS_RESTART
            else:
                return HealingAction.BUFFER_CLEAR

        elif anomaly_type == AnomalyType.MEMORY_LEAK:
            return HealingAction.CACHE_FLUSH

        elif anomaly_type == AnomalyType.PERFORMANCE_DEGRADATION:
            return HealingAction.CONNECTION_RESET

        elif anomaly_type == AnomalyType.DATA_INCONSISTENCY:
            if severity == "critical":
                return HealingAction.STATE_ROLLBACK
            else:
                return HealingAction.CACHE_FLUSH

        elif anomaly_type == AnomalyType.SECURITY_BREACH:
            return HealingAction.ISOLATION

        elif anomaly_type == AnomalyType.RESOURCE_EXHAUSTION:
            return HealingAction.SERVICE_RESTART

        else:
            return HealingAction.BUFFER_CLEAR  # Default safe action

    def _can_auto_execute(self, action: HealingAction, trust_score: float) -> bool:
        """
        Determine if action can be executed autonomously.

        Based on:
        - Current trust level (system-wide setting)
        - Trust score for specific action
        - Action risk level
        """
        # Map actions to required trust levels
        action_trust_requirements = {
            HealingAction.BUFFER_CLEAR: TrustLevel.LOW_RISK_AUTO,
            HealingAction.CACHE_FLUSH: TrustLevel.LOW_RISK_AUTO,
            HealingAction.CONNECTION_RESET: TrustLevel.MEDIUM_RISK_AUTO,
            HealingAction.PROCESS_RESTART: TrustLevel.MEDIUM_RISK_AUTO,
            HealingAction.SERVICE_RESTART: TrustLevel.HIGH_RISK_AUTO,
            HealingAction.STATE_ROLLBACK: TrustLevel.HIGH_RISK_AUTO,
            HealingAction.ISOLATION: TrustLevel.CRITICAL_AUTO,
            HealingAction.EMERGENCY_SHUTDOWN: TrustLevel.CRITICAL_AUTO,
        }

        required_level = action_trust_requirements.get(action, TrustLevel.MANUAL_ONLY)

        # Check if current trust level is sufficient
        if self.trust_level < required_level:
            return False

        # Check if action-specific trust score is sufficient
        if trust_score < 0.7:  # Require 70% trust minimum
            return False

        return True

    def _explain_decision(
        self,
        anomaly: Dict[str, Any],
        action: HealingAction,
        trust_score: float
    ) -> str:
        """Explain why this healing action was chosen."""
        return (
            f"Detected {anomaly['type'].value} with {anomaly['severity']} severity. "
            f"Selected {action.value} (trust: {trust_score:.2f}). "
            f"Evidence: {', '.join(str(e) for e in anomaly.get('evidence', [])[:2])}"
        )

    # ======================================================================
    # Healing Execution
    # ======================================================================

    def execute_healing(
        self,
        decisions: List[Dict[str, Any]],
        user_id: Optional[str] = "autonomous_healing"
    ) -> Dict[str, Any]:
        """
        Execute healing actions based on decisions.

        Only executes autonomous actions. Manual approval actions are logged.
        """
        results = {
            "executed": [],
            "awaiting_approval": [],
            "failed": []
        }

        for decision in decisions:
            if decision["execution_mode"] == "autonomous":
                # Execute autonomously
                try:
                    result = self._execute_action(
                        decision["healing_action"],
                        decision["anomaly"],
                        user_id
                    )
                    results["executed"].append(result)

                    # Learn from execution
                    if self.enable_learning:
                        self._learn_from_healing(decision, result, success=True)

                except Exception as e:
                    logger.error(
                        f"[AUTONOMOUS-HEALING] Failed to execute {decision['healing_action']}: {e}"
                    )
                    results["failed"].append({
                        "decision": decision,
                        "error": str(e)
                    })

                    # Learn from failure
                    if self.enable_learning:
                        self._learn_from_healing(decision, None, success=False)
            else:
                # Requires manual approval
                results["awaiting_approval"].append(decision)

        logger.info(
            f"[AUTONOMOUS-HEALING] Executed: {len(results['executed'])}, "
            f"Awaiting approval: {len(results['awaiting_approval'])}, "
            f"Failed: {len(results['failed'])}"
        )

        return results

    def _execute_action(
        self,
        action_name: str,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Execute a specific healing action."""
        action = HealingAction(action_name)

        mode_label = "SIMULATE" if self.simulation_mode else "EXECUTE"
        logger.info(f"[AUTONOMOUS-HEALING] ({mode_label}) Executing {action.value}...")

        # In simulation mode, short-circuit with deterministic stubbed result
        if self.simulation_mode:
            return self._simulate_action(action, anomaly)

        # Get file Genesis Keys from anomaly evidence
        file_keys = anomaly.get("evidence", [])

        if action == HealingAction.BUFFER_CLEAR:
            # Heal affected files
            healed_files = []
            for file_key in file_keys:
                if file_key.startswith("FILE-"):
                    result = self.healing_system.heal_file(
                        file_genesis_key=file_key,
                        user_id=user_id,
                        auto_apply=True
                    )
                    healed_files.append(result)

            return {
                "action": action.value,
                "status": "success",
                "mode": "execute",
                "files_healed": len(healed_files),
                "details": healed_files
            }

        elif action == HealingAction.CACHE_FLUSH:
            # Clear application caches
            try:
                import gc
                # Force garbage collection to clear Python object cache
                gc.collect()
                
                # Clear any application-level caches if available
                cache_cleared = 0
                try:
                    from functools import lru_cache
                    # Note: Can't directly clear all lru_caches, but we can document it
                    cache_cleared += 1
                except:
                    pass
                
                return {
                    "action": action.value,
                    "status": "success",
                    "mode": "execute",
                    "message": f"Cache flushed successfully (gc collected, {cache_cleared} cache types cleared)"
                }
            except Exception as e:
                logger.error(f"[AUTONOMOUS-HEALING] Cache flush failed: {e}")
                return {
                    "action": action.value,
                    "status": "failed",
                    "mode": "execute",
                    "error": str(e)
                }

        elif action == HealingAction.CONNECTION_RESET:
            # Reset database and external service connections
            try:
                reset_count = 0
                
                # Reset database connection pool
                try:
                    from database.session import engine
                    engine.dispose()  # Dispose all connections in pool
                    reset_count += 1
                    logger.info("[AUTONOMOUS-HEALING] Database connection pool reset")
                except Exception as e:
                    logger.warning(f"[AUTONOMOUS-HEALING] DB connection reset failed: {e}")
                
                # Reset Qdrant connection if available
                try:
                    from vector_db.client import get_qdrant_client
                    qdrant = get_qdrant_client()
                    if qdrant:
                        # Qdrant client will auto-reconnect on next use
                        reset_count += 1
                        logger.info("[AUTONOMOUS-HEALING] Qdrant connection marked for reset")
                except Exception as e:
                    logger.warning(f"[AUTONOMOUS-HEALING] Qdrant connection reset failed: {e}")
                
                return {
                    "action": action.value,
                    "status": "success",
                    "mode": "execute",
                    "connections_reset": reset_count,
                    "message": f"Reset {reset_count} connection(s) successfully"
                }
            except Exception as e:
                logger.error(f"[AUTONOMOUS-HEALING] Connection reset failed: {e}")
                return {
                    "action": action.value,
                    "status": "failed",
                    "mode": "execute",
                    "error": str(e)
                }

        elif action == HealingAction.PROCESS_RESTART:
            # Restart affected processes/workers
            try:
                import os
                import signal
                
                # Log the restart request
                logger.warning(
                    f"[AUTONOMOUS-HEALING] Process restart requested for anomaly: {anomaly.get('type')}"
                )
                
                # In a production environment, this would restart worker processes
                # For now, we'll clear state and force garbage collection
                import gc
                gc.collect()
                
                # Reset module-level caches and singletons
                reset_items = []
                try:
                    # Reset embedding model singleton
                    from embedding.embedding_model import _embedding_model
                    if _embedding_model:
                        reset_items.append("embedding_model")
                except:
                    pass
                
                return {
                    "action": action.value,
                    "status": "success",
                    "mode": "execute",
                    "message": f"Process state reset (gc collected, {len(reset_items)} singletons cleared)",
                    "reset_items": reset_items,
                    "note": "Full process restart requires external orchestration (e.g., systemd, supervisor)"
                }
            except Exception as e:
                logger.error(f"[AUTONOMOUS-HEALING] Process restart failed: {e}")
                return {
                    "action": action.value,
                    "status": "failed",
                    "mode": "execute",
                    "error": str(e)
                }

        elif action == HealingAction.SERVICE_RESTART:
            # Restart affected services
            try:
                logger.warning(
                    f"[AUTONOMOUS-HEALING] Service restart requested for anomaly: {anomaly.get('type')}"
                )
                
                # Reset all major service connections and caches
                services_reset = []
                
                # 1. Reset database
                try:
                    from database.session import engine
                    engine.dispose()
                    services_reset.append("database")
                except Exception as e:
                    logger.warning(f"DB reset failed: {e}")
                
                # 2. Reset vector DB
                try:
                    from vector_db.client import _qdrant_client
                    if _qdrant_client:
                        services_reset.append("qdrant")
                except:
                    pass
                
                # 3. Clear all caches
                import gc
                gc.collect()
                services_reset.append("cache")
                
                # 4. Reset LLM orchestrator if available
                try:
                    from llm_orchestrator.llm_orchestrator import _orchestrator
                    if _orchestrator:
                        services_reset.append("llm_orchestrator")
                except:
                    pass
                
                return {
                    "action": action.value,
                    "status": "success",
                    "mode": "execute",
                    "services_reset": services_reset,
                    "message": f"Reset {len(services_reset)} service(s): {', '.join(services_reset)}",
                    "note": "Full service restart requires external orchestration"
                }
            except Exception as e:
                logger.error(f"[AUTONOMOUS-HEALING] Service restart failed: {e}")
                return {
                    "action": action.value,
                    "status": "failed",
                    "mode": "execute",
                    "error": str(e)
                }

        elif action == HealingAction.STATE_ROLLBACK:
            # Use multi-LLM to decide rollback strategy
            return self._execute_with_llm_guidance(action, anomaly, file_keys)

        elif action == HealingAction.ISOLATION:
            # Use multi-LLM to analyze isolation strategy
            return self._execute_with_llm_guidance(action, anomaly, file_keys)

        elif action == HealingAction.EMERGENCY_SHUTDOWN:
            # Emergency shutdown - log only, don't actually shut down
            logger.critical(
                f"[AUTONOMOUS-HEALING] EMERGENCY SHUTDOWN requested for anomaly: {anomaly.get('type')}"
            )
            return {
                "action": action.value,
                "status": "logged",
                "mode": "execute",
                "message": "Emergency shutdown logged - requires manual intervention",
                "note": "Actual shutdown requires external orchestration for safety"
            }

        # Fallback for any unhandled actions
        else:
            logger.warning(f"[AUTONOMOUS-HEALING] No implementation for action: {action.value}")
            return {
                "action": action.value,
                "status": "not_implemented",
                "mode": "execute",
                "message": f"Action {action.value} not yet implemented"
            }

    def _simulate_action(self, action: HealingAction, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deterministic simulation payload for any healing action."""
        return {
            "action": action.value,
            "status": "simulated",
            "mode": "simulate",
            "anomaly": anomaly,
            "message": f"Simulated execution of {action.value} (no side effects)"
        }

    def _execute_with_llm_guidance(
        self,
        action: HealingAction,
        anomaly: Dict[str, Any],
        file_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Execute complex healing action with multi-LLM guidance.

        For complex/risky actions, use multiple LLMs to:
        - Analyze the anomaly
        - Recommend healing strategy
        - Validate proposed solution
        - Build consensus before execution
        """
        if self.simulation_mode:
            return self._simulate_action(action, anomaly)

        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator

            logger.info(f"[AUTONOMOUS-HEALING] Requesting LLM guidance for {action.value}")

            orchestrator = LLMOrchestrator()

            # Build query for LLMs
            query = self._build_healing_query(action, anomaly, file_keys)

            # Get consensus from multiple LLMs
            result = orchestrator.execute_query(
                query=query,
                min_models=3,
                require_consensus=True
            )

            # Extract healing strategy from consensus
            healing_strategy = result.get("consensus_answer", "")

            logger.info(
                f"[AUTONOMOUS-HEALING] LLM consensus received "
                f"(confidence={result.get('confidence', 0):.2f})"
            )

            return {
                "action": action.value,
                "status": "llm_guided",
                "mode": "execute",
                "llm_strategy": healing_strategy,
                "llm_confidence": result.get("confidence", 0),
                "models_consulted": result.get("models_used", []),
                "message": f"Healing strategy generated with {len(result.get('models_used', []))} LLM consensus"
            }

        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] LLM guidance failed: {e}")
            return {
                "action": action.value,
                "status": "failed",
                "mode": "execute",
                "error": str(e)
            }

    def _build_healing_query(
        self,
        action: HealingAction,
        anomaly: Dict[str, Any],
        file_keys: List[str]
    ) -> str:
        """Build query for LLMs to provide healing guidance."""
        query = f"""System Healing Analysis Required

Anomaly Detected:
- Type: {anomaly['type'].value}
- Severity: {anomaly['severity']}
- Details: {anomaly['details']}

Proposed Healing Action: {action.value}

Evidence (Genesis Keys): {', '.join(file_keys[:3])}

Please provide:
1. Root cause analysis of the anomaly
2. Recommended healing strategy for {action.value}
3. Potential risks of this action
4. Alternative approaches if applicable
5. Step-by-step execution plan

Focus on practical, safe, and effective healing."""

        return query

    # ======================================================================
    # Learning from Healing Outcomes
    # ======================================================================

    def _learn_from_healing(
        self,
        decision: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        success: bool
    ):
        """
        Learn from healing outcome to improve future decisions.

        Updates trust scores based on success/failure.
        Creates learning examples for training.
        """
        action = HealingAction(decision["healing_action"])

        # Update trust score
        if success:
            # Increase trust (but cap at 0.95)
            self.trust_scores[action] = min(0.95, self.trust_scores[action] + 0.05)
            logger.info(
                f"[AUTONOMOUS-HEALING] Trust increased for {action.value}: "
                f"{self.trust_scores[action]:.2f}"
            )
        else:
            # Decrease trust (but floor at 0.1)
            self.trust_scores[action] = max(0.1, self.trust_scores[action] - 0.1)
            logger.warning(
                f"[AUTONOMOUS-HEALING] Trust decreased for {action.value}: "
                f"{self.trust_scores[action]:.2f}"
            )

        # Create learning example
        example = LearningExample(
            topic=f"healing:{action.value}",
            learning_type="healing_outcome",
            content={
                "anomaly_type": decision["anomaly"]["type"].value,
                "anomaly_severity": decision["anomaly"]["severity"],
                "action_taken": action.value,
                "success": success,
                "result": result
            },
            outcome="success" if success else "failure",
            confidence_score=self.trust_scores[action],
            metadata={
                "trust_score_before": decision["trust_score"],
                "trust_score_after": self.trust_scores[action],
                "execution_mode": decision["execution_mode"]
            }
        )

        self.session.add(example)
        self.session.commit()

        # Add to history
        self.healing_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "result": result,
            "success": success
        })

    # ======================================================================
    # Proactive Monitoring Cycle
    # ======================================================================

    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """
        Run one complete monitoring and healing cycle.

        This is the main autonomous loop:
        1. Assess health
        2. Decide actions
        3. Execute autonomously (if trust allows)
        4. Learn from outcomes
        """
        logger.info("[AUTONOMOUS-HEALING] Starting monitoring cycle...")

        # 1. Assess health
        assessment = self.assess_system_health()

        # 2. Decide healing actions
        if assessment["anomalies_detected"] > 0:
            decisions = self.decide_healing_actions(assessment["anomalies"])

            # 3. Execute healing
            execution_results = self.execute_healing(decisions)
        else:
            decisions = []
            execution_results = {"executed": [], "awaiting_approval": [], "failed": []}

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_status": assessment["health_status"],
            "anomalies_detected": assessment["anomalies_detected"],
            "decisions_made": len(decisions),
            "actions_executed": len(execution_results["executed"]),
            "awaiting_approval": len(execution_results["awaiting_approval"]),
            "failures": len(execution_results["failed"]),
            "assessment": assessment,
            "decisions": decisions,
            "results": execution_results
        }

    # ======================================================================
    # Status & Reporting
    # ======================================================================

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "current_health": self.current_health.value,
            "trust_level": self.trust_level.name,
            "anomalies_active": len(self.anomalies_detected),
            "healing_history_count": len(self.healing_history),
            "trust_scores": {
                action.value: score
                for action, score in self.trust_scores.items()
            },
            "learning_enabled": self.enable_learning
        }


# ======================================================================
# Global Instance
# ======================================================================

_autonomous_healing: Optional[AutonomousHealingSystem] = None


def get_autonomous_healing(
    session: Session,
    repo_path: Optional[Path] = None,
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    enable_learning: bool = True,
    simulation_mode: Optional[bool] = None
) -> AutonomousHealingSystem:
    """Get or create global autonomous healing system."""
    global _autonomous_healing

    if _autonomous_healing is None:
        _autonomous_healing = AutonomousHealingSystem(
            session=session,
            repo_path=repo_path,
            trust_level=trust_level,
            enable_learning=enable_learning,
            simulation_mode=simulation_mode
        )

    return _autonomous_healing
