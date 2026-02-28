"""
Grace Complete Launcher — ONE COMMAND starts EVERYTHING.

python grace_start.py

Starts: Docker/Qdrant → Backend → Frontend → Diagnostics
Fixes: .env, imports, ports, embedding model
Auto-restarts: if anything crashes
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

def p(icon, msg):
    print(f"  {icon} {msg}")

def header(msg):
    print(f"\n{'='*50}\n  {msg}\n{'='*50}")


def kill_ports():
    """Kill anything on our ports."""
    header("STEP 1: Clearing ports")
    for port in [8000, 5173, 5174, 5175, 6333, 6334]:
        try:
            r = subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True, text=True)
            for line in r.stdout.strip().split('\n'):
                if line.strip():
                    pid = line.split()[-1]
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True, timeout=5)
        except Exception:
            pass
    time.sleep(2)
    p("✅", "Ports cleared")


def fix_env():
    """Fix all .env issues."""
    header("STEP 2: Fixing configuration")
    env = BACKEND / ".env"
    if not env.exists():
        ex = BACKEND / ".env.example"
        if ex.exists():
            shutil.copy(ex, env)
            p("✅", "Created .env from example")

    if env.exists():
        c = env.read_text()
        fixes = [
            ("qwen_4b", "all-MiniLM-L6-v2"),
            ("api.moonshot.cn", "api.moonshot.ai"),
        ]
        for old, new in fixes:
            if old in c:
                c = c.replace(old, new)
                p("✅", f"Fixed: {old} → {new}")

        for flag in ["SKIP_EMBEDDING_LOAD=true", "SKIP_QDRANT_CHECK=false"]:
            key = flag.split("=")[0]
            if key not in c:
                c += f"\n{flag}"

        env.write_text(c)
    p("✅", "Config ready")


def fix_frontend():
    """Fix all frontend import issues."""
    header("STEP 3: Fixing frontend")
    
    components = FRONTEND / "src" / "components"
    if not components.exists():
        p("❌", "Frontend components not found")
        return

    fixed = 0
    for f in components.glob("*.jsx"):
        content = f.read_text(errors='ignore')
        uses_api = 'API_BASE_URL' in content
        has_import = "from '../config/api'" in content or 'from "../config/api"' in content

        if uses_api and not has_import:
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_idx = i + 1
            lines.insert(insert_idx, "import { API_BASE_URL } from '../config/api';")
            f.write_text('\n'.join(lines))
            fixed += 1

    if fixed:
        p("✅", f"Fixed {fixed} components with missing imports")
    else:
        p("✅", "All imports correct")

    # npm install
    os.chdir(FRONTEND)
    subprocess.run('npm install', shell=True, capture_output=True, timeout=120)
    os.chdir(ROOT)
    p("✅", "npm packages ready")


def start_qdrant():
    """Start Qdrant via Docker."""
    header("STEP 4: Starting Qdrant")

    # Check Docker
    r = subprocess.run('docker --version', shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        p("⚠️", "Docker not found — Qdrant will be skipped")
        return

    # Check if already running
    r = subprocess.run('docker ps --filter name=qdrant --format "{{.Names}}"', shell=True, capture_output=True, text=True)
    if 'qdrant' in r.stdout:
        p("✅", "Qdrant already running")
        return

    # Check if container exists but stopped
    r = subprocess.run('docker ps -a --filter name=qdrant --format "{{.Names}}"', shell=True, capture_output=True, text=True)
    if 'qdrant' in r.stdout:
        subprocess.run('docker start qdrant', shell=True, capture_output=True)
        p("✅", "Qdrant restarted")
        return

    # Create new container
    cmd = (
        'docker run -d --name qdrant '
        '-p 6333:6333 -p 6334:6334 '
        '-v qdrant_storage:/qdrant/storage '
        'qdrant/qdrant'
    )
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode == 0:
        p("✅", "Qdrant started on ports 6333/6334")
    else:
        p("⚠️", f"Qdrant failed: {r.stderr[:100]}")


def start_backend():
    """Start backend server."""
    header("STEP 5: Starting backend")
    os.chdir(BACKEND)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    p("✅", f"Backend starting (PID {proc.pid})")

    # Wait for health
    for i in range(30):
        try:
            import requests
            r = requests.get("http://localhost:8000/health", timeout=2)
            if r.status_code == 200:
                p("✅", "Backend LIVE at http://localhost:8000")
                os.chdir(ROOT)
                return proc
        except Exception:
            pass
        time.sleep(2)
        if i % 5 == 4:
            print(f"      ... waiting ({i+1}/30)")

    p("⚠️", "Backend slow — may still be loading")
    os.chdir(ROOT)
    return proc


def start_frontend():
    """Start frontend dev server."""
    header("STEP 6: Starting frontend")
    os.chdir(FRONTEND)

    proc = subprocess.Popen(
        'npm run dev -- --port 5173',
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    p("✅", f"Frontend starting (PID {proc.pid})")
    time.sleep(3)
    os.chdir(ROOT)
    return proc


def run_diagnostics():
    """Run diagnostics through the API."""
    header("STEP 7: Diagnostics")
    try:
        import requests

        # Health
        r = requests.get("http://localhost:8000/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            healthy = data.get("summary", {}).get("healthy", 0)
            total = healthy + data.get("summary", {}).get("unhealthy", 0) + data.get("summary", {}).get("degraded", 0)
            p("✅", f"Health: {healthy}/{total} services healthy")

        # Vault
        r = requests.get("http://localhost:8000/api/vault/status", timeout=10)
        if r.status_code == 200:
            for prov in r.json().get("providers", []):
                icon = "✅" if prov.get("key_configured") else "⚠️"
                p(icon, f"{prov['name']}: {prov['key_masked']}")

        # Smoke test
        r = requests.get("http://localhost:8000/api/audit/test/smoke", timeout=30)
        if r.status_code == 200:
            data = r.json()
            p("✅", f"Smoke: {data.get('passed',0)}/{data.get('passed',0)+data.get('failed',0)} checks passed")

    except Exception as e:
        p("⚠️", f"Diagnostics: {e}")


def main():
    header("GRACE — Starting Everything")
    print("  One command. Fixes problems. Starts all services.")
    print("  Press Ctrl+C to stop.\n")

    kill_ports()
    fix_env()
    fix_frontend()
    start_qdrant()
    backend = start_backend()
    frontend = start_frontend()
    run_diagnostics()

    header("GRACE IS RUNNING!")
    print("  🌐 Frontend:  http://localhost:5173")
    print("  🔧 Backend:   http://localhost:8000")
    print("  ❤️  Health:    http://localhost:8000/health")
    print("  🤖 Console:   http://localhost:8000/api/console/status")
    print("  🔑 Vault:     http://localhost:8000/api/vault/status")
    print()
    print("  Press Ctrl+C to stop Grace")

    try:
        while True:
            time.sleep(10)
            if backend.poll() is not None:
                p("❌", "Backend crashed — restarting...")
                backend = start_backend()
            if frontend.poll() is not None:
                p("❌", "Frontend crashed — restarting...")
                frontend = start_frontend()
    except KeyboardInterrupt:
        print("\n  Stopping Grace...")
        try:
            backend.terminate()
            frontend.terminate()
        except Exception:
            pass
        print("  Grace stopped.")


if __name__ == "__main__":
    main()
