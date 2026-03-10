"""
Model Auto-Update — Checks for new Kimi/Opus model versions and updates config.

When providers release new model versions (e.g. kimi-k2-0711 → kimi-k2-0812,
claude-sonnet-4 → claude-opus-5), this module:
1. Polls provider APIs for available models
2. Compares against current config
3. Logs new versions found
4. Optionally auto-switches to the latest model
5. Records the change via Genesis Key

Can be triggered manually or run on a schedule (e.g. daily).
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

VERSIONS_FILE = Path(__file__).parent.parent / "data" / "model_versions.json"


def _load_version_history() -> Dict[str, Any]:
    if VERSIONS_FILE.exists():
        try:
            return json.loads(VERSIONS_FILE.read_text())
        except Exception:
            pass
    return {"checks": [], "current": {}, "history": []}


def _save_version_history(data: Dict[str, Any]):
    VERSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSIONS_FILE.write_text(json.dumps(data, indent=2, default=str))


def check_kimi_models() -> Dict[str, Any]:
    """Check available Kimi models from the Moonshot API."""
    from settings import settings
    result = {"provider": "kimi", "current_model": settings.KIMI_MODEL, "available": [], "new_found": []}

    if not settings.KIMI_API_KEY:
        result["error"] = "KIMI_API_KEY not configured"
        return result

    try:
        from llm_orchestrator.kimi_client import KimiLLMClient
        client = KimiLLMClient()
        models = client.get_all_models()
        result["available"] = [
            {"id": m.get("id"), "created": m.get("created"), "owned_by": m.get("owned_by", "")}
            for m in models
        ]

        current = settings.KIMI_MODEL
        available_ids = {m.get("id") for m in models}
        new_models = [m for m in models if m.get("id") != current and "kimi" in (m.get("id", "")).lower()]
        if new_models:
            result["new_found"] = [m.get("id") for m in new_models]

        result["model_count"] = len(models)
        result["checked_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        result["error"] = str(e)

    return result


def check_opus_models() -> Dict[str, Any]:
    """Check available Opus/Claude models from the Anthropic API."""
    from settings import settings
    result = {"provider": "opus", "current_model": settings.OPUS_MODEL, "available": [], "new_found": []}

    if not settings.OPUS_API_KEY:
        result["error"] = "OPUS_API_KEY not configured"
        return result

    try:
        import requests
        resp = requests.get(
            f"{settings.OPUS_BASE_URL}/models",
            headers={
                "x-api-key": settings.OPUS_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            result["available"] = [
                {"id": m.get("id"), "display_name": m.get("display_name", ""), "created_at": m.get("created_at", "")}
                for m in models
            ]

            current = settings.OPUS_MODEL
            new_models = [m for m in models if m.get("id") != current]
            if new_models:
                result["new_found"] = [m.get("id") for m in new_models]

            result["model_count"] = len(models)
        else:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"

        result["checked_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        result["error"] = str(e)

    return result


def check_ollama_models() -> Dict[str, Any]:
    """Check available Ollama models."""
    from settings import settings
    result = {"provider": "ollama", "current_model": settings.OLLAMA_LLM_DEFAULT, "available": [], "new_found": []}

    try:
        import requests
        resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            result["available"] = [
                {"name": m.get("name"), "size": m.get("size"), "modified_at": m.get("modified_at", "")}
                for m in models
            ]
            result["model_count"] = len(models)
        else:
            result["error"] = f"HTTP {resp.status_code}"

        result["checked_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        result["error"] = str(e)

    return result


def check_runpod_models() -> Dict[str, Any]:
    """Check available RunPod vLLM models."""
    from settings import settings
    result = {"provider": "runpod", "current_model": getattr(settings, "RUNPOD_MODEL", "Mistral-7B-Instruct"), "available": [], "new_found": []}

    if not getattr(settings, "RUNPOD_API_KEY", None) or not getattr(settings, "RUNPOD_ENDPOINT_ID", None):
        result["error"] = "RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID not configured"
        return result

    try:
        import requests
        base_url = f"https://api.runpod.ai/v2/{settings.RUNPOD_ENDPOINT_ID}/openai/v1"
        resp = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {settings.RUNPOD_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            result["available"] = [{"id": m.get("id")} for m in models]
            
            current = result["current_model"]
            new_models = [m for m in models if m.get("id") != current]
            if new_models:
                result["new_found"] = [m.get("id") for m in new_models]

            result["model_count"] = len(models)
        else:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"

        result["checked_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        result["error"] = str(e)

    return result


def check_all_models() -> Dict[str, Any]:
    """Check all providers for model updates."""
    results = {
        "kimi": check_kimi_models(),
        "opus": check_opus_models(),
        "ollama": check_ollama_models(),
        "runpod": check_runpod_models(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Track any new discoveries
    total_new = 0
    for provider, data in results.items():
        if isinstance(data, dict):
            total_new += len(data.get("new_found", []))

    results["total_new_models"] = total_new

    # Save to version history
    history = _load_version_history()
    history["checks"].append({
        "timestamp": results["checked_at"],
        "total_new": total_new,
        "kimi_count": results["kimi"].get("model_count", 0),
        "opus_count": results["opus"].get("model_count", 0),
        "ollama_count": results["ollama"].get("model_count", 0),
        "runpod_count": results["runpod"].get("model_count", 0),
    })
    history["checks"] = history["checks"][-50:]  # Keep last 50 checks
    history["current"] = {
        "kimi": results["kimi"].get("current_model"),
        "opus": results["opus"].get("current_model"),
        "ollama": results["ollama"].get("current_model"),
        "runpod": results["runpod"].get("current_model"),
    }
    _save_version_history(history)

    # Genesis tracking
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Model version check: {total_new} new models found",
            how="model_updater.check_all_models",
            output_data={
                "new_kimi": results["kimi"].get("new_found", []),
                "new_opus": results["opus"].get("new_found", []),
            },
            tags=["model_update", "version_check"],
        )
    except Exception:
        pass

    return results


def update_model(provider: str, model_id: str) -> Dict[str, Any]:
    """
    Update the active model for a provider.
    Changes the runtime config (requires restart for settings.py defaults).
    """
    from settings import settings

    old_model = None
    if provider == "kimi":
        old_model = settings.KIMI_MODEL
        settings.KIMI_MODEL = model_id
    elif provider == "opus":
        old_model = settings.OPUS_MODEL
        settings.OPUS_MODEL = model_id
    elif provider == "ollama":
        old_model = settings.OLLAMA_LLM_DEFAULT
        settings.OLLAMA_LLM_DEFAULT = model_id
    elif provider == "runpod":
        old_model = getattr(settings, "RUNPOD_MODEL", "Mistral-7B-Instruct")
        settings.RUNPOD_MODEL = model_id
    else:
        return {"error": f"Unknown provider: {provider}"}

    # Update .env file for persistence
    try:
        env_file = Path(__file__).parent.parent / ".env"
        env_key = {
            "kimi": "KIMI_MODEL",
            "opus": "OPUS_MODEL",
            "ollama": "OLLAMA_LLM_DEFAULT",
            "runpod": "RUNPOD_MODEL",
        }.get(provider)

        if env_key and env_file.exists():
            content = env_file.read_text()
            lines = content.split("\n")
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{env_key}="):
                    lines[i] = f"{env_key}={model_id}"
                    found = True
                    break
            if not found:
                lines.append(f"{env_key}={model_id}")
            env_file.write_text("\n".join(lines))
    except Exception as e:
        logger.warning(f"Failed to update .env: {e}")

    # Record in version history
    history = _load_version_history()
    history["history"].append({
        "provider": provider,
        "old_model": old_model,
        "new_model": model_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    history["current"][provider] = model_id
    _save_version_history(history)

    # Genesis tracking
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Model updated: {provider} {old_model} → {model_id}",
            how="model_updater.update_model",
            output_data={"provider": provider, "old": old_model, "new": model_id},
            tags=["model_update", provider],
        )
    except Exception:
        pass

    return {
        "updated": True,
        "provider": provider,
        "old_model": old_model,
        "new_model": model_id,
    }


def get_version_history() -> Dict[str, Any]:
    """Get the model version change history."""
    return _load_version_history()
