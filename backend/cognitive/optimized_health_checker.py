import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache
logger = logging.getLogger(__name__)

class OptimizedHealthChecker:
    """
    Optimized health checker with parallel async checks and caching.
    
    Features:
    - Parallel service checks (all services checked simultaneously)
    - Result caching with TTL
    - Fast async I/O
    - Graceful fallback to sync if async unavailable
    """
    
    def __init__(self, cache_ttl: int = 30):
        """
        Initialize optimized health checker.
        
        Args:
            cache_ttl: Cache TTL in seconds (default: 30s)
        """
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.use_async = AIOHTTP_AVAILABLE
    
    async def check_all_services_parallel(self) -> Dict[str, Any]:
        """
        Check all services in parallel using asyncio.
        
        Returns:
            Dict with health status for all services
        """
        start_time = time.time()
        
        # Run all checks in parallel
        try:
            results = await asyncio.gather(
                self._check_qdrant_async(),
                self._check_ollama_async(),
                self._check_database_async(),
                self._check_backend_async(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"[HEALTH-CHECK] Parallel check failed: {e}")
            # Fallback to sequential
            results = [
                await self._check_qdrant_async(),
                await self._check_ollama_async(),
                await self._check_database_async(),
                await self._check_backend_async()
            ]
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "qdrant": self._safe_result(results[0]),
            "ollama": self._safe_result(results[1]),
            "database": self._safe_result(results[2]),
            "backend": self._safe_result(results[3]),
            "check_duration_ms": elapsed,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _safe_result(self, result: Any) -> Dict[str, Any]:
        """Safely extract result, handling exceptions."""
        if isinstance(result, Exception):
            return {"status": "error", "error": str(result)}
        return result if isinstance(result, dict) else {"status": "unknown"}
    
    async def _check_qdrant_async(self) -> Dict[str, Any]:
        """Async Qdrant check with caching."""
        cache_key = "qdrant"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            from vector_db.client import get_qdrant_client
            # Run in thread pool to avoid blocking
            client = await asyncio.to_thread(get_qdrant_client)
            if client:
                try:
                    collections = await asyncio.to_thread(client.list_collections)
                    result = {"status": "healthy", "collections": len(collections)}
                except Exception as e:
                    result = {"status": "unhealthy", "error": str(e)}
            else:
                result = {"status": "unavailable"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        
        self._cache_result(cache_key, result)
        return result
    
    async def _check_ollama_async(self) -> Dict[str, Any]:
        """Async Ollama check with caching."""
        cache_key = "ollama"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        if self.use_async:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:11434",
                        timeout=aiohttp.ClientTimeout(total=0.5)
                    ) as response:
                        result = {"status": "healthy" if response.status == 200 else "unavailable"}
            except asyncio.TimeoutError:
                result = {"status": "unavailable"}
            except Exception as e:
                result = {"status": "error", "error": str(e)}
        else:
            # Fallback to sync
            try:
                from ollama_client.client import get_ollama_client
                client = await asyncio.to_thread(get_ollama_client)
                is_running = await asyncio.to_thread(client.is_running)
                result = {"status": "healthy" if is_running else "unavailable"}
            except Exception as e:
                result = {"status": "error", "error": str(e)}
        
        self._cache_result(cache_key, result)
        return result
    
    async def _check_database_async(self) -> Dict[str, Any]:
        """Async database check with caching."""
        cache_key = "database"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            from database.connection import DatabaseConnection
            is_healthy = await asyncio.to_thread(DatabaseConnection.health_check)
            result = {"status": "healthy" if is_healthy else "unhealthy"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        
        self._cache_result(cache_key, result)
        return result
    
    async def _check_backend_async(self) -> Dict[str, Any]:
        """Async backend health endpoint check with caching."""
        cache_key = "backend"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        if self.use_async:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:8000/health",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = {"status": data.get("status", "unknown")}
                        else:
                            result = {"status": "degraded", "code": response.status}
            except asyncio.TimeoutError:
                result = {"status": "timeout"}
            except Exception as e:
                result = {"status": "error", "error": str(e)}
        else:
            # Fallback to sync
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    result = {"status": data.get("status", "unknown")}
                else:
                    result = {"status": "degraded", "code": response.status_code}
            except requests.exceptions.Timeout:
                result = {"status": "timeout"}
            except Exception as e:
                result = {"status": "error", "error": str(e)}
        
        self._cache_result(cache_key, result)
        return result
    
    def _is_cached(self, key: str) -> bool:
        """Check if result is cached and still valid."""
        if key not in self.cache:
            return False
        age = time.time() - self.cache_timestamps.get(key, 0)
        return age < self.cache_ttl
    
    def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache a health check result."""
        self.cache[key] = result
        self.cache_timestamps[key] = time.time()
    
    def invalidate_cache(self, key: str = None):
        """
        Invalidate cache for a specific service or all services.
        
        Args:
            key: Service name to invalidate, or None for all
        """
        if key:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
        else:
            self.cache.clear()
            self.cache_timestamps.clear()
    
    def get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and valid."""
        if self._is_cached(key):
            return self.cache.get(key)
        return None


# Global instance for reuse
_global_checker: Optional[OptimizedHealthChecker] = None


def get_optimized_health_checker(cache_ttl: int = 30) -> OptimizedHealthChecker:
    """Get or create global optimized health checker instance."""
    global _global_checker
    if _global_checker is None:
        _global_checker = OptimizedHealthChecker(cache_ttl=cache_ttl)
    return _global_checker
