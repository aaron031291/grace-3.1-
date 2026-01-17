#!/usr/bin/env python3
"""
Run Both Tests - Self-Healing and Coding Agent

Runs comprehensive tests for both systems and displays results.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import subprocess
from datetime import datetime


def run_test(script_name: str, description: str):
    """Run a test script and return results."""
    print("=" * 80)
    print(f"{description.upper()}")
    print("=" * 80)
    print()
    
    script_path = project_root / "scripts" / script_name
    
    if not script_path.exists():
        print(f"ERROR: Test script not found: {script_path}")
        return None
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            # Filter out warnings we expect
            filtered_stderr = []
            for line in result.stderr.split('\n'):
                if line.strip() and not any(skip in line for skip in [
                    "Could not import",
                    "[CODING-AGENT]",
                    "[FEDERATED-LEARNING]",
                    "WARNING:",
                    "DeprecationWarning"
                ]):
                    filtered_stderr.append(line)
            
            if filtered_stderr:
                print("\nErrors:")
                print('\n'.join(filtered_stderr))
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Test timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"ERROR: Failed to run test: {e}")
        return None


def main():
    """Run both tests."""
    print("=" * 80)
    print("COMPREHENSIVE SYSTEM TESTS")
    print("=" * 80)
    print()
    print(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Coding Agent
    print()
    coding_result = run_test(
        "test_grace_code_generation.py",
        "CODING AGENT TEST"
    )
    results["coding"] = coding_result
    
    print()
    print()
    
    # Test 2: Self-Healing Training
    print()
    healing_result = run_test(
        "verify_self_healing_training.py",
        "SELF-HEALING TRAINING TEST"
    )
    results["healing"] = healing_result
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    if results.get("coding"):
        coding_success = results["coding"]["success"]
        print(f"Coding Agent Test: {'PASSED' if coding_success else 'FAILED'}")
    else:
        print("Coding Agent Test: NOT RUN")
    
    if results.get("healing"):
        healing_success = results["healing"]["success"]
        print(f"Self-Healing Test: {'PASSED' if healing_success else 'FAILED'}")
    else:
        print("Self-Healing Test: NOT RUN")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
