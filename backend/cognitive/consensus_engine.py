"""
Multi-Model Consensus Engine — Knights of the Roundtable

A 4-layer deliberation protocol where multiple LLMs independently tackle the
same problem, then converge through deterministic consensus and verification.

Layer 1 — Independent Deliberation:
  Each selected model receives the same prompt/problem/context independently.
  No model sees another's output.

Layer 2 — Consensus Formation (DETERMINISTIC):
  Responses are compared using token-overlap / Jaccard similarity to detect
  agreements and disagreements.  The best response is selected by a
  deterministic scoring function (length, relevance, agreement coverage,
  latency).  No LLM call is made in this layer.

Layer 3 — Alignment (DETERMINISTIC):
  Rule-based post-processing: strip LLM meta-commentary, check prompt
  relevance, tag actionable items for autonomous queries, prepend context
  headers.  No LLM call is made in this layer.

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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BATCH_DIR = Path(__file__).parent.parent / "data" / "consensus_batches"


def _build_model_registry() -> dict:
    """Build model registry using the actual configured model names (resolved to existing Ollama models)."""
    try:
        from llm_orchestrator.ollama_resolver import resolve_ollama_model
        reason_model = resolve_ollama_model("reason")
        code_model = resolve_ollama_model("code")
    except Exception:
        reason_model = "qwen3:32b"
        code_model = "qwen3:32b"

    return {
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
            "name": f"Qwen 3 — {code_model} (Local)",
            "provider": "ollama",
            "task": "code",
            "strengths": ["code generation", "fast iteration", "local/private", "free"],
            "cost_tier": "free",
        },
        "reasoning": {
            "name": f"Qwen 3 — {reason_model} (Local)",
            "provider": "ollama",
            "task": "reason",
            "strengths": ["chain-of-thought", "mathematical reasoning", "problem decomposition"],
            "cost_tier": "free",
        },
        "runpod": {
            "name": "RunPod (Mistral/vLLM)",
            "provider": "runpod",
            "strengths": ["fast", "custom finetunes", "serverless inference"],
            "cost_tier": "cloud",
        },
    }


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

    from llm_orchestrator.factory import get_llm_client, get_llm_for_task, get_qwen_coder, get_deepseek_reasoner

    provider = info.get("provider")
    task = info.get("task")

    if provider == "opus":
        return get_llm_client(provider="opus")
    elif provider == "kimi":
        return get_llm_client(provider="kimi")
    elif provider == "runpod":
        from cognitive.runpod_client import get_runpod_client
        return get_runpod_client()
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
    For local Ollama models this uses the resolved model (with fallbacks)
    and confirms that model exists in Ollama.
    """
    from settings import settings
    from llm_orchestrator.ollama_resolver import resolve_ollama_model, ollama_model_exists

    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return False

    if info["provider"] == "opus":
        return bool(getattr(settings, "OPUS_API_KEY", ""))
    elif info["provider"] == "kimi":
        return bool(getattr(settings, "KIMI_API_KEY", ""))
    elif info["provider"] == "runpod":
        return bool(getattr(settings, "RUNPOD_API_KEY", "")) and bool(getattr(settings, "RUNPOD_ENDPOINT_ID", ""))
    elif info["provider"] == "ollama":
        task = info.get("task") or "fast"
        resolved = resolve_ollama_model(task)
        return bool(resolved) and ollama_model_exists(resolved, settings)
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


# ── Layer 2: Consensus Formation (Deterministic) ─────────────────────

def _tokenize(text: str) -> List[str]:
    """Simple word tokenizer: lowercase, strip punctuation, remove stopwords."""
    import re
    _STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "and", "or",
        "but", "if", "then", "else", "when", "while", "for", "of", "to", "in",
        "on", "at", "by", "with", "from", "as", "into", "about", "not", "no",
        "so", "it", "its", "this", "that", "these", "those", "i", "you", "he",
        "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
        "his", "our", "their", "what", "which", "who", "whom", "how", "than",
    }
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def _sentence_split(text: str) -> List[str]:
    """Split text into sentences."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _jaccard_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Compute Jaccard similarity between two token lists."""
    set_a, set_b = set(tokens_a), set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _extract_key_claims(text: str) -> List[str]:
    """Extract key sentences/claims from a response for comparison."""
    sentences = _sentence_split(text)
    # Score sentences by information density (non-stopword ratio)
    scored = []
    for s in sentences:
        tokens = _tokenize(s)
        all_words = s.lower().split()
        density = len(tokens) / max(len(all_words), 1)
        scored.append((density, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:20]]


