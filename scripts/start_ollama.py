#!/usr/bin/env python3
"""
Start Ollama Service
====================
Checks if Ollama is running, starts it if needed, and verifies it's active.
"""

import subprocess
import time
import requests
import sys
import os
import platform


def check_ollama_running():
    """Check if Ollama is already running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def find_ollama_executable():
    """Find Ollama executable."""
    # Check common locations
    possible_paths = [
        "ollama",
        r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.getenv("USERNAME")),
        r"C:\Program Files\Ollama\ollama.exe",
        os.path.expanduser("~/AppData/Local/Programs/Ollama/ollama.exe"),
    ]
    
    # Check if in PATH
    try:
        result = subprocess.run(
            ["where", "ollama"] if platform.system() == "Windows" else ["which", "ollama"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    # Check common paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def start_ollama():
    """Start Ollama service."""
    print("[INFO] Starting Ollama service...")
    
    ollama_path = find_ollama_executable()
    if not ollama_path:
        print("[ERROR] Ollama executable not found!")
        print()
        print("Please install Ollama:")
        print("  Windows: Download from https://ollama.com/download")
        print("  Or run: winget install Ollama.Ollama")
        return False
    
    print(f"[INFO] Found Ollama at: {ollama_path}")
    
    # Check if already running as service
    if check_ollama_running():
        print("[OK] Ollama is already running as a service")
        return True
    
    # On Windows, Ollama runs as a service, so we just need to start the service
    if platform.system() == "Windows":
        try:
            # Try to start Ollama service
            result = subprocess.run(
                ["net", "start", "ollama"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("[OK] Ollama service started")
                return True
            else:
                # Service might not be installed or already running
                print("[INFO] Attempting to run Ollama directly...")
                # Run Ollama in background
                subprocess.Popen(
                    [ollama_path, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                print("[OK] Ollama process started")
                return True
        except Exception as e:
            print(f"[ERROR] Failed to start Ollama: {e}")
            return False
    else:
        # Unix-like systems
        try:
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[OK] Ollama process started")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to start Ollama: {e}")
            return False


def wait_for_ollama(max_wait=30):
    """Wait for Ollama to become available."""
    print("[INFO] Waiting for Ollama to be ready...")
    for i in range(max_wait):
        if check_ollama_running():
            print(f"[OK] Ollama is ready! (took {i+1} seconds)")
            return True
        time.sleep(1)
    return False


def verify_ollama():
    """Verify Ollama is working."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"[OK] Ollama is running with {len(models)} model(s)")
            if models:
                print(f"     Models: {', '.join([m.get('name', 'unknown')[:20] for m in models[:3]])}")
            return True
        else:
            print(f"[WARN] Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to verify Ollama: {e}")
        return False


def main():
    print("=" * 60)
    print("Starting Ollama LLM Service")
    print("=" * 60)
    print()
    
    # Step 1: Check if already running
    print("[STEP 1] Checking if Ollama is already running...")
    if check_ollama_running():
        print("[OK] Ollama is already running!")
        verify_ollama()
        sys.exit(0)
    print("[INFO] Ollama is not running")
    print()
    
    # Step 2: Start Ollama
    print("[STEP 2] Starting Ollama...")
    if not start_ollama():
        print()
        print("[ERROR] Failed to start Ollama")
        print()
        print("Manual start instructions:")
        print("  1. Install Ollama from https://ollama.com/download")
        print("  2. Or run: winget install Ollama.Ollama")
        print("  3. Start Ollama (it usually runs as a Windows service)")
        sys.exit(1)
    print()
    
    # Step 3: Wait for Ollama to be ready
    print("[STEP 3] Waiting for Ollama to be ready...")
    if not wait_for_ollama():
        print()
        print("[ERROR] Ollama did not become ready in time")
        print("[INFO] Ollama may be starting in the background. Check manually:")
        print("  curl http://localhost:11434/api/tags")
        sys.exit(1)
    print()
    
    # Step 4: Verify
    print("[STEP 4] Verifying Ollama...")
    if not verify_ollama():
        print()
        print("[ERROR] Ollama verification failed")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("[SUCCESS] Ollama is running and ready!")
    print("=" * 60)
    print()
    print("Ollama API: http://localhost:11434")
    print()


if __name__ == "__main__":
    main()
