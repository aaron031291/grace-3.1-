import sys
import os
from pathlib import Path
import logging

# Configure logging to see the OpenAI requests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST")

# Add backend to path
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

def test_analyzer():
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, SessionLocal
        from settings import settings
        from models.database_models import Document, DocumentChunk
        from librarian.ai_analyzer import AIContentAnalyzer
        from embedding import get_embedding_model
        
        # Initialize database
        db_type = DatabaseType(settings.DATABASE_TYPE)
        db_config = DatabaseConfig(
            db_type=db_type,
            database=settings.DATABASE_NAME,
            database_path=settings.DATABASE_PATH,
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        db = SessionLocal()
        
        # Create a dummy document if none exists
        doc = db.query(Document).first()
        if not doc:
            print("Creating dummy document for testing...")
            doc = Document(
                filename="test_openai.txt",
                file_path="test_openai.txt",
                file_size=100,
                mime_type="text/plain"
            )
            db.add(doc)
            db.flush()
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                text_content="This is a test document about artificial intelligence and space exploration."
            )
            db.add(chunk)
            db.commit()
            db.refresh(doc)
        
        print(f"Testing analyzer with document: {doc.filename}")
        
        analyzer = AIContentAnalyzer(
            db_session=db
        )
        
        result = analyzer.analyze_document(doc.id)
        
        print("\nAnalysis Result:")
        import json
        print(json.dumps(result, indent=2))
        
        if "error" in result:
            print(f"\n[FAIL] Analyzer returned error: {result['error']}")
            return False
        
        print("\n[PASS] Analyzer worked successfully!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_analyzer()
