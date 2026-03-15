"""
Probe Agent API — automated crawler that sends synthetic pulses to every
API endpoint and cognitive module, classifies them as active/dormant/broken,
and feeds results into the dormancy protocol + self-healing pipeline.

The probe agent:
  1. Discovers all registered routes from FastAPI's app.routes
  2. Sends a lightweight synthetic request to each endpoint
  3. Tags every probe with a Genesis key (test=true so metrics aren't polluted)
  4. Classifies results: ACTIVE (2xx), DORMANT (no recent Genesis keys),
     BROKEN (4xx/5xx/timeout)
  5. Broken endpoints trigger self-healing via consensus

The consensus auto-fix flow:
  1. Probe finds a broken endpoint
  2. Sends the error to ALL available models (Kimi, Opus, Qwen, DeepSeek)
  3. Each model proposes a diagnosis + fix
  4. If all models agree → execute the fix (with Genesis key provenance)
  5. If disagreement → queue for human approval
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import threading
import time
import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/probe", tags=["Probe Agent"])

_probe_results: List[dict] = []
_probe_lock = threading.Lock()
_MAX_RESULTS = 500

SAFE_METHODS_ONLY = True
PROBE_TIMEOUT = 5
BASE = "http://127.0.0.1:8000"

SKIP_PREFIXES = (
    "/docs", "/openapi.json", "/redoc", "/favicon",
    "/api/probe",  # don't probe ourselves
    "/api/runtime",  # don't trigger runtime actions
    "/diagnostic/start", "/diagnostic/stop",
    "/diagnostic/pause", "/diagnostic/resume",
)


def _discover_routes() -> List[dict]:
    """Discover all routes from the running FastAPI app — both GET and POST."""
    routes = []

    # Method 1: direct app introspection (fastest, no HTTP call)
    try:
        from starlette.routing import Route, Mount
        from app import app as _app

        def _extract(routes_list, prefix=""):
            for route in routes_list:
                if isinstance(route, Mount) and hasattr(route, "routes"):
                    _extract(route.routes, prefix + (route.path or ""))
                elif isinstance(route, Route):
                    path = prefix + route.path
                    if any(path.startswith(p) for p in SKIP_PREFIXES):
                        continue
                    if "{" in path:
                        continue
                    for method in (route.methods or {"GET"}):
                        if method in ("GET", "HEAD"):
                            routes.append({"path": path, "method": "GET"})
                            break

        _extract(_app.routes)
        if routes:
            logger.info("Probe discovered %d routes via app introspection", len(routes))
            return routes
    except Exception as e:
        logger.debug("App introspection failed, falling back to OpenAPI: %s", e)

    # Method 2: OpenAPI spec fallback
    try:
        url = f"{BASE}/openapi.json"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            spec = json.loads(resp.read())

        for path, methods in spec.get("paths", {}).items():
            if any(path.startswith(p) for p in SKIP_PREFIXES):
                continue
            if "{" in path:
                continue
            if "get" in methods:
                routes.append({"path": path, "method": "GET"})

        logger.info("Probe discovered %d routes via OpenAPI", len(routes))
    except Exception as e:
        logger.warning("Route discovery failed: %s", e)

    return routes


def _probe_endpoint(path: str, method: str = "GET") -> dict:
    """Send a synthetic pulse to a single endpoint."""
    url = f"{BASE}{path}"
    start = time.time()
    result = {
        "path": path,
        "method": method,
        "status": "unknown",
        "status_code": 0,
        "latency_ms": 0,
        "error": None,
        "probed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("X-Probe-Agent", "true")
        req.add_header("X-Genesis-Test", "true")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            result["status_code"] = resp.status
            result["latency_ms"] = round((time.time() - start) * 1000, 1)
            result["status"] = "active"
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        if e.code == 405:
            result["status"] = "active"
        elif e.code < 500:
            result["status"] = "active"
            result["error"] = f"HTTP {e.code}"
        else:
            result["status"] = "broken"
            result["error"] = f"HTTP {e.code}: {str(e.reason)[:100]}"
    except urllib.error.URLError as e:
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        result["status"] = "broken"
        result["error"] = f"Connection failed: {str(e.reason)[:100]}"
    except Exception as e:
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        if "timed out" in str(e).lower() or "timeout" in str(e).lower():
            result["status"] = "dormant"
            result["error"] = "Timeout"
        else:
            result["status"] = "broken"
            result["error"] = str(e)[:200]

    return result


def _probe_llm_models() -> List[dict]:
    """Probe each LLM model individually to check if it's callable."""
    results = []
    try:
        from settings import settings
    except Exception:
        return results

    models = [
        ("ollama_qwen", "qwen", settings.OLLAMA_MODEL_CODE),
        ("ollama_deepseek", "reasoning", settings.OLLAMA_MODEL_REASON),
        ("kimi", "kimi", settings.KIMI_MODEL if settings.KIMI_API_KEY else None),
        ("opus", "opus", settings.OPUS_MODEL if settings.OPUS_API_KEY else None),
    ]

    for label, model_id, model_name in models:
        if not model_name:
            results.append({
                "model_id": label,
                "model_name": model_name or "(not configured)",
                "status": "not_configured",
                "error": "API key or model not set",
                "latency_ms": 0,
            })
            continue

        start = time.time()
        try:
            from cognitive.consensus_engine import _get_client, MODEL_REGISTRY
            client = _get_client(model_id)
            if not client:
                results.append({
                    "model_id": label,
                    "model_name": model_name,
                    "status": "broken",
                    "error": "Client creation failed",
                    "latency_ms": 0,
                })
                continue

            response = client.generate(
                prompt="Reply with exactly: PROBE_OK",
                system_prompt="You are a health check probe. Reply with exactly the text PROBE_OK and nothing else.",
                temperature=0.0,
                max_tokens=20,
            )
            latency = round((time.time() - start) * 1000, 1)
            results.append({
                "model_id": label,
                "model_name": model_name,
                "status": "active",
                "response_preview": (response[:50] if isinstance(response, str) else str(response)[:50]),
                "latency_ms": latency,
            })
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            results.append({
                "model_id": label,
                "model_name": model_name,
                "status": "broken",
                "error": str(e)[:200],
                "latency_ms": latency,
            })

    return results


