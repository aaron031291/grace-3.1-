from typing import List

class DependencyGraph:
    """
    Tracks component/topic dependencies and supports impact analysis when an alert fires.
    """
    def __init__(self):
        self.graph = {}
        
    def add_dependency(self, source: str, target: str):
        if source not in self.graph:
            self.graph[source] = []
        self.graph[source].append(target)
        
    def get_impacted_components(self, component: str) -> List[str]:
        """Returns downstream components affected by this failure."""
        impacted = set()
        stack = [component]
        
        while stack:
            current = stack.pop()
            impacted.add(current)
            for neighbor in self.graph.get(current, []):
                if neighbor not in impacted:
                    stack.append(neighbor)
                    
        return list(impacted)
