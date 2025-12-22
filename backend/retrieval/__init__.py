"""
Retrieval module for RAG (Retrieval-Augmented Generation).
Provides document retrieval and context building capabilities.
"""

from .retriever import DocumentRetriever, get_retriever

__all__ = [
    "DocumentRetriever",
    "get_retriever",
]
