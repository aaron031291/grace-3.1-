"""
Ghost Enforcer — Real-time filesystem bouncer for Grace 3.1

An independent background daemon that watches file changes in real-time
and enforces integrity rules. Acts as the "bouncer" that KPI/Governance
SHOULD have been but couldn't be because external agents bypass them.

Architecture:
    File change detected (watchdog)
        → Was it made through the sanctioned pipeline? (genesis key check)
        → Is the file in a protected zone? (critical file list)
        → Has trust dropped below threshold? (KPI check)
        → If unauthorized: flag, alert, optionally revert

This closes the #1 bypass vector: external coding agents writing
files directly to disk without going through L1→L9 or Spindle.
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

logger = logging.getLogger("ghost_enforcer")

# ── Config ────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Files that should NEVER be modified without pipeline approval
CRITICAL_FILES = {
    "backend/app.py",
    "backend/settings.py",
    "backend/database/connection.py",
    "backend/database/session.py",
    "backend/database/migration.py",
    "backend/guardian/action_gate.py",
    "backend/guardian/ghost_enforcer.py",
    "backend/security/governance.py",
    "backend/cognitive/spindle_executor.py",
    "backend/cognitive/spindle_checkpoint.py",
    "backend/grace_os/config/layer_permissions.yaml",
    "backend/grace_os/layers/l8_verification/verification_layer.py",
    "backend/grace_mcp/client.py",
    "backend/core/file_artifact_tracker.py",
    ".github/workflows/ci.yml",
    "grace_launcher.py",
}

# Directories to skip entirely (noisy, non-code)
IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "venv_gpu",
    ".pytest_cache", "logs", "cache", "mcp_repos", "__grACE_shadow",
    ".grace", "qdrant_storage", "data", "tmp", "sandbox_lab",
    "knowledge_base", "layer_1", "learning memory-ai reaseach",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".log", ".bak", ".tmp", ".db", ".db-shm", ".db-wal",
}

# How long to wait before checking if a change has a genesis key (seconds)
GENESIS_KEY_GRACE_PERIOD = 5.0

# Trust threshold — below this, block deploys and alert
TRUST_BLOCK_THRESHOLD = 0.35


# ── Violation Record ──────────────────────────────────────────────────────

class Violation:
    """Record of an unauthorized file modification."""

    def __init__(self, path: str, change_type: str, severity: str,
                 reason: str, reverted: bool = False):
        self.path = path
        self.change_type = change_type  # modified, created, deleted
        self.severity = severity        # critical, warning, info
        self.reason = reason
        self.reverted = reverted
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.file_hash = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "severity": self.severity,
            "reason": self.reason,
            "reverted": self.reverted,
            "timestamp": self.timestamp,
        }


# ── Ghost Enforcer ────────────────────────────────────────────────────────

class GhostEnforcer(FileSystemEventHandler):
    """
    Real-time filesystem bouncer.

    Watches for file changes, checks if they came through the sanctioned
    pipeline (have a corresponding genesis key), and flags/reverts
    unauthorized modifications to critical files.
    """

    def __init__(
        self,
        watch_path: Optional[str] = None,
        auto_revert_critical: bool = False,
        on_violation: Optional[Callable] = None,
    ):
        self.watch_path = Path(watch_path or str(PROJECT_ROOT))
        self.auto_revert_critical = auto_revert_critical
        self.on_violation = on_violation  # External callback (e.g., launcher)

        self._observer: Optional[Observer] = None
        self._violations: List[Violation] = []
        self._violations_lock = threading.Lock()
        self._recent_pipeline_writes: Dict[str, float] = {}
        self._pipeline_lock = threading.Lock()
        self._file_snapshots: Dict[str, str] = {}  # path → sha256
        self._snapshot_lock = threading.Lock()
        self._debounce: Dict[str, float] = {}
        self._stats = {
            "files_watched": 0,
            "changes_detected": 0,
            "violations_flagged": 0,
            "auto_reverted": 0,
            "pipeline_approved": 0,
        }
        self._running = False
        self._started_at: Optional[float] = None
        # Boot grace period — don't flag during first 30s of startup
        self._boot_grace_until = time.time() + 30

        # Take initial snapshots of critical files
        self._snapshot_critical_files()

    # ── Snapshot Management ───────────────────────────────────────────────

    def _snapshot_critical_files(self):
        """Take SHA-256 snapshots of all critical files for rollback."""
        for rel_path in CRITICAL_FILES:
            full_path = self.watch_path / rel_path
            if full_path.exists():
                try:
                    h = self._hash_file(full_path)
                    with self._snapshot_lock:
                        self._file_snapshots[rel_path] = h
                except Exception:
                    pass
        logger.info(
            "[GHOST] Snapshotted %d critical files", len(self._file_snapshots)
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA-256 of file contents."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # ── Pipeline Registration ─────────────────────────────────────────────

    def register_pipeline_write(self, file_path: str):
        """
        Call this BEFORE writing a file through the sanctioned pipeline.
        The ghost enforcer will then approve the change when watchdog fires.
        """
        rel = self._to_rel(file_path)
        with self._pipeline_lock:
            self._recent_pipeline_writes[rel] = time.time()

    def _is_pipeline_approved(self, rel_path: str) -> bool:
        """Check if a file change was pre-registered by the pipeline."""
        with self._pipeline_lock:
            ts = self._recent_pipeline_writes.get(rel_path)
            if ts and (time.time() - ts) < GENESIS_KEY_GRACE_PERIOD * 2:
                del self._recent_pipeline_writes[rel_path]
                return True
        return False

    # ── Path Helpers ──────────────────────────────────────────────────────

    def _to_rel(self, path: str) -> str:
        """Convert absolute path to project-relative path."""
        try:
            return str(Path(path).relative_to(self.watch_path)).replace("\\", "/")
        except ValueError:
            return path.replace("\\", "/")

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored entirely."""
        parts = Path(path).parts
        for part in parts:
            if part in IGNORE_DIRS:
                return True
        ext = Path(path).suffix
        if ext in IGNORE_EXTENSIONS:
            return True
        return False

    def _is_critical(self, rel_path: str) -> bool:
        """Check if a file is in the critical protection list."""
        return rel_path in CRITICAL_FILES

    # ── Watchdog Event Handlers ───────────────────────────────────────────

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "modified")

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "created")

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "deleted")

    def _handle_change(self, src_path: str, change_type: str):
        """Core handler for all file changes."""
        if self._should_ignore(src_path):
            return

        rel_path = self._to_rel(src_path)

        # Debounce — editors trigger multiple events per save
        now = time.time()
        last = self._debounce.get(rel_path, 0)
        if now - last < 2.0:
            return
        self._debounce[rel_path] = now

        self._stats["changes_detected"] += 1

        # Boot grace period — don't flag during startup
        if now < self._boot_grace_until:
            return

        # Check if this change was pre-registered by the pipeline
        if self._is_pipeline_approved(rel_path):
            self._stats["pipeline_approved"] += 1
            logger.debug("[GHOST] Pipeline-approved: %s", rel_path)
            # Update snapshot for approved changes
            if change_type != "deleted":
                full_path = self.watch_path / rel_path
                if full_path.exists() and self._is_critical(rel_path):
                    try:
                        with self._snapshot_lock:
                            self._file_snapshots[rel_path] = self._hash_file(full_path)
                    except Exception:
                        pass
            return

        # Check if it's a genesis-key-tracked change (async — check after grace period)
        # For now, check immediately via genesis key lookup
        has_genesis_key = self._check_genesis_key(rel_path)
        if has_genesis_key:
            self._stats["pipeline_approved"] += 1
            return

        # ── UNAUTHORIZED CHANGE DETECTED ──────────────────────────────

        is_critical = self._is_critical(rel_path)
        severity = "critical" if is_critical else "warning"

        reason = (
            f"File {change_type} outside sanctioned pipeline"
            + (" (CRITICAL FILE)" if is_critical else "")
        )

        violation = Violation(
            path=rel_path,
            change_type=change_type,
            severity=severity,
            reason=reason,
        )

        with self._violations_lock:
            self._violations.append(violation)
            # Keep last 500 violations
            if len(self._violations) > 500:
                self._violations = self._violations[-300:]

        self._stats["violations_flagged"] += 1
        logger.warning("[GHOST] %s: %s (%s)", severity.upper(), rel_path, reason)

        # Auto-revert critical files if enabled
        if is_critical and self.auto_revert_critical and change_type == "modified":
            self._auto_revert(rel_path, violation)

        # Fire external callback (e.g., to launcher problems panel)
        if self.on_violation:
            try:
                self.on_violation(violation)
            except Exception:
                pass

        # Emit event to cognitive bus
        self._emit_event(violation)

    # ── Genesis Key Check ─────────────────────────────────────────────────

    def _check_genesis_key(self, rel_path: str) -> bool:
        """Check if a recent genesis key exists for this file change."""
        try:
            from genesis.genesis_key_service import GenesisKeyService
            gks = GenesisKeyService()
            # Look for genesis keys created in the last 10 seconds for this file
            recent_keys = gks.query_keys(
                where_location=rel_path,
                limit=1,
            )
            if recent_keys:
                # Check if the key was created recently (within grace period)
                for key in recent_keys:
                    created = getattr(key, "created_at", None)
                    if created:
                        age = (datetime.now(timezone.utc) - created).total_seconds()
                        if age < GENESIS_KEY_GRACE_PERIOD:
                            return True
            return False
        except Exception:
            # Genesis key system unavailable — don't block
            return False

    # ── Auto-Revert ───────────────────────────────────────────────────────

    def _auto_revert(self, rel_path: str, violation: Violation):
        """Revert a critical file to its last-known-good snapshot."""
        # First try: restore from our in-memory snapshot
        with self._snapshot_lock:
            expected_hash = self._file_snapshots.get(rel_path)

        if not expected_hash:
            logger.warning("[GHOST] No snapshot for %s — cannot auto-revert", rel_path)
            return

        full_path = self.watch_path / rel_path
        if not full_path.exists():
            logger.warning("[GHOST] File deleted — cannot auto-revert %s", rel_path)
            return

        current_hash = self._hash_file(full_path)
        if current_hash == expected_hash:
            # File is already at snapshot state (editor double-event)
            return

        # Try git checkout to restore from last commit
        try:
            import subprocess
            r = subprocess.run(
                ["git", "checkout", "HEAD", "--", rel_path],
                cwd=str(self.watch_path),
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                violation.reverted = True
                self._stats["auto_reverted"] += 1
                logger.warning(
                    "[GHOST] AUTO-REVERTED critical file: %s (restored from git HEAD)",
                    rel_path,
                )
                # Update snapshot
                if full_path.exists():
                    with self._snapshot_lock:
                        self._file_snapshots[rel_path] = self._hash_file(full_path)
            else:
                logger.error("[GHOST] git checkout failed for %s: %s", rel_path, r.stderr[:200])
        except Exception as e:
            logger.error("[GHOST] Auto-revert failed for %s: %s", rel_path, e)

    # ── Event Bus Integration ─────────────────────────────────────────────

    def _emit_event(self, violation: Violation):
        """Emit violation to the cognitive event bus."""
        try:
            from cognitive.event_bus import publish
            publish(
                "ghost.violation",
                data=violation.to_dict(),
                source="ghost_enforcer",
            )
        except Exception:
            pass

        # Update KPI trust score
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            tracker.record_event(
                component="ghost_enforcer",
                event_type="violation",
                metadata={"severity": violation.severity, "path": violation.path},
            )
        except Exception:
            pass

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self):
        """Start watching the filesystem."""
        if self._running:
            return

        self._observer = Observer()
        self._observer.schedule(self, str(self.watch_path), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self._running = True
        self._started_at = time.time()
        logger.info(
            "[GHOST] Enforcer started — watching %s (%d critical files protected)",
            self.watch_path, len(CRITICAL_FILES),
        )

    def stop(self):
        """Stop watching."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        logger.info("[GHOST] Enforcer stopped")

    # ── Query API ─────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    def get_violations(self, limit: int = 50) -> List[dict]:
        """Get recent violations."""
        with self._violations_lock:
            return [v.to_dict() for v in reversed(self._violations[-limit:])]

    def get_stats(self) -> dict:
        """Get enforcer statistics."""
        uptime = time.time() - self._started_at if self._started_at else 0
        return {
            **self._stats,
            "uptime_seconds": round(uptime),
            "critical_files_protected": len(CRITICAL_FILES),
            "active_violations": len([
                v for v in self._violations
                if v.severity == "critical" and not v.reverted
            ]),
        }

    def get_critical_file_status(self) -> List[dict]:
        """Check integrity of all critical files against snapshots."""
        results = []
        with self._snapshot_lock:
            for rel_path, expected_hash in self._file_snapshots.items():
                full_path = self.watch_path / rel_path
                status = "missing"
                if full_path.exists():
                    try:
                        current = self._hash_file(full_path)
                        status = "intact" if current == expected_hash else "modified"
                    except Exception:
                        status = "error"
                results.append({"path": rel_path, "status": status})
        return results


# ── Singleton ─────────────────────────────────────────────────────────────

_enforcer: Optional[GhostEnforcer] = None
_enforcer_lock = threading.Lock()


def get_ghost_enforcer(**kwargs) -> GhostEnforcer:
    """Get or create the singleton Ghost Enforcer."""
    global _enforcer
    if _enforcer is None:
        with _enforcer_lock:
            if _enforcer is None:
                _enforcer = GhostEnforcer(**kwargs)
    return _enforcer


def start_ghost_enforcer(**kwargs) -> GhostEnforcer:
    """Start the Ghost Enforcer daemon."""
    enforcer = get_ghost_enforcer(**kwargs)
    if not enforcer.is_running:
        enforcer.start()
    return enforcer
