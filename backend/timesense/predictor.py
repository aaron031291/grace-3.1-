import math
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from timesense.primitives import PrimitiveType, PrimitiveCategory, get_primitive_registry
from timesense.profiles import ProfileManager, TimeProfile, ProfileStatus

logger = logging.getLogger(__name__)

class ConfidenceLevel(str, Enum):
    """Confidence levels for predictions."""
    LOW = "low"           # < 50% confidence
    MEDIUM = "medium"     # 50-75% confidence
    HIGH = "high"         # 75-90% confidence
    VERY_HIGH = "very_high"  # > 90% confidence


@dataclass
class PredictionResult:
    """
    Result of a time prediction.

    Contains distribution estimates, not just a single number.
    """
    # Identity
    primitive_type: Optional[PrimitiveType] = None
    task_id: Optional[str] = None

    # Size/scale of the operation
    size: float = 0.0
    unit: str = "bytes"

    # Time estimates (milliseconds)
    p50_ms: float = 0.0   # Typical/median estimate
    p90_ms: float = 0.0   # 90th percentile
    p95_ms: float = 0.0   # 95th percentile (good for deadlines)
    p99_ms: float = 0.0   # 99th percentile (worst case)

    # Confidence in prediction
    confidence: float = 0.0  # 0-1
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW

    # Breakdown if composite prediction
    breakdown: List['PredictionResult'] = field(default_factory=list)

    # Metadata
    model_used: str = "linear"  # linear, bucketed, etc.
    profile_status: ProfileStatus = ProfileStatus.UNCALIBRATED
    predicted_at: datetime = field(default_factory=datetime.utcnow)

    # Warning flags
    is_extrapolation: bool = False  # Prediction outside calibrated range
    is_stale: bool = False          # Based on old calibration data
    warnings: List[str] = field(default_factory=list)

    @property
    def p50_seconds(self) -> float:
        """Get p50 estimate in seconds."""
        return self.p50_ms / 1000.0

    @property
    def p95_seconds(self) -> float:
        """Get p95 estimate in seconds."""
        return self.p95_ms / 1000.0

    @property
    def range_seconds(self) -> Tuple[float, float]:
        """Get (p50, p95) range in seconds."""
        return (self.p50_seconds, self.p95_seconds)

    def human_readable(self) -> str:
        """Get human-readable time estimate."""
        if self.p50_ms < 1000:
            return f"{self.p50_ms:.0f}-{self.p95_ms:.0f}ms"
        elif self.p50_ms < 60000:
            return f"{self.p50_seconds:.1f}-{self.p95_seconds:.1f}s"
        else:
            p50_min = self.p50_ms / 60000
            p95_min = self.p95_ms / 60000
            return f"{p50_min:.1f}-{p95_min:.1f}min"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'primitive_type': self.primitive_type.value if self.primitive_type else None,
            'task_id': self.task_id,
            'size': self.size,
            'unit': self.unit,
            'p50_ms': self.p50_ms,
            'p90_ms': self.p90_ms,
            'p95_ms': self.p95_ms,
            'p99_ms': self.p99_ms,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'profile_status': self.profile_status.value,
            'is_extrapolation': self.is_extrapolation,
            'is_stale': self.is_stale,
            'warnings': self.warnings,
            'human_readable': self.human_readable(),
            'breakdown': [b.to_dict() for b in self.breakdown] if self.breakdown else []
        }


@dataclass
class TaskPlan:
    """
    A plan composed of multiple primitive operations.

    Used for predicting complex task durations.
    """
    task_id: str
    description: str
    steps: List[Tuple[PrimitiveType, float, str]] = field(default_factory=list)  # (primitive, size, unit)
    parallel_groups: List[List[int]] = field(default_factory=list)  # Groups of step indices that run in parallel

    def add_step(
        self,
        primitive_type: PrimitiveType,
        size: float,
        unit: str = "bytes"
    ) -> int:
        """Add a step and return its index."""
        self.steps.append((primitive_type, size, unit))
        return len(self.steps) - 1

    def add_parallel_group(self, step_indices: List[int]):
        """Mark a group of steps as running in parallel."""
        self.parallel_groups.append(step_indices)


