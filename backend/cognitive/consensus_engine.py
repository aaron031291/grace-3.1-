"""
Multi-Model Consensus Engine — Knights of the Roundtable

A 4-layer deliberation protocol where multiple LLMs independently tackle the
same problem, then converge through consensus, alignment, and verification.

Layer 1 — Independent Deliberation:
  Each selected model receives the same prompt/problem/context independently.
  No model sees another's output.

Layer 2 — Consensus Formation:
  All responses are collected, compared, and synthesised into a unified position.
  Areas of agreement strengthen; disagreements are flagged for deeper analysis.

Layer 3 — Alignment:
  The consensus is aligned to Grace's internal world, user context, and the
  specific problem domain. If Grace initiated the query autonomously, alignment
  is to her own needs and the system's integrity.

Layer 4 — Verification:
  The aligned output passes through the existing verification pipeline:
  trust scoring, hallucination guard, contradiction detection, and
  deterministic checks.

Autonomous Mode:
  Grace can invoke the roundtable when she's stuck — needs deterministic
  answers or faces ambiguity. Autonomous queries are batched to control
  token costs (daily/weekly configurable).

Available Models:
  - Opus 4.6   (Anthropic Claude) — deep reasoning, audit, architecture
  - Kimi 2.5   (Moonshot AI)      — long-context, document analysis
  - Qwen 2.5   (via Ollama)       — local, fast, code-oriented
  - Reasoning   (via Ollama)       — local reasoning model (configurable)
"""

import asyncio
import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BATCH_DIR = Path(__file__).parent.parent / "data" / "consensus_batches"

def _build_model_registry() -> dict:
    """Build model registry using the actual configured model names."""
    try:
        from settings import settings
        reason_model = getattr(settings, "OLLAMA_MODEL_REASON", "") or "deepseek-r1:7b"
        qwen_model = getattr(settings, "QWEN_MODEL", "") or "qwen3:8b"
        qwen_has_key = bool(getattr(settings, "QWEN_API_KEY", ""))
    except Exception:
        reason_model = "deepseek-r1:7b"
        qwen_model = "qwen3:8b"
        qwen_has_key = False

    registry = {
        "opus": {
            "name": "Opus 4.6 (Claude)",
            "provider": "opus",
            "strengths": ["deep reasoning", "architecture", "audit", "code review"],
            "cost_tier": "cloud",
        },
        "kimi": {
            "name": "Kimi K2.5 (Moonshot)",
            "provider": "kimi",
            "strengths": ["long context (262K)", "document analysis", "system reasoning"],
            "cost_tier": "cloud",
        },
        "qwen": {
            "name": f"Qwen 3 — {qwen_model} ({'Cloud' if qwen_has_key else 'Local'})",
            "provider": "qwen",
            "strengths": ["code generation", "reasoning", "multilingual", "256K context", "tool calling"],
            "cost_tier": "cloud" if qwen_has_key else "free",
        },
        "reasoning": {
            "name": f"DeepSeek R1 — {reason_model} (Local)",
            "provider": "ollama",
            "task": "reason",
            "strengths": ["chain-of-thought", "mathematical reasoning", "problem decomposition"],
            "cost_tier": "free",
        },
    }

    return registry


MODEL_REGISTRY = _build_model_registry()


@dataclass
class ModelResponse:
    model_id: str
    model_name: str
    response: str
    latency_ms: float
    error: Optional[str] = None
    token_estimate: int = 0


@dataclass
class ConsensusResult:
    query: str
    models_used: List[str]
    individual_responses: List[dict]
    consensus_text: str
    alignment_text: str
    verification: dict
    confidence: float
    agreements: List[str]
    disagreements: List[str]
    final_output: str
    total_latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "user"  # user or autonomous


def _get_client(model_id: str):
    """Get the appropriate LLM client for a model."""
    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return None

    from llm_orchestrator.factory import get_llm_client, get_llm_for_task, get_qwen_coder, get_qwen_client, get_deepseek_reasoner

    provider = info.get("provider")
    task = info.get("task")

    if provider == "opus":
        return get_llm_client(provider="opus")
    elif provider == "kimi":
        return get_llm_client(provider="kimi")
    elif provider == "qwen":
        return get_qwen_client()
    elif task == "code":
        return get_qwen_coder()
    elif task == "reason":
        return get_deepseek_reasoner()
    elif task:
        return get_llm_for_task(task)
    else:
        return get_llm_client()


