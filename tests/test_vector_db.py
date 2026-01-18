"""
Test Script for Vector Database Client

Tests the complete integration of:
1. Client initialization
2. Insert vectors (upsert)
3. Search/query vectors
4. Delete vectors
5. Collection management
6. Error handling for connection issues
"""

import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List, Dict, Any

sys.path.insert(0, 'backend')


class MockCollectionInfo:
    """Mock for collection info response."""
    def __init__(self, name: str):
        self.name = name


class MockCollectionsResponse:
    """Mock for get_collections response."""
    def __init__(self, collections: List[str]):
        self.collections = [MockCollectionInfo(name) for name in collections]


class MockSearchResult:
    """Mock for search result."""
    def __init__(self, id: int, score: float, payload: Dict[str, Any]):
        self.id = id
        self.score = score
        self.payload = payload


class MockQueryResponse:
    """Mock for query_points response."""
    def __init__(self, points: List[MockSearchResult]):
        self.points = points


class MockCollectionInfoResponse:
    """Mock for get_collection response."""
    def __init__(self, points_count: int = 100, vectors_count: int = 100):
        self.points_count = points_count
        self.vectors_count = vectors_count
        self.config = {"vector_size": 128, "distance": "cosine"}


class TestQdrantVectorDBInitialization:
    """Test class for QdrantVectorDB initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        
        assert db.host == "localhost"
        assert db.port == 6333
        assert db.api_key is None
        assert db.timeout == 30
        assert db.client is None
        assert db.connected is False
    
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB(
            host="custom-host",
            port=6334,
            api_key="test-api-key",
            timeout=60
        )
        
        assert db.host == "custom-host"
        assert db.port == 6334
        assert db.api_key == "test-api-key"
        assert db.timeout == 60
    
    def test_is_connected_when_not_connected(self):
        """Test is_connected returns False when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        
        assert db.is_connected() is False


class TestQdrantVectorDBConnection:
    """Test class for connection functionality."""
    
    @patch('vector_db.client.QdrantClient')
    def test_connect_success(self, mock_qdrant_client):
        """Test successful connection to Qdrant."""
        from vector_db.client import QdrantVectorDB
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        db = QdrantVectorDB()
        result = db.connect()
        
        assert result is True
        assert db.connected is True
        assert db.is_connected() is True
        mock_qdrant_client.assert_called_once_with(
            host="localhost",
            port=6333,
            api_key=None,
            timeout=30
        )
    
    @patch('vector_db.client.QdrantClient')
    def test_connect_failure(self, mock_qdrant_client):
        """Test failed connection to Qdrant."""
        from vector_db.client import QdrantVectorDB
        
        mock_qdrant_client.side_effect = Exception("Connection refused")
        
        db = QdrantVectorDB()
        result = db.connect()
        
        assert result is False
        assert db.connected is False
        assert db.is_connected() is False
    
    @patch('vector_db.client.QdrantClient')
    def test_connect_with_api_key(self, mock_qdrant_client):
        """Test connection with API key."""
        from vector_db.client import QdrantVectorDB
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        db = QdrantVectorDB(api_key="secret-key")
        result = db.connect()
        
        assert result is True
        mock_qdrant_client.assert_called_once_with(
            host="localhost",
            port=6333,
            api_key="secret-key",
            timeout=30
        )


