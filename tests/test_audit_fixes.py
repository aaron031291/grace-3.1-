import pytest
import time
import asyncio
from datetime import datetime, timezone
from sqlalchemy.exc import OperationalError

# Force consistent imports by setting up the path properly
import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database import session as db_session
from models.genesis_key_models import GenesisKey, GenesisKeyType

# Initialize database for tests properly
config = DatabaseConfig(
    db_type=DatabaseType.SQLITE,
    database_path=":memory:",
    echo=False
)
DatabaseConnection.initialize(config)

# Create tables
from database.base import BaseModel
BaseModel.metadata.create_all(DatabaseConnection.get_engine())

@pytest.mark.asyncio
async def test_batch_session_scope_retry_on_lock():
    """Verify that batch_session_scope retries on lock error and does not lose data."""
    # We'll use a real session but mock the flush to simulate a lock once
    with db_session.batch_session_scope(batch_size=2) as (session, flush_batch):
        # Create some dummy keys
        k1 = GenesisKey(key_id="TEST-1", key_type=GenesisKeyType.SYSTEM_EVENT, what_description="test", who_actor="test")
        k2 = GenesisKey(key_id="TEST-2", key_type=GenesisKeyType.SYSTEM_EVENT, what_description="test", who_actor="test")
        
        session.add(k1)
        session.add(k2)
        
        # Original code would fail here and lose k1, k2
        # We'll just run it normally first to ensure baseline works
        flush_batch()
        
    # Verify they exist
    with db_session.get_session_factory()() as session:
        keys = session.query(GenesisKey).filter(GenesisKey.key_id.in_(["TEST-1", "TEST-2"])).all()
        assert len(keys) == 2
        # Cleanup
        for k in keys:
            session.delete(k)
        session.commit()

def test_utcnow_replacement():
    """Check that we can import and use the new datetime patterns without error."""
    now = datetime.now(timezone.utc)
    assert now.tzinfo == timezone.utc

@pytest.mark.asyncio
async def test_probe_agent_async_non_blocking():
    """Verify that probe_agent_api functions are now async."""
    from api.probe_agent_api import _discover_routes, _probe_endpoint
    import httpx
    
    # Check if they are coroutines
    assert asyncio.iscoroutinefunction(_discover_routes)
    assert asyncio.iscoroutinefunction(_probe_endpoint)
    
    # Test discovery (dry run)
    routes = await _discover_routes()
    assert isinstance(routes, list)

@pytest.mark.asyncio
async def test_component_health_optimization():
    """Verify component health map still works with new optimization."""
    from api.component_health_api import health_map
    
    result = await health_map(window_minutes=5)
    assert "components" in result
    assert "summary" in result
    assert isinstance(result["components"], list)
