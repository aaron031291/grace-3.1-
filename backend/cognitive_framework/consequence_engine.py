from typing import List, Dict, Any
from .events import CognitiveEvent
from .dependency_graph import DependencyGraph

class ConsequenceResult:
    def __init__(self, risk_score: float, description: str):
        self.risk_score = risk_score
        self.description = description

class ConsequenceEngine:
    """
    Simulates the blast radius of potential actions using the dependency graph,
    ensuring compliance with risk thresholds.
    """
    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        
    def simulate_consequences(self, event: CognitiveEvent, impacted_components: List[str]) -> ConsequenceResult:
        """
        Computes risk based on severity, recurrence, and number of impacted downstream systems.
        """
        base_risk = event.severity * 0.1
        recurrence_penalty = min(event.recurrence_count * 0.05, 0.2)
        impact_penalty = min(len(impacted_components) * 0.05, 0.4)
        
        # Risk caps at 1.0
        total_risk = min(base_risk + recurrence_penalty + impact_penalty, 1.0)
        
        description = (
            f"Event {event.id} from {event.source_component} impacts {len(impacted_components)} downstream components. "
            f"Severity {event.severity}, Occurred {event.recurrence_count} times."
        )
        return ConsequenceResult(risk_score=total_risk, description=description)
