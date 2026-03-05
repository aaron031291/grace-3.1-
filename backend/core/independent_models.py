"""
Independent Model Execution — each model works on its own.

If Kimi is down, Opus/Qwen/DeepSeek still work independently.
Consensus is optional — models can run solo or together.

Features:
  - Parallel independent execution
  - Failover: skip failed models, continue with working ones
  - Individual model results available separately
  - Consensus only when explicitly requested
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def run_independent(prompt: str, models: List[str] = None,
                    system_prompt: str = "", timeout: int = 60) -> dict:
    """
    Run each model independently in parallel.
    Failed models don't block others.

    Returns individual results — NOT consensus.
    """
    if not models:
        models = _get_available_models()

    results = {}
    threads = []
    lock = threading.Lock()

    def _run_one(model_id):
        start = time.time()
        try:
            from cognitive.consensus_engine import _get_client, _check_model_available
            if not _check_model_available(model_id):
                with lock:
                    results[model_id] = {
                        "status": "unavailable",
                        "error": "Model not configured",
                        "latency_ms": 0,
                    }
                return

            client = _get_client(model_id)
            if not client:
                with lock:
                    results[model_id] = {
                        "status": "no_client",
                        "error": "Client creation failed",
                        "latency_ms": 0,
                    }
                return

            response = client.generate(
                prompt=prompt,
                system_prompt=system_prompt or "You are a helpful assistant.",
                temperature=0.5,
                max_tokens=4096,
            )
            latency = round((time.time() - start) * 1000, 1)

            with lock:
                results[model_id] = {
                    "status": "success",
                    "response": response if isinstance(response, str) else str(response),
                    "latency_ms": latency,
                }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            with lock:
                results[model_id] = {
                    "status": "failed",
                    "error": str(e)[:200],
                    "latency_ms": latency,
                }

    for mid in models:
        t = threading.Thread(target=_run_one, args=(mid,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=timeout)

    successful = {k: v for k, v in results.items() if v["status"] == "success"}
    failed = {k: v for k, v in results.items() if v["status"] != "success"}

    return {
        "models_requested": models,
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
        "any_success": len(successful) > 0,
    }


def run_with_failover(prompt: str, preferred_order: List[str] = None,
                      system_prompt: str = "") -> dict:
    """
    Try models in order. First success wins. Others skip.
    """
    if not preferred_order:
        preferred_order = ["kimi", "opus", "qwen", "reasoning"]

    for model_id in preferred_order:
        result = run_independent(prompt, [model_id], system_prompt, timeout=30)
        model_result = result["results"].get(model_id, {})
        if model_result.get("status") == "success":
            return {
                "model": model_id,
                "response": model_result["response"],
                "latency_ms": model_result["latency_ms"],
                "failover_attempts": preferred_order.index(model_id) + 1,
            }

    return {"model": None, "response": "", "error": "All models failed",
            "failover_attempts": len(preferred_order)}


def _get_available_models() -> list:
    """Get list of models that might be available."""
    try:
        from cognitive.consensus_engine import _check_model_available
        all_models = ["kimi", "opus", "qwen", "reasoning"]
        return [m for m in all_models if _check_model_available(m)]
    except Exception:
        return ["kimi", "opus"]
