"""
Spindle Trust Score Aggregator

Normalizes scores from all Spindle/Grace layers into a 0-10 scale.
Enforces binary thresholds and triggers HITL handoffs when confidence drops.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TrustScoreAggregator:
    """
    Aggregates trust scores across the 9 layers of the Spindle architecture.
    Normalizes them to a 1-10 scale and triggers HITL handoffs if the 
    threshold (e.g., < 7.5) is breached.
    """
    
    def __init__(self, failure_threshold: float = 7.5):
        self.failure_threshold = failure_threshold
        # The 9 theoretical layers mapped to our systems
        self.layers = [
            "L1_Ingestion",
            "L2_Parse",
            "L3_LLM",
            "L4_Obfuscation",
            "L5_Bitmask",
            "L6_HDC",
            "L7_SMT",
            "L8_Consensus",
            "L9_Memory",
            "L10_Execution"
        ]

    def normalize_score(self, raw_score: float, max_raw: float = 1.0) -> float:
        """Normalize a raw score (e.g., 0.0-1.0) to a 0.0-10.0 scale."""
        if max_raw == 0:
            return 0.0
        normalized = (raw_score / max_raw) * 10.0
        return round(max(0.0, min(10.0, normalized)), 2)

    def evaluate_pipeline(self, layer_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluate all layers. Expects layer_scores to be on a 0-10 scale.
        If any layer is below the threshold, fails the pipeline and emits the appropriate signal.
        """
        failed_layers = []
        overall_score = 0.0
        valid_layers = 0
        
        for layer, score in layer_scores.items():
            valid_layers += 1
            overall_score += score
            if score < self.failure_threshold:
                failed_layers.append({"layer": layer, "score": score})
                
        if valid_layers > 0:
            overall_score = round(overall_score / valid_layers, 2)
            
        passed = len(failed_layers) == 0
        
        result = {
            "passed": passed,
            "overall_score": overall_score,
            "layer_scores": layer_scores,
            "failed_layers": failed_layers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not passed:
            self._trigger_handoff(result)
            
        return result

    def _trigger_handoff(self, evaluation_result: Dict[str, Any]):
        """
        Triggers a HITL handoff by emitting a Spindle handoff signal.
        """
        try:
            from cognitive.event_bus import publish
            
            # Determine the best signal code based on failures
            failed_layer_names = [f["layer"] for f in evaluation_result["failed_layers"]]
            
            signal_code = "GRACE-GV-012" # Default: Confidence score
            
            if "L7_SMT" in failed_layer_names:
                signal_code = "GRACE-HO-004" # Problem / SMT timeout
            elif "L3_LLM" in failed_layer_names:
                signal_code = "GRACE-CG-001" # Clarification requested
            elif len(failed_layer_names) > 2:
                signal_code = "GRACE-OP-012" # General handoff
                
            publish("spindle.hitl.handoff", {
                "signal": signal_code,
                "overall_score": evaluation_result["overall_score"],
                "failed_layers": evaluation_result["failed_layers"],
                "timestamp": evaluation_result["timestamp"],
                "requires_hitl": True
            }, source="trust_score_aggregator")
            
            logger.warning(
                f"[SPINDLE-HITL] Pipeline failed verification. Emitting {signal_code}. "
                f"Failed layers: {failed_layer_names}"
            )
            
        except ImportError:
            logger.error("[SPINDLE-HITL] Could not import event_bus to emit handoff signal.")
        except Exception as e:
            logger.error(f"[SPINDLE-HITL] Failed to emit handoff signal: {e}")

# Global singleton
_aggregator = None

def get_trust_aggregator(threshold: float = 7.5) -> TrustScoreAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = TrustScoreAggregator(failure_threshold=threshold)
    return _aggregator
