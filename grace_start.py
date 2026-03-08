"""
Grace launcher — delegates to canonical startup (no redundant logic).

Single path: startup_preflight.py (self-heal + knowledge) + start.bat / start.sh staged.
Run from project root:  python grace_start.py
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print("\n  GRACE — delegating to preflight + staged runtime (no duplicate logic).\n")
    # Preflight chunk 0 (self-first) and chunk 2 (knowledge)
    for chunk in (0, 2):
        r = subprocess.run(
            [sys.executable, str(ROOT / "startup_preflight.py"), "--chunk", str(chunk)],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            sys.exit(r.returncode)
    # Staged runtime: 1st 30s ahead, 2nd 15s behind
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", str(ROOT / "start.bat"), "staged"], cwd=str(ROOT))
    else:
        subprocess.run(["bash", str(ROOT / "start.sh"), "staged"], cwd=str(ROOT))

if __name__ == "__main__":
    main()
