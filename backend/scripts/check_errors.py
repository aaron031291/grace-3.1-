import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import initialize_session_factory, get_db
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from models.genesis_key_models import GenesisKey, GenesisKeyType

def check_errors():
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    
    errors = session.query(GenesisKey).filter(
        GenesisKey.key_type == GenesisKeyType.ERROR
    ).all()
    
    print(f"Total Errors in DB: {len(errors)}")
    for e in errors[-5:]:
        print(f" - {e.what_description} (Actor: {e.who_actor}, TS: {e.when_timestamp})")

if __name__ == "__main__":
    check_errors()
