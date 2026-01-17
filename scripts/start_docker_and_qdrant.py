#!/usr/bin/env python3
"""
Start Docker and Qdrant
=======================
Attempts to start Docker Desktop, then starts Qdrant container.
"""

import subprocess
import time
import sys
import os
from pathlib import Path


def find_docker_desktop():
    """Find Docker Desktop executable."""
    possible_paths = [
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
        os.path.expanduser(r"~\AppData\Local\Docker\Docker Desktop.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def is_docker_running():
    """Check if Docker is running."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def start_docker_desktop():
    """Attempt to start Docker Desktop."""
    docker_path = find_docker_desktop()
    if not docker_path:
        print("[ERROR] Docker Desktop not found in common locations")
        print()
        print("Please manually start Docker Desktop:")
        print("  1. Search for 'Docker Desktop' in Start Menu")
        print("  2. Open Docker Desktop")
        print("  3. Wait for it to fully start (whale icon in system tray)")
        return False
    
    print(f"[INFO] Found Docker Desktop at: {docker_path}")
    print("[INFO] Starting Docker Desktop...")
    
    try:
        # Start Docker Desktop
        subprocess.Popen([docker_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[OK] Docker Desktop starting...")
        print("[INFO] Waiting for Docker to be ready (this may take 30-60 seconds)...")
        
        # Wait for Docker to start
        max_wait = 90
        for i in range(max_wait):
            if is_docker_running():
                print(f"[OK] Docker is ready! (took {i+1} seconds)")
                return True
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"[INFO] Still waiting... ({i+1}/{max_wait} seconds)")
        
        print("[WARN] Docker did not become ready in time")
        print("[INFO] Docker may still be starting in the background")
        return False
        
    except Exception as e:
        print(f"[ERROR] Failed to start Docker Desktop: {e}")
        return False


def start_qdrant():
    """Start Qdrant container using Docker."""
    print()
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
        print("[ERROR] Docker not found")
        return False


def wait_for_qdrant(max_wait=30):
    """Wait for Qdrant to become available."""
    import requests
    
    print("[INFO] Waiting for Qdrant to be ready...")
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:6333/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Qdrant is ready! (took {i+1} seconds)")
                return True
        except:
            pass
        time.sleep(1)
    return False


def verify_qdrant():
    """Verify Qdrant is working."""
    import requests
    
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
    print("Starting Docker Desktop and Qdrant")
    print("=" * 60)
    print()
    
    # Step 1: Check if Docker is already running
    print("[STEP 1] Checking if Docker is running...")
    if is_docker_running():
        print("[OK] Docker is already running!")
    else:
        print("[INFO] Docker is not running")
        print()
        
        # Step 2: Try to start Docker Desktop
        print("[STEP 2] Attempting to start Docker Desktop...")
        if not start_docker_desktop():
            print()
            print("[ERROR] Could not start Docker Desktop automatically")
            print()
            print("Please manually start Docker Desktop:")
            print("  1. Open Docker Desktop from Start Menu")
            print("  2. Wait for it to fully start")
            print("  3. Run this script again, or run: python scripts/start_qdrant.py")
            sys.exit(1)
        print()
    
    # Step 3: Start Qdrant
    print("[STEP 3] Starting Qdrant...")
    if not start_qdrant():
        print()
        print("[ERROR] Failed to start Qdrant")
        sys.exit(1)
    print()
    
    # Step 4: Wait for Qdrant to be ready
    print("[STEP 4] Waiting for Qdrant to be ready...")
    if not wait_for_qdrant():
        print()
        print("[ERROR] Qdrant did not become ready in time")
        print("[INFO] Check manually: curl http://localhost:6333/health")
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
