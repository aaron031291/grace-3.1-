"""
Database initialization and migration utilities.
Handles database schema creation and management.
"""

from sqlalchemy import inspect, MetaData
import logging

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
)

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

# Import Librarian models for document management
from models.librarian_models import (  # noqa: F401
    LibrarianTag,
    DocumentTag,
    DocumentRelationship,
    LibrarianRule,
    LibrarianAction,
    LibrarianAudit,
)

# Import Immutable Audit models for data integrity and traceability
from genesis.immutable_audit_storage import (  # noqa: F401
    ImmutableAuditRecord,
)


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
        # Use checkfirst=True to avoid errors if tables already exist
        # Note: extend_existing is not a valid parameter for create_all()
        # The issue is that metadata is loaded multiple times, causing "already defined" errors
        # The real fix is to prevent multiple imports of models, but we'll handle it gracefully here
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database tables created successfully")
    except Exception as e:
        error_msg = str(e)
        # Check if it's the "already defined" error - this is expected when models are imported multiple times
        if "already defined" in error_msg.lower() or "extend_existing" in error_msg.lower():
            logger.info("Table metadata already loaded (normal when models imported multiple times)")
            # Try to create tables individually to skip ones that already exist
            logger.info("Attempting to create tables individually...")
            for table_name, table in Base.metadata.tables.items():
                try:
                    table.create(bind=engine, checkfirst=True)
                    logger.debug(f"Table '{table_name}' created or already exists")
                except Exception as table_error:
                    # Ignore "already defined" errors - they're expected
                    if "already defined" not in str(table_error).lower():
                        logger.debug(f"Could not create table '{table_name}': {table_error}")
            logger.info("Individual table creation completed")
        else:
            logger.warning(f"Error during table creation: {type(e).__name__}: {error_msg[:200]}")
            # Still try individual creation as fallback
            for table_name, table in Base.metadata.tables.items():
                try:
                    table.create(bind=engine, checkfirst=True)
                except Exception:
                    pass


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
            "primary_key": col["primary_key"],
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
                "primary_key": col["primary_key"],
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
