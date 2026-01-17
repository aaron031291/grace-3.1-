"""
Dependency Resolution for Enterprise Launcher

Resolves service dependencies and determines optimal startup order.
Similar to Kubernetes init containers, Docker Compose, and systemd.
"""

import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Type of service dependency."""
    REQUIRED = "required"    # Must be available
    OPTIONAL = "optional"    # Can start without it
    CONDITIONAL = "conditional"  # Required if other services are present


@dataclass
class ServiceDefinition:
    """Definition of a service and its dependencies."""
    name: str
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    service_type: ServiceType = ServiceType.REQUIRED
    startup_timeout: int = 120
    health_check_endpoint: Optional[str] = None
    start_command: Optional[List[str]] = None


class DependencyResolver:
    """
    Resolves service dependencies and startup order.
    
    Features:
    - Dependency graph building
    - Topological sort for startup order
    - Parallel startup where possible
    - Circular dependency detection
    """
    
    def __init__(self):
        """Initialize dependency resolver."""
        self.services: Dict[str, ServiceDefinition] = {}
        self._build_service_definitions()
    
    def _build_service_definitions(self):
        """Build service dependency definitions."""
        self.services = {
            "database": ServiceDefinition(
                name="database",
                dependencies=[],
                service_type=ServiceType.REQUIRED,
                startup_timeout=30
            ),
            "backend": ServiceDefinition(
                name="backend",
                dependencies=["database"],
                optional_dependencies=["qdrant", "ollama"],
                service_type=ServiceType.REQUIRED,
                startup_timeout=120,
                health_check_endpoint="/health"
            ),
            "qdrant": ServiceDefinition(
                name="qdrant",
                dependencies=[],
                service_type=ServiceType.OPTIONAL,
                startup_timeout=60
            ),
            "ollama": ServiceDefinition(
                name="ollama",
                dependencies=[],
                service_type=ServiceType.OPTIONAL,
                startup_timeout=30
            ),
            "frontend": ServiceDefinition(
                name="frontend",
                dependencies=["backend"],
                service_type=ServiceType.OPTIONAL,
                startup_timeout=30
            )
        }
    
    def resolve_startup_order(self, required_only: bool = False) -> List[List[str]]:
        """
        Resolve optimal startup order using topological sort.
        
        Returns:
            List of service groups that can start in parallel
            Each group is a list of service names
        """
        # Build dependency graph
        graph = {}
        for name, service in self.services.items():
            if required_only and service.service_type != ServiceType.REQUIRED:
                continue
            graph[name] = set(service.dependencies)
        
        # Topological sort with parallel groups
        startup_groups = []
        remaining = set(graph.keys())
        completed = set()
        
        while remaining:
            # Find services with no uncompleted dependencies
            ready = []
            for service in remaining:
                deps = graph.get(service, set())
                if deps.issubset(completed):
                    ready.append(service)
            
            if not ready:
                # Circular dependency or missing dependency
                unresolved = remaining - completed
                raise RuntimeError(
                    f"Cannot resolve dependencies. "
                    f"Circular or missing dependencies: {unresolved}"
                )
            
            # Add ready services to current group
            startup_groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)
        
        logger.info(f"[DEPENDENCY-RESOLVER] Startup order: {startup_groups}")
        return startup_groups
    
    def get_service_dependencies(self, service_name: str) -> Dict[str, List[str]]:
        """
        Get dependencies for a service.
        
        Returns:
            Dict with 'required' and 'optional' dependency lists
        """
        service = self.services.get(service_name)
        if not service:
            return {"required": [], "optional": []}
        
        return {
            "required": service.dependencies,
            "optional": service.optional_dependencies
        }
    
    def can_start_without(self, service_name: str, missing_services: Set[str]) -> bool:
        """
        Check if a service can start without certain dependencies.
        
        Args:
            service_name: Service to check
            missing_services: Set of missing service names
            
        Returns:
            True if service can start without missing dependencies
        """
        service = self.services.get(service_name)
        if not service:
            return False
        
        # Check required dependencies
        required_missing = set(service.dependencies) & missing_services
        if required_missing:
            return False
        
        # Optional dependencies can be missing
        return True
    
    def get_startup_plan(self, available_services: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Get complete startup plan.
        
        Args:
            available_services: Set of available service names (None = all)
            
        Returns:
            Startup plan with order, dependencies, and timing
        """
        if available_services is None:
            available_services = set(self.services.keys())
        
        # Resolve startup order
        startup_groups = self.resolve_startup_order(required_only=False)
        
        # Filter to available services
        filtered_groups = []
        for group in startup_groups:
            filtered = [s for s in group if s in available_services]
            if filtered:
                filtered_groups.append(filtered)
        
        # Calculate timing
        total_timeout = 0
        for group in filtered_groups:
            group_timeout = max(
                self.services[s].startup_timeout
                for s in group
                if s in self.services
            )
            total_timeout += group_timeout
        
        return {
            "startup_groups": filtered_groups,
            "total_timeout": total_timeout,
            "services": {
                name: {
                    "dependencies": svc.dependencies,
                    "optional_dependencies": svc.optional_dependencies,
                    "type": svc.service_type.value,
                    "timeout": svc.startup_timeout
                }
                for name, svc in self.services.items()
                if name in available_services
            }
        }
