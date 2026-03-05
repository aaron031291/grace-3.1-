"""
Live Console API — Real-time interaction with Kimi + Opus while Grace is running.

Endpoints the user can call from their browser to talk to both models
about Grace's LIVE state:
  - /api/console/ask — ask Kimi+Opus anything about the running system
  - /api/console/diagnose — both models diagnose current errors
  - /api/console/fix — both models suggest fixes for current problems
  - /api/console/status — full system status in plain English
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Live Console"])


class ConsoleQuery(BaseModel):
    message: str
    use_consensus: bool = True


@router.get("/status")
async def live_status():
    """Full system status — what's working and what's broken RIGHT NOW."""
    status = {
        "backend": "running",
        "errors": [],
        "warnings": [],
        "models": {},
        "database": "unknown",
        "services": {},
    }

    # Check database
    try:
        from database.session import SessionLocal, initialize_session_factory
        if SessionLocal is None:
            initialize_session_factory()
        from database.session import SessionLocal as SL
        db = SL()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)[:100]}"
        status["errors"].append(f"Database: {str(e)[:100]}")

    # Check Kimi
    try:
        from settings import settings
        if settings.KIMI_API_KEY:
            import requests
            r = requests.get(f"{settings.KIMI_BASE_URL}/models",
                           headers={"Authorization": f"Bearer {settings.KIMI_API_KEY}"},
                           timeout=5)
            if r.status_code == 200:
                models = r.json().get("data", [])
                status["models"]["kimi"] = {"status": "connected", "model_count": len(models)}
            else:
                status["models"]["kimi"] = {"status": f"error: HTTP {r.status_code}"}
                status["errors"].append(f"Kimi: HTTP {r.status_code}")
        else:
            status["models"]["kimi"] = {"status": "no API key"}
            status["warnings"].append("Kimi: no API key configured")
    except Exception as e:
        status["models"]["kimi"] = {"status": f"error: {str(e)[:80]}"}

    # Check Opus
    try:
        from settings import settings
        if settings.OPUS_API_KEY:
            status["models"]["opus"] = {"status": "configured", "model": settings.OPUS_MODEL}
        else:
            status["models"]["opus"] = {"status": "no API key"}
            status["warnings"].append("Opus: no API key configured")
    except Exception as e:
        status["models"]["opus"] = {"status": f"error: {str(e)[:80]}"}

    # Check Qwen 3 (DashScope)
    try:
        from settings import settings
        qwen_key = getattr(settings, "QWEN_API_KEY", "")
        qwen_model = getattr(settings, "QWEN_MODEL", "qwen-plus")
        if qwen_key:
            status["models"]["qwen"] = {"status": "configured", "model": qwen_model, "mode": "cloud"}
        elif getattr(settings, "OLLAMA_MODEL_FAST", ""):
            status["models"]["qwen"] = {"status": "local (via Ollama)", "model": settings.OLLAMA_MODEL_FAST, "mode": "local"}
        else:
            status["models"]["qwen"] = {"status": "not configured"}
            status["warnings"].append("Qwen: no API key and no Ollama model configured")
    except Exception as e:
        status["models"]["qwen"] = {"status": f"error: {str(e)[:80]}"}

    # Check Ollama
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = r.json().get("models", [])
            status["models"]["ollama"] = {
                "status": "connected",
                "models": [m["name"] for m in models[:5]],
            }
        else:
            status["models"]["ollama"] = {"status": "not running"}
            status["warnings"].append("Ollama: not running")
    except Exception:
        status["models"]["ollama"] = {"status": "not running"}
        status["warnings"].append("Ollama: not running — local models unavailable")

    # Check services
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        s = fc.stats()
        status["services"]["flash_cache"] = f"{s.get('total_entries', 0)} entries"
    except Exception:
        status["services"]["flash_cache"] = "error"

    try:
        from cognitive.circuit_breaker import NAMED_LOOPS
        status["services"]["loops"] = f"{len(NAMED_LOOPS)} registered"
    except Exception:
        status["services"]["loops"] = "error"

    # Summary
    if not status["errors"]:
        status["summary"] = "Grace is running. All systems operational."
    else:
        status["summary"] = f"Grace is running with {len(status['errors'])} error(s): {'; '.join(status['errors'][:3])}"

    return status


@router.post("/ask")
async def ask_models(query: ConsoleQuery):
    """Ask Kimi+Opus anything about the running system."""
    # Get current system state for context
    try:
        current_status = await live_status()
        context = f"Grace is running. Status: {current_status.get('summary', 'unknown')}"
    except Exception:
        context = "Grace is running."

    if query.use_consensus:
        try:
            from cognitive.consensus_engine import run_consensus
            result = run_consensus(
                prompt=query.message,
                models=["kimi", "opus"],
                context=context,
                source="user",
            )
            return {
                "response": result.final_output,
                "models_used": result.models_used,
                "confidence": result.confidence,
                "individual": [
                    {"model": r["model_name"], "response": r["response"][:1000]}
                    for r in result.individual_responses if r.get("response")
                ],
            }
        except Exception as e:
            return {"error": str(e), "suggestion": "Check API keys in .env file"}
    else:
        try:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client(provider="opus")
            response = client.generate(prompt=query.message, temperature=0.5, max_tokens=2048)
            return {"response": response, "model": "opus"}
        except Exception as e:
            return {"error": str(e)}


@router.post("/diagnose")
async def diagnose_live():
    """Both models diagnose current errors in the running system."""
    current_status = await live_status()

    if not current_status.get("errors"):
        return {"diagnosis": "No errors detected. Grace is healthy.", "errors": []}

    try:
        from cognitive.consensus_engine import run_consensus
        result = run_consensus(
            prompt=(
                f"Grace is running but has these errors:\n\n"
                + "\n".join(f"- {e}" for e in current_status["errors"])
                + f"\n\nWarnings:\n"
                + "\n".join(f"- {w}" for w in current_status.get("warnings", []))
                + f"\n\nDiagnose each error and give the exact fix command."
            ),
            models=["kimi", "opus"],
            source="user",
        )
        return {
            "errors": current_status["errors"],
            "warnings": current_status.get("warnings", []),
            "diagnosis": result.final_output,
            "confidence": result.confidence,
        }
    except Exception as e:
        return {
            "errors": current_status["errors"],
            "diagnosis": f"Consensus unavailable: {e}. Check API keys.",
        }


@router.get("/health-plain")
async def health_plain_english():
    """One sentence: is Grace healthy?"""
    status = await live_status()
    return {"health": status.get("summary", "Unknown")}
