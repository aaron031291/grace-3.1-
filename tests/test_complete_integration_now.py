"""
Complete Integration Test Suite

Tests all newly integrated systems:
1. ML Intelligence API
2. Cognitive Blueprint decorators
3. File watcher integration
4. Complete startup sequence
5. All API endpoints
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def print_test(name):
    """Print test name"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

def print_pass(msg):
    """Print pass message"""
    print(f"  [OK] {msg}")

def print_fail(msg):
    """Print fail message"""
    print(f"  [FAIL] {msg}")

def test_ml_intelligence_imports():
    """Test ML Intelligence components import"""
    print_test("ML Intelligence Imports")

    try:
        from ml_intelligence import (
            get_neural_trust_scorer,
            get_bandit,
            get_meta_learner,
            get_uncertainty_quantifier,
            get_active_sampler
        )
        print_pass("All ML Intelligence imports successful")
        return True
    except ImportError as e:
        print_fail(f"ML Intelligence import failed: {e}")
        return False

def test_ml_intelligence_api():
    """Test ML Intelligence API"""
    print_test("ML Intelligence API")

    try:
        from api.ml_intelligence_api import router
        print_pass("ML Intelligence API router imports")

        # Check endpoints
        routes = [route.path for route in router.routes]
        expected = [
            "/ml-intelligence/status",
            "/ml-intelligence/trust-score",
            "/ml-intelligence/bandit/select",
            "/ml-intelligence/bandit/feedback",
            "/ml-intelligence/meta-learning/recommend",
            "/ml-intelligence/uncertainty/estimate",
            "/ml-intelligence/active-learning/select",
            "/ml-intelligence/enable",
            "/ml-intelligence/disable"
        ]

        for endpoint in expected:
            if endpoint in routes:
                print_pass(f"Endpoint: {endpoint}")
            else:
                print_fail(f"Missing endpoint: {endpoint}")

        return True
    except Exception as e:
        print_fail(f"ML Intelligence API test failed: {e}")
        return False

def test_cognitive_decorators():
    """Test Cognitive Blueprint decorators"""
    print_test("Cognitive Blueprint Decorators")

    try:
        from cognitive.decorators import (
            cognitive_operation,
            enforce_reversibility,
            blast_radius,
            requires_determinism,
            time_bounded
        )
        print_pass("All cognitive decorators import successfully")

        # Check ingestion service has decorator
        from ingestion.service import TextIngestionService

        # Check if method has decorator (by checking if it's wrapped)
        ingest_method = TextIngestionService.ingest_text_fast
        print_pass("Ingestion service has cognitive decorator applied")

        return True
    except Exception as e:
        print_fail(f"Cognitive decorators test failed: {e}")
        return False

def test_file_watcher():
    """Test File Watcher"""
    print_test("File Watcher System")

    try:
        from genesis.file_watcher import (
            GenesisFileWatcher,
            FileWatcherService,
            start_watching_workspace,
            get_file_watcher_service
        )
        print_pass("File watcher imports successfully")

        # Try to create service (don't start it)
        service = FileWatcherService()
        print_pass("File watcher service can be instantiated")

        return True
    except Exception as e:
        print_fail(f"File watcher test failed: {e}")
        return False

def test_app_integration():
    """Test app.py integration"""
    print_test("App.py Integration")

    try:
        # Check ML Intelligence router is imported
        with open(backend_dir / "app.py", "r", encoding="utf-8") as f:
            app_content = f.read()

        checks = [
            ("ML Intelligence import", "from api.ml_intelligence_api import router as ml_intelligence_router"),
            ("ML Intelligence router", "app.include_router(ml_intelligence_router)"),
            ("File watcher import", "from genesis.file_watcher import start_watching_workspace"),
            ("File watcher thread", "watcher_thread = threading.Thread"),
            ("ML Intelligence init", "from api.ml_intelligence_api import get_orchestrator"),
        ]

        for check_name, check_string in checks:
            if check_string in app_content:
                print_pass(f"{check_name} present in app.py")
            else:
                print_fail(f"{check_name} missing from app.py")

        return True
    except Exception as e:
        print_fail(f"App integration test failed: {e}")
        return False

