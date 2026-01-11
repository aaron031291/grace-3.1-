"""
Procedural Memory - Learned Skills and Procedures

Stores HOW to do things, not just WHAT is true.
This is the difference between knowing and doing.
"""
from sqlalchemy import Column, String, Float, Integer, Text, JSON, ForeignKey
from database.base import BaseModel
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


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
    """

    def __init__(self, session: Session):
        self.session = session

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
        timestamp = int(datetime.utcnow().timestamp())
        return f"{proc_type}_{clean_goal}_{timestamp}"

    def find_procedure(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> Optional[Procedure]:
        """
        Find existing procedure for goal and context.
        """
        # Simple search - should use embeddings
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
