import json
import math
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from timesense.primitives import PrimitiveType, CacheState, ScalingVariable

logger = logging.getLogger(__name__)

class ProfileStatus(str, Enum):
    """Status of a time profile."""
    UNCALIBRATED = "uncalibrated"   # No measurements yet
    CALIBRATING = "calibrating"     # Currently being calibrated
    STABLE = "stable"               # Well-calibrated, predictions reliable
    UNSTABLE = "unstable"           # High variance, predictions uncertain
    STALE = "stale"                 # Too old, needs recalibration
    DEGRADED = "degraded"           # Recent predictions have high error


@dataclass
class DistributionStats:
    """
    Statistical distribution of measurements.

    Stores percentiles and moments for uncertainty quantification.
    """
    # Sample information
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Central tendency
    mean: float = 0.0
    median: float = 0.0  # p50

    # Percentiles for uncertainty bounds
    p10: float = 0.0
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    # Spread
    std_dev: float = 0.0
    variance: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0

    # Coefficient of variation (std_dev / mean) - useful for stability
    cv: float = 0.0

    @classmethod
    def from_samples(cls, samples: List[float]) -> 'DistributionStats':
        """Compute distribution stats from raw samples."""
        if not samples:
            return cls()

        n = len(samples)
        sorted_samples = sorted(samples)

        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std_dev = math.sqrt(variance)

        def percentile(p: float) -> float:
            idx = int(p * (n - 1))
            return sorted_samples[idx]

        cv = std_dev / mean if mean > 0 else 0.0

        return cls(
            sample_count=n,
            last_updated=datetime.utcnow(),
            mean=mean,
            median=percentile(0.5),
            p10=percentile(0.10),
            p25=percentile(0.25),
            p50=percentile(0.50),
            p75=percentile(0.75),
            p90=percentile(0.90),
            p95=percentile(0.95),
            p99=percentile(0.99),
            std_dev=std_dev,
            variance=variance,
            min_value=sorted_samples[0],
            max_value=sorted_samples[-1],
            cv=cv
        )

    def is_stable(self, cv_threshold: float = 0.5) -> bool:
        """Check if distribution is stable (low coefficient of variation)."""
        return self.cv < cv_threshold and self.sample_count >= 5


@dataclass
class LinearModel:
    """
    Linear scaling model: time = a + b * size

    Where:
    - a = fixed overhead (ms)
    - b = time per unit (ms/unit) = inverse throughput
    """
    # Model coefficients
    a: float = 0.0  # Overhead (intercept)
    b: float = 0.0  # Slope (time per unit)

    # Confidence in model fit
    r_squared: float = 0.0  # Goodness of fit
    residual_std: float = 0.0  # Standard deviation of residuals

    # Data points used for fitting
    n_points: int = 0
    fitted_at: datetime = field(default_factory=datetime.utcnow)

    # Bounds for uncertainty
    a_std: float = 0.0  # Standard error of intercept
    b_std: float = 0.0  # Standard error of slope

    def predict(self, size: float) -> float:
        """Predict time for given size."""
        return max(0.0, self.a + self.b * size)

    def predict_with_bounds(
        self,
        size: float,
        confidence: float = 0.95
    ) -> Tuple[float, float, float]:
        """
        Predict time with uncertainty bounds.

        Returns (p50, lower_bound, upper_bound)
        """
        prediction = self.predict(size)

        # Simple uncertainty propagation
        # More accurate would use t-distribution, but this is pragmatic
        if confidence == 0.90:
            z = 1.645
        elif confidence == 0.95:
            z = 1.96
        elif confidence == 0.99:
            z = 2.576
        else:
            z = 1.96

        # Prediction interval (not confidence interval for mean)
        # accounts for both coefficient uncertainty and residual variance
        se_prediction = math.sqrt(
            self.residual_std ** 2 +
            self.a_std ** 2 +
            (size * self.b_std) ** 2
        )

        lower = max(0.0, prediction - z * se_prediction)
        upper = prediction + z * se_prediction

        return prediction, lower, upper

    @classmethod
    def fit(cls, sizes: List[float], times: List[float]) -> 'LinearModel':
        """
        Fit linear model using ordinary least squares.

        time = a + b * size
        """
        if len(sizes) < 2 or len(times) < 2 or len(sizes) != len(times):
            return cls()

        n = len(sizes)

        # Compute means
        x_mean = sum(sizes) / n
        y_mean = sum(times) / n

        # Compute slope (b) and intercept (a)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(sizes, times))
        denominator = sum((x - x_mean) ** 2 for x in sizes)

        if denominator == 0:
            return cls(a=y_mean, b=0.0, n_points=n)

        b = numerator / denominator
        a = y_mean - b * x_mean

        # Compute R-squared
        predictions = [a + b * x for x in sizes]
        ss_res = sum((y - pred) ** 2 for y, pred in zip(times, predictions))
        ss_tot = sum((y - y_mean) ** 2 for y in times)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Compute residual standard deviation
        if n > 2:
            residual_std = math.sqrt(ss_res / (n - 2))
        else:
            residual_std = 0.0

        # Standard errors for coefficients
        if denominator > 0 and n > 2:
            se_b = residual_std / math.sqrt(denominator)
            se_a = residual_std * math.sqrt(sum(x ** 2 for x in sizes) / (n * denominator))
        else:
            se_a = 0.0
            se_b = 0.0

        return cls(
            a=max(0.0, a),  # Overhead can't be negative
            b=max(0.0, b),  # Time per unit can't be negative
            r_squared=max(0.0, r_squared),
            residual_std=residual_std,
            n_points=n,
            fitted_at=datetime.utcnow(),
            a_std=se_a,
            b_std=se_b
        )


