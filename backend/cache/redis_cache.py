"""
Redis Caching Layer
===================
Provides caching functionality using Redis for improved performance.
Supports TTL, tags, and cache invalidation patterns.
"""

import json
import hashlib
import asyncio
from typing import Any, Optional, Callable, TypeVar, Union, List
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Type variable for generic cache decorator
T = TypeVar('T')


class RedisCache:
    """
    Redis-based caching client with async support.

    Features:
    - Automatic serialization/deserialization
    - TTL (Time To Live) support
    - Cache tags for group invalidation
    - Distributed locking
    - Connection pooling
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "grace:",
        default_ttl: int = 3600,
        max_connections: int = 10
    ):
        """
        Initialize Redis cache client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            prefix: Key prefix for all cache entries
            default_ttl: Default TTL in seconds
            max_connections: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self._client = None
        self._pool = None

    async def connect(self):
        """Establish connection to Redis."""
        try:
            import redis.asyncio as redis

            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

        except ImportError:
            logger.warning("redis package not installed. Using in-memory fallback.")
            self._client = InMemoryFallback()
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._client = InMemoryFallback()

    async def disconnect(self):
        """Close Redis connection."""
        if self._pool:
            await self._pool.disconnect()
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage."""
        if value is None:
            return None
        return json.loads(value)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._client:
            await self.connect()

        try:
            full_key = self._make_key(key)
            value = await self._client.get(full_key)
            if value:
                logger.debug("Cache hit: %s", full_key)
                return self._deserialize(value)
            else:
                logger.debug("Cache miss: %s", full_key)
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
            tags: List of tags for group invalidation (optional)

        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()

        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            expire = ttl or self.default_ttl

            await self._client.setex(full_key, expire, serialized)

            # Store tags for group invalidation
            if tags:
                for tag in tags:
                    tag_key = self._make_key(f"tag:{tag}")
                    await self._client.sadd(tag_key, full_key)
                    await self._client.expire(tag_key, expire)

            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self._client:
            await self.connect()

        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def invalidate_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.

        Args:
            tag: Tag to invalidate

        Returns:
            Number of entries invalidated
        """
        if not self._client:
            await self.connect()

        try:
            tag_key = self._make_key(f"tag:{tag}")
            keys = await self._client.smembers(tag_key)

            if keys:
                count = await self._client.delete(*keys)
                await self._client.delete(tag_key)
                logger.info(f"Invalidated {count} cache entries with tag '{tag}'")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache tag invalidation error: {e}")
            return 0

    async def clear(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Glob pattern (default: all)

        Returns:
            Number of entries cleared
        """
        if not self._client:
            await self.connect()

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                count = await self._client.delete(*keys)
                logger.info(f"Cleared {count} cache entries matching '{pattern}'")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._client:
            await self.connect()

        try:
            full_key = self._make_key(key)
            return await self._client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        if not self._client:
            await self.connect()

        try:
            full_key = self._make_key(key)
            return await self._client.ttl(full_key)
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return -1

    # ==========================================================================
    # Distributed Locking
    # ==========================================================================

    async def acquire_lock(
        self,
        name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: int = 5
    ) -> Optional[str]:
        """
        Acquire a distributed lock.

        Args:
            name: Lock name
            timeout: Lock expiration in seconds
            blocking: Whether to block waiting for lock
            blocking_timeout: Max time to wait for lock

        Returns:
            Lock token if acquired, None otherwise
        """
        if not self._client:
            await self.connect()

        import uuid
        token = str(uuid.uuid4())
        lock_key = self._make_key(f"lock:{name}")

        end_time = asyncio.get_event_loop().time() + blocking_timeout

        while True:
            acquired = await self._client.set(
                lock_key,
                token,
                ex=timeout,
                nx=True
            )

            if acquired:
                return token

            if not blocking:
                return None

            if asyncio.get_event_loop().time() >= end_time:
                return None

            await asyncio.sleep(0.1)

    async def release_lock(self, name: str, token: str) -> bool:
        """
        Release a distributed lock.

        Args:
            name: Lock name
            token: Lock token from acquire_lock

        Returns:
            True if released successfully
        """
        if not self._client:
            return False

        lock_key = self._make_key(f"lock:{name}")

        # Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await self._client.eval(script, 1, lock_key, token)
            return result == 1
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False


class InMemoryFallback:
    """In-memory cache fallback when Redis is unavailable."""

    def __init__(self):
        self._cache = {}
        self._expiry = {}
        self._tags = {}

    async def ping(self):
        return True

    async def get(self, key: str) -> Optional[str]:
        import time
        if key in self._expiry and self._expiry[key] < time.time():
            del self._cache[key]
            del self._expiry[key]
            return None
        return self._cache.get(key)

    async def setex(self, key: str, expire: int, value: str):
        import time
        self._cache[key] = value
        self._expiry[key] = time.time() + expire

    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._cache:
                del self._cache[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count

    async def exists(self, key: str) -> int:
        return 1 if key in self._cache else 0

    async def ttl(self, key: str) -> int:
        import time
        if key in self._expiry:
            remaining = int(self._expiry[key] - time.time())
            return max(0, remaining)
        return -1

    async def sadd(self, key: str, value: str):
        if key not in self._tags:
            self._tags[key] = set()
        self._tags[key].add(value)

    async def smembers(self, key: str):
        return self._tags.get(key, set())

    async def expire(self, key: str, seconds: int):
        import time
        self._expiry[key] = time.time() + seconds

    def scan_iter(self, match: str = "*"):
        import fnmatch
        for key in list(self._cache.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    async def set(self, key: str, value: str, ex: int = None, nx: bool = False):
        if nx and key in self._cache:
            return False
        self._cache[key] = value
        if ex:
            import time
            self._expiry[key] = time.time() + ex
        return True

    async def eval(self, script: str, numkeys: int, *args):
        # Simplified lock release for in-memory
        key = args[0]
        token = args[1]
        if self._cache.get(key) == token:
            del self._cache[key]
            return 1
        return 0


# =============================================================================
# Cache Decorator
# =============================================================================

def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    tags: Optional[List[str]] = None,
    cache_none: bool = False
):
    """
    Decorator for caching function results.

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key
        tags: Tags for group invalidation
        cache_none: Whether to cache None results

    Usage:
        @cached(ttl=300, key_prefix="user", tags=["users"])
        async def get_user(user_id: int):
            return await db.get_user(user_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            key_string = ":".join(key_parts)
            cache_key = hashlib.md5(key_string.encode()).hexdigest()

            # Try to get from cache
            cache = get_cache()
            cached_value = await cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            if result is not None or cache_none:
                await cache.set(cache_key, result, ttl=ttl, tags=tags)

            return result

        return wrapper
    return decorator


# =============================================================================
# Global Cache Instance
# =============================================================================

_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        import os
        _cache_instance = RedisCache(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            prefix=os.getenv("REDIS_PREFIX", "grace:"),
            default_ttl=int(os.getenv("REDIS_DEFAULT_TTL", "3600"))
        )
    return _cache_instance


async def init_cache():
    """Initialize the cache connection."""
    cache = get_cache()
    await cache.connect()


async def close_cache():
    """Close the cache connection."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None
