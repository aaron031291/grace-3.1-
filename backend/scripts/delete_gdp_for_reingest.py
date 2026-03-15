#!/usr/bin/env python3
"""
Delete a document completely to allow re-ingestion.
"""

import sys
sys.path.insert(0, '.')

from pathlib import Path
from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.session import initialize_session_factory, get_session
from models.database_models import Document, DocumentChunk
import requests

print("="*80)
print("DELETE DOCUMENT 3 (GDP) FOR RE-INGESTION")
print("="*80)

# Initialize database
db_config = DatabaseConfig.from_env()
DatabaseConnection.initialize(db_config)
initialize_session_factory()

# Get database session via app's running instance
# We'll use a workaround by calling the API directly
print("\n1. Deleting vectors from Qdrant for document 3...")
qdrant_url = "http://localhost:6333"

# Get all point IDs for document 3
try:
    response = requests.post(
        f"{qdrant_url}/collections/documents/points/search",
        json={
            "vector": [0.0] * 2560,  # Dummy vector
            "limit": 1000,
            "with_payload": True,
            "score_threshold": -1.0  # Return all
        },
        timeout=10,
    )
    
    if response.status_code == 200:
        points = response.json()['result']
        doc3_ids = [p['id'] for p in points if p['payload'].get('document_id') == 3]
        print(f"   Found {len(doc3_ids)} vectors for document 3: {doc3_ids}")
        
        if doc3_ids:
            # Delete these vectors
            delete_response = requests.post(
                f"{qdrant_url}/collections/documents/points/delete",
                json={"point_ids": doc3_ids},
                timeout=10,
            )
            if delete_response.status_code == 200:
                print(f"   ✓ Deleted {len(doc3_ids)} vectors from Qdrant")
            else:
                print(f"   ⚠ Error deleting vectors: {delete_response.status_code}")
except Exception as e:
    print(f"   ⚠ Error accessing Qdrant: {e}")

print("\n2. Deleting document 3 from database...")
try:
    # Use raw database connection instead of SessionLocal
    from sqlalchemy import text
    
    engine = DatabaseConnection.get_engine()
    
    with engine.begin() as conn:
        # Delete chunks for document 3
        conn.execute(text("DELETE FROM document_chunks WHERE document_id = 3"))
        
        # Delete document 3
        conn.execute(text("DELETE FROM documents WHERE id = 3"))
    
    print("   ✓ Deleted document 3 and all associated chunks from database")
    
except Exception as e:
    print(f"   ⚠ Error deleting from database: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("NEXT STEP: Re-upload the GDP PDF file via the UI or API")
print("="*80)
