"""
Domain Lineage Bridge — Codebase → Domain folder metadata logging.

When code is written in the codebase (operational layer), this bridge logs
lineage and execution metadata into domain folders (governance layer) so
you can audit and govern by domain.

Flow:
  File write in data/projects/{domain}/... or repos/{domain}/...
    → log_lineage(domain, path, operation, genesis_key_id)
    → domains/{domain}/metadata/lineage.jsonl (append-only)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Knowledge base domains path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_KB_DOMAINS = _BACKEND_DIR / "knowledge_base" / "domains"

def infer_domain_from_path(abs_path: str) -> Optional[str]:
    """
    Infer domain from absolute file path.
    Returns domain name or None if path doesn't match known patterns.
    """
    path = str(abs_path).replace("\\", "/")
    parts = [p for p in path.split("/") if p]
    # data/projects/{domain}/...
    for i, p in enumerate(parts):
        if p == "projects" and i + 1 < len(parts):
            domain = parts[i + 1]
            if domain and not domain.startswith("."):
                return domain
    # domains/{domain}/...
    for i, p in enumerate(parts):
        if p == "domains" and i + 1 < len(parts):
            return parts[i + 1]
    return None


def ensure_domain_metadata_dir(domain: str) -> Path:
    """Ensure domains/{domain}/metadata/ exists; return its path."""
    domain_safe = domain.lower().replace(" ", "_").replace(os.sep, "_")
    meta_dir = _KB_DOMAINS / domain_safe / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir


def log_lineage(
    domain: str,
    file_path: str,
    operation_type: str = "modify",
    source: str = "unknown",
    genesis_key_id: Optional[str] = None,
    user_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Log a lineage record to the domain's metadata folder.
    Appends to lineage.jsonl (one JSON object per line).
    Returns path to lineage file or None on error.
    """
    try:
        meta_dir = ensure_domain_metadata_dir(domain)
        lineage_file = meta_dir / "lineage.jsonl"

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "operation_type": operation_type,
            "source": source,
            "genesis_key_id": genesis_key_id,
            "user_id": user_id,
            **(extra or {}),
        }

        with open(lineage_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        logger.debug(f"[DOMAIN_LINEAGE] Logged to {domain}/metadata/lineage.jsonl: {file_path}")
        return str(lineage_file)
    except Exception as e:
        logger.warning(f"[DOMAIN_LINEAGE] Failed to log lineage: {e}")
        return None


def log_lineage_from_path(
    abs_path: str,
    operation_type: str = "modify",
    source: str = "unknown",
    genesis_key_id: Optional[str] = None,
    user_id: Optional[str] = None,
    domain_override: Optional[str] = None,
) -> Optional[str]:
    """
    Infer domain from path and log lineage. Use domain_override to force domain.
    """
    domain = domain_override or infer_domain_from_path(abs_path)
    if not domain:
        return None
    # Use relative-ish path for readability
    try:
        rel = Path(abs_path).name
        parent = str(Path(abs_path).parent)
        if "projects" in parent:
            parts = Path(abs_path).parts
            for i, p in enumerate(parts):
                if p == "projects" and i + 1 < len(parts):
                    rel = str(Path(*parts[i + 2:]))  # domain/rest
                    break
    except Exception:
        rel = abs_path
    return log_lineage(
        domain=domain,
        file_path=rel or abs_path,
        operation_type=operation_type,
        source=source,
        genesis_key_id=genesis_key_id,
        user_id=user_id,
    )


def get_lineage_for_domain(domain: str, limit: int = 100) -> list:
    """Read recent lineage records for a domain (last N lines)."""
    try:
        meta_dir = ensure_domain_metadata_dir(domain)
        lineage_file = meta_dir / "lineage.jsonl"
        if not lineage_file.exists():
            return []
        lines = []
        with open(lineage_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return lines[-limit:]
    except Exception as e:
        logger.warning(f"[DOMAIN_LINEAGE] Failed to read lineage: {e}")
        return []
