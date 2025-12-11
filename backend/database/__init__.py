"""
Database module providing SQLAlchemy-based database interface.
Supports SQLite, PostgreSQL, MySQL, and other SQL databases.
"""

from .base import Base, BaseModel
from .connection import DatabaseConnection, get_db_connection
from .session import get_session, SessionLocal

__all__ = [
    "Base",
    "BaseModel",
    "DatabaseConnection",
    "get_db_connection",
    "get_session",
    "SessionLocal",
]
