"""
Episodic Memory - Concrete Experiences

Stores what happened, when it happened, and what the outcome was.
This is different from semantic knowledge - it's experiential.

OPTIMIZED: Now supports semantic similarity using embeddings
"""
from sqlalchemy import Column, String, Float, Text, DateTime
from sqlalchemy.orm import Session, validates
from database.base import BaseModel
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)


def _to_json_str(val) -> str:
    if val is None:
        return "{}"
    if isinstance(val, str):
        return val
    try:
        return json.dumps(val, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        if isinstance(val, dict):
            return json.dumps({str(k): str(v) for k, v in val.items()})
        return json.dumps({"raw": str(val)})


class Episode(BaseModel):
    """
    Single episodic memory - a concrete experience.
    All dict-like fields stored as Text (JSON strings) to avoid
    SQLite 'dict is not supported' binding errors.
    """
    __tablename__ = "episodes"
    __table_args__ = {"extend_existing": True}

    problem = Column(Text, nullable=False)
    action = Column(Text, nullable=False, default="{}")
    outcome = Column(Text, nullable=False, default="{}")
    predicted_outcome = Column(Text, nullable=True)

    prediction_error = Column(Float, default=0.0)

    trust_score = Column(Float, default=0.5, nullable=False)
    source = Column(String, nullable=False)

    genesis_key_id = Column(String, nullable=True)
    decision_id = Column(String, nullable=True)

    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    embedding = Column(Text, nullable=True)

    episode_metadata = Column(Text, nullable=True)

    @validates("action", "outcome", "predicted_outcome", "episode_metadata")
    def _coerce_json(self, key, value):
        return _to_json_str(value)


class EpisodicBuffer:
    """
    Manages episodic memory storage and retrieval.

    OPTIMIZED: Now supports semantic similarity using embeddings
    """

    def __init__(self, session: Session, embedder=None):
        self.session = session
        self._embedder = embedder
        self._use_semantic = False

    @property
    def embedder(self):
        """Lazy load embedder for semantic similarity"""
        if self._embedder is None:
            try:
                from embedding import get_embedding_model
                self._embedder = get_embedding_model()
                self._use_semantic = True
                logger.info("[EPISODIC] Semantic similarity enabled")
            except Exception as e:
                logger.warning(f"[EPISODIC] Embedder not available, using text matching: {e}")
                self._use_semantic = False
        return self._embedder

    def record_episode(
        self,
        problem: str,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        predicted_outcome: Optional[Dict[str, Any]] = None,
        trust_score: float = 0.5,
        source: str = "system",
        genesis_key_id: Optional[str] = None,
        decision_id: Optional[str] = None
    ) -> Episode:
        """
        Record a new episode.
        """
        # Calculate prediction error
        prediction_error = self._calculate_prediction_error(
            outcome,
            predicted_outcome
        )

        episode = Episode(
            problem=str(problem)[:2000] if problem else "",
            action=_to_json_str(action),
            outcome=_to_json_str(outcome),
            predicted_outcome=_to_json_str(predicted_outcome) if predicted_outcome else None,
            prediction_error=prediction_error,
            trust_score=float(trust_score) if trust_score else 0.5,
            source=source or "system",
            genesis_key_id=genesis_key_id,
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc)
        )

        self.session.add(episode)
        self.session.commit()

        return episode

    def _calculate_prediction_error(
        self,
        actual: Dict[str, Any],
        predicted: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate error between predicted and actual."""
        if not predicted:
            return 0.0

        # Simple error calculation
        matching_keys = set(actual.keys()) & set(predicted.keys())
        if not matching_keys:
            return 1.0

        errors = []
        for key in matching_keys:
            if actual[key] == predicted[key]:
                errors.append(0.0)
            else:
                errors.append(1.0)

        return sum(errors) / len(errors) if errors else 0.0

    def recall_similar(
        self,
        problem: str,
        k: int = 5,
        min_trust: float = 0.5
    ) -> List[Episode]:
        """
        Recall similar past episodes.

        OPTIMIZED: Uses embedding-based semantic similarity when available,
        falls back to word overlap when embedder is not available.
        """
        # Try semantic similarity first
        if self._use_semantic or self.embedder:
            try:
                return self._recall_similar_semantic(problem, k, min_trust)
            except Exception as e:
                logger.warning(f"[EPISODIC] Semantic recall failed, using fallback: {e}")

        # Fallback to text-based matching
        return self._recall_similar_text(problem, k, min_trust)

    def _recall_similar_semantic(
        self,
        problem: str,
        k: int,
        min_trust: float
    ) -> List[Episode]:
        """
        Recall episodes using semantic similarity (embedding-based).
        """
        # Generate embedding for query
        query_embedding = self.embedder.embed_text([problem])[0]
        query_embedding = np.array(query_embedding)

        # Get episodes with embeddings
        episodes = self.session.query(Episode).filter(
            Episode.trust_score >= min_trust,
            Episode.embedding.isnot(None)
        ).order_by(
            Episode.timestamp.desc()
        ).limit(k * 3).all()  # Get more to filter by similarity

        # Calculate semantic similarity
        scored = []
        for ep in episodes:
            try:
                ep_embedding = np.array(json.loads(ep.embedding))
                similarity = self._cosine_similarity(query_embedding, ep_embedding)
                scored.append((similarity, ep))
            except Exception:
                # If embedding parsing fails, use text-based score
                text_score = self._calculate_relevance_text(problem, ep.problem)
                scored.append((text_score, ep))

        # Sort by similarity and return top k
        scored.sort(reverse=True, key=lambda x: x[0])

        logger.debug(f"[EPISODIC] Semantic recall found {len(scored)} episodes")
        return [ep for _, ep in scored[:k]]

    def _recall_similar_text(
        self,
        problem: str,
        k: int,
        min_trust: float
    ) -> List[Episode]:
        """
        Recall episodes using text-based word overlap (fallback).
        """
        episodes = self.session.query(Episode).filter(
            Episode.trust_score >= min_trust
        ).order_by(
            Episode.timestamp.desc()
        ).limit(k * 2).all()

        # Simple relevance scoring
        scored = []
        for ep in episodes:
            relevance = self._calculate_relevance_text(problem, ep.problem)
            scored.append((relevance, ep))

        scored.sort(reverse=True, key=lambda x: x[0])

        return [ep for _, ep in scored[:k]]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))
        except Exception:
            return 0.0

    def _calculate_relevance_text(self, query: str, episode_problem: str) -> float:
        """Calculate relevance score using word overlap (fallback)."""
        query_words = set(query.lower().split())
        episode_words = set(episode_problem.lower().split())

        if not query_words or not episode_words:
            return 0.0

        overlap = query_words & episode_words
        return len(overlap) / len(query_words)

    def generate_episode_embedding(self, episode: Episode) -> Optional[List[float]]:
        """
        Generate and store embedding for an episode.
        """
        if not self.embedder:
            return None

        try:
            embedding = self.embedder.embed_text([episode.problem])[0]
            episode.embedding = json.dumps(embedding)
            self.session.commit()
            return embedding
        except Exception as e:
            logger.error(f"[EPISODIC] Error generating embedding: {e}")
            return None

    def index_all_episodes(self) -> int:
        """
        Generate embeddings for all episodes that don't have them.
        Returns count of episodes indexed.
        """
        if not self.embedder:
            logger.warning("[EPISODIC] Cannot index - no embedder available")
            return 0

        # Get episodes without embeddings
        episodes = self.session.query(Episode).filter(
            Episode.embedding.is_(None)
        ).all()

        if not episodes:
            logger.info("[EPISODIC] All episodes already indexed")
            return 0

        # Batch embed
        problems = [ep.problem for ep in episodes]
        embeddings = self.embedder.embed_text(problems, batch_size=32)

        # Update episodes
        for ep, emb in zip(episodes, embeddings):
            ep.embedding = json.dumps(emb)

        self.session.commit()
        logger.info(f"[EPISODIC] Indexed {len(episodes)} episodes")
        return len(episodes)

    def recall_by_topic(
        self,
        conversation_id: str,
        topic: str,
        k: int = 3
    ) -> List[Episode]:
        """Recall episodes by topic."""
        # Simple implementation
        return self.recall_similar(topic, k=k)
