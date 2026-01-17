#!/usr/bin/env python3
"""
Automated Stability Verification Script
Run this script to verify Grace is definitively stable.

Usage:
    python verify_stability.py
"""

import requests
import sys
import time
from typing import Dict, List, Tuple, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 5

def check_endpoint(name: str, endpoint: str, expected_status: int = 200) -> Tuple[bool, str, Optional[Dict]]:
    """Check if an endpoint responds correctly."""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
        if response.status_code == expected_status:
            try:
                data = response.json()
                return True, "OK", data
            except:
                return True, "OK", None
        else:
            return False, f"Status {response.status_code}", None
    except requests.exceptions.ConnectionError:
        return False, "Connection refused (service not running?)", None
    except requests.exceptions.Timeout:
        return False, "Timeout", None
    except Exception as e:
        return False, str(e), None

def check_health_component(data: Dict, component_name: str) -> bool:
    """Check if a specific component in health response is healthy."""
    if "components" in data:
        components = data["components"]
        if isinstance(components, dict):
            value = components.get(component_name)
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ["healthy", "operational", "ok"]
    return False

def main():
    """Run all stability checks."""
    print("\n" + "=" * 70)
    print("GRACE SYSTEM STABILITY VERIFICATION")
    print("=" * 70)
    print()
    
    checks = [
        ("Main Health", "/grace/health", ["layer1", "trigger_pipeline", "learning_orchestrator", "memory_learner"]),
        ("System Status", "/grace/status", None),
        ("Librarian Health", "/librarian/health", None),
        ("ML Intelligence", "/ml-intelligence/status", None),
        ("Telemetry", "/telemetry/health", None),
        ("Ingestion", "/ingest/status", None),
        ("File Management", "/file-ingestion/status", None),
        ("API Health", "/health", None),
    ]
    
    all_passed = True
    failed_checks = []
    
    for name, endpoint, components in checks:
        passed, message, data = check_endpoint(name, endpoint)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name:30} {message}")
        
        # Check component health if data available
        if passed and data and components:
            for component in components:
                if not check_health_component(data, component):
                    print(f"      ⚠️  Component '{component}' not healthy")
                    passed = False
        
        if not passed:
            all_passed = False
            failed_checks.append((name, endpoint, message))
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("✅ SYSTEM IS STABLE - All checks passed!")
        print()
        print("Your Grace system is definitively stable and operational.")
    else:
        print("❌ SYSTEM UNSTABLE - Some checks failed!")
        print()
        print("Failed checks:")
        for name, endpoint, message in failed_checks:
            print(f"  - {name}: {endpoint}")
            print(f"    Error: {message}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure backend is running: python backend/app.py")
        print("  2. Check if services are accessible (Qdrant, Ollama, Database)")
        print("  3. Review logs for error messages")
        print("  4. Run: python backend/scripts/verify_grace_complete.py")
    
    print("=" * 70)
    print()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
