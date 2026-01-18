"""
Pytest configuration and fixtures for Grace API tests.

This module handles graceful fallback when full app dependencies
are not available, and reports diagnostic information back to GRACE
for autonomous learning and self-improvement.
"""

import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pytest
from unittest.mock import MagicMock

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Diagnostic data collection
_diagnostics: Dict[str, Any] = {
    "session_id": datetime.utcnow().isoformat(),
    "environment": {
        "python_version": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
    },
    "passes": [],  # Track passing tests with diagnostic info
    "failures": [],  # Track failing tests with diagnostic info
    "skips": [],
    "import_errors": [],
    "missing_dependencies": set(),
    "suggested_fixes": [],
    "learned_patterns": [],  # Patterns GRACE can learn from successful tests
    "test_results": {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0
    }
}

# Track if we can import the full app
_app_available = False
_app = None

# FIX: Track database initialization to prevent multiple initializations
_database_initialized = False
_test_db_path = None

# Diagnostic report path
DIAGNOSTIC_REPORT_PATH = backend_dir / "tests" / "diagnostic_report.json"


class DiagnosticCollector:
    """Collects diagnostic information about test passes, skips and failures.

    This collector helps GRACE learn from ALL test outcomes:
    - PASSES: Learn what makes tests succeed, capture validation patterns
    - FAILURES: Learn what breaks, capture error patterns for self-healing
    - SKIPS: Learn what dependencies are missing, track environment issues
    """

    # Known dependency mappings for helpful suggestions
    DEPENDENCY_FIXES = {
        "numpy": "pip install numpy",
        "scipy": "pip install scipy",
        "scikit-learn": "pip install scikit-learn",
        "fastapi": "pip install fastapi uvicorn",
        "sqlalchemy": "pip install sqlalchemy",
        "pydantic": "pip install pydantic",
        "qdrant-client": "pip install qdrant-client",
        "sentence-transformers": "pip install sentence-transformers",
        "torch": "pip install torch",
        "transformers": "pip install transformers",
        "httpx": "pip install httpx",
        "psutil": "pip install psutil",
        "embedding.embedder": "Ensure embedding/ module is in PYTHONPATH",
        "cognitive": "Ensure cognitive/ module is in PYTHONPATH",
        "retrieval": "Ensure retrieval/ module is in PYTHONPATH",
        "models.database_models": "Ensure models/ module exists with database_models.py",
    }

    # Categories of tests for learning patterns
    TEST_CATEGORIES = {
        "api": ["test_api_", "TestAPI", "endpoint"],
        "database": ["test_database", "test_db", "TestDatabase", "repository"],
        "model": ["test_model", "TestModel", "embedding", "ml_"],
        "security": ["test_security", "TestSecurity", "auth", "injection"],
        "integration": ["test_integration", "TestIntegration", "complete"],
        "cognitive": ["test_cognitive", "cognitive", "learning"],
        "retrieval": ["test_retrieval", "rag", "search", "retrieve"],
    }

    @classmethod
    def _categorize_test(cls, test_name: str) -> List[str]:
        """Categorize a test based on its name for pattern learning."""
        categories = []
        test_lower = test_name.lower()
        for category, patterns in cls.TEST_CATEGORIES.items():
            if any(pattern.lower() in test_lower for pattern in patterns):
                categories.append(category)
        return categories if categories else ["general"]

    @classmethod
    def record_pass(cls, test_name: str, duration_ms: float, details: Optional[Dict] = None):
        """Record a passing test with diagnostic information for GRACE learning.

        Args:
            test_name: Full test identifier (module::class::method)
            duration_ms: Test execution time in milliseconds
            details: Additional context about the test
        """
        categories = cls._categorize_test(test_name)

        pass_info = {
            "test": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "categories": categories,
            "details": details or {},
            "validation_type": cls._infer_validation_type(test_name),
            "learned_insight": cls._generate_learned_insight(test_name, details)
        }
        _diagnostics["passes"].append(pass_info)
        _diagnostics["test_results"]["passed"] += 1

        # Extract learnable patterns from successful tests
        pattern = cls._extract_success_pattern(test_name, details)
        if pattern and pattern not in _diagnostics["learned_patterns"]:
            _diagnostics["learned_patterns"].append(pattern)

    @classmethod
    def record_failure(cls, test_name: str, error_type: str, error_message: str,
                       duration_ms: float, details: Optional[Dict] = None):
        """Record a failing test with diagnostic information.

        Args:
            test_name: Full test identifier
            error_type: Exception type name
            error_message: Error message
            duration_ms: Test execution time
            details: Additional context
        """
        categories = cls._categorize_test(test_name)

        failure_info = {
            "test": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "categories": categories,
            "error_type": error_type,
            "error_message": error_message,
            "details": details or {},
            "suggested_fix": cls._suggest_fix_for_failure(error_type, error_message),
            "is_infrastructure_issue": cls._is_infrastructure_failure(error_message),
        }
        _diagnostics["failures"].append(failure_info)
        _diagnostics["test_results"]["failed"] += 1

    @classmethod
    def _infer_validation_type(cls, test_name: str) -> str:
        """Infer what type of validation the test performs."""
        test_lower = test_name.lower()

        if "response" in test_lower or "status_code" in test_lower or "endpoint" in test_lower:
            return "api_response_validation"
        elif "create" in test_lower or "insert" in test_lower:
            return "data_creation_validation"
        elif "get" in test_lower or "retrieve" in test_lower or "fetch" in test_lower:
            return "data_retrieval_validation"
        elif "update" in test_lower or "modify" in test_lower:
            return "data_modification_validation"
        elif "delete" in test_lower or "remove" in test_lower:
            return "data_deletion_validation"
        elif "auth" in test_lower or "permission" in test_lower:
            return "authorization_validation"
        elif "search" in test_lower or "query" in test_lower:
            return "search_validation"
        elif "connection" in test_lower or "health" in test_lower:
            return "connectivity_validation"
        elif "config" in test_lower or "setting" in test_lower:
            return "configuration_validation"
        else:
            return "general_validation"

    @classmethod
    def _generate_learned_insight(cls, test_name: str, details: Optional[Dict]) -> str:
        """Generate a human-readable insight about what the test validates."""
        validation_type = cls._infer_validation_type(test_name)

        # Extract test components
        parts = test_name.split("::")
        method_name = parts[-1] if parts else test_name

        insights = {
            "api_response_validation": f"API endpoint responds correctly: {method_name}",
            "data_creation_validation": f"Data creation works as expected: {method_name}",
            "data_retrieval_validation": f"Data retrieval returns expected results: {method_name}",
            "data_modification_validation": f"Data updates are applied correctly: {method_name}",
            "data_deletion_validation": f"Data deletion removes records properly: {method_name}",
            "authorization_validation": f"Authorization rules are enforced: {method_name}",
            "search_validation": f"Search functionality returns relevant results: {method_name}",
            "connectivity_validation": f"Service connectivity is established: {method_name}",
            "configuration_validation": f"Configuration is valid and applied: {method_name}",
            "general_validation": f"Test assertion passed: {method_name}",
        }

        return insights.get(validation_type, f"Validation passed: {method_name}")

    @classmethod
    def _extract_success_pattern(cls, test_name: str, details: Optional[Dict]) -> Optional[Dict]:
        """Extract a learnable pattern from a successful test."""
        categories = cls._categorize_test(test_name)
        validation_type = cls._infer_validation_type(test_name)

        # Only extract patterns for significant test categories
        if "general" not in categories or validation_type != "general_validation":
            return {
                "pattern_type": validation_type,
                "categories": categories,
                "test_name": test_name,
                "description": f"Successfully validated {validation_type} for {', '.join(categories)}",
            }
        return None

    @classmethod
    def _suggest_fix_for_failure(cls, error_type: str, error_message: str) -> Optional[str]:
        """Suggest a fix based on the failure type."""
        error_lower = error_message.lower()

        if "connection refused" in error_lower:
            return "Start the required service (Qdrant/Ollama/Database)"
        elif "no module named" in error_lower:
            return cls._get_suggested_fix(error_message)
        elif "assertion" in error_type.lower():
            return "Check test expectations vs actual implementation"
        elif "timeout" in error_lower:
            return "Increase timeout or check service performance"
        elif "permission" in error_lower or "forbidden" in error_lower:
            return "Check authentication/authorization configuration"
        elif "not found" in error_lower or "404" in error_lower:
            return "Verify endpoint/resource exists"

        return None

    @classmethod
    def _is_infrastructure_failure(cls, error_message: str) -> bool:
        """Determine if failure is due to infrastructure issues."""
        infrastructure_indicators = [
            "connection refused",
            "no module named",
            "service unavailable",
            "timeout",
            "503",
            "qdrant",
            "ollama",
            "database not initialized",
        ]
        error_lower = error_message.lower()
        return any(indicator in error_lower for indicator in infrastructure_indicators)

    @classmethod
    def record_skip(cls, test_name: str, reason: str, details: Optional[Dict] = None):
        """Record a test skip with diagnostic information."""
        skip_info = {
            "test": test_name,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "categories": cls._categorize_test(test_name),
            "details": details or {},
            "suggested_fix": cls._get_suggested_fix(reason),
            "is_infrastructure_issue": cls._is_infrastructure_failure(reason),
        }
        _diagnostics["skips"].append(skip_info)
        _diagnostics["test_results"]["skipped"] += 1

        # Extract missing dependency if present
        if "No module named" in reason:
            module = reason.split("No module named")[-1].strip().strip("'\"")
            _diagnostics["missing_dependencies"].add(module)
            if module in cls.DEPENDENCY_FIXES:
                fix = cls.DEPENDENCY_FIXES[module]
                if fix not in _diagnostics["suggested_fixes"]:
                    _diagnostics["suggested_fixes"].append(fix)

    @classmethod
    def record_import_error(cls, module: str, error: Exception, import_chain: List[str] = None):
        """Record an import error with full traceback."""
        error_info = {
            "module": module,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "import_chain": import_chain or [],
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat(),
            "suggested_fix": cls._get_suggested_fix(str(error))
        }
        _diagnostics["import_errors"].append(error_info)

        # Extract the root cause module
        if "No module named" in str(error):
            root_module = str(error).split("No module named")[-1].strip().strip("'\"")
            _diagnostics["missing_dependencies"].add(root_module)

    @classmethod
    def _get_suggested_fix(cls, error_message: str) -> Optional[str]:
        """Get a suggested fix based on the error message."""
        for key, fix in cls.DEPENDENCY_FIXES.items():
            if key in error_message:
                return fix
        return None

    @classmethod
    def get_report(cls) -> Dict[str, Any]:
        """Get the full diagnostic report with learning insights."""
        report = _diagnostics.copy()
        report["missing_dependencies"] = list(_diagnostics["missing_dependencies"])

        # Calculate pass rate and categorize results
        total_tests = (
            _diagnostics["test_results"]["passed"] +
            _diagnostics["test_results"]["failed"] +
            _diagnostics["test_results"]["skipped"]
        )
        pass_rate = (_diagnostics["test_results"]["passed"] / total_tests * 100) if total_tests > 0 else 0

        # Categorize failures
        infrastructure_failures = [f for f in _diagnostics["failures"]
                                    if f.get("is_infrastructure_issue", False)]
        code_failures = [f for f in _diagnostics["failures"]
                         if not f.get("is_infrastructure_issue", False)]

        # Extract unique validation types from passes
        validation_types_passed = list(set(
            p.get("validation_type", "unknown")
            for p in _diagnostics["passes"]
        ))

        # Extract categories with most passes
        category_pass_counts = {}
        for p in _diagnostics["passes"]:
            for cat in p.get("categories", ["general"]):
                category_pass_counts[cat] = category_pass_counts.get(cat, 0) + 1

        report["summary"] = {
            "total_tests": total_tests,
            "pass_rate": round(pass_rate, 2),
            "total_passes": len(_diagnostics["passes"]),
            "total_failures": len(_diagnostics["failures"]),
            "total_skips": len(_diagnostics["skips"]),
            "total_import_errors": len(_diagnostics["import_errors"]),
            "infrastructure_failures": len(infrastructure_failures),
            "code_failures": len(code_failures),
            "missing_dependency_count": len(_diagnostics["missing_dependencies"]),
            "has_critical_issues": len(_diagnostics["import_errors"]) > 0,
            "environment_ready": _app_available,
            "validation_types_working": validation_types_passed,
            "category_pass_counts": category_pass_counts,
            "learned_patterns_count": len(_diagnostics["learned_patterns"]),
        }

        # Add learning insights section
        report["learning_insights"] = {
            "what_works": [p.get("learned_insight") for p in _diagnostics["passes"][:20]],
            "what_fails": [
                {
                    "test": f["test"],
                    "reason": f.get("error_message", "Unknown"),
                    "fix": f.get("suggested_fix"),
                    "is_infra": f.get("is_infrastructure_issue", False)
                }
                for f in _diagnostics["failures"][:20]
            ],
            "patterns_learned": _diagnostics["learned_patterns"][:20],
        }

        return report

    @classmethod
    def save_report(cls, path: Path = None):
        """Save the diagnostic report to a JSON file."""
        path = path or DIAGNOSTIC_REPORT_PATH
        report = cls.get_report()
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return path

    @classmethod
    def report_to_grace(cls) -> bool:
        """Report ALL diagnostics to GRACE API for learning.

        Reports successes, failures, and skips - GRACE learns from everything.
        """
        report = cls.get_report()

        try:
            import httpx

            # Report full diagnostics to GRACE learning endpoint
            response = httpx.post(
                "http://localhost:8000/test/diagnostics",
                json=report,
                timeout=10.0
            )

            if response.status_code == 200:
                return True

            # Also try the autonomous learning endpoint for pattern extraction
            try:
                httpx.post(
                    "http://localhost:8000/api/learning/from-tests",
                    json={
                        "passes": report.get("passes", [])[:50],
                        "failures": report.get("failures", [])[:50],
                        "learned_patterns": report.get("learned_patterns", []),
                        "session_id": report.get("session_id"),
                    },
                    timeout=5.0
                )
            except Exception:
                pass  # Learning endpoint is optional

            return response.status_code == 200
        except Exception:
            # If GRACE isn't running, save locally for later learning
            cls.save_report()
            return False


