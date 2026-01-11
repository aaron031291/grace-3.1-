"""
Setup Script for Autonomous Version Control System.

Installs and configures:
1. Git post-commit hook (Git → Genesis Keys)
2. File system watcher (Real-time file tracking)
3. Layer 1 version control connector (Automatic tracking)

Run this script once to enable fully autonomous version control in GRACE.
"""
import os
import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_git_hook():
    """Install Git post-commit hook."""
    try:
        from genesis.git_genesis_bridge import get_git_genesis_bridge

        logger.info("Setting up Git post-commit hook...")
        bridge = get_git_genesis_bridge()
        success = bridge.create_post_commit_hook()

        if success:
            logger.info("✓ Git post-commit hook installed successfully")
            logger.info("  Now every Git commit will automatically create Genesis Keys")
            return True
        else:
            logger.error("✗ Failed to install Git post-commit hook")
            return False

    except Exception as e:
        logger.error(f"✗ Error setting up Git hook: {e}")
        return False


def test_symbiotic_version_control():
    """Test symbiotic version control system."""
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control

        logger.info("Testing symbiotic version control...")
        symbiotic = get_symbiotic_version_control()

        # Get statistics
        stats = symbiotic.get_symbiotic_stats()

        logger.info("✓ Symbiotic version control operational")
        logger.info(f"  Total files tracked: {stats['version_control'].get('total_files_tracked', 0)}")
        logger.info(f"  Total versions: {stats['version_control'].get('total_versions', 0)}")
        logger.info(f"  Genesis Key integration: {stats.get('integration_percentage', 0):.1f}%")

        return True

    except Exception as e:
        logger.error(f"✗ Error testing symbiotic version control: {e}")
        return False


def check_layer1_integration():
    """Check if version control connector is registered in Layer 1."""
    try:
        from layer1.components.version_control_connector import get_version_control_connector

        logger.info("Checking Layer 1 integration...")
        connector = get_version_control_connector()

        stats = connector.get_statistics()

        logger.info("✓ Version control connector available")
        logger.info(f"  Operations tracked: {stats.get('operations_tracked', 0)}")
        logger.info(f"  Status: {stats.get('status', 'unknown')}")

        return True

    except Exception as e:
        logger.error(f"✗ Error checking Layer 1 integration: {e}")
        return False


def install_watchdog_if_needed():
    """Install watchdog library if not available."""
    try:
        import watchdog
        logger.info("✓ watchdog library already installed")
        return True
    except ImportError:
        logger.info("Installing watchdog library for file system monitoring...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog"])
            logger.info("✓ watchdog library installed successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to install watchdog: {e}")
            logger.error("  Please run: pip install watchdog")
            return False


def show_usage_examples():
    """Show usage examples for the version control system."""
    print("\n" + "=" * 70)
    print("AUTONOMOUS VERSION CONTROL - USAGE EXAMPLES")
    print("=" * 70)

    print("\n1. AUTOMATIC FILE TRACKING (via File Ingestion):")
    print("   When you upload/ingest files, they're automatically version-tracked:")
    print("   ```python")
    print("   # File gets uploaded → Auto-creates Genesis Key + Version")
    print("   POST /api/ingest/file")
    print("   ```")

    print("\n2. GIT INTEGRATION (via Post-Commit Hook):")
    print("   Every Git commit now creates Genesis Keys:")
    print("   ```bash")
    print("   git add .")
    print("   git commit -m \"Fix bug\"")
    print("   # → Automatically creates Genesis Keys for changed files")
    print("   ```")

    print("\n3. FILE SYSTEM WATCHER (Real-Time Monitoring):")
    print("   Start watching workspace for file changes:")
    print("   ```python")
    print("   from genesis.file_watcher import start_watching_workspace")
    print("   start_watching_workspace()  # Auto-tracks all file changes")
    print("   ```")

    print("\n4. MANUAL TRACKING (Symbiotic API):")
    print("   Track file changes programmatically:")
    print("   ```python")
    print("   from genesis.symbiotic_version_control import get_symbiotic_version_control")
    print("   symbiotic = get_symbiotic_version_control()")
    print("   result = symbiotic.track_file_change(")
    print("       file_path='backend/app.py',")
    print("       user_id='GU-123...',")
    print("       change_description='Updated authentication'")
    print("   )")
    print("   ```")

    print("\n5. VIEW VERSION HISTORY:")
    print("   Get complete history for a file:")
    print("   ```python")
    print("   history = symbiotic.get_complete_history('FILE-abc123...')")
    print("   # Shows unified timeline of Genesis Keys + Versions")
    print("   ```")

    print("\n6. ROLLBACK TO VERSION:")
    print("   Restore a file to a previous version:")
    print("   ```python")
    print("   result = symbiotic.rollback_to_version(")
    print("       file_genesis_key='FILE-abc123...',")
    print("       version_number=3")
    print("   )")
    print("   ```")

    print("\n" + "=" * 70)
    print("All systems are now configured for AUTONOMOUS operation!")
    print("=" * 70 + "\n")


def main():
    """Main setup function."""
    print("\n" + "="*70)
    print(" GRACE AUTONOMOUS VERSION CONTROL SETUP")
    print("="*70 + "\n")

    results = []

    # Step 1: Install dependencies
    logger.info("Step 1: Checking dependencies...")
    results.append(("Install watchdog library", install_watchdog_if_needed()))

    # Step 2: Setup Git hook
    logger.info("\nStep 2: Setting up Git integration...")
    results.append(("Git post-commit hook", setup_git_hook()))

    # Step 3: Test symbiotic version control
    logger.info("\nStep 3: Testing symbiotic version control...")
    results.append(("Symbiotic version control", test_symbiotic_version_control()))

    # Step 4: Check Layer 1 integration
    logger.info("\nStep 4: Checking Layer 1 integration...")
    results.append(("Layer 1 connector", check_layer1_integration()))

    # Summary
    print("\n" + "=" * 70)
    print("SETUP SUMMARY")
    print("=" * 70)

    for name, success in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {name:.<50} {status}")

    all_success = all(success for _, success in results)

    if all_success:
        print("\n🎉 All systems configured successfully!")
        print("   Version control is now FULLY AUTONOMOUS.")
        show_usage_examples()
    else:
        print("\n⚠️  Some components failed to set up.")
        print("   Please check the errors above and resolve them.")
        print("   Version control may not be fully autonomous.")

    print("\n" + "=" * 70 + "\n")

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
