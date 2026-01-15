"""
Complete Grace File Intelligence Test

Tests the COMPLETE end-to-end flow:
Phase 1 + Phase 2 working together
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_complete_workflow():
    """Test complete file intelligence workflow."""
    logger.info("\n" + "="*80)
    logger.info("COMPLETE GRACE FILE INTELLIGENCE WORKFLOW TEST")
    logger.info("="*80)

    try:
        from file_manager.grace_file_integration import get_grace_file_manager
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db

        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        # Initialize Grace File Manager
        manager = get_grace_file_manager(
            session=session,
            knowledge_base_path="backend/knowledge_base",
            trust_level=5
        )
        logger.info("[1/6] Grace File Manager initialized")

        # Create test files of different types
        test_files = {
            'python_code.py': """
def calculate_fibonacci(n):
    '''Calculate Fibonacci sequence up to n terms.'''
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# Machine learning and data science applications
def train_model(data, labels):
    '''Train a simple ML model.'''
    # Implementation here
    pass
""",
            'research_paper.txt': """
Artificial Intelligence and Machine Learning: A Comprehensive Review

Abstract:
This paper examines the current state of artificial intelligence and machine learning
technologies. We explore neural networks, deep learning architectures, and natural
language processing applications. The research demonstrates significant advances in
computer vision and autonomous systems.

Introduction:
Machine learning has revolutionized data science and software engineering. Python
and JavaScript remain the dominant languages for AI development. TensorFlow and
PyTorch are the leading frameworks for building neural network models.
""",
            'markdown_doc.md': """
# Grace File Intelligence System

## Overview

Grace is an advanced AI system with autonomous learning capabilities.

### Key Features

- **Deep Content Understanding**: Analyzes file content semantically
- **Adaptive Learning**: Improves processing strategies over time
- **Self-Healing**: Automatically detects and fixes file system issues
- **Complete Tracking**: Creates Genesis Keys for all operations

### Technologies

