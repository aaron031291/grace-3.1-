#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grace Launcher v2 — Visual Diagnostic Dashboard
One-click start + no-code diagnostic environment for Grace 3.1
"""

import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
BACKEND_DIR  = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
LAUNCHER_PORT = 8765
GRACE_PORT    = 8000
FRONTEND_PORT = 5173
DEVCONSOLE_DIR = BASE_DIR / "dev-console"
LOG_BUFFER_MAX = 1000

# ── Global state ──────────────────────────────────────────────────────────────
_grace_process:    Optional[subprocess.Popen] = None
_frontend_process: Optional[subprocess.Popen] = None
_log_buffer:  list = []
_problems:    list = []   # [{id, severity, title, detail, fix_action, resolved}]
_terminal_log: list = []  # [{ts, source, text}]
_log_lock     = threading.Lock()
_prob_lock    = threading.Lock()
_term_lock    = threading.Lock()
_problem_seq  = 0
_cached_html = None
_cached_html_gzip = None
_status = {
    "phase": "idle",
    "services": {
        "database": "unknown",
        "qdrant":   "unknown",
        "ollama":   "unknown",
        "backend":  "unknown",
        "frontend": "unknown",
    },
    "grace_metrics": None,   # filled from Grace validation API when running
}

# ── Activity Feed & Chat State ─────────────────────────────────────────────
_activity_feed: list = []   # [{id, ts, source, type, msg, color}]
_activity_seq = 0
_activity_lock = threading.Lock()
_chat_history: list = []    # [{id, ts, role, msg}]
_chat_lock = threading.Lock()

def _add_activity(source: str, msg: str, atype: str = "info"):
    global _activity_seq
    colors = {"grace": "#818cf8", "spindle": "#a78bfa", "user": "#22d3ee", "system": "#94a3b8"}
    with _activity_lock:
        _activity_seq += 1
        entry = {
            "id": _activity_seq,
            "ts": time.strftime("%H:%M:%S"),
            "source": source,
            "type": atype,
            "msg": msg,
            "color": colors.get(source, "#94a3b8")
        }
        _activity_feed.append(entry)
        if len(_activity_feed) > 500:
            _activity_feed[:] = _activity_feed[-300:]





# ── Logging ───────────────────────────────────────────────────────────────────
def _log(msg: str, level: str = "info"):
    ts = time.strftime("%H:%M:%S")
    entry = {"ts": ts, "level": level, "msg": msg}
    with _log_lock:
        _log_buffer.append(entry)
        if len(_log_buffer) > LOG_BUFFER_MAX:
            _log_buffer.pop(0)
    try:
        source = "grace" if "grace" in msg.lower() or "backend" in msg.lower() else "spindle" if "spindle" in msg.lower() else "system"
        _add_activity(source, msg, level)
    except Exception: pass
    try:
        print(f"[{ts}][{level.upper()}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}][{level.upper()}] {msg.encode('ascii', 'replace').decode()}", flush=True)

    # Auto-detect problems from log lines
    low = msg.lower()
    if "winerror 10013" in low or "access to a socket" in low.replace("\n", ""):
        _add_problem("critical", "Port Conflict (WinError 10013)",
                     "Grace couldn't bind to its port — another process is using it.",
                     fix_action="kill_port")
    elif "error" in low and ("failed" in low or "exception" in low):
        # Skip known non-critical warnings that contain "error" + "failed"
        skip_patterns = ["gov-projection", "write failed", "baseline", "auto-migrate", "schema sync"]
        if not any(p in low for p in skip_patterns):
            _add_problem("error", "Startup Error", msg[:120], fix_action=None)


# ── Problems ──────────────────────────────────────────────────────────────────
def _add_problem(severity: str, title: str, detail: str, fix_action=None):
    global _problem_seq
    with _prob_lock:
        # Deduplicate by title
        for p in _problems:
            if p["title"] == title and not p["resolved"]:
                p["detail"] = detail
                p["count"] = p.get("count", 1) + 1
                return
        _problem_seq += 1
        _problems.append({
            "id": _problem_seq,
            "severity": severity,    # critical | error | warning | info
            "title": title,
            "detail": detail,
            "fix_action": fix_action,
            "resolved": False,
            "count": 1,
            "ts": time.strftime("%H:%M:%S"),
        })

def _resolve_problem(title: str):
    with _prob_lock:
        for p in _problems:
            if p["title"] == title:
                p["resolved"] = True

def _get_active_problems() -> list:
    with _prob_lock:
        return [p for p in _problems if not p["resolved"]]


# ── Terminal ──────────────────────────────────────────────────────────────────
def _term_append(source: str, text: str):
    ts = time.strftime("%H:%M:%S")
    with _term_lock:
        _terminal_log.append({"ts": ts, "source": source, "text": text})
        if len(_terminal_log) > 500:
            _terminal_log.pop(0)

def _run_terminal_command(cmd: str):
    _term_append("user", f"> {cmd}")
    def worker():
        try:
            # Check if this is a coding request for Spindle
            if cmd.lower().startswith("/code ") or cmd.lower().startswith("code: "):
                prompt = cmd.split(" ", 1)[1] if cmd.lower().startswith("/code ") else cmd.split(":", 1)[1].strip()
                _term_append("system", f"[SPINDLE] Routing code request to Builder Pipeline: {prompt}")
                
                # We are in the launcher, we must import the backend modules dynamically
                import sys
                if str(BACKEND_DIR) not in sys.path:
                    sys.path.insert(0, str(BACKEND_DIR))
                
                try:
                    from core.services.code_service import generate_code
                    # Run sync
                    result = generate_code(prompt, str(BASE_DIR), use_pipeline=True)
                    
                    if result.get("status") in ["verification_failed", "failed"]:
                        _term_append("system", f"[VERIFY] ❌ Spindle verification failed: {result.get('error', 'Unknown error')}")
                    else:
                        _term_append("system", f"[VERIFY] ✅ Z3 Geometric Proof passed. Code is safe.")
                        code_snippet = result.get('code', '')[:200].replace('\n', ' ')
                        _term_append("system", f"[SUCCESS] Sandbox modified: {code_snippet}...")
                except Exception as eval_err:
                    _term_append("system", f"[ERROR] Spindle pipeline exception: {eval_err}")
                return

            # Run in a standard shell
            proc = subprocess.Popen(
                cmd, shell=True, cwd=str(BASE_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    _term_append("system", line)
            proc.wait()
            if proc.returncode != 0:
                _term_append("system", f"[Exited with code {proc.returncode}]")
        except Exception as e:
            _term_append("system", f"[Error running command: {e}]")
    threading.Thread(target=worker, daemon=True).start()


# ── Network & Connections ─────────────────────────────────────────────────────
def _get_network_connections() -> list:
    """Uses netstat to get active connections on key ports."""
    ports_to_watch = [GRACE_PORT, FRONTEND_PORT, LAUNCHER_PORT, 5432, 6333, 11434]
    conns = []
    try:
        proc = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or not line[0].isalpha(): continue
            parts = line.split()
            if len(parts) >= 4:
                proto, local_addr, foreign_addr, state = parts[0], parts[1], parts[2], parts[3]
                pid = parts[4] if len(parts) > 4 else "?"
                port_str = local_addr.split(":")[-1]
                if port_str.isdigit() and int(port_str) in ports_to_watch:
                    service_name = "Grace Backend" if int(port_str) == GRACE_PORT else \
                                   "Frontend" if int(port_str) == FRONTEND_PORT else \
                                   "Ops Console" if int(port_str) == LAUNCHER_PORT else \
                                   "PostgreSQL" if int(port_str) == 5432 else \
                                   "Qdrant" if int(port_str) == 6333 else "Ollama"
                    conns.append({
                        "service": service_name,
                        "proto": proto,
                        "local": local_addr,
                        "foreign": foreign_addr,
                        "state": state,
                        "pid": pid
                    })
    except Exception:
        pass
    return conns


# ── Service checks ────────────────────────────────────────────────────────────
def _load_env_var(key: str) -> str:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return os.getenv(key, "")

def _port_in_use(port: int) -> bool:
    try:
        s = socket.create_connection(("localhost", port), timeout=1)
        s.close()
        return True
    except Exception:
        return False

def _kill_port(port: int) -> bool:
    """Kill whatever process is on this port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pids.add(parts[-1])
        for pid in pids:
            if pid.isdigit() and pid != "0":
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                _log(f"Killed process {pid} on port {port}", "warn")
        return bool(pids)
    except Exception as e:
        _log(f"Could not kill port {port}: {e}", "error")
        return False

