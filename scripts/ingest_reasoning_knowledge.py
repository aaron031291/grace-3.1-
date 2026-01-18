"""
Ingest Reasoning Knowledge into Grace

Complete pipeline:
1. Download datasets (math/reasoning from LLMs)
2. Convert to patterns
3. Embed and store in Qdrant
4. Ready for retrieval-based reasoning

Usage:
    python scripts/ingest_reasoning_knowledge.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_datasets():
    """Check if datasets are downloaded."""
    
    data_dir = Path(__file__).parent.parent / "data" / "oracle_knowledge"
    benchmark_dir = data_dir / "benchmarks"
    
    if not benchmark_dir.exists():
        logger.warning("Datasets not found!")
        logger.info("Downloading datasets first...")
        
        # Import and run downloader
        from download_reasoning_datasets import OracleKnowledgeDownloader
        
        downloader = OracleKnowledgeDownloader(str(data_dir))
        downloader.download_core_benchmarks(max_samples=500)
        
        return True
    
    benchmarks = list(benchmark_dir.glob("*_benchmark.json"))
    logger.info(f"Found {len(benchmarks)} benchmark datasets")
    return len(benchmarks) > 0


def ingest_to_grace():
    """Ingest patterns into Grace's vector database."""
    
    from reasoning_knowledge import ReasoningKnowledgeBase, GRACE_AVAILABLE
    
    if not GRACE_AVAILABLE:
        logger.error("Grace backend not available!")
        logger.error("Make sure you're running from the backend directory")
        return False
    
    kb = ReasoningKnowledgeBase()
    
    # Ingest core benchmarks
    datasets = ["gsm8k", "math", "arc", "humaneval"]
    
    total = 0
    for dataset in datasets:
        try:
            count = kb.ingest_dataset(dataset, max_samples=1000)
            total += count
            logger.info(f"✓ {dataset}: {count} patterns")
        except Exception as e:
            logger.warning(f"✗ {dataset}: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"INGESTION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total patterns: {total}")
    
    # Show stats
    stats = kb.get_stats()
    logger.info(f"Qdrant vectors: {stats.get('qdrant_vectors', 'N/A')}")
    
    return True


def test_retrieval():
    """Test the retrieval system."""
    
    from reasoning_knowledge import ReasoningKnowledgeBase
    
    kb = ReasoningKnowledgeBase()
    
    test_problems = [
        "John has 5 apples. He buys 3 more. How many apples does he have?",
        "Solve for x: 2x + 5 = 15",
        "Write a function that returns the factorial of a number",
    ]
    
    logger.info("\n" + "="*60)
    logger.info("TESTING RETRIEVAL")
    logger.info("="*60)
    
    for problem in test_problems:
        logger.info(f"\nProblem: {problem[:60]}...")
        
        result = kb.solve_by_retrieval(problem)
        
        if result.get("solved"):
            logger.info(f"  Confidence: {result['confidence']:.2f}")
            logger.info(f"  Answer: {result['predicted_answer']}")
            logger.info(f"  Similar problems found: {len(result['similar_problems'])}")
        else:
            logger.info(f"  Not solved: {result.get('message', 'Unknown error')}")


def main():
    logger.info("="*60)
    logger.info("GRACE REASONING KNOWLEDGE INGESTION")
    logger.info("="*60)
    
    # Step 1: Check/download datasets
    logger.info("\n[1/3] Checking datasets...")
    if not check_datasets():
        logger.error("Failed to get datasets")
        return
    
    # Step 2: Ingest to Grace
    logger.info("\n[2/3] Ingesting to Grace...")
    if not ingest_to_grace():
        logger.error("Failed to ingest")
        return
    
    # Step 3: Test retrieval
    logger.info("\n[3/3] Testing retrieval...")
    test_retrieval()
    
    logger.info("\n" + "="*60)
    logger.info("DONE! Grace now has reasoning knowledge.")
    logger.info("="*60)
    logger.info("\nUsage:")
    logger.info("  from reasoning_knowledge import ReasoningKnowledgeBase")
    logger.info("  kb = ReasoningKnowledgeBase()")
    logger.info("  result = kb.solve_by_retrieval('your math problem here')")


if __name__ == "__main__":
    main()
