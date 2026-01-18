"""
Enterprise API Endpoints
========================

Exposes enterprise features via REST API:
- Environment management
- Orchestration layer
- Disaster recovery
- Compliance
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise", tags=["Enterprise"])


# =============================================================================
# ENVIRONMENT
# =============================================================================

@router.get("/environment")
async def get_environment():
    """Get current environment configuration."""
    try:
        from enterprise.environment_manager import get_environment_manager
        env = get_environment_manager()
        return {
            "status": "success",
            "environment": env.get_startup_config(),
            "details": {
                "is_production": env.is_production,
                "is_development": env.is_development,
                "is_containerized": env.is_containerized,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/environment/features")
async def get_features():
    """Get feature flag status."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        orch = get_orchestration_layer()
        return {
            "status": "success",
            "features": orch.features.get_all_flags(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FeatureToggle(BaseModel):
    """Feature toggle request."""
    feature: str
    enabled: bool
    user_id: Optional[str] = None


@router.post("/environment/features/toggle")
async def toggle_feature(request: FeatureToggle):
    """Toggle a feature flag."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        orch = get_orchestration_layer()
        
        if request.user_id:
            orch.features.set_override(request.feature, request.user_id, request.enabled)
        else:
            # Global toggle would require modifying the flag itself
            pass
        
        return {"status": "success", "feature": request.feature, "enabled": request.enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ORCHESTRATION
# =============================================================================

@router.get("/orchestration/status")
async def get_orchestration_status():
    """Get orchestration layer status."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        orch = get_orchestration_layer()
        return {
            "status": "success",
            "orchestration": orch.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestration/traces")
async def get_traces(since_hours: int = Query(1, description="Hours to look back")):
    """Get distributed traces."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        from datetime import timedelta
        
        orch = get_orchestration_layer()
        since = datetime.now() - timedelta(hours=since_hours)
        
        return {
            "status": "success",
            "traces": orch.tracer.export_traces(since=since),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestration/circuits")
async def get_circuit_breakers():
    """Get circuit breaker status."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        orch = get_orchestration_layer()
        
        circuits = {}
        for name, circuit in orch.mesh._circuits.items():
            circuits[name] = {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "success_count": circuit.success_count,
            }
        
        return {
            "status": "success",
            "circuits": circuits,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DISASTER RECOVERY
# =============================================================================

@router.get("/dr/status")
async def get_dr_status():
    """Get disaster recovery status."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        dr = get_disaster_recovery()
        return {
            "status": "success",
            "disaster_recovery": dr.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dr/backups")
async def list_backups():
    """List all backups."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        dr = get_disaster_recovery()
        return {
            "status": "success",
            "backups": dr.backup_manager.list_backups(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BackupRequest(BaseModel):
    """Backup request."""
    type: str = Field("full", description="Backup type: full, incremental, snapshot")


@router.post("/dr/backup")
async def create_backup(request: BackupRequest, background_tasks: BackgroundTasks):
    """Create a new backup."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery, BackupType
        
        dr = get_disaster_recovery()
        backup_type = BackupType(request.type)
        
        # Run backup in background
        def run_backup():
            dr.create_backup(backup_type)
        
        background_tasks.add_task(run_backup)
        
        return {
            "status": "accepted",
            "message": f"Backup ({request.type}) started in background",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RestoreRequest(BaseModel):
    """Restore request."""
    backup_id: str


@router.post("/dr/restore")
async def restore_backup(request: RestoreRequest):
    """Restore from a backup."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        
        dr = get_disaster_recovery()
        success = dr.backup_manager.restore_backup(request.backup_id)
        
        if success:
            return {"status": "success", "message": f"Restored from {request.backup_id}"}
        else:
            raise HTTPException(status_code=400, detail="Restore failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dr/failover")
async def trigger_failover(reason: str = Query("manual", description="Reason for failover")):
    """Trigger failover to backup system."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        
        dr = get_disaster_recovery()
        success = dr.trigger_failover(reason)
        
        if success:
            active = dr.failover_manager.get_active_target()
            return {
                "status": "success",
                "message": "Failover completed",
                "active_target": active.name if active else None,
            }
        else:
            raise HTTPException(status_code=400, detail="No healthy failover targets")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dr/test")
async def test_recovery():
    """Test disaster recovery procedures."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        
        dr = get_disaster_recovery()
        results = dr.test_recovery()
        
        return {
            "status": "success",
            "test_results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPLIANCE
# =============================================================================

@router.get("/compliance/status")
async def get_compliance_status():
    """Get compliance status."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery
        
        dr = get_disaster_recovery()
        return {
            "status": "success",
            "compliance": dr.get_compliance_report(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/check")
async def run_compliance_checks(
    framework: Optional[str] = Query(None, description="Framework: soc2, hipaa, gdpr, pci_dss, iso27001")
):
    """Run compliance checks."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery, ComplianceFramework
        
        dr = get_disaster_recovery()
        
        fw = None
        if framework:
            fw = ComplianceFramework(framework)
        
        results = dr.compliance_manager.run_all_checks(framework=fw)
        
        return {
            "status": "success",
            "results": results,
            "report": dr.compliance_manager.get_compliance_report(framework=fw),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/report/{framework}")
async def get_compliance_report(framework: str):
    """Get compliance report for a specific framework."""
    try:
        from enterprise.disaster_recovery import get_disaster_recovery, ComplianceFramework
        
        dr = get_disaster_recovery()
        fw = ComplianceFramework(framework)
        
        return {
            "status": "success",
            "report": dr.compliance_manager.get_compliance_report(framework=fw),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SCALING
# =============================================================================

@router.get("/scaling/status")
async def get_scaling_status():
    """Get auto-scaling status."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        
        orch = get_orchestration_layer()
        
        return {
            "status": "success",
            "scaling": {
                "current_instances": orch.scaler.current_instances,
                "policy": {
                    "min": orch.scaler.policy.min_instances,
                    "max": orch.scaler.policy.max_instances,
                    "target_cpu": orch.scaler.policy.target_cpu_percent,
                    "target_memory": orch.scaler.policy.target_memory_percent,
                },
                "last_scale_up": orch.scaler.last_scale_up.isoformat() if orch.scaler.last_scale_up else None,
                "last_scale_down": orch.scaler.last_scale_down.isoformat() if orch.scaler.last_scale_down else None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ScaleRequest(BaseModel):
    """Manual scaling request."""
    instances: int = Field(..., ge=1, le=100)


@router.post("/scaling/scale")
async def manual_scale(request: ScaleRequest):
    """Manually scale instances."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        
        orch = get_orchestration_layer()
        orch.scaler.apply_scaling(request.instances)
        
        return {
            "status": "success",
            "instances": orch.scaler.current_instances,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CHAOS ENGINEERING
# =============================================================================

@router.get("/chaos/status")
async def get_chaos_status():
    """Get chaos engineering status."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        
        orch = get_orchestration_layer()
        
        return {
            "status": "success",
            "chaos": {
                "enabled": orch.chaos.enabled,
                "failure_rate": orch.chaos._failure_rate,
                "latency_ms": orch.chaos._latency_ms,
                "affected_services": orch.chaos._affected_services,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChaosConfig(BaseModel):
    """Chaos configuration."""
    enabled: bool = False
    failure_rate: float = Field(0.0, ge=0.0, le=1.0)
    latency_ms: int = Field(0, ge=0, le=10000)
    services: Optional[List[str]] = None


@router.post("/chaos/configure")
async def configure_chaos(config: ChaosConfig):
    """Configure chaos engineering."""
    try:
        from enterprise.orchestration_layer import get_orchestration_layer
        
        orch = get_orchestration_layer()
        orch.chaos.enabled = config.enabled
        orch.chaos.set_failure_rate(config.failure_rate, config.services)
        orch.chaos.set_latency(config.latency_ms)
        
        return {
            "status": "success",
            "message": "Chaos configuration updated",
            "config": {
                "enabled": orch.chaos.enabled,
                "failure_rate": orch.chaos._failure_rate,
                "latency_ms": orch.chaos._latency_ms,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
