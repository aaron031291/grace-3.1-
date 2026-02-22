"""
Self-Mirror API - Grace's Telemetry Dashboard

Exposes the Self-Mirror's unified telemetry data:
- [T,M,P] vectors from all components
- Statistical profiles (mean, mode, variance)
- Pillar triggers (what's been activated and why)
- Bi-directional challenges between components
- RFI (Request for Intelligence) management
- Real-time system pulse

Classes:
- `TelemetryVectorInput`
- `RFICreateRequest`
"""

from fastapi import APIRouter
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mirror", tags=["Self-Mirror Telemetry"])


class TelemetryVectorInput(BaseModel):
    """Input model for reporting a [T,M,P] vector."""
    T: float = Field(..., description="Time in milliseconds")
    M: float = Field(..., description="Mass in bytes")
    P: float = Field(..., description="Pressure 0.0-1.0")
    component: str = Field(..., description="Component name")
    task_domain: str = Field("general", description="Task domain")


class RFICreateRequest(BaseModel):
    """Request to create a Request for Intelligence."""
    void_description: str = Field(..., description="What knowledge is missing")
    required_knowledge: str = Field(..., description="What specific knowledge is needed")
    source_component: str = Field(..., description="Which component identified the void")


@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """
    Get the unified telemetry dashboard.

    Returns statistical profiles, component pulse, triggers, and challenges.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return mirror.get_dashboard()


@router.get("/pulse")
async def get_system_pulse() -> Dict[str, Any]:
    """
    Get the current [T,M,P] vector for every component.

    This is the real-time "heartbeat" of every component in the system.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    pulse = mirror.broadcast_system_pulse()
    return {
        "components": {k: v.to_dict() for k, v in pulse.items()},
        "component_count": len(pulse),
    }


@router.get("/stats")
async def get_mirror_stats() -> Dict[str, Any]:
    """Get Self-Mirror operational statistics."""
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return mirror.get_stats()


@router.get("/profiles")
async def get_profiles() -> Dict[str, Any]:
    """
    Get statistical profiles for all task domains.

    Shows mean, mode, variance, and observation counts.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()

    profiles = {}
    for domain, profile in mirror.profiles.items():
        profiles[domain] = {
            "domain": domain,
            "mean_time": round(profile.mean_time, 2),
            "mode_time": round(profile.mode_time, 2),
            "std_time": round(profile.std_time, 2),
            "variance_time": round(profile.variance_time, 2),
            "mean_mass": round(profile.mean_mass, 2),
            "mean_pressure": round(profile.mean_pressure, 3),
            "total_observations": profile.total_observations,
        }

    return {"profiles": profiles, "total_domains": len(profiles)}


@router.get("/triggers")
async def get_triggers(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent pillar triggers.

    Shows which pillars were activated and why.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()

    triggers = [
        {
            "pillar": t.pillar.value,
            "reason": t.reason,
            "severity": t.severity,
            "telemetry": t.telemetry.to_dict(),
            "stats": t.stats,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in list(mirror.pillar_triggers)[-limit:]
    ]

    return {
        "triggers": triggers,
        "total_triggers": mirror._stats["total_triggers_fired"],
        "by_pillar": mirror._stats["pillar_trigger_counts"],
    }


@router.get("/challenges")
async def get_challenges(limit: int = 50) -> Dict[str, Any]:
    """
    Get bi-directional challenges between components.

    Shows where components have flagged performance deviations in each other.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()

    challenges = [
        {
            "challenger": c.challenger,
            "challenged": c.challenged,
            "metric": c.metric,
            "deviation_factor": round(c.deviation_factor, 1),
            "message": c.message,
            "resolved": c.resolved,
            "timestamp": c.timestamp.isoformat(),
        }
        for c in list(mirror.challenges)[-limit:]
    ]

    return {
        "challenges": challenges,
        "total_challenges": mirror._stats["total_challenges_issued"],
    }


@router.post("/report")
async def report_telemetry(vector: TelemetryVectorInput) -> Dict[str, Any]:
    """
    Report a [T,M,P] telemetry vector from a component.

    Any component can call this to report its state.
    The mirror will record it, check triggers, and issue challenges.
    """
    from cognitive.self_mirror import get_self_mirror, TelemetryVector
    mirror = get_self_mirror()

    tv = TelemetryVector(
        T=vector.T,
        M=vector.M,
        P=vector.P,
        component=vector.component,
        task_domain=vector.task_domain,
    )
    mirror.receive_vector(tv)

    return {
        "received": True,
        "vector": tv.to_dict(),
        "total_vectors": mirror._stats["total_vectors_received"],
    }


@router.post("/rfi")
async def create_rfi(request: RFICreateRequest) -> Dict[str, Any]:
    """
    Create a Request for Intelligence (RFI).

    Used when Grace identifies a knowledge void that needs external resolution.
    """
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()

    rfi = mirror.create_rfi(
        void=request.void_description,
        required=request.required_knowledge,
        source=request.source_component,
    )

    return {
        "rfi_id": rfi.rfi_id,
        "status": rfi.status,
        "void": rfi.void_description,
    }


@router.get("/rfi/list")
async def list_rfis() -> Dict[str, Any]:
    """List all RFIs and their status."""
    from cognitive.self_mirror import get_self_mirror
    mirror = get_self_mirror()

    rfis = [
        {
            "rfi_id": r.rfi_id,
            "void": r.void_description,
            "required": r.required_knowledge,
            "source": r.source_component,
            "status": r.status,
            "baked_to": r.baked_to_pillars,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in mirror.resolution_engine.rfis
    ]

    return {
        "rfis": rfis,
        "stats": mirror.resolution_engine.get_stats(),
    }
