#!/usr/bin/env python3
"""
Unified GRACE Startup Script
=============================

Multi-OS startup script that works on Windows, macOS, and Linux.

Usage:
    python start_grace.py [backend|frontend|all]
    
Default: all (starts both backend and frontend)
"""

import sys
import os
from pathlib import Path

# Add backend to path for OS adapter
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from backend.utils.os_adapter import OS, paths, process, shell
from backend.utils.safe_print import safe_print


def print_header(text: str):
    """Print formatted header."""
    safe_print("=" * 70)
    safe_print(f"  {text}")
    safe_print("=" * 70)
    safe_print()


def start_backend():
    """Start backend server."""
    safe_print("[1/2] Starting Backend (FastAPI)...")
    
    backend_dir = paths.resolve("backend")
    python_exe = sys.executable
    
    # Activate virtual environment if it exists
    if OS.is_windows:
        venv_activate = paths.join(backend_dir, "venv", "Scripts", "activate.bat")
    else:
        venv_activate = paths.join(backend_dir, "venv", "bin", "activate")
    
    # Build uvicorn command
    command = [
        python_exe,
        "-m",
        "uvicorn",
        "app:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
    ]
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    safe_print("Backend server starting on http://localhost:8000")
    safe_print("API Documentation: http://localhost:8000/docs")
    safe_print()
    
    # Start backend (blocks)
    try:
        process.spawn(
            command,
            cwd=backend_dir,
            shell=False
        ).wait()
    except KeyboardInterrupt:
        safe_print("\nBackend stopped.")


def start_frontend():
    """Start frontend server."""
    safe_print("[2/2] Starting Frontend (Vite)...")
    
    frontend_dir = paths.resolve("frontend")
    
    # Find npm
    npm_path = shell.find_executable("npm")
    if not npm_path:
        safe_print("ERROR: npm not found. Please install Node.js.")
        sys.exit(1)
    
    command = [npm_path, "run", "dev"]
    
    os.chdir(frontend_dir)
    
    safe_print("Frontend server starting on http://localhost:5173")
    safe_print()
    
    # Start frontend (blocks)
    try:
        process.spawn(
            command,
            cwd=frontend_dir,
            shell=False
        ).wait()
    except KeyboardInterrupt:
        safe_print("\nFrontend stopped.")


def start_all():
    """Start both backend and frontend."""
    safe_print("Starting GRACE in full-stack mode...")
    safe_print()
    
    root_dir = Path(__file__).parent.resolve()
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    
    python_exe = sys.executable
    
    # Start backend in background
    safe_print("[1/2] Starting Backend (FastAPI)...")
    backend_command = [
        python_exe,
        "-m",
        "uvicorn",
        "app:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
    ]
    
    backend_proc = process.spawn(
        backend_command,
        cwd=str(backend_dir),
        shell=False
    )
    
    safe_print(f"Backend started (PID: {backend_proc.pid})")
    
    # Wait a moment for backend to initialize
    import time
    time.sleep(3)
    
    # Start frontend in background
    safe_print("[2/2] Starting Frontend (Vite)...")
    npm_path = shell.find_executable("npm")
    if not npm_path:
        safe_print("ERROR: npm not found. Please install Node.js.")
        process.terminate(backend_proc)
        sys.exit(1)
    
    frontend_command = [npm_path, "run", "dev"]
    
    frontend_proc = process.spawn(
        frontend_command,
        cwd=str(frontend_dir),
        shell=False
    )
    
    safe_print(f"Frontend started (PID: {frontend_proc.pid})")
    safe_print()
    
    print_header("GRACE System Started Successfully")
    safe_print("  Backend API:  http://localhost:8000")
    safe_print("  Frontend UI:  http://localhost:5173")
    safe_print("  API Docs:     http://localhost:8000/docs")
    safe_print()
    safe_print("Press Ctrl+C to stop all services.")
    safe_print()
    
    # Wait for both processes
    try:
        import time
        while backend_proc.poll() is None and frontend_proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        safe_print("\nShutting down services...")
        process.terminate(backend_proc)
        process.terminate(frontend_proc)
        safe_print("Services stopped.")


def main():
    """Main entry point."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode not in ["backend", "frontend", "all"]:
        safe_print(f"Invalid mode: {mode}")
        safe_print("Usage: python start_grace.py [backend|frontend|all]")
        sys.exit(1)
    
    print_header("GRACE System Startup")
    
    if mode == "backend":
        start_backend()
    elif mode == "frontend":
        start_frontend()
    else:
        start_all()


if __name__ == "__main__":
    main()
