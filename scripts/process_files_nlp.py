#!/usr/bin/env python3
"""
Script to process all files and folders through NLP to generate natural language descriptions.
Makes the filesystem "no-code friendly" for non-technical users.

Usage:
    python scripts/process_files_nlp.py [--root-path PATH] [--max-workers N] [--force]
"""

import sys
import argparse
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir.parent))

from backend.file_manager.nlp_file_descriptor import NLPFileDescriptor
from backend.file_manager.file_handler import FileHandler
from backend.ollama_client.client import get_ollama_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Process all files and folders through NLP to generate descriptions"
    )
    parser.add_argument(
        '--root-path',
        type=str,
        default=None,
        help='Root directory to process (default: workspace root)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regeneration of all descriptions'
    )
    
    args = parser.parse_args()
    
    # Determine root path
    if args.root_path:
        root_path = Path(args.root_path).resolve()
    else:
        # Default to workspace root (parent of backend)
        root_path = Path(__file__).parent.parent
    
    logger.info(f"Processing filesystem: {root_path}")
    logger.info(f"Max workers: {args.max_workers}")
    logger.info(f"Force regenerate: {args.force}")
    
    # Initialize components
    ollama_client = get_ollama_client()
    file_handler = FileHandler()
    
    # Check Ollama
    if not ollama_client.is_running():
        logger.warning("Ollama is not running. Descriptions will use fallback heuristics.")
    else:
        logger.info("Ollama is running. Will use LLM for descriptions.")
    
    # Create descriptor
    descriptor = NLPFileDescriptor(
        root_path=str(root_path),
        ollama_client=ollama_client,
        file_handler=file_handler
    )
    
    # Progress callback
    def progress_callback(current: int, total: int, path: str):
        if current % 10 == 0 or current == total:
            logger.info(f"Progress: {current}/{total} ({current*100//total if total > 0 else 0}%) - {path[:60]}")
    
    # Process all files
    logger.info("Starting processing...")
    stats = descriptor.process_all_files(
        max_workers=args.max_workers,
        force_regenerate=args.force,
        progress_callback=progress_callback
    )
    
    # Print results
    logger.info("\n" + "="*60)
    logger.info("Processing Complete!")
    logger.info("="*60)
    logger.info(f"Total items: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped (cached): {stats['skipped']}")
    logger.info(f"Total cached: {stats['cached']}")
    logger.info(f"\nDescriptions saved to: {descriptor.storage_path}")
    logger.info("\nYou can now access descriptions via the API:")
    logger.info("  GET /api/nlp-descriptions/file/{path}")
    logger.info("  GET /api/nlp-descriptions/folder/{path}")
    logger.info("  GET /api/nlp-descriptions/search?query=...")
    logger.info("  GET /api/nlp-descriptions/all")


if __name__ == "__main__":
    main()
