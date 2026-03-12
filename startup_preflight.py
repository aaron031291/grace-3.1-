"""
Startup Preflight — self-heal BEFORE runtime. Run in chunks.

Usage:
  python startup_preflight.py --chunk 0   REM Self-first: kill ports, fix .env, fix frontend (no venv)
  python startup_preflight.py --chunk 1   REM Optional: deterministic scan + auto-fix (needs backend venv)
  python startup_preflight.py --chunk 2   REM Apply startup knowledge from last run's error

Exit: 0 = OK, 1 = critical failure (chunk 0 should always fix and retry; chunk 1 may exit 1)
"""

import os
import sys
import re
import json
import time
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"
ERROR_FILE = DATA / "last_startup_error.txt"
KNOWLEDGE_FILE = ROOT / "startup_knowledge.json"
LEARNING_FILE = DATA / "startup_learning.json"
SUCCESS_FILE = DATA / "startup_success.txt"

# Ensure data dir exists
DATA.mkdir(exist_ok=True)

# Max age of success file to consider "last run succeeded" (seconds)
SUCCESS_FILE_MAX_AGE = 600


def log(icon: str, msg: str) -> None:
    try:
        print(f"  {icon} {msg}")
    except UnicodeEncodeError:
        # Windows cp1252 can't encode emoji; use ASCII
        print(f"  [*] {msg}")


def header(msg: str) -> None:
    print(f"\n{'='*60}\n  {msg}\n{'='*60}\n")


# ─── Chunk 0: Self-first (no backend venv) ───────────────────────────────

def chunk0_kill_ports() -> bool:
    """Free ports 8000, 5173, 5174, 5175, 6333, 6334."""
    header("Preflight Chunk 0: Clearing ports")
    log("🔧", "Closing any process on Grace ports (8000, 5173, 6333, ...)")
    try:
        for port in [8000, 5173, 5174, 5175, 6333, 6334]:
            if sys.platform == "win32":
                r = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True, timeout=5
                )
                for line in (r.stdout or "").strip().splitlines():
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True, timeout=5)
            else:
                subprocess.run(f"lsof -ti:{port} | xargs -r kill -9", shell=True, capture_output=True, timeout=5)
        time.sleep(2)
        log("✅", "Ports cleared")
        return True
    except Exception as e:
        log("⚠️", f"Port cleanup: {e}")
        return True  # non-fatal


def chunk0_fix_env() -> bool:
    """Fix .env: create from example, fix known bad values, add skip flags."""
    log("🔧", "Checking backend .env")
    env = BACKEND / ".env"
    example = BACKEND / ".env.example"
    if not env.exists() and example.exists():
        shutil.copy(example, env)
        log("✅", "Created .env from .env.example")
    if not env.exists():
        log("⚠️", "No .env found; backend may prompt for config")
        return True
    content = env.read_text(encoding="utf-8", errors="replace")
    changes = []
    # Known fixes (from past errors)
    fixes = [
        ("qwen_4b", "all-MiniLM-L6-v2"),
        ("api.moonshot.cn", "api.moonshot.ai"),
    ]
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            changes.append(f"{old} → {new}")
    for flag in ["SKIP_EMBEDDING_LOAD=false", "SKIP_QDRANT_CHECK=false"]:
        key = flag.split("=")[0]
        if key not in content:
            content = content.rstrip() + "\n" + flag + "\n"
            changes.append(f"Added {flag}")
    if changes:
        env.write_text(content, encoding="utf-8")
        for c in changes:
            log("✅", c)
    else:
        log("✅", ".env OK")
    return True


