from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime
from sqlalchemy import text
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
        session.execute(text("SELECT 1"))
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
        session.execute(text("SELECT 1"))

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
    - Procedural memory availability and count
    - Episodic memory availability and count
    - Learning memory availability and count
    - Vector DB (Qdrant) connection status
    - Memory mesh cache status
    
    Example:
    ```bash
    curl http://localhost:8000/health/memory
    ```
    """
    from database.session import SessionLocal
    
    session = SessionLocal()
    issues: List[str] = []
    
    try:
        components: Dict[str, Any] = {}
        
        # Check procedural memory
        try:
            from cognitive.procedural_memory import ProceduralRepository, Procedure
            
            proc_repo = ProceduralRepository(session)
            total = session.query(Procedure).count()
            
            if proc_repo.embedder:
                components["procedural_memory"] = {"status": "up", "count": total}
            else:
                components["procedural_memory"] = {"status": "degraded", "count": total}
                issues.append("Procedural memory: embedder not available")
        except Exception as e:
            components["procedural_memory"] = {"status": "down", "count": 0}
            issues.append(f"Procedural memory error: {str(e)}")
        
        # Check episodic memory
        try:
            from cognitive.episodic_memory import EpisodicBuffer, Episode
            
            epi_buffer = EpisodicBuffer(session)
            total = session.query(Episode).count()
            
            if epi_buffer.embedder:
                components["episodic_memory"] = {"status": "up", "count": total}
            else:
                components["episodic_memory"] = {"status": "degraded", "count": total}
                issues.append("Episodic memory: embedder not available")
        except Exception as e:
            components["episodic_memory"] = {"status": "down", "count": 0}
            issues.append(f"Episodic memory error: {str(e)}")
        
        # Check learning memory
        try:
            from cognitive.learning_memory import LearningExample, LearningMemoryManager
            
            total = session.query(LearningExample).count()
            components["learning_memory"] = {"status": "up", "count": total}
        except Exception as e:
            components["learning_memory"] = {"status": "down", "count": 0}
            issues.append(f"Learning memory error: {str(e)}")
        
        # Check vector DB (Qdrant) connection
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            collections_response = client.get_collections()
            collection_names = [c.name for c in collections_response.collections] if collections_response else []
            components["vector_db"] = {"status": "up", "collections": collection_names}
        except Exception as e:
            components["vector_db"] = {"status": "down", "collections": []}
            issues.append(f"Vector DB (Qdrant) error: {str(e)}")
        
        # Check memory mesh cache
        try:
            from cognitive.memory_mesh_cache import get_memory_mesh_cache
            cache = get_memory_mesh_cache()
            cache_stats = cache.get_cache_stats()
            components["memory_mesh_cache"] = {"status": "up", "stats": cache_stats}
        except Exception as e:
            components["memory_mesh_cache"] = {"status": "down", "stats": {}}
            issues.append(f"Memory mesh cache error: {str(e)}")
        
        # Determine overall status
        all_statuses = [c.get("status", "unknown") for c in components.values()]
        if all(s == "up" for s in all_statuses):
            overall_status = "healthy"
        elif any(s == "down" for s in all_statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
            "issues": issues
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "issues": [f"Memory health check failed: {str(e)}"]
        }
    finally:
        session.close()


@router.get("/systems")
async def check_systems_health() -> Dict[str, Any]:
    """
    Check health of all major systems.
    
    Returns status of:
    - LLM Orchestrator
    - Diagnostic Engine
    - Self-Healing System
    - Code Analyzer
    - Genesis Service
    
    Example:
    ```bash
    curl http://localhost:8000/health/systems
    ```
    """
    from database.session import SessionLocal
    
    session = SessionLocal()
    issues: List[str] = []
    
    try:
        components: Dict[str, Any] = {}
        
        # Check LLM Orchestrator
        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            orchestrator = LLMOrchestrator(session=session)
            
            details = {
                "has_multi_llm_client": hasattr(orchestrator, 'multi_llm_client') and orchestrator.multi_llm_client is not None,
                "has_hallucination_guard": hasattr(orchestrator, 'hallucination_guard') and orchestrator.hallucination_guard is not None,
            }
            components["llm_orchestrator"] = {"status": "up", "details": details}
        except Exception as e:
            components["llm_orchestrator"] = {"status": "down", "error": str(e)}
            issues.append(f"LLM Orchestrator error: {str(e)}")
        
        # Check Diagnostic Engine
        try:
            from diagnostic_machine.diagnostic_engine import DiagnosticEngine, EngineState
            engine = DiagnosticEngine(enable_heartbeat=False)
            
            details = {
                "state": engine.state.value if hasattr(engine, 'state') else "unknown",
                "has_sensors": hasattr(engine, 'sensor_layer'),
                "has_interpreters": hasattr(engine, 'interpreter_layer'),
            }
            components["diagnostic_engine"] = {"status": "up", "details": details}
        except Exception as e:
            components["diagnostic_engine"] = {"status": "down", "error": str(e)}
            issues.append(f"Diagnostic Engine error: {str(e)}")
        
        # Check Self-Healing System
        try:
            from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel
            healing = AutonomousHealingSystem(
                session=session,
                trust_level=TrustLevel.SUGGEST_ONLY,
                enable_learning=False
            )
            
            details = {
                "trust_level": healing.trust_level.name if hasattr(healing, 'trust_level') else "unknown",
                "has_healing_system": hasattr(healing, 'healing_system'),
                "has_genesis_service": hasattr(healing, 'genesis_service'),
            }
            components["self_healing_system"] = {"status": "up", "details": details}
        except Exception as e:
            components["self_healing_system"] = {"status": "down", "error": str(e)}
            issues.append(f"Self-Healing System error: {str(e)}")
        
        # Check Code Analyzer
        try:
            from cognitive.grace_code_analyzer import GraceCodeAnalyzer
            analyzer = GraceCodeAnalyzer()
            
            details = {
                "has_pattern_matcher": hasattr(analyzer, 'pattern_matcher'),
                "has_rules": hasattr(analyzer, 'rules') and len(getattr(analyzer, 'rules', [])) > 0,
            }
            components["code_analyzer"] = {"status": "up", "details": details}
        except Exception as e:
            components["code_analyzer"] = {"status": "down", "error": str(e)}
            issues.append(f"Code Analyzer error: {str(e)}")
        
        # Check Genesis Service
        try:
            from genesis.genesis_key_service import GenesisKeyService
            genesis = GenesisKeyService(session=session)
            
            details = {
                "has_git_service": genesis.git_service is not None,
                "repo_path": str(genesis.repo_path) if genesis.repo_path else None,
            }
            components["genesis_service"] = {"status": "up", "details": details}
        except Exception as e:
            components["genesis_service"] = {"status": "down", "error": str(e)}
            issues.append(f"Genesis Service error: {str(e)}")
        
        # Determine overall status
        all_statuses = [c.get("status", "unknown") for c in components.values()]
        if all(s == "up" for s in all_statuses):
            overall_status = "healthy"
        elif any(s == "down" for s in all_statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
            "issues": issues
        }
    except Exception as e:
        logger.error(f"Systems health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "issues": [f"Systems health check failed: {str(e)}"]
        }
    finally:
        session.close()
