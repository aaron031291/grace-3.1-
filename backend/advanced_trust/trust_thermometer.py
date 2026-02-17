"""
System-Wide Trust Thermometer

One number: how confident is Grace in herself right now?

Aggregate of all component KPIs, all pillar success rates, all data trust
scores. When the thermometer is low, Grace automatically becomes more
cautious -- verifies more, asks more questions, flags uncertainty. When
it's high, she acts more autonomously.

This is the master knob that controls how aggressive or conservative
the entire system behaves.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SystemMode(str, Enum):
    """Grace's operational mode based on thermometer."""
    AGGRESSIVE = "aggressive"      # High trust, act fast, verify less
    CONFIDENT = "confident"        # Good trust, normal operation
    CAUTIOUS = "cautious"          # Medium trust, verify more
    CONSERVATIVE = "conservative"  # Low trust, verify everything
    PARANOID = "paranoid"          # Very low trust, ask before everything


@dataclass
class ThermometerReading:
    """A single reading of the trust thermometer."""
    temperature: float  # 0.0 - 1.0
    mode: SystemMode
    component_scores: Dict[str, float]
    pillar_scores: Dict[str, float]
    data_trust_score: float
    verification_multiplier: float
    autonomy_level: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ThermometerConfig:
    """Configuration for the thermometer."""
    # Weights for different inputs
    component_weight: float = 0.30
    pillar_weight: float = 0.30
    data_trust_weight: float = 0.25
    recent_performance_weight: float = 0.15

    # Mode thresholds
    aggressive_threshold: float = 0.85
    confident_threshold: float = 0.70
    cautious_threshold: float = 0.50
    conservative_threshold: float = 0.30
    # Below conservative = paranoid

    # Verification multiplier bounds
    min_verification_multiplier: float = 0.2  # High trust = less verification
    max_verification_multiplier: float = 3.0  # Low trust = 3x verification

    # Autonomy bounds
    min_autonomy: float = 0.1  # Almost no autonomy
    max_autonomy: float = 1.0  # Full autonomy


