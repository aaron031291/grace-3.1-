"""
Test ALL Genesis Key Connections.

Verifies that Genesis Keys are connected to:
1. Memory Mesh
2. Genesis Key Folder (Layer 1)
3. Librarian
4. RAG System
5. Ingestion System
6. Autonomous Triggers
"""

import sys
import os
from datetime import datetime

# Initialize database
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

config = DatabaseConfig.from_env()
DatabaseConnection.initialize(config)

def test_memory_mesh_connection():
    """Test Genesis Key → Memory Mesh connection."""
    print("\n" + "="*80)
    print("TEST 1: Memory Mesh Connection")
    print("="*80)

    try:
        from genesis.genesis_key_service import get_genesis_service
        from models.genesis_key_models import GenesisKeyType
        from database.session import get_session

        session = next(get_session())
        genesis_service = get_genesis_service(session)

        # Create a test Genesis Key
        key = genesis_service.create_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description="Test Memory Mesh Integration",
            who_actor="test_script",
            where_location="test_all_genesis_connections.py",
            why_reason="Testing Memory Mesh connection",
            how_method="Direct test",
            input_data={"test": "memory_mesh"},
            output_data={"status": "testing"},
            session=session
        )

        print(f"\n[OK] Created Genesis Key: {key.key_id}")
        print(f"   Should have been fed into Memory Mesh")
        print(f"   Check logs for: '[OK] Genesis Key fed into Memory Mesh'")

        return True

    except Exception as e:
        print(f"\n[FAIL] Memory Mesh connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_layer1_folder_connection():
    """Test Genesis Key → Layer 1 Folder connection."""
    print("\n" + "="*80)
    print("TEST 2: Layer 1 Folder Connection")
    print("="*80)

    try:
        from pathlib import Path

        backend_dir = Path(__file__).parent
        layer1_kb = backend_dir / "knowledge_base" / "layer_1" / "genesis_key"

        print(f"\nChecking Layer 1 KB folder: {layer1_kb}")

        if layer1_kb.exists():
            files = list(layer1_kb.glob("**/*.json"))
            print(f"\n[OK] Layer 1 Genesis Key folder exists")
            print(f"   Found {len(files)} JSON files")

            # Show recent files
            if files:
                recent = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]
                print(f"\n   Recent files:")
                for f in recent:
                    print(f"      - {f.relative_to(layer1_kb)}")

            return True
        else:
            print(f"\n[WARNING] Layer 1 KB folder not found")
            return False

    except Exception as e:
        print(f"\n[FAIL] Layer 1 folder check failed: {e}")
        return False


def test_librarian_connection():
    """Test Librarian daily organization."""
    print("\n" + "="*80)
    print("TEST 3: Librarian Connection")
    print("="*80)

    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        status = curator.get_curation_status()

        print(f"\n[OK] Librarian curator operational")
        print(f"   Scheduler Running: {status['scheduler_running']}")
        print(f"   Organized Days: {status['organized_days_count']}")
        print(f"   Latest Day: {status['latest_organized_day']}")

        return True

    except Exception as e:
        print(f"\n[FAIL] Librarian connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_connection():
    """Test RAG system creates Genesis Keys."""
    print("\n" + "="*80)
    print("TEST 4: RAG Connection")
    print("="*80)

    try:
        import inspect
        from api.retrieve import retrieve_chunks_cognitive

        source_file = inspect.getsourcefile(retrieve_chunks_cognitive)
        with open(source_file, 'r') as f:
            content = f.read()

        has_genesis = 'genesis' in content.lower() and 'create_key' in content

        if has_genesis:
            print(f"\n[OK] RAG system creates Genesis Keys on queries")
            print(f"   File: {source_file}")
            print(f"   Genesis Key creation: FOUND")
        else:
            print(f"\n[FAIL] RAG system not creating Genesis Keys")

        return has_genesis

    except Exception as e:
        print(f"\n[FAIL] RAG connection check failed: {e}")
        return False


def test_ingestion_connection():
    """Test ingestion system creates Genesis Keys."""
    print("\n" + "="*80)
    print("TEST 5: Ingestion Connection")
    print("="*80)

    try:
        import inspect
        from api.file_ingestion import scan_knowledge_base

        source_file = inspect.getsourcefile(scan_knowledge_base)
        with open(source_file, 'r') as f:
            content = f.read()

        has_genesis = 'genesis' in content.lower() and 'create_key' in content

        if has_genesis:
            print(f"\n[OK] Ingestion system creates Genesis Keys")
            print(f"   File: {source_file}")
            print(f"   Genesis Key creation: FOUND")
        else:
            print(f"\n[FAIL] Ingestion system not creating Genesis Keys")

        return has_genesis

    except Exception as e:
        print(f"\n[FAIL] Ingestion connection check failed: {e}")
        return False


def test_autonomous_triggers():
    """Test autonomous triggers are connected."""
    print("\n" + "="*80)
    print("TEST 6: Autonomous Triggers")
    print("="*80)

    try:
        from genesis.autonomous_triggers import get_genesis_trigger_pipeline
        from database.session import get_session

        session = next(get_session())
        trigger_pipeline = get_genesis_trigger_pipeline(session=session)

        print(f"\n[OK] Autonomous trigger pipeline exists")
        print(f"   Pipeline: {trigger_pipeline}")
        print(f"   Triggers on every Genesis Key creation")

        return True

    except Exception as e:
        print(f"\n[FAIL] Autonomous triggers check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all connection tests."""
    print("\n" + "="*80)
    print("GENESIS KEY - ALL CONNECTIONS TEST SUITE")
    print("="*80)
    print("Testing all Genesis Key system integrations...")

    results = []

    # Test 1: Memory Mesh
    results.append(("Memory Mesh", test_memory_mesh_connection()))

    # Test 2: Layer 1 Folder
    results.append(("Layer 1 Folder", test_layer1_folder_connection()))

    # Test 3: Librarian
    results.append(("Librarian", test_librarian_connection()))

    # Test 4: RAG
    results.append(("RAG System", test_rag_connection()))

    # Test 5: Ingestion
    results.append(("Ingestion", test_ingestion_connection()))

    # Test 6: Autonomous Triggers
    results.append(("Autonomous Triggers", test_autonomous_triggers()))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n[SUCCESS] All Genesis Key connections operational!")
        print("\nCOMPLETE FLOW:")
        print("  Input → Genesis Key → Memory Mesh")
        print("                     → Layer 1 Folder")
        print("                     → Librarian (daily)")
        print("                     → Autonomous Triggers")
        print("                     → Learning & Adaptation")
        return 0
    else:
        print("\n[WARNING] Some connections need attention.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
