#!/usr/bin/env python3
"""
Ultra-Optimized Embedding Benchmark - Direct Model Access

Bypasses wrapper classes and uses SentenceTransformer directly for maximum speed.
Targets RTX 3090 with aggressive optimization: FP16, large batches, no progress bars.

Usage:
    python benchmark_embedding_optimized.py [--batch-size 256] [--precision fp16]
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple
import json

import torch
import numpy as np
from sentence_transformers import SentenceTransformer

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def generate_sample_text(target_tokens: int = 5000) -> str:
    """Generate sample text with approximately target_tokens tokens."""
    sample_paragraph = """
    Machine learning is a subset of artificial intelligence that enables systems 
    to learn and improve from experience without explicit programming. The field has 
    seen remarkable growth in recent years, with applications spanning computer vision, 
    natural language processing, healthcare, finance, and numerous other domains. 
    
    Deep learning, a subset of machine learning, uses artificial neural networks with 
    multiple layers to process data and extract increasingly abstract features at each layer. 
    These models have proven particularly effective for tasks like image recognition, 
    language translation, and text generation. The success of deep learning has driven 
    significant advances in artificial intelligence.
    
    Modern language models like transformers have revolutionized the field of natural 
    language processing. These models use attention mechanisms to weigh the importance 
    of different words in a sentence, allowing them to capture long-range dependencies 
    and contextual relationships. This architecture has become the foundation for most 
    state-of-the-art NLP systems today.
    
    Embeddings are numerical representations of text that capture semantic meaning. 
    By converting words or documents into high-dimensional vectors, machine learning 
    models can perform mathematical operations to measure similarity, classify content, 
    or retrieve relevant information. Embedding models have become essential tools in 
    modern NLP and recommendation systems.
    
    The transformer architecture, introduced in the "Attention Is All You Need" paper, 
    has become the dominant approach for sequence-to-sequence tasks. Self-attention 
    mechanisms allow the model to focus on different parts of the input simultaneously, 
    making it highly parallelizable and efficient for training on large datasets.
    
    Distributed computing enables processing large amounts of data across multiple machines.
    The rise of cloud computing has made it easier for organizations to scale their ML systems.
    Containerization with Docker and orchestration with Kubernetes have standardized deployment.
    
    Natural language understanding requires models to grasp context, nuance, and meaning.
    Pre-trained models like BERT, GPT, and others have achieved state-of-the-art results.
    Transfer learning allows these models to be fine-tuned for specific downstream tasks.
    
    Retrieval-augmented generation combines information retrieval with generative models.
    This approach allows models to access external knowledge during generation.
    RAG systems can provide more accurate and grounded responses than language models alone.
    
    Vector databases store and retrieve high-dimensional embeddings efficiently.
    Approximate nearest neighbor search enables fast similarity queries at scale.
    These systems power modern recommendation engines and semantic search applications.
    """
    
    chars_per_token = 6.5
    needed_chars = int(target_tokens * chars_per_token)
    repetitions = (needed_chars // len(sample_paragraph)) + 1
    
    full_text = sample_paragraph * repetitions
    word_count = len(full_text.split())
    estimated_tokens = word_count / 1.3
    
    if estimated_tokens > target_tokens:
        trim_point = int(len(full_text) * (target_tokens / estimated_tokens))
        full_text = full_text[:trim_point]
    
    return full_text


def split_text_into_chunks(text: str, num_chunks: int) -> List[str]:
    """Split text into equal chunks."""
    chunk_size = len(text) // num_chunks
    chunks = []
    
    for i in range(num_chunks):
        start = i * chunk_size
        end = len(text) if i == num_chunks - 1 else (i + 1) * chunk_size
        chunks.append(text[start:end].strip())
    
    return [c for c in chunks if c]


def combine_chunks_for_throughput(chunks: List[str], target_size: int = 2048, max_size: int = 8192) -> List[str]:
    """
    Combine small chunks into larger texts for better throughput.
    Smaller texts have higher per-text overhead.
    
    Args:
        chunks: List of small text chunks
        target_size: Target size in characters for combined texts
        max_size: Maximum size in characters (never exceed model context)
        
    Returns:
        List of combined texts
    """
    combined = []
    current_combined = []
    current_size = 0
    
    for chunk in chunks:
        chunk_size = len(chunk)
        
        # If adding this chunk would exceed max or target, flush current
        if (current_size + chunk_size > max_size) or (current_size + chunk_size > target_size and current_combined and len(current_combined) > 2):
            combined.append(" ".join(current_combined))
            current_combined = [chunk]
            current_size = chunk_size
        else:
            current_combined.append(chunk)
            current_size += chunk_size
    
    # Add remaining
    if current_combined:
        combined.append(" ".join(current_combined))
    
    return combined


def load_model_optimized(model_path: str, device: str = "cuda") -> SentenceTransformer:
    """Load model with optimizations for speed."""
    print(f"\n⏳ Loading model: {model_path}")
    print(f"   Device: {device}")
    print(f"   PyTorch version: {torch.__version__}")
    
    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA Compute Capability: {torch.cuda.get_device_capability(0)}")
    
    # Load with trust_remote_code for custom models
    model = SentenceTransformer(model_path, device=device, trust_remote_code=True)
    
    # Optimization: Set to eval mode
    model.eval()
    
    # Optimization: Disable gradients
    torch.set_grad_enabled(False)
    
    print(f"✅ Model loaded successfully")
    
    if device == "cuda" and torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / 1e9
        reserved = torch.cuda.memory_reserved(0) / 1e9
        print(f"   GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")
    
    return model


def benchmark_embedding_direct(
    model: SentenceTransformer,
    texts: List[str],
    batch_size: int = 128,
    precision: str = "fp32",
    show_progress: bool = False,
    chunk_group_size: int = 128,
) -> Tuple[float, float]:
    """
    Benchmark direct embedding using SentenceTransformer.encode()
    
    Args:
        model: SentenceTransformer model instance
        texts: List of texts to embed
        batch_size: Batch size for encoding
        precision: "fp32" or "fp16"
        show_progress: Whether to show progress bar
        chunk_group_size: Process texts in groups to avoid OOM
        
    Returns:
        Tuple of (elapsed_time, total_tokens)
    """
    print(f"\n{'='*70}")
    print(f"DIRECT EMBEDDING BENCHMARK")
    print(f"{'='*70}")
    print(f"\nConfiguration:")
    print(f"  Number of texts: {len(texts)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Group size: {chunk_group_size}")
    print(f"  Precision: {precision}")
    print(f"  Total characters: {sum(len(t) for t in texts):,}")
    print(f"  Total words: {sum(len(t.split()) for t in texts):,}")
    
    total_tokens = sum(len(t.split()) / 1.3 for t in texts)
    print(f"  Estimated total tokens: {total_tokens:,.0f}")
    
    # Warmup
    print(f"\n⏳ Warming up model...")
    with torch.no_grad():
        _ = model.encode("Warmup text", batch_size=batch_size, show_progress_bar=False)
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
    
    print(f"🚀 Starting embedding benchmark...\n")
    
    start_time = time.time()
    all_embeddings = []
    
    # Process texts in groups to avoid OOM
    num_groups = (len(texts) + chunk_group_size - 1) // chunk_group_size
    
    for group_idx in range(num_groups):
        group_start = group_idx * chunk_group_size
        group_end = min((group_idx + 1) * chunk_group_size, len(texts))
        group_texts = texts[group_start:group_end]
        
        if show_progress or num_groups > 1:
            print(f"  Processing group {group_idx + 1}/{num_groups} ({len(group_texts)} texts)...")
        
        try:
            with torch.no_grad():
                if precision == "fp16":
                    with torch.amp.autocast(device_type='cuda', dtype=torch.float16):
                        group_embeddings = model.encode(
                            group_texts,
                            batch_size=batch_size,
                            show_progress_bar=False,
                            convert_to_numpy=False,
                            normalize_embeddings=False,
                        )
                else:
                    group_embeddings = model.encode(
                        group_texts,
                        batch_size=batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=False,
                        normalize_embeddings=False,
                    )
            
            # Handle both tensor and list outputs
            if isinstance(group_embeddings, torch.Tensor):
                all_embeddings.append(group_embeddings)
            elif isinstance(group_embeddings, list):
                all_embeddings.extend(group_embeddings)
            else:
                all_embeddings.append(group_embeddings)
            
            # Clear cache between groups
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
        
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print(f"\n⚠️  OOM with batch_size={batch_size}, reducing...")
                # Retry with smaller batch size
                smaller_batch_size = max(4, batch_size // 2)
                print(f"  Retrying with batch_size={smaller_batch_size}...")
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                with torch.no_grad():
                    if precision == "fp16":
                        with torch.amp.autocast(device_type='cuda', dtype=torch.float16):
                            group_embeddings = model.encode(
                                group_texts,
                                batch_size=smaller_batch_size,
                                show_progress_bar=False,
                                convert_to_numpy=False,
                                normalize_embeddings=False,
                            )
                    else:
                        group_embeddings = model.encode(
                            group_texts,
                            batch_size=smaller_batch_size,
                            show_progress_bar=False,
                            convert_to_numpy=False,
                            normalize_embeddings=False,
                        )
                
                if isinstance(group_embeddings, torch.Tensor):
                    all_embeddings.append(group_embeddings)
                elif isinstance(group_embeddings, list):
                    all_embeddings.extend(group_embeddings)
                else:
                    all_embeddings.append(group_embeddings)
                
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                    torch.cuda.empty_cache()
            else:
                raise
    
    # Concatenate all embeddings
    if isinstance(all_embeddings[0], torch.Tensor):
        embeddings = torch.cat(all_embeddings, dim=0)
    else:
        embeddings = all_embeddings
    
    # Synchronize GPU to ensure all operations complete
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ Embedding complete!")
    
    # Handle both tensor and list outputs
    if isinstance(embeddings, torch.Tensor):
        print(f"  Embeddings shape: {embeddings.shape}")
    elif isinstance(embeddings, list):
        print(f"  Embeddings: {len(embeddings)} vectors of dimension {len(embeddings[0]) if embeddings else 0}")
    else:
        print(f"  Embeddings shape: {embeddings.shape}")
    
    print(f"  ⏱️  Time elapsed: {elapsed:.2f}s")
    print(f"  📊 Throughput: {total_tokens / elapsed:,.0f} tokens/sec")
    print(f"  📊 Texts/sec: {len(texts) / elapsed:.1f}")
    
    if torch.cuda.is_available():
        peak_memory = torch.cuda.max_memory_allocated(0) / 1e9
        print(f"  🧠 Peak GPU Memory: {peak_memory:.2f}GB")
    
    return elapsed, total_tokens


def main():
    """Main benchmark function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ultra-optimized embedding benchmark (direct model access)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for encoding (default: 64, safe for RTX 3090)"
    )
    parser.add_argument(
        "--tokens",
        type=int,
        default=5000,
        help="Approximate total tokens to process (default: 5000)"
    )
    parser.add_argument(
        "--num-texts",
        type=int,
        default=None,
        help="Number of texts to create (default: auto - 1 large text)"
    )
    parser.add_argument(
        "--group-size",
        type=int,
        default=128,
        help="Process chunks in groups to avoid OOM (default: 128)"
    )
    parser.add_argument(
        "--precision",
        type=str,
        choices=["fp32", "fp16"],
        default="fp16",
        help="Precision: fp32 or fp16 (default: fp16 for speed)"
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device (cuda or cpu, default: cuda)"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to model directory"
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bar during encoding"
    )
    
    args = parser.parse_args()
    
    # Determine model path
    if args.model_path is None:
        model_path = str(backend_dir / "models" / "embedding" / "qwen_4b")
    else:
        model_path = args.model_path
    
    print("\n" + "="*70)
    print("⚡ ULTRA-OPTIMIZED EMBEDDING BENCHMARK")
    print("="*70)
    print(f"\nBenchmark Configuration:")
    print(f"  Model: {Path(model_path).name}")
    print(f"  Device: {args.device}")
    print(f"  Precision: {args.precision.upper()}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Total tokens: ~{args.tokens}")
    if args.num_texts:
        print(f"  Number of texts: {args.num_texts}")
    else:
        print(f"  Number of texts: AUTO (1 large text for max throughput)")
    
    # Check CUDA
    if args.device == "cuda":
        if not torch.cuda.is_available():
            print("\n❌ CUDA requested but not available!")
            sys.exit(1)
        print(f"  CUDA available: Yes")
        print(f"  CUDA version: {torch.version.cuda}")
    
    # Load model
    try:
        model = load_model_optimized(model_path, args.device)
    except Exception as e:
        print(f"\n❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Generate text
    print(f"\n⏳ Generating sample text (~{args.tokens} tokens)...")
    full_text = generate_sample_text(args.tokens)
    print(f"✅ Generated text: {len(full_text):,} characters")
    
    # Create texts
    if args.num_texts is None:
        # Default: use 1-3 large texts for maximum throughput
        # Auto-split if text is too large for safety
        max_chars_per_text = 20000  # ~3000 tokens
        
        if len(full_text) > max_chars_per_text:
            # Split into multiple texts
            num_texts = (len(full_text) + max_chars_per_text - 1) // max_chars_per_text
            texts_to_embed = split_text_into_chunks(full_text, num_texts)
            texts_to_embed = [t for t in texts_to_embed if len(t.strip()) > 50]
            print(f"✅ Auto-split into {len(texts_to_embed)} texts (max {max_chars_per_text} chars each)")
        else:
            texts_to_embed = [full_text]
            print(f"✅ Using 1 text for maximum throughput")
    else:
        # User specified number of texts
        texts_to_embed = split_text_into_chunks(full_text, args.num_texts)
        texts_to_embed = [t for t in texts_to_embed if len(t.strip()) > 50]
        print(f"✅ Split into {len(texts_to_embed)} texts")
    
    print(f"\nText Statistics:")
    for i, text in enumerate(texts_to_embed):
        tokens = len(text.split()) / 1.3
        print(f"  Text {i+1}: {len(text):,} chars, ~{tokens:,.0f} tokens")
    
    # Run benchmark
    elapsed, total_tokens = benchmark_embedding_direct(
        model,
        texts_to_embed,
        batch_size=args.batch_size,
        precision=args.precision,
        show_progress=args.progress,
        chunk_group_size=args.group_size,
    )
    
    # Summary
    print("\n" + "="*70)
    print("📊 BENCHMARK RESULTS")
    print("="*70)
    
    results = {
        "configuration": {
            "model": Path(model_path).name,
            "device": args.device,
            "precision": args.precision,
            "batch_size": args.batch_size,
            "num_texts": len(texts_to_embed),
            "total_tokens": total_tokens,
        },
        "performance": {
            "elapsed_seconds": elapsed,
            "total_tokens": total_tokens,
            "tokens_per_second": total_tokens / elapsed,
            "texts_per_second": len(texts_to_embed) / elapsed,
        }
    }
    
    print(f"\n📈 Performance Metrics:")
    print(f"  ⏱️  Total time: {elapsed:.2f}s")
    print(f"  📊 Throughput: {total_tokens / elapsed:,.0f} tokens/sec")
    print(f"  📊 Speed: {len(texts_to_embed) / elapsed:.2f} texts/sec")
    print(f"  ✅ Tokens processed: {total_tokens:,.0f}")
    
    # Save results
    output_file = backend_dir / "benchmark_optimized_results.json"
    try:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Failed to save results: {e}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
