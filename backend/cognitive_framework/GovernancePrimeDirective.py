import logging
from typing import Dict, Any
from backend.constitutional.grace_charter import GraceCharter

logger = logging.getLogger("governance_prime")

class GovernancePrimeDirective:
    """
    Enforces constitutional constraints on any action the framework proposes.
    Queries GraceCharter to assert compliance before execution.
    """
    def __init__(self):
        self.charter = GraceCharter()
        
    def evaluate_action(self, proposed_action: str, risk_score: float) -> bool:
        """
        Evaluates a proposed action against Pillar 5 (Cohabitation) and 
        Clause 4 (Approval thresholds).
        """
        is_acceptable = self.charter.is_risk_acceptable(risk_score)
        if not is_acceptable:
            logger.warning(
                f"Governance Rejected Action {proposed_action}. "
                f"Risk score {risk_score} exceeds 0.7 limit."
            )
            return False
            
        logger.info(f"Governance Approved Action {proposed_action}. Risk: {risk_score}.")
        return True
