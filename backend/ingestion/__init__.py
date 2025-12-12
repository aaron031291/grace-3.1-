"""
Text ingestion module for document processing and vector storage.
"""

from .service import TextIngestionService, TextChunker

__all__ = ["TextIngestionService", "TextChunker"]
