import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import threading
from utils.os_adapter import OS, paths
class ActionType(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Action types."""
    TEST = "test"
    MIGRATE = "migrate"
    LINT = "lint"
    BUILD = "build"
    DEPLOY = "deploy"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    HEALTH_CHECK = "health_check"


class TriggerType(str, Enum):
    """Trigger types."""
    SCHEDULE = "schedule"  # Time-based (cron-like)
    FILE_CHANGE = "file_change"  # File modification
    API_CALL = "api_call"  # HTTP endpoint hit
    EVENT = "event"  # Internal event
    MANUAL = "manual"  # Manual trigger


@dataclass
class Action:
    """Action definition."""
    id: str
    name: str
    action_type: ActionType
    trigger_type: TriggerType
    command: str
    schedule: Optional[str] = None  # Cron-like schedule
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        if self.last_run:
            data['last_run'] = self.last_run.isoformat()
        if self.next_run:
            data['next_run'] = self.next_run.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Action':
        """Create from dictionary."""
        if data.get('last_run'):
            data['last_run'] = datetime.fromisoformat(data['last_run'])
        if data.get('next_run'):
            data['next_run'] = datetime.fromisoformat(data['next_run'])
        return cls(**data)


class AutoActionsManager:
    """
    Manages auto-actions within GRACE.
    
    Runs actions automatically based on triggers.
    All actions run natively within GRACE.
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """Initialize auto-actions manager."""
        self.root_path = root_path or Path(__file__).parent.parent.parent
        self.config_path = self.root_path / "backend" / "ci_cd" / "auto_actions_config.json"
        self.actions: Dict[str, Action] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        self.logger = logger
        
        # Load configuration
        self._load_config()
        
        # Register default actions
        self._register_default_actions()
    
    def _load_config(self):
        """Load actions configuration."""
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text(encoding='utf-8'))
                for action_data in config.get('actions', []):
                    action = Action.from_dict(action_data)
                    self.actions[action.id] = action
                self.logger.info(f"Loaded {len(self.actions)} actions from config")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        else:
            self.logger.info("No config file found, using defaults")
    
    def _save_config(self):
        """Save actions configuration."""
        config = {
            'actions': [action.to_dict() for action in self.actions.values()],
            'updated': datetime.now().isoformat(),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    
    def _register_default_actions(self):
        """Register default auto-actions."""
        defaults = [
            Action(
                id="daily_test",
                name="Daily Test Run",
                action_type=ActionType.TEST,
                trigger_type=TriggerType.SCHEDULE,
                command="python -m backend.ci_cd.native_test_runner",
                schedule="0 2 * * *",  # 2 AM daily
                enabled=True,
            ),
            Action(
                id="pre_commit_test",
                name="Pre-Commit Tests",
                action_type=ActionType.TEST,
                trigger_type=TriggerType.FILE_CHANGE,
                command="python -m backend.ci_cd.native_test_runner",
                enabled=True,
                metadata={"watch_paths": ["backend/"]},
            ),
            Action(
                id="weekly_cleanup",
                name="Weekly Cleanup",
                action_type=ActionType.CLEANUP,
                trigger_type=TriggerType.SCHEDULE,
                command="python -m backend.ci_cd.cleanup",
                schedule="0 3 * * 0",  # 3 AM Sunday
                enabled=True,
            ),
            Action(
                id="health_check",
                name="Health Check",
                action_type=ActionType.HEALTH_CHECK,
                trigger_type=TriggerType.SCHEDULE,
                command="python -m backend.ci_cd.health_check",
                schedule="*/30 * * * *",  # Every 30 minutes
                enabled=True,
            ),
        ]
        
        for action in defaults:
            if action.id not in self.actions:
                self.actions[action.id] = action
        
        self._save_config()
    
    def register_action(self, action: Action):
        """Register a new action."""
        self.actions[action.id] = action
        self._save_config()
        self.logger.info(f"Registered action: {action.name} ({action.id})")
    
    def trigger_action(self, action_id: str) -> Dict[str, Any]:
        """Manually trigger an action."""
        if action_id not in self.actions:
            return {'success': False, 'error': f'Action not found: {action_id}'}
        
        action = self.actions[action_id]
        if not action.enabled:
            return {'success': False, 'error': f'Action is disabled: {action_id}'}
        
        return self._execute_action(action)
    
    def _execute_action(self, action: Action) -> Dict[str, Any]:
        """Execute an action."""
        start_time = time.time()
        self.logger.info(f"Executing action: {action.name} ({action.id})")
        
        try:
            import subprocess
            from utils.os_adapter import process
            
            # Parse command
            parts = action.command.split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Execute command
            proc = process.spawn(
                [cmd] + args,
                cwd=str(self.root_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = proc.communicate(timeout=300)  # 5 minute timeout
            
            duration = time.time() - start_time
            
            result = {
                'success': proc.returncode == 0,
                'action_id': action.id,
                'action_name': action.name,
                'duration': duration,
                'returncode': proc.returncode,
                'stdout': stdout.decode('utf-8', errors='ignore') if stdout else '',
                'stderr': stderr.decode('utf-8', errors='ignore') if stderr else '',
            }
            
            # Update action
            action.last_run = datetime.now()
            self._save_config()
            
            if result['success']:
                self.logger.info(f"Action completed successfully: {action.name} ({duration:.2f}s)")
            else:
                self.logger.warning(f"Action failed: {action.name} (return code: {proc.returncode})")
            
            return result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.logger.error(f"Action timed out: {action.name}")
            return {
                'success': False,
                'action_id': action.id,
                'action_name': action.name,
                'duration': duration,
                'error': 'Action timed out after 5 minutes',
            }
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Action error: {action.name} - {e}")
            return {
                'success': False,
                'action_id': action.id,
                'action_name': action.name,
                'duration': duration,
                'error': str(e),
            }
    
    def start(self):
        """Start the auto-actions manager."""
        if self.running:
            self.logger.warning("Auto-actions manager already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.logger.info("Auto-actions manager started")
    
    def stop(self):
        """Stop the auto-actions manager."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Auto-actions manager stopped")
    
    def _run_loop(self):
        """Main loop for scheduled actions."""
        while self.running:
            try:
                now = datetime.now()
                
                # Check scheduled actions
                for action in self.actions.values():
                    if not action.enabled:
                        continue
                    
                    if action.trigger_type == TriggerType.SCHEDULE:
                        if self._should_run(action, now):
                            self._execute_action(action)
                            self._calculate_next_run(action, now)
                            self._save_config()
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in auto-actions loop: {e}")
                time.sleep(60)
    
    def _should_run(self, action: Action, now: datetime) -> bool:
        """Check if scheduled action should run."""
        if not action.schedule:
            return False
        
        if action.last_run is None:
            # Never run before
            return True
        
        if action.next_run and now >= action.next_run:
            return True
        
        return False
    
    def _calculate_next_run(self, action: Action, now: datetime):
        """Calculate next run time for scheduled action."""
        # Simple schedule parser (supports basic cron-like syntax)
        # Format: "minute hour day month weekday"
        # Example: "0 2 * * *" = 2 AM daily
        
        parts = action.schedule.split()
        if len(parts) != 5:
            # Invalid schedule
            return
        
        minute, hour, day, month, weekday = parts
        
        # Simple calculation for daily schedules
        if day == '*' and month == '*' and weekday == '*':
            # Daily schedule
            next_run = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            action.next_run = next_run
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of auto-actions manager."""
        return {
            'running': self.running,
            'actions_count': len(self.actions),
            'enabled_actions': sum(1 for a in self.actions.values() if a.enabled),
            'actions': [action.to_dict() for action in self.actions.values()],
        }


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='GRACE Auto-Actions Manager')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'trigger', 'list'], help='Action to perform')
    parser.add_argument('--action-id', type=str, help='Action ID for trigger command')
    
    args = parser.parse_args()
    
    manager = AutoActionsManager()
    
    if args.action == 'start':
        manager.start()
        print("Auto-actions manager started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop()
            print("\nAuto-actions manager stopped")
    
    elif args.action == 'stop':
        manager.stop()
        print("Auto-actions manager stopped")
    
    elif args.action == 'status':
        status = manager.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.action == 'trigger':
        if not args.action_id:
            print("Error: --action-id required for trigger command")
            sys.exit(1)
        result = manager.trigger_action(args.action_id)
        print(json.dumps(result, indent=2))
    
    elif args.action == 'list':
        for action in manager.actions.values():
            print(f"{action.id}: {action.name} ({'enabled' if action.enabled else 'disabled'})")


if __name__ == '__main__':
    import sys
    main()
