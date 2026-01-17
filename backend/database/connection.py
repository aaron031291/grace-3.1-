from sqlalchemy import create_engine, Engine, event, text
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Optional
import logging
from database.config import DatabaseConfig, DatabaseType
class DatabaseConnection:
    logger = logging.getLogger(__name__)
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
            # Don't try to reconnect or check health here - just fail fast
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
        
        self.logger.info(f"Creating database engine for {config.db_type}")
        
        # SQLite uses a different pool strategy
        if config.db_type == DatabaseType.SQLITE:
            engine = create_engine(
                connection_string,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=config.echo,
            )
            # Enable foreign keys for SQLite
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # Use QueuePool for remote databases with enhanced scalability
            engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_pre_ping=config.pool_pre_ping,
                pool_recycle=getattr(config, 'pool_recycle', 3600),  # Recycle connections
                echo=config.echo,
            )
        
        self.logger.info(f"Database engine created successfully: {config.get_connection_string()}")
        return engine
    
    @classmethod
    def close(cls) -> None:
        """Close database connection."""
        instance = cls()
        if instance._engine:
            instance._engine.dispose()
            instance._engine = None
            cls.logger.info("Database connection closed")
    
    @classmethod
    def health_check(cls) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        instance = cls()
        
        # Quick check: engine must exist
        if instance._engine is None:
            cls.logger.warning("Database health check: Engine not initialized")
            return False
        
        # Try to execute a simple query
        try:
            with instance._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.commit()
            return True
        except Exception as e:
            cls.logger.error(f"Database health check failed: {e}")
            return False


def get_db_connection() -> DatabaseConnection:
    """
    Get the database connection singleton.
    
    Returns:
        DatabaseConnection: Database connection instance
    """
    return DatabaseConnection()
