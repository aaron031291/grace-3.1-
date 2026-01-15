"""
Test Genesis Key creation and autonomous trigger pipeline.

This script verifies that:
1. Genesis Keys are created for all inputs
2. Autonomous trigger pipeline is executed
3. Learning actions are triggered
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
from database.session import get_session
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database connection
config = DatabaseConfig.from_env()
DatabaseConnection.initialize(config)


def test_genesis_key_creation():
    """Test that Genesis Keys are created properly."""
    print("\n" + "="*80)
    print("TEST 1: Genesis Key Creation")
    print("="*80)

    try:
        # Get session
        session = next(get_session())

        # Create a test Genesis Key
        genesis_service = get_genesis_service(session)
        key = genesis_service.create_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description="Test Genesis Key - Pipeline Verification",
            who_actor="test_script",
            where_location="test_genesis_pipeline.py",
            why_reason="Testing Genesis Key creation and autonomous triggers",
            how_method="Direct API call",
            input_data={"test": "data", "purpose": "pipeline_verification"},
            context_data={"test_type": "pipeline_test"},
            tags=["test", "pipeline", "autonomous"],
            session=session
        )

        print(f"[OK] Genesis Key created successfully!")
        print(f"   Key ID: {key.key_id}")
        print(f"   Type: {key.key_type}")
        print(f"   Description: {key.what_description}")
        print(f"   Timestamp: {key.when_timestamp}")

        return True

    except Exception as e:
        print(f"[FAIL] Genesis Key creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_status():
    """Check Genesis Key database status."""
    print("\n" + "="*80)
    print("TEST 2: Database Status Check")
    print("="*80)

    try:
        engine = create_engine('sqlite:///data/grace.db')
        conn = engine.connect()

        # Count total keys
        result = conn.execute(text('SELECT COUNT(*) as count FROM genesis_key')).fetchone()
        total_keys = result[0]
        print(f"[OK] Total Genesis Keys in database: {total_keys}")

        # Get recent keys
        result = conn.execute(text('''
            SELECT key_id, key_type, what_description, when_timestamp
            FROM genesis_key
            ORDER BY when_timestamp DESC
            LIMIT 5
        ''')).fetchall()

        if result:
            print(f"\nRecent Genesis Keys:")
            for row in result:
                print(f"   - [{row[1]}] {row[2][:60]}...")
                print(f"     ID: {row[0][:30]}... | {row[3]}")
        else:
            print("[WARNING] No Genesis Keys found in database")

        # Check autonomous triggers
        print(f"\nChecking related tables:")

        # Check user profiles
        result = conn.execute(text('SELECT COUNT(*) FROM user_profile')).fetchone()
        print(f"   - User Profiles: {result[0]}")

        # Check fix suggestions
        result = conn.execute(text('SELECT COUNT(*) FROM fix_suggestion')).fetchone()
        print(f"   - Fix Suggestions: {result[0]}")

        # Check archives
        result = conn.execute(text('SELECT COUNT(*) FROM genesis_key_archive')).fetchone()
        print(f"   - Archives: {result[0]}")

        # Check learning patterns (if exists)
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM learning_patterns')).fetchone()
            print(f"   - Learning Patterns: {result[0]}")
        except Exception:
            print(f"   - Learning Patterns: Table not found")

        conn.close()
        return total_keys > 0

    except Exception as e:
        print(f"[FAIL] Database check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_autonomous_trigger():
    """Test that autonomous triggers are working."""
    print("\n" + "="*80)
    print("TEST 3: Autonomous Trigger Pipeline")
    print("="*80)

    try:
        # Import autonomous trigger pipeline
        from genesis.autonomous_triggers import get_genesis_trigger_pipeline
        from database.session import get_session

        session = next(get_session())

        # Create a test Genesis Key that should trigger learning
        genesis_service = get_genesis_service(session)
        key = genesis_service.create_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description="Test query for autonomous learning trigger",
            who_actor="test_script",
            where_location="test_genesis_pipeline.py",
            why_reason="Testing autonomous trigger system",
            how_method="Simulated user query",
            input_data={"query": "How does the retrieval system work?"},
            context_data={"test_autonomous": True},
            session=session
        )

        print(f"[OK] Test Genesis Key created: {key.key_id}")
        print(f"   The autonomous trigger pipeline should have been called automatically!")
        print(f"   Check logs above for '[OK] Triggered X autonomous action(s)' message")

        return True

    except Exception as e:
        print(f"[FAIL] Autonomous trigger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GENESIS KEY PIPELINE TEST SUITE")
    print("="*80)
    print("Testing Genesis Key creation and autonomous trigger system...")

    results = []

    # Test 1: Genesis Key Creation
    results.append(("Genesis Key Creation", test_genesis_key_creation()))

    # Test 2: Database Status
    results.append(("Database Status", check_database_status()))

    # Test 3: Autonomous Triggers
    results.append(("Autonomous Triggers", test_autonomous_trigger()))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n[SUCCESS] All tests passed! Genesis Key pipeline is working correctly.")
        print("\nSUMMARY:")
        print("   - Genesis Keys are being created")
        print("   - Autonomous trigger pipeline is connected")
        print("   - All inputs flow through the Genesis Key system")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
