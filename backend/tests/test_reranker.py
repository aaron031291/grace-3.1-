"""
Test the reranker functionality.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from retrieval.reranker import get_reranker

def test_reranker():
    """Test reranker initialization and basic functionality."""
    
    print("Testing reranker...")
    
    # Get reranker instance
    reranker = get_reranker()
    print(f"✓ Reranker loaded: {reranker.model_name}")
    print(f"  Device: {reranker.device}")
    
    # Test reranking
    query = "What is machine learning?"
    chunks = [
        {
            "chunk_id": 1,
            "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience."
        },
        {
            "chunk_id": 2,
            "text": "The weather today is sunny with a high of 75 degrees."
        },
        {
            "chunk_id": 3,
            "text": "Deep learning uses neural networks with multiple layers to process complex data."
        },
    ]
    
    print(f"\nOriginal chunks:")
    for chunk in chunks:
        print(f"  - {chunk['chunk_id']}: {chunk['text'][:60]}...")
    
    reranked = reranker.rerank(query, chunks, top_k=2)
    
    print(f"\nReranked chunks (top 2):")
    for chunk in reranked:
        print(f"  - {chunk['chunk_id']}: {chunk['text'][:60]}... (score: {chunk['rerank_score']:.4f})")
    
    print("\n✓ Reranker test passed!")
    
    # Unload
    reranker.unload_model()
    print("✓ Reranker unloaded")

if __name__ == "__main__":
    test_reranker()