@dataclass
class TimeProfile:
    """
    Complete time profile for a primitive operation.

    Contains both raw distribution stats and fitted scaling model.
    """
    # Identity
    primitive_type: PrimitiveType
    machine_id: str = "default"
    model_name: Optional[str] = None  # For LLM/embedding primitives

    # Status
    status: ProfileStatus = ProfileStatus.UNCALIBRATED

    # Unit of measurement
    unit: str = "bytes"
    time_unit: str = "ms"

    # Distribution of raw measurements (per-size bucket)
    # Maps size -> DistributionStats
    size_distributions: Dict[int, DistributionStats] = field(default_factory=dict)

    # Fitted scaling model
    scaling_model: LinearModel = field(default_factory=LinearModel)

    # Context tags (SSD/HDD, GPU, network type, etc.)
    context_tags: Dict[str, str] = field(default_factory=dict)

    # Cache state performance differences
    cache_profiles: Dict[CacheState, LinearModel] = field(default_factory=dict)

    # Confidence and freshness
    confidence: float = 0.0  # 0-1, how much to trust this profile
    freshness: float = 1.0   # 0-1, decays over time

    # Calibration history
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_calibrated: Optional[datetime] = None
    calibration_count: int = 0

    # Prediction error tracking
    prediction_errors: List[float] = field(default_factory=list)  # Recent error ratios
    mean_absolute_error: float = 0.0

    def add_measurement(self, size: int, time_ms: float, cache_state: CacheState = CacheState.WARM):
        """Add a new measurement to the profile."""
        if size not in self.size_distributions:
            self.size_distributions[size] = DistributionStats()

        # We need to track raw samples to recompute distribution
        # For now, use exponential moving average approach
        dist = self.size_distributions[size]

        if dist.sample_count == 0:
            dist.mean = time_ms
            dist.min_value = time_ms
            dist.max_value = time_ms
            dist.p50 = time_ms
            dist.p90 = time_ms
            dist.p95 = time_ms
        else:
            # Exponential moving average
            alpha = 0.1  # Smoothing factor
            dist.mean = alpha * time_ms + (1 - alpha) * dist.mean
            dist.min_value = min(dist.min_value, time_ms)
            dist.max_value = max(dist.max_value, time_ms)

            # Update percentiles with approximation
            # This is a simplified approach; real implementation would use t-digest or similar
            if time_ms > dist.p95:
                dist.p95 = alpha * time_ms + (1 - alpha) * dist.p95
            if time_ms > dist.p90:
                dist.p90 = alpha * time_ms + (1 - alpha) * dist.p90

        dist.sample_count += 1
        dist.last_updated = datetime.utcnow()

        self._refit_model()

    def add_measurements_batch(self, measurements: List[Tuple[int, float]]):
        """Add multiple measurements and refit model."""
        # Group by size
        by_size: Dict[int, List[float]] = {}
        for size, time_ms in measurements:
            if size not in by_size:
                by_size[size] = []
            by_size[size].append(time_ms)

        # Update distributions
        for size, times in by_size.items():
            self.size_distributions[size] = DistributionStats.from_samples(times)

        self._refit_model()

    def _refit_model(self):
        """Refit the scaling model from current distributions."""
        if len(self.size_distributions) < 2:
            return

        sizes = []
        times = []

        for size, dist in self.size_distributions.items():
            if dist.sample_count > 0:
                sizes.append(float(size))
                times.append(dist.mean)

        if len(sizes) >= 2:
            self.scaling_model = LinearModel.fit(sizes, times)
            self.last_calibrated = datetime.utcnow()
            self.calibration_count += 1
            self._update_status()

    def _update_status(self):
        """Update profile status based on current state."""
        if self.scaling_model.n_points == 0:
            self.status = ProfileStatus.UNCALIBRATED
            self.confidence = 0.0
        elif self.scaling_model.n_points < 3:
            self.status = ProfileStatus.CALIBRATING
            self.confidence = 0.3
        elif self.scaling_model.r_squared < 0.7:
            self.status = ProfileStatus.UNSTABLE
            self.confidence = 0.5
        elif self.mean_absolute_error > 0.5:  # 50% error
            self.status = ProfileStatus.DEGRADED
            self.confidence = 0.4
        else:
            self.status = ProfileStatus.STABLE
            # Confidence based on R-squared and sample size
            self.confidence = min(0.95, self.scaling_model.r_squared * (1 - 1 / (self.scaling_model.n_points + 1)))

        # Apply freshness decay
        if self.last_calibrated:
            age_hours = (datetime.utcnow() - self.last_calibrated).total_seconds() / 3600
            # Decay to 50% after 24 hours
            self.freshness = math.exp(-age_hours / 34.7)  # ln(2) / 24 ≈ 0.0289, so 1/0.0289 ≈ 34.7

    def predict(self, size: float) -> float:
        """Predict time for given size (p50 estimate)."""
        return self.scaling_model.predict(size)

    def predict_with_uncertainty(
        self,
        size: float
    ) -> Tuple[float, float, float, float]:
        """
        Predict time with uncertainty bounds.

        Returns (p50, p90, p95, p99) estimates in milliseconds.
        """
        p50, lower, upper = self.scaling_model.predict_with_bounds(size, confidence=0.95)

        # Estimate other percentiles based on model uncertainty
        # These are approximations assuming roughly normal residuals
        spread = upper - p50
        p90 = p50 + spread * 0.65
        p95 = p50 + spread * 1.0
        p99 = p50 + spread * 1.7

        return p50, p90, p95, p99

    def record_prediction_error(self, predicted: float, actual: float):
        """Record prediction error for adaptive learning."""
        if predicted > 0:
            error_ratio = abs(actual - predicted) / predicted
            self.prediction_errors.append(error_ratio)

            # Keep last 100 errors
            if len(self.prediction_errors) > 100:
                self.prediction_errors = self.prediction_errors[-100:]

            # Update mean absolute error
            self.mean_absolute_error = sum(self.prediction_errors) / len(self.prediction_errors)

            # Degrade confidence if errors are high
            if self.mean_absolute_error > 0.3:  # 30% average error
                self.status = ProfileStatus.DEGRADED
                self.confidence *= 0.9

    def get_throughput(self) -> Optional[float]:
        """Get throughput in units/second."""
        if self.scaling_model.b > 0:
            # b is ms per unit, so 1000/b is units per second
            return 1000.0 / self.scaling_model.b
        return None

    def get_overhead_ms(self) -> float:
        """Get fixed overhead in milliseconds."""
        return self.scaling_model.a

    def needs_recalibration(self, max_age_hours: float = 24.0) -> bool:
        """Check if profile needs recalibration."""
        if self.status == ProfileStatus.UNCALIBRATED:
            return True
        if self.status == ProfileStatus.DEGRADED:
            return True
        if self.freshness < 0.5:
            return True
        if self.last_calibrated:
            age_hours = (datetime.utcnow() - self.last_calibrated).total_seconds() / 3600
            return age_hours > max_age_hours
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'primitive_type': self.primitive_type.value,
            'machine_id': self.machine_id,
            'model_name': self.model_name,
            'status': self.status.value,
            'unit': self.unit,
            'scaling_model': {
                'a': self.scaling_model.a,
                'b': self.scaling_model.b,
                'r_squared': self.scaling_model.r_squared,
                'n_points': self.scaling_model.n_points
            },
            'context_tags': self.context_tags,
            'confidence': self.confidence,
            'freshness': self.freshness,
            'throughput': self.get_throughput(),
            'overhead_ms': self.get_overhead_ms(),
            'last_calibrated': self.last_calibrated.isoformat() if self.last_calibrated else None,
            'calibration_count': self.calibration_count,
            'mean_absolute_error': self.mean_absolute_error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeProfile':
        """Create from dictionary."""
        profile = cls(
            primitive_type=PrimitiveType(data['primitive_type']),
            machine_id=data.get('machine_id', 'default'),
            model_name=data.get('model_name'),
            status=ProfileStatus(data.get('status', 'uncalibrated')),
            unit=data.get('unit', 'bytes')
        )

        if 'scaling_model' in data:
            sm = data['scaling_model']
            profile.scaling_model = LinearModel(
                a=sm.get('a', 0.0),
                b=sm.get('b', 0.0),
                r_squared=sm.get('r_squared', 0.0),
                n_points=sm.get('n_points', 0)
            )

        profile.context_tags = data.get('context_tags', {})
        profile.confidence = data.get('confidence', 0.0)
        profile.freshness = data.get('freshness', 1.0)
        profile.calibration_count = data.get('calibration_count', 0)
        profile.mean_absolute_error = data.get('mean_absolute_error', 0.0)

        if data.get('last_calibrated'):
            profile.last_calibrated = datetime.fromisoformat(data['last_calibrated'])

        return profile


