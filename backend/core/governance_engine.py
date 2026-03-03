"""
Governance Engine — per-project rules, approval workflow, KPI scoring.

Each project gets its own governance rules.
Approval table with approve/deny/discuss workflow.
KPI scoring per feature feeds into trust scores.
"""

import json
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


# ═══════════════════════════════════════════════════════════════════
#  PER-PROJECT GOVERNANCE
# ═══════════════════════════════════════════════════════════════════

def get_project_rules(project_id: str) -> dict:
    """Get governance rules for a specific project."""
    rules_dir = DATA_DIR / "projects" / project_id / "governance"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rules = []
    for f in sorted(rules_dir.glob("*")):
        if f.is_file():
            rules.append({
                "id": f.name,
                "name": f.stem,
                "size": f.stat().st_size,
                "content_preview": f.read_text(errors="ignore")[:200],
            })

    config_path = rules_dir / "_config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass

    return {"project_id": project_id, "rules": rules, "config": config, "total": len(rules)}


def set_project_rules(project_id: str, config: dict) -> dict:
    """Set governance config for a project."""
    rules_dir = DATA_DIR / "projects" / project_id / "governance"
    rules_dir.mkdir(parents=True, exist_ok=True)
    config_path = rules_dir / "_config.json"
    config["updated_at"] = datetime.utcnow().isoformat()
    config_path.write_text(json.dumps(config, indent=2))
    return {"saved": True, "project_id": project_id}


# ═══════════════════════════════════════════════════════════════════
#  APPROVAL WORKFLOW
# ═══════════════════════════════════════════════════════════════════

_approvals: List[dict] = []
_approval_lock = threading.Lock()
_approval_counter = 0


def create_approval(title: str, description: str, category: str = "general",
                    project_id: str = "", severity: str = "medium",
                    data: dict = None) -> dict:
    """Create a new approval request."""
    global _approval_counter
    with _approval_lock:
        _approval_counter += 1
        approval = {
            "id": _approval_counter,
            "title": title,
            "description": description,
            "category": category,
            "project_id": project_id,
            "severity": severity,
            "status": "pending",
            "data": data or {},
            "created_at": datetime.utcnow().isoformat(),
            "responses": [],
        }
        _approvals.append(approval)

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Approval created: {title}",
              who="governance_engine", tags=["approval", "pending", category])
    except Exception:
        pass

    return approval


def get_approvals(status: str = None, project_id: str = None) -> list:
    """Get approvals filtered by status and/or project."""
    with _approval_lock:
        result = list(_approvals)
    if status:
        result = [a for a in result if a["status"] == status]
    if project_id:
        result = [a for a in result if a["project_id"] == project_id]
    return result


def respond_to_approval(approval_id: int, action: str, reason: str = "",
                        user_id: str = "default") -> dict:
    """Approve, deny, or discuss an approval."""
    with _approval_lock:
        approval = next((a for a in _approvals if a["id"] == approval_id), None)
        if not approval:
            return {"error": "Approval not found"}

        response = {
            "action": action,
            "reason": reason,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        approval["responses"].append(response)

        if action in ("approve", "deny"):
            approval["status"] = "approved" if action == "approve" else "denied"
            approval["resolved_at"] = datetime.utcnow().isoformat()
        elif action == "discuss":
            approval["status"] = "discussing"

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Approval {action}: {approval['title']}",
              who=f"governance_engine.{user_id}",
              tags=["approval", action, approval.get("category", "")])
    except Exception:
        pass

    return approval


# ═══════════════════════════════════════════════════════════════════
#  KPI SCORING
# ═══════════════════════════════════════════════════════════════════

_kpi_scores: Dict[str, dict] = {}
_kpi_lock = threading.Lock()


