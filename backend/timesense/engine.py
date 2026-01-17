import os
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from timesense.primitives import PrimitiveType, PrimitiveCategory, PrimitiveRegistry, get_primitive_registry
from timesense.profiles import ProfileManager, TimeProfile, ProfileStatus
from timesense.benchmarks import CalibrationService, CalibrationReport
from timesense.predictor import TimePredictor, PredictionResult, TaskPlan

logger = logging.getLogger(__name__)

class EngineStatus(str, Enum):
    """Status of the TimeSense engine."""
    INITIALIZING = "initializing"
    CALIBRATING = "calibrating"
    READY = "ready"
    DEGRADED = "degraded"  # Some profiles stale or unreliable
    ERROR = "error"


@dataclass
class EngineStats:
    """Statistics for the TimeSense engine."""
    status: EngineStatus = EngineStatus.INITIALIZING
    started_at: Optional[datetime] = None
    last_calibration: Optional[datetime] = None
    calibration_count: int = 0

    # Profile stats
    total_profiles: int = 0
    stable_profiles: int = 0
    stale_profiles: int = 0
    uncalibrated_profiles: int = 0

    # Prediction stats
    total_predictions: int = 0
    predictions_last_hour: int = 0
    average_confidence: float = 0.0

    # Accuracy stats
    predictions_within_p95: float = 0.0
    mean_absolute_error: float = 0.0

    # Task tracking
    active_tasks: int = 0
    completed_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_calibration': self.last_calibration.isoformat() if self.last_calibration else None,
            'calibration_count': self.calibration_count,
            'total_profiles': self.total_profiles,
            'stable_profiles': self.stable_profiles,
            'stale_profiles': self.stale_profiles,
            'uncalibrated_profiles': self.uncalibrated_profiles,
            'total_predictions': self.total_predictions,
            'predictions_last_hour': self.predictions_last_hour,
            'average_confidence': self.average_confidence,
            'predictions_within_p95': self.predictions_within_p95,
            'mean_absolute_error': self.mean_absolute_error,
            'active_tasks': self.active_tasks,
            'completed_tasks': self.completed_tasks
        }


