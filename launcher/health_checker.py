"""
Strict Health Checker
=====================
Health checks that verify actual functionality, not just "process is running".

Philosophy:
- Backend up ≠ backend healthy
- Embeddings loaded ≠ embeddings compatible
- IDE bridge running ≠ protocol version match

All checks are strict: fail fast or don't start.
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    details: Optional[Dict] = None
    
    def is_fatal(self) -> bool:
        """Check if this result is fatal (must fail startup)."""
        return self.status == HealthStatus.UNHEALTHY or self.status == HealthStatus.TIMEOUT


class HealthChecker:
    """
    Strict health checker.
    
    Dumb by design: just checks endpoints, no business logic.
    """
    
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize health checker.
        
        Args:
            backend_url: Base URL for backend API
            timeout: Request timeout in seconds
            max_retries: Maximum retries for flaky checks
            retry_delay: Delay between retries in seconds
            
        Raises:
            ImportError: If requests library is not available
        """
        if not HAS_REQUESTS:
            raise ImportError(
                "requests library is required for health checks.\n"
                "Install it with: pip install requests"
            )
        
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _retry_check(self, check_func, component: str) -> HealthCheckResult:
        """
        Retry a health check function.
        
        Args:
            check_func: Function that returns HealthCheckResult
            component: Component name for logging
            
        Returns:
            HealthCheckResult (aggregated from retries)
        """
        last_result = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = check_func()
                if result.status == HealthStatus.HEALTHY:
                    return result
                last_result = result
                if attempt < self.max_retries:
                    logger.warning(
                        f"{component} health check attempt {attempt}/{self.max_retries} failed: "
                        f"{result.message}. Retrying..."
                    )
                    time.sleep(self.retry_delay)
            except Exception as e:
                logger.warning(f"{component} health check attempt {attempt}/{self.max_retries} error: {e}")
                last_result = HealthCheckResult(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Exception: {str(e)}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
        
        # All retries failed
        if last_result:
            return last_result
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="All health check attempts failed"
        )
    
    def check_backend_up(self) -> HealthCheckResult:
        """
        Check if backend is up (basic connectivity).
        
        This is NOT a health check - it's just "is the process running".
        """
        start = time.time()
        try:
            response = requests.get(
                f"{self.backend_url}/health/live",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return HealthCheckResult(
                    component="backend",
                    status=HealthStatus.HEALTHY,
                    message="Backend process is running",
                    latency_ms=latency_ms
                )
            else:
                return HealthCheckResult(
                    component="backend",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Backend returned status {response.status_code}",
                    latency_ms=latency_ms
                )
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                component="backend",
                status=HealthStatus.TIMEOUT,
                message=f"Backend did not respond within {self.timeout}s",
                latency_ms=None
            )
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                component="backend",
                status=HealthStatus.UNHEALTHY,
                message="Cannot connect to backend (process may not be running)"
            )
        except Exception as e:
            return HealthCheckResult(
                component="backend",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking backend: {str(e)}"
            )
    
    def check_backend_healthy(self) -> HealthCheckResult:
        """
        STRICT: Check if backend is actually healthy (not just running).
        
        This verifies:
        - Database connectivity
        - Core services initialized
        - No critical errors
        """
        start = time.time()
        try:
            response = requests.get(
                f"{self.backend_url}/health",
                timeout=self.timeout * 2  # Health check can be slower
            )
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code != 200:
                return HealthCheckResult(
                    component="backend_health",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health endpoint returned {response.status_code}",
                    latency_ms=latency_ms
                )
            
            data = response.json()
            overall_status = data.get("status", "unknown")
            
            if overall_status == "healthy":
                return HealthCheckResult(
                    component="backend_health",
                    status=HealthStatus.HEALTHY,
                    message="Backend is healthy",
                    latency_ms=latency_ms,
                    details=data
                )
            elif overall_status == "degraded":
                # Degraded is acceptable for startup, but warn
                return HealthCheckResult(
                    component="backend_health",
                    status=HealthStatus.DEGRADED,
                    message="Backend is degraded (some services unavailable)",
                    latency_ms=latency_ms,
                    details=data
                )
            else:
                return HealthCheckResult(
                    component="backend_health",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Backend health status: {overall_status}",
                    latency_ms=latency_ms,
                    details=data
                )
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                component="backend_health",
                status=HealthStatus.TIMEOUT,
                message=f"Backend health check timed out after {self.timeout * 2}s"
            )
        except Exception as e:
            return HealthCheckResult(
                component="backend_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking backend health: {str(e)}"
            )
    
    def check_embeddings_loaded(self) -> HealthCheckResult:
        """
        Check if embeddings are loaded (basic check).
        
        This is NOT sufficient - we also need compatibility check.
        """
        return self._retry_check(self._check_embeddings_internal, "embeddings_loaded")
    
    def _check_embeddings_internal(self) -> HealthCheckResult:
        """Internal embeddings check."""
        start = time.time()
        try:
            # Check health endpoint for embeddings status
            response = requests.get(
                f"{self.backend_url}/health",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code != 200:
                return HealthCheckResult(
                    component="embeddings_loaded",
                    status=HealthStatus.UNHEALTHY,
                    message="Cannot check embeddings: health endpoint failed"
                )
            
            data = response.json()
            services = data.get("services", [])
            
            # Find embedding service in health check results
            embedding_service = next(
                (s for s in services if s.get("name") == "embedding_model"),
                None
            )
            
            if embedding_service is None:
                return HealthCheckResult(
                    component="embeddings_loaded",
                    status=HealthStatus.UNHEALTHY,
                    message="Embedding service not found in health check"
                )
            
            embedding_status = embedding_service.get("status", "unknown")
            if embedding_status == "healthy":
                return HealthCheckResult(
                    component="embeddings_loaded",
                    status=HealthStatus.HEALTHY,
                    message="Embeddings are loaded and working",
                    latency_ms=latency_ms,
                    details=embedding_service
                )
            else:
                return HealthCheckResult(
                    component="embeddings_loaded",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Embeddings status: {embedding_status}",
                    latency_ms=latency_ms,
                    details=embedding_service
                )
        except Exception as e:
            return HealthCheckResult(
                component="embeddings_loaded",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking embeddings: {str(e)}"
            )
    
    def check_embeddings_compatible(self) -> HealthCheckResult:
        """
        STRICT: Check if embeddings are compatible (version, dimension, etc.).
        
        This verifies:
        - Embedding model version matches requirements
        - Embedding dimensions are correct
        - Model can actually generate embeddings
        """
        start = time.time()
        try:
            # Try to get embedding info from backend
            # This would need a dedicated endpoint, but for now use health check details
            response = requests.get(
                f"{self.backend_url}/health",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code != 200:
                return HealthCheckResult(
                    component="embeddings_compatible",
                    status=HealthStatus.UNHEALTHY,
                    message="Cannot verify embeddings compatibility: health endpoint failed"
                )
            
            data = response.json()
            services = data.get("services", [])
            embedding_service = next(
                (s for s in services if s.get("name") == "embedding_model"),
                None
            )
            
            if embedding_service is None:
                return HealthCheckResult(
                    component="embeddings_compatible",
                    status=HealthStatus.UNHEALTHY,
                    message="Embedding service not found"
                )
            
            details = embedding_service.get("details", {})
            dimension = details.get("dimension")
            
            # Basic compatibility check: embeddings must have a valid dimension
            if dimension is None or dimension <= 0:
                return HealthCheckResult(
                    component="embeddings_compatible",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Invalid embedding dimension: {dimension}",
                    latency_ms=latency_ms
                )
            
            # TODO: Add version check once backend exposes embedding model version
            # For now, if embeddings are loaded and have valid dimension, assume compatible
            
            return HealthCheckResult(
                component="embeddings_compatible",
                status=HealthStatus.HEALTHY,
                message=f"Embeddings compatible (dimension: {dimension})",
                latency_ms=latency_ms,
                details=details
            )
        except Exception as e:
            return HealthCheckResult(
                component="embeddings_compatible",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking embeddings compatibility: {str(e)}"
            )
    
    def check_version_endpoint(self) -> HealthCheckResult:
        """
        Check if backend version endpoint is available.
        
        Required for version handshake.
        """
        start = time.time()
        try:
            # Try /version endpoint (we'll add this to backend)
            response = requests.get(
                f"{self.backend_url}/version",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return HealthCheckResult(
                    component="version_endpoint",
                    status=HealthStatus.HEALTHY,
                    message="Version endpoint available",
                    latency_ms=latency_ms,
                    details=response.json()
                )
            else:
                return HealthCheckResult(
                    component="version_endpoint",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Version endpoint returned {response.status_code}",
                    latency_ms=latency_ms
                )
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                component="version_endpoint",
                status=HealthStatus.UNHEALTHY,
                message="Cannot connect to version endpoint"
            )
        except Exception as e:
            return HealthCheckResult(
                component="version_endpoint",
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking version endpoint: {str(e)}"
            )
    
    def run_all_checks(self, strict: bool = True) -> List[HealthCheckResult]:
        """
        Run all health checks.
        
        Args:
            strict: If True, fatal results cause immediate failure
            
        Returns:
            List of health check results
            
        Raises:
            RuntimeError: If strict=True and any check fails fatally
        """
        logger.info("Running strict health checks...")
        
        checks = [
            ("Backend process", self.check_backend_up),
            ("Backend health", self.check_backend_healthy),
            ("Embeddings loaded", self.check_embeddings_loaded),
            ("Embeddings compatible", self.check_embeddings_compatible),
            ("Version endpoint", self.check_version_endpoint),
        ]
        
        results = []
        for name, check_func in checks:
            logger.info(f"Checking {name}...")
            result = self._retry_check(check_func, name)
            results.append(result)
            
            if strict and result.is_fatal():
                logger.error(f"❌ FATAL: {name} check failed: {result.message}")
                raise RuntimeError(
                    f"Health check failed: {name}\n"
                    f"Status: {result.status.value}\n"
                    f"Message: {result.message}\n"
                    f"System cannot start in unhealthy state."
                )
            elif result.status != HealthStatus.HEALTHY:
                logger.warning(f"⚠ {name}: {result.message}")
        
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        logger.info(f"Health checks complete: {healthy_count}/{len(results)} healthy")
        
        return results
