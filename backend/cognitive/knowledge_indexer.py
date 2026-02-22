"""
Backward compatibility wrapper.
KnowledgeIndexer and RetrievalQualityTracker merged into knowledge_compiler.py
"""
from cognitive.knowledge_compiler import KnowledgeIndexer, RetrievalQualityTracker, get_knowledge_indexer, get_retrieval_quality_tracker

__all__ = ['KnowledgeIndexer', 'RetrievalQualityTracker', 'get_knowledge_indexer', 'get_retrieval_quality_tracker']
