import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def main():
    print("========================================")
    print("  Grace 3.1 -- Starting Launcher")
    print("========================================")
    
    root_dir = Path(__file__).parent.absolute()
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    
    print("[Grace] Launching Backend Services...")
    
    # Start the FastAPI backend
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(backend_dir),
        env=dict(os.environ, PYTHONPATH=".")
    )
    
    print("[Grace] Waiting for backend to initialize (2 seconds)...")
    time.sleep(2.0)
    
    print("[Grace] Launching Frontend Interface...")
    index_path = frontend_dir / "index.html"
    
    if index_path.exists():
        webbrowser.open(index_path.as_uri())
    else:
        print(f"[Error] Could not find frontend index.html at {index_path}")
        
    print("[Grace] Close this window to stop the launcher and backend.")
    
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("[Grace] Shutting down...")
        backend_process.terminate()

if __name__ == "__main__":
    main()
