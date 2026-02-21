"""
Intelligence Synthesis Engine

Aggregates data from all connectors, detects trends over time,
scores opportunities, and produces actionable intelligence reports.
This is Grace's "thinking" layer for business intelligence.
"""

from .intelligence_engine import IntelligenceEngine
from .trend_detector import TrendDetector
from .opportunity_scorer import OpportunityScorer
from .reasoning_engine import BIReasoningEngine
