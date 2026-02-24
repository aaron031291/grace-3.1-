"""
Grace OS — Layer Messaging Protocol

Defines the core data structures for asynchronous, mesh-based inter-layer 
communication within Grace OS.
"""

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

@dataclass
class LayerMessage:
    """
    Represents a structured request sent from one Grace OS layer to another.
    """
    from_layer: str
    to_layer: str  # Can be a specific layer name (e.g., "L5") or "*" for broadcast
    message_type: str
    payload: Dict[str, Any]
    
    # Tracking and tracing
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_message_id: Optional[str] = None
    
    # Priority and routing
    priority: int = 0  # 0 = normal, 1 = high, 2 = critical
    max_depth: int = 10  # Recursion budget to prevent infinite loops
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class LayerResponse:
    """
    Represents the result returned by a layer after processing a LayerMessage.
    """
    message_id: str
    from_layer: str
    status: str  # "success" | "failure" | "partial" | "delegated"
    payload: Dict[str, Any]
    
    # Confidence and audit
    trust_score: float = 0.0  # 0.0 to 100.0 confidence rating
    duration_ms: int = 0
    tool_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    child_messages: List[str] = field(default_factory=list)  # IDs of messages spawned
