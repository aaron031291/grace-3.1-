"""
Tests for Embedding Module

Tests:
1. EmbeddingModel initialization
2. embed_text with single and batch
3. similarity calculation
4. most_similar ranking
5. cluster_texts functionality
6. Singleton pattern
7. Error handling
"""

import pytest
import sys
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestEmbeddingModelInit:
    """Tests for EmbeddingModel initialization."""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.rand(384)
            mock.return_value = mock_model
            yield mock
    
    def test_init_default_device(self, mock_sentence_transformer):
        """Test default device initialization."""
        from backend.embedding.embedder import EmbeddingModel
        
        with patch('backend.embedding.embedder.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            model = EmbeddingModel(device='cpu')
            
            assert model.device == 'cpu'
    
    def test_init_normalize_embeddings(self, mock_sentence_transformer):
        """Test normalize_embeddings setting."""
        from backend.embedding.embedder import EmbeddingModel
        
        model = EmbeddingModel(normalize_embeddings=True, device='cpu')
        assert model.normalize_embeddings == True
        
        model2 = EmbeddingModel(normalize_embeddings=False, device='cpu')
        assert model2.normalize_embeddings == False
    
    def test_init_max_length(self, mock_sentence_transformer):
        """Test max_length setting."""
        from backend.embedding.embedder import EmbeddingModel
        
        model = EmbeddingModel(max_length=512, device='cpu')
        assert model.max_length == 512
    
    def test_init_default_max_length(self, mock_sentence_transformer):
        """Test default max_length."""
        from backend.embedding.embedder import EmbeddingModel
        
        model = EmbeddingModel(device='cpu')
        assert model.max_length == 32768


class TestEmbedText:
    """Tests for embed_text functionality."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock embedding model."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock_instance.encode.return_value = np.random.rand(384)
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import EmbeddingModel
            model = EmbeddingModel(device='cpu')
            yield model
    
    def test_embed_single_text(self, mock_model):
        """Test embedding single text."""
        mock_model.model.encode.return_value = np.random.rand(384)
        
        result = mock_model.embed_text("Hello world")
        
        assert result is not None
        mock_model.model.encode.assert_called()
    
    def test_embed_batch_text(self, mock_model):
        """Test embedding batch of texts."""
        mock_model.model.encode.return_value = np.random.rand(3, 384)
        
        texts = ["Hello", "World", "Test"]
        result = mock_model.embed_text(texts)
        
        assert result is not None
        mock_model.model.encode.assert_called()
    
    def test_embed_with_instruction(self, mock_model):
        """Test embedding with instruction prefix."""
        mock_model.model.encode.return_value = np.random.rand(384)
        
        result = mock_model.embed_text(
            "Hello world",
            instruction="Represent this for search:"
        )
        
        assert result is not None
    
    def test_embed_convert_to_numpy(self, mock_model):
        """Test convert_to_numpy option."""
        mock_model.model.encode.return_value = np.random.rand(384)
        
        result = mock_model.embed_text("Test", convert_to_numpy=True)
        
        assert isinstance(result, np.ndarray)


class TestSimilarity:
    """Tests for similarity calculation."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock embedding model."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import EmbeddingModel
            model = EmbeddingModel(device='cpu')
            yield model
    
    def test_cosine_similarity(self, mock_model):
        """Test cosine similarity calculation."""
        mock_model.model.encode.side_effect = [
            np.array([1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0])
        ]
        
        with patch('backend.embedding.embedder.cosine_similarity') as mock_cos:
            mock_cos.return_value = np.array([[1.0]])
            
            result = mock_model.similarity("text1", "text2", metric="cosine")
            
            assert result == 1.0
    
    def test_euclidean_similarity(self, mock_model):
        """Test euclidean distance calculation."""
        mock_model.model.encode.side_effect = [
            np.array([1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0])
        ]
        
        with patch('backend.embedding.embedder.euclidean_distances') as mock_euc:
            mock_euc.return_value = np.array([[0.0]])
            
            result = mock_model.similarity("text1", "text2", metric="euclidean")
            
            assert result == 0.0
    
    def test_invalid_metric(self, mock_model):
        """Test invalid metric raises error."""
        mock_model.model.encode.side_effect = [
            np.array([1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0])
        ]
        
        with pytest.raises(ValueError, match="Unknown metric"):
            mock_model.similarity("text1", "text2", metric="invalid")


class TestMostSimilar:
    """Tests for most_similar functionality."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock embedding model."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import EmbeddingModel
            model = EmbeddingModel(device='cpu')
            yield model
    
    def test_most_similar_returns_ranked_list(self, mock_model):
        """Test most_similar returns ranked results."""
        mock_model.model.encode.side_effect = [
            np.array([1.0, 0.0, 0.0]),  # query
            np.array([[0.9, 0.1, 0.0], [0.5, 0.5, 0.0], [0.1, 0.9, 0.0]])  # candidates
        ]
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_cos:
            mock_cos.return_value = np.array([[0.95, 0.7, 0.3]])
            
            candidates = ["similar", "medium", "different"]
            results = mock_model.most_similar("query", candidates, top_k=2)
            
            assert len(results) == 2
            assert results[0][0] == "similar"
    
    def test_most_similar_respects_top_k(self, mock_model):
        """Test top_k parameter limits results."""
        mock_model.model.encode.side_effect = [
            np.array([1.0, 0.0, 0.0]),
            np.array([[0.9, 0.1, 0.0], [0.5, 0.5, 0.0], [0.1, 0.9, 0.0]])
        ]
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_cos:
            mock_cos.return_value = np.array([[0.95, 0.7, 0.3]])
            
            candidates = ["a", "b", "c"]
            results = mock_model.most_similar("query", candidates, top_k=1)
            
            assert len(results) == 1


class TestClusterTexts:
    """Tests for cluster_texts functionality."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock embedding model."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import EmbeddingModel
            model = EmbeddingModel(device='cpu')
            yield model
    
    def test_cluster_texts_returns_clusters(self, mock_model):
        """Test clustering returns cluster assignments."""
        mock_model.model.encode.return_value = np.random.rand(5, 384)
        
        with patch('sklearn.cluster.KMeans') as mock_kmeans:
            mock_km = MagicMock()
            mock_km.fit_predict.return_value = np.array([0, 0, 1, 1, 2])
            mock_kmeans.return_value = mock_km
            
            texts = ["a", "b", "c", "d", "e"]
            clusters = mock_model.cluster_texts(texts, num_clusters=3)
            
            assert len(clusters) > 0


class TestSingletonPattern:
    """Tests for singleton pattern."""
    
    def test_get_embedding_model_returns_singleton(self):
        """Test get_embedding_model returns same instance."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import get_embedding_model, invalidate_embedding_cache
            
            invalidate_embedding_cache()
            
            model1 = get_embedding_model(device='cpu')
            model2 = get_embedding_model(device='cpu')
            
            assert model1 is model2
    
    def test_invalidate_cache_forces_reload(self):
        """Test invalidate_embedding_cache forces new instance."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import get_embedding_model, invalidate_embedding_cache
            
            invalidate_embedding_cache()
            model1 = get_embedding_model(device='cpu')
            
            invalidate_embedding_cache()
            model2 = get_embedding_model(device='cpu')
            
            assert model1 is not model2


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_embed_function(self):
        """Test embed convenience function."""
        with patch('backend.embedding.embedder.get_embedding_model') as mock_get:
            mock_model = MagicMock()
            mock_model.embed_text.return_value = np.random.rand(384)
            mock_get.return_value = mock_model
            
            from backend.embedding.embedder import embed
            
            result = embed("test text")
            
            mock_model.embed_text.assert_called_once()
    
    def test_similarity_function(self):
        """Test similarity convenience function."""
        with patch('backend.embedding.embedder.get_embedding_model') as mock_get:
            mock_model = MagicMock()
            mock_model.similarity.return_value = 0.95
            mock_get.return_value = mock_model
            
            from backend.embedding.embedder import similarity
            
            result = similarity("text1", "text2")
            
            assert result == 0.95
    
    def test_most_similar_function(self):
        """Test most_similar convenience function."""
        with patch('backend.embedding.embedder.get_embedding_model') as mock_get:
            mock_model = MagicMock()
            mock_model.most_similar.return_value = [("match", 0.9)]
            mock_get.return_value = mock_model
            
            from backend.embedding.embedder import most_similar
            
            result = most_similar("query", ["match", "other"])
            
            assert result[0][0] == "match"


class TestGetModelInfo:
    """Tests for get_model_info and get_embedding_dimension."""
    
    @pytest.fixture
    def mock_model(self):
        """Create mock embedding model."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock_instance = MagicMock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock.return_value = mock_instance
            
            from backend.embedding.embedder import EmbeddingModel
            model = EmbeddingModel(device='cpu')
            yield model
    
    def test_get_model_info(self, mock_model):
        """Test get_model_info returns correct info."""
        info = mock_model.get_model_info()
        
        assert "model_path" in info
        assert "device" in info
        assert "embedding_dimension" in info
        assert "max_length" in info
        assert "normalize_embeddings" in info
    
    def test_get_embedding_dimension(self, mock_model):
        """Test get_embedding_dimension returns correct dimension."""
        dim = mock_model.get_embedding_dimension()
        
        assert dim == 384


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_model_not_loaded_error(self):
        """Test error when model not loaded."""
        with patch('backend.embedding.embedder.SentenceTransformer') as mock:
            mock.side_effect = Exception("Model not found")
            
            from backend.embedding.embedder import EmbeddingModel
            
            with pytest.raises(Exception):
                EmbeddingModel(model_path="/nonexistent/path", device='cpu')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
