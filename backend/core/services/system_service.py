"""System domain service Ã¢â‚¬â€ direct function calls for health, runtime, monitoring."""

import time as _time
import gc


def get_runtime_status() -> dict:
    try:
        from app import app
        return {
            "paused": getattr(app.state, "runtime_paused", False),
            "diagnostic_engine": "running",
            "self_healing": True,
            "uptime_seconds": _time.time() - getattr(app.state, "_start_time", _time.time()),
        }
    except Exception:
        return {"paused": False, "diagnostic_engine": "unknown"}


def hot_reload() -> dict:
    results = {}
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
        results["settings"] = "reloaded"
    except Exception as e:
        results["settings"] = f"error: {e}"

    try:
        from cognitive.consensus_engine import _build_model_registry, get_available_models
        import cognitive.consensus_engine as ce
        ce.MODEL_REGISTRY = _build_model_registry()
        results["consensus_models"] = {m["id"]: m["available"] for m in get_available_models()}
    except Exception as e:
        results["consensus_models"] = f"error: {e}"

    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.get_engine().dispose()
        results["database"] = "pool refreshed"
    except Exception as e:
        results["database"] = f"error: {e}"

    return {"status": "hot-reload complete", "results": results}


def pause_runtime() -> dict:
    try:
        from app import app
        app.state.runtime_paused = True
        diag = getattr(app.state, "diagnostic_engine", None)
        if diag:
            diag.pause()
    except Exception:
        pass
    return {"status": "paused"}


def resume_runtime() -> dict:
    try:
        from app import app
        app.state.runtime_paused = False
        diag = getattr(app.state, "diagnostic_engine", None)
        if diag:
            diag.resume()
    except Exception:
        pass
    return {"status": "resumed"}


def get_health_dashboard() -> dict:
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }


def get_bi_dashboard() -> dict:
    try:
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        return get_llm_usage_stats()
    except Exception:
        return {"total_calls": 0}


def get_diagnostics_status() -> dict:
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        return get_diagnostics().get_status() if hasattr(get_diagnostics(), 'get_status') else {"status": "running"}
    except Exception:
        return {"status": "unavailable"}


def get_health_map(payload: dict) -> dict:
    from api.component_health_api import health_map
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(health_map(payload.get("window_minutes", 60)))
    finally:
        loop.close()


def get_problems() -> dict:
    from api.component_health_api import problems_list
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(problems_list())
    finally:
        loop.close()


def get_consensus_models() -> dict:
    from cognitive.consensus_engine import get_available_models
    return {"models": get_available_models()}


def gc_collect() -> dict:
    collected = gc.collect()
    return {"collected": collected}