class TestQdrantVectorDBCollectionManagement:
    """Test class for collection management."""
    
    @pytest.fixture
    def connected_db(self):
        """Fixture for a connected database client."""
        from vector_db.client import QdrantVectorDB
        
        with patch('vector_db.client.QdrantClient') as mock_qdrant_client:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MockCollectionsResponse([])
            mock_qdrant_client.return_value = mock_client
            
            db = QdrantVectorDB()
            db.connect()
            yield db, mock_client
    
    def test_create_collection_success(self, connected_db):
        """Test successful collection creation."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        
        result = db.create_collection("test_collection", vector_size=128)
        
        assert result is True
        mock_client.create_collection.assert_called_once()
    
    def test_create_collection_already_exists(self, connected_db):
        """Test creating a collection that already exists."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse(["test_collection"])
        
        result = db.create_collection("test_collection", vector_size=128)
        
        assert result is True
        mock_client.create_collection.assert_not_called()
    
    def test_create_collection_not_connected(self):
        """Test creating collection when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        result = db.create_collection("test_collection", vector_size=128)
        
        assert result is False
    
    def test_create_collection_with_distance_metrics(self, connected_db):
        """Test creating collection with different distance metrics."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        
        for metric in ["cosine", "euclidean", "manhattan", "dot"]:
            mock_client.reset_mock()
            mock_client.get_collections.return_value = MockCollectionsResponse([])
            
            result = db.create_collection(
                f"test_{metric}", 
                vector_size=128, 
                distance_metric=metric
            )
            
            assert result is True
    
    def test_create_collection_failure(self, connected_db):
        """Test collection creation failure."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_client.create_collection.side_effect = Exception("Creation failed")
        
        result = db.create_collection("test_collection", vector_size=128)
        
        assert result is False
    
    def test_collection_exists_true(self, connected_db):
        """Test collection_exists returns True when collection exists."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse(["my_collection"])
        
        result = db.collection_exists("my_collection")
        
        assert result is True
    
    def test_collection_exists_false(self, connected_db):
        """Test collection_exists returns False when collection doesn't exist."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse(["other_collection"])
        
        result = db.collection_exists("my_collection")
        
        assert result is False
    
    def test_collection_exists_not_connected(self):
        """Test collection_exists when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        result = db.collection_exists("test_collection")
        
        assert result is False
    
    def test_delete_collection_success(self, connected_db):
        """Test successful collection deletion."""
        db, mock_client = connected_db
        
        result = db.delete_collection("test_collection")
        
        assert result is True
        mock_client.delete_collection.assert_called_once_with("test_collection")
    
    def test_delete_collection_not_connected(self):
        """Test delete collection when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        result = db.delete_collection("test_collection")
        
        assert result is False
    
    def test_delete_collection_failure(self, connected_db):
        """Test collection deletion failure."""
        db, mock_client = connected_db
        mock_client.delete_collection.side_effect = Exception("Delete failed")
        
        result = db.delete_collection("test_collection")
        
        assert result is False
    
    def test_list_collections_success(self, connected_db):
        """Test listing collections."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse(
            ["collection1", "collection2", "collection3"]
        )
        
        result = db.list_collections()
        
        assert result == ["collection1", "collection2", "collection3"]
    
    def test_list_collections_empty(self, connected_db):
        """Test listing collections when none exist."""
        db, mock_client = connected_db
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        
        result = db.list_collections()
        
        assert result == []
    
    def test_list_collections_not_connected(self):
        """Test listing collections when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        result = db.list_collections()
        
        assert result == []
    
    def test_get_collection_info_success(self, connected_db):
        """Test getting collection info."""
        db, mock_client = connected_db
        mock_client.get_collection.return_value = MockCollectionInfoResponse(
            points_count=500, vectors_count=500
        )
        
        result = db.get_collection_info("test_collection")
        
        assert result is not None
        assert result["name"] == "test_collection"
        assert result["points_count"] == 500
        assert result["vectors_count"] == 500
    
    def test_get_collection_info_not_connected(self):
        """Test getting collection info when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        result = db.get_collection_info("test_collection")
        
        assert result is None
    
    def test_get_collection_info_failure(self, connected_db):
        """Test getting collection info failure."""
        db, mock_client = connected_db
        mock_client.get_collection.side_effect = Exception("Not found")
        
        result = db.get_collection_info("nonexistent")
        
        assert result is None


