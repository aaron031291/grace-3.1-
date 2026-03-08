"""
Restricted Admin API — safe live control of the running system.

Endpoints: registry, state, reload-config, trigger-diagnostics.
Requires ADMIN_TOKEN header or query param (env ADMIN_TOKEN).
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _check_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    token: Optional[str] = Query(None),
) -> None:
    """Require valid admin token."""
    required = os.environ.get("ADMIN_TOKEN", "").strip()
    if not required:
        raise HTTPException(status_code=503, detail="Admin API disabled (ADMIN_TOKEN not set)")
    provided = (x_admin_token or token or "").strip()
    if provided != required:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/registry", summary="List brains, components, models")
async def get_registry(
    _: None = Depends(_check_admin_token),
):
    """List all registered brains, components, and models."""
    try:
        from core.execution_registry import get_registry, init_registry
        try:
            r = get_registry()
        except Exception:
            r = init_registry()
        return {"ok": True, "data": r.get_registry()}
    except Exception as e:
        logger.warning("Admin registry: %s", e)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/state", summary="Basic system state")
async def get_state(
    _: None = Depends(_check_admin_token),
):
    """KPI summary, component health, basic state."""
    try:
        out = {}
        # KPI summary
        try:
            from core.governance_engine import get_kpi_dashboard
            out["kpi_dashboard"] = get_kpi_dashboard()
        except Exception:
            out["kpi_dashboard"] = None
        # Component trust
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            if tracker:
                out["system_trust"] = tracker.get_system_trust_score()
                out["components"] = {
                    name: tracker.get_component_trust_score(name)
                    for name in ["brain_chat", "brain_ai", "rag", "ingestion", "learning"]
                }
        except Exception:
            out["system_trust"] = None
            out["components"] = None
        return {"ok": True, "data": out}
    except Exception as e:
        logger.warning("Admin state: %s", e)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/reload-config", summary="Reload config (hot reload)")
async def reload_config(
    _: None = Depends(_check_admin_token),
):
    """Trigger config reload (if supported). No module reimport."""
    try:
        # Settings reload (common pattern)
        try:
            import importlib
            import settings
            importlib.reload(settings)
            return {"ok": True, "message": "Config reloaded"}
        except ImportError:
            return {"ok": True, "message": "No settings module to reload"}
    except Exception as e:
        logger.warning("Admin reload-config: %s", e)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/trigger-diagnostics", summary="Trigger diagnostic run")
async def trigger_diagnostics(
    _: None = Depends(_check_admin_token),
):
    """Run diagnostics in background. Returns immediately."""
    try:
        from core.background_tasks import submit_background

        def _run() -> None:
            try:
                from core.governance_engine import get_kpi_dashboard
                get_kpi_dashboard()
            except Exception as e:
                logger.warning("Diagnostics run: %s", e)

        submit_background(_run)
        return {"ok": True, "message": "Diagnostics triggered in background"}
    except Exception as e:
        logger.warning("Admin trigger-diagnostics: %s", e)
        raise HTTPException(status_code=500, detail=str(e)[:200])
