"""
Learning Memory System - Connects to Memory Mesh

Manages training data from learning memory folders and feeds it
to the memory mesh with trust scores for continuous improvement.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean, ForeignKey
import json

from database.base import BaseModel


class LearningExample(BaseModel):
    """
    Individual learning example with trust score.

    Stores experiences that Grace learns from.
    """
    __tablename__ = "learning_examples"

    # What was learned
    example_type = Column(String, nullable=False, index=True)  # feedback, correction, pattern, success, failure
    input_context = Column(JSON, nullable=False)  # What was the situation
    expected_output = Column(JSON, nullable=False)  # What should have happened
    actual_output = Column(JSON, nullable=True)  # What actually happened

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

    # Metadata
    example_metadata = Column(JSON, nullable=True)


class LearningPattern(BaseModel):
    """
    Extracted patterns from multiple learning examples.

    Higher-level abstractions learned from concrete examples.
    """
    __tablename__ = "learning_patterns"

    pattern_name = Column(String, nullable=False, unique=True)
    pattern_type = Column(String, nullable=False)  # behavioral, optimization, error_recovery, etc.

    # Pattern definition
    preconditions = Column(JSON, nullable=False)  # When this pattern applies
    actions = Column(JSON, nullable=False)  # What to do
    expected_outcomes = Column(JSON, nullable=False)  # What should happen

    # Trust and quality
    trust_score = Column(Float, default=0.5, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)  # % of times it worked
    sample_size = Column(Integer, default=0)  # How many examples support this

    # Supporting evidence
    supporting_examples = Column(JSON, nullable=False)  # List of learning_example IDs

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
    
    Can optionally use enhanced trust scorer for advanced features.
    """

    def __init__(self, use_enhanced: bool = False):
        """
        Initialize trust scorer.
        
        Args:
            use_enhanced: If True, use enhanced trust scorer with confidence intervals
        """
        self.use_enhanced = use_enhanced
        
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
        
        # Initialize enhanced scorer if requested
        if self.use_enhanced:
            try:
                from cognitive.enhanced_trust_scorer import get_adaptive_trust_scorer
                self.enhanced_scorer = get_adaptive_trust_scorer()
            except ImportError:
                self.use_enhanced = False
                self.enhanced_scorer = None
        else:
            self.enhanced_scorer = None

    def calculate_trust_score(
        self,
        source: str,
        outcome_quality: float,
        consistency_score: float,
        validation_history: Dict[str, int],
        age_days: float,
        context: Optional[Dict[str, Any]] = None,
        operational_confidence: Optional[float] = None
    ) -> float:
        """
        Calculate comprehensive trust score.

        Args:
            source: Source of learning example
            outcome_quality: Quality of outcome (0-1)
            consistency_score: Consistency with other knowledge (0-1)
            validation_history: {'validated': N, 'invalidated': M}
            age_days: Age in days
            context: Optional context for enhanced scoring
            operational_confidence: Optional operational confidence (0-1)

        Returns:
            Trust score (0-1)
        """
        # Use enhanced scorer if available and requested
        if self.use_enhanced and self.enhanced_scorer:
            result = self.enhanced_scorer.calculate_trust_score(
                source=source,
                outcome_quality=outcome_quality,
                consistency_score=consistency_score,
                validation_history=validation_history,
                age_days=age_days,
                operational_confidence=operational_confidence,
                context=context or {}
            )
            return result.trust_score
        
        # Original implementation (backward compatible)
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

    def __init__(self, session: Session, knowledge_base_path: Path):
        self.session = session
        self.kb_path = knowledge_base_path
        self.learning_memory_path = knowledge_base_path / "layer_1" / "learning_memory"
        self.trust_scorer = TrustScorer()

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
        # Extract context and outcomes
        input_context = learning_data.get('context', {})
        expected_output = learning_data.get('expected', {})
        actual_output = learning_data.get('actual', {})

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

        # Create learning example
        example = LearningExample(
            example_type=learning_type,
            input_context=input_context,
            expected_output=expected_output,
            actual_output=actual_output,
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
        self.session.commit()

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
        if not actual:
            return 0.5  # Neutral if no actual outcome

        # Simple similarity for now (can be enhanced with semantic similarity)
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
        expected_output: Dict[str, Any],
        use_enhanced: bool = False
    ) -> float:
        """
        Calculate consistency with existing knowledge.

        Checks if this aligns with other learning examples.
        
        Args:
            input_context: Input context for the learning example
            expected_output: Expected output
            use_enhanced: If True, use enhanced consistency checker
            
        Returns:
            Consistency score (0-1)
        """
        # Find similar learning examples
        topic = input_context.get('topic', '')
        similar_examples = self.session.query(LearningExample).filter(
            LearningExample.trust_score > 0.7
        ).limit(50).all()  # Get more examples for enhanced checking

        if not similar_examples:
            return 0.5  # Neutral if no comparison data

        # Use enhanced consistency checker if available
        if use_enhanced:
            try:
                from cognitive.enhanced_consistency_checker import get_consistency_checker
                checker = get_consistency_checker(use_semantic_detection=True)
                
                # Create a temporary example dict for checking
                temp_example = {
                    'input_context': input_context,
                    'expected_output': expected_output,
                    'topic': topic
                }
                
                # Run comprehensive consistency check
                result = checker.check_consistency(
                    new_example=temp_example,
                    existing_examples=similar_examples,
                    topic=topic
                )
                
                # Return the consistency score
                return result.consistency_score
            except ImportError:
                logger.warning("Enhanced consistency checker not available, using simple check")
                use_enhanced = False

        # Simple consistency check (fallback)
        consistent_count = 0
        total_count = len(similar_examples)

        for example in similar_examples:
            # Check if similar context leads to similar output
            # (This is simplified - should use semantic similarity)
            if self._contexts_similar(input_context, example.input_context):
                if self._outputs_similar(expected_output, example.expected_output):
                    consistent_count += 1

        return consistent_count / total_count if total_count > 0 else 0.5

    def _contexts_similar(self, ctx1: Dict, ctx2: Dict) -> bool:
        """Check if contexts are similar (simplified)."""
        # Simple overlap check - should use embeddings
        overlap = set(ctx1.keys()) & set(ctx2.keys())
        return len(overlap) > len(ctx1.keys()) * 0.5

    def _outputs_similar(self, out1: Dict, out2: Dict) -> bool:
        """Check if outputs are similar (simplified)."""
        # Simple overlap check - should use embeddings
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
        pattern_name = f"pattern_{examples[0].example_type}_{datetime.utcnow().timestamp()}"

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
        # Simplified - should use more sophisticated extraction
        all_keys = set()
        for ex in examples:
            all_keys.update(ex.input_context.keys())

        common = {}
        for key in all_keys:
            values = [ex.input_context.get(key) for ex in examples if key in ex.input_context]
            if len(values) >= len(examples) * 0.7:  # 70% threshold
                # This key appears in most examples
                common[key] = values[0]  # Simplified - should find common value

        return common

    def _extract_common_actions(self, examples: List[LearningExample]) -> Dict:
        """Extract common actions from examples."""
        # Simplified pattern extraction
        return examples[0].expected_output  # Should be more sophisticated

    def _extract_common_outcomes(self, examples: List[LearningExample]) -> Dict:
        """Extract common outcomes from examples."""
        # Simplified pattern extraction
        return examples[0].expected_output  # Should be more sophisticated

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
        example.last_used = datetime.utcnow()

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
            age_days = (datetime.utcnow() - example.created_at).days
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
