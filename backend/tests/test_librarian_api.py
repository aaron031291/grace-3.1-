"""
Test script for librarian API endpoints.

This script tests basic functionality of the librarian API
without starting the full server.
"""

import sys
import os
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def _init_db():
    """Lazily initialize database connection."""
    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import initialize_session_factory

    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    return initialize_session_factory()


def test_tag_operations():
    """Test tag creation and retrieval."""
    print("\n" + "="*60)
    print("TEST: Tag Operations")
    print("="*60)

    from librarian.tag_manager import TagManager

    SessionLocal = _init_db()
    db = SessionLocal()
    tag_manager = TagManager(db)

    # Create a test tag
    tag = tag_manager.get_or_create_tag(
        name="api-test",
        description="Test tag created via API test",
        category="testing",
        color="#00FF00"
    )
    print(f"  [OK] Created tag: {tag.name} (ID: {tag.id})")

    # Get all tags
    all_tags = db.query(tag.__class__).all()
    print(f"  [OK] Total tags in system: {len(all_tags)}")

    # Get tag statistics
    stats = tag_manager.get_tag_statistics()
    print(f"  [OK] Tag statistics retrieved: {stats['total_tags']} tags")

    db.close()
    print("\n[OK] Tag operations working")


def test_librarian_engine_integration():
    """Test librarian engine with API-like operations."""
    print("\n" + "="*60)
    print("TEST: Librarian Engine Integration")
    print("="*60)

    from librarian.engine import LibrarianEngine
    from embedding import get_embedding_model
    from llm_orchestrator.factory import get_llm_client
    from vector_db.client import get_qdrant_client
    from settings import settings

    SessionLocal = _init_db()
    db = SessionLocal()

    # Create librarian engine
    librarian = LibrarianEngine(
        db_session=db,
        embedding_model=get_embedding_model(),
        llm_client=get_llm_client(),
        vector_db_client=get_qdrant_client(),
        ai_model_name=settings.LIBRARIAN_AI_MODEL,
        use_ai=False,  # Disable AI for quick test
        detect_relationships=False,
        ai_confidence_threshold=settings.LIBRARIAN_AI_CONFIDENCE_THRESHOLD,
        similarity_threshold=settings.LIBRARIAN_SIMILARITY_THRESHOLD
    )
    print("  [OK] Librarian engine initialized")

    # Get system statistics
    stats = librarian.get_system_statistics()
    print(f"  [OK] System statistics:")
    print(f"      - Total tags: {stats['tags']['total_tags']}")
    print(f"      - Active rules: {stats['rules']['total_rules']}")
    print(f"      - AI available: {stats['ai_available']}")

    # Health check
    health = librarian.health_check()
    print(f"  [OK] Health check: {health['overall_status']}")
    if 'database' in health:
        print(f"      - Database: {health['database']}")
    if 'vector_db' in health:
        print(f"      - Vector DB: {health['vector_db']}")

    db.close()
    print("\n[OK] Librarian engine integration working")


def test_rule_operations():
    """Test rule-based categorization."""
    print("\n" + "="*60)
    print("TEST: Rule Operations")
    print("="*60)

    from librarian.rule_categorizer import RuleBasedCategorizer

    SessionLocal = _init_db()
    db = SessionLocal()
    categorizer = RuleBasedCategorizer(db)

    # Get rule statistics
    stats = categorizer.get_rule_statistics()
    print(f"  [OK] Rule statistics:")
    print(f"      - Total rules: {stats['total_rules']}")
    if 'active_rules' in stats:
        print(f"      - Active rules: {stats['active_rules']}")

    if stats.get('most_effective'):
        print(f"  [OK] Most effective rules:")
        for rule in stats['most_effective'][:3]:
            print(f"      - {rule['name']}: {rule['matches_count']} matches")

    db.close()
    print("\n[OK] Rule operations working")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("LIBRARIAN API - INTEGRATION TEST")
    print("="*60)

    tests = [
        ("Tag Operations", test_tag_operations),
        ("Rule Operations", test_rule_operations),
        ("Librarian Engine", test_librarian_engine_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, True))
        except Exception as e:
            print(f"\n[FAIL] {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)
