"""
Spindle Checkpoint — Snapshot & rollback for autonomous executions.
Takes a state snapshot before execution and reverts on failure.
"""
import asyncio
import logging
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

        # Restore file backups in parallel
        if cp.file_backups:
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {
                    pool.submit(self._restore_file, path, content): path
                    for path, content in cp.file_backups.items()
                }
                for future in futures:
                    try:
                        future.result(timeout=5)
                    except Exception as e:
                        logger.error(f"[CHECKPOINT] Failed to restore {futures[future]}: {e}")

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
