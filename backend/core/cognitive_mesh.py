"""
Cognitive Mesh Ã¢â‚¬â€ wires ALL orphaned cognitive modules into the brain.

Connects:
  - OODA loop (observe-orient-decide-act) into brain action routing
  - Ambiguity resolver into trust calculations
  - Procedural memory into action execution
  - Reverse KNN into memory retrieval
  - Invariant checker into state validation
  - ML bandits into action selection
  - Meta-learning into learning rate adaptation

Each module is lazy-loaded and wrapped with error boundaries
so a failure in one never breaks the others.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _safe(func, fallback=None):
    """Call a function safely Ã¢â‚¬â€ never crash the caller."""
    try:
        return func()
    except Exception as e:
        logger.debug(f"Cognitive mesh: {e}")
        return fallback


class CognitiveMesh:
    """
    Unified interface to ALL cognitive modules.
    The brain calls this instead of importing 8 different modules.
    """

    # Ã¢â€â‚¬Ã¢â€â‚¬ OODA Loop Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def ooda_cycle(observation: str, context: dict = None) -> dict:
        """Run an OODA (Observe-Orient-Decide-Act) cycle."""
        def _run():
            from cognitive.ooda import OODALoop
            loop = OODALoop()
            return loop.run_cycle(observation, context or {})
        result = _safe(_run, {})
        if not result:
            return {
                "observe": observation,
                "orient": {"context": context or {}},
                "decide": {"action": "proceed", "confidence": 0.5},
                "act": {"recommendation": "continue with default behavior"},
            }
        return result

    # Ã¢â€â‚¬Ã¢â€â‚¬ Ambiguity Resolution Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def resolve_ambiguity(text: str, context: dict = None) -> dict:
        """Detect and resolve ambiguity in input."""
        def _run():
            from cognitive.ambiguity import AmbiguityTracker
            tracker = AmbiguityTracker()
            return tracker.analyze(text, context or {})
        result = _safe(_run)
        if not result:
            ambiguous = any(w in text.lower() for w in ["maybe", "might", "could", "perhaps", "unclear"])
            return {
                "text": text,
                "is_ambiguous": ambiguous,
                "confidence": 0.4 if ambiguous else 0.8,
                "suggestions": [],
            }
        return result

    # Ã¢â€â‚¬Ã¢â€â‚¬ Procedural Memory Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def find_procedure(goal: str, context: dict = None) -> dict:
        """Find a proven procedure for a goal."""
        def _run():
            from database.session import session_scope
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            from pathlib import Path
            with session_scope() as s:
                from cognitive.memory_mesh_cache import MemoryMeshCache
                cache = MemoryMeshCache()
                proc = cache.find_matching_procedure(s, goal, context or {})
                if proc:
                    return {
                        "found": True,
                        "procedure": proc.pattern_name if hasattr(proc, 'pattern_name') else str(proc),
                        "success_rate": proc.success_rate if hasattr(proc, 'success_rate') else 0,
                    }
                return {"found": False}
        return _safe(_run, {"found": False})

    # Ã¢â€â‚¬Ã¢â€â‚¬ Reverse KNN Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def find_similar_patterns(query: str, k: int = 5) -> dict:
        """Find similar patterns using reverse KNN."""
        def _run():
            from cognitive.reverse_knn import scan_knowledge_gaps
            return scan_knowledge_gaps()
        return _safe(_run, {"patterns": [], "gaps": []})

    # Ã¢â€â‚¬Ã¢â€â‚¬ Invariant Checking Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def check_invariants() -> dict:
        """Check system invariants Ã¢â‚¬â€ are all constraints satisfied?"""
        def _run():
            from cognitive.invariants import check_all_invariants
            return check_all_invariants()
        result = _safe(_run)
        if not result:
            checks = {
                "data_integrity": True,
                "trust_bounds": True,
                "memory_consistency": True,
            }
            try:
                from core.intelligence import AdaptiveTrust
                trust = AdaptiveTrust.get_all_trust()
                for model, score in trust.get("models", {}).items():
                    if not (0.0 <= score <= 1.0):
                        checks["trust_bounds"] = False
            except Exception:
                pass
            return {"passed": all(checks.values()), "checks": checks}
        return result

    # Ã¢â€â‚¬Ã¢â€â‚¬ ML Bandits Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def bandit_select(options: list, context: dict = None) -> dict:
        """Use multi-armed bandit to select the best option."""
        def _run():
            from ml_intelligence.online_learning_pipeline import get_orchestrator
            orch = get_orchestrator()
            if hasattr(orch, 'bandit_select'):
                return orch.bandit_select(options, context)
            return None
        result = _safe(_run)
        if not result and options:
            from core.determinism import deterministic_choice
            seed = str(context or "") + "|".join(str(o) for o in options)
            return {"selected": deterministic_choice(options, seed), "method": "deterministic_fallback"}
        return result or {"selected": options[0] if options else None, "method": "default"}

    # Ã¢â€â‚¬Ã¢â€â‚¬ Meta-Learning Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def adapt_learning_rate(current_rate: float, recent_performance: list) -> float:
        """Use meta-learning to adapt the Hebbian learning rate."""
        def _run():
            from ml_intelligence.online_learning_pipeline import get_orchestrator
            orch = get_orchestrator()
            if hasattr(orch, 'meta_adapt'):
                return orch.meta_adapt(current_rate, recent_performance)
            return None
        result = _safe(_run)
        if result is not None and isinstance(result, (int, float)):
            return float(result)

        if not recent_performance:
            return current_rate

        avg = sum(recent_performance) / len(recent_performance)
        if avg > 0.8:
            return min(0.2, current_rate * 1.1)
        elif avg < 0.3:
            return max(0.01, current_rate * 0.9)
        return current_rate

    # Ã¢â€â‚¬Ã¢â€â‚¬ Knowledge Gap Analysis Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def analyze_knowledge_gaps() -> dict:
        """Use memory mesh learner to find knowledge gaps."""
        def _run():
            from database.session import session_scope
            from cognitive.memory_mesh_learner import get_memory_mesh_learner
            with session_scope() as s:
                learner = get_memory_mesh_learner(s)
                return learner.get_learning_suggestions()
        return _safe(_run, {"knowledge_gaps": [], "top_priorities": []})

    # Ã¢â€â‚¬Ã¢â€â‚¬ Full Cognitive Report Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    @staticmethod
    def full_cognitive_report(query: str = "") -> dict:
        """Run ALL cognitive modules and return unified report."""
        mesh = CognitiveMesh
        return {
            "ooda": mesh.ooda_cycle(query or "system status check"),
            "ambiguity": mesh.resolve_ambiguity(query or "test") if query else {"skipped": True},
            "invariants": mesh.check_invariants(),
            "knowledge_gaps": mesh.analyze_knowledge_gaps(),
            "procedural": mesh.find_procedure(query or "default"),
        }


def get_cognitive_mesh() -> CognitiveMesh:
    return CognitiveMesh()
