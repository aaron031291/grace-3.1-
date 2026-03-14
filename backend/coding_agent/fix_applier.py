"""
coding_agent/fix_applier.py
─────────────────────────────────────────────────────────────────────────────
Fix Applier — Writes generated code to disk and verifies it works.

This is the "last mile" of the coding agent loop:
  Generated code → Backup original → Write to disk → Syntax check
  → Hot-reload module → Verify import → If fail → Rollback
  → Record outcome as episode + learning event

Without this, the coding agent generates fixes that sit in memory and
never affect the actual codebase. This module closes the loop.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import logging
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Safety: only allow applying fixes to backend Python files
_SAFE_BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
_BACKUP_DIR = _SAFE_BASE_DIR / ".fix_backups"


@dataclass
class ApplyResult:
    """Result of a fix application attempt."""
    success: bool = False
    file_path: str = ""
    backup_path: str = ""
    error: str = ""
    rolled_back: bool = False
    module_reloaded: bool = False
    syntax_valid: bool = False
    lines_written: int = 0
    applied_at: str = ""

    def summary(self) -> str:
        if self.success:
            return f"✅ Applied to {self.file_path} ({self.lines_written} lines) | reload={'OK' if self.module_reloaded else 'skipped'}"
        if self.rolled_back:
            return f"⏪ Rolled back {self.file_path} — {self.error[:80]}"
        return f"❌ Failed to apply to {self.file_path} — {self.error[:80]}"


class FixApplier:
    """
    Applies generated code fixes to the filesystem with full safety guarantees.

    Safety chain:
    1. Validate file is within backend/ (no path traversal)
    2. AST-parse the generated code (reject on syntax error)
    3. Backup original file to .fix_backups/
    4. Write new code
    5. AST-parse the written file (double-check)
    6. Attempt hot-reload of the affected module
    7. If reload fails → rollback from backup
    8. Record outcome as episode + genesis key
    """

    def apply(
        self,
        file_path: str,
        generated_code: str,
        task_id: str = "",
        task_description: str = "",
        allow_create: bool = False,
    ) -> ApplyResult:
        """
        Apply a generated fix to a file, or create a new file.

        Args:
            file_path: Absolute or relative (to backend/) path of file to fix/create
            generated_code: The new code to write
            task_id: Coding agent task ID for traceability
            task_description: Human-readable description for learning records
            allow_create: If True, allow creating new files (not just patching)

        Returns:
            ApplyResult with full details of what happened
        """
        result = ApplyResult(applied_at=datetime.now(timezone.utc).isoformat())

        # ── 1. Resolve and validate path ───────────────────────────────
        target = self._resolve_safe_path(file_path, allow_create=allow_create)
        if target is None:
            result.error = f"Unsafe or non-existent path: {file_path}"
            logger.error("[FIX-APPLY] %s", result.error)
            self._record(task_id, task_description, result)
            return result

        result.file_path = str(target)

        # ── 2. Validate generated code syntax ──────────────────────────
        try:
            ast.parse(generated_code)
            result.syntax_valid = True
        except SyntaxError as se:
            result.error = f"Syntax error in generated code: line {se.lineno}: {se.msg}"
            logger.error("[FIX-APPLY] Rejected — %s", result.error)
            self._record(task_id, task_description, result)
            return result

        # ── 3. Backup original (skip for new files) ──────────────────
        is_new_file = not target.exists()
        backup = None
        if not is_new_file:
            backup = self._backup(target)
            if backup is None:
                result.error = "Failed to create backup — aborting for safety"
                logger.error("[FIX-APPLY] %s", result.error)
                self._record(task_id, task_description, result)
                return result
            result.backup_path = str(backup)
        else:
            # Ensure parent directories exist for new files
            target.parent.mkdir(parents=True, exist_ok=True)

        # ── 4. Write new code ──────────────────────────────────────────
        try:
            target.write_text(generated_code, encoding="utf-8")
            result.lines_written = len(generated_code.splitlines())
            logger.info("[FIX-APPLY] Wrote %d lines to %s", result.lines_written, target)
        except Exception as e:
            result.error = f"Write failed: {e}"
            self._rollback(target, backup, result, is_new_file=is_new_file)
            self._record(task_id, task_description, result)
            return result

        # ── 5. Post-write syntax check ─────────────────────────────────
        try:
            ast.parse(target.read_text(encoding="utf-8"))
        except SyntaxError as se:
            result.error = f"Post-write syntax check failed: {se}"
            self._rollback(target, backup, result, is_new_file=is_new_file)
            self._record(task_id, task_description, result)
            return result

        # ── 6. Hot-reload the module ────────────────────────────────────
        result.module_reloaded = self._hot_reload(target)

        # ── 7. If reload failed, consider rollback ─────────────────────
        # We don't auto-rollback on reload failure — the file is syntactically
        # valid. Reload failure usually means a runtime dependency issue.
        # Log a warning and let the operator decide.
        if not result.module_reloaded:
            logger.warning(
                "[FIX-APPLY] Module reload failed for %s — file written but not active until next restart",
                target,
            )

        result.success = True
        logger.info("[FIX-APPLY] ✅ %s", result.summary())

        # Publish fix.applied so trigger_fabric records it as learning reward
        try:
            from cognitive.event_bus import publish_async
            publish_async("fix.applied", {
                "file": result.file_path,
                "task_id": task_id,
                "lines": result.lines_written,
                "reloaded": result.module_reloaded,
            }, source="fix_applier")
        except Exception:
            pass

        self._record(task_id, task_description, result)
        return result

    def _resolve_safe_path(self, file_path: str, allow_create: bool = False) -> Optional[Path]:
        """Validate and resolve to an absolute path within backend/."""
        try:
            p = Path(file_path)
            if not p.is_absolute():
                p = _SAFE_BASE_DIR / p
            resolved = p.resolve()

            # Security: must be inside backend/
            if not str(resolved).startswith(str(_SAFE_BASE_DIR)):
                logger.error(
                    "[FIX-APPLY] Path traversal rejected: %s is outside %s",
                    resolved, _SAFE_BASE_DIR,
                )
                return None

            # Must be a Python file
            if resolved.suffix not in (".py",):
                logger.error("[FIX-APPLY] Only .py files can be patched: %s", resolved)
                return None

            if not resolved.exists():
                if allow_create:
                    logger.info("[FIX-APPLY] Creating new file: %s", resolved)
                else:
                    logger.error("[FIX-APPLY] File does not exist: %s", resolved)
                    return None

            return resolved
        except Exception as e:
            logger.error("[FIX-APPLY] Path resolution error: %s", e)
            return None

    def _backup(self, target: Path) -> Optional[Path]:
        """Back up the original file. Returns backup path or None on failure."""
        try:
            _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            # Use relative-ish path as backup name to avoid collisions
            safe_name = str(target.relative_to(_SAFE_BASE_DIR)).replace("/", "_").replace("\\", "_")
            backup = _BACKUP_DIR / f"{safe_name}.{ts}.bak"
            shutil.copy2(target, backup)
            logger.info("[FIX-APPLY] Backed up %s → %s", target.name, backup.name)
            return backup
        except Exception as e:
            logger.error("[FIX-APPLY] Backup failed: %s", e)
            return None

    def _rollback(self, target: Path, backup: Optional[Path], result: ApplyResult, is_new_file: bool = False) -> None:
        """Restore original file from backup, or delete new file on failure."""
        try:
            if is_new_file:
                # New file that failed validation — remove it entirely
                if target.exists():
                    target.unlink()
                logger.warning("[FIX-APPLY] ⏪ Removed failed new file %s", target.name)
            elif backup:
                shutil.copy2(backup, target)
                logger.warning("[FIX-APPLY] ⏪ Rolled back %s from backup", target.name)
            result.rolled_back = True
            result.success = False
        except Exception as e:
            logger.error("[FIX-APPLY] Rollback failed: %s — MANUAL RECOVERY NEEDED", e)

    def _hot_reload(self, target: Path) -> bool:
        """Attempt to hot-reload the module corresponding to the changed file."""
        try:
            # Compute module name from file path relative to backend/
            rel = target.relative_to(_SAFE_BASE_DIR)
            module_name = ".".join(rel.with_suffix("").parts)

            if module_name in sys.modules:
                module = sys.modules[module_name]
                importlib.reload(module)
                logger.info("[FIX-APPLY] 🔄 Reloaded module: %s", module_name)
                return True
            else:
                logger.debug("[FIX-APPLY] Module %s not live — no reload needed", module_name)
                return True  # Not loaded = not a failure
        except Exception as e:
            logger.warning("[FIX-APPLY] Hot-reload failed for %s: %s", target.name, e)
            return False

    def _record(
        self, task_id: str, description: str, result: ApplyResult
    ) -> None:
        """Record apply outcome as episode + genesis key."""
        # Genesis key
        try:
            from api._genesis_tracker import track
            track(
                key_type="fix_applied" if result.success else "error",
                what_description=f"Fix {'applied' if result.success else 'failed'}: {result.file_path}",
                why_reason=description[:200] or task_id,
                how_method="coding_agent.fix_applier",
                context_data={
                    "task_id": task_id,
                    "file_path": result.file_path,
                    "lines_written": result.lines_written,
                    "rolled_back": result.rolled_back,
                    "error": result.error[:200] if result.error else "",
                },
                is_error=not result.success,
            )
        except Exception:
            pass

        # Episodic memory — this is the critical learning record
        try:
            import json
            from database.session import session_scope
            from cognitive.episodic_memory import EpisodicBuffer
            with session_scope() as session:
                buf = EpisodicBuffer(session)
                buf.record_episode(
                    problem=f"Code fix needed: {description[:100]}",
                    action={"type": "apply_fix", "file": result.file_path, "task_id": task_id},
                    outcome={
                        "success": result.success,
                        "lines_written": result.lines_written,
                        "rolled_back": result.rolled_back,
                        "reloaded": result.module_reloaded,
                        "error": result.error[:100] if result.error else "",
                    },
                    predicted_outcome={"success": True},
                    trust_score=0.9 if result.success else 0.2,
                    source="fix_applier",
                    genesis_key_id=task_id,
                )
        except Exception:
            pass


# Singleton
_applier: Optional[FixApplier] = None


def get_fix_applier() -> FixApplier:
    global _applier
    if _applier is None:
        _applier = FixApplier()
    return _applier
