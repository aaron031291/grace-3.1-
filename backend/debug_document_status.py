#!/usr/bin/env python3
"""
Debug script to check document ingestion status and vectors.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database.session import SessionLocal
from models.database_models import Document, DocumentChunk
from vector_db.client import get_qdrant_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_document_status(filename_pattern: str):
    """Check document status in database."""
    print("\n" + "="*80)
    print("DOCUMENT STATUS CHECK")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Find documents matching pattern
        documents = db.query(Document).filter(
            Document.filename.ilike(f"%{filename_pattern}%")
        ).all()
        
        if not documents:
            print(f"\n❌ No documents found matching: {filename_pattern}")
            return
        
        for doc in documents:
            print(f"\n📄 Document: {doc.filename}")
            print(f"   ID: {doc.id}")
            print(f"   Status: {doc.status}")
            print(f"   Created: {doc.created_at}")
            print(f"   Text length: {doc.extracted_text_length} chars")
            print(f"   Total chunks: {doc.total_chunks}")
            print(f"   Confidence score: {doc.confidence_score:.3f}")
            
            # Check chunks
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()
            
            print(f"\n   📦 Chunks ({len(chunks)} total):")
            for i, chunk in enumerate(chunks[:3]):  # Show first 3
                print(f"      Chunk {i}: {len(chunk.text_content)} chars")
                print(f"        Vector ID: {chunk.embedding_vector_id}")
                print(f"        Text preview: {chunk.text_content[:50]}...")
            
            if len(chunks) > 3:
                print(f"      ... and {len(chunks) - 3} more chunks")
            
            # Check vectors in Qdrant
            print(f"\n   🔍 Checking Qdrant vectors...")
            qdrant = get_qdrant_client()
            
            if chunks and chunks[0].embedding_vector_id:
                try:
                    vector_id = int(chunks[0].embedding_vector_id)
                    # Try to retrieve the vector
                    try:
                        result = qdrant.qdrant_client.retrieve(
                            collection_name=qdrant.collection_name,
                            ids=[vector_id]
                        )
                        if result:
                            print(f"      ✓ Vector {vector_id} found in Qdrant")
                        else:
                            print(f"      ❌ Vector {vector_id} NOT found in Qdrant")
                    except Exception as e:
                        print(f"      ❌ Error checking vector: {e}")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
            
            # Summary
            print(f"\n   📊 Status Summary:")
            if doc.status != "completed":
                print(f"      ⚠️  Document status is '{doc.status}' (should be 'completed')")
            else:
                print(f"      ✓ Document status is 'completed'")
            
            if doc.total_chunks == 0:
                print(f"      ❌ No chunks recorded (total_chunks = 0)")
            else:
                print(f"      ✓ {doc.total_chunks} chunks recorded")
            
            if not chunks:
                print(f"      ❌ No chunk records in database")
            else:
                print(f"      ✓ {len(chunks)} chunk records found")
    
    finally:
        db.close()

def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_document_status.py <filename_pattern>")
        print("Example: python debug_document_status.py gdp_volatility")
        sys.exit(1)
    
    pattern = sys.argv[1]
    check_document_status(pattern)

if __name__ == "__main__":
    main()
