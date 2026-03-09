import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from .events import CognitiveEvent
from .dependency_graph import DependencyGraph
from .escalation_manager import EscalationManager
from .consequence_engine import ConsequenceEngine
from .cognitive_playbook_executor import PlaybookExecutor
from backend.core.clarity_framework import ClarityFramework

logger = logging.getLogger("cognitive_framework")

class CognitiveFramework:
    """
    Orchestrator for Grace's perception, reasoning, and response logic.
    Coordinates between triggers, decision graphs, policies, and playbooks.
    """
    def __init__(self):
        self.dependency_graph = DependencyGraph()
        self.consequence_engine = ConsequenceEngine(self.dependency_graph)
        self.escalation_manager = EscalationManager()
        self.playbook_executor = PlaybookExecutor()
        logger.info("Cognitive Framework Initialized")

    def process_event(self, event: CognitiveEvent) -> Optional[Dict[str, Any]]:
        """
        Main entry point for processing incoming signals (warnings, errors, etc.)
        """
        logger.info(f"Processing cognitive event: {event.id} ({event.type})")
        
        # 1. Dependency Context & Blast Radius
        impacted = self.dependency_graph.get_impacted_components(event.source_component)
        blast_radius = self.consequence_engine.simulate_consequences(event, impacted)
        
        # 2. Determine Escalation Level and Response
        response_plan = self.escalation_manager.determine_response(event, blast_radius.risk_score)
        
        # 3. Record the Decision via Clarity Framework
        decision = ClarityFramework.record_decision(
            what=f"Processed event {event.type} from {event.source_component}",
            why=f"Escalation level {response_plan.get('level')} triggered due to risk {blast_radius.risk_score:.2f}",
            who={"actor": "cognitive_framework"},
            where={"impacted_components": impacted},
            how=response_plan,
            risk_score=blast_radius.risk_score,
            related_ids=[event.id]
        )
        
        # 4. Execute the Response
        execution_result = None
        if response_plan.get("playbook"):
            execution_result = self.playbook_executor.execute(response_plan["playbook"], event, decision.id)
            
        return {
            "decision_id": decision.id,
            "execution_result": execution_result
        }
