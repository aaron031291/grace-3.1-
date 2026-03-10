"""
Workspace Bridge — syncs folders and Dev tab via Genesis keys.

Every file write from ANY source (folder UI, Dev tab, AI agent) goes
through this bridge. Both sides stay in sync automatically.

The bridge:
  1. Tracks every write with a Genesis key (source, timestamp, hash)
  2. Broadcasts file_changed events via the event bus
  3. Auto-scans uploaded documents and suggests usage
  4. Manages workspace context for project-scoped chat
"""

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_workspace_contexts: Dict[str, str] = {}
_file_events: list = []
_event_lock = threading.Lock()


def write_file(path: str, content: str, source: str = "unknown") -> dict:
    """
    Universal file write — every write goes through here.
    Tracks via Genesis key, broadcasts event, updates workspace context.
    """
    from pathlib import Path as P
    target = P(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    target.write_text(content, encoding="utf-8")

    # Genesis key
    gk_id = None
    try:
        from api._genesis_tracker import track
        gk_id = track(
            key_type="file_op",
            what=f"File write: {path} ({len(content)} chars)",
            who=f"workspace_bridge.{source}",
            file_path=path,
            output_data={"hash": content_hash, "size": len(content), "source": source},
            tags=["workspace", "file_write", source],
        )
    except Exception:
        pass

    # Broadcast event
    event = {
        "type": "file_changed",
        "path": path,
        "source": source,
        "genesis_key": gk_id,
        "hash": content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _event_lock:
        _file_events.append(event)
        if len(_file_events) > 500:
            _file_events.pop(0)

    try:
        from cognitive.event_bus import publish_async
        publish_async("file.changed", event, source="workspace_bridge")
    except Exception:
        pass

    # Real-time sync — notify all views
    try:
        from core.realtime_sync import on_file_write
        workspace = _get_workspace(path) or ""
        on_file_write(path, source, workspace)
    except Exception:
        pass

    # Update workspace context
    workspace = _get_workspace(path)
    if workspace:
        _update_context(workspace, path, content)

    # Librarian — auto-categorize, tag, version every file write
    try:
        from core.librarian import ingest_document
        ingest_document(path, content, workspace or "", source)
    except Exception:
        pass

    return {"saved": True, "path": path, "genesis_key": gk_id, "hash": content_hash, "source": source}


def read_file(path: str) -> dict:
    """Universal file read."""
    from pathlib import Path as P
    target = P(path)
    if not target.exists():
        return {"error": "File not found", "path": path}
    return {
        "content": target.read_text(errors="ignore"),
        "path": path,
        "size": target.stat().st_size,
        "modified": datetime.fromtimestamp(target.stat().st_mtime).isoformat(),
    }


def scan_upload(path: str, content: str) -> dict:
    """
    Scan an uploaded document and suggest how to use it in the system.
    Called automatically when a file is uploaded to any workspace folder.
    """
    file_ext = path.split(".")[-1].lower() if "." in path else ""
    file_name = path.split("/")[-1]

    analysis = {
        "file": file_name,
        "type": file_ext,
        "size_chars": len(content),
        "detected_purpose": "unknown",
        "suggestions": [],
    }

    content_lower = content[:2000].lower()

    if any(w in content_lower for w in ["api", "endpoint", "route", "http", "rest"]):
        analysis["detected_purpose"] = "api_specification"
        analysis["suggestions"].append("Use as API governance rule — LLMs will generate matching endpoints")
    if any(w in content_lower for w in ["schema", "table", "column", "create table", "model"]):
        analysis["detected_purpose"] = "database_schema"
        analysis["suggestions"].append("Use as schema governance — LLMs will generate matching data models")
    if any(w in content_lower for w in ["import", "def ", "class ", "function", "const ", "export"]):
        analysis["detected_purpose"] = "source_code"
        analysis["suggestions"].append("Use as code blueprint — LLMs will follow this coding pattern")
    if any(w in content_lower for w in ["requirement", "specification", "user story", "acceptance"]):
        analysis["detected_purpose"] = "requirements"
        analysis["suggestions"].append("Use as requirements spec — pipeline will validate against these")
    if any(w in content_lower for w in ["test", "assert", "expect", "describe", "it("]):
        analysis["detected_purpose"] = "test_suite"
        analysis["suggestions"].append("Use as test template — code agent will generate matching tests")
    if file_ext in ("env", "ini", "cfg", "conf", "toml", "yaml", "yml"):
        analysis["detected_purpose"] = "configuration"
        analysis["suggestions"].append("Use as environment config — system will follow these settings")

    if not analysis["suggestions"]:
        analysis["suggestions"].append("Upload as reference document — available to all LLM calls for context")

    # Get AI analysis
    try:
        from api.brain_api_v2 import call_brain
        r = call_brain("ai", "fast", {
            "prompt": f"I uploaded a file to Grace:\n\nFilename: {file_name}\nType: {file_ext}\n"
                      f"First 500 chars:\n{content[:500]}\n\n"
                      f"In one sentence, what is this file and how should Grace use it?",
            "models": ["kimi"],
        })
        if r.get("ok"):
            resp = r["data"].get("individual_responses", [{}])[0].get("response", "")
            if resp:
                analysis["ai_summary"] = resp.strip()
    except Exception:
        pass

    return analysis


def get_recent_events(limit: int = 50) -> list:
    """Get recent file events."""
    with _event_lock:
        return list(reversed(_file_events[-limit:]))


def get_workspace_context(workspace: str) -> str:
    """Get the cached context for a workspace."""
    return _workspace_contexts.get(workspace, "")


def _get_workspace(path: str) -> Optional[str]:
    """Extract workspace name from path."""
    parts = path.replace("\\", "/").split("/")
    if "projects" in parts:
        idx = parts.index("projects")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if "governance_rules" in parts:
        return "governance"
    return None


def _update_context(workspace: str, path: str, content: str):
    """Update workspace context cache."""
    existing = _workspace_contexts.get(workspace, "")
    file_name = path.split("/")[-1]
    snippet = f"\n--- {file_name} ---\n{content[:300]}"
    if len(existing) + len(snippet) > 15000:
        existing = existing[-10000:]
    _workspace_contexts[workspace] = existing + snippet
