from pydantic import BaseModel, Field
import uuid

class HealingAction(BaseModel):
    """
    Contract required by the Constitutional Stack for all automated self-healing.
    See: Grace Blueprint (Deep-Dive) Pillar 3.
    """
    action_id: str = Field(default_factory=lambda: f"heal_{uuid.uuid4().hex[:8]}", description="Unique identifier for the action")
    trigger: str = Field(..., description="The Guardian or OS event that triggered this action")
    playbook_id: str = Field(..., description="Reference to the YAML playbook executing the remediation")
    risk: float = Field(..., ge=0.0, le=1.0, description="Risk assessment of the action. Escalate if > 0.7")
    mttr_goal: int = Field(..., description="Target Mean Time To Recovery in seconds (e.g. 60 or 300)")

    def is_escalation_required(self) -> bool:
        """Returns True if this action's risk score exceeds constitutional thresholds."""
        return self.risk > 0.7
