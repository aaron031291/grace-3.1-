import sys
import os
import uuid
from datetime import datetime, timezone
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import initialize_session_factory, get_db
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from models.genesis_key_models import GenesisKey, GenesisKeyType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosTrigger")

def trigger_network_chaos():
    """Inject an error spike into the database to trigger autonomous healing."""
    logger.info("Initializing database connection...")
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    
    logger.info("Injecting simulated 'ConnectionError' anomalies...")
    
    # We need >10 errors to trigger an ERROR_SPIKE or >3 on same file for PERFORMANCE_DEGRADATION
    # Let's trigger both by injecting 12 errors on the same file
    for i in range(12):
        key_id = str(uuid.uuid4())
        error_key = GenesisKey(
            key_id=key_id,
            key_type=GenesisKeyType.ERROR,
            what_description=f"Simulated Database Timeout Exception #{i+1}",
            where_location="database.connection",
            who_actor="system_chaos_agent",
            file_path="backend/database/connection.py",
            is_error=True,
            error_type="TimeoutError",
            error_message="Connection to upstream database timed out after 30000ms",
            when_timestamp=datetime.now(timezone.utc)
        )
        session.add(error_key)
        
    session.commit()
    logger.info("Successfully injected 12 simulated TimeoutErrors into the Genesis Log.")
    logger.info("Grace's 'Health Monitor' thread should detect these on its next 300s sweep.")
    logger.info("To see it immediately, you can manually trigger health monitor in the codebase.")

if __name__ == "__main__":
    trigger_network_chaos()
