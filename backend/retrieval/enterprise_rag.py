import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict, deque
import hashlib
import json
from retrieval.retriever import DocumentRetriever
from models.database_models import Document, DocumentChunk
from embedding import EmbeddingModel
logger = logging.getLogger(__name__)

class EnterpriseRAG:
    """
    Enterprise-grade RAG system.
    
    Features:
    - Smart retrieval with caching
    - Retrieval analytics
    - Query prediction
    - Performance optimization
    - Resource efficiency
    """
    
    def __init__(
        self,
        session: Session,
        retriever: DocumentRetriever,
        cache_size: int = 100,
        max_cache_age_seconds: int = 3600
    ):
        """Initialize enterprise RAG."""
        self.session = session
        self.retriever = retriever
        self.cache_size = cache_size
        self.max_cache_age = max_cache_age_seconds
        
        # Query cache
        self._query_cache: Dict[str, Tuple[List[Dict], datetime]] = {}
        
        # Query history for prediction
        self._query_history: deque = deque(maxlen=1000)
        
        # Analytics
        self._query_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_results": 0.0,
            "avg_score": 0.0
        }
        
        logger.info(
            f"[ENTERPRISE-RAG] Initialized: "
            f"cache_size={cache_size}, max_age={max_cache_age_seconds}s"
        )
    
    def _hash_query(self, query: str, limit: int, threshold: float) -> str:
        """Create hash of query for caching."""
        query_str = f"{query}_{limit}_{threshold}"
        return hashlib.md5(query_str.encode()).hexdigest()[:16]
    
    def smart_retrieve(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        use_cache: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Smart retrieval with caching and analytics.
        
        Args:
            query: Query text
            limit: Maximum results
            score_threshold: Minimum similarity score
            use_cache: Whether to use cache
            context: Optional context for relevance
            
        Returns:
            Retrieval results with metadata
        """
        logger.info(f"[ENTERPRISE-RAG] Smart retrieve: '{query[:50]}...'")
        
        # Check cache
        cache_key = self._hash_query(query, limit, score_threshold)
        if use_cache and cache_key in self._query_cache:
            cached_results, cached_time = self._query_cache[cache_key]
            age = (datetime.utcnow() - cached_time).total_seconds()
            
            if age < self.max_cache_age:
                self._query_stats["cache_hits"] += 1
                logger.debug(f"[ENTERPRISE-RAG] Cache hit (age: {age:.1f}s)")
                return {
                    "results": cached_results,
                    "cached": True,
                    "cache_age_seconds": age,
                    "query": query
                }
        
        # Cache miss - perform retrieval
        self._query_stats["cache_misses"] += 1
        self._query_stats["total_queries"] += 1
        
        # Retrieve
        results = self.retriever.retrieve(
            query=query,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Update cache
        if use_cache and len(self._query_cache) < self.cache_size:
            self._query_cache[cache_key] = (results, datetime.utcnow())
        
        # Record in history
        self._query_history.append({
            "query": query,
            "results_count": len(results),
            "timestamp": datetime.utcnow(),
            "context": context
        })
        
        # Update stats
        if results:
            avg_score = sum(r.get("score", 0) for r in results) / len(results)
            self._query_stats["avg_results"] = (
                (self._query_stats["avg_results"] * (self._query_stats["total_queries"] - 1) +
                 len(results)) / self._query_stats["total_queries"]
            )
            self._query_stats["avg_score"] = (
                (self._query_stats["avg_score"] * (self._query_stats["total_queries"] - 1) +
                 avg_score) / self._query_stats["total_queries"]
            )
        
        return {
            "results": results,
            "cached": False,
            "query": query,
            "results_count": len(results)
        }
    
    def predict_queries(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Predict likely queries based on history and context.
        
        Args:
            context: Optional context for prediction
            
        Returns:
            Predicted queries with confidence
        """
        logger.info("[ENTERPRISE-RAG] Predicting queries...")
        
        # Count query frequency
        query_counts = defaultdict(int)
        for entry in self._query_history:
            query_counts[entry["query"]] += 1
        
        # Get top queries
        top_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        predictions = []
        max_count = top_queries[0][1] if top_queries else 1
        
        for query, count in top_queries:
            confidence = min(1.0, count / max_count)
            predictions.append({
                "query": query,
                "confidence": confidence,
                "frequency": count,
                "prediction_type": "historical"
            })
        
        logger.info(f"[ENTERPRISE-RAG] Predicted {len(predictions)} queries")
        
        return predictions
    
    def get_retrieval_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive retrieval analytics.
        
        Returns:
            Analytics dashboard
        """
        logger.info("[ENTERPRISE-RAG] Generating analytics...")
        
        # Cache statistics
        cache_hit_rate = (
            self._query_stats["cache_hits"] / 
            (self._query_stats["cache_hits"] + self._query_stats["cache_misses"])
            if (self._query_stats["cache_hits"] + self._query_stats["cache_misses"]) > 0 else 0.0
        )
        
        # Collection statistics
        collection_info = self.retriever.qdrant_client.get_collection_info(
            self.retriever.collection_name
        )
        vector_count = collection_info.get("points_count", 0) if collection_info else 0
        
        # Recent queries
        recent_queries = [
            entry for entry in self._query_history
            if (datetime.utcnow() - entry["timestamp"]).total_seconds() < 3600
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "query_statistics": {
                "total_queries": self._query_stats["total_queries"],
                "cache_hits": self._query_stats["cache_hits"],
                "cache_misses": self._query_stats["cache_misses"],
                "cache_hit_rate": cache_hit_rate,
                "avg_results_per_query": self._query_stats["avg_results"],
                "avg_score": self._query_stats["avg_score"]
            },
            "collection_statistics": {
                "vector_count": vector_count,
                "collection_name": self.retriever.collection_name
            },
            "recent_activity": {
                "queries_last_hour": len(recent_queries),
                "cache_size": len(self._query_cache),
                "history_size": len(self._query_history)
            }
        }
    
    def optimize_cache(self):
        """Optimize cache by removing old entries."""
        logger.info("[ENTERPRISE-RAG] Optimizing cache...")
        
        now = datetime.utcnow()
        to_remove = []
        
        for key, (results, cached_time) in self._query_cache.items():
            age = (now - cached_time).total_seconds()
            if age > self.max_cache_age:
                to_remove.append(key)
        
        for key in to_remove:
            del self._query_cache[key]
        
        logger.info(f"[ENTERPRISE-RAG] Removed {len(to_remove)} old cache entries")


def get_enterprise_rag(
    session: Session,
    retriever: DocumentRetriever,
    cache_size: int = 100
) -> EnterpriseRAG:
    """Factory function to get enterprise RAG."""
    return EnterpriseRAG(
        session=session,
        retriever=retriever,
        cache_size=cache_size
    )
