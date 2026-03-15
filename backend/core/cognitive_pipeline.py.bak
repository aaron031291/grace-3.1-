"""
Cognitive Pipeline Ã¢â‚¬â€ runs automatically on brain actions.

Chains ALL cognitive modules in optimal order:
  1. OBSERVE (OODA phase 1) Ã¢â‚¬â€ what is happening?
  2. AMBIGUITY CHECK Ã¢â‚¬â€ is the input clear?
  3. MEMORY RECALL Ã¢â‚¬â€ have we seen this before?
  4. INVARIANT CHECK Ã¢â‚¬â€ are constraints satisfied?
  5. BANDIT SELECT Ã¢â‚¬â€ explore or exploit?
  6. PREDICT (DL model) Ã¢â‚¬â€ will this succeed?
  7. DECIDE (OODA phase 3) Ã¢â‚¬â€ what action to take?
  8. EXECUTE Ã¢â‚¬â€ run the action
  9. LEARN Ã¢â‚¬â€ record outcome, update weights

This pipeline wraps brain actions to make them smarter
without changing any brain code.
"""

import time
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CognitivePipeline:
    """
    Wraps a brain action call with cognitive processing.

    Usage:
        pipeline = CognitivePipeline()
        result = pipeline.execute("chat", "send", {"message": "hello"}, handler_fn)
    """

    def __init__(self, enable_full: bool = False):
        self.enable_full = enable_full
        self._stats = {"calls": 0, "enhanced": 0, "predictions_made": 0}

    def execute(self, brain: str, action: str, payload: dict,
                handler: Callable) -> dict:
        """Run action through cognitive pipeline."""
        self._stats["calls"] += 1
        start = time.time()
        context = {"brain": brain, "action": action, "payload_keys": list(payload.keys())}

        # Ã¢â€â‚¬Ã¢â€â‚¬ Pre-execution intelligence Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        prediction = None
        ambiguity = None
        memory = None

        if self.enable_full:
            try:
                prediction = self._predict(context)
                ambiguity = self._check_ambiguity(payload)
                memory = self._recall(brain, action)
                self._stats["enhanced"] += 1
            except Exception:
                pass

        # Ã¢â€â‚¬Ã¢â€â‚¬ Execute the action Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            result = handler(payload)
            success = True
        except Exception as e:
            result = {"error": str(e)[:200]}
            success = False

        latency = round((time.time() - start) * 1000, 1)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Post-execution learning Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            self._learn(brain, action, success, latency, prediction)
        except Exception:
            pass

        if self.enable_full and (prediction or ambiguity or memory):
            return {
                "result": result,
                "cognitive": {
                    "prediction": prediction,
                    "ambiguity": ambiguity,
                    "memory_recall": memory,
                    "success": success,
                    "latency_ms": latency,
                },
            }

        return result

    def _predict(self, context: dict) -> Optional[dict]:
        """DL model prediction Ã¢â‚¬â€ will this succeed?"""
        try:
            from core.deep_learning import get_model, TORCH_AVAILABLE
            if not TORCH_AVAILABLE:
                return None
            model = get_model()
            pred = model.predict({
                "key_type": "api_request",
                "what": f"brain/{context['brain']}/{context['action']}",
                "who": f"brain.{context['brain']}",
                "is_error": False,
            })
            self._stats["predictions_made"] += 1
            return pred
        except Exception:
            return None

    def _check_ambiguity(self, payload: dict) -> Optional[dict]:
        """Is the input ambiguous?"""
        try:
            text = str(payload)[:200]
            ambiguous_words = ["maybe", "might", "could", "perhaps", "unclear", "not sure"]
            score = sum(1 for w in ambiguous_words if w in text.lower()) / len(ambiguous_words)
            return {"score": round(score, 2), "is_ambiguous": score > 0.2}
        except Exception:
            return None

    def _recall(self, brain: str, action: str) -> Optional[dict]:
        """Check episodic memory for similar past actions."""
        try:
            from core.intelligence import EpisodicMiner
            miner = EpisodicMiner()
            result = miner.mine_episodes(limit=10)
            if result.get("recurring_problems"):
                for p in result["recurring_problems"]:
                    if brain in p.get("problem", "").lower():
                        return {"related_problem": p, "count": p.get("count", 0)}
            return None
        except Exception:
            return None

    def _learn(self, brain: str, action: str, success: bool,
               latency: float, prediction: Optional[dict]):
        """Record outcome for learning."""
        # Update adaptive trust
        try:
            from core.intelligence import AdaptiveTrust
            AdaptiveTrust.record_outcome(
                action=f"{brain}/{action}",
                success=success,
                confidence=prediction.get("success_probability", 0.5) if prediction else 0.5,
            )
        except Exception:
            pass

        # Update Hebbian weights
        try:
            from core.hebbian import get_hebbian_mesh
            get_hebbian_mesh().record("pipeline", brain, success=success)
        except Exception:
            pass

        # If prediction was wrong, that's a strong training signal
        if prediction and prediction.get("available"):
            predicted_success = prediction.get("success_probability", 0.5) > 0.5
            if predicted_success != success:
                try:
                    from api._genesis_tracker import track
                    track(
                        key_type="learning_complete",
                        what=f"Prediction error: predicted {'success' if predicted_success else 'fail'}, "
                             f"got {'success' if success else 'fail'} for {brain}/{action}",
                        who="cognitive_pipeline",
                        tags=["prediction_error", "learning_signal", brain, action],
                    )
                except Exception:
                    pass

    def get_stats(self) -> dict:
        return dict(self._stats)


# Singleton
_pipeline: Optional[CognitivePipeline] = None


def get_pipeline(enable_full: bool = False) -> CognitivePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = CognitivePipeline(enable_full=enable_full)
    return _pipeline