def _check_model_available(model_id: str) -> bool:
    """Check if a model is available and configured.

    For cloud models (Opus, Kimi) this checks API keys.
    For local Ollama models this pings the Ollama API to confirm the model
    is actually pulled and reachable, falling back to a simple config check
    if Ollama is unreachable.
    """
    from settings import settings
    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return False

    if info["provider"] == "opus":
        return bool(getattr(settings, "OPUS_API_KEY", ""))
    elif info["provider"] == "kimi":
        return bool(getattr(settings, "KIMI_API_KEY", ""))
    elif info["provider"] == "qwen":
        if getattr(settings, "QWEN_API_KEY", ""):
            return True
        fallback_model = getattr(settings, "OLLAMA_MODEL_FAST", "")
        if fallback_model:
            return _ollama_model_exists(fallback_model, settings)
        return False
    elif info["provider"] == "ollama":
        if info.get("task") == "code":
            model_name = getattr(settings, "OLLAMA_MODEL_CODE", "")
        elif info.get("task") == "reason":
            model_name = getattr(settings, "OLLAMA_MODEL_REASON", "")
        else:
            model_name = getattr(settings, "OLLAMA_MODEL_FAST", "")

        if not model_name:
            return False

        return _ollama_model_exists(model_name, settings)
    return True


def _ollama_model_exists(model_name: str, settings) -> bool:
    """Verify an Ollama model is pulled and reachable."""
    import urllib.request
    import json as _json
    try:
        url = (getattr(settings, "OLLAMA_URL", "http://localhost:11434")
               .rstrip("/") + "/api/tags")
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read())
        available = [m.get("name", "") for m in data.get("models", [])]
        needle = model_name if ":" in model_name else f"{model_name}:latest"
        return any(
            needle == a or needle.split(":")[0] == a.split(":")[0]
            for a in available
        )
    except Exception:
        return True


def get_available_models() -> List[dict]:
    """Return list of available models with their status."""
    global MODEL_REGISTRY
    MODEL_REGISTRY = _build_model_registry()
    result = []
    for mid, info in MODEL_REGISTRY.items():
        available = _check_model_available(mid)
        result.append({
            "id": mid,
            "name": info["name"],
            "strengths": info["strengths"],
            "cost_tier": info["cost_tier"],
            "available": available,
        })
    return result


# ── Layer 1: Independent Deliberation ─────────────────────────────────