class TestQdrantVectorDBVectorOperations:
    """Test class for vector operations (insert, search, delete)."""
    
    @pytest.fixture
    def connected_db(self):
        """Fixture for a connected database client."""
        from vector_db.client import QdrantVectorDB
        
        with patch('vector_db.client.QdrantClient') as mock_qdrant_client:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MockCollectionsResponse([])
            mock_qdrant_client.return_value = mock_client
            
            db = QdrantVectorDB()
            db.connect()
            yield db, mock_client
    
    def test_upsert_vectors_success(self, connected_db):
        """Test successful vector upsert."""
        db, mock_client = connected_db
        
        vectors = [
            (1, [0.1, 0.2, 0.3], {"text": "hello"}),
            (2, [0.4, 0.5, 0.6], {"text": "world"}),
        ]
        
        result = db.upsert_vectors("test_collection", vectors)
        
        assert result is True
        mock_client.upsert.assert_called_once()
    
    def test_upsert_vectors_empty_list(self, connected_db):
        """Test upserting empty vector list."""
        db, mock_client = connected_db
        
        result = db.upsert_vectors("test_collection", [])
        
        assert result is True
    
    def test_upsert_vectors_not_connected(self):
        """Test upsert when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        vectors = [(1, [0.1, 0.2, 0.3], {"text": "hello"})]
        
        result = db.upsert_vectors("test_collection", vectors)
        
        assert result is False
    
    def test_upsert_vectors_failure(self, connected_db):
        """Test upsert failure."""
        db, mock_client = connected_db
        mock_client.upsert.side_effect = Exception("Upsert failed")
        
        vectors = [(1, [0.1, 0.2, 0.3], {"text": "hello"})]
        
        result = db.upsert_vectors("test_collection", vectors)
        
        assert result is False
    
    def test_search_vectors_success(self, connected_db):
        """Test successful vector search."""
        db, mock_client = connected_db
        
        mock_results = [
            MockSearchResult(1, 0.95, {"text": "hello"}),
            MockSearchResult(2, 0.85, {"text": "world"}),
        ]
        mock_client.query_points.return_value = MockQueryResponse(mock_results)
        
        query_vector = [0.1, 0.2, 0.3]
        results = db.search_vectors("test_collection", query_vector, limit=10)
        
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["score"] == 0.95
        assert results[0]["payload"] == {"text": "hello"}
        assert results[1]["id"] == 2
        assert results[1]["score"] == 0.85
    
    def test_search_vectors_with_threshold(self, connected_db):
        """Test vector search with score threshold."""
        db, mock_client = connected_db
        
        mock_client.query_points.return_value = MockQueryResponse([
            MockSearchResult(1, 0.95, {"text": "hello"})
        ])
        
        query_vector = [0.1, 0.2, 0.3]
        results = db.search_vectors(
            "test_collection", 
            query_vector, 
            limit=10,
            score_threshold=0.9
        )
        
        mock_client.query_points.assert_called_once()
        call_kwargs = mock_client.query_points.call_args[1]
        assert call_kwargs.get("score_threshold") == 0.9
    
    def test_search_vectors_empty_results(self, connected_db):
        """Test search with no results."""
        db, mock_client = connected_db
        mock_client.query_points.return_value = MockQueryResponse([])
        
        query_vector = [0.1, 0.2, 0.3]
        results = db.search_vectors("test_collection", query_vector)
        
        assert results == []
    
    def test_search_vectors_not_connected(self):
        """Test search when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        query_vector = [0.1, 0.2, 0.3]
        
        results = db.search_vectors("test_collection", query_vector)
        
        assert results == []
    
    def test_search_vectors_failure(self, connected_db):
        """Test search failure."""
        db, mock_client = connected_db
        mock_client.query_points.side_effect = Exception("Search failed")
        
        query_vector = [0.1, 0.2, 0.3]
        results = db.search_vectors("test_collection", query_vector)
        
        assert results == []
    
    def test_delete_vectors_success(self, connected_db):
        """Test successful vector deletion."""
        db, mock_client = connected_db
        
        result = db.delete_vectors("test_collection", [1, 2, 3])
        
        assert result is True
        mock_client.delete.assert_called_once()
    
    def test_delete_vectors_single(self, connected_db):
        """Test deleting single vector."""
        db, mock_client = connected_db
        
        result = db.delete_vectors("test_collection", [42])
        
        assert result is True
    
    def test_delete_vectors_not_connected(self):
        """Test delete when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        
        result = db.delete_vectors("test_collection", [1, 2, 3])
        
        assert result is False
    
    def test_delete_vectors_failure(self, connected_db):
        """Test delete failure."""
        db, mock_client = connected_db
        mock_client.delete.side_effect = Exception("Delete failed")
        
        result = db.delete_vectors("test_collection", [1, 2, 3])
        
        assert result is False


class TestQdrantVectorDBScrollOperations:
    """Test class for scroll operations."""
    
    @pytest.fixture
    def connected_db(self):
        """Fixture for a connected database client."""
        from vector_db.client import QdrantVectorDB
        
        with patch('vector_db.client.QdrantClient') as mock_qdrant_client:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MockCollectionsResponse([])
            mock_qdrant_client.return_value = mock_client
            
            db = QdrantVectorDB()
            db.connect()
            yield db, mock_client
    
    def test_scroll_all_points_success(self, connected_db):
        """Test scrolling all points."""
        db, mock_client = connected_db
        
        mock_points = [MagicMock(id=i) for i in range(10)]
        mock_client.scroll.side_effect = [
            (mock_points[:5], "offset1"),
            (mock_points[5:], None),
        ]
        
        result = db.scroll_all_points("test_collection")
        
        assert len(result) == 10
    
    def test_scroll_all_points_empty(self, connected_db):
        """Test scrolling empty collection."""
        db, mock_client = connected_db
        mock_client.scroll.return_value = ([], None)
        
        result = db.scroll_all_points("test_collection")
        
        assert result == []
    
    def test_scroll_all_points_not_connected(self):
        """Test scroll when not connected."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        
        result = db.scroll_all_points("test_collection")
        
        assert result == []
    
    def test_scroll_all_points_failure(self, connected_db):
        """Test scroll failure."""
        db, mock_client = connected_db
        mock_client.scroll.side_effect = Exception("Scroll failed")
        
        result = db.scroll_all_points("test_collection")
        
        assert result == []
    
    def test_scroll_with_options(self, connected_db):
        """Test scroll with payload and vector options."""
        db, mock_client = connected_db
        mock_client.scroll.return_value = ([], None)
        
        db.scroll_all_points(
            "test_collection",
            limit=50,
            with_payload=True,
            with_vectors=True
        )
        
        mock_client.scroll.assert_called_with(
            collection_name="test_collection",
            limit=50,
            offset=None,
            with_payload=True,
            with_vectors=True
        )