def _try_import_app():
    """Try to import the FastAPI app, handling missing dependencies gracefully."""
    global _app_available, _app, _database_initialized, _test_db_path
    import_chain = []

    try:
        # Initialize database BEFORE importing app to ensure middleware has DB access
        import_chain.append("database initialization")
        try:
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            from database.base import Base
            import tempfile
            import time

            # FIX: Use global flag to prevent multiple initializations
            if not _database_initialized:
                try:
                    DatabaseConnection.get_engine()
                    # Already initialized by another path
                    _database_initialized = True
                except RuntimeError:
                    # Not initialized, set it up
                    temp_dir = tempfile.gettempdir()
                    timestamp = int(time.time() * 1000)
                    _test_db_path = os.path.join(temp_dir, f"grace_test_{timestamp}_{os.getpid()}.db")

                    test_config = DatabaseConfig(
                        db_type=DatabaseType.SQLITE,
                        database_path=_test_db_path,
                        echo=False,
                    )
                    DatabaseConnection.initialize(test_config)

                    # Import models and create tables
                    from models import database_models, genesis_key_models
                    Base.metadata.create_all(bind=DatabaseConnection.get_engine())

                    # Also initialize session factory
                    from database.session import initialize_session_factory
                    initialize_session_factory()

                    _database_initialized = True
        except Exception as db_err:
            import logging
            logging.warning(f"Test database pre-initialization failed: {db_err}")

        import_chain.append("fastapi.testclient")
        from fastapi.testclient import TestClient

        import_chain.append("app")
        from app import app as fastapi_app

        _app = fastapi_app
        _app_available = True
        return fastapi_app

    except ImportError as e:
        DiagnosticCollector.record_import_error(
            module="app",
            error=e,
            import_chain=import_chain
        )
        _app_available = False
        return None


