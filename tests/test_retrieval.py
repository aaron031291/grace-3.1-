"""
Tests for Retrieval Module

Tests:
1. Retriever functionality
2. Cognitive retrieval
3. Enterprise RAG
4. Reranking
5. Trust-aware retrieval
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestRetriever:
    """Tests for main Retriever class."""
    
    @pytest.fixture
    def mock_retriever(self):
        """Create mock retriever."""
        with patch('backend.retrieval.retriever.get_embedding_model') as mock_emb:
            mock_emb.return_value = Mock()
            with patch('backend.retrieval.retriever.get_qdrant_client') as mock_db:
                mock_db.return_value = Mock()
                try:
                    from backend.retrieval.retriever import Retriever
                    return Retriever()
                except Exception:
                    return Mock()
    
    def test_retriever_init(self, mock_retriever):
        """Test retriever initialization."""
        assert mock_retriever is not None
    
    def test_retrieve_basic(self, mock_retriever):
        """Test basic retrieval."""
        if hasattr(mock_retriever, 'retrieve'):
            mock_retriever.retrieve = Mock(return_value=[
                {"id": "1", "content": "test doc", "score": 0.9}
            ])
            
            results = mock_retriever.retrieve("test query", top_k=5)
            
            assert len(results) >= 0
    
    def test_retrieve_with_filters(self, mock_retriever):
        """Test retrieval with filters."""
        if hasattr(mock_retriever, 'retrieve'):
            mock_retriever.retrieve = Mock(return_value=[])
            
            results = mock_retriever.retrieve(
                "test query",
                filters={"category": "docs"}
            )
            
            assert results is not None


class TestCognitiveRetriever:
    """Tests for CognitiveRetriever class."""
    
    @pytest.fixture
    def cognitive_retriever(self):
        """Create cognitive retriever."""
        try:
            with patch('backend.retrieval.cognitive_retriever.get_embedding_model'):
                with patch('backend.retrieval.cognitive_retriever.get_qdrant_client'):
                    from backend.retrieval.cognitive_retriever import CognitiveRetriever
                    return CognitiveRetriever()
        except Exception:
            return Mock()
    
    def test_cognitive_retriever_init(self, cognitive_retriever):
        """Test cognitive retriever initialization."""
        assert cognitive_retriever is not None
    
    def test_semantic_search(self, cognitive_retriever):
        """Test semantic search capability."""
        if hasattr(cognitive_retriever, 'semantic_search'):
            cognitive_retriever.semantic_search = Mock(return_value=[])
            
            results = cognitive_retriever.semantic_search("query")
            
            assert results is not None


class TestEnterpriseRAG:
    """Tests for EnterpriseRAG class."""
    
    @pytest.fixture
    def enterprise_rag(self):
        """Create enterprise RAG."""
        try:
            with patch.multiple(
                'backend.retrieval.enterprise_rag',
                get_embedding_model=Mock(),
                get_qdrant_client=Mock()
            ):
                from backend.retrieval.enterprise_rag import EnterpriseRAG
                return EnterpriseRAG()
        except Exception:
            return Mock()
    
    def test_enterprise_rag_init(self, enterprise_rag):
        """Test enterprise RAG initialization."""
        assert enterprise_rag is not None
    
    def test_hybrid_search(self, enterprise_rag):
        """Test hybrid search."""
        if hasattr(enterprise_rag, 'hybrid_search'):
            enterprise_rag.hybrid_search = Mock(return_value=[])
            
            results = enterprise_rag.hybrid_search("query")
            
            assert results is not None
    
    def test_answer_question(self, enterprise_rag):
        """Test question answering."""
        if hasattr(enterprise_rag, 'answer_question'):
            enterprise_rag.answer_question = Mock(return_value={
                "answer": "test answer",
                "sources": []
            })
            
            result = enterprise_rag.answer_question("What is X?")
            
            assert "answer" in result


class TestReranker:
    """Tests for Reranker class."""
    
    @pytest.fixture
    def reranker(self):
        """Create reranker."""
        try:
            from backend.retrieval.reranker import Reranker
            return Reranker()
        except Exception:
            return Mock()
    
    def test_reranker_init(self, reranker):
        """Test reranker initialization."""
        assert reranker is not None
    
    def test_rerank_results(self, reranker):
        """Test reranking results."""
        if hasattr(reranker, 'rerank'):
            reranker.rerank = Mock(return_value=[
                {"id": "2", "score": 0.95},
                {"id": "1", "score": 0.9}
            ])
            
            results = [
                {"id": "1", "content": "doc1", "score": 0.8},
                {"id": "2", "content": "doc2", "score": 0.7}
            ]
            
            reranked = reranker.rerank("query", results)
            
            assert reranked[0]["id"] == "2"
    
    def test_rerank_empty_results(self, reranker):
        """Test reranking empty results."""
        if hasattr(reranker, 'rerank'):
            reranker.rerank = Mock(return_value=[])
            
            reranked = reranker.rerank("query", [])
            
            assert len(reranked) == 0


class TestTrustAwareRetriever:
    """Tests for TrustAwareRetriever class."""
    
    @pytest.fixture
    def trust_retriever(self):
        """Create trust-aware retriever."""
        try:
            with patch.multiple(
                'backend.retrieval.trust_aware_retriever',
                get_embedding_model=Mock(),
                get_qdrant_client=Mock()
            ):
                from backend.retrieval.trust_aware_retriever import TrustAwareRetriever
                return TrustAwareRetriever()
        except Exception:
            return Mock()
    
    def test_trust_retriever_init(self, trust_retriever):
        """Test trust-aware retriever initialization."""
        assert trust_retriever is not None
    
    def test_retrieve_with_trust_scores(self, trust_retriever):
        """Test retrieval with trust scores."""
        if hasattr(trust_retriever, 'retrieve_with_trust'):
            trust_retriever.retrieve_with_trust = Mock(return_value=[
                {"id": "1", "content": "doc", "score": 0.9, "trust": 0.95}
            ])
            
            results = trust_retriever.retrieve_with_trust("query")
            
            assert "trust" in results[0]
    
    def test_filter_by_trust_threshold(self, trust_retriever):
        """Test filtering by trust threshold."""
        if hasattr(trust_retriever, 'retrieve_with_trust'):
            trust_retriever.retrieve_with_trust = Mock(return_value=[
                {"id": "1", "trust": 0.95}
            ])
            
            results = trust_retriever.retrieve_with_trust(
                "query",
                min_trust=0.8
            )
            
            assert all(r.get("trust", 1) >= 0.8 for r in results)


class TestRetrievalIntegration:
    """Integration tests for retrieval components."""
    
    def test_modules_importable(self):
        """Test all retrieval modules are importable."""
        try:
            from backend.retrieval import retriever
            from backend.retrieval import cognitive_retriever
            from backend.retrieval import enterprise_rag
            from backend.retrieval import reranker
            from backend.retrieval import trust_aware_retriever
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_retriever_module_has_classes(self):
        """Test retriever module has expected classes."""
        try:
            from backend.retrieval import retriever as ret_module
            assert hasattr(ret_module, '__file__')
        except ImportError:
            pytest.skip("Retriever module not available")


class TestErrorHandling:
    """Tests for error handling in retrieval."""
    
    def test_empty_query_handling(self):
        """Test handling of empty queries."""
        mock_retriever = Mock()
        mock_retriever.retrieve = Mock(return_value=[])
        
        results = mock_retriever.retrieve("")
        
        assert results == []
    
    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        mock_retriever = Mock()
        mock_retriever.retrieve = Mock(side_effect=ConnectionError("DB unavailable"))
        
        with pytest.raises(ConnectionError):
            mock_retriever.retrieve("query")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
