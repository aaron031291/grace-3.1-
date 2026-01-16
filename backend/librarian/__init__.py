"""
Grace Librarian System - Full File System Librarian

A comprehensive file management and organization system that automatically:
- Categorizes and tags documents using hybrid rules + AI analysis
- Tracks relationships between documents (citations, prerequisites, versions, etc.)
- Manages approval workflows for sensitive operations
- Maintains complete audit trail of all actions
- **FULL FILE SYSTEM OPERATIONS**: File creation, naming, organization, and retrieval

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
- FileOrganizer: Automatic folder creation and file organization
- FileNamingManager: Naming convention enforcement and renaming
- FileCreator: Template-based file creation (index files, summaries, READMEs)
- UnifiedRetriever: Combined search across tags, relationships, and metadata

Usage:
    from librarian.engine import LibrarianEngine
    from database.session import SessionLocal
    from embedding import get_embedding_model
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
from .file_organizer import FileOrganizer
from .file_naming_manager import FileNamingManager
from .file_creator import FileCreator
from .unified_retriever import UnifiedRetriever

__all__ = [
    "LibrarianEngine",
    "TagManager",
    "RuleBasedCategorizer",
    "AIContentAnalyzer",
    "RelationshipManager",
    "ApprovalWorkflow",
    "FileOrganizer",
    "FileNamingManager",
    "FileCreator",
    "UnifiedRetriever",
]
