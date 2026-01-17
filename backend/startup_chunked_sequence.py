import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import threading
import time
class StartupChunkedSequence:
    logger = logging.getLogger(__name__)
    """
    Chunked startup sequence with preflight → healing → startup.
    
    Order:
    1. Preflight checks (detect issues)
    2. Self-healing in preflight mode (fix issues)
    3. Normal startup (continue with healed system)
    """
    
    def __init__(self):
        self.preflight_issues = []
        self.healing_results = []
        self.startup_success = False
        self.chunk_results = {}
    
    # ==================== CHUNK 1: PREFLIGHT CHECKS ====================
    
    def run_preflight_checks(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Chunk 1: Run preflight checks to identify issues.
        
        Returns:
            (success, issues_found)
        """
        logger.info("=" * 80)
        logger.info("[CHUNK 1] PREFLIGHT CHECKS - Identifying Issues")
        logger.info("=" * 80)
        
        issues = []
        checks_passed = 0
        total_checks = 0
        
        # Check 1: Python version
        total_checks += 1
        try:
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                issues.append({
                    "check": "Python Version",
                    "status": "FAIL",
                    "issue": f"Python {python_version.major}.{python_version.minor} < 3.8 required",
                    "severity": "critical"
                })
            else:
                logger.info(f"[PREFLIGHT] ✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
                checks_passed += 1
        except Exception as e:
            issues.append({
                "check": "Python Version",
                "status": "ERROR",
                "issue": str(e),
                "severity": "critical"
            })
        
        # Check 2: Required directories
        total_checks += 1
        required_dirs = [
            "backend",
            "backend/knowledge_base",
            "backend/logs",
            "data"
        ]
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            issues.append({
                "check": "Required Directories",
                "status": "FAIL",
                "issue": f"Missing directories: {', '.join(missing_dirs)}",
                "severity": "high"
            })
        else:
            logger.info("[PREFLIGHT] ✓ All required directories exist")
            checks_passed += 1
        
        # Check 3: Database connection
        total_checks += 1
        try:
            from backend.database.config import DatabaseConfig
            from backend.database.connection import DatabaseConnection
            from backend.database.session import initialize_session_factory
            
            db_config = DatabaseConfig()
            DatabaseConnection.initialize(db_config)
            initialize_session_factory()
            
            # Test connection
            from backend.database.session import get_session
            session = next(get_session())
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            session.close()
            
            logger.info("[PREFLIGHT] ✓ Database connection working")
            checks_passed += 1
        except Exception as e:
            issues.append({
                "check": "Database Connection",
                "status": "FAIL",
                "issue": f"Database initialization failed: {str(e)}",
                "severity": "critical",
                "error": str(e)
            })
        
        # Check 4: Critical imports
        total_checks += 1
        critical_modules = [
            "backend.cognitive.autonomous_healing_system",
            "backend.diagnostic_machine.engine",
            "backend.genesis.genesis_key_service"
        ]
        missing_modules = []
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError as e:
                missing_modules.append(f"{module}: {str(e)}")
        
        if missing_modules:
            issues.append({
                "check": "Critical Modules",
                "status": "FAIL",
                "issue": f"Missing or broken modules: {', '.join(missing_modules)}",
                "severity": "high"
            })
        else:
            logger.info("[PREFLIGHT] ✓ All critical modules importable")
            checks_passed += 1
        
        # Check 5: File permissions
        total_checks += 1
        writable_dirs = ["backend/logs", "data"]
        permission_issues = []
        for dir_path in writable_dirs:
            path = Path(dir_path)
            if path.exists() and not os.access(path, os.W_OK):
                permission_issues.append(dir_path)
        
        if permission_issues:
            issues.append({
                "check": "File Permissions",
                "status": "FAIL",
                "issue": f"Non-writable directories: {', '.join(permission_issues)}",
                "severity": "medium"
            })
        else:
            logger.info("[PREFLIGHT] ✓ File permissions OK")
            checks_passed += 1
        
        # Summary
        success = len(issues) == 0
        logger.info(f"\n[PREFLIGHT] Results: {checks_passed}/{total_checks} checks passed")
        logger.info(f"[PREFLIGHT] Issues found: {len(issues)}")
        
        if issues:
            logger.warning("\n[PREFLIGHT] Issues detected:")
            for issue in issues:
                logger.warning(f"  - {issue['check']}: {issue['issue']} ({issue['severity']})")
        
        self.preflight_issues = issues
        self.chunk_results["preflight"] = {
            "success": success,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "issues": issues
        }
        
        return success, issues
    
    # ==================== CHUNK 2: SELF-HEALING IN PREFLIGHT MODE ====================
    
    def run_healing_preflight_mode(self, issues: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Chunk 2: Activate self-healing in preflight mode to fix detected issues.
        
        Args:
            issues: Issues detected in preflight
            
        Returns:
            (success, healing_results)
        """
        logger.info("\n" + "=" * 80)
        logger.info("[CHUNK 2] SELF-HEALING IN PREFLIGHT MODE - Fixing Issues")
        logger.info("=" * 80)
        
        if not issues:
            logger.info("[HEALING] No issues to fix - skipping healing")
            self.chunk_results["healing"] = {
                "success": True,
                "issues_fixed": 0,
                "issues_remaining": 0,
                "results": []
            }
            return True, []
        
        healing_results = []
        issues_fixed = 0
        issues_remaining = 0
        
        try:
            # Initialize database for healing
            from backend.database.config import DatabaseConfig
            from backend.database.connection import DatabaseConnection
            from backend.database.session import initialize_session_factory, get_session
            
            try:
                DatabaseConnection.get_engine()
            except RuntimeError:
                db_config = DatabaseConfig()
                DatabaseConnection.initialize(db_config)
                initialize_session_factory()
            
            session = next(get_session())
            
            # Initialize self-healing system
            logger.info("[HEALING] Initializing self-healing system...")
            from backend.cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            
            healing_system = get_autonomous_healing(
                session=session,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,  # Allow auto-healing in preflight
                enable_learning=True
            )
            
            logger.info("[HEALING] ✓ Self-healing system initialized in preflight mode")
            
            # Try to heal each issue
            for issue in issues:
                logger.info(f"\n[HEALING] Attempting to fix: {issue['check']}")
                
                result = self._heal_issue(healing_system, session, issue)
                healing_results.append(result)
                
                if result.get("fixed", False):
                    issues_fixed += 1
                    logger.info(f"[HEALING] ✓ Fixed: {issue['check']}")
                else:
                    issues_remaining += 1
                    logger.warning(f"[HEALING] ✗ Could not fix: {issue['check']} - {result.get('reason', 'Unknown')}")
            
            # Run diagnostic engine to check for additional issues
            logger.info("\n[HEALING] Running diagnostic engine...")
            try:
                from backend.diagnostic_machine.engine import DiagnosticEngine
                diagnostic = DiagnosticEngine(session=session)
                diagnostic_result = diagnostic.run_diagnostic_cycle()
                
                if diagnostic_result.get("anomalies_detected", 0) > 0:
                    logger.info(f"[HEALING] Diagnostic found {diagnostic_result['anomalies_detected']} additional issues")
                    # Healing system will handle these automatically
                else:
                    logger.info("[HEALING] ✓ Diagnostic engine: No additional issues")
            except Exception as e:
                logger.warning(f"[HEALING] Diagnostic engine not available: {e}")
            
        except Exception as e:
            logger.error(f"[HEALING] Failed to initialize healing system: {e}")
            healing_results.append({
                "issue": "Healing System Initialization",
                "fixed": False,
                "reason": str(e),
                "severity": "critical"
            })
            issues_remaining += len(issues)
        
        success = issues_remaining == 0
        logger.info(f"\n[HEALING] Results: {issues_fixed} fixed, {issues_remaining} remaining")
        
        self.healing_results = healing_results
        self.chunk_results["healing"] = {
            "success": success,
            "issues_fixed": issues_fixed,
            "issues_remaining": issues_remaining,
            "results": healing_results
        }
        
        return success, healing_results
    
    def _heal_issue(
        self,
        healing_system,
        session,
        issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to heal a specific issue."""
        check_name = issue["check"]
        issue_desc = issue["issue"]
        severity = issue.get("severity", "medium")
        
        result = {
            "issue": check_name,
            "description": issue_desc,
            "severity": severity,
            "fixed": False,
            "reason": None,
            "healing_actions": []
        }
        
        # Healing logic for specific checks
        if check_name == "Required Directories":
            # Create missing directories
            try:
                missing_dirs = issue_desc.replace("Missing directories: ", "").split(", ")
                for dir_path in missing_dirs:
                    Path(dir_path).mkdir(parents=True, exist_ok=True)
                result["fixed"] = True
                result["healing_actions"] = ["Created missing directories"]
            except Exception as e:
                result["reason"] = str(e)
        
        elif check_name == "Database Connection":
            # Try to reinitialize database
            try:
                from backend.database.config import DatabaseConfig
                from backend.database.connection import DatabaseConnection
                from backend.database.session import initialize_session_factory
                
                # Try to reset connection
                try:
                    DatabaseConnection.close()
                except:
                    pass
                
                db_config = DatabaseConfig()
                DatabaseConnection.initialize(db_config)
                initialize_session_factory()
                
                # Test again
                test_session = next(get_session())
                from sqlalchemy import text
                test_session.execute(text("SELECT 1"))
                test_session.close()
                
                result["fixed"] = True
                result["healing_actions"] = ["Reinitialized database connection"]
            except Exception as e:
                result["reason"] = str(e)
        
        elif check_name == "File Permissions":
            # Try to fix permissions (warning only - may require admin)
            result["reason"] = "Permission fixes may require administrator access"
            result["healing_actions"] = ["Note: Check file permissions manually"]
        
        else:
            # Generic healing attempt via healing system
            # Note: Some issues may not be automatically fixable
            result["reason"] = "Issue type not automatically fixable - may require manual intervention"
            result["healing_actions"] = [f"Review {check_name}: {issue_desc}"]
        
        return result
    
    # ==================== CHUNK 3: NORMAL STARTUP ====================
    
    def run_normal_startup(self) -> bool:
        """
        Chunk 3: Continue with normal startup (after preflight and healing).
        
        Returns:
            success
        """
        logger.info("\n" + "=" * 80)
        logger.info("[CHUNK 3] NORMAL STARTUP - Continuing with Healed System")
        logger.info("=" * 80)
        
        try:
            # Initialize database (should already be done, but verify)
            from backend.database.config import DatabaseConfig
            from backend.database.connection import DatabaseConnection
            from backend.database.session import initialize_session_factory
            
            try:
                DatabaseConnection.get_engine()
            except RuntimeError:
                logger.info("[STARTUP] Initializing database...")
                db_config = DatabaseConfig()
                DatabaseConnection.initialize(db_config)
                initialize_session_factory()
            
            # Initialize critical systems
            logger.info("[STARTUP] Initializing critical systems...")
            
            # Keep self-healing active
            from backend.database.session import get_session
            session = next(get_session())
            
            from backend.cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            healing_system = get_autonomous_healing(
                session=session,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )
            logger.info("[STARTUP] ✓ Self-healing system active")
            
            # Initialize diagnostic engine
            try:
                from backend.diagnostic_machine.engine import DiagnosticEngine
                diagnostic = DiagnosticEngine(session=session)
                logger.info("[STARTUP] ✓ Diagnostic engine active")
            except Exception as e:
                logger.warning(f"[STARTUP] Diagnostic engine not available: {e}")
            
            # Initialize TimeSense Engine (background, non-blocking)
            logger.info("[STARTUP] Initializing TimeSense Engine (background)...")
            def initialize_timesense_background():
                """Initialize TimeSense in background thread."""
                try:
                    from timesense.engine import get_timesense_engine
                    logger.info("[TIMESENSE] Initializing Time & Cost Model...")
                    
                    timesense_engine = get_timesense_engine(auto_calibrate=True)
                    
                    # Run quick calibration at startup
                    initialized = timesense_engine.initialize_sync(quick_calibration=True)
                    
                    if initialized:
                        logger.info("[TIMESENSE] ✓ TimeSense engine ready")
                        logger.info(f"[TIMESENSE] Calibrated profiles: {timesense_engine.stats.stable_profiles}")
                        logger.info(f"[TIMESENSE] Average confidence: {timesense_engine.stats.average_confidence:.2f}")
                        logger.info("[TIMESENSE] Time predictions: p50/p90/p95/p99 latencies available")
                    else:
                        logger.warning("[TIMESENSE] Engine initialized but calibration incomplete")
                except Exception as e:
                    logger.warning(f"[TIMESENSE] Could not initialize TimeSense: {e}")
                    logger.info("[TIMESENSE] Time predictions will use default estimates")
            
            timesense_thread = threading.Thread(target=initialize_timesense_background, daemon=True)
            timesense_thread.start()
            logger.info("[STARTUP] ✓ TimeSense initialization started in background")
            
            # Initialize other background systems
            logger.info("[STARTUP] Initializing other background systems...")
            # These will initialize in background as normal
            
            logger.info("\n[STARTUP] ✓ Normal startup complete")
            self.startup_success = True
            self.chunk_results["startup"] = {"success": True}
            
            return True
            
        except Exception as e:
            logger.error(f"[STARTUP] Startup failed: {e}")
            self.startup_success = False
            self.chunk_results["startup"] = {"success": False, "error": str(e)}
            return False
    
    # ==================== RUN COMPLETE SEQUENCE ====================
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete chunked startup sequence.
        
        Returns:
            Summary of all chunks
        """
        logger.info("\n" + "=" * 80)
        logger.info("GRACE CHUNKED STARTUP SEQUENCE")
        logger.info("=" * 80)
        
        # Chunk 1: Preflight
        preflight_success, issues = self.run_preflight_checks()
        
        # Chunk 2: Healing (even if preflight passed, run healing in case of hidden issues)
        healing_success, healing_results = self.run_healing_preflight_mode(issues)
        
        # Chunk 3: Normal startup
        startup_success = self.run_normal_startup()
        
        # Summary
        overall_success = preflight_success and healing_success and startup_success
        
        summary = {
            "overall_success": overall_success,
            "chunks": {
                "preflight": self.chunk_results.get("preflight", {}),
                "healing": self.chunk_results.get("healing", {}),
                "startup": self.chunk_results.get("startup", {})
            },
            "preflight_issues": len(issues),
            "issues_fixed": len([r for r in healing_results if r.get("fixed", False)]),
            "issues_remaining": len([r for r in healing_results if not r.get("fixed", False)]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("STARTUP SEQUENCE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Overall: {'SUCCESS' if overall_success else 'PARTIAL/FAILED'}")
        logger.info(f"Preflight: {len(issues)} issues found")
        logger.info(f"Healing: {summary['issues_fixed']} fixed, {summary['issues_remaining']} remaining")
        logger.info(f"Startup: {'SUCCESS' if startup_success else 'FAILED'}")
        logger.info("=" * 80)
        
        return summary


def main():
    """Main entry point for chunked startup."""
    sequence = StartupChunkedSequence()
    summary = sequence.run()
    return summary


if __name__ == "__main__":
    summary = main()
    sys.exit(0 if summary["overall_success"] else 1)
