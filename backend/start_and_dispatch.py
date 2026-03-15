"""Start backend in background thread, wait for ready, then dispatch 50 tasks."""
import sys, os, time, threading, subprocess

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["DISABLE_PROACTIVE_HEALING"] = "true"
os.environ["SKIP_AUTO_INGESTION"] = "true"
os.environ["SKIP_EMBEDDING_LOAD"] = "true"
os.environ["DISABLE_CONTINUOUS_LEARNING"] = "true"
os.environ["DISABLE_SPINDLE_DAEMON"] = "true"

# Start uvicorn in a background thread within this process
def run_server():
    import uvicorn
    sys.path.insert(0, ".")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="warning", timeout_keep_alive=120)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for ready
import requests
for i in range(60):
    time.sleep(2)
    try:
        r = requests.get("http://localhost:8000/health/live", timeout=5)
        if r.ok:
            print(f"Backend READY after {(i+1)*2}s")
            break
    except:
        if i % 5 == 0:
            print(f"Waiting... ({(i+1)*2}s)")
else:
    print("Backend failed to start in 120s")
    sys.exit(1)

# Now dispatch
print("=" * 90)
exec(open("dispatch_50_tasks.py").read())
