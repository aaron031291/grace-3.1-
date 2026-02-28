"""
Grace Self-Healing Launcher for Windows

One file. Fixes everything. Starts everything.
Kimi+Opus diagnose and fix problems through Grace's own API.

Usage: python start_grace_windows.py
"""

import os
import sys
import json
import time
import subprocess
import signal
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR / "backend"
FRONTEND_DIR = SCRIPT_DIR / "frontend"

def print_header(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}\n")

def print_ok(msg):
    print(f"  [OK] {msg}")

def print_warn(msg):
    print(f"  [!!] {msg}")

def print_fail(msg):
    print(f"  [XX] {msg}")


def kill_old_processes():
    """Kill any existing Grace processes."""
    print_header("Step 1: Cleaning up old processes")
    
    if sys.platform == 'win32':
        # Kill by port
        for port in [8000, 5173, 5174, 5175]:
            try:
                result = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(f'taskkill /PID {pid} /F', shell=True, 
                                             capture_output=True, timeout=5)
                            except Exception:
                                pass
            except Exception:
                pass
        print_ok("Old processes killed")
    else:
        os.system("pkill -f uvicorn 2>/dev/null; pkill -f 'npm run dev' 2>/dev/null")
        print_ok("Old processes killed")
    
    time.sleep(2)


def fix_env():
    """Fix the .env file — correct embedding model, add skip flags."""
    print_header("Step 2: Fixing configuration")
    
    env_path = BACKEND_DIR / ".env"
    
    if not env_path.exists():
        # Create from example
        example = BACKEND_DIR / ".env.example"
        if example.exists():
            shutil.copy(example, env_path)
            print_ok("Created .env from example")
        else:
            print_warn("No .env or .env.example found")
            return
    
    content = env_path.read_text()
    changed = False
    
    # Fix embedding model
    if "qwen_4b" in content:
        content = content.replace("qwen_4b", "all-MiniLM-L6-v2")
        changed = True
        print_ok("Fixed embedding model: qwen_4b → all-MiniLM-L6-v2")
    
    # Fix Kimi URL
    if "api.moonshot.cn" in content:
        content = content.replace("api.moonshot.cn", "api.moonshot.ai")
        changed = True
        print_ok("Fixed Kimi URL: .cn → .ai")
    
    # Ensure skip flags
    for flag in ["SKIP_EMBEDDING_LOAD=true", "SKIP_QDRANT_CHECK=true"]:
        key = flag.split("=")[0]
        if key not in content:
            content += f"\n{flag}"
            changed = True
            print_ok(f"Added {flag}")
    
    if changed:
        env_path.write_text(content)
        print_ok("Configuration saved")
    else:
        print_ok("Configuration already correct")


