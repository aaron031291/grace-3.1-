"""
System Introspection & Deterministic Validation API
=====================================================
Enables anyone to search, explore, and validate the entire Grace system.

Endpoints:
- GET  /api/system/search?q=...          - Search everything (files, APIs, models, configs)
- GET  /api/system/index                 - Full system index
- GET  /api/system/index/files           - All indexed files
- GET  /api/system/index/endpoints       - All API endpoints
- GET  /api/system/index/connectors      - All Layer 1 connectors with actions
- GET  /api/system/index/models          - All models, weights, LLM configs
- GET  /api/system/index/data-flows      - Data flow relationships
- GET  /api/system/index/rebuild         - Force rebuild index
- GET  /api/system/validate              - Run deterministic validation
- GET  /api/system/validate/silent       - Find silent failures
- GET  /api/system/validate/wiring       - Find unwired routers
- GET  /api/system/validate/imports      - Find broken imports
- GET  /api/system/validate/kimi-opus    - Validate Kimi/Opus connectivity
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System Introspection"])


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search")
async def search_system(
    q: str = Query(..., description="Search query — files, APIs, models, configs, connectors"),
):
    """
    Search the entire Grace system.
    
    A newcomer can ask anything: 'consensus engine', 'kimi', 'RAG',
    'embedding', 'database', 'healing' — and get back relevant files,
    endpoints, connectors, classes, functions, and settings.
    """
    from system_introspector import search_system as _search
    return _search(q)


# ---------------------------------------------------------------------------
# System Index
# ---------------------------------------------------------------------------

@router.get("/index")
async def get_system_index():
    """
    Full system index — every file, endpoint, connector, model, setting.
    This is the complete cognitive map of Grace.
    """
    from system_introspector import get_system_index
    index = get_system_index()
    summary = {
        "timestamp": index.timestamp,
        "file_count": index.file_count,
        "total_classes": index.total_classes,
        "total_functions": index.total_functions,
        "total_endpoints": index.total_endpoints,
        "connector_count": len(index.connectors),
        "llm_providers": len(index.models.get("llm_providers", [])),
        "ml_models": len(index.models.get("ml_models", [])),
        "settings_count": len(index.settings),
        "data_flows": len(index.data_flows),
        "categories": {},
    }
    for f in index.files:
        summary["categories"][f.category] = summary["categories"].get(f.category, 0) + 1
    return summary


@router.get("/index/files")
async def get_indexed_files(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """All indexed Python files with classes, functions, imports."""
    from system_introspector import get_system_index
    index = get_system_index()
    from dataclasses import asdict
    files = index.files
    if category:
        files = [f for f in files if f.category == category]
    return {"files": [asdict(f) for f in files], "total": len(files)}


@router.get("/index/endpoints")
async def get_indexed_endpoints():
    """All discovered API endpoints with methods, paths, functions."""
    from system_introspector import get_system_index
    index = get_system_index()
    from dataclasses import asdict
    return {"endpoints": [asdict(e) for e in index.endpoints], "total": len(index.endpoints)}


@router.get("/index/connectors")
async def get_indexed_connectors():
    """All Layer 1 connectors with autonomous actions, handlers, subscriptions."""
    from system_introspector import get_system_index
    index = get_system_index()
    from dataclasses import asdict
    return {"connectors": [asdict(c) for c in index.connectors], "total": len(index.connectors)}


@router.get("/index/models")
async def get_indexed_models():
    """All models, weights, LLM configurations."""
    from system_introspector import get_system_index
    index = get_system_index()
    return index.models


@router.get("/index/data-flows")
async def get_data_flows():
    """Data flow relationships between components."""
    from system_introspector import get_system_index
    index = get_system_index()
    return {"data_flows": index.data_flows, "total": len(index.data_flows)}


@router.post("/index/rebuild")
async def rebuild_index():
    """Force rebuild the system index."""
    from system_introspector import get_system_index
    index = get_system_index(force_rebuild=True)
    return {
        "status": "rebuilt",
        "file_count": index.file_count,
        "total_classes": index.total_classes,
        "total_functions": index.total_functions,
        "total_endpoints": index.total_endpoints,
    }


# ---------------------------------------------------------------------------
# Deterministic Validation
# ---------------------------------------------------------------------------

@router.get("/validate")
async def run_validation():
    """
    Run full deterministic validation pipeline.
    
    Finds: silent failures, unwired routers, broken imports,
    Layer 1 initialization issues, config gaps, Kimi/Opus connectivity.
    
    No LLM needed. Pure structural analysis.
    """
    from deterministic_validator import run_full_validation
    report = run_full_validation()
    return report.to_dict()


@router.get("/validate/silent-failures")
async def detect_silent_failures():
    """Find all except:pass and error-swallowing patterns."""
    from deterministic_validator import detect_silent_failures as _detect
    issues = _detect()
    from dataclasses import asdict
    return {
        "category": "silent_failures",
        "total": len(issues),
        "issues": [asdict(i) for i in issues],
    }


@router.get("/validate/wiring")
async def detect_wiring_issues():
    """Find API routers that exist but aren't registered in app.py."""
    from deterministic_validator import detect_unwired_routers
    issues = detect_unwired_routers()
    from dataclasses import asdict
    return {
        "category": "unwired_routers",
        "total": len(issues),
        "issues": [asdict(i) for i in issues],
    }


