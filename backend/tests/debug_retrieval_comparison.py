#!/usr/bin/env python3
"""
Debug retrieval issues - compare working vs non-working documents.
"""

import sqlite3
import json

db_path = "grace.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DOCUMENT COMPARISON: WORKING vs NON-WORKING")
    print("=" * 80)
    
    # Get all documents
    cursor.execute("""
        SELECT id, filename, status, total_chunks, extracted_text_length, 
               confidence_score, source_reliability, content_quality
        FROM documents
        ORDER BY created_at DESC
    """)
    
    docs = cursor.fetchall()
    
    print(f"\nFound {len(docs)} documents:\n")
    
    for i, (doc_id, filename, status, chunks, text_len, conf_score, 
            source_rel, content_qual) in enumerate(docs, 1):
        print(f"{i}. {filename}")
        print(f"   ID: {doc_id}")
        print(f"   Status: {status}")
        print(f"   Chunks: {chunks}")
        print(f"   Text length: {text_len}")
        print(f"   Confidence scores:")
        print(f"     - Overall: {conf_score:.3f}")
        print(f"     - Source reliability: {source_rel:.3f}")
        print(f"     - Content quality: {content_qual:.3f}")
        
        # Check if chunks exist and have vectors
        cursor.execute("""
            SELECT COUNT(*) FROM document_chunks WHERE document_id = ?
        """, (doc_id,))
        actual_chunks = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM document_chunks 
            WHERE document_id = ? AND embedding_vector_id IS NOT NULL
        """, (doc_id,))
        chunks_with_vectors = cursor.fetchone()[0]
        
        print(f"   Chunks in DB: {actual_chunks}")
        print(f"   Chunks with vectors: {chunks_with_vectors}")
        
        if actual_chunks == 0:
            print(f"   ⚠️  WARNING: No chunks found in database!")
        elif chunks_with_vectors == 0:
            print(f"   ⚠️  WARNING: No vector IDs assigned!")
        else:
            print(f"   ✓ All chunks have vectors")
        
        # Sample first chunk
        cursor.execute("""
            SELECT id, text_content, confidence_score, embedding_vector_id
            FROM document_chunks 
            WHERE document_id = ?
            LIMIT 1
        """, (doc_id,))
        chunk = cursor.fetchone()
        
        if chunk:
            chunk_id, text, chunk_conf, vector_id = chunk
            print(f"   First chunk:")
            print(f"     - ID: {chunk_id}")
            print(f"     - Vector ID: {vector_id}")
            print(f"     - Confidence: {chunk_conf:.3f}")
            print(f"     - Text length: {len(text)}")
            print(f"     - Text preview: {text[:60].replace(chr(10), ' ')}...")
        
        print()
    
    # Now test if the issue is query-specific
    print("\n" + "=" * 80)
    print("TESTING RETRIEVAL FOR EACH DOCUMENT")
    print("=" * 80)
    
    try:
        from embedding import EmbeddingModel
        from vector_db.client import get_qdrant_client
        import logging
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger('pdfminer').setLevel(logging.WARNING)
        
        print("\nLoading embedding model...")
        embedder = EmbeddingModel()
        qdrant = get_qdrant_client()
        print("✓ Loaded\n")
        
        # Test different queries
        test_queries = [
            "Pakistan GDP volatility",
            "economic growth",
            "hello world",
            "data analysis"
        ]
        
        for doc_id, filename, _, _, _, _, _, _ in docs:
            print(f"\n📄 Testing retrieval for: {filename}")
            
            # Get a sample chunk text to use as query
            cursor.execute("""
                SELECT text_content FROM document_chunks 
                WHERE document_id = ? LIMIT 1
            """, (doc_id,))
            result = cursor.fetchone()
            
            if result:
                sample_text = result[0][:50]
                print(f"   Using sample text: '{sample_text}...'")
                
                # Generate embedding and search
                try:
                    query_embedding = embedder.embed_text([sample_text])[0]
                    search_results = qdrant.search_vectors(
                        collection_name="documents",
                        query_vector=query_embedding,
                        limit=10,
                        score_threshold=0.0
                    )
                    
                    # Count how many results are from this document
                    matching = sum(1 for r in search_results 
                                 if r['payload']['document_id'] == doc_id)
                    
                    print(f"   ✓ Search returned {len(search_results)} results")
                    print(f"   ✓ {matching} results from this document")
                    
                    if matching == 0:
                        print(f"   ⚠️  Document chunks not in search results!")
                
                except Exception as e:
                    print(f"   ❌ Search error: {e}")
            
    except Exception as e:
        print(f"⚠️  Could not test retrieval: {e}")
    
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
