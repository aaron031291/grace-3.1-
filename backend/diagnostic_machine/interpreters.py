"""
Layer 2 - Interpreters: Pattern Analysis Layer

Analyzes raw sensor data to detect:
- Patterns (recurring issues, success patterns)
- Anomalies (unusual behavior, outliers)
- Invariant checks (rule violations)
- Clarity classification (clear vs ambiguous states)
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .sensors import SensorData, TestResultData, MetricsData

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns detected."""
    TEST_FAILURE_PATTERN = "test_failure_pattern"
    TEST_SUCCESS_PATTERN = "test_success_pattern"
    ERROR_CLUSTER = "error_cluster"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RECOVERY_PATTERN = "recovery_pattern"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    INFRASTRUCTURE_ISSUE = "infrastructure_issue"
    CODE_QUALITY_ISSUE = "code_quality_issue"


class AnomalyType(str, Enum):
    """Types of anomalies detected."""
    TEST_PASS_RATE_DROP = "test_pass_rate_drop"
    ERROR_SPIKE = "error_spike"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SERVICE_DEGRADATION = "service_degradation"
    UNUSUAL_ACTIVITY = "unusual_activity"
    INVARIANT_VIOLATION = "invariant_violation"
    GENESIS_KEY_ANOMALY = "genesis_key_anomaly"
    COGNITIVE_ANOMALY = "cognitive_anomaly"
    CODE_QUALITY_ISSUE = "code_quality_issue"  # NEW: Static analysis and design pattern issues


class ClarityLevel(str, Enum):
    """Clarity classification of system state."""
    CLEAR = "clear"  # System state is well understood
    PARTIALLY_CLEAR = "partially_clear"  # Some ambiguity
    AMBIGUOUS = "ambiguous"  # Significant uncertainty
    OPAQUE = "opaque"  # Cannot determine state


@dataclass
class Pattern:
    """A detected pattern in the system."""
    pattern_type: PatternType
    description: str
    confidence: float  # 0.0 to 1.0
    frequency: int  # How often this pattern occurs
    affected_components: List[str] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    suggested_action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Anomaly:
    """A detected anomaly in the system."""
    anomaly_type: AnomalyType
    severity: float  # 0.0 (minor) to 1.0 (critical)
    description: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    deviation_percent: float = 0.0
    affected_components: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InvariantCheck:
    """Result of an invariant check."""
    invariant_id: str
    invariant_name: str
    passed: bool
    description: str
    violation_details: Optional[str] = None
    severity: float = 0.0  # Only relevant if failed
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterpretedData:
    """Aggregated interpreted data from analysis."""
    patterns: List[Pattern] = field(default_factory=list)
    anomalies: List[Anomaly] = field(default_factory=list)
    invariant_checks: List[InvariantCheck] = field(default_factory=list)
    clarity_level: ClarityLevel = ClarityLevel.CLEAR
    clarity_score: float = 1.0  # 0.0 (opaque) to 1.0 (clear)
    interpretation_timestamp: datetime = field(default_factory=datetime.utcnow)
    interpretation_duration_ms: float = 0.0


