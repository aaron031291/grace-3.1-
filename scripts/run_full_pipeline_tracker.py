#!/usr/bin/env python3
"""
Full Pipeline Tracker: Runs self-healing, diagnostics, and tracks every move.

This script:
1. Runs the diagnostic engine
2. Runs the self-healing system
3. Tracks every action with detailed logging
4. Verifies if fixes actually work
5. Identifies errors and issues
6. Generates a comprehensive report
"""

import sys
import json
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"pipeline_tracker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    """Status of tracked actions."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class TrackedAction:
    """Represents a single tracked action."""
    id: str
    timestamp: datetime
    action_type: str
    description: str
    status: ActionStatus = ActionStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    parent_action_id: Optional[str] = None
    child_actions: List[str] = field(default_factory=list)
    verification_result: Optional[Dict[str, Any]] = None

    def to_dict(self):
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['status'] = self.status.value
        return data


@dataclass
class PipelineTracker:
    """Tracks all actions in the pipeline."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    actions: Dict[str, TrackedAction] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    current_action_id: Optional[str] = None

    def start_action(
        self,
        action_type: str,
        description: str,
        input_data: Optional[Dict] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Start tracking a new action."""
        action_id = f"{action_type}_{len(self.actions)}"
        
        action = TrackedAction(
            id=action_id,
            timestamp=datetime.now(),
            action_type=action_type,
            description=description,
            status=ActionStatus.IN_PROGRESS,
            input_data=input_data or {},
            parent_action_id=parent_id
        )
        
        self.actions[action_id] = action
        self.current_action_id = action_id
        
        # Add to parent's child list
        if parent_id and parent_id in self.actions:
            self.actions[parent_id].child_actions.append(action_id)
        
        logger.info(f"[TRACKER] -> {action_type}: {description}")
        return action_id

    def complete_action(self, action_id: str, output_data: Optional[Dict] = None, error: Optional[str] = None):
        """Mark an action as completed or failed."""
        if action_id not in self.actions:
            logger.warning(f"[TRACKER] Action {action_id} not found")
            return
        
        action = self.actions[action_id]
        action.end_time = datetime.now()
        action.duration_ms = (action.end_time - action.timestamp).total_seconds() * 1000
        
        if error:
            action.status = ActionStatus.FAILED
            action.error_message = error
            logger.error(f"[TRACKER] X {action.action_type} FAILED: {error}")
            
            # Track error
            self.errors.append({
                "action_id": action_id,
                "action_type": action.action_type,
                "error": error,
                "timestamp": action.end_time.isoformat(),
                "traceback": traceback.format_exc() if error else None
            })
        else:
            action.status = ActionStatus.COMPLETED
            action.output_data = output_data or {}
            logger.info(f"[TRACKER] OK {action.action_type} COMPLETED ({action.duration_ms:.1f}ms)")

    def verify_action(self, action_id: str, verification_result: Dict[str, Any]):
        """Verify that an action actually fixed the problem."""
        if action_id not in self.actions:
            logger.warning(f"[TRACKER] Action {action_id} not found for verification")
            return
        
        action = self.actions[action_id]
        action.verification_result = verification_result
        
        if verification_result.get("success", False):
            action.status = ActionStatus.VERIFIED
            logger.info(f"[TRACKER] VERIFIED {action.action_type}: {verification_result.get('message', 'Fix verified')}")
        else:
            action.status = ActionStatus.VERIFICATION_FAILED
            logger.warning(f"[TRACKER] WARN {action.action_type} VERIFICATION FAILED: {verification_result.get('message', 'Fix did not work')}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total = len(self.actions)
        completed = sum(1 for a in self.actions.values() if a.status == ActionStatus.COMPLETED)
        failed = sum(1 for a in self.actions.values() if a.status == ActionStatus.FAILED)
        verified = sum(1 for a in self.actions.values() if a.status == ActionStatus.VERIFIED)
        verification_failed = sum(1 for a in self.actions.values() if a.status == ActionStatus.VERIFICATION_FAILED)
        
        duration = (datetime.now() - self.start_time).total_seconds() if not self.end_time else (self.end_time - self.start_time).total_seconds()
        
        return {
            "total_actions": total,
            "completed": completed,
            "failed": failed,
            "verified": verified,
            "verification_failed": verification_failed,
            "total_errors": len(self.errors),
            "duration_seconds": duration,
            "actions_by_type": self._count_by_type()
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count actions by type."""
        counts = {}
        for action in self.actions.values():
            counts[action.action_type] = counts.get(action.action_type, 0) + 1
        return counts

    def save_report(self, filepath: Path):
        """Save tracking report to file."""
        report = {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "summary": self.get_summary(),
            "actions": [action.to_dict() for action in self.actions.values()],
            "errors": self.errors
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[TRACKER] Report saved to {filepath}")


def initialize_database(tracker: PipelineTracker) -> Optional[Any]:
    """Initialize database connection."""
    action_id = tracker.start_action("database_init", "Initialize database connection")
    
    try:
        # Import from backend database module
        import sys
        backend_path = Path(__file__).parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        # Create a temporary config.py shim if it doesn't exist (for connection.py import)
        config_shim_path = backend_path / "config.py"
        if not config_shim_path.exists():
            logger.debug("[TRACKER] Creating config.py shim for database imports")
            with open(config_shim_path, 'w') as f:
                f.write("""# Temporary config shim for database imports
from database.config import DatabaseConfig, DatabaseType
__all__ = ['DatabaseConfig', 'DatabaseType']
""")
        
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        tracker.complete_action(action_id, {"status": "connected"})
        logger.info("[OK] Database connection established")
        return session
        
    except Exception as e:
        error_msg = f"Database initialization failed: {str(e)}"
        tracker.complete_action(action_id, error=error_msg)
        logger.error(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return None


def run_diagnostic_cycle(tracker: PipelineTracker, diagnostic_engine: Any) -> Optional[Dict[str, Any]]:
    """Run a diagnostic cycle."""
    action_id = tracker.start_action("diagnostic_cycle", "Run diagnostic engine cycle")
    
    try:
        cycle = diagnostic_engine.run_cycle()
        
        result = {
            "cycle_id": cycle.cycle_id,
            "trigger_source": cycle.trigger_source.value,
            "health_status": cycle.judgement.health.status.value if cycle.judgement else "unknown",
            "anomalies_detected": len(cycle.interpreted_data.anomalies) if cycle.interpreted_data else 0,
            "action_taken": cycle.action_decision.action_type.value if cycle.action_decision else "none",
            "duration_ms": cycle.total_duration_ms,
            "success": cycle.success
        }
        
        tracker.complete_action(action_id, result)
        return result
        
    except Exception as e:
        error_msg = f"Diagnostic cycle failed: {str(e)}"
        tracker.complete_action(action_id, error=error_msg)
        traceback.print_exc()
        return None


def start_diagnostic_engine(tracker: PipelineTracker) -> Optional[Any]:
    """Start diagnostic engine."""
    action_id = tracker.start_action("diagnostic_start", "Start diagnostic engine")
    
    try:
        from diagnostic_machine.diagnostic_engine import start_diagnostic_engine
        
        engine = start_diagnostic_engine(
            heartbeat_interval=60,
            enable_heartbeat=False,  # Don't run heartbeat in tracker mode
            enable_cicd=True,
            enable_healing=True,
            enable_freeze=True,
            enable_forensics=True,
            dry_run=False
        )
        
        tracker.complete_action(action_id, {"engine_id": id(engine), "state": engine.state.value})
        logger.info("[OK] Diagnostic Engine started")
        return engine
        
    except Exception as e:
        error_msg = f"Failed to start diagnostic engine: {str(e)}"
        tracker.complete_action(action_id, error=error_msg)
        traceback.print_exc()
        return None


def start_healing_system(tracker: PipelineTracker, session: Any) -> Optional[Any]:
    """Start self-healing system."""
    action_id = tracker.start_action("healing_start", "Start self-healing system")
    
    try:
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        
        healing_system = get_autonomous_healing(
            session=session,
            repo_path=Path("backend").resolve() if Path("backend").exists() else Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        tracker.complete_action(action_id, {"trust_level": TrustLevel.MEDIUM_RISK_AUTO.name})
        logger.info("[OK] Self-Healing System started")
        return healing_system
        
    except Exception as e:
        error_msg = f"Failed to start healing system: {str(e)}"
        tracker.complete_action(action_id, error=error_msg)
        traceback.print_exc()
        return None


def run_healing_cycle(tracker: PipelineTracker, healing_system: Any) -> Optional[Dict[str, Any]]:
    """Run a healing monitoring cycle."""
    action_id = tracker.start_action("healing_cycle", "Run self-healing monitoring cycle")
    
    try:
        result = healing_system.run_monitoring_cycle()
        
        # Track individual healing actions
        if result.get("actions_executed", 0) > 0:
            for i, executed_action in enumerate(result.get("results", {}).get("executed", [])):
                heal_action_id = tracker.start_action(
                    "healing_action",
                    f"Healing action: {executed_action.get('action', 'unknown')}",
                    input_data=executed_action,
                    parent_id=action_id
                )
                tracker.complete_action(heal_action_id, executed_action)
                
                # Verify the healing action
                verify_healing_action(tracker, heal_action_id, executed_action, healing_system)
        
        # Track failures
        if result.get("failures", 0) > 0:
            for failed_action in result.get("results", {}).get("failed", []):
                fail_action_id = tracker.start_action(
                    "healing_failure",
                    f"Healing action failed: {failed_action.get('decision', {}).get('healing_action', 'unknown')}",
                    input_data=failed_action,
                    parent_id=action_id
                )
                tracker.complete_action(fail_action_id, failed_action, error=failed_action.get("error", "Unknown error"))
        
        tracker.complete_action(action_id, result)
        return result
        
    except Exception as e:
        error_msg = f"Healing cycle failed: {str(e)}"
        tracker.complete_action(action_id, error=error_msg)
        traceback.print_exc()
        return None


def verify_healing_action(tracker: PipelineTracker, action_id: str, healing_result: Dict[str, Any], healing_system: Any):
    """Verify that a healing action actually fixed the problem."""
    verify_id = tracker.start_action("verification", "Verify healing action worked", parent_id=action_id)
    
    try:
        action = healing_result.get("action", "")
        success = healing_result.get("success", False)
        
        # Re-assess health to see if issue is resolved
        assessment = healing_system.assess_system_health()
        
        # Check if the original issue is still present
        original_anomaly = healing_result.get("anomaly", {})
        anomaly_type = original_anomaly.get("type", "")
        
        # Check if similar anomalies still exist
        current_anomalies = assessment.get("anomalies", [])
        similar_anomalies = [
            a for a in current_anomalies
            if a.get("type") == anomaly_type or a.get("service") == original_anomaly.get("service")
        ]
        
        verification_result = {
            "success": success and len(similar_anomalies) == 0,
            "action": action,
            "original_anomaly_type": anomaly_type,
            "similar_anomalies_remaining": len(similar_anomalies),
            "health_status_after": assessment.get("health_status"),
            "message": f"Action {action} {'succeeded' if success else 'failed'}, "
                      f"{len(similar_anomalies)} similar anomalies {'remain' if similar_anomalies else 'resolved'}"
        }
        
        tracker.verify_action(action_id, verification_result)
        tracker.complete_action(verify_id, verification_result)
        
    except Exception as e:
        error_msg = f"Verification failed: {str(e)}"
        tracker.complete_action(verify_id, error=error_msg)
        tracker.verify_action(action_id, {"success": False, "message": f"Verification error: {error_msg}"})


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("GRACE FULL PIPELINE TRACKER")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script will:")
    logger.info("  1. Run diagnostic engine")
    logger.info("  2. Run self-healing system")
    logger.info("  3. Track every action with detailed logging")
    logger.info("  4. Verify if fixes actually work")
    logger.info("  5. Identify errors and issues")
    logger.info("")
    
    tracker = PipelineTracker()
    
    try:
        # Step 1: Initialize database
        logger.info("[STEP 1] Initializing database...")
        session = initialize_database(tracker)
        if not session:
            logger.error("[FATAL] Cannot continue without database connection")
            return 1
        
        # Step 2: Start diagnostic engine
        logger.info("[STEP 2] Starting diagnostic engine...")
        diagnostic_engine = start_diagnostic_engine(tracker)
        if not diagnostic_engine:
            logger.warning("[WARNING] Diagnostic engine failed to start, continuing with healing only")
        
        # Step 3: Start healing system
        logger.info("[STEP 3] Starting self-healing system...")
        healing_system = start_healing_system(tracker, session)
        if not healing_system:
            logger.error("[FATAL] Cannot continue without healing system")
            return 1
        
        # Step 4: Run initial diagnostic cycle
        logger.info("[STEP 4] Running initial diagnostic cycle...")
        if diagnostic_engine:
            diagnostic_result = run_diagnostic_cycle(tracker, diagnostic_engine)
            if diagnostic_result:
                logger.info(f"  Health: {diagnostic_result.get('health_status')}")
                logger.info(f"  Anomalies: {diagnostic_result.get('anomalies_detected')}")
                logger.info(f"  Action: {diagnostic_result.get('action_taken')}")
        
        # Step 5: Run initial healing cycle
        logger.info("[STEP 5] Running initial healing cycle...")
        healing_result = run_healing_cycle(tracker, healing_system)
        if healing_result:
            logger.info(f"  Health: {healing_result.get('health_status')}")
            logger.info(f"  Anomalies: {healing_result.get('anomalies_detected')}")
            logger.info(f"  Actions executed: {healing_result.get('actions_executed')}")
            logger.info(f"  Failures: {healing_result.get('failures')}")
        
        # Step 6: Run verification cycle
        logger.info("[STEP 6] Running verification cycle...")
        time.sleep(2)  # Brief pause to let changes settle
        verification_result = run_healing_cycle(tracker, healing_system)
        if verification_result:
            logger.info(f"  Health after fixes: {verification_result.get('health_status')}")
            logger.info(f"  Anomalies after fixes: {verification_result.get('anomalies_detected')}")
        
        # Step 7: Final diagnostic cycle
        logger.info("[STEP 7] Running final diagnostic cycle...")
        if diagnostic_engine:
            final_diagnostic = run_diagnostic_cycle(tracker, diagnostic_engine)
            if final_diagnostic:
                logger.info(f"  Final health: {final_diagnostic.get('health_status')}")
        
        # Cleanup
        if diagnostic_engine:
            try:
                diagnostic_engine.stop()
                logger.info("[OK] Diagnostic engine stopped")
            except Exception as e:
                logger.warning(f"Error stopping diagnostic engine: {e}")
        
        tracker.end_time = datetime.now()
        
        # Generate report
        summary = tracker.get_summary()
        logger.info("")
        logger.info("=" * 80)
        logger.info("PIPELINE TRACKER SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total actions: {summary['total_actions']}")
        logger.info(f"  Completed: {summary['completed']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Verified: {summary['verified']}")
        logger.info(f"  Verification failed: {summary['verification_failed']}")
        logger.info(f"Total errors: {summary['total_errors']}")
        logger.info(f"Duration: {summary['duration_seconds']:.1f} seconds")
        logger.info("")
        logger.info("Actions by type:")
        for action_type, count in summary['actions_by_type'].items():
            logger.info(f"  {action_type}: {count}")
        logger.info("")
        
        # Save report
        report_file = log_dir / f"pipeline_tracker_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        tracker.save_report(report_file)
        
        logger.info("=" * 80)
        logger.info(f"[OK] Pipeline tracker completed. Report saved to {report_file}")
        logger.info("=" * 80)
        
        return 0 if summary['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPTED] Pipeline tracker interrupted by user")
        tracker.end_time = datetime.now()
        return 130
        
    except Exception as e:
        logger.error(f"[FATAL] Pipeline tracker failed: {e}")
        traceback.print_exc()
        tracker.end_time = datetime.now()
        
        # Save partial report
        report_file = log_dir / f"pipeline_tracker_report_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        tracker.save_report(report_file)
        logger.info(f"Partial report saved to {report_file}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
