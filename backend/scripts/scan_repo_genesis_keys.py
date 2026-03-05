"""
Scan entire GRACE repository and assign Genesis Keys to every directory and file.

This creates:
- Genesis Key for every directory (DIR-prefix)
- Genesis Key for every subdirectory (recursive)
- Genesis Key for every file (FILE-prefix)
- Immutable memory snapshot
- Complete hierarchy tracking
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scan_entire_repo():
    """Scan entire repository and assign Genesis Keys."""
    print("\n" + "="*80)
    print("REPOSITORY GENESIS KEY SCANNER")
    print("="*80)
    print("Scanning entire GRACE repository...")
    print("This will assign Genesis Keys to EVERY directory and file.\n")

    try:
        # Get repo root (grace_3 directory)
        backend_dir = Path(__file__).parent
        repo_root = backend_dir.parent

        print(f"Repository Root: {repo_root}")
        print(f"Backend Dir: {backend_dir}\n")

        # Import after path setup
        from genesis.repo_scanner import get_repo_scanner, scan_and_save_repo

        # Scan repository
        print("Starting repository scan...")
        print("This may take a moment for large repositories...\n")

        result = scan_and_save_repo(repo_path=str(repo_root))

        # Display results
        print("\n" + "="*80)
        print("SCAN COMPLETE")
        print("="*80)
        print(f"\nScan Timestamp: {result['scan_timestamp']}")
        print(f"Repository Path: {result['repo_path']}")
        print(f"Root Genesis Key: {result['root_genesis_key']}")

        stats = result['statistics']
        print(f"\nStatistics:")
        print(f"  - Total Directories: {stats['total_directories']}")
        print(f"  - Total Files: {stats['total_files']}")
        print(f"  - Total Size: {stats['total_size_bytes']:,} bytes ({stats['total_size_bytes'] / (1024**2):.2f} MB)")

        print(f"\nImmutable Memory Saved To:")
        print(f"  {result.get('immutable_memory_path', 'N/A')}")

        # Show sample of directories
        print(f"\nSample Directories with Genesis Keys:")
        dirs = result.get('directories', {})
        for i, (path, info) in enumerate(list(dirs.items())[:10]):
            print(f"  [{info['genesis_key']}] {path}")
            if i >= 9:
                print(f"  ... and {len(dirs) - 10} more directories")
                break

        # Show sample of files
        print(f"\nSample Files with Genesis Keys:")
        files = result.get('files', {})
        for i, (path, info) in enumerate(list(files.items())[:10]):
            print(f"  [{info['genesis_key']}] {path}")
            if i >= 9:
                print(f"  ... and {len(files) - 10} more files")
                break

        print("\n" + "="*80)
        print("SUCCESS - Repository Genesis Keys Assigned")
        print("="*80)
        print("\nEvery directory and file now has a unique Genesis Key.")
        print("All future changes will be tracked through the Genesis Key pipeline.")

        return result

    except Exception as e:
        print(f"\nERROR: Failed to scan repository: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_scan():
    """Verify that the scan worked."""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)

    try:
        backend_dir = Path(__file__).parent
        immutable_memory_dir = backend_dir / "knowledge_base" / "layer_1" / "immutable_memory"

        if immutable_memory_dir.exists():
            print(f"\n[OK] Immutable memory directory exists")
            files = list(immutable_memory_dir.glob("*.json"))
            print(f"[OK] Found {len(files)} immutable memory file(s)")

            for file in files:
                print(f"  - {file.name}")

            return True
        else:
            print(f"\n[FAIL] Immutable memory directory not found")
            return False

    except Exception as e:
        print(f"\n[FAIL] Verification failed: {e}")
        return False


def main():
    """Main function."""
    # Scan repository
    result = scan_entire_repo()

    if result:
        # Verify
        verified = verify_scan()

        if verified:
            print("\n\n[SUCCESS] Repository scan complete and verified!")
            print("\nNext steps:")
            print("  1. Every file change will now create a Genesis Key")
            print("  2. All Genesis Keys flow through the autonomous pipeline")
            print("  3. The system learns from every interaction")
            return 0
        else:
            print("\n\n[WARNING] Scan completed but verification failed")
            return 1
    else:
        print("\n\n[FAIL] Repository scan failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
