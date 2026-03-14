"""
Governance Projection Service
=============================
Subscribes to the event bus and projects metadata, lineage, trust scores,
and audit records back to workspace domain folders.

This is the bridge between:
  - OPERATIONAL LAYER (DB tables: file_versions, pipeline_runs, genesis_key)
  - GOVERNANCE LAYER (filesystem: /projects/{workspace}/.grace/)

Everything that happens in the codebase DB gets a readable, auditable
record written to the project's .grace/ folder so you can browse
governance by domain without touching the database.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_GRACE_DIR = ".grace"
_instance = None
_lock = threading.Lock()


class GovernanceProjection:
    """Projects operational events to workspace governance folders."""

    def __init__(self):
        self._running = False

    def start(self):
        """Subscribe to event bus topics and start projecting."""
        if self._running:
            return
        self._running = True
        try:
            from cognitive.event_bus import subscribe
            subscribe("workspace.*", self._on_workspace_event)
            subscribe("trust.updated", self._on_trust_event)
            subscribe("consensus.completed", self._on_consensus_event)
            subscribe("consensus.actuated", self._on_consensus_event)
            subscribe("healing.*", self._on_healing_event)
            logger.info("[GOV-PROJECTION] Governance projection service started")
        except Exception as e:
            logger.warning(f"[GOV-PROJECTION] Failed to subscribe: {e}")

    def stop(self):
        self._running = False

    # ─── Event Handlers ───

    def _on_workspace_event(self, event):
        """Handle workspace.* events (file_versioned, branch_merged, task_created, pipeline_completed)."""
        workspace_id = event.data.get("workspace_id")
        if not workspace_id:
            return
        grace_dir = self._get_grace_dir(workspace_id)
        if not grace_dir:
            return

        record = {
            "event": event.topic,
            "timestamp": event.timestamp,
            "source": event.source,
            "data": _sanitize(event.data),
        }

        # Append to audit log
        self._append_json(grace_dir / "audit_log.jsonl", record)

        # For VCS events, update lineage
        if "file_versioned" in event.topic or "branch_merged" in event.topic:
            self._update_lineage(grace_dir, event)

        # For pipeline events, log to pipeline history
        if "pipeline" in event.topic:
            pipelines_dir = grace_dir / "pipeline_runs"
            pipelines_dir.mkdir(parents=True, exist_ok=True)
            run_id = event.data.get("run_id", event.timestamp)
            self._write_json(pipelines_dir / f"{run_id}.json", record)

        # For task events, log to task history
        if "task" in event.topic:
            self._append_json(grace_dir / "tasks_log.jsonl", record)

    def _on_trust_event(self, event):
        """When trust scores change, project them to all workspace folders."""
        # Trust events are system-wide, project to a global governance dir
        global_dir = self._get_global_grace_dir()
        if not global_dir:
            return

        trust_file = global_dir / "trust_scores.json"
        try:
            scores = json.loads(trust_file.read_text()) if trust_file.exists() else {}
        except Exception:
            scores = {}

        component_id = event.data.get("component_id", "unknown")
        scores[component_id] = {
            "component_name": event.data.get("component_name"),
            "trust_score": event.data.get("trust_score"),
            "trend": event.data.get("trend"),
            "needs_remediation": event.data.get("needs_remediation"),
            "last_updated": event.timestamp,
        }
        self._write_json(trust_file, scores)

    def _on_consensus_event(self, event):
        """When consensus completes, log the decision."""
        global_dir = self._get_global_grace_dir()
        if not global_dir:
            return
        record = {
            "event": event.topic,
            "timestamp": event.timestamp,
            "models": event.data.get("models", []),
            "confidence": event.data.get("confidence"),
            "agreements": event.data.get("agreements"),
            "disagreements": event.data.get("disagreements"),
        }
        self._append_json(global_dir / "consensus_log.jsonl", record)

    def _on_healing_event(self, event):
        """When healing occurs, log to governance."""
        global_dir = self._get_global_grace_dir()
        if not global_dir:
            return
        record = {
            "event": event.topic,
            "timestamp": event.timestamp,
            "data": _sanitize(event.data),
        }
        self._append_json(global_dir / "healing_log.jsonl", record)

    # ─── Lineage Tracking ───

    def _update_lineage(self, grace_dir: Path, event):
        """Update the lineage.json with file version history."""
        lineage_file = grace_dir / "lineage.json"
        try:
            lineage = json.loads(lineage_file.read_text()) if lineage_file.exists() else {}
        except Exception:
            lineage = {}

        file_path = event.data.get("file_path", "")
        if file_path:
            if file_path not in lineage:
                lineage[file_path] = {"versions": [], "total_changes": 0}
            entry = lineage[file_path]
            entry["versions"].append({
                "version": event.data.get("version"),
                "author": event.data.get("author", "grace"),
                "timestamp": event.timestamp,
                "event": event.topic,
            })
            # Keep last 50 versions per file
            entry["versions"] = entry["versions"][-50:]
            entry["total_changes"] = len(entry["versions"])
            entry["last_modified"] = event.timestamp

        merge_id = event.data.get("merge_id")
        if merge_id:
            if "_merges" not in lineage:
                lineage["_merges"] = []
            lineage["_merges"].append({
                "merge_id": merge_id,
                "source": event.data.get("source_branch"),
                "target": event.data.get("target_branch"),
                "status": event.data.get("status"),
                "timestamp": event.timestamp,
            })
            lineage["_merges"] = lineage["_merges"][-100:]

        self._write_json(lineage_file, lineage)

    # ─── Helpers ───

    def _get_grace_dir(self, workspace_id: str) -> Path:
        """Get or create the .grace governance directory for a workspace."""
        try:
            from database.session import session_scope
            from models.workspace_models import Workspace
            with session_scope() as session:
                ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
                if ws and ws.root_path:
                    grace_dir = Path(ws.root_path) / _GRACE_DIR
                    grace_dir.mkdir(parents=True, exist_ok=True)
                    return grace_dir
        except Exception:
            pass
        return None

    def _get_global_grace_dir(self) -> Path:
        """Get the global .grace governance directory (system-wide)."""
        try:
            base = Path(__file__).resolve().parent.parent.parent
            grace_dir = base / _GRACE_DIR
            grace_dir.mkdir(parents=True, exist_ok=True)
            return grace_dir
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, data):
        """Write JSON atomically (Windows-safe)."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            try:
                tmp.replace(path)
            except OSError:
                # Windows: target file locked — fall back to direct write
                path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
                tmp.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"[GOV-PROJECTION] Write failed {path}: {e}")

    @staticmethod
    def _append_json(path: Path, record: dict):
        """Append a JSON record to a JSONL file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            logger.warning(f"[GOV-PROJECTION] Append failed {path}: {e}")


def _sanitize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove large fields from event data before persisting."""
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 2000:
            cleaned[k] = v[:2000] + "...[truncated]"
        else:
            cleaned[k] = v
    return cleaned


def get_governance_projection() -> GovernanceProjection:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GovernanceProjection()
    return _instance