class SystemTrustThermometer:
    """
    The master trust thermometer for the entire Grace system.

    Aggregates:
    - Component KPI trust scores (from KPITracker)
    - Pillar success rates (from PillarTracker)
    - Data trust scores (from ConfidenceScorer/CascadeEngine)
    - Recent performance metrics

    Outputs:
    - Single temperature (0.0 - 1.0)
    - System mode (aggressive/confident/cautious/conservative/paranoid)
    - Verification multiplier (how much more/less to verify)
    - Autonomy level (how autonomous Grace should be)
    """

    def __init__(self, config: Optional[ThermometerConfig] = None):
        self.config = config or ThermometerConfig()
        self.readings: List[ThermometerReading] = []
        self._component_scores: Dict[str, float] = {}
        self._pillar_scores: Dict[str, float] = {}
        self._data_trust_score: float = 0.5
        self._recent_performance: float = 0.5
        logger.info("[THERMOMETER] System Trust Thermometer initialized")

    def update_component_score(
        self, component_name: str, trust_score: float
    ) -> None:
        """Update trust score for a component."""
        self._component_scores[component_name] = max(
            0.0, min(1.0, trust_score)
        )

    def update_pillar_score(
        self, pillar_name: str, success_rate: float
    ) -> None:
        """Update success rate for a pillar."""
        self._pillar_scores[pillar_name] = max(0.0, min(1.0, success_rate))

    def update_data_trust(self, average_trust: float) -> None:
        """Update average data trust score."""
        self._data_trust_score = max(0.0, min(1.0, average_trust))

    def update_recent_performance(self, score: float) -> None:
        """Update recent performance score."""
        self._recent_performance = max(0.0, min(1.0, score))

    def read_temperature(self) -> ThermometerReading:
        """
        Take a reading of the system trust thermometer.

        Returns:
            ThermometerReading with current temperature, mode, and settings
        """
        # Calculate component aggregate
        if self._component_scores:
            component_avg = sum(self._component_scores.values()) / len(
                self._component_scores
            )
        else:
            component_avg = 0.5

        # Calculate pillar aggregate
        if self._pillar_scores:
            pillar_avg = sum(self._pillar_scores.values()) / len(
                self._pillar_scores
            )
        else:
            pillar_avg = 0.5

        # Calculate weighted temperature
        temperature = (
            component_avg * self.config.component_weight
            + pillar_avg * self.config.pillar_weight
            + self._data_trust_score * self.config.data_trust_weight
            + self._recent_performance * self.config.recent_performance_weight
        )

        temperature = max(0.0, min(1.0, temperature))

        # Determine mode
        mode = self._determine_mode(temperature)

        # Calculate verification multiplier
        verification_multiplier = self._calculate_verification_multiplier(
            temperature
        )

        # Calculate autonomy level
        autonomy_level = self._calculate_autonomy(temperature)

        reading = ThermometerReading(
            temperature=temperature,
            mode=mode,
            component_scores=dict(self._component_scores),
            pillar_scores=dict(self._pillar_scores),
            data_trust_score=self._data_trust_score,
            verification_multiplier=verification_multiplier,
            autonomy_level=autonomy_level,
        )

        self.readings.append(reading)

        logger.info(
            f"[THERMOMETER] Temperature={temperature:.2f} "
            f"Mode={mode.value} "
            f"Verify={verification_multiplier:.1f}x "
            f"Autonomy={autonomy_level:.2f}"
        )

        return reading

    def _determine_mode(self, temperature: float) -> SystemMode:
        """Determine operational mode from temperature."""
        if temperature >= self.config.aggressive_threshold:
            return SystemMode.AGGRESSIVE
        elif temperature >= self.config.confident_threshold:
            return SystemMode.CONFIDENT
        elif temperature >= self.config.cautious_threshold:
            return SystemMode.CAUTIOUS
        elif temperature >= self.config.conservative_threshold:
            return SystemMode.CONSERVATIVE
        else:
            return SystemMode.PARANOID

    def _calculate_verification_multiplier(
        self, temperature: float
    ) -> float:
        """
        Calculate how much to multiply verification efforts.

        High temperature = less verification (multiplier < 1.0)
        Low temperature = more verification (multiplier > 1.0)
        """
        # Inverse relationship: low temp = high multiplier
        # Map [0,1] temperature to [max_mult, min_mult]
        mult_range = (
            self.config.max_verification_multiplier
            - self.config.min_verification_multiplier
        )
        multiplier = (
            self.config.max_verification_multiplier - (temperature * mult_range)
        )
        return max(
            self.config.min_verification_multiplier,
            min(self.config.max_verification_multiplier, multiplier),
        )

    def _calculate_autonomy(self, temperature: float) -> float:
        """
        Calculate autonomy level from temperature.

        High temperature = high autonomy
        Low temperature = low autonomy
        """
        autonomy_range = self.config.max_autonomy - self.config.min_autonomy
        autonomy = self.config.min_autonomy + (temperature * autonomy_range)
        return max(
            self.config.min_autonomy,
            min(self.config.max_autonomy, autonomy),
        )

    def get_current_mode(self) -> SystemMode:
        """Get current operational mode."""
        if self.readings:
            return self.readings[-1].mode
        return SystemMode.CAUTIOUS

    def get_current_temperature(self) -> float:
        """Get current temperature."""
        if self.readings:
            return self.readings[-1].temperature
        return 0.5

    def get_temperature_trend(
        self, window: int = 10
    ) -> str:
        """
        Get temperature trend over recent readings.

        Returns:
            'rising', 'falling', or 'stable'
        """
        if len(self.readings) < 2:
            return "stable"

        recent = self.readings[-min(window, len(self.readings)):]
        if len(recent) < 2:
            return "stable"

        first_half = recent[: len(recent) // 2]
        second_half = recent[len(recent) // 2:]

        avg_first = sum(r.temperature for r in first_half) / len(first_half)
        avg_second = sum(r.temperature for r in second_half) / len(second_half)

        diff = avg_second - avg_first
        if diff > 0.03:
            return "rising"
        elif diff < -0.03:
            return "falling"
        return "stable"

    def get_stats(self) -> Dict[str, Any]:
        """Get thermometer statistics."""
        if not self.readings:
            return {
                "current_temperature": 0.5,
                "current_mode": SystemMode.CAUTIOUS.value,
                "trend": "stable",
                "total_readings": 0,
            }

        latest = self.readings[-1]
        temps = [r.temperature for r in self.readings]

        return {
            "current_temperature": latest.temperature,
            "current_mode": latest.mode.value,
            "verification_multiplier": latest.verification_multiplier,
            "autonomy_level": latest.autonomy_level,
            "trend": self.get_temperature_trend(),
            "total_readings": len(self.readings),
            "average_temperature": sum(temps) / len(temps),
            "min_temperature": min(temps),
            "max_temperature": max(temps),
            "component_scores": latest.component_scores,
            "pillar_scores": latest.pillar_scores,
        }
