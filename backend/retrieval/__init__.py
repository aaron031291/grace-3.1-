"""
Retrieval module for RAG (Retrieval-Augmented Generation).
Provides document retrieval and context building capabilities.
"""

try:
    from .retriever import DocumentRetriever, get_retriever
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not import retriever: {e}")
    DocumentRetriever = None
    get_retriever = None

try:
    from .reranker import Reranker, get_reranker
except ImportError:
    Reranker = None
    get_reranker = None

__all__ = [
    "DocumentRetriever",
    "get_retriever",
    "Reranker",
    "get_reranker",
]
