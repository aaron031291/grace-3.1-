"""
Architecture Proposer

Allows users to submit a simple JSON specification for a new component.
Grace (via Qwen) queries the ArchitectureCompass to find integration points,
determines a 'Need Score', and formulates an integration plan.
If the user accepts the proposal, the specification is handed over to the 
HUNTER Assimilator coding agent for autonomous assembly and deployment.
"""

import json
import logging
from typing import Dict, Any
from llm_orchestrator.factory import get_llm_client

logger = logging.getLogger(__name__)

class ArchitectureProposer:
    def __init__(self):
        self.proposals: Dict[str, Dict[str, Any]] = {}

    def propose(self, json_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a JSON component spec and return a proposal with a need score."""
        name = json_spec.get("name", "Unknown Component")
        desc = json_spec.get("description", "No description provided")
        caps = json_spec.get("capabilities", [])

        # 1. Query Grace's Architecture Compass
        compass_context = ""
        try:
            from cognitive.architecture_compass import get_compass
            compass = get_compass()
            # Find what existing components might handle similar tasks
            existing = set()
            for cap in caps:
                existing.update(compass.find_for(cap))
            if existing:
                compass_context = f"\nExisting components with similar capabilities: {', '.join(existing)}\n"
            else:
                compass_context = "\nNo existing components claim these precise capabilities. This is a novel addition.\n"
            
            # Context about total system scale
            diag = compass.diagnose()
            compass_context += f"Total components in Grace: {diag.get('total_components', '?')}\n"
        except Exception as e:
            logger.error(f"[Proposer] Failed to query compass: {e}")
            compass_context = "Could not reach ArchitectureCompass."

        # 2. Query Qwen to analyze the need and formulate the integration plan
        prompt = f"""
You are Grace's Chief Software Architect. A user has proposed adding the following new component to your architecture:

COMPONENT SPECIFICATION:
Name: {name}
Description: {desc}
Capabilities: {', '.join(caps)}

CURRENT ARCHITECTURE STATE:
{compass_context}

TASK:
1. Determine how much Grace NEEDS this component (0-10 scale). 
   - 10 = Solves critical missing capability
   - 5 = Nice to have, overlaps slightly
   - 1 = Completely redundant
2. List 1-3 existing Grace components this new module should connect to (Incoming/Outgoing).
3. Briefly explain the **Value Proposition** of building this.

FORMAT YOUR RESPONSE AS STRICT JSON ONLY:
{{
  "need_score": 8.5,
  "connections": ["cognitive/event_bus.py", "database/connection.py"],
  "value_proposition": "Short explanation of value"
}}
"""
        
        try:
            # Use Qwen/reasoner for logical architecture planning
            try:
                from llm_orchestrator.factory import get_llm_for_task
                qwen = get_llm_for_task("reason")
            except Exception:
                qwen = get_llm_client()
            response = qwen.generate(
                prompt=prompt,
                system_prompt="You are the Architect. Output only raw JSON.",
                temperature=0.2,
            )
            # Normalize to string (LLM may return dict with "response"/"content" or raw string)
            if isinstance(response, dict):
                response = response.get("response", response.get("content", str(response)))
            text = response if isinstance(response, str) else str(response)

            # Parse the JSON response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                raw_json = text[start:end]
            else:
                raw_json = text
            prediction = json.loads(raw_json)
        except Exception as e:
            logger.error(f"[Proposer] LLM Generation failed: {e}")
            prediction = {
                "need_score": 5.0,
                "connections": ["api/brain_api_v2.py"],
                "value_proposition": f"Could not analyze via LLM (Error: {e}). Defaulting to standard API integration."
            }

        proposal_id = f"prop_{len(self.proposals) + 1}"
        
        proposal = {
            "proposal_id": proposal_id,
            "spec": json_spec,
            "score": prediction.get("need_score", 5.0),
            "connections": prediction.get("connections", []),
            "value": prediction.get("value_proposition", ""),
            "status": "proposed"
        }
        self.proposals[proposal_id] = proposal
        return proposal

    def build(self, proposal_id: str) -> Dict[str, Any]:
        """Trigger the HUNTER Assimilator to build the proposed component."""
        if proposal_id not in self.proposals:
            return {"error": "Proposal not found."}
            
        proposal = self.proposals[proposal_id]
        spec = proposal["spec"]
        
        prompt = f"""
I am using the HUNTER protocol. Build the following component and integrate it into Grace:

Name: {spec.get("name")}
Description: {spec.get("description")}
Capabilities: {', '.join(spec.get("capabilities", []))}

It should connect to: {', '.join(proposal.get("connections", []))}
Value: {proposal.get("value")}

Write the full Python code for this component. Ensure it uses standard Grace imports (like `logger`).
Provide the code in a standard markdown filepath block, e.g. ```filepath: cognitive/new_component.py
"""
        try:
            from cognitive.hunter_assimilator import get_hunter
            hunter = get_hunter()
            result = hunter.assimilate(code=prompt, description=f"Auto-Building Architect Proposal: {spec.get('name')}", user="Architect")
            
            proposal["status"] = "building"
            proposal["hunter_request_id"] = result.request_id
            
            return {
                "status": "building",
                "message": "Handed over to HUNTER Assimilator",
                "request_id": result.request_id,
            }
        except Exception as e:
            logger.error(f"[Proposer] Failed to trigger builder: {e}")
            return {"error": f"Failed to start builder: {e}"}

_proposer = None
def get_architecture_proposer() -> ArchitectureProposer:
    global _proposer
    if _proposer is None:
        _proposer = ArchitectureProposer()
    return _proposer
