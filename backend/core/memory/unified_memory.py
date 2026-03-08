"""
Unified Memory — sessionful facade for memory when you have a DB session.

For global (singleton) access without a session, use:
  from cognitive.unified_memory import get_unified_memory
  mem = get_unified_memory()

This module provides a sessionful facade that merges:
  - cognitive/learning_memory.py (LearningExample, LearningPattern, LearningMemoryManager)
  - cognitive/episodic_memory.py (Episode, EpisodicBuffer)
  - cognitive/memory_mesh_integration.py (MemoryMeshIntegration)
  - cognitive/memory_mesh_learner.py (MemoryMeshLearner)

All Grace memory ultimately uses the same backends; this is the facade for
callers that already have a session and optional knowledge_base_path.
"""

from pathlib import Path

from cognitive.learning_memory import (
    LearningExample,
    LearningPattern,
    LearningMemoryManager,
    TrustScorer,
)

from cognitive.episodic_memory import (
    Episode,
    EpisodicBuffer,
)

from cognitive.memory_mesh_integration import (
    MemoryMeshIntegration,
)

from cognitive.memory_mesh_learner import (
    MemoryMeshLearner,
    get_memory_mesh_learner,
)


def get_unified_memory():
    """Return the global singleton. Re-export from cognitive.unified_memory."""
    from cognitive.unified_memory import get_unified_memory as _get
    return _get()


class UnifiedMemory:
    """Sessionful facade for all memory operations (use when you have session + optional kb_path)."""

    def __init__(self, session, knowledge_base_path=None):
        self.session = session
        kb = Path(knowledge_base_path) if knowledge_base_path else Path(".")
        self.learning = LearningMemoryManager(session, kb)
        self.episodic = EpisodicBuffer(session)
        self.mesh = MemoryMeshIntegration(
            session=session,
            knowledge_base_path=kb,
        ) if knowledge_base_path else None
        self.learner = MemoryMeshLearner(session)

    def ingest_experience(self, **kwargs):
        """Ingest a learning experience into the full memory pipeline."""
        if self.mesh:
            return self.mesh.ingest_learning_experience(**kwargs)
        return self.learning.ingest_learning_data(**kwargs)

    def recall_similar(self, problem: str, k: int = 5, min_trust: float = 0.5):
        """Recall similar past episodes."""
        return self.episodic.recall_similar(problem, k=k, min_trust=min_trust)

    def get_learning_suggestions(self):
        """Get learning suggestions from the mesh learner."""
        return self.learner.get_learning_suggestions()

    def get_training_data(self, min_trust: float = 0.7, limit: int = 100):
        """Get high-trust training data."""
        return self.learning.get_training_data(min_trust_score=min_trust, limit=limit)

    def track(self, **kwargs):
        """Create a Genesis key."""
        try:
            from api._genesis_tracker import track
            return track(**kwargs)
        except Exception:
            return None


__all__ = [
    "UnifiedMemory",
    "get_unified_memory",
    "LearningExample",
    "LearningPattern",
    "Episode",
    "EpisodicBuffer",
    "MemoryMeshIntegration",
    "MemoryMeshLearner",
]
