"""
GRACE Diagnostic Machine - 4-Layer Autonomous Diagnostic System

Integrates with:
- Test results (passed/failed/skipped)
- Genesis Keys (provenance tracking)
- Cognitive Framework (learning/memory)
- GRACE Mirror (self-reflection)
- Tail logs and metrics

Architecture:
- Layer 1: Sensors (data collection)
- Layer 2: Interpreters (pattern analysis)
- Layer 3: Judgement (decision making)
- Layer 4: Action Routing (response execution)

Enhanced Features:
- Notifications: Webhook, Slack, Email alerts
- Real-time: WebSocket live updates
- Cognitive: Learning Memory, Memory Mesh integration
- Trends: Historical analysis and baseline calibration
- Healing: Comprehensive self-repair actions
"""

from .sensors import SensorLayer, SensorData
from .interpreters import InterpreterLayer, InterpretedData
from .judgement import JudgementLayer, JudgementResult
from .action_router import ActionRouter, ActionDecision
from .diagnostic_engine import DiagnosticEngine

# Enhanced modules
from .notifications import (
    NotificationManager,
    NotificationPayload,
    NotificationPriority,
    get_notification_manager,
)
from .realtime import (
    ConnectionManager,
    DiagnosticEventEmitter,
    EventType,
    RealtimeEvent,
    get_connection_manager,
    get_event_emitter,
)
from .cognitive_integration import (
    CognitiveIntegrationManager,
    LearningMemoryIntegration,
    DecisionLogIntegration,
    MemoryMeshIntegration,
    get_cognitive_manager,
)
from .trend_analysis import (
    TimeSeriesStore,
    TrendAnalyzer,
    DiagnosticMetricsCollector,
    TrendResult,
    TrendDirection,
    get_time_series_store,
    get_trend_analyzer,
    get_metrics_collector,
)
from .healing import (
    HealingExecutor,
    HealingActionType,
    HealingResult,
    get_healing_executor,
    execute_healing,
)

__all__ = [
    # Core layers
    'SensorLayer',
    'SensorData',
    'InterpreterLayer',
    'InterpretedData',
    'JudgementLayer',
    'JudgementResult',
    'ActionRouter',
    'ActionDecision',
    'DiagnosticEngine',

    # Notifications
    'NotificationManager',
    'NotificationPayload',
    'NotificationPriority',
    'get_notification_manager',

    # Real-time
    'ConnectionManager',
    'DiagnosticEventEmitter',
    'EventType',
    'RealtimeEvent',
    'get_connection_manager',
    'get_event_emitter',

    # Cognitive integration
    'CognitiveIntegrationManager',
    'LearningMemoryIntegration',
    'DecisionLogIntegration',
    'MemoryMeshIntegration',
    'get_cognitive_manager',

    # Trend analysis
    'TimeSeriesStore',
    'TrendAnalyzer',
    'DiagnosticMetricsCollector',
    'TrendResult',
    'TrendDirection',
    'get_time_series_store',
    'get_trend_analyzer',
    'get_metrics_collector',

    # Healing
    'HealingExecutor',
    'HealingActionType',
    'HealingResult',
    'get_healing_executor',
    'execute_healing',
]
