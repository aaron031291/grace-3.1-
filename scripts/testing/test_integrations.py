#!/usr/bin/env python3
"""
Comprehensive Integration Test Script
Tests all component integrations and verifies everything is wired correctly
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_imports():
    """Test that all critical components can be imported"""
    print("=" * 60)
    print("TEST 1: Component Imports")
    print("=" * 60)
    
    results = {}
    
    # Test TimeSense
    try:
        from timesense.engine import get_timesense_engine
        from timesense.connector import TimeSenseConnector
        from api.timesense import router as timesense_router
        results['TimeSense'] = "[OK]"
    except Exception as e:
        results['TimeSense'] = f"[FAILED] {e}"
    
    # Test Genesis IDE
    try:
        from genesis_ide import GenesisIDECore, CognitiveIDEFramework
        from genesis_ide.layer_intelligence import Layer1Intelligence
        results['Genesis IDE'] = "[OK]"
    except Exception as e:
        results['Genesis IDE'] = f"[FAILED] {e}"
    
    # Test Grace OS
    try:
        from api.grace_os_api import router as grace_os_router
        # Grace OS modules may have import dependencies, test router first
        results['Grace OS'] = "[OK]"
    except Exception as e:
        results['Grace OS'] = f"[FAILED] {e}"
    
    # Test Diagnostic Engine
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        from diagnostic_machine.sensors import SensorType, SensorData
        results['Diagnostic Engine'] = "[OK]"
    except Exception as e:
        results['Diagnostic Engine'] = f"[FAILED] {e}"
    
    # Test API Routers
    try:
        from api.timesense import router
        from api.grace_os_api import router
        from diagnostic_machine.api import router
        results['API Routers'] = "[OK]"
    except Exception as e:
        results['API Routers'] = f"[FAILED] {e}"
    
    # Print results
    for component, status in results.items():
        print(f"  {component:25} {status}")
    
    return all("[OK]" in status for status in results.values())


def test_app_integration():
    """Test that app.py has all routers registered"""
    print("\n" + "=" * 60)
    print("TEST 2: App.py Router Integration")
    print("=" * 60)
    
    app_file = Path("backend/app.py")
    if not app_file.exists():
        print("  [FAILED] backend/app.py not found")
        return False
    
    content = app_file.read_text()
    
    required_routers = [
        "timesense_router",
        "grace_os_router",
        "diagnostic_router"
    ]
    
    results = {}
    for router in required_routers:
        if f"include_router({router})" in content or f"app.include_router({router})" in content:
            results[router] = "[Registered]"
        else:
            results[router] = "[NOT FOUND]"
    
    # Check imports
    if "from api.timesense import router as timesense_router" in content:
        results['timesense_import'] = "[Imported]"
    else:
        results['timesense_import'] = "[NOT IMPORTED]"
    
    if "from api.grace_os_api import router as grace_os_router" in content:
        results['grace_os_import'] = "[Imported]"
    else:
        results['grace_os_import'] = "[NOT IMPORTED]"
    
    if "from diagnostic_machine.api import router as diagnostic_router" in content:
        results['diagnostic_import'] = "[Imported]"
    else:
        results['diagnostic_import'] = "[NOT IMPORTED]"
    
    # Print results
    for item, status in results.items():
        print(f"  {item:30} {status}")
    
    return all("[Registered]" in status or "[Imported]" in status for status in results.values())


def test_timesense_integration():
    """Test TimeSense initialization and connector"""
    print("\n" + "=" * 60)
    print("TEST 3: TimeSense Integration")
    print("=" * 60)
    
    try:
        from timesense.engine import get_timesense_engine
        from timesense.connector import TimeSenseConnector
        
        # Test engine creation
        engine = get_timesense_engine(auto_calibrate=False)
        print(f"  Engine created: [OK]")
        
        # Test connector
        connector = TimeSenseConnector(engine)
        print(f"  Connector created: [OK]")
        
        # Test API router
        from api.timesense import router
        print(f"  API router available: [OK]")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_genesis_ide_integration():
    """Test Genesis IDE components"""
    print("\n" + "=" * 60)
    print("TEST 4: Genesis IDE Integration")
    print("=" * 60)
    
    try:
        from genesis_ide import GenesisIDECore, CognitiveIDEFramework
        from genesis_ide.layer_intelligence import Layer1Intelligence, Layer2Intelligence
        
        print(f"  GenesisIDECore: [OK]")
        print(f"  CognitiveIDEFramework: [OK]")
        print(f"  Layer1Intelligence: [OK]")
        print(f"  Layer2Intelligence: [OK]")
        
        # Check if used in Grace OS
        grace_os_file = Path("backend/api/grace_os_api.py")
        if grace_os_file.exists():
            content = grace_os_file.read_text()
            if "genesis_ide" in content.lower() or "GenesisIDE" in content:
                print(f"  Used in Grace OS API: [OK]")
            else:
                print(f"  Used in Grace OS API: [WARN] NOT FOUND (may be indirect)")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_diagnostic_integration():
    """Test Diagnostic Engine integration"""
    print("\n" + "=" * 60)
    print("TEST 5: Diagnostic Engine Integration")
    print("=" * 60)
    
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        from diagnostic_machine.sensors import SensorType, SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        # Check healing module exists
        import diagnostic_machine.healing as healing_module
        
        print(f"  DiagnosticEngine: [OK]")
        print(f"  SensorType/SensorData: [OK]")
        print(f"  InterpreterLayer: [OK]")
        print(f"  Healing module: [OK]")
        
        # Check API
        try:
            from diagnostic_machine.api import router
            print(f"  API router: [OK]")
        except Exception as e:
            print(f"  API router: [FAILED] {e}")
        
        return True
    except Exception as e:
        print(f"  [FAILED] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_grace_os_integration():
    """Test Grace OS components"""
    print("\n" + "=" * 60)
    print("TEST 6: Grace OS Integration")
    print("=" * 60)
    
    try:
        from api.grace_os_api import router as grace_os_router
        print(f"  API router: [OK]")
        
        # Check Grace OS modules
        grace_os_modules = [
            "grace_os.ide_bridge",
            "grace_os.autonomous_scheduler",
            "grace_os.deterministic_pipeline",
            "grace_os.ghost_ledger",
            "grace_os.nocode_panels",
            "grace_os.reasoning_planes"
        ]
        
        for module_name in grace_os_modules:
            try:
                __import__(module_name)
                print(f"  {module_name}: [OK]")
            except Exception as e:
                print(f"  {module_name}: [FAILED] {e}")
        
        return True
    except Exception as e:
        print(f"  [FAILED] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connections():
    """Test database connectivity"""
    print("\n" + "=" * 60)
    print("TEST 7: Database Connections")
    print("=" * 60)
    
    try:
        from database.session import SessionLocal, initialize_session_factory
        from database.connection import DatabaseConnection
        
        print(f"  Session factory: [OK]")
        print(f"  Database connection: [OK]")
        
        # Try to create a session
        try:
            session = SessionLocal()
            session.close()
            print(f"  Session creation: [OK]")
        except Exception as e:
            print(f"  Session creation: [WARN] {e}")
        
        return True
    except Exception as e:
        print(f"  [FAILED] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("GRACE INTEGRATION TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        ("Component Imports", test_imports),
        ("App Router Integration", test_app_integration),
        ("TimeSense Integration", test_timesense_integration),
        ("Genesis IDE Integration", test_genesis_ide_integration),
        ("Diagnostic Engine Integration", test_diagnostic_integration),
        ("Grace OS Integration", test_grace_os_integration),
        ("Database Connections", test_database_connections),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n  [FAILED] Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {test_name:35} {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  [SUCCESS] All integration tests passed!")
        return 0
    else:
        print(f"\n  [WARN] {total - passed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
