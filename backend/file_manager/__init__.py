"""
File manager module for knowledge base management.
"""

from .file_handler import FileHandler, extract_file_text
from .knowledge_base_manager import KnowledgeBaseManager

__all__ = [
    "FileHandler",
    "extract_file_text",
    "KnowledgeBaseManager",
]
