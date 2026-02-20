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

from .sensors import SensorLayer, SensorData
from .interpreters import InterpreterLayer, InterpretedData
from .judgement import JudgementLayer, JudgementResult, HealthStatus
from .action_router import ActionRouter, ActionDecision, ActionType, CICDConfig, AlertConfig

logger = logging.getLogger(__name__)
def _record_time(op, ms):
    try:
        from cognitive.timesense_governance import get_timesense_governance
        get_timesense_governance().record(op, ms, 'diagnostic_engine')
    except Exception:
        pass

def _track_op(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event('diagnostic_engine', desc, **kw)
    except Exception:
        pass



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
