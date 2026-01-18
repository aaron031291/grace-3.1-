import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

class CachePolicy:
    """Cache policy based on operation characteristics."""
    ttl_seconds: int  # Time to live
    priority: int  # Cache priority (higher = keep longer)
    should_cache: bool  # Whether to cache at all
    cache_key_prefix: str  # Prefix for cache key


class TimeAwareCacheStrategy:
    """
    Determines cache policies based on time predictions.
    
    Strategy:
    - Slow operations (>1s) → Long TTL, high priority
    - Medium operations (100ms-1s) → Medium TTL, medium priority
    - Fast operations (<100ms) → Short TTL, low priority (optional cache)
    """
    
    # Time thresholds (milliseconds)
    SLOW_THRESHOLD_MS = 1000  # 1 second
    MEDIUM_THRESHOLD_MS = 100  # 100ms
    
    # TTL policies (seconds)
    SLOW_OPERATION_TTL = 3600  # 1 hour
    MEDIUM_OPERATION_TTL = 600  # 10 minutes
    FAST_OPERATION_TTL = 60  # 1 minute
    
    def __init__(self):
        logger.info("[TIME-AWARE-CACHE] Initialized")
    
    def get_cache_policy(
        self,
        primitive_type: Optional[PrimitiveType] = None,
        operation_size: float = 1.0,
        model_name: Optional[str] = None,
        estimated_time_ms: Optional[float] = None,
        operation_name: Optional[str] = None
    ) -> CachePolicy:
        """
        Get cache policy for an operation based on time prediction.
        
        Args:
            primitive_type: Primitive operation type
            operation_size: Operation size/complexity
            model_name: Model name (for LLM/embedding operations)
            estimated_time_ms: Pre-computed time estimate (optional)
            operation_name: Operation identifier (for logging)
        
        Returns:
            CachePolicy with TTL and priority
        """
        # Get time estimate if not provided
        if estimated_time_ms is None and TIMESENSE_AVAILABLE and primitive_type:
            try:
                prediction = predict_time(primitive_type, operation_size, model_name)
                if prediction:
                    estimated_time_ms = prediction.p50_ms
            except Exception as e:
                logger.debug(f"[TIME-AWARE-CACHE] Time estimation failed: {e}")
        
        # Default to medium if no estimate
        if estimated_time_ms is None:
            estimated_time_ms = 500  # Assume medium operation
        
        # Determine cache policy based on estimated time
        if estimated_time_ms >= self.SLOW_THRESHOLD_MS:
            # Slow operation - cache aggressively
            policy = CachePolicy(
                ttl_seconds=self.SLOW_OPERATION_TTL,
                priority=10,
                should_cache=True,
                cache_key_prefix=f"slow_{primitive_type.value if primitive_type else operation_name or 'op'}"
            )
            logger.debug(
                f"[TIME-AWARE-CACHE] Slow operation ({estimated_time_ms:.0f}ms): "
                f"Long TTL ({policy.ttl_seconds}s), high priority"
            )
        
        elif estimated_time_ms >= self.MEDIUM_THRESHOLD_MS:
            # Medium operation - moderate caching
            policy = CachePolicy(
                ttl_seconds=self.MEDIUM_OPERATION_TTL,
                priority=5,
                should_cache=True,
                cache_key_prefix=f"medium_{primitive_type.value if primitive_type else operation_name or 'op'}"
            )
            logger.debug(
                f"[TIME-AWARE-CACHE] Medium operation ({estimated_time_ms:.0f}ms): "
                f"Medium TTL ({policy.ttl_seconds}s)"
            )
        
        else:
            # Fast operation - minimal caching (or skip)
            policy = CachePolicy(
                ttl_seconds=self.FAST_OPERATION_TTL,
                priority=1,
                should_cache=True,  # Still cache, but short TTL
                cache_key_prefix=f"fast_{primitive_type.value if primitive_type else operation_name or 'op'}"
            )
            logger.debug(
                f"[TIME-AWARE-CACHE] Fast operation ({estimated_time_ms:.0f}ms): "
                f"Short TTL ({policy.ttl_seconds}s)"
            )
        
        return policy
    
    def should_cache_operation(
        self,
        actual_time_ms: float,
        cache_hit_rate: float = 0.5
    ) -> bool:
        """
        Decide if operation should be cached based on actual time and cache efficiency.
        
        Args:
            actual_time_ms: Actual operation time in milliseconds
            cache_hit_rate: Historical cache hit rate (0-1)
        
        Returns:
            True if operation should be cached
        """
        # Always cache slow operations
        if actual_time_ms >= self.SLOW_THRESHOLD_MS:
            return True
        
        # Cache medium operations if hit rate is good
        if actual_time_ms >= self.MEDIUM_THRESHOLD_MS:
            return cache_hit_rate > 0.3
        
        # Only cache fast operations if hit rate is very high
        return cache_hit_rate > 0.7
    
    def get_optimal_cache_size(
        self,
        available_memory_mb: int,
        avg_operation_time_ms: float,
        cache_hit_rate: float
    ) -> int:
        """
        Calculate optimal cache size based on operation characteristics.
        
        Args:
            available_memory_mb: Available memory in MB
            avg_operation_time_ms: Average operation time
            cache_hit_rate: Historical cache hit rate
        
        Returns:
            Optimal cache size in entries
        """
        # More memory for slower operations
        if avg_operation_time_ms >= self.SLOW_THRESHOLD_MS:
            # Slow operations: use more memory
            max_cache_mb = available_memory_mb * 0.3  # 30% of memory
            entries_per_mb = 100  # Rough estimate
            optimal_size = int(max_cache_mb * entries_per_mb)
        elif avg_operation_time_ms >= self.MEDIUM_THRESHOLD_MS:
            # Medium operations: moderate memory
            max_cache_mb = available_memory_mb * 0.15  # 15% of memory
            entries_per_mb = 200
            optimal_size = int(max_cache_mb * entries_per_mb)
        else:
            # Fast operations: minimal memory
            max_cache_mb = available_memory_mb * 0.05  # 5% of memory
            entries_per_mb = 500
            optimal_size = int(max_cache_mb * entries_per_mb)
        
        # Adjust based on cache hit rate
        if cache_hit_rate > 0.8:
            # High hit rate: can afford larger cache
            optimal_size = int(optimal_size * 1.5)
        elif cache_hit_rate < 0.3:
            # Low hit rate: reduce cache size
            optimal_size = int(optimal_size * 0.5)
        
        return max(10, min(optimal_size, 10000))  # Between 10 and 10,000 entries


# Global cache strategy instance
_cache_strategy: Optional[TimeAwareCacheStrategy] = None


def get_time_aware_cache_strategy() -> TimeAwareCacheStrategy:
    """Get or create global time-aware cache strategy."""
    global _cache_strategy
    if _cache_strategy is None:
        _cache_strategy = TimeAwareCacheStrategy()
    return _cache_strategy
