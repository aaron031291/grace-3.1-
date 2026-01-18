"""
Grace Service Manager
======================
Manages all Grace dependencies and services.

Starts and monitors:
- Qdrant (vector database)
- Frontend (web UI)
- Backend (already handled by launcher)
- Ollama (optional, if available)
"""

import os
import sys
import subprocess
import time
import socket
import logging
import threading
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.utils.os_adapter import OS, paths, process

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    name: str
    port: int
    start_command: List[str]
    working_dir: Optional[Path] = None
    health_endpoint: Optional[str] = None
    required: bool = False
    auto_start: bool = True
    startup_timeout: float = 60.0
    env: Optional[Dict[str, str]] = None


@dataclass
class ServiceState:
    """Current state of a service."""
    config: ServiceConfig
    status: ServiceStatus = ServiceStatus.STOPPED
    process: Optional[Any] = None
    pid: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[float] = None


class GraceServiceManager:
    """
    Manages all Grace services and dependencies.
    
    Services managed:
    - qdrant: Vector database for RAG
    - frontend: Web UI
    - ollama: Local LLM (optional)
    """
    
    def __init__(self, root_path: Path, backend_port: int = 8000):
        """Initialize service manager."""
        self.root_path = Path(root_path).resolve()
        self.backend_port = backend_port
        self.services: Dict[str, ServiceState] = {}
        self._shutdown_requested = False
        self._lock = threading.Lock()
        
        # Initialize service configurations
        self._init_services()
        
        logger.info("Grace Service Manager initialized")
    
    def _init_services(self):
        """Initialize service configurations."""
        # Qdrant - Vector Database
        qdrant_cmd = self._get_qdrant_command()
        if qdrant_cmd:
            self.services["qdrant"] = ServiceState(
                config=ServiceConfig(
                    name="qdrant",
                    port=6333,
                    start_command=qdrant_cmd,
                    health_endpoint="http://localhost:6333/health",
                    required=False,  # Grace can run without vector search
                    auto_start=True,
                    startup_timeout=30.0,
                )
            )
        
        # Frontend - Web UI
        frontend_dir = self.root_path / "frontend"
        if frontend_dir.exists() and (frontend_dir / "package.json").exists():
            npm_cmd = "npm.cmd" if OS.is_windows else "npm"
            self.services["frontend"] = ServiceState(
                config=ServiceConfig(
                    name="frontend",
                    port=5173,
                    start_command=[npm_cmd, "run", "dev"],
                    working_dir=frontend_dir,
                    required=False,
                    auto_start=True,
                    startup_timeout=60.0,
                )
            )
        
        # Ollama - Local LLM (optional)
        ollama_path = self._find_ollama()
        if ollama_path:
            self.services["ollama"] = ServiceState(
                config=ServiceConfig(
                    name="ollama",
                    port=11434,
                    start_command=[ollama_path, "serve"],
                    health_endpoint="http://localhost:11434/api/tags",
                    required=False,
                    auto_start=False,  # Don't auto-start Ollama by default
                    startup_timeout=30.0,
                )
            )
    
    def _get_qdrant_command(self) -> Optional[List[str]]:
        """Get command to start Qdrant."""
        # Check for Docker
        docker_path = shutil.which("docker")
        if docker_path:
            return [
                docker_path, "run", "-d",
                "--name", "grace-qdrant",
                "-p", "6333:6333",
                "-p", "6334:6334",
                "-v", f"{self.root_path / 'data' / 'qdrant'}:/qdrant/storage",
                "qdrant/qdrant:latest"
            ]
        
        # Check for local Qdrant binary
        qdrant_binary = shutil.which("qdrant")
        if qdrant_binary:
            return [qdrant_binary]
        
        # Check in common locations
        if OS.is_windows:
            common_paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "qdrant" / "qdrant.exe",
                Path("C:/Program Files/qdrant/qdrant.exe"),
                self.root_path / "tools" / "qdrant" / "qdrant.exe",
            ]
        else:
            common_paths = [
                Path("/usr/local/bin/qdrant"),
                Path.home() / ".local/bin/qdrant",
                self.root_path / "tools" / "qdrant" / "qdrant",
            ]
        
        for path in common_paths:
            if path.exists():
                return [str(path)]
        
        return None
    
    def _find_ollama(self) -> Optional[str]:
        """Find Ollama binary."""
        ollama_path = shutil.which("ollama")
        if ollama_path:
            return ollama_path
        
        if OS.is_windows:
            common_paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path("C:/Program Files/Ollama/ollama.exe"),
            ]
        else:
            common_paths = [
                Path("/usr/local/bin/ollama"),
                Path.home() / ".local/bin/ollama",
            ]
        
        for path in common_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    def _check_docker_container(self, name: str) -> bool:
        """Check if a Docker container is running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={name}"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def _start_docker_container(self, service: ServiceState) -> bool:
        """Start a Docker container."""
        config = service.config
        
        # Check if container already exists (stopped)
        try:
            result = subprocess.run(
                ["docker", "ps", "-aq", "-f", f"name=grace-{config.name}"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            if result.stdout.strip():
                # Container exists, try to start it
                subprocess.run(
                    ["docker", "start", f"grace-{config.name}"],
                    capture_output=True,
                    timeout=10.0
                )
                logger.info(f"Started existing Docker container: grace-{config.name}")
                return True
        except Exception:
            pass
        
        # Create and start new container
        try:
            result = subprocess.run(
                config.start_command,
                capture_output=True,
                text=True,
                timeout=60.0
            )
            if result.returncode == 0:
                logger.info(f"Created Docker container: grace-{config.name}")
                return True
            else:
                logger.error(f"Failed to create container: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Docker error: {e}")
            return False
    
    def start_service(self, name: str) -> bool:
        """Start a single service."""
        if name not in self.services:
            logger.warning(f"Unknown service: {name}")
            return False
        
        service = self.services[name]
        config = service.config
        
        # Check if already running
        if self._is_port_in_use(config.port):
            logger.info(f"✓ {config.name} already running on port {config.port}")
            service.status = ServiceStatus.RUNNING
            return True
        
        logger.info(f"Starting {config.name}...")
        service.status = ServiceStatus.STARTING
        
        try:
            # Handle Docker-based services
            if config.start_command and config.start_command[0].endswith("docker"):
                if self._start_docker_container(service):
                    service.status = ServiceStatus.RUNNING
                    service.started_at = time.time()
                    return self._wait_for_service(service)
                else:
                    service.status = ServiceStatus.FAILED
                    return False
            
            # Handle regular process services
            env = os.environ.copy()
            if config.env:
                env.update(config.env)
            
            proc = process.spawn(
                config.start_command,
                cwd=str(config.working_dir) if config.working_dir else None,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            service.process = proc
            service.pid = proc.pid
            service.started_at = time.time()
            
            # Wait for service to be ready
            if self._wait_for_service(service):
                service.status = ServiceStatus.RUNNING
                logger.info(f"✓ {config.name} started on port {config.port}")
                return True
            else:
                service.status = ServiceStatus.FAILED
                return False
                
        except Exception as e:
            logger.error(f"Failed to start {config.name}: {e}")
            service.status = ServiceStatus.FAILED
            service.error_message = str(e)
            return False
    
    def _wait_for_service(self, service: ServiceState, timeout: Optional[float] = None) -> bool:
        """Wait for a service to become available."""
        config = service.config
        timeout = timeout or config.startup_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._is_port_in_use(config.port):
                # Port is open, check health endpoint if available
                if config.health_endpoint:
                    try:
                        import requests
                        response = requests.get(config.health_endpoint, timeout=2.0)
                        if response.status_code == 200:
                            return True
                    except Exception:
                        pass
                else:
                    return True
            
            time.sleep(1.0)
        
        return False
    
    def stop_service(self, name: str) -> bool:
        """Stop a single service."""
        if name not in self.services:
            return False
        
        service = self.services[name]
        config = service.config
        
        logger.info(f"Stopping {config.name}...")
        
        # Handle Docker containers
        if config.start_command and config.start_command[0].endswith("docker"):
            try:
                subprocess.run(
                    ["docker", "stop", f"grace-{config.name}"],
                    capture_output=True,
                    timeout=30.0
                )
                service.status = ServiceStatus.STOPPED
                return True
            except Exception as e:
                logger.error(f"Failed to stop Docker container: {e}")
                return False
        
        # Handle regular processes
        if service.process:
            try:
                service.process.terminate()
                service.process.wait(timeout=10.0)
                service.status = ServiceStatus.STOPPED
                return True
            except subprocess.TimeoutExpired:
                service.process.kill()
                service.status = ServiceStatus.STOPPED
                return True
            except Exception as e:
                logger.error(f"Failed to stop process: {e}")
                return False
        
        return False
    
    def start_all(self, include_optional: bool = False) -> Dict[str, bool]:
        """Start all configured services."""
        results = {}
        
        for name, service in self.services.items():
            if not service.config.auto_start and not include_optional:
                logger.info(f"Skipping optional service: {name}")
                results[name] = None  # Skipped
                continue
            
            results[name] = self.start_service(name)
        
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """Stop all running services."""
        self._shutdown_requested = True
        results = {}
        
        for name in self.services:
            results[name] = self.stop_service(name)
        
        return results
    
    def get_status(self) -> Dict[str, Dict]:
        """Get status of all services."""
        status = {}
        
        for name, service in self.services.items():
            # Update status by checking port
            if self._is_port_in_use(service.config.port):
                if service.status not in [ServiceStatus.RUNNING, ServiceStatus.DEGRADED]:
                    service.status = ServiceStatus.RUNNING
            elif service.status == ServiceStatus.RUNNING:
                service.status = ServiceStatus.STOPPED
            
            status[name] = {
                "name": name,
                "status": service.status.value,
                "port": service.config.port,
                "pid": service.pid,
                "required": service.config.required,
                "error": service.error_message,
            }
        
        return status
    
    def print_status(self):
        """Print status summary."""
        status = self.get_status()
        
        print("\n=== Grace Services Status ===")
        for name, info in status.items():
            icon = "✓" if info["status"] == "running" else "✗"
            print(f"  {icon} {name}: {info['status']} (port {info['port']})")
        print()


def get_service_manager(root_path: Path, backend_port: int = 8000) -> GraceServiceManager:
    """Get or create service manager singleton."""
    global _service_manager
    if "_service_manager" not in globals() or _service_manager is None:
        _service_manager = GraceServiceManager(root_path, backend_port)
    return _service_manager


_service_manager: Optional[GraceServiceManager] = None
