"""
Database connection management module.
Handles engine creation and connection pooling.

SQLite anti-lock strategy:
  - WAL journal mode for concurrent read/write access
  - busy_timeout to auto-retry on lock instead of failing immediately
  - Serialized connection pool (StaticPool) to prevent thread contention
  - Session-level retry decorator for transient OperationalErrors
"""

from sqlalchemy import create_engine, Engine, event, text
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from typing import Optional
import logging

from .config import DatabaseConfig, DatabaseType


logger = logging.getLogger(__name__)

SQLITE_BUSY_TIMEOUT_MS = 30_000
SQLITE_CONNECT_TIMEOUT_S = 60


class DatabaseConnection:
    """Manages SQLAlchemy engine and connection lifecycle."""
    
    _instance: Optional["DatabaseConnection"] = None
    _engine: Optional[Engine] = None
    _config: Optional[DatabaseConfig] = None
    
    def __new__(cls):
        """Singleton pattern - only one database connection instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, config: DatabaseConfig) -> "DatabaseConnection":
        """
        Initialize database connection with configuration.
        
        Args:
            config: DatabaseConfig instance
            
        Returns:
            DatabaseConnection: Singleton instance
        """
        instance = cls()
        instance._config = config
        instance._engine = instance._create_engine(config)
        return instance
    
    @classmethod
    def get_engine(cls) -> Engine:
        """
        Get the SQLAlchemy engine.
        
        Returns:
            Engine: SQLAlchemy engine instance
            
        Raises:
            RuntimeError: If database not initialized
        """
        instance = cls()
        if instance._engine is None:
            raise RuntimeError(
                "Database not initialized. Call DatabaseConnection.initialize() first."
            )
        return instance._engine
    
    @classmethod
    def get_config(cls) -> DatabaseConfig:
        """
        Get the database configuration.
        
        Returns:
            DatabaseConfig: Current configuration
            
        Raises:
            RuntimeError: If database not initialized
        """
        instance = cls()
        if instance._config is None:
            raise RuntimeError(
                "Database not initialized. Call DatabaseConnection.initialize() first."
            )
        return instance._config
    
    def _create_engine(self, config: DatabaseConfig) -> Engine:
        """
        Create SQLAlchemy engine with appropriate configuration.
        
        Args:
            config: DatabaseConfig instance
            
        Returns:
            Engine: Configured SQLAlchemy engine
        """
        connection_string = config.get_connection_string()
        
        logger.info(f"Creating database engine for {config.db_type}")
        
        if config.db_type == DatabaseType.SQLITE:
            engine = create_engine(
                connection_string,
                connect_args={
                    "check_same_thread": False,
                    "timeout": SQLITE_CONNECT_TIMEOUT_S,
                },
                poolclass=StaticPool,
                echo=config.echo,
            )

            @event.listens_for(engine, "connect")
            def _set_sqlite_pragmas(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

            logger.info(
                "SQLite engine configured: WAL mode, "
                f"busy_timeout={SQLITE_BUSY_TIMEOUT_MS}ms, "
                f"connect_timeout={SQLITE_CONNECT_TIMEOUT_S}s"
            )
        elif config.db_type == DatabaseType.POSTGRESQL:
            connect_args = {
                "options": "-c statement_timeout=30000",
            }
            engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_pre_ping=config.pool_pre_ping,
                pool_recycle=getattr(config, 'pool_recycle', 3600),
                pool_timeout=30,
                connect_args=connect_args,
                isolation_level="READ COMMITTED",
                echo=config.echo,
            )
            logger.info(
                f"PostgreSQL engine configured: pool_size={config.pool_size}, "
                f"max_overflow={config.max_overflow}, statement_timeout=30s"
            )
        else:
            engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_pre_ping=config.pool_pre_ping,
                pool_recycle=getattr(config, 'pool_recycle', 3600),
                echo=config.echo,
            )
        
        safe_url = connection_string.split("@")[-1] if "@" in connection_string else connection_string
        logger.info(f"Database engine created successfully: {safe_url}")
        return engine
    
    @classmethod
    def close(cls) -> None:
        """Close database connection."""
        instance = cls()
        if instance._engine:
            instance._engine.dispose()
            instance._engine = None
            logger.info("Database connection closed")
    
    @classmethod
    def health_check(cls) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            engine = cls.get_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


def get_db_connection() -> DatabaseConnection:
    """
    Get the database connection singleton.
    
    Returns:
        DatabaseConnection: Database connection instance
    """
    return DatabaseConnection()
