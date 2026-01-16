"""
TimeSense Engine - Grace's Empirical Time Calibration System

This subsystem gives Grace a "clock" grounded in physics (CPU, disk, network),
not assumptions. It continuously measures throughput/latency for primitive
operations, learns scaling laws, and predicts runtime with uncertainty bounds.

Core Capabilities:
- Benchmark primitive operations (disk I/O, network, CPU, LLM, DB)
- Learn scaling laws (time = a + b*size with confidence intervals)
- Predict task duration with uncertainty (p50/p90/p95)
- Continuously calibrate predictions against actual results
- Adapt to changing system conditions (cache state, load, etc.)

Architecture:
- TimeSenseEngine: Main orchestrator
- PrimitiveRegistry: Catalog of benchmarkable operations
- CalibrationService: Runs benchmarks and updates profiles
- TimePredictor: Predicts duration with uncertainty
- TimeSenseConnector: Layer 1 message bus integration
"""

from timesense.engine import TimeSenseEngine, get_timesense_engine
from timesense.primitives import (
    PrimitiveType,
    PrimitiveCategory,
    Primitive,
    PrimitiveRegistry,
    get_primitive_registry
)
from timesense.predictor import TimePredictor, PredictionResult
from timesense.profiles import TimeProfile, ProfileManager
from timesense.benchmarks import CalibrationService

__all__ = [
    'TimeSenseEngine',
    'get_timesense_engine',
    'PrimitiveType',
    'PrimitiveCategory',
    'Primitive',
    'PrimitiveRegistry',
    'get_primitive_registry',
    'TimePredictor',
    'PredictionResult',
    'TimeProfile',
    'ProfileManager',
    'CalibrationService'
]
