"""
Database initialization and migration utilities.
Handles database schema creation and management.
"""

from sqlalchemy import inspect, MetaData
import logging

from .connection import DatabaseConnection
from .base import Base


logger = logging.getLogger(__name__)


def create_tables() -> None:
    """
    Create all database tables defined in Base metadata.
    
    This should be called once at application startup to ensure
    all tables are created if they don't already exist.
    """
    engine = DatabaseConnection.get_engine()
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


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
