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



# ── Logging ───────────────────────────────────────────────────────────────────
def _log(msg: str, level: str = "info"):
    ts = time.strftime("%H:%M:%S")
    entry = {"ts": ts, "level": level, "msg": msg}
    with _log_lock:
        _log_buffer.append(entry)
        if len(_log_buffer) > LOG_BUFFER_MAX:
            _log_buffer.pop(0)
    print(f"[{ts}][{level.upper()}] {msg}", flush=True)

    # Auto-detect problems from log lines
    low = msg.lower()
    if "winerror 10013" in low or "access to a socket" in low.replace("\n", ""):
        _add_problem("critical", "Port Conflict (WinError 10013)",
                     "Grace couldn't bind to its port — another process is using it.",
                     fix_action="kill_port")
    elif "error" in low and ("failed" in low or "exception" in low):
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
    ports_to_watch = [GRACE_PORT, FRONTEND_PORT, 5432, 6333, 11434]
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

def _check_postgres() -> str:
    try:
        s = socket.create_connection(("localhost", 5432), timeout=2)
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
    try:
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
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

def _background_probe():
    while True:
        _probe_all()
        if _status["services"]["backend"] == "online":
            _fetch_grace_metrics()
        time.sleep(8)


# ── Grace startup ─────────────────────────────────────────────────────────────
def _start_grace():
    global _grace_process, _frontend_process
    if _grace_process and _grace_process.poll() is None:
        _log("Grace is already running", "warn")
        return

    _status["phase"] = "booting"
    _problems.clear()
    _log("=== Grace 3.1 Boot Sequence Starting ===", "info")

    # Pre-flight: kill any stale process on port 8000
    if _port_in_use(GRACE_PORT):
        _log(f"Port {GRACE_PORT} is in use — clearing it...", "warn")
        _kill_port(GRACE_PORT)
        time.sleep(1.5)

    # Service pre-check
    _log("Checking services...", "info")
    _probe_all()
    for svc, state in _status["services"].items():
        icon = "OK" if state == "online" else "WARN"
        _log(f"  [{icon}] {svc}: {state}", "info" if state == "online" else "warn")

    python = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    _log(f"Starting Grace backend...", "info")
    try:
        _grace_process = subprocess.Popen(
            [python, "-m", "uvicorn", "app:app",
             "--host", "0.0.0.0", "--port", str(GRACE_PORT),
             "--log-level", "info"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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
            bufsize=1,
        )

    def _stream_logs(proc):
        tb_lines = []
        in_tb = False
        has_triggered_heal = False
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
                
            if "Traceback (most recent call last):" in line:
                in_tb = True
                tb_lines = [line]
            elif in_tb:
                tb_lines.append(line)
                if not line.startswith(" ") and ("Error:" in line or "Exception:" in line):
                    in_tb = False
                    crash_detail = "\n".join(tb_lines)
                    _add_problem("critical", f"Backend Crash: {line}", crash_detail, fix_action="spindle-heal")
                    
                    if not has_triggered_heal:
                        has_triggered_heal = True
                        prompt = (
                            f"The Grace Backend crashed on boot with the following error:\n"
                            f"{crash_detail}\n\n"
                            f"Analyze this traceback gracefully. If the fix requires modifying python code, write the modified code to the file directly. Ensure your fix is actually executed! DO NOT just define a function in the sandbox, you MUST execute the file I/O or the sandbox modification to save the fix."
                        )
                        _log("Autonomously triggering Spindle Meta-Healing for backend crash...", "warn")
                        _run_terminal_command(f"/code {prompt}")

            level = "error" if any(x in line.lower() for x in ["error", "exception", "critical"]) else \
                    "warn"  if "warning" in line.lower() else "info"
            _log(line, level)
        _log("Grace backend process ended", "warn")
        _status["phase"] = "stopped"
        _status["services"]["backend"] = "offline"

    threading.Thread(target=_stream_logs, args=(_grace_process,),
                     daemon=True, name="grace-log").start()

    # Wait for ready
    _log("Waiting for Grace backend...", "info")
    for attempt in range(40):
        time.sleep(2)
        if _check_backend() == "online":
            _status["services"]["backend"] = "online"
            _log(f"Grace backend LIVE at http://localhost:{GRACE_PORT}", "info")
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
                     "--log-level", "info"],
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
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self._html(UI_HTML)
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
        elif self.path == "/fix/kill-port":

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
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);height:100vh;display:grid;grid-template-rows:56px 1fr;overflow:hidden;}

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
.sec-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-bottom:8px;}

