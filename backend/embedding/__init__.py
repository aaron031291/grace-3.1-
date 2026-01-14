"""Embedding module for text embeddings."""

try:
    from .embedder import EmbeddingModel, get_embedding_model
    # Alias for backward compatibility
    get_embedder = get_embedding_model
except ImportError:
    # Graceful fallback when dependencies are not available
    EmbeddingModel = None
    get_embedding_model = None
    get_embedder = None

try:
    from .async_embedder import AsyncEmbeddingModel, get_async_embedding_model
except ImportError:
    AsyncEmbeddingModel = None
    get_async_embedding_model = None

__all__ = [
    'EmbeddingModel',
    'get_embedding_model',
    'get_embedder',  # Alias for backward compatibility
    'AsyncEmbeddingModel',
    'get_async_embedding_model'
]
