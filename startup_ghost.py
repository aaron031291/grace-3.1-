"""
Startup Ghost — parallel watcher. Runs while runtime starts; checks /health in real time.

Usage:
  python startup_ghost.py [--timeout 90] [--interval 10]

Exits 0 when backend responds 200 at /health within timeout; writes startup_success.txt for self-learning.
Exits 1 on timeout; writes last_startup_error.txt so next preflight chunk 2 can apply knowledge.
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ERROR_FILE = DATA / "last_startup_error.txt"
SUCCESS_FILE = DATA / "startup_success.txt"
LEARNING_FILE = DATA / "startup_learning.json"
DATA.mkdir(exist_ok=True)

def check_health(url: str = "http://localhost:8000/health", timeout: float = 5) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Ghost: wait for backend /health")
    ap.add_argument("--timeout", type=int, default=90, help="Max seconds to wait")
    ap.add_argument("--interval", type=int, default=10, help="Seconds between checks")
    args = ap.parse_args()
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if check_health():
            try:
                SUCCESS_FILE.write_text(
                    datetime.utcnow().isoformat() + "Z",
                    encoding="utf-8"
                )
            except Exception:
                pass
            print("  [GHOST] Backend healthy. (Success recorded for self-learning.)")
            return 0
        time.sleep(min(args.interval, max(0, deadline - time.time())))
    err_msg = "Backend did not become healthy within {}s. Try: run preflight (chunk 0), then start backend in a new window.".format(args.timeout)
    try:
        ERROR_FILE.write_text(err_msg, encoding="utf-8")
    except Exception:
        pass
    try:
        import json
        state = {"last_error": None, "last_applied_fix": None, "history": []}
        if LEARNING_FILE.exists():
            try:
                state = json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        state.setdefault("history", [])
        state["history"] = (state["history"] or [])[-99:]
        state["history"].append({
            "ts": datetime.utcnow().isoformat() + "Z",
            "error_snippet": err_msg[:200],
            "outcome": "timeout",
        })
        LEARNING_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass
    print("  [GHOST] Timeout — backend not ready. Last error saved for next startup knowledge.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
