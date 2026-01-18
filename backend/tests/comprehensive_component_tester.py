import os
import sys
import importlib
import inspect
import traceback
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy.orm import Session
from database.session import SessionLocal
from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.autonomous_healing_system import AutonomousHealingSystem, HealthStatus, AnomalyType, TrustLevel
from genesis.genesis_key_service import get_genesis_service
logger = logging.getLogger(__name__)

class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class ComponentTestResult:
    """Result of testing a single component."""
    component_path: str
    component_name: str
    status: TestStatus
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    test_duration_ms: float = 0.0
    issues_found: List[Dict[str, Any]] = None
    genesis_key_id: Optional[str] = None
    healing_triggered: bool = False
    healing_status: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.issues_found is None:
            self.issues_found = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class TestSuiteResult:
    """Result of testing an entire suite."""
    suite_name: str
    total_components: int
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total_duration_ms: float = 0.0
    results: List[ComponentTestResult] = None
    healing_summary: Dict[str, Any] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.healing_summary is None:
            self.healing_summary = {}


class ComprehensiveComponentTester:
    """
    Comprehensive tester for all GRACE components with self-healing integration.
    """

    def __init__(
        self,
        session: Session,
        repo_path: Optional[Path] = None,
        enable_healing: bool = True,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        test_timeout_seconds: int = 30
    ):
        self.session = session
        self.repo_path = repo_path or Path(__file__).parent.parent.parent
        self.enable_healing = enable_healing
        self.trust_level = trust_level
        self.test_timeout_seconds = test_timeout_seconds

        # Initialize services
        self.genesis_service = get_genesis_service()
        self.healing_system = None
        if enable_healing:
            self.healing_system = AutonomousHealingSystem(
                session=session,
                repo_path=self.repo_path,
                trust_level=trust_level,
                enable_learning=True
            )

        # Component registry
        self.components = self._load_component_registry()
        
        # Test results
        self.test_results: List[ComponentTestResult] = []
        self.healing_log: List[Dict[str, Any]] = []

        logger.info(
            f"[COMPONENT-TESTER] Initialized: {len(self.components)} components, "
            f"healing={'ENABLED' if enable_healing else 'DISABLED'}"
        )

    def _load_component_registry(self) -> List[Dict[str, Any]]:
        """
        Load all components from the component list.
        
        Returns list of component metadata.
        """
        components = []
        backend_path = self.repo_path / "backend"

        # Component categories and their paths
        component_categories = {
            "api": ("backend/api", "*.py"),
            "cognitive": ("backend/cognitive", "*.py"),
            "genesis": ("backend/genesis", "*.py"),
            "llm_orchestrator": ("backend/llm_orchestrator", "*.py"),
            "retrieval": ("backend/retrieval", "*.py"),
            "ingestion": ("backend/ingestion", "*.py"),
            "file_manager": ("backend/file_manager", "*.py"),
            "librarian": ("backend/librarian", "*.py"),
            "ml_intelligence": ("backend/ml_intelligence", "*.py"),
            "layer1": ("backend/layer1", "*.py"),
            "layer2": ("backend/layer2", "*.py"),
            "diagnostic_machine": ("backend/diagnostic_machine", "*.py"),
            "timesense": ("backend/timesense", "*.py"),
            "enterprise": ("backend/enterprise", "*.py"),
            "ci_cd": ("backend/ci_cd", "*.py"),
            "autonomous_stress_testing": ("backend/autonomous_stress_testing", "*.py"),
            "security": ("backend/security", "*.py"),
            "embedding": ("backend/embedding", "*.py"),
            "ollama_client": ("backend/ollama_client", "*.py"),
            "vector_db": ("backend/vector_db", "*.py"),
            "version_control": ("backend/version_control", "*.py"),
            "utils": ("backend/utils", "*.py"),
            "world_model": ("backend/world_model", "*.py"),
            "agent": ("backend/agent", "*.py"),
            "confidence_scorer": ("backend/confidence_scorer", "*.py"),
            "scraping": ("backend/scraping", "*.py"),
            "models": ("backend/models", "*.py"),
            "database": ("backend/database", "*.py"),
        }

        for category, (rel_path, pattern) in component_categories.items():
            category_path = self.repo_path / rel_path
            if not category_path.exists():
                continue

            # Find all Python files
            for py_file in category_path.rglob("*.py"):
                # Skip __init__ and test files for now
                if py_file.name == "__init__.py" or "test" in py_file.name.lower():
                    continue

                # Get relative path
                rel_file_path = py_file.relative_to(self.repo_path)
                
                components.append({
                    "category": category,
                    "path": str(rel_file_path),
                    "full_path": str(py_file),
                    "name": py_file.stem,
                    "module_path": str(rel_file_path).replace("/", ".").replace("\\", ".").replace(".py", "")
                })

        logger.info(f"[COMPONENT-TESTER] Loaded {len(components)} components")
        return components

    def test_component(self, component: Dict[str, Any]) -> ComponentTestResult:
        """
        Test a single component.
        
        Tests include:
        - Import test
        - Class/function discovery
        - Basic instantiation (if applicable)
        - Error detection
        """
        start_time = datetime.utcnow()
        component_path = component["path"]
        component_name = component["name"]
        module_path = component["module_path"]

        result = ComponentTestResult(
            component_path=component_path,
            component_name=component_name,
            status=TestStatus.PASSED
        )

        try:
            # Test 1: Import test
            try:
                module = importlib.import_module(module_path)
                logger.debug(f"[TEST] ✓ Imported: {module_path}")
            except Exception as e:
                result.status = TestStatus.ERROR
                result.error_message = f"Import failed: {str(e)}"
                result.error_type = type(e).__name__
                result.traceback = traceback.format_exc()
                result.issues_found.append({
                    "type": "import_error",
                    "severity": "critical",
                    "message": str(e)
                })
                return result

            # Test 2: Discover classes and functions
            classes = []
            functions = []
            try:
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and obj.__module__ == module_path:
                        classes.append(name)
                    elif inspect.isfunction(obj) and obj.__module__ == module_path:
                        functions.append(name)
            except Exception as e:
                result.issues_found.append({
                    "type": "discovery_error",
                    "severity": "medium",
                    "message": f"Failed to discover members: {str(e)}"
                })

            # Test 3: Check for common issues
            issues = self._check_component_issues(module, component)
            result.issues_found.extend(issues)

            # Test 4: Try basic instantiation for main classes
            if classes and not result.issues_found:
                main_class = self._find_main_class(module, classes)
                if main_class:
                    try:
                        # Try to instantiate with minimal args
                        if hasattr(main_class, "__init__"):
                            sig = inspect.signature(main_class.__init__)
                            # Skip if requires complex args
                            if len(sig.parameters) <= 2:  # self + maybe one simple arg
                                try:
                                    instance = main_class()
                                    logger.debug(f"[TEST] ✓ Instantiated: {main_class.__name__}")
                                except Exception as e:
                                    result.issues_found.append({
                                        "type": "instantiation_error",
                                        "severity": "low",
                                        "message": f"Could not instantiate {main_class.__name__}: {str(e)}"
                                    })
                    except Exception as e:
                        result.issues_found.append({
                            "type": "instantiation_check_error",
                            "severity": "low",
                            "message": f"Error checking instantiation: {str(e)}"
                        })

            # Determine final status
            if result.issues_found:
                critical_issues = [i for i in result.issues_found if i.get("severity") == "critical"]
                if critical_issues:
                    result.status = TestStatus.FAILED
                else:
                    result.status = TestStatus.FAILED if result.issues_found else TestStatus.PASSED

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = f"Unexpected error: {str(e)}"
            result.error_type = type(e).__name__
            result.traceback = traceback.format_exc()
            result.issues_found.append({
                "type": "unexpected_error",
                "severity": "critical",
                "message": str(e),
                "traceback": result.traceback
            })

        finally:
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.test_duration_ms = duration

        return result

    def _check_component_issues(self, module: Any, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for common issues in a component."""
        issues = []
        source_file = component.get("full_path")

        if not source_file or not os.path.exists(source_file):
            return issues

        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check 1: Syntax errors (basic)
            try:
                compile(content, source_file, 'exec')
            except SyntaxError as e:
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "message": f"Syntax error at line {e.lineno}: {e.msg}",
                    "line": e.lineno
                })

            # Check 2: Missing imports
            import_lines = [line for line in content.split('\n') if line.strip().startswith('import') or line.strip().startswith('from')]
            for imp_line in import_lines:
                try:
                    # Try to parse import
                    compile(imp_line, '<string>', 'exec')
                except SyntaxError:
                    issues.append({
                        "type": "import_syntax_error",
                        "severity": "medium",
                        "message": f"Invalid import syntax: {imp_line[:50]}"
                    })

            # Check 3: Common patterns
            if "TODO" in content or "FIXME" in content or "XXX" in content:
                issues.append({
                    "type": "todo_found",
                    "severity": "low",
                    "message": "Contains TODO/FIXME/XXX markers"
                })

            # Check 4: Error handling
            if "except:" in content or "except Exception:" in content:
                # Check if it's too broad
                if "except:" in content and "pass" in content:
                    issues.append({
                        "type": "broad_exception",
                        "severity": "low",
                        "message": "Uses bare except: or broad exception handling"
                    })

        except Exception as e:
            issues.append({
                "type": "file_read_error",
                "severity": "medium",
                "message": f"Could not read file for analysis: {str(e)}"
            })

        return issues

    def _find_main_class(self, module: Any, classes: List[str]) -> Optional[Any]:
        """Find the main class in a module (usually the one with the same name as module)."""
        module_name = module.__name__.split('.')[-1]
        
        # Try exact match first
        for cls_name in classes:
            if cls_name.lower() == module_name.lower():
                return getattr(module, cls_name)
        
        # Try common patterns
        for cls_name in classes:
            cls = getattr(module, cls_name)
            # Skip if it's a base class or abstract
            if hasattr(cls, '__abstractmethods__') and cls.__abstractmethods__:
                continue
            return cls
        
        return None

    def log_bug_to_healing(self, result: ComponentTestResult) -> Optional[str]:
        """
        Log a bug to the healing system and trigger healing.
        
        Returns Genesis Key ID if created.
        """
        if not result.issues_found and result.status == TestStatus.PASSED:
            return None

        # Create Genesis Key for the bug
        genesis_key_id = None
        try:
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.ERROR,
                what_description=f"Component test failure: {result.component_name}",
                who_actor="comprehensive_component_tester",
                where_location=result.component_path,
                why_reason=f"Test found {len(result.issues_found)} issues",
                how_method="automated_component_testing",
                file_path=result.component_path,
                error_message=result.error_message,
                error_type=result.error_type,
                context_data={
                    "test_status": result.status.value,
                    "issues": result.issues_found,
                    "component_name": result.component_name,
                    "test_duration_ms": result.test_duration_ms,
                    "traceback": result.traceback
                },
                tags=["component_test", "automated_testing", "self_healing"]
            )
            genesis_key_id = key.key_id
            result.genesis_key_id = genesis_key_id

            logger.info(f"[HEALING] Created Genesis Key {genesis_key_id} for {result.component_name}")

        except Exception as e:
            logger.error(f"[HEALING] Failed to create Genesis Key: {str(e)}")
            return None

        # Trigger healing system
        if self.healing_system and result.status != TestStatus.PASSED:
            try:
                # Assess health (this will detect the new Genesis Key)
                health_assessment = self.healing_system.assess_system_health()
                
                # Check if healing was triggered
                if health_assessment.get("anomalies_detected", 0) > 0:
                    # Decide and execute healing
                    healing_actions = self.healing_system.decide_healing_actions(
                        health_assessment.get("anomalies", [])
                    )
                    
                    if healing_actions:
                        for action in healing_actions:
                            healing_result = self.healing_system.execute_healing(action)
                            result.healing_triggered = True
                            result.healing_status = healing_result.get("status", "unknown")
                            
                            self.healing_log.append({
                                "component": result.component_name,
                                "genesis_key_id": genesis_key_id,
                                "healing_action": action.get("action"),
                                "healing_result": healing_result,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            
                            logger.info(
                                f"[HEALING] Triggered healing for {result.component_name}: "
                                f"{action.get('action')} -> {result.healing_status}"
                            )

            except Exception as e:
                logger.error(f"[HEALING] Failed to trigger healing: {str(e)}")
                result.healing_status = f"error: {str(e)}"

        return genesis_key_id

    def test_all_components(self) -> TestSuiteResult:
        """
        Test all components and send bugs to healing system.
        
        Returns comprehensive test suite results.
        """
        logger.info(f"[COMPONENT-TESTER] Starting comprehensive test of {len(self.components)} components...")
        
        start_time = datetime.utcnow()
        suite_result = TestSuiteResult(
            suite_name="comprehensive_component_test",
            total_components=len(self.components)
        )

        # Test each component
        for idx, component in enumerate(self.components, 1):
            logger.info(
                f"[TEST] [{idx}/{len(self.components)}] Testing: {component['name']} "
                f"({component['category']})"
            )

            # Test component
            result = self.test_component(component)
            
            # Log bug to healing system
            if result.status != TestStatus.PASSED or result.issues_found:
                self.log_bug_to_healing(result)

            # Update statistics
            if result.status == TestStatus.PASSED:
                suite_result.passed += 1
            elif result.status == TestStatus.FAILED:
                suite_result.failed += 1
            elif result.status == TestStatus.ERROR:
                suite_result.errors += 1
            else:
                suite_result.skipped += 1

            # Store result
            suite_result.results.append(result)
            self.test_results.append(result)

            # Progress update
            if idx % 10 == 0:
                logger.info(
                    f"[PROGRESS] {idx}/{len(self.components)} tested. "
                    f"Passed: {suite_result.passed}, Failed: {suite_result.failed}, "
                    f"Errors: {suite_result.errors}"
                )

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        suite_result.total_duration_ms = duration

        # Generate healing summary
        suite_result.healing_summary = {
            "total_issues_found": sum(len(r.issues_found) for r in suite_result.results),
            "healing_triggered": sum(1 for r in suite_result.results if r.healing_triggered),
            "healing_successful": sum(
                1 for r in suite_result.results 
                if r.healing_triggered and r.healing_status == "success"
            ),
            "genesis_keys_created": sum(
                1 for r in suite_result.results if r.genesis_key_id
            ),
            "healing_log": self.healing_log
        }

        logger.info(
            f"[COMPONENT-TESTER] Test complete: "
            f"{suite_result.passed} passed, {suite_result.failed} failed, "
            f"{suite_result.errors} errors in {duration/1000:.2f}s"
        )

        return suite_result

    def generate_report(self, suite_result: TestSuiteResult, output_path: Optional[Path] = None) -> str:
        """Generate a comprehensive test report."""
        if output_path is None:
            output_path = self.repo_path / "backend" / "tests" / "component_test_report.json"

        report = {
            "test_suite": suite_result.suite_name,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_components": suite_result.total_components,
                "passed": suite_result.passed,
                "failed": suite_result.failed,
                "errors": suite_result.errors,
                "skipped": suite_result.skipped,
                "total_duration_ms": suite_result.total_duration_ms,
                "success_rate": (
                    suite_result.passed / suite_result.total_components * 100
                    if suite_result.total_components > 0 else 0
                )
            },
            "healing_summary": suite_result.healing_summary,
            "results": [
                {
                    "component_path": r.component_path,
                    "component_name": r.component_name,
                    "status": r.status.value,
                    "issues_count": len(r.issues_found),
                    "issues": r.issues_found,
                    "error_message": r.error_message,
                    "genesis_key_id": r.genesis_key_id,
                    "healing_triggered": r.healing_triggered,
                    "healing_status": r.healing_status,
                    "test_duration_ms": r.test_duration_ms
                }
                for r in suite_result.results
            ]
        }

        # Save report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"[REPORT] Saved test report to: {output_path}")

        # Generate human-readable summary
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║         GRACE COMPREHENSIVE COMPONENT TEST REPORT            ║
╚══════════════════════════════════════════════════════════════╝

Test Suite: {suite_result.suite_name}
Timestamp: {datetime.utcnow().isoformat()}
Duration: {suite_result.total_duration_ms/1000:.2f} seconds

SUMMARY:
  Total Components: {suite_result.total_components}
  ✓ Passed: {suite_result.passed}
  ✗ Failed: {suite_result.failed}
  ⚠ Errors: {suite_result.errors}
  ⊘ Skipped: {suite_result.skipped}
  Success Rate: {report['summary']['success_rate']:.2f}%

HEALING SUMMARY:
  Total Issues Found: {suite_result.healing_summary['total_issues_found']}
  Genesis Keys Created: {suite_result.healing_summary['genesis_keys_created']}
  Healing Actions Triggered: {suite_result.healing_summary['healing_triggered']}
  Healing Successful: {suite_result.healing_summary['healing_successful']}

FAILED COMPONENTS:
"""
        failed_components = [r for r in suite_result.results if r.status != TestStatus.PASSED]
        for result in failed_components[:20]:  # Show first 20
            summary += f"  ✗ {result.component_name} ({result.component_path})\n"
            if result.error_message:
                summary += f"    Error: {result.error_message[:100]}\n"
            if result.issues_found:
                summary += f"    Issues: {len(result.issues_found)}\n"

        if len(failed_components) > 20:
            summary += f"  ... and {len(failed_components) - 20} more\n"

        summary += f"\nFull report saved to: {output_path}\n"

        return summary


def main():
    """Main entry point for comprehensive component testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Test all GRACE components and send bugs to self-healing")
    parser.add_argument(
        "--no-healing",
        action="store_true",
        help="Disable self-healing (only test and log)"
    )
    parser.add_argument(
        "--trust-level",
        type=int,
        default=3,
        help="Trust level for healing (0-9, default: 3)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for test report"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Test only specific category (e.g., 'api', 'cognitive')"
    )

    args = parser.parse_args()

    # Initialize database connection and session factory
    from database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
    from database.session import initialize_session_factory
    from settings import settings
    
    # Initialize database
    db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
    db_config = DatabaseConfig(
        db_type=db_type,
        host=settings.DATABASE_HOST if settings else None,
        port=settings.DATABASE_PORT if settings else None,
        username=settings.DATABASE_USER if settings else None,
        password=settings.DATABASE_PASSWORD if settings else None,
        database=settings.DATABASE_NAME if settings else "grace",
        database_path=settings.DATABASE_PATH if settings else None,
        echo=settings.DATABASE_ECHO if settings else False,
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    
    # Get database session
    from database.session import SessionLocal
    session = SessionLocal()

    try:
        # Initialize tester
        tester = ComprehensiveComponentTester(
            session=session,
            enable_healing=not args.no_healing,
            trust_level=TrustLevel(args.trust_level)
        )

        # Filter by category if specified
        if args.category:
            tester.components = [
                c for c in tester.components 
                if c["category"] == args.category
            ]
            logger.info(f"[FILTER] Testing only category: {args.category} ({len(tester.components)} components)")

        # Run tests
        suite_result = tester.test_all_components()

        # Generate report
        output_path = Path(args.output) if args.output else None
        report_summary = tester.generate_report(suite_result, output_path)
        
        print(report_summary)

        # Exit with error code if failures
        if suite_result.failed > 0 or suite_result.errors > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"[FATAL] Test suite failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