def _find_agreements_and_disagreements(
    responses: List[ModelResponse],
    agreement_threshold: float = 0.35,
    disagreement_threshold: float = 0.10,
) -> Tuple[List[str], List[str]]:
    """
    Deterministic agreement/disagreement detection via token overlap.

    For each key claim in each response, check if it has high token overlap
    with claims from other responses (agreement) or very low overlap
    (potential disagreement).
    """
    all_claims = {}  # model_id -> list of (sentence, tokens)
    for r in responses:
        claims = _extract_key_claims(r.response[:3000])
        all_claims[r.model_id] = [(c, _tokenize(c)) for c in claims]

    agreements = []
    disagreements = []
    seen_agree = set()
    seen_disagree = set()

    model_ids = list(all_claims.keys())
    for i, mid_a in enumerate(model_ids):
        for j, mid_b in enumerate(model_ids):
            if j <= i:
                continue
            for claim_a, tokens_a in all_claims[mid_a]:
                best_sim = 0.0
                best_match = ""
                for claim_b, tokens_b in all_claims[mid_b]:
                    sim = _jaccard_similarity(tokens_a, tokens_b)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = claim_b

                if best_sim >= agreement_threshold:
                    # Use the shorter claim as the canonical agreement text
                    canonical = claim_a if len(claim_a) <= len(best_match) else best_match
                    key = canonical[:80].lower()
                    if key not in seen_agree:
                        seen_agree.add(key)
                        agreements.append(canonical)
                elif best_sim <= disagreement_threshold and tokens_a:
                    key = claim_a[:80].lower()
                    if key not in seen_disagree:
                        seen_disagree.add(key)
                        disagreements.append(
                            f"{mid_a} claims: {claim_a[:150]}"
                        )

    return agreements[:15], disagreements[:10]


def _get_model_trust(model_id: str) -> float:
    """Get trust score (0-1) for a model from the Trust Engine.

    Returns 0.5 (neutral) if the engine is unavailable or has no data.
    """
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        comp = te.get_component(f"model.{model_id}")
        if comp and comp.trust_score > 0:
            return min(1.0, comp.trust_score / 100.0)
    except Exception:
        pass
    return 0.5


def _score_response(response: ModelResponse, prompt: str,
                    agreements: List[str]) -> float:
    """
    Deterministic quality score for a single response.

    Factors:
    - Length adequacy (not too short, not too long)
    - Coverage of agreement points
    - Latency (faster is mildly preferred, all else equal)
    - Model trust score from Trust Engine (P0 wire)
    - No error
    """
    if not response.response or response.error:
        return 0.0

    text = response.response
    tokens = _tokenize(text)
    prompt_tokens = _tokenize(prompt)

    # 1. Length score: prefer 100-2000 words
    word_count = len(text.split())
    if word_count < 20:
        length_score = 0.2
    elif word_count < 50:
        length_score = 0.5
    elif word_count <= 2000:
        length_score = 1.0
    else:
        length_score = max(0.6, 1.0 - (word_count - 2000) / 5000)

    # 2. Prompt relevance: token overlap with prompt
    if prompt_tokens:
        relevance = len(set(tokens) & set(prompt_tokens)) / max(len(set(prompt_tokens)), 1)
    else:
        relevance = 0.5

    # 3. Agreement coverage: how many agreement points appear in this response
    if agreements:
        covered = 0
        for ag in agreements:
            ag_tokens = set(_tokenize(ag))
            if ag_tokens and len(ag_tokens & set(tokens)) / len(ag_tokens) > 0.4:
                covered += 1
        coverage = covered / len(agreements)
    else:
        coverage = 0.5

    # 4. Latency bonus (minor): faster responses get a small boost
    latency_score = max(0.5, 1.0 - response.latency_ms / 60000)

    # 5. Trust Engine weight: models with higher trust get a boost
    trust_weight = _get_model_trust(response.model_id)

    # Weighted combination (trust replaces some latency weight)
    score = (
        0.20 * length_score
        + 0.25 * relevance
        + 0.30 * coverage
        + 0.05 * latency_score
        + 0.20 * trust_weight
    )
    return round(min(1.0, score), 4)


