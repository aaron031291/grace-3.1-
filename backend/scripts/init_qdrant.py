#!/usr/bin/env python3
"""
Initialize Qdrant collection for Grace API.
Run this script to create the 'documents' collection with the correct vector dimensions.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from vector_db.client import get_qdrant_client
from embedding.embedder import get_embedding_model

def main():
    print("=" * 60)
    print("Qdrant Collection Initialization")
    print("=" * 60)
    
    # Get embedding model and vector dimension
    print("\n[1/4] Loading embedding model...")
    try:
        model = get_embedding_model()
        vector_size = model.get_embedding_dimension()
        print(f"✓ Embedding model loaded")
        print(f"  Model path: {model.model_path}")
        print(f"  Vector dimension: {vector_size}")
    except Exception as e:
        print(f"✗ Failed to load embedding model: {e}")
        return False
    
    # Connect to Qdrant
    print("\n[2/4] Connecting to Qdrant...")
    try:
        client = get_qdrant_client()
        if client.connect():
            print(f"✓ Connected to Qdrant")
            print(f"  Host: {client.host}:{client.port}")
        else:
            print("✗ Failed to connect to Qdrant")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False
    
    # Create collection
    print("\n[3/4] Creating collection...")
    collection_name = "documents"
    try:
        if client.collection_exists(collection_name):
            print(f"✓ Collection '{collection_name}' already exists")
            info = client.get_collection_info(collection_name)
            if info:
                print(f"  Vectors count: {info.get('vectors_count', 0)}")
                print(f"  Points count: {info.get('points_count', 0)}")
        else:
            success = client.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
                distance_metric="cosine"
            )
            if success:
                print(f"✓ Collection '{collection_name}' created successfully")
                print(f"  Vector size: {vector_size}")
                print(f"  Distance metric: cosine")
            else:
                print(f"✗ Failed to create collection")
                return False
    except Exception as e:
        print(f"✗ Error creating collection: {e}")
        return False
    
    # List all collections
    print("\n[4/4] Verifying collections...")
    try:
        collections = client.list_collections()
        print(f"✓ Available collections: {collections}")
    except Exception as e:
        print(f"✗ Error listing collections: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Qdrant setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart the backend: python app.py")
    print("2. Check logs for: [OK] Qdrant connection verified")
    print("3. Test ingestion with web scraper or file upload")
    print()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
