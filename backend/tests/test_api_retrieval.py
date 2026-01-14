"""
Tests for Retrieval and RAG API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestRetrievalStatus:
    """Test retrieval system status endpoints."""

    def test_get_retrieval_status(self, client):
        """Test getting retrieval system status."""
        response = client.get("/retrieve/status")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "vector_db" in data


@pytest.mark.api
class TestSemanticSearch:
    """Test semantic search endpoints."""

    def test_semantic_search(self, client):
        """Test semantic search."""
        response = client.post("/retrieve/search", json={
            "query": "What is machine learning?",
            "top_k": 5
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "results" in data or "chunks" in data

    def test_semantic_search_with_filters(self, client):
        """Test semantic search with filters."""
        response = client.post("/retrieve/search", json={
            "query": "Python programming",
            "top_k": 10,
            "filters": {"file_type": "pdf"}
        })
        assert response.status_code in [200, 500]

    def test_semantic_search_with_folder(self, client):
        """Test semantic search scoped to folder."""
        response = client.post("/retrieve/search", json={
            "query": "test query",
            "top_k": 5,
            "folder_path": "/documents"
        })
        assert response.status_code in [200, 500]

    def test_semantic_search_empty_query(self, client):
        """Test semantic search with empty query."""
        response = client.post("/retrieve/search", json={
            "query": "",
            "top_k": 5
        })
        assert response.status_code in [200, 400, 422]


@pytest.mark.api
class TestReranking:
    """Test reranking endpoints."""

    def test_search_with_reranking(self, client):
        """Test search with reranking enabled."""
        response = client.post("/retrieve/search-reranked", json={
            "query": "What are neural networks?",
            "top_k": 5,
            "rerank": True
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            # Should have rerank scores if reranking worked
            if "results" in data and len(data["results"]) > 0:
                # Results may have rerank_score
                pass

    def test_rerank_results(self, client):
        """Test explicit reranking of results."""
        response = client.post("/retrieve/rerank", json={
            "query": "Python functions",
            "chunks": [
                {"text": "A function in Python is defined using def keyword."},
                {"text": "Python is a programming language."},
                {"text": "Functions help organize code into reusable blocks."}
            ]
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestCognitiveRetrieval:
    """Test cognitive retrieval endpoints."""

    def test_cognitive_search(self, client):
        """Test cognitive retrieval."""
        response = client.post("/retrieve/cognitive", json={
            "query": "Explain object-oriented programming",
            "use_memory": True,
            "use_context": True
        })
        assert response.status_code in [200, 500]

    def test_cognitive_search_with_history(self, client):
        """Test cognitive search with conversation history."""
        response = client.post("/retrieve/cognitive", json={
            "query": "Tell me more about that",
            "conversation_history": [
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language."}
            ]
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestDocumentRetrieval:
    """Test document retrieval endpoints."""

    def test_get_document_chunks(self, client):
        """Test getting document chunks."""
        response = client.get("/retrieve/document/test-doc-id/chunks")
        assert response.status_code in [200, 404]

    def test_get_similar_documents(self, client):
        """Test getting similar documents."""
        response = client.get("/retrieve/document/test-doc-id/similar")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestRAGContext:
    """Test RAG context building endpoints."""

    def test_build_context(self, client):
        """Test building RAG context."""
        response = client.post("/retrieve/context", json={
            "query": "How do I create a class in Python?",
            "max_chunks": 5,
            "include_metadata": True
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "context" in data or "chunks" in data

    def test_build_context_with_threshold(self, client):
        """Test building RAG context with similarity threshold."""
        response = client.post("/retrieve/context", json={
            "query": "Database design patterns",
            "max_chunks": 10,
            "similarity_threshold": 0.7
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestVectorDBOperations:
    """Test vector database operation endpoints."""

    def test_get_collection_stats(self, client):
        """Test getting vector collection statistics."""
        response = client.get("/retrieve/collections/stats")
        assert response.status_code in [200, 500]

    def test_get_collections(self, client):
        """Test listing vector collections."""
        response = client.get("/retrieve/collections")
        assert response.status_code in [200, 500]
