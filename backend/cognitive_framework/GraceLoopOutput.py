from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class GraceLoopOutput(BaseModel):
    """
    Captures the results from missions/healing/testing and feeds them 
    back into knowledge + learning loops.
    """
    loop_id: str = Field(..., description="Unique ID for the learning/healing loop")
    decision_id: str = Field(..., description="Clarity decision ID that initiated it")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="success, failure, or partial")
    mttr_seconds: Optional[int] = Field(None)
    artifacts_produced: list[str] = Field(default_factory=list)
    knowledge_updates: Dict[str, Any] = Field(default_factory=dict)
