import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import logging

# We will hook this into the immutable log or root registry later as needed.
logger = logging.getLogger("clarity_framework")

class ClarityDecision(BaseModel):
    """
    A decision record capturing the 5W1H reasoning for autonomous choices.
    """
    id: str = Field(..., description="Unique decision ID, e.g., 'decision_1_20251123135820'")
    what: str = Field(..., description="Summary of the event or action")
    why: str = Field(..., description="Rationale, linked cause, policy references")
    who: Dict = Field(..., description="Actor(s), service account, requester")
    where: Dict = Field(..., description="Subsystem/kernel IDs, environment metadata")
    when: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    how: Dict = Field(..., description="Chosen playbook/mission, steps, expected outcome")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="0-1 scale, feeds Governance")
    related_ids: List[str] = Field(default_factory=list, description="Mission IDs, playbook IDs, handshake IDs")


class ClarityFramework:
    """
    The decision-log subsystem that records every significant Guardian/cognitive action.
    Provides auditable reasoning for autonomous choices.
    """

    @staticmethod
    def _generate_decision_id() -> str:
        """Generates a unique ID for a clarity decision."""
        # Format: decision_<timestamp>_<uuid4_prefix>
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4()).split("-")[0]
        return f"decision_{timestamp}_{short_uuid}"

    @classmethod
    def record_decision(
        cls,
        what: str,
        why: str,
        who: Dict,
        where: Dict,
        how: Dict,
        risk_score: float,
        related_ids: Optional[List[str]] = None
    ) -> ClarityDecision:
        """
        Records a new decision in the clarity framework.
        
        Args:
            what: Summary of the event or action.
            why: Rationale, linked cause, policy references.
            who: Actor(s), service account, requester.
            where: Subsystem/kernel IDs, environment metadata.
            how: Chosen playbook/mission, steps, expected outcome.
            risk_score: 0-1 scale assessing the risk of the action.
            related_ids: Optional list of associated IDs (missions, playbooks, etc.)
            
        Returns:
            The created ClarityDecision object.
        """
        decision_id = cls._generate_decision_id()
        
        decision = ClarityDecision(
            id=decision_id,
            what=what,
            why=why,
            who=who,
            where=where,
            how=how,
            risk_score=risk_score,
            related_ids=related_ids or []
        )
        
        # In a full implementation, this would persist to the `root_registry`
        # and emit an event to the `immutable_log`.
        # For now, we log it to stdout/file.
        logger.info(
            f"Clarity analysis complete: {decision.id} "
            f"| What: {decision.what} "
            f"| Risk: {decision.risk_score:.2f} "
            f"| Why: {decision.why}"
        )
        
        return decision