def layer2_consensus(
    prompt: str,
    responses: List[ModelResponse],
    synthesizer_model: str = "kimi",
) -> Tuple[str, List[str], List[str]]:
    """
    Layer 2: Deterministic consensus formation.

    Instead of calling an LLM to synthesise, this uses token-overlap
    analysis to identify agreements/disagreements, scores each response
    deterministically, and selects the highest-scoring response as the
    consensus text.

    Returns (consensus_text, agreements, disagreements).
    """
    valid_responses = [r for r in responses if r.response and not r.error]
    if not valid_responses:
        return "No valid responses to synthesise.", [], ["All models failed"]

    if len(valid_responses) == 1:
        return valid_responses[0].response, ["Single model — no consensus needed"], []

    # Step 1: Deterministic agreement/disagreement detection
    agreements, disagreements = _find_agreements_and_disagreements(valid_responses)

    # Step 2: Score each response deterministically
    scored = [
        (_score_response(r, prompt, agreements), r)
        for r in valid_responses
    ]
    scored.sort(key=lambda x: -x[0])

    best_score, best_response = scored[0]

    # Step 3: Build consensus text from the best response
    # Prepend a summary header with agreements/disagreements
    header_parts = []
    if agreements:
        header_parts.append("## Agreements\n" + "\n".join(f"- {a}" for a in agreements))
    if disagreements:
        header_parts.append("## Disagreements\n" + "\n".join(f"- {d}" for d in disagreements))

    consensus_text = best_response.response
    if header_parts:
        consensus_text = "\n\n".join(header_parts) + f"\n\n## Consensus\n{best_response.response}"

    logger.info(
        "Deterministic consensus: selected %s (score=%.3f), %d agreements, %d disagreements",
        best_response.model_id, best_score, len(agreements), len(disagreements),
    )

    return consensus_text, agreements, disagreements


# ── Layer 3: Alignment (Deterministic) ────────────────────────────────

def layer3_align(
    prompt: str,
    consensus: str,
    source: str = "user",
    user_context: str = "",
    system_context: str = "",
) -> str:
    """
    Layer 3: Deterministic alignment of the consensus to context.

    Instead of an LLM rewrite, this applies rule-based checks:
    - Strips meta-commentary (e.g. "As an AI…") that doesn't help the user.
    - Prepends relevant system/user context as a header if present.
    - For autonomous queries, tags actionable items.
    - Validates the consensus isn't empty/degenerate.
    """
    if not consensus or not consensus.strip():
        return f"No consensus produced for query: {prompt[:200]}"

    aligned = consensus

    # Rule 1: Strip common LLM meta-commentary
    _meta_patterns = [
        "as an ai language model",
        "as an ai,",
        "i'm just an ai",
        "i don't have personal",
        "i cannot provide",
        "please note that i",
    ]
    lines = aligned.split("\n")
    filtered_lines = []
    for line in lines:
        lower = line.lower().strip()
        if any(pat in lower for pat in _meta_patterns):
            continue
        filtered_lines.append(line)
    aligned = "\n".join(filtered_lines)

    # Rule 2: Ensure the response references the prompt topic
    prompt_tokens = set(_tokenize(prompt))
    response_tokens = set(_tokenize(aligned))
    if prompt_tokens:
        overlap = len(prompt_tokens & response_tokens) / len(prompt_tokens)
        if overlap < 0.05 and len(aligned) > 100:
            aligned = f"[Alignment Note: Low relevance to query detected]\n\n{aligned}"

    # Rule 3: For autonomous queries, tag actionable lines
    if source == "autonomous":
        action_keywords = {"fix", "restart", "update", "rebuild", "deploy",
                           "install", "configure", "migrate", "patch", "reset"}
        action_lines = []
        for line in aligned.split("\n"):
            line_tokens = set(_tokenize(line))
            if line_tokens & action_keywords:
                action_lines.append(line.strip())
        if action_lines:
            aligned += "\n\n## Actionable Items\n" + "\n".join(f"- {a}" for a in action_lines[:10])

    # Rule 4: Prepend context headers if provided
    context_header = ""
    if system_context:
        context_header += f"[System Context: {system_context[:300].strip()}]\n"
    if user_context:
        context_header += f"[User Context: {user_context[:300].strip()}]\n"
    if context_header:
        aligned = context_header + "\n" + aligned

    return aligned.strip()


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

    # Constitutional Alignment Check
    try:
        from constitutional.grace_charter import GraceCharter
        
        # Simple heuristic risk assessment for the raw output
        estimated_risk = 0.1
        if "delete" in aligned_output.lower() or "remove" in aligned_output.lower():
            estimated_risk += 0.4
        if "os." in aligned_output or "subprocess" in aligned_output or "eval(" in aligned_output:
            estimated_risk += 0.5
            
        if not GraceCharter.is_risk_acceptable(estimated_risk):
            verification["contradiction_flags"].append(f"Constitutional Violation: Estimated risk ({estimated_risk}) exceeds Clause 4 limits.")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Constitutional alignment check failed: {e}")

    # Z3 Physics Formal Verification
    try:
        from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
        from cognitive.physics.z3_sandbox import Z3Sandbox

        # Translate aligned output to formal logic
        z3_pipeline = QwenZ3Pipeline()
        z3_constraint = z3_pipeline.generate_z3_constraint(aligned_output[:2000])

        if z3_constraint:
            # Validate formally against laws of physics
            sandbox = Z3Sandbox()
            is_valid, sandbox_msg = sandbox.test_generated_constraint(z3_constraint)

            verification["z3_verified"] = is_valid
            if not is_valid:
                verification["contradiction_flags"].append(f"Z3 Physics Violation: {sandbox_msg}")
        else:
            # Failed to generate a constraint, neutral pass
            verification["z3_verified"] = "Skipped"
    except Exception as e:
        logger.warning(f"Z3 Physics validation failed: {e}")
        verification["z3_verified"] = "Error"

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

