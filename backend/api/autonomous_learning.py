"""
Autonomous Learning API — Learning Orchestrator facade

Exposes a single learning orchestrator for continuous learning, mirror actions,
and other components. Uses ThreadLearningOrchestrator (thread-based, Windows-safe)
and adapts different call signatures for compatibility.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_learning_orchestrator_instance = None
_orchestrator_lock = __import__("threading").Lock()


def _get_orchestrator():
    """Build or return the singleton ThreadLearningOrchestrator."""
    global _learning_orchestrator_instance
    with _orchestrator_lock:
        if _learning_orchestrator_instance is not None:
            return _learning_orchestrator_instance
        try:
            import settings as _s
            kb_path = getattr(_s, "KNOWLEDGE_BASE_PATH", None) or "backend/knowledge_base"
            from pathlib import Path
            kb_path = str(Path(kb_path).resolve())
        except Exception:
            kb_path = "backend/knowledge_base"
        try:
            from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator
            orch = ThreadLearningOrchestrator(
                knowledge_base_path=kb_path,
                num_study_agents=1,
                num_practice_agents=1
            )
            orch.start()
            _learning_orchestrator_instance = _LearningOrchestratorAdapter(orch)
            logger.info("[AUTONOMOUS_LEARNING] ThreadLearningOrchestrator started")
            return _learning_orchestrator_instance
        except Exception as e:
            logger.warning(f"[AUTONOMOUS_LEARNING] Could not start orchestrator: {e}")
            return None


class _LearningOrchestratorAdapter:
    """
    Adapter that maps mirror/other call signatures to ThreadLearningOrchestrator.
    - submit_study_task(topic, learning_objectives, priority) — unchanged
    - submit_practice_task: accepts both
      - (skill_name, task_description, complexity)
      - (topic=..., practice_type=..., difficulty=..., priority=...)
    """

    def __init__(self, inner):
        self._inner = inner

    def submit_study_task(
        self,
        topic: str,
        learning_objectives: List[str],
        priority: int = 5
    ) -> str:
        return self._inner.submit_study_task(topic, learning_objectives, priority=priority)

    def submit_practice_task(
        self,
        skill_name: Optional[str] = None,
        task_description: Optional[str] = None,
        complexity: float = 0.5,
        topic: Optional[str] = None,
        practice_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        priority: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        if topic is not None and skill_name is None:
            skill_name = topic
        if task_description is None:
            task_description = f"{practice_type or 'practice'} at {difficulty or 'medium'} difficulty"
        return self._inner.submit_practice_task(
            skill_name=skill_name or "general",
            task_description=task_description,
            complexity=complexity
        )

    def get_status(self) -> Dict[str, Any]:
        return self._inner.get_status()

    def stop(self) -> None:
        if hasattr(self._inner, "stop"):
            self._inner.stop()


def get_learning_orchestrator():
    """Return the shared learning orchestrator instance, or None if unavailable."""
    return _get_orchestrator()
