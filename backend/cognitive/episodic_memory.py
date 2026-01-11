"""
Episodic Memory - Concrete Experiences

Stores what happened, when it happened, and what the outcome was.
This is different from semantic knowledge - it's experiential.
"""
from sqlalchemy import Column, String, Float, Text, DateTime, JSON
from database.base import BaseModel
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


class Episode(BaseModel):
    """
    Single episodic memory - a concrete experience.

    Difference from Decision Logger:
    - Decision Logger = audit trail (immutable record)
    - Episodic Memory = learning substrate (used for pattern extraction)
    """
    __tablename__ = "episodes"

    # What happened
    problem = Column(Text, nullable=False)
    action = Column(JSON, nullable=False)
    outcome = Column(JSON, nullable=False)
    predicted_outcome = Column(JSON, nullable=True)

    # How accurate was prediction
    prediction_error = Column(Float, default=0.0)

    # Trust and quality
    trust_score = Column(Float, default=0.5, nullable=False)
    source = Column(String, nullable=False)  # Where this episode came from

    # Provenance
    genesis_key_id = Column(String, nullable=True)
    decision_id = Column(String, nullable=True)  # Link to OODA decision

    # Temporal
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Embedding for similarity search
    embedding = Column(Text, nullable=True)  # JSON array

    # Metadata
    episode_metadata = Column(JSON, nullable=True)


class EpisodicBuffer:
    """
    Manages episodic memory storage and retrieval.
    """

    def __init__(self, session: Session):
        self.session = session

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
            problem=problem,
            action=action,
            outcome=outcome,
            predicted_outcome=predicted_outcome,
            prediction_error=prediction_error,
            trust_score=trust_score,
            source=source,
            genesis_key_id=genesis_key_id,
            decision_id=decision_id,
            timestamp=datetime.utcnow()
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

        Uses problem similarity to find relevant experiences.
        """
        # For now, simple keyword matching
        # TODO: Use embeddings for semantic similarity

        episodes = self.session.query(Episode).filter(
            Episode.trust_score >= min_trust
        ).order_by(
            Episode.timestamp.desc()
        ).limit(k * 2).all()  # Get more, then filter

        # Simple relevance scoring
        scored = []
        for ep in episodes:
            relevance = self._calculate_relevance(problem, ep.problem)
            scored.append((relevance, ep))

        scored.sort(reverse=True, key=lambda x: x[0])

        return [ep for _, ep in scored[:k]]

    def _calculate_relevance(self, query: str, episode_problem: str) -> float:
        """Calculate relevance score (simplified)."""
        # Simple word overlap
        query_words = set(query.lower().split())
        episode_words = set(episode_problem.lower().split())

        if not query_words or not episode_words:
            return 0.0

        overlap = query_words & episode_words
        return len(overlap) / len(query_words)

    def recall_by_topic(
        self,
        conversation_id: str,
        topic: str,
        k: int = 3
    ) -> List[Episode]:
        """Recall episodes by topic."""
        # Simple implementation
        return self.recall_similar(topic, k=k)
