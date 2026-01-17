"""
Real-Time Stability Monitor

Continuously monitors and proves system stability in real-time.
Runs as a background service and automatically generates stability proofs.
"""
import logging
import threading
import time
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from database.session import SessionLocal, initialize_session_factory
from cognitive.deterministic_stability_proof import (
    get_stability_prover,
    DeterministicStabilityProver,
    StabilityLevel,
    StabilityProof
)

logger = logging.getLogger(__name__)


class MonitorStatus(str, Enum):
    """Monitor status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StabilityAlert:
    """Alert when stability changes."""
    alert_id: str
    timestamp: datetime
    previous_level: StabilityLevel
    current_level: StabilityLevel
    previous_confidence: float
    current_confidence: float
    proof_id: str
    message: str
    severity: str  # "info", "warning", "critical"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'previous_level': self.previous_level.value,
            'current_level': self.current_level.value,
            'previous_confidence': self.previous_confidence,
            'current_confidence': self.current_confidence,
            'proof_id': self.proof_id,
            'message': self.message,
            'severity': self.severity
        }


class RealtimeStabilityMonitor:
    """
    Real-time stability monitor that continuously proves system stability.
    
    Runs in background and:
    - Generates stability proofs at regular intervals
    - Detects stability changes
    - Triggers alerts when stability degrades
    - Maintains stability history
    - Provides real-time status
    """
    
    def __init__(
        self,
        check_interval_seconds: int = 60,
        alert_on_degradation: bool = True,
        alert_callbacks: Optional[list[Callable]] = None
    ):
        """
        Initialize real-time stability monitor.
        
        Args:
            check_interval_seconds: How often to check stability (default: 60s)
            alert_on_degradation: If True, alert when stability degrades
            alert_callbacks: List of callback functions for alerts
        """
        self.check_interval = check_interval_seconds
        self.alert_on_degradation = alert_on_degradation
        self.alert_callbacks = alert_callbacks or []
        
        self.status = MonitorStatus.STOPPED
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        self.current_proof: Optional[StabilityProof] = None
        self.previous_proof: Optional[StabilityProof] = None
        self.stability_history: list[StabilityProof] = []
        self.alerts: list[StabilityAlert] = []
        
        self.prover: Optional[DeterministicStabilityProver] = None
        self.session_factory = None
        
        # Statistics
        self.total_checks = 0
        self.stable_count = 0
        self.unstable_count = 0
        self.last_check_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        logger.info(
            f"[STABILITY-MONITOR] Initialized with check interval: {check_interval_seconds}s"
        )
    
    def start(self, session_factory=None):
        """
        Start the real-time stability monitor.
        
        Args:
            session_factory: Optional database session factory
        """
        if self.status == MonitorStatus.RUNNING:
            logger.warning("[STABILITY-MONITOR] Already running")
            return
        
        logger.info("[STABILITY-MONITOR] Starting real-time stability monitoring...")
        
        self.status = MonitorStatus.STARTING
        self.session_factory = session_factory or initialize_session_factory
        self.start_time = datetime.utcnow()
        self.stop_event.clear()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="StabilityMonitor"
        )
        self.monitor_thread.start()
        
        # Wait a moment to ensure thread started
        time.sleep(0.5)
        
        if self.status == MonitorStatus.RUNNING:
            logger.info(
                f"[STABILITY-MONITOR] Started successfully. "
                f"Checking every {self.check_interval} seconds"
            )
        else:
            logger.error("[STABILITY-MONITOR] Failed to start")
            self.status = MonitorStatus.ERROR
    
    def stop(self):
        """Stop the real-time stability monitor."""
        if self.status == MonitorStatus.STOPPED:
            return
        
        logger.info("[STABILITY-MONITOR] Stopping...")
        self.status = MonitorStatus.STOPPED
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("[STABILITY-MONITOR] Stopped")
    
    def pause(self):
        """Pause monitoring (keeps thread alive)."""
        if self.status == MonitorStatus.RUNNING:
            self.status = MonitorStatus.PAUSED
            logger.info("[STABILITY-MONITOR] Paused")
    
    def resume(self):
        """Resume monitoring."""
        if self.status == MonitorStatus.PAUSED:
            self.status = MonitorStatus.RUNNING
            logger.info("[STABILITY-MONITOR] Resumed")
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)."""
        self.status = MonitorStatus.RUNNING
        
        try:
            while not self.stop_event.is_set():
                if self.status == MonitorStatus.RUNNING:
                    try:
                        self._check_stability()
                    except Exception as e:
                        logger.error(
                            f"[STABILITY-MONITOR] Error during stability check: {e}",
                            exc_info=True
                        )
                        self.status = MonitorStatus.ERROR
                        time.sleep(10)  # Wait before retrying
                        self.status = MonitorStatus.RUNNING
                
                # Wait for next check interval
                self.stop_event.wait(self.check_interval)
        
        except Exception as e:
            logger.error(
                f"[STABILITY-MONITOR] Fatal error in monitor loop: {e}",
                exc_info=True
            )
            self.status = MonitorStatus.ERROR
        finally:
            if not self.stop_event.is_set():
                self.status = MonitorStatus.STOPPED
    
    def _check_stability(self):
        """Perform a stability check."""
        session = None
        try:
            # Get database session
            if self.session_factory:
                session = self.session_factory()
            else:
                session = SessionLocal()
            
            # Get or create prover
            if not self.prover:
                self.prover = get_stability_prover(session=session)
            
            # Generate stability proof
            proof = self.prover.prove_stability(include_proof=True)
            
            # Update state
            self.previous_proof = self.current_proof
            self.current_proof = proof
            self.last_check_time = datetime.utcnow()
            self.total_checks += 1
            
            # Update statistics
            if proof.stability_level in [StabilityLevel.STABLE, StabilityLevel.PROVABLY_STABLE]:
                self.stable_count += 1
            else:
                self.unstable_count += 1
            
            # Add to history (keep last 100)
            self.stability_history.append(proof)
            if len(self.stability_history) > 100:
                self.stability_history.pop(0)
            
            # Check for stability changes
            if self.previous_proof and self.alert_on_degradation:
                self._check_stability_change()
            
            # Log status
            logger.info(
                f"[STABILITY-MONITOR] Check #{self.total_checks}: "
                f"{proof.stability_level.value} "
                f"(confidence: {proof.overall_confidence:.2%})"
            )
        
        except Exception as e:
            logger.error(
                f"[STABILITY-MONITOR] Error generating stability proof: {e}",
                exc_info=True
            )
            raise
        
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
    
    def _check_stability_change(self):
        """Check if stability has changed and trigger alerts if needed."""
        if not self.previous_proof or not self.current_proof:
            return
        
        prev_level = self.previous_proof.stability_level
        curr_level = self.current_proof.stability_level
        prev_conf = self.previous_proof.overall_confidence
        curr_conf = self.current_proof.overall_confidence
        
        # Check for degradation
        if self._is_degradation(prev_level, curr_level, prev_conf, curr_conf):
            alert = self._create_alert(
                prev_level, curr_level, prev_conf, curr_conf
            )
            self.alerts.append(alert)
            
            # Keep last 50 alerts
            if len(self.alerts) > 50:
                self.alerts.pop(0)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(
                        f"[STABILITY-MONITOR] Alert callback error: {e}",
                        exc_info=True
                    )
            
            logger.warning(
                f"[STABILITY-MONITOR] Stability degraded: "
                f"{prev_level.value} -> {curr_level.value}"
            )
    
    def _is_degradation(
        self,
        prev_level: StabilityLevel,
        curr_level: StabilityLevel,
        prev_conf: float,
        curr_conf: float
    ) -> bool:
        """Check if stability has degraded."""
        # Define stability hierarchy
        hierarchy = {
            StabilityLevel.PROVABLY_STABLE: 4,
            StabilityLevel.STABLE: 3,
            StabilityLevel.PARTIALLY_STABLE: 2,
            StabilityLevel.UNSTABLE: 1
        }
        
        prev_rank = hierarchy.get(prev_level, 0)
        curr_rank = hierarchy.get(curr_level, 0)
        
        # Degradation if rank decreased
        if curr_rank < prev_rank:
            return True
        
        # Degradation if same level but confidence dropped significantly
        if curr_rank == prev_rank and curr_conf < prev_conf - 0.1:
            return True
        
        return False
    
    def _create_alert(
        self,
        prev_level: StabilityLevel,
        curr_level: StabilityLevel,
        prev_conf: float,
        curr_conf: float
    ) -> StabilityAlert:
        """Create a stability alert."""
        import hashlib
        
        alert_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}_{prev_level}_{curr_level}".encode()
        ).hexdigest()[:16]
        
        # Determine severity
        if curr_level == StabilityLevel.UNSTABLE:
            severity = "critical"
        elif curr_level == StabilityLevel.PARTIALLY_STABLE:
            severity = "warning"
        else:
            severity = "info"
        
        # Create message
        message = (
            f"System stability changed from {prev_level.value} "
            f"({prev_conf:.2%}) to {curr_level.value} ({curr_conf:.2%})"
        )
        
        return StabilityAlert(
            alert_id=alert_id,
            timestamp=datetime.utcnow(),
            previous_level=prev_level,
            current_level=curr_level,
            previous_confidence=prev_conf,
            current_confidence=curr_conf,
            proof_id=self.current_proof.proof_id if self.current_proof else "",
            message=message,
            severity=severity
        )
    
    def get_current_status(self) -> Dict:
        """Get current monitoring status."""
        uptime_seconds = None
        if self.start_time:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'status': self.status.value,
            'check_interval_seconds': self.check_interval,
            'total_checks': self.total_checks,
            'stable_count': self.stable_count,
            'unstable_count': self.unstable_count,
            'uptime_seconds': uptime_seconds,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'current_stability': {
                'level': self.current_proof.stability_level.value if self.current_proof else None,
                'confidence': self.current_proof.overall_confidence if self.current_proof else None,
                'proof_id': self.current_proof.proof_id if self.current_proof else None
            },
            'alerts_count': len(self.alerts),
            'history_count': len(self.stability_history)
        }
    
    def get_recent_proofs(self, limit: int = 10) -> list[StabilityProof]:
        """Get recent stability proofs."""
        return self.stability_history[-limit:] if self.stability_history else []
    
    def get_recent_alerts(self, limit: int = 10) -> list[StabilityAlert]:
        """Get recent stability alerts."""
        return self.alerts[-limit:] if self.alerts else []
    
    def force_check(self) -> Optional[StabilityProof]:
        """
        Force an immediate stability check (synchronous).
        
        Returns:
            StabilityProof or None if check failed
        """
        try:
            session = SessionLocal()
            try:
                if not self.prover:
                    self.prover = get_stability_prover(session=session)
                
                proof = self.prover.prove_stability(include_proof=True)
                
                # Update state
                self.previous_proof = self.current_proof
                self.current_proof = proof
                self.last_check_time = datetime.utcnow()
                self.total_checks += 1
                
                if proof.stability_level in [StabilityLevel.STABLE, StabilityLevel.PROVABLY_STABLE]:
                    self.stable_count += 1
                else:
                    self.unstable_count += 1
                
                self.stability_history.append(proof)
                if len(self.stability_history) > 100:
                    self.stability_history.pop(0)
                
                return proof
            
            finally:
                session.close()
        
        except Exception as e:
            logger.error(
                f"[STABILITY-MONITOR] Force check failed: {e}",
                exc_info=True
            )
            return None


# Global monitor instance
_global_monitor: Optional[RealtimeStabilityMonitor] = None


def get_stability_monitor(
    check_interval_seconds: int = 60,
    auto_start: bool = False
) -> RealtimeStabilityMonitor:
    """
    Get or create global stability monitor instance.
    
    Args:
        check_interval_seconds: Check interval if creating new monitor
        auto_start: If True, automatically start monitoring
        
    Returns:
        RealtimeStabilityMonitor instance
    """
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = RealtimeStabilityMonitor(
            check_interval_seconds=check_interval_seconds
        )
        
        if auto_start:
            _global_monitor.start()
    
    return _global_monitor


def start_stability_monitoring(
    check_interval_seconds: int = 60,
    alert_on_degradation: bool = True
):
    """
    Start global stability monitoring.
    
    Args:
        check_interval_seconds: How often to check stability
        alert_on_degradation: If True, alert on stability degradation
    """
    monitor = get_stability_monitor(
        check_interval_seconds=check_interval_seconds,
        auto_start=False
    )
    monitor.alert_on_degradation = alert_on_degradation
    monitor.start()


def stop_stability_monitoring():
    """Stop global stability monitoring."""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop()
        _global_monitor = None
