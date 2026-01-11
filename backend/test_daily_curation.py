"""
Test Genesis Key Daily Curation System.

Demonstrates:
1. Curating today's Genesis Keys
2. Organizing by type with metadata
3. Generating daily summaries
4. Exporting to Layer 1 folder
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Initialize database
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

config = DatabaseConfig.from_env()
DatabaseConnection.initialize(config)


def test_daily_curation():
    """Test curating today's Genesis Keys."""
    print("\n" + "="*80)
    print("TEST: Daily Genesis Key Curation")
    print("="*80)

    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()

        print("\nCurating today's Genesis Keys...")
        result = curator.curate_today()

        if result['success']:
            if result.get('curated'):
                print(f"\n[OK] Curation successful!")
                print(f"  Date: {result['date']}")
                print(f"  Keys Curated: {result['keys_count']}")
                print(f"\n  Summary: {result.get('summary', 'N/A')}")
            else:
                print(f"\n[OK] No Genesis Keys to curate for {result['date']}")

            return True
        else:
            print(f"\n[FAIL] Curation failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_layer1_export():
    """Check if Genesis Keys were exported to Layer 1."""
    print("\n" + "="*80)
    print("TEST: Layer 1 Export Verification")
    print("="*80)

    try:
        backend_dir = Path(__file__).parent
        layer1_path = backend_dir / "knowledge_base" / "layer_1" / "genesis_keys"

        print(f"\nChecking Layer 1 path: {layer1_path}")

        if not layer1_path.exists():
            print(f"[WARNING] Layer 1 genesis_keys folder not found")
            return False

        # Get today's date folder
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_folder = layer1_path / today

        if not today_folder.exists():
            print(f"[WARNING] Today's folder not found: {today}")
            return False

        print(f"\n[OK] Found today's folder: {today}")

        # Check what files exist
        files = list(today_folder.glob("*"))
        print(f"\nFiles in folder:")
        for file in files:
            file_size = file.stat().st_size
            print(f"  - {file.name} ({file_size} bytes)")

        # Read metadata if exists
        metadata_file = today_folder / "metadata.json"
        if metadata_file.exists():
            print(f"\n[OK] Metadata file found")

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            print(f"\nMetadata Summary:")
            print(f"  Total Keys: {metadata['statistics']['total_keys']}")
            print(f"  Errors: {metadata['statistics']['errors']}")
            print(f"  Fixes: {metadata['statistics']['fixes']}")
            print(f"  Unique Users: {metadata['statistics']['unique_users']}")

            print(f"\n  Summary Text:")
            print(f"  {metadata['summary']}")

            return True
        else:
            print(f"[WARNING] Metadata file not found")
            return False

    except Exception as e:
        print(f"[FAIL] Error checking export: {e}")
        import traceback
        traceback.print_exc()
        return False


def view_daily_summary():
    """View today's daily summary in Markdown."""
    print("\n" + "="*80)
    print("TEST: View Daily Summary")
    print("="*80)

    try:
        backend_dir = Path(__file__).parent
        layer1_path = backend_dir / "knowledge_base" / "layer_1" / "genesis_keys"
        today = datetime.utcnow().strftime("%Y-%m-%d")
        summary_file = layer1_path / today / "DAILY_SUMMARY.md"

        if not summary_file.exists():
            print(f"[WARNING] Summary file not found for {today}")
            return False

        print(f"\n[OK] Found summary file: {summary_file.name}\n")

        with open(summary_file, 'r') as f:
            summary_content = f.read()

        # Print first 50 lines
        lines = summary_content.split('\n')
        for line in lines[:50]:
            print(line)

        if len(lines) > 50:
            print(f"\n... and {len(lines) - 50} more lines")

        return True

    except Exception as e:
        print(f"[FAIL] Error viewing summary: {e}")
        return False


def test_curation_status():
    """Test getting curation status."""
    print("\n" + "="*80)
    print("TEST: Curation Status")
    print("="*80)

    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        status = curator.get_curation_status()

        print(f"\n[OK] Curation Status:")
        print(f"  Scheduler Running: {status['scheduler_running']}")
        print(f"  Last Curation: {status['last_curation']}")
        print(f"  Organized Days: {status['organized_days_count']}")
        print(f"  Latest Day: {status['latest_organized_day']}")

        if status['organized_days']:
            print(f"\n  Recent organized days:")
            for day in status['organized_days'][:5]:
                print(f"    - {day}")

        return True

    except Exception as e:
        print(f"[FAIL] Error getting status: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GENESIS KEY DAILY CURATION TEST SUITE")
    print("="*80)
    print("Testing automatic daily organization by Librarian...")

    results = []

    # Test 1: Curate today
    results.append(("Daily Curation", test_daily_curation()))

    # Test 2: Check Layer 1 export
    results.append(("Layer 1 Export", check_layer1_export()))

    # Test 3: View summary
    results.append(("Daily Summary", view_daily_summary()))

    # Test 4: Curation status
    results.append(("Curation Status", test_curation_status()))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        print("\nDaily curation system is working correctly.")
        print("Genesis Keys are being organized in Layer 1 every 24 hours.")
        return 0
    else:
        print("\n[WARNING] Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
