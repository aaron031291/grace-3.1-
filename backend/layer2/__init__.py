"""
Layer 2 - Higher-Level Orchestration Layer

Layer 2 components operate on top of Layer 1 and provide:
- Higher-level coordination
- Cross-component intelligence
- Autonomous decision-making
- Self-healing and maintenance

Components:
- Self-Healing Agent: Autonomous issue detection and fixing
"""

import logging

_logger = logging.getLogger(__name__)

# Import Layer 2 components
try:
    from .self_healing_connector import SelfHealingConnector
except ImportError as e:
    _logger.warning(f"Could not import self_healing_connector: {e}")
    SelfHealingConnector = None

__all__ = [
    "SelfHealingConnector",
]
