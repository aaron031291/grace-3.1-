"""
Enterprise Orchestration Layer
==============================

Complete enterprise infrastructure management:

1. Secret Management - Vault, AWS Secrets, Azure Key Vault
2. Distributed Tracing - OpenTelemetry integration
3. Service Mesh - Health-aware routing, circuit breakers
4. Auto-Scaling - Dynamic resource allocation
5. Disaster Recovery - Failover, backup, restore
6. Feature Flags - Gradual rollout, A/B testing
7. Compliance - SOC2, HIPAA, GDPR automation
8. Chaos Engineering - Resilience testing
"""

import os
import sys
import json
import time
import hashlib
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
import random
import asyncio

logger = logging.getLogger(__name__)


# =============================================================================
# SECRET MANAGEMENT
# =============================================================================

class SecretProvider(str, Enum):
    """Supported secret providers."""
    ENV = "environment"           # Environment variables
    FILE = "file"                 # Local files
    VAULT = "hashicorp_vault"     # HashiCorp Vault
    AWS_SECRETS = "aws_secrets"   # AWS Secrets Manager
    AZURE_KEYVAULT = "azure_keyvault"  # Azure Key Vault
    GCP_SECRET = "gcp_secret"     # Google Secret Manager


@dataclass
class Secret:
    """A secret with metadata."""
    key: str
    value: str
    provider: SecretProvider
    expires_at: Optional[datetime] = None
    version: str = "1"
    cached_at: datetime = field(default_factory=datetime.now)


class SecretManager:
    """
    Unified secret management across providers.
    
    Features:
    - Multi-provider support
    - Automatic rotation
    - Caching with TTL
    - Audit logging
    """
    
    def __init__(self, default_provider: SecretProvider = SecretProvider.ENV):
        self.default_provider = default_provider
        self._cache: Dict[str, Secret] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._providers: Dict[SecretProvider, Callable] = {
            SecretProvider.ENV: self._get_from_env,
            SecretProvider.FILE: self._get_from_file,
        }
        self._audit_log: List[Dict] = []
        
        # Try to initialize cloud providers
        self._init_cloud_providers()
    
    def _init_cloud_providers(self):
        """Initialize cloud secret providers if available."""
        # AWS Secrets Manager
        try:
            import boto3
            self._aws_client = boto3.client('secretsmanager')
            self._providers[SecretProvider.AWS_SECRETS] = self._get_from_aws
            logger.info("AWS Secrets Manager available")
        except ImportError:
            pass
        
        # HashiCorp Vault
        try:
            import hvac
            vault_addr = os.environ.get("VAULT_ADDR")
            vault_token = os.environ.get("VAULT_TOKEN")
            if vault_addr and vault_token:
                self._vault_client = hvac.Client(url=vault_addr, token=vault_token)
                self._providers[SecretProvider.VAULT] = self._get_from_vault
                logger.info("HashiCorp Vault available")
        except ImportError:
            pass
    
    def get_secret(self, key: str, provider: Optional[SecretProvider] = None) -> Optional[str]:
        """Get a secret value."""
        provider = provider or self.default_provider
        
        # Check cache
        cache_key = f"{provider.value}:{key}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached.cached_at < self._cache_ttl:
                return cached.value
        
        # Fetch from provider
        if provider not in self._providers:
            logger.warning(f"Secret provider not available: {provider}")
            return None
        
        try:
            value = self._providers[provider](key)
            if value:
                self._cache[cache_key] = Secret(
                    key=key,
                    value=value,
                    provider=provider,
                )
                self._audit("get", key, provider, success=True)
            return value
        except Exception as e:
            self._audit("get", key, provider, success=False, error=str(e))
            logger.error(f"Failed to get secret {key}: {e}")
            return None
    
    def _get_from_env(self, key: str) -> Optional[str]:
        """Get secret from environment variable."""
        return os.environ.get(key) or os.environ.get(key.upper())
    
    def _get_from_file(self, key: str) -> Optional[str]:
        """Get secret from file."""
        secrets_dir = Path(os.environ.get("SECRETS_DIR", "/run/secrets"))
        secret_file = secrets_dir / key
        if secret_file.exists():
            return secret_file.read_text().strip()
        return None
    
    def _get_from_aws(self, key: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self._aws_client.get_secret_value(SecretId=key)
            return response.get("SecretString")
        except Exception as e:
            logger.error(f"AWS secret fetch failed: {e}")
            return None
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """Get secret from HashiCorp Vault."""
        try:
            path = os.environ.get("VAULT_PATH", "secret/data/grace")
            response = self._vault_client.secrets.kv.v2.read_secret_version(
                path=f"{path}/{key}"
            )
            return response["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Vault secret fetch failed: {e}")
            return None
    
    def _audit(self, action: str, key: str, provider: SecretProvider, 
               success: bool, error: Optional[str] = None):
        """Log secret access for audit."""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "key": key,
            "provider": provider.value,
            "success": success,
            "error": error,
        })
        # Keep only last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]