class TestGetQdrantClientSingleton:
    """Test class for the singleton get_qdrant_client function."""
    
    def setup_method(self):
        """Reset the global singleton before each test."""
        import vector_db.client as client_module
        client_module._qdrant_client = None
    
    @patch('vector_db.client.QdrantClient')
    def test_get_qdrant_client_creates_new(self, mock_qdrant_client):
        """Test that get_qdrant_client creates a new client."""
        from vector_db.client import get_qdrant_client
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        client = get_qdrant_client()
        
        assert client is not None
        assert client.host == "localhost"
        assert client.port == 6333
    
    @patch('vector_db.client.QdrantClient')
    def test_get_qdrant_client_returns_singleton(self, mock_qdrant_client):
        """Test that get_qdrant_client returns the same instance."""
        from vector_db.client import get_qdrant_client
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        client1 = get_qdrant_client()
        client2 = get_qdrant_client()
        
        assert client1 is client2
    
    @patch('vector_db.client.QdrantClient')
    def test_get_qdrant_client_force_new(self, mock_qdrant_client):
        """Test that force_new creates a new instance."""
        from vector_db.client import get_qdrant_client
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        client1 = get_qdrant_client()
        client2 = get_qdrant_client(force_new=True)
        
        assert client1 is not client2
    
    @patch('vector_db.client.QdrantClient')
    def test_get_qdrant_client_with_custom_params(self, mock_qdrant_client):
        """Test get_qdrant_client with custom parameters."""
        from vector_db.client import get_qdrant_client
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        client = get_qdrant_client(
            host="custom-host",
            port=6334,
            api_key="my-key",
            force_new=True
        )
        
        assert client.host == "custom-host"
        assert client.port == 6334
        assert client.api_key == "my-key"


class TestQdrantVectorDBErrorHandling:
    """Test class for error handling scenarios."""
    
    def test_operations_when_client_is_none(self):
        """Test that operations fail gracefully when client is None."""
        from vector_db.client import QdrantVectorDB
        
        db = QdrantVectorDB()
        db.connected = True  # Simulate inconsistent state
        db.client = None
        
        assert db.is_connected() is False
    
    @patch('vector_db.client.QdrantClient')
    def test_connection_lost_during_operation(self, mock_qdrant_client):
        """Test handling of connection loss during operation."""
        from vector_db.client import QdrantVectorDB
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        db = QdrantVectorDB()
        db.connect()
        
        mock_client.upsert.side_effect = ConnectionError("Connection lost")
        
        vectors = [(1, [0.1, 0.2, 0.3], {"text": "hello"})]
        result = db.upsert_vectors("test_collection", vectors)
        
        assert result is False
    
    @patch('vector_db.client.QdrantClient')
    def test_timeout_during_search(self, mock_qdrant_client):
        """Test handling of timeout during search."""
        from vector_db.client import QdrantVectorDB
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_qdrant_client.return_value = mock_client
        
        db = QdrantVectorDB()
        db.connect()
        
        mock_client.query_points.side_effect = TimeoutError("Request timed out")
        
        results = db.search_vectors("test_collection", [0.1, 0.2, 0.3])
        
        assert results == []
    
    @patch('vector_db.client.QdrantClient')
    def test_invalid_collection_name(self, mock_qdrant_client):
        """Test handling of invalid collection name."""
        from vector_db.client import QdrantVectorDB
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MockCollectionsResponse([])
        mock_client.create_collection.side_effect = ValueError("Invalid collection name")
        mock_qdrant_client.return_value = mock_client
        
        db = QdrantVectorDB()
        db.connect()
        
        result = db.create_collection("", vector_size=128)
        
        assert result is False
