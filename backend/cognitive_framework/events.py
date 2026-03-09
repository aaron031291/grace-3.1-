from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from typing import Dict, Any

class CognitiveEvent(BaseModel):
    """
    Normalizes incoming signals from Guardian, agents, and HTM anomalies.
    """
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    type: str = Field(..., description="E.g., guardian.warning, mission.failed, htm.anomaly.detected")
    source_component: str = Field(..., description="Component emitting the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: int = Field(default=1, ge=1, le=5)
    recurrence_count: int = Field(default=0)
    payload: Dict[str, Any] = Field(default_factory=dict)
