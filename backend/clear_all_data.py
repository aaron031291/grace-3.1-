"""
Utility script.
"""
#!/usr/bin/env python
"""
Clear all data from PostgreSQL and Qdrant vector database.
Use this to reset the system to a clean state.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_postgresql():
    """Clear all data from SQLite database."""
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory
        from models.database_models import Document, DocumentChunk
        
        logger.info("Setting up SQLite configuration...")
        # Use SQLite (default)
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="grace.db",
            echo=False,
        )
        
        logger.info("Initializing database connection...")
        DatabaseConnection.initialize(config)
        
        logger.info("Creating session factory...")
        session_factory = initialize_session_factory()
        db = session_factory()
        
        try:
            # Delete all chunks first (foreign key constraint)
            logger.info("Deleting all document chunks...")
            count = db.query(DocumentChunk).delete()
            logger.info(f"✓ Deleted {count} document chunks")
            
            # Delete all documents
            logger.info("Deleting all documents...")
            count = db.query(Document).delete()
            logger.info(f"✓ Deleted {count} documents")
            
            db.commit()
            logger.info("✓ SQLite data cleared successfully")
            
        except Exception as e:
            if "no such table" in str(e).lower():
                logger.info("✓ Database tables don't exist yet (OK - nothing to clear)")
            else:
                db.rollback()
                logger.error(f"Error clearing SQLite: {e}", exc_info=True)
                raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to clear SQLite: {e}", exc_info=True)
        return False
    
    return True


def clear_qdrant():
    """Clear all data from Qdrant."""
    try:
        from vector_db.client import get_qdrant_client
        
        logger.info("Connecting to Qdrant...")
        client = get_qdrant_client()
        
        # Delete the collection
        collection_name = "documents"
        logger.info(f"Deleting Qdrant collection: {collection_name}")
        
        try:
            client.delete_collection(collection_name=collection_name)
            logger.info(f"✓ Qdrant collection '{collection_name}' deleted")
        except Exception as e:
            # Collection might not exist, which is fine
            if "not found" in str(e).lower():
                logger.info(f"Collection '{collection_name}' doesn't exist (OK)")
            else:
                raise
        
        logger.info("✓ Qdrant data cleared successfully")
        
    except Exception as e:
        logger.error(f"Failed to clear Qdrant: {e}", exc_info=True)
        return False
    
    return True


def main():
    """Clear all data."""
    logger.info("=" * 60)
    logger.info("CLEARING ALL DATA FROM VECTOR DB AND SQLITE")
    logger.info("=" * 60)
    
    # Clear SQLite
    logger.info("\n[1/2] Clearing SQLite...")
    if not clear_postgresql():
        logger.error("Failed to clear SQLite")
        return False
    
    # Clear Qdrant
    logger.info("\n[2/2] Clearing Qdrant...")
    if not clear_qdrant():
        logger.error("Failed to clear Qdrant")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ ALL DATA CLEARED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info("\nThe system is now clean. New file uploads will:")
    logger.info("  1. Be saved to knowledge_base/ directory")
    logger.info("  2. Have text extracted based on file type")
    logger.info("  3. Be chunked and embedded")
    logger.info("  4. Be stored in PostgreSQL + Qdrant")
    logger.info("  5. Appear in RAG search results")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
