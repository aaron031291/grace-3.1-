"""
Memory Injector — connects LLMs to ALL memory systems.

Before every LLM call, this module builds a rich context block
containing unified memory, Genesis patterns, trust scores,
governance rules, episodic recalls, and knowledge gaps.

This is THE missing piece. Without it, models fly blind.
"""

import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8000


def build_llm_context(task: str = "", project: str = "", session_id: str = "") -> str:
    """
    Build a complete context block for LLM injection.
    This gets prepended to every LLM system prompt.
    """
    parts = []
    char_budget = MAX_CONTEXT_CHARS

    # 1. Governance rules (highest priority — these are LAW)
    rules = _get_governance_rules()
    if rules:
        parts.append(f"[GOVERNANCE RULES — MANDATORY]\n{rules[:2000]}")
        char_budget -= min(len(rules), 2000)

    # 2. Trust scores (which models are reliable right now)
    trust = _get_trust_scores()
    if trust:
        parts.append(f"[MODEL TRUST SCORES]\n{trust}")
        char_budget -= len(trust)

    # 3. Episodic memory (similar past problems and what worked)
    if task:
        episodes = _get_episodic_context(task)
        if episodes:
            parts.append(f"[PAST EXPERIENCE]\n{episodes[:1500]}")
            char_budget -= min(len(episodes), 1500)

    # 4. Genesis key patterns (what happened in last 24h)
    patterns = _get_genesis_patterns()
    if patterns:
        parts.append(f"[SYSTEM ACTIVITY — LAST 24H]\n{patterns[:1000]}")
        char_budget -= min(len(patterns), 1000)

    # 5. Knowledge gaps (what Grace doesn't know yet)
    gaps = _get_knowledge_gaps()
    if gaps:
        parts.append(f"[KNOWLEDGE GAPS]\n{gaps[:500]}")
        char_budget -= min(len(gaps), 500)

    # 6. DL model prediction (success probability for this task)
    if task:
        prediction = _get_dl_prediction(task)
        if prediction:
            parts.append(f"[AI PREDICTION]\n{prediction}")

    # 7. Hebbian weights (strongest brain connections)
    hebbian = _get_hebbian_context()
    if hebbian:
        parts.append(f"[BRAIN SYNAPSE STRENGTHS]\n{hebbian}")

    # 8. Self-mirror observation
    mirror = _get_mirror_observation()
    if mirror:
        parts.append(f"[SELF-OBSERVATION]\n{mirror}")

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)


def _get_governance_rules() -> str:
    try:
        from core.services.govern_service import list_rules, get_persona
        rules = list_rules()
        persona = get_persona()
        parts = []
        if persona.get("personal"):
            parts.append(f"Communication style: {persona['personal'][:200]}")
        if persona.get("professional"):
            parts.append(f"Professional style: {persona['professional'][:200]}")
        docs = rules.get("documents", [])
        if docs:
            parts.append(f"Active governance documents: {len(docs)}")
            for d in docs[:5]:
                parts.append(f"  - {d.get('filename', '?')} ({d.get('category', '?')})")
        return "\n".join(parts) if parts else ""
    except Exception:
        return ""


def _get_trust_scores() -> str:
    try:
        from core.intelligence import AdaptiveTrust
        trust = AdaptiveTrust.get_all_trust()
        models = trust.get("models", {})
        if models:
            return "\n".join(f"  {m}: {s:.2f}" for m, s in models.items())
        return ""
    except Exception:
        return ""


def _get_episodic_context(task: str) -> str:
    try:
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicBuffer
        with session_scope() as s:
            buf = EpisodicBuffer(s)
            episodes = buf.recall_similar(task, k=3, min_trust=0.5)
            if not episodes:
                return ""
            parts = []
            for ep in episodes:
                problem = ep.problem[:100] if isinstance(ep.problem, str) else str(ep.problem)[:100]
                outcome = ep.outcome[:100] if isinstance(ep.outcome, str) else str(ep.outcome)[:100]
                parts.append(f"  Past: {problem} → {outcome} (trust={ep.trust_score:.2f})")
            return "\n".join(parts)
    except Exception:
        return ""


def _get_genesis_patterns() -> str:
    try:
        from core.intelligence import GenesisKeyMiner
        miner = GenesisKeyMiner()
        patterns = miner.mine_patterns(hours=24, limit=500)
        parts = []
        keys = patterns.get("keys_analyzed", 0)
        parts.append(f"Operations in last 24h: {keys}")
        errors = patterns.get("error_clusters", [])
        if errors:
            parts.append(f"Error clusters: {len(errors)}")
            for e in errors[:3]:
                parts.append(f"  - {e.get('error_type', '?')}: {e.get('count', 0)} occurrences")
        repeated = patterns.get("repeated_failures", [])
        if repeated:
            parts.append(f"Repeated failures: {', '.join(r.get('pattern', '?')[:30] for r in repeated[:3])}")
        return "\n".join(parts)
    except Exception:
        return ""


def _get_knowledge_gaps() -> str:
    try:
        from core.cognitive_mesh import CognitiveMesh
        gaps = CognitiveMesh.analyze_knowledge_gaps()
        if not gaps or not gaps.get("knowledge_gaps"):
            return ""
        gap_list = gaps.get("knowledge_gaps", [])
        if not gap_list:
            return ""
        return f"Grace has {len(gap_list)} knowledge gaps in: " + ", ".join(
            g.get("topic", "?")[:20] for g in gap_list[:5] if isinstance(g, dict)
        )
    except Exception:
        return ""


def _get_dl_prediction(task: str) -> str:
    try:
        from core.deep_learning import get_model, TORCH_AVAILABLE
        if not TORCH_AVAILABLE:
            return ""
        model = get_model()
        pred = model.predict({"key_type": "code_change", "what": task[:60], "who": "user", "is_error": False})
        if pred.get("available"):
            return (f"Success probability: {pred['success_probability']:.0%}\n"
                    f"Risk component: {pred.get('risky_component', '?')}\n"
                    f"Predicted trust: {pred.get('predicted_trust', 0):.2f}")
        return ""
    except Exception:
        return ""


def _get_hebbian_context() -> str:
    try:
        from core.hebbian import get_hebbian_mesh
        strongest = get_hebbian_mesh().get_strongest(5)
        if not strongest:
            return ""
        return "\n".join(
            f"  {s['source']}→{s['target']}: weight={s['weight']:.2f} ({s['calls']} calls)"
            for s in strongest
        )
    except Exception:
        return ""


def _get_mirror_observation() -> str:
    try:
        from core.awareness.self_model import SelfModel
        model = SelfModel()
        ctx = model.now()
        return f"Period: {ctx.get('period', '?')}, Business hours: {ctx.get('is_business_hours', '?')}"
    except Exception:
        return ""