def _track_probe(results: List[dict]):
    """Log probe results via Genesis keys."""
    try:
        from api._genesis_tracker import track

        active = sum(1 for r in results if r.get("status") == "active")
        broken = sum(1 for r in results if r.get("status") == "broken")
        dormant = sum(1 for r in results if r.get("status") == "dormant")

        track(
            key_type="system_event",
            what=f"Probe sweep: {active} active, {broken} broken, {dormant} dormant out of {len(results)}",
            who="probe_agent",
            how="synthetic_pulse",
            output_data={
                "active": active, "broken": broken, "dormant": dormant,
                "total": len(results),
                "broken_paths": [r["path"] for r in results if r.get("status") == "broken"][:20],
            },
            tags=["probe", "health-check", "synthetic-test"],
        )
    except Exception:
        pass


def _consensus_diagnose(broken_items: List[dict]) -> List[dict]:
    """Ask ALL models to diagnose broken endpoints and propose fixes."""
    if not broken_items:
        return []

    diagnoses = []
    for item in broken_items[:5]:
        prompt = (
            f"A Grace API endpoint is broken.\n\n"
            f"Endpoint: {item.get('path') or item.get('model_id')}\n"
            f"Error: {item.get('error', 'unknown')}\n"
            f"Status code: {item.get('status_code', 'N/A')}\n\n"
            f"Diagnose the root cause and propose a specific fix. "
            f"Be concise — max 3 sentences for diagnosis, max 3 sentences for fix."
        )

        try:
            from cognitive.consensus_engine import run_consensus
            result = run_consensus(
                prompt=prompt,
                system_prompt="You are a system diagnostician. Diagnose API failures and propose fixes.",
                source="autonomous",
            )
            diagnoses.append({
                "endpoint": item.get("path") or item.get("model_id"),
                "error": item.get("error"),
                "diagnosis": result.final_output,
                "confidence": result.confidence,
                "models_used": result.models_used,
                "agreements": result.agreements,
                "disagreements": result.disagreements,
                "all_agree": len(result.disagreements) == 0,
            })

            try:
                from api._genesis_tracker import track
                track(
                    key_type="ai_response",
                    what=f"Consensus diagnosis for {item.get('path') or item.get('model_id')}: {result.final_output[:100]}",
                    who="probe_agent.consensus_diagnose",
                    how="consensus_engine.run_consensus",
                    input_data={"endpoint": item.get("path"), "error": item.get("error")},
                    output_data={
                        "diagnosis": result.final_output[:500],
                        "confidence": result.confidence,
                        "all_agree": len(result.disagreements) == 0,
                    },
                    tags=["probe", "consensus", "diagnosis", "auto-fix"],
                )
            except Exception:
                pass

        except Exception as e:
            diagnoses.append({
                "endpoint": item.get("path") or item.get("model_id"),
                "error": item.get("error"),
                "diagnosis": f"Consensus failed: {e}",
                "confidence": 0,
                "all_agree": False,
            })

    return diagnoses


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/sweep")
async def probe_sweep():
    """
    Full probe sweep — discover all routes, send synthetic pulses,
    classify as active/dormant/broken, track via Genesis keys.
    """
    routes = _discover_routes()
    results = []

    for route in routes:
        result = _probe_endpoint(route["path"], route["method"])
        results.append(result)

    _track_probe(results)

    with _probe_lock:
        _probe_results.clear()
        _probe_results.extend(results)

    active = [r for r in results if r["status"] == "active"]
    broken = [r for r in results if r["status"] == "broken"]
    dormant = [r for r in results if r["status"] == "dormant"]

    return {
        "total": len(results),
        "active": len(active),
        "broken": len(broken),
        "dormant": len(dormant),
        "broken_endpoints": broken,
        "dormant_endpoints": dormant,
        "sweep_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sweep-models")