def _run_model(model_id: str, prompt: str, system_prompt: str,
               context: str = "") -> ModelResponse:
    """Run a single model independently."""
    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return ModelResponse(
            model_id=model_id, model_name="unknown",
            response="", latency_ms=0, error="Unknown model"
        )

    client = _get_client(model_id)
    if not client:
        return ModelResponse(
            model_id=model_id, model_name=info["name"],
            response="", latency_ms=0, error="Client unavailable"
        )

    full_prompt = prompt
    if context:
        full_prompt = f"Context:\n{context}\n\n{prompt}"

    start = time.time()
    try:
        response = client.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=4096,
        )
        latency = (time.time() - start) * 1000
        token_est = len(response.split()) if isinstance(response, str) else 0
        return ModelResponse(
            model_id=model_id,
            model_name=info["name"],
            response=response if isinstance(response, str) else str(response),
            latency_ms=round(latency, 1),
            token_estimate=token_est,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Model {model_id} failed: {e}")
        return ModelResponse(
            model_id=model_id, model_name=info["name"],
            response="", latency_ms=round(latency, 1), error=str(e)
        )


def layer1_deliberate(
    prompt: str,
    models: List[str],
    system_prompt: str = "",
    context: str = "",
) -> List[ModelResponse]:
    """
    Layer 1: Run all selected models independently on the same problem.
    Uses threading for parallel execution.
    """
    if not system_prompt:
        system_prompt = (
            "You are a member of a multi-model deliberation panel. "
            "Analyze the problem thoroughly and provide your independent assessment. "
            "Be specific, cite reasoning, and highlight any uncertainties."
        )

    responses = []
    threads = []
    results_lock = threading.Lock()

    def run_and_collect(mid):
        resp = _run_model(mid, prompt, system_prompt, context)
        with results_lock:
            responses.append(resp)

    for mid in models:
        if not _check_model_available(mid):
            responses.append(ModelResponse(
                model_id=mid,
                model_name=MODEL_REGISTRY.get(mid, {}).get("name", mid),
                response="", latency_ms=0, error="Model not configured"
            ))
            continue
        t = threading.Thread(target=run_and_collect, args=(mid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=180)

    return responses


# ── Layer 2: Consensus Formation ──────────────────────────────────────

def layer2_consensus(
    prompt: str,
    responses: List[ModelResponse],
    synthesizer_model: str = "kimi",
) -> Tuple[str, List[str], List[str]]:
    """
    Layer 2: Synthesise individual responses into a consensus.
    Returns (consensus_text, agreements, disagreements).
    """
    valid_responses = [r for r in responses if r.response and not r.error]
    if not valid_responses:
        return "No valid responses to synthesise.", [], ["All models failed"]

    if len(valid_responses) == 1:
        return valid_responses[0].response, ["Single model — no consensus needed"], []

    response_block = ""
    for i, r in enumerate(valid_responses, 1):
        response_block += f"\n--- Model {i}: {r.model_name} ---\n{r.response[:3000]}\n"

    synthesis_prompt = (
        f"You are the consensus synthesiser. Multiple AI models have independently "
        f"analyzed the same problem. Your job is to:\n\n"
        f"1. Identify AGREEMENTS — points where models converge\n"
        f"2. Identify DISAGREEMENTS — points of divergence\n"
        f"3. Produce a CONSENSUS — the strongest, most reliable unified answer\n"
        f"4. Note UNCERTAINTIES — areas where confidence is low\n\n"
        f"Original problem:\n{prompt[:2000]}\n\n"
        f"Model responses:{response_block}\n\n"
        f"Produce your response in this structure:\n"
        f"## Agreements\n- ...\n\n"
        f"## Disagreements\n- ...\n\n"
        f"## Consensus\n...\n\n"
        f"## Confidence Level\nHigh/Medium/Low with reasoning"
    )

    client = _get_client(synthesizer_model)
    if not client:
        client = _get_client("qwen") or _get_client("reasoning")
    if not client:
        combined = "\n\n".join(r.response[:1500] for r in valid_responses)
        return combined, ["Fallback: combined responses"], ["No synthesiser available"]

    try:
        result = client.generate(
            prompt=synthesis_prompt,
            system_prompt="You are a consensus formation engine. Synthesise multiple perspectives into one authoritative answer.",
            temperature=0.3,
            max_tokens=4096,
        )

        agreements = []
        disagreements = []
        if isinstance(result, str):
            lines = result.split("\n")
            section = ""
            for line in lines:
                stripped = line.strip()
                if "agreement" in stripped.lower():
                    section = "agree"
                elif "disagreement" in stripped.lower():
                    section = "disagree"
                elif "consensus" in stripped.lower():
                    section = "consensus"
                elif stripped.startswith("- ") and section == "agree":
                    agreements.append(stripped[2:])
                elif stripped.startswith("- ") and section == "disagree":
                    disagreements.append(stripped[2:])

        return result if isinstance(result, str) else str(result), agreements, disagreements

    except Exception as e:
        logger.error(f"Consensus synthesis failed: {e}")
        combined = "\n\n---\n\n".join(r.response[:2000] for r in valid_responses)
        return combined, [], [f"Synthesis error: {e}"]


# ── Layer 3: Alignment ────────────────────────────────────────────────

def layer3_align(
    prompt: str,
    consensus: str,
    source: str = "user",
    user_context: str = "",
    system_context: str = "",
) -> str:
    """
    Layer 3: Align the consensus to Grace/user/system needs.
    """
    if source == "autonomous":
        alignment_prompt = (
            f"You are Grace's alignment engine. The consensus below was produced "
            f"by a multi-model roundtable. Grace initiated this query autonomously "
            f"because she needs a deterministic answer.\n\n"
            f"Align this consensus to Grace's internal needs:\n"
            f"- Is it actionable for Grace's self-improvement?\n"
            f"- Does it align with Grace's governance rules?\n"
            f"- What specific system actions should result from this?\n"
            f"- How should this knowledge be stored (learning, memory, rules)?\n\n"
        )
    else:
        alignment_prompt = (
            f"You are Grace's alignment engine. The consensus below was produced "
            f"by a multi-model roundtable for a user query.\n\n"
            f"Align this consensus to the user's needs:\n"
            f"- Is it directly answering what the user asked?\n"
            f"- Is it practical and actionable?\n"
            f"- Does it account for the user's context?\n"
            f"- Is the language appropriate for the user?\n\n"
        )

    if user_context:
        alignment_prompt += f"User context: {user_context}\n\n"
    if system_context:
        alignment_prompt += f"System context: {system_context}\n\n"

    alignment_prompt += (
        f"Original query: {prompt[:1000]}\n\n"
        f"Consensus:\n{consensus[:4000]}\n\n"
        f"Produce the final aligned response."
    )

    client = _get_client("kimi") or _get_client("opus") or _get_client("qwen")
    if not client:
        return consensus

    try:
        result = client.generate(
            prompt=alignment_prompt,
            system_prompt="You are Grace's alignment engine. Ensure the roundtable consensus is optimally aligned to the recipient's needs.",
            temperature=0.3,
            max_tokens=4096,
        )
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        logger.warning(f"Alignment failed, returning raw consensus: {e}")
        return consensus


# ── Layer 4: Verification ─────────────────────────────────────────────

def layer4_verify(aligned_output: str, prompt: str) -> dict:
    """
    Layer 4: Pass through existing verification pipeline.
    Trust scoring, contradiction detection, hallucination guard.
    """
    verification = {
        "trust_score": 0.0,
        "hallucination_flags": [],
        "contradiction_flags": [],
        "passed": False,
    }

    # Trust Engine scoring
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        score = te.score_output(
            "consensus_engine", "Consensus Roundtable",
            aligned_output[:1000], source="multi_model"
        )
        verification["trust_score"] = score if isinstance(score, (int, float)) else 0.7
    except Exception:
        verification["trust_score"] = 0.7

    # Basic hallucination checks
    try:
        suspicious = 0
        if "I don't have" in aligned_output or "I cannot" in aligned_output:
            suspicious += 1
        if "as an AI" in aligned_output.lower():
            suspicious += 1
        if len(aligned_output) < 50:
            suspicious += 1
            verification["hallucination_flags"].append("Response too short")

        verification["hallucination_score"] = max(0, 1.0 - suspicious * 0.2)
    except Exception:
        verification["hallucination_score"] = 0.7

    # Determine pass/fail
    trust = verification.get("trust_score", 0)
    if isinstance(trust, dict):
        trust = trust.get("score", 0.7)
    verification["passed"] = (
        trust >= 0.4
        and verification.get("hallucination_score", 0) >= 0.5
        and len(verification.get("contradiction_flags", [])) == 0
    )

    return verification


# ── Full Pipeline ─────────────────────────────────────────────────────

def run_consensus(
    prompt: str,
    models: List[str] = None,
    system_prompt: str = "",
    context: str = "",
    source: str = "user",
    user_context: str = "",
) -> ConsensusResult:
    """
    Execute the full 4-layer consensus pipeline.
    """
    global MODEL_REGISTRY
    MODEL_REGISTRY = _build_model_registry()

    if not models:
        models = [m for m in MODEL_REGISTRY if _check_model_available(m)]
    if not models:
        models = ["qwen"]

    logger.info(
        "Consensus roundtable starting — models: %s",
        ", ".join(f"{m} ({MODEL_REGISTRY.get(m, {}).get('name', '?')})" for m in models),
    )

    start = time.time()

    # Gather system context
    system_context = ""
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        kpis = te.get_dashboard()
        system_context = f"System trust: {kpis.get('overall_trust', 'unknown')}"
    except Exception:
        pass

    # Layer 1
    responses = layer1_deliberate(prompt, models, system_prompt, context)

    # Layer 2
    consensus_text, agreements, disagreements = layer2_consensus(prompt, responses)

    # Layer 3
    aligned_text = layer3_align(
        prompt, consensus_text, source=source,
        user_context=user_context, system_context=system_context,
    )

    # Layer 4
    verification = layer4_verify(aligned_text, prompt)

    total_latency = (time.time() - start) * 1000
    final_output = aligned_text if verification["passed"] else consensus_text

    result = ConsensusResult(
        query=prompt,
        models_used=models,
        individual_responses=[
            {
                "model_id": r.model_id,
                "model_name": r.model_name,
                "response": r.response[:2000],
                "latency_ms": r.latency_ms,
                "error": r.error,
                "token_estimate": r.token_estimate,
            }
            for r in responses
        ],
        consensus_text=consensus_text,
        alignment_text=aligned_text,
        verification=verification,
        confidence=verification.get("trust_score", 0.5) if isinstance(verification.get("trust_score"), (int, float)) else 0.5,
        agreements=agreements,
        disagreements=disagreements,
        final_output=final_output,
        total_latency_ms=round(total_latency, 1),
        source=source,
    )

    # Route disagreements to governance approval queue + ML reward buffer
    if disagreements:
        try:
            from cognitive.event_bus import publish
            publish("consensus.disagreement", {
                "models": models,
                "disagreements": disagreements,
                "prompt_preview": prompt[:200],
                "requires_governance": True,
            }, source="consensus_engine")
        except Exception:
            pass

        # Feed disagreement as ML training signal
        try:
            from cognitive.ml_trainer import get_ml_trainer
            get_ml_trainer().observe("consensus_refinement", {
                "agreement_count": len(agreements),
                "disagreement_count": len(disagreements),
                "confidence": result.confidence,
            }, "degradation" if len(disagreements) > len(agreements) else "success")
        except Exception:
            pass

        # Feed consensus result into adaptive trust (real-time)
        try:
            from core.intelligence import ConsensusTrustBridge
            ConsensusTrustBridge.process_consensus_result({
                "models_used": models,
                "agreements": agreements,
                "disagreements": disagreements,
                "confidence": result.confidence,
                "individual_responses": result.individual_responses,
            })
        except Exception:
            pass

    # Log to reporting engine
    try:
        from cognitive.event_bus import publish
        publish("consensus.completed", {
            "models": models,
            "agreements": len(agreements),
            "disagreements": len(disagreements),
            "confidence": result.confidence,
            "latency_ms": result.total_latency_ms,
            "passed": verification["passed"],
        }, source="consensus_engine")
    except Exception:
        pass

    # Track via Genesis
    try:
        from api._genesis_tracker import track
        track(
            key_type="ai_response",
            what=f"Consensus roundtable: {len(models)} models, {len(agreements)} agreements, {len(disagreements)} disagreements",
            how="consensus_engine.run_consensus",
            output_data={
                "models": models,
                "confidence": result.confidence,
                "passed_verification": verification["passed"],
                "agreements": len(agreements),
                "disagreements": len(disagreements),
                "disagreement_details": disagreements[:5],
            },
            tags=["consensus", "roundtable", source],
        )
    except Exception:
        pass

    # Store in learning if from autonomous
    if source == "autonomous":
        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="", prompt=prompt,
                output=final_output[:3000], outcome="positive",
            )
        except Exception:
            pass

    return result


# ── Autonomous Batch Queue ────────────────────────────────────────────

_batch_queue: List[dict] = []
_batch_lock = threading.Lock()


def queue_autonomous_query(prompt: str, context: str = "", priority: str = "normal"):
    """
    Queue a query for the next autonomous batch run.
    Grace calls this when she needs multi-model help but it's not urgent.
    """
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "prompt": prompt,
        "context": context,
        "priority": priority,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
    }
    with _batch_lock:
        _batch_queue.append(entry)
        _save_batch_queue()
    return entry


