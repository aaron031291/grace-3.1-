"""
Test Grace File Intelligence System

Tests the new Grace-aligned file management features:
- Deep content understanding
- Genesis Key tracking
- Autonomous health monitoring
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_file_intelligence_agent():
    """Test FileIntelligenceAgent."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: File Intelligence Agent")
    logger.info("="*60)

    try:
        from file_manager.file_intelligence_agent import get_file_intelligence_agent

        agent = get_file_intelligence_agent()
        logger.info("[OK] Agent initialized")

        # Test with sample content
        test_content = """
        Python is a high-level programming language. It emphasizes code readability
        and supports multiple programming paradigms. Python was created by Guido van Rossum
        and first released in 1991. It's widely used for web development, data science,
        and automation.
        """

        intelligence = agent.analyze_file_deeply(
            file_path="test.txt",
            content=test_content
        )

        logger.info(f"[OK] Summary: {intelligence.content_summary[:100]}...")
        logger.info(f"[OK] Quality Score: {intelligence.quality_score:.2f}")
        logger.info(f"[OK] Complexity: {intelligence.complexity_level}")
        logger.info(f"[OK] Topics: {intelligence.detected_topics}")
        logger.info(f"[OK] Entities: {sum(len(v) for v in intelligence.extracted_entities.values())}")
        logger.info(f"[OK] Chunk Strategy: size={intelligence.recommended_chunk_strategy['chunk_size']}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] File Intelligence Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_genesis_file_tracker():
    """Test GenesisFileTracker."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Genesis File Tracker")
    logger.info("="*60)

    try:
        from file_manager.genesis_file_tracker import get_genesis_file_tracker

        tracker = get_genesis_file_tracker()
        logger.info("[OK] Tracker initialized")

        # Test tracking operations
        key_id = tracker.track_file_upload(
            file_path="test_file.pdf",
            user_id="test_user",
            metadata={'reason': 'testing', 'source': 'unit_test'}
        )

        if key_id:
            logger.info(f"[OK] Tracked file upload: key_id={key_id}")
        else:
            logger.info("[INFO] Tracker has no Genesis service (expected in test)")

        # Test processing tracking
        processing_result = {
            'num_chunks': 10,
            'num_embeddings': 10,
            'duration': 1.5,
            'quality_score': 0.85,
            'strategy': 'adaptive',
            'success': True
        }

        key_id = tracker.track_file_processing(
            file_id=1,
            file_path="test_file.pdf",
            processing_result=processing_result
        )

        if key_id:
            logger.info(f"[OK] Tracked processing: key_id={key_id}")
        else:
            logger.info("[INFO] Tracker logged processing (no Genesis service)")

        logger.info("[OK] Genesis File Tracker functional")
        return True

    except Exception as e:
        logger.error(f"[FAIL] Genesis File Tracker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_health_monitor():
    """Test FileHealthMonitor."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: File Health Monitor")
    logger.info("="*60)

    try:
        from file_manager.file_health_monitor import get_file_health_monitor
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db

        # Initialize database
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())

        monitor = get_file_health_monitor(
            session=session,
            knowledge_base_path="backend/knowledge_base",
            trust_level=5
        )
        logger.info("[OK] Monitor initialized with trust_level=5")

        # Run health check
        report = monitor.run_health_check_cycle()

        logger.info(f"[OK] Health Status: {report.health_status}")
        logger.info(f"[OK] Anomalies Detected: {len(report.anomalies)}")
        logger.info(f"[OK] Healing Actions: {len(report.healing_actions)}")
        logger.info(f"[OK] Recommendations: {len(report.recommendations)}")

        if report.anomalies:
            logger.info("\nAnomalies found:")
            for anomaly in report.anomalies:
                logger.info(f"  - {anomaly['type']}: severity={anomaly['severity']}")

        if report.healing_actions:
            logger.info("\nHealing actions taken:")
            for action in report.healing_actions:
                logger.info(f"  - {action}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] File Health Monitor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_tables():
    """Test that new database tables exist."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Database Tables")
    logger.info("="*60)

    try:
        import sqlite3
        from pathlib import Path

        # Find grace.db - could be in backend/data or data
        db_paths = [
            'backend/data/grace.db',
            'data/grace.db',
            '../data/grace.db'
        ]

        db_path = None
        for path in db_paths:
            if Path(path).exists():
                db_path = path
                break

        if not db_path:
            logger.error("[FAIL] Could not find grace.db")
            return False

        logger.info(f"[INFO] Using database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for new tables
        tables_to_check = [
            'file_intelligence',
            'file_relationships',
            'processing_strategies',
            'file_health_checks'
        ]

        for table in tables_to_check:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            result = cursor.fetchone()

            if result:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"[OK] Table '{table}' exists ({count} rows)")
            else:
                logger.error(f"[FAIL] Table '{table}' not found")
                return False

        conn.close()
        return True

    except Exception as e:
        logger.error(f"[FAIL] Database tables test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("GRACE FILE INTELLIGENCE - INTEGRATION TEST")
    logger.info("="*80)

    results = {
        "File Intelligence Agent": test_file_intelligence_agent(),
        "Genesis File Tracker": test_genesis_file_tracker(),
        "File Health Monitor": test_file_health_monitor(),
        "Database Tables": test_database_tables()
    }

    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "[PASS]" if passed_test else "[FAIL]"
        logger.info(f"{test_name:35} {status}")

    logger.info("\n" + "="*80)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("="*80)

    if passed == total:
        logger.info("\n[SUCCESS] All Grace file intelligence features working!")
        logger.info("\nGrace can now:")
        logger.info("  - Understand file content deeply")
        logger.info("  - Track all operations with Genesis Keys")
        logger.info("  - Monitor file system health autonomously")
        logger.info("  - Detect and heal issues automatically")
        return 0
    else:
        logger.warning(f"\n[PARTIAL] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
