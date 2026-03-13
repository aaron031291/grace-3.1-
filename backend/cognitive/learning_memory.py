"""
Learning Memory System - Connects to Memory Mesh

Manages training data from learning memory folders and feeds it
to the memory mesh with trust scores for continuous improvement.

NOTE: All JSON-like columns use Text + json.dumps/loads instead of
Column(JSON) because SQLite's JSON type adapter does not reliably
serialize Python dicts on INSERT — the sqlite3 C driver raises
"ProgrammingError: type 'dict' is not supported" when it encounters
a raw dict in a parameter slot.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session, validates
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean, ForeignKey
import json

from core.datetime_utils import ensure_aware
from backend.database.base import BaseModel


def _to_json_str(val) -> str:
    """Coerce any value to a JSON string safe for SQLite Text columns."""
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


def _from_json_str(val) -> dict:
    """Parse a stored JSON string back to a dict."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {"raw": val}
        except Exception:
            return {"raw": val}
    return {"raw": str(val)}


class LearningExample(BaseModel):
    """
    Individual learning example with trust score.

    Stores experiences that Grace learns from.
    """
    __tablename__ = "learning_examples"
    __table_args__ = {"extend_existing": True}

    example_type = Column(String, nullable=False, index=True)
    input_context = Column(Text, nullable=False, default="{}")
    expected_output = Column(Text, nullable=False, default="{}")
    actual_output = Column(Text, nullable=True)

    # Trust scoring
    trust_score = Column(Float, default=0.5, nullable=False)  # Overall trust (0-1)
    source_reliability = Column(Float, default=0.5, nullable=False)  # How reliable is the source
    outcome_quality = Column(Float, default=0.5, nullable=False)  # How good was the outcome
    consistency_score = Column(Float, default=0.5, nullable=False)  # Consistency with other examples
    recency_weight = Column(Float, default=1.0, nullable=False)  # Decay over time

    # Provenance
    source = Column(String, nullable=False)  # user_feedback, system_observation, external_api, etc.
    source_user_id = Column(String, nullable=True)  # Genesis ID if user-provided
    genesis_key_id = Column(String, nullable=True)  # Link to Genesis Key

    # Learning metadata
    times_referenced = Column(Integer, default=0)  # How often used in training
    times_validated = Column(Integer, default=0)  # How often validated as correct
    times_invalidated = Column(Integer, default=0)  # How often proven wrong
    last_used = Column(DateTime, nullable=True)  # Last time referenced

    # Storage location
    file_path = Column(String, nullable=True)  # Path in learning_memory folder

    # Connections to memory mesh
    episodic_episode_id = Column(String, nullable=True)  # Link to episodic memory
    procedure_id = Column(String, nullable=True)  # Link to learned procedure

    example_metadata = Column(Text, nullable=True)

    @validates("input_context", "expected_output", "actual_output", "example_metadata")
    def _coerce_to_json_str(self, key, value):
        return _to_json_str(value)


