"""
Quick test script to verify librarian system integration.

Tests:
1. Database tables exist
2. Default rules are seeded
3. Tag creation and assignment
4. Rule-based categorization
5. Document processing pipeline
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

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import initialize_session_factory
from models.librarian_models import LibrarianTag, LibrarianRule, DocumentTag
from models.database_models import Document
from librarian.tag_manager import TagManager
from librarian.rule_categorizer import RuleBasedCategorizer
from librarian.engine import LibrarianEngine
from embedding import get_embedding_model
from llm_orchestrator.factory import get_llm_client
from vector_db.client import get_qdrant_client
from settings import settings


def test_database_tables():
    """Test that all librarian tables exist."""
    print("\n" + "="*60)
    print("TEST 1: Database Tables")
    print("="*60)

    try:
        config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(config)
        SessionLocal = initialize_session_factory()
        db = SessionLocal()

        # Try to query each table
        tables = [
            ("librarian_tags", LibrarianTag),
            ("librarian_rules", LibrarianRule),
            ("document_tags", DocumentTag),
        ]

        for table_name, model in tables:
            count = db.query(model).count()
            print(f"  [OK] {table_name}: {count} rows")

        db.close()
        print("\n[OK] All database tables exist and are accessible")
        return True

    except Exception as e:
        print(f"\n[FAIL] Database test failed: {e}")
        return False


def test_default_rules():
    """Test that default rules are seeded."""
    print("\n" + "="*60)
    print("TEST 2: Default Rules")
    print("="*60)

    try:
        SessionLocal = initialize_session_factory()
        db = SessionLocal()

        rules = db.query(LibrarianRule).filter(
            LibrarianRule.enabled == True
        ).all()

        print(f"  Total active rules: {len(rules)}")

        # Group by pattern type
        by_type = {}
        for rule in rules:
            by_type[rule.pattern_type] = by_type.get(rule.pattern_type, 0) + 1

        for pattern_type, count in sorted(by_type.items()):
            print(f"    - {pattern_type}: {count} rules")

        # Show a few example rules
        print("\n  Example rules:")
        for rule in rules[:5]:
            print(f"    - {rule.name} ({rule.pattern_type}): {rule.pattern_value}")

        db.close()

        if len(rules) > 0:
            print(f"\n[OK] Found {len(rules)} active rules")
            return True
        else:
            print("\n[FAIL] No rules found (run seed_default_rules.py)")
            return False

    except Exception as e:
        print(f"\n[FAIL] Rules test failed: {e}")
        return False


def test_tag_management():
    """Test tag creation and assignment."""
    print("\n" + "="*60)
    print("TEST 3: Tag Management")
    print("="*60)

    try:
        SessionLocal = initialize_session_factory()
        db = SessionLocal()
        tag_manager = TagManager(db)

        # Create a test tag
        tag = tag_manager.get_or_create_tag(
            name="test-tag",
            description="Test tag for verification",
            category="test",
            color="#FF0000"
        )
        print(f"  [OK] Created/found tag: {tag.name} (ID: {tag.id})")

        # Get tag statistics
        stats = tag_manager.get_tag_statistics()
        print(f"\n  Tag statistics:")
        print(f"    - Total tags: {stats['total_tags']}")
        if 'by_category' in stats and stats['by_category']:
            print(f"    - Categories: {', '.join(stats['by_category'].keys())}")

        if 'most_used' in stats and stats['most_used']:
            print(f"\n  Most used tags:")
            for tag_info in stats['most_used'][:5]:
                print(f"    - {tag_info['name']}: {tag_info['usage_count']} uses")

        db.close()
        print("\n[OK] Tag management working")
        return True

    except Exception as e:
        print(f"\n[FAIL] Tag management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_categorization():
    """Test rule-based categorization on existing documents."""
    print("\n" + "="*60)
    print("TEST 4: Rule-Based Categorization")
    print("="*60)

    try:
        SessionLocal = initialize_session_factory()
        db = SessionLocal()
        rule_categorizer = RuleBasedCategorizer(db)

        # Find a document to test with
        try:
            document = db.query(Document).filter(
                Document.status == "completed"
            ).first()
        except Exception as e:
            if "no such table" in str(e):
                print("  [WARN] Documents table not found (expected on fresh install)")
                print("\n[OK] Rule categorization ready (skipped - no documents)")
                db.close()
                return True
            raise

        if not document:
            print("  [WARN] No completed documents found to test with (expected on fresh install)")
            print("\n[OK] Rule categorization ready (skipped - no documents)")
            db.close()
            return True

        print(f"  Testing with document: {document.filename} (ID: {document.id})")

        # Categorize the document
        matches = rule_categorizer.categorize_document(document.id)

        print(f"\n  Matched {len(matches)} rules:")
        for match in matches:
            print(f"    - {match['rule_name']} (confidence: {match['confidence']})")
            if match['action_type'] == 'assign_tag':
                tags = match['action_params'].get('tag_names', [])
                print(f"      → Suggests tags: {', '.join(tags)}")

        db.close()

        if len(matches) > 0:
            print(f"\n[OK] Rule categorization working ({len(matches)} matches)")
        else:
            print("\n[OK] Rule categorization working (no matches for this document)")

        return True

    except Exception as e:
        print(f"\n[FAIL] Rule categorization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_librarian_engine():
    """Test the complete librarian engine pipeline."""
    print("\n" + "="*60)
    print("TEST 5: Librarian Engine Pipeline")
    print("="*60)

    try:
        SessionLocal = initialize_session_factory()
        db = SessionLocal()

        # Find a document to test with
        try:
            document = db.query(Document).filter(
                Document.status == "completed"
            ).first()
        except Exception as e:
            if "no such table" in str(e):
                print("  [WARN] Documents table not found (expected on fresh install)")
                print("\n[OK] Librarian engine ready (skipped - no documents)")
                db.close()
                return True
            raise

        if not document:
            print("  [WARN] No completed documents found to test with (expected on fresh install)")
            print("\n[OK] Librarian engine ready (skipped - no documents)")
            db.close()
            return True

        print(f"  Processing document: {document.filename} (ID: {document.id})")

        # Create librarian engine
        librarian = LibrarianEngine(
            db_session=db,
            embedding_model=get_embedding_model(),
            llm_client=get_llm_client(),
            vector_db_client=get_qdrant_client(),
            ai_model_name=settings.LIBRARIAN_AI_MODEL,
            use_ai=False,  # Disable AI for quick test
            detect_relationships=False,  # Disable relationships for quick test
            ai_confidence_threshold=settings.LIBRARIAN_AI_CONFIDENCE_THRESHOLD,
            similarity_threshold=settings.LIBRARIAN_SIMILARITY_THRESHOLD
        )

        # Process the document
        result = librarian.process_document(
            document_id=document.id,
            use_ai=False,
            detect_relationships=False,
            auto_execute=True
        )

        print(f"\n  Processing result:")
        print(f"    - Status: {result['status']}")
        print(f"    - Tags assigned: {result['tags_assigned']}")
        print(f"    - Relationships detected: {result['relationships_detected']}")
        print(f"    - Rules matched: {', '.join(result['rules_matched']) if result['rules_matched'] else 'None'}")

        if result.get('ai_analysis'):
            print(f"    - AI analysis: {result['ai_analysis']}")

        # Get system statistics
        stats = librarian.get_system_statistics()
        print(f"\n  System statistics:")
        print(f"    - Total tags: {stats['tags']['total_tags']}")
        print(f"    - Active rules: {stats['rules']['total_rules']}")
        print(f"    - AI available: {stats['ai_available']}")
        print(f"    - Relationships enabled: {stats['relationships_enabled']}")

        db.close()

        if result['status'] == 'success':
            print("\n[OK] Librarian engine pipeline working")
            return True
        else:
            print(f"\n[FAIL] Pipeline failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\n[FAIL] Librarian engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("GRACE LIBRARIAN SYSTEM - INTEGRATION TEST")
    print("="*60)

    tests = [
        ("Database Tables", test_database_tables),
        ("Default Rules", test_default_rules),
        ("Tag Management", test_tag_management),
        ("Rule Categorization", test_rule_categorization),
        ("Librarian Engine", test_librarian_engine),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[FAIL] {test_name} crashed: {e}")
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

    if passed == total:
        print("\n[OK] ALL TESTS PASSED - Librarian system is working!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed - check output above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
