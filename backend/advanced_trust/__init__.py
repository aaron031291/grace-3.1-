"""
Advanced Trust System for Grace.

Seven interconnected subsystems that provide deep trust management:
1. Confidence Cascading - Provenance chain trust propagation
2. Adversarial Self-Testing - Break own outputs before trusting them
3. Competence Boundaries - Domain accuracy tracking and auto-behavior
4. Cross-Pillar Learning - Pillars teaching each other
5. Trust Decay + Auto Re-verification - Time-based trust degradation
6. System-Wide Trust Thermometer - Single master confidence knob
7. Meta-Learning on Verification - Learn which verification strategies work best

Plus:
- Pillar Tracking Tables - Track self-building, self-healing, self-learning, self-governing
- KPI Mechanism - Per-domain, per-pillar KPI aggregation
- Verification Pipeline - Dynamic, strategy-aware verification
"""

from .confidence_cascading import ConfidenceCascadeEngine
from .adversarial_self_testing import AdversarialSelfTester
from .competence_boundaries import CompetenceBoundaryTracker
from .cross_pillar_learning import CrossPillarLearningEngine
from .trust_decay import TrustDecayEngine
from .trust_thermometer import SystemTrustThermometer
from .meta_verification_learner import MetaVerificationLearner
from .pillar_tracker import PillarTracker, Pillar, PillarEvent
from .verification_pipeline import VerificationPipeline, VerificationStrategy

__all__ = [
    "ConfidenceCascadeEngine",
    "AdversarialSelfTester",
    "CompetenceBoundaryTracker",
    "CrossPillarLearningEngine",
    "TrustDecayEngine",
    "SystemTrustThermometer",
    "MetaVerificationLearner",
    "PillarTracker",
    "Pillar",
    "PillarEvent",
    "VerificationPipeline",
    "VerificationStrategy",
]
