"""
Export Module — PDF, JSON, CSV from any data source in Grace.

Export: training data, documents, genesis keys, learning patterns,
episodic memory, procedural memory, healing playbook, or custom queries.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["Export"])


def _get_db():
    try:
        from database.session import SessionLocal
        if SessionLocal:
            return SessionLocal()
    except Exception:
        pass
    return None


class ExportRequest(BaseModel):
    source: str  # training_data, documents, genesis_keys, patterns, episodes, procedures, playbook
    format: str  # json, csv, pdf
    filters: Optional[Dict[str, Any]] = None
    limit: int = 500


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def _fetch_data(source: str, filters: Dict = None, limit: int = 500) -> List[Dict]:
    from sqlalchemy import text
    db = _get_db()
    if not db:
        return []

    try:
        queries = {
            "training_data": "SELECT id, example_type, input_context, expected_output, actual_output, trust_score, source, created_at FROM learning_examples ORDER BY created_at DESC LIMIT :lim",
            "documents": "SELECT id, filename, original_filename, file_path, file_size, source, status, upload_method, total_chunks, confidence_score, created_at FROM documents ORDER BY created_at DESC LIMIT :lim",
            "genesis_keys": "SELECT id, key_id, key_type, what_description, who_actor, where_location, when_timestamp, why_reason, how_method, is_error, file_path, tags FROM genesis_key ORDER BY when_timestamp DESC LIMIT :lim",
            "patterns": "SELECT id, pattern_name, pattern_type, trust_score, success_rate, created_at FROM learning_patterns ORDER BY trust_score DESC LIMIT :lim",
            "episodes": "SELECT id, problem, action, outcome, trust_score, source, created_at FROM episodes ORDER BY created_at DESC LIMIT :lim",
            "procedures": "SELECT id, name, goal, procedure_type, trust_score, success_rate, usage_count, created_at FROM procedures ORDER BY trust_score DESC LIMIT :lim",
        }

        query = queries.get(source)
        if not query:
            return []

        result = db.execute(text(query), {"lim": limit})
        columns = list(result.keys())
        rows = []
        for row in result.fetchall():
            record = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, datetime):
                    val = val.isoformat()
                elif hasattr(val, 'value'):
                    val = val.value
                record[col] = val
            rows.append(record)
        return rows
    except Exception as e:
        logger.error(f"Export fetch failed: {e}")
        return []
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Format converters
# ---------------------------------------------------------------------------

def _to_json(data: List[Dict], source: str) -> str:
    export = {
        "exported_at": datetime.utcnow().isoformat(),
        "source": source,
        "record_count": len(data),
        "data": data,
    }
    return json.dumps(export, indent=2, default=str)


def _to_csv(data: List[Dict]) -> str:
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    for row in data:
        writer.writerow({k: str(v)[:500] if v else "" for k, v in row.items()})
    return output.getvalue()


def _to_pdf_text(data: List[Dict], source: str) -> str:
    """Generate a text-based report (PDF generation needs reportlab in production)."""
    lines = []
    lines.append(f"GRACE EXPORT REPORT — {source.upper()}")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    lines.append(f"Records: {len(data)}")
    lines.append("=" * 60)
    lines.append("")

    for i, record in enumerate(data[:100]):
        lines.append(f"--- Record {i + 1} ---")
        for key, val in record.items():
            val_str = str(val)[:200] if val else ""
            lines.append(f"  {key}: {val_str}")
        lines.append("")

    if len(data) > 100:
        lines.append(f"... and {len(data) - 100} more records")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def export_data(request: ExportRequest):
    """Export data from any source as JSON, CSV, or PDF."""
    data = _fetch_data(request.source, request.filters, request.limit)

    if not data:
        return {"error": f"No data found for source: {request.source}", "records": 0}

    from api._genesis_tracker import track
    track(key_type="system", what=f"Export: {request.source} ({request.format}, {len(data)} records)",
          how="POST /api/v1/export", tags=["export", request.source, request.format])

    if request.format == "json":
        content = _to_json(data, request.source)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=grace_export_{request.source}_{datetime.utcnow().strftime('%Y%m%d')}.json"}
        )

    elif request.format == "csv":
        content = _to_csv(data)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=grace_export_{request.source}_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
        )

    elif request.format == "pdf":
        content = _to_pdf_text(data, request.source)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=grace_export_{request.source}_{datetime.utcnow().strftime('%Y%m%d')}.txt"}
        )

    return {"error": f"Unknown format: {request.format}"}


@router.get("/sources")
async def list_export_sources():
    """List available data sources for export."""
    return {"sources": [
        {"id": "training_data", "label": "Training Data", "description": "Learning examples with trust scores"},
        {"id": "documents", "label": "Documents", "description": "All documents in the library"},
        {"id": "genesis_keys", "label": "Genesis Keys", "description": "Provenance tracking records"},
        {"id": "patterns", "label": "Patterns", "description": "Learned patterns"},
        {"id": "episodes", "label": "Episodes", "description": "Episodic memory — concrete experiences"},
        {"id": "procedures", "label": "Procedures", "description": "Procedural memory — learned skills"},
    ]}
