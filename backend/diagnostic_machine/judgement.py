"""
Layer 3 - Judgement: Decision Making Layer

Evaluates interpreted data to produce:
- Health score (overall system health)
- Confidence score (certainty in diagnosis)
- Risk vectors (potential future issues)
- Drift detection (deviation from baseline)
- Forensic analysis (root cause investigation)
- AVN (Anomaly Violation Notification)
- AVM (Anomaly Violation Monitor)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .sensors import SensorData
from .interpreters import (
    InterpretedData, Pattern, Anomaly, InvariantCheck,
    PatternType, AnomalyType, ClarityLevel
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(str, Enum):
    """Types of system drift detected."""
    PERFORMANCE_DRIFT = "performance_drift"
    BEHAVIORAL_DRIFT = "behavioral_drift"
    QUALITY_DRIFT = "quality_drift"
    RESOURCE_DRIFT = "resource_drift"
    NO_DRIFT = "no_drift"


@dataclass
class HealthScore:
    """Comprehensive health assessment."""
    overall_score: float  # 0.0 (critical) to 1.0 (healthy)
    status: HealthStatus
    component_scores: Dict[str, float] = field(default_factory=dict)
    degraded_components: List[str] = field(default_factory=list)
    critical_components: List[str] = field(default_factory=list)
    trend: str = "stable"  # improving, stable, degrading


@dataclass
class ConfidenceScore:
    """Confidence in the diagnostic assessment."""
    overall_confidence: float  # 0.0 to 1.0
    data_completeness: float
    signal_clarity: float
    historical_correlation: float
    reasoning: str = ""


@dataclass
class RiskVector:
    """A potential risk to the system."""
    risk_id: str
    risk_type: str
    level: RiskLevel
    probability: float  # 0.0 to 1.0
    impact: float  # 0.0 to 1.0
    description: str
    affected_components: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)
    time_to_impact: Optional[str] = None  # "immediate", "hours", "days"


@dataclass
class DriftAnalysis:
    """Analysis of system drift from baseline."""
    drift_type: DriftType
    drift_magnitude: float  # 0.0 to 1.0
    baseline_value: Optional[Any] = None
    current_value: Optional[Any] = None
    drift_direction: str = "neutral"  # positive, negative, neutral
    affected_metrics: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class ForensicFinding:
    """Forensic analysis finding for root cause."""
    finding_id: str
    category: str  # "root_cause", "contributing_factor", "symptom"
    description: str
    evidence: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    related_components: List[str] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)


@dataclass
class AVNAlert:
    """Anomaly Violation Notification alert."""
    alert_id: str
    severity: str  # "info", "warning", "critical"
    anomaly_type: str
    violation_type: Optional[str] = None
    message: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False


@dataclass
class AVMStatus:
    """Anomaly Violation Monitor status."""
    monitor_id: str
    is_active: bool = True
    anomalies_detected: int = 0
    violations_detected: int = 0
    last_check: datetime = field(default_factory=datetime.utcnow)
    alert_threshold: int = 3
    current_alert_level: str = "normal"  # normal, elevated, critical


@dataclass
class JudgementResult:
    """Complete judgement result from Layer 3."""
    health: HealthScore = field(default_factory=lambda: HealthScore(1.0, HealthStatus.UNKNOWN))
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.0, 0.0, 0.0, 0.0))
    risk_vectors: List[RiskVector] = field(default_factory=list)
    drift_analysis: List[DriftAnalysis] = field(default_factory=list)
    forensic_findings: List[ForensicFinding] = field(default_factory=list)
    avn_alerts: List[AVNAlert] = field(default_factory=list)
    avm_status: AVMStatus = field(default_factory=lambda: AVMStatus("avm-001"))
    recommended_action: str = "none"  # none, monitor, alert, heal, freeze
    judgement_timestamp: datetime = field(default_factory=datetime.utcnow)
    judgement_duration_ms: float = 0.0


class JudgementLayer:
    """
    Layer 3 - Judgement: Makes decisions based on interpreted data.

    This layer produces actionable assessments including:
    - Health scores for system components
    - Confidence in the diagnostic
    - Risk vectors for potential issues
    - Drift detection from baseline behavior
    - Forensic analysis for root causes
    - AVN (Anomaly Violation Notifications)
    - AVM (Anomaly Violation Monitor) status
    """

    # Historical baselines for drift detection
    BASELINES = {
        'test_pass_rate': 0.9,
        'cpu_percent': 30.0,
        'memory_percent': 50.0,
        'error_rate': 0.02,
        'decision_confidence': 0.8,
        'response_latency_ms': 100.0,
    }

    # Weights for health score calculation
    HEALTH_WEIGHTS = {
        'tests': 0.25,
        'services': 0.25,
        'resources': 0.20,
        'cognitive': 0.15,
        'governance': 0.15,
    }

    def __init__(
        self,
        baselines: Dict[str, float] = None,
        avn_threshold: int = 3,
        enable_forensics: bool = True
    ):
        """Initialize the judgement layer."""
        if baselines:
            self.BASELINES.update(baselines)
        self.avn_threshold = avn_threshold
        self.enable_forensics = enable_forensics
        self._alert_counter = 0
        self._finding_counter = 0

    def judge(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> JudgementResult:
        """Produce judgement from sensor and interpreted data."""
        start_time = datetime.utcnow()
        result = JudgementResult()

        # Calculate health score
        result.health = self._calculate_health_score(sensor_data, interpreted_data)

        # Calculate confidence score
        result.confidence = self._calculate_confidence(sensor_data, interpreted_data)

        # Identify risk vectors
        result.risk_vectors = self._identify_risk_vectors(sensor_data, interpreted_data)

        # Analyze drift
        result.drift_analysis = self._analyze_drift(sensor_data, interpreted_data)

        # Forensic analysis (if enabled)
        if self.enable_forensics:
            result.forensic_findings = self._forensic_analysis(
                sensor_data, interpreted_data
            )

        # Generate AVN alerts
        result.avn_alerts = self._generate_avn_alerts(interpreted_data)

        # Update AVM status
        result.avm_status = self._update_avm_status(interpreted_data)

        # Determine recommended action
        result.recommended_action = self._determine_action(result)

        end_time = datetime.utcnow()
        result.judgement_timestamp = end_time
        result.judgement_duration_ms = (end_time - start_time).total_seconds() * 1000

        return result

    def _calculate_health_score(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> HealthScore:
        """Calculate overall system health score."""
        component_scores = {}
        degraded = []
        critical = []

        # Test health
        test_score = 1.0
        if sensor_data.test_results:
            test_score = sensor_data.test_results.pass_rate
        component_scores['tests'] = test_score
        if test_score < 0.5:
            critical.append('tests')
        elif test_score < 0.8:
            degraded.append('tests')

        # Service health
        service_score = 1.0
        if sensor_data.metrics:
            healthy_count = sum([
                sensor_data.metrics.database_health,
                sensor_data.metrics.vector_db_health,
                sensor_data.metrics.llm_health,
                sensor_data.metrics.embedding_health,
            ])
            service_score = healthy_count / 4
        component_scores['services'] = service_score
        if service_score < 0.5:
            critical.append('services')
        elif service_score < 0.75:
            degraded.append('services')

        # Resource health
        resource_score = 1.0
        if sensor_data.metrics:
            cpu_health = 1.0 - (sensor_data.metrics.cpu_percent / 100)
            mem_health = 1.0 - (sensor_data.metrics.memory_percent / 100)
            disk_health = 1.0 - (sensor_data.metrics.disk_percent / 100)
            resource_score = (cpu_health + mem_health + disk_health) / 3
        component_scores['resources'] = resource_score
        if resource_score < 0.2:
            critical.append('resources')
        elif resource_score < 0.4:
            degraded.append('resources')

        # Cognitive health
        cognitive_score = 1.0
        if sensor_data.agent_outputs:
            if sensor_data.agent_outputs.total_decisions > 0:
                success_rate = (
                    sensor_data.agent_outputs.successful_decisions /
                    sensor_data.agent_outputs.total_decisions
                )
                confidence_factor = sensor_data.agent_outputs.average_confidence
                cognitive_score = (success_rate + confidence_factor) / 2
        component_scores['cognitive'] = cognitive_score
        if cognitive_score < 0.5:
            degraded.append('cognitive')

        # Governance health
        governance_score = 1.0
        invariant_passed = sum(1 for c in interpreted_data.invariant_checks if c.passed)
        invariant_total = len(interpreted_data.invariant_checks)
        if invariant_total > 0:
            governance_score = invariant_passed / invariant_total
        component_scores['governance'] = governance_score
        if governance_score < 0.7:
            critical.append('governance')
        elif governance_score < 0.9:
            degraded.append('governance')

        # Calculate weighted overall score
        overall = sum(
            component_scores.get(comp, 1.0) * weight
            for comp, weight in self.HEALTH_WEIGHTS.items()
        )

        # Determine status
        if critical:
            status = HealthStatus.CRITICAL
        elif degraded:
            status = HealthStatus.DEGRADED
        elif overall >= 0.8:
            status = HealthStatus.HEALTHY
        else:
            status = HealthStatus.DEGRADED

        # Determine trend
        trend = "stable"
        if interpreted_data.anomalies:
            high_severity = any(a.severity > 0.7 for a in interpreted_data.anomalies)
            trend = "degrading" if high_severity else "stable"

        return HealthScore(
            overall_score=overall,
            status=status,
            component_scores=component_scores,
            degraded_components=degraded,
            critical_components=critical,
            trend=trend,
        )

    def _calculate_confidence(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> ConfidenceScore:
        """Calculate confidence in the diagnostic assessment."""
        # Data completeness
        total_sensors = 6
        available_sensors = len(sensor_data.sensors_available)
        data_completeness = available_sensors / total_sensors

        # Signal clarity
        signal_clarity = interpreted_data.clarity_score

        # Historical correlation (based on pattern confidence)
        pattern_confidences = [p.confidence for p in interpreted_data.patterns] or [0.5]
        historical_correlation = sum(pattern_confidences) / len(pattern_confidences)

        # Overall confidence
        overall = (data_completeness * 0.3 +
                  signal_clarity * 0.4 +
                  historical_correlation * 0.3)

        # Generate reasoning
        reasoning_parts = []
        if data_completeness < 0.8:
            missing = total_sensors - available_sensors
            reasoning_parts.append(f"{missing} sensors unavailable")
        if signal_clarity < 0.7:
            reasoning_parts.append("signal clarity is low")
        if historical_correlation < 0.6:
            reasoning_parts.append("limited historical correlation")

        reasoning = "High confidence" if overall > 0.8 else ", ".join(reasoning_parts) or "Moderate confidence"

        return ConfidenceScore(
            overall_confidence=overall,
            data_completeness=data_completeness,
            signal_clarity=signal_clarity,
            historical_correlation=historical_correlation,
            reasoning=reasoning,
        )

    def _identify_risk_vectors(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> List[RiskVector]:
        """Identify potential risk vectors from the data."""
        risks = []

        # Test degradation risk
        if sensor_data.test_results:
            pass_rate = sensor_data.test_results.pass_rate
            if pass_rate < 0.9:
                risks.append(RiskVector(
                    risk_id=f"RISK-{len(risks)+1:03d}",
                    risk_type="test_quality",
                    level=RiskLevel.HIGH if pass_rate < 0.7 else RiskLevel.MEDIUM,
                    probability=1.0 - pass_rate,
                    impact=0.8,
                    description=f"Test pass rate at {pass_rate:.1%} indicates quality issues",
                    affected_components=["tests", "code"],
                    mitigation_suggestions=[
                        "Review failing tests",
                        "Fix infrastructure issues",
                        "Update outdated test expectations",
                    ],
                    time_to_impact="immediate",
                ))

        # Resource exhaustion risk
        if sensor_data.metrics:
            if sensor_data.metrics.memory_percent > 70:
                risks.append(RiskVector(
                    risk_id=f"RISK-{len(risks)+1:03d}",
                    risk_type="resource_exhaustion",
                    level=RiskLevel.HIGH if sensor_data.metrics.memory_percent > 85 else RiskLevel.MEDIUM,
                    probability=sensor_data.metrics.memory_percent / 100,
                    impact=0.9,
                    description=f"Memory usage at {sensor_data.metrics.memory_percent:.1f}%",
                    affected_components=["memory", "services"],
                    mitigation_suggestions=[
                        "Restart services to clear memory",
                        "Review memory leaks",
                        "Scale resources",
                    ],
                    time_to_impact="hours" if sensor_data.metrics.memory_percent < 90 else "immediate",
                ))

        # Service degradation risk
        unhealthy_services = []
        if sensor_data.metrics:
            if not sensor_data.metrics.database_health:
                unhealthy_services.append("database")
            if not sensor_data.metrics.llm_health:
                unhealthy_services.append("llm")
            if not sensor_data.metrics.vector_db_health:
                unhealthy_services.append("vector_db")

        if unhealthy_services:
            risks.append(RiskVector(
                risk_id=f"RISK-{len(risks)+1:03d}",
                risk_type="service_outage",
                level=RiskLevel.CRITICAL if len(unhealthy_services) > 2 else RiskLevel.HIGH,
                probability=0.9,
                impact=len(unhealthy_services) / 4,
                description=f"Services degraded: {', '.join(unhealthy_services)}",
                affected_components=unhealthy_services,
                mitigation_suggestions=[
                    "Check service health",
                    "Restart affected services",
                    "Review connection settings",
                ],
                time_to_impact="immediate",
            ))

        # Governance risk
        violations = [c for c in interpreted_data.invariant_checks if not c.passed]
        if violations:
            risks.append(RiskVector(
                risk_id=f"RISK-{len(risks)+1:03d}",
                risk_type="governance_violation",
                level=RiskLevel.HIGH,
                probability=0.8,
                impact=0.7,
                description=f"{len(violations)} invariant violations detected",
                affected_components=["governance", "cognitive"],
                mitigation_suggestions=[
                    "Review invariant violations",
                    "Implement corrective actions",
                    "Update governance rules",
                ],
                time_to_impact="days",
            ))

        return risks

    def _analyze_drift(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> List[DriftAnalysis]:
        """Analyze system drift from baselines."""
        drift_analyses = []

        # Test pass rate drift
        if sensor_data.test_results:
            baseline = self.BASELINES['test_pass_rate']
            current = sensor_data.test_results.pass_rate
            drift_mag = abs(current - baseline) / baseline

            if drift_mag > 0.1:
                drift_analyses.append(DriftAnalysis(
                    drift_type=DriftType.QUALITY_DRIFT,
                    drift_magnitude=drift_mag,
                    baseline_value=baseline,
                    current_value=current,
                    drift_direction="negative" if current < baseline else "positive",
                    affected_metrics=["test_pass_rate"],
                    recommendation="Review test changes" if current < baseline else "Update baseline",
                ))

        # Resource drift
        if sensor_data.metrics:
            cpu_baseline = self.BASELINES['cpu_percent']
            cpu_current = sensor_data.metrics.cpu_percent
            cpu_drift = abs(cpu_current - cpu_baseline) / max(cpu_baseline, 1)

            if cpu_drift > 0.3:
                drift_analyses.append(DriftAnalysis(
                    drift_type=DriftType.RESOURCE_DRIFT,
                    drift_magnitude=cpu_drift,
                    baseline_value=cpu_baseline,
                    current_value=cpu_current,
                    drift_direction="negative" if cpu_current > cpu_baseline else "positive",
                    affected_metrics=["cpu_percent"],
                    recommendation="Investigate CPU usage increase" if cpu_current > cpu_baseline else "Good performance",
                ))

        # Behavioral drift (from agent outputs)
        if sensor_data.agent_outputs:
            conf_baseline = self.BASELINES['decision_confidence']
            conf_current = sensor_data.agent_outputs.average_confidence
            conf_drift = abs(conf_current - conf_baseline) / max(conf_baseline, 0.1)

            if conf_drift > 0.2:
                drift_analyses.append(DriftAnalysis(
                    drift_type=DriftType.BEHAVIORAL_DRIFT,
                    drift_magnitude=conf_drift,
                    baseline_value=conf_baseline,
                    current_value=conf_current,
                    drift_direction="negative" if conf_current < conf_baseline else "positive",
                    affected_metrics=["decision_confidence"],
                    recommendation="Review decision quality" if conf_current < conf_baseline else "Confidence improved",
                ))

        # No drift detected
        if not drift_analyses:
            drift_analyses.append(DriftAnalysis(
                drift_type=DriftType.NO_DRIFT,
                drift_magnitude=0.0,
                recommendation="System operating within expected parameters",
            ))

        return drift_analyses

    def _forensic_analysis(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData
    ) -> List[ForensicFinding]:
        """Perform forensic analysis to identify root causes."""
        findings = []

        # Analyze test failures for root causes
        if sensor_data.test_results and sensor_data.test_results.failed > 0:
            # Check if infrastructure issues are the root cause
            if sensor_data.test_results.infrastructure_failures > sensor_data.test_results.code_failures:
                self._finding_counter += 1
                findings.append(ForensicFinding(
                    finding_id=f"FORENSIC-{self._finding_counter:04d}",
                    category="root_cause",
                    description="Infrastructure issues are primary cause of test failures",
                    evidence=[
                        {
                            'type': 'test_analysis',
                            'infrastructure_failures': sensor_data.test_results.infrastructure_failures,
                            'code_failures': sensor_data.test_results.code_failures,
                        }
                    ],
                    confidence=0.85,
                    related_components=["infrastructure", "services"],
                    timeline=[
                        {'event': 'Test failures detected', 'time': 'recent'},
                    ],
                ))

            # Check for error type clustering
            if sensor_data.test_results.top_error_types:
                dominant_error = max(
                    sensor_data.test_results.top_error_types.items(),
                    key=lambda x: x[1]
                )
                if dominant_error[1] >= 3:
                    self._finding_counter += 1
                    findings.append(ForensicFinding(
                        finding_id=f"FORENSIC-{self._finding_counter:04d}",
                        category="contributing_factor",
                        description=f"'{dominant_error[0]}' errors cluster suggests common issue",
                        evidence=[
                            {
                                'type': 'error_cluster',
                                'error_type': dominant_error[0],
                                'count': dominant_error[1],
                            }
                        ],
                        confidence=0.75,
                        related_components=[dominant_error[0]],
                    ))

        # Analyze service health for root causes
        if sensor_data.metrics:
            unhealthy = []
            if not sensor_data.metrics.database_health:
                unhealthy.append("database")
            if not sensor_data.metrics.llm_health:
                unhealthy.append("llm")

            if unhealthy:
                self._finding_counter += 1
                findings.append(ForensicFinding(
                    finding_id=f"FORENSIC-{self._finding_counter:04d}",
                    category="root_cause",
                    description=f"Service unavailability: {', '.join(unhealthy)}",
                    evidence=[
                        {
                            'type': 'service_health',
                            'unhealthy_services': unhealthy,
                        }
                    ],
                    confidence=0.9,
                    related_components=unhealthy,
                ))

        # Analyze anomalies for contributing factors
        for anomaly in interpreted_data.anomalies:
            if anomaly.severity > 0.6:
                self._finding_counter += 1
                findings.append(ForensicFinding(
                    finding_id=f"FORENSIC-{self._finding_counter:04d}",
                    category="symptom",
                    description=anomaly.description,
                    evidence=[
                        {
                            'type': 'anomaly',
                            'anomaly_type': anomaly.anomaly_type.value,
                            'severity': anomaly.severity,
                        }
                    ],
                    confidence=anomaly.severity,
                    related_components=anomaly.affected_components,
                ))

        return findings

    def _generate_avn_alerts(self, interpreted_data: InterpretedData) -> List[AVNAlert]:
        """Generate Anomaly Violation Notification alerts."""
        alerts = []

        # Generate alerts for high-severity anomalies
        for anomaly in interpreted_data.anomalies:
            if anomaly.severity > 0.5:
                self._alert_counter += 1
                severity = "critical" if anomaly.severity > 0.8 else "warning"
                alerts.append(AVNAlert(
                    alert_id=f"AVN-{self._alert_counter:04d}",
                    severity=severity,
                    anomaly_type=anomaly.anomaly_type.value,
                    violation_type=None,
                    message=anomaly.description,
                    details={
                        'expected': anomaly.expected_value,
                        'actual': anomaly.actual_value,
                        'deviation': anomaly.deviation_percent,
                        'affected_components': anomaly.affected_components,
                    },
                ))

        # Generate alerts for invariant violations
        for check in interpreted_data.invariant_checks:
            if not check.passed:
                self._alert_counter += 1
                alerts.append(AVNAlert(
                    alert_id=f"AVN-{self._alert_counter:04d}",
                    severity="warning" if check.severity < 0.7 else "critical",
                    anomaly_type="invariant_check",
                    violation_type=check.invariant_id,
                    message=f"Invariant '{check.invariant_name}' violated: {check.violation_details}",
                    details={
                        'invariant_id': check.invariant_id,
                        'invariant_name': check.invariant_name,
                        'severity': check.severity,
                    },
                ))

        return alerts

    def _update_avm_status(self, interpreted_data: InterpretedData) -> AVMStatus:
        """Update Anomaly Violation Monitor status."""
        anomaly_count = len(interpreted_data.anomalies)
        violation_count = sum(1 for c in interpreted_data.invariant_checks if not c.passed)

        # Determine alert level
        total_issues = anomaly_count + violation_count
        if total_issues >= self.avn_threshold * 2:
            alert_level = "critical"
        elif total_issues >= self.avn_threshold:
            alert_level = "elevated"
        else:
            alert_level = "normal"

        return AVMStatus(
            monitor_id="avm-001",
            is_active=True,
            anomalies_detected=anomaly_count,
            violations_detected=violation_count,
            last_check=datetime.utcnow(),
            alert_threshold=self.avn_threshold,
            current_alert_level=alert_level,
        )

    def _determine_action(self, result: JudgementResult) -> str:
        """Determine recommended action based on judgement."""
        # Critical health -> freeze
        if result.health.status == HealthStatus.CRITICAL:
            if result.confidence.overall_confidence > 0.7:
                return "freeze"
            return "alert"

        # Critical risks -> heal or alert
        critical_risks = [r for r in result.risk_vectors if r.level == RiskLevel.CRITICAL]
        if critical_risks:
            if result.confidence.overall_confidence > 0.8:
                return "heal"
            return "alert"

        # High risks or degraded health -> alert
        high_risks = [r for r in result.risk_vectors if r.level == RiskLevel.HIGH]
        if high_risks or result.health.status == HealthStatus.DEGRADED:
            return "alert"

        # Drift detected -> monitor
        significant_drift = [d for d in result.drift_analysis
                           if d.drift_type != DriftType.NO_DRIFT and d.drift_magnitude > 0.2]
        if significant_drift:
            return "monitor"

        # All good
        return "none"

    def to_dict(self, result: JudgementResult) -> Dict[str, Any]:
        """Convert judgement result to dictionary for serialization."""
        return {
            'judgement_timestamp': result.judgement_timestamp.isoformat(),
            'judgement_duration_ms': result.judgement_duration_ms,
            'recommended_action': result.recommended_action,
            'health': {
                'overall_score': result.health.overall_score,
                'status': result.health.status.value,
                'component_scores': result.health.component_scores,
                'degraded_components': result.health.degraded_components,
                'critical_components': result.health.critical_components,
                'trend': result.health.trend,
            },
            'confidence': {
                'overall_confidence': result.confidence.overall_confidence,
                'data_completeness': result.confidence.data_completeness,
                'signal_clarity': result.confidence.signal_clarity,
                'historical_correlation': result.confidence.historical_correlation,
                'reasoning': result.confidence.reasoning,
            },
            'risk_vectors': [
                {
                    'risk_id': r.risk_id,
                    'risk_type': r.risk_type,
                    'level': r.level.value,
                    'probability': r.probability,
                    'impact': r.impact,
                    'description': r.description,
                    'affected_components': r.affected_components,
                    'mitigation_suggestions': r.mitigation_suggestions,
                    'time_to_impact': r.time_to_impact,
                }
                for r in result.risk_vectors
            ],
            'drift_analysis': [
                {
                    'drift_type': d.drift_type.value,
                    'drift_magnitude': d.drift_magnitude,
                    'baseline_value': d.baseline_value,
                    'current_value': d.current_value,
                    'drift_direction': d.drift_direction,
                    'affected_metrics': d.affected_metrics,
                    'recommendation': d.recommendation,
                }
                for d in result.drift_analysis
            ],
            'forensic_findings': [
                {
                    'finding_id': f.finding_id,
                    'category': f.category,
                    'description': f.description,
                    'confidence': f.confidence,
                    'related_components': f.related_components,
                }
                for f in result.forensic_findings
            ],
            'avn_alerts': [
                {
                    'alert_id': a.alert_id,
                    'severity': a.severity,
                    'anomaly_type': a.anomaly_type,
                    'violation_type': a.violation_type,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat(),
                }
                for a in result.avn_alerts
            ],
            'avm_status': {
                'monitor_id': result.avm_status.monitor_id,
                'is_active': result.avm_status.is_active,
                'anomalies_detected': result.avm_status.anomalies_detected,
                'violations_detected': result.avm_status.violations_detected,
                'last_check': result.avm_status.last_check.isoformat(),
                'current_alert_level': result.avm_status.current_alert_level,
            },
            'summary': {
                'health_status': result.health.status.value,
                'confidence_level': 'high' if result.confidence.overall_confidence > 0.8 else 'medium' if result.confidence.overall_confidence > 0.5 else 'low',
                'total_risks': len(result.risk_vectors),
                'critical_risks': sum(1 for r in result.risk_vectors if r.level == RiskLevel.CRITICAL),
                'total_alerts': len(result.avn_alerts),
                'avm_level': result.avm_status.current_alert_level,
            }
        }
