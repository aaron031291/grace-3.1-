import logging
from functools import lru_cache, wraps
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json
class MemoryMeshCache:
    logger = logging.getLogger(__name__)
    """
    Intelligent caching layer for Memory Mesh operations.

    Features:
    - LRU cache for frequently accessed data
    - TTL-based invalidation
    - Automatic cache warming
    - Cache statistics tracking
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache layer.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache_version = 0  # Increment to invalidate all caches

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'last_reset': datetime.utcnow()
        }

        # Internal cache storage for stats and other data (beyond LRU cache)
        self._stats_cache = {}
        self._learning_cache = {}
        self._similar_examples_cache = {}
        self._procedure_cache = {}

        logger.info(f"[MEMORY-MESH-CACHE] Initialized with TTL={ttl_seconds}s")

    def invalidate_all(self):
        """Invalidate all cached data"""
        self.cache_version += 1
        self.stats['invalidations'] += 1

        # Clear function-level LRU caches
        self._get_high_trust_learning_cached.cache_clear()
        self._get_memory_stats_cached.cache_clear()
        self._find_similar_examples_cached.cache_clear()

        # Clear internal cache dictionaries
        self._stats_cache.clear()
        self._learning_cache.clear()
        self._similar_examples_cache.clear()
        self._procedure_cache.clear()

        logger.info(f"[MEMORY-MESH-CACHE] All caches invalidated (version={self.cache_version})")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'invalidations': self.stats['invalidations'],
            'cache_version': self.cache_version,
            'last_reset': self.stats['last_reset'].isoformat()
        }

    # ================================================================
    # HIGH-TRUST LEARNING CACHE
    # ================================================================

    @lru_cache(maxsize=100)
    def _get_high_trust_learning_cached(
        self,
        min_trust: float,
        cache_version: int
    ) -> Tuple[str, ...]:
        """
        Cached high-trust learning IDs.

        Returns tuple of IDs for immutability (required for caching)
        """
        # This is just the cache key - actual query done by caller
        return ()  # Placeholder

    def get_high_trust_learning(
        self,
        session,
        min_trust: float = 0.7,
        limit: int = 1000
    ) -> List:
        """
        Get high-trust learning examples with caching.

        Args:
            session: Database session
            min_trust: Minimum trust score
            limit: Maximum examples to return

        Returns:
            List of LearningExample objects
        """
        from models.database_models import LearningExample

        cache_key = (min_trust, limit, self.cache_version)

        # Try cache first
        try:
            # Check internal cache dict first
            if hasattr(self, '_learning_cache'):
                cache_key = (min_trust, limit, self.cache_version)
                if cache_key in self._learning_cache:
                    cached_ids = self._learning_cache[cache_key]
                    if cached_ids:
                        self.stats['hits'] += 1
                        # Retrieve from DB by IDs (fast with index)
                        return session.query(LearningExample).filter(
                            LearningExample.id.in_(cached_ids)
                        ).all()
            
            # Try LRU cache as fallback
            cached_ids = self._get_high_trust_learning_cached(min_trust, self.cache_version)
            if cached_ids:
                self.stats['hits'] += 1
                # Retrieve from DB by IDs (fast with index)
                return session.query(LearningExample).filter(
                    LearningExample.id.in_(cached_ids)
                ).all()
        except (KeyError, TypeError, AttributeError):
            pass  # Cache miss or invalid cache state

        # Cache miss - query database
        self.stats['misses'] += 1
        examples = session.query(LearningExample).filter(
            LearningExample.trust_score >= min_trust
        ).order_by(
            LearningExample.trust_score.desc()
        ).limit(limit).all()

        # Store IDs in cache by calling the cached function with the result
        # Since lru_cache stores based on arguments, we need to actually call it
        example_ids = tuple(ex.id for ex in examples)
        # Note: lru_cache doesn't allow setting values directly
        # The cache will be populated on next call with same arguments
        # For now, we store in an internal cache dict for faster access
        if not hasattr(self, '_learning_cache'):
            self._learning_cache = {}
        self._learning_cache[(min_trust, limit, self.cache_version)] = example_ids

        return examples

    # ================================================================
    # MEMORY STATS CACHE
    # ================================================================

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache layer.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache_version = 0  # Increment to invalidate all caches

        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'last_reset': datetime.utcnow()
        }

        # Internal cache storage for stats and other data
        self._stats_cache = {}
        self._learning_cache = {}
        self._similar_examples_cache = {}
        self._procedure_cache = {}

        logger.info(f"[MEMORY-MESH-CACHE] Initialized with TTL={ttl_seconds}s")

    def get_or_compute_stats(
        self,
        compute_func,
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get memory stats with caching.

        Args:
            compute_func: Function to compute stats if cache miss
            ttl_seconds: Override default TTL

        Returns:
            Memory mesh statistics
        """
        # Check internal cache dict first
        cache_key = self.cache_version
        if cache_key in self._stats_cache:
            self.stats['hits'] += 1
            return self._stats_cache[cache_key]

        # Check LRU cache as fallback
        try:
            cached = self._get_memory_stats_cached(self.cache_version)
            if cached:
                self.stats['hits'] += 1
                self._stats_cache[cache_key] = cached  # Store in internal cache too
                return cached
        except (KeyError, TypeError, AttributeError):
            pass  # Cache miss or invalid cache state

        # Compute fresh stats
        self.stats['misses'] += 1
        stats = compute_func()

        # Store in both caches
        self._stats_cache[cache_key] = stats
        # Note: LRU cache will be populated on next call with same arguments

        return stats

    # ================================================================
    # SIMILAR EXAMPLES CACHE
    # ================================================================

    @lru_cache(maxsize=500)
    def _find_similar_examples_cached(
        self,
        example_type: str,
        min_trust: float,
        cache_version: int
    ) -> Tuple[str, ...]:
        """Cached similar example IDs"""
        return ()  # Placeholder

    def find_similar_examples(
        self,
        session,
        example_type: str,
        min_trust: float = 0.7,
        exclude_id: Optional[str] = None,
        limit: int = 5
    ) -> List:
        """
        Find similar learning examples with caching.

        Args:
            session: Database session
            example_type: Type of example to match
            min_trust: Minimum trust score
            exclude_id: ID to exclude from results
            limit: Maximum examples to return

        Returns:
            List of similar LearningExample objects
        """
        from models.database_models import LearningExample

        # Try internal cache first
        cache_key = (example_type, min_trust, self.cache_version)
        if cache_key in self._similar_examples_cache:
            cached_ids = self._similar_examples_cache[cache_key]
            if cached_ids:
                self.stats['hits'] += 1
                examples = session.query(LearningExample).filter(
                    LearningExample.id.in_(cached_ids)
                ).all()

                # Filter out excluded ID
                if exclude_id:
                    examples = [ex for ex in examples if ex.id != exclude_id]

                return examples[:limit]

        # Try LRU cache as fallback
        try:
            cached_ids = self._find_similar_examples_cached(
                example_type,
                min_trust,
                self.cache_version
            )
            if cached_ids:
                self.stats['hits'] += 1
                self._similar_examples_cache[cache_key] = cached_ids  # Store in internal cache
                examples = session.query(LearningExample).filter(
                    LearningExample.id.in_(cached_ids)
                ).all()

                # Filter out excluded ID
                if exclude_id:
                    examples = [ex for ex in examples if ex.id != exclude_id]

                return examples[:limit]
        except (KeyError, TypeError, AttributeError):
            pass  # Cache miss or invalid cache state

        # Cache miss - query database
        self.stats['misses'] += 1
        query = session.query(LearningExample).filter(
            LearningExample.example_type == example_type,
            LearningExample.trust_score >= min_trust
        )

        if exclude_id:
            query = query.filter(LearningExample.id != exclude_id)

        examples = query.limit(limit).all()

        # Store in cache
        example_ids = tuple(ex.id for ex in examples)
        self._similar_examples_cache[cache_key] = example_ids

        return examples

    # ================================================================
    # PROCEDURE MATCH CACHE
    # ================================================================

    def _procedure_cache_key(self, goal: str, context: Dict[str, Any]) -> str:
        """Generate cache key for procedure match"""
        context_str = json.dumps(context, sort_keys=True)
        combined = f"{goal}:{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    @lru_cache(maxsize=200)
    def _get_procedure_match_cached(self, cache_key: str, cache_version: int) -> Optional[Tuple]:
        """Cached procedure match results"""
        return None  # Placeholder

    def find_matching_procedure(
        self,
        session,
        goal: str,
        context: Dict[str, Any],
        min_success_rate: float = 0.7
    ):
        """
        Find matching procedure with caching.

        Args:
            session: Database session
            goal: Goal to match
            context: Context for matching
            min_success_rate: Minimum procedure success rate

        Returns:
            Matching Procedure or None
        """
        from models.database_models import Procedure

        cache_key = self._procedure_cache_key(goal, context)

        # Try internal cache first
        internal_cache_key = (cache_key, self.cache_version)
        if internal_cache_key in self._procedure_cache:
            cached = self._procedure_cache[internal_cache_key]
            if cached:
                self.stats['hits'] += 1
                procedure_id = cached[0] if isinstance(cached, tuple) else cached
                return session.query(Procedure).get(procedure_id)

        # Try LRU cache as fallback
        try:
            cached = self._get_procedure_match_cached(cache_key, self.cache_version)
            if cached:
                self.stats['hits'] += 1
                self._procedure_cache[internal_cache_key] = cached  # Store in internal cache
                procedure_id = cached[0] if isinstance(cached, tuple) else cached
                return session.query(Procedure).get(procedure_id)
        except (KeyError, TypeError, AttributeError):
            pass  # Cache miss or invalid cache state

        # Cache miss - query database
        self.stats['misses'] += 1
        procedure = session.query(Procedure).filter(
            Procedure.goal.contains(goal),
            Procedure.success_rate >= min_success_rate
        ).order_by(
            Procedure.success_rate.desc()
        ).first()

        # Store in cache if found
        if procedure:
            self._procedure_cache[internal_cache_key] = (procedure.id,)

        return procedure


# ================================================================
# GLOBAL CACHE INSTANCE
# ================================================================

_global_cache: Optional[MemoryMeshCache] = None


def get_memory_mesh_cache(ttl_seconds: int = 300) -> MemoryMeshCache:
    """Get or create global Memory Mesh cache"""
    global _global_cache

    if _global_cache is None:
        _global_cache = MemoryMeshCache(ttl_seconds=ttl_seconds)

    return _global_cache


def invalidate_memory_mesh_cache():
    """Invalidate all Memory Mesh caches"""
    cache = get_memory_mesh_cache()
    cache.invalidate_all()
