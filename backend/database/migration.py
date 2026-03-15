"""
Database initialization and migration utilities.
Handles database schema creation and management.

Single source of truth: create_tables() creates ALL app tables. To add a new table:
  1. Define the model in the appropriate models/*.py (using BaseModel from database.base).
  2. Import it here (so Base.metadata knows about it).
  Do not create tables via separate migration scripts that use a different Base.
"""

import logging

from sqlalchemy import inspect

from .connection import DatabaseConnection
from .base import Base

# Import all models to register them with Base.metadata
# This must be done BEFORE calling create_all()
from models.database_models import (  # noqa: F401
    User,
    Conversation,
    Message,
    Embedding,
    Chat,
    ChatHistory,
    Document,
    DocumentChunk,
    GovernanceRule,
    GovernanceDocument,
    GovernanceDecision,
    LearningExample,
    LearningPattern,
    Episode,
    Procedure,
    LLMUsageStats,
    GraphNode,
    AdaptiveOverride,
    SchemaProposal,
)

# Import dynamic autonomous schema changes
try:
    from models.dynamic_models import *  # noqa: F401, F403
except ImportError:
    pass

# Import Notion task management models
from models.notion_models import (  # noqa: F401
    NotionProfile,
    NotionTask,
    TaskHistory,
    TaskTemplate,
)

# Import telemetry models for self-modeling
from models.telemetry_models import (  # noqa: F401
    OperationLog,
    PerformanceBaseline,
    DriftAlert,
    OperationReplay,
    SystemState,
)

# Import Genesis Key models for version control
from models.genesis_key_models import (  # noqa: F401
    GenesisKey,
    FixSuggestion,
    GenesisKeyArchive,
    UserProfile,
)

# Import Braille Sandbox models
from database.models.braille_node import BrailleSandboxNode  # noqa: F401
from database.models.braille_dictionary import BrailleDictionaryMapping  # noqa: F401
# Import Librarian models for document management
from models.librarian_models import (  # noqa: F401
    LibrarianTag,
    DocumentTag,
    DocumentRelationship,
    LibrarianRule,
    LibrarianAction,
    LibrarianAudit,
)

# Import Query Intelligence models (query_handling_log, knowledge_gaps, context_submissions)
from models.query_intelligence_models import (  # noqa: F401
    QueryHandlingLog,
    KnowledgeGap,
    ContextSubmission,
)

# Import File Intelligence models (file_intelligence, file_relationships, etc.)
from models.file_intelligence_models import (  # noqa: F401
    FileIntelligence,
    FileRelationship,
    ProcessingStrategy,
    FileHealthCheck,
)

# Import Coding Agent task model — creates coding_agent_tasks table
from database.models.coding_agent_task import CodingAgentTask  # noqa: F401

# Import Spindle event model — creates spindle_events table
from models.spindle_event_model import SpindleEvent  # noqa: F401


logger = logging.getLogger(__name__)


def create_tables() -> None:
    """
    Create all database tables defined in Base metadata.
    
    This should be called once at application startup to ensure
    all tables are created if they don't already exist.
    """
    engine = DatabaseConnection.get_engine()
    
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Error during table creation (may be normal): {type(e).__name__}: {str(e)[:100]}")
        # Try to create tables individually to skip ones that already exist
        logger.info("Attempting to create tables individually...")
        for table_name, table in Base.metadata.tables.items():
            try:
                table.create(bind=engine, checkfirst=True)
                logger.debug(f"Table '{table_name}' created or already exists")
            except Exception as table_error:
                logger.debug(f"Could not create table '{table_name}': {table_error}")
        logger.info("Individual table creation completed")


def drop_tables() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data. Use with caution, typically only
    for testing or development cleanup.
    """
    engine = DatabaseConnection.get_engine()
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def table_exists(table_name: str) -> bool:
    """
    Check if a specific table exists in the database.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return table_name in tables


def get_table_columns(table_name: str) -> dict:
    """
    Get column information for a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        dict: Column information
    """
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    
    if not table_exists(table_name):
        return {}
    
    columns = {}
    for col in inspector.get_columns(table_name):
        columns[col["name"]] = {
            "type": str(col["type"]),
            "nullable": col["nullable"],
            "primary_key": col.get("primary_key", False),
        }
    
    return columns


def get_all_tables() -> list:
    """
    Get list of all tables in the database.
    
    Returns:
        list: Table names
    """
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    return inspector.get_table_names()


def get_db_schema() -> dict:
    """
    Get complete database schema information.
    
    Returns:
        dict: Schema information for all tables
    """
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    
    schema = {}
    for table_name in inspector.get_table_names():
        columns = {}
        for col in inspector.get_columns(table_name):
            columns[col["name"]] = {
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": col.get("primary_key", False),
            }
        
        indexes = {}
        for idx in inspector.get_indexes(table_name):
            indexes[idx["name"]] = {
                "columns": idx["column_names"],
                "unique": idx["unique"],
            }
        
        schema[table_name] = {
            "columns": columns,
            "indexes": indexes,
        }
    
    return schema
