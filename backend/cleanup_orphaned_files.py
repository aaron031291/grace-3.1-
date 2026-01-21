#!/usr/bin/env python3
"""
Database cleanup script for orphaned file records.
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.session import get_session
from models.database_models import Document, DocumentChunk
from vector_db.client import get_qdrant_client

def cleanup():
    """Remove documents whose files no longer exist."""
    # Get session
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        qdrant = None
        try:
            qdrant = get_qdrant_client()
            print("[OK] Qdrant connected")
        except:
            print("[WARN] Qdrant not available")
        
        # Find orphaned documents
        docs = session.query(Document).all()
        print(f"\n[INFO] Checking {len(docs)} documents...")
        
        orphaned = []
        for doc in docs:
            if not doc.file_path:
                continue
            
            # Check if file exists
            fp = Path(doc.file_path)
            if not fp.is_absolute():
                fp = backend_dir / "knowledge_base" / doc.file_path
            
            if not fp.exists():
                orphaned.append(doc)
                print(f"[ORPHAN] {doc.file_path}")
        
        if not orphaned:
            print("\n✅ No orphaned documents!")
            return
        
        print(f"\n[ACTION] Found {len(orphaned)} orphaned documents")
        resp = input("Delete them? (yes/no): ")
        
        if resp.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete
        for doc in orphaned:
            session.delete(doc)
            print(f"[DELETED] {doc.file_path}")
        
        session.commit()
        print(f"\n✅ Deleted {len(orphaned)} documents!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 80)
    print("Database Cleanup - Orphaned Files")
    print("=" * 80)
    cleanup()
