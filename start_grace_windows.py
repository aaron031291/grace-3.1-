"""
Grace launcher for Windows — delegates to canonical startup (no redundant logic).

Single path: startup_preflight.py + start.bat staged.
Usage: python start_grace_windows.py
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print("\n  GRACE (Windows) — preflight + staged runtime.\n")
    for chunk in (0, 2):
        r = subprocess.run(
            [sys.executable, str(ROOT / "startup_preflight.py"), "--chunk", str(chunk)],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            sys.exit(r.returncode)
    subprocess.run(["cmd", "/c", str(ROOT / "start.bat"), "staged"], cwd=str(ROOT))

if __name__ == "__main__":
    main()
