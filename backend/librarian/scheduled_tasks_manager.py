import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, time, timedelta
from threading import Timer
import json
class ScheduledTask:
    logger = logging.getLogger(__name__)
    """Represents a scheduled task."""

    def __init__(
        self,
        task_id: str,
        name: str,
        task_func: Callable,
        schedule_type: str,  # "daily", "hourly", "interval", "once"
        schedule_config: Dict[str, Any],
        enabled: bool = True,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None
    ):
        self.task_id = task_id
        self.name = name
        self.task_func = task_func
        self.schedule_type = schedule_type
        self.schedule_config = schedule_config
        self.enabled = enabled
        self.last_run = last_run
        self.next_run = next_run
        self.run_count = 0
        self.last_error: Optional[str] = None

    def should_run(self) -> bool:
        """Check if task should run now."""
        if not self.enabled:
            return False

        if self.next_run is None:
            return False

        return datetime.utcnow() >= self.next_run

    def calculate_next_run(self):
        """Calculate next run time based on schedule."""
        now = datetime.utcnow()

        if self.schedule_type == "daily":
            hour = self.schedule_config.get("hour", 0)
            minute = self.schedule_config.get("minute", 0)
            
            next_run = datetime.combine(now.date(), time(hour, minute))
            if next_run <= now:
                next_run += timedelta(days=1)
            
            self.next_run = next_run

        elif self.schedule_type == "hourly":
            interval_hours = self.schedule_config.get("interval", 1)
            self.next_run = now + timedelta(hours=interval_hours)

        elif self.schedule_type == "interval":
            interval_seconds = self.schedule_config.get("interval_seconds", 3600)
            self.next_run = now + timedelta(seconds=interval_seconds)

        elif self.schedule_type == "once":
            self.next_run = None  # Won't run again

    def execute(self) -> Dict[str, Any]:
        """Execute the task."""
        try:
            self.last_run = datetime.utcnow()
            result = self.task_func()
            self.run_count += 1
            self.last_error = None
            self.calculate_next_run()
            return {
                "success": True,
                "result": result,
                "run_time": self.last_run.isoformat()
            }
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error executing task {self.task_id}: {e}")
            self.calculate_next_run()  # Still schedule next run
            return {
                "success": False,
                "error": str(e),
                "run_time": self.last_run.isoformat() if self.last_run else None
            }


class ScheduledTasksManager:
    """
    Manages scheduled automated tasks for the librarian.

    Supports:
    - Daily tasks (at specific times)
    - Hourly tasks (at intervals)
    - Interval tasks (every N seconds)
    - One-time tasks
    """

    def __init__(self):
        """Initialize task manager."""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.timer: Optional[Timer] = None
        self.running = False
        self.check_interval = 60  # Check every minute

        logger.info("[SCHEDULED-TASKS] Manager initialized")

    def add_task(
        self,
        task_id: str,
        name: str,
        task_func: Callable,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        enabled: bool = True
    ) -> ScheduledTask:
        """
        Add a scheduled task.

        Args:
            task_id: Unique task identifier
            name: Human-readable task name
            task_func: Function to execute
            schedule_type: "daily", "hourly", "interval", or "once"
            schedule_config: Configuration for schedule type
            enabled: Whether task is enabled

        Returns:
            Created ScheduledTask instance
        """
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            task_func=task_func,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            enabled=enabled
        )

        task.calculate_next_run()
        self.tasks[task_id] = task

        logger.info(f"[SCHEDULED-TASKS] Added task: {name} (id: {task_id}, next: {task.next_run})")
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"[SCHEDULED-TASKS] Removed task: {task_id}")
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            return True
        return False

    def run_task(self, task_id: str) -> Dict[str, Any]:
        """Manually run a task."""
        if task_id not in self.tasks:
            return {"success": False, "error": f"Task {task_id} not found"}

        return self.tasks[task_id].execute()

    def _check_and_run_tasks(self):
        """Check for tasks that should run and execute them."""
        if not self.running:
            return

        for task in self.tasks.values():
            if task.should_run():
                logger.info(f"[SCHEDULED-TASKS] Running task: {task.name}")
                result = task.execute()
                
                if not result["success"]:
                    logger.error(f"[SCHEDULED-TASKS] Task {task.name} failed: {result.get('error')}")

        # Schedule next check
        if self.running:
            self.timer = Timer(self.check_interval, self._check_and_run_tasks)
            self.timer.daemon = True
            self.timer.start()

    def start(self):
        """Start the task scheduler."""
        if self.running:
            logger.warning("[SCHEDULED-TASKS] Scheduler already running")
            return

        self.running = True
        logger.info("[SCHEDULED-TASKS] Started scheduler")
        self._check_and_run_tasks()

    def stop(self):
        """Stop the task scheduler."""
        self.running = False
        if self.timer:
            self.timer.cancel()
            self.timer = None
        logger.info("[SCHEDULED-TASKS] Stopped scheduler")

    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of task(s)."""
        if task_id:
            if task_id not in self.tasks:
                return {"error": f"Task {task_id} not found"}
            
            task = self.tasks[task_id]
            return {
                "task_id": task.task_id,
                "name": task.name,
                "enabled": task.enabled,
                "schedule_type": task.schedule_type,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "run_count": task.run_count,
                "last_error": task.last_error
            }
        else:
            return {
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "name": task.name,
                        "enabled": task.enabled,
                        "schedule_type": task.schedule_type,
                        "last_run": task.last_run.isoformat() if task.last_run else None,
                        "next_run": task.next_run.isoformat() if task.next_run else None,
                        "run_count": task.run_count
                    }
                    for task in self.tasks.values()
                ],
                "total_tasks": len(self.tasks),
                "running": self.running
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        enabled_count = sum(1 for task in self.tasks.values() if task.enabled)
        total_runs = sum(task.run_count for task in self.tasks.values())
        tasks_with_errors = sum(1 for task in self.tasks.values() if task.last_error)

        return {
            "total_tasks": len(self.tasks),
            "enabled_tasks": enabled_count,
            "disabled_tasks": len(self.tasks) - enabled_count,
            "total_runs": total_runs,
            "tasks_with_errors": tasks_with_errors,
            "scheduler_running": self.running
        }


# Global task manager instance
_task_manager: Optional[ScheduledTasksManager] = None


def get_scheduled_tasks_manager() -> ScheduledTasksManager:
    """Get or create the global scheduled tasks manager."""
    global _task_manager
    if _task_manager is None:
        _task_manager = ScheduledTasksManager()
    return _task_manager