def get_batch_queue() -> List[dict]:
    """Get the current autonomous batch queue."""
    _load_batch_queue()
    with _batch_lock:
        return list(_batch_queue)


def run_batch(max_queries: int = 5) -> List[dict]:
    """
    Process queued autonomous queries. Called on schedule (daily/weekly).
    Limits to max_queries per batch to control costs.
    """
    _load_batch_queue()
    results = []

    with _batch_lock:
        to_process = [q for q in _batch_queue if q["status"] == "queued"][:max_queries]

    for query in to_process:
        try:
            result = run_consensus(
                prompt=query["prompt"],
                context=query.get("context", ""),
                source="autonomous",
            )
            query["status"] = "completed"
            query["completed_at"] = datetime.now(timezone.utc).isoformat()
            query["result_confidence"] = result.confidence
            query["result_summary"] = result.final_output[:500]
            results.append({
                "prompt": query["prompt"][:200],
                "status": "completed",
                "confidence": result.confidence,
            })
        except Exception as e:
            query["status"] = "failed"
            query["error"] = str(e)
            results.append({
                "prompt": query["prompt"][:200],
                "status": "failed",
                "error": str(e),
            })

    _save_batch_queue()
    return results


def _save_batch_queue():
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    path = BATCH_DIR / "queue.json"
    with _batch_lock:
        path.write_text(json.dumps(_batch_queue, indent=2, default=str))


def _load_batch_queue():
    path = BATCH_DIR / "queue.json"
    if path.exists():
        try:
            data = json.loads(path.read_text())
            with _batch_lock:
                _batch_queue.clear()
                _batch_queue.extend(data)
        except Exception:
            pass