class ProfileManager:
    """
    Manages time profiles for all primitives.

    This is Grace's "physics table" - the empirical knowledge
    of how long operations take on this machine.
    """

    def __init__(self, machine_id: str = "default"):
        self.machine_id = machine_id
        self._profiles: Dict[str, TimeProfile] = {}
        self._profile_file: Optional[str] = None

    def _profile_key(
        self,
        primitive_type: PrimitiveType,
        model_name: Optional[str] = None,
        context_key: Optional[str] = None
    ) -> str:
        """Generate unique key for a profile."""
        parts = [primitive_type.value]
        if model_name:
            parts.append(model_name)
        if context_key:
            parts.append(context_key)
        return ":".join(parts)

    def get_profile(
        self,
        primitive_type: PrimitiveType,
        model_name: Optional[str] = None,
        context_key: Optional[str] = None
    ) -> Optional[TimeProfile]:
        """Get profile for a primitive."""
        key = self._profile_key(primitive_type, model_name, context_key)
        return self._profiles.get(key)

    def get_or_create_profile(
        self,
        primitive_type: PrimitiveType,
        model_name: Optional[str] = None,
        unit: str = "bytes",
        context_tags: Optional[Dict[str, str]] = None
    ) -> TimeProfile:
        """Get existing profile or create new one."""
        key = self._profile_key(primitive_type, model_name)

        if key not in self._profiles:
            self._profiles[key] = TimeProfile(
                primitive_type=primitive_type,
                machine_id=self.machine_id,
                model_name=model_name,
                unit=unit,
                context_tags=context_tags or {}
            )
            logger.info(f"[TIMESENSE] Created new profile: {key}")

        return self._profiles[key]

    def update_profile(
        self,
        primitive_type: PrimitiveType,
        measurements: List[Tuple[int, float]],
        model_name: Optional[str] = None,
        unit: str = "bytes"
    ):
        """Update profile with new measurements."""
        profile = self.get_or_create_profile(primitive_type, model_name, unit)
        profile.add_measurements_batch(measurements)
        logger.debug(f"[TIMESENSE] Updated profile {primitive_type.value}: {len(measurements)} measurements")

    def record_prediction(
        self,
        primitive_type: PrimitiveType,
        predicted_ms: float,
        actual_ms: float,
        model_name: Optional[str] = None
    ):
        """Record prediction vs actual for adaptive learning."""
        profile = self.get_profile(primitive_type, model_name)
        if profile:
            profile.record_prediction_error(predicted_ms, actual_ms)

    def get_all_profiles(self) -> List[TimeProfile]:
        """Get all profiles."""
        return list(self._profiles.values())

    def get_stale_profiles(self, max_age_hours: float = 24.0) -> List[TimeProfile]:
        """Get profiles that need recalibration."""
        return [p for p in self._profiles.values() if p.needs_recalibration(max_age_hours)]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all profiles."""
        profiles = self.get_all_profiles()

        by_status = {}
        for p in profiles:
            status = p.status.value
            if status not in by_status:
                by_status[status] = 0
            by_status[status] += 1

        return {
            'machine_id': self.machine_id,
            'total_profiles': len(profiles),
            'by_status': by_status,
            'average_confidence': sum(p.confidence for p in profiles) / len(profiles) if profiles else 0,
            'stale_count': len(self.get_stale_profiles()),
            'profiles': [p.to_dict() for p in profiles]
        }

    def save(self, filepath: str):
        """Save profiles to JSON file."""
        data = {
            'machine_id': self.machine_id,
            'saved_at': datetime.utcnow().isoformat(),
            'profiles': {key: profile.to_dict() for key, profile in self._profiles.items()}
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        self._profile_file = filepath
        logger.info(f"[TIMESENSE] Saved {len(self._profiles)} profiles to {filepath}")

    def load(self, filepath: str):
        """Load profiles from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.machine_id = data.get('machine_id', self.machine_id)

            for key, profile_data in data.get('profiles', {}).items():
                self._profiles[key] = TimeProfile.from_dict(profile_data)

            self._profile_file = filepath
            logger.info(f"[TIMESENSE] Loaded {len(self._profiles)} profiles from {filepath}")

        except FileNotFoundError:
            logger.warning(f"[TIMESENSE] Profile file not found: {filepath}")
        except Exception as e:
            logger.error(f"[TIMESENSE] Failed to load profiles: {e}")

    def clear(self):
        """Clear all profiles."""
        self._profiles.clear()
        logger.info("[TIMESENSE] Cleared all profiles")
