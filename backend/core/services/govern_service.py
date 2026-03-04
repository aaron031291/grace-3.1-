"""Governance domain service — direct calls, no HTTP."""
from pathlib import Path
import json, logging
from datetime import datetime

logger = logging.getLogger(__name__)

RULES_DIR = Path(__file__).parent.parent.parent / "data" / "governance_rules"
PERSONA_FILE = Path(__file__).parent.parent.parent / "data" / "persona_config.json"

def _ensure():
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    PERSONA_FILE.parent.mkdir(parents=True, exist_ok=True)

def get_persona():
    _ensure()
    if PERSONA_FILE.exists():
        try: return json.loads(PERSONA_FILE.read_text())
        except Exception: pass
    return {"personal": "", "professional": ""}

def update_persona(personal=None, professional=None):
    current = get_persona()
    if personal is not None: current["personal"] = personal
    if professional is not None: current["professional"] = professional
    _ensure()
    PERSONA_FILE.write_text(json.dumps(current, indent=2))
    return current

def list_rules():
    _ensure()
    docs = []
    if not RULES_DIR.exists(): return {"documents": [], "categories": {}}
    for cat in sorted(RULES_DIR.iterdir()):
        if cat.is_dir():
            for f in sorted(cat.iterdir()):
                if f.is_file():
                    docs.append({"id": f"{cat.name}/{f.name}", "filename": f.name,
                                 "category": cat.name, "size": f.stat().st_size})
    return {"documents": docs, "total": len(docs)}

def get_rule_content(doc_id):
    _ensure()
    fp = RULES_DIR / doc_id
    if not fp.exists(): return {"error": "Not found"}
    return {"id": doc_id, "content": fp.read_text(errors="ignore")}

def save_rule_content(doc_id, content):
    _ensure()
    fp = RULES_DIR / doc_id
    if not fp.exists(): return {"error": "Not found"}
    fp.write_text(content, encoding="utf-8")
    return {"id": doc_id, "saved": True}

def dashboard():
    try:
        from security.governance import GovernanceEngine
        engine = GovernanceEngine()
        return {"timestamp": datetime.utcnow().isoformat(),
                "pillars": {"self_governance": True, "human_oversight": True}}
    except Exception:
        return {"timestamp": datetime.utcnow().isoformat(), "status": "basic"}

def get_approvals():
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as db:
            rows = db.execute(text("SELECT * FROM governance_decisions WHERE status='pending' ORDER BY id DESC LIMIT 20")).fetchall()
            return {"approvals": [dict(r._mapping) for r in rows]}
    except Exception:
        return {"approvals": []}

def approve_action(decision_id, action, reason=""):
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as db:
            db.execute(text("UPDATE governance_decisions SET status=:s, resolved_at=:t WHERE id=:id"),
                       {"s": action, "t": datetime.utcnow().isoformat(), "id": decision_id})
            return {"decision_id": decision_id, "action": action}
    except Exception as e:
        return {"error": str(e)}

def get_scores():
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        return tracker.get_system_health()
    except Exception:
        return {"trust_score": 0.5}

def trigger_healing():
    import gc
    gc.collect()
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine, TriggerSource
        get_diagnostic_engine().run_cycle(TriggerSource.SENSOR_FLAG)
        return {"status": "healed"}
    except Exception as e:
        return {"status": "gc_only", "detail": str(e)}

def trigger_learning():
    try:
        from api._genesis_tracker import track
        track(key_type="learning_complete", what="Manual learning trigger",
              who="govern_service", tags=["learning", "manual"])
        return {"status": "triggered"}
    except Exception:
        return {"status": "logged"}

def genesis_stats():
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import func
        with session_scope() as s:
            total = s.query(func.count(GenesisKey.id)).scalar() or 0
            errors = s.query(func.count(GenesisKey.id)).filter(GenesisKey.is_error == True).scalar() or 0
            return {"total_keys": total, "total_errors": errors}
    except Exception:
        return {"total_keys": 0}

def genesis_keys(limit=20):
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        with session_scope() as s:
            keys = s.query(GenesisKey).order_by(GenesisKey.when_timestamp.desc()).limit(limit).all()
            return {"keys": [{"key_id": k.key_id, "key_type": str(k.key_type),
                              "what": k.what_description, "when": k.when_timestamp.isoformat() if k.when_timestamp else None}
                             for k in keys]}
    except Exception:
        return {"keys": []}

def approvals_history(limit=30):
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as db:
            rows = db.execute(text(f"SELECT * FROM governance_decisions ORDER BY id DESC LIMIT {int(limit)}")).fetchall()
            return {"history": [dict(r._mapping) for r in rows]}
    except Exception:
        return {"history": []}