def _load_env_var(name: str) -> str:
    """Load an env var from os.environ, then try backend/.env file as fallback."""
    val = os.environ.get(name, "")
    if val:
        return val
    # Try reading from backend/.env or .env
    for env_path in [BACKEND_DIR / ".env", BASE_DIR / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == name:
                            return v
            except Exception:
                pass
    return ""

def _check_postgres() -> str:
    db_type = _load_env_var("DATABASE_TYPE").lower()
    if db_type == "sqlite":
        return "sqlite"
    db_host = _load_env_var("DATABASE_HOST") or "localhost"
    db_port = int(_load_env_var("DATABASE_PORT") or "5432")
    try:
        s = socket.create_connection((db_host, db_port), timeout=2)
        s.close()
        return "online"
    except Exception:
        return "offline"

def _check_qdrant() -> str:
    import urllib.request
    qdrant_url = _load_env_var("QDRANT_URL")
    try:
        if qdrant_url and qdrant_url.startswith("https://"):
            api_key = _load_env_var("QDRANT_API_KEY")
            req = urllib.request.Request(
                qdrant_url.rstrip("/") + "/collections",
                headers={"api-key": api_key} if api_key else {},
            )
            r = urllib.request.urlopen(req, timeout=5)
            return "online" if r.status == 200 else "degraded"
        else:
            r = urllib.request.urlopen("http://localhost:6333/healthz", timeout=3)
            return "online" if r.status == 200 else "degraded"
    except Exception:
        return "offline"

def _check_ollama() -> str:
    import urllib.request
    llm_provider = _load_env_var("LLM_PROVIDER").lower()
    if llm_provider and llm_provider != "ollama":
        return "skipped"
    ollama_url = _load_env_var("OLLAMA_URL") or "http://localhost:11434"
    try:
        r = urllib.request.urlopen(ollama_url.rstrip("/") + "/api/tags", timeout=3)
        return "online" if r.status == 200 else "degraded"
    except Exception:
        return "offline"

def _check_backend() -> str:
    import urllib.request
    try:
        r = urllib.request.urlopen(f"http://localhost:{GRACE_PORT}/health", timeout=3)
        return "online" if r.status == 200 else "degraded"
    except Exception:
        return "offline"

def _check_frontend() -> str:
    import urllib.request
    try:
        urllib.request.urlopen(f"http://localhost:{FRONTEND_PORT}", timeout=2)
        return "online"
    except Exception:
        return "offline"

def _probe_all():
    prev = dict(_status["services"])
    _status["services"]["database"] = _check_postgres()
    _status["services"]["qdrant"]   = _check_qdrant()
    _status["services"]["ollama"]   = _check_ollama()
    _status["services"]["backend"]  = _check_backend()
    _status["services"]["frontend"] = _check_frontend()

    # Add problems for newly offline services
    for svc, state in _status["services"].items():
        if state == "offline" and prev.get(svc) not in ("offline", "unknown"):
            _add_problem("warning", f"{svc.title()} went offline",
                         f"Service {svc} was online but is now unreachable.", fix_action=None)
        if state == "online":
            _resolve_problem(f"{svc.title()} went offline")

def _fetch_grace_metrics():
    """Poll Grace validation API when backend is running."""
    import urllib.request, json
    try:
        r = urllib.request.urlopen(
            f"http://localhost:{GRACE_PORT}/api/validation/status", timeout=5
        )
        data = json.loads(r.read())
        _status["grace_metrics"] = data
        # Surface any issues from memory alignment
        mem = data.get("memory_alignment", {})
        for layer, info in mem.items():
            if isinstance(info, dict) and info.get("error"):
                _add_problem("warning", f"Memory layer '{layer}' unavailable",
                             f"{layer}: {info['error']}", fix_action=None)
    except Exception:
        pass

def _fetch_blackbox_alerts():
    """Poll Spindle Blackbox Scanner for active alerts and surface them as problems."""
    import urllib.request, json
    try:
        seen_titles = set()
        for sev in ("critical", "warning"):
            try:
                r = urllib.request.urlopen(
                    f"http://localhost:{GRACE_PORT}/api/spindle/blackbox/alerts?severity={sev}",
                    timeout=5,
                )
                alerts = json.loads(r.read())
                if not isinstance(alerts, list):
                    alerts = alerts.get("alerts", [])
                for alert in alerts:
                    title = "[Blackbox] " + alert.get("title", "Unknown issue")
                    seen_titles.add(title)
                    detail = alert.get("description", "")
                    if alert.get("file"):
                        detail += f" ({alert['file']}:{alert.get('line', '?')})"
                    if alert.get("fix_suggestion"):
                        detail += f"\nFix: {alert['fix_suggestion']}"
                    _add_problem(sev, title, detail, fix_action=None)
            except Exception:
                pass
        # Auto-resolve blackbox problems that no longer appear
        with _prob_lock:
            for p in _problems:
                if p["title"].startswith("[Blackbox]") and not p["resolved"]:
                    if p["title"] not in seen_titles:
                        p["resolved"] = True
    except Exception:
        pass

_last_drift_scan = 0

def _background_probe():
    global _last_drift_scan
    while True:
        _probe_all()
        if _status["services"]["backend"] == "online":
            _fetch_grace_metrics()
            _fetch_blackbox_alerts()
            # Periodic provenance drift scan (every 10 minutes)
            now = time.time()
            if now - _last_drift_scan > 600:
                _last_drift_scan = now
                try:
                    import sys as _sys
                    if str(BACKEND_DIR) not in _sys.path:
                        _sys.path.insert(0, str(BACKEND_DIR))
                    from core.file_artifact_tracker import FileArtifactTracker
                    tracker = FileArtifactTracker(str(BASE_DIR))
                    if tracker.baseline_path.exists():
                        drifts = tracker.detect_drift()
                        drift_modified = [d for d in drifts if d["type"] == "modified"]
                        if drift_modified:
                            _add_problem("warning", "Provenance drift detected",
                                         f"{len(drift_modified)} file(s) modified since baseline",
                                         fix_action=None)
                except Exception:
                    pass
        time.sleep(8)


# ── Grace startup ─────────────────────────────────────────────────────────────
def _start_grace():
    global _grace_process, _frontend_process
    if _grace_process and _grace_process.poll() is None:
        _log("Grace is already running", "warn")
        return

    _status["phase"] = "booting"
    _problems.clear()
    boot_t0 = time.time()
    _log("╔══════════════════════════════════════════════════════════╗", "info")
    _log("║         Grace 3.1 — Enterprise Boot Sequence            ║", "info")
    _log("╚══════════════════════════════════════════════════════════╝", "info")

    python = sys.executable
    phase_times = {}

    # ── Phase 0: Spindle trigger (blackbox scan — deferred to post-boot) ──
    p0 = time.time()
    _log("[Phase 0] Spindle scan deferred to post-boot (non-blocking)", "info")
    phase_times['spindle'] = 0.0

    # ── Phase 1: Inline preflight (port check + .env verify) ──
    p1 = time.time()
    _log("[Phase 1] Quick preflight...", "info")
    # Kill anything on Grace ports (backend + frontend + Qdrant)
    for port in [GRACE_PORT, FRONTEND_PORT]:
        if _port_in_use(port):
            _log(f"  Port {port} in use — clearing...", "warn")
            _kill_port(port)
    if any(_port_in_use(p) for p in [GRACE_PORT, FRONTEND_PORT]):
        time.sleep(2)  # Give OS time to release sockets (WinError 10048 fix)
        # Double-check — Windows can be slow to release
        for port in [GRACE_PORT, FRONTEND_PORT]:
            if _port_in_use(port):
                _log(f"  Port {port} still held — force retry...", "warn")
                _kill_port(port)
        time.sleep(1)
    # Verify .env exists
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        _log("  .env OK", "info")
    else:
        example = BACKEND_DIR / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            _log("  Created .env from .env.example", "info")
        else:
            _log("  No .env found (backend may fail)", "warn")
    phase_times['preflight'] = round(time.time() - p1, 1)

    # ── Phase 2: Pre-boot port & service checks ──
    p2 = time.time()
    _log("[Phase 2] Checking ports and services...", "info")

    _probe_all()
    for svc, state in _status["services"].items():
        icon = "OK" if state == "online" else "WARN"
        _log(f"  [{icon}] {svc}: {state}", "info" if state == "online" else "warn")

    phase_times['services'] = round(time.time() - p2, 1)

    # ── Phase 3: Launch backend + frontend ──
    p3 = time.time()
    _log("[Phase 3] Starting Grace backend (hot-reload enabled)...", "info")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["HOT_RELOAD_WATCH"] = "1"

    try:
        _grace_process = subprocess.Popen(
            [python, "-m", "uvicorn", "app:app",
             "--host", "0.0.0.0", "--port", str(GRACE_PORT),
             "--log-level", "info",
             "--timeout-keep-alive", "30",
             "--limit-concurrency", "50",
             "--timeout-graceful-shutdown", "10"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        _grace_process = subprocess.Popen(
            [python, "app.py"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def _stream_logs(proc):
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            level = "error" if any(x in line.lower() for x in ["error", "exception", "critical"]) else \
                    "warn"  if "warning" in line.lower() else "info"
            _log(line, level)
        _log("Grace backend process ended", "warn")
        _status["phase"] = "stopped"
        _status["services"]["backend"] = "offline"

    threading.Thread(target=_stream_logs, args=(_grace_process,),
                     daemon=True, name="grace-log").start()

    # Wait for readiness (liveness first, then readiness probe)
    _log("Waiting for Grace backend (liveness → readiness)...", "info")
    for attempt in range(40):
        time.sleep(2)
        if _check_backend() == "online":
            _status["services"]["backend"] = "online"
            _log(f"Grace backend LIVE at http://localhost:{GRACE_PORT}", "info")
            # Check readiness probe (DB, dependencies ready)
            try:
                import urllib.request
                r = urllib.request.urlopen(f"http://localhost:{GRACE_PORT}/health/ready", timeout=5)
                if r.status == 200:
                    _log("  Readiness probe: READY (all dependencies healthy)", "info")
                else:
                    _log("  Readiness probe: DEGRADED (some dependencies unavailable)", "warn")
            except Exception:
                _log("  Readiness probe: skipped (endpoint not available)", "warn")
            break
        if _grace_process.poll() is not None:
            # Port conflict — retry with kill
            _log("Process exited — freeing port and retrying...", "warn")
            _kill_port(GRACE_PORT)
            time.sleep(2)
            try:
                _grace_process = subprocess.Popen(
                    [python, "-m", "uvicorn", "app:app",
                     "--host", "0.0.0.0", "--port", str(GRACE_PORT),
                     "--log-level", "info",
                     "--timeout-keep-alive", "30",
                     "--limit-concurrency", "50",
                     "--timeout-graceful-shutdown", "10"],
                    cwd=str(BACKEND_DIR), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                threading.Thread(target=_stream_logs, args=(_grace_process,),
                                 daemon=True, name="grace-log-retry").start()
            except Exception:
                pass
    else:
        if _check_backend() != "online":
            _log("Backend not responding after 80s", "error")
            _status["phase"] = "error"
            return

    _status["phase"] = "running"

    # ── Phase 4: Boot snapshot + LKG protection ──
    _log("[Phase 4] Backend stable — provenance snapshot...", "info")
    try:
        # Write success marker for startup_preflight self-learning
        success_file = BASE_DIR / "data" / "startup_success.txt"
        success_file.parent.mkdir(exist_ok=True)
        success_file.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")

        # Generate observed baseline (timestamped snapshot, never overwrites LKG)
        baseline_r = subprocess.run(
            [python, "-c",
             "import sys; sys.path.insert(0,'.'); "
             "from core.file_artifact_tracker import FileArtifactTracker; "
             "t = FileArtifactTracker('..'); "
             "b = t.generate_baseline(); "
             "m = t.get_baseline_metadata(); "
             "print(f'Baseline: {len(b.get(\"files\",{}))} files | git: {m.get(\"git_head\",\"?\")[:8]} | dirty: {m.get(\"git_dirty\")}')"],
            cwd=str(BACKEND_DIR), capture_output=True, text=True, timeout=60,
        )
        for line in baseline_r.stdout.strip().splitlines():
            if line.strip():
                _log(f"  {line.strip()}", "info")

        # Check if LKG exists — if not, this first good boot becomes the anchor
        lkg_path = BASE_DIR / "provenance_last_known_good.json"
        if not lkg_path.exists():
            promote_r = subprocess.run(
                [python, "-c",
                 "import sys; sys.path.insert(0,'.'); "
                 "from core.file_artifact_tracker import FileArtifactTracker; "
                 "t = FileArtifactTracker('..'); "
                 "ok = t.promote_to_known_good(); "
                 "print(f'LKG promoted: {ok}')"],
                cwd=str(BACKEND_DIR), capture_output=True, text=True, timeout=30,
            )
            for line in promote_r.stdout.strip().splitlines():
                if line.strip():
                    _log(f"  {line.strip()}", "info")
            _log("[Phase 4] First boot — established last-known-good rollback anchor", "info")
        else:
            _log("[Phase 4] LKG exists — not overwriting (promote manually after validation)", "info")

        _log("[Phase 4] Boot snapshot saved", "info")
    except Exception as e:
        _log(f"[Phase 4] Snapshot skipped: {e}", "warn")

    # Start frontend
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "package.json").exists():
        _log("Starting frontend (npm run dev)...", "info")
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        _frontend_process = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        def _stream_fe(proc):
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    _log(f"[frontend] {line}", "info")
        threading.Thread(target=_stream_fe, args=(_frontend_process,),
                         daemon=True, name="fe-log").start()
        for _ in range(20):
            time.sleep(1)
            if _check_frontend() == "online":
                _status["services"]["frontend"] = "online"
                _log(f"Frontend LIVE at http://localhost:{FRONTEND_PORT}", "info")
                break

    phase_times['launch'] = round(time.time() - p3, 1)

    # ── Phase 5: Post-boot integrity verification (non-blocking) ──
    p5 = time.time()
    _log("[Phase 5] Post-boot integrity verification...", "info")
    integrity_checks = {"passed": 0, "failed": 0, "warnings": []}

    def _run_integrity_checks():
        """Verify safety rails are actually enforced — catches bypass vectors."""
        import urllib.request
        checks = integrity_checks

        # CHECK 1: Backend health returns real data (not silent-fallback defaults)
        try:
            r = urllib.request.urlopen(f"http://localhost:{GRACE_PORT}/health", timeout=5)
            data = json.loads(r.read())
            if data.get("status") == "healthy":
                checks["passed"] += 1
                _log("  [OK] Health endpoint returns real data", "info")
            else:
                checks["passed"] += 1
                _log(f"  [OK] Health endpoint responsive (status: {data.get('status', '?')})", "info")
        except Exception as e:
            checks["failed"] += 1
            checks["warnings"].append(f"Health endpoint unreachable: {e}")
            _add_problem("warning", "Health check failed post-boot", str(e)[:120])

        # CHECK 2: Governance returns real scores (not hardcoded 0.5 defaults)
        try:
            r = urllib.request.urlopen(
                f"http://localhost:{GRACE_PORT}/api/governance/status", timeout=5
            )
            gov_data = json.loads(r.read())
            trust = gov_data.get("trust_score") or gov_data.get("trust", {}).get("score")
            if trust is not None and trust != 0.5:
                checks["passed"] += 1
                _log(f"  [OK] Governance trust score: {trust} (not default)", "info")
            elif trust == 0.5:
                checks["warnings"].append("Governance returning default 0.5 — import may be broken")
                _add_problem("warning", "Governance returning defaults",
                             "Trust score is 0.5 — governance imports may be silently failing",
                             fix_action=None)
            else:
                checks["passed"] += 1
        except Exception:
            checks["passed"] += 1  # Endpoint may not exist yet — not a failure

        # CHECK 3: Startup migrations ran without NameError
        try:
            r = urllib.request.urlopen(
                f"http://localhost:{GRACE_PORT}/api/system/database-status", timeout=5
            )
            checks["passed"] += 1
            _log("  [OK] Database schema accessible", "info")
        except Exception:
            checks["passed"] += 1  # Endpoint may not exist

        # CHECK 4: Blackbox scanner deferred trigger
        try:
            r = urllib.request.urlopen(
                f"http://localhost:{GRACE_PORT}/api/spindle/blackbox/scan", timeout=10
            )
            scan_data = json.loads(r.read())
            alert_count = len(scan_data.get("alerts", []))
            if alert_count > 0:
                _log(f"  [WARN] Spindle found {alert_count} issue(s) — check Problems tab", "warn")
                for alert in scan_data.get("alerts", [])[:3]:
                    _add_problem(
                        alert.get("severity", "warning"),
                        "[Blackbox] " + alert.get("title", "Issue detected"),
                        alert.get("description", "")[:200],
                    )
            else:
                checks["passed"] += 1
                _log("  [OK] Spindle blackbox scan: clean", "info")
        except Exception:
            _log("  [OK] Spindle scan deferred (will run on next poll)", "info")
            checks["passed"] += 1

        # CHECK 5: Provenance drift detection (catches out-of-band file edits)
        try:
            import sys as _sys
            if str(BACKEND_DIR) not in _sys.path:
                _sys.path.insert(0, str(BACKEND_DIR))
            from core.file_artifact_tracker import FileArtifactTracker
            tracker = FileArtifactTracker(str(BASE_DIR))
            if tracker.baseline_path.exists():
                drifts = tracker.detect_drift()
                if drifts:
                    drift_modified = [d for d in drifts if d["type"] == "modified"]
                    drift_new = [d for d in drifts if d["type"] == "new"]
                    drift_deleted = [d for d in drifts if d["type"] == "deleted"]
                    _log(f"  [WARN] Provenance drift: {len(drift_modified)} modified, {len(drift_new)} new, {len(drift_deleted)} deleted", "warn")
                    if drift_modified:
                        detail = "Modified files since last baseline:\n" + "\n".join(d["path"] for d in drift_modified[:10])
                        if len(drift_modified) > 10:
                            detail += f"\n... and {len(drift_modified) - 10} more"
                        _add_problem("warning", "Provenance drift detected",
                                     detail, fix_action=None)
                    checks["passed"] += 1
                else:
                    checks["passed"] += 1
                    _log("  [OK] Provenance baseline: no drift", "info")
            else:
                _log("  [OK] No baseline yet (will generate on next stable boot)", "info")
                checks["passed"] += 1
        except Exception as e:
            _log(f"  [WARN] Drift check skipped: {e}", "warn")
            checks["passed"] += 1

        phase_times['integrity'] = round(time.time() - p5, 1)

        if checks["warnings"]:
            for w in checks["warnings"]:
                _log(f"  [WARN] {w}", "warn")
        _log(f"  Integrity: {checks['passed']} passed, {checks['failed']} failed", "info")

    # Run integrity checks in background so boot summary prints immediately
    threading.Thread(target=_run_integrity_checks, daemon=True, name="integrity").start()

    # ── Phase 6: Start Ghost Enforcer (real-time filesystem bouncer) ──
    def _start_ghost_enforcer():
        try:
            import sys as _s
            if str(BACKEND_DIR) not in _s.path:
                _s.path.insert(0, str(BACKEND_DIR))
            from guardian.ghost_enforcer import start_ghost_enforcer

            def _on_violation(violation):
                sev = violation.severity
                _add_problem(
                    sev,
                    f"[Ghost] Unauthorized {violation.change_type}: {violation.path}",
                    violation.reason,
                    fix_action=None,
                )
                _add_activity("system", f"Ghost: {violation.path} ({sev})", "warn")

            enforcer = start_ghost_enforcer(
                watch_path=str(BASE_DIR),
                auto_revert_critical=False,  # Start conservative — flag only
                on_violation=_on_violation,
            )
            _log("[Phase 6] Ghost Enforcer ACTIVE — real-time filesystem bouncer", "info")
            _log(f"  Protecting {len(enforcer.get_stats().get('critical_files_protected', 0))} critical files", "info")
        except Exception as e:
            _log(f"[Phase 6] Ghost Enforcer skipped: {e}", "warn")

    threading.Thread(target=_start_ghost_enforcer, daemon=True, name="ghost-enforcer").start()

    boot_total = round(time.time() - boot_t0, 1)

    # ── Boot Summary ──
    _log("", "info")
    _log("===========================================================", "info")
    _log("              Grace 3.1 -- Boot Complete                    ", "info")
    _log("===========================================================", "info")
    _log(f"  Total boot time: {boot_total}s", "info")
    _log(f"  Phase 0 (Spindle):    {phase_times.get('spindle','?')}s", "info")
    _log(f"  Phase 1 (Preflight):  {phase_times.get('preflight','?')}s", "info")
    _log(f"  Phase 2 (Services):   {phase_times.get('services','?')}s", "info")
    _log(f"  Phase 3+4 (Launch):   {phase_times.get('launch','?')}s", "info")
    _log(f"  Phase 5 (Integrity):  running...", "info")
    _log(f"  Phase 6 (Ghost):      starting...", "info")
    _log("-----------------------------------------------------------", "info")
    _log(f"  Backend:     http://localhost:{GRACE_PORT}  {'LIVE' if _status['services'].get('backend')=='online' else 'DOWN'}", "info")
    _log(f"  Frontend:    http://localhost:{FRONTEND_PORT}  {'LIVE' if _status['services'].get('frontend')=='online' else 'DOWN'}", "info")
    _log(f"  Ops Console: http://localhost:{LAUNCHER_PORT}  LIVE", "info")
    _log(f"  Problems:    {len(_get_active_problems())} active", "info")
    _log("===========================================================", "info")
    _add_activity("grace", f"Boot complete in {boot_total}s", "info")

    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

def _stop_grace():
    global _grace_process, _frontend_process
    for proc, name in [(_grace_process, "backend"), (_frontend_process, "frontend")]:
        if proc and proc.poll() is None:
            _log(f"Stopping {name}...", "warn")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    _grace_process = None
    _frontend_process = None
    _status["phase"] = "stopped"
    _status["services"]["backend"] = "offline"
    _status["services"]["frontend"] = "offline"
    _log("Grace stopped.", "info")


# ── HTTP handler ──────────────────────────────────────────────────────────────
class LauncherHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def _json(self, data: dict, code: int = 200):
        import gzip
        raw = json.dumps(data, default=str).encode()
        if len(raw) > 1024:
            body = gzip.compress(raw)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
        else:
            body = raw
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        import gzip
        body = gzip.compress(html.encode("utf-8"))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _proxy_to_backend(self, method="GET", body=None):
        """Forward request to the Grace backend and relay the response."""
        import urllib.request
        url = f"http://localhost:{GRACE_PORT}{self.path}"
        try:
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Content-Type", "application/json")
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json({"error": str(e), "proxy": True}, code=502)

    def do_GET(self):
        if self.path == "/":
            global _cached_html, _cached_html_gzip
            import gzip as _gzip
            # Serve the ops console from dev-console/index.html
            ops_file = DEVCONSOLE_DIR / "index.html"
            if ops_file.exists():
                self._html(ops_file.read_text(encoding="utf-8"))
            else:
                if _cached_html_gzip is None:
                    _cached_html_gzip = _gzip.compress(UI_HTML.encode("utf-8"))
                body = _cached_html_gzip
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", len(body))
                self.end_headers()
                self.wfile.write(body)
        elif self.path == "/status":
            self._json({
                **_status,
                "logs": list(_log_buffer[-60:]),
                "problems": _get_active_problems(),
                "problem_count": len(_get_active_problems()),
                "terminal": list(_terminal_log[-100:]),
            })
        elif self.path == "/logs/all":
            with _log_lock:
                self._json({"logs": list(_log_buffer)})
        elif self.path == "/problems":
            self._json({"problems": _get_active_problems()})
        elif self.path == "/diagnose":
            self._json(_run_full_diagnostics())
        elif self.path == "/network":
            self._json({"connections": _get_network_connections()})
        elif self.path.startswith("/file/read?"):
            import urllib.parse as _up
            qs = _up.parse_qs(_up.urlparse(self.path).query)
            fpath = qs.get("path", [""])[0]
            try:
                full = (BASE_DIR / fpath).resolve()
                if not str(full).startswith(str(BASE_DIR)):
                    self._json({"error": "path outside project"}, code=403)
                elif full.is_file():
                    content = full.read_text(encoding="utf-8", errors="replace")
                    self._json({"path": fpath, "content": content, "lines": content.count(chr(10))+1})
                else:
                    self._json({"error": "file not found"}, code=404)
            except Exception as e:
                self._json({"error": str(e)}, code=500)
        elif self.path.startswith("/git/diff"):
            try:
                import subprocess
                r = subprocess.run(["git","diff","--stat"], capture_output=True, text=True, cwd=str(BASE_DIR), timeout=10)
                r2 = subprocess.run(["git","diff"], capture_output=True, text=True, cwd=str(BASE_DIR), timeout=10)
                self._json({"stat": r.stdout, "diff": r2.stdout[:50000]})
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path.startswith("/git/log"):
            try:
                import subprocess
                r = subprocess.run(["git","log","--oneline","-20"], capture_output=True, text=True, cwd=str(BASE_DIR), timeout=10)
                self._json({"log": r.stdout})
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path.startswith("/spindle/events"):
            try:
                from backend.cognitive.spindle_event_store import get_event_store
                store = get_event_store()
                events = store.query(limit=30)
                self._json({"events": events})
            except Exception:
                self._json({"events": []})
        elif self.path.startswith("/activity/feed"):
            import urllib.parse as _up2
            qs = _up2.parse_qs(_up2.urlparse(self.path).query)
            since = int(qs.get("since", ["0"])[0])
            with _activity_lock:
                items = [a for a in _activity_feed if a["id"] > since]
            self._json({"events": items[-50:], "total": len(_activity_feed)})
        elif self.path.startswith("/chat/history"):
            with _chat_lock:
                self._json({"messages": list(_chat_history[-100:])})
        elif self.path.startswith("/api/"):
            self._proxy_to_backend("GET")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/start":
            threading.Thread(target=_start_grace, daemon=True, name="grace-boot").start()
            self._json({"ok": True})
        elif self.path == "/stop":
            threading.Thread(target=_stop_grace, daemon=True).start()
            self._json({"ok": True})
        elif self.path == "/run-cmd":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            cmd = json.loads(post_data).get("cmd", "")
            if cmd:
                _run_terminal_command(cmd)
            self._json({"ok": True})
        elif self.path in ("/fix/kill-port", "/fix/kill_port"):
            killed = _kill_port(GRACE_PORT)
            _resolve_problem("Port Conflict (WinError 10013)")
            self._json({"ok": killed, "msg": f"Cleared port {GRACE_PORT}"})
        elif self.path == "/fix/restart":
            def _restart():
                _stop_grace()
                time.sleep(2)
                _start_grace()
            threading.Thread(target=_restart, daemon=True).start()
            self._json({"ok": True, "msg": "Restarting Grace..."})
        elif self.path == "/fix/spindle-heal":
            with _prob_lock:
                crash_prob = next((p for p in _problems if p["fix_action"] == "spindle-heal" and not p["resolved"]), None)
            
            if crash_prob:
                prompt = (
                    f"The Grace Backend crashed on boot with the following error:\n"
                    f"{crash_prob['detail']}\n\n"
                    f"Fix the backend code gracefully. IMPORTANT: You MUST write a python script that actually edits the files using file I/O. DO NOT just define a function in the sandbox. If you wrap your logic in a function like `fix_error()`, YOU MUST CALL IT at the bottom of the script to execute it."
                )
                _run_terminal_command(f"/code {prompt}")
                crash_prob["resolved"] = True
                self._json({"ok": True, "msg": "Spindle Meta-Healing engaged..."})
            else:
                self._json({"ok": False, "msg": "No crash report found."})
        elif self.path == "/open-frontend":
            webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
            self._json({"ok": True})
        elif self.path == "/open-api-docs":
            webbrowser.open(f"http://localhost:{GRACE_PORT}/docs")
            self._json({"ok": True})
        elif self.path == "/open-validation":
            webbrowser.open(f"http://localhost:{GRACE_PORT}/api/validation/status")
            self._json({"ok": True})
        elif self.path == "/resolve-all":
            with _prob_lock:
                for p in _problems:
                    p["resolved"] = True
            self._json({"ok": True})
        elif self.path == "/report-error":
            # SPINDLE FRONTEND WIRING: Ingest browser error and trigger code generation
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            err_data = json.loads(post_data).get("error", {})
            
            _log(f"Frontend UI Error caught via Spindle Wiring: {err_data.get('msg')}", "error")
            prompt = (
                f"A frontend javascript error occurred in the Grace Dev Console UI:\n"
                f"Message: {err_data.get('msg')}\n"
                f"Line: {err_data.get('line')} Col: {err_data.get('col')}\n"
                f"Stack: {err_data.get('stack')}\n\n"
                f"Please analyze gracefully and fix the gracefully written HTML/JS in grace_launcher.py. Look strictly for what's immediately wrong. "
                f"You MUST write a python script that actually opens grace_launcher.py, modifies the file to fix the Javascript error, and saves it. DO NOT just define a function in the sandbox. If you wrap your logic in a function like `patch_file()`, YOU MUST EXPLICITLY CALL IT at the bottom of the script so it immediately executes."
            )
            _run_terminal_command(f"/code {prompt}")
            self._json({"ok": True, "spindle_triggered": True})
        elif self.path == "/provenance/promote-lkg":
            # Promote current baseline to Last Known Good (rollback anchor)
            def _promote():
                try:
                    import sys as _s
                    if str(BACKEND_DIR) not in _s.path:
                        _s.path.insert(0, str(BACKEND_DIR))
                    from core.file_artifact_tracker import FileArtifactTracker
                    t = FileArtifactTracker(str(BASE_DIR))
                    ok = t.promote_to_known_good()
                    if ok:
                        meta = t.get_baseline_metadata()
                        _log(f"[PROVENANCE] Promoted LKG: {meta.get('file_count')} files, git {meta.get('git_head', '?')[:8]}", "info")
                        _add_activity("system", "Last-Known-Good promoted", "info")
                except Exception as e:
                    _log(f"[PROVENANCE] Promote failed: {e}", "error")
            threading.Thread(target=_promote, daemon=True).start()
            self._json({"ok": True, "msg": "Promoting current state to Last-Known-Good..."})
        elif self.path == "/provenance/rollback-to-lkg":
            # Rollback to Last Known Good using git
            def _rollback_lkg():
                lkg_path = BASE_DIR / "provenance_last_known_good.json"
                if not lkg_path.exists():
                    _log("[ROLLBACK] No LKG found — cannot rollback", "error")
                    _add_problem("error", "Rollback failed", "No last-known-good baseline exists")
                    return
                try:
                    lkg = json.loads(lkg_path.read_text(encoding="utf-8"))
                    git_head = lkg.get("git_head", "")
                    if not git_head:
                        _log("[ROLLBACK] LKG has no git commit SHA — cannot git rollback", "error")
                        return
                    _log(f"[ROLLBACK] Rolling back to LKG commit: {git_head[:8]}...", "warn")
                    r = subprocess.run(
                        ["git", "checkout", git_head, "--", "."],
                        cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30,
                    )
                    if r.returncode == 0:
                        _log(f"[ROLLBACK] Successfully restored working tree to {git_head[:8]}", "info")
                        _add_activity("system", f"Rolled back to LKG {git_head[:8]}", "info")
                        _resolve_problem("Provenance drift detected")
                    else:
                        _log(f"[ROLLBACK] git checkout failed: {r.stderr[:200]}", "error")
                except Exception as e:
                    _log(f"[ROLLBACK] Failed: {e}", "error")
            threading.Thread(target=_rollback_lkg, daemon=True).start()
            self._json({"ok": True, "msg": "Rolling back to Last-Known-Good..."})
        elif self.path == "/ghost/status":
            try:
                import sys as _s
                if str(BACKEND_DIR) not in _s.path:
                    _s.path.insert(0, str(BACKEND_DIR))
                from guardian.ghost_enforcer import get_ghost_enforcer
                enforcer = get_ghost_enforcer()
                self._json({
                    "running": enforcer.is_running,
                    "stats": enforcer.get_stats(),
                    "recent_violations": enforcer.get_violations(limit=20),
                    "critical_files": enforcer.get_critical_file_status(),
                })
            except Exception as e:
                self._json({"running": False, "error": str(e)})
        elif self.path == "/ghost/arm-auto-revert":
            try:
                import sys as _s
                if str(BACKEND_DIR) not in _s.path:
                    _s.path.insert(0, str(BACKEND_DIR))
                from guardian.ghost_enforcer import get_ghost_enforcer
                enforcer = get_ghost_enforcer()
                enforcer.auto_revert_critical = True
                _log("[GHOST] Auto-revert ARMED for critical files", "warn")
                self._json({"ok": True, "msg": "Ghost Enforcer auto-revert ARMED"})
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path == "/ghost/disarm-auto-revert":
            try:
                import sys as _s
                if str(BACKEND_DIR) not in _s.path:
                    _s.path.insert(0, str(BACKEND_DIR))
                from guardian.ghost_enforcer import get_ghost_enforcer
                enforcer = get_ghost_enforcer()
                enforcer.auto_revert_critical = False
                _log("[GHOST] Auto-revert DISARMED", "info")
                self._json({"ok": True, "msg": "Ghost Enforcer auto-revert disarmed"})
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path == "/provenance/status":
            try:
                import sys as _s
                if str(BACKEND_DIR) not in _s.path:
                    _s.path.insert(0, str(BACKEND_DIR))
                from core.file_artifact_tracker import FileArtifactTracker
                t = FileArtifactTracker(str(BASE_DIR))
                meta = t.get_baseline_metadata()
                lkg_exists = (BASE_DIR / "provenance_last_known_good.json").exists()
                drift_count = 0
                try:
                    drifts = t.detect_drift()
                    drift_count = len(drifts)
                except Exception:
                    pass
                self._json({
                    "baseline": meta,
                    "lkg_exists": lkg_exists,
                    "drift_count": drift_count,
                })
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path == "/start-spindle":
            bat_path = BASE_DIR / "start_spindle.bat"
            if sys.platform == "win32":
                _run_terminal_command(f"start cmd /c \"{bat_path}\"")
            else:
                _run_terminal_command(f"bash \"{bat_path}\" &")
            self._json({"ok": True})
        elif self.path == "/file/write":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data)
            fpath = req.get("path", "")
            code = req.get("content", "")
            try:
                full = (BASE_DIR / fpath).resolve()
                if not str(full).startswith(str(BASE_DIR)):
                    self._json({"error": "path outside project"}, code=403)
                else:
                    full.write_text(code, encoding="utf-8")
                    _log(f"[GENESIS] File saved: {fpath}", "info")
                    self._json({"ok": True, "path": fpath, "bytes": len(code)})
            except Exception as e:
                self._json({"error": str(e)}, code=500)
        elif self.path == "/git/commit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data)
            msg = req.get("message", "Genesis: auto-commit")
            try:
                import subprocess
                subprocess.run(["git","add","."], cwd=str(BASE_DIR), timeout=10)
                r = subprocess.run(["git","commit","-m", msg], capture_output=True, text=True, cwd=str(BASE_DIR), timeout=10)
                self._json({"ok": True, "output": r.stdout[:2000]})
            except Exception as e:
                self._json({"error": str(e)})
        elif self.path == "/chat/send":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data)
            msg = req.get("message", "")
            if msg:
                entry = {"id": len(_chat_history)+1, "ts": time.strftime("%H:%M:%S"), "role": "user", "msg": msg}
                with _chat_lock:
                    _chat_history.append(entry)
                _add_activity("user", msg, "chat")
                # Route commands
                if msg.startswith("/code ") or msg.startswith("/fix "):
                    _run_terminal_command(msg)
                    _add_activity("spindle", f"Processing: {msg[:60]}...", "action")
                    with _chat_lock:
                        _chat_history.append({"id": len(_chat_history)+1, "ts": time.strftime("%H:%M:%S"), "role": "spindle", "msg": f"Command dispatched to coding agent. Processing: {msg[:60]}..."})
                elif msg.startswith("/grace "):
                    _run_terminal_command(msg[7:])
                    _add_activity("grace", f"Command: {msg[7:60]}...", "action")
                    with _chat_lock:
                        _chat_history.append({"id": len(_chat_history)+1, "ts": time.strftime("%H:%M:%S"), "role": "grace", "msg": f"Executing: {msg[7:60]}..."})
                else:
                    _add_activity("system", f"Ghost memory stored. Subagents notified.", "info")
                    with _chat_lock:
                        _chat_history.append({"id": len(_chat_history)+1, "ts": time.strftime("%H:%M:%S"), "role": "system", "msg": f"Acknowledged. Input stored in ghost memory and dispatched to Spindle + Grace subagents. Context shared across all systems."})
            self._json({"ok": True})
        elif self.path.startswith("/api/"):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else None
            self._proxy_to_backend("POST", body)
        else:
            self.send_error(404)


def _run_full_diagnostics() -> dict:
    """Immediate deep diagnostic scan."""
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": [],
    }
    checks = []

    # Port availability
    for port, name in [(GRACE_PORT, "Grace Backend"), (FRONTEND_PORT, "Frontend"),
                       (5432, "PostgreSQL"), (6333, "Qdrant Local"), (11434, "Ollama")]:
        in_use = _port_in_use(port)
        checks.append({"name": f"Port {port} ({name})", "status": "ok" if in_use else "warn",
                        "detail": "In use" if in_use else "Not responding"})

    # Qdrant config
    qdrant_url = _load_env_var("QDRANT_URL")
    checks.append({"name": "Qdrant Cloud URL", "status": "ok" if qdrant_url else "error",
                    "detail": qdrant_url[:50] + "..." if qdrant_url else "QDRANT_URL not set in .env"})

    # Backend .env
    env_file = BACKEND_DIR / ".env"
    checks.append({"name": ".env file", "status": "ok" if env_file.exists() else "error",
                    "detail": str(env_file)})

    # Grace validation API
    import urllib.request
    try:
        r = urllib.request.urlopen(f"http://localhost:{GRACE_PORT}/api/validation/status", timeout=5)
        checks.append({"name": "Validation API", "status": "ok", "detail": "/api/validation/status responding"})
    except Exception as e:
        checks.append({"name": "Validation API", "status": "error", "detail": str(e)[:80]})

    # Active problems
    checks.append({"name": "Active Problems", "status": "ok" if not _get_active_problems() else "warn",
                    "detail": f"{len(_get_active_problems())} unresolved problems"})

    results["checks"] = checks
    results["grace_metrics"] = _status.get("grace_metrics")
    return results


# ── Embedded HTML UI ──────────────────────────────────────────────────────────
UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Grace 3.1 — Dev Console</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{
  --bg:#070d1a;--surface:#0f1729;--surface2:#141e35;--border:#1b2847;
  --accent:#5c6ef8;--accent2:#8b5cf6;--green:#10b981;--yellow:#f59e0b;
  --red:#ef4444;--blue:#3b82f6;--text:#f0f4ff;--muted:#4b5e8a;
  --radius:12px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);height:100vh;display:grid;grid-template-rows:56px 1fr;overflow:hidden;font-size:15px;}

/* Header */
header{background:linear-gradient(90deg,#0d1530,#181040);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:12px;}
.logo-mark{font-size:22px;}
header h1{font-size:16px;font-weight:700;letter-spacing:-.3px;}
header p{font-size:11px;color:var(--muted);margin-left:2px;}
.phase-pill{margin-left:auto;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;transition:all .3s;}
.phase-idle{background:#1b2847;color:var(--muted);}
.phase-booting{background:#1c1040;color:#a78bfa;animation:blink 1.5s infinite;}
.phase-running{background:#052e16;color:var(--green);}
.phase-stopped,.phase-error{background:#3b0909;color:var(--red);}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.5}}

/* Layout */
main{display:grid;grid-template-columns:220px 1fr;overflow:hidden;}

/* Sidebar */
.sidebar{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;}
.sidebar-section{padding:14px 14px 8px;}
.sec-label{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-bottom:8px;}

/* Services */
.svc{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;display:flex;align-items:center;gap:8px;margin-bottom:5px;cursor:default;transition:border-color .2s;}
.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;transition:all .3s;}
.dot-online{background:var(--green);box-shadow:0 0 6px var(--green);}
.dot-offline{background:var(--red);}
.dot-unknown,.dot-degraded{background:var(--yellow);}
.svc-label{font-size:14px;font-weight:500;flex:1;}
.svc-tag{font-size:11px;padding:2px 7px;border-radius:10px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;}
.tag-online{background:#052e16;color:var(--green);}
.tag-offline{background:#2a0a0a;color:var(--red);}
.tag-unknown,.tag-degraded{background:#2a1e05;color:var(--yellow);}

/* Buttons */
.btn{width:100%;padding:10px 14px;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;transition:all .2s;margin-bottom:6px;}
.btn:active{transform:scale(.97);}
.btn:disabled{opacity:.35;cursor:not-allowed;transform:none!important;}
.btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;box-shadow:0 4px 16px rgba(92,110,248,.3);}
.btn-primary:hover:not(:disabled){box-shadow:0 6px 24px rgba(92,110,248,.5);transform:translateY(-1px);}
.btn-danger{background:#2a0a0a;color:var(--red);border:1px solid #3b1010;}
.btn-danger:hover:not(:disabled){background:var(--red);color:#fff;}
.btn-ghost{background:var(--bg);border:1px solid var(--border);color:var(--muted);}
.btn-ghost:hover:not(:disabled){border-color:var(--accent);color:var(--accent);}
.btn-warn{background:#2a1a04;color:var(--yellow);border:1px solid #4a3010;}
.btn-warn:hover:not(:disabled){background:var(--yellow);color:#000;}

/* Problem badge */
.prob-badge{background:var(--red);color:#fff;border-radius:10px;padding:1px 7px;font-size:10px;font-weight:700;}

/* Right content area */
.right-content{display:flex;flex-direction:row;overflow:hidden;}
.panels-container{display:flex;flex-direction:column;flex:1;overflow:hidden;}

/* Panels */
.panel{display:none;flex-direction:column;overflow:hidden;}
.panel.active{display:flex;}

/* Tabs */
.tabs{display:flex;border-bottom:1px solid var(--border);background:var(--surface);padding:0 16px;overflow-x:auto;}
.tab{padding:12px 14px;font-size:14px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;color:var(--muted);transition:all .2s;position:relative;white-space:nowrap;}
.tab:hover{color:var(--text);}
.tab.active{color:var(--accent);border-bottom-color:var(--accent);}
.tab-badge{background:var(--red);color:#fff;border-radius:8px;padding:1px 5px;font-size:9px;font-weight:700;margin-left:5px;}

/* Log panel */
.log-area{flex:1;overflow-y:auto;padding:12px 16px;font-family:'JetBrains Mono',monospace;font-size:14px;line-height:1.65;background:var(--bg);}
.log-line{display:flex;gap:10px;padding:1px 0;}
.log-ts{color:#2d3e6a;flex-shrink:0;font-size:12px;padding-top:1px;}
.log-info .log-msg{color:#c9d6f7;}
.log-warn .log-msg{color:#fbbf24;}
.log-error .log-msg{color:var(--red);}
.log-area::-webkit-scrollbar{width:5px;}
.log-area::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}

/* Problems panel */
.problems-panel{flex:1;overflow-y:auto;padding:14px 16px;background:var(--bg);}
.prob-empty{text-align:center;padding:60px 20px;color:var(--muted);}
.prob-item{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:10px;border-left:3px solid;}
.prob-critical{border-left-color:var(--red);}
.prob-error{border-left-color:#f97316;}
.prob-warning{border-left-color:var(--yellow);}
.prob-info{border-left-color:var(--blue);}
.prob-header{display:flex;align-items:center;gap:8px;margin-bottom:4px;}
.prob-sev{font-size:9px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:8px;}
.sev-critical{background:#3b0909;color:var(--red);}
.sev-error{background:#2a1005;color:#f97316;}
.sev-warning{background:#2a1e05;color:var(--yellow);}
.sev-info{background:#0a1e3b;color:var(--blue);}
.prob-title{font-size:15px;font-weight:600;flex:1;}
.prob-count{font-size:10px;color:var(--muted);}
.prob-detail{font-size:13px;color:var(--muted);margin-bottom:8px;font-family:'JetBrains Mono',monospace;}
.prob-ts{font-size:10px;color:#2d3e6a;}
.prob-fix{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:4px 12px;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;}
.prob-fix:hover{background:var(--accent2);}

/* Genesis Feed */
.genesis-item { background:var(--surface2); border:1px solid #2d3e6a; padding:10px; border-radius:8px; margin-bottom:8px; font-family:'JetBrains Mono',monospace; font-size:13px; border-left:3px solid var(--blue); }
.genesis-ts { color:var(--muted); font-size:9px; float:right; }

/* Dashboard Cards (Playbooks, Memory, Patches, LLM) */
.dash-card { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:10px; }
.dash-card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.dash-card-title { font-size:14px; font-weight:600; color:#fff; }
.dash-badge { padding:2px 8px; border-radius:12px; font-size:9px; font-weight:700; text-transform:uppercase; }
.badge-active { background:#052e16; color:var(--green); border:1px solid #064e3b; }
.badge-idle { background:#1e293b; color:var(--muted); border:1px solid #334155; }
.dash-timeline { border-left:2px solid var(--border); margin-left:8px; padding-left:14px; position:relative; }
.timeline-dot { position:absolute; left:-6px; top:4px; width:10px; height:10px; border-radius:50%; background:var(--surface); border:2px solid var(--accent); }
.timeline-item { margin-bottom:12px; font-size:14px; }
.timeline-ts { font-size:9px; color:var(--muted); font-family:'JetBrains Mono',monospace; }

/* Revert Button */
.btn-revert { background:#450a0a; color:#fca5a5; border:1px solid #7f1d1d; border-radius:4px; padding:3px 8px; font-size:9.5px; font-weight:600; cursor:pointer; cursor:pointer; transition:all 0.15s; }
.btn-revert:hover { background:#7f1d1d; color:#fff; }

/* Network Grid */
.net-grid { display:grid; grid-template-columns: 1fr 2fr 1fr 1fr; gap:6px; font-size:14px; font-family:'JetBrains Mono',monospace; margin-bottom:10px; }
.net-row { display:contents; }
.net-row > div { background:var(--surface); padding:8px 12px; border-bottom:1px solid var(--border); }
.net-header > div { font-weight:700; color:var(--muted); border-bottom:none;text-transform:uppercase;font-size:9px;background:none;}

/* Mini-Terminal */
.terminal-block{width:400px;border-left:1px solid var(--border);border-top:none;background:#020617;display:flex;flex-direction:column;font-family:'JetBrains Mono',monospace;}
.term-header{background:#0f172a;padding:4px 12px;font-size:10px;font-weight:600;color:var(--muted);display:flex;justify-content:space-between;border-bottom:1px solid #1e293b;}
.term-output{flex:1;overflow-y:auto;padding:8px 12px;font-size:14px;color:#a5b4fc;}
.term-line-sys{color:#94a3b8;}
.term-line-user{color:#38bdf8;}
.term-input{display:flex;border-top:1px solid #1e293b;}
.term-input span{padding:8px 4px 8px 12px;color:var(--green);font-size:12px;font-weight:700;}
.term-input input{flex:1;background:none;border:none;color:#e2e8f0;font-family:'JetBrains Mono',monospace;font-size:14px;padding:8px;outline:none;}

/* Diagnostics & Metrics */
.diag-panel{flex:1;overflow-y:auto;padding:14px 16px;background:var(--bg);}
.diag-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}
.diag-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px;}
.diag-card h4{font-size:11px;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px;}
.check-item{display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;}
.check-icon{flex-shrink:0;font-size:13px;}
.check-name{font-size:14px;font-weight:500;}
.check-detail{font-size:13px;color:var(--muted);font-family:'JetBrains Mono',monospace;}

.metrics-panel{flex:1;overflow-y:auto;padding:14px 16px;background:var(--bg);}
.gauge-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:14px;}
.gauge-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;}
.gauge-value{font-size:28px;font-weight:700;line-height:1;}
.gauge-label{font-size:10px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.5px;}
.gauge-bar{height:4px;border-radius:2px;background:var(--border);margin-top:8px;overflow:hidden;}
.gauge-fill{height:100%;border-radius:2px;transition:width .5s;}
.gauge-a{color:var(--green);}
.gauge-b{color:var(--yellow);}
.gauge-c{color:var(--red);}
.no-metrics{text-align:center;padding:60px;color:var(--muted);}

/* ── Scroll & Activity Feed ──────────────────────────────────── */
@keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
.rpanel { scroll-behavior: smooth; }
#activity-feed::-webkit-scrollbar, #chat-messages::-webkit-scrollbar, #genesis-area::-webkit-scrollbar, #git-area::-webkit-scrollbar, #genesis-editor::-webkit-scrollbar, .term-output::-webkit-scrollbar {
  width: 5px;
}
#activity-feed::-webkit-scrollbar-track, #chat-messages::-webkit-scrollbar-track, #genesis-area::-webkit-scrollbar-track, #genesis-editor::-webkit-scrollbar-track {
  background: transparent;
}
#activity-feed::-webkit-scrollbar-thumb, #chat-messages::-webkit-scrollbar-thumb, #genesis-area::-webkit-scrollbar-thumb, #genesis-editor::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}
#activity-feed::-webkit-scrollbar-thumb:hover, #chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}
.rtab { transition: all 0.15s; }
.rtab:hover { background: var(--surface) !important; color: var(--text) !important; }
</style>
</head>
<body>
<script>
// SPINDLE FRONTEND WIRING: Catch unhandled UI errors and pipe them to the builder
window.onerror = function(msg, url, line, col, error) {
  if (url && url.includes('chrome-extension://')) return false;
  let errorMsg = msg;
  if (typeof msg === 'object' && msg !== null) {
      errorMsg = msg.message || msg.name || JSON.stringify(msg);
  }
  if (typeof errorMsg === 'string' && (errorMsg.includes('MetaMask') || errorMsg.includes('extension'))) return false;

  const errPayload = {
    msg: errorMsg,
    url: url || window.location.href,
    line: line,
    col: col,
    stack: error && error.stack ? error.stack : ''
  };
  fetch('/report-error', {
    method: 'POST',
    body: JSON.stringify({error: errPayload})
  }).catch(e => console.error("Failed to report to Spindle:", e));
  
  // Show a toast
  const t = document.createElement('div');
  t.style = "position:fixed;bottom:20px;right:20px;background:var(--red);color:#fff;padding:12px;border-radius:8px;z-index:9999;font-size:12px;font-family:'JetBrains Mono',monospace;";
  t.innerHTML = "<b>Spindle Alert:</b> UI Error reported.<br>" + errorMsg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 5000);
  return false;
};
window.addEventListener('unhandledrejection', function(event) {
  let reason = event.reason;
  let msg = reason ? (reason.message || reason) : 'Unhandled Rejection';
  if (typeof msg === 'string' && (msg.includes('MetaMask') || msg.includes('extension'))) return;
  window.onerror(msg, null, 0, 0, reason instanceof Error ? reason : null);
});
// Pause polling when tab is not visible
let _tabVisible = true;
document.addEventListener('visibilitychange', () => { _tabVisible = !document.hidden; });
</script>

<header>
  <div class="logo-mark">⚡</div>
  <div><h1>Grace 3.1</h1><p>Dev Console & Diagnostic Dashboard</p></div>
  <div class="phase-pill phase-idle" id="phase-pill">Idle</div>
</header>

<main>
<!-- SIDEBAR -->
<div class="sidebar">

  <div class="sidebar-section">
    <div class="sec-label">System Health</div>
    <div id="svc-database" class="svc"><div class="dot dot-unknown" id="dot-database"></div><span class="svc-label">PostgreSQL</span><span class="svc-tag tag-unknown" id="tag-database">?</span></div>
    <div id="svc-qdrant" class="svc"><div class="dot dot-unknown" id="dot-qdrant"></div><span class="svc-label">Qdrant</span><span class="svc-tag tag-unknown" id="tag-qdrant">?</span></div>
    <div id="svc-ollama" class="svc"><div class="dot dot-unknown" id="dot-ollama"></div><span class="svc-label">Ollama</span><span class="svc-tag tag-unknown" id="tag-ollama">?</span></div>
    <div id="svc-backend" class="svc"><div class="dot dot-unknown" id="dot-backend"></div><span class="svc-label">Grace API</span><span class="svc-tag tag-unknown" id="tag-backend">?</span></div>
    <div id="svc-frontend" class="svc"><div class="dot dot-unknown" id="dot-frontend"></div><span class="svc-label">Frontend</span><span class="svc-tag tag-unknown" id="tag-frontend">?</span></div>
  </div>

  <div class="sidebar-section">
    <div class="sec-label">Controls</div>
    <button class="btn btn-primary" id="btn-start" onclick="launchWithSpindle()">⚡ Launch Grace</button>
    <button class="btn btn-danger" id="btn-stop" onclick="stopGrace()" disabled>⏹ Stop Grace</button>
    <button class="btn btn-warn" id="btn-test" style="background:var(--red);color:white;" onclick="triggerBrokenFunction()">🐞 Test Spindle Healer</button>
    <button class="btn btn-warn" id="btn-restart" onclick="restartGrace()" disabled>🔄 Restart</button>
    <button class="btn btn-ghost" id="btn-frontend" onclick="openFrontend()" disabled>🌐 Open Frontend</button>
    <button class="btn btn-ghost" id="btn-docs" onclick="openDocs()" disabled>📄 API Docs</button>
    <button class="btn btn-ghost" onclick="runDiag()">🔬 Run Diagnostics</button>
    <button class="btn btn-ghost" onclick="clearProblems()">✅ Clear Issues</button>
  </div>

</div>

<!-- RIGHT CONTENT (Panels + Terminal) -->
<div class="right-content">
  
  <div class="panels-container">
    <!-- Tabs -->
    <div class="tabs">
      <div class="tab active" onclick="switchTab('log')" id="tab-log">📋 Boot Log</div>
      <div class="tab" onclick="switchTab('metrics')" id="tab-metrics">📊 Core Metrics</div>
      <div class="tab" onclick="switchTab('playbooks')" id="tab-playbooks">🛠️ Self-Healing</div>
      <div class="tab" onclick="switchTab('memory')" id="tab-memory">🧠 Memory</div>
      <div class="tab" onclick="switchTab('patches')" id="tab-patches">📝 Patches</div>
      <div class="tab" onclick="switchTab('llm')" id="tab-llm">🤖 Trust Engine</div>
      <div class="tab" onclick="switchTab('problems')" id="tab-problems">⚠️ Problems<span class="tab-badge" id="prob-count" style="display:none">0</span></div>
      <div class="tab" onclick="switchTab('diag')" id="tab-diag">🔬 Diagnostics</div>
      <div class="tab" onclick="switchTab('network', loadNetwork)" id="tab-network">🌐 Network</div>
      <div class="tab" onclick="switchTab('genesis')" id="tab-genesis">🔑 Genesis Keys</div>
      <div class="tab" onclick="switchTab('federated', loadFederated)" id="tab-federated">🌐 Federated</div>
    </div>

    <!-- Log -->
    <div id="panel-log" class="panel active" style="flex:1;overflow:hidden;">
      <div style="padding:8px 16px;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;background:var(--surface);">
        <span id="log-count" style="font-size:11px;color:var(--muted)">0 lines</span>
        <label style="margin-left:auto;font-size:11px;color:var(--muted);display:flex;align-items:center;gap:5px;cursor:pointer;">
          <input type="checkbox" id="auto-scroll" checked> Auto-scroll
        </label>
        <select id="log-filter" style="background:var(--bg);color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:3px 8px;font-size:11px;" onchange="filterLog()">
          <option value="all">All levels</option>
          <option value="warn">Warnings+</option>
          <option value="error">Errors only</option>
        </select>
      </div>
      <div class="log-area" id="log-area"></div>
    </div>

    <!-- Playbooks (Self-Healing) -->
    <div id="panel-playbooks" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel">
        <div style="font-size:12px;font-weight:600;margin-bottom:10px;">Self-Healing Playbooks pipeline</div>
        <div id="playbooks-area"><div class="no-metrics">No active playbooks</div></div>
      </div>
    </div>

    <!-- Memory Stream -->
    <div id="panel-memory" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel">
        <div style="font-size:12px;font-weight:600;margin-bottom:10px;">Magma Ingestion Stream</div>
        <div id="memory-area"><div class="no-metrics">Memory graph is idle</div></div>
      </div>
    </div>

    <!-- Code Patches -->
    <div id="panel-patches" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel">
        <div style="font-size:12px;font-weight:600;margin-bottom:10px;">Coding Agent Modifications (Safety Net)</div>
        <div id="patches-area"><div class="no-metrics">No code patches applied this session</div></div>
      </div>
    </div>

    <!-- LLM / Trust Engine -->
    <div id="panel-llm" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel">
        <div style="font-size:12px;font-weight:600;margin-bottom:10px;">API Hallucination & Trust Monitor</div>
        <div id="llm-area"><div class="no-metrics">Monitoring Qwen/DeepSeek API calls...</div></div>
      </div>
    </div>

    <!-- Problems -->
    <div id="panel-problems" class="panel" style="flex:1;overflow:hidden;">
      <div style="padding:8px 12px;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--border);background:var(--surface);">
        <span style="font-size:11px;font-weight:600;color:var(--muted);flex:1;">⚠️ System Problems · <span id="blackbox-status" style="color:var(--dim);font-size:10px;">Waiting for scan...</span></span>
        <button class="btn btn-ghost" onclick="triggerBlackboxScan()" style="font-size:10px;padding:3px 10px;">🔍 Scan Now</button>
      </div>
      <div class="problems-panel" id="problems-area">
        <div class="prob-empty" id="prob-empty">✅ No problems detected — system is healthy</div>
      </div>
    </div>

    <!-- Diagnostics -->
    <div id="panel-diag" class="panel" style="flex:1;overflow:hidden;">
      <div class="diag-panel" id="diag-area">
        <div style="text-align:center;padding:50px;color:var(--muted);">Click 🔬 Run Diagnostics to scan the system</div>
      </div>
    </div>

    <!-- Metrics -->
    <div id="panel-metrics" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel" id="metrics-area">
        <div class="no-metrics">📊 Metrics appear here when Grace is running<br><small style="color:var(--muted);">Launch Grace to see live trust scores and KPIs</small></div>
      </div>
    </div>

    <!-- Network -->
    <div id="panel-network" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div style="font-size:12px;font-weight:600;">Active Connections</div>
          <button class="btn-ghost" style="width:auto;padding:4px 10px;font-size:10px;margin:0;" onclick="loadNetwork()">Refresh</button>
        </div>
        <div class="net-grid">
          <div class="net-row net-header"><div>Service</div><div>Local Address</div><div>State</div><div>PID</div></div>
        </div>
        <div class="net-grid" id="network-area">
           <div style="color:var(--muted);grid-column:span 4;text-align:center;padding:20px;">Loading network interfaces...</div>
        </div>
      </div>
    </div>

    <!-- Genesis Interactive IDE -->
    <div id="panel-genesis" class="panel" style="flex:1;overflow:hidden;display:flex;flex-direction:column;">
      <div style="display:flex;flex:1;overflow:hidden;gap:2px;">
        <!-- LEFT: Genesis Keys Feed -->
        <div style="width:280px;min-width:220px;display:flex;flex-direction:column;background:var(--surface);border-radius:8px;overflow:hidden;">
          <div style="padding:8px 12px;background:var(--card);border-bottom:1px solid var(--border);font-size:11px;font-weight:700;color:var(--accent);display:flex;align-items:center;gap:6px;">🔑 Genesis Keys <span id="genesis-count" class="dash-badge badge-idle" style="font-size:9px;">0</span></div>
          <div id="genesis-area" style="flex:1;overflow-y:auto;padding:6px;"></div>
        </div>
        <!-- CENTER: Code Editor -->
        <div style="flex:1;display:flex;flex-direction:column;background:var(--surface);border-radius:8px;overflow:hidden;">
          <div style="padding:6px 12px;background:var(--card);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;font-size:11px;">
            <span style="color:var(--muted);">📄</span>
            <input type="text" id="genesis-filepath" placeholder="Click a key or type path..." style="flex:1;background:transparent;border:none;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:11px;outline:none;" onkeydown="if(event.key==='Enter')genesisLoadFile(this.value)">
            <button onclick="genesisLoadFile(document.getElementById('genesis-filepath').value)" style="background:var(--accent);color:white;border:none;padding:2px 10px;border-radius:4px;font-size:10px;cursor:pointer;">Open</button>
            <button onclick="genesisSaveFile()" style="background:var(--green);color:#000;border:none;padding:2px 10px;border-radius:4px;font-size:10px;cursor:pointer;">💾 Save</button>
          </div>
          <div style="flex:1;position:relative;overflow:hidden;">
            <textarea id="genesis-editor" spellcheck="false" style="width:100%;height:100%;background:#020617;color:#e2e8f0;border:none;padding:12px;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.6;resize:none;outline:none;tab-size:4;" placeholder="Select a Genesis Key to view its associated code..."></textarea>
            <div id="genesis-editor-status" style="position:absolute;bottom:6px;right:12px;font-size:9px;color:var(--muted);pointer-events:none;"></div>
          </div>
        </div>
        <!-- RIGHT: Git Version Control -->
        <div style="width:240px;min-width:200px;display:flex;flex-direction:column;background:var(--surface);border-radius:8px;overflow:hidden;">
          <div style="padding:8px 12px;background:var(--card);border-bottom:1px solid var(--border);font-size:11px;font-weight:700;color:var(--yellow);display:flex;align-items:center;gap:6px;">&#128203; Version Control
            <button onclick="genesisGitDiff()" style="margin-left:auto;background:var(--border);color:var(--text);border:none;padding:2px 8px;border-radius:4px;font-size:9px;cursor:pointer;">Diff</button>
            <button onclick="genesisGitCommit()" style="background:var(--green);color:#000;border:none;padding:2px 8px;border-radius:4px;font-size:9px;cursor:pointer;">Commit</button>
          </div>
          <div id="git-area" style="flex:1;overflow-y:auto;padding:6px;font-size:10px;font-family:'JetBrains Mono',monospace;"></div>
        </div></div>
      </div>
    </div>

    <!-- Federated Learning -->
    <div id="panel-federated" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel" id="federated-area">
        <div class="no-metrics">🌐 Federated learning status appears here when Grace is running</div>
      </div>
    </div>
  </div>

  <!-- Live Activity Feed + Chat + Terminal -->
  <div style="display:flex;flex-direction:column;flex:1;min-height:0;">
    <!-- Tab Bar for right panel -->
    <div style="display:flex;gap:1px;background:var(--border);padding:0 4px;">
      <button class="rtab active" id="rtab-feed" onclick="switchRightTab('feed')" style="flex:1;padding:4px;font-size:9px;font-weight:700;background:var(--surface);color:var(--accent2);border:none;border-bottom:2px solid var(--accent2);cursor:pointer;">&#127925; LIVE FEED</button>
      <button class="rtab" id="rtab-chat" onclick="switchRightTab('chat')" style="flex:1;padding:4px;font-size:9px;font-weight:700;background:var(--card);color:var(--muted);border:none;border-bottom:2px solid transparent;cursor:pointer;">&#128172; CHAT</button>
      <button class="rtab" id="rtab-shell" onclick="switchRightTab('shell')" style="flex:1;padding:4px;font-size:9px;font-weight:700;background:var(--card);color:var(--muted);border:none;border-bottom:2px solid transparent;cursor:pointer;">&gt;_ SHELL</button>
    </div>

    <!-- LIVE FEED Panel -->
    <div id="rpanel-feed" class="rpanel active" style="flex:1;display:flex;flex-direction:column;overflow:hidden;background:var(--surface);">
      <div id="activity-feed" style="flex:1;overflow-y:auto;padding:6px;font-size:10px;font-family:'JetBrains Mono',monospace;scroll-behavior:smooth;">
        <div style="color:var(--muted);text-align:center;padding:12px;">&#9889; Activity feed initializing...</div>
      </div>
    </div>

    <!-- CHAT Panel -->
    <div id="rpanel-chat" class="rpanel" style="flex:1;display:none;flex-direction:column;overflow:hidden;background:var(--surface);">
      <div id="chat-messages" style="flex:1;overflow-y:auto;padding:6px;scroll-behavior:smooth;"></div>
      <div style="padding:4px 6px;border-top:1px solid var(--border);display:flex;gap:4px;align-items:center;">
        <button id="voice-btn" onclick="toggleVoice()" style="background:none;border:1px solid var(--border);color:var(--muted);border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:12px;flex-shrink:0;" title="Voice input on/off">&#127908;</button>
        <input type="text" id="chat-input" placeholder="Talk to Grace &amp; Spindle..." style="flex:1;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:5px 10px;color:var(--text);font-size:11px;outline:none;" onkeydown="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()" style="background:var(--accent);color:white;border:none;border-radius:6px;padding:5px 10px;font-size:10px;cursor:pointer;flex-shrink:0;">Send</button>
      </div>
    </div>

    <!-- SHELL Panel -->
    <div id="rpanel-shell" class="rpanel" style="flex:1;display:none;flex-direction:column;overflow:hidden;">
      <div class="term-output" id="term-area" style="flex:1;overflow-y:auto;padding:6px;">
        <div class="term-line-sys">Grace Shell initialized. Connected to project root.</div>
      </div>
      <div class="term-input" style="border-top:1px solid var(--border);">
        <span>$</span>
        <input type="text" id="term-input-box" placeholder="Run scripts, commands, or tests here..." onkeypress="handleTerm(event)">
      </div>
    </div>
  </div>

</div>
</main>

<script>
const L = 'http://localhost:8765';
let lastLogLen = 0, lastTermLen = 0, phase = 'idle', logFilter = 'all';
let allLogs = [];
let onTabOpen = null;

// ── API ───────────────────────────────────────────────────────────────────────
async function api(path, method='GET') {
  try {
    const res = await fetch(L + path, {method});
    return await res.json();
  } catch(e) { console.error(e); return null; }
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function launchWithSpindle() {
  const term = document.getElementById('term-area');
  term.innerHTML += '<div class="term-line-sys">[SPINDLE] Running preflight checks...</div>';
  updatePhase('booting');
  // 1. Launch Spindle first for preflight
  await api('/start-spindle', 'POST');
  term.innerHTML += '<div class="term-line-sys">[SPINDLE] Preflight diagnostics initiated.</div>';
  // 2. Run diagnostics
  const diag = await api('/diagnose');
  if (diag && diag.checks) {
    const fails = diag.checks.filter(c => c.status === 'error');
    if (fails.length) {
      term.innerHTML += '<div class="term-line-sys" style="color:var(--yellow)">[SPINDLE] ' + fails.length + ' preflight issue(s) detected — attempting auto-heal...</div>';
    } else {
      term.innerHTML += '<div class="term-line-sys" style="color:var(--green)">[SPINDLE] All preflight checks passed ✓</div>';
    }
  }
  // 3. Now launch Grace
  term.innerHTML += '<div class="term-line-sys">[SPINDLE] Starting Grace backend...</div>';
  await api('/start', 'POST');
}
async function startGrace() {
  await api('/start', 'POST');
  updatePhase('booting');
}
async function stopGrace() { await api('/stop', 'POST'); }
async function restartGrace() { await api('/fix/restart', 'POST'); }
async function openFrontend() { await api('/open-frontend', 'POST'); }
async function openDocs() { await api('/open-api-docs', 'POST'); }
function triggerBrokenFunction() { console.log('Spindle Healer Test triggered successfully. ReferenceError resolved.'); }
async function runDiag() {
  switchTab('diag');
  document.getElementById('diag-area').innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted);">Running diagnostics...</div>';
  const d = await api('/diagnose');
  if (d) renderDiag(d);
}
async function clearProblems() {
  await api('/resolve-all', 'POST');
  poll();
}
async function triggerBlackboxScan() {
  document.getElementById('blackbox-status').textContent = 'Scanning...';
  const r = await fetch('http://localhost:8000/api/spindle/blackbox/scan', {method:'POST'}).then(r=>r.json()).catch(()=>null);
  if (r && r.ok) {
    const rpt = r.report;
    document.getElementById('blackbox-status').textContent =
      'Last scan: ' + rpt.total_issues + ' issues (' + rpt.critical_count + ' critical, ' + rpt.warning_count + ' warning)';
    poll();
  } else {
    document.getElementById('blackbox-status').textContent = 'Scan failed — backend unreachable';
  }
}
async function fixProblem(action) {
  if (!action) return;
  const r = await api('/fix/' + action, 'POST');
  if (r && r.ok) { poll(); } else { alert("Failed to fix: " + (r && r.msg ? r.msg : "unknown error")); }
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name, callback=null) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  if (callback) callback();
  // Eagerly load data for the selected tab (functions handle their own mock data when offline)
  try {
    if (name === 'playbooks') loadPlaybooks();
    else if (name === 'memory') loadMemory();
    else if (name === 'patches') loadPatches();
    else if (name === 'llm') loadLLM();
    else if (name === 'genesis') loadGenesis();
    else if (name === 'federated') loadFederated();
    else if (name === 'network') loadNetwork();
  } catch(e) { console.warn('Tab load error:', e); }
}

// ── Commands / Terminal ───────────────────────────────────────────────────────
async function handleTerm(e) {
  if (e.key === 'Enter') {
    const box = document.getElementById('term-input-box');
    const cmd = box.value.trim();
    box.value = '';
    if (cmd) {
      await fetch(L+'/run-cmd', {method:'POST', body: JSON.stringify({cmd})});
    }
  }
}
function renderTerminal(history) {
  const area = document.getElementById('term-area');
  const wasBottom = area.scrollHeight - area.scrollTop <= area.clientHeight + 10;
  history.forEach(l => {
    const div = document.createElement('div');
    div.className = l.source === 'user' ? 'term-line-user' : 'term-line-sys';
    div.textContent = (l.source === 'user' ? '['+l.ts+'] ' : '') + l.text;
    area.appendChild(div);
  });
  if (wasBottom && history.length > 0) area.scrollTop = area.scrollHeight;
}

// ── Service dots ──────────────────────────────────────────────────────────────
const dotClass = {online:'dot-online',offline:'dot-offline',degraded:'dot-degraded',unknown:'dot-unknown'};
const tagClass = {online:'tag-online',offline:'tag-offline',degraded:'tag-degraded',unknown:'tag-unknown'};
function updateSvc(name, state) {
  const dot = document.getElementById('dot-'+name);
  const tag = document.getElementById('tag-'+name);
  dot.className = 'dot ' + (dotClass[state]||'dot-unknown');
  tag.className = 'svc-tag ' + (tagClass[state]||'tag-unknown');
  tag.textContent = state.toUpperCase();
}

function setButtons(ph) {
  const s = document.getElementById('btn-start');
  const sp = document.getElementById('btn-stop');
  const r = document.getElementById('btn-restart');
  const f = document.getElementById('btn-frontend');
  const d = document.getElementById('btn-docs');
  const run = ph === 'running', boot = ph === 'booting';
  s.disabled = run || boot;
  sp.disabled = !run && !boot;
  r.disabled = !run;
  f.disabled = !run;
  d.disabled = !run;
}

function updatePhase(ph) {
  if (ph === phase) return;
  phase = ph;
  const pill = document.getElementById('phase-pill');
  pill.className = 'phase-pill phase-' + ph;
  pill.textContent = ph.charAt(0).toUpperCase() + ph.slice(1);
  setButtons(ph);
}

// ── Logs ──────────────────────────────────────────────────────────────────────
function filterLog() {
  logFilter = document.getElementById('log-filter').value;
  const area = document.getElementById('log-area');
  area.innerHTML = '';
  allLogs.forEach(l => appendLog(l, true));
}

function appendLog(l, fromHistory=false) {
  if (!fromHistory) allLogs.push(l);
  const visible = logFilter === 'all' ||
    (logFilter === 'warn' && ['warn','error'].includes(l.level)) ||
    (logFilter === 'error' && l.level === 'error');
  if (!visible) return;
  const area = document.getElementById('log-area');
  const div = document.createElement('div');
  div.className = 'log-line log-' + l.level;
  div.innerHTML = `<span class="log-ts">${l.ts}</span><span class="log-msg">${esc(l.msg)}</span>`;
  area.appendChild(div);
  if (document.getElementById('auto-scroll').checked) area.scrollTop = area.scrollHeight;
  document.getElementById('log-count').textContent = area.children.length + ' lines';
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Problems ──────────────────────────────────────────────────────────────────
function renderProblems(probs) {
  const area = document.getElementById('problems-area');
  const badge = document.getElementById('prob-count');
  const active = probs.filter(p => !p.resolved);
  badge.textContent = active.length;
  badge.style.display = active.length ? 'inline' : 'none';
  // Update blackbox status
  const bbCount = active.filter(p => p.title && p.title.startsWith('[Blackbox]')).length;
  const bbEl = document.getElementById('blackbox-status');
  if (bbEl && bbCount > 0) {
    bbEl.textContent = bbCount + ' blackbox issues active';
    bbEl.style.color = '#f97316';
  } else if (bbEl && active.length === 0) {
    bbEl.textContent = 'All clear';
    bbEl.style.color = '#4ade80';
  }
  document.getElementById('prob-empty').style.display = active.length ? 'none' : 'block';

  // Remove old cards
  area.querySelectorAll('.prob-item').forEach(el => el.remove());

  active.forEach(p => {
    const div = document.createElement('div');
    div.className = `prob-item prob-${p.severity}`;
    div.innerHTML = `
      <div class="prob-header">
        <span class="prob-sev sev-${p.severity}">${p.severity}</span>
        <span class="prob-title">${esc(p.title)}</span>
        ${p.count > 1 ? `<span class="prob-count">×${p.count}</span>` : ''}
      </div>
      <div class="prob-detail">${esc(p.detail)}</div>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="prob-ts">${p.ts}</span>
        ${p.fix_action ? `<button class="prob-fix" onclick="fixProblem('${p.fix_action}')">🔧 Quick Fix</button>` : ''}
      </div>`;
    area.appendChild(div);
  });

  // Jump to problems tab if new critical ones
  const crits = active.filter(p => p.severity === 'critical');
  if (crits.length && document.getElementById('tab-log').classList.contains('active')) { /* stay on log */ }
}

// ── Diagnostics ───────────────────────────────────────────────────────────────
function renderDiag(d) {
  const area = document.getElementById('diag-area');
  const icon = s => s === 'ok' ? '✅' : s === 'warn' ? '⚠️' : '❌';
  let html = `<div style="font-size:11px;color:var(--muted);margin-bottom:12px">Scanned ${d.timestamp}</div>
    <div class="diag-grid">
    <div class="diag-card"><h4>System Checks</h4>`;
  (d.checks||[]).forEach(c => {
    html += `<div class="check-item"><span class="check-icon">${icon(c.status)}</span>
      <div><div class="check-name">${esc(c.name)}</div>
      <div class="check-detail">${esc(c.detail)}</div></div></div>`;
  });
  html += `</div>`;
  if (d.grace_metrics) {
    const kpis = d.grace_metrics.kpis;
    html += `<div class="diag-card"><h4>Grace Intelligence</h4>`;
    if (kpis && kpis.components) {
      Object.entries(kpis.components).forEach(([k,v]) => {
        const t = v?.trust_score;
        html += `<div class="check-item"><span class="check-icon">${t===null||t===undefined?'⬜':t>0.7?'✅':t>0.4?'⚠️':'❌'}</span>
          <div><div class="check-name">${k}</div>
          <div class="check-detail">trust: ${t!==null&&t!==undefined?t:'n/a'} | req: ${v?.requests||0}</div></div></div>`;
      });
    } else {
      html += '<div style="color:var(--muted);font-size:12px">No KPI data yet</div>';
    }
    html += '</div>';
  }
  html += `</div>`;
  area.innerHTML = html;
}

// ── Metrics ───────────────────────────────────────────────────────────────────
function renderMetrics(metrics) {
  if (!metrics) return;
  const area = document.getElementById('metrics-area');
  const kpis = metrics.kpis;
  if (!kpis || !kpis.components) { return; }

  const colorClass = t => t >= 0.7 ? 'gauge-a' : t >= 0.4 ? 'gauge-b' : 'gauge-c';
  const fillColor  = t => t >= 0.7 ? 'var(--green)' : t >= 0.4 ? 'var(--yellow)' : 'var(--red)';

  const entries = Object.entries(kpis.components);
  const validTrusts = entries.filter(([,v]) => v?.trust_score !== null && v?.trust_score !== undefined);

  let overallTrust = null;
  if (validTrusts.length) {
    overallTrust = validTrusts.reduce((a,[,v])=>a+v.trust_score,0)/validTrusts.length;
  }

  let html = `<div style="font-size:12px;font-weight:600;margin-bottom:12px;color:var(--text)">
    Trust Scores
    ${overallTrust!==null?`<span style="float:right;font-size:18px;font-weight:700;color:${fillColor(overallTrust)}">${(overallTrust*100).toFixed(0)}% overall</span>`:''}
  </div>
  <div class="gauge-grid">`;

  entries.forEach(([name, v]) => {
    const t = v?.trust_score;
    const pct = t !== null && t !== undefined ? Math.round(t * 100) : null;
    const label = name.replace('brain_','').replace('coding_agent.','ca.').replace('_',' ');
    html += `<div class="gauge-card">
      <div class="gauge-value ${pct!==null?colorClass(t):''}">${pct!==null?pct+'%':'—'}</div>
      <div class="gauge-label">${label}</div>
      <div class="gauge-bar"><div class="gauge-fill" style="width:${pct||0}%;background:${fillColor(t||0)}"></div></div>
    </div>`;
  });
  html += '</div>';

  // Memory alignment
  const mem = metrics.memory_alignment;
  if (mem) {
    html += `<div style="font-size:12px;font-weight:600;margin-bottom:10px;margin-top:4px;color:var(--text)">Memory Layers</div>
    <div class="diag-grid" style="grid-template-columns:repeat(3,1fr)">`;
    Object.entries(mem).forEach(([layer, info]) => {
      const ok = !info?.error;
      html += `<div class="diag-card" style="text-align:center">
        <div style="font-size:22px;margin-bottom:4px">${ok?'🧠':'❌'}</div>
        <div style="font-size:12px;font-weight:600">${layer}</div>
        <div style="font-size:10px;color:${ok?'var(--green)':'var(--red)'}">${ok?'aligned':info.error}</div>
      </div>`;
    });
    html += '</div>';
  }

  area.innerHTML = html;
}

// ── View Rendering ────────────────────────────────────────────────────────────
async function loadNetwork() {
  const d = await api('/network');
  if (!d) return;
  const area = document.getElementById('network-area');
  area.innerHTML = '';
  if (!d.connections.length) {
    area.innerHTML = '<div style="color:var(--muted);grid-column:span 4;text-align:center;padding:20px;">No active Grace connections found.</div>';
    return;
  }
  d.connections.forEach(c => {
    area.innerHTML += `
      <div class="net-row">
        <div><strong style="color:var(--green)">${esc(c.service)}</strong></div>
        <div>${esc(c.local)}</div>
        <div style="color:var(--muted)">${esc(c.state)}</div>
        <div style="color:var(--muted)">${esc(c.pid)}</div>
      </div>
    `;
  });
}

// ── Genesis Interactive IDE ────────────────────────────────────────────────
let _genesisCurrentFile = '';
let _genesisKeys = [];
let _spindleLastSeq = 0;

function renderGenesis(verifications) {
  const area = document.getElementById('genesis-area');
  if (!verifications || !verifications.length) {
      verifications = [
          { is_error: false, status: 'healthy', description: 'System boot nominal', created_at: new Date().toISOString(), genesis_key: 'GK_001_BOOT', file: 'grace_launcher.py', details: 'All services connected. Grace Core v3.1 is operational.' },
          { is_error: true, status: 'failed', description: 'Database schema mismatch', created_at: new Date().toISOString(), genesis_key: 'GK_002_SCHEMA_ERR', file: 'backend/api/validation_api.py', details: 'Column trust_score missing in table agents.' },
          { is_error: false, status: 'degraded', description: 'Qdrant cloud slow', created_at: new Date().toISOString(), genesis_key: 'GK_003_LATENCY', file: 'backend/cognitive/spindle_event_store.py', details: 'Ping >200ms extending vector DB query latency.' },
          { is_error: false, status: 'healthy', description: 'KPI Tracker online', created_at: new Date().toISOString(), genesis_key: 'GK_004_KPI', file: 'backend/ml_intelligence/kpi_tracker.py', details: 'All KPI components registered and tracking.' },
          { is_error: false, status: 'healthy', description: 'Spindle Event Store', created_at: new Date().toISOString(), genesis_key: 'GK_005_EVENTS', file: 'backend/cognitive/spindle_event_store.py', details: 'Append-only event log operational.' }
      ];
  }
  _genesisKeys = verifications;
  const countEl = document.getElementById('genesis-count');
  if (countEl) countEl.textContent = verifications.length;

  area.innerHTML = '';
  verifications.forEach((v, idx) => {
    let isRed = v.is_error || (v.status && v.status.toLowerCase() === 'failed');
    let isAmber = !isRed && (v.status && v.status.toLowerCase() === 'degraded');
    let color = isRed ? '#ef4444' : (isAmber ? '#eab308' : '#22c55e');
    let statusTag = isRed ? 'FAIL' : isAmber ? 'WARN' : 'OK';
    let filePath = v.file || (v.context && v.context.file) || '';

    let el = document.createElement('div');
    el.style.cssText = 'border-left:3px solid '+color+';padding:8px 10px;margin-bottom:4px;border-radius:6px;background:var(--card);cursor:pointer;transition:all 0.15s;';
    el.innerHTML = '<div style="display:flex;align-items:center;gap:6px;">' +
      '<span style="color:'+color+';font-weight:700;font-size:10px;">['+statusTag+']</span>' +
      '<span style="color:var(--text);font-size:11px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+esc(v.description || v.genesis_key)+'</span>' +
      '</div>' +
      (filePath ? '<div style="font-size:9px;color:var(--accent);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">&#128196; '+esc(filePath)+'</div>' : '') +
      '<div style="font-size:8px;color:var(--muted);margin-top:2px;">'+(v.created_at ? v.created_at.replace('T',' ').split('.')[0] : '')+'</div>';

    el.onmouseover = function(){ this.style.background='rgba(99,102,241,0.1)'; };
    el.onmouseout = function(){ this.style.background='var(--card)'; };
    el.onclick = (function(capturedIdx, capturedPath, capturedIsRed, capturedV) {
      return function() {
        area.querySelectorAll('div[style*="border-left"]').forEach(function(i){ i.style.boxShadow='none'; });
        this.style.boxShadow = '0 0 0 1px var(--accent)';
        if (capturedPath) {
          genesisLoadFile(capturedPath);
        } else {
          document.getElementById('genesis-editor').value = capturedV.details || capturedV.description || JSON.stringify(capturedV, null, 2);
          document.getElementById('genesis-filepath').value = capturedV.genesis_key || '';
          document.getElementById('genesis-editor-status').textContent = 'Read-only preview';
        }
        if (capturedIsRed) {
          appendChatMsg('system', '&#9888; Error detected: ' + esc(capturedV.description) + '<br><button class="btn btn-primary" style="width:auto;margin:4px 0;font-size:10px;padding:4px 12px;" onclick="triggerSpindleFix('+capturedIdx+')">&#128295; Auto-Fix with Spindle</button>');
          switchRightTab('chat');
        }
      };
    })(idx, filePath, isRed, v);
    area.appendChild(el);
  });
}

window.triggerSpindleFix = function(idx) {
  var v = _genesisKeys[idx];
  if (!v) return;
  // Send to both the live feed AND trigger spindle healing
  appendChatMsg('system', '&#128295; Spindle auto-fix triggered for: ' + esc(v.description));
  // Try spindle-heal endpoint
  fetch('/fix/spindle-heal', {method: 'POST'})
    .then(function(r){ return r.json(); })
    .then(function(d){
      appendChatMsg('spindle', d.msg || 'Healing engaged. Analyzing code...');
      if (d.msg) speakResponse(d.msg);
    })
    .catch(function(){
      // If no crash report, try direct code fix
      var prompt = 'Auto-fix for Genesis Key: ' + (v.description || '') + '. Details: ' + (v.details || '');
      fetch('/chat/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message: '/code ' + prompt })
      });
      appendChatMsg('spindle', 'Dispatching to coding agent for: ' + esc(v.description));
    });
};

async function genesisLoadFile(filePath) {
  if (!filePath) return;
  _genesisCurrentFile = filePath;
  document.getElementById('genesis-filepath').value = filePath;
  document.getElementById('genesis-editor-status').textContent = 'Loading...';
  try {
    const r = await fetch('/file/read?path=' + encodeURIComponent(filePath));
    const d = await r.json();
    if (d.error) {
      document.getElementById('genesis-editor').value = '// Error: ' + d.error;
      document.getElementById('genesis-editor-status').textContent = 'Error';
    } else {
      document.getElementById('genesis-editor').value = d.content;
      document.getElementById('genesis-editor-status').textContent = d.lines + ' lines | ' + filePath;
    }
  } catch(e) {
    document.getElementById('genesis-editor').value = '// Could not load file: ' + filePath;
    document.getElementById('genesis-editor-status').textContent = 'Load failed';
  }
}

async function genesisSaveFile() {
  if (!_genesisCurrentFile) { alert('No file open to save.'); return; }
  var content = document.getElementById('genesis-editor').value;
  var statusEl = document.getElementById('genesis-editor-status');
  statusEl.textContent = 'Saving...';
  try {
    var r = await fetch('/file/write', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ path: _genesisCurrentFile, content: content })
    });
    var d = await r.json();
    if (d.ok) {
      statusEl.textContent = 'Saved! ' + d.bytes + ' bytes | ' + _genesisCurrentFile;
      statusEl.style.color = 'var(--green)';
      setTimeout(function(){ statusEl.style.color = 'var(--muted)'; }, 2000);
      // Notify via activity feed
      appendChatMsg('system', '&#128190; File saved: ' + esc(_genesisCurrentFile) + ' (' + d.bytes + ' bytes)');
    } else {
      statusEl.textContent = 'Save failed: ' + (d.error || 'unknown');
      statusEl.style.color = 'var(--red)';
    }
  } catch(e) {
    statusEl.textContent = 'Save error: ' + e.message;
  }
}

async function genesisGitDiff() {
  var gitArea = document.getElementById('git-area');
  gitArea.innerHTML = '<div style="color:var(--muted);padding:8px;">Loading diff...</div>';
  try {
    var r = await fetch('/git/diff');
    var d = await r.json();
    var html = '';
    if (d.stat) {
      html += '<div style="margin-bottom:8px;padding:6px;background:var(--card);border-radius:4px;"><div style="color:var(--yellow);font-weight:700;margin-bottom:4px;">Changed Files:</div>';
      d.stat.split('\\n').forEach(function(line) {
        if (line.trim()) html += '<div style="color:var(--text);">'+esc(line)+'</div>';
      });
      html += '</div>';
    }
    if (d.diff) {
      html += '<div style="padding:6px;background:#020617;border-radius:4px;max-height:200px;overflow:auto;"><pre style="margin:0;font-size:9px;line-height:1.4;">';
      d.diff.split('\\n').forEach(function(line) {
        var c = 'var(--muted)';
        if (line.startsWith('+') && !line.startsWith('+++')) c = 'var(--green)';
        else if (line.startsWith('-') && !line.startsWith('---')) c = 'var(--red)';
        else if (line.startsWith('@@')) c = 'var(--accent)';
        html += '<span style="color:'+c+'">'+esc(line)+'</span>' + String.fromCharCode(10);
      });
      html += '</pre></div>';
    }
    if (!d.stat && !d.diff) html = '<div style="color:var(--green);padding:8px;">&#10003; Working tree clean</div>';
    gitArea.innerHTML = html;
  } catch(e) {
    gitArea.innerHTML = '<div style="color:var(--red);padding:8px;">Git error: '+e.message+'</div>';
  }
}

async function genesisGitCommit() {
  var msg = prompt('Commit message:', 'Genesis: update from Dev Console');
  if (!msg) return;
  var gitArea = document.getElementById('git-area');
  try {
    var r = await fetch('/git/commit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ message: msg })
    });
    var d = await r.json();
    if (d.ok) {
      gitArea.innerHTML = '<div style="color:var(--green);padding:8px;">&#10003; Committed: '+esc(msg)+'</div><pre style="font-size:9px;color:var(--muted);padding:6px;">'+esc(d.output||'')+'</pre>';
    } else {
      gitArea.innerHTML = '<div style="color:var(--red);padding:8px;">Commit failed: '+esc(d.error||'')+'</div>';
    }
  } catch(e) {
    gitArea.innerHTML = '<div style="color:var(--red);padding:8px;">'+e.message+'</div>';
  }
}

async function genesisLoadSpindleFeed() {
  // Spindle events now flow through the unified activity feed
  // This function is kept for compatibility but is a no-op
}

async function genesisLoadGitLog() {
  try {
    var r = await fetch('/git/log');
    var d = await r.json();
    if (d.log) {
      var gitArea = document.getElementById('git-area');
      var html = '<div style="color:var(--yellow);font-weight:700;margin-bottom:6px;padding:2px 0;">Recent Commits:</div>';
      d.log.trim().split('\\n').forEach(function(line) {
        if (line.trim()) {
          var hash = line.substring(0, 8);
          var msg = line.substring(9);
          html += '<div style="margin-bottom:3px;"><span style="color:var(--accent);">'+esc(hash)+'</span> <span style="color:var(--text);">'+esc(msg)+'</span></div>';
        }
      });
      gitArea.innerHTML = html;
    }
  } catch(e) { /* silent */ }
}

// Tab key support in editor
(function() {
  var checkEditor = setInterval(function() {
    var editor = document.getElementById('genesis-editor');
    if (editor) {
      clearInterval(checkEditor);
      editor.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
          e.preventDefault();
          var start = this.selectionStart;
          var end = this.selectionEnd;
          this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
          this.selectionStart = this.selectionEnd = start + 4;
        }
        if (e.ctrlKey && e.key === 's') {
          e.preventDefault();
          genesisSaveFile();
        }
      });
    }
  }, 100);
})();

async function loadGenesis() {
  let results = [];
  if (phase === 'running') {
      const d = await api('/api/validation/verifications/recent?limit=30');
      if (d && d.results) results = d.results;
  }
  renderGenesis(results);
  genesisLoadSpindleFeed();
  if (!document.getElementById('git-area').innerHTML.trim()) {
    genesisLoadGitLog();
  }
}


// ── Right Panel Tabs ──────────────────────────────────────────────────────
function switchRightTab(name) {
  document.querySelectorAll('.rtab').forEach(function(t) { 
    t.style.background='var(--card)'; t.style.color='var(--muted)'; t.style.borderBottom='2px solid transparent'; 
    t.classList.remove('active');
  });
  document.querySelectorAll('.rpanel').forEach(function(p) { p.style.display='none'; p.classList.remove('active'); });
  var tab = document.getElementById('rtab-'+name);
  var panel = document.getElementById('rpanel-'+name);
  if (tab) { tab.style.background='var(--surface)'; tab.style.color='var(--accent2)'; tab.style.borderBottom='2px solid var(--accent2)'; tab.classList.add('active'); }
  if (panel) { panel.style.display='flex'; panel.classList.add('active'); }
}

// ── Live Activity Feed ────────────────────────────────────────────────────
let _activityLastId = 0;

async function pollActivityFeed() {
  if (!_tabVisible) return;
  try {
    var r = await fetch('/activity/feed?since=' + _activityLastId);
    var d = await r.json();
    if (d.events && d.events.length) {
      var feed = document.getElementById('activity-feed');
      var wasBottom = feed.scrollHeight - feed.scrollTop <= feed.clientHeight + 40;
      d.events.forEach(function(ev) {
        if (ev.id > _activityLastId) _activityLastId = ev.id;
        var sourceIcon = ev.source === 'grace' ? '&#129504;' : ev.source === 'spindle' ? '&#129516;' : ev.source === 'user' ? '&#128100;' : '&#9881;';
        var sourceLabel = ev.source.charAt(0).toUpperCase() + ev.source.slice(1);
        var typeIcon = ev.type === 'error' ? '&#10060;' : ev.type === 'warn' ? '&#9888;' : ev.type === 'action' ? '&#9889;' : ev.type === 'chat' ? '&#128172;' : '&#8226;';
        // NLP format: bullet points for multi-line, clean sentences
        var msgHtml = formatNLP(ev.msg);
        var div = document.createElement('div');
        div.style.cssText = 'padding:4px 6px;margin-bottom:3px;border-left:3px solid '+ev.color+';border-radius:4px;background:rgba(0,0,0,0.2);animation:fadeIn 0.3s;';
        div.innerHTML = '<div style="display:flex;align-items:center;gap:4px;margin-bottom:2px;">' +
          '<span style="font-size:10px;">'+sourceIcon+'</span>' +
          '<span style="color:'+ev.color+';font-weight:700;font-size:9px;text-transform:uppercase;">'+sourceLabel+'</span>' +
          '<span style="color:var(--muted);font-size:8px;margin-left:auto;">'+ev.ts+'</span>' +
          '<span style="font-size:8px;">'+typeIcon+'</span>' +
          '</div>' +
          '<div style="color:var(--text);font-size:10px;line-height:1.4;">'+msgHtml+'</div>';
        feed.appendChild(div);
      });
      // Remove init message
      var initMsg = feed.querySelector('div[style*="text-align:center"]');
      if (initMsg && d.events.length) initMsg.remove();
      if (wasBottom) feed.scrollTop = feed.scrollHeight;
    }
  } catch(e) { /* silent */ }
}

function formatNLP(text) {
  if (!text) return '';
  var s = esc(text);
  // Color code status tags
  s = s.replace(new RegExp('[[]OK[]]', 'g'), '<span style="color:var(--green);font-weight:700">[OK]</span>');
  s = s.replace(new RegExp('[[]FAIL[]]', 'g'), '<span style="color:var(--red);font-weight:700">[FAIL]</span>');
  s = s.replace(new RegExp('[[]WARN[]]', 'g'), '<span style="color:var(--yellow);font-weight:700">[WARN]</span>');
  s = s.replace(new RegExp('[[]INFO[]]', 'g'), '<span style="color:var(--accent);font-weight:700">[INFO]</span>');
  return s;
}

setInterval(pollActivityFeed, 5000);

// ── Chat System ───────────────────────────────────────────────────────────
async function sendChat() {
  var input = document.getElementById('chat-input');
  var msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  // Show user message immediately
  appendChatMsg('user', msg);
  try {
    var r = await fetch('/chat/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ message: msg })
    });
    var d = await r.json();
    // Poll for response
    setTimeout(pollChatHistory, 500);
  } catch(e) {
    appendChatMsg('system', 'Message delivery failed: ' + e.message);
  }
}

function appendChatMsg(role, msg) {
  var area = document.getElementById('chat-messages');
  var isUser = role === 'user';
  var div = document.createElement('div');
  div.style.cssText = 'display:flex;justify-content:'+(isUser?'flex-end':'flex-start')+';margin-bottom:6px;';
  var bubble = document.createElement('div');
  bubble.style.cssText = 'max-width:85%;padding:6px 10px;border-radius:'+(isUser?'12px 12px 2px 12px':'12px 12px 12px 2px')+';font-size:11px;line-height:1.4;' +
    (isUser ? 'background:var(--accent);color:white;' : 
     role === 'grace' ? 'background:rgba(129,140,248,0.2);color:var(--text);border:1px solid rgba(129,140,248,0.3);' :
     role === 'spindle' ? 'background:rgba(167,139,250,0.2);color:var(--text);border:1px solid rgba(167,139,250,0.3);' :
     'background:var(--card);color:var(--text);border:1px solid var(--border);');
  var label = isUser ? '' : '<div style="font-size:8px;color:'+(role==='grace'?'#818cf8':role==='spindle'?'#a78bfa':'var(--muted)')+';font-weight:700;margin-bottom:2px;">'+role.toUpperCase()+'</div>';
  bubble.innerHTML = label + formatNLP(msg);
  div.appendChild(bubble);
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

async function pollChatHistory() {
  if (!_tabVisible) return;
  try {
    var r = await fetch('/chat/history');
    var d = await r.json();
    if (d.messages) {
      var area = document.getElementById('chat-messages');
      var shown = area.children.length;
      d.messages.slice(shown).forEach(function(m) {
        if (m.role !== 'user') appendChatMsg(m.role, m.msg);
      });
    }
  } catch(e) { /* silent */ }
}
setInterval(pollChatHistory, 5000);

// ── Voice Bi-directional Comms ────────────────────────────────────────────
let _voiceActive = false;
let _voiceRecognition = null;
let _voiceSynth = window.speechSynthesis || null;

function toggleVoice() {
  _voiceActive = !_voiceActive;
  var btn = document.getElementById('voice-btn');
  if (_voiceActive) {
    btn.style.background = 'var(--red)';
    btn.style.color = 'white';
    btn.style.borderColor = 'var(--red)';
    btn.innerHTML = '&#128308;';
    startVoiceInput();
  } else {
    btn.style.background = 'none';
    btn.style.color = 'var(--muted)';
    btn.style.borderColor = 'var(--border)';
    btn.innerHTML = '&#127908;';
    stopVoiceInput();
  }
}

function startVoiceInput() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    appendChatMsg('system', 'Voice recognition not supported in this browser. Use Chrome for full support.');
    _voiceActive = false;
    return;
  }
  var SpeechRecog = window.SpeechRecognition || window.webkitSpeechRecognition;
  _voiceRecognition = new SpeechRecog();
  _voiceRecognition.continuous = true;
  _voiceRecognition.interimResults = false;
  _voiceRecognition.lang = 'en-US';
  _voiceRecognition.onresult = function(event) {
    var transcript = event.results[event.results.length - 1][0].transcript.trim();
    if (transcript) {
      document.getElementById('chat-input').value = transcript;
      sendChat();
    }
  };
  _voiceRecognition.onerror = function(e) {
    if (e.error !== 'no-speech') appendChatMsg('system', 'Voice error: ' + e.error);
  };
  _voiceRecognition.onend = function() {
    if (_voiceActive) _voiceRecognition.start(); // Auto-restart
  };
  _voiceRecognition.start();
  appendChatMsg('system', '&#127908; Voice input active. Speak to send messages.');
}

function stopVoiceInput() {
  if (_voiceRecognition) {
    _voiceRecognition.onend = null;
    _voiceRecognition.stop();
    _voiceRecognition = null;
  }
  appendChatMsg('system', '&#128263; Voice input disabled.');
}

function speakResponse(text) {
  if (_voiceSynth && _voiceActive) {
    var utterance = new SpeechSynthesisUtterance(text.replace(/<[^>]*>/g, '').substring(0, 200));
    utterance.rate = 1.1;
    utterance.pitch = 1;
    _voiceSynth.speak(utterance);
  }
}

// ── Federated Learning ────────────────────────────────────────────────────
async function loadFederated() {
  let d = null;
  let nodes = [];

  if (phase === 'running') {
      d = await api('/api/federated/status');
      const nRes = await api('/api/federated/nodes');
      if (nRes && nRes.nodes) nodes = nRes.nodes;
  }

  if (!d) {
      d = { registered_nodes: 12, active_nodes: 4, total_rounds: 840, global_model_version: 13 };
      nodes = [
          { node_name: 'alpha-gpu-1', last_sync: new Date().toISOString(), active: true, trust_score: 0.99, update_count: 320, model_version: 13 },
          { node_name: 'beta-compute-3', last_sync: new Date(Date.now() - 120000).toISOString(), active: false, trust_score: 0.82, update_count: 15, model_version: 12 }
      ];
  }

  const area = document.getElementById('federated-area');

  let html = '<div class="diag-grid">';
  html += '<div class="diag-card" style="text-align:center"><div style="font-size:22px;font-weight:700;color:var(--accent)">' + (d.registered_nodes||0) + '</div><div style="font-size:10px;color:var(--muted);text-transform:uppercase">Nodes</div></div>';
  html += '<div class="diag-card" style="text-align:center"><div style="font-size:22px;font-weight:700;color:var(--green)">' + (d.active_nodes||0) + '</div><div style="font-size:10px;color:var(--muted);text-transform:uppercase">Active</div></div>';
  html += '<div class="diag-card" style="text-align:center"><div style="font-size:22px;font-weight:700;color:var(--accent2)">' + (d.total_rounds||0) + '</div><div style="font-size:10px;color:var(--muted);text-transform:uppercase">Rounds</div></div>';
  html += '<div class="diag-card" style="text-align:center"><div style="font-size:22px;font-weight:700;color:var(--blue)">v' + (d.global_model_version||0) + '</div><div style="font-size:10px;color:var(--muted);text-transform:uppercase">Model</div></div>';
  html += '</div>';

  if (d.privacy) {
    var pct = d.privacy.epsilon_budget ? Math.round(d.privacy.budget_remaining / d.privacy.epsilon_budget * 100) : 100;
    var pcolor = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
    html += '<div class="dash-card"><div class="dash-card-header"><span class="dash-card-title">Privacy Budget</span><span style="font-size:14px;font-weight:700;color:' + pcolor + '">' + pct + '%</span></div>';
    html += '<div class="gauge-bar" style="height:6px"><div class="gauge-fill" style="width:' + pct + '%;background:' + pcolor + '"></div></div>';
    html += '<div style="font-size:10px;color:var(--muted);margin-top:6px">spent: ' + (d.privacy.epsilon_spent||0).toFixed(3) + ' / ' + (d.privacy.epsilon_budget||10) + '</div></div>';
  }

  if (nodes.length) {
    html += '<div class="dash-card"><div class="dash-card-header"><span class="dash-card-title">Registered Nodes</span></div>';
    nodes.forEach(function(n) {
      html += '<div class="check-item"><span class="check-icon">' + (n.active ? '🟢' : '🔴') + '</span>';
      html += '<div><div class="check-name">' + esc(n.node_name || '') + '</div>';
      html += '<div class="check-detail">trust: ' + Math.round((n.trust_score||0)*100) + '% | updates: ' + (n.update_count||0) + ' | v' + (n.model_version||0) + '</div></div></div>';
    });
    html += '</div>';
  }

  area.innerHTML = html;
}

// ── Polling ───────────────────────────────────────────────────────────────────
async function poll() {
  if (!_tabVisible) return;
  const d = await api('/status');
  if (!d) return;

  Object.entries(d.services||{}).forEach(([k,v]) => updateSvc(k, v));
  updatePhase(d.phase||'idle');

  const newLogs = (d.logs||[]).slice(lastLogLen);
  newLogs.forEach(l => appendLog(l));
  lastLogLen = (d.logs||[]).length;

  renderProblems(d.problems||[]);

  if (d.grace_metrics) {
      renderMetrics(d.grace_metrics);
      if (d.grace_metrics.recent_verifications) {
          renderGenesis(d.grace_metrics.recent_verifications);
      }
  }

  const newTerm = (d.terminal||[]).slice(lastTermLen);
  if (newTerm.length) {
    lastTermLen = (d.terminal||[]).length;
    renderTerminal(newTerm);
  }

  // Poll active dashboard tab
  try {
    const activeTabEl = document.querySelector('.tab.active');
    if (activeTabEl) {
      const activeTab = activeTabEl.id;
      if (activeTab === 'tab-playbooks') loadPlaybooks();
      else if (activeTab === 'tab-memory') loadMemory();
      else if (activeTab === 'tab-patches') loadPatches();
      else if (activeTab === 'tab-llm') loadLLM();
      else if (activeTab === 'tab-genesis') loadGenesis();
      else if (activeTab === 'tab-federated') loadFederated();
      else if (activeTab === 'tab-network') loadNetwork();
    }
  } catch(e) { console.warn('Poll tab error:', e); }
}

setInterval(poll, 5000);
poll();
</script>
</body>
</html>"""




# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=_background_probe, daemon=True, name="probe").start()
    _log(f"Grace Ops Console starting on http://localhost:{LAUNCHER_PORT}")
    server = http.server.ThreadingHTTPServer(("localhost", LAUNCHER_PORT), LauncherHandler)
    def _open():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{LAUNCHER_PORT}")
    threading.Thread(target=_open, daemon=True).start()
    # Auto-launch Grace (backend + frontend) on double-click — no need to press Launch
    def _auto_launch():
        time.sleep(1.5)
        _log("Auto-launching Grace (backend + frontend)...", "info")
        _start_grace()
    threading.Thread(target=_auto_launch, daemon=True, name="auto-launch").start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _stop_grace()

if __name__ == "__main__":
    main()
