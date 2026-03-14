"""
Tests for backend.embedding — real logic, mocked model.
"""
import asyncio
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# EmbeddingModel (sync)
# ---------------------------------------------------------------------------

def _make_embedder(dim=8):
    """Create an EmbeddingModel with a mocked SentenceTransformer."""
    with patch("backend.embedding.embedder.SentenceTransformer") as MockST, \
         patch("backend.embedding.embedder.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        model_inst = MagicMock()
        model_inst.encode.side_effect = lambda texts, **kw: np.random.default_rng(42).random((len(texts), dim))
        model_inst.get_sentence_embedding_dimension.return_value = dim
        MockST.return_value = model_inst

        from backend.embedding.embedder import EmbeddingModel
        em = EmbeddingModel(model_path="mock-model", device="cpu")
    return em


class TestEmbedText:
    """embed_text logic."""

    def test_single_text_returns_1d(self):
        em = _make_embedder()
        out = em.embed_text("hello")
        assert isinstance(out, np.ndarray)
        assert out.ndim == 1 and out.shape[0] == 8

    def test_list_returns_2d(self):
        em = _make_embedder()
        out = em.embed_text(["a", "b", "c"])
        assert out.ndim == 2 and out.shape == (3, 8)

    def test_instruction_prefix_forwarded(self):
        em = _make_embedder()
        em.model.encode.side_effect = lambda texts, **kw: np.ones((len(texts), 8))
        em.embed_text("hello", instruction="Represent query:")
        call_args = em.model.encode.call_args
        assert call_args[0][0] == ["Represent query: hello"]

    def test_cpu_caps_batch_size(self):
        em = _make_embedder()
        em.device = "cpu"
        em.model.encode.side_effect = lambda texts, **kw: np.ones((len(texts), 8))
        em.embed_text(["t"] * 20, batch_size=64)
        _, kwargs = em.model.encode.call_args
        assert kwargs["batch_size"] <= 8


class TestEmbedWithScores:
    """embed_with_scores returns (embeddings, norms)."""

    def test_returns_tuple(self):
        em = _make_embedder()
        embeddings, norms = em.embed_with_scores(["a", "b"])
        assert embeddings.shape == (2, 8)
        assert len(norms) == 2
        assert all(isinstance(n, float) for n in norms)

    def test_norms_match_l2(self):
        em = _make_embedder()
        em.model.encode.side_effect = lambda texts, **kw: np.array(
            [[3.0, 4.0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0]]
        )
        _, norms = em.embed_with_scores(["x", "y"])
        assert abs(norms[0] - 5.0) < 1e-6
        assert abs(norms[1] - 1.0) < 1e-6


class TestSimilarity:
    """similarity() metric dispatch."""

    def _em_with_fixed_encode(self):
        em = _make_embedder()
        vecs = {
            "cat": np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=float),
            "kitten": np.array([0.9, 0.1, 0, 0, 0, 0, 0, 0], dtype=float),
            "car": np.array([0, 0, 0, 0, 0, 0, 0, 1], dtype=float),
        }
        def encode(texts, **kw):
            return np.array([vecs.get(t, np.zeros(8)) for t in texts])
        em.model.encode.side_effect = encode
        return em

    def test_cosine_similar_texts_high(self):
        em = self._em_with_fixed_encode()
        score = em.similarity("cat", "kitten", metric="cosine")
        assert score > 0.9

    def test_cosine_dissimilar_texts_low(self):
        em = self._em_with_fixed_encode()
        score = em.similarity("cat", "car", metric="cosine")
        assert score < 0.1

    def test_unknown_metric_raises(self):
        em = self._em_with_fixed_encode()
        with pytest.raises(ValueError, match="Unknown metric"):
            em.similarity("cat", "car", metric="jaccard")


