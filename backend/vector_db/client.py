"""
Qdrant vector database client for managing vector embeddings and search.
Handles connection to Qdrant, collection management, and vector operations.
"""

import os
from typing import List, Dict, Optional, Any, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging

logger = logging.getLogger(__name__)

# Global Qdrant client instance
_qdrant_client: Optional['QdrantVectorDB'] = None


class QdrantVectorDB:
    """Qdrant vector database client wrapper."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Qdrant client.
        
        Args:
            host: Qdrant server host (default: localhost)
            port: Qdrant server port (default: 6333)
            api_key: Optional API key for Qdrant authentication
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self.client: Optional[QdrantClient] = None
        self.connected = False
        
    def connect(self, retries: int = 5, retry_delay: float = 2.0) -> bool:
        """
        Connect to Qdrant server (local or cloud).
        Retries with backoff so Qdrant has time to start (e.g. after docker start).

        Args:
            retries: Number of connection attempts.
            retry_delay: Seconds to wait between attempts.

        Returns:
            bool: True if connection successful, False otherwise
        """
        import time
        last_error = None
        # Cloud API from env: use QDRANT_URL (and QDRANT_API_KEY) when set in .env
        try:
            from settings import settings
            qdrant_url = (getattr(settings, "QDRANT_URL", None) or "").strip()
        except Exception:
            qdrant_url = (os.getenv("QDRANT_URL") or "").strip()

        for attempt in range(1, retries + 1):
            try:
                # Check for cloud URL (Qdrant Cloud uses HTTPS) — use cloud API from env when set
                if qdrant_url and qdrant_url.startswith("https://"):
                    self.client = QdrantClient(
                        url=qdrant_url,
                        api_key=self.api_key,
                        timeout=self.timeout,
                    )
                    logger.info(f"Connecting to Qdrant Cloud: {qdrant_url[:50]}...")
                else:
                    self.client = QdrantClient(
                        host=self.host,
                        port=self.port,
                        api_key=self.api_key,
                        timeout=self.timeout,
                    )

                # Test connection
                self.client.get_collections()
                self.connected = True
                if qdrant_url and qdrant_url.startswith("https://"):
                    logger.info("[OK] Connected to Qdrant Cloud")
                else:
                    logger.info(f"[OK] Connected to Qdrant at {self.host}:{self.port}")
                return True
            except Exception as e:
                last_error = e
                self.client = None
                self.connected = False
                if attempt < retries:
                    logger.warning(
                        "[Qdrant] Connection attempt %s/%s failed: %s. Retrying in %.1fs...",
                        attempt, retries, e, retry_delay,
                    )
                    time.sleep(retry_delay)
                else:
                    if qdrant_url and qdrant_url.startswith("https://"):
                        logger.error(
                            "[FAIL] Failed to connect to Qdrant Cloud after %s attempts: %s. "
                            "Check QDRANT_URL and QDRANT_API_KEY in backend/.env.",
                            retries, e,
                        )
                    else:
                        logger.error(
                            "[FAIL] Failed to connect to Qdrant after %s attempts: %s. "
                            "Ensure Qdrant is running (e.g. .\\start_services.bat qdrant or docker start qdrant), or set QDRANT_URL + QDRANT_API_KEY for Cloud.",
                            retries, e,
                        )
        return False
    
    def is_connected(self) -> bool:
        """Check if connected to Qdrant."""
        return self.connected and self.client is not None

    def ensure_connected(self, retries: int = 2, retry_delay: float = 1.0) -> bool:
        """
        Ensure we have a live connection. If not connected, try to connect.
        Call this when you want to give Qdrant a chance to come back (e.g. after startup).
        """
        if self.is_connected():
            return True
        return self.connect(retries=retries, retry_delay=retry_delay)

    def _is_connection_error(self, e: Exception) -> bool:
        """Heuristic: exception likely due to connection/transport failure."""
        if e is None:
            return False
        msg = str(e).lower()
        err_type = type(e).__name__
        return (
            "connection" in msg or "timeout" in msg or "refused" in msg
            or "reset" in msg or "closed" in msg or "unreachable" in msg
            or err_type in ("ConnectionError", "TimeoutError", "ConnectError")
        )

    def _with_reconnect(self, op, *args, **kwargs):
        """
        Run op(*args, **kwargs). On connection-like failure, reconnect once and retry.
        Returns (result, True) on success, (None, False) on failure.
        """
        try:
            return op(*args, **kwargs), True
        except Exception as e:
            if not self._is_connection_error(e):
                raise
            logger.warning("[Qdrant] Operation failed (connection-like), reconnecting once: %s", e)
            self.client = None
            self.connected = False
            if not self.connect(retries=2, retry_delay=1.0):
                raise
            return op(*args, **kwargs), True

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance_metric: str = "cosine",
        **kwargs
    ) -> bool:
        """
        Create a new collection in Qdrant.
        
        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
            distance_metric: Distance metric (cosine, euclidean, manhattan, dot)
            **kwargs: Additional parameters for collection creation
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected() and not self.ensure_connected():
            logger.error("Not connected to Qdrant")
            return False

        def _do_create():
            collections = self.client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "manhattan": Distance.MANHATTAN,
                "dot": Distance.DOT,
            }
            distance = distance_map.get(distance_metric.lower(), Distance.COSINE)
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
                **kwargs
            )
            logger.info(f"[OK] Created collection '{collection_name}' with vector size {vector_size}")
            return True

        try:
            self._with_reconnect(_do_create)
            return True
        except Exception as e:
            logger.error(f"[FAIL] Failed to create collection '{collection_name}': {e}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            bool: True if collection exists, False otherwise
        """
        if not self.is_connected() and not self.ensure_connected():
            return False
        try:
            collections = self.client.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"[FAIL] Error checking collection existence: {e}")
            return False
    
    def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[Tuple[int, List[float], Dict[str, Any]]],
        **kwargs
    ) -> bool:
        """
        Upsert vectors into a collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of tuples (id, vector, payload)
            **kwargs: Additional parameters for upsert operation
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected() and not self.ensure_connected():
            logger.error("Not connected to Qdrant")
            return False

        def _do_upsert():
            points = [
                PointStruct(id=v[0], vector=v[1], payload=v[2])
                for v in vectors
            ]
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                **kwargs
            )
            logger.info(f"[OK] Upserted {len(vectors)} vectors to '{collection_name}'")
            return True

        try:
            self._with_reconnect(_do_upsert)
            return True
        except Exception as e:
            logger.error(f"[FAIL] Failed to upsert vectors: {e}")
            return False
    
    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score
            **kwargs: Additional search parameters
            
        Returns:
            List of search results with scores and payloads
        """
        if not self.is_connected() and not self.ensure_connected():
            logger.error("Not connected to Qdrant")
            return []

        def _do_search():
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                **kwargs
            )
            return [
                {"id": result.id, "score": result.score, "payload": result.payload}
                for result in results.points
            ]

        try:
            out, _ = self._with_reconnect(_do_search)
            return out or []
        except Exception as e:
            logger.error(f"[FAIL] Search failed: {e}")
            return []
    
    def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[int],
        **kwargs
    ) -> bool:
        """
        Delete vectors from a collection.
        
        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to delete
            **kwargs: Additional parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected() and not self.ensure_connected():
            logger.error("Not connected to Qdrant")
            return False
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=vector_ids,
                **kwargs
            )
            logger.info(f"[OK] Deleted {len(vector_ids)} vectors from '{collection_name}'")
            return True
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to delete vectors: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection information or None if error
        """
        if not self.is_connected() and not self.ensure_connected():
            return None
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "config": info.config,
            }
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to get collection info: {e}")
            return None
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected() and not self.ensure_connected():
            return False
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"[OK] Deleted collection '{collection_name}'")
            return True
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to delete collection: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        if not self.is_connected() and not self.ensure_connected():
            return []
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to list collections: {e}")
            return []

    def get_collections(self):
        """
        Proxy to raw QdrantClient.get_collections() for backwards compatibility.
        """
        if not self.is_connected() and not self.ensure_connected():
            class EmptyCollections:
                collections = []
            return EmptyCollections()
        try:
            return self.client.get_collections()
        except Exception as e:
            logger.error(f"[FAIL] Failed to get collections: {e}")
            class EmptyCollections:
                collections = []
            return EmptyCollections()


def get_qdrant_client(
    host: str = None,
    port: int = None,
    api_key: Optional[str] = None,
    force_new: bool = False,
) -> QdrantVectorDB:
    """
    Get or create a Qdrant client instance (singleton pattern).
    Reads from settings/env if not provided. Supports both local and cloud Qdrant.
    Uses circuit breaker so repeated connection failures fail fast and allow recovery.
    """
    global _qdrant_client

    if _qdrant_client is None or force_new:
        # Read from settings
        try:
            from settings import settings
            host = host or getattr(settings, 'QDRANT_HOST', 'localhost')
            port = port or getattr(settings, 'QDRANT_PORT', 6333)
            api_key = api_key or getattr(settings, 'QDRANT_API_KEY', '') or None
        except Exception:
            host = host or os.getenv('QDRANT_HOST', 'localhost')
            port = port or int(os.getenv('QDRANT_PORT', '6333'))
            api_key = api_key or os.getenv('QDRANT_API_KEY', '') or None

        client = QdrantVectorDB(host=host, port=port, api_key=api_key)

        def _connect_raise():
            if not client.connect():
                raise ConnectionError("Qdrant connection failed")

        try:
            from core.resilience import get_breaker
            cb = get_breaker("qdrant", failure_threshold=3, reset_timeout=20)
            cb.call(_connect_raise)
        except Exception:
            client.connect()
        _qdrant_client = client

    # Lazy reconnect: if singleton exists but is disconnected, try once so we recover when Qdrant comes back
    if not _qdrant_client.is_connected():
        _qdrant_client.ensure_connected(retries=2, retry_delay=1.0)

    return _qdrant_client