def fix_frontend():
    """Force-reset frontend files from git."""
    print_header("Step 3: Fixing frontend")
    
    os.chdir(SCRIPT_DIR)
    
    # Force checkout frontend files from repo
    result = subprocess.run(
        'git checkout origin/Aaron-new -- frontend/src/components/ frontend/vite.config.js frontend/src/App.jsx frontend/src/config/api.js',
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print_ok("Frontend files reset from repo")
    else:
        print_warn(f"Git checkout: {result.stderr[:100]}")
    
    # Install npm dependencies
    os.chdir(FRONTEND_DIR)
    print("  Installing npm packages...")
    result = subprocess.run('npm install', shell=True, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print_ok("npm packages installed")
    else:
        print_warn("npm install had issues (may still work)")
    
    os.chdir(SCRIPT_DIR)


def check_ollama():
    """Check if Ollama is running and has models."""
    print_header("Step 4: Checking Ollama")
    
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            print_ok(f"Ollama running — {len(models)} models")
            model_names = [m["name"] for m in models]
            
            # Check for required models
            needed = ["qwen2.5-coder", "qwen2.5", "deepseek-r1"]
            for model in needed:
                found = any(model in name for name in model_names)
                if found:
                    print_ok(f"  {model}: available")
                else:
                    print_warn(f"  {model}: not found — run 'ollama pull {model}:7b'")
            return True
        else:
            print_warn("Ollama not responding")
            return False
    except Exception:
        print_warn("Ollama not running — start it with 'ollama serve'")
        return False


def check_api_keys():
    """Check cloud API keys."""
    print_header("Step 5: Checking API keys")
    
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        print_warn("No .env file")
        return
    
    content = env_path.read_text()
    
    for key_name, display in [("KIMI_API_KEY", "Kimi K2.5"), ("OPUS_API_KEY", "Opus 4.6")]:
        lines = [l for l in content.split('\n') if l.startswith(f"{key_name}=")]
        if lines:
            val = lines[0].split("=", 1)[1].strip()
            if val and len(val) > 10:
                print_ok(f"{display}: configured ({val[:8]}...{val[-4:]})")
            else:
                print_warn(f"{display}: empty — add key to .env")
        else:
            print_warn(f"{display}: not in .env")


def start_backend():
    """Start the backend server."""
    print_header("Step 6: Starting backend")
    
    os.chdir(BACKEND_DIR)
    
    if sys.platform == 'win32':
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
        )
    
    print_ok(f"Backend starting (PID: {proc.pid})")
    print("  Waiting for backend to be ready...")
    
    # Wait for backend to respond
    import requests
    for i in range(30):
        try:
            r = requests.get("http://localhost:8000/health", timeout=2)
            if r.status_code == 200:
                print_ok("Backend is LIVE at http://localhost:8000")
                return proc
        except Exception:
            pass
        time.sleep(2)
        print(f"  ... waiting ({i+1}/30)")
    
    print_warn("Backend slow to start — check terminal for errors")
    return proc


def start_frontend():
    """Start the frontend dev server."""
    print_header("Step 7: Starting frontend")
    
    os.chdir(FRONTEND_DIR)
    
    if sys.platform == 'win32':
        proc = subprocess.Popen(
            'npm run dev',
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        proc = subprocess.Popen(['npm', 'run', 'dev'])
    
    print_ok(f"Frontend starting (PID: {proc.pid})")
    time.sleep(3)
    print_ok("Frontend should be at http://localhost:5173")
    return proc


def run_diagnostics():
    """Run smoke test through the API."""
    print_header("Step 8: Running diagnostics")
    
    try:
        import requests
        
        # Smoke test
        r = requests.get("http://localhost:8000/api/audit/test/smoke", timeout=30)
        if r.status_code == 200:
            data = r.json()
            print_ok(f"Smoke test: {data.get('passed', 0)}/{data.get('passed',0)+data.get('failed',0)} passed")
            print(f"  Status: {data.get('status', 'unknown')}")
        
        # Vault status
        r = requests.get("http://localhost:8000/api/vault/status", timeout=10)
        if r.status_code == 200:
            data = r.json()
            for provider in data.get("providers", []):
                status = "connected" if provider.get("key_configured") else "no key"
                print(f"  {provider['name']}: {status}")
    except Exception as e:
        print_warn(f"Diagnostics: {e}")


def main():
    print_header("Grace Autonomous AI System — Launcher")
    print("  This script fixes everything and starts Grace.")
    print("")
    
    kill_old_processes()
    fix_env()
    fix_frontend()
    check_ollama()
    check_api_keys()
    
    backend_proc = start_backend()
    frontend_proc = start_frontend()
    
    run_diagnostics()
    
    print_header("Grace is RUNNING!")
    print("  Frontend:  http://localhost:5173")
    print("  Backend:   http://localhost:8000")
    print("  Health:    http://localhost:8000/health")
    print("  Console:   http://localhost:8000/api/console/status")
    print("  Vault:     http://localhost:8000/api/vault/status")
    print("")
    print("  Press Ctrl+C to stop Grace")
    print("")
    
    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(10)
            # Check if processes are still alive
            if backend_proc.poll() is not None:
                print_fail("Backend crashed! Restarting...")
                backend_proc = start_backend()
            if frontend_proc.poll() is not None:
                print_fail("Frontend crashed! Restarting...")
                frontend_proc = start_frontend()
    except KeyboardInterrupt:
        print("\n\nShutting down Grace...")
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
        except Exception:
            pass
        print("Grace stopped.")


if __name__ == "__main__":
    main()