@router.get("/validate/imports")
async def detect_import_issues():
    """Find imports referencing non-existent modules."""
    from deterministic_validator import detect_broken_imports
    issues = detect_broken_imports()
    from dataclasses import asdict
    return {
        "category": "broken_imports",
        "total": len(issues),
        "issues": [asdict(i) for i in issues],
    }


@router.get("/validate/kimi-opus")
async def validate_kimi_opus():
    """Validate Kimi and Opus are properly wired and reachable."""
    from deterministic_validator import validate_kimi_opus as _validate
    issues = _validate()
    from deterministic_validator import validate_configuration
    config_issues = [i for i in validate_configuration()
                     if 'kimi' in i.message.lower() or 'opus' in i.message.lower()]
    all_issues = issues + config_issues
    from dataclasses import asdict
    return {
        "category": "kimi_opus",
        "total": len(all_issues),
        "issues": [asdict(i) for i in all_issues],
    }


@router.get("/validate/layer1")
async def validate_layer1():
    """Check Layer 1 message bus and connector initialization."""
    from deterministic_validator import check_layer1_initialization
    issues = check_layer1_initialization()
    from dataclasses import asdict
    return {
        "category": "layer1_initialization",
        "total": len(issues),
        "issues": [asdict(i) for i in issues],
    }


# ---------------------------------------------------------------------------
# Problems + Kimi/Opus
# ---------------------------------------------------------------------------

class AskAboutProblemsRequest(BaseModel):
    question: str
    use_kimi: bool = True
    use_opus: bool = True