def record_kpi(component: str, feature: str, passed: bool, layer: int = 0):
    """Record a KPI event — feature passed or failed at a layer."""
    key = f"{component}/{feature}"
    with _kpi_lock:
        if key not in _kpi_scores:
            _kpi_scores[key] = {
                "component": component,
                "feature": feature,
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "score": 0.0,
                "layers_passed": [],
            }
        entry = _kpi_scores[key]
        entry["total_checks"] += 1
        if passed:
            entry["passed"] += 1
            entry["layers_passed"].append(layer)
        else:
            entry["failed"] += 1
        entry["score"] = round(entry["passed"] / entry["total_checks"] * 100, 1)


def get_kpi_scores(component: str = None) -> dict:
    """Get KPI scores, optionally filtered by component."""
    with _kpi_lock:
        if component:
            scores = {k: v for k, v in _kpi_scores.items() if v["component"] == component}
        else:
            scores = dict(_kpi_scores)

    # Calculate overall trust from KPIs
    if scores:
        avg_score = sum(s["score"] for s in scores.values()) / len(scores)
        trust = avg_score / 100
    else:
        avg_score = 0
        trust = 0.5

    return {
        "scores": scores,
        "total_features": len(scores),
        "average_score": round(avg_score, 1),
        "trust_score": round(trust, 3),
    }


def get_kpi_dashboard() -> dict:
    """Full KPI dashboard grouped by component."""
    with _kpi_lock:
        by_component = defaultdict(list)
        for key, data in _kpi_scores.items():
            by_component[data["component"]].append(data)

    components = {}
    for comp, features in by_component.items():
        avg = sum(f["score"] for f in features) / len(features) if features else 0
        components[comp] = {
            "features": len(features),
            "average_score": round(avg, 1),
            "trust": round(avg / 100, 3),
            "details": features,
        }

    return {"components": components, "total_components": len(components)}


# ═══════════════════════════════════════════════════════════════════
#  COMPLIANCE PRESETS
# ═══════════════════════════════════════════════════════════════════

COMPLIANCE_PRESETS = {
    "iso_27001": {
        "name": "ISO 27001 Information Security",
        "rules": [
            "All data must be encrypted at rest and in transit",
            "Access control must follow least privilege principle",
            "All security events must be logged and auditable",
            "Regular security assessments must be conducted",
            "Incident response procedures must be documented",
        ],
    },
    "gdpr": {
        "name": "GDPR Data Protection",
        "rules": [
            "Personal data processing requires explicit consent",
            "Data subjects have the right to access and delete their data",
            "Data breaches must be reported within 72 hours",
            "Privacy by design must be implemented",
            "Data processing records must be maintained",
        ],
    },
    "soc2": {
        "name": "SOC 2 Trust Services",
        "rules": [
            "Security controls must prevent unauthorized access",
            "Availability SLAs must be defined and monitored",
            "Processing integrity must be verified",
            "Confidentiality of data must be maintained",
            "Privacy commitments must be documented",
        ],
    },
    "owasp": {
        "name": "OWASP Top 10 Security",
        "rules": [
            "Prevent injection attacks (SQL, NoSQL, LDAP)",
            "Implement proper authentication and session management",
            "Protect against cross-site scripting (XSS)",
            "Enforce access control on every request",
            "Security configuration must be hardened",
        ],
    },
}


def get_compliance_presets() -> dict:
    return {"presets": COMPLIANCE_PRESETS, "total": len(COMPLIANCE_PRESETS)}


def apply_compliance_preset(project_id: str, preset_name: str) -> dict:
    """Apply a compliance preset to a project."""
    preset = COMPLIANCE_PRESETS.get(preset_name)
    if not preset:
        return {"error": f"Unknown preset: {preset_name}"}

    rules_dir = DATA_DIR / "projects" / project_id / "governance"
    rules_dir.mkdir(parents=True, exist_ok=True)

    filename = f"compliance_{preset_name}.md"
    content = f"# {preset['name']}\n\n" + "\n".join(f"- {r}" for r in preset["rules"])
    (rules_dir / filename).write_text(content)

    return {"applied": True, "project_id": project_id, "preset": preset_name,
            "rules_count": len(preset["rules"])}