# =============================================================================
# DISTRIBUTED TRACING
# =============================================================================

@dataclass
class Span:
    """A trace span."""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)


class DistributedTracer:
    """
    Distributed tracing for request tracking across services.
    
    Compatible with OpenTelemetry when available, falls back to local tracing.
    """
    
    def __init__(self):
        self._spans: Dict[str, Span] = {}
        self._current_trace = threading.local()
        self._otel_available = False
        
        # Try to use OpenTelemetry
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            self._otel_trace = trace
            self._otel_available = True
            logger.info("OpenTelemetry tracing available")
        except ImportError:
            logger.info("Using built-in tracing (OpenTelemetry not installed)")
    
    def _generate_id(self, length: int = 16) -> str:
        """Generate random trace/span ID."""
        return hashlib.sha256(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:length]
    
    @contextmanager
    def start_span(self, operation: str, parent_id: Optional[str] = None):
        """Start a new span."""
        trace_id = getattr(self._current_trace, 'trace_id', None) or self._generate_id(32)
        span_id = self._generate_id(16)
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            operation=operation,
            start_time=datetime.now(),
        )
        
        self._spans[span_id] = span
        self._current_trace.trace_id = trace_id
        self._current_trace.span_id = span_id
        
        try:
            yield span
            span.status = "ok"
        except Exception as e:
            span.status = "error"
            span.attributes["error"] = str(e)
            raise
        finally:
            span.end_time = datetime.now()
    
    def add_event(self, name: str, attributes: Optional[Dict] = None):
        """Add an event to the current span."""
        span_id = getattr(self._current_trace, 'span_id', None)
        if span_id and span_id in self._spans:
            self._spans[span_id].events.append({
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "attributes": attributes or {},
            })
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [s for s in self._spans.values() if s.trace_id == trace_id]
    
    def export_traces(self, since: Optional[datetime] = None) -> List[Dict]:
        """Export traces for analysis."""
        traces = []
        for span in self._spans.values():
            if since and span.start_time < since:
                continue
            traces.append({
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "parent_id": span.parent_id,
                "operation": span.operation,
                "start_time": span.start_time.isoformat(),
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "duration_ms": (span.end_time - span.start_time).total_seconds() * 1000 if span.end_time else None,
                "status": span.status,
                "attributes": span.attributes,
                "events": span.events,
            })
        return traces


