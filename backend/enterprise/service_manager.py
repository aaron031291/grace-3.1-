import os
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from backend.utils.os_adapter import OS, paths, process, shell
class ServiceState(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Service state."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceDefinition:
    """Service definition."""
    name: str
    command: List[str]
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    depends_on: List[str] = None
    restart_policy: str = "always"  # always, on-failure, never
    health_check: Optional[str] = None
    health_check_interval: int = 30
    timeout: int = 300
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class EnterpriseServiceManager:
    """
    Enterprise service manager.
    
    Manages service lifecycle across multiple OSes.
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """Initialize service manager."""
        self.root_path = root_path or Path(__file__).parent.parent.parent
        self.services: Dict[str, ServiceDefinition] = {}
        self.service_processes: Dict[str, Any] = {}
        self.service_states: Dict[str, ServiceState] = {}
        
        logger = logging.getLogger('enterprise.service_manager')
        logger.setLevel(logging.INFO)
        self.logger = logger
        
        # Register default services
        self._register_default_services()
    
    def _register_default_services(self):
        """Register default GRACE services."""
        backend_dir = self.root_path / "backend"
        frontend_dir = self.root_path / "frontend"
        
        # Backend service
        self.register_service(ServiceDefinition(
            name="backend",
            command=[sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(backend_dir),
            health_check="http://localhost:8000/health",
            depends_on=[],
        ))
        
        # Frontend service (if exists)
        if frontend_dir.exists():
            npm_path = shell.find_executable("npm")
            if npm_path:
                self.register_service(ServiceDefinition(
                    name="frontend",
                    command=[npm_path, "run", "dev"],
                    cwd=str(frontend_dir),
                    depends_on=["backend"],
                ))
    
    def register_service(self, service: ServiceDefinition):
        """Register a service."""
        self.services[service.name] = service
        self.service_states[service.name] = ServiceState.STOPPED
        self.logger.info(f"Registered service: {service.name}")
    
    def start_service(self, service_name: str) -> bool:
        """Start a service."""
        if service_name not in self.services:
            self.logger.error(f"Service not found: {service_name}")
            return False
        
        service = self.services[service_name]
        
        # Check dependencies
        for dep in service.depends_on:
            if dep not in self.service_states:
                self.logger.error(f"Dependency not found: {dep}")
                return False
            
            if self.service_states[dep] != ServiceState.RUNNING:
                self.logger.info(f"Starting dependency: {dep}")
                if not self.start_service(dep):
                    self.logger.error(f"Failed to start dependency: {dep}")
                    return False
        
        # Check if already running
        if self.service_states[service_name] == ServiceState.RUNNING:
            self.logger.warning(f"Service already running: {service_name}")
            return True
        
        self.logger.info(f"Starting service: {service_name}")
        self.service_states[service_name] = ServiceState.STARTING
        
        try:
            # Start process
            proc = process.spawn(
                service.command,
                cwd=service.cwd,
                env=service.env,
                stdout=open(f"logs/{service_name}_stdout.log", "a") if OS.is_unix else None,
                stderr=open(f"logs/{service_name}_stderr.log", "a") if OS.is_unix else None,
            )
            
            self.service_processes[service_name] = proc
            self.service_states[service_name] = ServiceState.RUNNING
            
            self.logger.info(f"Service started: {service_name} (PID: {proc.pid})")
            return True
            
        except Exception as e:
            self.service_states[service_name] = ServiceState.FAILED
            self.logger.error(f"Failed to start service {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a service."""
        if service_name not in self.services:
            self.logger.error(f"Service not found: {service_name}")
            return False
        
        if service_name not in self.service_processes:
            self.logger.warning(f"Service not running: {service_name}")
            return True
        
        self.logger.info(f"Stopping service: {service_name}")
        self.service_states[service_name] = ServiceState.STOPPING
        
        try:
            proc = self.service_processes[service_name]
            process.terminate(proc, timeout=10.0)
            
            del self.service_processes[service_name]
            self.service_states[service_name] = ServiceState.STOPPED
            
            self.logger.info(f"Service stopped: {service_name}")
            return True
            
        except Exception as e:
            self.service_states[service_name] = ServiceState.FAILED
            self.logger.error(f"Failed to stop service {service_name}: {e}")
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        self.logger.info(f"Restarting service: {service_name}")
        self.stop_service(service_name)
        time.sleep(2)
        return self.start_service(service_name)
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get service status."""
        if service_name not in self.services:
            return {'error': 'Service not found'}
        
        service = self.services[service_name]
        state = self.service_states.get(service_name, ServiceState.UNKNOWN)
        
        status = {
            'name': service_name,
            'state': state.value,
            'command': service.command,
        }
        
        if service_name in self.service_processes:
            proc = self.service_processes[service_name]
            if proc.poll() is None:
                status['pid'] = proc.pid
                status['running'] = True
            else:
                status['running'] = False
                status['exit_code'] = proc.returncode
        else:
            status['running'] = False
        
        return status
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        return {
            name: self.get_service_status(name)
            for name in self.services.keys()
        }
    
    def start_all(self) -> Dict[str, bool]:
        """Start all services."""
        results = {}
        for service_name in self.services.keys():
            results[service_name] = self.start_service(service_name)
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """Stop all services."""
        results = {}
        # Stop in reverse order (dependencies first)
        for service_name in reversed(list(self.services.keys())):
            results[service_name] = self.stop_service(service_name)
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enterprise Service Manager')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'], help='Action')
    parser.add_argument('--service', type=str, help='Service name (optional, all if not specified)')
    
    args = parser.parse_args()
    
    manager = EnterpriseServiceManager()
    
    if args.action == 'start':
        if args.service:
            manager.start_service(args.service)
        else:
            manager.start_all()
    
    elif args.action == 'stop':
        if args.service:
            manager.stop_service(args.service)
        else:
            manager.stop_all()
    
    elif args.action == 'restart':
        if args.service:
            manager.restart_service(args.service)
        else:
            for name in manager.services.keys():
                manager.restart_service(name)
    
    elif args.action == 'status':
        if args.service:
            status = manager.get_service_status(args.service)
            print(json.dumps(status, indent=2))
        else:
            status = manager.get_all_status()
            print(json.dumps(status, indent=2))


if __name__ == '__main__':
    import json
    main()
