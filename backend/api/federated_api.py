"""
Federated Learning API — REST endpoints for the Oracle tab's federation panel.

Provides federation status, node management, aggregation rounds,
and knowledge import/export for cross-instance learning.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from dataclasses import asdict

router = APIRouter(prefix="/api/federated", tags=["Federated Learning"])


def _mgr():
    """Lazy singleton for FederatedLearningManager."""
    from ml_intelligence.federated_learning import get_federated_manager
    return get_federated_manager()


# ── Status ────────────────────────────────────────────────────────────

@router.get("/status", response_model=dict)
def get_federation_status():
    """Overall federation status."""
    try:
        return _mgr().get_federation_status()
    except ImportError:
        return {
            "registered_nodes": 0, "active_nodes": 0,
            "total_rounds": 0, "global_model_version": 0,
            "privacy": {}, "last_aggregation": None,
            "torch_available": False, "status": "unavailable",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Nodes ─────────────────────────────────────────────────────────────

@router.get("/nodes", response_model=dict)
def list_nodes():
    """List registered nodes."""
    try:
        nodes = _mgr().get_nodes()
        return {"nodes": nodes, "total": len(nodes)}
    except ImportError:
        return {"nodes": [], "total": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NodeRegisterRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/nodes/register", response_model=dict)
def register_node(payload: NodeRegisterRequest):
    """Register a new federation node."""
    try:
        node = _mgr().register_node(
            name=payload.name, description=payload.description,
        )
        return {"registered": True, **asdict(node)}
    except ImportError:
        raise HTTPException(status_code=503, detail="Federated module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Aggregation ───────────────────────────────────────────────────────

@router.post("/round", response_model=dict)
def trigger_aggregation_round():
    """Trigger a federated aggregation round."""
    try:
        return _mgr().run_aggregation_round()
    except ImportError:
        raise HTTPException(status_code=503, detail="Federated module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rounds", response_model=dict)
def get_round_history(limit: int = Query(50, ge=1, le=500)):
    """Aggregation round history."""
    try:
        rounds = _mgr().get_rounds_history(limit=limit)
        return {"rounds": rounds, "total": len(rounds)}
    except ImportError:
        return {"rounds": [], "total": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Knowledge Exchange ────────────────────────────────────────────────

class KnowledgeExportRequest(BaseModel):
    min_trust: float = 0.4
    types: Optional[List[str]] = None


@router.post("/knowledge/export", response_model=dict)
def export_knowledge(payload: KnowledgeExportRequest):
    """Export a distilled knowledge package."""
    try:
        fm = _mgr()
        # Fetch learning examples from DB if possible
        examples = []
        try:
            from database.session import get_sync_session
            from cognitive.learning_memory import LearningExample
            session = get_sync_session()
            rows = session.query(LearningExample).all()
            for r in rows:
                examples.append({
                    "example_type": r.example_type,
                    "trust_score": r.trust_score or 0.0,
                    "source": r.source or "",
                    "input_context": str(r.input_context or "")[:500],
                    "expected_output": str(r.expected_output or "")[:500],
                })
            session.close()
        except Exception:
            pass  # export with empty examples is fine

        package = fm.export_knowledge_package(
            source_node="local",
            examples=examples,
            min_trust=payload.min_trust,
        )
        return package
    except ImportError:
        raise HTTPException(status_code=503, detail="Federated module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class KnowledgeImportRequest(BaseModel):
    package: dict


@router.post("/knowledge/import", response_model=dict)
def import_knowledge(payload: KnowledgeImportRequest):
    """Import a knowledge package from another instance."""
    try:
        return _mgr().import_knowledge_package(payload.package)
    except ImportError:
        raise HTTPException(status_code=503, detail="Federated module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
