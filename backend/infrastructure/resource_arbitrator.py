"""
resource_arbitrator.py
Dynamic Resource Arbitration for Grace's LLM ecosystem.

Assesses task risk and intelligently routes inference to specific models:
- High Risk / Critical Logic -> Opus (High Trust, Expensive)
- Low Risk / Bulk / Fast -> Qwen (Local, Fast, Cheaper)
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResourceArbitrator:
    """
    Intelligently routes tasks to the best LLM provider based on risk vs. speed tradeoffs.
    """
    
    # Simple heuristic risk keywords
    CRITICAL_KEYWORDS = [
        "architecture", "security", "database", "schema", 
        "authentication", "authorization", "financial", "payment",
        "deploy", "production", "firewall", "encryption"
    ]
    
    def __init__(self):
        pass

    def calculate_risk_score(self, task_description: str, context: Dict[str, Any] = None) -> float:
        """
        Calculate a risk score (0.0 to 1.0) for a given task.
        """
        score = 0.2 # Base baseline risk
        task_desc_lower = task_description.lower()
        
        # Keyword matching
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword in task_desc_lower:
                score += 0.3
                break
                
        # Context modifiers
        if context:
            if context.get("is_production", False):
                score += 0.4
            if context.get("requires_dry_run", False):
                score += 0.2
            if context.get("trust_required", 0) > 0.8:
                score += 0.3
                
        return min(score, 1.0)

    def route_task(self, task_description: str, context: Dict[str, Any] = None) -> str:
        """
        Routes the task to 'opus', 'kimi', or 'qwen' depending on the assessed risk.
        Returns the model_id.
        """
        risk_score = self.calculate_risk_score(task_description, context)
        
        logger.info(f"[ResourceArbitrator] Assessed task risk: {risk_score:.2f} for '{task_description[:50]}...'")
        
        if risk_score >= 0.7:
            logger.info("[ResourceArbitrator] High-Risk task -> Routing to Opus (High Trust).")
            return "opus"
        elif risk_score >= 0.4:
            logger.info("[ResourceArbitrator] Medium-Risk task -> Routing to Kimi (Balanced).")
            return "kimi"
        else:
            logger.info("[ResourceArbitrator] Low-Risk task -> Routing to Qwen (Local/Fast).")
            return "qwen"

def get_resource_arbitrator() -> ResourceArbitrator:
    return ResourceArbitrator()
