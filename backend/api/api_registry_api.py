"""
API Registry — Catalogue of every API endpoint in Grace

Shows all APIs categorised as internal/external, with:
- What, Where, When, How, Who, Why metadata
- Color-coded status: live (green), unconnected (yellow), broken (red)
- Broken API diagnostics with metadata on why
- Kimi reasoning for broken endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import requests as req

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/registry", tags=["API Registry"])


API_METADATA = {
    "/api/world-model": {"category": "internal", "who": "World Model", "why": "Bird's eye system view", "group": "Core Intelligence"},
    "/api/mcp": {"category": "internal", "who": "MCP Orchestrator", "why": "Tool-calling chat with file/terminal access", "group": "Core Intelligence"},
    "/api/docs": {"category": "internal", "who": "Docs Library", "why": "Central document registry", "group": "Knowledge"},
    "/api/librarian-fs": {"category": "internal", "who": "Librarian", "why": "Autonomous file management CRUD", "group": "Knowledge"},
    "/api/governance-hub": {"category": "internal", "who": "Governance Hub", "why": "Approvals, scores, healing, learning", "group": "Governance"},
    "/api/governance-rules": {"category": "internal", "who": "Governance Rules", "why": "Law documents and persona", "group": "Governance"},
    "/api/genesis-daily": {"category": "internal", "who": "Genesis Daily", "why": "24hr genesis key logs", "group": "Governance"},
    "/api/whitelist-hub": {"category": "internal", "who": "Whitelist Hub", "why": "API/web sources for learning", "group": "Learning"},
    "/api/oracle": {"category": "internal", "who": "Oracle", "why": "Training data store and audit", "group": "Learning"},
    "/api/codebase-hub": {"category": "internal", "who": "Codebase Hub", "why": "Code projects and coding agent", "group": "Development"},
    "/api/tasks-hub": {"category": "internal", "who": "Tasks Hub", "why": "Real-time activity, task submission, scheduling", "group": "Operations"},
    "/api/intelligence": {"category": "internal", "who": "Cross-Tab Intelligence", "why": "Folder chat, tags, relationships", "group": "Core Intelligence"},
    "/api/bridge": {"category": "internal", "who": "System Bridge", "why": "Aggregates all 190+ backend systems", "group": "Infrastructure"},
    "/chats": {"category": "internal", "who": "Chat Engine", "why": "Chat session management", "group": "Core Intelligence"},
    "/chat": {"category": "internal", "who": "Chat Engine", "why": "Chat with RAG", "group": "Core Intelligence"},
    "/retrieve": {"category": "internal", "who": "RAG Retrieval", "why": "Semantic search and retrieval", "group": "Knowledge"},
    "/ingest": {"category": "internal", "who": "Ingestion", "why": "Document ingestion pipeline", "group": "Knowledge"},
    "/files": {"category": "internal", "who": "File Manager", "why": "File upload and management", "group": "Knowledge"},
    "/librarian": {"category": "internal", "who": "Librarian", "why": "Tag, relationship, rule management", "group": "Knowledge"},
    "/cognitive": {"category": "internal", "who": "Cognitive Engine", "why": "OODA decisions, ambiguity tracking", "group": "Core Intelligence"},
    "/governance": {"category": "internal", "who": "Governance Framework", "why": "Three-pillar governance rules", "group": "Governance"},
    "/kpi": {"category": "internal", "who": "KPI Tracker", "why": "Component trust scores and metrics", "group": "Governance"},
    "/monitoring": {"category": "internal", "who": "Monitoring", "why": "System health and organs progress", "group": "Operations"},
    "/telemetry": {"category": "internal", "who": "Telemetry", "why": "Operation logs and drift alerts", "group": "Operations"},
    "/diagnostic": {"category": "internal", "who": "Diagnostic Machine", "why": "4-layer diagnostic engine", "group": "Operations"},
    "/training": {"category": "internal", "who": "Training", "why": "Active learning study/practice", "group": "Learning"},
    "/autonomous-learning": {"category": "internal", "who": "Autonomous Learning", "why": "Multi-process learning subagents", "group": "Learning"},
    "/ml-intelligence": {"category": "internal", "who": "ML Intelligence", "why": "Neural trust, bandits, meta-learning", "group": "Learning"},
    "/learning-memory": {"category": "internal", "who": "Learning Memory", "why": "Learning examples and trust scoring", "group": "Learning"},
    "/genesis-keys": {"category": "internal", "who": "Genesis Keys", "why": "Provenance and lineage tracking", "group": "Governance"},
    "/genesis": {"category": "internal", "who": "Genesis", "why": "Genesis key management", "group": "Governance"},
    "/agent": {"category": "internal", "who": "Agent", "why": "Software engineering agent", "group": "Development"},
    "/api/cicd": {"category": "internal", "who": "CI/CD", "why": "Build and deployment pipelines", "group": "Development"},
    "/version-control": {"category": "internal", "who": "Version Control", "why": "Git operations", "group": "Development"},
    "/repositories": {"category": "internal", "who": "Repositories", "why": "Repository management", "group": "Development"},
    "/codebase": {"category": "internal", "who": "Codebase Browser", "why": "Code browsing and search", "group": "Development"},
    "/api/ide": {"category": "internal", "who": "IDE Bridge", "why": "VSCode extension bridge", "group": "Development"},
    "/api/grace-planning": {"category": "internal", "who": "Planning", "why": "Planning workflow", "group": "Development"},
    "/api/grace-todos": {"category": "internal", "who": "Todos", "why": "Task management", "group": "Operations"},
    "/scrape": {"category": "internal", "who": "Web Scraper", "why": "URL scraping and crawling", "group": "External"},
    "/voice": {"category": "internal", "who": "Voice", "why": "Speech-to-text and TTS", "group": "Communication"},
    "/notion": {"category": "internal", "who": "Notion", "why": "Task management integration", "group": "External"},
    "/knowledge-base": {"category": "internal", "who": "Knowledge Base", "why": "KB connectors", "group": "Knowledge"},
    "/sandbox-lab": {"category": "internal", "who": "Sandbox Lab", "why": "Self-improvement experiments", "group": "Learning"},
    "/health": {"category": "internal", "who": "Health", "why": "System health checks", "group": "Infrastructure"},
    "/metrics": {"category": "internal", "who": "Metrics", "why": "Prometheus metrics", "group": "Infrastructure"},
    "/auth": {"category": "internal", "who": "Auth", "why": "Authentication", "group": "Infrastructure"},
    "/api/whitelist": {"category": "internal", "who": "Whitelist Pipeline", "why": "Whitelist learning pipeline", "group": "Learning"},
    "/api/autonomous": {"category": "internal", "who": "Autonomous Engine", "why": "Autonomous action execution", "group": "Operations"},
}

EXTERNAL_APIS = [
    {"name": "Kimi 2.5 (Moonshot)", "url": "https://api.moonshot.cn/v1", "category": "external", "who": "Moonshot AI", "why": "Cloud LLM reasoning", "group": "External LLM", "check_path": "/models"},
    {"name": "Ollama", "url": "http://localhost:11434", "category": "external", "who": "Ollama", "why": "Local LLM inference", "group": "External LLM", "check_path": "/api/tags"},
    {"name": "Qdrant", "url": "http://localhost:6333", "category": "external", "who": "Qdrant", "why": "Vector database", "group": "External DB", "check_path": "/collections"},
]


class KimiDiagnoseRequest(BaseModel):
    api_path: str
    error_info: Optional[str] = None


def _get_route_info() -> List[Dict[str, Any]]:
    """Introspect all registered routes from the FastAPI app."""
    try:
        from app import app
        routes = []
        seen = set()
        for route in app.routes:
            if not hasattr(route, "methods"):
                continue
            for method in route.methods:
                if method in ("HEAD", "OPTIONS"):
                    continue
                key = f"{method} {route.path}"
                if key in seen:
                    continue
                seen.add(key)

                prefix = "/" + route.path.strip("/").split("/")[0] if route.path != "/" else "/"
                api_prefix = None
                for known in sorted(API_METADATA.keys(), key=len, reverse=True):
                    if route.path.startswith(known):
                        api_prefix = known
                        break

                meta = API_METADATA.get(api_prefix, {})

                routes.append({
                    "method": method,
                    "path": route.path,
                    "prefix": api_prefix or prefix,
                    "name": getattr(route, "name", ""),
                    "category": meta.get("category", "internal"),
                    "who": meta.get("who", "Unknown"),
                    "why": meta.get("why", ""),
                    "group": meta.get("group", "Other"),
                })
        return routes
    except Exception as e:
        logger.error(f"Route introspection failed: {e}")
        return []


def _check_internal(path: str) -> Dict[str, Any]:
    """Health-check an internal endpoint."""
    try:
        url = f"http://localhost:8000{path}"
        r = req.get(url, timeout=5)
        return {"status": "live" if r.status_code < 500 else "broken",
                "code": r.status_code, "response_ms": r.elapsed.total_seconds() * 1000}
    except req.ConnectionError:
        return {"status": "unconnected", "error": "Connection refused"}
    except req.Timeout:
        return {"status": "broken", "error": "Timeout"}
    except Exception as e:
        return {"status": "broken", "error": str(e)}


def _check_external(url: str, check_path: str, headers: dict = None) -> Dict[str, Any]:
    """Health-check an external service."""
    try:
        r = req.get(f"{url}{check_path}", timeout=5, headers=headers or {})
        return {"status": "live" if r.status_code < 500 else "broken",
                "code": r.status_code, "response_ms": r.elapsed.total_seconds() * 1000}
    except req.ConnectionError:
        return {"status": "unconnected", "error": "Connection refused"}
    except req.Timeout:
        return {"status": "broken", "error": "Timeout"}
    except Exception as e:
        return {"status": "broken", "error": str(e)}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/all")
async def get_all_apis():
    """Get every API endpoint categorised with metadata."""
    routes = _get_route_info()

    groups: Dict[str, list] = {}
    for r in routes:
        g = r["group"]
        if g not in groups:
            groups[g] = []
        groups[g].append(r)

    external = []
    for ext in EXTERNAL_APIS:
        health = _check_external(ext["url"], ext.get("check_path", "/"))
        external.append({**ext, "health": health})

    return {
        "total_routes": len(routes),
        "groups": {g: {"name": g, "count": len(items), "routes": items} for g, items in sorted(groups.items())},
        "external_services": external,
    }


@router.get("/health-check")
async def health_check_all():
    """Run health checks on key API prefixes."""
    check_paths = [
        "/health", "/api/world-model/subsystems", "/api/docs/stats",
        "/api/governance-hub/dashboard", "/api/oracle/dashboard",
        "/api/tasks-hub/live", "/api/registry/all",
    ]

    results = []
    for path in check_paths:
        meta = {}
        for known in sorted(API_METADATA.keys(), key=len, reverse=True):
            if path.startswith(known):
                meta = API_METADATA[known]
                break
        health = _check_internal(path)
        results.append({
            "path": path,
            "who": meta.get("who", "Unknown"),
            "group": meta.get("group", "Other"),
            **health,
        })

    external = []
    for ext in EXTERNAL_APIS:
        health = _check_external(ext["url"], ext.get("check_path", "/"))
        external.append({"name": ext["name"], "url": ext["url"], **health})

    live = sum(1 for r in results if r["status"] == "live")
    broken = sum(1 for r in results if r["status"] == "broken")
    unconnected = sum(1 for r in results if r["status"] == "unconnected")

    return {
        "summary": {"live": live, "broken": broken, "unconnected": unconnected, "total": len(results)},
        "internal": results,
        "external": external,
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.post("/diagnose")
async def diagnose_api(request: KimiDiagnoseRequest):
    """Use Kimi to reason about why an API is broken and how to fix it."""
    health = _check_internal(request.api_path)
    meta = {}
    for known in sorted(API_METADATA.keys(), key=len, reverse=True):
        if request.api_path.startswith(known):
            meta = API_METADATA[known]
            break

    prompt = (
        f"Diagnose this API endpoint and explain why it might be broken:\n\n"
        f"Endpoint: {request.api_path}\n"
        f"Owner: {meta.get('who', 'Unknown')}\n"
        f"Purpose: {meta.get('why', 'Unknown')}\n"
        f"Group: {meta.get('group', 'Unknown')}\n"
        f"Health check result: {health}\n"
        f"Additional error info: {request.error_info or 'None'}\n\n"
        f"Provide:\n1. Likely root cause\n2. How to fix it\n3. Impact on the system\n4. Priority level"
    )

    try:
        from llm_orchestrator.factory import get_kimi_client
        client = get_kimi_client()
        response = client.generate(
            prompt=prompt,
            system_prompt="You are Grace's API diagnostics intelligence. Analyse broken APIs and provide actionable fixes.",
            temperature=0.3, max_tokens=2048,
        )

        from api._genesis_tracker import track
        track(key_type="ai_response", what=f"API diagnosis: {request.api_path}",
              how="POST /api/registry/diagnose", tags=["api_registry", "diagnose"])

        return {"path": request.api_path, "health": health, "meta": meta, "diagnosis": response}
    except Exception as e:
        return {"path": request.api_path, "health": health, "meta": meta, "diagnosis": f"Kimi unavailable: {e}"}
