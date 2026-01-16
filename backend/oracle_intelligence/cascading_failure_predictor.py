"""
Cascading Failure Predictor for Grace
======================================

Analyzes code and system interactions to predict cascading failures
before they happen, allowing proactive prevention.

A cascading failure is when one component's failure triggers failures
in dependent components, potentially bringing down the entire system.

Key Capabilities:
1. Dependency graph analysis
2. Failure propagation simulation
3. Risk scoring for each component
4. Circuit breaker recommendations
5. Fallback strategy suggestions
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class FailureMode(str, Enum):
    """Types of failures that can cascade."""
    CONNECTION_FAILURE = "connection_failure"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_CORRUPTION = "data_corruption"
    DEPENDENCY_FAILURE = "dependency_failure"
    CONFIGURATION_ERROR = "configuration_error"
    RATE_LIMIT_EXCEEDED = "rate_limit"
    MEMORY_EXHAUSTION = "memory"
    DEADLOCK = "deadlock"
    NETWORK_PARTITION = "network_partition"


class PropagationPattern(str, Enum):
    """How failures propagate."""
    DIRECT = "direct"           # A fails → B fails immediately
    DELAYED = "delayed"         # A fails → timeout → B fails
    AMPLIFIED = "amplified"     # A fails → many components fail
    CONTAINED = "contained"     # Failure is isolated
    CASCADING = "cascading"     # Chain reaction


class RiskLevel(str, Enum):
    """Risk levels for cascading failure."""
    CRITICAL = "critical"   # System-wide impact
    HIGH = "high"           # Major component impact
    MEDIUM = "medium"       # Limited impact
    LOW = "low"             # Minimal impact
    MINIMAL = "minimal"     # Isolated failure


@dataclass
class ComponentNode:
    """A component in the dependency graph."""
    component_id: str
    name: str
    component_type: str  # service, database, api, function, module
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    failure_modes: List[FailureMode] = field(default_factory=list)
    has_circuit_breaker: bool = False
    has_fallback: bool = False
    has_retry: bool = False
    criticality: float = 0.5  # 0.0 - 1.0
    file_path: Optional[str] = None


@dataclass
class CascadeChain:
    """A potential cascade chain."""
    chain_id: str
    trigger_component: str
    failure_mode: FailureMode
    affected_components: List[str] = field(default_factory=list)
    propagation_pattern: PropagationPattern = PropagationPattern.DIRECT
    total_impact_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    time_to_failure_seconds: float = 0.0
    prevention_strategies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "trigger": self.trigger_component,
            "failure_mode": self.failure_mode.value,
            "affected": self.affected_components,
            "pattern": self.propagation_pattern.value,
            "impact": self.total_impact_score,
            "risk": self.risk_level.value,
            "time_to_failure": self.time_to_failure_seconds,
            "prevention": self.prevention_strategies
        }


@dataclass
class CascadeAnalysis:
    """Complete cascade failure analysis."""
    analysis_id: str
    components_analyzed: int
    total_dependencies: int
    cascade_chains: List[CascadeChain] = field(default_factory=list)
    critical_paths: List[List[str]] = field(default_factory=list)
    single_points_of_failure: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.MEDIUM
    resilience_score: float = 0.0  # 0.0 - 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "components": self.components_analyzed,
            "dependencies": self.total_dependencies,
            "cascade_chains": [c.to_dict() for c in self.cascade_chains],
            "critical_paths": self.critical_paths,
            "spof": self.single_points_of_failure,
            "recommendations": self.recommendations,
            "overall_risk": self.overall_risk.value,
            "resilience_score": self.resilience_score
        }


class CascadingFailurePredictor:
    """
    Predicts and helps prevent cascading failures.

    Analyzes code structure, dependencies, and patterns to:
    1. Build dependency graphs
    2. Identify potential cascade chains
    3. Score component criticality
    4. Recommend prevention strategies
    """

    def __init__(
        self,
        session=None,
        genesis_service=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self._genesis_service = genesis_service
        self.repo_path = repo_path or Path.cwd()

        # Dependency graph
        self._components: Dict[str, ComponentNode] = {}

        # Analysis cache
        self._analyses: Dict[str, CascadeAnalysis] = {}

        # Failure pattern knowledge
        self._known_cascade_patterns = self._init_cascade_patterns()

        # Metrics
        self.metrics = {
            "analyses_performed": 0,
            "cascade_chains_found": 0,
            "spof_identified": 0,
            "failures_prevented": 0
        }

        logger.info("[CASCADE-PREDICTOR] Initialized")

    def _init_cascade_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize known cascade failure patterns."""
        return {
            "database_cascade": {
                "trigger": ["database", "db", "connection", "query"],
                "propagates_to": ["api", "service", "handler"],
                "pattern": PropagationPattern.AMPLIFIED,
                "prevention": [
                    "Add connection pooling",
                    "Implement circuit breaker",
                    "Add read replicas for failover"
                ]
            },
            "api_cascade": {
                "trigger": ["api", "http", "request", "endpoint"],
                "propagates_to": ["frontend", "client", "consumer"],
                "pattern": PropagationPattern.CASCADING,
                "prevention": [
                    "Add retry with backoff",
                    "Implement timeout handling",
                    "Add fallback responses"
                ]
            },
            "memory_cascade": {
                "trigger": ["memory", "cache", "buffer", "queue"],
                "propagates_to": ["process", "worker", "service"],
                "pattern": PropagationPattern.DELAYED,
                "prevention": [
                    "Add memory limits",
                    "Implement garbage collection triggers",
                    "Add monitoring alerts"
                ]
            },
            "auth_cascade": {
                "trigger": ["auth", "token", "session", "login"],
                "propagates_to": ["all_endpoints", "user_operations"],
                "pattern": PropagationPattern.AMPLIFIED,
                "prevention": [
                    "Add token refresh mechanism",
                    "Implement session failover",
                    "Add authentication cache"
                ]
            },
            "file_cascade": {
                "trigger": ["file", "disk", "storage", "write"],
                "propagates_to": ["logging", "data_persistence", "uploads"],
                "pattern": PropagationPattern.DIRECT,
                "prevention": [
                    "Add disk space monitoring",
                    "Implement log rotation",
                    "Add storage failover"
                ]
            }
        }

    async def analyze_code(
        self,
        code: str,
        file_path: Optional[str] = None
    ) -> CascadeAnalysis:
        """Analyze code for cascading failure risks."""
        analysis = CascadeAnalysis(
            analysis_id=f"CASCADE-{uuid.uuid4().hex[:12]}",
            components_analyzed=0,
            total_dependencies=0
        )

        # Extract components from code
        components = self._extract_components(code, file_path)
        for comp in components:
            self._components[comp.component_id] = comp
            analysis.components_analyzed += 1

        # Build dependency relationships
        self._build_dependencies(code)
        analysis.total_dependencies = sum(
            len(c.dependencies) for c in self._components.values()
        )

        # Find cascade chains
        analysis.cascade_chains = self._find_cascade_chains()

        # Identify critical paths
        analysis.critical_paths = self._find_critical_paths()

        # Find single points of failure
        analysis.single_points_of_failure = self._find_spof()

        # Calculate resilience score
        analysis.resilience_score = self._calculate_resilience()

        # Determine overall risk
        analysis.overall_risk = self._calculate_overall_risk(analysis)

        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)

        # Store analysis
        self._analyses[analysis.analysis_id] = analysis

        # Update metrics
        self.metrics["analyses_performed"] += 1
        self.metrics["cascade_chains_found"] += len(analysis.cascade_chains)
        self.metrics["spof_identified"] += len(analysis.single_points_of_failure)

        logger.info(
            f"[CASCADE-PREDICTOR] Analysis complete: "
            f"{len(analysis.cascade_chains)} chains, "
            f"{len(analysis.single_points_of_failure)} SPOFs, "
            f"risk={analysis.overall_risk.value}"
        )

        return analysis

    def _extract_components(
        self,
        code: str,
        file_path: Optional[str]
    ) -> List[ComponentNode]:
        """Extract components from code."""
        components = []

        # Extract classes
        classes = re.findall(r'class\s+(\w+)', code)
        for cls in classes:
            comp = ComponentNode(
                component_id=f"class:{cls}",
                name=cls,
                component_type="class",
                file_path=file_path,
                has_circuit_breaker="circuit" in code.lower() or "breaker" in code.lower(),
                has_fallback="fallback" in code.lower() or "default" in code.lower(),
                has_retry="retry" in code.lower()
            )

            # Determine criticality based on name patterns
            if any(kw in cls.lower() for kw in ["service", "manager", "handler", "controller"]):
                comp.criticality = 0.8
            elif any(kw in cls.lower() for kw in ["database", "db", "repository"]):
                comp.criticality = 0.9
            elif any(kw in cls.lower() for kw in ["auth", "security", "session"]):
                comp.criticality = 0.85

            # Detect failure modes
            if "connection" in code.lower():
                comp.failure_modes.append(FailureMode.CONNECTION_FAILURE)
            if "timeout" in code.lower():
                comp.failure_modes.append(FailureMode.TIMEOUT)
            if "async" in code.lower() or "await" in code.lower():
                comp.failure_modes.append(FailureMode.DEADLOCK)

            components.append(comp)

        # Extract functions
        functions = re.findall(r'(?:async\s+)?def\s+(\w+)', code)
        for func in functions:
            if func.startswith("_"):  # Skip private functions
                continue

            comp = ComponentNode(
                component_id=f"func:{func}",
                name=func,
                component_type="function",
                file_path=file_path,
                criticality=0.5
            )

            # Higher criticality for certain functions
            if any(kw in func.lower() for kw in ["init", "main", "start", "run"]):
                comp.criticality = 0.7

            components.append(comp)

        # Extract imports as external dependencies
        imports = re.findall(r'(?:from\s+(\S+)\s+)?import\s+(\S+)', code)
        for from_mod, import_mod in imports:
            module = from_mod or import_mod.split(".")[0]
            if module in ["os", "sys", "json", "re", "typing"]:
                continue  # Skip standard library

            comp = ComponentNode(
                component_id=f"import:{module}",
                name=module,
                component_type="external_dependency",
                criticality=0.6
            )
            comp.failure_modes.append(FailureMode.DEPENDENCY_FAILURE)
            components.append(comp)

        return components

    def _build_dependencies(self, code: str):
        """Build dependency relationships between components."""
        for comp_id, comp in self._components.items():
            if comp.component_type == "class":
                # Find class dependencies (inheritance, composition)
                class_match = re.search(
                    rf'class\s+{comp.name}\s*\(([^)]+)\)',
                    code
                )
                if class_match:
                    parents = class_match.group(1).split(",")
                    for parent in parents:
                        parent = parent.strip()
                        parent_id = f"class:{parent}"
                        if parent_id in self._components:
                            comp.dependencies.append(parent_id)
                            self._components[parent_id].dependents.append(comp_id)

            elif comp.component_type == "function":
                # Find function calls within this function
                func_pattern = rf'def\s+{comp.name}\s*\([^)]*\).*?(?=\ndef\s|\Z)'
                func_match = re.search(func_pattern, code, re.DOTALL)
                if func_match:
                    func_body = func_match.group(0)
                    calls = re.findall(r'(?<![.\w])(\w+)\s*\(', func_body)
                    for call in calls:
                        if call == comp.name:
                            continue  # Skip self-calls
                        call_id = f"func:{call}"
                        if call_id in self._components:
                            comp.dependencies.append(call_id)
                            self._components[call_id].dependents.append(comp_id)

    def _find_cascade_chains(self) -> List[CascadeChain]:
        """Find potential cascade failure chains."""
        chains = []

        for comp_id, comp in self._components.items():
            # Components with many dependents are cascade risks
            if len(comp.dependents) >= 2:
                for failure_mode in comp.failure_modes or [FailureMode.DEPENDENCY_FAILURE]:
                    chain = CascadeChain(
                        chain_id=f"CHAIN-{uuid.uuid4().hex[:8]}",
                        trigger_component=comp.name,
                        failure_mode=failure_mode,
                        affected_components=self._trace_cascade(comp_id),
                        propagation_pattern=self._determine_propagation_pattern(comp)
                    )

                    # Calculate impact
                    chain.total_impact_score = sum(
                        self._components.get(f"class:{c}", ComponentNode("", "", "")).criticality
                        for c in chain.affected_components
                    ) / max(1, len(chain.affected_components))

                    # Determine risk level
                    chain.risk_level = self._score_to_risk(
                        chain.total_impact_score * len(chain.affected_components) / 10
                    )

                    # Add prevention strategies
                    chain.prevention_strategies = self._get_prevention_strategies(comp, failure_mode)

                    if len(chain.affected_components) >= 2:
                        chains.append(chain)

        # Check against known patterns
        chains.extend(self._check_known_patterns())

        return chains

    def _trace_cascade(self, start_id: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Trace the cascade path from a starting component."""
        if visited is None:
            visited = set()

        if start_id in visited:
            return []

        visited.add(start_id)
        affected = []

        if start_id in self._components:
            comp = self._components[start_id]
            for dependent_id in comp.dependents:
                affected.append(self._components[dependent_id].name if dependent_id in self._components else dependent_id)
                affected.extend(self._trace_cascade(dependent_id, visited))

        return affected[:20]  # Limit depth

    def _determine_propagation_pattern(self, comp: ComponentNode) -> PropagationPattern:
        """Determine how failure would propagate from this component."""
        if len(comp.dependents) > 5:
            return PropagationPattern.AMPLIFIED
        elif comp.has_circuit_breaker:
            return PropagationPattern.CONTAINED
        elif len(comp.dependents) > 2:
            return PropagationPattern.CASCADING
        else:
            return PropagationPattern.DIRECT

    def _get_prevention_strategies(
        self,
        comp: ComponentNode,
        failure_mode: FailureMode
    ) -> List[str]:
        """Get prevention strategies for a component failure."""
        strategies = []

        if not comp.has_circuit_breaker:
            strategies.append(f"Add circuit breaker to {comp.name}")

        if not comp.has_fallback:
            strategies.append(f"Add fallback for {comp.name}")

        if not comp.has_retry and failure_mode in [FailureMode.CONNECTION_FAILURE, FailureMode.TIMEOUT]:
            strategies.append(f"Add retry logic to {comp.name}")

        # Failure-mode specific strategies
        strategy_map = {
            FailureMode.CONNECTION_FAILURE: ["Add connection pooling", "Implement health checks"],
            FailureMode.TIMEOUT: ["Add timeout handling", "Implement async with timeout"],
            FailureMode.RESOURCE_EXHAUSTION: ["Add resource limits", "Implement backpressure"],
            FailureMode.MEMORY_EXHAUSTION: ["Add memory limits", "Implement garbage collection"],
            FailureMode.DEADLOCK: ["Add lock timeouts", "Use async/await properly"],
        }

        strategies.extend(strategy_map.get(failure_mode, []))

        return strategies[:5]

    def _check_known_patterns(self) -> List[CascadeChain]:
        """Check code against known cascade patterns."""
        chains = []

        for pattern_name, pattern in self._known_cascade_patterns.items():
            # Check if pattern triggers exist in components
            has_trigger = any(
                any(t in comp.name.lower() for t in pattern["trigger"])
                for comp in self._components.values()
            )

            if has_trigger:
                chain = CascadeChain(
                    chain_id=f"PATTERN-{pattern_name}-{uuid.uuid4().hex[:6]}",
                    trigger_component=pattern_name,
                    failure_mode=FailureMode.DEPENDENCY_FAILURE,
                    propagation_pattern=pattern["pattern"],
                    prevention_strategies=pattern["prevention"],
                    risk_level=RiskLevel.MEDIUM
                )
                chains.append(chain)

        return chains

    def _find_critical_paths(self) -> List[List[str]]:
        """Find critical paths through the dependency graph."""
        paths = []

        # Find longest dependency chains
        for comp_id, comp in self._components.items():
            if not comp.dependencies:  # Start from leaf nodes
                path = self._trace_path_up(comp_id)
                if len(path) >= 3:
                    paths.append(path)

        # Sort by length (longer = more critical)
        paths.sort(key=len, reverse=True)

        return paths[:5]  # Top 5 critical paths

    def _trace_path_up(self, start_id: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Trace path from component up through dependents."""
        if visited is None:
            visited = set()

        if start_id in visited:
            return []

        visited.add(start_id)

        if start_id not in self._components:
            return []

        comp = self._components[start_id]
        path = [comp.name]

        if comp.dependents:
            # Follow the dependent with most criticality
            best_dependent = max(
                comp.dependents,
                key=lambda d: self._components.get(d, ComponentNode("", "", "")).criticality
            )
            path.extend(self._trace_path_up(best_dependent, visited))

        return path

    def _find_spof(self) -> List[str]:
        """Find single points of failure."""
        spof = []

        for comp_id, comp in self._components.items():
            # High criticality + many dependents + no redundancy
            if (comp.criticality >= 0.7 and
                len(comp.dependents) >= 2 and
                not comp.has_circuit_breaker and
                not comp.has_fallback):
                spof.append(comp.name)

            # External dependencies are often SPOFs
            if comp.component_type == "external_dependency" and len(comp.dependents) >= 2:
                spof.append(f"{comp.name} (external)")

        return spof

    def _calculate_resilience(self) -> float:
        """Calculate overall system resilience score."""
        if not self._components:
            return 0.5

        factors = []

        # Factor 1: Circuit breaker coverage
        with_breaker = sum(1 for c in self._components.values() if c.has_circuit_breaker)
        factors.append(with_breaker / len(self._components))

        # Factor 2: Fallback coverage
        with_fallback = sum(1 for c in self._components.values() if c.has_fallback)
        factors.append(with_fallback / len(self._components))

        # Factor 3: Retry coverage
        with_retry = sum(1 for c in self._components.values() if c.has_retry)
        factors.append(with_retry / len(self._components))

        # Factor 4: Dependency depth (lower is better)
        max_depth = max(len(self._trace_path_up(c)) for c in self._components.keys()) if self._components else 0
        depth_score = 1.0 - min(1.0, max_depth / 10)
        factors.append(depth_score)

        return sum(factors) / len(factors)

    def _calculate_overall_risk(self, analysis: CascadeAnalysis) -> RiskLevel:
        """Calculate overall risk level."""
        risk_score = 0.0

        # Factor in cascade chains
        if len(analysis.cascade_chains) > 5:
            risk_score += 0.3
        elif len(analysis.cascade_chains) > 2:
            risk_score += 0.2

        # Factor in SPOFs
        if len(analysis.single_points_of_failure) > 3:
            risk_score += 0.3
        elif len(analysis.single_points_of_failure) > 0:
            risk_score += 0.15

        # Factor in resilience
        risk_score += (1.0 - analysis.resilience_score) * 0.4

        return self._score_to_risk(risk_score)

    def _score_to_risk(self, score: float) -> RiskLevel:
        """Convert score to risk level."""
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    def _generate_recommendations(self, analysis: CascadeAnalysis) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Address SPOFs first
        for spof in analysis.single_points_of_failure[:3]:
            recommendations.append(f"Add redundancy for {spof}")

        # Address high-risk chains
        for chain in analysis.cascade_chains:
            if chain.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                recommendations.extend(chain.prevention_strategies[:2])

        # General resilience improvements
        if analysis.resilience_score < 0.5:
            recommendations.append("Implement circuit breaker pattern across services")
            recommendations.append("Add fallback mechanisms for critical paths")

        if len(analysis.critical_paths) > 0 and len(analysis.critical_paths[0]) > 5:
            recommendations.append("Consider breaking up long dependency chains")

        return list(set(recommendations))[:10]  # Unique, top 10

    def prevent_cascade(
        self,
        chain_id: str
    ) -> Dict[str, Any]:
        """Mark a cascade as prevented and log."""
        for analysis in self._analyses.values():
            for chain in analysis.cascade_chains:
                if chain.chain_id == chain_id:
                    self.metrics["failures_prevented"] += 1
                    return {
                        "prevented": True,
                        "chain": chain.to_dict(),
                        "strategies_used": chain.prevention_strategies
                    }

        return {"prevented": False, "error": "Chain not found"}

    def get_component_risk(self, component_name: str) -> Dict[str, Any]:
        """Get risk assessment for a specific component."""
        for comp_id, comp in self._components.items():
            if comp.name == component_name:
                cascade_impact = self._trace_cascade(comp_id)
                return {
                    "component": component_name,
                    "criticality": comp.criticality,
                    "dependencies": len(comp.dependencies),
                    "dependents": len(comp.dependents),
                    "failure_modes": [f.value for f in comp.failure_modes],
                    "cascade_impact": len(cascade_impact),
                    "has_protection": {
                        "circuit_breaker": comp.has_circuit_breaker,
                        "fallback": comp.has_fallback,
                        "retry": comp.has_retry
                    }
                }

        return {"error": "Component not found"}

    def get_metrics(self) -> Dict[str, Any]:
        """Get predictor metrics."""
        return {
            **self.metrics,
            "components_tracked": len(self._components),
            "analyses_cached": len(self._analyses)
        }
