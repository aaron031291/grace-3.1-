"""
Healing Scheduler - Robust scheduling for self-healing operations.

Provides:
1. APScheduler-like scheduling with the `schedule` library
2. Persistent healing queue that survives restarts
3. File watcher integration for proactive healing
4. Centralized scheduler management
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from queue import PriorityQueue
import schedule

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Severity levels for diagnostic alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DiagnosticAlert:
    """A diagnostic alert to be sent."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str = "healing_scheduler"
    created_at: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    sent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "details": self.details,
            "sent": self.sent,
        }


class HealingPriority(int, Enum):
    """Priority levels for healing tasks."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class HealingTaskStatus(str, Enum):
    """Status of a healing task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class HealingTask:
    """A healing task in the queue."""
    task_id: str
    task_type: str
    priority: HealingPriority
    created_at: datetime
    status: HealingTaskStatus = HealingTaskStatus.PENDING
    
    # Task details
    description: str = ""
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    anomaly_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def __lt__(self, other):
        """Compare by priority for queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "description": self.description,
            "file_path": self.file_path,
            "error_message": self.error_message,
            "anomaly_data": self.anomaly_data,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealingTask":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            priority=HealingPriority(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=HealingTaskStatus(data["status"]),
            description=data.get("description", ""),
            file_path=data.get("file_path"),
            error_message=data.get("error_message"),
            anomaly_data=data.get("anomaly_data", {}),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            last_error=data.get("last_error"),
        )


class PersistentHealingQueue:
    """
    Persistent queue for healing tasks that survives restarts.
    
    Tasks are stored in a JSON file and reloaded on startup.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/healing_queue.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._queue: PriorityQueue = PriorityQueue()
        self._tasks: Dict[str, HealingTask] = {}
        self._lock = threading.Lock()
        
        # Load persisted tasks
        self._load_from_disk()
        
        logger.info(f"[HEALING-QUEUE] Initialized with {len(self._tasks)} persisted tasks")
    
    def _load_from_disk(self):
        """Load tasks from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            for task_data in data.get("tasks", []):
                task = HealingTask.from_dict(task_data)
                # Only reload pending/retrying tasks
                if task.status in (HealingTaskStatus.PENDING, HealingTaskStatus.RETRYING):
                    self._tasks[task.task_id] = task
                    self._queue.put(task)
            
            logger.info(f"[HEALING-QUEUE] Loaded {len(self._tasks)} pending tasks from disk")
        except Exception as e:
            logger.warning(f"[HEALING-QUEUE] Could not load tasks: {e}")
    
    def _save_to_disk(self):
        """Save tasks to disk."""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "tasks": [task.to_dict() for task in self._tasks.values()]
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[HEALING-QUEUE] Could not save tasks: {e}")
    
    def add_task(self, task: HealingTask) -> bool:
        """Add a task to the queue."""
        with self._lock:
            if task.task_id in self._tasks:
                logger.debug(f"[HEALING-QUEUE] Task {task.task_id} already exists")
                return False
            
            self._tasks[task.task_id] = task
            self._queue.put(task)
            self._save_to_disk()
            
            logger.info(f"[HEALING-QUEUE] Added task {task.task_id} ({task.priority.name})")
            return True
    
    def get_next_task(self) -> Optional[HealingTask]:
        """Get the highest priority task."""
        with self._lock:
            while not self._queue.empty():
                task = self._queue.get_nowait()
                if task.task_id in self._tasks and task.status == HealingTaskStatus.PENDING:
                    task.status = HealingTaskStatus.IN_PROGRESS
                    task.started_at = datetime.now()
                    self._save_to_disk()
                    return task
            return None
    
    def complete_task(self, task_id: str, success: bool, result: Optional[Dict] = None, error: Optional[str] = None):
        """Mark a task as completed."""
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.completed_at = datetime.now()
            task.result = result
            
            if success:
                task.status = HealingTaskStatus.COMPLETED
                logger.info(f"[HEALING-QUEUE] Task {task_id} completed successfully")
            else:
                task.last_error = error
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = HealingTaskStatus.RETRYING
                    task.started_at = None
                    task.completed_at = None
                    self._queue.put(task)
                    logger.warning(f"[HEALING-QUEUE] Task {task_id} failed, retrying ({task.retry_count}/{task.max_retries})")
                else:
                    task.status = HealingTaskStatus.FAILED
                    logger.error(f"[HEALING-QUEUE] Task {task_id} failed after {task.max_retries} retries")
            
            self._save_to_disk()
    
    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return sum(1 for t in self._tasks.values() if t.status == HealingTaskStatus.PENDING)
    
    def get_all_tasks(self) -> List[HealingTask]:
        """Get all tasks."""
        return list(self._tasks.values())
    
    def clear_completed(self, older_than_hours: int = 24):
        """Clear completed tasks older than specified hours."""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=older_than_hours)
            to_remove = [
                task_id for task_id, task in self._tasks.items()
                if task.status in (HealingTaskStatus.COMPLETED, HealingTaskStatus.CANCELLED)
                and task.completed_at and task.completed_at < cutoff
            ]
            for task_id in to_remove:
                del self._tasks[task_id]
            
            if to_remove:
                self._save_to_disk()
                logger.info(f"[HEALING-QUEUE] Cleared {len(to_remove)} old tasks")


class FileWatcherHealing:
    """
    File watcher that triggers healing on file changes.
    
    Uses watchdog to monitor the codebase and trigger proactive healing.
    """
    
    def __init__(
        self,
        watch_paths: List[Path],
        healing_callback: Callable[[str, str], None],
        debounce_seconds: float = 2.0,
    ):
        self.watch_paths = watch_paths
        self.healing_callback = healing_callback
        self.debounce_seconds = debounce_seconds
        
        self._observer = None
        self._pending_changes: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._debounce_thread = None
        
        self.exclude_patterns = {
            "__pycache__",
            ".git",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            "*.pyc",
            "*.pyo",
            "*.log",
            "healing_queue.json",
        }
    
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.exclude_patterns:
            if pattern.startswith("*"):
                if path.endswith(pattern[1:]):
                    return True
            elif pattern in path:
                return True
        return False
    
    def _on_file_change(self, event_type: str, src_path: str):
        """Handle file change event."""
        if self._should_ignore(src_path):
            return
        
        # Only process Python files for healing
        if not src_path.endswith(".py"):
            return
        
        with self._lock:
            self._pending_changes[src_path] = time.time()
    
    def _debounce_worker(self):
        """Process pending changes after debounce period."""
        while self._running:
            time.sleep(0.5)
            
            with self._lock:
                now = time.time()
                to_process = [
                    (path, ts) for path, ts in self._pending_changes.items()
                    if now - ts >= self.debounce_seconds
                ]
                
                for path, _ in to_process:
                    del self._pending_changes[path]
            
            for path, _ in to_process:
                try:
                    logger.info(f"[FILE-WATCHER] File changed: {path}")
                    self.healing_callback("file_change", path)
                except Exception as e:
                    logger.error(f"[FILE-WATCHER] Healing callback error: {e}")
    
    def start(self):
        """Start the file watcher."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class HealingEventHandler(FileSystemEventHandler):
                def __init__(self, callback):
                    self.callback = callback
                
                def on_modified(self, event):
                    if not event.is_directory:
                        self.callback("modified", event.src_path)
                
                def on_created(self, event):
                    if not event.is_directory:
                        self.callback("created", event.src_path)
            
            self._observer = Observer()
            handler = HealingEventHandler(self._on_file_change)
            
            for watch_path in self.watch_paths:
                if watch_path.exists():
                    self._observer.schedule(handler, str(watch_path), recursive=True)
                    logger.info(f"[FILE-WATCHER] Watching: {watch_path}")
            
            self._running = True
            self._observer.start()
            
            self._debounce_thread = threading.Thread(target=self._debounce_worker, daemon=True)
            self._debounce_thread.start()
            
            logger.info("[FILE-WATCHER] File watcher started")
            
        except ImportError:
            logger.warning("[FILE-WATCHER] watchdog not installed, file watching disabled")
        except Exception as e:
            logger.error(f"[FILE-WATCHER] Could not start: {e}")
    
    def stop(self):
        """Stop the file watcher."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            logger.info("[FILE-WATCHER] File watcher stopped")


class HealingScheduler:
    """
    Central scheduler for all healing operations.
    
    Manages:
    - Periodic health checks
    - File watching
    - Persistent healing queue
    - Task execution
    - Alert notifications
    """
    
    def __init__(
        self,
        healing_system=None,
        repo_path: Optional[Path] = None,
        enable_file_watcher: bool = True,
        enable_scheduler: bool = True,
        enable_alerts: bool = True,
    ):
        self.repo_path = repo_path or Path.cwd()
        self.healing_system = healing_system
        self.enable_alerts = enable_alerts
        
        # Persistent queue
        queue_path = self.repo_path / "data" / "healing_queue.json"
        self.queue = PersistentHealingQueue(storage_path=queue_path)
        
        # Alert history
        self._alerts: List[DiagnosticAlert] = []
        self._alert_counter = 0
        
        # Notification manager (lazy loaded)
        self._notification_manager = None
        
        # File watcher
        self.file_watcher: Optional[FileWatcherHealing] = None
        if enable_file_watcher:
            watch_paths = [self.repo_path / "backend"]
            self.file_watcher = FileWatcherHealing(
                watch_paths=watch_paths,
                healing_callback=self._on_file_change,
            )
        
        # Scheduler state
        self._running = False
        self._scheduler_thread = None
        self._worker_thread = None
        
        # Schedule configuration
        self.schedules = {
            "health_check": 5,        # Every 5 minutes
            "proactive_scan": 30,     # Every 30 minutes
            "queue_cleanup": 60,      # Every hour
            "drift_detection": 15,    # Every 15 minutes
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "critical_anomalies": 3,      # Alert if 3+ critical anomalies
            "failed_healing_streak": 5,   # Alert if 5 consecutive failures
            "queue_backlog": 20,          # Alert if 20+ pending tasks
            "health_degraded_minutes": 15, # Alert if degraded for 15+ min
        }
        
        logger.info("[HEALING-SCHEDULER] Initialized")
    
    def _get_notification_manager(self):
        """Get or create the notification manager."""
        if self._notification_manager is None:
            try:
                from diagnostic_machine.notifications import get_notification_manager
                self._notification_manager = get_notification_manager()
            except Exception as e:
                logger.warning(f"[HEALING-SCHEDULER] Notification manager unavailable: {e}")
        return self._notification_manager
    
    def send_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "healing_scheduler",
    ) -> Optional[DiagnosticAlert]:
        """
        Send a diagnostic alert through all configured channels.
        
        Args:
            severity: Alert severity level
            title: Alert title
            message: Alert message
            details: Additional details dict
            source: Source of the alert
        
        Returns:
            DiagnosticAlert if sent, None if alerts disabled
        """
        if not self.enable_alerts:
            return None
        
        import uuid
        self._alert_counter += 1
        
        alert = DiagnosticAlert(
            alert_id=f"ALERT-{self._alert_counter:06d}-{uuid.uuid4().hex[:4]}",
            severity=severity,
            title=title,
            message=message,
            source=source,
            details=details or {},
        )
        
        self._alerts.append(alert)
        
        # Send through notification manager
        manager = self._get_notification_manager()
        if manager:
            try:
                from diagnostic_machine.notifications import NotificationPriority
                
                # Map severity to notification priority
                priority_map = {
                    AlertSeverity.INFO: NotificationPriority.LOW,
                    AlertSeverity.WARNING: NotificationPriority.MEDIUM,
                    AlertSeverity.ERROR: NotificationPriority.HIGH,
                    AlertSeverity.CRITICAL: NotificationPriority.CRITICAL,
                }
                
                results = manager.notify(
                    title=f"[{severity.value.upper()}] {title}",
                    message=message,
                    priority=priority_map.get(severity, NotificationPriority.MEDIUM),
                    details=details,
                    tags=["self-healing", source, severity.value],
                )
                
                alert.sent = any(r.status.value == "sent" for r in results)
                
                if alert.sent:
                    logger.info(f"[ALERT] Sent: {title}")
                else:
                    logger.warning(f"[ALERT] Failed to send: {title}")
                    
            except Exception as e:
                logger.error(f"[ALERT] Notification error: {e}")
        else:
            # Fallback: just log
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }.get(severity, logging.INFO)
            
            logger.log(log_level, f"[ALERT] {title}: {message}")
            alert.sent = True
        
        return alert
    
    def trigger_alert_if_needed(self, health_result: Dict[str, Any]):
        """Check health result and trigger alerts based on thresholds."""
        anomalies = health_result.get("anomalies_detected", 0)
        health_status = health_result.get("health_status", "healthy")
        
        # Alert on critical anomaly count
        if anomalies >= self.alert_thresholds["critical_anomalies"]:
            self.send_alert(
                severity=AlertSeverity.ERROR,
                title="Multiple Anomalies Detected",
                message=f"{anomalies} anomalies detected in health check. System may be degraded.",
                details={
                    "anomaly_count": anomalies,
                    "health_status": health_status,
                    "threshold": self.alert_thresholds["critical_anomalies"],
                },
            )
        
        # Alert on degraded health
        if health_status in ("critical", "failing"):
            self.send_alert(
                severity=AlertSeverity.CRITICAL,
                title="System Health Critical",
                message=f"System health is {health_status}. Immediate attention required.",
                details={"health_status": health_status},
            )
        
        # Alert on queue backlog
        pending = self.queue.get_pending_count()
        if pending >= self.alert_thresholds["queue_backlog"]:
            self.send_alert(
                severity=AlertSeverity.WARNING,
                title="Healing Queue Backlog",
                message=f"{pending} tasks pending in healing queue. Consider scaling resources.",
                details={
                    "pending_tasks": pending,
                    "threshold": self.alert_thresholds["queue_backlog"],
                },
            )
    
    def get_recent_alerts(self, limit: int = 50) -> List[DiagnosticAlert]:
        """Get recent alerts."""
        return sorted(self._alerts, key=lambda a: a.created_at, reverse=True)[:limit]
    
    def _on_file_change(self, event_type: str, file_path: str):
        """Handle file change from watcher."""
        import uuid
        
        task = HealingTask(
            task_id=f"file-{uuid.uuid4().hex[:8]}",
            task_type="proactive_scan",
            priority=HealingPriority.MEDIUM,
            created_at=datetime.now(),
            description=f"Proactive scan triggered by file change",
            file_path=file_path,
            anomaly_data={"trigger": event_type, "file": file_path},
        )
        
        self.queue.add_task(task)
    
    def _run_health_check(self):
        """Run periodic health check."""
        if not self.healing_system:
            return
        
        try:
            result = self.healing_system.run_monitoring_cycle()
            logger.info(
                f"[SCHEDULED] Health check: status={result.get('health_status')}, "
                f"anomalies={result.get('anomalies_detected', 0)}"
            )
            
            # Trigger alerts based on health result
            self.trigger_alert_if_needed(result)
            
            # Queue any detected issues
            for anomaly in result.get("anomalies", []):
                import uuid
                task = HealingTask(
                    task_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                    task_type="heal_anomaly",
                    priority=HealingPriority.HIGH,
                    created_at=datetime.now(),
                    description=f"Heal detected anomaly",
                    anomaly_data=anomaly,
                )
                self.queue.add_task(task)
                
        except Exception as e:
            logger.error(f"[SCHEDULED] Health check error: {e}")
            # Alert on health check failure
            self.send_alert(
                severity=AlertSeverity.ERROR,
                title="Health Check Failed",
                message=f"Scheduled health check encountered an error: {str(e)[:200]}",
                details={"error": str(e)},
            )
    
    def _run_proactive_scan(self):
        """Run periodic proactive code scan."""
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            
            engine = get_diagnostic_engine()
            result = engine.run_proactive_scan(auto_heal=False)
            
            issues = result.get("issues_found", 0)
            if issues > 0:
                logger.info(f"[SCHEDULED] Proactive scan found {issues} issues")
                
                # Queue issues for healing
                for issue in result.get("issues", [])[:10]:  # Limit to 10 per scan
                    import uuid
                    task = HealingTask(
                        task_id=f"scan-{uuid.uuid4().hex[:8]}",
                        task_type="code_fix",
                        priority=HealingPriority.MEDIUM,
                        created_at=datetime.now(),
                        description=issue.get("message", "Code issue"),
                        file_path=issue.get("file_path"),
                        anomaly_data=issue,
                    )
                    self.queue.add_task(task)
                    
        except Exception as e:
            logger.debug(f"[SCHEDULED] Proactive scan error: {e}")
    
    def _run_drift_detection(self):
        """Run periodic drift detection."""
        try:
            from telemetry.telemetry_service import get_telemetry_service
            
            telemetry = get_telemetry_service()
            if telemetry:
                drift_result = telemetry.check_for_drift()
                if drift_result.get("drift_detected"):
                    logger.warning(f"[SCHEDULED] Drift detected: {drift_result}")
        except Exception as e:
            logger.debug(f"[SCHEDULED] Drift detection error: {e}")
    
    def _run_queue_cleanup(self):
        """Clean up old completed tasks."""
        self.queue.clear_completed(older_than_hours=24)
    
    def _scheduler_worker(self):
        """Run the scheduler loop."""
        # Set up scheduled jobs
        schedule.every(self.schedules["health_check"]).minutes.do(self._run_health_check)
        schedule.every(self.schedules["proactive_scan"]).minutes.do(self._run_proactive_scan)
        schedule.every(self.schedules["queue_cleanup"]).minutes.do(self._run_queue_cleanup)
        schedule.every(self.schedules["drift_detection"]).minutes.do(self._run_drift_detection)
        
        logger.info("[HEALING-SCHEDULER] Scheduled jobs configured:")
        logger.info(f"  - Health check: every {self.schedules['health_check']} minutes")
        logger.info(f"  - Proactive scan: every {self.schedules['proactive_scan']} minutes")
        logger.info(f"  - Drift detection: every {self.schedules['drift_detection']} minutes")
        logger.info(f"  - Queue cleanup: every {self.schedules['queue_cleanup']} minutes")
        
        while self._running:
            schedule.run_pending()
            time.sleep(10)  # Check every 10 seconds
    
    def _task_worker(self):
        """Process tasks from the queue."""
        while self._running:
            task = self.queue.get_next_task()
            
            if task:
                try:
                    logger.info(f"[TASK-WORKER] Processing task {task.task_id} ({task.task_type})")
                    result = self._execute_task(task)
                    self.queue.complete_task(task.task_id, success=True, result=result)
                except Exception as e:
                    logger.error(f"[TASK-WORKER] Task {task.task_id} failed: {e}")
                    self.queue.complete_task(task.task_id, success=False, error=str(e))
            else:
                time.sleep(5)  # No tasks, wait before checking again
    
    def _execute_task(self, task: HealingTask) -> Dict[str, Any]:
        """Execute a healing task."""
        if task.task_type == "heal_anomaly" and self.healing_system:
            decisions = self.healing_system.decide_healing_actions([task.anomaly_data])
            if decisions:
                return self.healing_system.execute_healing(decisions)
        
        elif task.task_type == "code_fix" and self.healing_system:
            from cognitive.autonomous_healing_system import HealingAction
            return self.healing_system._execute_action(
                HealingAction.CODE_FIX.value,
                task.anomaly_data,
                "scheduler"
            )
        
        elif task.task_type == "proactive_scan":
            from diagnostic_machine.proactive_code_scanner import get_proactive_scanner
            scanner = get_proactive_scanner()
            if task.file_path:
                return {"scanned": task.file_path, "issues": scanner.scan_file(Path(task.file_path))}
        
        return {"status": "no_action", "task_type": task.task_type}
    
    def start(self):
        """Start the healing scheduler."""
        if self._running:
            return
        
        self._running = True
        
        # Start file watcher
        if self.file_watcher:
            self.file_watcher.start()
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self._scheduler_thread.start()
        
        # Start task worker thread
        self._worker_thread = threading.Thread(target=self._task_worker, daemon=True)
        self._worker_thread.start()
        
        # Run initial health check
        self._run_health_check()
        
        logger.info("[HEALING-SCHEDULER] Started with file watcher and task queue")
    
    def stop(self):
        """Stop the healing scheduler."""
        self._running = False
        
        if self.file_watcher:
            self.file_watcher.stop()
        
        logger.info("[HEALING-SCHEDULER] Stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "pending_tasks": self.queue.get_pending_count(),
            "total_tasks": len(self.queue.get_all_tasks()),
            "file_watcher_active": self.file_watcher is not None and self.file_watcher._running,
            "schedules": self.schedules,
        }
    
    def add_healing_task(
        self,
        task_type: str,
        priority: HealingPriority = HealingPriority.MEDIUM,
        description: str = "",
        file_path: Optional[str] = None,
        anomaly_data: Optional[Dict] = None,
    ) -> str:
        """Add a healing task to the queue."""
        import uuid
        
        task = HealingTask(
            task_id=f"manual-{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            priority=priority,
            created_at=datetime.now(),
            description=description,
            file_path=file_path,
            anomaly_data=anomaly_data or {},
        )
        
        self.queue.add_task(task)
        return task.task_id


# Singleton instance
_scheduler_instance: Optional[HealingScheduler] = None
_scheduler_lock = threading.Lock()


def get_healing_scheduler(
    healing_system=None,
    repo_path: Optional[Path] = None,
) -> HealingScheduler:
    """Get or create the healing scheduler singleton."""
    global _scheduler_instance
    
    with _scheduler_lock:
        if _scheduler_instance is None:
            _scheduler_instance = HealingScheduler(
                healing_system=healing_system,
                repo_path=repo_path,
            )
        elif healing_system and _scheduler_instance.healing_system is None:
            _scheduler_instance.healing_system = healing_system
        
        return _scheduler_instance


def start_healing_scheduler(healing_system=None, repo_path: Optional[Path] = None):
    """Start the healing scheduler."""
    scheduler = get_healing_scheduler(healing_system, repo_path)
    scheduler.start()
    return scheduler
