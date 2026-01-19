#!/usr/bin/env python3
"""
Download lightweight embedding model for laptop testing.

This script downloads the all-MiniLM-L6-v2 model which is much smaller
than Qwen-4B and can run on laptops with limited resources.

Model Details:
- Name: all-MiniLM-L6-v2
- Size: ~90 MB
- RAM Usage: ~500 MB
- Embedding Dimension: 384
- Quality: Good for general purpose semantic search

Usage:
    python download_lightweight_model.py
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def download_model():
    """Download and save the lightweight embedding model."""
    try:
        print("=" * 60)
        print("Downloading Lightweight Embedding Model")
        print("=" * 60)
        print()
        print("Model: all-MiniLM-L6-v2")
        print("Size: ~90 MB")
        print("RAM Usage: ~500 MB")
        print()
        print("This may take a few minutes depending on your internet speed...")
        print()
        
        # Import sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("❌ Error: sentence-transformers not installed")
            print()
            print("Please install it with:")
            print("  pip install sentence-transformers")
            return False
        
        # Create models directory
        backend_dir = Path(__file__).parent
        models_dir = backend_dir / "models" / "embedding"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / "all-MiniLM-L6-v2"
        
        # Check if model already exists
        if model_path.exists():
            print(f"⚠️  Model already exists at: {model_path}")
            response = input("Do you want to re-download? (y/N): ").strip().lower()
            if response != 'y':
                print("✓ Using existing model")
                return True
        
        # Download model
        print("📥 Downloading model from HuggingFace...")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Save model
        print(f"💾 Saving model to: {model_path}")
        model.save(str(model_path))
        
        print()
        print("=" * 60)
        print("✅ Model downloaded successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Update your .env file with:")
        print("   EMBEDDING_DEFAULT=all-MiniLM-L6-v2")
        print("   EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2")
        print()
        print("2. Set SKIP_EMBEDDING_LOAD=false to enable the model")
        print()
        print("3. Restart your backend server")
        print()
        print("To switch back to Qwen-4B for deployment:")
        print("   EMBEDDING_DEFAULT=qwen_4b")
        print("   EMBEDDING_MODEL_PATH=./models/embedding/qwen_4b")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