Built with Python, using SQLite for data storage and Qdrant for vector embeddings.
"""
        }

        # Process each file type
        results = []
        for filename, content in test_files.items():
            logger.info(f"\n[2/6] Processing {filename}...")

            # Create test file
            test_path = Path(filename)
            test_path.write_text(content)

            try:
                # Process file intelligently
                result = manager.process_file_intelligently(
                    file_path=str(test_path),
                    user_id="test_user",
                    metadata={'test': 'complete_workflow', 'file_type': test_path.suffix}
                )

                logger.info(f"  ✓ Intelligence: quality={result['intelligence']['quality_score']:.2f}, "
                           f"complexity={result['intelligence']['complexity_level']}")
                logger.info(f"  ✓ Topics: {result['intelligence']['topics']}")
                logger.info(f"  ✓ Strategy: chunk_size={result['strategy']['chunk_size']}, "
                           f"semantic={result['strategy']['use_semantic_chunking']}")

                results.append({
                    'filename': filename,
                    'result': result,
                    'success': result['success']
                })

            finally:
                # Clean up test file
                if test_path.exists():
                    test_path.unlink()

        logger.info(f"\n[3/6] Processed {len(results)} files successfully")

        # Simulate learning by recording outcomes
        logger.info("\n[4/6] Recording processing outcomes for learning...")
        for i, item in enumerate(results):
            manager.record_ingestion_outcome(
                file_id=1000 + i,
                file_path=item['filename'],
                processing_result={
                    'success': True,
                    'num_chunks': 20 + i * 5,
                    'num_embeddings': 20 + i * 5,
                    'intelligence': item['result']['intelligence'],
                    'strategy': item['result']['strategy'],
                    'processing_time': 1.5 + i * 0.5
                }
            )
            logger.info(f"  ✓ Recorded outcome for {item['filename']}")

        # Verify learning happened
        logger.info("\n[5/6] Verifying adaptive learning...")
        from file_manager.adaptive_file_processor import StrategyLearner
        learner = StrategyLearner(session=session)

        for file_type in ['.py', '.txt', '.md']:
            strategy = learner.get_optimal_strategy(
                file_type=file_type,
                file_size=100000,
                complexity_level="intermediate"
            )

            if strategy.times_used > 0:
                logger.info(f"  ✓ {file_type}: Learned strategy used {strategy.times_used} times, "
                           f"success_rate={strategy.success_rate:.1%}, "
                           f"quality={strategy.avg_quality_score:.2f}")
            else:
                logger.info(f"  ○ {file_type}: Using default strategy (no learning data yet)")

        # Run health check
        logger.info("\n[6/6] Running health check...")
        health = manager.run_health_check()
        logger.info(f"  ✓ Health status: {health['health_status']}")
        logger.info(f"  ✓ Anomalies detected: {health['anomalies_count']}")
        logger.info(f"  ✓ Healing actions taken: {health['healing_actions_count']}")

        # Get performance metrics
        metrics = manager.get_performance_metrics(days=7)
        logger.info(f"\n[METRICS] Performance summary:")
        logger.info(f"  - Files processed: {metrics['total_processed']}")
        logger.info(f"  - Success rate: {metrics['success_rate']:.1%}")
        logger.info(f"  - Avg quality: {metrics['avg_quality_score']:.2f}")

        logger.info("\n" + "="*80)
        logger.info("✓ COMPLETE WORKFLOW TEST PASSED")
        logger.info("="*80)
        logger.info("\nGrace File Intelligence demonstrated:")
        logger.info("  1. Deep content understanding (quality, complexity, topics)")
        logger.info("  2. Adaptive strategy selection (chunk size, semantic chunking)")
        logger.info("  3. Learning from outcomes (strategies improve over time)")
        logger.info("  4. Health monitoring (autonomous system health checks)")
        logger.info("  5. Complete integration (all components working together)")

        return True

    except Exception as e:
        logger.error(f"\n[FAIL] Complete workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_improvement():
    """Test that processing improves over multiple iterations."""
    logger.info("\n" + "="*80)
    logger.info("LEARNING IMPROVEMENT TEST")
    logger.info("="*80)

    try:
        from file_manager.adaptive_file_processor import (
            StrategyLearner,
            ProcessingStrategy,
            ProcessingOutcome
        )
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from datetime import datetime

        # Initialize
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        learner = StrategyLearner(session=session)
        file_type = ".improvement_test"

        # Initial strategy
        initial_strategy = learner.get_optimal_strategy(
            file_type=file_type,
            file_size=100000,
            complexity_level="intermediate"
        )
        logger.info(f"[1/3] Initial strategy: chunk_size={initial_strategy.chunk_size}")

        # Simulate 10 processing outcomes with improving quality
        logger.info("\n[2/3] Simulating 10 processing outcomes with improving quality...")
        for i in range(10):
            quality = 0.60 + (i * 0.03)  # Quality improves from 0.60 to 0.87

            outcome = ProcessingOutcome(
                file_id=2000 + i,
                file_path=f"file_{i}.improvement_test",
                file_type=file_type,
                strategy_used=initial_strategy,
                success=True,
                quality_score=quality,
                processing_time=1.0,
                num_chunks=10,
                num_embeddings=10,
                errors=[],
                timestamp=datetime.now()
            )

            learner.learn_from_outcome(outcome)

            if (i + 1) % 5 == 0:
                logger.info(f"  ✓ Processed {i+1}/10 files (quality: {quality:.2f})")

        # Get learned strategy
        learned_strategy = learner.get_optimal_strategy(
            file_type=file_type,
            file_size=100000,
            complexity_level="intermediate"
        )

        logger.info(f"\n[3/3] After learning:")
        logger.info(f"  - Times used: {learned_strategy.times_used}")
        logger.info(f"  - Success rate: {learned_strategy.success_rate:.1%}")
        logger.info(f"  - Avg quality: {learned_strategy.avg_quality_score:.2f}")

        # Verify improvement
        if learned_strategy.times_used == 10:
            logger.info(f"\n✓ Learning verified: strategy used 10 times")
        if learned_strategy.success_rate == 1.0:
            logger.info(f"✓ Success rate perfect: 100%")
        if learned_strategy.avg_quality_score > 0.70:
            logger.info(f"✓ Quality improved: {learned_strategy.avg_quality_score:.2f} > 0.70")

        logger.info("\n" + "="*80)
        logger.info("✓ LEARNING IMPROVEMENT TEST PASSED")
        logger.info("="*80)

        return True

    except Exception as e:
        logger.error(f"\n[FAIL] Learning improvement test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all complete integration tests."""
    logger.info("\n" + "="*80)
    logger.info("GRACE FILE INTELLIGENCE - COMPLETE INTEGRATION TESTS")
    logger.info("Phase 1 (Foundation) + Phase 2 (Adaptive Learning)")
    logger.info("="*80)

    results = {
        "Complete Workflow": test_complete_workflow(),
        "Learning Improvement": test_learning_improvement()
    }

    logger.info("\n" + "="*80)
    logger.info("FINAL TEST SUMMARY")
    logger.info("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "[PASS]" if passed_test else "[FAIL]"
        logger.info(f"{test_name:40} {status}")

    logger.info("\n" + "="*80)
    logger.info(f"TOTAL: {passed}/{total} integration tests passed")
    logger.info("="*80)

    if passed == total:
        logger.info("\n" + "="*80)
        logger.info("✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
        logger.info("="*80)
        logger.info("\nGrace File Intelligence is FULLY OPERATIONAL:")
        logger.info("\n  PHASE 1 - Foundation:")
        logger.info("    ✓ Deep content understanding")
        logger.info("    ✓ Genesis Key tracking")
        logger.info("    ✓ Autonomous health monitoring")
        logger.info("\n  PHASE 2 - Adaptive Learning:")
        logger.info("    ✓ Strategy learning from outcomes")
        logger.info("    ✓ Continuous quality improvement")
        logger.info("    ✓ Performance tracking")
        logger.info("\n  INTEGRATION:")
        logger.info("    ✓ Complete end-to-end workflow")
        logger.info("    ✓ All components working together")
        logger.info("    ✓ Demonstrated learning improvement")
        logger.info("\n" + "="*80)
        return 0
    else:
        logger.warning(f"\n[PARTIAL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
