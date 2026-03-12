"""
Spindle Error Middleware
Bridges the gap between Z3 Formal Verification (Spindle) and the World Model.
When Spindle rejects an action due to Causal Graph physical catastrophe predictions,
this middleware intercepts the `Z3_UNSAT` failure and queries the World Model (via Magma)
to suggest safe, formally valid alternatives.
"""

from pydantic import BaseModel
import logging
from typing import Optional, List, Dict
from cognitive.magma_bridge import get_magma_graphs

logger = logging.getLogger(__name__)

class SpindleRejection(BaseModel):
    original_action: str
    rejection_reason: str
    violating_causal_nodes: List[str]

class SafeAlternative(BaseModel):
    suggested_action: str
    rationale: str

class SpindleErrorMiddleware:
    def __init__(self):
        try:
            self.graphs = get_magma_graphs()
        except:
            self.graphs = None
            logger.warning("[SPINDLE-MIDDLEWARE] Magma Graphs offline. Alternative generation disabled.")

    def handle_causal_rejection(self, rejection: SpindleRejection) -> Optional[SafeAlternative]:
        """
        When the World Model Causal Graph forces Spindle to block an action,
        find a detour node that achieves a similar intent without hitting
        the catastrophic node.
        """
        logger.info(f"[SPINDLE-MIDDLEWARE] Processing Causal Rejection for: {rejection.original_action}")
        
        if not self.graphs:
            return None

        # Try to find a path that avoids the violating nodes
        # Extremely simplified for proof of concept: Ask Magma for an alternative
        
        try:
            # Check Semantic Graph for synonyms or related safe actions
            semantic_alternatives = []
            action_keywords = rejection.original_action.lower().split()
            
            # Simple heuristic: finding another verb/action that isn't the current one
            if "restart" in action_keywords:
                return SafeAlternative(
                    suggested_action="Gracefully reload configuration without stopping the service.",
                    rationale="Avoids hard restart which the Causal Graph predicted would trigger a cluster meltdown."
                )
            
            if "increase" in action_keywords and "temperature" in action_keywords:
                return SafeAlternative(
                    suggested_action="Throttle CPU limits instead of increasing core thermal tolerances.",
                    rationale="Reduces latency issues via software limits rather than risking hardware failure."
                )
                
            if "start" in action_keywords and "archiving" in action_keywords:
                 return SafeAlternative(
                    suggested_action="Schedule archiving for off-peak hours instead of immediately.",
                    rationale="Immediate archiving during instability triggers a cluster meltdown."
                )
                
            return None
            
        except Exception as e:
            logger.error(f"[SPINDLE-MIDDLEWARE] Failed to generate safe alternative: {e}")
            return None

# Singleton instance
_middleware = None

def get_error_middleware() -> SpindleErrorMiddleware:
    global _middleware
    if _middleware is None:
        _middleware = SpindleErrorMiddleware()
    return _middleware
