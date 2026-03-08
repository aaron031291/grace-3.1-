"""
Auto-Router — Grace decides which brain to call.

Instead of the user specifying brain + action, they just describe
what they want and Grace routes to the optimal brain based on:
  1. Keyword matching against brain action descriptions
  2. Hebbian synaptic weights (prefer brains that succeed)
  3. Historical success rates per action
  4. Adaptive trust scores
"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

BRAIN_KEYWORDS = {
    "chat": ["chat", "message", "send", "talk", "conversation", "prompt", "say", "discuss"],
    "files": ["file", "folder", "directory", "read", "write", "create", "delete", "upload", "browse", "tree", "document", "search"],
    "govern": ["governance", "rule", "policy", "approve", "reject", "persona", "genesis", "key", "permission", "compliance"],
    "ai": ["consensus", "model", "models", "llm", "predict", "train", "intelligence", "analyze", "diagnose", "test", "logic", "ooda", "ambiguity", "deep learning"],
    "system": ["health", "runtime", "status", "monitor", "probe", "trigger", "heal", "restart", "pause", "resume", "backup", "performance", "cpu", "memory", "synapse", "embedding", "architecture", "component", "dependency", "blueprint", "trace", "schema", "brains", "apis", "models", "llm", "database", "databases", "graphs", "paths", "way"],
    "data": ["source", "api", "web", "whitelist", "cache", "data", "import", "fetch"],
    "tasks": ["task", "schedule", "plan", "time", "deadline", "priority", "todo", "planner"],
    "code": ["code", "project", "generate", "codebase", "programming", "function", "class", "build", "compile", "deploy"],
    "deterministic": ["deterministic", "scan", "ast", "syntax", "verify", "no llm", "rule only", "phase 0", "parse", "import check"],
}

ACTION_KEYWORDS = {
    "chat/send": ["send", "message", "chat", "talk"],
    "chat/consensus": ["consensus", "all models", "roundtable", "deliberate"],
    "ai/dl_predict": ["predict", "forecast", "what will happen"],
    "ai/dl_train": ["train", "learn", "fit", "model"],
    "ai/cognitive_report": ["report", "cognitive", "full analysis"],
    "ai/ooda": ["observe", "orient", "decide", "act", "ooda"],
    "system/health_map": ["health", "status", "components", "map"],
    "system/runtime": ["runtime", "uptime", "running"],
    "system/probe": ["probe", "test", "check", "alive"],
    "system/auto_cycle": ["autonomous", "ouroboros", "self-heal", "cycle"],
    "system/intelligence": ["intelligence", "report", "analysis"],
    "system/embedding_config": ["embedding", "embedding model", "what embedding", "vector model", "which model for embeddings"],
    "system/architecture_explain": ["what does component", "explain component", "what is pipeline", "what does trust_engine do", "component does"],
    "system/architecture_find": ["what can handle", "which component", "capability", "who handles", "trace capability"],
    "system/architecture_connected": ["trace path", "path from", "connected", "dependency graph", "data flow from", "how connected"],
    "system/architecture_diagnose": ["architecture diagnose", "bottlenecks", "isolated modules", "dependency issues"],
    "system/architecture_map": ["full architecture", "architecture map", "all components", "component map", "blueprint"],
    "system/brain_directory": ["brains", "apis", "api map", "list actions", "what brains", "brain directory", "all endpoints", "what can i call"],
    "system/models_summary": ["models summary", "all models", "llm models", "what models", "embedding and llm", "which llm", "which models", "what llm", "list llm", "list models", "available llm", "available models", "llm in the system", "models in the system", "what embedding"],
    "system/schema_info": ["schema", "databases", "database", "db config", "what database", "qdrant", "storage", "tables"],
    "system/graphs_info": ["graphs", "graph", "component graph", "vector store", "magma"],
    "system/deterministic_first_loop": ["deterministic first", "phase 0", "genesis probe ast", "deterministic loop", "probe then fix", "determinism before llm"],
    "deterministic/scan": ["deterministic scan", "ast scan", "syntax check", "rule only scan", "parse check"],
    "deterministic/fix": ["deterministic fix", "auto fix", "rule fix", "ast fix"],
    "deterministic/first_loop": ["deterministic first loop", "phase 0 loop", "deterministic loop"],
    "files/browse": ["browse", "list", "directory"],
    "files/search": ["search", "find", "look for"],
    "govern/genesis_stats": ["genesis", "keys", "tracking"],
    "govern/coding_contract": ["coding contract", "governance coding contract", "governance contract", "rules for coding", "what rules apply to code"],
    "tasks/time_sense": ["time", "when", "schedule"],
}


def get_nearest_actions(query: str, top_k: int = 5) -> List[dict]:
    """
    Neighbor-by-neighbor: score every (brain, action) by keyword overlap with query.
    When NLP routing has low confidence, suggest these as "did you mean?" options.
    """
    query_lower = query.lower()
    scored = []
    for action_path, keywords in ACTION_KEYWORDS.items():
        brain, action = action_path.split("/", 1)
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scored.append({"brain": brain, "action": action, "path": action_path, "score": score})
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def auto_route(query: str) -> Tuple[str, str, float]:
    """
    Determine the best brain + action for a natural language query.

    Returns: (brain, action, confidence)
    """
    query_lower = query.lower()
    words = set(re.findall(r'\w+', query_lower))

    # Score each brain
    brain_scores = {}
    for brain, keywords in BRAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        # Boost from Hebbian weights
        try:
            from core.hebbian import get_hebbian_mesh
            mesh = get_hebbian_mesh()
            hebbian_boost = mesh.get_weight("external", brain) - 0.5
            score += hebbian_boost * 2
        except Exception:
            pass
        # Boost from adaptive trust
        try:
            from core.intelligence import AdaptiveTrust
            trust = AdaptiveTrust.get_model_trust(brain)
            score += (trust - 0.5) * 0.5
        except Exception:
            pass
        brain_scores[brain] = score

    best_brain = max(brain_scores, key=brain_scores.get)
    brain_confidence = brain_scores[best_brain]

    # Score actions within the best brain
    action_scores = {}
    for action_path, keywords in ACTION_KEYWORDS.items():
        if action_path.startswith(best_brain + "/"):
            action = action_path.split("/")[1]
            score = sum(1 for kw in keywords if kw in query_lower)
            action_scores[action] = score

    if action_scores:
        best_action = max(action_scores, key=action_scores.get)
    else:
        # Default to first action in the brain
        try:
            from api.brain_api_v2 import _build_directory
            d = _build_directory()
            best_action = d[best_brain]["actions"][0]
        except Exception:
            best_action = "list"

    # Confidence: normalize to 0-1
    max_possible = max(len(kws) for kws in BRAIN_KEYWORDS.values())
    confidence = min(1.0, brain_confidence / max(max_possible, 1))

    return best_brain, best_action, round(confidence, 3)


# When confidence is below this, include nearest_actions so UI can suggest "did you mean?"
LOW_CONFIDENCE_THRESHOLD = 0.25


# Queries that should never go to chat/send (Ask tab architecture questions)
_ARCHITECTURE_HINTS = ("llm", "model", "models", "embedding", "architecture", "schema", "brain", "api", "database", "graph", "component", "path", "trace", "which ", "what ", "list ", "available ")


def _looks_like_architecture_query(query: str) -> bool:
    q = query.lower()
    return any(h in q for h in _ARCHITECTURE_HINTS)


def smart_call(query: str, payload: dict = None) -> dict:
    """
    Smart call — just describe what you want, Grace routes it.
    When NLP match is weak (low confidence), adds nearest_actions: neighbor-by-neighbor
    suggestions so the UI can show "Did you mean: ...?"
    If routed to chat/send without chat_id and query looks like architecture, retry with system/models_summary.
    """
    brain, action, confidence = auto_route(query)
    payload = payload or {}

    from api.brain_api_v2 import call_brain
    result = call_brain(brain, action, payload)

    # Fallback: Ask-tab style query routed to chat/send without chat_id → use models_summary instead
    # (Any error from chat/send when no chat_id and query looks architectural — don't require "chat_id" in error message)
    if (
        brain == "chat"
        and action == "send"
        and not payload.get("chat_id")
        and _looks_like_architecture_query(query)
        and result.get("error")
    ):
        result = call_brain("system", "models_summary", {})
        result["routing"] = {
            "query": query,
            "brain": "system",
            "action": "models_summary",
            "confidence": confidence,
            "auto_routed": True,
            "fallback": "chat/send required chat_id; rerouted to system/models_summary",
        }
        try:
            from api._genesis_tracker import track
            track(
                key_type="api_request",
                what=f"Ask fallback: '{query[:50]}' → system/models_summary",
                who="auto_router",
                tags=["auto-route", "ask-fallback", "system", "models_summary"],
            )
        except Exception:
            pass
        return result

    result["routing"] = {
        "query": query,
        "brain": brain,
        "action": action,
        "confidence": confidence,
        "auto_routed": True,
    }

    # Neighbor-by-neighbor: if confidence is low, suggest nearest components by keyword overlap
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        result["routing"]["nearest_actions"] = get_nearest_actions(query, top_k=6)
        result["routing"]["low_confidence_hint"] = "No strong match. Try one of the suggested actions below, or rephrase."

    try:
        from api._genesis_tracker import track
        track(
            key_type="api_request",
            what=f"Auto-routed: '{query[:50]}' → {brain}/{action} (conf={confidence})",
            who="auto_router",
            tags=["auto-route", brain, action],
        )
    except Exception:
        pass

    return result
