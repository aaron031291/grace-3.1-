"""
Unified Health Controller — merges component health, probe agent,
trigger scanning, and dormancy detection into ONE monitoring surface.

Replaces:
  - api/component_health_api.py (health map, timeline, problems, orphans, baselines, correlation)
  - api/probe_agent_api.py (endpoint probing, model probing)
  - api/runtime_triggers_api.py (CPU/RAM/service/code/network triggers)

All capabilities preserved. One loop. One entry point per concern.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitor", tags=["Unified Health Monitor"])


# Re-export ALL existing functionality through the new router.
# This is Phase 1 — preserve every capability, just unify the entry point.
# Phase 2 will merge the internals.


# ── Component Health (from component_health_api) ─────────────────

@router.get("/health-map")
async def health_map(window_minutes: int = Query(60, ge=5, le=1440)):
    from api.component_health_api import health_map as _impl
    return await _impl(window_minutes)


@router.get("/timeline/{component_id}")
async def timeline(component_id: str, window_minutes: int = Query(60), limit: int = Query(200)):
    from api.component_health_api import component_timeline as _impl
    return await _impl(component_id, window_minutes, limit)


@router.get("/problems")
async def problems():
    from api.component_health_api import problems_list as _impl
    return await _impl()


@router.get("/dependencies/{component_id}")
async def dependencies(component_id: str):
    from api.component_health_api import dependency_graph as _impl
    return await _impl(component_id)


@router.get("/correlate/{component_id}")
async def correlate(component_id: str):
    from api.component_health_api import correlate_failure as _impl
    return await _impl(component_id)


@router.get("/orphans")
async def orphans():
    from api.component_health_api import detect_orphan_services as _impl
    return await _impl()


@router.get("/baselines")
async def baselines():
    from api.component_health_api import learned_baselines as _impl
    return await _impl()


@router.get("/mirror-feed")
async def mirror_feed():
    from api.component_health_api import mirror_feed as _impl
    return await _impl()


@router.get("/approvals")
async def approvals():
    from api.component_health_api import get_approvals as _impl
    return await _impl()


@router.post("/approvals/{index}/approve")
async def approve(index: int):
    from api.component_health_api import approve_remediation as _impl
    return await _impl(index)


@router.post("/approvals/{index}/reject")
async def reject(index: int):
    from api.component_health_api import reject_remediation as _impl
    return await _impl(index)


@router.get("/registry")
async def registry():
    from api.component_health_api import get_component_registry as _impl
    return await _impl()


@router.get("/rules")
async def rules():
    from api.component_health_api import get_remediation_rules as _impl
    return await _impl()


# ── Probe Agent (from probe_agent_api) ───────────────────────────

@router.post("/probe/sweep")
async def probe_sweep():
    from api.probe_agent_api import probe_sweep as _impl
    return await _impl()


@router.post("/probe/models")
async def probe_models():
    from api.probe_agent_api import probe_models as _impl
    return await _impl()


@router.post("/probe/sweep-and-heal")
async def probe_and_heal():
    from api.probe_agent_api import probe_and_heal as _impl
    return await _impl()


@router.get("/probe/results")
async def probe_results():
    from api.probe_agent_api import get_probe_results as _impl
    return await _impl()


@router.post("/probe/endpoint")
async def probe_endpoint(path: str):
    from api.probe_agent_api import probe_single as _impl
    return await _impl(path)


# ── Trigger Scanning (from runtime_triggers_api) ─────────────────

@router.get("/triggers/scan")
async def trigger_scan():
    from api.runtime_triggers_api import scan_triggers as _impl
    return await _impl()


@router.post("/triggers/scan-and-heal")
async def trigger_scan_heal():
    from api.runtime_triggers_api import scan_and_heal as _impl
    return await _impl()


@router.get("/triggers/log")
async def trigger_log(limit: int = 50):
    from api.runtime_triggers_api import get_trigger_log as _impl
    return await _impl(limit)


@router.post("/triggers/stress-heal")
async def stress_heal():
    from api.runtime_triggers_api import stress_then_heal as _impl
    return await _impl()
