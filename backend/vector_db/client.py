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
        
    def connect(self) -> bool:
        """
        Connect to Qdrant server (local or cloud).
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Check for cloud URL (Qdrant Cloud uses HTTPS)
            qdrant_url = os.getenv("QDRANT_URL", "")
            
            if qdrant_url and qdrant_url.startswith("https://"):
                # Cloud Qdrant connection
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
                logger.info(f"Connecting to Qdrant Cloud: {qdrant_url[:50]}...")
            else:
                # Local Qdrant connection
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
            
            # Test connection by getting server info
            info = self.client.get_collections()
            self.connected = True
            logger.info(f"[OK] Connected to Qdrant at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[FAIL] Failed to connect to Qdrant: {e}")
            self.connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Qdrant."""
        return self.connected and self.client is not None
    
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
        if not self.is_connected():
            logger.error("Not connected to Qdrant")
            return False
        
        try:
            # Check if collection already exists
            collections = self.client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            
            # Map distance metric to Qdrant enum
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "manhattan": Distance.MANHATTAN,
                "dot": Distance.DOT,
            }
            distance = distance_map.get(distance_metric.lower(), Distance.COSINE)
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
                **kwargs
            )
            logger.info(f"[OK] Created collection '{collection_name}' with vector size {vector_size}")
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
        if not self.is_connected():
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
        if not self.is_connected():
            logger.error("Not connected to Qdrant")
            return False
        
        try:
            # Convert to PointStruct format
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
        if not self.is_connected():
            logger.error("Not connected to Qdrant")
            return []
        
        try:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                **kwargs
            )
            
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results.points
            ]
        
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
        if not self.is_connected():
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
        if not self.is_connected():
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
        if not self.is_connected():
            return False
        
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"[OK] Deleted collection '{collection_name}'")
            return True
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to delete collection: {e}")
            return False
    
    def scroll(
        self,
        collection_name: str,
        limit: int = 100,
        with_vectors: bool = False,
        with_payload: bool = True,
        offset: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Scroll through all points in a collection (paginated).

        Used by Reverse KNN and other exhaustive search operations.
        """
        if not self.is_connected():
            logger.error("Not connected to Qdrant")
            return []

        try:
            results, _next_offset = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_vectors=with_vectors,
                with_payload=with_payload,
                offset=offset,
                **kwargs,
            )

            return [
                {
                    "id": point.id,
                    "vector": point.vector if with_vectors else None,
                    "payload": point.payload if with_payload else {},
                }
                for point in results
            ]
        except Exception as e:
            logger.error(f"[FAIL] Scroll failed on '{collection_name}': {e}")
            return []

    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        if not self.is_connected():
            return []
        
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        
        except Exception as e:
            logger.error(f"[FAIL] Failed to list collections: {e}")
            return []


def get_qdrant_client(
    host: str = None,
    port: int = None,
    api_key: Optional[str] = None,
    force_new: bool = False,
) -> QdrantVectorDB:
    """
    Get or create a Qdrant client instance (singleton pattern).
    Reads from settings/env if not provided. Supports both local and cloud Qdrant.
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
        
        _qdrant_client = QdrantVectorDB(host=host, port=port, api_key=api_key)
        _qdrant_client.connect()
    
    return _qdrant_client