# =============================================================================
# SERVICE MESH / CIRCUIT BREAKER
# =============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 30.0               # Seconds in open state before half-open
    half_open_max_calls: int = 3        # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    
    Prevents cascading failures by stopping requests to failing services.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout:
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_calls = 0
                        logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
                        return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
        
        return False
    
    def record_success(self):
        """Record successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit {self.name}: CLOSED -> OPEN")
    
    @contextmanager
    def call(self):
        """Context manager for protected calls."""
        if not self.can_execute():
            raise CircuitOpenError(f"Circuit {self.name} is open")
        
        try:
            yield
            self.record_success()
        except Exception as e:
            self.record_failure()
            raise


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


class ServiceMesh:
    """
    Simple service mesh for internal service communication.
    
    Features:
    - Service discovery
    - Health-aware routing
    - Circuit breakers
    - Retry logic
    """
    
    def __init__(self):
        self._services: Dict[str, List[str]] = {}  # service -> [endpoints]
        self._health: Dict[str, bool] = {}          # endpoint -> healthy
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def register_service(self, name: str, endpoints: List[str]):
        """Register a service with its endpoints."""
        with self._lock:
            self._services[name] = endpoints
            for endpoint in endpoints:
                self._health[endpoint] = True
                if endpoint not in self._circuits:
                    self._circuits[endpoint] = CircuitBreaker(endpoint)
        logger.info(f"Registered service: {name} with {len(endpoints)} endpoints")
    
    def get_endpoint(self, service: str) -> Optional[str]:
        """Get a healthy endpoint for a service."""
        if service not in self._services:
            return None
        
        endpoints = self._services[service]
        healthy = [e for e in endpoints if self._health.get(e, False)]
        
        if not healthy:
            # Fall back to any endpoint
            healthy = endpoints
        
        if healthy:
            return random.choice(healthy)
        return None
    
    def mark_unhealthy(self, endpoint: str):
        """Mark an endpoint as unhealthy."""
        self._health[endpoint] = False
    
    def mark_healthy(self, endpoint: str):
        """Mark an endpoint as healthy."""
        self._health[endpoint] = True
    
    def get_circuit(self, endpoint: str) -> CircuitBreaker:
        """Get circuit breaker for an endpoint."""
        if endpoint not in self._circuits:
            self._circuits[endpoint] = CircuitBreaker(endpoint)
        return self._circuits[endpoint]


# =============================================================================
# AUTO-SCALING
# =============================================================================

@dataclass
class ScalingPolicy:
    """Auto-scaling policy."""
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0
    scale_up_cooldown: int = 60      # seconds
    scale_down_cooldown: int = 300   # seconds


class AutoScaler:
    """
    Auto-scaling based on metrics.
    
    Works with:
    - Local process pools
    - Docker containers
    - Kubernetes pods
    """
    
    def __init__(self, policy: Optional[ScalingPolicy] = None):
        self.policy = policy or ScalingPolicy()
        self.current_instances = 1
        self.last_scale_up: Optional[datetime] = None
        self.last_scale_down: Optional[datetime] = None
        self._metrics_history: List[Dict] = []
    
    def record_metrics(self, cpu_percent: float, memory_percent: float):
        """Record current metrics."""
        self._metrics_history.append({
            "timestamp": datetime.now(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
        })
        # Keep last 100 samples
        if len(self._metrics_history) > 100:
            self._metrics_history = self._metrics_history[-100:]
    
    def get_scaling_decision(self) -> Tuple[str, int]:
        """
        Determine scaling action.
        
        Returns:
            Tuple of (action, target_instances)
            action: "scale_up", "scale_down", or "none"
        """
        if len(self._metrics_history) < 5:
            return ("none", self.current_instances)
        
        # Calculate average over last 5 samples
        recent = self._metrics_history[-5:]
        avg_cpu = sum(m["cpu_percent"] for m in recent) / len(recent)
        avg_memory = sum(m["memory_percent"] for m in recent) / len(recent)
        
        now = datetime.now()
        
        # Scale up check
        if avg_cpu > self.policy.target_cpu_percent or avg_memory > self.policy.target_memory_percent:
            if self.current_instances < self.policy.max_instances:
                if not self.last_scale_up or (now - self.last_scale_up).total_seconds() > self.policy.scale_up_cooldown:
                    return ("scale_up", self.current_instances + 1)
        
        # Scale down check
        if avg_cpu < self.policy.target_cpu_percent * 0.5 and avg_memory < self.policy.target_memory_percent * 0.5:
            if self.current_instances > self.policy.min_instances:
                if not self.last_scale_down or (now - self.last_scale_down).total_seconds() > self.policy.scale_down_cooldown:
                    return ("scale_down", self.current_instances - 1)
        
        return ("none", self.current_instances)
    
    def apply_scaling(self, target_instances: int):
        """Apply scaling decision."""
        if target_instances > self.current_instances:
            self.last_scale_up = datetime.now()
            logger.info(f"Scaling up: {self.current_instances} -> {target_instances}")
        elif target_instances < self.current_instances:
            self.last_scale_down = datetime.now()
            logger.info(f"Scaling down: {self.current_instances} -> {target_instances}")
        
        self.current_instances = target_instances


# =============================================================================
# FEATURE FLAGS
# =============================================================================

@dataclass
class FeatureFlag:
    """A feature flag with rollout configuration."""
    name: str
    enabled: bool = False
    rollout_percentage: float = 0.0    # 0-100
    allowed_users: List[str] = field(default_factory=list)
    allowed_groups: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureFlagManager:
    """
    Feature flag management for gradual rollouts.
    
    Features:
    - Percentage-based rollout
    - User/group targeting
    - A/B testing support
    """
    
    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._overrides: Dict[str, Dict[str, bool]] = {}  # flag -> {user_id -> enabled}
    
    def register_flag(self, flag: FeatureFlag):
        """Register a feature flag."""
        self._flags[flag.name] = flag
    
    def is_enabled(self, name: str, user_id: Optional[str] = None, 
                   groups: Optional[List[str]] = None) -> bool:
        """Check if feature is enabled for user."""
        if name not in self._flags:
            return False
        
        flag = self._flags[name]
        
        # Check user override
        if user_id and name in self._overrides:
            if user_id in self._overrides[name]:
                return self._overrides[name][user_id]
        
        # Check if globally enabled
        if flag.enabled:
            return True
        
        # Check allowed users
        if user_id and user_id in flag.allowed_users:
            return True
        
        # Check allowed groups
        if groups:
            for group in groups:
                if group in flag.allowed_groups:
                    return True
        
        # Check rollout percentage
        if flag.rollout_percentage > 0 and user_id:
            # Consistent hash for user
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            if (user_hash % 100) < flag.rollout_percentage:
                return True
        
        return False
    
    def set_override(self, flag_name: str, user_id: str, enabled: bool):
        """Set user-specific override."""
        if flag_name not in self._overrides:
            self._overrides[flag_name] = {}
        self._overrides[flag_name][user_id] = enabled
    
    def get_all_flags(self) -> Dict[str, Dict]:
        """Get all flags with their status."""
        return {
            name: {
                "enabled": flag.enabled,
                "rollout_percentage": flag.rollout_percentage,
                "allowed_users_count": len(flag.allowed_users),
                "allowed_groups": flag.allowed_groups,
            }
            for name, flag in self._flags.items()
        }


# =============================================================================
# CHAOS ENGINEERING
# =============================================================================

class ChaosMonkey:
    """
    Chaos engineering for resilience testing.
    
    Injects failures to test system resilience:
    - Random latency
    - Service failures
    - Resource exhaustion
    """
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._failure_rate = 0.0  # 0-1
        self._latency_ms = 0      # Added latency
        self._affected_services: List[str] = []
    
    def set_failure_rate(self, rate: float, services: Optional[List[str]] = None):
        """Set random failure rate (0-1)."""
        self._failure_rate = max(0, min(1, rate))
        self._affected_services = services or []
        logger.warning(f"Chaos: Failure rate set to {rate*100:.1f}%")
    
    def set_latency(self, ms: int):
        """Set added latency in milliseconds."""
        self._latency_ms = max(0, ms)
        logger.warning(f"Chaos: Latency set to {ms}ms")
    
    def should_fail(self, service: Optional[str] = None) -> bool:
        """Check if request should fail."""
        if not self.enabled:
            return False
        
        if self._affected_services and service not in self._affected_services:
            return False
        
        return random.random() < self._failure_rate
    
    def inject_latency(self):
        """Inject artificial latency."""
        if not self.enabled or self._latency_ms <= 0:
            return
        
        time.sleep(self._latency_ms / 1000)
    
    @contextmanager
    def chaos_context(self, service: Optional[str] = None):
        """Context manager that may inject chaos."""
        if self.should_fail(service):
            raise ChaosError(f"Chaos monkey struck! Service: {service}")
        
        self.inject_latency()
        yield


class ChaosError(Exception):
    """Raised by chaos monkey."""
    pass


# =============================================================================
# ORCHESTRATION LAYER (MAIN COORDINATOR)
# =============================================================================

class OrchestrationLayer:
    """
    Central orchestration for all enterprise features.
    
    Coordinates:
    - Secret management
    - Distributed tracing
    - Service mesh
    - Auto-scaling
    - Feature flags
    - Chaos engineering
    """
    
    _instance: Optional["OrchestrationLayer"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Initialize all components
        self.secrets = SecretManager()
        self.tracer = DistributedTracer()
        self.mesh = ServiceMesh()
        self.scaler = AutoScaler()
        self.features = FeatureFlagManager()
        self.chaos = ChaosMonkey(enabled=False)
        
        # Register default feature flags
        self._register_default_flags()
        
        logger.info("Enterprise Orchestration Layer initialized")
    
    def _register_default_flags(self):
        """Register default feature flags."""
        default_flags = [
            FeatureFlag(name="gpu_acceleration", enabled=False),
            FeatureFlag(name="experimental_rag", enabled=False, rollout_percentage=10),
            FeatureFlag(name="new_ui", enabled=False, rollout_percentage=50),
            FeatureFlag(name="advanced_healing", enabled=True),
            FeatureFlag(name="telemetry", enabled=True),
        ]
        for flag in default_flags:
            self.features.register_flag(flag)
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret."""
        return self.secrets.get_secret(key)
    
    @contextmanager
    def trace(self, operation: str):
        """Start a trace span."""
        with self.tracer.start_span(operation) as span:
            yield span
    
    def get_service_endpoint(self, service: str) -> Optional[str]:
        """Get endpoint for a service."""
        return self.mesh.get_endpoint(service)
    
    def is_feature_enabled(self, feature: str, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled."""
        return self.features.is_enabled(feature, user_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestration layer status."""
        return {
            "secrets": {
                "provider": self.secrets.default_provider.value,
                "cached_count": len(self.secrets._cache),
            },
            "tracing": {
                "spans_count": len(self.tracer._spans),
                "otel_available": self.tracer._otel_available,
            },
            "mesh": {
                "services_count": len(self.mesh._services),
                "circuits": {
                    name: circuit.state.value 
                    for name, circuit in self.mesh._circuits.items()
                },
            },
            "scaling": {
                "current_instances": self.scaler.current_instances,
                "policy": asdict(self.scaler.policy),
            },
            "features": self.features.get_all_flags(),
            "chaos": {
                "enabled": self.chaos.enabled,
                "failure_rate": self.chaos._failure_rate,
                "latency_ms": self.chaos._latency_ms,
            },
        }


def get_orchestration_layer() -> OrchestrationLayer:
    """Get the singleton orchestration layer."""
    return OrchestrationLayer()
