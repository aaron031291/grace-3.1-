import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import psutil
from backend.utils.os_adapter import OS, paths, process, get_os_info
class ServiceStatus(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Service status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ServiceHealth:
    """Service health status."""
    service_name: str
    status: ServiceStatus
    uptime: float
    cpu_percent: float
    memory_mb: float
    last_check: datetime
    checks_passed: int
    checks_failed: int
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['last_check'] = self.last_check.isoformat()
        return data


@dataclass
class Alert:
    """Alert definition."""
    id: str
    level: AlertLevel
    service: str
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class EnterpriseMultiOSManager:
    """
    Enterprise-grade multi-OS management.
    
    Features:
    - Service health monitoring
    - Performance metrics
    - Alerting system
    - Resource management
    - Configuration management
    - Logging and auditing
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """Initialize enterprise manager."""
        self.root_path = root_path or Path(__file__).parent.parent.parent
        self.config_path = self.root_path / "backend" / "enterprise" / "multi_os_config.json"
        self.logs_path = self.root_path / "logs" / "enterprise"
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Service tracking
        self.services: Dict[str, ServiceHealth] = {}
        self.alerts: List[Alert] = []
        self.metrics: List[Dict] = []
        
        # Configuration
        self.config = self._load_config()
        
        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self.start_time = time.time()
        self.os_info = get_os_info()
        
        self.logger.info(f"Enterprise Multi-OS Manager initialized on {self.os_info['family']}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup enterprise logging."""
        logger = logging.getLogger('enterprise.multi_os')
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.logs_path / f"multi_os_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_config(self) -> Dict:
        """Load configuration."""
        default_config = {
            'monitoring_interval': 30,  # seconds
            'health_check_interval': 60,  # seconds
            'alert_retention_hours': 24,
            'metrics_retention_hours': 168,  # 7 days
            'cpu_threshold': 80.0,  # percent
            'memory_threshold': 80.0,  # percent
            'disk_threshold': 90.0,  # percent
            'services': {
                'backend': {
                    'enabled': True,
                    'port': 8000,
                    'health_endpoint': '/health',
                },
                'frontend': {
                    'enabled': True,
                    'port': 5173,
                },
                'database': {
                    'enabled': True,
                    'path': 'backend/data/grace.db',
                },
            },
        }
        
        if self.config_path.exists():
            try:
                user_config = json.loads(self.config_path.read_text(encoding='utf-8'))
                default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def _save_config(self):
        """Save configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2),
            encoding='utf-8'
        )
    
    def register_service(self, service_name: str, health_check: Optional[Callable] = None):
        """Register a service for monitoring."""
        self.services[service_name] = ServiceHealth(
            service_name=service_name,
            status=ServiceStatus.UNKNOWN,
            uptime=0.0,
            cpu_percent=0.0,
            memory_mb=0.0,
            last_check=datetime.now(),
            checks_passed=0,
            checks_failed=0,
        )
        self.logger.info(f"Registered service: {service_name}")
    
    def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a service."""
        if service_name not in self.services:
            self.register_service(service_name)
        
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            # Check if service is running
            if service_name == 'backend':
                health = self._check_backend_health()
            elif service_name == 'frontend':
                health = self._check_frontend_health()
            elif service_name == 'database':
                health = self._check_database_health()
            else:
                health = self._check_generic_health(service_name)
            
            # Update service health
            service.status = health['status']
            service.uptime = health.get('uptime', 0.0)
            service.cpu_percent = health.get('cpu_percent', 0.0)
            service.memory_mb = health.get('memory_mb', 0.0)
            service.last_check = datetime.now()
            
            if health['status'] == ServiceStatus.HEALTHY:
                service.checks_passed += 1
            else:
                service.checks_failed += 1
                self._create_alert(
                    level=AlertLevel.WARNING if health['status'] == ServiceStatus.DEGRADED else AlertLevel.ERROR,
                    service=service_name,
                    message=health.get('message', 'Service health check failed')
                )
            
            service.metadata = health.get('metadata', {})
            
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.checks_failed += 1
            self._create_alert(
                level=AlertLevel.ERROR,
                service=service_name,
                message=f"Health check error: {str(e)}"
            )
            self.logger.error(f"Health check failed for {service_name}: {e}")
        
        return service
    
    def _check_backend_health(self) -> Dict:
        """Check backend service health."""
        import socket
        
        port = self.config['services']['backend']['port']
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            # Port is open, try health endpoint
            try:
                import requests
                response = requests.get(
                    f"http://localhost:{port}/health",
                    timeout=2.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'status': ServiceStatus.HEALTHY,
                        'uptime': data.get('uptime', 0.0),
                        'cpu_percent': data.get('cpu_percent', 0.0),
                        'memory_mb': data.get('memory_mb', 0.0),
                        'message': 'Backend is healthy',
                        'metadata': data,
                    }
                else:
                    return {
                        'status': ServiceStatus.DEGRADED,
                        'message': f'Backend returned {response.status_code}',
                    }
            except ImportError:
                return {
                    'status': ServiceStatus.HEALTHY,
                    'message': 'Backend port is open (requests not available)',
                }
            except Exception as e:
                return {
                    'status': ServiceStatus.DEGRADED,
                    'message': f'Backend health endpoint error: {str(e)}',
                }
        else:
            return {
                'status': ServiceStatus.UNHEALTHY,
                'message': 'Backend port is not open',
            }
    
    def _check_frontend_health(self) -> Dict:
        """Check frontend service health."""
        import socket
        
        port = self.config['services']['frontend']['port']
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            return {
                'status': ServiceStatus.HEALTHY,
                'message': 'Frontend is healthy',
            }
        else:
            return {
                'status': ServiceStatus.UNHEALTHY,
                'message': 'Frontend port is not open',
            }
    
    def _check_database_health(self) -> Dict:
        """Check database health."""
        db_path = Path(self.config['services']['database']['path'])
        
        if not db_path.is_absolute():
            db_path = self.root_path / db_path
        
        if db_path.exists():
            # Check file size and permissions
            size_mb = db_path.stat().st_size / (1024 * 1024)
            readable = os.access(db_path, os.R_OK)
            writable = os.access(db_path, os.W_OK)
            
            if readable and writable:
                return {
                    'status': ServiceStatus.HEALTHY,
                    'message': 'Database is accessible',
                    'metadata': {
                        'size_mb': size_mb,
                        'path': str(db_path),
                    },
                }
            else:
                return {
                    'status': ServiceStatus.DEGRADED,
                    'message': 'Database has permission issues',
                }
        else:
            return {
                'status': ServiceStatus.UNHEALTHY,
                'message': 'Database file not found',
            }
    
    def _check_generic_health(self, service_name: str) -> Dict:
        """Check generic service health."""
        # Try to find process by name
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                if service_name.lower() in proc.info['name'].lower():
                    return {
                        'status': ServiceStatus.HEALTHY,
                        'cpu_percent': proc.info['cpu_percent'] or 0.0,
                        'memory_mb': (proc.info['memory_info'].rss / (1024 * 1024)) if proc.info['memory_info'] else 0.0,
                        'message': f'{service_name} process is running',
                    }
        except Exception:
            pass
        
        return {
            'status': ServiceStatus.UNKNOWN,
            'message': f'Could not determine health for {service_name}',
        }
    
    def _create_alert(self, level: AlertLevel, service: str, message: str, metadata: Optional[Dict] = None):
        """Create an alert."""
        alert = Alert(
            id=f"{service}_{int(time.time())}",
            level=level,
            service=service,
            message=message,
            timestamp=datetime.now(),
            resolved=False,
            metadata=metadata,
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }.get(level, logging.WARNING)
        
        self.logger.log(log_level, f"ALERT [{level.value.upper()}] {service}: {message}")
        
        # Keep only recent alerts
        cutoff = datetime.now() - timedelta(hours=self.config['alert_retention_hours'])
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]
    
    def collect_metrics(self) -> Dict:
        """Collect system metrics."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'os_info': self.os_info,
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_available_mb': psutil.virtual_memory().available / (1024 * 1024),
                'disk_percent': psutil.disk_usage('/').percent if OS.is_unix else psutil.disk_usage('C:\\').percent,
            },
            'services': {name: service.to_dict() for name, service in self.services.items()},
            'uptime': time.time() - self.start_time,
        }
        
        # Check thresholds
        if metrics['system']['cpu_percent'] > self.config['cpu_threshold']:
            self._create_alert(
                level=AlertLevel.WARNING,
                service='system',
                message=f"High CPU usage: {metrics['system']['cpu_percent']:.1f}%"
            )
        
        if metrics['system']['memory_percent'] > self.config['memory_threshold']:
            self._create_alert(
                level=AlertLevel.WARNING,
                service='system',
                message=f"High memory usage: {metrics['system']['memory_percent']:.1f}%"
            )
        
        if metrics['system']['disk_percent'] > self.config['disk_threshold']:
            self._create_alert(
                level=AlertLevel.WARNING,
                service='system',
                message=f"High disk usage: {metrics['system']['disk_percent']:.1f}%"
            )
        
        # Store metrics
        self.metrics.append(metrics)
        
        # Keep only recent metrics
        cutoff = datetime.now() - timedelta(hours=self.config['metrics_retention_hours'])
        self.metrics = [m for m in self.metrics if datetime.fromisoformat(m['timestamp']) > cutoff]
        
        return metrics
    
    def start_monitoring(self):
        """Start monitoring loop."""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Enterprise monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring loop."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Enterprise monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Check service health
                for service_name in self.config['services'].keys():
                    if self.config['services'][service_name].get('enabled', True):
                        self.check_service_health(service_name)
                
                # Collect metrics
                self.collect_metrics()
                
                # Sleep
                time.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def get_status(self) -> Dict:
        """Get enterprise status."""
        return {
            'os_info': self.os_info,
            'monitoring_active': self.monitoring_active,
            'services': {name: service.to_dict() for name, service in self.services.items()},
            'alerts': {
                'total': len(self.alerts),
                'unresolved': sum(1 for a in self.alerts if not a.resolved),
                'by_level': {
                    level.value: sum(1 for a in self.alerts if a.level == level and not a.resolved)
                    for level in AlertLevel
                },
                'recent': [a.to_dict() for a in self.alerts[-10:]],
            },
            'metrics': {
                'total': len(self.metrics),
                'latest': self.metrics[-1] if self.metrics else None,
            },
            'uptime': time.time() - self.start_time,
        }
    
    def save_report(self, output_path: Optional[Path] = None):
        """Save enterprise status report."""
        if output_path is None:
            output_path = self.logs_path / f"enterprise_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': self.get_status(),
            'config': self.config,
        }
        
        output_path.write_text(
            json.dumps(report, indent=2),
            encoding='utf-8'
        )
        
        self.logger.info(f"Enterprise report saved to: {output_path}")
        return output_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enterprise Multi-OS Manager')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'report'], help='Action to perform')
    
    args = parser.parse_args()
    
    manager = EnterpriseMultiOSManager()
    
    if args.action == 'start':
        manager.start_monitoring()
        print("Enterprise monitoring started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop_monitoring()
            print("\nEnterprise monitoring stopped")
    
    elif args.action == 'stop':
        manager.stop_monitoring()
        print("Enterprise monitoring stopped")
    
    elif args.action == 'status':
        status = manager.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.action == 'report':
        report_path = manager.save_report()
        print(f"Report saved to: {report_path}")


if __name__ == '__main__':
    main()
