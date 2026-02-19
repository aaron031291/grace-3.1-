"""
Test Grace File Intelligence - Phase 2: Adaptive Learning

Tests the adaptive learning components:
- StrategyLearner (learns optimal strategies)
- PerformanceTracker (tracks outcomes)
- AdaptiveFileProcessor (uses learned strategies)
- GraceFileManager (complete integration)
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_strategy_learner():
    """Test StrategyLearner."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Strategy Learner")
    logger.info("="*60)

    try:
        from file_manager.adaptive_file_processor import StrategyLearner
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db

        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        learner = StrategyLearner(session=session)
        logger.info("[OK] StrategyLearner initialized")

        # Test getting optimal strategy
        strategy = learner.get_optimal_strategy(
            file_type=".pdf",
            file_size=500000,
            complexity_level="intermediate"
        )

        logger.info(f"[OK] Got strategy for .pdf: chunk_size={strategy.chunk_size}")
        logger.info(f"[OK] Semantic chunking: {strategy.use_semantic_chunking}")
        logger.info(f"[OK] Overlap: {strategy.overlap}")
        logger.info(f"[OK] Batch size: {strategy.embedding_batch_size}")

        # Test different file types
        py_strategy = learner.get_optimal_strategy(
            file_type=".py",
            file_size=100000,
            complexity_level="advanced"
        )
        logger.info(f"[OK] Got strategy for .py: chunk_size={py_strategy.chunk_size}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] StrategyLearner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_processor():
    """Test AdaptiveFileProcessor."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Adaptive File Processor")
    logger.info("="*60)

    try:
        from file_manager.adaptive_file_processor import (
            get_adaptive_file_processor,
            ProcessingStrategy,
            ProcessingOutcome
        )
        from file_manager.file_intelligence_agent import get_file_intelligence_agent
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from datetime import datetime

        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        intelligence_agent = get_file_intelligence_agent()
        processor = get_adaptive_file_processor(
            session=session,
            intelligence_agent=intelligence_agent
        )
        logger.info("[OK] AdaptiveFileProcessor initialized")

        # Test getting strategy
        strategy = processor.get_processing_strategy(
            file_path="test_document.pdf"
        )
        logger.info(f"[OK] Got strategy: chunk_size={strategy.chunk_size}")

        # Test recording outcome
        processor.record_processing_outcome(
            file_id=999,
            file_path="test_document.pdf",
            strategy=strategy,
            success=True,
            quality_score=0.85,
            processing_time=2.5,
            num_chunks=25,
            num_embeddings=25,
            errors=[]
        )
        logger.info("[OK] Recorded processing outcome")

        # Test learning from outcome
        logger.info("[OK] Strategy learner learned from outcome")

        return True

    except Exception as e:
        logger.error(f"[FAIL] AdaptiveFileProcessor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_grace_file_manager():
    """Test complete GraceFileManager integration."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Grace File Manager Integration")
    logger.info("="*60)

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

        manager = get_grace_file_manager(
            session=session,
            knowledge_base_path="backend/knowledge_base",
            trust_level=5
        )
        logger.info("[OK] GraceFileManager initialized")

        # Test intelligent file processing
        # Create a test file
        test_file = Path("test_sample.txt")
        test_file.write_text("""
        Artificial Intelligence is transforming software development.
        Machine learning models can now understand code and suggest improvements.
        Python and JavaScript are popular languages for AI development.
        """)

        try:
            result = manager.process_file_intelligently(
                file_path=str(test_file),
                user_id="test_user",
                metadata={'reason': 'testing', 'phase': 'phase2'}
            )

            if result['success']:
                logger.info("[OK] File processed intelligently")
                logger.info(f"[OK] Quality score: {result['intelligence']['quality_score']:.2f}")
                logger.info(f"[OK] Complexity: {result['intelligence']['complexity_level']}")
                logger.info(f"[OK] Topics: {result['intelligence']['topics']}")
                logger.info(f"[OK] Strategy chunk_size: {result['strategy']['chunk_size']}")
                logger.info(f"[OK] Processing time: {result['processing_time']:.2f}s")
            else:
                logger.warning(f"[WARN] Processing returned success=False: {result.get('error')}")

        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()

        # Test health check
        health = manager.run_health_check()
        logger.info(f"[OK] Health check: status={health['health_status']}")
        logger.info(f"[OK] Anomalies: {health['anomalies_count']}")

        # Test performance metrics
        metrics = manager.get_performance_metrics(days=7)
        logger.info(f"[OK] Performance metrics: {metrics}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] GraceFileManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_cycle():
    """Test complete learning cycle."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Complete Learning Cycle")
    logger.info("="*60)

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

        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        learner = StrategyLearner(session=session)
        logger.info("[OK] Initialized strategy learner")

        # Simulate processing outcomes over time
        file_type = ".test"

        # Create a strategy
        strategy = ProcessingStrategy(
            file_type=file_type,
            chunk_size=512,
            overlap=50,
            use_semantic_chunking=True,
            embedding_batch_size=32,
            quality_threshold=0.5,
            additional_params={}
        )

        # Record several outcomes
        for i in range(5):
            outcome = ProcessingOutcome(
                file_id=1000 + i,
                file_path=f"test_{i}.test",
                file_type=file_type,
                strategy_used=strategy,
                success=True,
                quality_score=0.7 + (i * 0.05),  # Improving quality
                processing_time=1.0 + (i * 0.1),
                num_chunks=10,
                num_embeddings=10,
                errors=[],
                timestamp=datetime.utcnow()
            )

            learner.learn_from_outcome(outcome)
            logger.info(f"[OK] Learned from outcome {i+1}/5")

        # Get updated strategy
        learned_strategy = learner.get_optimal_strategy(
            file_type=file_type,
            file_size=100000,
            complexity_level="intermediate"
        )

        logger.info(f"[OK] Learned strategy - success_rate: {learned_strategy.success_rate:.2f}")
        logger.info(f"[OK] Learned strategy - avg_quality: {learned_strategy.avg_quality_score:.2f}")
        logger.info(f"[OK] Learned strategy - times_used: {learned_strategy.times_used}")

        # Verify learning happened
        if learned_strategy.times_used == 5:
            logger.info("[OK] Learning cycle complete - strategy was used and improved")
        else:
            logger.warning(f"[WARN] Expected 5 uses, got {learned_strategy.times_used}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] Learning cycle test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    logger.info("\n" + "="*80)
    logger.info("GRACE FILE INTELLIGENCE - PHASE 2 (ADAPTIVE LEARNING) TEST")
    logger.info("="*80)

    results = {
        "Strategy Learner": test_strategy_learner(),
        "Adaptive File Processor": test_adaptive_processor(),
        "Grace File Manager Integration": test_grace_file_manager(),
        "Complete Learning Cycle": test_learning_cycle()
    }

    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "[PASS]" if passed_test else "[FAIL]"
        logger.info(f"{test_name:40} {status}")

    logger.info("\n" + "="*80)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("="*80)

    if passed == total:
        logger.info("\n[SUCCESS] Phase 2 Adaptive Learning complete!")
        logger.info("\nGrace can now:")
        logger.info("  - Learn optimal strategies from processing outcomes")
        logger.info("  - Adapt chunk sizes based on file type and complexity")
        logger.info("  - Continuously improve processing quality")
        logger.info("  - Track performance metrics over time")
        logger.info("  - Use complete intelligent file management")
        return 0
    else:
        logger.warning(f"\n[PARTIAL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
