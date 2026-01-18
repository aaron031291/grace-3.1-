#!/usr/bin/env python3
"""
Train Grace on GitHub Failures

Loads broken code examples from GitHub collection and trains Grace
to fix them in a sandbox environment.

Usage:
    python scripts/train_on_github_failures.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--max MAX_EXAMPLES]
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train Grace on GitHub failures"
    )
    parser.add_argument(
        '--input',
        type=str,
        default='github_failures_10000.json',
        help='Input file with GitHub failures (default: github_failures_10000.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='github_training_results.json',
        help='Output file for training results (default: github_training_results.json)'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help='Maximum examples to process (default: all)'
    )
    parser.add_argument(
        '--sandbox-dir',
        type=str,
        default=None,
        help='Sandbox directory (default: temporary)'
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.info("Run collect_github_failures_enhanced.py first to collect failures")
        return 1
    
    # Initialize systems
    logger.info("Initializing Grace systems...")
    
    try:
        # Database session
        from backend.database.session import initialize_session_factory
        session_factory = initialize_session_factory()
        session = session_factory()
    except Exception as e:
        logger.warning(f"Could not create database session: {e}")
        logger.info("Creating mock session...")
        from unittest.mock import MagicMock
        session = MagicMock()
    
    # Coding agent
    try:
        from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent
        coding_agent = EnterpriseCodingAgent(
            session=session,
            enable_learning=True,
            enable_sandbox=True
        )
        logger.info("✓ Coding agent initialized")
    except Exception as e:
        logger.error(f"Failed to initialize coding agent: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Learning memory
    try:
        from backend.cognitive.learning_memory import LearningMemoryManager
        knowledge_base_path = project_root / "knowledge_base"
        learning_memory = LearningMemoryManager(
            session=session,
            knowledge_base_path=knowledge_base_path
        )
        logger.info("✓ Learning memory initialized")
    except Exception as e:
        logger.warning(f"Could not initialize learning memory: {e}")
        learning_memory = None
    
    # Memory mesh (optional)
    memory_mesh = None
    try:
        from backend.cognitive.memory_mesh_integration import MemoryMeshIntegration
        memory_mesh = MemoryMeshIntegration(session=session)
        logger.info("✓ Memory mesh initialized")
    except Exception as e:
        logger.warning(f"Could not initialize memory mesh: {e}")
    
    # Initialize training system
    try:
        from backend.cognitive.github_failures_sandbox_training import GitHubFailuresSandboxTraining
        
        sandbox_dir = Path(args.sandbox_dir) if args.sandbox_dir else None
        
        training = GitHubFailuresSandboxTraining(
            coding_agent=coding_agent,
            learning_memory=learning_memory,
            memory_mesh=memory_mesh,
            sandbox_dir=sandbox_dir,
            max_examples=args.max
        )
        logger.info("✓ Training system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize training system: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Load failures
    logger.info(f"Loading failures from {input_path}...")
    examples = training.load_failures_from_file(input_path)
    
    if not examples:
        logger.error("No examples loaded!")
        return 1
    
    logger.info(f"Loaded {len(examples)} examples")
    
    # Run training
    logger.info("Starting training...")
    print("\n" + "="*80)
    print("GITHUB FAILURES SANDBOX TRAINING")
    print("="*80)
    print(f"Examples to process: {len(examples)}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()
    
    progress = training.train(examples)
    
    # Save results
    output_path = Path(args.output)
    training.save_results(output_path)
    
    # Print summary
    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    print(f"Total examples: {progress.total_examples}")
    print(f"Attempted: {progress.attempted}")
    print(f"Fixed: {progress.fixed}")
    print(f"Failed: {progress.failed}")
    print(f"Errors: {progress.errors}")
    print(f"Skipped: {progress.skipped}")
    print(f"Success Rate: {progress.success_rate:.1f}%")
    print(f"\nResults saved to: {output_path}")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
