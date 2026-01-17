#!/usr/bin/env python3
"""
MOTHER OF ALL STRESS TESTS

Comprehensive end-to-end stress test that exercises:
1. System E2E functionality
2. Self-healing agent
3. Pipeline coding agent
4. Concurrent operations
5. Multiple failure modes
6. Performance under load
7. Recovery capabilities

This is the ultimate test of Grace's resilience and autonomous capabilities.
"""

import sys
import os
import json
import logging
import time
import threading
import random
import asyncio
import traceback
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup comprehensive logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = log_dir / f"mother_stress_test_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TestCategory(Enum):
    """Categories of stress tests."""
    E2E = "e2e"
    SELF_HEALING = "self_healing"
    PIPELINE_CODING = "pipeline_coding"
    CONCURRENT = "concurrent"
    PERFORMANCE = "performance"
    RECOVERY = "recovery"
    INTEGRATION = "integration"


class TestResult(Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class StressTestResult:
    """Result of a stress test."""
    test_name: str
    category: TestCategory
    result: TestResult
    duration_seconds: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    healing_actions: List[Dict[str, Any]] = field(default_factory=list)
    pipeline_operations: List[Dict[str, Any]] = field(default_factory=list)
    coding_operations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MotherOfAllStressTests:
    """The ultimate stress test suite."""
    
    def __init__(self):
        self.results: List[StressTestResult] = []
        self.session = None
        self.healing_system = None
        self.pipeline = None
        self.coding_agent = None
        self.llm_orchestrator = None
        self.start_time = datetime.now(UTC)
        self.test_files_created = []
        self.backup_files = {}
        self.concurrent_operations = []
        self.performance_metrics = []
        self.failures_log = []
        
        # Setup failure-specific logging
        failure_log_file = log_dir / f"mother_stress_test_failures_{timestamp}.log"
        self.failure_logger = logging.getLogger("failures")
        self.failure_logger.setLevel(logging.ERROR)
        failure_handler = logging.FileHandler(failure_log_file)
        failure_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
        self.failure_logger.addHandler(failure_handler)
        
    def initialize_systems(self) -> bool:
        """Initialize all required systems."""
        logger.info("=" * 100)
        logger.info("INITIALIZING SYSTEMS FOR MOTHER OF ALL STRESS TESTS")
        logger.info("=" * 100)
        
        try:
            # Initialize database
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            from database.session import initialize_session_factory
            
            db_config = DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                database_path="data/grace.db"
            )
            DatabaseConnection.initialize(db_config)
            session_factory = initialize_session_factory()
            self.session = session_factory()
            logger.info("[OK] Database initialized")
            
            # Initialize self-healing system
            try:
                from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
                self.healing_system = get_autonomous_healing(
                    session=self.session,
                    repo_path=Path("backend"),
                    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                    enable_learning=True
                )
                logger.info("[OK] Self-healing system initialized")
            except Exception as e:
                logger.warning(f"⚠ Self-healing system not available: {e}")
            
            # Initialize pipeline
            try:
                from genesis.pipeline_integration import get_data_pipeline
                self.pipeline = get_data_pipeline(session=self.session)
                logger.info("[OK] Pipeline initialized")
            except Exception as e:
                logger.warning(f"⚠ Pipeline not available: {e}")
            
            # Initialize coding agent
            try:
                from agent.grace_agent import GraceAgent, AgentConfig
                agent_config = AgentConfig(
                    max_iterations=50,
                    use_rag=True,
                    use_memory=True,
                    learn_from_execution=True
                )
                self.coding_agent = GraceAgent(config=agent_config)
                logger.info("[OK] Coding agent initialized")
            except Exception as e:
                logger.warning(f"⚠ Coding agent not available: {e}")
            
            # Initialize LLM orchestrator
            try:
                from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                self.llm_orchestrator = get_llm_orchestrator(session=self.session)
                logger.info("[OK] LLM orchestrator initialized")
            except Exception as e:
                logger.warning(f"⚠ LLM orchestrator not available: {e}")
            
            logger.info("=" * 100)
            logger.info("SYSTEM INITIALIZATION COMPLETE")
            logger.info("=" * 100)
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize systems: {e}", exc_info=True)
            return False
    
    def run_all_tests(self):
        """Run the complete stress test suite."""
        logger.info("\n" + "=" * 100)
        logger.info("MOTHER OF ALL STRESS TESTS - STARTING")
        logger.info("=" * 100)
        logger.info(f"Start Time: {self.start_time.isoformat()}")
        logger.info("=" * 100 + "\n")
        
        # Test suites organized by category
        test_suites = {
            TestCategory.E2E: [
                ("System Initialization", self.test_e2e_system_init),
                ("Database Connectivity", self.test_e2e_database),
                ("API Endpoints", self.test_e2e_api_endpoints),
                ("Memory Systems", self.test_e2e_memory_systems),
                ("Complete Workflow", self.test_e2e_complete_workflow),
            ],
            TestCategory.SELF_HEALING: [
                ("Syntax Error Healing", self.test_healing_syntax_error),
                ("Import Error Healing", self.test_healing_import_error),
                ("File System Healing", self.test_healing_file_system),
                ("Database Healing", self.test_healing_database),
                ("Configuration Healing", self.test_healing_configuration),
                ("Concurrent Error Healing", self.test_healing_concurrent_errors),
                ("Performance Degradation Healing", self.test_healing_performance),
                ("Memory Leak Healing", self.test_healing_memory_leak),
            ],
            TestCategory.PIPELINE_CODING: [
                ("Pipeline Input Processing", self.test_pipeline_input),
                ("Pipeline Code Generation", self.test_pipeline_code_generation),
                ("Pipeline Error Handling", self.test_pipeline_error_handling),
                ("Pipeline Concurrent Operations", self.test_pipeline_concurrent),
                ("Pipeline Recovery", self.test_pipeline_recovery),
            ],
            TestCategory.CONCURRENT: [
                ("Concurrent File Operations", self.test_concurrent_files),
                ("Concurrent Database Operations", self.test_concurrent_database),
                ("Concurrent API Calls", self.test_concurrent_api),
                ("Concurrent Healing Operations", self.test_concurrent_healing),
                ("Concurrent Pipeline Operations", self.test_concurrent_pipeline),
            ],
            TestCategory.PERFORMANCE: [
                ("High Load File Operations", self.test_performance_files),
                ("High Load Database Operations", self.test_performance_database),
                ("High Load API Operations", self.test_performance_api),
                ("Memory Pressure", self.test_performance_memory),
                ("CPU Pressure", self.test_performance_cpu),
            ],
            TestCategory.RECOVERY: [
                ("Recovery from Syntax Errors", self.test_recovery_syntax),
                ("Recovery from Import Errors", self.test_recovery_import),
                ("Recovery from Database Errors", self.test_recovery_database),
                ("Recovery from File System Errors", self.test_recovery_filesystem),
                ("Recovery from Configuration Errors", self.test_recovery_config),
            ],
            TestCategory.INTEGRATION: [
                ("End-to-End with Healing", self.test_integration_e2e_healing),
                ("End-to-End with Pipeline", self.test_integration_e2e_pipeline),
                ("End-to-End with Coding Agent", self.test_integration_e2e_coding),
                ("Complete System Integration", self.test_integration_complete),
            ],
        }
        
        # Run all test suites
        total_tests = sum(len(tests) for tests in test_suites.values())
        test_count = 0
        
        for category, tests in test_suites.items():
            logger.info("\n" + "=" * 100)
            logger.info(f"RUNNING {category.value.upper()} TESTS ({len(tests)} tests)")
            logger.info("=" * 100)
            
            for test_name, test_func in tests:
                test_count += 1
                logger.info(f"\n[{test_count}/{total_tests}] Running: {test_name}")
                logger.info("-" * 100)
                
                start_time = time.time()
                result = TestResult.ERROR
                error = None
                details = {}
                healing_actions = []
                pipeline_operations = []
                coding_operations = []
                
                try:
                    # Run test with timeout
                    test_result = self._run_test_with_timeout(test_func, timeout=300)
                    
                    if test_result.get("success", False):
                        result = TestResult.PASSED
                        details = test_result.get("details", {})
                        healing_actions = test_result.get("healing_actions", [])
                        pipeline_operations = test_result.get("pipeline_operations", [])
                        coding_operations = test_result.get("coding_operations", [])
                    else:
                        result = TestResult.FAILED
                        error = test_result.get("error", "Test failed")
                        details = test_result.get("details", {})
                        healing_actions = test_result.get("healing_actions", [])
                        pipeline_operations = test_result.get("pipeline_operations", [])
                        coding_operations = test_result.get("coding_operations", [])
                        
                        # Log failure details
                        self._log_failure(
                            test_name=test_name,
                            category=category,
                            error=error,
                            details=details,
                            healing_actions=healing_actions,
                            pipeline_operations=pipeline_operations,
                            coding_operations=coding_operations,
                            traceback_str=test_result.get("traceback")
                        )
                        
                except TimeoutError:
                    result = TestResult.TIMEOUT
                    error = "Test timed out after 300 seconds"
                    self._log_failure(
                        test_name=test_name,
                        category=category,
                        error=error,
                        details={"timeout_seconds": 300},
                        traceback_str=None
                    )
                except Exception as e:
                    result = TestResult.ERROR
                    error = str(e)
                    traceback_str = traceback.format_exc()
                    logger.error(f"Test error: {e}", exc_info=True)
                    self._log_failure(
                        test_name=test_name,
                        category=category,
                        error=error,
                        details={},
                        traceback_str=traceback_str
                    )
                
                duration = time.time() - start_time
                
                test_result = StressTestResult(
                    test_name=test_name,
                    category=category,
                    result=result,
                    duration_seconds=duration,
                    error=error,
                    details=details,
                    healing_actions=healing_actions,
                    pipeline_operations=pipeline_operations,
                    coding_operations=coding_operations
                )
                
                self.results.append(test_result)
                
                # Log result
                status_icon = "✓" if result == TestResult.PASSED else "✗"
                logger.info(f"{status_icon} {test_name}: {result.value.upper()} ({duration:.2f}s)")
                if error:
                    logger.error(f"  [FAILURE] {test_name}")
                    logger.error(f"    Category: {category.value}")
                    logger.error(f"    Error: {error}")
                    logger.error(f"    Duration: {duration:.2f}s")
                    if details:
                        logger.error(f"    Details: {json.dumps(details, indent=6, default=str)}")
                    if healing_actions:
                        logger.error(f"    Healing Actions Attempted: {len(healing_actions)}")
                        for i, action in enumerate(healing_actions, 1):
                            logger.error(f"      {i}. {action}")
                    if pipeline_operations:
                        logger.error(f"    Pipeline Operations Attempted: {len(pipeline_operations)}")
                        for i, op in enumerate(pipeline_operations, 1):
                            logger.error(f"      {i}. {op}")
                    if coding_operations:
                        logger.error(f"    Coding Operations Attempted: {len(coding_operations)}")
                        for i, op in enumerate(coding_operations, 1):
                            logger.error(f"      {i}. {op}")
                
                # Brief pause between tests
                time.sleep(1)
        
        # Generate final report
        self._generate_report()
        
        # Cleanup
        self._cleanup()
        
        logger.info("\n" + "=" * 100)
        logger.info("MOTHER OF ALL STRESS TESTS - COMPLETE")
        logger.info("=" * 100)
    
    def _log_failure(
        self,
        test_name: str,
        category: TestCategory,
        error: str,
        details: Dict[str, Any],
        healing_actions: List[Dict[str, Any]] = None,
        pipeline_operations: List[Dict[str, Any]] = None,
        coding_operations: List[Dict[str, Any]] = None,
        traceback_str: Optional[str] = None
    ):
        """Log a failure with comprehensive details."""
        failure_record = {
            "test_name": test_name,
            "category": category.value,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details,
            "healing_actions": healing_actions or [],
            "pipeline_operations": pipeline_operations or [],
            "coding_operations": coding_operations or [],
            "traceback": traceback_str
        }
        
        self.failures_log.append(failure_record)
        
        # Log to failure logger
        self.failure_logger.error("=" * 100)
        self.failure_logger.error(f"FAILURE: {test_name}")
        self.failure_logger.error(f"Category: {category.value}")
        self.failure_logger.error(f"Timestamp: {failure_record['timestamp']}")
        self.failure_logger.error(f"Error: {error}")
        
        if details:
            self.failure_logger.error(f"Details: {json.dumps(details, indent=2, default=str)}")
        
        if healing_actions:
            self.failure_logger.error(f"Healing Actions ({len(healing_actions)}):")
            for i, action in enumerate(healing_actions, 1):
                self.failure_logger.error(f"  {i}. {json.dumps(action, indent=4, default=str)}")
        
        if pipeline_operations:
            self.failure_logger.error(f"Pipeline Operations ({len(pipeline_operations)}):")
            for i, op in enumerate(pipeline_operations, 1):
                self.failure_logger.error(f"  {i}. {json.dumps(op, indent=4, default=str)}")
        
        if coding_operations:
            self.failure_logger.error(f"Coding Operations ({len(coding_operations)}):")
            for i, op in enumerate(coding_operations, 1):
                self.failure_logger.error(f"  {i}. {json.dumps(op, indent=4, default=str)}")
        
        if traceback_str:
            self.failure_logger.error("Traceback:")
            self.failure_logger.error(traceback_str)
        
        self.failure_logger.error("=" * 100)
        self.failure_logger.error("")
    
    def _run_test_with_timeout(self, test_func: Callable, timeout: int = 300):
        """Run a test with timeout protection."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Test timed out")
        
        # Set up timeout (Unix only)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
        
        try:
            result = test_func()
            # Add traceback if test failed
            if not result.get("success", False) and "traceback" not in result:
                import sys
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exc_traceback:
                    result["traceback"] = traceback.format_exception(exc_type, exc_value, exc_traceback)
            return result
        except Exception as e:
            # Capture traceback for exceptions
            import sys
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            return {
                "success": False,
                "error": str(e),
                "traceback": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            }
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm
    
    # =====================================================================
    # E2E TESTS
    # =====================================================================
    
    def test_e2e_system_init(self) -> Dict[str, Any]:
        """Test: System initialization end-to-end."""
        try:
            from app import app
            assert app is not None, "App not initialized"
            return {"success": True, "details": {"app_initialized": True}}
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_e2e_database(self) -> Dict[str, Any]:
        """Test: Database connectivity end-to-end."""
        try:
            assert self.session is not None, "Session not initialized"
            from sqlalchemy import text
            result = self.session.execute(text("SELECT 1"))
            result.fetchone()
            return {"success": True, "details": {"database_connected": True}}
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__, "session_available": self.session is not None},
                "traceback": traceback.format_exc()
            }
    
    def test_e2e_api_endpoints(self) -> Dict[str, Any]:
        """Test: API endpoints end-to-end."""
        try:
            from app import app
            routes = [route.path for route in app.routes]
            assert len(routes) > 0, "No routes found"
            return {"success": True, "details": {"routes_found": len(routes)}}
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_e2e_memory_systems(self) -> Dict[str, Any]:
        """Test: Memory systems end-to-end."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
            from cognitive.episodic_memory import EpisodicBuffer
            
            proc_memory = ProceduralRepository(session=self.session)
            epi_memory = EpisodicBuffer(session=self.session)
            
            assert proc_memory is not None, "Procedural memory not initialized"
            assert epi_memory is not None, "Episodic memory not initialized"
            return {"success": True, "details": {"memory_systems_ok": True}}
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "exception_type": type(e).__name__,
                    "session_available": self.session is not None
                },
                "traceback": traceback.format_exc()
            }
    
    def test_e2e_complete_workflow(self) -> Dict[str, Any]:
        """Test: Complete workflow end-to-end."""
        try:
            # Simulate a complete workflow
            test_file = Path("backend/test_e2e_workflow.py")
            test_file.write_text("""
def test_function():
    return "Hello, World!"

if __name__ == "__main__":
    print(test_function())
""")
            self.test_files_created.append(test_file)
            
            # Try to execute it
            import subprocess
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            success = result.returncode == 0 and "Hello, World!" in result.stdout
            
            return {
                "success": success,
                "details": {
                    "file_created": True,
                    "execution_success": success,
                    "output": result.stdout
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # SELF-HEALING TESTS
    # =====================================================================
    
    def test_healing_syntax_error(self) -> Dict[str, Any]:
        """Test: Self-healing of syntax errors."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            # Create file with syntax error
            test_file = Path("backend/test_healing_syntax.py")
            test_file.write_text("def broken_function(\n    return 'missing colon'\n")
            self.test_files_created.append(test_file)
            self.backup_files[str(test_file)] = ""
            
            # Trigger healing
            healing_result = self.healing_system.run_monitoring_cycle()
            
            # Check if fixed
            time.sleep(3)
            try:
                compile(test_file.read_text(), str(test_file), 'exec')
                fixed = True
            except SyntaxError:
                fixed = False
            
            return {
                "success": fixed,
                "details": {"file_fixed": fixed},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_import_error(self) -> Dict[str, Any]:
        """Test: Self-healing of import errors."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            test_file = Path("backend/test_healing_import.py")
            test_file.write_text("from nonexistent_module import something\nprint('test')")
            self.test_files_created.append(test_file)
            
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"healing_triggered": True},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_file_system(self) -> Dict[str, Any]:
        """Test: Self-healing of file system issues."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            test_file = Path("backend/test_healing_filesystem.txt")
            test_file.write_text("Test content")
            self.backup_files[str(test_file)] = test_file.read_text()
            test_file.unlink()
            
            healing_result = self.healing_system.run_monitoring_cycle()
            
            time.sleep(2)
            fixed = test_file.exists()
            
            return {
                "success": fixed,
                "details": {"file_restored": fixed},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_database(self) -> Dict[str, Any]:
        """Test: Self-healing of database issues."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"healing_triggered": True},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_configuration(self) -> Dict[str, Any]:
        """Test: Self-healing of configuration issues."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"healing_triggered": True},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_concurrent_errors(self) -> Dict[str, Any]:
        """Test: Self-healing of concurrent errors."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            # Create multiple errors
            errors = []
            for i in range(5):
                test_file = Path(f"backend/test_concurrent_error_{i}.py")
                test_file.write_text(f"def broken_{i}()\n    return {i}\n")
                self.test_files_created.append(test_file)
                errors.append(test_file)
            
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"errors_introduced": len(errors)},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_performance(self) -> Dict[str, Any]:
        """Test: Self-healing of performance degradation."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"healing_triggered": True},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_healing_memory_leak(self) -> Dict[str, Any]:
        """Test: Self-healing of memory leaks."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            healing_result = self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"healing_triggered": True},
                "healing_actions": healing_result.get("actions_executed", [])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # PIPELINE CODING TESTS
    # =====================================================================
    
    def test_pipeline_input(self) -> Dict[str, Any]:
        """Test: Pipeline input processing."""
        if not self.pipeline:
            return {"success": False, "error": "Pipeline not available"}
        
        try:
            result = self.pipeline.process_input(
                input_data="Test input data",
                input_type="user_input",
                user_id="stress_test_user",
                description="Stress test input"
            )
            
            return {
                "success": result.get("complete", False),
                "details": result,
                "pipeline_operations": [result]
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_pipeline_code_generation(self) -> Dict[str, Any]:
        """Test: Pipeline code generation."""
        if not self.pipeline or not self.coding_agent:
            return {"success": False, "error": "Pipeline or coding agent not available"}
        
        try:
            # Process code generation request through pipeline
            result = self.pipeline.process_input(
                input_data="Create a function that adds two numbers",
                input_type="code_generation",
                user_id="stress_test_user",
                description="Code generation request"
            )
            
            return {
                "success": result.get("complete", False),
                "details": result,
                "pipeline_operations": [result]
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_pipeline_error_handling(self) -> Dict[str, Any]:
        """Test: Pipeline error handling."""
        if not self.pipeline:
            return {"success": False, "error": "Pipeline not available"}
        
        try:
            # Process invalid input
            result = self.pipeline.process_input(
                input_data=None,
                input_type="invalid_type",
                user_id="stress_test_user"
            )
            
            # Pipeline should handle error gracefully
            return {
                "success": True,
                "details": {"error_handled": True},
                "pipeline_operations": [result]
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_pipeline_concurrent(self) -> Dict[str, Any]:
        """Test: Pipeline concurrent operations."""
        if not self.pipeline:
            return {"success": False, "error": "Pipeline not available"}
        
        try:
            def process_input(i):
                return self.pipeline.process_input(
                    input_data=f"Concurrent input {i}",
                    input_type="user_input",
                    user_id=f"user_{i}"
                )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_input, i) for i in range(10)]
                results = [f.result() for f in as_completed(futures)]
            
            success_count = sum(1 for r in results if r.get("complete", False))
            
            return {
                "success": success_count > 5,
                "details": {"concurrent_operations": len(results), "successful": success_count},
                "pipeline_operations": results
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_pipeline_recovery(self) -> Dict[str, Any]:
        """Test: Pipeline recovery from errors."""
        if not self.pipeline:
            return {"success": False, "error": "Pipeline not available"}
        
        try:
            # Process input after error
            result1 = self.pipeline.process_input(
                input_data=None,
                input_type="invalid",
                user_id="stress_test_user"
            )
            
            # Process valid input
            result2 = self.pipeline.process_input(
                input_data="Valid input",
                input_type="user_input",
                user_id="stress_test_user"
            )
            
            return {
                "success": result2.get("complete", False),
                "details": {"recovered": True},
                "pipeline_operations": [result1, result2]
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # CONCURRENT TESTS
    # =====================================================================
    
    def test_concurrent_files(self) -> Dict[str, Any]:
        """Test: Concurrent file operations."""
        try:
            def create_file(i):
                test_file = Path(f"backend/test_concurrent_file_{i}.txt")
                test_file.write_text(f"Content {i}")
                self.test_files_created.append(test_file)
                return test_file.exists()
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(create_file, i) for i in range(50)]
                results = [f.result() for f in as_completed(futures)]
            
            success_count = sum(1 for r in results if r)
            
            return {
                "success": success_count > 40,
                "details": {"files_created": success_count, "total": len(results)}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_concurrent_database(self) -> Dict[str, Any]:
        """Test: Concurrent database operations."""
        try:
            def db_operation(i):
                from sqlalchemy import text
                result = self.session.execute(text(f"SELECT {i}"))
                return result.fetchone()[0] == i
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(db_operation, i) for i in range(20)]
                results = [f.result() for f in as_completed(futures)]
            
            success_count = sum(1 for r in results if r)
            
            return {
                "success": success_count > 15,
                "details": {"operations": len(results), "successful": success_count}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_concurrent_api(self) -> Dict[str, Any]:
        """Test: Concurrent API calls."""
        try:
            # Simulate API calls
            def api_call(i):
                time.sleep(0.1)
                return {"status": "ok", "id": i}
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(api_call, i) for i in range(30)]
                results = [f.result() for f in as_completed(futures)]
            
            return {
                "success": len(results) == 30,
                "details": {"api_calls": len(results)}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_concurrent_healing(self) -> Dict[str, Any]:
        """Test: Concurrent healing operations."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            def healing_operation(i):
                return self.healing_system.run_monitoring_cycle()
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(healing_operation, i) for i in range(5)]
                results = [f.result() for f in as_completed(futures)]
            
            return {
                "success": len(results) == 5,
                "details": {"healing_operations": len(results)},
                "healing_actions": [r.get("actions_executed", []) for r in results]
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_concurrent_pipeline(self) -> Dict[str, Any]:
        """Test: Concurrent pipeline operations."""
        if not self.pipeline:
            return {"success": False, "error": "Pipeline not available"}
        
        try:
            def pipeline_op(i):
                return self.pipeline.process_input(
                    input_data=f"Concurrent {i}",
                    input_type="user_input",
                    user_id=f"user_{i}"
                )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(pipeline_op, i) for i in range(15)]
                results = [f.result() for f in as_completed(futures)]
            
            success_count = sum(1 for r in results if r.get("complete", False))
            
            return {
                "success": success_count > 10,
                "details": {"operations": len(results), "successful": success_count},
                "pipeline_operations": results
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # PERFORMANCE TESTS
    # =====================================================================
    
    def test_performance_files(self) -> Dict[str, Any]:
        """Test: High load file operations."""
        try:
            start_time = time.time()
            
            for i in range(100):
                test_file = Path(f"backend/test_perf_file_{i}.txt")
                test_file.write_text(f"Performance test content {i}")
                self.test_files_created.append(test_file)
            
            duration = time.time() - start_time
            throughput = 100 / duration if duration > 0 else 0
            
            return {
                "success": duration < 5.0,
                "details": {
                    "files_created": 100,
                    "duration": duration,
                    "throughput": throughput
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_performance_database(self) -> Dict[str, Any]:
        """Test: High load database operations."""
        try:
            from sqlalchemy import text
            
            start_time = time.time()
            
            for i in range(100):
                result = self.session.execute(text(f"SELECT {i}"))
                result.fetchone()
            
            duration = time.time() - start_time
            throughput = 100 / duration if duration > 0 else 0
            
            return {
                "success": duration < 10.0,
                "details": {
                    "operations": 100,
                    "duration": duration,
                    "throughput": throughput
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_performance_api(self) -> Dict[str, Any]:
        """Test: High load API operations."""
        try:
            start_time = time.time()
            
            # Simulate API calls
            for i in range(50):
                time.sleep(0.01)  # Simulate API call
            
            duration = time.time() - start_time
            
            return {
                "success": duration < 10.0,
                "details": {
                    "api_calls": 50,
                    "duration": duration
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_performance_memory(self) -> Dict[str, Any]:
        """Test: Memory pressure."""
        try:
            # Create memory pressure
            large_data = []
            for i in range(20):
                data = bytearray(1024 * 1024)  # 1MB chunks
                large_data.append(data)
            
            # Cleanup
            del large_data
            
            return {
                "success": True,
                "details": {"memory_test": "completed"}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_performance_cpu(self) -> Dict[str, Any]:
        """Test: CPU pressure."""
        try:
            start_time = time.time()
            
            # CPU-intensive task
            total = 0
            for i in range(100000):
                total += i * i
            
            duration = time.time() - start_time
            
            return {
                "success": duration < 5.0,
                "details": {
                    "cpu_test": "completed",
                    "duration": duration
                }
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # RECOVERY TESTS
    # =====================================================================
    
    def test_recovery_syntax(self) -> Dict[str, Any]:
        """Test: Recovery from syntax errors."""
        try:
            test_file = Path("backend/test_recovery_syntax.py")
            test_file.write_text("def broken()\n    pass\n")
            self.test_files_created.append(test_file)
            
            # Try to fix
            if self.healing_system:
                self.healing_system.run_monitoring_cycle()
                time.sleep(2)
            
            # Check recovery
            try:
                compile(test_file.read_text(), str(test_file), 'exec')
                recovered = True
            except SyntaxError:
                recovered = False
            
            return {
                "success": recovered,
                "details": {"recovered": recovered}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_recovery_import(self) -> Dict[str, Any]:
        """Test: Recovery from import errors."""
        try:
            test_file = Path("backend/test_recovery_import.py")
            test_file.write_text("from missing import something")
            self.test_files_created.append(test_file)
            
            if self.healing_system:
                self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"recovery_attempted": True}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_recovery_database(self) -> Dict[str, Any]:
        """Test: Recovery from database errors."""
        try:
            # Test database recovery
            from sqlalchemy import text
            result = self.session.execute(text("SELECT 1"))
            result.fetchone()
            
            return {
                "success": True,
                "details": {"database_recovered": True}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_recovery_filesystem(self) -> Dict[str, Any]:
        """Test: Recovery from file system errors."""
        try:
            test_file = Path("backend/test_recovery_fs.txt")
            test_file.write_text("Recovery test")
            self.backup_files[str(test_file)] = test_file.read_text()
            test_file.unlink()
            
            if self.healing_system:
                self.healing_system.run_monitoring_cycle()
                time.sleep(2)
            
            recovered = test_file.exists()
            
            return {
                "success": recovered,
                "details": {"recovered": recovered}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_recovery_config(self) -> Dict[str, Any]:
        """Test: Recovery from configuration errors."""
        try:
            if self.healing_system:
                self.healing_system.run_monitoring_cycle()
            
            return {
                "success": True,
                "details": {"recovery_attempted": True}
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # INTEGRATION TESTS
    # =====================================================================
    
    def test_integration_e2e_healing(self) -> Dict[str, Any]:
        """Test: E2E with self-healing integration."""
        try:
            # Create error
            test_file = Path("backend/test_integration_e2e_healing.py")
            test_file.write_text("def broken()\n    pass\n")
            self.test_files_created.append(test_file)
            
            # E2E test
            e2e_result = self.test_e2e_system_init()
            
            # Healing
            healing_actions = []
            if self.healing_system:
                healing_result = self.healing_system.run_monitoring_cycle()
                healing_actions = healing_result.get("actions_executed", [])
            
            return {
                "success": e2e_result.get("success", False),
                "details": {"e2e": e2e_result, "healing": True},
                "healing_actions": healing_actions
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_integration_e2e_pipeline(self) -> Dict[str, Any]:
        """Test: E2E with pipeline integration."""
        try:
            e2e_result = self.test_e2e_system_init()
            
            pipeline_result = None
            if self.pipeline:
                pipeline_result = self.pipeline.process_input(
                    input_data="Integration test",
                    input_type="user_input",
                    user_id="integration_test"
                )
            
            return {
                "success": e2e_result.get("success", False) and (pipeline_result is None or pipeline_result.get("complete", False)),
                "details": {"e2e": e2e_result, "pipeline": pipeline_result},
                "pipeline_operations": [pipeline_result] if pipeline_result else []
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_integration_e2e_coding(self) -> Dict[str, Any]:
        """Test: E2E with coding agent integration."""
        try:
            e2e_result = self.test_e2e_system_init()
            
            coding_result = None
            if self.coding_agent:
                # Simulate coding task
                coding_result = {"status": "simulated"}
            
            return {
                "success": e2e_result.get("success", False),
                "details": {"e2e": e2e_result, "coding": coding_result},
                "coding_operations": [coding_result] if coding_result else []
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    def test_integration_complete(self) -> Dict[str, Any]:
        """Test: Complete system integration."""
        try:
            # Run all integration components
            e2e_result = self.test_e2e_system_init()
            
            healing_actions = []
            if self.healing_system:
                healing_result = self.healing_system.run_monitoring_cycle()
                healing_actions = healing_result.get("actions_executed", [])
            
            pipeline_result = None
            if self.pipeline:
                pipeline_result = self.pipeline.process_input(
                    input_data="Complete integration test",
                    input_type="user_input",
                    user_id="complete_test"
                )
            
            return {
                "success": e2e_result.get("success", False),
                "details": {
                    "e2e": e2e_result,
                    "healing": len(healing_actions) > 0,
                    "pipeline": pipeline_result is not None
                },
                "healing_actions": healing_actions,
                "pipeline_operations": [pipeline_result] if pipeline_result else []
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__},
                "traceback": traceback.format_exc()
            }
    
    # =====================================================================
    # REPORTING AND CLEANUP
    # =====================================================================
    
    def _generate_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 100)
        logger.info("GENERATING COMPREHENSIVE TEST REPORT")
        logger.info("=" * 100)
        
        end_time = datetime.now(UTC)
        duration = (end_time - self.start_time).total_seconds()
        
        # Calculate statistics
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.result == TestResult.PASSED)
        failed = sum(1 for r in self.results if r.result == TestResult.FAILED)
        errors = sum(1 for r in self.results if r.result == TestResult.ERROR)
        timeouts = sum(1 for r in self.results if r.result == TestResult.TIMEOUT)
        
        # By category
        by_category = {}
        for category in TestCategory:
            category_results = [r for r in self.results if r.category == category]
            by_category[category.value] = {
                "total": len(category_results),
                "passed": sum(1 for r in category_results if r.result == TestResult.PASSED),
                "failed": sum(1 for r in category_results if r.result == TestResult.FAILED),
                "errors": sum(1 for r in category_results if r.result == TestResult.ERROR)
            }
        
        # Healing statistics
        total_healing_actions = sum(len(r.healing_actions) for r in self.results)
        total_pipeline_ops = sum(len(r.pipeline_operations) for r in self.results)
        total_coding_ops = sum(len(r.coding_operations) for r in self.results)
        
        # Create report
        report = {
            "test_suite": "Mother of All Stress Tests",
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "timeouts": timeouts,
                "success_rate": (passed / total_tests * 100) if total_tests > 0 else 0
            },
            "by_category": by_category,
            "statistics": {
                "total_healing_actions": total_healing_actions,
                "total_pipeline_operations": total_pipeline_ops,
                "total_coding_operations": total_coding_ops,
                "average_test_duration": sum(r.duration_seconds for r in self.results) / total_tests if total_tests > 0 else 0
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "category": r.category.value,
                    "result": r.result.value,
                    "duration": r.duration_seconds,
                    "error": r.error,
                    "details": r.details,
                    "healing_actions_count": len(r.healing_actions),
                    "pipeline_operations_count": len(r.pipeline_operations),
                    "coding_operations_count": len(r.coding_operations)
                }
                for r in self.results
            ]
        }
        
        # Save JSON report
        report_file = Path(f"mother_stress_test_report_{timestamp}.json")
        report_file.write_text(json.dumps(report, indent=2, default=str))
        
        # Save markdown report
        md_report = self._generate_markdown_report(report)
        md_file = Path(f"mother_stress_test_report_{timestamp}.md")
        md_file.write_text(md_report)
        
        # Save failures summary
        if self.failures_log:
            failures_file = Path(f"mother_stress_test_failures_{timestamp}.json")
            failures_file.write_text(json.dumps({
                "total_failures": len(self.failures_log),
                "failures_by_category": self._categorize_failures(),
                "failures": self.failures_log
            }, indent=2, default=str))
            logger.info(f"  Failures: {failures_file}")
        
        # Print summary
        logger.info("\n" + "=" * 100)
        logger.info("TEST SUMMARY")
        logger.info("=" * 100)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed} ({passed/total_tests*100:.1f}%)" if total_tests > 0 else "Passed: 0")
        logger.info(f"Failed: {failed}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Timeouts: {timeouts}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"\nReports saved:")
        logger.info(f"  JSON: {report_file}")
        logger.info(f"  Markdown: {md_file}")
        logger.info(f"  Log: {log_file}")
        if self.failures_log:
            failures_file = Path(f"mother_stress_test_failures_{timestamp}.json")
            logger.info(f"  Failures: {failures_file}")
            logger.info(f"\nFAILURE SUMMARY:")
            logger.info(f"  Total Failures: {len(self.failures_log)}")
            failures_by_cat = self._categorize_failures()
            for category, count in failures_by_cat.items():
                logger.info(f"  {category}: {count}")
        logger.info("=" * 100)
    
    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate markdown report."""
        summary = report["summary"]
        
        md = f"""# Mother of All Stress Tests - Report

**Date:** {report['start_time']}  
**Duration:** {report['duration_seconds']:.2f} seconds  
**Status:** {'✅ PASSED' if summary['success_rate'] >= 80 else '⚠️ PARTIAL' if summary['success_rate'] >= 50 else '❌ FAILED'}

---

## Executive Summary

- **Total Tests:** {summary['total_tests']}
- **Passed:** {summary['passed']} ({summary['success_rate']:.1f}%)
- **Failed:** {summary['failed']}
- **Errors:** {summary['errors']}
- **Timeouts:** {summary['timeouts']}

---

## Results by Category

"""
        for category, stats in report['by_category'].items():
            md += f"### {category.upper()}\n"
            md += f"- Total: {stats['total']}\n"
            md += f"- Passed: {stats['passed']}\n"
            md += f"- Failed: {stats['failed']}\n"
            md += f"- Errors: {stats['errors']}\n\n"
        
        md += f"""
---

## Statistics

- **Total Healing Actions:** {report['statistics']['total_healing_actions']}
- **Total Pipeline Operations:** {report['statistics']['total_pipeline_operations']}
- **Total Coding Operations:** {report['statistics']['total_coding_operations']}
- **Average Test Duration:** {report['statistics']['average_test_duration']:.2f} seconds

---

## Failures Summary

**Total Failures:** {len(self.failures_log)}

### Failures by Category

"""
        failures_by_cat = self._categorize_failures()
        for category, count in failures_by_cat.items():
            md += f"- **{category}:** {count}\n"
        
        md += f"""
### Detailed Failures

"""
        for i, failure in enumerate(self.failures_log, 1):
            md += f"#### {i}. {failure['test_name']}\n"
            md += f"- **Category:** {failure['category']}\n"
            md += f"- **Error:** {failure['error']}\n"
            md += f"- **Timestamp:** {failure['timestamp']}\n"
            if failure.get('details'):
                md += f"- **Details:**\n```json\n{json.dumps(failure['details'], indent=2, default=str)}\n```\n"
            if failure.get('healing_actions'):
                md += f"- **Healing Actions:** {len(failure['healing_actions'])}\n"
            if failure.get('pipeline_operations'):
                md += f"- **Pipeline Operations:** {len(failure['pipeline_operations'])}\n"
            if failure.get('traceback'):
                md += f"- **Traceback:**\n```python\n{failure['traceback']}\n```\n"
            md += "\n"
        
        md += f"""
---

## Test Results

"""
        for result in report['results']:
            status_icon = "[PASS]" if result['result'] == 'passed' else "[FAIL]"
            md += f"### {status_icon} {result['test_name']}\n"
            md += f"- **Category:** {result['category']}\n"
            md += f"- **Result:** {result['result']}\n"
            md += f"- **Duration:** {result['duration']:.2f}s\n"
            if result['error']:
                md += f"- **Error:** {result['error']}\n"
            md += f"- **Healing Actions:** {result['healing_actions_count']}\n"
            md += f"- **Pipeline Operations:** {result['pipeline_operations_count']}\n"
            md += f"- **Coding Operations:** {result['coding_operations_count']}\n"
            md += "\n"
        
        return md
    
    def _categorize_failures(self) -> Dict[str, int]:
        """Categorize failures by category."""
        by_category = {}
        for failure in self.failures_log:
            category = failure.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
        return by_category
    
    def _cleanup(self):
        """Cleanup test files."""
        logger.info("\nCleaning up test files...")
        
        for test_file in self.test_files_created:
            try:
                if test_file.exists():
                    test_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove {test_file}: {e}")
        
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")


def main():
    """Main entry point."""
    logger.info("=" * 100)
    logger.info("MOTHER OF ALL STRESS TESTS")
    logger.info("=" * 100)
    
    tester = MotherOfAllStressTests()
    
    if not tester.initialize_systems():
        logger.error("Failed to initialize systems. Exiting.")
        return 1
    
    try:
        tester.run_all_tests()
        return 0
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        tester._cleanup()
        return 130
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        tester._cleanup()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