/* Services */
.svc{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 10px;display:flex;align-items:center;gap:8px;margin-bottom:5px;cursor:default;transition:border-color .2s;}
.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;transition:all .3s;}
.dot-online{background:var(--green);box-shadow:0 0 6px var(--green);}
.dot-offline{background:var(--red);}
.dot-unknown,.dot-degraded{background:var(--yellow);}
.svc-label{font-size:12px;font-weight:500;flex:1;}
.svc-tag{font-size:9px;padding:2px 7px;border-radius:10px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;}
.tag-online{background:#052e16;color:var(--green);}
.tag-offline{background:#2a0a0a;color:var(--red);}
.tag-unknown,.tag-degraded{background:#2a1e05;color:var(--yellow);}

/* Buttons */
.btn{width:100%;padding:10px 14px;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;transition:all .2s;margin-bottom:6px;}
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
.tab{padding:12px 14px;font-size:11px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;color:var(--muted);transition:all .2s;position:relative;white-space:nowrap;}
.tab:hover{color:var(--text);}
.tab.active{color:var(--accent);border-bottom-color:var(--accent);}
.tab-badge{background:var(--red);color:#fff;border-radius:8px;padding:1px 5px;font-size:9px;font-weight:700;margin-left:5px;}

/* Log panel */
.log-area{flex:1;overflow-y:auto;padding:12px 16px;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.65;background:var(--bg);}
.log-line{display:flex;gap:10px;padding:1px 0;}
.log-ts{color:#2d3e6a;flex-shrink:0;font-size:9.5px;padding-top:1px;}
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
.prob-title{font-size:13px;font-weight:600;flex:1;}
.prob-count{font-size:10px;color:var(--muted);}
.prob-detail{font-size:11px;color:var(--muted);margin-bottom:8px;font-family:'JetBrains Mono',monospace;}
.prob-ts{font-size:10px;color:#2d3e6a;}
.prob-fix{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:4px 12px;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;}
.prob-fix:hover{background:var(--accent2);}

/* Genesis Feed */
.genesis-item { background:var(--surface2); border:1px solid #2d3e6a; padding:10px; border-radius:8px; margin-bottom:8px; font-family:'JetBrains Mono',monospace; font-size:10.5px; border-left:3px solid var(--blue); }
.genesis-ts { color:var(--muted); font-size:9px; float:right; }

/* Dashboard Cards (Playbooks, Memory, Patches, LLM) */
.dash-card { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:10px; }
.dash-card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.dash-card-title { font-size:12px; font-weight:600; color:#fff; }
.dash-badge { padding:2px 8px; border-radius:12px; font-size:9px; font-weight:700; text-transform:uppercase; }
.badge-active { background:#052e16; color:var(--green); border:1px solid #064e3b; }
.badge-idle { background:#1e293b; color:var(--muted); border:1px solid #334155; }
.dash-timeline { border-left:2px solid var(--border); margin-left:8px; padding-left:14px; position:relative; }
.timeline-dot { position:absolute; left:-6px; top:4px; width:10px; height:10px; border-radius:50%; background:var(--surface); border:2px solid var(--accent); }
.timeline-item { margin-bottom:12px; font-size:11px; }
.timeline-ts { font-size:9px; color:var(--muted); font-family:'JetBrains Mono',monospace; }

/* Revert Button */
.btn-revert { background:#450a0a; color:#fca5a5; border:1px solid #7f1d1d; border-radius:4px; padding:3px 8px; font-size:9.5px; font-weight:600; cursor:pointer; cursor:pointer; transition:all 0.15s; }
.btn-revert:hover { background:#7f1d1d; color:#fff; }

/* Network Grid */
.net-grid { display:grid; grid-template-columns: 1fr 2fr 1fr 1fr; gap:6px; font-size:11px; font-family:'JetBrains Mono',monospace; margin-bottom:10px; }
.net-row { display:contents; }
.net-row > div { background:var(--surface); padding:8px 12px; border-bottom:1px solid var(--border); }
.net-header > div { font-weight:700; color:var(--muted); border-bottom:none;text-transform:uppercase;font-size:9px;background:none;}

/* Mini-Terminal */
.terminal-block{width:400px;border-left:1px solid var(--border);border-top:none;background:#020617;display:flex;flex-direction:column;font-family:'JetBrains Mono',monospace;}
.term-header{background:#0f172a;padding:4px 12px;font-size:10px;font-weight:600;color:var(--muted);display:flex;justify-content:space-between;border-bottom:1px solid #1e293b;}
.term-output{flex:1;overflow-y:auto;padding:8px 12px;font-size:11px;color:#a5b4fc;}
.term-line-sys{color:#94a3b8;}
.term-line-user{color:#38bdf8;}
.term-input{display:flex;border-top:1px solid #1e293b;}
.term-input span{padding:8px 4px 8px 12px;color:var(--green);font-size:12px;font-weight:700;}
.term-input input{flex:1;background:none;border:none;color:#e2e8f0;font-family:'JetBrains Mono',monospace;font-size:12px;padding:8px;outline:none;}

/* Diagnostics & Metrics */
.diag-panel{flex:1;overflow-y:auto;padding:14px 16px;background:var(--bg);}
.diag-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}
.diag-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px;}
.diag-card h4{font-size:11px;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px;}
.check-item{display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;}
.check-icon{flex-shrink:0;font-size:13px;}
.check-name{font-size:12px;font-weight:500;}
.check-detail{font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace;}

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
</style>
</head>
<body>
<script>
// SPINDLE FRONTEND WIRING: Catch unhandled UI errors and pipe them to the builder
window.onerror = function(msg, url, line, col, error) {
  const errPayload = {
    msg: msg,
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
  t.innerHTML = "<b>Spindle Alert:</b> UI Error reported.<br>" + msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 5000);
  return false;
};
window.addEventListener('unhandledrejection', function(event) {
  window.onerror(event.reason, null, 0, 0, event.reason);
});
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
    <button class="btn btn-primary" id="btn-start" onclick="startGrace()">⚡ Launch Grace</button>
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
      <div class="problems-panel" id="problems-area">
        <div class="prob-empty" id="prob-empty">✅ No problems detected</div>
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

    <!-- Genesis Feed -->
    <div id="panel-genesis" class="panel" style="flex:1;overflow:hidden;">
      <div class="metrics-panel" id="genesis-area">
        <div class="no-metrics">🔑 Genesis Keys feed appears here when Grace is running</div>
      </div>
    </div>
  </div>

  <!-- Terminal Block -->
  <div class="terminal-block">
    <div class="term-header">
      <div>>_ Grace Shell (cmd.exe)</div>
      <div style="cursor:pointer;" onclick="document.getElementById('term-area').innerHTML=''">Clear</div>
    </div>
    <div class="term-output" id="term-area">
      <div class="term-line-sys">Grace Shell initialized. Connected to project root.</div>
    </div>
    <div class="term-input">
      <span>$</span>
      <input type="text" id="term-input-box" placeholder="Run scripts, commands, or tests here..." onkeypress="handleTerm(event)">
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
async function startGrace() {
  await api('/start', 'POST');
  updatePhase('booting');
}
async function stopGrace() { await api('/stop', 'POST'); }
async function restartGrace() { await api('/fix/restart', 'POST'); }
async function openFrontend() { await api('/open-frontend', 'POST'); }
async function openDocs() { await api('/open-api-docs', 'POST'); }
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

function renderGenesis(verifications) {
  const area = document.getElementById('genesis-area');
  if (!verifications || !verifications.length) return;
  area.innerHTML = '';
  verifications.forEach(v => {
    area.innerHTML += `
      <div class="genesis-item">
        <span class="genesis-ts" style="color:${v.is_error ? 'var(--red)' : 'var(--muted)'}">${v.created_at.replace('T',' ').split('.')[0] || ''}</span>
        <strong style="color:var(--accent2)">[${v.is_error ? 'FAIL' : 'OK'}]</strong> ${esc(v.description)}
      </div>
    `;
  });
}

async function loadPlaybooks() {
  if (phase !== 'running') return;
  const d = await api('/api/validation/playbooks/active');
  if (!d) return;
  const area = document.getElementById('playbooks-area');
  const activeKeys = Object.keys(d.active || {});
  
  if (!activeKeys.length && !(d.recent_history||[]).length) {
    area.innerHTML = '<div class="no-metrics">No active playbooks</div>';
    return;
  }
  
  let html = '';
  if (activeKeys.length) {
    html += `<div class="dash-card" style="border-color:var(--red)">
      <div class="dash-card-header">
        <span class="dash-card-title">🚨 Active Mitigation</span>
        <span class="dash-badge badge-active">RUNNING</span>
      </div>
      <div class="dash-timeline">`;
    activeKeys.forEach(k => {
      html += `<div class="timeline-item"><div class="timeline-dot" style="background:var(--red);border-color:#7f1d1d"></div>
        <div class="timeline-ts">Just now</div>
        <div style="color:#fca5a5;font-family:'JetBrains Mono',monospace">${esc(k)}</div>
        <div style="color:var(--muted);font-size:10px;margin-top:2px">${esc(d.active[k]||'Processing...')}</div>
      </div>`;
    });
    html += `</div></div>`;
  }
  
  if ((d.recent_history||[]).length) {
    html += `<div class="dash-card">
      <div class="dash-card-header"><span class="dash-card-title">Recent History</span></div>
      <div class="dash-timeline">`;
    [...d.recent_history].reverse().slice(0, 10).forEach(h => {
      html += `<div class="timeline-item"><div class="timeline-dot" style="border-color:var(--muted)"></div>
        <div style="color:var(--text);font-family:'JetBrains Mono',monospace">${esc(h.playbook_id)}</div>
        <div style="color:var(--green);font-size:10px;margin-top:2px">✓ Completed</div>
      </div>`;
    });
    html += `</div></div>`;
  }
  area.innerHTML = html;
}

async function loadMemory() {
  if (phase !== 'running') return;
  const d = await api('/api/validation/memory/stream');
  if (!d || !d.stats) return;
  const area = document.getElementById('memory-area');
  
  let html = `<div class="diag-grid">`;
  Object.entries(d.stats).forEach(([k,v]) => {
     html += `<div class="diag-card" style="text-align:center">
       <div style="font-size:16px;font-weight:700;color:var(--accent)">${v}</div>
       <div style="font-size:10px;color:var(--muted);text-transform:uppercase">${k} Items</div>
     </div>`;
  });
  html += `</div>
  <div class="dash-card">
    <div class="dash-card-header"><span class="dash-card-title">Live Ingestion</span><span class="dash-badge badge-active">LISTENING</span></div>
    <div class="dash-timeline">
      <div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-ts">Listening for new vectors...</div></div>
    </div>
  </div>`;
  area.innerHTML = html;
}

async function loadPatches() {
  if (phase !== 'running') return;
  const d = await api('/api/validation/patches/recent');
  if (!d) return;
  const area = document.getElementById('patches-area');
  
  if (!(d.patches||[]).length) {
    area.innerHTML = '<div class="no-metrics">No code patches applied this session</div>';
    return;
  }
  
  let html = '';
  [...d.patches].reverse().forEach(p => {
    html += `<div class="dash-card">
      <div class="dash-card-header">
        <span class="dash-card-title" style="font-family:'JetBrains Mono',monospace;color:var(--accent2)">${esc(p.file)}</span>
        <button class="btn-revert" onclick="revertPatch('${p.id}')">↺ Revert Patch</button>
      </div>
      <div style="font-size:10.5px;color:var(--muted);margin-bottom:6px">${esc(p.reason)}</div>
      <div style="background:#020617;padding:8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--green);max-height:80px;overflow-y:auto">
        + ${esc(p.summary || 'Code injected successfully')}
      </div>
    </div>`;
  });
  area.innerHTML = html;
}

async function revertPatch(id) {
  const r = await api('/api/validation/revert-patch?patch_id=' + id, 'POST');
  if (r && r.error) alert("Revert failed: " + r.error);
  else { alert("Patch reverted successfully."); loadPatches(); }
}

async function loadLLM() {
  if (phase !== 'running') return;
  const d = await api('/api/validation/llm/monitor');
  if (!d) return;
  const area = document.getElementById('llm-area');
  
  if (!(d.calls||[]).length) {
    area.innerHTML = '<div class="no-metrics">No API calls monitored yet</div>';
    return;
  }
  
  let html = '';
  d.calls.forEach(c => {
    const isWarn = c.trust_score < 0.6;
    html += `<div class="dash-card" style="${isWarn ? 'border-left:3px solid var(--red)' : 'border-left:3px solid var(--green)'}">
      <div class="dash-card-header">
        <span class="dash-card-title">LLM Call</span>
        <span style="font-size:11px;font-weight:700;color:${isWarn ? 'var(--red)' : 'var(--green)'}">Trust: ${c.trust_score ? Math.round(c.trust_score*100)+'%' : 'N/A'}</span>
      </div>
      <div style="font-size:11px;color:var(--text);margin-bottom:4px">${esc(c.description)}</div>
      <div class="timeline-ts">${c.created_at.replace('T',' ').split('.')[0]}</div>
    </div>`;
  });
  area.innerHTML = html;
}

// ── Polling ───────────────────────────────────────────────────────────────────
async function poll() {
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

  // Poll active dashboard tab if Grace is running
  if (phase === 'running') {
    const activeTab = document.querySelector('.tab.active').id;
    if (activeTab === 'tab-playbooks') loadPlaybooks();
    else if (activeTab === 'tab-memory') loadMemory();
    else if (activeTab === 'tab-patches') loadPatches();
    else if (activeTab === 'tab-llm') loadLLM();
  }
}

setInterval(poll, 2500);
poll();
</script>
</body>
</html>"""




# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    threading.Thread(target=_background_probe, daemon=True, name="probe").start()
    _log(f"Grace Dev Console starting on http://localhost:{LAUNCHER_PORT}")
    server = http.server.ThreadingHTTPServer(("localhost", LAUNCHER_PORT), LauncherHandler)
    def _open():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{LAUNCHER_PORT}")
    threading.Thread(target=_open, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _stop_grace()

if __name__ == "__main__":
    main()
