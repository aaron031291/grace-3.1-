"""
Daily Report System — auto-generates reports of everything Grace achieved.

Reports include:
  - Genesis key activity summary
  - Brain actions executed
  - Errors found and fixed
  - Trust score changes
  - Pipeline runs and outcomes
  - Autonomous loop cycles
  - Code changes tracked

Reports are LLM-named, timestamped, stored in data/reports/,
downloadable and exportable.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"


def generate_daily_report(hours: int = 24) -> dict:
    """Generate a comprehensive report of Grace's activity."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "window_hours": hours,
        "sections": {},
    }

    # Genesis key summary
    try:
        from core.intelligence import GenesisKeyMiner
        miner = GenesisKeyMiner()
        patterns = miner.mine_patterns(hours=hours, limit=5000)
        report["sections"]["genesis_keys"] = {
            "total_keys": patterns.get("keys_analyzed", 0),
            "type_distribution": patterns.get("type_distribution", {}),
            "error_clusters": patterns.get("error_clusters", []),
            "temporal_patterns": patterns.get("temporal_patterns", {}),
            "repeated_failures": patterns.get("repeated_failures", []),
        }
    except Exception as e:
        report["sections"]["genesis_keys"] = {"error": str(e)}

    # Trust scores
    try:
        from core.intelligence import AdaptiveTrust
        report["sections"]["trust"] = AdaptiveTrust.get_all_trust()
    except Exception:
        report["sections"]["trust"] = {}

    # Autonomous loop
    try:
        from api.autonomous_loop_api import _loop_state, _loop_log
        report["sections"]["autonomous"] = {
            "state": dict(_loop_state),
            "recent_cycles": len(_loop_log),
        }
    except Exception:
        report["sections"]["autonomous"] = {}

    # Hebbian synapses
    try:
        from core.hebbian import get_hebbian_mesh
        mesh = get_hebbian_mesh()
        report["sections"]["synapses"] = {
            "strongest": mesh.get_strongest(5),
            "total_connections": len(mesh.get_weights()),
        }
    except Exception:
        report["sections"]["synapses"] = {}

    # Component health
    try:
        from api.brain_api_v2 import call_brain
        health = call_brain("system", "problems", {})
        if health.get("ok"):
            report["sections"]["health"] = health["data"]
    except Exception:
        report["sections"]["health"] = {}

    # Generate LLM-reasoned title
    title = _generate_title(report)
    report["title"] = title

    # Save
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60].strip().replace(" ", "_")
    filename = f"{timestamp}_{safe_title}.json"
    filepath = REPORTS_DIR / filename

    filepath.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Track via Genesis
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Daily report generated: {title}",
            who="report_system",
            output_data={"filename": filename, "sections": list(report["sections"].keys())},
            tags=["report", "daily"],
        )
    except Exception:
        pass

    return {
        "title": title,
        "filename": filename,
        "path": str(filepath),
        "sections": list(report["sections"].keys()),
        "generated_at": report["generated_at"],
        "downloadable": True,
    }


def _generate_title(report: dict) -> str:
    """Use LLM to generate a meaningful report title."""
    try:
        from api.brain_api_v2 import call_brain
        keys = report["sections"].get("genesis_keys", {}).get("total_keys", 0)
        errors = len(report["sections"].get("genesis_keys", {}).get("error_clusters", []))
        problems = report["sections"].get("health", {}).get("total", 0)

        r = call_brain("ai", "fast", {
            "prompt": f"Generate a SHORT title (max 8 words) for a daily report. "
                      f"Stats: {keys} operations, {errors} error types, {problems} problems. "
                      f"Return ONLY the title, nothing else.",
            "models": ["kimi"],
        })
        if r.get("ok"):
            title = r["data"].get("individual_responses", [{}])[0].get("response", "").strip()
            if title and len(title) < 80:
                return title.strip('"').strip("'")
    except Exception:
        pass

    return f"Grace Daily Report {datetime.utcnow().strftime('%Y-%m-%d')}"


def list_reports() -> list:
    """List all saved reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            reports.append({
                "filename": f.name,
                "title": data.get("title", f.stem),
                "generated_at": data.get("generated_at", ""),
                "sections": list(data.get("sections", {}).keys()),
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
        except Exception:
            reports.append({"filename": f.name, "title": f.stem})
    return reports


def get_report(filename: str) -> dict:
    """Get a specific report."""
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        return {"error": "Report not found"}
    return json.loads(filepath.read_text())
