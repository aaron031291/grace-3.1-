"""
Production Safety — the 4 critical gaps identified by Kimi+Opus.

1. Multi-step rollback (undo chains when hot-reload breaks things)
2. Security scanning (detect code injection in generated code)
3. Budget circuit breaker (hard token/cost limits)
4. Provenance ledger (cryptographic hash chain for audit)
"""

import hashlib
import json
import time
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import deque

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  1. MULTI-STEP ROLLBACK
# ═══════════════════════════════════════════════════════════════════

MAX_SNAPSHOT_SIZE_MB = 50  # Max total snapshot storage
_rollback_stack: deque = deque(maxlen=20)  # Reduced from 100 to prevent RAM bloat
_rollback_lock = threading.Lock()


def snapshot_state(label: str = "") -> str:
    """Take a snapshot of critical files for rollback."""
    snapshot_id = f"SNAP-{int(time.time())}"
    snapshot = {"id": snapshot_id, "label": label, "ts": datetime.now(timezone.utc).isoformat(), "files": {}}

    root = Path(__file__).parent.parent
    critical = ["app.py", "api/brain_api_v2.py"] + \
               [str(f.relative_to(root)) for f in (root / "core" / "services").glob("*.py")] + \
               [str(f.relative_to(root)) for f in (root / "core").glob("*.py") if f.is_file()]

    for f in critical[:30]:
        fp = root / f
        if fp.exists():
            try:
                snapshot["files"][f] = fp.read_text(errors="ignore")
            except Exception:
                pass

    with _rollback_lock:
        # Size-based eviction — remove oldest if total exceeds limit
        total_size = sum(
            sum(len(c) for c in s.get("files", {}).values())
            for s in _rollback_stack
        )
        snapshot_size = sum(len(c) for c in snapshot["files"].values())

        while total_size + snapshot_size > MAX_SNAPSHOT_SIZE_MB * 1024 * 1024 and _rollback_stack:
            evicted = _rollback_stack.popleft()
            total_size -= sum(len(c) for c in evicted.get("files", {}).values())

        _rollback_stack.append(snapshot)

    return snapshot_id


def rollback_to(snapshot_id: str = None) -> dict:
    """Rollback to a snapshot. If no ID, rollback to last."""
    with _rollback_lock:
        if not _rollback_stack:
            return {"error": "No snapshots available"}

        if snapshot_id:
            snapshot = next((s for s in _rollback_stack if s["id"] == snapshot_id), None)
        else:
            snapshot = _rollback_stack[-1]

        if not snapshot:
            return {"error": f"Snapshot {snapshot_id} not found"}

    root = Path(__file__).parent.parent
    restored = 0
    for filepath, content in snapshot["files"].items():
        try:
            (root / filepath).write_text(content, encoding="utf-8")
            restored += 1
        except Exception:
            pass

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Rollback to {snapshot['id']}: {restored} files restored",
              who="safety.rollback", tags=["rollback", "safety"])
    except Exception:
        pass

    return {"rolled_back": True, "snapshot_id": snapshot["id"], "files_restored": restored}


def list_snapshots() -> list:
    with _rollback_lock:
        return [{"id": s["id"], "label": s["label"], "ts": s["ts"],
                 "files": len(s["files"])} for s in _rollback_stack]


# ═══════════════════════════════════════════════════════════════════
#  2. SECURITY SCANNING
# ═══════════════════════════════════════════════════════════════════

DANGEROUS_PATTERNS = [
    ("exec(", "code_execution", "critical"),
    ("eval(", "code_execution", "critical"),
    ("__import__('os')", "os_import", "critical"),
    ("subprocess.call", "subprocess", "high"),
    ("subprocess.Popen", "subprocess", "high"),
    ("os.system(", "os_system", "critical"),
    ("os.popen(", "os_popen", "critical"),
    ("shutil.rmtree", "recursive_delete", "high"),
    ("open('/etc", "filesystem_access", "high"),
    ("rm -rf", "destructive_command", "critical"),
    ("DROP TABLE", "sql_drop", "critical"),
    ("DELETE FROM", "sql_delete", "high"),
    ("pickle.loads", "deserialization", "high"),
    ("yaml.load(", "unsafe_yaml", "medium"),
    ("__builtins__", "builtin_access", "high"),
    ("ctypes", "native_code", "high"),
    ("socket.socket", "raw_socket", "medium"),
    ("requests.get(f'http://{", "ssrf_risk", "medium"),
]


