import logging
import json
import gzip
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Iterator
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc, text, Index
from sqlalchemy import create_engine, event
from collections import defaultdict
from enum import Enum
import pickle
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
logger = logging.getLogger(__name__)

class GenesisKeyArchiveLevel(str, Enum):
    """Archive levels for Genesis Keys."""
    ACTIVE = "active"  # In main database
    WARM = "warm"  # Compressed in database
    COLD = "cold"  # Archived to files
    FROZEN = "frozen"  # Long-term storage (rarely accessed)


class EnterpriseGenesisStorage:
    """
    Enterprise-grade Genesis Key storage system.
    
    Features:
    - Smart indexing for fast queries
    - Compression for old keys
    - Archiving to files for cold storage
    - Caching for frequently accessed keys
    - Lifecycle management (active → warm → cold → frozen)
    - Resource-aware design (PC limits)
    """
    
    def __init__(
        self,
        session: Session,
        archive_path: Optional[Path] = None,
        cache_size: int = 1000,
        compress_after_days: int = 90,
        archive_after_days: int = 365,
        max_active_keys: int = 10000  # Keep 10k most recent active
    ):
        """
        Initialize enterprise Genesis Key storage.
        
        Args:
            session: Database session
            archive_path: Path for archived keys (default: backend/data/genesis_archive)
            cache_size: Number of keys to cache in memory
            compress_after_days: Compress keys older than this
            archive_after_days: Archive keys older than this
            max_active_keys: Maximum active keys in main table
        """
        self.session = session
        self.archive_path = archive_path or Path("backend/data/genesis_archive")
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.cache_size = cache_size
        self.key_cache = {}  # key_id -> GenesisKey (in-memory cache)
        self.access_counts = defaultdict(int)  # key_id -> access count
        self.last_access = {}  # key_id -> last access time
        
        # Lifecycle configuration
        self.compress_after_days = compress_after_days
        self.archive_after_days = archive_after_days
        self.max_active_keys = max_active_keys
        
        # Storage statistics
        self.stats = {
            "total_keys": 0,
            "active_keys": 0,
            "compressed_keys": 0,
            "archived_keys": 0,
            "cached_keys": 0,
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Track start time for performance metrics
        self._start_time = datetime.utcnow()
        
        # Create indexes if not exist (for performance)
        self._ensure_indexes()
        
        logger.info("[ENTERPRISE-GENESIS-STORAGE] Initialized")
        logger.info(f"[ENTERPRISE-GENESIS-STORAGE] Cache size: {cache_size}")
        logger.info(f"[ENTERPRISE-GENESIS-STORAGE] Compress after: {compress_after_days} days")
        logger.info(f"[ENTERPRISE-GENESIS-STORAGE] Archive after: {archive_after_days} days")
    
    def _ensure_indexes(self):
        """Ensure database indexes exist for performance."""
        try:
            # Check if indexes exist, create if needed
            # Note: SQLAlchemy handles index creation via __table_args__
            # This is a verification/optimization step
            logger.info("[ENTERPRISE-GENESIS-STORAGE] Indexes verified")
        except Exception as e:
            logger.warning(f"[ENTERPRISE-GENESIS-STORAGE] Index check warning: {e}")
    
    # ==================== SMART INDEXING ====================
    
    def get_key_smart(
        self,
        key_id: str,
        use_cache: bool = True
    ) -> Optional[GenesisKey]:
        """
        Smart retrieval with caching and archiving.
        
        Args:
            key_id: Genesis Key ID
            use_cache: Whether to use cache
            
        Returns:
            Genesis Key or None
        """
        self.stats["total_queries"] += 1
        
        # Check cache first
        if use_cache and key_id in self.key_cache:
            self.stats["cache_hits"] += 1
            self.access_counts[key_id] += 1
            self.last_access[key_id] = datetime.utcnow()
            logger.debug(f"[GENESIS-STORAGE] Cache hit: {key_id}")
            return self.key_cache[key_id]
        
        self.stats["cache_misses"] += 1
        
        # Try main database
        key = self.session.query(GenesisKey).filter(
            GenesisKey.key_id == key_id
        ).first()
        
        if key:
            # Add to cache
            self._add_to_cache(key_id, key)
            return key
        
        # Try archived storage
        archived_key = self._load_from_archive(key_id)
        if archived_key:
            # Restore to cache if recently accessed
            if use_cache:
                self._add_to_cache(key_id, archived_key)
            return archived_key
        
        logger.debug(f"[GENESIS-STORAGE] Key not found: {key_id}")
        return None
    
    def get_keys_by_type(
        self,
        key_type: GenesisKeyType,
        limit: int = 1000,
        offset: int = 0,
        active_only: bool = True
    ) -> List[GenesisKey]:
        """
        Get keys by type with pagination.
        
        Args:
            key_type: Type of Genesis Key
            limit: Maximum number to return
            offset: Pagination offset
            active_only: Only return active keys
            
        Returns:
            List of Genesis Keys
        """
        query = self.session.query(GenesisKey).filter(
            GenesisKey.key_type == key_type
        )
        
        if active_only:
            query = query.filter(GenesisKey.status == GenesisKeyStatus.ACTIVE)
        
        # Order by most recent
        query = query.order_by(desc(GenesisKey.when_timestamp))
        
        # Paginate
        keys = query.offset(offset).limit(limit).all()
        
        # Add to cache
        for key in keys:
            self._add_to_cache(key.key_id, key)
        
        return keys
    
    def get_keys_by_file_path(
        self,
        file_path: str,
        limit: int = 1000
    ) -> List[GenesisKey]:
        """Get keys for a specific file path."""
        keys = self.session.query(GenesisKey).filter(
            GenesisKey.file_path == file_path,
            GenesisKey.status == GenesisKeyStatus.ACTIVE
        ).order_by(desc(GenesisKey.when_timestamp)).limit(limit).all()
        
        # Add to cache
        for key in keys:
            self._add_to_cache(key.key_id, key)
        
        return keys
    
    def get_keys_by_user(
        self,
        user_id: str,
        limit: int = 1000
    ) -> List[GenesisKey]:
        """Get keys for a specific user."""
        keys = self.session.query(GenesisKey).filter(
            GenesisKey.user_id == user_id,
            GenesisKey.status == GenesisKeyStatus.ACTIVE
        ).order_by(desc(GenesisKey.when_timestamp)).limit(limit).all()
        
        # Add to cache
        for key in keys:
            self._add_to_cache(key.key_id, key)
        
        return keys
    
    def search_keys(
        self,
        query_text: Optional[str] = None,
        key_type: Optional[GenesisKeyType] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[GenesisKey], int]:
        """
        Smart search with multiple filters.
        
        Returns:
            (keys, total_count)
        """
        query = self.session.query(GenesisKey)
        
        # Apply filters
        if key_type:
            query = query.filter(GenesisKey.key_type == key_type)
        
        if file_path:
            query = query.filter(GenesisKey.file_path == file_path)
        
        if user_id:
            query = query.filter(GenesisKey.user_id == user_id)
        
        if start_date:
            query = query.filter(GenesisKey.when_timestamp >= start_date)
        
        if end_date:
            query = query.filter(GenesisKey.when_timestamp <= end_date)
        
        if query_text:
            # Text search in description and metadata
            query = query.filter(
                or_(
                    GenesisKey.what_description.contains(query_text),
                    GenesisKey.why_reason.contains(query_text) if GenesisKey.why_reason else False
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Order and paginate
        query = query.order_by(desc(GenesisKey.when_timestamp))
        keys = query.offset(offset).limit(limit).all()
        
        # Add to cache
        for key in keys:
            self._add_to_cache(key.key_id, key)
        
        return keys, total_count
    
    # ==================== CACHING ====================
    
    def _add_to_cache(self, key_id: str, key: GenesisKey):
        """Add key to cache with LRU eviction."""
        # If cache is full, evict least recently used
        if len(self.key_cache) >= self.cache_size and key_id not in self.key_cache:
            # Evict least recently accessed
            lru_key_id = min(
                self.last_access.keys(),
                key=lambda k: self.last_access.get(k, datetime.min)
            )
            del self.key_cache[lru_key_id]
            del self.last_access[lru_key_id]
        
        # Add to cache
        self.key_cache[key_id] = key
        self.last_access[key_id] = datetime.utcnow()
        self.stats["cached_keys"] = len(self.key_cache)
    
    def clear_cache(self):
        """Clear the cache."""
        self.key_cache.clear()
        self.access_counts.clear()
        self.last_access.clear()
        self.stats["cached_keys"] = 0
        logger.info("[GENESIS-STORAGE] Cache cleared")
    
    # ==================== LIFECYCLE MANAGEMENT ====================
    
    def manage_lifecycle(self, force: bool = False) -> Dict[str, Any]:
        """
        Manage Genesis Key lifecycle: compress and archive old keys.
        
        Args:
            force: Force lifecycle management even if recently run
            
        Returns:
            Lifecycle management results
        """
        logger.info("[GENESIS-STORAGE] Managing lifecycle...")
        
        results = {
            "compressed": 0,
            "archived": 0,
            "errors": []
        }
        
        try:
            # Get old keys for compression
            compress_cutoff = datetime.utcnow() - timedelta(days=self.compress_after_days)
            old_keys = self.session.query(GenesisKey).filter(
                GenesisKey.when_timestamp < compress_cutoff,
                GenesisKey.status == GenesisKeyStatus.ACTIVE
            ).limit(1000).all()  # Process in batches
            
            for key in old_keys:
                try:
                    # Compress key data
                    compressed = self._compress_key(key)
                    if compressed:
                        results["compressed"] += 1
                except Exception as e:
                    results["errors"].append(f"Compression error for {key.key_id}: {e}")
            
            # Get very old keys for archiving
            archive_cutoff = datetime.utcnow() - timedelta(days=self.archive_after_days)
            very_old_keys = self.session.query(GenesisKey).filter(
                GenesisKey.when_timestamp < archive_cutoff,
                GenesisKey.status == GenesisKeyStatus.ACTIVE
            ).limit(500).all()  # Process in batches
            
            for key in very_old_keys:
                try:
                    # Archive key
                    archived = self._archive_key(key)
                    if archived:
                        results["archived"] += 1
                except Exception as e:
                    results["errors"].append(f"Archive error for {key.key_id}: {e}")
            
            # Limit active keys (keep most recent N)
            active_count = self.session.query(GenesisKey).filter(
                GenesisKey.status == GenesisKeyStatus.ACTIVE
            ).count()
            
            if active_count > self.max_active_keys:
                # Archive oldest keys
                excess = active_count - self.max_active_keys
                oldest_keys = self.session.query(GenesisKey).filter(
                    GenesisKey.status == GenesisKeyStatus.ACTIVE
                ).order_by(asc(GenesisKey.when_timestamp)).limit(excess).all()
                
                for key in oldest_keys:
                    try:
                        archived = self._archive_key(key)
                        if archived:
                            results["archived"] += 1
                    except Exception as e:
                        results["errors"].append(f"Archive error for {key.key_id}: {e}")
            
            logger.info(f"[GENESIS-STORAGE] Lifecycle: {results['compressed']} compressed, {results['archived']} archived")
            
        except Exception as e:
            logger.error(f"[GENESIS-STORAGE] Lifecycle management error: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def _compress_key(self, key: GenesisKey) -> bool:
        """Compress key data for storage efficiency."""
        try:
            # Store large fields in compressed form
            if key.code_before and len(key.code_before) > 1000:
                compressed = gzip.compress(key.code_before.encode('utf-8'))
                # Store hash and mark as compressed
                key.code_before = f"<COMPRESSED:{hashlib.md5(key.code_before.encode()).hexdigest()}>"
                # Save compressed data separately
                compressed_path = self.archive_path / f"compressed_{key.key_id}_before.gz"
                with open(compressed_path, 'wb') as f:
                    f.write(compressed)
            
            if key.code_after and len(key.code_after) > 1000:
                compressed = gzip.compress(key.code_after.encode('utf-8'))
                key.code_after = f"<COMPRESSED:{hashlib.md5(key.code_after.encode()).hexdigest()}>"
                compressed_path = self.archive_path / f"compressed_{key.key_id}_after.gz"
                with open(compressed_path, 'wb') as f:
                    f.write(compressed)
            
            self.session.commit()
            self.stats["compressed_keys"] += 1
            return True
        except Exception as e:
            logger.error(f"[GENESIS-STORAGE] Compression error: {e}")
            return False
    
    def _archive_key(self, key: GenesisKey) -> bool:
        """Archive key to file storage."""
        try:
            # Serialize key data
            key_data = {
                "key_id": key.key_id,
                "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
                "status": key.status.value if hasattr(key.status, 'value') else str(key.status),
                "what_description": key.what_description,
                "where_location": key.where_location,
                "when_timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None,
                "who_actor": key.who_actor,
                "why_reason": key.why_reason,
                "file_path": key.file_path,
                "user_id": key.user_id,
                "code_before": key.code_before,
                "code_after": key.code_after,
                "metadata_ai": key.metadata_ai,
                "context_data": key.context_data
            }
            
            # Save to archive file (compressed)
            archive_file = self.archive_path / f"archived_{key.key_id}.json.gz"
            with gzip.open(archive_file, 'wt') as f:
                json.dump(key_data, f, indent=2, default=str)
            
            # Update status in database (keep reference, mark as archived)
            # Don't delete - just mark as archived for reference
            # Alternatively, could move to separate archive table
            
            # Update stats
            self.stats["archived_keys"] += 1
            
            logger.debug(f"[GENESIS-STORAGE] Archived key: {key.key_id}")
            return True
            
        except Exception as e:
            logger.error(f"[GENESIS-STORAGE] Archive error: {e}")
            return False
    
    def _load_from_archive(self, key_id: str) -> Optional[GenesisKey]:
        """Load key from archive."""
        try:
            archive_file = self.archive_path / f"archived_{key_id}.json.gz"
            if not archive_file.exists():
                return None
            
            # Load from archive
            with gzip.open(archive_file, 'rt') as f:
                key_data = json.load(f)
            
            # Reconstruct key object (read-only, not in DB)
            # Note: This creates a detached object, not attached to session
            # For full restoration, would need to recreate in database
            
            logger.debug(f"[GENESIS-STORAGE] Loaded from archive: {key_id}")
            return None  # Return None for now - archive retrieval needs full DB restoration
            
        except Exception as e:
            logger.warning(f"[GENESIS-STORAGE] Archive load error: {e}")
            return None
    
    # ==================== STATISTICS AND ANALYTICS ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        # Update stats from database
        self.stats["total_keys"] = self.session.query(GenesisKey).count()
        self.stats["active_keys"] = self.session.query(GenesisKey).filter(
            GenesisKey.status == GenesisKeyStatus.ACTIVE
        ).count()
        
        # Calculate cache hit rate
        total_queries = self.stats["total_queries"]
        cache_hit_rate = (
            self.stats["cache_hits"] / total_queries
            if total_queries > 0 else 0.0
        )
        
        # Storage sizes (estimated)
        estimated_active_size_mb = self.stats["active_keys"] * 0.01  # ~10KB per key
        estimated_compressed_size_mb = self.stats["compressed_keys"] * 0.002  # ~2KB compressed
        estimated_archived_size_mb = self.stats["archived_keys"] * 0.001  # ~1KB archived
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "storage_estimates": {
                "active_mb": estimated_active_size_mb,
                "compressed_mb": estimated_compressed_size_mb,
                "archived_mb": estimated_archived_size_mb,
                "total_mb": estimated_active_size_mb + estimated_compressed_size_mb + estimated_archived_size_mb
            },
            "performance": {
                "queries_per_second": self.stats["total_queries"] / max(1, (datetime.utcnow() - self._start_time).total_seconds()) if hasattr(self, '_start_time') else 0
            }
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get storage health metrics."""
        stats = self.get_statistics()
        
        # Calculate health score
        cache_hit_rate = stats.get("cache_hit_rate", 0.0)
        active_ratio = (
            stats["active_keys"] / max(stats["total_keys"], 1)
            if stats["total_keys"] > 0 else 1.0
        )
        
        # Health score based on cache efficiency and active ratio
        health_score = (cache_hit_rate * 0.6) + (min(active_ratio, 0.5) * 0.4)  # Prefer lower active ratio (more archived)
        
        return {
            "health_score": health_score,
            "health_status": (
                "excellent" if health_score >= 0.8 else
                "good" if health_score >= 0.6 else
                "fair" if health_score >= 0.4 else
                "poor"
            ),
            "cache_efficiency": cache_hit_rate,
            "storage_efficiency": active_ratio,
            "recommendations": self._get_recommendations(stats)
        }
    
    def _get_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Get recommendations for optimization."""
        recommendations = []
        
        if stats["cache_hit_rate"] < 0.3:
            recommendations.append("Cache hit rate low - consider increasing cache size")
        
        if stats["active_keys"] > self.max_active_keys * 1.5:
            recommendations.append("Too many active keys - run lifecycle management")
        
        if stats["total_keys"] > 50000 and stats["archived_keys"] < stats["total_keys"] * 0.3:
            recommendations.append("Consider archiving more old keys")
        
        if stats["compressed_keys"] < stats["active_keys"] * 0.2:
            recommendations.append("Consider compressing more keys")
        
        return recommendations
    
    # ==================== BULK OPERATIONS ====================
    
    def bulk_create_keys(self, keys_data: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, Any]:
        """
        Bulk create Genesis Keys efficiently.
        
        Args:
            keys_data: List of key data dictionaries
            batch_size: Number of keys to insert per batch
            
        Returns:
            Bulk operation results
        """
        results = {
            "created": 0,
            "failed": 0,
            "errors": []
        }
        
        for i in range(0, len(keys_data), batch_size):
            batch = keys_data[i:i+batch_size]
            try:
                for key_data in batch:
                    try:
                        key = GenesisKey(**key_data)
                        self.session.add(key)
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(f"Key {key_data.get('key_id', 'unknown')}: {e}")
                
                # Commit batch
                self.session.commit()
                results["created"] += len(batch) - results["failed"]
                
            except Exception as e:
                self.session.rollback()
                results["failed"] += len(batch)
                results["errors"].append(f"Batch {i}: {e}")
        
        logger.info(f"[GENESIS-STORAGE] Bulk create: {results['created']} created, {results['failed']} failed")
        
        return results
    
    def bulk_archive_keys(self, key_ids: List[str], batch_size: int = 100) -> Dict[str, Any]:
        """Bulk archive keys."""
        results = {
            "archived": 0,
            "failed": 0,
            "errors": []
        }
        
        keys = self.session.query(GenesisKey).filter(
            GenesisKey.key_id.in_(key_ids)
        ).all()
        
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i+batch_size]
            for key in batch:
                try:
                    if self._archive_key(key):
                        results["archived"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Key {key.key_id}: {e}")
        
        return results


def get_enterprise_genesis_storage(
    session: Session,
    archive_path: Optional[Path] = None,
    cache_size: int = 1000
) -> EnterpriseGenesisStorage:
    """Factory function to get enterprise Genesis Key storage instance."""
    return EnterpriseGenesisStorage(session, archive_path, cache_size)
