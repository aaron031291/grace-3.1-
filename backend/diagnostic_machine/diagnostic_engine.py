"""
Diagnostic Engine - Main Orchestrator for 4-Layer Diagnostic Machine

Coordinates:
- Layer 1: Sensors (data collection)
- Layer 2: Interpreters (pattern analysis)
- Layer 3: Judgement (decision making)
- Layer 4: Action Routing (response execution)

Features:
- 60-second heartbeat for continuous monitoring
- Event-driven sensor triggering
- CI/CD pipeline integration
- Forensic analysis and AVN/AVM
"""

import os
import json
import logging
import threading
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .sensors import SensorLayer, SensorData, CodeQualityData
from .interpreters import InterpreterLayer, InterpretedData
from .judgement import JudgementLayer, JudgementResult, HealthStatus
from .action_router import ActionRouter, ActionDecision, ActionType, CICDConfig, AlertConfig
from .healing import HealingExecutor, HealingActionType, get_healing_executor

logger = logging.getLogger(__name__)


class EngineState(str, Enum):
    """State of the diagnostic engine."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class TriggerSource(str, Enum):
    """Source of diagnostic trigger."""
    HEARTBEAT = "heartbeat"  # 60-second interval
    SENSOR_FLAG = "sensor_flag"  # Sensor detected issue
    CICD_PIPELINE = "cicd_pipeline"  # CI/CD triggered
    MANUAL = "manual"  # User-initiated
    API = "api"  # API call
    WEBHOOK = "webhook"  # External webhook
    PROACTIVE_SCAN = "proactive_scan"  # FIX: Proactive code quality scan
    FILE_CHANGE = "file_change"  # FIX: File watcher detected change


@dataclass
class DiagnosticCycle:
    """Result of a complete diagnostic cycle."""
    cycle_id: str
    trigger_source: TriggerSource
    sensor_data: Optional[SensorData] = None
    interpreted_data: Optional[InterpretedData] = None
    judgement: Optional[JudgementResult] = None
    action_decision: Optional[ActionDecision] = None
    cycle_start: datetime = field(default_factory=datetime.utcnow)
    cycle_end: Optional[datetime] = None
    total_duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class EngineStats:
    """Statistics for the diagnostic engine."""
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    total_alerts: int = 0
    total_healing_actions: int = 0
    total_freeze_events: int = 0
    average_cycle_duration_ms: float = 0.0
    last_cycle_timestamp: Optional[datetime] = None
    uptime_seconds: float = 0.0


class DiagnosticEngine:
    """
    Main orchestrator for the 4-Layer Diagnostic Machine.

    Runs a continuous 60-second heartbeat to monitor system health,
    with event-driven triggers for immediate response to issues.

    Architecture:
        Sensors → Interpreters → Judgement → Action Router

    Features:
        - 60-second heartbeat monitoring
        - Event-driven sensor triggers
        - CI/CD pipeline integration
        - AVN (Anomaly Violation Notification)
        - AVM (Anomaly Violation Monitor)
        - Forensic analysis for root cause
    """

    DEFAULT_HEARTBEAT_INTERVAL = 60  # seconds

    def __init__(
        self,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        enable_heartbeat: bool = True,
        enable_cicd: bool = True,
        enable_healing: bool = True,
        enable_freeze: bool = True,
        enable_forensics: bool = True,
        dry_run: bool = False,
        log_dir: str = None,
        diagnostic_report_path: str = None,
    ):
        """Initialize the diagnostic engine."""
        self.heartbeat_interval = heartbeat_interval
        self.enable_heartbeat = enable_heartbeat
        self.dry_run = dry_run
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs"

        # Initialize all layers
        self.sensor_layer = SensorLayer(
            diagnostic_report_path=diagnostic_report_path,
            decision_log_dir=str(self.log_dir / "decisions"),
        )
        self.interpreter_layer = InterpreterLayer()
        self.judgement_layer = JudgementLayer(
            enable_forensics=enable_forensics,
        )
        self.action_router = ActionRouter(
            alert_config=AlertConfig(alert_file="diagnostic_alerts.jsonl"),
            cicd_config=CICDConfig(enabled=enable_cicd),
            log_dir=str(self.log_dir),
            enable_healing=enable_healing,
            enable_freeze=enable_freeze,
            dry_run=dry_run,
        )

        # Engine state
        self._state = EngineState.STOPPED
        self._cycle_counter = 0
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stats = EngineStats()
        self._start_time: Optional[datetime] = None

        # Event callbacks
        self._on_cycle_complete: List[Callable] = []
        self._on_alert: List[Callable] = []
        self._on_heal: List[Callable] = []
        self._on_freeze: List[Callable] = []

        # Recent cycles for analysis
        self._recent_cycles: List[DiagnosticCycle] = []
        self._max_recent_cycles = 100

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"DiagnosticEngine initialized (heartbeat: {heartbeat_interval}s)")

    @property
    def state(self) -> EngineState:
        """Get current engine state."""
        return self._state

    @property
    def stats(self) -> EngineStats:
        """Get engine statistics."""
        if self._start_time:
            self._stats.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
        return self._stats

    def start(self) -> bool:
        """Start the diagnostic engine with heartbeat."""
        if self._state == EngineState.RUNNING:
            logger.warning("Engine already running")
            return True

        try:
            self._state = EngineState.STARTING
            self._start_time = datetime.utcnow()
            self._stop_event.clear()

            logger.info("Starting DiagnosticEngine...")

            # Run initial diagnostic
            self.run_cycle(TriggerSource.MANUAL)

            # Start heartbeat thread if enabled
            if self.enable_heartbeat:
                self._heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop,
                    name="DiagnosticHeartbeat",
                    daemon=True
                )
                self._heartbeat_thread.start()
                logger.info(f"Heartbeat started ({self.heartbeat_interval}s interval)")

            self._state = EngineState.RUNNING
            logger.info("DiagnosticEngine started successfully")
            return True

        except Exception as e:
            self._state = EngineState.ERROR
            logger.error(f"Failed to start DiagnosticEngine: {e}")
            return False

    def stop(self) -> bool:
        """Stop the diagnostic engine."""
        if self._state == EngineState.STOPPED:
            logger.warning("Engine already stopped")
            return True

        try:
            logger.info("Stopping DiagnosticEngine...")
            self._stop_event.set()

            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=5)

            # FIX: Also stop file watcher if running
            self.stop_file_watcher()

            self._state = EngineState.STOPPED
            self._save_stats()
            logger.info("DiagnosticEngine stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping DiagnosticEngine: {e}")
            return False

    def pause(self):
        """Pause the heartbeat (still allows manual triggers)."""
        if self._state == EngineState.RUNNING:
            self._state = EngineState.PAUSED
            logger.info("DiagnosticEngine paused")

    def resume(self):
        """Resume the heartbeat."""
        if self._state == EngineState.PAUSED:
            self._state = EngineState.RUNNING
            logger.info("DiagnosticEngine resumed")

    def run_cycle(self, trigger_source: TriggerSource = TriggerSource.MANUAL) -> DiagnosticCycle:
        """Run a complete diagnostic cycle."""
        self._cycle_counter += 1
        cycle = DiagnosticCycle(
            cycle_id=f"CYCLE-{self._cycle_counter:06d}",
            trigger_source=trigger_source,
        )

        try:
            cycle_start = datetime.utcnow()

            # Layer 1: Collect sensor data
            logger.debug("Layer 1: Collecting sensor data...")
            cycle.sensor_data = self.sensor_layer.collect_all()

            # Layer 2: Interpret patterns
            logger.debug("Layer 2: Interpreting patterns...")
            cycle.interpreted_data = self.interpreter_layer.interpret(cycle.sensor_data)

            # Layer 3: Make judgement
            logger.debug("Layer 3: Making judgement...")
            cycle.judgement = self.judgement_layer.judge(
                cycle.sensor_data,
                cycle.interpreted_data
            )

            # Layer 4: Route actions
            logger.debug("Layer 4: Routing actions...")
            cycle.action_decision = self.action_router.route(
                cycle.sensor_data,
                cycle.interpreted_data,
                cycle.judgement
            )

            cycle_end = datetime.utcnow()
            cycle.cycle_end = cycle_end
            cycle.total_duration_ms = (cycle_end - cycle_start).total_seconds() * 1000
            cycle.success = True

            # Update stats
            self._stats.total_cycles += 1
            self._stats.successful_cycles += 1
            self._stats.last_cycle_timestamp = cycle_end
            self._update_average_duration(cycle.total_duration_ms)

            # Track specific actions
            if cycle.action_decision:
                if cycle.action_decision.action_type == ActionType.ALERT_HUMAN:
                    self._stats.total_alerts += 1
                    self._fire_alert_callbacks(cycle)
                elif cycle.action_decision.action_type == ActionType.TRIGGER_HEALING:
                    self._stats.total_healing_actions += 1
                    self._fire_heal_callbacks(cycle)
                elif cycle.action_decision.action_type == ActionType.FREEZE_SYSTEM:
                    self._stats.total_freeze_events += 1
                    self._fire_freeze_callbacks(cycle)

            # Store recent cycle
            self._recent_cycles.append(cycle)
            if len(self._recent_cycles) > self._max_recent_cycles:
                self._recent_cycles.pop(0)

            # Log cycle result
            self._log_cycle(cycle)

            # Fire completion callbacks
            self._fire_cycle_callbacks(cycle)

            logger.info(
                f"Cycle {cycle.cycle_id} completed: "
                f"health={cycle.judgement.health.status.value}, "
                f"action={cycle.action_decision.action_type.value}, "
                f"duration={cycle.total_duration_ms:.1f}ms"
            )

        except Exception as e:
            cycle.success = False
            cycle.error_message = str(e)
            cycle.cycle_end = datetime.utcnow()
            self._stats.total_cycles += 1
            self._stats.failed_cycles += 1
            logger.error(f"Cycle {cycle.cycle_id} failed: {e}")

        return cycle

    def trigger_from_sensor(self, sensor_type: str, reason: str = None) -> DiagnosticCycle:
        """Trigger diagnostic cycle from sensor flag."""
        logger.info(f"Sensor trigger: {sensor_type} - {reason or 'no reason provided'}")
        return self.run_cycle(TriggerSource.SENSOR_FLAG)

    def trigger_from_cicd(self, pipeline_id: str = None) -> DiagnosticCycle:
        """Trigger diagnostic cycle from CI/CD pipeline."""
        logger.info(f"CI/CD trigger: {pipeline_id or 'unknown pipeline'}")
        return self.run_cycle(TriggerSource.CICD_PIPELINE)

    def trigger_from_webhook(self, payload: Dict = None) -> DiagnosticCycle:
        """Trigger diagnostic cycle from external webhook."""
        logger.info(f"Webhook trigger: {payload or {}}")
        return self.run_cycle(TriggerSource.WEBHOOK)

    # ==================== PROACTIVE SCANNING CAPABILITIES ====================

    def run_proactive_scan(self, auto_heal: bool = False) -> Dict[str, Any]:
        """
        Run a proactive code quality scan.

        FIX: This method performs comprehensive static analysis to detect:
        - Security vulnerabilities
        - Configuration issues
        - Database schema problems
        - Dependency issues

        Parameters:
            auto_heal: If True, automatically apply fixes for detected issues

        Returns:
            Dictionary with scan results and any healing actions taken
        """
        logger.info("Running proactive code quality scan...")
        scan_start = datetime.utcnow()

        # Run the code quality sensor directly
        code_quality = self.sensor_layer._collect_code_quality()

        if not code_quality:
            return {
                'success': False,
                'error': 'Code quality sensor failed',
                'timestamp': scan_start.isoformat(),
            }

        result = {
            'success': True,
            'timestamp': scan_start.isoformat(),
            'scan_duration_ms': code_quality.scan_duration_ms,
            'files_scanned': code_quality.files_scanned,
            'total_issues': code_quality.total_issues,
            'critical_issues': code_quality.critical_issues,
            'high_issues': code_quality.high_issues,
            'medium_issues': code_quality.medium_issues,
            'low_issues': code_quality.low_issues,
            'security_vulnerabilities': len(code_quality.security_vulnerabilities),
            'configuration_issues': len(code_quality.configuration_issues),
            'database_issues': len(code_quality.database_issues),
            'dependency_issues': len(code_quality.dependency_issues),
            'healing_actions': [],
        }

        # Auto-heal if requested and issues found
        if auto_heal and code_quality.critical_issues > 0:
            result['healing_actions'] = self._auto_heal_code_issues(code_quality)

        # Also trigger a full diagnostic cycle to update system health
        cycle = self.run_cycle(TriggerSource.PROACTIVE_SCAN)
        result['diagnostic_cycle_id'] = cycle.cycle_id

        logger.info(
            f"Proactive scan complete: {code_quality.total_issues} issues found "
            f"({code_quality.critical_issues} critical)"
        )

        return result

    def _auto_heal_code_issues(self, code_quality: CodeQualityData) -> List[Dict]:
        """
        Automatically apply fixes for detected code issues.

        FIX: Uses the healing system to apply safe, reversible fixes.
        Only applies fixes for issues that have well-defined remediation patterns.
        """
        healing_results = []
        healer = get_healing_executor()

        # Focus on critical security issues first
        for issue in code_quality.security_vulnerabilities:
            if issue.severity in ('critical', 'high'):
                try:
                    heal_result = healer.execute(
                        HealingActionType.CODE_FIX,
                        {
                            'issue_type': issue.issue_type,
                            'file_path': issue.file_path,
                            'line_number': issue.line_number,
                        }
                    )

                    healing_results.append({
                        'issue_type': issue.issue_type,
                        'file_path': issue.file_path,
                        'line_number': issue.line_number,
                        'success': heal_result.success,
                        'message': heal_result.message,
                        'rollback_available': heal_result.rollback_available,
                    })

                    if heal_result.success:
                        logger.info(f"Auto-healed: {issue.issue_type} in {issue.file_path}")
                    else:
                        logger.warning(f"Auto-heal failed: {issue.issue_type} - {heal_result.message}")

                except Exception as e:
                    logger.error(f"Auto-heal error for {issue.issue_type}: {e}")
                    healing_results.append({
                        'issue_type': issue.issue_type,
                        'file_path': issue.file_path,
                        'success': False,
                        'message': str(e),
                    })

        return healing_results

    def start_file_watcher(self, watch_paths: List[str] = None, scan_interval: int = 30):
        """
        Start watching for file changes and trigger scans.

        FIX: Provides continuous monitoring of the codebase for changes.
        When files change, triggers a proactive scan to detect new issues.

        Parameters:
            watch_paths: List of paths to watch (defaults to backend directory)
            scan_interval: Seconds between change checks
        """
        if not hasattr(self, '_file_watcher_thread') or self._file_watcher_thread is None:
            self._file_watcher_stop = threading.Event()
            self._file_watcher_thread = threading.Thread(
                target=self._file_watcher_loop,
                args=(watch_paths, scan_interval),
                name="CodeQualityWatcher",
                daemon=True
            )
            self._file_watcher_thread.start()
            logger.info(f"File watcher started (interval: {scan_interval}s)")

    def stop_file_watcher(self):
        """Stop the file watcher."""
        if hasattr(self, '_file_watcher_stop'):
            self._file_watcher_stop.set()
            if hasattr(self, '_file_watcher_thread') and self._file_watcher_thread:
                self._file_watcher_thread.join(timeout=5)
                self._file_watcher_thread = None
            logger.info("File watcher stopped")

    def _file_watcher_loop(self, watch_paths: List[str], scan_interval: int):
        """Background loop to watch for file changes."""
        backend_dir = Path(__file__).parent.parent
        paths_to_watch = watch_paths or [str(backend_dir)]
        file_mtimes: Dict[str, float] = {}

        # Initial scan to establish baseline
        for path in paths_to_watch:
            for py_file in Path(path).rglob("*.py"):
                if '__pycache__' not in str(py_file):
                    file_mtimes[str(py_file)] = py_file.stat().st_mtime

        logger.info(f"File watcher monitoring {len(file_mtimes)} Python files")

        while not self._file_watcher_stop.is_set():
            try:
                if self._file_watcher_stop.wait(timeout=scan_interval):
                    break

                # Check for changes
                changes_detected = False
                for path in paths_to_watch:
                    for py_file in Path(path).rglob("*.py"):
                        if '__pycache__' not in str(py_file):
                            file_path = str(py_file)
                            current_mtime = py_file.stat().st_mtime

                            if file_path not in file_mtimes:
                                # New file
                                file_mtimes[file_path] = current_mtime
                                changes_detected = True
                                logger.debug(f"New file detected: {file_path}")
                            elif file_mtimes[file_path] < current_mtime:
                                # Modified file
                                file_mtimes[file_path] = current_mtime
                                changes_detected = True
                                logger.debug(f"File modified: {file_path}")

                if changes_detected:
                    logger.info("File changes detected, triggering proactive scan...")
                    self.run_cycle(TriggerSource.FILE_CHANGE)

            except Exception as e:
                logger.error(f"File watcher error: {e}")

        logger.info("File watcher loop stopped")

    def get_code_quality_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive code quality report.

        FIX: Provides detailed insights into codebase health for proactive maintenance.
        """
        code_quality = self.sensor_layer._collect_code_quality()

        if not code_quality:
            return {'error': 'Code quality sensor not available'}

        # Group issues by severity and type
        issues_by_type: Dict[str, List] = {}
        issues_by_file: Dict[str, List] = {}

        all_issues = (
            code_quality.security_vulnerabilities +
            code_quality.configuration_issues +
            code_quality.database_issues +
            code_quality.dependency_issues
        )

        for issue in all_issues:
            # Group by type
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append({
                'file': issue.file_path,
                'line': issue.line_number,
                'severity': issue.severity,
                'description': issue.description,
                'cwe': issue.cwe_id,
            })

            # Group by file
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append({
                'type': issue.issue_type,
                'line': issue.line_number,
                'severity': issue.severity,
            })

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'files_scanned': code_quality.files_scanned,
                'total_issues': code_quality.total_issues,
                'critical': code_quality.critical_issues,
                'high': code_quality.high_issues,
                'medium': code_quality.medium_issues,
                'low': code_quality.low_issues,
            },
            'issues_by_type': issues_by_type,
            'issues_by_file': issues_by_file,
            'most_affected_files': sorted(
                issues_by_file.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:10],
            'recommended_priorities': [
                issue_type for issue_type, issues in sorted(
                    issues_by_type.items(),
                    key=lambda x: sum(1 for i in x[1] if i['severity'] in ('critical', 'high')),
                    reverse=True
                )
            ][:5],
        }

    def _heartbeat_loop(self):
        """Main heartbeat loop running at configured interval."""
        logger.info(f"Heartbeat loop started ({self.heartbeat_interval}s)")

        while not self._stop_event.is_set():
            try:
                # Wait for interval or stop event
                if self._stop_event.wait(timeout=self.heartbeat_interval):
                    break

                # Skip if paused
                if self._state == EngineState.PAUSED:
                    continue

                # Run diagnostic cycle
                cycle = self.run_cycle(TriggerSource.HEARTBEAT)

                # Check if we need to increase frequency based on health
                if cycle.judgement and cycle.judgement.health.status == HealthStatus.CRITICAL:
                    # Run more frequently when critical
                    logger.warning("Critical health - running accelerated monitoring")
                    time.sleep(10)  # Wait 10 seconds instead of full interval
                    self.run_cycle(TriggerSource.SENSOR_FLAG)

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

        logger.info("Heartbeat loop stopped")

    def _update_average_duration(self, new_duration: float):
        """Update rolling average cycle duration."""
        if self._stats.average_cycle_duration_ms == 0:
            self._stats.average_cycle_duration_ms = new_duration
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats.average_cycle_duration_ms = (
                alpha * new_duration +
                (1 - alpha) * self._stats.average_cycle_duration_ms
            )

    def _log_cycle(self, cycle: DiagnosticCycle):
        """Log diagnostic cycle to file."""
        try:
            cycle_log = {
                'cycle_id': cycle.cycle_id,
                'trigger_source': cycle.trigger_source.value,
                'cycle_start': cycle.cycle_start.isoformat(),
                'cycle_end': cycle.cycle_end.isoformat() if cycle.cycle_end else None,
                'total_duration_ms': cycle.total_duration_ms,
                'success': cycle.success,
                'error_message': cycle.error_message,
            }

            if cycle.sensor_data:
                cycle_log['sensors_available'] = len(cycle.sensor_data.sensors_available)
                cycle_log['sensors_failed'] = len(cycle.sensor_data.sensors_failed)

            if cycle.interpreted_data:
                cycle_log['patterns_detected'] = len(cycle.interpreted_data.patterns)
                cycle_log['anomalies_detected'] = len(cycle.interpreted_data.anomalies)
                cycle_log['clarity_level'] = cycle.interpreted_data.clarity_level.value

            if cycle.judgement:
                cycle_log['health_status'] = cycle.judgement.health.status.value
                cycle_log['health_score'] = cycle.judgement.health.overall_score
                cycle_log['confidence'] = cycle.judgement.confidence.overall_confidence
                cycle_log['recommended_action'] = cycle.judgement.recommended_action

            if cycle.action_decision:
                cycle_log['action_taken'] = cycle.action_decision.action_type.value
                cycle_log['action_priority'] = cycle.action_decision.priority.value

            cycle_file = self.log_dir / "diagnostic_cycles.jsonl"
            with open(cycle_file, 'a') as f:
                f.write(json.dumps(cycle_log) + '\n')

        except Exception as e:
            logger.error(f"Failed to log cycle: {e}")

    def _save_stats(self):
        """Save engine statistics to file."""
        try:
            stats_dict = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_cycles': self._stats.total_cycles,
                'successful_cycles': self._stats.successful_cycles,
                'failed_cycles': self._stats.failed_cycles,
                'total_alerts': self._stats.total_alerts,
                'total_healing_actions': self._stats.total_healing_actions,
                'total_freeze_events': self._stats.total_freeze_events,
                'average_cycle_duration_ms': self._stats.average_cycle_duration_ms,
                'uptime_seconds': self._stats.uptime_seconds,
            }

            stats_file = self.log_dir / "engine_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats_dict, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    # Callback registration
    def on_cycle_complete(self, callback: Callable):
        """Register callback for cycle completion."""
        self._on_cycle_complete.append(callback)

    def on_alert(self, callback: Callable):
        """Register callback for alert actions."""
        self._on_alert.append(callback)

    def on_heal(self, callback: Callable):
        """Register callback for healing actions."""
        self._on_heal.append(callback)

    def on_freeze(self, callback: Callable):
        """Register callback for freeze actions."""
        self._on_freeze.append(callback)

    def _fire_cycle_callbacks(self, cycle: DiagnosticCycle):
        """Fire cycle completion callbacks."""
        for callback in self._on_cycle_complete:
            try:
                callback(cycle)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _fire_alert_callbacks(self, cycle: DiagnosticCycle):
        """Fire alert callbacks."""
        for callback in self._on_alert:
            try:
                callback(cycle)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def _fire_heal_callbacks(self, cycle: DiagnosticCycle):
        """Fire healing callbacks."""
        for callback in self._on_heal:
            try:
                callback(cycle)
            except Exception as e:
                logger.error(f"Heal callback error: {e}")

    def _fire_freeze_callbacks(self, cycle: DiagnosticCycle):
        """Fire freeze callbacks."""
        for callback in self._on_freeze:
            try:
                callback(cycle)
            except Exception as e:
                logger.error(f"Freeze callback error: {e}")

    def get_recent_cycles(self, limit: int = 10) -> List[DiagnosticCycle]:
        """Get recent diagnostic cycles."""
        return self._recent_cycles[-limit:]

    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary."""
        if not self._recent_cycles:
            return {
                'status': 'unknown',
                'message': 'No diagnostic cycles completed yet',
            }

        latest = self._recent_cycles[-1]
        if not latest.judgement:
            return {
                'status': 'unknown',
                'message': 'Latest cycle has no judgement',
            }

        return {
            'status': latest.judgement.health.status.value,
            'health_score': latest.judgement.health.overall_score,
            'confidence': latest.judgement.confidence.overall_confidence,
            'last_check': latest.cycle_end.isoformat() if latest.cycle_end else None,
            'degraded_components': latest.judgement.health.degraded_components,
            'critical_components': latest.judgement.health.critical_components,
            'avm_level': latest.judgement.avm_status.current_alert_level,
            'recommended_action': latest.judgement.recommended_action,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert engine state to dictionary."""
        return {
            'state': self._state.value,
            'heartbeat_interval': self.heartbeat_interval,
            'stats': {
                'total_cycles': self._stats.total_cycles,
                'successful_cycles': self._stats.successful_cycles,
                'failed_cycles': self._stats.failed_cycles,
                'total_alerts': self._stats.total_alerts,
                'total_healing_actions': self._stats.total_healing_actions,
                'total_freeze_events': self._stats.total_freeze_events,
                'average_cycle_duration_ms': self._stats.average_cycle_duration_ms,
                'uptime_seconds': self._stats.uptime_seconds,
            },
            'health_summary': self.get_health_summary(),
            'recent_cycles_count': len(self._recent_cycles),
        }


# Global engine instance
_engine_instance: Optional[DiagnosticEngine] = None


def get_diagnostic_engine(
    heartbeat_interval: int = 60,
    **kwargs
) -> DiagnosticEngine:
    """Get or create the global diagnostic engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DiagnosticEngine(
            heartbeat_interval=heartbeat_interval,
            **kwargs
        )
    return _engine_instance


def start_diagnostic_engine(**kwargs) -> DiagnosticEngine:
    """Start the global diagnostic engine."""
    engine = get_diagnostic_engine(**kwargs)
    engine.start()
    return engine


def stop_diagnostic_engine():
    """Stop the global diagnostic engine."""
    global _engine_instance
    if _engine_instance:
        _engine_instance.stop()
        _engine_instance = None
