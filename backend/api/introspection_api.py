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