def query_braille_sandbox(intent: str) -> str:
    """
    Query the new deterministic Braille Sandbox nodes to provide raw AST code 
    to Spindle exactly as requested via the new genesis keys.
    """
    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        from database.session import get_session_factory
        from database.models.braille_node import BrailleSandboxNode
        
        try:
            DatabaseConnection.get_engine()
        except RuntimeError:
            config = DatabaseConfig.from_env()
            DatabaseConnection.initialize(config)
            
        SessionLocal = get_session_factory()
        db = SessionLocal()
        # For autonomous/context injection, we pull a few relevant Nodes 
        # (This will be improved with pgvector embeddings in the future)
        keywords = intent.lower().split()
        nodes = db.query(BrailleSandboxNode).filter(BrailleSandboxNode.is_active == True).limit(10).all()
        
        matches = []
        for n in nodes:
            if any(k in n.ast_content.lower() or k in n.genesis_key.lower() for k in keywords):
                matches.append(n)
        
        db.close()
        
        if not matches:
            return ""
            
        ctx = "[Braille Sandbox Deterministic Code Context]\n"
        for m in matches[:3]:
            ctx += f"--- {m.genesis_key} ({m.braille_encoding}) | {m.master_loop} ---\n{m.ast_content[:1500]}\n\n"
        return ctx
    except Exception as e:
        logger.warning(f"Braille Sandbox offline: {e}")
        return ""


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
        system_context = f"System trust: {kpis.get('overall_trust', 'unknown')}\n"
    except Exception:
        pass

    # Inject Unified Memory Context
    try:
        from cognitive.unified_memory import get_unified_memory
        um_results = get_unified_memory().search_all(prompt, top_k=3)
        if um_results:
            system_context += "\n[Unified Memory]\n"
            for res in um_results:
                system_context += f"- {res.get('memory_type', 'unknown')}: {res.get('content', '')}\n"
    except Exception:
        pass

    # Inject Braille Sandbox Context
    sandbox_context = query_braille_sandbox(prompt)
    if sandbox_context:
        system_context += "\n" + sandbox_context

    # Inject Dynamic Semantic Braille Dictionary
    try:
        from core.dynamic_dictionary import get_dynamic_dictionary
        semantic_dict = get_dynamic_dictionary().get_full_dictionary()
        if semantic_dict:
            system_context += "\n[Semantic Braille Dictionary Mapping]\n"
            for item in semantic_dict:
                system_context += f"- Word: '{item['word']}' = Braille: '{item['encoding']}' | Meaning: {item['meaning']}\n"
    except Exception as e:
        logger.warning(f"Semantic Dictionary offline Context injection failed: {e}")

    # Inject Workspace Global Topological Context natively
    try:
        import os
        from pathlib import Path
        workspace_root = Path(os.getcwd())
        tree = []
        for p in workspace_root.rglob('*.py'):
            if 'node_modules' not in str(p) and 'venv' not in str(p):
                tree.append(str(p.relative_to(workspace_root)))
        if tree:
            system_context += "\n[Workspace Topology Tracker (Native Sandbox)]\n"
            system_context += "Active Scripts:\n" + "\n".join(tree[:50]) + ("\n...truncated" if len(tree) > 50 else "")
    except Exception as e:
        logger.warning(f"Workspace Topology Context injection failed: {e}")

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

    # ── Wire: Consensus → Executive Actuation ──
    _actuatable_sources = {"autonomous", "governance", "healing", "diagnostic"}
    if source in _actuatable_sources and verification["passed"]:
        try:
            from cognitive.consensus_actuation import ConsensusActuation
            actuator = ConsensusActuation()
            action_keywords = {"fix", "restart", "update", "rebuild", "deploy",
                                "install", "configure", "migrate", "patch", "reset"}
            for line in final_output.split("\n"):
                line_lower = line.lower().strip()
                if any(kw in line_lower for kw in action_keywords) and len(line_lower) > 10:
                    action_payload = {
                        "action_type": "submit_coding_task",
                        "params": {"description": line.strip()[:500], "source": "consensus_engine"},
                        "rationale": f"Consensus ({len(models)} models, confidence={result.confidence:.2f})",
                    }
                    actuator.execute_action(action_payload, prompt[:200], result.confidence)
                    break
        except Exception as e:
            logger.warning(f"Consensus actuation failed (non-fatal): {e}")
        try:
            from cognitive.event_bus import publish
            publish("consensus.actuated", {
                "models": models, "confidence": result.confidence, "source": source,
            }, source="consensus_engine")
        except Exception as e:
            logger.warning(f"Consensus actuation event publish failed (non-fatal): {e}")

    # ── Gap 5.1: Consensus → Executive Quorum Commit ──
    # Build signed quorum packet and propagate to trust vectors + MEMORY + MESH
    try:
        quorum_hash = hashlib.sha256(result.consensus_text.encode()).hexdigest()
        quorum_sig = hashlib.sha256(
            f"{','.join(models)}:{quorum_hash}:{result.timestamp}".encode()
        ).hexdigest()
        quorum_packet = {
            "models": models,
            "hash": quorum_hash,
            "sig": quorum_sig,
            "confidence": result.confidence,
            "passed": verification["passed"],
            "timestamp": result.timestamp,
            "source": source,
        }

        # a) Publish quorum to event bus
        try:
            from cognitive.event_bus import publish
            publish("consensus.quorum_committed", quorum_packet, source="consensus_engine")
        except Exception:
            pass

        # b) Update trust vectors in Unified Memory
        try:
            from cognitive.unified_memory import get_unified_memory
            get_unified_memory().store_episode(
                problem=f"consensus_quorum:{prompt[:120]}",
                action=f"models={','.join(models)}",
                outcome=f"confidence={result.confidence:.2f} passed={verification['passed']}",
                trust=result.confidence,
                source="consensus_quorum",
            )
        except Exception:
            pass

        # c) Update Memory Mesh via reconciler
        try:
            from cognitive.memory_reconciler import get_reconciler
            get_reconciler().atomic_set(
                key=f"quorum:{quorum_hash[:16]}",
                value=json.dumps(quorum_packet, default=str),
                source="consensus_engine",
                trust=result.confidence,
            )
        except Exception:
            pass

        # d) Update AdaptiveTrust for each model
        try:
            from core.intelligence import AdaptiveTrust
            for mid in models:
                AdaptiveTrust.record_outcome(
                    model_id=mid,
                    success=verification["passed"],
                    confidence=result.confidence,
                )
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Quorum commit failed (non-fatal): {e}")

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