def _skip_with_diagnostic(reason: str, test_name: str = "unknown", details: Dict = None):
    """Skip a test and record diagnostic information."""
    DiagnosticCollector.record_skip(test_name, reason, details)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def app(request):
    """Get the FastAPI application."""
    fastapi_app = _try_import_app()
    if fastapi_app is None:
        DiagnosticCollector.record_skip(
            test_name=request.node.name if hasattr(request, 'node') else "app_fixture",
            reason="Full app dependencies not available",
            details={"import_errors": _diagnostics["import_errors"]}
        )
        pytest.skip("Full app dependencies not available")
    return fastapi_app


@pytest.fixture(scope="session")
def client(app, request):
    """Create a test client for the application."""
    global _database_initialized, _test_db_path

    if app is None:
        DiagnosticCollector.record_skip(
            test_name=request.node.name if hasattr(request, 'node') else "client_fixture",
            reason="App not available for test client"
        )
        pytest.skip("Full app dependencies not available")

    # FIX: Database should already be initialized by _try_import_app()
    # Use the global flag to check - only initialize if absolutely necessary
    if not _database_initialized:
        try:
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            from database.session import initialize_session_factory
            from database.base import Base
            import tempfile
            import time

            # Check if already initialized via DatabaseConnection
            try:
                DatabaseConnection.get_engine()
                _database_initialized = True
            except RuntimeError:
                # Not initialized, set it up
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time() * 1000)
                _test_db_path = os.path.join(temp_dir, f"grace_test_{timestamp}_{os.getpid()}.db")

                test_config = DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    database_path=_test_db_path,
                    echo=False,
                )
                DatabaseConnection.initialize(test_config)
                initialize_session_factory()

                # Import all models and create tables
                try:
                    from models import database_models, genesis_key_models
                except ImportError as e:
                    import logging
                    logging.warning(f"Could not import all models: {e}")

                Base.metadata.create_all(bind=DatabaseConnection.get_engine())
                _database_initialized = True

        except Exception as e:
            import logging
            logging.warning(f"Could not initialize test database: {e}")

    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def ensure_database_initialized():
    """Ensure database is initialized for the entire test session.

    FIX: Uses global flag to prevent multiple initializations.
    """
    global _database_initialized, _test_db_path

    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from database.session import initialize_session_factory
        from database.base import Base
        import tempfile
        import time

        # FIX: Check global flag first
        if not _database_initialized:
            try:
                DatabaseConnection.get_engine()
                _database_initialized = True
            except RuntimeError:
                # Initialize database
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time() * 1000)
                _test_db_path = os.path.join(temp_dir, f"grace_test_session_{timestamp}.db")

                test_config = DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    database_path=_test_db_path,
                    echo=False,
                )
                DatabaseConnection.initialize(test_config)
                initialize_session_factory()

                # Import and create tables
                from models import database_models, genesis_key_models
                Base.metadata.create_all(bind=DatabaseConnection.get_engine())
                _database_initialized = True

        yield

        # Cleanup after all tests
        try:
            engine = DatabaseConnection.get_engine()
            if engine:
                engine.dispose()
            # Clean up temp database file
            if _test_db_path and os.path.exists(_test_db_path):
                try:
                    os.remove(_test_db_path)
                except Exception:
                    pass
        except Exception:
            pass
    except Exception as e:
        import logging
        logging.warning(f"Database initialization fixture failed: {e}")
        yield


