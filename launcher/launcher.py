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

from .version import VersionManager, VersionMismatchError
from .health_checker import HealthChecker, HealthCheckResult
from .folder_validator import FolderValidator
from .sqlite_logger import SQLiteLogHandler, LauncherLogCapture

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
        
        # Setup SQLite logging
        logs_dir = self.root_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        db_path = logs_dir / "launcher_log.db"
        self.log_capture = LauncherLogCapture(db_path=db_path)
        
        # Add SQLite handler to logger
        sqlite_handler = SQLiteLogHandler(db_path=db_path, genesis_key=self.log_capture.genesis_key)
        sqlite_handler.setLevel(logging.INFO)
        logger.addHandler(sqlite_handler)
        
        # Components
        self.version_manager = VersionManager()
        self.folder_validator = FolderValidator(self.root_path)
        self.health_checker = HealthChecker(
            backend_url=f"http://localhost:{backend_port}",
            timeout=5.0
        )
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Launcher initialized for: {self.root_path}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
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
        logger.info("Validating setup...")
        
        # Validate folders
        self.folder_validator.validate_all(strict=True)
        
        logger.info("✓ Setup validation passed")
        return True
    
    def start_backend(self) -> ProcessInfo:
        """
        Start backend process using existing start.bat script.
        
        Returns:
            ProcessInfo for the started process
            
        Raises:
            RuntimeError: If backend cannot be started
        """
        logger.info("Starting backend using start.bat...")
        
        # Check if start.bat exists
        start_bat = self.root_path / "start.bat"
        if not start_bat.exists():
            raise RuntimeError(
                f"start.bat not found at {start_bat}\n"
                f"Cannot start backend without startup script."
            )
        
        # Use existing start.bat / start.sh scripts - no duplication
        if sys.platform == "win32":
            # Call start.bat backend mode directly
            command = ["cmd", "/c", str(start_bat), "backend"]
            cwd_path = self.root_path
        else:
            # On Unix/Mac, use start.sh
            start_sh = self.root_path / "start.sh"
            if not start_sh.exists():
                raise RuntimeError(
                    f"start.sh not found at {start_sh}\n"
                    f"Cannot start backend without startup script."
                )
            command = ["bash", str(start_sh), "backend"]
            cwd_path = self.root_path
        
        # Prepare environment
        env = os.environ.copy()
        
        # Start process (using same logic as start.bat/start.sh, just in subprocess)
        try:
            process = subprocess.Popen(
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
                pid=process.pid,
                command=command,
                cwd=self.root_path,
                env=env
            )
            
            # Store process object for monitoring
            process_info.process = process  # type: ignore
            
            # Capture both stdout and stderr to SQLite and echo to console
            if process.stdout:
                self.log_capture.capture_stream(process.stdout, stream_name="backend-stdout", echo=True)
            if process.stderr:
                self.log_capture.capture_stream(process.stderr, stream_name="backend-stderr", echo=True)
            
            self.processes.append(process_info)
            
            logger.info(f"✓ Backend started via startup script (PID: {process.pid})")
            logger.info("Waiting for backend to initialize (this may take 30-120 seconds)...")
            logger.info("(Backend startup output will be shown below)")
            
            return process_info
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to start backend: {str(e)}\n"
                f"Command: {' '.join(command)}\n"
                f"CWD: {self.root_path}"
            )
    
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
        logger.info(f"Waiting for backend to become available (max {max_wait}s)...")
        
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
        
        while time.time() - start_time < max_wait:
            # Check if process is still alive
            if backend_process_info and hasattr(backend_process_info, 'process'):
                process = backend_process_info.process
                if process.poll() is not None:
                    # Process exited - get error output
                    try:
                        stdout, _ = process.communicate(timeout=1)
                        error_output = stdout[-2000:] if stdout else "No output captured"
                    except:
                        error_output = "Could not capture process output"
                    
                    raise RuntimeError(
                        f"Backend process died during startup (exit code: {process.returncode})\n"
                        f"Last output:\n{error_output}\n"
                        f"Check backend logs for detailed error messages."
                    )
            
            # First check if port is open (simpler check)
            port_open = is_port_open("localhost", self.backend_port)
            
            if port_open:
                # Port is open, now check health endpoint
                result = self.health_checker.check_backend_up()
                if result.status.value == "healthy":
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Backend is up and healthy (took {elapsed:.1f}s)")
                    return True
                else:
                    # Port is open but health check failing - backend is initializing
                    if time.time() - last_log_time >= 10:
                        elapsed = int(time.time() - start_time)
                        logger.info(f"Port {self.backend_port} is open, backend initializing... ({elapsed}s elapsed)")
                        last_log_time = time.time()
            else:
                # Port not open yet - backend still starting
                if time.time() - last_log_time >= 10:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"Waiting for backend to start listening on port {self.backend_port}... ({elapsed}s elapsed)")
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
                    # Use select or just try to read what's available
                    import select
                    if sys.platform != "win32" and select.select([process.stdout], [], [], 0)[0]:
                        # Unix: can do non-blocking read
                        chunk = process.stdout.read(1000)
                        if chunk:
                            recent_output = f"\n\nRecent backend output:\n{chunk[-500:]}"  # Last 500 chars
                except:
                    # Windows or no output available - that's ok
                    pass
                
                logger.warning(f"\n⚠ Backend process (PID: {process.pid}) is running but not responding yet.")
                logger.warning(f"   It may still be initializing (database, embeddings, file watchers, etc.)")
                logger.warning(f"   This can take 60-120+ seconds on first startup.")
                
                raise RuntimeError(
                    f"Backend did not become available within {max_wait}s\n"
                    f"Process is still running (PID: {process.pid}), but not responding.\n"
                    f"Last check: {result.message}\n"
                    f"\nBackend may still be initializing:\n"
                    f"  - Database setup (creating tables)\n"
                    f"  - Loading embeddings model\n"
                    f"  - Setting up file watchers\n"
                    f"  - Initializing Genesis trigger pipeline\n"
                    f"  - Starting healing/mirror systems\n"
                    f"\nTry:\n"
                    f"  1. Wait a bit longer and try again\n"
                    f"  2. Check backend logs in backend/logs/\n"
                    f"  3. Start backend manually to see detailed output:\n"
                    f"     cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000"
                    f"{recent_output}"
                )
        
        raise RuntimeError(
            f"Backend did not become available within {max_wait}s\n"
            f"Last check: {result.message}"
        )
    
    def perform_version_handshake(self) -> bool:
        """
        Perform version handshake with backend.
        
        Returns:
            True if handshake successful
            
        Raises:
            VersionMismatchError: If version mismatch detected
        """
        logger.info("Performing version handshake...")
        
        # Get backend version from /version endpoint
        try:
            try:
                import requests
            except ImportError:
                raise VersionMismatchError(
                    "requests library is required for version handshake.\n"
                    "Install it with: pip install requests"
                )
            
            response = requests.get(
                f"http://localhost:{self.backend_port}/version",
                timeout=5.0
            )
            
            if response.status_code != 200:
                raise VersionMismatchError(
                    f"Backend version endpoint returned {response.status_code}\n"
                    f"Cannot perform version handshake without version information."
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
            
            logger.info("✓ Version handshake successful")
            return True
            
        except requests.exceptions.ConnectionError:
            raise VersionMismatchError(
                "Cannot connect to backend version endpoint.\n"
                "Backend may not be running or not yet ready."
            )
        except Exception as e:
            if isinstance(e, VersionMismatchError):
                raise
            raise VersionMismatchError(
                f"Version handshake failed: {str(e)}"
            )
    
    def run_health_checks(self) -> bool:
        """
        Run strict health checks.
        
        Returns:
            True if all checks pass
            
        Raises:
            RuntimeError: If any health check fails
        """
        logger.info("Running strict health checks...")
        
        results = self.health_checker.run_all_checks(strict=True)
        
        # Log results
        for result in results:
            if result.status.value == "healthy":
                logger.info(f"✓ {result.component}: {result.message}")
            else:
                logger.error(f"❌ {result.component}: {result.message}")
        
        logger.info("✓ All health checks passed")
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
        logger.info("GRACE LAUNCHER")
        logger.info("=" * 60)
        logger.info("")
        
        try:
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
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ GRACE LAUNCHED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info("")
            logger.info(f"Backend API: http://localhost:{self.backend_port}")
            logger.info(f"API Docs: http://localhost:{self.backend_port}/docs")
            logger.info("")
            logger.info("Press Ctrl+C to shutdown")
            logger.info("")
            
            return True
            
        except Exception as e:
            logger.error("")
            logger.error("=" * 60)
            logger.error("❌ LAUNCH FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {str(e)}")
            logger.error("")
            logger.error("Shutting down started processes...")
            self.shutdown()
            raise
    
    def shutdown(self):
        """Shutdown all managed processes."""
        if not self.processes:
            return
        
        logger.info("Shutting down processes...")
        
        for process_info in self.processes:
            try:
                # Use subprocess methods for cross-platform compatibility
                if process_info.process:
                    # Try graceful shutdown first
                    process_info.process.terminate()
                    
                    # Wait up to 5 seconds for process to exit
                    for _ in range(5):
                        if process_info.process.poll() is not None:
                            # Process has exited
                            break
                        time.sleep(1)
                    
                    # Force kill if still running
                    if process_info.process.poll() is None:
                        process_info.process.kill()
                        # Give it a moment to die
                        time.sleep(0.5)
                    
                    logger.info(f"✓ Stopped {process_info.name} (PID: {process_info.pid})")
                else:
                    # Fallback: use os.kill if process object not available
                    if sys.platform != "win32":
                        # Unix: use signals
                        os.kill(process_info.pid, signal.SIGTERM)
                        # Wait up to 5 seconds
                        for _ in range(5):
                            try:
                                pid, _ = os.waitpid(process_info.pid, os.WNOHANG)
                                if pid == process_info.pid:
                                    break
                            except ChildProcessError:
                                break
                            time.sleep(1)
                        # Force kill if still running
                        try:
                            os.kill(process_info.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # Already dead
                    else:
                        # Windows: use taskkill
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(process_info.pid)],
                                capture_output=True,
                                timeout=5
                            )
                        except Exception:
                            pass  # Process may already be dead
                    
                    logger.info(f"✓ Stopped {process_info.name} (PID: {process_info.pid})")
                
            except ProcessLookupError:
                logger.warning(f"Process {process_info.name} (PID: {process_info.pid}) not found")
            except Exception as e:
                logger.error(f"Error stopping {process_info.name}: {e}")
        
        self.processes.clear()
        logger.info("✓ All processes stopped")
        
        # Close log capture
        if hasattr(self, 'log_capture'):
            self.log_capture.close()
    
    def run(self):
        """
        Run launcher and keep it alive.
        
        Monitors processes and shuts down gracefully on signal.
        """
        try:
            self.launch()
            
            # Keep launcher alive, monitoring processes
            while not self._shutdown_requested:
                # Check if backend process is still alive
                if self.processes:
                    backend_process = next(
                        (p for p in self.processes if p.name == "backend"),
                        None
                    )
                    if backend_process:
                        try:
                            # Check if process is still running
                            os.kill(backend_process.pid, 0)
                        except ProcessLookupError:
                            logger.error("Backend process died unexpectedly!")
                            break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.shutdown()


def main():
    """Main entry point."""
    # Determine root path (parent of launcher directory)
    launcher_dir = Path(__file__).parent
    root_path = launcher_dir.parent
    
    launcher = GraceLauncher(root_path=root_path)
    launcher.run()


if __name__ == "__main__":
    main()
