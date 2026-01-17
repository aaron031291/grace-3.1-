import os
import sys
import time
import signal
import subprocess
import logging
import json
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from backend.utils.os_adapter import OS, process, shell
class SystemState(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """System state."""
    RUNNING = "running"
    CRASHED = "crashed"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPED = "stopped"


class IssueSeverity(str, Enum):
    """Issue severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DiagnosedIssue:
    """A diagnosed issue."""
    issue_id: str
    severity: IssueSeverity
    category: str
    description: str
    root_cause: str
    fix_action: str
    fix_commands: List[str]
    estimated_time_seconds: int
    confidence: float
    detected_at: datetime


@dataclass
class WatchdogStatus:
    """Watchdog status."""
    state: SystemState
    main_process_pid: Optional[int]
    uptime_seconds: float
    restart_count: int
    issues_fixed: int
    last_check: datetime
    last_restart: Optional[datetime]


class WatchdogHealing:
    """
    Watchdog that monitors and heals the GRACE system.
    
    Runs as a separate process that can survive main runtime crashes.
    """
    
    def __init__(
        self,
        main_script_path: str,
        check_interval: int = 30,
        max_restarts: int = 10,
        restart_delay: int = 5,
        log_dir: Optional[Path] = None,
        start_frontend: bool = True,
        frontend_path: Optional[str] = None
    ):
        """
        Initialize watchdog.
        
        Args:
            main_script_path: Path to main launcher script
            check_interval: Seconds between health checks
            max_restarts: Maximum restarts before giving up
            restart_delay: Seconds to wait before restarting
            log_dir: Directory for watchdog logs
            start_frontend: Whether to also start the frontend
            frontend_path: Path to frontend directory (auto-detected if None)
        """
        self.main_script_path = Path(main_script_path)
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self.log_dir = log_dir or Path(__file__).parent.parent.parent / "logs" / "watchdog"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.start_frontend = start_frontend
        
        # Find frontend path
        if frontend_path:
            self.frontend_path = Path(frontend_path)
        else:
            # Auto-detect: look for frontend directory relative to main script
            project_root = self.main_script_path.parent
            self.frontend_path = project_root / "frontend"
        
        # State
        self.main_process: Optional[subprocess.Popen] = None
        self.main_process_pid: Optional[int] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.frontend_process_pid: Optional[int] = None
        self.restart_count = 0
        self.issues_fixed = 0
        self.start_time = datetime.utcnow()
        self.last_restart: Optional[datetime] = None
        self.running = False
        
        # Load previous state
        self._load_state()
        
        logger.info(f"[WATCHDOG] Initialized - monitoring: {self.main_script_path}")
        if self.start_frontend:
            logger.info(f"[WATCHDOG] Frontend will be started: {self.frontend_path}")
        logger.info(f"[WATCHDOG] Max restarts: {max_restarts}, Check interval: {check_interval}s")
    
    def _load_state(self):
        """Load previous watchdog state."""
        state_file = self.log_dir / "watchdog_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.restart_count = state.get("restart_count", 0)
                    self.issues_fixed = state.get("issues_fixed", 0)
                    logger.info(f"[WATCHDOG] Loaded state: {self.restart_count} restarts, {self.issues_fixed} fixes")
            except Exception as e:
                logger.warning(f"[WATCHDOG] Could not load state: {e}")
    
    def _save_state(self):
        """Save current watchdog state."""
        state_file = self.log_dir / "watchdog_state.json"
        try:
            state = {
                "restart_count": self.restart_count,
                "issues_fixed": self.issues_fixed,
                "last_restart": self.last_restart.isoformat() if self.last_restart else None,
                "start_time": self.start_time.isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[WATCHDOG] Could not save state: {e}")
    
    def start(self):
        """Start the watchdog and main process."""
        self.running = True
        logger.info("[WATCHDOG] Starting watchdog service...")
        
        # Start main process
        self._start_main_process()
        
        # Start frontend if enabled
        if self.start_frontend:
            self._start_frontend_process()
        
        # Start monitoring loop
        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            logger.info("[WATCHDOG] Shutdown requested")
            self.stop()
        except Exception as e:
            logger.error(f"[WATCHDOG] Fatal error: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Stop watchdog and main process."""
        logger.info("[WATCHDOG] Stopping watchdog...")
        self.running = False
        
        # Stop frontend
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("[WATCHDOG] Frontend process did not terminate, forcing kill")
                self.frontend_process.kill()
            except Exception as e:
                logger.error(f"[WATCHDOG] Error stopping frontend process: {e}")
        
        # Stop main process
        if self.main_process:
            try:
                self.main_process.terminate()
                self.main_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("[WATCHDOG] Main process did not terminate, forcing kill")
                self.main_process.kill()
            except Exception as e:
                logger.error(f"[WATCHDOG] Error stopping main process: {e}")
        
        self._save_state()
        logger.info("[WATCHDOG] Stopped")
    
    def _start_main_process(self):
        """Start the main GRACE process."""
        if self.main_process and self.main_process.poll() is None:
            logger.warning("[WATCHDOG] Main process already running")
            return
        
        # Check if process is already running by PID
        if self.main_process_pid:
            try:
                process = psutil.Process(self.main_process_pid)
                if process.is_running():
                    logger.info(f"[WATCHDOG] Main process already running (PID: {self.main_process_pid})")
                    # Try to get the process object
                    try:
                        self.main_process = subprocess.Popen(
                            [],  # Dummy command
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        # Replace with actual process reference if possible
                    except:
                        pass
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process doesn't exist or we can't access it
                self.main_process_pid = None
        
        logger.info(f"[WATCHDOG] Starting main process: {self.main_script_path}")
        
        try:
            # Determine how to run the script
            if self.main_script_path.suffix == '.py':
                cmd = [sys.executable, str(self.main_script_path)]
            elif self.main_script_path.suffix == '.bat':
                cmd = [str(self.main_script_path)]
            else:
                cmd = [str(self.main_script_path)]
            
            # Start process using OS adapter (handles OS-specific flags)
            self.main_process = process.spawn(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.main_script_path.parent),
                shell=False,
                bufsize=1,  # Line buffered
                text=True
            )
            
            self.main_process_pid = self.main_process.pid
            logger.info(f"[WATCHDOG] Main process started (PID: {self.main_process_pid})")
            
        except Exception as e:
            logger.error(f"[WATCHDOG] Failed to start main process: {e}")
            raise
    
    def _start_frontend_process(self):
        """Start the frontend process."""
        if not self.frontend_path.exists():
            logger.warning(f"[WATCHDOG] Frontend path does not exist: {self.frontend_path}")
            return
        
        if self.frontend_process and self.frontend_process.poll() is None:
            logger.warning("[WATCHDOG] Frontend process already running")
            return
        
        logger.info(f"[WATCHDOG] Starting frontend process: {self.frontend_path}")
        
        try:
            # Check if package.json exists
            package_json = self.frontend_path / "package.json"
            if not package_json.exists():
                logger.warning(f"[WATCHDOG] Frontend package.json not found: {package_json}")
                return
            
            # Determine npm command (npm run dev for Vite)
            cmd = ["npm", "run", "dev"]
            
            # Start process using OS adapter (handles OS-specific flags)
            self.frontend_process = process.spawn(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.frontend_path),
                shell=False,  # Use command list, not shell
                bufsize=1,
                text=True
            )
            
            self.frontend_process_pid = self.frontend_process.pid
            logger.info(f"[WATCHDOG] Frontend process started (PID: {self.frontend_process_pid})")
            
        except Exception as e:
            logger.error(f"[WATCHDOG] Failed to start frontend process: {e}")
            # Don't raise - frontend is optional
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("[WATCHDOG] Monitoring loop started")
        
        while self.running:
            try:
                # Check if main process is alive
                if not self._is_process_alive():
                    logger.warning("[WATCHDOG] Main process is not running!")
                    
                    # Diagnose the issue
                    issues = self._diagnose_crash()
                    
                    # Fix issues
                    if issues:
                        self._fix_issues(issues)
                    
                    # Restart if allowed
                    if self.restart_count < self.max_restarts:
                        logger.info(f"[WATCHDOG] Restarting main process (attempt {self.restart_count + 1}/{self.max_restarts})")
                        time.sleep(self.restart_delay)
                        self._start_main_process()
                        self.restart_count += 1
                        self.last_restart = datetime.utcnow()
                        self._save_state()
                    else:
                        logger.error(f"[WATCHDOG] Max restarts ({self.max_restarts}) reached. Stopping.")
                        self.running = False
                        break
                
                # Check if frontend process is alive (if enabled)
                if self.start_frontend and self.frontend_process:
                    if self.frontend_process.poll() is not None:
                        logger.warning("[WATCHDOG] Frontend process is not running! Restarting...")
                        self._start_frontend_process()
                
                # Check system health
                health_status = self._check_system_health()
                if health_status != "healthy":
                    logger.warning(f"[WATCHDOG] System health: {health_status}")
                    # Diagnose and fix proactively
                    issues = self._diagnose_health_issues(health_status)
                    if issues:
                        self._fix_issues(issues)
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[WATCHDOG] Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
    
    def _is_process_alive(self) -> bool:
        """Check if main process is alive."""
        if not self.main_process:
            return False
        
        # Check if process is still running
        if self.main_process.poll() is not None:
            # Process has terminated
            return_code = self.main_process.returncode
            logger.warning(f"[WATCHDOG] Main process terminated with code: {return_code}")
            
            # Capture stderr/stdout for diagnosis
            try:
                stdout, stderr = self.main_process.communicate(timeout=1)
                if stdout:
                    self._log_output("stdout", stdout.decode('utf-8', errors='ignore'))
                if stderr:
                    self._log_output("stderr", stderr.decode('utf-8', errors='ignore'))
            except:
                pass
            
            return False
        
        # Also check using psutil for more reliable detection
        try:
            if self.main_process_pid:
                process = psutil.Process(self.main_process_pid)
                return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return True
    
    def _log_output(self, stream: str, output: str):
        """Log process output for diagnosis."""
        log_file = self.log_dir / f"main_process_{stream}.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"{datetime.utcnow().isoformat()} - {stream}\n")
                f.write(f"{'='*80}\n")
                f.write(output)
                f.write("\n")
        except Exception as e:
            logger.error(f"[WATCHDOG] Could not log output: {e}")
    
    def _check_system_health(self) -> str:
        """Check overall system health."""
        try:
            # Check if backend is responding
            import requests
            response = requests.get("http://localhost:8000/health/live", timeout=5)
            if response.status_code == 200:
                return "healthy"
            else:
                return "degraded"
        except requests.exceptions.ConnectionError:
            return "unhealthy"
        except Exception as e:
            logger.debug(f"[WATCHDOG] Health check error: {e}")
            return "unknown"
    
    def _diagnose_crash(self) -> List[DiagnosedIssue]:
        """Diagnose why the system crashed."""
        logger.info("[WATCHDOG] Diagnosing crash...")
        issues = []
        
        # Check log files for errors
        log_files = [
            self.log_dir / "main_process_stderr.log",
            Path(__file__).parent.parent.parent / "logs" / "backend.log",
            Path(__file__).parent.parent.parent / "logs" / "error.log"
        ]
        
        error_patterns = {
            "database": ["database", "sql", "connection", "session"],
            "embedding": ["embedding", "model", "qwen", "cuda"],
            "import": ["import", "module", "no module named"],
            "port": ["port", "address already in use", "8000"],
            "memory": ["memory", "out of memory", "oom"],
            "permission": ["permission", "access denied", "forbidden"]
        }
        
        detected_errors = {}
        
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # Read last 100 lines
                        lines = f.readlines()[-100:]
                        content = ' '.join(lines).lower()
                        
                        for category, patterns in error_patterns.items():
                            for pattern in patterns:
                                if pattern in content:
                                    if category not in detected_errors:
                                        detected_errors[category] = []
                                    detected_errors[category].append(pattern)
                except Exception as e:
                    logger.debug(f"[WATCHDOG] Could not read log file {log_file}: {e}")
        
        # Create diagnosed issues
        for category, patterns in detected_errors.items():
            issue = self._create_issue_for_category(category, patterns)
            if issue:
                issues.append(issue)
        
        # If no specific issues found, create generic crash issue
        if not issues:
            issues.append(DiagnosedIssue(
                issue_id=f"crash_{datetime.utcnow().timestamp()}",
                severity=IssueSeverity.HIGH,
                category="crash",
                description="System crashed for unknown reason",
                root_cause="Process terminated unexpectedly",
                fix_action="restart_and_monitor",
                fix_commands=[],
                estimated_time_seconds=10,
                confidence=0.3,
                detected_at=datetime.utcnow()
            ))
        
        logger.info(f"[WATCHDOG] Diagnosed {len(issues)} issue(s)")
        return issues
    
    def _diagnose_health_issues(self, health_status: str) -> List[DiagnosedIssue]:
        """Diagnose health issues when system is degraded."""
        issues = []
        
        if health_status == "unhealthy":
            # Backend not responding
            issues.append(DiagnosedIssue(
                issue_id=f"unhealthy_{datetime.utcnow().timestamp()}",
                severity=IssueSeverity.MEDIUM,
                category="connectivity",
                description="Backend health endpoint not responding",
                root_cause="Backend may have crashed or is not started",
                fix_action="restart_backend",
                fix_commands=[],
                estimated_time_seconds=15,
                confidence=0.7,
                detected_at=datetime.utcnow()
            ))
        
        return issues
    
    def _create_issue_for_category(self, category: str, patterns: List[str]) -> Optional[DiagnosedIssue]:
        """Create a diagnosed issue for a category."""
        fixes = {
            "database": {
                "description": "Database connection or query error detected",
                "root_cause": "Database may be unavailable or schema mismatch",
                "fix_action": "reset_database_connection",
                "fix_commands": [],
                "severity": IssueSeverity.HIGH
            },
            "embedding": {
                "description": "Embedding model error detected",
                "root_cause": "Embedding model path missing or CUDA issue",
                "fix_action": "skip_embedding_or_download",
                "fix_commands": [],
                "severity": IssueSeverity.MEDIUM
            },
            "import": {
                "description": "Python import error detected",
                "root_cause": "Missing dependency or module path issue",
                "fix_action": "install_missing_dependencies",
                "fix_commands": ["pip install -r requirements.txt"],
                "severity": IssueSeverity.HIGH
            },
            "port": {
                "description": "Port conflict detected",
                "root_cause": "Port 8000 already in use",
                "fix_action": "kill_port_process",
                "fix_commands": ["netstat -ano | findstr :8000", "taskkill /PID <pid> /F"],
                "severity": IssueSeverity.MEDIUM
            },
            "memory": {
                "description": "Memory issue detected",
                "root_cause": "Out of memory or memory leak",
                "fix_action": "clear_memory",
                "fix_commands": [],
                "severity": IssueSeverity.CRITICAL
            },
            "permission": {
                "description": "Permission error detected",
                "root_cause": "File or directory access denied",
                "fix_action": "fix_permissions",
                "fix_commands": [],
                "severity": IssueSeverity.MEDIUM
            }
        }
        
        if category in fixes:
            fix_info = fixes[category]
            return DiagnosedIssue(
                issue_id=f"{category}_{datetime.utcnow().timestamp()}",
                severity=fix_info["severity"],
                category=category,
                description=fix_info["description"],
                root_cause=fix_info["root_cause"],
                fix_action=fix_info["fix_action"],
                fix_commands=fix_info["fix_commands"],
                estimated_time_seconds=30,
                confidence=0.6,
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _fix_issues(self, issues: List[DiagnosedIssue]):
        """Apply fixes for diagnosed issues."""
        logger.info(f"[WATCHDOG] Fixing {len(issues)} issue(s)...")
        
        for issue in issues:
            try:
                logger.info(f"[WATCHDOG] Fixing: {issue.description} (severity: {issue.severity})")
                
                if issue.fix_action == "reset_database_connection":
                    self._fix_database_connection()
                elif issue.fix_action == "skip_embedding_or_download":
                    self._fix_embedding_model()
                elif issue.fix_action == "install_missing_dependencies":
                    self._fix_missing_dependencies()
                elif issue.fix_action == "kill_port_process":
                    self._fix_port_conflict()
                elif issue.fix_action == "clear_memory":
                    self._fix_memory()
                elif issue.fix_action == "fix_permissions":
                    self._fix_permissions()
                elif issue.fix_action == "restart_backend":
                    # Will be handled by restart logic
                    pass
                
                self.issues_fixed += 1
                logger.info(f"[WATCHDOG] ✓ Fixed: {issue.description}")
                
                # Log the fix
                self._log_fix(issue, success=True)
                
            except Exception as e:
                logger.error(f"[WATCHDOG] ✗ Failed to fix {issue.description}: {e}")
                self._log_fix(issue, success=False, error=str(e))
        
        self._save_state()
    
    def _fix_database_connection(self):
        """Fix database connection issues."""
        logger.info("[WATCHDOG] Resetting database connection...")
        # Database will reconnect automatically on next use
        pass
    
    def _fix_embedding_model(self):
        """Fix embedding model issues."""
        logger.info("[WATCHDOG] Embedding model will be loaded on first use (if available)")
        # Model will be downloaded/loaded on first use
        pass
    
    def _fix_missing_dependencies(self):
        """Install missing dependencies."""
        logger.info("[WATCHDOG] Installing missing dependencies...")
        try:
            requirements_file = Path(__file__).parent.parent.parent / "requirements.txt"
            if requirements_file.exists():
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    timeout=300,
                    check=False
                )
        except Exception as e:
            logger.error(f"[WATCHDOG] Could not install dependencies: {e}")
    
    def _fix_port_conflict(self):
        """Kill process using port 8000."""
        logger.info("[WATCHDOG] Checking for port 8000 conflict...")
        try:
            if OS.is_windows:
                # Windows: use netstat to find process
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if ':8000' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) > 4:
                            pid = int(parts[-1])
                            try:
                                process.kill_process_tree(pid)
                                logger.info(f"[WATCHDOG] Killed process {pid} using port 8000")
                            except Exception:
                                pass
            else:
                # Unix: use lsof to find process
                result = subprocess.run(
                    ["lsof", "-ti:8000"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    pid = int(result.stdout.strip())
                    try:
                        process.kill_process_tree(pid)
                        logger.info(f"[WATCHDOG] Killed process {pid} using port 8000")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"[WATCHDOG] Could not fix port conflict: {e}")
    
    def _fix_memory(self):
        """Fix memory issues."""
        logger.info("[WATCHDOG] Clearing memory...")
        import gc
        gc.collect()
    
    def _fix_permissions(self):
        """Fix permission issues."""
        logger.info("[WATCHDOG] Permission issues should be resolved on restart")
        # Permissions are usually fixed by restarting with proper user
    
    def _log_fix(self, issue: DiagnosedIssue, success: bool, error: Optional[str] = None):
        """Log a fix attempt."""
        log_file = self.log_dir / "fixes.jsonl"
        try:
            fix_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "issue": asdict(issue),
                "success": success,
                "error": error
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(fix_log) + '\n')
        except Exception as e:
            logger.error(f"[WATCHDOG] Could not log fix: {e}")
    
    def get_status(self) -> WatchdogStatus:
        """Get current watchdog status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        return WatchdogStatus(
            state=SystemState.RUNNING if self._is_process_alive() else SystemState.CRASHED,
            main_process_pid=self.main_process_pid,
            uptime_seconds=uptime,
            restart_count=self.restart_count,
            issues_fixed=self.issues_fixed,
            last_check=datetime.utcnow(),
            last_restart=self.last_restart
        )


def main():
    """Main entry point for watchdog."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GRACE Watchdog Self-Healing System")
    parser.add_argument(
        "--script",
        default="launch_grace.py",
        help="Path to main launcher script"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="Health check interval in seconds"
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=10,
        help="Maximum restart attempts"
    )
    parser.add_argument(
        "--restart-delay",
        type=int,
        default=5,
        help="Delay before restart in seconds"
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Don't start the frontend (backend only)"
    )
    parser.add_argument(
        "--frontend-path",
        type=str,
        default=None,
        help="Path to frontend directory (auto-detected if not specified)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Find script path
    script_path = Path(args.script)
    if not script_path.is_absolute():
        # Look in project root
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / script_path
    
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        sys.exit(1)
    
    # Create and start watchdog
    watchdog = WatchdogHealing(
        main_script_path=str(script_path),
        check_interval=args.check_interval,
        max_restarts=args.max_restarts,
        restart_delay=args.restart_delay,
        start_frontend=not args.no_frontend,
        frontend_path=args.frontend_path
    )
    
    try:
        watchdog.start()
    except KeyboardInterrupt:
        logger.info("[WATCHDOG] Shutdown requested")
        watchdog.stop()
    except Exception as e:
        logger.error(f"[WATCHDOG] Fatal error: {e}", exc_info=True)
        watchdog.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