@pytest.fixture(scope="function")
def test_db(request):
    """Create a test database session."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from database.base import Base

        # Create in-memory SQLite database
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create session
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = TestingSessionLocal()

        yield session

        session.close()
        Base.metadata.drop_all(bind=engine)
    except ImportError as e:
        DiagnosticCollector.record_skip(
            test_name=request.node.name if hasattr(request, 'node') else "test_db_fixture",
            reason=f"Database dependencies not available: {e}",
            details={"missing_module": str(e)}
        )
        pytest.skip(f"Database dependencies not available: {e}")


@pytest.fixture
def diagnostic_collector():
    """Provide access to the diagnostic collector for tests."""
    return DiagnosticCollector


@pytest.fixture
def sample_chat_request():
    """Sample chat request data."""
    return {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40
    }


@pytest.fixture
def sample_document_content():
    """Sample document content for ingestion tests."""
    return """
    # Sample Document

    This is a test document for Grace API testing.

    ## Section 1

    This section contains information about testing.

    ## Section 2

    This section contains more test content.
    """


@pytest.fixture
def sample_genesis_key():
    """Sample Genesis Key data."""
    return {
        "entity_type": "document",
        "entity_id": "test-doc-123",
        "origin_source": "test",
        "origin_type": "unit_test"
    }


@pytest.fixture
def sample_learning_example():
    """Sample learning example for ML tests."""
    return {
        "input": "What is machine learning?",
        "output": "Machine learning is a subset of AI...",
        "task_type": "qa",
        "trust_score": 0.85
    }


@pytest.fixture
def sample_governance_rule():
    """Sample governance rule data."""
    return {
        "rule_id": "test-rule-001",
        "name": "Test Rule",
        "description": "A test governance rule",
        "pillar": "operational",
        "priority": 1,
        "conditions": [
            {"field": "action_type", "operator": "equals", "value": "delete"}
        ],
        "actions": ["require_approval"]
    }


@pytest.fixture
def sample_whitelist_entry():
    """Sample whitelist entry data."""
    return {
        "entry_type": "domain",
        "value": "trusted.example.com",
        "reason": "Test whitelisted domain",
        "approved_by": "test_user"
    }


# Pytest hooks for diagnostic collection

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks tests as API endpoint tests")
    config.addinivalue_line("markers", "requires_app: marks tests that need full app")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture detailed test results for GRACE learning.

    Captures comprehensive diagnostic data for:
    - PASSED tests: Why they passed, what was validated, duration
    - FAILED tests: Error details, stack traces, suggested fixes
    - SKIPPED tests: Reasons, missing dependencies
    """
    outcome = yield
    report = outcome.get_result()

    # Calculate duration in milliseconds
    duration_ms = (call.stop - call.start) * 1000 if hasattr(call, 'stop') and hasattr(call, 'start') else 0

    # Get test details
    test_name = item.nodeid
    test_module = item.module.__name__ if hasattr(item, 'module') else "unknown"
    test_class = item.cls.__name__ if hasattr(item, 'cls') and item.cls else None
    test_function = item.name

    # Build details dict
    details = {
        "module": test_module,
        "class": test_class,
        "function": test_function,
        "file": str(item.fspath) if hasattr(item, 'fspath') else None,
        "markers": [mark.name for mark in item.iter_markers()],
        "fixtures_used": list(item.fixturenames) if hasattr(item, 'fixturenames') else [],
    }

    if call.when == "call":
        if report.passed:
            # Record successful test with full details
            DiagnosticCollector.record_pass(
                test_name=test_name,
                duration_ms=duration_ms,
                details={
                    **details,
                    "outcome": "passed",
                    "assertions_likely_validated": _infer_assertions(test_function),
                }
            )
            
            # ✅ NEW: Record outcome in OutcomeAggregator for cross-system learning
            try:
                from cognitive.outcome_aggregator import get_outcome_aggregator
                from database.session import get_db
                
                session = next(get_db())
                aggregator = get_outcome_aggregator(session)
                aggregator.record_outcome('testing', {
                    'test_name': test_name,
                    'success': True,
                    'trust_score': 0.9,  # High trust for passing tests
                    'duration': duration_ms,
                    'test_module': test_module,
                    'test_class': test_class,
                    'test_function': test_function
                })
            except Exception as e:
                # Don't fail tests if aggregator fails
                pass
            
            # ✅ NEW: Create Genesis Key for test outcome to trigger LLM knowledge update
            try:
                from genesis.genesis_key_service import get_genesis_service
                from models.genesis_key_models import GenesisKeyType
                from database.session import get_db
                
                session = next(get_db())
                genesis_service = get_genesis_service()
                
                genesis_key = genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"Test passed: {test_name}",
                    who_actor="pytest",
                    where_location=str(item.fspath) if hasattr(item, 'fspath') else None,
                    why_reason="Test outcome for LLM knowledge update",
                    how_method="pytest_execution",
                    file_path=str(item.fspath) if hasattr(item, 'fspath') else None,
                    context_data={
                        'test_name': test_name,
                        'test_module': test_module,
                        'test_class': test_class,
                        'test_function': test_function,
                        'duration_ms': duration_ms,
                        'outcome': 'passed'
                    },
                    metadata={
                        'outcome_type': 'test_outcome',
                        'example_type': 'test_outcome',
                        'trust_score': 0.9,  # High trust for passing tests
                        'success': True,
                        'test_name': test_name,
                        'duration_ms': duration_ms
                    },
                    session=session
                )
            except Exception as e:
                # Don't fail tests if Genesis Key creation fails
                pass
        
        elif report.failed:
            # Record failed test with error details
            error_type = call.excinfo.typename if call.excinfo else "Unknown"
            error_message = str(call.excinfo.value) if call.excinfo else "No error message"
            tb_lines = traceback.format_exception(
                call.excinfo.type, call.excinfo.value, call.excinfo.tb
            ) if call.excinfo else []

            DiagnosticCollector.record_failure(
                test_name=test_name,
                error_type=error_type,
                error_message=error_message,
                duration_ms=duration_ms,
                details={
                    **details,
                    "outcome": "failed",
                    "traceback_summary": tb_lines[-3:] if tb_lines else [],
                    "full_traceback": "".join(tb_lines) if len(tb_lines) < 50 else "Traceback too long",
                }
            )
            
            # ✅ NEW: Record outcome in OutcomeAggregator for cross-system learning
            try:
                from cognitive.outcome_aggregator import get_outcome_aggregator
                from database.session import get_db
                
                session = next(get_db())
                aggregator = get_outcome_aggregator(session)
                aggregator.record_outcome('testing', {
                    'test_name': test_name,
                    'success': False,
                    'trust_score': 0.7,  # Medium trust - failures are still valuable
                    'duration': duration_ms,
                    'error_type': error_type,
                    'error_message': error_message,
                    'test_module': test_module,
                    'test_class': test_class,
                    'test_function': test_function
                })
            except Exception as e:
                # Don't fail tests if aggregator fails
                pass
            
            # ✅ NEW: Create Genesis Key for test failure outcome
            try:
                from genesis.genesis_key_service import get_genesis_service
                from models.genesis_key_models import GenesisKeyType
                from database.session import get_db
                
                session = next(get_db())
                genesis_service = get_genesis_service()
                
                genesis_key = genesis_service.create_key(
                    key_type=GenesisKeyType.ERROR,
                    what_description=f"Test failed: {test_name}",
                    who_actor="pytest",
                    where_location=str(item.fspath) if hasattr(item, 'fspath') else None,
                    why_reason="Test failure outcome for LLM knowledge update",
                    how_method="pytest_execution",
                    file_path=str(item.fspath) if hasattr(item, 'fspath') else None,
                    is_error=True,
                    error_type=error_type,
                    error_message=error_message,
                    context_data={
                        'test_name': test_name,
                        'test_module': test_module,
                        'test_class': test_class,
                        'test_function': test_function,
                        'duration_ms': duration_ms,
                        'outcome': 'failed',
                        'error_type': error_type
                    },
                    metadata={
                        'outcome_type': 'test_outcome',
                        'example_type': 'test_outcome',
                        'trust_score': 0.7,  # Medium trust - failures are still valuable for learning
                        'success': False,
                        'test_name': test_name,
                        'error_type': error_type,
                        'duration_ms': duration_ms
                    },
                    session=session
                )
            except Exception as e:
                # Don't fail tests if Genesis Key creation fails
                pass
        elif report.skipped:
            # Skip is already recorded elsewhere, but update count if needed
            pass

    elif call.when == "setup" and call.excinfo is not None:
        if call.excinfo.typename != "Skipped":
            # Setup error
            error_type = call.excinfo.typename
            error_message = str(call.excinfo.value)

            DiagnosticCollector.record_failure(
                test_name=test_name,
                error_type=f"SetupError:{error_type}",
                error_message=error_message,
                duration_ms=duration_ms,
                details={
                    **details,
                    "outcome": "setup_error",
                    "phase": "setup",
                }
            )
            _diagnostics["test_results"]["errors"] += 1


