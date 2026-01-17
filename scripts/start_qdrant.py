#!/usr/bin/env python3
"""
Start Qdrant Service
====================
Checks Docker, starts Qdrant container, and verifies it's running.
"""

import subprocess
import time
import requests
import sys
from pathlib import Path


def check_docker_running():
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def check_qdrant_running():
    """Check if Qdrant is already running."""
    try:
        response = requests.get("http://localhost:6333/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_qdrant_container():
    """Start Qdrant container."""
    print("[INFO] Starting Qdrant container...")
    try:
        # Check if container exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=qdrant", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "qdrant" in result.stdout:
            print("[INFO] Qdrant container exists, starting it...")
            subprocess.run(
                ["docker", "start", "qdrant"],
                check=True,
                timeout=10
            )
        else:
            print("[INFO] Creating new Qdrant container...")
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "qdrant",
                    "-p", "6333:6333",
                    "-p", "6334:6334",
                    "-v", "qdrant_storage:/qdrant/storage",
                    "qdrant/qdrant"
                ],
                check=True,
                timeout=30
            )
        
        print("[OK] Qdrant container started")
        return True
    except subprocess.TimeoutExpired:
        print("[ERROR] Docker command timed out")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to start Qdrant: {e}")
        return False
    except FileNotFoundError:
        print("[ERROR] Docker not found. Please install Docker Desktop.")
        return False


def wait_for_qdrant(max_wait=30):
    """Wait for Qdrant to become available."""
    print("[INFO] Waiting for Qdrant to be ready...")
    for i in range(max_wait):
        if check_qdrant_running():
            print(f"[OK] Qdrant is ready! (took {i+1} seconds)")
            return True
        time.sleep(1)
    return False


def verify_qdrant():
    """Verify Qdrant is working."""
    try:
        response = requests.get("http://localhost:6333/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Qdrant health check: {response.json()}")
            return True
        else:
            print(f"[WARN] Qdrant returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to verify Qdrant: {e}")
        return False


def main():
    print("=" * 60)
    print("Starting Qdrant Vector Database")
    print("=" * 60)
    print()
    
    # Step 1: Check Docker
    print("[STEP 1] Checking Docker...")
    if not check_docker_running():
        print("[ERROR] Docker is not running!")
        print()
        print("Please start Docker Desktop and try again:")
        print("  1. Open Docker Desktop application")
        print("  2. Wait for it to fully start")
        print("  3. Run this script again")
        sys.exit(1)
    print("[OK] Docker is running")
    print()
    
    # Step 2: Check if Qdrant is already running
    print("[STEP 2] Checking if Qdrant is already running...")
    if check_qdrant_running():
        print("[OK] Qdrant is already running!")
        verify_qdrant()
        sys.exit(0)
    print("[INFO] Qdrant is not running")
    print()
    
    # Step 3: Start Qdrant
    print("[STEP 3] Starting Qdrant container...")
    if not start_qdrant_container():
        print()
        print("[ERROR] Failed to start Qdrant")
        sys.exit(1)
    print()
    
    # Step 4: Wait for Qdrant to be ready
    print("[STEP 4] Waiting for Qdrant to be ready...")
    if not wait_for_qdrant():
        print()
        print("[ERROR] Qdrant did not become ready in time")
        sys.exit(1)
    print()
    
    # Step 5: Verify
    print("[STEP 5] Verifying Qdrant...")
    if not verify_qdrant():
        print()
        print("[ERROR] Qdrant verification failed")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("[SUCCESS] Qdrant is running and ready!")
    print("=" * 60)
    print()
    print("Qdrant Dashboard: http://localhost:6333/dashboard")
    print("API Endpoint: http://localhost:6333")
    print()


if __name__ == "__main__":
    main()
