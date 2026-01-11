"""
Database configuration module supporting multiple SQL databases.
Handles connection strings and engine configuration for various database backends.
"""

from enum import Enum
from typing import Optional
import os
from pathlib import Path


class DatabaseType(str, Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"


class DatabaseConfig:
    """Configuration for database connections."""
    
    def __init__(
        self,
        db_type: DatabaseType = DatabaseType.SQLITE,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "grace",
        database_path: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        echo: bool = False,
    ):
        """
        Initialize database configuration.
        
        Args:
            db_type: Type of database (sqlite, postgresql, mysql, mariadb)
            host: Database host (required for remote databases)
            port: Database port (optional, uses default if not specified)
            username: Database username (required for remote databases)
            password: Database password (required for remote databases)
            database: Database name
            database_path: Path for SQLite database file
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum overflow size for connection pool
            pool_pre_ping: Test connections before using them
            echo: Echo SQL statements (useful for debugging)
        """
        self.db_type = DatabaseType(db_type) if isinstance(db_type, str) else db_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.database_path = database_path
        # OPTIMIZED: Increased pool size for Memory Mesh scalability
        # From: pool_size=5, max_overflow=10 (15 total)
        # To: pool_size=20, max_overflow=30 (50 total)
        self.pool_size = pool_size if pool_size != 5 else 20  # Upgrade default
        self.max_overflow = max_overflow if max_overflow != 10 else 30  # Upgrade default
        self.pool_pre_ping = pool_pre_ping
        self.pool_recycle = 3600  # Recycle connections every hour
        self.echo = echo
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """
        Create configuration from environment variables.
        
        Expected environment variables:
            DATABASE_TYPE: Type of database (default: sqlite)
            DATABASE_HOST: Database host
            DATABASE_PORT: Database port
            DATABASE_USER: Database username
            DATABASE_PASSWORD: Database password
            DATABASE_NAME: Database name (default: grace)
            DATABASE_PATH: Path for SQLite database (default: ./data/grace.db)
            DATABASE_ECHO: Echo SQL statements (default: false)
        
        Returns:
            DatabaseConfig: Configuration instance
        """
        db_type = os.getenv("DATABASE_TYPE", "sqlite")
        echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        
        return cls(
            db_type=db_type,
            host=os.getenv("DATABASE_HOST"),
            port=int(os.getenv("DATABASE_PORT", 0)) or None,
            username=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            database=os.getenv("DATABASE_NAME", "grace"),
            database_path=os.getenv("DATABASE_PATH", "./data/grace.db"),
            echo=echo,
        )
    
    def get_connection_string(self) -> str:
        """
        Generate database connection string.
        
        Returns:
            str: Database connection URL string
            
        Raises:
            ValueError: If required parameters are missing for the database type
        """
        if self.db_type == DatabaseType.SQLITE:
            return self._get_sqlite_url()
        elif self.db_type == DatabaseType.POSTGRESQL:
            return self._get_postgresql_url()
        elif self.db_type == DatabaseType.MYSQL:
            return self._get_mysql_url()
        elif self.db_type == DatabaseType.MARIADB:
            return self._get_mariadb_url()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _get_sqlite_url(self) -> str:
        """Generate SQLite connection string."""
        db_path = self.database_path or "./data/grace.db"
        # Ensure the directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # SQLite URLs use sqlite:/// for absolute paths
        return f"sqlite:///{db_path}"
    
    def _get_postgresql_url(self) -> str:
        """Generate PostgreSQL connection string."""
        if not self.host or not self.username:
            raise ValueError(
                "PostgreSQL requires DATABASE_HOST and DATABASE_USER environment variables"
            )
        
        port = self.port or 5432
        password_part = f":{self.password}@" if self.password else "@"
        
        return (
            f"postgresql://{self.username}{password_part}"
            f"{self.host}:{port}/{self.database}"
        )
    
    def _get_mysql_url(self) -> str:
        """Generate MySQL connection string."""
        if not self.host or not self.username:
            raise ValueError(
                "MySQL requires DATABASE_HOST and DATABASE_USER environment variables"
            )
        
        port = self.port or 3306
        password_part = f":{self.password}@" if self.password else "@"
        
        return (
            f"mysql+pymysql://{self.username}{password_part}"
            f"{self.host}:{port}/{self.database}"
        )
    
    def _get_mariadb_url(self) -> str:
        """Generate MariaDB connection string."""
        if not self.host or not self.username:
            raise ValueError(
                "MariaDB requires DATABASE_HOST and DATABASE_USER environment variables"
            )
        
        port = self.port or 3306
        password_part = f":{self.password}@" if self.password else "@"
        
        return (
            f"mariadb+pymysql://{self.username}{password_part}"
            f"{self.host}:{port}/{self.database}"
        )
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"DatabaseConfig(type={self.db_type}, "
            f"host={self.host}, port={self.port}, "
            f"database={self.database}, echo={self.echo})"
        )