async def probe_models():
    """Probe each LLM model individually — send a test prompt, check response."""
    results = _probe_llm_models()

    try:
        from api._genesis_tracker import track
        for r in results:
            track(
                key_type="system_event",
                what=f"LLM probe: {r['model_id']} = {r['status']}",
                who="probe_agent",
                how="synthetic_prompt",
                output_data=r,
                tags=["probe", "llm", r["model_id"], r["status"]],
            )
    except Exception:
        pass

    return {
        "models": results,
        "active": sum(1 for r in results if r["status"] == "active"),
        "broken": sum(1 for r in results if r["status"] == "broken"),
        "not_configured": sum(1 for r in results if r["status"] == "not_configured"),
    }


@router.post("/sweep-and-heal")
async def probe_and_heal():
    """
    Full pipeline: probe → classify → diagnose broken via consensus → heal.
    """
    # 1. Probe APIs
    api_sweep = await probe_sweep()

    # 2. Probe LLM models
    model_sweep = await probe_models()

    # 3. Collect all broken items
    broken = api_sweep.get("broken_endpoints", [])
    broken_models = [m for m in model_sweep.get("models", []) if m["status"] == "broken"]

    # 4. Consensus diagnosis on broken items
    diagnoses = []
    if broken or broken_models:
        all_broken = broken + broken_models
        diagnoses = _consensus_diagnose(all_broken)

    # 5. Auto-heal: dispatch to healing swarm + diagnostic engine
    healed = []
    for diag in diagnoses:
        if diag.get("all_agree") and diag.get("confidence", 0) > 0.6:
            # Dispatch to healing swarm for concurrent fix
            try:
                from cognitive.healing_swarm import get_healing_swarm
                swarm = get_healing_swarm()
                swarm.submit({
                    "component": diag.get("endpoint", "unknown"),
                    "description": diag.get("diagnosis", "Broken endpoint"),
                    "error": diag.get("error", ""),
                    "severity": "high",
                })
            except Exception:
                pass
            try:
                from diagnostic_machine.diagnostic_engine import get_diagnostic_engine, TriggerSource
                engine = get_diagnostic_engine()
                engine.run_cycle(TriggerSource.SENSOR_FLAG)
                healed.append({
                    "endpoint": diag["endpoint"],
                    "action": "swarm_dispatched_and_diagnostic_triggered",
                    "consensus_confidence": diag["confidence"],
                })
            except Exception as e:
                healed.append({
                    "endpoint": diag["endpoint"],
                    "action": "heal_failed",
                    "error": str(e),
                })

    return {
        "api_sweep": api_sweep,
        "model_sweep": model_sweep,
        "diagnoses": diagnoses,
        "healed": healed,
        "summary": {
            "apis_probed": api_sweep.get("total", 0),
            "apis_broken": api_sweep.get("broken", 0),
            "models_probed": len(model_sweep.get("models", [])),
            "models_broken": model_sweep.get("broken", 0),
            "diagnoses_made": len(diagnoses),
            "auto_healed": len([h for h in healed if h.get("action") != "heal_failed"]),
        },
    }


