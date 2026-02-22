"""
Utility script.
"""
#!/usr/bin/env python3
"""
Force Re-Ingestion Script
Resets ingestion status in SQL database to trigger re-ingestion into Qdrant.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.connection import get_session
from models.document_models import Document

def reset_ingestion_status():
    """Reset all documents to pending status to force re-ingestion."""
    print("=" * 60)
    print("Force Re-Ingestion")
    print("=" * 60)
    
    session = next(get_session())
    
    try:
        # Get all documents
        documents = session.query(Document).all()
        print(f"\nFound {len(documents)} documents in database")
        
        if len(documents) == 0:
            print("No documents to reset")
            return
        
        # Count by status
        completed = sum(1 for d in documents if d.ingestion_status == 'completed')
        pending = sum(1 for d in documents if d.ingestion_status == 'pending')
        failed = sum(1 for d in documents if d.ingestion_status == 'failed')
        
        print(f"\nCurrent status:")
        print(f"  Completed: {completed}")
        print(f"  Pending: {pending}")
        print(f"  Failed: {failed}")
        
        # Reset all to pending
        for doc in documents:
            doc.ingestion_status = 'pending'
            doc.vector_id = None  # Clear old vector ID
        
        session.commit()
        
        print(f"\n✅ Reset {len(documents)} documents to 'pending' status")
        print("   Vector IDs cleared")
        print("\nNext step: Restart backend to trigger auto-ingestion")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    reset_ingestion_status()
