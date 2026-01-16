"""
Layer 4 - Action Router: Response Execution Layer

Routes decisions to appropriate actions:
- Alert Human: Notify operators of issues
- Trigger Self-Healing: Attempt automatic fixes
- Freeze System: Halt operations for safety
- Recommend Learning: Capture patterns for improvement
- Do Nothing: System is healthy, no action needed
- Trigger CI/CD: Initiate pipeline for testing/deployment
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .sensors import SensorData
from .interpreters import InterpretedData, Pattern, PatternType
from .judgement import JudgementResult, HealthStatus, RiskLevel, ForensicFinding
from .healing import HealingExecutor, HealingActionType, get_healing_executor

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions the router can execute."""
    ALERT_HUMAN = "alert_human"
    TRIGGER_HEALING = "trigger_healing"
    FREEZE_SYSTEM = "freeze_system"
    RECOMMEND_LEARNING = "recommend_learning"
    DO_NOTHING = "do_nothing"
    TRIGGER_CICD = "trigger_cicd"
    ESCALATE = "escalate"
    LOG_OBSERVATION = "log_observation"


class ActionPriority(str, Enum):
    """Priority levels for actions."""
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    """Status of action execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ActionResult:
    """Result of an executed action."""
    action_id: str
    action_type: ActionType
    status: ActionStatus
    message: str
    details: Dict = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ActionDecision:
    """A decision about what action to take."""
    decision_id: str
    action_type: ActionType
    priority: ActionPriority
    reason: str
    confidence: float
    target_components: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    results: List[ActionResult] = field(default_factory=list)
    decision_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealingAction:
    """A self-healing action to execute."""
    healing_id: str
    name: str
    description: str
    target_component: str
    command: Optional[str] = None
    function: Optional[str] = None
    parameters: Dict = field(default_factory=dict)
    reversible: bool = True
    estimated_duration_ms: float = 1000.0


@dataclass
class AlertConfig:
    """Configuration for alerting."""
    alert_file: str = "alerts.jsonl"
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    slack_channel: Optional[str] = None
    enable_sound: bool = False


@dataclass
class CICDConfig:
    """Configuration for CI/CD triggering."""
    enabled: bool = True
    pipeline_command: Optional[str] = None
    github_actions_workflow: Optional[str] = None
    test_command: str = "pytest tests/ -v"
    pre_flight_checks: List[str] = field(default_factory=list)


class ActionRouter:
    """
    Layer 4 - Action Router: Executes appropriate responses based on judgement.

    This layer routes decisions to concrete actions:
    - Alert Human: Send notifications to operators
    - Trigger Healing: Execute automatic recovery procedures
    - Freeze System: Halt dangerous operations
    - Recommend Learning: Capture insights for future improvement
    - Do Nothing: Acknowledge healthy state
    - Trigger CI/CD: Run test pipelines
    """

    # Predefined healing actions
    HEALING_ACTIONS = {
        'restart_service': HealingAction(
            healing_id="HEAL-001",
            name="Restart Service",
            description="Restart a failing service",
            target_component="services",
            command="systemctl restart {service_name}",
            reversible=True,
        ),
        'clear_cache': HealingAction(
            healing_id="HEAL-002",
            name="Clear Cache",
            description="Clear application cache",
            target_component="cache",
            function="clear_application_cache",
            reversible=True,
        ),
        'reconnect_database': HealingAction(
            healing_id="HEAL-003",
            name="Reconnect Database",
            description="Reset database connection pool",
            target_component="database",
            function="reset_database_connection",
            reversible=True,
        ),
        'reset_vector_db': HealingAction(
            healing_id="HEAL-004",
            name="Reset Vector DB Client",
            description="Reset vector database connection",
            target_component="vector_db",
            function="reset_vector_db_client",
            reversible=True,
        ),
        'run_garbage_collection': HealingAction(
            healing_id="HEAL-005",
            name="Run GC",
            description="Force garbage collection to free memory",
            target_component="memory",
            function="force_garbage_collection",
            reversible=False,
        ),
        # WHOLE-SYSTEM HEALING ACTIONS
        'fix_code_issues': HealingAction(
            healing_id="HEAL-006",
            name="Fix Code Issues",
            description="Automatically fix detected security vulnerabilities",
            target_component="code",
            function="fix_code_issues",
            reversible=True,
        ),
        'restart_container': HealingAction(
            healing_id="HEAL-007",
            name="Restart Container",
            description="Restart unhealthy Docker container",
            target_component="containers",
            command="docker restart {container_name}",
            reversible=True,
        ),
        'clear_disk_space': HealingAction(
            healing_id="HEAL-008",
            name="Clear Disk Space",
            description="Clear temporary files and logs to free disk space",
            target_component="disk",
            function="clear_disk_space",
            reversible=False,
        ),
        'reload_embedding_model': HealingAction(
            healing_id="HEAL-009",
            name="Reload Embedding Model",
            description="Reload embedding model to fix model issues",
            target_component="embedding",
            function="reload_embedding_model",
            reversible=True,
        ),
    }

    def __init__(
        self,
        alert_config: AlertConfig = None,
        cicd_config: CICDConfig = None,
        log_dir: str = None,
        enable_healing: bool = True,
        enable_freeze: bool = True,
        dry_run: bool = False
    ):
        """Initialize the action router."""
        self.alert_config = alert_config or AlertConfig()
        self.cicd_config = cicd_config or CICDConfig()
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs"
        self.enable_healing = enable_healing
        self.enable_freeze = enable_freeze
        self.dry_run = dry_run
        self._decision_counter = 0
        self._action_counter = 0

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Healing function registry
        self._healing_functions: Dict[str, Callable] = {}
        self._register_default_healing_functions()

    def _register_default_healing_functions(self):
        """Register default healing functions."""
        self._healing_functions['clear_application_cache'] = self._heal_clear_cache
        self._healing_functions['reset_database_connection'] = self._heal_reset_database
        self._healing_functions['reset_vector_db_client'] = self._heal_reset_vector_db
        self._healing_functions['force_garbage_collection'] = self._heal_garbage_collection
        # WHOLE-SYSTEM HEALING FUNCTIONS
        self._healing_functions['fix_code_issues'] = self._heal_code_issues
        self._healing_functions['clear_disk_space'] = self._heal_clear_disk_space
        self._healing_functions['reload_embedding_model'] = self._heal_reload_embedding

    def register_healing_function(self, name: str, func: Callable):
        """Register a custom healing function."""
        self._healing_functions[name] = func

    def route(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> ActionDecision:
        """Route judgement to appropriate action."""
        start_time = datetime.utcnow()
        self._decision_counter += 1

        # Create decision based on judgement
        decision = self._create_decision(sensor_data, interpreted_data, judgement)

        # Execute actions based on decision
        if not self.dry_run:
            decision.results = self._execute_actions(decision, sensor_data, interpreted_data, judgement)

        end_time = datetime.utcnow()
        decision.decision_timestamp = end_time

        # Log the decision
        self._log_decision(decision)

        return decision

    def _create_decision(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> ActionDecision:
        """Create action decision based on judgement."""
        action_mapping = {
            'freeze': (ActionType.FREEZE_SYSTEM, ActionPriority.IMMEDIATE),
            'alert': (ActionType.ALERT_HUMAN, ActionPriority.HIGH),
            'heal': (ActionType.TRIGGER_HEALING, ActionPriority.HIGH),
            'monitor': (ActionType.LOG_OBSERVATION, ActionPriority.MEDIUM),
            'none': (ActionType.DO_NOTHING, ActionPriority.LOW),
        }

        recommended = judgement.recommended_action
        action_type, priority = action_mapping.get(recommended, (ActionType.DO_NOTHING, ActionPriority.LOW))

        # Determine target components
        target_components = []
        if judgement.health.critical_components:
            target_components.extend(judgement.health.critical_components)
        if judgement.health.degraded_components:
            target_components.extend(judgement.health.degraded_components)

        # Build parameters
        parameters = {
            'health_status': judgement.health.status.value,
            'health_score': judgement.health.overall_score,
            'confidence': judgement.confidence.overall_confidence,
            'risk_count': len(judgement.risk_vectors),
            'alert_count': len(judgement.avn_alerts),
        }

        # Check if CI/CD should be triggered
        should_trigger_cicd = self._should_trigger_cicd(sensor_data, interpreted_data, judgement)
        if should_trigger_cicd:
            action_type = ActionType.TRIGGER_CICD
            parameters['cicd_reason'] = should_trigger_cicd

        # Check for learning opportunities
        learning_patterns = [
            p for p in interpreted_data.patterns
            if p.pattern_type == PatternType.LEARNING_OPPORTUNITY
        ]
        if learning_patterns and action_type == ActionType.DO_NOTHING:
            action_type = ActionType.RECOMMEND_LEARNING
            parameters['learning_patterns'] = len(learning_patterns)

        return ActionDecision(
            decision_id=f"DEC-{self._decision_counter:04d}",
            action_type=action_type,
            priority=priority,
            reason=self._generate_reason(action_type, judgement),
            confidence=judgement.confidence.overall_confidence,
            target_components=list(set(target_components)),
            parameters=parameters,
        )

    def _should_trigger_cicd(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> Optional[str]:
        """Determine if CI/CD pipeline should be triggered."""
        if not self.cicd_config.enabled:
            return None

        # Trigger on test failures that might be fixable
        if sensor_data.test_results:
            if sensor_data.test_results.pass_rate < 0.95:
                if sensor_data.test_results.infrastructure_failures > 0:
                    return "infrastructure_test_failures"

        # Trigger on healing completion to verify fix
        if judgement.recommended_action == 'heal':
            return "post_healing_verification"

        # Trigger on significant code quality issues
        code_quality_patterns = [
            p for p in interpreted_data.patterns
            if p.pattern_type == PatternType.CODE_QUALITY_ISSUE
        ]
        if code_quality_patterns and code_quality_patterns[0].frequency > 5:
            return "code_quality_regression"

        return None

    def _generate_reason(self, action_type: ActionType, judgement: JudgementResult) -> str:
        """Generate human-readable reason for action."""
        reasons = {
            ActionType.FREEZE_SYSTEM: f"Critical health status ({judgement.health.status.value}) requires system freeze",
            ActionType.ALERT_HUMAN: f"Health issues detected: {', '.join(judgement.health.critical_components + judgement.health.degraded_components)}" or "System requires attention",
            ActionType.TRIGGER_HEALING: f"Attempting automatic recovery for: {', '.join(judgement.health.degraded_components)}" or "Self-healing triggered",
            ActionType.TRIGGER_CICD: "Running CI/CD pipeline to verify system state",
            ActionType.RECOMMEND_LEARNING: "Learning opportunities detected from recent patterns",
            ActionType.LOG_OBSERVATION: "Monitoring system state",
            ActionType.DO_NOTHING: "System is healthy, no action required",
            ActionType.ESCALATE: "Issue requires escalation to higher authority",
        }
        return reasons.get(action_type, "Action required")

    def _execute_actions(
        self,
        decision: ActionDecision,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> List[ActionResult]:
        """Execute actions based on decision."""
        results = []

        if decision.action_type == ActionType.FREEZE_SYSTEM:
            results.append(self._execute_freeze(decision))

        elif decision.action_type == ActionType.ALERT_HUMAN:
            results.append(self._execute_alert(decision, judgement))

        elif decision.action_type == ActionType.TRIGGER_HEALING:
            results.extend(self._execute_healing(decision, sensor_data, judgement))

        elif decision.action_type == ActionType.TRIGGER_CICD:
            results.append(self._execute_cicd(decision))

        elif decision.action_type == ActionType.RECOMMEND_LEARNING:
            results.append(self._execute_learning_capture(decision, interpreted_data))

        elif decision.action_type == ActionType.LOG_OBSERVATION:
            results.append(self._execute_log_observation(decision, judgement))

        elif decision.action_type == ActionType.DO_NOTHING:
            results.append(self._execute_noop(decision))

        return results

    def _execute_freeze(self, decision: ActionDecision) -> ActionResult:
        """Execute system freeze action."""
        self._action_counter += 1
        start_time = datetime.utcnow()

        if not self.enable_freeze:
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.SKIPPED,
                message="Freeze disabled by configuration",
            )

        try:
            # Create freeze marker file
            freeze_file = self.log_dir / "SYSTEM_FROZEN"
            with open(freeze_file, 'w') as f:
                json.dump({
                    'frozen_at': datetime.utcnow().isoformat(),
                    'decision_id': decision.decision_id,
                    'reason': decision.reason,
                    'components': decision.target_components,
                }, f, indent=2)

            logger.critical(f"SYSTEM FROZEN: {decision.reason}")

            end_time = datetime.utcnow()
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.COMPLETED,
                message="System freeze marker created",
                details={'freeze_file': str(freeze_file)},
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Failed to freeze system: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.FAILED,
                message=f"Freeze failed: {str(e)}",
            )

    def _execute_alert(self, decision: ActionDecision, judgement: JudgementResult) -> ActionResult:
        """Execute alert action."""
        self._action_counter += 1
        start_time = datetime.utcnow()

        try:
            # Build alert payload
            alert_payload = {
                'alert_id': f"ALERT-{self._action_counter:04d}",
                'timestamp': datetime.utcnow().isoformat(),
                'severity': 'critical' if judgement.health.status == HealthStatus.CRITICAL else 'warning',
                'decision_id': decision.decision_id,
                'reason': decision.reason,
                'health_status': judgement.health.status.value,
                'health_score': judgement.health.overall_score,
                'critical_components': judgement.health.critical_components,
                'degraded_components': judgement.health.degraded_components,
                'avn_alerts': len(judgement.avn_alerts),
                'risk_vectors': len(judgement.risk_vectors),
            }

            # Write to alert file
            alert_file = self.log_dir / self.alert_config.alert_file
            with open(alert_file, 'a') as f:
                f.write(json.dumps(alert_payload) + '\n')

            logger.warning(f"ALERT: {decision.reason}")

            # TODO: Send to webhook if configured
            # TODO: Send email if configured
            # TODO: Post to Slack if configured

            end_time = datetime.utcnow()
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.ALERT_HUMAN,
                status=ActionStatus.COMPLETED,
                message="Alert logged successfully",
                details=alert_payload,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.ALERT_HUMAN,
                status=ActionStatus.FAILED,
                message=f"Alert failed: {str(e)}",
            )

    def _execute_healing(
        self,
        decision: ActionDecision,
        sensor_data: SensorData,
        judgement: JudgementResult
    ) -> List[ActionResult]:
        """Execute self-healing actions."""
        results = []

        if not self.enable_healing:
            self._action_counter += 1
            return [ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_HEALING,
                status=ActionStatus.SKIPPED,
                message="Healing disabled by configuration",
            )]

        # Determine which healing actions to run
        healing_actions = []

        # Database issues
        if sensor_data.metrics and not sensor_data.metrics.database_health:
            healing_actions.append(self.HEALING_ACTIONS['reconnect_database'])

        # Vector DB issues
        if sensor_data.metrics and not sensor_data.metrics.vector_db_health:
            healing_actions.append(self.HEALING_ACTIONS['reset_vector_db'])

        # Memory issues
        if sensor_data.metrics and sensor_data.metrics.memory_percent > 85:
            healing_actions.append(self.HEALING_ACTIONS['run_garbage_collection'])

        # WHOLE-SYSTEM HEALING

        # Code quality issues (security vulnerabilities, syntax errors, etc.)
        if sensor_data.code_quality and sensor_data.code_quality.critical_issues > 0:
            healing_actions.append(self.HEALING_ACTIONS['fix_code_issues'])
        
        # Static analysis issues (syntax errors, import errors, missing files)
        if sensor_data.static_analysis:
            static_issues = sensor_data.static_analysis
            critical_count = getattr(static_issues, 'critical_issues', 0)
            high_count = getattr(static_issues, 'high_issues', 0)
            if critical_count > 0 or high_count > 0:
                healing_actions.append(HealingAction(
                    healing_id=f"FIX-CODE-{self._action_counter}",
                    name="Fix Code Issues",
                    description=f"Fix {critical_count} critical and {high_count} high severity code issues",
                    target_component="codebase",
                    function="fix_code_issues",
                    parameters={'fix_warnings': False}  # Only fix critical/high for now
                ))

        # Infrastructure issues - unhealthy containers
        if sensor_data.infrastructure and sensor_data.infrastructure.containers_unhealthy > 0:
            healing_actions.append(self.HEALING_ACTIONS['restart_container'])

        # Disk space issues
        if sensor_data.infrastructure and sensor_data.infrastructure.disk_space_critical:
            healing_actions.append(self.HEALING_ACTIONS['clear_disk_space'])

        # Embedding service issues
        if sensor_data.metrics and not sensor_data.metrics.embedding_health:
            healing_actions.append(self.HEALING_ACTIONS['reload_embedding_model'])

        # Execute each healing action
        for healing in healing_actions:
            self._action_counter += 1
            start_time = datetime.utcnow()

            try:
                if healing.function and healing.function in self._healing_functions:
                    func = self._healing_functions[healing.function]
                    success = func(healing.parameters)

                    end_time = datetime.utcnow()
                    results.append(ActionResult(
                        action_id=f"ACT-{self._action_counter:04d}",
                        action_type=ActionType.TRIGGER_HEALING,
                        status=ActionStatus.COMPLETED if success else ActionStatus.FAILED,
                        message=f"Healing '{healing.name}' {'completed' if success else 'failed'}",
                        details={
                            'healing_id': healing.healing_id,
                            'target': healing.target_component,
                        },
                        duration_ms=(end_time - start_time).total_seconds() * 1000,
                    ))
                else:
                    results.append(ActionResult(
                        action_id=f"ACT-{self._action_counter:04d}",
                        action_type=ActionType.TRIGGER_HEALING,
                        status=ActionStatus.SKIPPED,
                        message=f"Healing function '{healing.function}' not registered",
                    ))
            except Exception as e:
                logger.error(f"Healing action failed: {e}")
                results.append(ActionResult(
                    action_id=f"ACT-{self._action_counter:04d}",
                    action_type=ActionType.TRIGGER_HEALING,
                    status=ActionStatus.FAILED,
                    message=f"Healing failed: {str(e)}",
                ))

        if not results:
            self._action_counter += 1
            results.append(ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_HEALING,
                status=ActionStatus.COMPLETED,
                message="No specific healing actions required",
            ))

        return results

    def _execute_cicd(self, decision: ActionDecision) -> ActionResult:
        """Execute CI/CD pipeline trigger."""
        self._action_counter += 1
        start_time = datetime.utcnow()

        try:
            cicd_reason = decision.parameters.get('cicd_reason', 'diagnostic_trigger')

            # Log CI/CD trigger
            cicd_log = {
                'trigger_id': f"CICD-{self._action_counter:04d}",
                'timestamp': datetime.utcnow().isoformat(),
                'reason': cicd_reason,
                'decision_id': decision.decision_id,
            }

            cicd_file = self.log_dir / "cicd_triggers.jsonl"
            with open(cicd_file, 'a') as f:
                f.write(json.dumps(cicd_log) + '\n')

            # Execute CI/CD command if configured
            if self.cicd_config.pipeline_command:
                result = subprocess.run(
                    self.cicd_config.pipeline_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                success = result.returncode == 0
            else:
                # Dry run - just log the trigger
                success = True

            end_time = datetime.utcnow()
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_CICD,
                status=ActionStatus.COMPLETED if success else ActionStatus.FAILED,
                message=f"CI/CD triggered: {cicd_reason}",
                details=cicd_log,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"CI/CD trigger failed: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_CICD,
                status=ActionStatus.FAILED,
                message=f"CI/CD trigger failed: {str(e)}",
            )

    def _execute_learning_capture(
        self,
        decision: ActionDecision,
        interpreted_data: InterpretedData
    ) -> ActionResult:
        """Execute learning capture action."""
        self._action_counter += 1
        start_time = datetime.utcnow()

        try:
            # Extract learning patterns
            learning_patterns = [
                p for p in interpreted_data.patterns
                if p.pattern_type == PatternType.LEARNING_OPPORTUNITY
            ]

            learning_data = {
                'capture_id': f"LEARN-{self._action_counter:04d}",
                'timestamp': datetime.utcnow().isoformat(),
                'decision_id': decision.decision_id,
                'patterns': [
                    {
                        'description': p.description,
                        'confidence': p.confidence,
                        'affected_components': p.affected_components,
                        'evidence': p.evidence,
                    }
                    for p in learning_patterns
                ],
            }

            # Write to learning log
            learning_file = self.log_dir / "learning_captures.jsonl"
            with open(learning_file, 'a') as f:
                f.write(json.dumps(learning_data) + '\n')

            logger.info(f"Learning captured: {len(learning_patterns)} patterns")

            end_time = datetime.utcnow()
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.RECOMMEND_LEARNING,
                status=ActionStatus.COMPLETED,
                message=f"Captured {len(learning_patterns)} learning patterns",
                details=learning_data,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Learning capture failed: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.RECOMMEND_LEARNING,
                status=ActionStatus.FAILED,
                message=f"Learning capture failed: {str(e)}",
            )

    def _execute_log_observation(
        self,
        decision: ActionDecision,
        judgement: JudgementResult
    ) -> ActionResult:
        """Execute observation logging action."""
        self._action_counter += 1
        start_time = datetime.utcnow()

        try:
            observation = {
                'observation_id': f"OBS-{self._action_counter:04d}",
                'timestamp': datetime.utcnow().isoformat(),
                'decision_id': decision.decision_id,
                'health_score': judgement.health.overall_score,
                'health_status': judgement.health.status.value,
                'confidence': judgement.confidence.overall_confidence,
                'drift_detected': any(
                    d.drift_magnitude > 0.1
                    for d in judgement.drift_analysis
                ),
            }

            # Write to observation log
            obs_file = self.log_dir / "observations.jsonl"
            with open(obs_file, 'a') as f:
                f.write(json.dumps(observation) + '\n')

            end_time = datetime.utcnow()
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.LOG_OBSERVATION,
                status=ActionStatus.COMPLETED,
                message="Observation logged",
                details=observation,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Observation logging failed: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.LOG_OBSERVATION,
                status=ActionStatus.FAILED,
                message=f"Observation logging failed: {str(e)}",
            )

    def _execute_noop(self, decision: ActionDecision) -> ActionResult:
        """Execute no-operation (healthy state)."""
        self._action_counter += 1
        return ActionResult(
            action_id=f"ACT-{self._action_counter:04d}",
            action_type=ActionType.DO_NOTHING,
            status=ActionStatus.COMPLETED,
            message="System healthy, no action required",
        )

    def _log_decision(self, decision: ActionDecision):
        """Log decision to decision log."""
        try:
            decision_log = {
                'decision_id': decision.decision_id,
                'timestamp': decision.decision_timestamp.isoformat(),
                'action_type': decision.action_type.value,
                'priority': decision.priority.value,
                'reason': decision.reason,
                'confidence': decision.confidence,
                'target_components': decision.target_components,
                'results': [
                    {
                        'action_id': r.action_id,
                        'status': r.status.value,
                        'message': r.message,
                    }
                    for r in decision.results
                ],
            }

            decision_file = self.log_dir / "action_decisions.jsonl"
            with open(decision_file, 'a') as f:
                f.write(json.dumps(decision_log) + '\n')

        except Exception as e:
            logger.error(f"Failed to log decision: {e}")

    # Healing function implementations
    def _heal_clear_cache(self, params: Dict) -> bool:
        """Clear application cache."""
        try:
            # Placeholder - implement actual cache clearing
            logger.info("Clearing application cache")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

    def _heal_reset_database(self, params: Dict) -> bool:
        """Reset database connection."""
        try:
            from database.connection import DatabaseConnection
            DatabaseConnection.close()
            logger.info("Database connection reset")
            return True
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False

    def _heal_reset_vector_db(self, params: Dict) -> bool:
        """Reset vector database client."""
        try:
            # Placeholder - implement actual vector DB reset
            logger.info("Vector DB client reset")
            return True
        except Exception as e:
            logger.error(f"Vector DB reset failed: {e}")
            return False

    def _heal_garbage_collection(self, params: Dict) -> bool:
        """Force garbage collection."""
        try:
            import gc
            gc.collect()
            logger.info("Garbage collection completed")
            return True
        except Exception as e:
            logger.error(f"GC failed: {e}")
            return False

    # ==================== WHOLE-SYSTEM HEALING FUNCTIONS ====================

    def _heal_code_issues(self, params: Dict) -> bool:
        """
        Fix detected code issues using the HealingExecutor and AutomaticBugFixer.

        This connects to the CODE_FIX action in the healing layer to automatically
        apply fixes for:
        - Syntax errors (indentation, missing colons, unclosed parentheses)
        - Import errors (comment out broken imports)
        - Missing files (comment out imports)
        - Code quality issues (bare except, mutable defaults, print vs logger, 'is' vs '==')
        - Security vulnerabilities (command injection, path traversal, etc.)
        - Warnings (if fix_warnings=True)
        """
        try:
            healer = get_healing_executor()

            # Get parameters
            fix_warnings = params.get('fix_warnings', False)
            issue_type = params.get('issue_type', 'auto')
            file_path = params.get('file_path')

            result = healer.execute(
                HealingActionType.CODE_FIX,
                {
                    'issue_type': issue_type,
                    'file_path': file_path,
                    'fix_type': 'auto',  # Auto-detect and fix
                    'fix_warnings': fix_warnings,  # Also fix warnings if requested
                }
            )

            if result.success:
                logger.info(f"Code issues healed: {result.message}")
                return True
            else:
                logger.warning(f"Code healing partial: {result.message}")
                return False

        except Exception as e:
            logger.error(f"Code issue healing failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _heal_clear_disk_space(self, params: Dict) -> bool:
        """Clear temporary files and logs to free up disk space."""
        try:
            import shutil

            # Clear Python cache files
            backend_dir = Path(__file__).parent.parent
            cleared_bytes = 0

            # Clear __pycache__ directories
            for pycache in backend_dir.rglob('__pycache__'):
                if pycache.is_dir():
                    try:
                        size = sum(f.stat().st_size for f in pycache.rglob('*') if f.is_file())
                        shutil.rmtree(pycache)
                        cleared_bytes += size
                    except Exception:
                        pass

            # Clear .pyc files
            for pyc in backend_dir.rglob('*.pyc'):
                try:
                    size = pyc.stat().st_size
                    pyc.unlink()
                    cleared_bytes += size
                except Exception:
                    pass

            # Clear old log files (older than 7 days)
            log_dir = backend_dir / 'logs'
            if log_dir.exists():
                import time
                cutoff = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
                for log_file in log_dir.glob('*.log*'):
                    try:
                        if log_file.stat().st_mtime < cutoff:
                            size = log_file.stat().st_size
                            log_file.unlink()
                            cleared_bytes += size
                    except Exception:
                        pass

            logger.info(f"Disk space cleared: {cleared_bytes / (1024*1024):.2f} MB")
            return True

        except Exception as e:
            logger.error(f"Disk space clearing failed: {e}")
            return False

    def _heal_reload_embedding(self, params: Dict) -> bool:
        """Reload embedding model to fix model issues."""
        try:
            healer = get_healing_executor()

            result = healer.execute(HealingActionType.EMBEDDING_MODEL_RELOAD, {})

            if result.success:
                logger.info("Embedding model reloaded successfully")
                return True
            else:
                logger.warning(f"Embedding reload issue: {result.message}")
                return False

        except Exception as e:
            logger.error(f"Embedding reload failed: {e}")
            return False

    def to_dict(self, decision: ActionDecision) -> Dict[str, Any]:
        """Convert action decision to dictionary for serialization."""
        return {
            'decision_id': decision.decision_id,
            'decision_timestamp': decision.decision_timestamp.isoformat(),
            'action_type': decision.action_type.value,
            'priority': decision.priority.value,
            'reason': decision.reason,
            'confidence': decision.confidence,
            'target_components': decision.target_components,
            'parameters': decision.parameters,
            'results': [
                {
                    'action_id': r.action_id,
                    'action_type': r.action_type.value,
                    'status': r.status.value,
                    'message': r.message,
                    'duration_ms': r.duration_ms,
                    'timestamp': r.timestamp.isoformat(),
                }
                for r in decision.results
            ],
        }