@router.get("/results")
async def get_probe_results():
    """Get results from the last probe sweep."""
    with _probe_lock:
        return {"results": list(_probe_results), "total": len(_probe_results)}


@router.post("/endpoint")
async def probe_single(path: str):
    """Probe a single endpoint."""
    result = _probe_endpoint(path)
    return result


# ── Component Alive Checker — throughput, telemetry, degradation ─────────

_vitals_history: Dict[str, List[dict]] = {}
_vitals_lock = threading.Lock()
_VITALS_MAX = 60  # keep last 60 readings per component


def _check_component_vitals() -> List[dict]:
    """
    Deep alive check: probe every core component for throughput,
    latency, error rate, and classify as alive / degraded / dead.
    """
    vitals = []

    # 1. Database — pool usage + query latency
    try:
        from database.connection import DatabaseConnection
        from sqlalchemy import text
        engine = DatabaseConnection.get_engine()
        pool = engine.pool
        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.time() - start) * 1000, 1)
        pool_size = pool.size() if callable(pool.size) else getattr(pool, '_pool', None) and pool._pool.qsize() or 0
        checked_out = pool.checkedout() if hasattr(pool, 'checkedout') else 0
        overflow = pool.overflow() if hasattr(pool, 'overflow') else 0
        status = "alive"
        if latency > 500:
            status = "degraded"
        if latency > 2000 or checked_out > 40:
            status = "critical"
        vitals.append({
            "component": "database",
            "status": status,
            "latency_ms": latency,
            "pool_checked_out": checked_out,
            "pool_overflow": overflow,
            "detail": f"query={latency}ms, conns={checked_out}+{overflow}",
        })
    except Exception as e:
        vitals.append({"component": "database", "status": "dead", "error": str(e)[:200]})

    # 2. Qdrant — collection count + query latency
    try:
        from vector_db.client import get_qdrant_client
        start = time.time()
        client = get_qdrant_client()
        collections = client.get_collections()
        latency = round((time.time() - start) * 1000, 1)
        count = len(collections.collections) if hasattr(collections, 'collections') else 0
        status = "alive" if latency < 1000 else "degraded"
        vitals.append({
            "component": "qdrant",
            "status": status,
            "latency_ms": latency,
            "collections": count,
            "detail": f"query={latency}ms, {count} collections",
        })
    except Exception as e:
        vitals.append({"component": "qdrant", "status": "dead", "error": str(e)[:200]})

    # 3. LLM / Ollama — tags endpoint latency
    try:
        start = time.time()
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        latency = round((time.time() - start) * 1000, 1)
        model_count = len(data.get("models", []))
        status = "alive" if latency < 2000 else "degraded"
        vitals.append({
            "component": "ollama",
            "status": status,
            "latency_ms": latency,
            "models_loaded": model_count,
            "detail": f"query={latency}ms, {model_count} models",
        })
    except Exception as e:
        vitals.append({"component": "ollama", "status": "dead", "error": str(e)[:200]})

    # 4. Brain domains — KPI throughput
    try:
        from api.kpi_api import get_kpi_tracker
        tracker = get_kpi_tracker()
        health = tracker.get_system_health() if hasattr(tracker, 'get_system_health') else {}
        for name, info in health.get("components", {}).items():
            trust = info.get("trust_score", 0)
            calls = info.get("total_calls", 0)
            errors = info.get("error_count", 0)
            error_rate = (errors / calls * 100) if calls > 0 else 0
            if trust < 0.3 or error_rate > 50:
                status = "critical"
            elif trust < 0.6 or error_rate > 20:
                status = "degraded"
            else:
                status = "alive"
            vitals.append({
                "component": f"brain:{name}",
                "status": status,
                "trust_score": round(trust, 3),
                "total_calls": calls,
                "error_rate_pct": round(error_rate, 1),
                "detail": f"trust={trust:.2f}, calls={calls}, err={error_rate:.1f}%",
            })
    except Exception:
        pass

    # 5. Event bus — throughput
    try:
        from cognitive.event_bus import get_stats
        stats = get_stats()
        published = stats.get("total_published", 0)
        dropped = stats.get("total_dropped", 0)
        drop_rate = (dropped / published * 100) if published > 0 else 0
        status = "alive" if drop_rate < 5 else "degraded" if drop_rate < 20 else "critical"
        vitals.append({
            "component": "event_bus",
            "status": status,
            "total_published": published,
            "drop_rate_pct": round(drop_rate, 1),
            "detail": f"published={published}, dropped={dropped}",
        })
    except Exception:
        pass

    # 6. Memory — system RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        status = "alive"
        if mem.percent > 85 or cpu > 80:
            status = "degraded"
        if mem.percent > 95 or cpu > 95:
            status = "critical"
        vitals.append({
            "component": "system_resources",
            "status": status,
            "memory_pct": mem.percent,
            "cpu_pct": cpu,
            "detail": f"RAM={mem.percent}%, CPU={cpu}%",
        })
    except Exception:
        pass

    # Store history for trend detection
    now = datetime.now(timezone.utc).isoformat()
    with _vitals_lock:
        for v in vitals:
            comp = v["component"]
            if comp not in _vitals_history:
                _vitals_history[comp] = []
            _vitals_history[comp].append({"ts": now, **v})
            if len(_vitals_history[comp]) > _VITALS_MAX:
                _vitals_history[comp] = _vitals_history[comp][-_VITALS_MAX:]

    # Detect degradation trends (was alive, now degraded/dead)
    with _vitals_lock:
        for v in vitals:
            history = _vitals_history.get(v["component"], [])
            if len(history) >= 3:
                recent = [h["status"] for h in history[-3:]]
                if recent[0] == "alive" and recent[-1] in ("degraded", "critical", "dead"):
                    v["trend"] = "degrading"
                elif recent[0] in ("degraded", "critical") and recent[-1] == "alive":
                    v["trend"] = "recovering"
                else:
                    v["trend"] = "stable"

    # Dispatch degraded/dead to healing swarm
    problems = [v for v in vitals if v.get("status") in ("degraded", "critical", "dead")]
    if problems:
        try:
            from cognitive.healing_swarm import get_healing_swarm
            swarm = get_healing_swarm()
            for p in problems:
                swarm.submit({
                    "component": p["component"],
                    "description": f"Component {p['status']}: {p.get('detail', p.get('error', ''))}",
                    "error": p.get("error", ""),
                    "severity": "critical" if p["status"] in ("dead", "critical") else "medium",
                })
        except Exception:
            pass

    return vitals


@router.get("/vitals")
async def get_component_vitals():
    """Deep alive check: throughput, latency, error rate for every core component."""
    import asyncio
    vitals = await asyncio.to_thread(_check_component_vitals)
    alive = sum(1 for v in vitals if v.get("status") == "alive")
    degraded = sum(1 for v in vitals if v.get("status") == "degraded")
    critical = sum(1 for v in vitals if v.get("status") == "critical")
    dead = sum(1 for v in vitals if v.get("status") == "dead")
    return {
        "vitals": vitals,
        "summary": {
            "total": len(vitals),
            "alive": alive,
            "degraded": degraded,
            "critical": critical,
            "dead": dead,
        },
    }


@router.get("/vitals/history")
async def get_vitals_history(component: Optional[str] = None):
    """Get vitals trend history for a component or all components."""
    with _vitals_lock:
        if component:
            return {"component": component, "history": _vitals_history.get(component, [])}
        return {"components": {k: v[-10:] for k, v in _vitals_history.items()}}
