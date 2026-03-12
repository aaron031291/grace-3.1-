import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import get_session_factory
from core.braille_sandbox_ingestor import BrailleIngestor

def main():
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    SessionLocal = get_session_factory()
    db = SessionLocal()
    ingestor = BrailleIngestor(db)
    
    # Run the ingestion on the backend directory
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    print(f"Starting Braille Sandbox Ingestion for: {backend_dir}")
    try:
        # Before ingesting, ensure the table exists
        from database.base import BaseModel
        from database.models.braille_node import BrailleSandboxNode
        
        engine = DatabaseConnection.get_engine()
        # Create table if it doesn't exist natively
        BaseModel.metadata.create_all(bind=engine, tables=[BrailleSandboxNode.__table__])
        
        count = ingestor.run_ingestion(backend_dir)
        print(f"\n==============================================")
        print(f"SUCCESS: {count} Braille Nodes generated.")
        print(f"==============================================")
        print(f"The Spindle Consensus Engine will now dynamically query the PostgreSQL Braille Nodes instead of static files.")
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
