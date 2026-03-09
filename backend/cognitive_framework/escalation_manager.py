from typing import Dict, Any
from .events import CognitiveEvent

class EscalationManager:
    """
    Tiered response engine (Levels 0-4). Each level maps to playbooks, 
    research tasks, or user notifications.
    """
    
    def determine_response(self, event: CognitiveEvent, risk_score: float) -> Dict[str, Any]:
        """
        Level 0 (auto-heal) - run predefined playbooks if low risk.
        Level 1 (research) - spawn cognitive missions to gather context (logs, metrics, GitHub knowledge).
        Level 2/3 - engage specialized agents (coding, learning, governance) or run deeper diagnostics.
        Level 4 - notify humans with immutable log references; mark mission for manual approval.
        """
        response = {
            "risk_score": risk_score,
            "playbook": None,
            "level": 0,
            "action": "none"
        }
        
        if risk_score <= 0.3:
            response["level"] = 0
            response["action"] = "auto-heal"
            # In a full system, this would lookup playbooks. We simulate.
            response["playbook"] = f"auto_{event.type.replace('.', '_')}"
            
        elif event.type == "guardian.log_error":
            # Map log errors directly to the self-healing remediation playbook
            response["level"] = 2
            response["action"] = "self_heal"
            response["playbook"] = "log_error_remediation"
            
        elif risk_score <= 0.5:
            response["level"] = 1
            response["action"] = "research_mission"
            
        elif risk_score <= 0.7:
            response["level"] = 2
            response["action"] = "engage_agents"
            
        else:
            response["level"] = 4
            response["action"] = "human_escalation"
            
        return response