class TestMostSimilar:
    """most_similar ranking."""

    def test_top_k_respects_limit(self):
        em = _make_embedder()
        # Use deterministic embeddings
        vecs = {
            "q": [1, 0, 0, 0, 0, 0, 0, 0],
            "a": [0.9, 0.1, 0, 0, 0, 0, 0, 0],
            "b": [0.5, 0.5, 0, 0, 0, 0, 0, 0],
            "c": [0, 0, 0, 0, 0, 0, 0, 1],
        }
        def encode(texts, **kw):
            return np.array([vecs.get(t, np.zeros(8)) for t in texts])
        em.model.encode.side_effect = encode
        results = em.most_similar("q", ["a", "b", "c"], top_k=2)
        assert len(results) == 2
        # "a" is most similar to "q"
        assert results[0][0] == "a"

    def test_returns_tuples(self):
        em = _make_embedder()
        results = em.most_similar("q", ["a"], top_k=1)
        assert isinstance(results[0], tuple)
        assert isinstance(results[0][1], float)


class TestModelInfo:
    """get_model_info returns correct metadata."""

    def test_keys_present(self):
        em = _make_embedder()
        info = em.get_model_info()
        assert info["device"] == "cpu"
        assert info["model_loaded"] is True
        assert info["embedding_dimension"] == 8

    def test_after_unload(self):
        em = _make_embedder()
        em.unload_model()
        info = em.get_model_info()
        assert info["model_loaded"] is False


# ---------------------------------------------------------------------------
# AsyncBatchEmbedder
# ---------------------------------------------------------------------------

class TestAsyncBatchEmbedder:
    """Async wrapper delegates to sync embedder correctly."""

    def test_embed_batch_empty(self):
        from backend.embedding.async_embedder import AsyncBatchEmbedder
        mock_embedder = MagicMock()
        ab = AsyncBatchEmbedder(mock_embedder, max_workers=1, batch_size=4)
        result = asyncio.run(ab.embed_batch_async([]))
        assert result == []
        ab.shutdown()

    def test_embed_batch_delegates(self):
        from backend.embedding.async_embedder import AsyncBatchEmbedder
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [[0.1, 0.2], [0.3, 0.4]]
        ab = AsyncBatchEmbedder(mock_embedder, max_workers=1, batch_size=4)
        result = asyncio.run(ab.embed_batch_async(["hello", "world"]))
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_embedder.embed_text.assert_called_once()
        ab.shutdown()

    def test_embed_single_returns_first(self):
        from backend.embedding.async_embedder import AsyncBatchEmbedder
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [[0.5, 0.6]]
        ab = AsyncBatchEmbedder(mock_embedder, max_workers=1, batch_size=4)
        result = asyncio.run(ab.embed_single_async("hi"))
        assert result == [0.5, 0.6]
        ab.shutdown()

    def test_parallel_batches_handles_exception(self):
        from backend.embedding.async_embedder import AsyncBatchEmbedder
        mock_embedder = MagicMock()
        call_count = 0
        def side_effect(texts, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("boom")
            return [[0.1]] * len(texts)
        mock_embedder.embed_text.side_effect = side_effect
        ab = AsyncBatchEmbedder(mock_embedder, max_workers=1, batch_size=4)
        results = asyncio.run(ab.embed_parallel_batches([["a"], ["b"], ["c"]]))
        # One of the batches should be empty due to error
        assert any(r == [] for r in results)
        ab.shutdown()


class TestAsyncSemanticSearch:
    """AsyncSemanticSearch delegates correctly."""

    def test_search_single(self):
        from backend.embedding.async_embedder import AsyncSemanticSearch, AsyncBatchEmbedder
        mock_embedder_base = MagicMock()
        mock_embedder_base.embed_text.return_value = [[0.1, 0.2]]
        ab = AsyncBatchEmbedder(mock_embedder_base, max_workers=1)
        mock_db = MagicMock()
        mock_db.search_vectors.return_value = [{"id": "1", "score": 0.9}]
        search = AsyncSemanticSearch(ab, mock_db)
        results = asyncio.run(search.search_single("test query"))
        assert results == [{"id": "1", "score": 0.9}]
        ab.shutdown()
