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
    "skips": [],
    "import_errors": [],
    "missing_dependencies": set(),
    "suggested_fixes": [],
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

# Diagnostic report path
DIAGNOSTIC_REPORT_PATH = backend_dir / "tests" / "diagnostic_report.json"


class DiagnosticCollector:
    """Collects diagnostic information about test skips and failures."""

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

    @classmethod
    def record_skip(cls, test_name: str, reason: str, details: Optional[Dict] = None):
        """Record a test skip with diagnostic information."""
        skip_info = {
            "test": test_name,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
            "suggested_fix": cls._get_suggested_fix(reason)
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
        """Get the full diagnostic report."""
        report = _diagnostics.copy()
        report["missing_dependencies"] = list(_diagnostics["missing_dependencies"])
        report["summary"] = {
            "total_skips": len(_diagnostics["skips"]),
            "total_import_errors": len(_diagnostics["import_errors"]),
            "missing_dependency_count": len(_diagnostics["missing_dependencies"]),
            "has_critical_issues": len(_diagnostics["import_errors"]) > 0,
            "environment_ready": _app_available
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
        """Attempt to report diagnostics back to GRACE API."""
        report = cls.get_report()

        # Only report if there are issues
        if report["summary"]["total_skips"] == 0 and report["summary"]["total_import_errors"] == 0:
            return True

        try:
            import httpx
            # Try to report to local GRACE instance
            response = httpx.post(
                "http://localhost:8000/test/diagnostics",
                json=report,
                timeout=5.0
            )
            return response.status_code == 200
        except Exception:
            # If GRACE isn't running, save locally
            cls.save_report()
            return False


def _try_import_app():
    """Try to import the FastAPI app, handling missing dependencies gracefully."""
    global _app_available, _app
    import_chain = []

    try:
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
    if app is None:
        DiagnosticCollector.record_skip(
            test_name=request.node.name if hasattr(request, 'node') else "client_fixture",
            reason="App not available for test client"
        )
        pytest.skip("Full app dependencies not available")
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="function")
def test_db(request):
    """Create a test database session."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from models.database_models import Base

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


def pytest_runtest_makereport(item, call):
    """Hook to capture test results for diagnostics."""
    if call.when == "call":
        if call.excinfo is None:
            _diagnostics["test_results"]["passed"] += 1
        elif call.excinfo.typename == "Skipped":
            # Already recorded in fixture
            pass
        else:
            _diagnostics["test_results"]["failed"] += 1
    elif call.when == "setup" and call.excinfo is not None:
        if call.excinfo.typename != "Skipped":
            _diagnostics["test_results"]["errors"] += 1


def pytest_sessionfinish(session, exitstatus):
    """Called after test session finishes - report diagnostics to GRACE."""
    # Save diagnostic report
    report_path = DiagnosticCollector.save_report()

    # Try to report to GRACE
    reported = DiagnosticCollector.report_to_grace()

    # Print summary if there were issues
    report = DiagnosticCollector.get_report()
    if report["summary"]["total_skips"] > 0 or report["summary"]["total_import_errors"] > 0:
        print("\n" + "=" * 60)
        print("GRACE TEST DIAGNOSTIC SUMMARY")
        print("=" * 60)
        print(f"Tests Passed:  {report['test_results']['passed']}")
        print(f"Tests Failed:  {report['test_results']['failed']}")
        print(f"Tests Skipped: {report['test_results']['skipped']}")
        print(f"Setup Errors:  {report['test_results']['errors']}")

        if report["missing_dependencies"]:
            print(f"\nMissing Dependencies ({len(report['missing_dependencies'])}):")
            for dep in sorted(report["missing_dependencies"]):
                print(f"  - {dep}")

        if report["suggested_fixes"]:
            print(f"\nSuggested Fixes:")
            for fix in report["suggested_fixes"]:
                print(f"  $ {fix}")

        print(f"\nDiagnostic report saved to: {report_path}")
        if reported:
            print("Diagnostics reported to GRACE API for learning.")
        else:
            print("GRACE API not available - diagnostics saved locally.")
        print("=" * 60)