def _infer_assertions(test_function: str) -> List[str]:
    """Infer what assertions a test likely validates based on its name."""
    assertions = []
    test_lower = test_function.lower()

    # Common assertion patterns
    assertion_patterns = {
        "status": "HTTP status code validation",
        "response": "Response structure/content validation",
        "create": "Object/record creation validation",
        "get": "Data retrieval validation",
        "update": "Data modification validation",
        "delete": "Data deletion validation",
        "list": "Collection/list retrieval validation",
        "search": "Search results validation",
        "filter": "Filtering logic validation",
        "auth": "Authentication/authorization validation",
        "permission": "Permission check validation",
        "valid": "Input validation",
        "invalid": "Invalid input handling validation",
        "error": "Error handling validation",
        "exception": "Exception handling validation",
        "connection": "Connection establishment validation",
        "health": "Health check validation",
        "config": "Configuration validation",
        "timestamp": "Timestamp/datetime validation",
        "relationship": "Data relationship validation",
        "singleton": "Singleton pattern validation",
        "initialization": "Initialization validation",
        "empty": "Empty state handling validation",
        "null": "Null/None handling validation",
        "unicode": "Unicode/encoding validation",
        "injection": "Injection protection validation",
    }

    for pattern, description in assertion_patterns.items():
        if pattern in test_lower:
            assertions.append(description)

    return assertions if assertions else ["General assertion validation"]


