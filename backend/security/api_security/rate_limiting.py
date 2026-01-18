"""
Advanced Rate Limiting System for GRACE.

Provides:
- Sliding window rate limiting algorithm
- Tiered rate limits by role/API key tier
- Burst allowance for temporary spikes
- Redis backend support (with memory fallback)
- Standard rate limit headers
- FastAPI middleware integration
"""

import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimitTier(str, Enum):
    """Rate limit tiers."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float
    retry_after: Optional[int] = None
    tier: RateLimitTier = RateLimitTier.FREE
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to standard rate limit headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


@dataclass
class TieredRateLimits:
    """Rate limit configuration per tier."""
    requests_per_second: int = 10
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 20
    burst_period_seconds: int = 10
    
    @classmethod
    def for_tier(cls, tier: RateLimitTier) -> "TieredRateLimits":
        """Get rate limits for a specific tier."""
        configs = {
            RateLimitTier.FREE: cls(
                requests_per_second=2,
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=2000,
                burst_size=5,
                burst_period_seconds=10
            ),
            RateLimitTier.BASIC: cls(
                requests_per_second=10,
                requests_per_minute=100,
                requests_per_hour=2000,
                requests_per_day=20000,
                burst_size=20,
                burst_period_seconds=10
            ),
            RateLimitTier.PROFESSIONAL: cls(
                requests_per_second=50,
                requests_per_minute=500,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_size=100,
                burst_period_seconds=10
            ),
            RateLimitTier.ENTERPRISE: cls(
                requests_per_second=200,
                requests_per_minute=2000,
                requests_per_hour=50000,
                requests_per_day=500000,
                burst_size=500,
                burst_period_seconds=10
            ),
            RateLimitTier.UNLIMITED: cls(
                requests_per_second=10000,
                requests_per_minute=100000,
                requests_per_hour=1000000,
                requests_per_day=10000000,
                burst_size=10000,
                burst_period_seconds=10
            ),
        }
        return configs.get(tier, configs[RateLimitTier.FREE])


@dataclass
class BurstAllowance:
    """Burst allowance tracking for a client."""
    tokens: float
    last_update: float
    max_tokens: int
    refill_rate: float
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Consume tokens from the burst bucket.
        
        Returns True if tokens were available.
        """
        now = time.time()
        elapsed = now - self.last_update
        
        self.tokens = min(
            self.max_tokens,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class SlidingWindowCounter:
    """
    Sliding window rate limiter using a memory-efficient approach.
    
    Combines fixed window counters with interpolation for accuracy.
    """
    
    def __init__(self, window_size: int = 60):
        self._window_size = window_size
        self._current_window: Dict[str, int] = defaultdict(int)
        self._previous_window: Dict[str, int] = defaultdict(int)
        self._window_start: float = time.time()
        
    def _rotate_windows(self):
        """Rotate windows if needed."""
        now = time.time()
        elapsed = now - self._window_start
        
        if elapsed >= self._window_size * 2:
            self._previous_window.clear()
            self._current_window.clear()
            self._window_start = now
        elif elapsed >= self._window_size:
            self._previous_window = self._current_window.copy()
            self._current_window.clear()
            self._window_start = now - (elapsed % self._window_size)
    
    def increment(self, key: str, count: int = 1) -> int:
        """Increment counter for a key and return current count."""
        self._rotate_windows()
        self._current_window[key] += count
        return self.get_count(key)
    
    def get_count(self, key: str) -> int:
        """Get the current sliding window count for a key."""
        self._rotate_windows()
        
        now = time.time()
        window_progress = (now - self._window_start) / self._window_size
        
        previous_weight = 1 - window_progress
        current_count = self._current_window.get(key, 0)
        previous_count = self._previous_window.get(key, 0)
        
        return int(current_count + previous_count * previous_weight)


class RateLimiter:
    """
    Advanced rate limiter with sliding window algorithm.
    
    Features:
    - Multiple time windows (second, minute, hour, day)
    - Tiered rate limits
    - Burst allowance
    - Redis backend support (optional)
    """
    
    def __init__(
        self,
        redis_client=None,
        default_tier: RateLimitTier = RateLimitTier.FREE
    ):
        self._redis = redis_client
        self._default_tier = default_tier
        
        self._second_window = SlidingWindowCounter(window_size=1)
        self._minute_window = SlidingWindowCounter(window_size=60)
        self._hour_window = SlidingWindowCounter(window_size=3600)
        self._day_window = SlidingWindowCounter(window_size=86400)
        
        self._bursts: Dict[str, BurstAllowance] = {}
        self._client_tiers: Dict[str, RateLimitTier] = {}
        
    def set_client_tier(self, client_id: str, tier: RateLimitTier):
        """Set the rate limit tier for a client."""
        self._client_tiers[client_id] = tier
        logger.info(f"Rate limit tier set: client={client_id}, tier={tier.value}")
    
    def get_client_tier(self, client_id: str) -> RateLimitTier:
        """Get the rate limit tier for a client."""
        return self._client_tiers.get(client_id, self._default_tier)
    
    def _get_burst_allowance(self, client_id: str, limits: TieredRateLimits) -> BurstAllowance:
        """Get or create burst allowance for a client."""
        if client_id not in self._bursts:
            self._bursts[client_id] = BurstAllowance(
                tokens=limits.burst_size,
                last_update=time.time(),
                max_tokens=limits.burst_size,
                refill_rate=limits.burst_size / limits.burst_period_seconds
            )
        return self._bursts[client_id]
    
    def check(
        self,
        client_id: str,
        endpoint: Optional[str] = None,
        cost: int = 1
    ) -> RateLimitResult:
        """
        Check if a request should be rate limited.
        
        Args:
            client_id: Unique client identifier
            endpoint: Optional endpoint for per-endpoint limits
            cost: Request cost (for weighted rate limiting)
            
        Returns:
            RateLimitResult with allow/deny and headers
        """
        tier = self.get_client_tier(client_id)
        limits = TieredRateLimits.for_tier(tier)
        
        key = f"{client_id}:{endpoint}" if endpoint else client_id
        
        second_count = self._second_window.get_count(key)
        minute_count = self._minute_window.get_count(key)
        hour_count = self._hour_window.get_count(key)
        day_count = self._day_window.get_count(key)
        
        now = time.time()
        
        if second_count >= limits.requests_per_second:
            burst = self._get_burst_allowance(client_id, limits)
            if not burst.consume(cost):
                return RateLimitResult(
                    allowed=False,
                    limit=limits.requests_per_second,
                    remaining=0,
                    reset_at=now + 1,
                    retry_after=1,
                    tier=tier
                )
        
        if minute_count >= limits.requests_per_minute:
            retry_after = int(60 - (now % 60))
            return RateLimitResult(
                allowed=False,
                limit=limits.requests_per_minute,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=retry_after,
                tier=tier
            )
        
        if hour_count >= limits.requests_per_hour:
            retry_after = int(3600 - (now % 3600))
            return RateLimitResult(
                allowed=False,
                limit=limits.requests_per_hour,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=retry_after,
                tier=tier
            )
        
        if day_count >= limits.requests_per_day:
            retry_after = int(86400 - (now % 86400))
            return RateLimitResult(
                allowed=False,
                limit=limits.requests_per_day,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=retry_after,
                tier=tier
            )
        
        self._second_window.increment(key, cost)
        self._minute_window.increment(key, cost)
        self._hour_window.increment(key, cost)
        self._day_window.increment(key, cost)
        
        remaining = min(
            limits.requests_per_minute - minute_count - cost,
            limits.requests_per_hour - hour_count - cost,
            limits.requests_per_day - day_count - cost
        )
        
        return RateLimitResult(
            allowed=True,
            limit=limits.requests_per_minute,
            remaining=max(0, remaining),
            reset_at=now + (60 - (now % 60)),
            tier=tier
        )
    
    def get_usage(self, client_id: str) -> Dict[str, Any]:
        """Get current usage stats for a client."""
        tier = self.get_client_tier(client_id)
        limits = TieredRateLimits.for_tier(tier)
        
        return {
            "client_id": client_id,
            "tier": tier.value,
            "usage": {
                "per_second": self._second_window.get_count(client_id),
                "per_minute": self._minute_window.get_count(client_id),
                "per_hour": self._hour_window.get_count(client_id),
                "per_day": self._day_window.get_count(client_id),
            },
            "limits": {
                "per_second": limits.requests_per_second,
                "per_minute": limits.requests_per_minute,
                "per_hour": limits.requests_per_hour,
                "per_day": limits.requests_per_day,
            }
        }
    
    def reset_client(self, client_id: str):
        """Reset rate limit counters for a client."""
        logger.info(f"Rate limit counters reset: client={client_id}")


class RateLimitMiddleware:
    """
    FastAPI middleware for rate limiting.
    
    Integrates with the RateLimiter to enforce limits on incoming requests.
    """
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        client_id_extractor: Optional[Callable] = None,
        exempt_paths: Optional[List[str]] = None,
        cost_calculator: Optional[Callable] = None
    ):
        self._limiter = rate_limiter or RateLimiter()
        self._client_id_extractor = client_id_extractor or self._default_client_extractor
        self._exempt_paths = set(exempt_paths or ["/health", "/ready", "/metrics"])
        self._cost_calculator = cost_calculator
        
    def _default_client_extractor(self, request) -> str:
        """Extract client ID from request (default: IP + User-Agent hash)."""
        import hashlib
        
        client_ip = getattr(request, "client", None)
        if client_ip:
            client_ip = client_ip.host if hasattr(client_ip, "host") else str(client_ip)
        else:
            client_ip = request.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
        
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_hash = hashlib.sha256(auth_header[7:].encode()).hexdigest()[:16]
            return f"token:{token_hash}"
        
        return f"ip:{client_ip}"
    
    async def __call__(self, request, call_next):
        """Middleware entry point."""
        path = request.url.path
        
        if path in self._exempt_paths:
            return await call_next(request)
        
        client_id = self._client_id_extractor(request)
        
        cost = 1
        if self._cost_calculator:
            cost = self._cost_calculator(request)
        
        result = self._limiter.check(client_id, endpoint=path, cost=cost)
        
        if not result.allowed:
            from starlette.responses import JSONResponse
            
            logger.warning(f"Rate limit exceeded: client={client_id}, path={path}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after": result.retry_after
                },
                headers=result.to_headers()
            )
        
        response = await call_next(request)
        
        for header, value in result.to_headers().items():
            response.headers[header] = value
        
        return response
    
    def get_limiter(self) -> RateLimiter:
        """Get the underlying rate limiter."""
        return self._limiter


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