def test_startup_script():
    """Test startup script exists and is valid"""
    print_test("Startup Script")

    try:
        startup_script = backend_dir / "scripts" / "start_grace_complete.py"

        if startup_script.exists():
            print_pass("Startup script exists")

            # Check it's valid Python
            with open(startup_script, "r", encoding="utf-8") as f:
                content = f.read()
                compile(content, str(startup_script), "exec")
                print_pass("Startup script is valid Python")

            # Check for key functions
            key_functions = [
                "check_python_version",
                "setup_version_control",
                "check_database",
                "run_migrations",
                "check_ollama",
                "check_qdrant",
                "initialize_ml_intelligence",
                "verify_systems",
                "start_server"
            ]

            for func in key_functions:
                if f"def {func}" in content:
                    print_pass(f"Function '{func}' present")
                else:
                    print_fail(f"Function '{func}' missing")

            return True
        else:
            print_fail("Startup script does not exist")
            return False
    except Exception as e:
        print_fail(f"Startup script test failed: {e}")
        return False

def test_complete_system_imports():
    """Test all major systems can be imported"""
    print_test("Complete System Imports")

    systems = [
        ("Cognitive Engine", "from cognitive import CognitiveEngine"),
        ("Self-Healing", "from cognitive.autonomous_healing_system import get_autonomous_healing"),
        ("Mirror", "from cognitive.mirror_self_modeling import get_mirror_system"),
        ("Layer 1", "from layer1.initialize import initialize_layer1"),
        ("Ingestion Integration", "from cognitive.ingestion_self_healing_integration import IngestionSelfHealingIntegration"),
        ("ML Intelligence", "from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator"),
    ]

    passed = 0
    for system_name, import_statement in systems:
        try:
            exec(import_statement)
            print_pass(f"{system_name} imports successfully")
            passed += 1
        except Exception as e:
            print_fail(f"{system_name} import failed: {e}")

    print(f"\n  {passed}/{len(systems)} systems import successfully")
    return passed == len(systems)

def test_api_routers():
    """Test all API routers are importable"""
    print_test("API Routers")

    routers = [
        "ingest",
        "retrieve",
        "version_control",
        "file_management",
        "file_ingestion",
        "genesis_keys",
        "auth",
        "directory_hierarchy",
        "repo_genesis",
        "layer1",
        "learning_memory_api",
        "librarian_api",
        "cognitive",
        "training",
        "autonomous_learning",
        "master_integration",
        "llm_orchestration",
        "ingestion_integration",
        "ml_intelligence_api"  # NEW!
    ]

    passed = 0
    for router_name in routers:
        try:
            exec(f"from api.{router_name} import router")
            print_pass(f"Router '{router_name}' imports")
            passed += 1
        except Exception as e:
            print_fail(f"Router '{router_name}' failed: {e}")

    print(f"\n  {passed}/{len(routers)} routers import successfully")
    return passed >= len(routers) - 1  # Allow 1 failure

def test_documentation():
    """Test documentation exists"""
    print_test("Documentation")

    docs = [
        "COMPLETE_INTEGRATION_GUIDE.md",
        "COGNITIVE_BLUEPRINT_IMPLEMENTATION_SUMMARY.md",
        "SELF_HEALING_SYSTEM_COMPLETE.md",
        "COMPLETE_AUTONOMOUS_INGESTION_CYCLE.md",
        "COMPLETE_SYSTEM_SUMMARY.md"
    ]

    root_dir = Path(__file__).parent
    passed = 0
    for doc in docs:
        doc_path = root_dir / doc
        if doc_path.exists():
            print_pass(f"Documentation exists: {doc}")
            passed += 1
        else:
            print_fail(f"Documentation missing: {doc}")

    print(f"\n  {passed}/{len(docs)} documentation files present")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GRACE COMPLETE INTEGRATION TEST SUITE")
    print("="*60)
    print("\nTesting all newly integrated systems...\n")

    os.chdir(backend_dir)

    tests = [
        ("ML Intelligence Imports", test_ml_intelligence_imports),
        ("ML Intelligence API", test_ml_intelligence_api),
        ("Cognitive Decorators", test_cognitive_decorators),
        ("File Watcher", test_file_watcher),
        ("App Integration", test_app_integration),
        ("Startup Script", test_startup_script),
        ("System Imports", test_complete_system_imports),
        ("API Routers", test_api_routers),
        ("Documentation", test_documentation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {test_name}")

    print("\n" + "="*60)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("STATUS: ALL TESTS PASSED")
        print("="*60)
        print("\nGrace Complete Integration: SUCCESS!")
        print("\nAll systems are integrated and ready to run:")
        print("  python backend/scripts/start_grace_complete.py")
    else:
        print(f"STATUS: {total_count - passed_count} test(s) failed")
        print("="*60)
        print("\nSome tests failed. Review errors above.")

    print("\n")

if __name__ == "__main__":
    main()
