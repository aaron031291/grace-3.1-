"""
Procedural Memory - Learned Skills and Procedures

Stores HOW to do things, not just WHAT is true.
This is the difference between knowing and doing.

OPTIMIZED: Now supports semantic similarity for procedure finding

Classes:
- `Procedure`
- `ProceduralRepository`

Key Methods:
- `embedder()`
- `create_procedure()`
- `find_procedure()`
- `generate_procedure_embedding()`
- `index_all_procedures()`
- `suggest_procedure()`
- `update_success_rate()`
- `update_procedure_evidence()`
- `classify_query()`
"""
from sqlalchemy import Column, String, Float, Integer, Text, JSON, ForeignKey
from database.base import BaseModel
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)


class Procedure(BaseModel):
    """
    Learned procedure or skill.

    Example: "How to fix a broken Dockerfile" (procedure)
    vs "What is a Dockerfile" (semantic knowledge)
    """
    __tablename__ = "procedures"

    # Identification
    name = Column(String, nullable=False, unique=True)
    goal = Column(Text, nullable=False)  # What this achieves
    procedure_type = Column(String, nullable=False)  # fix, configure, analyze, etc.

    # How to execute
    steps = Column(JSON, nullable=False)  # Sequence of actions
    preconditions = Column(JSON, nullable=False)  # When this applies

    # Quality metrics
    trust_score = Column(Float, default=0.5, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    # Evidence
    supporting_examples = Column(JSON, nullable=True)  # Learning example IDs
    learned_from_episode_id = Column(String, nullable=True)

    # Embedding for similarity
    embedding = Column(Text, nullable=True)  # JSON array

    # Metadata
    procedure_metadata = Column(JSON, nullable=True)


class ProceduralRepository:
    """
    Manages procedural memory - learned skills and procedures.

    OPTIMIZED: Now supports semantic similarity for procedure finding
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
                logger.info("[PROCEDURAL] Semantic similarity enabled")
            except Exception as e:
                logger.warning(f"[PROCEDURAL] Embedder not available, using text matching: {e}")
                self._use_semantic = False
        return self._embedder

    def create_procedure(
        self,
        goal: str,
        action_sequence: List[Dict[str, Any]],
        preconditions: Dict[str, Any],
        supporting_examples: Optional[List] = None,
        procedure_type: str = "general"
    ) -> Procedure:
        """
        Create new procedure from successful examples.
        """
        # Generate name
        name = self._generate_procedure_name(goal, procedure_type)

        procedure = Procedure(
            name=name,
            goal=goal,
            procedure_type=procedure_type,
            steps=action_sequence,
            preconditions=preconditions,
            trust_score=0.7,  # Initial trust
            success_rate=1.0,  # Optimistic start
            usage_count=1,
            success_count=1,
            supporting_examples=[e.id for e in supporting_examples] if supporting_examples else []
        )

        self.session.add(procedure)
        self.session.commit()

        return procedure

    def _generate_procedure_name(self, goal: str, proc_type: str) -> str:
        """Generate unique procedure name."""
        # Clean goal for name
        clean_goal = goal.lower().replace(' ', '_')[:50]
        timestamp = int(datetime.now().timestamp())
        return f"{proc_type}_{clean_goal}_{timestamp}"

    def find_procedure(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> Optional[Procedure]:
        """
        Find existing procedure for goal and context.

        OPTIMIZED: Uses semantic similarity when embedder is available,
        falls back to text CONTAINS when not.
        """
        # Try semantic search first
        if self._use_semantic or self.embedder:
            try:
                return self._find_procedure_semantic(goal, context)
            except Exception as e:
                logger.warning(f"[PROCEDURAL] Semantic search failed, using fallback: {e}")

        # Fallback to text-based search
        return self._find_procedure_text(goal, context)

    def _find_procedure_semantic(
        self,
        goal: str,
        context: Dict[str, Any],
        min_similarity: float = 0.6
    ) -> Optional[Procedure]:
        """
        Find procedure using semantic similarity (embedding-based).
        """
        # Generate embedding for goal
        goal_embedding = self.embedder.embed_text([goal])[0]
        goal_embedding = np.array(goal_embedding)

        # Get procedures with embeddings
        procedures = self.session.query(Procedure).filter(
            Procedure.embedding.isnot(None)
        ).all()

        if not procedures:
            # Fallback if no embeddings
            return self._find_procedure_text(goal, context)

        # Calculate semantic similarity for each
        scored = []
        for proc in procedures:
            try:
                proc_embedding = np.array(json.loads(proc.embedding))
                similarity = self._cosine_similarity(goal_embedding, proc_embedding)

                # Combine with precondition match
                precond_score = self._match_preconditions(context, proc.preconditions)
                combined_score = (similarity * 0.7) + (precond_score * 0.3)

                if similarity >= min_similarity:
                    scored.append((combined_score, proc))
            except Exception:
                continue

        if not scored:
            return None

        # Return best match
        scored.sort(reverse=True, key=lambda x: x[0])
        best_score, best_proc = scored[0]

        logger.debug(f"[PROCEDURAL] Semantic match found: {best_proc.name} (score={best_score:.2f})")
        return best_proc

    def _find_procedure_text(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> Optional[Procedure]:
        """
        Find procedure using text CONTAINS (fallback).
        """
        procedures = self.session.query(Procedure).filter(
            Procedure.goal.contains(goal)
        ).all()

        if not procedures:
            return None

        # Find best match based on preconditions
        best_match = None
        best_score = 0.0

        for proc in procedures:
            score = self._match_preconditions(context, proc.preconditions)
            if score > best_score:
                best_score = score
                best_match = proc

        return best_match if best_score > 0.5 else None

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

    def _match_preconditions(
        self,
        context: Dict[str, Any],
        preconditions: Dict[str, Any]
    ) -> float:
        """Calculate how well context matches preconditions."""
        if not preconditions:
            return 0.5

        matching_keys = set(context.keys()) & set(preconditions.keys())
        if not matching_keys:
            return 0.0

        matches = 0
        for key in matching_keys:
            if context[key] == preconditions[key]:
                matches += 1

        return matches / len(matching_keys)

    def generate_procedure_embedding(self, procedure: Procedure) -> Optional[List[float]]:
        """
        Generate and store embedding for a procedure.
        """
        if not self.embedder:
            return None

        try:
            # Embed goal + name for better matching
            text = f"{procedure.name}: {procedure.goal}"
            embedding = self.embedder.embed_text([text])[0]
            procedure.embedding = json.dumps(embedding)
            self.session.commit()
            return embedding
        except Exception as e:
            logger.error(f"[PROCEDURAL] Error generating embedding: {e}")
            return None

    def index_all_procedures(self) -> int:
        """
        Generate embeddings for all procedures that don't have them.
        Returns count of procedures indexed.
        """
        if not self.embedder:
            logger.warning("[PROCEDURAL] Cannot index - no embedder available")
            return 0

        # Get procedures without embeddings
        procedures = self.session.query(Procedure).filter(
            Procedure.embedding.is_(None)
        ).all()

        if not procedures:
            logger.info("[PROCEDURAL] All procedures already indexed")
            return 0

        # Batch embed
        texts = [f"{p.name}: {p.goal}" for p in procedures]
        embeddings = self.embedder.embed_text(texts, batch_size=32)

        # Update procedures
        for proc, emb in zip(procedures, embeddings):
            proc.embedding = json.dumps(emb)

        self.session.commit()
        logger.info(f"[PROCEDURAL] Indexed {len(procedures)} procedures")
        return len(procedures)

    def suggest_procedure(
        self,
        goal: str,
        context: Dict[str, Any],
        min_success_rate: float = 0.6
    ) -> Optional[Procedure]:
        """
        Suggest procedure for current situation.
        """
        procedure = self.find_procedure(goal, context)

        if procedure and procedure.success_rate >= min_success_rate:
            return procedure

        return None

    def update_success_rate(
        self,
        procedure_id: str,
        succeeded: bool
    ):
        """
        Update success rate based on outcome.
        """
        procedure = self.session.query(Procedure).filter(
            Procedure.id == procedure_id
        ).first()

        if not procedure:
            return

        procedure.usage_count += 1

        if succeeded:
            procedure.success_count += 1

        # Recalculate success rate
        procedure.success_rate = procedure.success_count / procedure.usage_count

        # Update trust score based on recent performance
        if procedure.usage_count > 5:
            # Use last 5 as moving average
            recent_performance = procedure.success_rate
            procedure.trust_score = recent_performance

        self.session.commit()

    def update_procedure_evidence(
        self,
        procedure_id: str,
        new_example: Any,
        success: bool
    ):
        """
        Add new evidence to existing procedure.
        """
        procedure = self.session.query(Procedure).filter(
            Procedure.id == procedure_id
        ).first()

        if not procedure:
            return

        # Add to supporting examples
        if procedure.supporting_examples is None:
            procedure.supporting_examples = []

        procedure.supporting_examples.append(new_example.id)

        # Update success rate
        self.update_success_rate(procedure_id, success)

    def classify_query(self, query: str) -> str:
        """Classify query type for routing."""
        query_lower = query.lower()

        if any(word in query_lower for word in ['how', 'fix', 'configure', 'setup']):
            return 'how_to'
        elif any(word in query_lower for word in ['what', 'define', 'explain']):
            return 'definition'
        elif any(word in query_lower for word in ['why', 'reason', 'cause']):
            return 'explanation'
        elif any(word in query_lower for word in ['code', 'function', 'class']):
            return 'code_search'
        else:
            return 'general'
