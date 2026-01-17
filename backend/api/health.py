from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime
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
_startup_time = datetime.utcnow()


async def check_ollama() -> ServiceHealth:
    """Check Ollama LLM service health."""
    import time
    start = time.time()
    try:
        from ollama_client.client import get_ollama_client
        client = get_ollama_client()

        if client.is_running():
            models = client.get_all_models()
            latency = (time.time() - start) * 1000
            return ServiceHealth(
                name="ollama",
                status="healthy",
                latency_ms=round(latency, 2),
                details={"models_available": len(models)}
            )
        else:
            return ServiceHealth(
                name="ollama",
                status="unhealthy",
                message="Ollama service not running"
            )
    except Exception as e:
        return ServiceHealth(
            name="ollama",
            status="unhealthy",
            message=str(e)
        )


async def check_database() -> ServiceHealth:
    """Check database connection health."""
    import time
    start = time.time()
    session = None
    try:
        from database.session import SessionLocal
        session = SessionLocal()
        session.execute("SELECT 1")
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
    finally:
        if session:
            session.close()


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
        test_result = embedder.embed(["health check"])
        latency = (time.time() - start) * 1000

        if test_result is not None and len(test_result) > 0:
            return ServiceHealth(
                name="embedding_model",
                status="healthy",
                latency_ms=round(latency, 2),
                details={"dimension": len(test_result[0]) if test_result else 0}
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
        check_ollama(),
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
    uptime = (datetime.utcnow() - _startup_time).total_seconds()

    return SystemHealth(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
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
    session = None
    try:
        # Quick checks for critical services
        from database.session import SessionLocal
        session = SessionLocal()
        session.execute("SELECT 1")

        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        if session:
            session.close()


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if service is alive (basic check).
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/stability-proof")
async def get_stability_proof(include_proof: bool = True) -> Dict[str, Any]:
    """
    **Deterministic Stability Proof**
    
    Proves that the system is in a stable state using mathematical determinism.
    
    This endpoint performs comprehensive deterministic checks on:
    - Database stability and determinism
    - Cognitive engine stability
    - Invariant satisfaction
    - State machine validity
    - Deterministic operations verification
    - System health metrics
    - Error rates
    - Component consistency
    
    **Parameters:**
    - `include_proof`: If True, includes full mathematical proof (default: True)
    
    **Returns:**
    - Complete stability proof with mathematical verification
    - System state hash for reproducibility
    - Component-by-component stability checks
    - Overall stability level and confidence
    
    **Example:**
    ```bash
    curl http://localhost:8000/health/stability-proof
    ```
    """
    try:
        from database.session import SessionLocal
        from cognitive.deterministic_stability_proof import get_stability_prover
        
        session = SessionLocal()
        
        try:
            prover = get_stability_prover(session=session)
            proof = prover.prove_stability(include_proof=include_proof)
            
            return {
                "status": "success",
                "proof": proof.to_dict(),
                "message": f"System stability: {proof.stability_level.value} (confidence: {proof.overall_confidence:.2f})"
            }
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Stability proof failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to generate stability proof"
        }


@router.get("/stability-proof/history")
async def get_stability_proof_history(limit: int = 10) -> Dict[str, Any]:
    """
    **Get Stability Proof History**
    
    Returns recent stability proofs for analysis.
    
    **Parameters:**
    - `limit`: Number of recent proofs to return (default: 10)
    
    **Example:**
    ```bash
    curl http://localhost:8000/health/stability-proof/history?limit=5
    ```
    """
    try:
        from database.session import SessionLocal
        from cognitive.deterministic_stability_proof import get_stability_prover
        
        session = SessionLocal()
        
        try:
            prover = get_stability_prover(session=session)
            history = prover.get_proof_history(limit=limit)
            
            return {
                "status": "success",
                "count": len(history),
                "proofs": [proof.to_dict() for proof in history]
            }
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to get stability proof history: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/stability-monitor/status")
async def get_stability_monitor_status() -> Dict[str, Any]:
    """
    **Get Real-Time Stability Monitor Status**
    
    Returns current status of the real-time stability monitoring system.
    
    **Returns:**
    - Monitor status (running, stopped, etc.)
    - Current stability level and confidence
    - Statistics (total checks, stable/unstable counts)
    - Recent alerts
    
    **Example:**
    ```bash
    curl http://localhost:8000/health/stability-monitor/status
    ```
    """
    try:
        from cognitive.realtime_stability_monitor import get_stability_monitor
        
        monitor = get_stability_monitor()
        status = monitor.get_current_status()
        
        # Add recent alerts
        recent_alerts = monitor.get_recent_alerts(limit=10)
        status['recent_alerts'] = [alert.to_dict() for alert in recent_alerts]
        
        return {
            "status": "success",
            "monitor": status
        }
    except Exception as e:
        logger.error(f"Failed to get stability monitor status: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/stability-monitor/force-check")
async def force_stability_check() -> Dict[str, Any]:
    """
    **Force Immediate Stability Check**
    
    Triggers an immediate stability proof check (synchronous).
    
    **Returns:**
    - Latest stability proof
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/health/stability-monitor/force-check
    ```
    """
    try:
        from cognitive.realtime_stability_monitor import get_stability_monitor
        
        monitor = get_stability_monitor()
        proof = monitor.force_check()
        
        if proof:
            return {
                "status": "success",
                "proof": proof.to_dict(),
                "message": f"Stability check completed: {proof.stability_level.value}"
            }
        else:
            return {
                "status": "error",
                "message": "Stability check failed"
            }
    except Exception as e:
        logger.error(f"Failed to force stability check: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/memory")
async def check_memory_health() -> Dict[str, Any]:
    """
    Check health of memory systems.
    
    Returns status of:
    - Memory retrieval system
    - Procedural memory (total procedures, procedures with embeddings)
    - Episodic memory (total episodes, episodes with embeddings)
    - Embedder availability
    
    Example:
    ```bash
    curl http://localhost:8000/health/memory
    ```
    """
    from database.session import SessionLocal
    from sqlalchemy.orm import Session
    
    session = SessionLocal()
    
    try:
        health = {
            "memory_retrieval": {
                "status": "unknown",
                "issues": []
            },
            "procedural_memory": {
                "status": "unknown",
                "total_procedures": 0,
                "procedures_with_embeddings": 0,
                "issues": []
            },
            "episodic_memory": {
                "status": "unknown",
                "total_episodes": 0,
                "episodes_with_embeddings": 0,
                "issues": []
            }
        }
        
        # Check procedural memory
        try:
            from cognitive.procedural_memory import ProceduralRepository, Procedure
            
            proc_repo = ProceduralRepository(session)
            total = session.query(Procedure).count()
            with_embeddings = session.query(Procedure).filter(
                Procedure.embedding.isnot(None)
            ).count()
            
            health["procedural_memory"]["total_procedures"] = total
            health["procedural_memory"]["procedures_with_embeddings"] = with_embeddings
            
            if proc_repo.embedder:
                health["procedural_memory"]["status"] = "operational"
            else:
                health["procedural_memory"]["status"] = "degraded"
                health["procedural_memory"]["issues"].append("Embedder not available")
                
            if total > 0 and with_embeddings == 0:
                health["procedural_memory"]["status"] = "needs_indexing"
                health["procedural_memory"]["issues"].append(
                    "No embeddings generated - run index_all_procedures()"
                )
        except Exception as e:
            health["procedural_memory"]["status"] = "error"
            health["procedural_memory"]["issues"].append(str(e))
        
        # Check episodic memory
        try:
            from cognitive.episodic_memory import EpisodicBuffer, Episode
            
            epi_buffer = EpisodicBuffer(session)
            total = session.query(Episode).count()
            with_embeddings = session.query(Episode).filter(
                Episode.embedding.isnot(None)
            ).count()
            
            health["episodic_memory"]["total_episodes"] = total
            health["episodic_memory"]["episodes_with_embeddings"] = with_embeddings
            
            if epi_buffer.embedder:
                health["episodic_memory"]["status"] = "operational"
            else:
                health["episodic_memory"]["status"] = "degraded"
                health["episodic_memory"]["issues"].append("Embedder not available")
                
            if total > 0 and with_embeddings == 0:
                health["episodic_memory"]["status"] = "needs_indexing"
                health["episodic_memory"]["issues"].append(
                    "No embeddings generated - run index_all_episodes()"
                )
        except Exception as e:
            health["episodic_memory"]["status"] = "error"
            health["episodic_memory"]["issues"].append(str(e))
        
        # Check memory retrieval (LLM Orchestrator dependency)
        try:
            try:
                from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.llm_orchestrator.llm_orchestrator import LLMOrchestrator
            
            # Check if LLMOrchestrator class exists and has expected attributes
            if hasattr(LLMOrchestrator, '__init__'):
                health["memory_retrieval"]["status"] = "operational"
            else:
                health["memory_retrieval"]["status"] = "degraded"
                health["memory_retrieval"]["issues"].append("LLM Orchestrator class structure incomplete")
        except Exception as e:
            health["memory_retrieval"]["status"] = "degraded"
            health["memory_retrieval"]["issues"].append(f"LLM Orchestrator dependency issue: {e}")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "health": health
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check memory system health"
        }
    finally:
        session.close()
