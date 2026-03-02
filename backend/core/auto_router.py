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
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

BRAIN_KEYWORDS = {
    "chat": ["chat", "message", "send", "talk", "conversation", "prompt", "ask", "say", "discuss"],
    "files": ["file", "folder", "directory", "read", "write", "create", "delete", "upload", "browse", "tree", "document", "search"],
    "govern": ["governance", "rule", "policy", "approve", "reject", "persona", "genesis", "key", "permission", "compliance"],
    "ai": ["consensus", "model", "predict", "train", "intelligence", "analyze", "diagnose", "test", "logic", "ooda", "ambiguity", "deep learning"],
    "system": ["health", "runtime", "status", "monitor", "probe", "trigger", "heal", "restart", "pause", "resume", "backup", "performance", "cpu", "memory", "synapse"],
    "data": ["source", "api", "web", "whitelist", "cache", "data", "import", "fetch"],
    "tasks": ["task", "schedule", "plan", "time", "deadline", "priority", "todo", "planner"],
    "code": ["code", "project", "generate", "codebase", "programming", "function", "class", "build", "compile", "deploy"],
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
    "files/browse": ["browse", "list", "directory"],
    "files/search": ["search", "find", "look for"],
    "govern/genesis_stats": ["genesis", "keys", "tracking"],
    "tasks/time_sense": ["time", "when", "schedule"],
}


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


def smart_call(query: str, payload: dict = None) -> dict:
    """
    Smart call — just describe what you want, Grace routes it.

    Usage:
        result = smart_call("what is the system health?")
        result = smart_call("send a message to chat", {"chat_id": 1, "message": "hi"})
    """
    brain, action, confidence = auto_route(query)

    from api.brain_api_v2 import call_brain
    result = call_brain(brain, action, payload or {})

    result["routing"] = {
        "query": query,
        "brain": brain,
        "action": action,
        "confidence": confidence,
        "auto_routed": True,
    }

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
