"""
Database initialization example.
This demonstrates how to initialize the database in your FastAPI application.

Copy and adapt this to your app.py or create a separate initialization module.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from sqlalchemy.orm import Session
from fastapi import Depends

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import get_session, initialize_session_factory
from database.migration import create_tables, DatabaseConnection
from settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for database initialization.
    
    This handles:
    - Database connection setup on app startup
    - Session factory initialization
    - Table creation
    - Graceful shutdown on app termination
    """
    # ============ STARTUP ============
    logger.info("Initializing database...")
    
    try:
        # Create database configuration from environment variables
        config = DatabaseConfig.from_env()
        logger.info(f"Database Configuration: {config}")
        
        # Initialize database connection
        DatabaseConnection.initialize(config)
        logger.info("Database connection established")
        
        # Initialize session factory for FastAPI dependency injection
        initialize_session_factory()
        logger.info("Session factory initialized")
        
        # Create all tables
        create_tables()
        logger.info("Database tables created/verified")
        
        # Health check
        if DatabaseConnection.health_check():
            logger.info("✓ Database health check passed")
        else:
            logger.warning("⚠ Database health check failed")
    
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # ============ APPLICATION RUNNING ============
    yield
    
    # ============ SHUTDOWN ============
    logger.info("Closing database connection...")
    try:
        DatabaseConnection.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Example: How to use in FastAPI app
"""
from fastapi import FastAPI

# Create FastAPI app with database lifespan
app = FastAPI(
    title="Grace API",
    lifespan=db_lifespan,
)

# Now you can use dependency injection for database sessions
@app.get("/api/users/")
def list_users(session: Session = Depends(get_session)):
    from models.repositories import UserRepository
    repo = UserRepository(session)
    return [user.to_dict() for user in repo.get_all()]

@app.post("/api/users/")
def create_user(
    username: str,
    email: str,
    session: Session = Depends(get_session)
):
    from models.repositories import UserRepository
    repo = UserRepository(session)
    user = repo.create(username=username, email=email)
    return user.to_dict()
"""


# Alternative: Manual initialization if not using lifespan
def init_database_manually():
    """
    Manual database initialization.
    Use this if you can't use the lifespan context manager.
    """
    logger.info("Initializing database (manual)...")
    
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    create_tables()
    
    if DatabaseConnection.health_check():
        logger.info("✓ Database initialized successfully")
    else:
        logger.warning("⚠ Database connection may have issues")


def close_database_manually():
    """
    Manual database cleanup.
    Call this when shutting down the application.
    """
    logger.info("Closing database (manual)...")
    DatabaseConnection.close()


# Example: Direct usage without FastAPI
"""
if __name__ == "__main__":
    init_database_manually()
    
    try:
        # Your application code here
        from models.repositories import UserRepository
        from database.session import SessionLocal
        
        session = SessionLocal()
        repo = UserRepository(session)
        user = repo.create(username="test", email="test@example.com")
        print(f"Created user: {user}")
        session.close()
    
    finally:
        close_database_manually()
"""