def pytest_sessionfinish(session, exitstatus):
    """Called after test session finishes - report ALL diagnostics to GRACE for learning."""
    # Save diagnostic report
    report_path = DiagnosticCollector.save_report()

    # Try to report to GRACE
    reported = DiagnosticCollector.report_to_grace()

    # Always print summary for GRACE learning visibility
    report = DiagnosticCollector.get_report()
    summary = report["summary"]

    print("\n" + "=" * 70)
    print("GRACE TEST DIAGNOSTIC SUMMARY - Learning from ALL Outcomes")
    print("=" * 70)

    # Overall results
    print(f"\n[RESULTS] TEST RESULTS (Pass Rate: {summary['pass_rate']}%)")
    print(f"   [PASS] Passed:  {summary['total_passes']}")
    print(f"   [FAIL] Failed:  {summary['total_failures']} (Infrastructure: {summary['infrastructure_failures']}, Code: {summary['code_failures']})")
    print(f"   [SKIP] Skipped: {summary['total_skips']}")
    print(f"   [WARN] Errors:  {report['test_results']['errors']}")

    # Learning insights from passes
    if summary['total_passes'] > 0:
        print(f"\n[LEARN] LEARNING FROM SUCCESS ({summary['total_passes']} tests):")
        print(f"   Validation types working: {', '.join(summary['validation_types_working'][:5])}")
        if summary['category_pass_counts']:
            top_categories = sorted(summary['category_pass_counts'].items(),
                                    key=lambda x: x[1], reverse=True)[:5]
            print(f"   Strongest areas: {', '.join(f'{cat}({count})' for cat, count in top_categories)}")
        if summary['learned_patterns_count'] > 0:
            print(f"   Patterns learned: {summary['learned_patterns_count']}")

    # Learning insights from failures
    if summary['total_failures'] > 0:
        print(f"\n[FIX] LEARNING FROM FAILURES ({summary['total_failures']} tests):")
        if summary['infrastructure_failures'] > 0:
            print(f"   Infrastructure issues: {summary['infrastructure_failures']} (external services/deps)")
        if summary['code_failures'] > 0:
            print(f"   Code issues: {summary['code_failures']} (logic/assertion failures)")

        # Show top failure patterns
        failure_types = {}
        for f in report.get("failures", [])[:20]:
            error_type = f.get("error_type", "Unknown")
            failure_types[error_type] = failure_types.get(error_type, 0) + 1
        if failure_types:
            print(f"   Top error types: {', '.join(f'{t}({c})' for t, c in sorted(failure_types.items(), key=lambda x: x[1], reverse=True)[:3])}")

    # Missing dependencies
    if report["missing_dependencies"]:
        print(f"\n[DEPS] MISSING DEPENDENCIES ({len(report['missing_dependencies'])}):")
        for dep in sorted(report["missing_dependencies"])[:5]:
            print(f"   - {dep}")
        if len(report["missing_dependencies"]) > 5:
            print(f"   ... and {len(report['missing_dependencies']) - 5} more")

    # Suggested fixes
    if report["suggested_fixes"]:
        print(f"\n[HINT] SUGGESTED FIXES:")
        for fix in report["suggested_fixes"][:5]:
            print(f"   $ {fix}")

    # Report status
    print(f"\n[FILE] Diagnostic report: {report_path}")
    if reported:
        print("[OK] Diagnostics reported to GRACE API for autonomous learning")
    else:
        print("[NOTE] GRACE API not available - diagnostics saved locally for later learning")

    print("=" * 70)