def chunk0_fix_frontend() -> bool:
    """Ensure frontend has API import and npm install."""
    log("🔧", "Checking frontend")
    components = FRONTEND / "src" / "components"
    if not components.exists():
        log("⚠️", "Frontend components not found")
        return True
    fixed = 0
    for f in components.glob("*.jsx"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if "API_BASE_URL" in content and "config/api" not in content:
                lines = content.split("\n")
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith(("import ", "from ")):
                        insert_idx = i + 1
                if insert_idx < len(lines) and "config/api" not in "\n".join(lines[:insert_idx]):
                    lines.insert(insert_idx, "import { API_BASE_URL } from '../config/api';")
                    f.write_text("\n".join(lines), encoding="utf-8")
                    fixed += 1
        except Exception:
            pass
    if fixed:
        log("✅", f"Fixed {fixed} component(s) missing API import")
    else:
        log("✅", "Frontend imports OK")
    # npm install
    try:
        subprocess.run(
            "npm install",
            shell=True, cwd=FRONTEND, capture_output=True, timeout=120
        )
        log("✅", "npm packages ready")
    except Exception as e:
        log("⚠️", f"npm install: {e}")
    return True


def run_chunk0() -> int:
    """Self-first: ports, env, frontend. No venv required."""
    chunk0_kill_ports()
    chunk0_fix_env()
    chunk0_fix_frontend()
    return 0


# ─── Chunk 1: Deterministic scan + auto-fix (needs backend venv) ──────────

def run_chunk1() -> int:
    """Run deterministic bridge scan and auto-fix from backend. Optional."""
    header("Preflight Chunk 1: Deterministic scan (backend venv)")
    if not (BACKEND / "app.py").exists():
        log("⚠️", "Backend not found; skip chunk 1")
        return 0
    venv_python = BACKEND / "venv_gpu" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = BACKEND / "venv_gpu" / "bin" / "python"
    if not venv_python.exists():
        venv_python = BACKEND / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = BACKEND / "venv" / "bin" / "python"
    if not venv_python.exists():
        log("⚠️", "No venv found; skip deterministic scan")
        return 0
    script = BACKEND / "scripts" / "_preflight_deterministic.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "from core.deterministic_bridge import build_deterministic_report, DeterministicAutoFixer\n"
        "r = build_deterministic_report()\n"
        "p = r.get('problems', [])\n"
        "fixer = DeterministicAutoFixer()\n"
        "fixes = fixer.auto_fix(p) if p else []\n"
        "print('Problems:', len(p), 'Auto-fixes applied:', len(fixes))\n",
        encoding="utf-8"
    )
    try:
        r = subprocess.run(
            [str(venv_python), str(script)],
            cwd=str(BACKEND), capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            log("⚠️", (r.stderr or r.stdout or "Deterministic scan failed")[:200])
            return 0
        out = (r.stdout or "").strip()
        if out:
            log("✅", out)
        return 0
    except Exception as e:
        log("⚠️", f"Chunk 1: {e}")
        return 0
    finally:
        try:
            script.unlink(missing_ok=True)
        except Exception:
            pass


# ─── Self-learning state ──────────────────────────────────────────────────

def load_learning() -> dict:
    if not LEARNING_FILE.exists():
        return {"last_error": None, "last_applied_fix": None, "history": []}
    try:
        return json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_error": None, "last_applied_fix": None, "history": []}


def save_learning(state: dict) -> None:
    try:
        LEARNING_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_applied_fix(error_snippet: str, applied_fix: str) -> None:
    """Record that we applied a fix for this error (for later learning)."""
    state = load_learning()
    state["last_error"] = (error_snippet or "")[:500]
    state["last_applied_fix"] = applied_fix
    state["history"] = (state.get("history") or [])[-99:]
    state["history"].append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "error_snippet": (error_snippet or "")[:200],
        "applied_fix": applied_fix,
        "outcome": "unknown",
    })
    save_learning(state)


def record_timeout(error_snippet: str) -> None:
    """Record that startup timed out (ghost calls this or we read from ERROR_FILE)."""
    state = load_learning()
    state["history"] = (state.get("history") or [])[-99:]
    state["history"].append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "error_snippet": (error_snippet or "")[:200],
        "outcome": "timeout",
    })
    save_learning(state)


# ─── Chunk 2: Startup knowledge (apply fixes from last error) ──────────────

def load_knowledge() -> list:
    if not KNOWLEDGE_FILE.exists():
        return []
    try:
        data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        return data.get("fixes", data) if isinstance(data, dict) else data
    except Exception:
        return []


def get_last_error() -> str:
    if not ERROR_FILE.exists():
        return ""
    return ERROR_FILE.read_text(encoding="utf-8", errors="replace").strip()


