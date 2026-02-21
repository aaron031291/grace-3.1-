"""
Quick test script to verify autonomous learning components are working.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all required imports."""
    logger.info("Testing imports...")

    try:
        from database.session import initialize_session_factory, get_db
        logger.info("  ✓ Database session")

        from cognitive.learning_subagent_system import LearningOrchestrator
        logger.info("  ✓ Learning Orchestrator")

        from genesis.autonomous_triggers import get_genesis_trigger_pipeline
        logger.info("  ✓ Genesis Trigger Pipeline")

        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        logger.info("  ✓ Autonomous Healing System")

        from cognitive.mirror_self_modeling import get_mirror_system
        logger.info("  ✓ Mirror Self-Modeling")

        return True

    except Exception as e:
        logger.error(f"  ✗ Import failed: {e}")
        return False


def test_database():
    """Test database connection."""
    logger.info("\nTesting database connection...")

    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db

        # Initialize database connection first
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)

        initialize_session_factory()
        session = next(get_db())

        # Check for genesis keys
        import sqlite3
        conn = sqlite3.connect('data/grace.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM genesis_key')
        count = cursor.fetchone()[0]
        logger.info(f"  ✓ Database connected ({count} Genesis Keys)")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"  ✗ Database test failed: {e}")
        return False


def test_orchestrator_initialization():
    """Test Learning Orchestrator can be initialized."""
    logger.info("\nTesting Learning Orchestrator initialization...")

    try:
        from cognitive.learning_subagent_system import LearningOrchestrator

        kb_path = str(Path("knowledge_base").resolve())
        orchestrator = LearningOrchestrator(
            knowledge_base_path=kb_path,
            num_study_agents=2,
            num_practice_agents=1
        )

        logger.info(f"  ✓ Orchestrator created with {len(orchestrator.study_agents)} study agents")
        logger.info(f"  ✓ Practice agents: {len(orchestrator.practice_agents)}")
        logger.info(f"  ✓ Mirror agent: {'Yes' if orchestrator.mirror_agent else 'No'}")

        # Don't start processes in test, just verify creation
        return True

    except Exception as e:
        logger.error(f"  ✗ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trigger_pipeline():
    """Test Genesis Key Trigger Pipeline."""
    logger.info("\nTesting Genesis Key Trigger Pipeline...")

    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from genesis.autonomous_triggers import get_genesis_trigger_pipeline

        # Initialize database connection first
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)

        initialize_session_factory()
        session = next(get_db())

        trigger_pipeline = get_genesis_trigger_pipeline(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )

        status = trigger_pipeline.get_status()
        logger.info(f"  ✓ Trigger pipeline initialized")
        logger.info(f"  ✓ Status: {status['message']}")

        return True

    except Exception as e:
        logger.error(f"  ✗ Trigger pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_healing_system():
    """Test Autonomous Healing System."""
    logger.info("\nTesting Autonomous Healing System...")

    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel

        # Initialize database connection first
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)

        initialize_session_factory()
        session = next(get_db())

        healing = get_autonomous_healing(
            session=session,
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )

        logger.info(f"  ✓ Healing system initialized")
        logger.info(f"  ✓ Trust level: MEDIUM_RISK_AUTO")

        return True

    except Exception as e:
        logger.error(f"  ✗ Healing system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mirror_system():
    """Test Mirror Self-Modeling System."""
    logger.info("\nTesting Mirror Self-Modeling System...")

    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory, get_db
        from cognitive.mirror_self_modeling import get_mirror_system

        # Initialize database connection first
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)

        initialize_session_factory()
        session = next(get_db())

        mirror = get_mirror_system(
            session=session,
            observation_window_hours=24,
            min_pattern_occurrences=3
        )

        logger.info(f"  ✓ Mirror system initialized")
        logger.info(f"  ✓ Observation window: 24 hours")

        return True

    except Exception as e:
        logger.error(f"  ✗ Mirror system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("="*60)
    logger.info("GRACE AUTONOMOUS LEARNING SYSTEM - VERIFICATION TEST")
    logger.info("="*60)

    results = {
        "Imports": test_imports(),
        "Database": test_database(),
        "Learning Orchestrator": test_orchestrator_initialization(),
        "Trigger Pipeline": test_trigger_pipeline(),
        "Healing System": test_healing_system(),
        "Mirror System": test_mirror_system()
    }

    logger.info("\n" + "="*60)
    logger.info("TEST RESULTS")
    logger.info("="*60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name:25} {status}")
        if not passed:
            all_passed = False

    logger.info("="*60)

    if all_passed:
        logger.info("\n✅ ALL TESTS PASSED - System ready to start!")
        logger.info("\nRun: python start_autonomous_learning.py")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED - Fix errors before starting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