class LearningPattern(BaseModel):
    """
    Extracted patterns from multiple learning examples.

    Higher-level abstractions learned from concrete examples.
    """
    __tablename__ = "learning_patterns"
    __table_args__ = {"extend_existing": True}

    pattern_name = Column(String, nullable=False, unique=True)
    pattern_type = Column(String, nullable=False)  # behavioral, optimization, error_recovery, etc.

    preconditions = Column(Text, nullable=False, default="{}")
    actions = Column(Text, nullable=False, default="{}")
    expected_outcomes = Column(Text, nullable=False, default="{}")

    trust_score = Column(Float, default=0.5, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    sample_size = Column(Integer, default=0)

    supporting_examples = Column(Text, nullable=False, default="[]")

    @validates("preconditions", "actions", "expected_outcomes", "supporting_examples")
    def _coerce_pattern_json(self, key, value):
        return _to_json_str(value)

    # Usage tracking
    times_applied = Column(Integer, default=0)
    times_succeeded = Column(Integer, default=0)
    times_failed = Column(Integer, default=0)

    # Connection to memory mesh
    linked_procedures = Column(JSON, nullable=True)  # List of procedure IDs


class TrustScorer:
    """
    Calculates and updates trust scores for learning examples.

    Trust score combines:
    1. Source reliability (who provided this)
    2. Outcome quality (how well it worked)
    3. Consistency (alignment with other knowledge)
    4. Recency (newer is often better)
    5. Validation history (proven right/wrong)
    """

    def __init__(self):
        # Source reliability weights
        self.source_weights = {
            'user_feedback_positive': 0.9,
            'user_feedback_negative': 0.8,  # Negative feedback is valuable
            'system_observation_success': 0.85,
            'system_observation_failure': 0.9,  # Failures teach more
            'external_api_validated': 0.7,
            'external_api_unvalidated': 0.4,
            'inferred': 0.3,
            'assumed': 0.1
        }

    def calculate_trust_score(
        self,
        source: str,
        outcome_quality: float,
        consistency_score: float,
        validation_history: Dict[str, int],
        age_days: float
    ) -> float:
        """
        Calculate comprehensive trust score.

        Args:
            source: Source of learning example
            outcome_quality: Quality of outcome (0-1)
            consistency_score: Consistency with other knowledge (0-1)
            validation_history: {'validated': N, 'invalidated': M}
            age_days: Age in days

        Returns:
            Trust score (0-1)
        """
        # 1. Source reliability (40% weight)
        source_score = self.source_weights.get(source, 0.5)

        # 2. Outcome quality (30% weight)
        outcome_score = outcome_quality

        # 3. Consistency (20% weight)
        consistency = consistency_score

        # 4. Validation history (10% weight)
        validated = validation_history.get('validated', 0)
        invalidated = validation_history.get('invalidated', 0)
        total = validated + invalidated

        if total > 0:
            validation_score = validated / total
        else:
            validation_score = 0.5  # Neutral if no validation

        # 5. Recency weight (decay over time)
        recency_weight = self._calculate_recency_weight(age_days)

        # Weighted combination
        base_score = (
            source_score * 0.4 +
            outcome_score * 0.3 +
            consistency * 0.2 +
            validation_score * 0.1
        )

        # Apply recency decay
        final_score = base_score * recency_weight

        return min(1.0, max(0.0, final_score))

    def _calculate_recency_weight(self, age_days: float) -> float:
        """
        Calculate recency weight with exponential decay.

        Half-life: 90 days
        After 90 days, weight = 0.5
        After 180 days, weight = 0.25
        """
        import math
        half_life_days = 90
        decay_rate = math.log(2) / half_life_days
        return math.exp(-decay_rate * age_days)

    def update_trust_on_validation(
        self,
        example: LearningExample,
        validation_result: bool
    ) -> float:
        """
        Update trust score when example is validated or invalidated.

        Args:
            example: Learning example
            validation_result: True if validated, False if invalidated

        Returns:
            New trust score
        """
        if validation_result:
            example.times_validated += 1
            # Boost trust
            example.trust_score = min(1.0, example.trust_score * 1.1)
        else:
            example.times_invalidated += 1
            # Reduce trust
            example.trust_score = max(0.0, example.trust_score * 0.8)

        return example.trust_score


class LearningMemoryManager:
    """
    Manages learning memory and its connection to memory mesh.

    Responsibilities:
    1. Ingest learning data from files
    2. Calculate trust scores
    3. Extract patterns
    4. Feed to episodic and procedural memory
    5. Update trust based on outcomes
    """

    def __init__(self, session: Session, knowledge_base_path: Optional[Path] = None):
        self.session = session
        if knowledge_base_path is None:
            self.kb_path = Path(__file__).resolve().parent.parent / "knowledge_base"
        elif isinstance(knowledge_base_path, str):
            self.kb_path = Path(knowledge_base_path)
        else:
            self.kb_path = knowledge_base_path
        self.learning_memory_path = self.kb_path / "layer_1" / "learning_memory"
        self.trust_scorer = TrustScorer()

    @staticmethod
    def _ensure_dict(value) -> dict:
        """Coerce value to a plain dict safe for SQLite JSON columns."""
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                import json as _j
                parsed = _j.loads(value)
                return parsed if isinstance(parsed, dict) else {"raw": value}
            except Exception:
                return {"raw": value}
        if isinstance(value, dict):
            import json as _j
            try:
                _j.dumps(value, default=str)
                return value
            except (TypeError, ValueError):
                return {k: str(v) for k, v in value.items()}
        return {"raw": str(value)}

    def ingest_learning_data(
        self,
        learning_type: str,
        learning_data: Dict[str, Any],
        source: str,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> LearningExample:
        """
        Ingest new learning data with trust scoring.

        Args:
            learning_type: Type of learning (feedback, correction, pattern, etc.)
            learning_data: The learning data
            source: Source of learning
            user_id: Genesis ID if user-provided
            genesis_key_id: Link to Genesis Key

        Returns:
            Created learning example
        """
        if isinstance(learning_data, str):
            try:
                import json as _j
                learning_data = _j.loads(learning_data)
            except Exception:
                learning_data = {"raw": learning_data}
        if not isinstance(learning_data, dict):
            learning_data = {"raw": str(learning_data)}

        input_context = self._ensure_dict(learning_data.get('context', {}))
        expected_output = self._ensure_dict(learning_data.get('expected', {}))
        actual_output = self._ensure_dict(learning_data.get('actual', {}))

        # Calculate outcome quality
        outcome_quality = self._calculate_outcome_quality(
            expected_output,
            actual_output
        )

        # Calculate consistency with existing knowledge
        consistency_score = self._calculate_consistency(
            input_context,
            expected_output
        )

        # Calculate trust score
        trust_score = self.trust_scorer.calculate_trust_score(
            source=source,
            outcome_quality=outcome_quality,
            consistency_score=consistency_score,
            validation_history={'validated': 0, 'invalidated': 0},
            age_days=0
        )

        example = LearningExample(
            example_type=learning_type,
            input_context=_to_json_str(input_context),
            expected_output=_to_json_str(expected_output),
            actual_output=_to_json_str(actual_output),
            trust_score=trust_score,
            source_reliability=self.trust_scorer.source_weights.get(source, 0.5),
            outcome_quality=outcome_quality,
            consistency_score=consistency_score,
            recency_weight=1.0,
            source=source,
            source_user_id=user_id,
            genesis_key_id=genesis_key_id
        )


        self.session.add(example)
        self.session.flush()  # Use flush instead of commit to keep object attached

        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("learning", "examples_ingested", 1.0, success=True)
        except Exception:
            pass

        # Check if this contributes to a pattern
        self._check_pattern_extraction(example)

        return example

    def _calculate_outcome_quality(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """
        Calculate quality of outcome (0-1).

        Compares expected vs actual outcomes.
        """
        expected = self._ensure_dict(expected)
        actual = self._ensure_dict(actual)

        if not actual:
            return 0.5

        matching_keys = set(expected.keys()) & set(actual.keys())

        if not matching_keys:
            return 0.3  # Low quality if no overlap

        matches = 0
        total = len(matching_keys)

        for key in matching_keys:
            if expected[key] == actual[key]:
                matches += 1
            elif isinstance(expected[key], (int, float)) and isinstance(actual[key], (int, float)):
                # Partial credit for numeric similarity
                diff = abs(expected[key] - actual[key])
                max_val = max(abs(expected[key]), abs(actual[key]))
                if max_val > 0:
                    similarity = 1 - (diff / max_val)
                    matches += max(0, similarity)

        return matches / total if total > 0 else 0.5

    def _calculate_consistency(
        self,
        input_context: Dict[str, Any],
        expected_output: Dict[str, Any]
    ) -> float:
        """
        Calculate consistency with existing knowledge.

        Checks if this aligns with other learning examples.
        """
        input_context = self._ensure_dict(input_context)
        expected_output = self._ensure_dict(expected_output)
        # Find similar learning examples
        similar_examples = self.session.query(LearningExample).filter(
            LearningExample.trust_score > 0.7
        ).limit(10).all()

        if not similar_examples:
            return 0.5  # Neutral if no comparison data

        # Simple consistency check (can be enhanced)
        consistent_count = 0
        total_count = len(similar_examples)

        for example in similar_examples:
            # Check if similar context leads to similar output
            # (This is simplified - should use semantic similarity)
            if self._contexts_similar(input_context, example.input_context):
                if self._outputs_similar(expected_output, example.expected_output):
                    consistent_count += 1

        return consistent_count / total_count if total_count > 0 else 0.5

    def _contexts_similar(self, ctx1, ctx2) -> bool:
        """Check if contexts are similar (simplified)."""
        ctx1 = _from_json_str(ctx1)
        ctx2 = _from_json_str(ctx2)
        if not ctx1 or not ctx2:
            return False
        overlap = set(ctx1.keys()) & set(ctx2.keys())
        return len(overlap) > len(ctx1.keys()) * 0.5

    def _outputs_similar(self, out1, out2) -> bool:
        """Check if outputs are similar (simplified)."""
        out1 = _from_json_str(out1)
        out2 = _from_json_str(out2)
        if not out1 or not out2:
            return False
        overlap = set(out1.keys()) & set(out2.keys())
        return len(overlap) > len(out1.keys()) * 0.5

    def _check_pattern_extraction(self, example: LearningExample):
        """
        Check if new example contributes to a pattern.

        If multiple similar examples exist, extract a pattern.
        """
        # Find similar examples
        similar = self.session.query(LearningExample).filter(
            LearningExample.example_type == example.example_type,
            LearningExample.trust_score > 0.6
        ).limit(5).all()

        if len(similar) >= 3:
            # Enough examples to extract pattern
            self._extract_pattern(similar)

    def _extract_pattern(self, examples: List[LearningExample]):
        """
        Extract pattern from multiple learning examples.
        """
        # Simple pattern extraction (can be enhanced with ML)
        pattern_name = f"pattern_{examples[0].example_type}_{datetime.now(timezone.utc).timestamp()}"

        # Extract common preconditions
        preconditions = self._extract_common_preconditions(examples)

        # Extract common actions
        actions = self._extract_common_actions(examples)

        # Extract expected outcomes
        outcomes = self._extract_common_outcomes(examples)

        # Calculate pattern trust
        avg_trust = sum(e.trust_score for e in examples) / len(examples)

        # Create pattern
        pattern = LearningPattern(
            pattern_name=pattern_name,
            pattern_type=examples[0].example_type,
            preconditions=preconditions,
            actions=actions,
            expected_outcomes=outcomes,
            trust_score=avg_trust,
            success_rate=0.0,  # Will be updated with usage
            sample_size=len(examples),
            supporting_examples=[e.id for e in examples]
        )

        self.session.add(pattern)
        self.session.commit()

    def _extract_common_preconditions(self, examples: List[LearningExample]) -> Dict:
        """Extract common preconditions from examples."""
        all_keys = set()
        parsed = [_from_json_str(ex.input_context) for ex in examples]
        for d in parsed:
            all_keys.update(d.keys())

        common = {}
        for key in all_keys:
            values = [d.get(key) for d in parsed if key in d]
            if len(values) >= len(examples) * 0.7:
                common[key] = values[0]

        return common

    def _extract_common_actions(self, examples: List[LearningExample]) -> Dict:
        """Extract common actions from examples."""
        return _from_json_str(examples[0].expected_output)

    def _extract_common_outcomes(self, examples: List[LearningExample]) -> Dict:
        """Extract common outcomes from examples."""
        return _from_json_str(examples[0].expected_output)

    def get_training_data(
        self,
        min_trust_score: float = 0.7,
        example_type: Optional[str] = None,
        limit: int = 100
    ) -> List[LearningExample]:
        """
        Get high-trust learning examples for training.

        Args:
            min_trust_score: Minimum trust score threshold
            example_type: Filter by type
            limit: Maximum number of examples

        Returns:
            List of learning examples suitable for training
        """
        query = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= min_trust_score
        )

        if example_type:
            query = query.filter(LearningExample.example_type == example_type)

        # Order by trust score and recency
        query = query.order_by(
            LearningExample.trust_score.desc(),
            LearningExample.created_at.desc()
        )

        return query.limit(limit).all()

    def update_trust_on_usage(
        self,
        example_id: str,
        outcome_success: bool
    ):
        """
        Update trust score when learning example is used.

        Args:
            example_id: Learning example ID
            outcome_success: Whether using this example led to success
        """
        example = self.session.query(LearningExample).filter(
            LearningExample.id == example_id
        ).first()

        if not example:
            return

        # Update usage tracking
        example.times_referenced += 1
        example.last_used = datetime.now(timezone.utc)

        # Update trust based on outcome
        new_trust = self.trust_scorer.update_trust_on_validation(
            example,
            outcome_success
        )

        self.session.commit()

    def decay_trust_scores(self):
        """
        Apply time-based decay to all trust scores.

        Should be run periodically (e.g., daily).
        """
        examples = self.session.query(LearningExample).all()

        for example in examples:
            created = ensure_aware(example.created_at)
            age_days = (datetime.now(timezone.utc) - created).days if created else 0
            example.recency_weight = self.trust_scorer._calculate_recency_weight(age_days)

            # Recalculate trust with new recency weight
            validation_history = {
                'validated': example.times_validated,
                'invalidated': example.times_invalidated
            }

            example.trust_score = self.trust_scorer.calculate_trust_score(
                source=example.source,
                outcome_quality=example.outcome_quality,
                consistency_score=example.consistency_score,
                validation_history=validation_history,
                age_days=age_days
            )

        self.session.commit()
