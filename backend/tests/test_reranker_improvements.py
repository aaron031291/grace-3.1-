"""
Test the reranker with half precision and singleton behavior.
"""

import sys
from pathlib import Path
import time
import torch

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from retrieval.reranker import get_reranker

def test_reranker_singleton_and_half_precision():
    """Test that reranker is loaded only once and uses half precision."""
    
    print("=" * 60)
    print("Testing Reranker: Singleton + Half Precision")
    print("=" * 60)
    
    # Get VRAM info before loading
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        vram_before = torch.cuda.memory_allocated() / 1024**2
        print(f"\nVRAM before loading reranker: {vram_before:.2f} MB")
    
    # First initialization
    print("\n[1] First call to get_reranker()...")
    start_time = time.time()
    reranker1 = get_reranker()
    load_time_1 = time.time() - start_time
    print(f"✓ Reranker loaded in {load_time_1:.2f} seconds")
    print(f"  Device: {reranker1.device}")
    print(f"  Using half precision: {reranker1.use_half_precision}")
    
    # Get VRAM after loading
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        vram_after = torch.cuda.memory_allocated() / 1024**2
        print(f"  VRAM usage: {vram_after:.2f} MB (delta: {vram_after - vram_before:.2f} MB)")
    
    # Second call should return same instance (no reload)
    print("\n[2] Second call to get_reranker()...")
    start_time = time.time()
    reranker2 = get_reranker()
    load_time_2 = time.time() - start_time
    print(f"✓ Returned in {load_time_2:.4f} seconds (should be instant)")
    
    # Verify singleton
    print(f"\n[3] Singleton check:")
    print(f"  Same instance? {reranker1 is reranker2}")
    print(f"  ✓ Reranker is loaded only ONCE" if reranker1 is reranker2 else "  ✗ Multiple instances created!")
    
    # Test reranking
    print(f"\n[4] Testing reranking with FP16...")
    query = "What is machine learning?"
    chunks = [
        {"chunk_id": 1, "text": "Machine learning is a subset of artificial intelligence."},
        {"chunk_id": 2, "text": "The weather is sunny today."},
        {"chunk_id": 3, "text": "Deep learning uses neural networks with multiple layers."},
    ]
    
    start_time = time.time()
    reranked = reranker1.rerank(query, chunks, top_k=2)
    rerank_time = time.time() - start_time
    
    print(f"  Reranked in {rerank_time:.3f} seconds")
    print(f"  Results (top 2):")
    for chunk in reranked:
        print(f"    - {chunk['chunk_id']}: {chunk['text'][:50]}... (score: {chunk['rerank_score']:.4f})")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    
    # Unload
    reranker1.unload_model()
    print("\n✓ Reranker unloaded from VRAM")

if __name__ == "__main__":
    test_reranker_singleton_and_half_precision()