@dataclass
class TrackedTask:
    """A task being tracked for time measurement."""
    task_id: str
    primitive_type: Optional[PrimitiveType]
    size: float
    started_at: datetime
    prediction: Optional[PredictionResult] = None
    completed_at: Optional[datetime] = None
    actual_duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimeSenseEngine:
    """
    Main TimeSense Engine orchestrator.

    Coordinates:
    - Startup calibration
    - Continuous profile updates
    - Time predictions
    - Task tracking and learning
    - Periodic recalibration
    """

    def __init__(
        self,
        machine_id: str = "default",
        profile_path: Optional[str] = None,
        auto_calibrate: bool = True,
        recalibration_interval_hours: float = 24.0
    ):
        self.machine_id = machine_id
        self.profile_path = profile_path or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'timesense_profiles.json'
        )
        self.auto_calibrate = auto_calibrate
        self.recalibration_interval_hours = recalibration_interval_hours

        # Core components
        self.profile_manager = ProfileManager(machine_id)
        self.primitive_registry = get_primitive_registry()
        self.calibration_service = CalibrationService(
            self.profile_manager,
            self.primitive_registry
        )
        self.predictor = TimePredictor(self.profile_manager)

        # State
        self.stats = EngineStats()
        self._active_tasks: Dict[str, TrackedTask] = {}
        self._initialized = False
        self._shutdown = False

        # Background tasks
        self._recalibration_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

        # Event callbacks
        self._on_calibration_complete: List[Callable] = []
        self._on_prediction_error: List[Callable] = []

        logger.info(f"[TIMESENSE] Engine created for machine: {machine_id}")

    async def initialize(self, quick_calibration: bool = False) -> bool:
        """
        Initialize the engine.

        Loads existing profiles and optionally runs calibration.
        """
        self.stats.started_at = datetime.utcnow()
        self.stats.status = EngineStatus.INITIALIZING

        logger.info("[TIMESENSE] Initializing engine...")

        # Ensure data directory exists
        data_dir = os.path.dirname(self.profile_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        # Try to load existing profiles
        if os.path.exists(self.profile_path):
            try:
                self.profile_manager.load(self.profile_path)
                logger.info(f"[TIMESENSE] Loaded {len(self.profile_manager.get_all_profiles())} profiles")
            except Exception as e:
                logger.warning(f"[TIMESENSE] Failed to load profiles: {e}")

        # Run calibration if needed
        if self.auto_calibrate:
            stale_count = len(self.profile_manager.get_stale_profiles())
            total_count = len(self.profile_manager.get_all_profiles())

            needs_calibration = (
                total_count == 0 or
                stale_count > total_count * 0.5  # More than 50% stale
            )

            if needs_calibration:
                self.stats.status = EngineStatus.CALIBRATING
                try:
                    report = self.calibration_service.run_startup_calibration(
                        quick=quick_calibration
                    )
                    self.stats.last_calibration = report.completed_at
                    self.stats.calibration_count += 1

                    # Save profiles
                    self.profile_manager.save(self.profile_path)

                    # Notify callbacks
                    for callback in self._on_calibration_complete:
                        try:
                            await callback(report)
                        except Exception as e:
                            logger.error(f"[TIMESENSE] Calibration callback error: {e}")

                except Exception as e:
                    logger.error(f"[TIMESENSE] Calibration failed: {e}")
                    self.stats.status = EngineStatus.ERROR
                    return False

        # Update stats
        self._update_stats()
        self.stats.status = EngineStatus.READY
        self._initialized = True

        # Start background recalibration task
        if self.auto_calibrate and self.recalibration_interval_hours > 0:
            self._recalibration_task = asyncio.create_task(
                self._recalibration_loop()
            )

        logger.info(f"[TIMESENSE] Engine ready: {self.stats.stable_profiles} stable profiles")
        return True

    def initialize_sync(self, quick_calibration: bool = True) -> bool:
        """Synchronous initialization for non-async contexts."""
        self.stats.started_at = datetime.utcnow()
        self.stats.status = EngineStatus.INITIALIZING

        logger.info("[TIMESENSE] Initializing engine (sync)...")

        # Ensure data directory exists
        data_dir = os.path.dirname(self.profile_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        # Try to load existing profiles
        if os.path.exists(self.profile_path):
            try:
                self.profile_manager.load(self.profile_path)
                logger.info(f"[TIMESENSE] Loaded {len(self.profile_manager.get_all_profiles())} profiles")
            except Exception as e:
                logger.warning(f"[TIMESENSE] Failed to load profiles: {e}")

        # Run calibration if needed
        if self.auto_calibrate:
            stale_count = len(self.profile_manager.get_stale_profiles())
            total_count = len(self.profile_manager.get_all_profiles())

            needs_calibration = (
                total_count == 0 or
                stale_count > total_count * 0.5
            )

            if needs_calibration:
                self.stats.status = EngineStatus.CALIBRATING
                try:
                    report = self.calibration_service.run_startup_calibration(
                        quick=quick_calibration
                    )
                    self.stats.last_calibration = report.completed_at
                    self.stats.calibration_count += 1

                    # Save profiles
                    self.profile_manager.save(self.profile_path)

                except Exception as e:
                    logger.error(f"[TIMESENSE] Calibration failed: {e}")
                    self.stats.status = EngineStatus.ERROR
                    return False

        # Update stats
        self._update_stats()
        self.stats.status = EngineStatus.READY
        self._initialized = True

        logger.info(f"[TIMESENSE] Engine ready: {self.stats.stable_profiles} stable profiles")
        return True

    async def shutdown(self):
        """Shutdown the engine gracefully."""
        logger.info("[TIMESENSE] Shutting down engine...")
        self._shutdown = True

        # Cancel background task
        if self._recalibration_task:
            self._recalibration_task.cancel()
            try:
                await self._recalibration_task
            except asyncio.CancelledError:
                pass

        # Save profiles
        try:
            self.profile_manager.save(self.profile_path)
        except Exception as e:
            logger.error(f"[TIMESENSE] Failed to save profiles: {e}")

        logger.info("[TIMESENSE] Engine shutdown complete")

    def _update_stats(self):
        """Update engine statistics."""
        profiles = self.profile_manager.get_all_profiles()

        self.stats.total_profiles = len(profiles)
        self.stats.stable_profiles = sum(
            1 for p in profiles if p.status == ProfileStatus.STABLE
        )
        self.stats.stale_profiles = sum(
            1 for p in profiles if p.needs_recalibration()
        )
        self.stats.uncalibrated_profiles = sum(
            1 for p in profiles if p.status == ProfileStatus.UNCALIBRATED
        )

        # Calculate average confidence
        if profiles:
            self.stats.average_confidence = sum(p.confidence for p in profiles) / len(profiles)

        # Update prediction accuracy
        accuracy = self.predictor.get_prediction_accuracy()
        self.stats.predictions_within_p95 = accuracy.get('within_p95_percent', 0)
        self.stats.mean_absolute_error = accuracy.get('mean_absolute_error', 0)

        # Determine status
        if self.stats.stable_profiles == 0:
            self.stats.status = EngineStatus.ERROR
        elif self.stats.stale_profiles > self.stats.total_profiles * 0.3:
            self.stats.status = EngineStatus.DEGRADED
        else:
            self.stats.status = EngineStatus.READY

    async def _recalibration_loop(self):
        """Background loop for periodic recalibration."""
        interval = timedelta(hours=self.recalibration_interval_hours)

        while not self._shutdown:
            try:
                await asyncio.sleep(interval.total_seconds())

                if self._shutdown:
                    break

                # Check if recalibration needed
                stale = self.profile_manager.get_stale_profiles()
                if stale:
                    logger.info(f"[TIMESENSE] Recalibrating {len(stale)} stale profiles...")
                    recalibrated = self.calibration_service.recalibrate_stale_profiles()
                    if recalibrated > 0:
                        self.profile_manager.save(self.profile_path)
                        self.stats.calibration_count += 1
                        self.stats.last_calibration = datetime.utcnow()
                        self._update_stats()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[TIMESENSE] Recalibration error: {e}")

    # ================================================================
    # PREDICTION API
    # ================================================================

    def predict(
        self,
        primitive_type: PrimitiveType,
        size: float,
        model_name: Optional[str] = None
    ) -> PredictionResult:
        """
        Predict time for a primitive operation.

        This is the main prediction API.
        """
        self.stats.total_predictions += 1
        return self.predictor.predict_primitive(primitive_type, size, model_name)

    def predict_task(self, plan: TaskPlan) -> PredictionResult:
        """Predict time for a composed task."""
        self.stats.total_predictions += 1
        return self.predictor.predict_task(plan)

    def estimate_file_processing(
        self,
        file_size_bytes: int,
        include_embedding: bool = True,
        model_name: Optional[str] = None
    ) -> PredictionResult:
        """Estimate time for file processing pipeline."""
        self.stats.total_predictions += 1
        return self.predictor.estimate_file_processing(
            file_size_bytes,
            include_embedding,
            model_name=model_name
        )

    def estimate_retrieval(
        self,
        query_tokens: int = 50,
        top_k: int = 10,
        num_vectors: int = 10000
    ) -> PredictionResult:
        """Estimate time for RAG retrieval."""
        self.stats.total_predictions += 1
        return self.predictor.estimate_retrieval(query_tokens, top_k, num_vectors)

    def estimate_llm_response(
        self,
        prompt_tokens: int,
        max_output_tokens: int,
        model_name: Optional[str] = None
    ) -> PredictionResult:
        """Estimate time for LLM response."""
        self.stats.total_predictions += 1
        return self.predictor.estimate_llm_response(
            prompt_tokens,
            max_output_tokens,
            model_name
        )

    # ================================================================
    # TASK TRACKING API
    # ================================================================

    def start_task(
        self,
        task_id: str,
        primitive_type: Optional[PrimitiveType] = None,
        size: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PredictionResult]:
        """
        Start tracking a task.

        Returns prediction if primitive_type is provided.
        """
        prediction = None
        if primitive_type:
            prediction = self.predict(primitive_type, size)

        with self._lock:
            self._active_tasks[task_id] = TrackedTask(
                task_id=task_id,
                primitive_type=primitive_type,
                size=size,
                started_at=datetime.utcnow(),
                prediction=prediction,
                metadata=metadata or {}
            )
            self.stats.active_tasks = len(self._active_tasks)

        return prediction

    def end_task(
        self,
        task_id: str,
        actual_size: Optional[float] = None
    ) -> Optional[float]:
        """
        End tracking a task and record actual duration.

        Returns actual duration in milliseconds.
        """
        with self._lock:
            task = self._active_tasks.pop(task_id, None)

        if not task:
            return None

        task.completed_at = datetime.utcnow()
        task.actual_duration_ms = (
            task.completed_at - task.started_at
        ).total_seconds() * 1000

        # Update size if provided
        if actual_size is not None:
            task.size = actual_size

        # Record for learning
        if task.prediction and task.primitive_type:
            self.predictor.record_actual(task.prediction, task.actual_duration_ms)

            # Also update profile directly with measurement
            self.profile_manager.get_or_create_profile(task.primitive_type).add_measurement(
                int(task.size),
                task.actual_duration_ms
            )

        self.stats.completed_tasks += 1
        self.stats.active_tasks = len(self._active_tasks)

        return task.actual_duration_ms

    def get_task(self, task_id: str) -> Optional[TrackedTask]:
        """Get a tracked task by ID."""
        return self._active_tasks.get(task_id)

    # ================================================================
    # PROFILE MANAGEMENT API
    # ================================================================

    def get_profile(
        self,
        primitive_type: PrimitiveType,
        model_name: Optional[str] = None
    ) -> Optional[TimeProfile]:
        """Get a specific profile."""
        return self.profile_manager.get_profile(primitive_type, model_name)

    def get_all_profiles(self) -> List[TimeProfile]:
        """Get all profiles."""
        return self.profile_manager.get_all_profiles()

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary of all profiles."""
        return self.profile_manager.get_summary()

    def force_recalibrate(
        self,
        primitive_type: Optional[PrimitiveType] = None
    ) -> int:
        """
        Force recalibration of profiles.

        Args:
            primitive_type: If provided, only recalibrate this primitive

        Returns:
            Number of profiles recalibrated
        """
        if primitive_type:
            # Recalibrate specific primitive
            primitive = self.primitive_registry.get(primitive_type)
            if not primitive:
                return 0

            benchmark_method = self.calibration_service._get_benchmark_method(primitive_type)
            if not benchmark_method:
                return 0

            try:
                results = benchmark_method(
                    primitive.benchmark_sizes,
                    iterations=primitive.measurement_iterations,
                    warmup=primitive.warmup_iterations
                )
                self.calibration_service._process_results(results)
                self.profile_manager.save(self.profile_path)
                self._update_stats()
                return 1
            except Exception as e:
                logger.error(f"[TIMESENSE] Recalibration failed: {e}")
                return 0
        else:
            # Recalibrate all stale
            count = self.calibration_service.recalibrate_stale_profiles()
            if count > 0:
                self.profile_manager.save(self.profile_path)
                self._update_stats()
            return count

    # ================================================================
    # CALIBRATION CALLBACKS
    # ================================================================

    def on_calibration_complete(self, callback: Callable):
        """Register callback for calibration completion."""
        self._on_calibration_complete.append(callback)

    def on_prediction_error(self, callback: Callable):
        """Register callback for prediction errors."""
        self._on_prediction_error.append(callback)

    # ================================================================
    # LLM/EMBEDDING CALIBRATION
    # ================================================================

    async def calibrate_llm(
        self,
        generate_func: Callable,
        model_name: str
    ):
        """Calibrate LLM token generation speed."""
        await self.calibration_service.calibrate_llm(generate_func, model_name)
        self.profile_manager.save(self.profile_path)
        self._update_stats()

    async def calibrate_embedding(
        self,
        embed_func: Callable,
        model_name: str
    ):
        """Calibrate embedding generation speed."""
        await self.calibration_service.calibrate_embedding(embed_func, model_name)
        self.profile_manager.save(self.profile_path)
        self._update_stats()

    async def calibrate_vector_db(
        self,
        search_func: Callable,
        insert_func: Optional[Callable] = None
    ):
        """Calibrate vector database operations."""
        await self.calibration_service.calibrate_vector_db(search_func, insert_func)
        self.profile_manager.save(self.profile_path)
        self._update_stats()

    # ================================================================
    # STATUS & HEALTH
    # ================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and stats."""
        self._update_stats()
        return {
            'engine': self.stats.to_dict(),
            'profiles': self.get_profile_summary(),
            'prediction_accuracy': self.predictor.get_prediction_accuracy()
        }

    def is_ready(self) -> bool:
        """Check if engine is ready for predictions."""
        return self._initialized and self.stats.status in (
            EngineStatus.READY,
            EngineStatus.DEGRADED
        )

    def get_health(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        return {
            'healthy': self.is_ready(),
            'status': self.stats.status.value,
            'stable_profiles': self.stats.stable_profiles,
            'stale_profiles': self.stats.stale_profiles,
            'average_confidence': self.stats.average_confidence,
            'last_calibration': self.stats.last_calibration.isoformat() if self.stats.last_calibration else None
        }


# Global engine instance
_timesense_engine: Optional[TimeSenseEngine] = None


def get_timesense_engine(
    machine_id: str = "default",
    auto_calibrate: bool = True
) -> TimeSenseEngine:
    """Get or create the global TimeSense engine."""
    global _timesense_engine
    if _timesense_engine is None:
        _timesense_engine = TimeSenseEngine(
            machine_id=machine_id,
            auto_calibrate=auto_calibrate
        )
    return _timesense_engine


def reset_timesense_engine():
    """Reset the global engine (for testing)."""
    global _timesense_engine
    _timesense_engine = None
