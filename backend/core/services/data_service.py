"""Data domain service — whitelist sources, flash cache."""
from pathlib import Path
import json, uuid, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "whitelist_sources"

def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["api_sources", "web_sources"]:
        (DATA_DIR / sub).mkdir(exist_ok=True)

def _load(kind):
    _ensure()
    p = DATA_DIR / f"{kind}.json"
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    return []

def _save(kind, data):
    _ensure()
    (DATA_DIR / f"{kind}.json").write_text(json.dumps(data, indent=2, default=str))

def api_sources(): return {"sources": _load("api_sources")}
def web_sources(): return {"sources": _load("web_sources")}

def add_api(payload):
    sources = _load("api_sources")
    source = {"id": f"api-{uuid.uuid4().hex[:8]}", "name": payload.get("name", ""),
              "url": payload.get("url", ""), "created_at": datetime.now(timezone.utc).isoformat()}
    sources.append(source)
    _save("api_sources", sources)
    return source

def add_web(payload):
    sources = _load("web_sources")
    source = {"id": f"web-{uuid.uuid4().hex[:8]}", "name": payload.get("name", ""),
              "url": payload.get("url", ""), "created_at": datetime.now(timezone.utc).isoformat()}
    sources.append(source)
    _save("web_sources", sources)
    return source

def delete_source(source_id):
    for kind in ["api_sources", "web_sources"]:
        sources = _load(kind)
        filtered = [s for s in sources if s.get("id") != source_id]
        if len(filtered) < len(sources):
            _save(kind, filtered)
            return {"deleted": True, "id": source_id}
    return {"error": "Not found"}

def stats():
    return {"api_source_count": len(_load("api_sources")),
            "web_source_count": len(_load("web_sources"))}

def flash_cache_stats():
    try:
        from cognitive.flash_cache import get_flash_cache
        return get_flash_cache().get_stats()
    except Exception:
        return {"entries": 0}