@router.get("/problems")
async def get_all_problems():
    """
    Find ALL problems in the system right now.

    Combines:
    1. Deterministic validation (broken imports, silent failures, unwired routers)
    2. Connection validation (which services are connected/disconnected)
    3. Runtime health (database, LLM, Qdrant, embedding)

    Returns a single unified problem list that you can then feed to
    /api/system/problems/ask-kimi-opus to get AI-powered fix suggestions.
    """
    from dataclasses import asdict

    problems = {
        "timestamp": None,
        "total_problems": 0,
        "critical": 0,
        "warning": 0,
        "categories": {},
        "structural_issues": [],
        "connection_issues": [],
        "runtime_issues": [],
    }

    # 1. Structural issues (deterministic)
    try:
        from deterministic_validator import run_full_validation
        validation = run_full_validation()
        problems["timestamp"] = validation.timestamp

        for issue in validation.issues:
            if issue.file.startswith("tests/"):
                continue
            entry = asdict(issue)
            problems["structural_issues"].append(entry)
            cat = issue.category
            problems["categories"][cat] = problems["categories"].get(cat, 0) + 1
            if issue.severity == "critical":
                problems["critical"] += 1
            elif issue.severity == "warning":
                problems["warning"] += 1
    except Exception as e:
        problems["structural_issues"].append({
            "category": "validator_error", "severity": "critical",
            "file": "deterministic_validator.py", "line": None,
            "message": f"Validator failed: {e}",
        })

    # 2. Connection issues
    try:
        from connection_validator import validate_all_connections, ConnectionStatus
        conn_report = validate_all_connections()
        for conn in conn_report.connections:
            if conn.status in (ConnectionStatus.DISCONNECTED, ConnectionStatus.DEGRADED):
                entry = {
                    "name": conn.name,
                    "category": conn.category.value,
                    "status": conn.status.value,
                    "message": conn.message,
                    "actions_failing": conn.actions_failing,
                    "actions_total": conn.actions_total,
                }
                problems["connection_issues"].append(entry)
                problems["categories"]["disconnected_service"] = (
                    problems["categories"].get("disconnected_service", 0) + 1
                )
                problems["critical"] += 1
    except Exception as e:
        problems["connection_issues"].append({
            "name": "connection_validator",
            "status": "error",
            "message": str(e),
        })

    # 3. Runtime health
    try:
        from api.health import check_llm, check_database, check_qdrant, check_embedding_model
        import asyncio

        async def _gather():
            return await asyncio.gather(
                check_llm(), check_database(), check_qdrant(), check_embedding_model(),
                return_exceptions=True,
            )

        loop = asyncio.get_event_loop()
        if loop.is_running():
            health_checks = []
        else:
            health_checks = loop.run_until_complete(_gather())

        for check in health_checks:
            if hasattr(check, 'status') and check.status in ("unhealthy", "degraded"):
                problems["runtime_issues"].append({
                    "service": check.name,
                    "status": check.status,
                    "message": check.message,
                })
                problems["categories"]["runtime_unhealthy"] = (
                    problems["categories"].get("runtime_unhealthy", 0) + 1
                )
    except Exception:
        pass

    problems["total_problems"] = (
        len(problems["structural_issues"])
        + len(problems["connection_issues"])
        + len(problems["runtime_issues"])
    )

    return problems


@router.post("/problems/ask-kimi-opus")
async def ask_kimi_opus_about_problems(request: AskAboutProblemsRequest):
    """
    Ask Kimi and/or Opus about the system's problems.

    First runs the full problem scan, then sends the results plus your
    question to Kimi and Opus for AI-powered diagnosis and fix suggestions.

    Example questions:
    - "What are the most important things to fix first?"
    - "Why is Qdrant disconnected and how do I fix it?"
    - "Explain the silent failures and which ones matter"
    - "Give me a prioritized fix plan"
    """
    # Get current problems
    problems_data = await get_all_problems()

    # Build context for the models
    problem_summary = (
        f"Grace system has {problems_data['total_problems']} problems: "
        f"{problems_data['critical']} critical, {problems_data['warning']} warnings.\n\n"
    )

    if problems_data["connection_issues"]:
        problem_summary += "DISCONNECTED SERVICES:\n"
        for c in problems_data["connection_issues"][:10]:
            problem_summary += f"  - {c['name']} ({c.get('category', '')}): {c.get('message', 'disconnected')}\n"
        problem_summary += "\n"

    if problems_data["structural_issues"]:
        # Group by category for summary
        by_cat = {}
        for s in problems_data["structural_issues"]:
            cat = s["category"]
            by_cat.setdefault(cat, []).append(s)

        problem_summary += "STRUCTURAL ISSUES:\n"
        for cat, items in by_cat.items():
            critical_items = [i for i in items if i["severity"] == "critical"]
            problem_summary += f"  - {cat}: {len(items)} total ({len(critical_items)} critical)\n"
            for item in critical_items[:3]:
                problem_summary += f"    * {item['file']}:{item.get('line', '?')} - {item['message'][:100]}\n"
        problem_summary += "\n"

    if problems_data["runtime_issues"]:
        problem_summary += "RUNTIME ISSUES:\n"
        for r in problems_data["runtime_issues"]:
            problem_summary += f"  - {r['service']}: {r['status']} - {r.get('message', '')}\n"

    full_prompt = (
        f"You are analyzing the Grace AI system. Here is the current state:\n\n"
        f"{problem_summary}\n"
        f"User question: {request.question}\n\n"
        f"Give specific, actionable answers. Reference file paths and exact fixes."
    )

    responses = {}

    # Ask Kimi
    if request.use_kimi:
        try:
            from llm_orchestrator.kimi_client import KimiLLMClient
            kimi = KimiLLMClient()
            if kimi.api_key:
                kimi_response = kimi.generate(
                    prompt=full_prompt,
                    system_prompt="You are a senior systems engineer analyzing the Grace AI platform. Be specific and actionable.",
                    temperature=0.3,
                    max_tokens=2048,
                )
                responses["kimi"] = {
                    "model": "kimi",
                    "response": kimi_response,
                    "status": "success",
                }
            else:
                responses["kimi"] = {"model": "kimi", "status": "no_api_key", "response": None}
        except Exception as e:
            responses["kimi"] = {"model": "kimi", "status": "error", "error": str(e), "response": None}

    # Ask Opus
    if request.use_opus:
        try:
            from llm_orchestrator.opus_client import OpusLLMClient
            opus = OpusLLMClient()
            if opus.api_key:
                opus_response = opus.generate(
                    prompt=full_prompt,
                    system_prompt="You are a senior systems engineer analyzing the Grace AI platform. Be specific and actionable.",
                    temperature=0.3,
                    max_tokens=2048,
                )
                responses["opus"] = {
                    "model": "opus",
                    "response": opus_response,
                    "status": "success",
                }
            else:
                responses["opus"] = {"model": "opus", "status": "no_api_key", "response": None}
        except Exception as e:
            responses["opus"] = {"model": "opus", "status": "error", "error": str(e), "response": None}

    return {
        "question": request.question,
        "problem_count": problems_data["total_problems"],
        "critical_count": problems_data["critical"],
        "responses": responses,
        "problem_summary": problem_summary,
    }


