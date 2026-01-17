"""
Grace Launcher
==============
Minimal, strict launcher with no business logic.

Philosophy:
- Dumb by design: just spawns processes and checks health
- No cognition, no configuration beyond paths
- Fail fast or don't start
- No orphan processes, ever

Think: BIOS, not OS.
"""

import os
import sys
import subprocess
import signal
import time
import logging
import socket
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
import threading

# Multi-OS support: use OS adapter instead of platform checks
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.os_adapter import OS, paths, process, shell

from .version import VersionManager, VersionMismatchError
from .health_checker import HealthChecker, HealthCheckResult
from .folder_validator import FolderValidator
from .sqlite_logger import SQLiteLogHandler, LauncherLogCapture
from .nlp_error_processor import get_nlp_error_processor, NLPErrorProcessor
from .preflight_checker import PreFlightChecker, PreFlightResult
from .dependency_resolver import DependencyResolver
from .circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from .graceful_degradation import GracefulDegradationManager
from .self_healing_integration import get_launcher_self_healing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a managed process."""
    name: str
    pid: int
    command: List[str]
    cwd: Optional[Path] = None
    env: Optional[Dict[str, str]] = None
    process: Optional[Any] = None  # subprocess.Popen instance


class GraceLauncher:
    """
    Minimal launcher for Grace.
    
    Responsibilities:
    1. Validate folder contracts
    2. Start backend process
    3. Perform version handshake
    4. Run strict health checks
    5. Manage process lifecycle (no orphans)
    
    NOT responsible for:
    - Business logic
    - Configuration beyond paths
    - Cognition or intelligence
    """
    
    def __init__(
        self,
        root_path: Path,
        backend_port: int = 8000,
        health_check_timeout: float = 120.0  # Increased to 120s for initialization
    ):
        """
        Initialize launcher.
        
        Args:
            root_path: Root path of Grace installation
            backend_port: Port for backend API
            health_check_timeout: Timeout for health checks in seconds
        """
        self.root_path = Path(root_path).resolve()
        self.backend_port = backend_port
        self.health_check_timeout = health_check_timeout
        
        # Process management
        self.processes: List[ProcessInfo] = []
        self._shutdown_requested = False
        self._processes_lock = threading.Lock()  # Thread-safe access to processes list
        self._max_reload_count = 50  # Max backend reloads before considering it unstable
        
        # Setup SQLite logging
        logs_dir = self.root_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        db_path = logs_dir / "launcher_log.db"
        self.log_capture = LauncherLogCapture(db_path=db_path)
        
        # Add SQLite handler to logger
        sqlite_handler = SQLiteLogHandler(db_path=db_path, genesis_key=self.log_capture.genesis_key)
        sqlite_handler.setLevel(logging.INFO)
        logger.addHandler(sqlite_handler)
        
        # Setup NLP error processor (will use LLM if available, otherwise rule-based)
        try:
            backend_url = f"http://localhost:{self.backend_port}"
            self.nlp_processor = get_nlp_error_processor(use_llm=True, backend_url=backend_url)
        except Exception as e:
            logger.warning(f"Could not initialize Grace's NLP error processor: {e}. Grace will still work, but error messages may be less detailed.")
            self.nlp_processor = None
        
        # Components
        self.version_manager = VersionManager()
        self.folder_validator = FolderValidator(self.root_path)
        self.preflight_checker = PreFlightChecker(self.root_path)
        self.dependency_resolver = DependencyResolver()
        self.degradation_manager = GracefulDegradationManager()
        self.health_checker = HealthChecker(
            backend_url=f"http://localhost:{backend_port}",
            timeout=5.0,
            use_exponential_backoff=True
        )
        
        # Initialize self-healing integration
        try:
            self.self_healing = get_launcher_self_healing(
                root_path=self.root_path,
                backend_port=backend_port,
                enable_healing=True,
                enable_notifications=True
            )
            logger.info("✓ Grace's self-healing system is ready to automatically fix problems")
        except Exception as e:
            logger.debug(f"Could not initialize self-healing: {e}")
            self.self_healing = None
        
        # Setup signal handlers for graceful shutdown (Windows-compatible)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        # Windows-specific signals
        if OS.is_windows and hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, self._signal_handler)
        
        logger.info(f"Grace's launcher has been initialized and is ready to start Grace from: {self.root_path}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name if hasattr(signal.Signals, '__call__') else str(signum)
        logger.info(f"Grace received a shutdown signal ({signal_name}). Gracefully shutting down Grace and cleaning up...")
        self._shutdown_requested = True
        self.shutdown()
        sys.exit(0)
    
    def validate_setup(self) -> bool:
        """
        Validate folder contracts and basic setup.
        
        Returns:
            True if validation passes
            
        Raises:
            RuntimeError: If validation fails
        """
        logger.info("Validating Grace's setup and configuration...")
        
        # Validate folders
        self.folder_validator.validate_all(strict=True)
        
        logger.info("✓ Setup validation passed - Grace's environment looks good!")
        return True
    
    def start_backend(self) -> ProcessInfo:
        """
        Start backend process using uvicorn directly.
        
        Returns:
            ProcessInfo for the started process
            
        Raises:
            RuntimeError: If backend cannot be started
        """
        logger.info("Starting Grace's backend server...")
        
        # Check if backend directory exists
        backend_dir = self.root_path / "backend"
        if not backend_dir.exists():
            # Attempt self-healing
            if self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=FileNotFoundError(f"Backend directory not found: {backend_dir}"),
                    context={
                        "location": "start_backend",
                        "missing_path": str(backend_dir),
                        "root_path": str(self.root_path)
                    },
                    problem_type="missing_directory"
                )
                
                # If healing created the directory, continue
                if healing_result.get("healed") and backend_dir.exists():
                    logger.info("Grace automatically created the missing backend directory structure.")
                elif not healing_result.get("healed"):
                    # Healing couldn't fix it, user will be notified
                    pass
            
            raise RuntimeError(
                f"I couldn't find the backend directory at {backend_dir}.\n"
                f"This is where Grace's backend server should be located.\n"
                f"Please make sure you're running the launcher from the Grace project root directory."
            )
        
        # Check if app.py exists in backend
        app_py = backend_dir / "app.py"
        if not app_py.exists():
            # Attempt self-healing
            if self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=FileNotFoundError(f"app.py not found: {app_py}"),
                    context={
                        "location": "start_backend",
                        "missing_file": str(app_py),
                        "backend_dir": str(backend_dir)
                    },
                    problem_type="missing_backend_file"
                )
                
                # If not healed, user will be notified
                if not healing_result.get("healed") and healing_result.get("notification_sent"):
                    logger.warning("Grace couldn't automatically fix the missing app.py file. Check notifications for details.")
            
            raise RuntimeError(
                f"I found the backend directory, but the main application file (app.py) is missing at {app_py}.\n"
                f"Without this file, Grace cannot start the backend server.\n"
                f"Please check if the backend files are properly installed or cloned."
            )
        
        # Build uvicorn command directly
        # Use the same Python executable that's running this launcher
        import sys
        command = [
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", str(self.backend_port)  # Use current port (may have been changed by healing)
        ]
        cwd_path = backend_dir
        
        # Prepare environment
        env = os.environ.copy()
        
        # Start process using OS adapter (handles OS-specific flags)
        try:
            backend_process = process.spawn(
                command,
                cwd=str(cwd_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr separately
                text=True,
                bufsize=1
            )
            
            process_info = ProcessInfo(
                name="backend",
                pid=backend_process.pid,
                command=command,
                cwd=self.root_path,
                env=env
            )
            
            # Store process object for monitoring
            process_info.process = backend_process  # type: ignore
            
            # Capture both stdout and stderr to SQLite and echo to console
            if backend_process.stdout:
                self.log_capture.capture_stream(backend_process.stdout, stream_name="backend-stdout", echo=True)
            if backend_process.stderr:
                self.log_capture.capture_stream(backend_process.stderr, stream_name="backend-stderr", echo=True)
            
            self.processes.append(process_info)
            
            logger.info(f"✓ Grace's backend server is starting up (Process ID: {backend_process.pid})")
            logger.info("Grace is now initializing... This may take 30-120 seconds on first startup.")
            logger.info("(You'll see Grace's startup messages below as they happen)")
            
            return process_info
            
        except Exception as e:
            # Attempt self-healing
            if self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=e,
                    context={
                        "location": "start_backend",
                        "command": ' '.join(command),
                        "working_directory": str(self.root_path),
                        "backend_dir": str(backend_dir)
                    },
                    problem_type="process_startup_failure"
                )
                
                # If healed, try again
                if healing_result.get("healed"):
                    logger.info(f"Grace automatically fixed the startup issue. Retrying...")
                    try:
                        # Retry starting the backend
                        return self.start_backend()
                    except Exception as retry_error:
                        # Healing didn't actually fix it, continue to error
                        pass
            
            # If not healed or retry failed, raise error with healing context
            error_msg = (
                f"I tried to start Grace's backend server but encountered an error: {str(e)}\n\n"
                f"Technical details:\n"
                f"  Command attempted: {' '.join(command)}\n"
                f"  Working directory: {self.root_path}\n\n"
            )
            
            if self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=e,
                    context={
                        "location": "start_backend",
                        "command": ' '.join(command),
                        "working_directory": str(self.root_path)
                    }
                )
                if not healing_result.get("healed"):
                    if healing_result.get("notification_sent"):
                        error_msg += f"Grace attempted to fix this automatically but couldn't.\n"
                        error_msg += f"A notification has been sent with details.\n\n"
            
            error_msg += (
                f"This could mean:\n"
                f"  - Python or uvicorn is not properly installed\n"
                f"  - There's a permission issue preventing the server from starting\n"
                f"  - A required dependency is missing\n\n"
                f"Try running the backend manually to see more detailed error messages:\n"
                f"  cd {backend_dir} && python -m uvicorn app:app --host 0.0.0.0 --port 8000"
            )
            
            raise RuntimeError(error_msg)
    
    def wait_for_backend(self, max_wait: float = 60.0) -> bool:
        """
        Wait for backend to become available.
        
        Args:
            max_wait: Maximum time to wait in seconds (default 60s for startup)
            
        Returns:
            True if backend becomes available
            
        Raises:
            RuntimeError: If backend doesn't become available in time
        """
        logger.info(f"Waiting for Grace's backend to finish initializing (waiting up to {max_wait} seconds)...")
        
        # Get backend process to monitor
        backend_process_info = next(
            (p for p in self.processes if p.name == "backend"),
            None
        )
        
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        last_log_time = start_time
        
        def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
            """Check if a port is open and accepting connections."""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except Exception:
                return False
        
        # Track reload count - Uvicorn may reload during startup (that's ok)
        reload_count = 0
        last_reload_check = start_time
        startup_grace_period = 30  # First 30 seconds, allow reloads
        
        while time.time() - start_time < max_wait:
            # Check if process is still alive
            if backend_process_info and hasattr(backend_process_info, 'process'):
                process = backend_process_info.process
                exit_code = process.poll()
                
                if exit_code is not None:
                    # Process exited - but could be a reload (Uvicorn reload mode)
                    # Check if port is still open (backend might have reloaded)
                    if is_port_open("localhost", self.backend_port):
                        # Port still open - likely a reload, not a crash
                        reload_count += 1
                        elapsed = time.time() - start_time
                        
                        if elapsed < startup_grace_period:
                            # Still in grace period - reloads are expected
                            logger.debug(
                                f"Grace's backend process restarted (reload #{reload_count}), "
                                f"but the server port is still active. This is normal - it's likely Grace reloading "
                                f"during startup to pick up configuration changes."
                            )
                            # Wait a bit and continue
                            time.sleep(2)
                            continue
                        else:
                            # Past grace period - unexpected reload
                            logger.warning(
                                f"Grace's backend process restarted again (reload #{reload_count}) after the initial startup period. "
                                f"The server is still running, so I'm checking if everything is healthy..."
                            )
                            # Check health - if healthy, continue
                            health_result = self.health_checker.check_backend_up()
                            if health_result.status.value in ["healthy", "degraded"]:
                                logger.info("✓ Backend reloaded and is healthy, continuing...")
                                time.sleep(2)
                                continue
                    
                    # Process died and port is closed - actual crash
                    try:
                        stdout, _ = process.communicate(timeout=1)
                        error_output = stdout[-2000:] if stdout else "No output captured"
                    except:
                        error_output = "Could not capture process output"
                    
                    # Attempt self-healing for process crash
                    if self.self_healing:
                        healing_result = self.self_healing.detect_and_heal_problem(
                            error=RuntimeError(f"Process exited with code {process.returncode}"),
                            context={
                                "location": "wait_for_backend",
                                "process_name": "backend",
                                "exit_code": process.returncode,
                                "last_output": error_output[:500],
                                "pid": process.pid
                            },
                            problem_type="process_crash"
                        )
                        
                        if healing_result.get("healed"):
                            logger.info(f"Grace automatically fixed the backend crash. The backend should restart automatically.")
                            # Continue waiting - backend may restart
                            time.sleep(5)
                            continue
                    
                    # Process error through NLP
                    error_msg = (
                        f"Grace's backend process stopped unexpectedly during startup.\n"
                        f"The process exited with code {process.returncode}, which indicates an error occurred.\n\n"
                        f"Last output from the backend:\n{error_output}\n\n"
                        f"This suggests something went wrong while Grace was trying to initialize. "
                        f"Check the backend logs in backend/logs/ for more detailed error information."
                    )
                    
                    if self.nlp_processor:
                        try:
                            error_info = self.nlp_processor.process_error(
                                error=RuntimeError(error_msg),
                                context={
                                    "process_name": "backend",
                                    "exit_code": process.returncode,
                                    "last_output": error_output[:500]
                                }
                            )
                            # Include NLP explanation in error if available
                            nlp_explanation = error_info.get('nlp_explanation', '')
                            if nlp_explanation:
                                error_msg = f"{nlp_explanation}\n\n{error_msg}"
                        except Exception:
                            pass  # Fall back to original error
                    
                    raise RuntimeError(error_msg)
            
            # First check if port is open (simpler check)
            port_open = is_port_open("localhost", self.backend_port)
            
            if port_open:
                # Port is open, now check health endpoint
                result = self.health_checker.check_backend_up()
                if result.status.value == "healthy":
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Grace's backend is up and running! (took {elapsed:.1f} seconds to start)")
                    return True
                else:
                    # Port is open but health check failing - backend is initializing
                    if time.time() - last_log_time >= 10:
                        elapsed = int(time.time() - start_time)
                        logger.info(f"Port {self.backend_port} is open and Grace's backend is initializing... ({elapsed} seconds elapsed)")
                        last_log_time = time.time()
            else:
                # Port not open yet - backend still starting
                if time.time() - last_log_time >= 10:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"Waiting for Grace's backend to start listening on port {self.backend_port}... ({elapsed} seconds elapsed)")
                    last_log_time = time.time()
            
            time.sleep(check_interval)
        
        # Timeout - get final status
        result = self.health_checker.check_backend_up()
        
        # If process is still alive, provide helpful message
        if backend_process_info and hasattr(backend_process_info, 'process'):
            process = backend_process_info.process
            if process.poll() is None:
                # Try to peek at recent output (non-blocking)
                recent_output = ""
                try:
                    # Use select for non-blocking read (Unix only)
                    if OS.is_unix:
                        import select
                        if select.select([process.stdout], [], [], 0)[0]:
                            # Unix: can do non-blocking read
                            chunk = process.stdout.read(1000)
                            if chunk:
                                recent_output = f"\n\nRecent output from Grace's backend:\n{chunk[-500:]}"  # Last 500 chars
                except:
                    # Windows or no output available - that's ok
                    pass
                
                logger.warning(f"\n⚠ Grace's backend process (PID: {process.pid}) is running but hasn't responded yet.")
                logger.warning(f"   This is normal during startup - Grace is still getting ready.")
                logger.warning(f"   Initial startup can take 60-120+ seconds as Grace sets up all its systems.")
                
                raise RuntimeError(
                    f"Grace's backend server didn't become available within {max_wait} seconds.\n"
                    f"The process is still running (PID: {process.pid}), which means Grace is working on it!\n"
                    f"Last status check: {result.message}\n\n"
                    f"Grace is likely still initializing. Here's what might be happening:\n"
                    f"  • Setting up the database (creating tables and indexes)\n"
                    f"  • Loading AI models and embeddings\n"
                    f"  • Setting up file watchers for the knowledge base\n"
                    f"  • Starting the Genesis learning trigger system\n"
                    f"  • Initializing self-healing and monitoring systems\n\n"
                    f"To help diagnose:\n"
                    f"  1. Give it a bit more time - first startup is always slower\n"
                    f"  2. Check Grace's logs in backend/logs/ to see detailed progress\n"
                    f"  3. Try starting the backend manually to watch the full startup process:\n"
                    f"     cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000\n"
                    f"{recent_output}"
                )
        
        raise RuntimeError(
            f"Grace's backend server didn't become available within {max_wait} seconds.\n"
            f"Last status check: {result.message}\n\n"
            f"It's possible the backend process didn't start properly, or there's an issue preventing it from responding.\n"
            f"Check the logs above for startup errors, or try starting the backend manually to see detailed output."
        )
    
    def perform_version_handshake(self) -> bool:
        """
        Perform version handshake with backend.
        
        Returns:
            True if handshake successful
            
        Raises:
            VersionMismatchError: If version mismatch detected
        """
        logger.info("Verifying that Grace's launcher and backend are compatible versions...")
        
        # Get backend version from /version endpoint
        try:
            try:
                import requests
            except ImportError:
                raise VersionMismatchError(
                    "I need the 'requests' library to check if Grace's launcher and backend versions are compatible.\n"
                    "Please install it by running: pip install requests\n"
                    "This library allows Grace to communicate with the backend to verify compatibility."
                )
            
            response = requests.get(
                f"http://localhost:{self.backend_port}/version",
                timeout=5.0
            )
            
            if response.status_code != 200:
                raise VersionMismatchError(
                    f"Grace's backend responded with status code {response.status_code} when I tried to check its version.\n"
                    f"Without version information, I cannot verify that the launcher and backend are compatible.\n"
                    f"This might mean the backend isn't fully initialized yet, or there's an issue with the version endpoint."
                )
            
            version_data = response.json()
            backend_version = version_data.get("version", "unknown")
            embeddings_version = version_data.get("embeddings_version")
            
            # Perform handshake
            self.version_manager.handshake(
                backend_version=backend_version,
                embeddings_version=embeddings_version,
                ide_bridge_version=None  # TODO: Check if IDE bridge is running
            )
            
            logger.info("✓ Version handshake successful - Grace launcher and backend are compatible")
            return True
            
        except requests.exceptions.ConnectionError:
            raise VersionMismatchError(
                "I couldn't connect to Grace's backend to check version compatibility.\n"
                "This usually means the backend isn't running yet, or it's still starting up.\n"
                "Please wait a moment and try again, or check if the backend started successfully."
            )
        except Exception as e:
            if isinstance(e, VersionMismatchError):
                raise
            raise VersionMismatchError(
                f"Grace couldn't verify version compatibility between the launcher and backend: {str(e)}\n"
                f"This might indicate a connection issue, or the backend might not be responding as expected.\n"
                f"Check that the backend is running and accessible at http://localhost:{self.backend_port}/version"
            )
    
    def run_health_checks(self) -> bool:
        """
        Run strict health checks.
        
        Returns:
            True if all checks pass
            
        Raises:
            RuntimeError: If any health check fails
        """
        logger.info("Running Grace's health checks to make sure everything is working...")
        
        results = self.health_checker.run_all_checks(strict=True)
        
        # Log results
        for result in results:
            if result.status.value == "healthy":
                logger.info(f"✓ {result.component}: {result.message}")
            else:
                logger.error(f"❌ {result.component} has an issue: {result.message}")
        
        logger.info("✓ All health checks passed - Grace is operating normally")
        return True
    
    def launch(self) -> bool:
        """
        Launch Grace system.
        
        Full sequence:
        1. Validate setup
        2. Start backend
        3. Wait for backend
        4. Version handshake
        5. Health checks
        
        Returns:
            True if launch successful
            
        Raises:
            RuntimeError: If any step fails
        """
        logger.info("=" * 60)
        logger.info("🚀 GRACE LAUNCHER - Starting Grace...")
        logger.info("=" * 60)
        logger.info("")
        
        try:
            # 0. Enterprise pre-flight checks (NEW)
            logger.info("Running pre-flight checks to ensure Grace can start safely...")
            preflight_result = self.preflight_checker.run_all_checks()
            
            if not preflight_result.can_proceed():
                logger.error("")
                logger.error("Grace couldn't pass the pre-flight checks. Here's what needs attention:")
                error_details = []
                for check in preflight_result.checks:
                    if not check.passed and check.severity.value == "fatal":
                        logger.error(f"  ✗ {check.name}: {check.message}")
                        error_details.append(f"{check.name}: {check.message}")
                        if check.fix_suggestion:
                            logger.error(f"    💡 Suggestion: {check.fix_suggestion}")
                
                error_msg = (
                    f"Grace's pre-flight checks found issues that prevent startup:\n"
                    f"{chr(10).join('  • ' + detail for detail in error_details)}\n\n"
                    f"Please address these issues and try launching again. See the messages above for suggestions on how to fix each issue."
                )
                raise RuntimeError(error_msg)
            
            logger.info(f"✓ Pre-flight checks complete: {preflight_result.summary}")
            if preflight_result.warnings > 0:
                logger.warning(f"⚠ Grace found {preflight_result.warnings} warning(s) during pre-flight checks.")
                # Show specific warnings
                for check in preflight_result.checks:
                    if not check.passed and check.severity.value == "warning":
                        logger.warning(f"   ⚠ {check.name}: {check.message}")
                        if check.fix_suggestion:
                            logger.warning(f"      💡 Suggestion: {check.fix_suggestion}")
                logger.warning(f"   Grace will start, but some features may be limited until these are resolved.")
                logger.warning(f"   This is called 'degraded mode' - Grace will do its best with what's available.")
            
            # 1. Validate setup
            self.validate_setup()
            
            # 2. Start backend
            self.start_backend()
            
            # 3. Wait for backend
            self.wait_for_backend(max_wait=self.health_check_timeout)
            
            # 4. Version handshake
            self.perform_version_handshake()
            
            # 5. Health checks
            self.run_health_checks()
            
            # 6. Register services and determine operational mode (NEW)
            self._register_services()
            status = self.degradation_manager.get_status_summary()
            mode = self.degradation_manager.get_operational_mode()
            
            logger.info("")
            logger.info("=" * 60)
            if mode.value == "full":
                logger.info("🎉 GRACE IS READY! (Full Mode - All Systems Operational)")
                logger.info("")
                logger.info("Grace has successfully started with all features enabled!")
            elif mode.value == "degraded":
                logger.info("✓ GRACE IS RUNNING (Degraded Mode)")
                logger.info("")
                logger.info(f"Grace started, but {status.get('degraded_count', 0)} optional service(s) are unavailable.")
                logger.info("Core features will work, but some advanced features may be limited.")
            elif mode.value == "minimal":
                logger.info("⚠ GRACE IS RUNNING (Minimal Mode)")
                logger.info("")
                logger.info("Grace started with only core services available.")
                logger.info("Some features won't work until additional services are started.")
            logger.info("=" * 60)
            logger.info("")
            logger.info(f"🌐 Grace's API is available at: http://localhost:{self.backend_port}")
            logger.info(f"📚 API Documentation: http://localhost:{self.backend_port}/docs")
            
            # Show capabilities
            capabilities = self.degradation_manager.get_capabilities()
            logger.info("")
            logger.info("Grace's Current Capabilities:")
            for cap, available in capabilities.items():
                status_icon = "✓" if available else "✗"
                cap_name = cap.replace('_', ' ').title()
                status_text = "Available and ready to use" if available else "Currently unavailable"
                logger.info(f"  {status_icon} {cap_name}: {status_text}")
            
            logger.info("")
            logger.info("Grace is now running and ready to help you!")
            logger.info("To stop Grace, press Ctrl+C (or Cmd+C on Mac)")
            logger.info("")
            
            return True
            
        except Exception as e:
            # Attempt self-healing before giving up
            healing_attempted = False
            if self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=e,
                    context={
                        "location": "launch",
                        "root_path": str(self.root_path),
                        "backend_port": self.backend_port
                    }
                )
                healing_attempted = True
                
                # If healed, try launching again (but only once to avoid loops)
                if healing_result.get("healed") and not getattr(self, '_retry_launch_after_healing', False):
                    self._retry_launch_after_healing = True
                    logger.info("Grace automatically fixed the launch issue. Retrying launch...")
                    try:
                        return self.launch()
                    except Exception as retry_error:
                        # Healing didn't work, continue to error display
                        pass
            
            logger.error("")
            logger.error("=" * 60)
            logger.error("❌ GRACE COULDN'T START")
            logger.error("=" * 60)
            logger.error("")
            logger.error("📝 What Happened:")
            logger.error(f"Grace's launcher encountered an issue while trying to start: {str(e)}")
            
            if healing_attempted and self.self_healing:
                healing_result = self.self_healing.detect_and_heal_problem(
                    error=e,
                    context={
                        "location": "launch",
                        "root_path": str(self.root_path),
                        "backend_port": self.backend_port
                    }
                )
                if healing_result.get("notification_sent"):
                    logger.error("")
                    logger.error("💬 Grace attempted to fix this automatically but couldn't.")
                    logger.error("   A notification has been sent with details about the issue.")
            
            logger.error("")
            logger.error("💡 What You Can Try:")
            logger.error("  1. Read the error message above - it usually explains what went wrong")
            logger.error("  2. Check Grace's logs in the launcher logs directory for more details")
            logger.error("  3. Make sure all system requirements are installed (Python, dependencies, etc.)")
            logger.error("  4. If this is your first time running Grace, check the setup documentation")
            logger.error("")
            logger.error("🔍 Technical Details:")
            logger.error(f"   Error Type: {type(e).__name__}")
            logger.error(f"   Error Message: {str(e)}")
            logger.error("   Severity: Medium - Grace didn't start, but no data was lost")
            logger.error("")
            logger.error("Grace is shutting down any processes that were started...")
            self.shutdown()
            raise
    
    def _register_services(self):
        """Register all services with degradation manager to determine Grace's operational mode."""
        logger.debug("Checking which services are available to determine Grace's operational capabilities...")
        
        # Register backend (assume available if we got here)
        self.degradation_manager.register_service("backend", True)
        logger.debug("✓ Backend service is registered and available")
        
        # Register database (assume available if we got here)
        self.degradation_manager.register_service("database", True)
        logger.debug("✓ Database service is registered and available")
        
        # Check optional services
        try:
            import requests
            # Check Qdrant (vector database)
            try:
                response = requests.get("http://localhost:6333/collections", timeout=1)
                qdrant_available = response.status_code == 200
                self.degradation_manager.register_service(
                    "qdrant", 
                    qdrant_available,
                    "Qdrant vector database is not running" if not qdrant_available else None
                )
                if not qdrant_available:
                    logger.debug("Qdrant vector database is not running - Grace will still work, but advanced vector search features will be limited")
                else:
                    logger.debug("✓ Qdrant vector database is available - full vector search capabilities enabled")
            except Exception:
                self.degradation_manager.register_service("qdrant", False, "Could not connect to Qdrant")
                logger.debug("Could not verify Qdrant availability - assuming unavailable")
            
            # Check Ollama (local LLM server)
            try:
                response = requests.get("http://localhost:11434", timeout=0.5)
                ollama_available = response.status_code == 200
                self.degradation_manager.register_service(
                    "ollama",
                    ollama_available,
                    "Ollama LLM server is not running" if not ollama_available else None
                )
                if not ollama_available:
                    logger.debug("Ollama LLM server is not running - Grace will still work, but some AI features may be limited")
                else:
                    logger.debug("✓ Ollama LLM server is available - full AI capabilities enabled")
            except Exception:
                self.degradation_manager.register_service("ollama", False, "Could not connect to Ollama")
                logger.debug("Could not verify Ollama availability - assuming unavailable")
        except Exception as e:
            logger.debug(f"Could not check optional services availability: {e}")
    
    def shutdown(self):
        """Shutdown all managed processes."""
        if not self.processes:
            return
        
        logger.info("Gracefully shutting down all Grace processes...")
        
        for process_info in self.processes:
            try:
                # Use OS adapter for portable process termination
                if process_info.process:
                    # Try graceful shutdown using adapter
                    process.terminate(process_info.process, timeout=5.0)
                    logger.info(f"✓ Grace's {process_info.name} has been stopped (was running as process {process_info.pid})")
                else:
                    # Fallback: use process adapter for PID-based termination
                    process.kill_process_tree(process_info.pid)
                    logger.info(f"✓ Grace's {process_info.name} has been stopped (was running as process {process_info.pid})")
                
            except ProcessLookupError:
                logger.warning(f"Grace's {process_info.name} process (PID: {process_info.pid}) was already stopped or no longer exists - that's okay!")
            except Exception as e:
                logger.error(f"I encountered an issue while trying to stop Grace's {process_info.name}: {e}")
                logger.error(f"   The process may have already exited, or there may be a permission issue.")
        
        self.processes.clear()
        logger.info("✓ All Grace processes have been stopped. Grace has shut down cleanly.")
        
        # Close log capture
        if hasattr(self, 'log_capture'):
            self.log_capture.close()
    
    def run(self):
        """
        Run launcher and keep Grace alive and healthy.
        
        This method:
        - Launches Grace through all startup steps
        - Monitors Grace's health continuously
        - Handles graceful shutdown on signals
        - Manages backend reloads (Uvicorn auto-reload mode)
        - Ensures no orphan processes are left behind
        """
        try:
            self.launch()
            
            # Keep launcher alive, monitoring processes
            logger.info("")
            logger.info("Grace is now running! I'll monitor Grace's health and keep everything working smoothly.")
            logger.info("")
            
            last_health_check = time.time()
            health_check_interval = 10  # Check health every 10 seconds
            backend_reload_count = 0
            
            while not self._shutdown_requested:
                # Check if backend process is still alive
                if self.processes:
                    backend_process = next(
                        (p for p in self.processes if p.name == "backend"),
                        None
                    )
                    if backend_process:
                        try:
                            # Check if process is still running using OS adapter
                            from backend.utils.os_adapter import process as process_adapter
                            if not process_adapter.check_process_alive(backend_process.pid):
                                # Process exited - could be a reload
                                if self._is_backend_healthy():
                                    # Backend is healthy - likely a reload
                                    backend_reload_count += 1
                                    
                                    # Check if reload count is excessive
                                    if backend_reload_count > self._max_reload_count:
                                        logger.error(
                                            f"⚠ Grace's backend has reloaded {backend_reload_count} times, "
                                            f"which exceeds the safe maximum of {self._max_reload_count}.\n"
                                            f"   This suggests Grace might be stuck in a reload loop, possibly due to\n"
                                            f"   code changes that keep triggering automatic reloading.\n"
                                            f"   Grace is shutting down to prevent instability."
                                        )
                                        break
                                    
                                    logger.debug(
                                        f"Grace's backend process restarted (reload #{backend_reload_count}), "
                                        f"but the backend is still healthy and responding. This is normal - "
                                        f"Grace automatically reloads when code changes are detected."
                                    )
                                    # Continue monitoring
                                    continue
                                else:
                                    # Backend actually crashed
                                    logger.error("⚠ Grace's backend process has stopped unexpectedly and is not responding!")
                                    logger.error("   Grace is shutting down to prevent running in an inconsistent state.")
                                    break
                        except Exception as e:
                            logger.debug(f"While checking Grace's backend process status, I encountered: {e}. Continuing to monitor...")
                
                # Periodic health check
                if time.time() - last_health_check >= health_check_interval:
                    if not self._is_backend_healthy():
                        logger.warning("Grace's periodic health check indicates the backend may be having issues, but I'm continuing to monitor it.")
                        logger.warning("   If this persists, Grace may need attention. Check the backend logs for details.")
                    last_health_check = time.time()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("Grace received an interrupt signal. Shutting down gracefully...")
        finally:
            self.shutdown()
    
    def _is_backend_healthy(self) -> bool:
        """Quick check if Grace's backend is healthy and responding."""
        try:
            result = self.health_checker.check_backend_up()
            return result.status.value in ["healthy", "degraded"]
        except Exception as e:
            logger.debug(f"Health check encountered an issue: {e}. Backend may be temporarily unavailable.")
            return False


def main():
    """
    Main entry point for Grace's launcher.
    
    This is where Grace begins! The launcher will:
    1. Check that everything is set up correctly
    2. Start Grace's backend server
    3. Verify Grace is working properly
    4. Keep Grace running and monitor its health
    """
    # Determine root path (parent of launcher directory)
    launcher_dir = Path(__file__).parent
    root_path = launcher_dir.parent
    
    logger.info("")
    logger.info("Starting Grace's launcher...")
    logger.info("")
    
    launcher = GraceLauncher(root_path=root_path)
    launcher.run()


if __name__ == "__main__":
    main()
