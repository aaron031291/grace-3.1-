"""
Comprehensive Health Check API
==============================
Health checks for all GRACE services and components.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class ServiceHealth(BaseModel):
    """Health status for a single service."""
    name: str
    status: str  # "healthy", "unhealthy", "degraded", "unknown"
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict] = None


class SystemHealth(BaseModel):
    """Overall system health response."""
    status: str
    timestamp: str
    version: str = "3.1"
    uptime_seconds: Optional[float] = None
    services: List[ServiceHealth]
    summary: Dict[str, int]


# Track startup time
_startup_time = datetime.now(timezone.utc)


async def check_llm() -> ServiceHealth:
    """Check LLM service health."""
    import time
    start = time.time()
    try:
        from llm_orchestrator.factory import get_llm_client
        from settings import settings
        client = get_llm_client()
        provider = (settings.LLM_PROVIDER if settings else "llm").lower()

        if client.is_running():
            models = client.get_all_models()
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name=provider,
                status="healthy",
                latency_ms=round(latency, 2),
                details={"models_available": len(models)}
            )
        else:
            return ServiceHealth(
                name=provider,
                status="unhealthy",
                message=f"{provider.upper()} service not responding"
            )
    except Exception as e:
        from settings import settings
        provider = (settings.LLM_PROVIDER if settings else "llm").lower()
        return ServiceHealth(
            name=provider,
            status="unhealthy",
            message=str(e)
        )


async def check_database() -> ServiceHealth:
    """Check database connection health."""
    import time
    start = time.time()
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        latency = (time.time() - start) * 1000
        return ServiceHealth(
            name="database",
            status="healthy",
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        return ServiceHealth(
            name="database",
            status="unhealthy",
            message=str(e)
        )


async def check_qdrant() -> ServiceHealth:
    """Check Qdrant vector database health."""
    import time
    start = time.time()
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()

        # Try to get collections
        collections = client.get_collections()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            name="qdrant",
            status="healthy",
            latency_ms=round(latency, 2),
            details={"collections": len(collections.collections) if collections else 0}
        )
    except Exception as e:
        return ServiceHealth(
            name="qdrant",
            status="unhealthy",
            message=str(e)
        )


async def check_embedding_model() -> ServiceHealth:
    """Check embedding model health."""
    import time
    start = time.time()
    try:
        from embedding import get_embedder
        embedder = get_embedder()

        # Quick test embedding
        test_result = embedder.embed_text(["health check"])
        latency = (time.time() - start) * 1000

        # Check if embedding was successful (test_result should be a numpy array)
        if test_result is not None and hasattr(test_result, 'shape') and test_result.shape[0] > 0:
            dimension = test_result.shape[0] if len(test_result.shape) == 1 else test_result.shape[1]
            return ServiceHealth(
                name="embedding_model",
                status="healthy",
                latency_ms=round(latency, 2),
                details={"dimension": int(dimension)}
            )
        else:
            return ServiceHealth(
                name="embedding_model",
                status="degraded",
                message="Embedding returned empty result"
            )
    except Exception as e:
        return ServiceHealth(
            name="embedding_model",
            status="unhealthy",
            message=str(e)
        )


async def check_memory() -> ServiceHealth:
    """Check system memory usage."""
    try:
        import psutil
        memory = psutil.virtual_memory()

        status = "healthy"
        if memory.percent > 90:
            status = "unhealthy"
        elif memory.percent > 80:
            status = "degraded"

        return ServiceHealth(
            name="memory",
            status=status,
            details={
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            }
        )
    except Exception as e:
        return ServiceHealth(
            name="memory",
            status="unknown",
            message=str(e)
        )


async def check_disk() -> ServiceHealth:
    """Check disk space."""
    try:
        import psutil
        disk = psutil.disk_usage('/')

        status = "healthy"
        if disk.percent > 95:
            status = "unhealthy"
        elif disk.percent > 85:
            status = "degraded"

        return ServiceHealth(
            name="disk",
            status=status,
            details={
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
        )
    except Exception as e:
        return ServiceHealth(
            name="disk",
            status="unknown",
            message=str(e)
        )


@router.get("", response_model=SystemHealth)
@router.get("/", response_model=SystemHealth)
async def comprehensive_health_check():
    """
    Comprehensive health check for all GRACE services.

    Returns status of:
    - Ollama LLM service
    - Database connection
    - Qdrant vector database
    - Embedding model
    - System memory
    - Disk space
    """
    # Run all health checks concurrently
    checks = await asyncio.gather(
        check_llm(),
        check_database(),
        check_qdrant(),
        check_embedding_model(),
        check_memory(),
        check_disk(),
        return_exceptions=True
    )

    # Process results
    services = []
    for check in checks:
        if isinstance(check, Exception):
            services.append(ServiceHealth(
                name="unknown",
                status="error",
                message=str(check)
            ))
        else:
            services.append(check)

    # Calculate summary
    summary = {
        "healthy": sum(1 for s in services if s.status == "healthy"),
        "degraded": sum(1 for s in services if s.status == "degraded"),
        "unhealthy": sum(1 for s in services if s.status == "unhealthy"),
        "unknown": sum(1 for s in services if s.status in ["unknown", "error"])
    }

    # Overall status
    if summary["unhealthy"] > 0:
        overall_status = "unhealthy"
    elif summary["degraded"] > 0:
        overall_status = "degraded"
    elif summary["unknown"] > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Calculate uptime
    uptime = (datetime.now(timezone.utc) - _startup_time).total_seconds()

    return SystemHealth(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
        services=services,
        summary=summary
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns 200 if service is ready to accept traffic.
    """
    try:
        # Quick checks for critical services
        from database.session import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()

        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if service is alive (basic check).
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