class InterpreterLayer:
    """
    Layer 2 - Interpreters: Analyzes sensor data to detect patterns and anomalies.

    This layer transforms raw sensor data into actionable insights by:
    - Detecting patterns in test results, logs, and metrics
    - Identifying anomalies that deviate from expected behavior
    - Checking system invariants (the 12 GRACE invariants)
    - Classifying system clarity (how well we understand the state)
    """

    # GRACE's 12 Invariants for checking
    INVARIANTS = [
        ("INV-1", "Never Harm, Always Help", "System should not cause harm"),
        ("INV-2", "Preserve Human Override", "Human control must be available"),
        ("INV-3", "Maintain Transparency", "Actions must be explainable"),
        ("INV-4", "Ensure Reversibility", "Critical actions must be reversible"),
        ("INV-5", "Bound Resource Usage", "Resources must stay within limits"),
        ("INV-6", "Observability Is Mandatory", "All actions must be logged"),
        ("INV-7", "Fail Gracefully", "Errors should not cascade"),
        ("INV-8", "Respect Privacy", "Personal data must be protected"),
        ("INV-9", "Maintain Consistency", "State must remain consistent"),
        ("INV-10", "Bound Recursion", "Self-improvement must be bounded"),
        ("INV-11", "Preserve Provenance", "Origin of data must be tracked"),
        ("INV-12", "Enable Learning", "System must be able to improve"),
    ]

    # Thresholds for anomaly detection
    THRESHOLDS = {
        'test_pass_rate_critical': 0.5,
        'test_pass_rate_warning': 0.8,
        'cpu_critical': 90.0,
        'cpu_warning': 70.0,
        'memory_critical': 90.0,
        'memory_warning': 80.0,
        'disk_critical': 95.0,
        'disk_warning': 85.0,
        'error_rate_critical': 0.1,
        'error_rate_warning': 0.05,
        'invariant_violation_threshold': 0,
    }

    def __init__(self, thresholds: Dict[str, float] = None):
        """Initialize the interpreter layer."""
        if thresholds:
            self.THRESHOLDS.update(thresholds)

    def interpret(self, sensor_data: SensorData) -> InterpretedData:
        """Interpret sensor data to extract patterns, anomalies, and clarity."""
        start_time = datetime.utcnow()
        result = InterpretedData()

        # Detect patterns
        result.patterns = self._detect_patterns(sensor_data)

        # Detect anomalies
        result.anomalies = self._detect_anomalies(sensor_data)

        # Check invariants
        result.invariant_checks = self._check_invariants(sensor_data)

        # Classify clarity
        result.clarity_level, result.clarity_score = self._classify_clarity(
            sensor_data, result.patterns, result.anomalies, result.invariant_checks
        )

        end_time = datetime.utcnow()
        result.interpretation_timestamp = end_time
        result.interpretation_duration_ms = (end_time - start_time).total_seconds() * 1000

        return result

    def _detect_patterns(self, sensor_data: SensorData) -> List[Pattern]:
        """Detect patterns in the sensor data."""
        patterns = []

        # Test result patterns
        if sensor_data.test_results:
            patterns.extend(self._detect_test_patterns(sensor_data.test_results))

        # Log patterns
        if sensor_data.logs:
            patterns.extend(self._detect_log_patterns(sensor_data))

        # Genesis key patterns
        if sensor_data.genesis_keys:
            patterns.extend(self._detect_genesis_patterns(sensor_data))

        # Learning opportunity patterns
        patterns.extend(self._detect_learning_opportunities(sensor_data))

        return patterns

    def _detect_test_patterns(self, test_results: TestResultData) -> List[Pattern]:
        """Detect patterns in test results."""
        patterns = []

        # Infrastructure failure pattern
        if test_results.infrastructure_failures > 0:
            ratio = test_results.infrastructure_failures / max(test_results.failed, 1)
            if ratio > 0.5:
                patterns.append(Pattern(
                    pattern_type=PatternType.INFRASTRUCTURE_ISSUE,
                    description=f"High infrastructure failure rate ({ratio:.1%})",
                    confidence=ratio,
                    frequency=test_results.infrastructure_failures,
                    affected_components=["infrastructure", "services"],
                    evidence=[{
                        'infrastructure_failures': test_results.infrastructure_failures,
                        'total_failures': test_results.failed,
                    }],
                    suggested_action="Check service dependencies and infrastructure"
                ))

        # Code quality issue pattern
        if test_results.code_failures > 5:
            patterns.append(Pattern(
                pattern_type=PatternType.CODE_QUALITY_ISSUE,
                description=f"{test_results.code_failures} code-related test failures",
                confidence=0.8,
                frequency=test_results.code_failures,
                affected_components=["code", "logic"],
                evidence=[{
                    'code_failures': test_results.code_failures,
                    'error_types': test_results.top_error_types,
                }],
                suggested_action="Review failing tests and fix code issues"
            ))

        # Error cluster pattern
        for error_type, count in test_results.top_error_types.items():
            if count >= 3:
                patterns.append(Pattern(
                    pattern_type=PatternType.ERROR_CLUSTER,
                    description=f"Cluster of {error_type} errors ({count} occurrences)",
                    confidence=min(count / 10, 1.0),
                    frequency=count,
                    affected_components=[error_type],
                    evidence=[{
                        'error_type': error_type,
                        'count': count,
                    }],
                    suggested_action=f"Investigate root cause of {error_type} errors"
                ))

        # Success pattern
        if test_results.pass_rate > 0.9:
            patterns.append(Pattern(
                pattern_type=PatternType.TEST_SUCCESS_PATTERN,
                description=f"High test pass rate ({test_results.pass_rate:.1%})",
                confidence=test_results.pass_rate,
                frequency=test_results.passed,
                affected_components=["tests"],
                evidence=[{
                    'pass_rate': test_results.pass_rate,
                    'passed': test_results.passed,
                }],
                suggested_action="Continue current practices"
            ))

        return patterns

    def _detect_log_patterns(self, sensor_data: SensorData) -> List[Pattern]:
        """Detect patterns in log data."""
        patterns = []
        logs = sensor_data.logs

        if not logs:
            return patterns

        # Error spike pattern
        error_count = logs.log_level_counts.get('ERROR', 0)
        total_logs = sum(logs.log_level_counts.values())

        if total_logs > 0 and error_count > 10:
            error_rate = error_count / total_logs
            if error_rate > self.THRESHOLDS['error_rate_warning']:
                patterns.append(Pattern(
                    pattern_type=PatternType.ERROR_CLUSTER,
                    description=f"High error rate in logs ({error_rate:.1%})",
                    confidence=min(error_rate * 10, 1.0),
                    frequency=error_count,
                    affected_components=["logging"],
                    evidence=[{
                        'error_count': error_count,
                        'total_logs': total_logs,
                        'error_rate': error_rate,
                    }],
                    suggested_action="Review error logs for root cause"
                ))

        return patterns

    def _detect_genesis_patterns(self, sensor_data: SensorData) -> List[Pattern]:
        """Detect patterns in Genesis Key data."""
        patterns = []
        genesis = sensor_data.genesis_keys

        if not genesis:
            return patterns

        # Error key pattern
        if genesis.total_keys > 0:
            error_ratio = genesis.error_keys / genesis.total_keys
            if error_ratio > 0.1:
                patterns.append(Pattern(
                    pattern_type=PatternType.ERROR_CLUSTER,
                    description=f"High error key ratio ({error_ratio:.1%})",
                    confidence=error_ratio,
                    frequency=genesis.error_keys,
                    affected_components=["genesis_keys"],
                    evidence=[{
                        'error_keys': genesis.error_keys,
                        'total_keys': genesis.total_keys,
                    }],
                    suggested_action="Review error genesis keys for patterns"
                ))

        # Fix application pattern
        if genesis.fix_suggestions > 0:
            fix_rate = genesis.applied_fixes / genesis.fix_suggestions
            patterns.append(Pattern(
                pattern_type=PatternType.RECOVERY_PATTERN,
                description=f"Fix application rate: {fix_rate:.1%}",
                confidence=fix_rate,
                frequency=genesis.applied_fixes,
                affected_components=["self_healing"],
                evidence=[{
                    'fix_suggestions': genesis.fix_suggestions,
                    'applied_fixes': genesis.applied_fixes,
                }],
                suggested_action="Review unapplied fixes" if fix_rate < 0.5 else None
            ))

        return patterns

    def _detect_learning_opportunities(self, sensor_data: SensorData) -> List[Pattern]:
        """Detect learning opportunities from sensor data."""
        patterns = []

        # Learning from test results
        if sensor_data.test_results and sensor_data.test_results.learned_patterns:
            for learned in sensor_data.test_results.learned_patterns[:5]:
                patterns.append(Pattern(
                    pattern_type=PatternType.LEARNING_OPPORTUNITY,
                    description=f"Learning from: {learned.get('description', 'test pattern')}",
                    confidence=learned.get('confidence', 0.7),
                    frequency=1,
                    affected_components=learned.get('categories', []),
                    evidence=[learned],
                    suggested_action="Incorporate into knowledge base"
                ))

        return patterns

    def _detect_anomalies(self, sensor_data: SensorData) -> List[Anomaly]:
        """Detect anomalies in the sensor data."""
        anomalies = []

        # Test anomalies
        if sensor_data.test_results:
            anomalies.extend(self._detect_test_anomalies(sensor_data.test_results))

        # Metric anomalies
        if sensor_data.metrics:
            anomalies.extend(self._detect_metric_anomalies(sensor_data.metrics))

        # Agent anomalies
        if sensor_data.agent_outputs:
            anomalies.extend(self._detect_agent_anomalies(sensor_data))
        
        # Configuration anomalies (NEW)
        if sensor_data.configuration:
            anomalies.extend(self._detect_configuration_anomalies(sensor_data.configuration))
        
        # Static analysis anomalies (NEW)
        if sensor_data.static_analysis:
            anomalies.extend(self._detect_static_analysis_anomalies(sensor_data.static_analysis))
        
        # Design pattern anomalies (NEW)
        if sensor_data.design_patterns:
            anomalies.extend(self._detect_design_pattern_anomalies(sensor_data.design_patterns))

        return anomalies

    def _detect_test_anomalies(self, test_results: TestResultData) -> List[Anomaly]:
        """Detect anomalies in test results."""
        anomalies = []

        # Pass rate anomaly
        if test_results.pass_rate < self.THRESHOLDS['test_pass_rate_critical']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.TEST_PASS_RATE_DROP,
                severity=1.0 - test_results.pass_rate,
                description=f"Critical: Test pass rate at {test_results.pass_rate:.1%}",
                expected_value=self.THRESHOLDS['test_pass_rate_warning'],
                actual_value=test_results.pass_rate,
                deviation_percent=(self.THRESHOLDS['test_pass_rate_warning'] - test_results.pass_rate) * 100,
                affected_components=["tests"],
            ))
        elif test_results.pass_rate < self.THRESHOLDS['test_pass_rate_warning']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.TEST_PASS_RATE_DROP,
                severity=0.5,
                description=f"Warning: Test pass rate at {test_results.pass_rate:.1%}",
                expected_value=self.THRESHOLDS['test_pass_rate_warning'],
                actual_value=test_results.pass_rate,
                deviation_percent=(self.THRESHOLDS['test_pass_rate_warning'] - test_results.pass_rate) * 100,
                affected_components=["tests"],
            ))

        return anomalies

    def _detect_metric_anomalies(self, metrics: MetricsData) -> List[Anomaly]:
        """Detect anomalies in system metrics."""
        anomalies = []

        # CPU anomaly
        if metrics.cpu_percent > self.THRESHOLDS['cpu_critical']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.RESOURCE_EXHAUSTION,
                severity=1.0,
                description=f"Critical: CPU at {metrics.cpu_percent:.1f}%",
                expected_value=self.THRESHOLDS['cpu_warning'],
                actual_value=metrics.cpu_percent,
                deviation_percent=metrics.cpu_percent - self.THRESHOLDS['cpu_warning'],
                affected_components=["cpu", "compute"],
            ))
        elif metrics.cpu_percent > self.THRESHOLDS['cpu_warning']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.RESOURCE_EXHAUSTION,
                severity=0.5,
                description=f"Warning: CPU at {metrics.cpu_percent:.1f}%",
                expected_value=self.THRESHOLDS['cpu_warning'],
                actual_value=metrics.cpu_percent,
                deviation_percent=metrics.cpu_percent - self.THRESHOLDS['cpu_warning'],
                affected_components=["cpu"],
            ))

        # Memory anomaly
        if metrics.memory_percent > self.THRESHOLDS['memory_critical']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.RESOURCE_EXHAUSTION,
                severity=1.0,
                description=f"Critical: Memory at {metrics.memory_percent:.1f}%",
                expected_value=self.THRESHOLDS['memory_warning'],
                actual_value=metrics.memory_percent,
                deviation_percent=metrics.memory_percent - self.THRESHOLDS['memory_warning'],
                affected_components=["memory"],
            ))

        # Service degradation
        unhealthy_services = []
        if not metrics.database_health:
            unhealthy_services.append("database")
        if not metrics.vector_db_health:
            unhealthy_services.append("vector_db")
        if not metrics.llm_health:
            unhealthy_services.append("llm")
        if not metrics.embedding_health:
            unhealthy_services.append("embedding")

        if unhealthy_services:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.SERVICE_DEGRADATION,
                severity=len(unhealthy_services) / 4,
                description=f"Services unhealthy: {', '.join(unhealthy_services)}",
                expected_value="all healthy",
                actual_value=f"{len(unhealthy_services)} unhealthy",
                affected_components=unhealthy_services,
            ))

        return anomalies

    def _detect_agent_anomalies(self, sensor_data: SensorData) -> List[Anomaly]:
        """Detect anomalies in agent outputs."""
        anomalies = []
        agent = sensor_data.agent_outputs

        if not agent:
            return anomalies

        # Invariant violation anomaly
        if agent.invariant_violations > self.THRESHOLDS['invariant_violation_threshold']:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.INVARIANT_VIOLATION,
                severity=min(agent.invariant_violations / 10, 1.0),
                description=f"{agent.invariant_violations} invariant violations detected",
                expected_value=0,
                actual_value=agent.invariant_violations,
                affected_components=["cognitive", "governance"],
            ))

        # Low confidence anomaly
        if agent.total_decisions > 0 and agent.average_confidence < 0.5:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.COGNITIVE_ANOMALY,
                severity=0.5,
                description=f"Low average decision confidence: {agent.average_confidence:.1%}",
                expected_value=0.7,
                actual_value=agent.average_confidence,
                affected_components=["cognitive"],
            ))

        return anomalies
    
    def _detect_configuration_anomalies(self, config_data: Any) -> List[Anomaly]:
        """Detect anomalies from configuration validation."""
        anomalies = []
        
        try:
            # Check for critical configuration issues
            if config_data.critical_issues > 0:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.SERVICE_DEGRADATION,
                    severity=1.0,  # Critical
                    description=f"Found {config_data.critical_issues} critical configuration issues",
                    expected_value=0,
                    actual_value=config_data.critical_issues,
                    affected_components=config_data.components_checked
                ))
            
            # Check for high severity issues
            if config_data.high_issues > 0:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.SERVICE_DEGRADATION,
                    severity=0.7,  # High
                    description=f"Found {config_data.high_issues} high-severity configuration issues",
                    expected_value=0,
                    actual_value=config_data.high_issues,
                    affected_components=config_data.components_checked
                ))
            
            # Check validation status
            if not config_data.validation_passed:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.INVARIANT_VIOLATION,
                    severity=0.8,
                    description="Configuration validation failed",
                    expected_value=True,
                    actual_value=False,
                    affected_components=config_data.components_checked
                ))
        except Exception as e:
            logger.error(f"Failed to detect configuration anomalies: {e}")
        
        return anomalies
    
    def _detect_static_analysis_anomalies(self, static_data: Any) -> List[Anomaly]:
        """Detect anomalies from static analysis."""
        anomalies = []
        
        try:
            # Check for critical static analysis issues
            if static_data.critical_issues > 0:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CODE_QUALITY_ISSUE,
                    severity=0.9,  # Critical code issues
                    description=f"Found {static_data.critical_issues} critical static analysis issues",
                    expected_value=0,
                    actual_value=static_data.critical_issues,
                    affected_components=["code_quality"]
                ))
            
            # Check for high severity issues
            if static_data.high_issues > 0:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CODE_QUALITY_ISSUE,
                    severity=0.6,  # High
                    description=f"Found {static_data.high_issues} high-severity static analysis issues",
                    expected_value=0,
                    actual_value=static_data.high_issues,
                    affected_components=["code_quality"]
                ))
            
            # Check analysis status
            if not static_data.analysis_passed:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CODE_QUALITY_ISSUE,
                    severity=0.5,
                    description="Static analysis found issues",
                    expected_value=True,
                    actual_value=False,
                    affected_components=["code_quality"]
                ))
        except Exception as e:
            logger.error(f"Failed to detect static analysis anomalies: {e}")
        
        return anomalies
    
    def _detect_design_pattern_anomalies(self, pattern_data: Any) -> List[Anomaly]:
        """Detect anomalies from design pattern detection."""
        anomalies = []
        
        try:
            # Check for high severity design issues
            if pattern_data.high_issues > 0:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CODE_QUALITY_ISSUE,
                    severity=0.5,  # Medium - design issues
                    description=f"Found {pattern_data.high_issues} high-severity design pattern issues",
                    expected_value=0,
                    actual_value=pattern_data.high_issues,
                    affected_components=pattern_data.patterns_checked
                ))
        except Exception as e:
            logger.error(f"Failed to detect design pattern anomalies: {e}")
        
        return anomalies

    def _check_invariants(self, sensor_data: SensorData) -> List[InvariantCheck]:
        """Check GRACE's 12 invariants against sensor data."""
        checks = []

        for inv_id, inv_name, inv_desc in self.INVARIANTS:
            check = self._check_single_invariant(inv_id, inv_name, inv_desc, sensor_data)
            checks.append(check)

        return checks

    def _check_single_invariant(
        self,
        inv_id: str,
        inv_name: str,
        inv_desc: str,
        sensor_data: SensorData
    ) -> InvariantCheck:
        """Check a single invariant."""
        passed = True
        violation_details = None
        severity = 0.0

        # INV-5: Bound Resource Usage
        if inv_id == "INV-5" and sensor_data.metrics:
            if sensor_data.metrics.cpu_percent > 95 or sensor_data.metrics.memory_percent > 95:
                passed = False
                violation_details = "Resource usage exceeds safe bounds"
                severity = 0.8

        # INV-6: Observability Is Mandatory
        if inv_id == "INV-6":
            if not sensor_data.genesis_keys or sensor_data.genesis_keys.total_keys == 0:
                passed = False
                violation_details = "Genesis key tracking may be disabled"
                severity = 0.5

        # INV-7: Fail Gracefully
        if inv_id == "INV-7" and sensor_data.test_results:
            if sensor_data.test_results.errors > sensor_data.test_results.failed:
                passed = False
                violation_details = "More errors than failures suggests ungraceful failure handling"
                severity = 0.6

        # INV-9: Maintain Consistency
        if inv_id == "INV-9" and sensor_data.metrics:
            if not sensor_data.metrics.database_health:
                passed = False
                violation_details = "Database health issue may affect consistency"
                severity = 0.7

        # INV-11: Preserve Provenance
        if inv_id == "INV-11" and sensor_data.genesis_keys:
            if sensor_data.genesis_keys.error_keys > sensor_data.genesis_keys.active_keys:
                passed = False
                violation_details = "High error rate in provenance tracking"
                severity = 0.5

        # INV-12: Enable Learning
        if inv_id == "INV-12" and sensor_data.test_results:
            if not sensor_data.test_results.learned_patterns:
                passed = False
                violation_details = "No learning patterns detected from recent tests"
                severity = 0.3

        return InvariantCheck(
            invariant_id=inv_id,
            invariant_name=inv_name,
            passed=passed,
            description=inv_desc,
            violation_details=violation_details,
            severity=severity,
        )

    def _classify_clarity(
        self,
        sensor_data: SensorData,
        patterns: List[Pattern],
        anomalies: List[Anomaly],
        invariant_checks: List[InvariantCheck]
    ) -> Tuple[ClarityLevel, float]:
        """Classify the clarity of the system state."""
        clarity_score = 1.0

        # Reduce clarity for failed sensors
        if sensor_data.sensors_failed:
            clarity_score -= 0.1 * len(sensor_data.sensors_failed)

        # Reduce clarity for anomalies
        for anomaly in anomalies:
            clarity_score -= 0.05 * anomaly.severity

        # Reduce clarity for invariant violations
        for check in invariant_checks:
            if not check.passed:
                clarity_score -= 0.05 * check.severity

        # Reduce clarity for conflicting patterns
        pattern_types = [p.pattern_type for p in patterns]
        if PatternType.TEST_SUCCESS_PATTERN in pattern_types and \
           PatternType.ERROR_CLUSTER in pattern_types:
            clarity_score -= 0.1  # Conflicting signals

        # Clamp to [0, 1]
        clarity_score = max(0.0, min(1.0, clarity_score))

        # Classify
        if clarity_score >= 0.8:
            return ClarityLevel.CLEAR, clarity_score
        elif clarity_score >= 0.6:
            return ClarityLevel.PARTIALLY_CLEAR, clarity_score
        elif clarity_score >= 0.3:
            return ClarityLevel.AMBIGUOUS, clarity_score
        else:
            return ClarityLevel.OPAQUE, clarity_score

    def to_dict(self, interpreted_data: InterpretedData) -> Dict[str, Any]:
        """Convert interpreted data to dictionary for serialization."""
        return {
            'interpretation_timestamp': interpreted_data.interpretation_timestamp.isoformat(),
            'interpretation_duration_ms': interpreted_data.interpretation_duration_ms,
            'clarity_level': interpreted_data.clarity_level.value,
            'clarity_score': interpreted_data.clarity_score,
            'patterns': [
                {
                    'type': p.pattern_type.value,
                    'description': p.description,
                    'confidence': p.confidence,
                    'frequency': p.frequency,
                    'affected_components': p.affected_components,
                    'suggested_action': p.suggested_action,
                }
                for p in interpreted_data.patterns
            ],
            'anomalies': [
                {
                    'type': a.anomaly_type.value,
                    'severity': a.severity,
                    'description': a.description,
                    'expected': a.expected_value,
                    'actual': a.actual_value,
                    'deviation_percent': a.deviation_percent,
                    'affected_components': a.affected_components,
                }
                for a in interpreted_data.anomalies
            ],
            'invariant_checks': [
                {
                    'id': c.invariant_id,
                    'name': c.invariant_name,
                    'passed': c.passed,
                    'violation_details': c.violation_details,
                    'severity': c.severity,
                }
                for c in interpreted_data.invariant_checks
            ],
            'summary': {
                'total_patterns': len(interpreted_data.patterns),
                'total_anomalies': len(interpreted_data.anomalies),
                'invariants_passed': sum(1 for c in interpreted_data.invariant_checks if c.passed),
                'invariants_failed': sum(1 for c in interpreted_data.invariant_checks if not c.passed),
            }
        }