def scan_code_security(code: str, filepath: str = "") -> dict:
    """Scan generated code for security vulnerabilities."""
    findings = []
    lines = code.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, vuln_type, severity in DANGEROUS_PATTERNS:
            if pattern in line:
                findings.append({
                    "line": i + 1,
                    "pattern": pattern,
                    "type": vuln_type,
                    "severity": severity,
                    "code": stripped[:80],
                    "file": filepath,
                })

    blocked = any(f["severity"] == "critical" for f in findings)

    if findings:
        try:
            from api._genesis_tracker import track
            track(key_type="error", what=f"Security scan: {len(findings)} findings in {filepath}",
                  who="safety.security_scan", is_error=blocked,
                  output_data={"findings": len(findings), "critical": sum(1 for f in findings if f["severity"] == "critical")},
                  tags=["security", "scan", "generated_code"])
        except Exception:
            pass

    return {"safe": len(findings) == 0, "blocked": blocked,
            "findings": findings, "total": len(findings)}


# ═══════════════════════════════════════════════════════════════════
#  3. BUDGET CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════

_budget = {
    "total_calls": 0,
    "total_tokens_est": 0,
    "limit_calls_per_hour": 500,
    "limit_tokens_per_hour": 500000,
    "window_start": time.time(),
    "blocked": 0,
}
_budget_lock = threading.Lock()


def check_budget() -> bool:
    """Check if we're within budget. Returns True if allowed."""
    with _budget_lock:
        now = time.time()
        if now - _budget["window_start"] > 3600:
            _budget["total_calls"] = 0
            _budget["total_tokens_est"] = 0
            _budget["window_start"] = now

        if _budget["total_calls"] >= _budget["limit_calls_per_hour"]:
            _budget["blocked"] += 1
            return False
        if _budget["total_tokens_est"] >= _budget["limit_tokens_per_hour"]:
            _budget["blocked"] += 1
            return False
        return True


def record_usage(tokens: int = 0):
    """Record an API call for budget tracking."""
    with _budget_lock:
        _budget["total_calls"] += 1
        _budget["total_tokens_est"] += tokens


def get_budget_status() -> dict:
    with _budget_lock:
        remaining_calls = max(0, _budget["limit_calls_per_hour"] - _budget["total_calls"])
        remaining_tokens = max(0, _budget["limit_tokens_per_hour"] - _budget["total_tokens_est"])
        elapsed = time.time() - _budget["window_start"]
        return {
            **_budget,
            "remaining_calls": remaining_calls,
            "remaining_tokens": remaining_tokens,
            "window_elapsed_minutes": round(elapsed / 60, 1),
        }


def set_budget_limits(calls_per_hour: int = None, tokens_per_hour: int = None):
    with _budget_lock:
        if calls_per_hour:
            _budget["limit_calls_per_hour"] = calls_per_hour
        if tokens_per_hour:
            _budget["limit_tokens_per_hour"] = tokens_per_hour
    return get_budget_status()


# ═══════════════════════════════════════════════════════════════════
#  4. PROVENANCE LEDGER — cryptographic hash chain
# ═══════════════════════════════════════════════════════════════════

LEDGER_PATH = Path(__file__).parent.parent / "data" / "provenance_ledger.jsonl"
_prev_hash = "0" * 64


def record_provenance(action: str, content_hash: str, model: str = "",
                      prompt_hash: str = "", metadata: dict = None) -> dict:
    """Record a provenance entry with cryptographic hash chain."""
    global _prev_hash

    entry = {
        "seq": int(time.time() * 1000),
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "content_hash": content_hash,
        "model": model,
        "prompt_hash": prompt_hash,
        "prev_hash": _prev_hash,
        "metadata": metadata or {},
    }

    entry_str = json.dumps(entry, sort_keys=True, default=str)
    entry["hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
    _prev_hash = entry["hash"]

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    return {"hash": entry["hash"], "seq": entry["seq"]}


def verify_ledger() -> dict:
    """Verify the hash chain integrity."""
    if not LEDGER_PATH.exists():
        return {"valid": True, "entries": 0}

    entries = []
    prev = "0" * 64
    broken_at = None

    for line in LEDGER_PATH.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
            if entry.get("prev_hash") != prev:
                broken_at = entry.get("seq")
                break
            prev = entry.get("hash", "")
            entries.append(entry["seq"])
        except Exception:
            break

    return {
        "valid": broken_at is None,
        "entries": len(entries),
        "broken_at": broken_at,
    }


def get_ledger_entries(limit: int = 20) -> list:
    if not LEDGER_PATH.exists():
        return []
    lines = LEDGER_PATH.read_text().strip().split("\n")
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries
