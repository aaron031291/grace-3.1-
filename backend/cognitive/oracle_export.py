"""
Oracle Export — Learning Memory → Human-Readable Files (Librarian)

Pushes learning memory (training data) to the Oracle file tree so:
- Full file management system stays human-readable
- Librarian can index and manage Oracle content
- Brains and autonomous training use the same source

Layout: knowledge_base/layer_1/oracle/
  <example_type>/
    YYYY-MM-DD/
      oracle_<id>.txt   (human-readable: context + expected + trust + source)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_oracle_export_path(kb_path: Optional[Path] = None) -> Path:
    """Return knowledge_base/layer_1/oracle root."""
    if kb_path is None:
        try:
            import os
            kb_path = Path(os.environ.get("GRACE_KNOWLEDGE_BASE_PATH", "."))
        except Exception:
            kb_path = Path(".")
    kb_path = Path(kb_path)
    return kb_path / "layer_1" / "oracle"


def export_learning_memory_to_oracle(
    limit: int = 500,
    min_trust: float = 0.3,
    kb_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Export learning memory to human-readable Oracle files for librarian.

    Reads LearningExample from DB, writes one .txt per example under
    knowledge_base/layer_1/oracle/<example_type>/<date>/ so the full file
    management system and librarian can use it.
    """
    result = {"exported": 0, "skipped": 0, "errors": 0, "paths": []}
    oracle_root = get_oracle_export_path(kb_path)
    oracle_root.mkdir(parents=True, exist_ok=True)

    try:
        from database.session import session_scope
        from cognitive.learning_memory import LearningExample, _from_json_str
    except Exception as e:
        logger.warning("Oracle export: session/learning_memory unavailable: %s", e)
        result["errors"] += 1
        return result

    with session_scope() as session:
        rows = (
            session.query(LearningExample)
            .filter(LearningExample.trust_score >= min_trust)
            .order_by(LearningExample.trust_score.desc(), LearningExample.updated_at.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            eid = str(getattr(r, "id", ""))
            if not eid:
                result["skipped"] += 1
                continue
            try:
                ic = getattr(r, "input_context", "") or "{}"
                eo = getattr(r, "expected_output", "") or "{}"
                d_ic = _from_json_str(ic) if isinstance(ic, str) else (ic or {})
                d_eo = _from_json_str(eo) if isinstance(eo, str) else (eo or {})
                trust = float(getattr(r, "trust_score", 0) or 0)
                source = str(getattr(r, "source", "") or "")
                example_type = str(getattr(r, "example_type", "") or "general").replace("/", "_").replace("\\", "_") or "general"
                updated = getattr(r, "updated_at", None)
                date_str = updated.strftime("%Y-%m-%d") if hasattr(updated, "strftime") else datetime.now(timezone.utc).strftime("%Y-%m-%d")

                dir_path = oracle_root / example_type / date_str
                dir_path.mkdir(parents=True, exist_ok=True)
                safe_id = eid.replace("/", "_").replace("\\", "_")[:32]
                file_path = dir_path / f"oracle_{safe_id}.txt"

                lines = [
                    "# Oracle training record (human-readable)",
                    f"id: {eid}",
                    f"type: {example_type}",
                    f"trust: {trust:.2f}",
                    f"source: {source}",
                    f"updated: {date_str}",
                    "",
                    "## Context",
                    json.dumps(d_ic, indent=2, default=str)[:4000],
                    "",
                    "## Expected",
                    json.dumps(d_eo, indent=2, default=str)[:4000],
                ]
                file_path.write_text("\n".join(lines), encoding="utf-8", errors="replace")
                result["exported"] += 1
                result["paths"].append(str(file_path.relative_to(oracle_root)))
            except Exception as e:
                logger.debug("Oracle export skip %s: %s", eid, e)
                result["errors"] += 1

    if result["paths"]:
        result["paths"] = result["paths"][:50]
    return result
