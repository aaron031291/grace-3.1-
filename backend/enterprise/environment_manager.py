"""
Environment Manager - Unified Environment & Deployment Management
==================================================================

Handles different deployment scenarios:
- Development (local machine)
- Staging (test servers)
- Production (live servers)

And different runtime environments:
- Local (native processes)
- Docker (containerized)
- Kubernetes (orchestrated)
- Cloud (AWS/GCP/Azure)

Integrates with multi_os_manager for OS-specific handling.
"""

import os
import sys
import json
import socket
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class DeploymentStage(str, Enum):
    """Deployment stage (lifecycle)."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class RuntimeEnvironment(str, Enum):
    """Where Grace is running."""
    LOCAL = "local"           # Native processes on host
    DOCKER = "docker"         # Docker containers
    DOCKER_COMPOSE = "docker_compose"  # Docker Compose stack
    KUBERNETES = "kubernetes" # K8s cluster
    AWS_ECS = "aws_ecs"       # AWS Elastic Container Service
    AWS_LAMBDA = "aws_lambda" # AWS Lambda (serverless)
    GCP_RUN = "gcp_run"       # Google Cloud Run
    AZURE_CONTAINER = "azure_container"  # Azure Container Instances


class HardwareProfile(str, Enum):
    """Hardware capability profile."""
    MINIMAL = "minimal"       # Low resources (1-2 CPU, 2GB RAM)
    STANDARD = "standard"     # Normal resources (4 CPU, 8GB RAM)
    PERFORMANCE = "performance"  # High resources (8+ CPU, 16GB+ RAM)
    GPU = "gpu"               # GPU acceleration available


@dataclass
class EnvironmentConfig:
    """Complete environment configuration."""
    stage: DeploymentStage
    runtime: RuntimeEnvironment
    hardware: HardwareProfile
    
    # Service URLs (may differ per environment)
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    qdrant_url: str = "http://localhost:6333"
    ollama_url: str = "http://localhost:11434"
    database_url: str = "sqlite:///./data/grace.db"
    
    # Feature flags
    enable_gpu: bool = False
    enable_caching: bool = True
    enable_telemetry: bool = True
    enable_self_healing: bool = True
    enable_hot_reload: bool = True
    
    # Resource limits
    max_workers: int = 4
    max_memory_mb: int = 4096
    request_timeout: float = 30.0
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
    
    # Security
    require_auth: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['stage'] = self.stage.value
        data['runtime'] = self.runtime.value
        data['hardware'] = self.hardware.value
        return data


class EnvironmentDetector:
    """
    Automatically detect the current environment.
    
    Detection order:
    1. Explicit environment variables
    2. Docker/container markers
    3. Cloud provider markers
    4. Default to local development
    """
    
    @staticmethod
    def detect_stage() -> DeploymentStage:
        """Detect deployment stage."""
        # Check explicit environment variable
        stage = os.environ.get("GRACE_STAGE", "").lower()
        if stage == "production" or stage == "prod":
            return DeploymentStage.PRODUCTION
        elif stage == "staging" or stage == "stage":
            return DeploymentStage.STAGING
        elif stage == "testing" or stage == "test":
            return DeploymentStage.TESTING
        elif stage == "development" or stage == "dev":
            return DeploymentStage.DEVELOPMENT
        
        # Check common production markers
        if os.environ.get("KUBERNETES_SERVICE_HOST"):
            return DeploymentStage.PRODUCTION
        if os.environ.get("AWS_EXECUTION_ENV"):
            return DeploymentStage.PRODUCTION
        
        # Default to development
        return DeploymentStage.DEVELOPMENT
    
    @staticmethod
    def detect_runtime() -> RuntimeEnvironment:
        """Detect runtime environment."""
        # Check explicit environment variable
        runtime = os.environ.get("GRACE_RUNTIME", "").lower()
        if runtime:
            try:
                return RuntimeEnvironment(runtime)
            except ValueError:
                pass
        
        # Kubernetes detection
        if os.environ.get("KUBERNETES_SERVICE_HOST"):
            return RuntimeEnvironment.KUBERNETES
        
        # Docker detection
        if Path("/.dockerenv").exists():
            return RuntimeEnvironment.DOCKER
        if os.environ.get("DOCKER_CONTAINER"):
            return RuntimeEnvironment.DOCKER
        
        # Docker Compose detection
        if os.environ.get("COMPOSE_PROJECT_NAME"):
            return RuntimeEnvironment.DOCKER_COMPOSE
        
        # AWS detection
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return RuntimeEnvironment.AWS_LAMBDA
        if os.environ.get("ECS_CONTAINER_METADATA_URI"):
            return RuntimeEnvironment.AWS_ECS
        
        # GCP detection
        if os.environ.get("K_SERVICE"):  # Cloud Run sets this
            return RuntimeEnvironment.GCP_RUN
        
        # Azure detection
        if os.environ.get("CONTAINER_APP_NAME"):
            return RuntimeEnvironment.AZURE_CONTAINER
        
        # Default to local
        return RuntimeEnvironment.LOCAL
    
    @staticmethod
    def detect_hardware() -> HardwareProfile:
        """Detect hardware profile."""
        try:
            import psutil
            
            # Check for GPU
            try:
                import torch
                if torch.cuda.is_available():
                    return HardwareProfile.GPU
            except ImportError:
                pass
            
            # Check CPU and memory
            cpu_count = psutil.cpu_count(logical=False) or 1
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            if cpu_count >= 8 and memory_gb >= 16:
                return HardwareProfile.PERFORMANCE
            elif cpu_count >= 4 and memory_gb >= 8:
                return HardwareProfile.STANDARD
            else:
                return HardwareProfile.MINIMAL
                
        except ImportError:
            return HardwareProfile.STANDARD
    
    @classmethod
    def detect_all(cls) -> EnvironmentConfig:
        """Detect complete environment configuration."""
        stage = cls.detect_stage()
        runtime = cls.detect_runtime()
        hardware = cls.detect_hardware()
        
        # Build configuration based on detection
        config = EnvironmentConfig(
            stage=stage,
            runtime=runtime,
            hardware=hardware,
        )
        
        # Adjust settings based on stage
        if stage == DeploymentStage.PRODUCTION:
            config.log_level = "WARNING"
            config.enable_hot_reload = False
            config.require_auth = True
            config.enable_telemetry = True
        elif stage == DeploymentStage.STAGING:
            config.log_level = "INFO"
            config.enable_hot_reload = False
            config.require_auth = False
        elif stage == DeploymentStage.TESTING:
            config.log_level = "DEBUG"
            config.enable_telemetry = False
        else:  # Development
            config.log_level = "DEBUG"
            config.enable_hot_reload = True
            config.require_auth = False
        
        # Adjust settings based on runtime
        if runtime in [RuntimeEnvironment.DOCKER, RuntimeEnvironment.DOCKER_COMPOSE]:
            # Docker: use container service names
            config.qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
            config.ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
        elif runtime == RuntimeEnvironment.KUBERNETES:
            # K8s: use service discovery
            config.qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant-service:6333")
            config.ollama_url = os.environ.get("OLLAMA_URL", "http://ollama-service:11434")
        
        # Adjust settings based on hardware
        if hardware == HardwareProfile.GPU:
            config.enable_gpu = True
            config.max_workers = 8
        elif hardware == HardwareProfile.PERFORMANCE:
            config.max_workers = 8
            config.max_memory_mb = 16384
        elif hardware == HardwareProfile.MINIMAL:
            config.max_workers = 2
            config.max_memory_mb = 2048
            config.enable_caching = False  # Save memory
        
        # Override with environment variables
        config = cls._apply_env_overrides(config)
        
        return config
    
    @staticmethod
    def _apply_env_overrides(config: EnvironmentConfig) -> EnvironmentConfig:
        """Apply environment variable overrides."""
        env_mappings = {
            "GRACE_BACKEND_URL": "backend_url",
            "GRACE_FRONTEND_URL": "frontend_url",
            "QDRANT_URL": "qdrant_url",
            "OLLAMA_URL": "ollama_url",
            "DATABASE_URL": "database_url",
            "GRACE_MAX_WORKERS": ("max_workers", int),
            "GRACE_MAX_MEMORY_MB": ("max_memory_mb", int),
            "GRACE_LOG_LEVEL": "log_level",
            "GRACE_ENABLE_GPU": ("enable_gpu", lambda x: x.lower() == "true"),
            "GRACE_ENABLE_CACHING": ("enable_caching", lambda x: x.lower() == "true"),
        }
        
        for env_var, mapping in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if isinstance(mapping, tuple):
                    attr_name, converter = mapping
                    setattr(config, attr_name, converter(value))
                else:
                    setattr(config, mapping, value)
        
        return config


class EnvironmentManager:
    """
    Central environment manager for Grace.
    
    Provides:
    - Environment detection and configuration
    - Service URL resolution
    - Feature flag management
    - Resource limit enforcement
    - Environment-specific behavior switching
    """
    
    _instance: Optional["EnvironmentManager"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize environment manager."""
        if self._initialized:
            return
        
        self._initialized = True
        self.config = EnvironmentDetector.detect_all()
        self._feature_flags: Dict[str, bool] = {}
        self._service_overrides: Dict[str, str] = {}
        
        logger.info(
            f"Environment: stage={self.config.stage.value}, "
            f"runtime={self.config.runtime.value}, "
            f"hardware={self.config.hardware.value}"
        )
    
    @property
    def stage(self) -> DeploymentStage:
        """Get deployment stage."""
        return self.config.stage
    
    @property
    def runtime(self) -> RuntimeEnvironment:
        """Get runtime environment."""
        return self.config.runtime
    
    @property
    def hardware(self) -> HardwareProfile:
        """Get hardware profile."""
        return self.config.hardware
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.config.stage == DeploymentStage.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.config.stage == DeploymentStage.DEVELOPMENT
    
    @property
    def is_containerized(self) -> bool:
        """Check if running in a container."""
        return self.config.runtime in [
            RuntimeEnvironment.DOCKER,
            RuntimeEnvironment.DOCKER_COMPOSE,
            RuntimeEnvironment.KUBERNETES,
            RuntimeEnvironment.AWS_ECS,
            RuntimeEnvironment.GCP_RUN,
            RuntimeEnvironment.AZURE_CONTAINER,
        ]
    
    def get_service_url(self, service: str) -> str:
        """Get URL for a service, handling environment differences."""
        # Check overrides first
        if service in self._service_overrides:
            return self._service_overrides[service]
        
        # Return from config
        url_mapping = {
            "backend": self.config.backend_url,
            "frontend": self.config.frontend_url,
            "qdrant": self.config.qdrant_url,
            "ollama": self.config.ollama_url,
            "database": self.config.database_url,
        }
        
        return url_mapping.get(service, f"http://localhost:8000/{service}")
    
    def set_service_override(self, service: str, url: str):
        """Override service URL."""
        self._service_overrides[service] = url
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        # Check explicit overrides first
        if feature in self._feature_flags:
            return self._feature_flags[feature]
        
        # Check config
        feature_mapping = {
            "gpu": self.config.enable_gpu,
            "caching": self.config.enable_caching,
            "telemetry": self.config.enable_telemetry,
            "self_healing": self.config.enable_self_healing,
            "hot_reload": self.config.enable_hot_reload,
            "auth": self.config.require_auth,
        }
        
        return feature_mapping.get(feature, False)
    
    def set_feature_flag(self, feature: str, enabled: bool):
        """Set feature flag override."""
        self._feature_flags[feature] = enabled
    
    def get_resource_limit(self, resource: str) -> Any:
        """Get resource limit."""
        limit_mapping = {
            "max_workers": self.config.max_workers,
            "max_memory_mb": self.config.max_memory_mb,
            "request_timeout": self.config.request_timeout,
        }
        return limit_mapping.get(resource)
    
    def should_use_docker(self) -> bool:
        """Check if Docker should be used for dependencies."""
        # In containerized environments, services are already containers
        if self.is_containerized:
            return False
        
        # In local dev, prefer Docker if available
        if self.is_development:
            try:
                import shutil
                return shutil.which("docker") is not None
            except Exception:
                return False
        
        return False
    
    def get_startup_config(self) -> Dict[str, Any]:
        """Get configuration for startup."""
        return {
            "stage": self.config.stage.value,
            "runtime": self.config.runtime.value,
            "hardware": self.config.hardware.value,
            "services": {
                "backend": self.get_service_url("backend"),
                "frontend": self.get_service_url("frontend"),
                "qdrant": self.get_service_url("qdrant"),
                "ollama": self.get_service_url("ollama"),
            },
            "features": {
                "gpu": self.is_feature_enabled("gpu"),
                "caching": self.is_feature_enabled("caching"),
                "telemetry": self.is_feature_enabled("telemetry"),
                "self_healing": self.is_feature_enabled("self_healing"),
            },
            "resources": {
                "max_workers": self.get_resource_limit("max_workers"),
                "max_memory_mb": self.get_resource_limit("max_memory_mb"),
            },
            "log_level": self.config.log_level,
        }
    
    def export_config(self, path: Optional[Path] = None) -> Path:
        """Export current configuration to file."""
        if path is None:
            path = Path("grace_environment.json")
        
        config_data = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config.to_dict(),
            "startup": self.get_startup_config(),
        }
        
        path.write_text(json.dumps(config_data, indent=2))
        logger.info(f"Environment config exported to: {path}")
        return path


def get_environment_manager() -> EnvironmentManager:
    """Get the singleton environment manager."""
    return EnvironmentManager()


# Convenience functions
def is_production() -> bool:
    """Check if running in production."""
    return get_environment_manager().is_production


def is_development() -> bool:
    """Check if running in development."""
    return get_environment_manager().is_development


def get_service_url(service: str) -> str:
    """Get URL for a service."""
    return get_environment_manager().get_service_url(service)


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return get_environment_manager().is_feature_enabled(feature)