class TimePredictor:
    """
    Predicts task duration with uncertainty bounds.

    Uses calibrated profiles to estimate how long operations will take,
    with proper uncertainty quantification.
    """

    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
        self.primitive_registry = get_primitive_registry()

        # Prediction history for learning
        self._prediction_history: List[Tuple[PredictionResult, Optional[float]]] = []
        self._max_history = 1000

    def predict_primitive(
        self,
        primitive_type: PrimitiveType,
        size: float,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Predict time for a single primitive operation.

        Args:
            primitive_type: Type of primitive operation
            size: Size in the primitive's native unit (bytes, tokens, records, etc.)
            model_name: For LLM/embedding primitives, the model name
            context: Additional context (cache_state, concurrency, etc.)

        Returns:
            PredictionResult with p50/p90/p95/p99 estimates
        """
        result = PredictionResult(
            primitive_type=primitive_type,
            size=size
        )

        # Get primitive definition
        primitive = self.primitive_registry.get(primitive_type)
        if primitive:
            result.unit = primitive.unit

        # Get calibrated profile
        profile = self.profile_manager.get_profile(primitive_type, model_name)

        if not profile or profile.status == ProfileStatus.UNCALIBRATED:
            # No calibration data - use primitive's typical values
            return self._predict_uncalibrated(result, primitive_type, size)

        result.profile_status = profile.status

        # Check if we're extrapolating beyond calibrated range
        calibrated_sizes = list(profile.size_distributions.keys())
        if calibrated_sizes:
            min_size = min(calibrated_sizes)
            max_size = max(calibrated_sizes)
            if size < min_size * 0.5 or size > max_size * 2:
                result.is_extrapolation = True
                result.warnings.append(f"Extrapolating beyond calibrated range ({min_size}-{max_size})")

        # Check staleness
        if profile.needs_recalibration():
            result.is_stale = True
            result.warnings.append("Profile is stale, predictions may be inaccurate")

        # Get prediction with uncertainty
        p50, p90, p95, p99 = profile.predict_with_uncertainty(size)

        result.p50_ms = p50
        result.p90_ms = p90
        result.p95_ms = p95
        result.p99_ms = p99
        result.confidence = profile.confidence * profile.freshness

        # Determine confidence level
        result.confidence_level = self._get_confidence_level(result.confidence)

        # Widen uncertainty for extrapolation or stale data
        if result.is_extrapolation or result.is_stale:
            uncertainty_factor = 1.5 if result.is_extrapolation else 1.2
            result.p90_ms *= uncertainty_factor
            result.p95_ms *= uncertainty_factor
            result.p99_ms *= uncertainty_factor
            result.confidence *= 0.7

        return result

    def _predict_uncalibrated(
        self,
        result: PredictionResult,
        primitive_type: PrimitiveType,
        size: float
    ) -> PredictionResult:
        """Make prediction without calibration data using typical values."""
        primitive = self.primitive_registry.get(primitive_type)

        if not primitive:
            result.warnings.append("Unknown primitive type")
            result.confidence = 0.1
            result.confidence_level = ConfidenceLevel.LOW
            return result

        # Use typical values from primitive definition
        scaling = primitive.scaling

        # Estimate using middle of typical ranges
        typical_overhead = (scaling.typical_overhead_ms[0] + scaling.typical_overhead_ms[1]) / 2
        typical_throughput = math.sqrt(
            scaling.typical_throughput_range[0] * scaling.typical_throughput_range[1]
        )  # Geometric mean

        # time = overhead + size / throughput
        # throughput is in units/sec, so convert to ms
        time_per_unit_ms = 1000.0 / typical_throughput
        p50 = typical_overhead + size * time_per_unit_ms

        # Wide uncertainty for uncalibrated
        result.p50_ms = p50
        result.p90_ms = p50 * 2.0
        result.p95_ms = p50 * 3.0
        result.p99_ms = p50 * 5.0

        result.confidence = 0.2
        result.confidence_level = ConfidenceLevel.LOW
        result.warnings.append("No calibration data - using typical values with high uncertainty")
        result.model_used = "typical_values"

        return result

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Map confidence score to level."""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def predict_task(self, plan: TaskPlan) -> PredictionResult:
        """
        Predict time for a composed task with multiple steps.

        Handles sequential and parallel execution.
        """
        result = PredictionResult(
            task_id=plan.task_id
        )

        if not plan.steps:
            return result

        # Predict each step
        step_predictions = []
        for primitive_type, size, unit in plan.steps:
            pred = self.predict_primitive(primitive_type, size)
            step_predictions.append(pred)
            result.breakdown.append(pred)

        # Find which steps are in parallel groups
        parallel_step_indices = set()
        for group in plan.parallel_groups:
            parallel_step_indices.update(group)

        # Calculate total time
        # Sequential steps add up
        # Parallel groups take max time

        total_p50 = 0.0
        total_p90 = 0.0
        total_p95 = 0.0
        total_p99 = 0.0

        # Handle sequential steps (not in any parallel group)
        for i, pred in enumerate(step_predictions):
            if i not in parallel_step_indices:
                total_p50 += pred.p50_ms
                total_p90 += pred.p90_ms
                total_p95 += pred.p95_ms
                total_p99 += pred.p99_ms

        # Handle parallel groups (take max of each percentile)
        for group in plan.parallel_groups:
            group_preds = [step_predictions[i] for i in group if i < len(step_predictions)]
            if group_preds:
                total_p50 += max(p.p50_ms for p in group_preds)
                total_p90 += max(p.p90_ms for p in group_preds)
                total_p95 += max(p.p95_ms for p in group_preds)
                total_p99 += max(p.p99_ms for p in group_preds)

        result.p50_ms = total_p50
        result.p90_ms = total_p90
        result.p95_ms = total_p95
        result.p99_ms = total_p99

        # Aggregate confidence (minimum of all steps)
        if step_predictions:
            result.confidence = min(p.confidence for p in step_predictions)
            result.confidence_level = self._get_confidence_level(result.confidence)

            # Aggregate warnings
            for pred in step_predictions:
                if pred.is_extrapolation:
                    result.is_extrapolation = True
                if pred.is_stale:
                    result.is_stale = True
                result.warnings.extend(pred.warnings)

            # Deduplicate warnings
            result.warnings = list(set(result.warnings))

        result.model_used = "composite"
        return result

    def predict_batch(
        self,
        items: List[Tuple[PrimitiveType, float]],
        parallel: bool = False
    ) -> PredictionResult:
        """
        Predict time for a batch of similar operations.

        Args:
            items: List of (primitive_type, size) tuples
            parallel: If True, assume items run in parallel
        """
        if not items:
            return PredictionResult()

        predictions = [
            self.predict_primitive(ptype, size)
            for ptype, size in items
        ]

        result = PredictionResult()
        result.breakdown = predictions

        if parallel:
            # Parallel: max of each percentile
            result.p50_ms = max(p.p50_ms for p in predictions)
            result.p90_ms = max(p.p90_ms for p in predictions)
            result.p95_ms = max(p.p95_ms for p in predictions)
            result.p99_ms = max(p.p99_ms for p in predictions)
        else:
            # Sequential: sum
            result.p50_ms = sum(p.p50_ms for p in predictions)
            result.p90_ms = sum(p.p90_ms for p in predictions)
            result.p95_ms = sum(p.p95_ms for p in predictions)
            result.p99_ms = sum(p.p99_ms for p in predictions)

        result.confidence = min(p.confidence for p in predictions)
        result.confidence_level = self._get_confidence_level(result.confidence)

        return result

    def estimate_file_processing(
        self,
        file_size_bytes: int,
        include_embedding: bool = True,
        chunk_size: int = 512,
        model_name: Optional[str] = None
    ) -> PredictionResult:
        """
        Estimate time for typical file processing pipeline.

        Includes: read, chunk, embed (optional), store
        """
        plan = TaskPlan(
            task_id=f"file_process_{file_size_bytes}",
            description=f"Process {file_size_bytes} byte file"
        )

        # Step 1: Read file
        plan.add_step(PrimitiveType.DISK_READ_SEQ, file_size_bytes, "bytes")

        # Step 2: Text chunking
        plan.add_step(PrimitiveType.CPU_TEXT_CHUNK, file_size_bytes, "bytes")

        if include_embedding:
            # Estimate tokens (rough: 4 chars per token)
            estimated_tokens = file_size_bytes / 4
            num_chunks = max(1, file_size_bytes / chunk_size)

            # Step 3: Embed chunks (could be batched)
            plan.add_step(PrimitiveType.EMBED_TEXT, estimated_tokens, "tokens")

            # Step 4: Vector insert
            plan.add_step(PrimitiveType.VECTOR_INSERT, num_chunks, "vectors")

        # Step 5: Database insert
        plan.add_step(PrimitiveType.DB_INSERT_SINGLE, 1, "records")

        return self.predict_task(plan)

    def estimate_retrieval(
        self,
        query_tokens: int = 50,
        top_k: int = 10,
        num_vectors: int = 10000,
        include_rerank: bool = False
    ) -> PredictionResult:
        """
        Estimate time for RAG retrieval pipeline.
        """
        plan = TaskPlan(
            task_id=f"retrieval_{top_k}",
            description=f"Retrieve top-{top_k} from {num_vectors} vectors"
        )

        # Step 1: Embed query
        plan.add_step(PrimitiveType.EMBED_TEXT, query_tokens, "tokens")

        # Step 2: Vector search
        plan.add_step(PrimitiveType.VECTOR_SEARCH, num_vectors, "vectors")

        # Step 3: Fetch documents from DB
        plan.add_step(PrimitiveType.DB_QUERY_SIMPLE, top_k, "records")

        return self.predict_task(plan)

    def estimate_llm_response(
        self,
        prompt_tokens: int,
        max_output_tokens: int,
        model_name: Optional[str] = None
    ) -> PredictionResult:
        """
        Estimate time for LLM response generation.
        """
        plan = TaskPlan(
            task_id=f"llm_response_{prompt_tokens}_{max_output_tokens}",
            description=f"Generate {max_output_tokens} tokens from {prompt_tokens} prompt"
        )

        # Step 1: Process prompt (TTFT)
        plan.add_step(PrimitiveType.LLM_PROMPT_PROCESS, prompt_tokens, "tokens")

        # Step 2: Generate tokens
        plan.add_step(PrimitiveType.LLM_TOKENS_GENERATE, max_output_tokens, "tokens")

        return self.predict_task(plan)

    def record_actual(
        self,
        prediction: PredictionResult,
        actual_ms: float
    ):
        """
        Record actual duration for a prediction.

        Used for continuous calibration and learning.
        """
        # Store in history
        self._prediction_history.append((prediction, actual_ms))
        if len(self._prediction_history) > self._max_history:
            self._prediction_history = self._prediction_history[-self._max_history:]

        # Update profile if primitive prediction
        if prediction.primitive_type:
            self.profile_manager.record_prediction(
                prediction.primitive_type,
                prediction.p50_ms,
                actual_ms
            )

    def get_prediction_accuracy(self) -> Dict[str, Any]:
        """Get accuracy statistics for recent predictions."""
        if not self._prediction_history:
            return {'sample_count': 0}

        # Filter to predictions with actual values
        completed = [(p, a) for p, a in self._prediction_history if a is not None]

        if not completed:
            return {'sample_count': 0}

        # Calculate error metrics
        errors = []
        for pred, actual in completed:
            if pred.p50_ms > 0:
                error_ratio = (actual - pred.p50_ms) / pred.p50_ms
                errors.append(error_ratio)

        if not errors:
            return {'sample_count': 0}

        mean_error = sum(errors) / len(errors)
        abs_errors = [abs(e) for e in errors]
        mean_abs_error = sum(abs_errors) / len(abs_errors)

        # Calculate what % of actuals were within p95
        within_p95 = sum(
            1 for pred, actual in completed
            if actual <= pred.p95_ms
        ) / len(completed)

        return {
            'sample_count': len(completed),
            'mean_error': mean_error,
            'mean_absolute_error': mean_abs_error,
            'within_p95_percent': within_p95 * 100,
            'total_predictions': len(self._prediction_history)
        }


# Convenience functions for common predictions

def estimate_disk_read(
    profile_manager: ProfileManager,
    size_bytes: int
) -> PredictionResult:
    """Quick estimate for disk read."""
    predictor = TimePredictor(profile_manager)
    return predictor.predict_primitive(PrimitiveType.DISK_READ_SEQ, size_bytes)


def estimate_embedding(
    profile_manager: ProfileManager,
    num_tokens: int,
    model_name: Optional[str] = None
) -> PredictionResult:
    """Quick estimate for embedding."""
    predictor = TimePredictor(profile_manager)
    return predictor.predict_primitive(
        PrimitiveType.EMBED_TEXT,
        num_tokens,
        model_name=model_name
    )


def estimate_vector_search(
    profile_manager: ProfileManager,
    collection_size: int
) -> PredictionResult:
    """Quick estimate for vector search."""
    predictor = TimePredictor(profile_manager)
    return predictor.predict_primitive(PrimitiveType.VECTOR_SEARCH, collection_size)