def apply_fix(do: str) -> bool:
    """Apply a known fix by id or command."""
    do = (do or "").strip().lower()
    if do == "kill_ports":
        chunk0_kill_ports()
        return True
    if do == "fix_env":
        chunk0_fix_env()
        return True
    if do == "fix_frontend":
        chunk0_fix_frontend()
        return True
    if do and not do.startswith(" "):
        log("🔧", f"Custom fix: {do[:60]}")
        try:
            subprocess.run(do, shell=True, cwd=str(ROOT), timeout=30)
            return True
        except Exception as e:
            log("⚠️", str(e))
    return False


def run_chunk2() -> int:
    """Apply startup knowledge from last_run error."""
    header("Preflight Chunk 2: Startup knowledge")
    last = get_last_error()
    if not last:
        log("✅", "No previous error to fix")
        return 0
    log("📋", f"Last error: {last[:120]}...")
    fixes = load_knowledge()
    applied = 0
    for rule in fixes:
        when = rule.get("when") or rule.get("match") or ""
        do = rule.get("do") or rule.get("fix") or ""
        if not when or not do:
            continue
        if when in last or (isinstance(when, str) and re.search(when, last, re.I)):
            log("🔧", f"Applying: when '{when[:40]}...' -> do '{do}'")
            if apply_fix(do):
                applied += 1
                record_applied_fix(last, do)
    if applied:
        log("✅", f"Applied {applied} fix(es) from knowledge")
        try:
            ERROR_FILE.write_text("", encoding="utf-8")
        except Exception:
            pass
    else:
        if last:
            record_timeout(last)
        log("✅", "No matching knowledge fix" if not last else "No matching rule; recorded for learning")
    return 0


# ─── Chunk 3: Learn from success (add new rules when last run succeeded) ───

def run_chunk3() -> int:
    """If previous run succeeded after we applied a fix, add that (error, fix) as a new rule."""
    header("Preflight Chunk 3: Self-learning from success")
    if not SUCCESS_FILE.exists():
        log("✅", "No recent success file; nothing to learn")
        return 0
    try:
        mtime = SUCCESS_FILE.stat().st_mtime
        if (time.time() - mtime) > SUCCESS_FILE_MAX_AGE:
            log("✅", "Success file too old; skip learning")
            return 0
    except Exception:
        return 0
    state = load_learning()
    last_err = state.get("last_error") or ""
    last_fix = state.get("last_applied_fix") or ""
    if not last_err or not last_fix:
        log("✅", "No error+fix pair to learn")
        try:
            SUCCESS_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return 0
    fixes = load_knowledge()
    when_snippet = last_err[:120].strip()
    exists = any(
        (r.get("when") or "").strip() in when_snippet or when_snippet in (r.get("when") or "").strip()
        for r in fixes if isinstance(r, dict))
    if exists:
        log("✅", "Rule already in knowledge")
    else:
        new_rule = {"when": when_snippet, "do": last_fix}
        if isinstance(fixes, list):
            fixes.append(new_rule)
        else:
            fixes = [new_rule]
        try:
            data = {}
            if KNOWLEDGE_FILE.exists():
                data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {"fixes": list(data) if isinstance(data, list) else []}
            data.setdefault("fixes", [])
            data["fixes"].append(new_rule)
            KNOWLEDGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            log("📚", f"Learned new rule: when '{when_snippet[:50]}...' -> do '{last_fix}'")
        except Exception as e:
            log("⚠️", f"Could not save new rule: {e}")
    state["last_error"] = None
    state["last_applied_fix"] = None
    save_learning(state)
    try:
        SUCCESS_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Startup preflight in chunks")
    ap.add_argument("--chunk", type=int, default=0, choices=[0, 1, 2, 3], help="0=self-first, 1=deterministic, 2=knowledge, 3=learn from success")
    args = ap.parse_args()
    if args.chunk == 0:
        return run_chunk0()
    if args.chunk == 1:
        return run_chunk1()
    if args.chunk == 2:
        return run_chunk2()
    return run_chunk3()


if __name__ == "__main__":
    sys.exit(main())
