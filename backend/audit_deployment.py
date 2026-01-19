#!/usr/bin/env python3
"""
Deployment Audit Script
Verifies system readiness for high-performance client deployment.
"""
import sys
import os
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# Define backend directory
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env explicitly
load_dotenv(BACKEND_DIR / ".env")

# Import codebase components
try:
    from settings import settings
    from embedding.embedder import get_embedding_model
    from vector_db.client import get_qdrant_client
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AUDIT")

def check_environment():
    print("\n[1] Environment Configuration")
    print(f"  • Embedding Model: {settings.EMBEDDING_DEFAULT}")
    print(f"  • Model Path: {settings.EMBEDDING_MODEL_PATH}")
    print(f"  • LLM Model: {settings.OLLAMA_LLM_DEFAULT}")
    print(f"  • Database: {settings.DATABASE_TYPE}")
    
    # Check Model Path
    if Path(settings.EMBEDDING_MODEL_PATH).exists():
        print(f"  ✅ Embedding model directory exists.")
    else:
        print(f"  ❌ Embedding model directory MISSING at {settings.EMBEDDING_MODEL_PATH}")
        print("     Action: You need to download the model or update the path.")

def check_qola_integration():
    print("\n[2] Ollama Integration (Mistral)")
    url = f"{settings.OLLAMA_URL}/api/tags"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            print(f"  ✅ Ollama Connected. Available: {', '.join(models)}")
            if settings.OLLAMA_LLM_DEFAULT in models:
                 print(f"  ✅ Target model '{settings.OLLAMA_LLM_DEFAULT}' is pulled.")
            else:
                 print(f"  ❌ Target model '{settings.OLLAMA_LLM_DEFAULT}' NOT found in Ollama.")
        else:
            print(f"  ❌ Ollama API returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ Ollama Connection Failed: {e}")

def check_qdrant_compatibility():
    print("\n[3] Qdrant Compatibility")
    client = get_qdrant_client()
    try:
        if client.connect():
            print(f"  ✅ Qdrant Connected at {client.host}:{client.port}")
            if client.collection_exists(settings.QDRANT_COLLECTION_NAME):
                info = client.get_collection_info(settings.QDRANT_COLLECTION_NAME)
                vec_size = info.get('config', {}).get('params', {}).get('vectors', {}).get('size')
                if not vec_size:
                     # New qdrant structure
                     vec_size = info.get('config', {}).get('params', {}).get('vectors', {}).get('size') # Try again? No
                     # Actually often it's direct content
                     pass
                
                print(f"  ℹ️  Existing Collection '{settings.QDRANT_COLLECTION_NAME}' has vector size: {vec_size}")
                
                # Check Expected Size
                # We can't load the model if it's missing, but we can guess or try
                print("  ❓ Verifying against expected model dimensions...")
                if Path(settings.EMBEDDING_MODEL_PATH).exists():
                    try:
                        # Attempt to load model (singleton)
                        # Warning: This might be heavy
                        from sentence_transformers import SentenceTransformer
                        # Use lightweight check if possible? No, load it.
                        model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH, device="cpu", trust_remote_code=True)
                        expected_dim = model.get_sentence_embedding_dimension()
                        print(f"  ℹ️  Model '{settings.EMBEDDING_DEFAULT}' expects dimension: {expected_dim}")
                        
                        if vec_size != expected_dim:
                             print(f"  ❌ CRITICAL MISMATCH: Collection ({vec_size}) != Model ({expected_dim})")
                             print("     Action: Delete Qdrant collection to allow re-initialization.")
                        else:
                             print(f"  ✅ Dimensions match.")
                    except Exception as e:
                        print(f"  ⚠️ Could not load model for verification: {e}")
                else:
                    print("  ⚠️ Cannot verify dimensions (Model missing).")
            else:
                print(f"  ℹ️  Collection '{settings.QDRANT_COLLECTION_NAME}' does not exist (Will be created).")
        else:
            print("  ❌ Qdrant Connection Failed")
    except Exception as e:
        print(f"  ❌ Qdrant Error: {e}")

if __name__ == "__main__":
    print("=== Grace System Deployment Audit ===")
    check_environment()
    check_qola_integration()
    check_qdrant_compatibility()
    print("\n=== Audit Complete ===")
