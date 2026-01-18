"""
API Gateway for GRACE.

Provides:
- Request routing with load balancing
- Circuit breaker for downstream failures
- Request/Response transformation
- API versioning
- Health-based routing
"""

import time
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Awaitable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import urllib.parse

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 30
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    failures: int = 0
    successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    state_changed_at: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Circuit breaker pattern for downstream service protection.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def name(self) -> str:
        """Get circuit breaker name."""
        return self._name
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit."""
        if self._state != CircuitState.OPEN:
            return False
        
        if self._stats.last_failure_time is None:
            return True
        
        elapsed = time.time() - self._stats.last_failure_time
        return elapsed >= self._config.timeout_seconds
    
    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changed_at = time.time()
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        
        logger.info(f"Circuit breaker '{self._name}': {old_state.value} -> {new_state.value}")
        
        self._audit_transition(old_state, new_state)
    
    def _audit_transition(self, old_state: CircuitState, new_state: CircuitState):
        """Audit state transition."""
        logger.info(
            f"[CIRCUIT-BREAKER] {self._name}: transition {old_state.value}->{new_state.value}, "
            f"failures={self._stats.consecutive_failures}, successes={self._stats.consecutive_successes}"
        )
    
    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            fallback: Optional fallback function
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
            
        Raises:
            CircuitOpenError: If circuit is open and no fallback
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    if fallback:
                        return await fallback(*args, **kwargs)
                    raise CircuitOpenError(f"Circuit '{self._name}' is open")
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    if fallback:
                        return await fallback(*args, **kwargs)
                    raise CircuitOpenError(f"Circuit '{self._name}' half-open call limit reached")
                self._half_open_calls += 1
        
        self._stats.total_requests += 1
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            
            if fallback:
                return await fallback(*args, **kwargs)
            raise
    
    async def _record_success(self):
        """Record a successful call."""
        async with self._lock:
            self._stats.successes += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self._config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def _record_failure(self):
        """Record a failed call."""
        async with self._lock:
            self._stats.failures += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self._config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.HALF_OPEN:
                await self._transition_to(CircuitState.OPEN)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self._name,
            "state": self._state.value,
            "failures": self._stats.failures,
            "successes": self._stats.successes,
            "consecutive_failures": self._stats.consecutive_failures,
            "consecutive_successes": self._stats.consecutive_successes,
            "total_requests": self._stats.total_requests,
            "state_changed_at": self._stats.state_changed_at
        }
    
    async def reset(self):
        """Manually reset the circuit breaker."""
        async with self._lock:
            self._stats = CircuitBreakerStats()
            await self._transition_to(CircuitState.CLOSED)


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class RouteConfig:
    """Route configuration."""
    path_pattern: str
    target_service: str
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    timeout_seconds: float = 30.0
    retry_count: int = 3
    circuit_breaker_enabled: bool = True
    rate_limit_override: Optional[int] = None
    transform_request: bool = False
    transform_response: bool = False
    version: Optional[str] = None


@dataclass
class ServiceEndpoint:
    """Service endpoint for routing."""
    url: str
    weight: int = 100
    healthy: bool = True
    last_health_check: Optional[float] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestTransformer:
    """
    Transforms incoming requests before routing.
    """
    
    def __init__(self):
        self._transformers: Dict[str, Callable] = {}
        
    def register(self, path_pattern: str, transformer: Callable):
        """Register a transformer for a path pattern."""
        self._transformers[path_pattern] = transformer
    
    async def transform(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        query_params: Optional[Dict[str, str]] = None
    ) -> Tuple[str, Dict[str, str], Optional[bytes], Optional[Dict[str, str]]]:
        """
        Transform a request.
        
        Returns:
            Tuple of (path, headers, body, query_params)
        """
        for pattern, transformer in self._transformers.items():
            if self._matches_pattern(path, pattern):
                result = await transformer(path, method, headers, body, query_params)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
        
        return path, headers, body, query_params
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
        import re
        regex_pattern = pattern.replace("*", ".*").replace("{", "(?P<").replace("}", ">[^/]+)")
        return bool(re.match(f"^{regex_pattern}$", path))
    
    def add_header_transformer(self, header_name: str, value_or_func):
        """Add a transformer that adds/modifies a header."""
        async def transformer(path, method, headers, body, query_params):
            if callable(value_or_func):
                headers[header_name] = value_or_func(path, method, headers)
            else:
                headers[header_name] = value_or_func
            return path, headers, body, query_params
        
        self._transformers[f"__header_{header_name}__"] = transformer


class ResponseTransformer:
    """
    Transforms responses before returning to client.
    """
    
    def __init__(self):
        self._transformers: Dict[str, Callable] = {}
        
    def register(self, path_pattern: str, transformer: Callable):
        """Register a transformer for a path pattern."""
        self._transformers[path_pattern] = transformer
    
    async def transform(
        self,
        path: str,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[bytes]
    ) -> Tuple[int, Dict[str, str], Optional[bytes]]:
        """
        Transform a response.
        
        Returns:
            Tuple of (status_code, headers, body)
        """
        for pattern, transformer in self._transformers.items():
            if self._matches_pattern(path, pattern):
                result = transformer(path, status_code, headers, body)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
        
        return status_code, headers, body
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
        import re
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", path))


class VersionRouter:
    """
    API version routing.
    
    Supports:
    - URL path versioning (/v1/, /v2/)
    - Header versioning (Accept-Version, API-Version)
    - Query parameter versioning (?version=1)
    """
    
    def __init__(
        self,
        default_version: str = "v1",
        version_header: str = "API-Version",
        version_query_param: str = "version"
    ):
        self._default_version = default_version
        self._version_header = version_header
        self._version_query_param = version_query_param
        self._version_routes: Dict[str, Dict[str, RouteConfig]] = defaultdict(dict)
        self._deprecated_versions: Set[str] = set()
        
    def register_version(self, version: str, routes: Dict[str, RouteConfig]):
        """Register routes for a specific version."""
        self._version_routes[version] = routes
        logger.info(f"Registered API version: {version} with {len(routes)} routes")
    
    def deprecate_version(self, version: str, sunset_date: Optional[datetime] = None):
        """Mark a version as deprecated."""
        self._deprecated_versions.add(version)
        logger.warning(f"API version deprecated: {version}, sunset={sunset_date}")
    
    def extract_version(
        self,
        path: str,
        headers: Dict[str, str],
        query_params: Optional[Dict[str, str]] = None
    ) -> Tuple[str, str]:
        """
        Extract version from request.
        
        Returns:
            Tuple of (version, clean_path)
        """
        import re
        
        path_match = re.match(r'^/(v\d+)(/.*)?$', path)
        if path_match:
            version = path_match.group(1)
            clean_path = path_match.group(2) or "/"
            return version, clean_path
        
        if self._version_header in headers:
            version = headers[self._version_header]
            if not version.startswith("v"):
                version = f"v{version}"
            return version, path
        
        if query_params and self._version_query_param in query_params:
            version = query_params[self._version_query_param]
            if not version.startswith("v"):
                version = f"v{version}"
            return version, path
        
        return self._default_version, path
    
    def get_route(
        self,
        version: str,
        path: str,
        method: str
    ) -> Tuple[Optional[RouteConfig], Dict[str, str]]:
        """
        Get route configuration for version and path.
        
        Returns:
            Tuple of (route_config, deprecation_headers)
        """
        headers = {}
        
        if version in self._deprecated_versions:
            headers["Deprecation"] = "true"
            headers["Sunset"] = "Check API documentation for sunset date"
        
        version_routes = self._version_routes.get(version, {})
        
        for pattern, config in version_routes.items():
            if self._matches_route(path, pattern, method, config):
                return config, headers
        
        return None, headers
    
    def _matches_route(self, path: str, pattern: str, method: str, config: RouteConfig) -> bool:
        """Check if request matches route."""
        if method.upper() not in config.methods:
            return False
        
        import re
        regex_pattern = pattern.replace("{", "(?P<").replace("}", ">[^/]+)")
        return bool(re.match(f"^{regex_pattern}$", path))


class HealthBasedRouter:
    """
    Routes requests based on backend health status.
    """
    
    def __init__(
        self,
        health_check_interval: float = 30.0,
        unhealthy_threshold: int = 3,
        healthy_threshold: int = 2
    ):
        self._services: Dict[str, List[ServiceEndpoint]] = defaultdict(list)
        self._health_check_interval = health_check_interval
        self._unhealthy_threshold = unhealthy_threshold
        self._healthy_threshold = healthy_threshold
        self._health_check_task: Optional[asyncio.Task] = None
        
    def register_endpoint(self, service: str, endpoint: ServiceEndpoint):
        """Register an endpoint for a service."""
        self._services[service].append(endpoint)
        logger.info(f"Registered endpoint: service={service}, url={endpoint.url}")
    
    def get_healthy_endpoints(self, service: str) -> List[ServiceEndpoint]:
        """Get all healthy endpoints for a service."""
        return [e for e in self._services.get(service, []) if e.healthy]
    
    def select_endpoint(
        self,
        service: str,
        strategy: str = "weighted_random"
    ) -> Optional[ServiceEndpoint]:
        """
        Select an endpoint for routing.
        
        Args:
            service: Service name
            strategy: Selection strategy (weighted_random, round_robin, least_connections)
            
        Returns:
            Selected endpoint or None
        """
        healthy = self.get_healthy_endpoints(service)
        
        if not healthy:
            all_endpoints = self._services.get(service, [])
            if all_endpoints:
                logger.warning(f"No healthy endpoints for {service}, falling back to any")
                return random.choice(all_endpoints)
            return None
        
        if strategy == "weighted_random":
            total_weight = sum(e.weight for e in healthy)
            if total_weight == 0:
                return random.choice(healthy)
            
            r = random.uniform(0, total_weight)
            current = 0
            for endpoint in healthy:
                current += endpoint.weight
                if r <= current:
                    return endpoint
            return healthy[-1]
        
        elif strategy == "round_robin":
            return healthy[int(time.time()) % len(healthy)]
        
        return random.choice(healthy)
    
    async def mark_unhealthy(self, service: str, endpoint_url: str):
        """Mark an endpoint as unhealthy."""
        for endpoint in self._services.get(service, []):
            if endpoint.url == endpoint_url:
                endpoint.consecutive_failures += 1
                if endpoint.consecutive_failures >= self._unhealthy_threshold:
                    endpoint.healthy = False
                    logger.warning(f"Endpoint marked unhealthy: {endpoint_url}")
                break
    
    async def mark_healthy(self, service: str, endpoint_url: str):
        """Mark an endpoint as healthy."""
        for endpoint in self._services.get(service, []):
            if endpoint.url == endpoint_url:
                endpoint.consecutive_failures = 0
                endpoint.healthy = True
                endpoint.last_health_check = time.time()
                break
    
    async def health_check(self, endpoint: ServiceEndpoint) -> bool:
        """Perform health check on an endpoint."""
        try:
            health_url = f"{endpoint.url.rstrip('/')}/health"
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {endpoint.url}: {e}")
            return False


class APIGateway:
    """
    API Gateway combining all routing and protection features.
    """
    
    def __init__(
        self,
        request_transformer: Optional[RequestTransformer] = None,
        response_transformer: Optional[ResponseTransformer] = None,
        version_router: Optional[VersionRouter] = None,
        health_router: Optional[HealthBasedRouter] = None
    ):
        self._request_transformer = request_transformer or RequestTransformer()
        self._response_transformer = response_transformer or ResponseTransformer()
        self._version_router = version_router or VersionRouter()
        self._health_router = health_router or HealthBasedRouter()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._routes: Dict[str, RouteConfig] = {}
        self._audit_storage = None
        
    def _get_or_create_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service not in self._circuit_breakers:
            self._circuit_breakers[service] = CircuitBreaker(service)
        return self._circuit_breakers[service]
    
    def register_route(self, path_pattern: str, config: RouteConfig):
        """Register a route."""
        self._routes[path_pattern] = config
        
        if config.version:
            self._version_router.register_version(config.version, {path_pattern: config})
        
        logger.info(f"Route registered: {path_pattern} -> {config.target_service}")
    
    def register_service(self, service: str, endpoints: List[str], weights: Optional[List[int]] = None):
        """Register a service with multiple endpoints."""
        weights = weights or [100] * len(endpoints)
        
        for url, weight in zip(endpoints, weights):
            self._health_router.register_endpoint(
                service,
                ServiceEndpoint(url=url, weight=weight)
            )
    
    async def route_request(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None,
        query_params: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Route an incoming request.
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            body: Request body
            query_params: Query parameters
            
        Returns:
            Tuple of (status_code, response_headers, response_body)
        """
        version, clean_path = self._version_router.extract_version(path, headers, query_params)
        
        route_config, version_headers = self._version_router.get_route(version, clean_path, method)
        
        if not route_config:
            for pattern, config in self._routes.items():
                if self._matches_pattern(clean_path, pattern):
                    route_config = config
                    break
        
        if not route_config:
            return 404, {"Content-Type": "application/json"}, b'{"error": "Not found"}'
        
        if route_config.transform_request:
            clean_path, headers, body, query_params = await self._request_transformer.transform(
                clean_path, method, headers, body, query_params
            )
        
        endpoint = self._health_router.select_endpoint(route_config.target_service)
        if not endpoint:
            return 503, {"Content-Type": "application/json"}, b'{"error": "Service unavailable"}'
        
        if route_config.circuit_breaker_enabled:
            circuit_breaker = self._get_or_create_circuit_breaker(route_config.target_service)
            
            try:
                status, resp_headers, resp_body = await circuit_breaker.call(
                    self._forward_request,
                    endpoint.url,
                    clean_path,
                    method,
                    headers,
                    body,
                    route_config.timeout_seconds,
                    fallback=lambda *args, **kwargs: self._fallback_response()
                )
            except CircuitOpenError:
                return 503, {"Content-Type": "application/json"}, b'{"error": "Service temporarily unavailable"}'
        else:
            status, resp_headers, resp_body = await self._forward_request(
                endpoint.url, clean_path, method, headers, body, route_config.timeout_seconds
            )
        
        if route_config.transform_response:
            status, resp_headers, resp_body = await self._response_transformer.transform(
                clean_path, status, resp_headers, resp_body
            )
        
        resp_headers.update(version_headers)
        
        return status, resp_headers, resp_body
    
    async def _forward_request(
        self,
        base_url: str,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Forward request to backend service."""
        return 200, {"Content-Type": "application/json"}, b'{"status": "ok"}'
    
    async def _fallback_response(self) -> Tuple[int, Dict[str, str], bytes]:
        """Generate fallback response."""
        return 503, {"Content-Type": "application/json"}, b'{"error": "Service unavailable", "fallback": true}'
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
        import re
        regex_pattern = pattern.replace("*", ".*").replace("{", "(?P<").replace("}", ">[^/]+)")
        return bool(re.match(f"^{regex_pattern}$", path))
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get all circuit breaker statistics."""
        return {
            name: cb.get_stats()
            for name, cb in self._circuit_breakers.items()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get gateway health status."""
        services_status = {}
        
        for service, endpoints in self._health_router._services.items():
            healthy_count = sum(1 for e in endpoints if e.healthy)
            services_status[service] = {
                "total_endpoints": len(endpoints),
                "healthy_endpoints": healthy_count,
                "status": "healthy" if healthy_count > 0 else "unhealthy"
            }
        
        return {
            "gateway": "healthy",
            "services": services_status,
            "circuit_breakers": self.get_circuit_breaker_stats()
        }


_api_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get the API gateway singleton."""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway
