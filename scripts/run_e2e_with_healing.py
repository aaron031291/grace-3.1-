"""
End-to-End Test with Self-Healing Integration

Runs comprehensive e2e tests, captures bugs, feeds them to self-healing system,
and logs what was healed.
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_test_healing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import required modules
try:
    from database.session import initialize_session_factory, get_session
    from database.connection import DatabaseConnection
    from database.config import DatabaseConfig
    from cognitive.error_learning_integration import get_error_learning_integration
    from cognitive.autonomous_healing_system import get_autonomous_healing
    from diagnostic_machine.healing import get_healing_executor
    from diagnostic_machine.diagnostic_engine import DiagnosticEngine
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.info("Some features may not be available")


class E2ETestRunner:
    """Runs e2e tests and integrates with self-healing."""
    
    def __init__(self):
        """Initialize test runner."""
        self.session = None
        self.error_learning = None
        self.healing_system = None
        self.diagnostic_engine = None
        self.test_results = []
        self.bugs_found = []
        self.healing_results = []
        
    def setup(self):
        """Setup test environment and services."""
        logger.info("="*70)
        logger.info("E2E TEST RUNNER - SETUP")
        logger.info("="*70)
        
        try:
            # Initialize database connection
            try:
                config = DatabaseConfig()
                DatabaseConnection.initialize(config)
                logger.info("[OK] Database connection initialized")
            except Exception as e:
                logger.warning(f"Database initialization warning: {e}")
            
            # Initialize session factory
            try:
                session_factory = initialize_session_factory()
                self.session = session_factory()
                logger.info("[OK] Database session initialized")
            except Exception as e:
                logger.warning(f"Session initialization warning: {e}")
                # Try alternative method
                try:
                    self.session = next(get_session())
                    logger.info("[OK] Database session initialized (alternative method)")
                except Exception as e2:
                    logger.error(f"Failed to initialize session: {e2}")
                    self.session = None
            
            # Initialize error learning integration
            try:
                self.error_learning = get_error_learning_integration(session=self.session)
                logger.info("[OK] Error learning integration initialized")
            except Exception as e:
                logger.warning(f"Error learning integration not available: {e}")
            
            # Initialize healing system
            try:
                self.healing_system = get_healing_executor()
                logger.info("[OK] Self-healing system initialized")
            except Exception as e:
                logger.warning(f"Healing system not available: {e}")
                try:
                    # Try autonomous healing as fallback
                    self.healing_system = get_autonomous_healing(session=self.session)
                    logger.info("[OK] Autonomous healing system initialized (fallback)")
                except Exception as e2:
                    logger.warning(f"Autonomous healing also not available: {e2}")
            
            # Initialize diagnostic engine
            try:
                # DiagnosticEngine doesn't take session parameter
                self.diagnostic_engine = DiagnosticEngine(
                    heartbeat_interval=60,
                    enable_heartbeat=False,
                    dry_run=True
                )
                logger.info("[OK] Diagnostic engine initialized")
            except Exception as e:
                logger.warning(f"Diagnostic engine not available: {e}")
                
        except Exception as e:
            logger.error(f"Setup failed: {e}", exc_info=True)
            raise
    
    def teardown(self):
        """Cleanup test environment."""
        if self.session:
            self.session.close()
            logger.info("✓ Database session closed")
    
    def run_test(self, test_name: str, test_func) -> Dict[str, Any]:
        """
        Run a single test and capture any errors.
        
        Args:
            test_name: Name of the test
            test_func: Test function to run
            
        Returns:
            Test result dictionary
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"RUNNING TEST: {test_name}")
        logger.info(f"{'='*70}")
        
        result = {
            "test_name": test_name,
            "passed": False,
            "error": None,
            "error_type": None,
            "error_message": None,
            "traceback": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Run the test
            test_result = test_func()
            
            if test_result:
                result["passed"] = True
                logger.info(f"[PASS] TEST PASSED: {test_name}")
            else:
                result["passed"] = False
                result["error"] = "Test returned False"
                logger.warning(f"[FAIL] TEST FAILED: {test_name} - Test returned False")
                
        except Exception as e:
            result["passed"] = False
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["error_message"] = str(e)
            result["traceback"] = traceback.format_exc()
            
            logger.error(f"[FAIL] TEST FAILED: {test_name}")
            logger.error(f"  Error Type: {result['error_type']}")
            logger.error(f"  Error Message: {result['error_message']}")
            
            # Record bug for learning
            self.record_bug(result)
            
        self.test_results.append(result)
        return result
    
    def record_bug(self, test_result: Dict[str, Any]):
        """
        Record a bug and feed it to self-healing pipeline.
        
        Args:
            test_result: Test result containing error information
        """
        if not test_result.get("error"):
            return
        
        logger.info(f"\n{'='*70}")
        logger.info(f"RECORDING BUG: {test_result['test_name']}")
        logger.info(f"{'='*70}")
        
        bug_info = {
            "test_name": test_result["test_name"],
            "error_type": test_result.get("error_type", "UnknownError"),
            "error_message": test_result.get("error_message", "Unknown error"),
            "traceback": test_result.get("traceback", ""),
            "timestamp": test_result.get("timestamp", datetime.utcnow().isoformat())
        }
        
        self.bugs_found.append(bug_info)
        
        # Feed to error learning integration
        if self.error_learning:
            try:
                # Create exception object for recording
                error_type_name = test_result.get("error_type", "Exception")
                error_message = test_result.get("error_message", "Test failed")
                
                # Create a proper exception instance
                try:
                    # Try to get the actual exception class
                    import builtins
                    exception_class = getattr(builtins, error_type_name, Exception)
                    error_exception = exception_class(error_message)
                except Exception:
                    # Fallback to generic Exception
                    error_exception = Exception(f"{error_type_name}: {error_message}")
                
                genesis_key_id = self.error_learning.record_error(
                    error=error_exception,
                    context={
                        "location": f"e2e_test.{test_result['test_name']}",
                        "reason": f"E2E test failed: {test_result['test_name']}",
                        "method": "run_test",
                        "test_name": test_result["test_name"]
                    },
                    component=f"e2e_test.{test_result['test_name']}",
                    severity="high"  # E2E test failures are high priority
                )
                
                bug_info["genesis_key_id"] = genesis_key_id
                logger.info(f"[OK] Bug recorded with Genesis Key: {genesis_key_id}")
                
            except Exception as e:
                logger.warning(f"Failed to record bug in error learning: {e}")
        
        # Trigger self-healing
        self.trigger_healing(bug_info)
    
    def trigger_healing(self, bug_info: Dict[str, Any]):
        """
        Trigger self-healing for a bug.
        
        Args:
            bug_info: Bug information dictionary
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"TRIGGERING SELF-HEALING FOR: {bug_info['test_name']}")
        logger.info(f"{'='*70}")
        
        healing_result = {
            "bug": bug_info,
            "healing_triggered": False,
            "healing_actions": [],
            "healing_status": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.healing_system:
            try:
                # Check if it's a HealingExecutor or AutonomousHealingSystem
                if hasattr(self.healing_system, 'run_monitoring_cycle'):
                    # Autonomous healing system
                    cycle_result = self.healing_system.run_monitoring_cycle()
                    healing_result["healing_triggered"] = True
                    healing_result["healing_actions"] = cycle_result.get("actions_executed", [])
                    healing_result["healing_status"] = cycle_result.get("health_status", {})
                elif hasattr(self.healing_system, 'execute'):
                    # Healing executor - try code fix
                    from diagnostic_machine.healing import HealingActionType
                    fix_result = self.healing_system.execute(
                        HealingActionType.CODE_FIX,
                        {"fix_warnings": True}
                    )
                    healing_result["healing_triggered"] = True
                    healing_result["healing_actions"] = [{
                        "action_type": "code_fix",
                        "success": fix_result.success,
                        "message": fix_result.message
                    }]
                    healing_result["healing_status"] = {"code_fixed": fix_result.success}
                
                logger.info(f"[OK] Healing cycle completed")
                logger.info(f"  Actions executed: {len(healing_result['healing_actions'])}")
                
                # Log what was healed
                if healing_result["healing_actions"]:
                    logger.info(f"\n  HEALING ACTIONS TAKEN:")
                    for i, action in enumerate(healing_result["healing_actions"], 1):
                        action_type = action.get('action_type', 'unknown')
                        message = action.get('message', 'N/A')
                        success = action.get('success', False)
                        logger.info(f"    {i}. {action_type}: {message}")
                        logger.info(f"       Status: {'SUCCESS' if success else 'FAILED'}")
                else:
                    logger.info(f"  No healing actions were taken")
                
            except Exception as e:
                logger.warning(f"Healing cycle failed: {e}")
                healing_result["error"] = str(e)
        
        if self.diagnostic_engine:
            try:
                # Run diagnostic cycle (correct method name)
                diagnostic_cycle = self.diagnostic_engine.run_cycle()
                healing_result["diagnostic_result"] = {
                    "cycle_id": diagnostic_cycle.cycle_id,
                    "health_status": diagnostic_cycle.judgement.health.status.value if diagnostic_cycle.judgement else "unknown",
                    "action_type": diagnostic_cycle.action_decision.action_type.value if diagnostic_cycle.action_decision else "none"
                }
                logger.info(f"✓ Diagnostic analysis completed")
            except Exception as e:
                logger.warning(f"Diagnostic analysis failed: {e}")
        
        self.healing_results.append(healing_result)
    
    def run_e2e_tests(self):
        """Run comprehensive e2e tests."""
        logger.info("\n" + "="*70)
        logger.info("RUNNING E2E TEST SUITE")
        logger.info("="*70)
        
        # Test 1: System initialization
        def test_system_init():
            """Test system initialization."""
            try:
                from app import app
                assert app is not None, "App not initialized"
                return True
            except Exception as e:
                logger.error(f"System init test failed: {e}")
                raise
        
        # Test 2: Database connectivity
        def test_database():
            """Test database connectivity."""
            try:
                assert self.session is not None, "Session not initialized"
                # Try a simple query
                from sqlalchemy import text
                self.session.execute(text("SELECT 1"))
                return True
            except Exception as e:
                logger.error(f"Database test failed: {e}")
                raise
        
        # Test 3: LLM Orchestrator availability
        def test_llm_orchestrator():
            """Test LLM Orchestrator."""
            try:
                from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                orchestrator = get_llm_orchestrator(session=self.session)
                assert orchestrator is not None, "Orchestrator not initialized"
                # Check if get_availability_status exists and is callable
                if hasattr(orchestrator, 'get_availability_status') and callable(getattr(orchestrator, 'get_availability_status', None)):
                    try:
                        status = orchestrator.get_availability_status()
                        logger.info(f"  LLM Orchestrator status: {status}")
                    except Exception as status_error:
                        logger.warning(f"  Could not get availability status: {status_error}")
                        logger.info(f"  LLM Orchestrator initialized: {orchestrator is not None}")
                else:
                    logger.info(f"  LLM Orchestrator initialized: {orchestrator is not None}")
                return True
            except Exception as e:
                logger.error(f"LLM Orchestrator test failed: {e}")
                raise
        
        # Test 4: Memory systems
        def test_memory_systems():
            """Test memory systems."""
            try:
                from cognitive.procedural_memory import ProceduralRepository
                from cognitive.episodic_memory import EpisodicBuffer
                
                proc_memory = ProceduralRepository(session=self.session)
                epi_memory = EpisodicBuffer(session=self.session)
                
                assert proc_memory is not None, "Procedural memory not initialized"
                assert epi_memory is not None, "Episodic memory not initialized"
                return True
            except Exception as e:
                logger.error(f"Memory systems test failed: {e}")
                raise
        
        # Test 5: Error learning integration
        def test_error_learning():
            """Test error learning integration."""
            try:
                assert self.error_learning is not None, "Error learning not initialized"
                return True
            except Exception as e:
                logger.error(f"Error learning test failed: {e}")
                raise
        
        # Test 6: Self-healing system
        def test_healing_system():
            """Test self-healing system."""
            try:
                assert self.healing_system is not None, "Healing system not initialized"
                return True
            except Exception as e:
                logger.error(f"Healing system test failed: {e}")
                raise
        
        # Test 7: API endpoints (if app is running)
        def test_api_endpoints():
            """Test API endpoints."""
            try:
                from app import app
                routes = [route.path for route in app.routes]
                assert len(routes) > 0, "No routes found"
                logger.info(f"  Found {len(routes)} API routes")
                return True
            except Exception as e:
                logger.error(f"API endpoints test failed: {e}")
                raise
        
        # Run all tests
        tests = [
            ("System Initialization", test_system_init),
            ("Database Connectivity", test_database),
            ("LLM Orchestrator", test_llm_orchestrator),
            ("Memory Systems", test_memory_systems),
            ("Error Learning Integration", test_error_learning),
            ("Self-Healing System", test_healing_system),
            ("API Endpoints", test_api_endpoints),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
    
    def print_summary(self):
        """Print test summary and healing results."""
        logger.info("\n" + "="*70)
        logger.info("E2E TEST SUMMARY")
        logger.info("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"\nTests Run: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        
        if self.bugs_found:
            logger.info(f"\n{'='*70}")
            logger.info("BUGS FOUND")
            logger.info("="*70)
            for i, bug in enumerate(self.bugs_found, 1):
                logger.info(f"\n{i}. {bug['test_name']}")
                logger.info(f"   Error Type: {bug['error_type']}")
                logger.info(f"   Error Message: {bug['error_message']}")
                if bug.get("genesis_key_id"):
                    logger.info(f"   Genesis Key: {bug['genesis_key_id']}")
        
        if self.healing_results:
            logger.info(f"\n{'='*70}")
            logger.info("HEALING RESULTS")
            logger.info("="*70)
            for i, healing in enumerate(self.healing_results, 1):
                logger.info(f"\n{i}. Bug: {healing['bug']['test_name']}")
                logger.info(f"   Healing Triggered: {healing['healing_triggered']}")
                if healing.get("healing_actions"):
                    logger.info(f"   Actions Taken: {len(healing['healing_actions'])}")
                    for j, action in enumerate(healing["healing_actions"], 1):
                        logger.info(f"     {j}. {action.get('action_type', 'unknown')}: {action.get('message', 'N/A')}")
                        logger.info(f"        Success: {action.get('success', False)}")
                else:
                    logger.info(f"   Actions Taken: 0 (no healing actions were needed)")
        
        logger.info("\n" + "="*70)
        logger.info("E2E TEST COMPLETE")
        logger.info("="*70)
        logger.info(f"\nFull log saved to: e2e_test_healing.log")


def main():
    """Main entry point."""
    runner = E2ETestRunner()
    
    try:
        runner.setup()
        runner.run_e2e_tests()
        runner.print_summary()
    except Exception as e:
        logger.error(f"Test runner failed: {e}", exc_info=True)
        return 1
    finally:
        runner.teardown()
    
    return 0 if all(r["passed"] for r in runner.test_results) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
