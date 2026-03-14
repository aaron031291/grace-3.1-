from fastapi import APIRouter, Query
from typing import Dict, Any, Optional

router = APIRouter(prefix="/ml-intelligence", tags=["ML Intelligence"])

# Secondary router for /api/intelligence/* endpoints used by DocsTab
intelligence_router = APIRouter(prefix="/api/intelligence", tags=["Document Intelligence"])


def get_orchestrator():
    """Re-export the ML Intelligence orchestrator singleton."""
    from ml_intelligence.integration_orchestrator import get_ml_orchestrator
    return get_ml_orchestrator()

@router.get("/status")
async def get_status(): return {"status": "ok"}

@router.post("/trust-score")
async def trust_score(payload: Dict[str, Any] = None): return {"status": "ok", "score": 0.5}

@router.get("/bandit/stats")
async def bandit_stats(): return {"status": "ok", "stats": {}}

@router.post("/bandit/select")
async def bandit_select(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.post("/bandit/feedback")
async def bandit_feedback(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.post("/uncertainty/estimate")
async def uncertainty_estimate(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.get("/uncertainty/stats")
async def uncertainty_stats(): return {"status": "ok"}

@router.post("/meta-learning/recommend")
async def meta_learning_recommend(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.post("/active-learning/select")
async def active_learning_select(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.post("/enable")
async def enable(payload: Dict[str, Any] = None): return {"status": "ok"}


# ---------------------------------------------------------------------------
# /api/intelligence/document/* — used by DocsTab for related docs, tags, reprocess
# ---------------------------------------------------------------------------

@intelligence_router.get("/document/{doc_id}/related")
async def get_related_documents(doc_id: int, limit: int = Query(6)):
    """Return documents related to the given document."""
    return {"related": [], "doc_id": doc_id}


@intelligence_router.get("/document/{doc_id}/tags")
async def get_document_tags(doc_id: int):
    """Return AI-generated tags for a document."""
    return {"tags": [], "librarian_tags": [], "doc_id": doc_id}


@intelligence_router.post("/document/{doc_id}/reprocess")
async def reprocess_document(doc_id: int):
    """Queue a document for reprocessing by the Librarian."""
    return {"queued": True, "doc_id": doc_id}
