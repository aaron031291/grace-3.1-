"""
Shared test fixtures for Grace AI test suite.
"""
import os
import sys
import pytest

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.update({
    "SKIP_EMBEDDING_LOAD": "true",
    "SKIP_QDRANT_CHECK": "true",
    "SKIP_OLLAMA_CHECK": "true",
    "SKIP_AUTO_INGESTION": "true",
    "DISABLE_CONTINUOUS_LEARNING": "true",
    "SKIP_LLM_CHECK": "true",
    "LIGHTWEIGHT_MODE": "true",
    "DATABASE_PATH": ":memory:",
})


@pytest.fixture(scope="session")
def app():
    from app import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def db_session():
    from database.session import session_scope
    with session_scope() as session:
        yield session
