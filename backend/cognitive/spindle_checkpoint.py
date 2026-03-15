"""
Spindle Checkpoint — Snapshot & rollback for autonomous executions.
Takes a state snapshot before execution and reverts on failure.
"""
import asyncio
import hashlib
import logging
import shutil
import threading
import time
import json
import copy
from contextlib import asynccontextmanager, contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

_CHECKPOINT_DIR = Path(__file__).parent.parent / ".grace" / "checkpoints"


@dataclass
class Checkpoint:
    """A snapshot of component state before Spindle execution."""
    checkpoint_id: str
    component: str
    timestamp: float = field(default_factory=time.time)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    file_backups: Dict[str, str] = field(default_factory=dict)  # path -> content
    rolled_back: bool = False


class SpindleCheckpointManager:
    """Manages checkpoints for safe autonomous execution."""

    def __init__(self):
        self._checkpoints: List[Checkpoint] = []
        self._max_checkpoints = 100
        self._rollback_handlers: Dict[str, Callable] = {}
        self._stats = {"created": 0, "committed": 0, "rolled_back": 0}
        self._lock = threading.Lock()

    def register_rollback(self, component: str, handler: Callable):
        """Register a custom rollback handler for a component type."""
        self._rollback_handlers[component] = handler

    def watch_file(self, cp: Checkpoint, path: str) -> None:
        """
        Capture the current content of a file before it gets modified.
        Call this BEFORE writing to the file. The content is stored both
        in-memory (for fast rollback) and on disk (survives restart).
        """
        file_path = Path(path)
        if not file_path.exists():
            # Mark as "did not exist" so rollback can delete it
            cp.file_backups[path] = "__CHECKPOINT_FILE_DID_NOT_EXIST__"
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            cp.file_backups[path] = content

            # Also persist to disk for crash recovery
            backup_dir = _CHECKPOINT_DIR / cp.checkpoint_id
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Use relative-safe name
            safe_name = path.replace("/", "_").replace("\\", "_").replace(":", "_")
            disk_backup = backup_dir / safe_name
            shutil.copy2(file_path, disk_backup)

            # Write manifest entry
            manifest_path = backup_dir / "manifest.json"
            manifest = {}
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            manifest[path] = {
                "backup_file": safe_name,
                "existed": True,
                "original_hash": hashlib.sha256(content.encode()).hexdigest(),
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            logger.debug(f"[CHECKPOINT] Watching file: {path}")
        except Exception as e:
            logger.warning(f"[CHECKPOINT] Could not watch file {path}: {e}")

    def watch_files(self, cp: Checkpoint, paths: list) -> None:
        """Watch multiple files before modification."""
        for p in paths:
            self.watch_file(cp, p)

    @contextmanager
    def checkpoint(self, component: str, proof_hash: str = ""):
        """
        Context manager: takes a snapshot before execution, reverts on failure.

        Usage:
            with checkpoint_mgr.checkpoint("database", proof.constraint_hash) as cp:
                # do risky stuff
                cp.state_snapshot["key"] = "value"  # record state
            # if exception raised, rollback is triggered
        """
        cp = Checkpoint(
            checkpoint_id=f"CP-{int(time.time()*1000)}-{proof_hash[:8]}",
            component=component,
        )

        # Capture pre-execution state
        self._capture_state(cp)

        logger.info(f"[CHECKPOINT] Created {cp.checkpoint_id} for {component}")
        self._stats["created"] += 1

        try:
            yield cp
            # Success — keep the checkpoint for audit but don't rollback
            logger.info(f"[CHECKPOINT] {cp.checkpoint_id} completed successfully")
            self._stats["committed"] += 1
        except Exception as e:
            # Failure — rollback
            logger.warning(f"[CHECKPOINT] {cp.checkpoint_id} failed: {e}, initiating rollback")
            self._rollback(cp)
            self._stats["rolled_back"] += 1
            raise  # Re-raise so caller knows it failed
        finally:
            with self._lock:
                self._checkpoints.append(cp)
                if len(self._checkpoints) > self._max_checkpoints:
                    self._checkpoints = self._checkpoints[-self._max_checkpoints:]

            # Log to event store
            try:
                from cognitive.spindle_event_store import get_event_store
                get_event_store().append(
                    topic="spindle.checkpoint",
                    source_type="system",
                    payload={
                        "checkpoint_id": cp.checkpoint_id,
                        "component": cp.component,
                        "rolled_back": cp.rolled_back,
                    },
                    proof_hash=proof_hash,
                    result="ROLLED_BACK" if cp.rolled_back else "COMMITTED",
                )
            except Exception:
                pass

    def _capture_state(self, cp: Checkpoint):
        """Capture component state before execution."""
        try:
            # Try to get component health status
            from core.deterministic_lifecycle import _registry
            if cp.component in _registry:
                comp_data = _registry[cp.component]
                cp.state_snapshot["registry_entry"] = {
                    "name": getattr(comp_data, "name", cp.component),
                    "status": getattr(comp_data, "status", "unknown"),
                }
        except Exception:
            pass

        cp.state_snapshot["capture_time"] = time.time()

    def _rollback(self, cp: Checkpoint):
        """Attempt to rollback to checkpoint state."""
        cp.rolled_back = True

        # Try custom handler first
        handler = self._rollback_handlers.get(cp.component)
        if handler:
            try:
                handler(cp)
                logger.info(f"[CHECKPOINT] Custom rollback for {cp.component} succeeded")
                return
            except Exception as e:
                logger.error(f"[CHECKPOINT] Custom rollback failed: {e}")

        # Restore file backups
        if cp.file_backups:
            restored = 0
            for path, content in cp.file_backups.items():
                try:
                    if content == "__CHECKPOINT_FILE_DID_NOT_EXIST__":
                        # File was created during checkpoint — delete it
                        p = Path(path)
                        if p.exists():
                            p.unlink()
                            logger.info(f"[CHECKPOINT] Deleted new file: {path}")
                            restored += 1
                    else:
                        self._restore_file(path, content)
                        restored += 1
                except Exception as e:
                    logger.error(f"[CHECKPOINT] Failed to restore {path}: {e}")
            logger.info(f"[CHECKPOINT] Restored {restored}/{len(cp.file_backups)} files")

        logger.info(f"[CHECKPOINT] Rollback completed for {cp.checkpoint_id}")

    @staticmethod
    def _restore_file(path: str, content: str):
        Path(path).write_text(content, encoding="utf-8")
        logger.info(f"[CHECKPOINT] Restored file: {path}")

    @asynccontextmanager
    async def async_checkpoint(self, component: str, proof_hash: str = ""):
        """Async context manager version of checkpoint."""
        cp = Checkpoint(
            checkpoint_id=f"CP-{int(time.time()*1000)}-{proof_hash[:8]}",
            component=component,
        )

        # Capture state in thread pool (may do I/O)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._capture_state, cp)

        logger.info(f"[CHECKPOINT] Created {cp.checkpoint_id} for {component}")
        self._stats["created"] += 1

        try:
            yield cp
            logger.info(f"[CHECKPOINT] {cp.checkpoint_id} completed successfully")
            self._stats["committed"] += 1
        except Exception as e:
            logger.warning(f"[CHECKPOINT] {cp.checkpoint_id} failed: {e}, initiating rollback")
            await loop.run_in_executor(None, self._rollback, cp)
            self._stats["rolled_back"] += 1
            raise
        finally:
            with self._lock:
                self._checkpoints.append(cp)
                if len(self._checkpoints) > self._max_checkpoints:
                    self._checkpoints = self._checkpoints[-self._max_checkpoints:]

            try:
                from cognitive.spindle_event_store import get_event_store
                get_event_store().append_async(
                    topic="spindle.checkpoint",
                    source_type="system",
                    payload={
                        "checkpoint_id": cp.checkpoint_id,
                        "component": cp.component,
                        "rolled_back": cp.rolled_back,
                    },
                    proof_hash=proof_hash,
                    result="ROLLED_BACK" if cp.rolled_back else "COMMITTED",
                )
            except Exception:
                pass

    def recover_from_disk(self, checkpoint_id: str) -> bool:
        """
        Recover files from a disk-persisted checkpoint (crash recovery).
        Use when the process restarted and in-memory checkpoints are lost.
        """
        backup_dir = _CHECKPOINT_DIR / checkpoint_id
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning(f"[CHECKPOINT] No manifest found for {checkpoint_id}")
            return False

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            restored = 0
            for original_path, info in manifest.items():
                backup_file = backup_dir / info["backup_file"]
                if info.get("existed") and backup_file.exists():
                    shutil.copy2(backup_file, original_path)
                    logger.info(f"[CHECKPOINT] Crash-recovered: {original_path}")
                    restored += 1
            logger.info(f"[CHECKPOINT] Crash recovery: restored {restored} files from {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"[CHECKPOINT] Crash recovery failed: {e}")
            return False

    def list_disk_checkpoints(self) -> List[str]:
        """List checkpoint IDs that have disk-persisted backups."""
        if not _CHECKPOINT_DIR.exists():
            return []
        return sorted([
            d.name for d in _CHECKPOINT_DIR.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ])

    def cleanup_old_checkpoints(self, keep: int = 50):
        """Remove old disk checkpoints, keeping the most recent N."""
        if not _CHECKPOINT_DIR.exists():
            return
        dirs = sorted(
            [d for d in _CHECKPOINT_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime
        )
        for old_dir in dirs[:-keep]:
            try:
                shutil.rmtree(old_dir)
            except Exception:
                pass

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent checkpoints."""
        return [
            {
                "checkpoint_id": cp.checkpoint_id,
                "component": cp.component,
                "timestamp": cp.timestamp,
                "rolled_back": cp.rolled_back,
            }
            for cp in reversed(self._checkpoints[-limit:])
        ]


# Singleton
_manager: Optional[SpindleCheckpointManager] = None


def get_checkpoint_manager() -> SpindleCheckpointManager:
    global _manager
    if _manager is None:
        _manager = SpindleCheckpointManager()
    return _manager
