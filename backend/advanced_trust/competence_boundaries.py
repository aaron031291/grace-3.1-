"""
Competence Boundary Tracker

Grace should know what she's good at and what she's not.
"I'm 95% accurate on Python questions, 60% on Kubernetes, and 30% on legal."

The KPI tracking per domain gives her this data over time. When she's in a
low-competence domain, she automatically verifies more aggressively and
warns the user. When she's in a high-competence domain, she can be more
autonomous.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CompetenceLevel(str, Enum):
    """Competence levels for a domain."""
    EXPERT = "expert"               # 90-100% accuracy
    PROFICIENT = "proficient"       # 75-89% accuracy
    COMPETENT = "competent"         # 60-74% accuracy
    DEVELOPING = "developing"       # 40-59% accuracy
    NOVICE = "novice"               # 20-39% accuracy
    UNCHARTED = "uncharted"         # <20% or insufficient data


class AutonomyLevel(str, Enum):
    """How autonomous Grace should be in this domain."""
    FULL_AUTONOMY = "full_autonomy"       # Act without asking
    HIGH_AUTONOMY = "high_autonomy"       # Act, but log everything
    MODERATE_AUTONOMY = "moderate_autonomy"  # Act, verify important steps
    LOW_AUTONOMY = "low_autonomy"         # Verify before every action
    SUPERVISED = "supervised"             # Ask user before every action


@dataclass
class DomainOutcome:
    """A recorded outcome in a domain."""
    domain: str
    query_type: str
    success: bool
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainCompetence:
    """Tracked competence for a single domain."""
    domain: str
    total_attempts: int = 0
    successful_attempts: int = 0
    accuracy: float = 0.0
    confidence_sum: float = 0.0
    competence_level: CompetenceLevel = CompetenceLevel.UNCHARTED
    autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED
    verification_intensity: float = 1.0  # 0.0=none, 1.0=maximum
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trend: str = "stable"  # improving, stable, declining
    recent_window_accuracy: float = 0.0
    warn_user: bool = True


@dataclass
class CompetenceReport:
    """Overall competence report."""
    total_domains: int
    domains: Dict[str, DomainCompetence]
    strongest_domains: List[Tuple[str, float]]
    weakest_domains: List[Tuple[str, float]]
    overall_accuracy: float
    overall_competence: CompetenceLevel
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CompetenceBoundaryTracker:
    """
    Tracks per-domain accuracy to determine competence boundaries.

    When Grace operates in a domain, every outcome is recorded. Over time,
    this builds a competence profile that determines:
    - How much to verify in each domain
    - When to warn the user
    - How autonomous Grace can be
    """

    # Thresholds for competence levels
    THRESHOLDS = {
        CompetenceLevel.EXPERT: 0.90,
        CompetenceLevel.PROFICIENT: 0.75,
        CompetenceLevel.COMPETENT: 0.60,
        CompetenceLevel.DEVELOPING: 0.40,
        CompetenceLevel.NOVICE: 0.20,
        CompetenceLevel.UNCHARTED: 0.0,
    }

    # Mapping: competence -> autonomy
    AUTONOMY_MAP = {
        CompetenceLevel.EXPERT: AutonomyLevel.FULL_AUTONOMY,
        CompetenceLevel.PROFICIENT: AutonomyLevel.HIGH_AUTONOMY,
        CompetenceLevel.COMPETENT: AutonomyLevel.MODERATE_AUTONOMY,
        CompetenceLevel.DEVELOPING: AutonomyLevel.LOW_AUTONOMY,
        CompetenceLevel.NOVICE: AutonomyLevel.SUPERVISED,
        CompetenceLevel.UNCHARTED: AutonomyLevel.SUPERVISED,
    }

    # Mapping: competence -> verification intensity
    VERIFICATION_MAP = {
        CompetenceLevel.EXPERT: 0.1,
        CompetenceLevel.PROFICIENT: 0.3,
        CompetenceLevel.COMPETENT: 0.5,
        CompetenceLevel.DEVELOPING: 0.7,
        CompetenceLevel.NOVICE: 0.9,
        CompetenceLevel.UNCHARTED: 1.0,
    }

    # Minimum attempts before establishing competence
    MIN_ATTEMPTS = 5
    # Window size for trend analysis
    RECENT_WINDOW = 20

    def __init__(self, min_attempts: int = MIN_ATTEMPTS, recent_window: int = RECENT_WINDOW):
        self.min_attempts = min_attempts
        self.recent_window = recent_window
        self.domains: Dict[str, DomainCompetence] = {}
        self.outcomes: Dict[str, List[DomainOutcome]] = defaultdict(list)
        logger.info("[COMPETENCE] Boundary Tracker initialized")

    def record_outcome(
        self,
        domain: str,
        success: bool,
        confidence: float = 0.5,
        query_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DomainCompetence:
        """
        Record an outcome in a domain.

        Args:
            domain: Knowledge domain
            success: Whether the outcome was successful
            confidence: Confidence in the outcome
            query_type: Type of query/task
            metadata: Additional metadata

        Returns:
            Updated DomainCompetence
        """
        outcome = DomainOutcome(
            domain=domain,
            query_type=query_type,
            success=success,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.outcomes[domain].append(outcome)

        # Update or create competence
        if domain not in self.domains:
            self.domains[domain] = DomainCompetence(domain=domain)

        comp = self.domains[domain]
        comp.total_attempts += 1
        if success:
            comp.successful_attempts += 1
        comp.confidence_sum += confidence
        comp.accuracy = comp.successful_attempts / comp.total_attempts
        comp.last_updated = datetime.now(timezone.utc)

        # Calculate recent window accuracy for trend
        recent = self.outcomes[domain][-self.recent_window:]
        if len(recent) >= self.min_attempts:
            recent_successes = sum(1 for o in recent if o.success)
            comp.recent_window_accuracy = recent_successes / len(recent)
        else:
            comp.recent_window_accuracy = comp.accuracy

        # Determine trend
        if comp.total_attempts >= self.min_attempts * 2:
            older = self.outcomes[domain][-self.recent_window * 2:-self.recent_window]
            if older:
                older_acc = sum(1 for o in older if o.success) / len(older)
                if comp.recent_window_accuracy > older_acc + 0.05:
                    comp.trend = "improving"
                elif comp.recent_window_accuracy < older_acc - 0.05:
                    comp.trend = "declining"
                else:
                    comp.trend = "stable"

        # Determine competence level
        self._update_competence_level(comp)

        return comp

    def _update_competence_level(self, comp: DomainCompetence) -> None:
        """Update competence level, autonomy, and verification intensity."""
        if comp.total_attempts < self.min_attempts:
            comp.competence_level = CompetenceLevel.UNCHARTED
        else:
            acc = comp.accuracy
            if acc >= self.THRESHOLDS[CompetenceLevel.EXPERT]:
                comp.competence_level = CompetenceLevel.EXPERT
            elif acc >= self.THRESHOLDS[CompetenceLevel.PROFICIENT]:
                comp.competence_level = CompetenceLevel.PROFICIENT
            elif acc >= self.THRESHOLDS[CompetenceLevel.COMPETENT]:
                comp.competence_level = CompetenceLevel.COMPETENT
            elif acc >= self.THRESHOLDS[CompetenceLevel.DEVELOPING]:
                comp.competence_level = CompetenceLevel.DEVELOPING
            elif acc >= self.THRESHOLDS[CompetenceLevel.NOVICE]:
                comp.competence_level = CompetenceLevel.NOVICE
            else:
                comp.competence_level = CompetenceLevel.UNCHARTED

        comp.autonomy_level = self.AUTONOMY_MAP[comp.competence_level]
        comp.verification_intensity = self.VERIFICATION_MAP[comp.competence_level]
        comp.warn_user = comp.competence_level in (
            CompetenceLevel.NOVICE,
            CompetenceLevel.UNCHARTED,
            CompetenceLevel.DEVELOPING,
        )

    def get_competence(self, domain: str) -> DomainCompetence:
        """Get competence for a domain."""
        if domain not in self.domains:
            return DomainCompetence(domain=domain)
        return self.domains[domain]

    def get_autonomy_level(self, domain: str) -> AutonomyLevel:
        """Get autonomy level for a domain."""
        return self.get_competence(domain).autonomy_level

    def get_verification_intensity(self, domain: str) -> float:
        """Get verification intensity for a domain."""
        return self.get_competence(domain).verification_intensity

    def should_warn_user(self, domain: str) -> bool:
        """Should Grace warn the user about low competence?"""
        return self.get_competence(domain).warn_user

    def get_competence_report(self) -> CompetenceReport:
        """Generate a comprehensive competence report."""
        if not self.domains:
            return CompetenceReport(
                total_domains=0,
                domains={},
                strongest_domains=[],
                weakest_domains=[],
                overall_accuracy=0.0,
                overall_competence=CompetenceLevel.UNCHARTED,
            )

        # Sort domains by accuracy
        sorted_domains = sorted(
            [(d, c.accuracy) for d, c in self.domains.items()
             if c.total_attempts >= self.min_attempts],
            key=lambda x: x[1],
            reverse=True,
        )

        # Overall accuracy
        total_attempts = sum(c.total_attempts for c in self.domains.values())
        total_successes = sum(
            c.successful_attempts for c in self.domains.values()
        )
        overall_accuracy = (
            total_successes / total_attempts if total_attempts > 0 else 0.0
        )

        # Determine overall competence
        if overall_accuracy >= 0.90:
            overall_competence = CompetenceLevel.EXPERT
        elif overall_accuracy >= 0.75:
            overall_competence = CompetenceLevel.PROFICIENT
        elif overall_accuracy >= 0.60:
            overall_competence = CompetenceLevel.COMPETENT
        elif overall_accuracy >= 0.40:
            overall_competence = CompetenceLevel.DEVELOPING
        elif overall_accuracy >= 0.20:
            overall_competence = CompetenceLevel.NOVICE
        else:
            overall_competence = CompetenceLevel.UNCHARTED

        return CompetenceReport(
            total_domains=len(self.domains),
            domains=dict(self.domains),
            strongest_domains=sorted_domains[:5],
            weakest_domains=sorted_domains[-5:] if len(sorted_domains) > 5 else list(reversed(sorted_domains[:5])),
            overall_accuracy=overall_accuracy,
            overall_competence=overall_competence,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        report = self.get_competence_report()
        return {
            "total_domains": report.total_domains,
            "overall_accuracy": report.overall_accuracy,
            "overall_competence": report.overall_competence.value,
            "strongest": report.strongest_domains[:3],
            "weakest": report.weakest_domains[:3],
            "domains_by_level": {
                level.value: sum(
                    1 for c in self.domains.values()
                    if c.competence_level == level
                )
                for level in CompetenceLevel
            },
        }
