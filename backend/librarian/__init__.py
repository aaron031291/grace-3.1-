"""
Grace Librarian System

A comprehensive file management and organization system that automatically:
- Categorizes and tags documents using hybrid rules + AI analysis
- Tracks relationships between documents (citations, prerequisites, versions, etc.)
- Manages approval workflows for sensitive operations
- Maintains complete audit trail of all actions

The librarian handles files from all sources:
- User uploads via UI
- Human-created content
- Grace's autonomous actions

Core Components:
- LibrarianEngine: Central orchestrator for all operations
- TagManager: Tag lifecycle management and search
- RuleBasedCategorizer: Pattern matching for automatic categorization
- AIContentAnalyzer: LLM-based content analysis
- RelationshipManager: Document relationship detection and graphs
- ApprovalWorkflow: Permission checking and approval queue
- ActionExecutor: Atomic action execution with rollback

Usage:
    from librarian.engine import LibrarianEngine
    from database.session import SessionLocal
    from embedding.embedder import get_embedding_model
    from ollama_client.client import get_ollama_client

    librarian = LibrarianEngine(
        db_session=SessionLocal(),
        embedding_model=get_embedding_model(),
        ollama_client=get_ollama_client()
    )

    # Process a single document
    librarian.process_document(document_id=123)

    # Process multiple documents
    librarian.process_batch([123, 456, 789])

    # Reprocess entire knowledge base
    librarian.reprocess_all_documents()
"""

__version__ = "1.0.0"
__author__ = "Grace AI"

# Core components
from .engine import LibrarianEngine
from .tag_manager import TagManager
from .rule_categorizer import RuleBasedCategorizer
from .ai_analyzer import AIContentAnalyzer
from .relationship_manager import RelationshipManager
from .approval_workflow import ApprovalWorkflow

__all__ = [
    "LibrarianEngine",
    "TagManager",
    "RuleBasedCategorizer",
    "AIContentAnalyzer",
    "RelationshipManager",
    "ApprovalWorkflow",
]
