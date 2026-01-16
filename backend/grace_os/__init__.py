"""
Grace OS - Self-Healing Autonomous Coding Platform
===================================================

Grace OS integrates self-healing, genesis keys, ghost ledger, and autonomous
coding capabilities into VS Code (code-server) for a no-code friendly experience.

Core Components:
- IDE Bridge: Connects VS Code to Grace's cognitive systems
- Self-Healing IDE: Real-time code healing within the editor
- No-Code Panels: Drag-and-drop interface for non-technical users
- Autonomous Scheduler: Background task execution with voice/NLP control
- Ghost Ledger: Line-by-line code generation tracking
- Deterministic Pipeline: Multi-LLM code generation with JSON contracts
"""

from .ide_bridge import IDEBridge, IDEBridgeConfig
# from .self_healing_ide import SelfHealingIDE  # TODO: Create this module
from .nocode_panels import NoCodePanelSystem
from .autonomous_scheduler import AutonomousTaskScheduler
from .ghost_ledger import GhostLedger, GhostMemory
from .deterministic_pipeline import DeterministicCodePipeline, ExecutionContract
from .reasoning_planes import MultiPlaneReasoner, ReasoningPlane

__all__ = [
    'IDEBridge',
    'IDEBridgeConfig',
    # 'SelfHealingIDE',  # TODO: Add when module is created
    'NoCodePanelSystem',
    'AutonomousTaskScheduler',
    'GhostLedger',
    'GhostMemory',
    'DeterministicCodePipeline',
    'ExecutionContract',
    'MultiPlaneReasoner',
    'ReasoningPlane',
]

__version__ = "1.0.0"
