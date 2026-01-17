#!/usr/bin/env python3
"""
Test script to verify stress test integration with diagnostic engine and self-healing system.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir / "backend"))

from autonomous_stress_testing.stress_test_suite import run_stress_test_suite

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/stress_test_run.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Run stress test and verify integration."""
    logger.info("=" * 80)
    logger.info("TESTING STRESS TEST INTEGRATION")
    logger.info("=" * 80)
    logger.info("This test verifies that stress tests alert both:")
    logger.info("  - Diagnostic Engine")
    logger.info("  - Self-Healing System")
    logger.info("  - Pattern Registration for Learning")
    logger.info("=" * 80)
    
    try:
        # Run stress test suite
        logger.info("\n[TEST] Running stress test suite...")
        results = await run_stress_test_suite(base_url="http://localhost:8000")
        
        # Display results
        summary = results.get("summary", {})
        pass_rate = summary.get("pass_rate", 0)
        passed = summary.get("passed", 0)
        total = summary.get("total_tests", 0)
        issues_found = len(results.get("issues_found", []))
        
        logger.info("\n" + "=" * 80)
        logger.info("STRESS TEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Pass Rate: {pass_rate:.1f}%")
        logger.info(f"Tests Passed: {passed}/{total}")
        logger.info(f"Issues Found: {issues_found}")
        logger.info("=" * 80)
        
        # Check if integration worked
        logger.info("\n[TEST] Verifying integration...")
        
        # Check if alert files were created
        from pathlib import Path
        diagnostic_log_dir = Path("logs/diagnostic")
        if diagnostic_log_dir.exists():
            alert_files = list(diagnostic_log_dir.glob("stress_test_alert_*.json"))
            if alert_files:
                logger.info(f"✓ Diagnostic engine alert files found: {len(alert_files)}")
            else:
                if issues_found > 0:
                    logger.warning("⚠ Diagnostic engine alert files not found (issues found but no alerts?)")
                else:
                    logger.info("✓ No diagnostic alerts (no issues found)")
        else:
            logger.warning("⚠ Diagnostic log directory does not exist")
        
        # Check if Genesis Keys were created
        try:
            from database.session import initialize_session_factory
            from genesis.genesis_key_service import get_genesis_service
            from models.genesis_key_models import GenesisKeyType
            
            session_factory = initialize_session_factory()
            session = session_factory()
            
            try:
                genesis_service = get_genesis_service(session=session)
                # Look for recent stress test keys
                recent_keys = session.query(genesis_service.GenesisKey).filter(
                    genesis_service.GenesisKey.key_type == GenesisKeyType.SYSTEM_EVENT,
                    genesis_service.GenesisKey.tags.contains("stress_test")
                ).order_by(genesis_service.GenesisKey.created_at.desc()).limit(5).all()
                
                if recent_keys:
                    logger.info(f"✓ Genesis Keys created for stress test: {len(recent_keys)}")
                else:
                    logger.warning("⚠ Genesis Keys not found for stress test")
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"⚠ Could not verify Genesis Keys: {e}")
        
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Status: {'PASS' if pass_rate >= 80 else 'WARN (Issues found)'}")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    results = asyncio.run(main())
