"""
Pytest configuration and fixtures for Grace API tests.

This module handles graceful fallback when full app dependencies
are not available, allowing tests to run in various environments.
"""

import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Track if we can import the full app
_app_available = False
_app = None


def _try_import_app():
    """Try to import the FastAPI app, handling missing dependencies gracefully."""
    global _app_available, _app
    try:
        from fastapi.testclient import TestClient
        from app import app as fastapi_app
        _app = fastapi_app
        _app_available = True
        return fastapi_app
    except ImportError as e:
        print(f"Note: Full app import failed ({e}). Using mock fixtures.")
        _app_available = False
        return None


@pytest.fixture(scope="session")
def app():
    """Get the FastAPI application."""
    fastapi_app = _try_import_app()
    if fastapi_app is None:
        pytest.skip("Full app dependencies not available")
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Create a test client for the application."""
    if app is None:
        pytest.skip("Full app dependencies not available")
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from models.database_models import Base

        # Create in-memory SQLite database
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create session
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = TestingSessionLocal()

        yield session

        session.close()
        Base.metadata.drop_all(bind=engine)
    except ImportError:
        pytest.skip("Database dependencies not available")


@pytest.fixture
def sample_chat_request():
    """Sample chat request data."""
    return {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40
    }


@pytest.fixture
def sample_document_content():
    """Sample document content for ingestion tests."""
    return """
    # Sample Document

    This is a test document for Grace API testing.

    ## Section 1

    This section contains information about testing.

    ## Section 2

    This section contains more test content.
    """


@pytest.fixture
def sample_genesis_key():
    """Sample Genesis Key data."""
    return {
        "entity_type": "document",
        "entity_id": "test-doc-123",
        "origin_source": "test",
        "origin_type": "unit_test"
    }


@pytest.fixture
def sample_learning_example():
    """Sample learning example for ML tests."""
    return {
        "input": "What is machine learning?",
        "output": "Machine learning is a subset of AI...",
        "task_type": "qa",
        "trust_score": 0.85
    }


@pytest.fixture
def sample_governance_rule():
    """Sample governance rule data."""
    return {
        "rule_id": "test-rule-001",
        "name": "Test Rule",
        "description": "A test governance rule",
        "pillar": "operational",
        "priority": 1,
        "conditions": [
            {"field": "action_type", "operator": "equals", "value": "delete"}
        ],
        "actions": ["require_approval"]
    }


@pytest.fixture
def sample_whitelist_entry():
    """Sample whitelist entry data."""
    return {
        "entry_type": "domain",
        "value": "trusted.example.com",
        "reason": "Test whitelisted domain",
        "approved_by": "test_user"
    }


# Markers for different test categories
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks tests as API endpoint tests")
    config.addinivalue_line("markers", "requires_app: marks tests that need full app")