@router.post("/ask")
async def ask_about_system(request: AskAboutProblemsRequest):
    """
    Ask Kimi and/or Opus anything about the Grace system.

    This searches the system index for context relevant to your question,
    then sends it to the models along with your question.

    Example questions:
    - "How does the consensus engine work?"
    - "What connects to the memory mesh?"
    - "Explain the RAG pipeline data flow"
    - "What models are configured and which are working?"
    """
    from system_introspector import search_system

    # Search for relevant context
    search_results = search_system(request.question)

    context = f"Grace system search results for '{request.question}':\n\n"

    if search_results.get("files"):
        context += "RELEVANT FILES:\n"
        for f in search_results["files"][:8]:
            context += f"  - {f['path']} ({f['category']}): {f.get('docstring', '')[:150]}\n"
        context += "\n"

    if search_results.get("endpoints"):
        context += "RELEVANT API ENDPOINTS:\n"
        for e in search_results["endpoints"][:5]:
            context += f"  - {e['method']} {e['path']} -> {e['function']} ({e['file']})\n"
        context += "\n"

    if search_results.get("connectors"):
        context += "RELEVANT CONNECTORS:\n"
        for c in search_results["connectors"][:5]:
            context += f"  - {c['name']} ({c['type']}): {c['file']}\n"
        context += "\n"

    full_prompt = (
        f"You are explaining the Grace AI system architecture.\n\n"
        f"{context}\n"
        f"User question: {request.question}\n\n"
        f"Answer based on the system information above. Be specific about file paths and connections."
    )

    responses = {}

    if request.use_kimi:
        try:
            from llm_orchestrator.kimi_client import KimiLLMClient
            kimi = KimiLLMClient()
            if kimi.api_key:
                responses["kimi"] = {
                    "model": "kimi",
                    "response": kimi.generate(prompt=full_prompt, temperature=0.3, max_tokens=2048),
                    "status": "success",
                }
            else:
                responses["kimi"] = {"model": "kimi", "status": "no_api_key", "response": None}
        except Exception as e:
            responses["kimi"] = {"model": "kimi", "status": "error", "error": str(e), "response": None}

    if request.use_opus:
        try:
            from llm_orchestrator.opus_client import OpusLLMClient
            opus = OpusLLMClient()
            if opus.api_key:
                responses["opus"] = {
                    "model": "opus",
                    "response": opus.generate(prompt=full_prompt, temperature=0.3, max_tokens=2048),
                    "status": "success",
                }
            else:
                responses["opus"] = {"model": "opus", "status": "no_api_key", "response": None}
        except Exception as e:
            responses["opus"] = {"model": "opus", "status": "error", "error": str(e), "response": None}

    return {
        "question": request.question,
        "search_results_count": search_results.get("total_results", 0),
        "responses": responses,
        "context_used": context[:500] + "..." if len(context) > 500 else context,
    }
