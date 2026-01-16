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

from .sensors import (
    SensorData, TestResultData, MetricsData, CodeQualityData,
    BuildStatusData, TestCoverageData, APIContractData, InfrastructureData
)

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
    # FIX: Added new pattern types for static code analysis
    SECURITY_VULNERABILITY = "security_vulnerability"
    DATABASE_SCHEMA_ISSUE = "database_schema_issue"
    CONFIGURATION_ISSUE = "configuration_issue"
    DEPENDENCY_ISSUE = "dependency_issue"
    # WHOLE-SYSTEM PATTERNS: Track system beyond runtime
    BUILD_FAILURE = "build_failure"
    COVERAGE_GAP = "coverage_gap"
    API_CONTRACT_VIOLATION = "api_contract_violation"
    INFRASTRUCTURE_DEGRADATION = "infrastructure_degradation"


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
    # WHOLE-SYSTEM ANOMALIES
    BUILD_BROKEN = "build_broken"
    COVERAGE_DROP = "coverage_drop"
    API_DRIFT = "api_drift"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


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

        # FIX: Code quality patterns from static analysis
        if sensor_data.code_quality:
            patterns.extend(self._detect_code_quality_patterns(sensor_data.code_quality))

        # WHOLE-SYSTEM SENSOR PATTERNS
        if sensor_data.build_status:
            patterns.extend(self._detect_build_status_patterns(sensor_data.build_status))
        if sensor_data.test_coverage:
            patterns.extend(self._detect_coverage_patterns(sensor_data.test_coverage))
        if sensor_data.api_contract:
            patterns.extend(self._detect_api_contract_patterns(sensor_data.api_contract))
        if sensor_data.infrastructure:
            patterns.extend(self._detect_infrastructure_patterns(sensor_data.infrastructure))

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

    def _detect_code_quality_patterns(self, code_quality: CodeQualityData) -> List[Pattern]:
        """
        FIX: Detect patterns from code quality static analysis.

        This method analyzes the code quality sensor data to identify:
        - Security vulnerability patterns
        - Database schema issues
        - Configuration problems
        - Dependency management issues
        """
        patterns = []

        # Security vulnerability pattern
        if code_quality.critical_issues > 0:
            patterns.append(Pattern(
                pattern_type=PatternType.SECURITY_VULNERABILITY,
                description=f"CRITICAL: {code_quality.critical_issues} critical security vulnerabilities detected",
                confidence=1.0,
                frequency=code_quality.critical_issues,
                affected_components=["security", "code"],
                evidence=[{
                    'critical_count': code_quality.critical_issues,
                    'vulnerabilities': [
                        {
                            'type': v.issue_type,
                            'file': v.file_path,
                            'line': v.line_number,
                            'cwe': v.cwe_id,
                        }
                        for v in code_quality.security_vulnerabilities[:5]
                        if v.severity == 'critical'
                    ]
                }],
                suggested_action="IMMEDIATE: Fix critical security vulnerabilities"
            ))

        if code_quality.high_issues > 0:
            patterns.append(Pattern(
                pattern_type=PatternType.SECURITY_VULNERABILITY,
                description=f"HIGH: {code_quality.high_issues} high severity security issues detected",
                confidence=0.9,
                frequency=code_quality.high_issues,
                affected_components=["security"],
                evidence=[{
                    'high_count': code_quality.high_issues,
                    'issues': [
                        {
                            'type': v.issue_type,
                            'file': v.file_path,
                            'line': v.line_number,
                        }
                        for v in code_quality.security_vulnerabilities[:5]
                        if v.severity == 'high'
                    ]
                }],
                suggested_action="Fix high severity security issues"
            ))

        # Database schema issue pattern
        if code_quality.database_issues:
            db_issue_count = len(code_quality.database_issues)
            patterns.append(Pattern(
                pattern_type=PatternType.DATABASE_SCHEMA_ISSUE,
                description=f"{db_issue_count} database schema issues detected",
                confidence=0.8,
                frequency=db_issue_count,
                affected_components=["database", "models"],
                evidence=[{
                    'issues': [
                        {
                            'type': i.issue_type,
                            'file': i.file_path,
                            'description': i.description,
                        }
                        for i in code_quality.database_issues[:5]
                    ]
                }],
                suggested_action="Review database models for type mismatches and missing constraints"
            ))

        # Configuration issue pattern
        if code_quality.configuration_issues:
            config_issue_count = len(code_quality.configuration_issues)
            patterns.append(Pattern(
                pattern_type=PatternType.CONFIGURATION_ISSUE,
                description=f"{config_issue_count} configuration security issues detected",
                confidence=0.7,
                frequency=config_issue_count,
                affected_components=["configuration", "security"],
                evidence=[{
                    'issues': [
                        {
                            'type': i.issue_type,
                            'file': i.file_path,
                            'description': i.description,
                        }
                        for i in code_quality.configuration_issues[:5]
                    ]
                }],
                suggested_action="Review security configuration settings"
            ))

        # Dependency issue pattern
        if code_quality.dependency_issues:
            dep_issue_count = len(code_quality.dependency_issues)
            patterns.append(Pattern(
                pattern_type=PatternType.DEPENDENCY_ISSUE,
                description=f"{dep_issue_count} dependency management issues detected",
                confidence=0.6,
                frequency=dep_issue_count,
                affected_components=["dependencies", "supply_chain"],
                evidence=[{
                    'unpinned_count': dep_issue_count,
                    'examples': [i.code_snippet for i in code_quality.dependency_issues[:5]]
                }],
                suggested_action="Pin dependency versions for reproducibility and security"
            ))

        # Overall code quality summary pattern
        if code_quality.total_issues > 10:
            patterns.append(Pattern(
                pattern_type=PatternType.CODE_QUALITY_ISSUE,
                description=f"Code quality scan found {code_quality.total_issues} total issues",
                confidence=0.8,
                frequency=code_quality.total_issues,
                affected_components=["codebase"],
                evidence=[{
                    'total': code_quality.total_issues,
                    'critical': code_quality.critical_issues,
                    'high': code_quality.high_issues,
                    'medium': code_quality.medium_issues,
                    'low': code_quality.low_issues,
                    'files_scanned': code_quality.files_scanned,
                }],
                suggested_action="Prioritize fixing critical and high severity issues"
            ))

        return patterns

    # ==================== WHOLE-SYSTEM PATTERN DETECTION ====================

    def _detect_build_status_patterns(self, build_status: BuildStatusData) -> List[Pattern]:
        """Detect patterns from build/CI status sensor."""
        patterns = []

        # Build failure pattern
        if not build_status.build_passing:
            failed_checks = []
            if not build_status.lint_passing:
                failed_checks.append("lint")
            if not build_status.type_check_passing:
                failed_checks.append("type_check")
            if not build_status.tests_passing:
                failed_checks.append("tests")

            patterns.append(Pattern(
                pattern_type=PatternType.BUILD_FAILURE,
                description=f"Build failing: {', '.join(failed_checks) or 'unknown cause'}",
                confidence=1.0,
                frequency=1,
                affected_components=["build", "ci_cd"] + failed_checks,
                evidence=[{
                    'build_passing': build_status.build_passing,
                    'lint_passing': build_status.lint_passing,
                    'type_check_passing': build_status.type_check_passing,
                    'tests_passing': build_status.tests_passing,
                    'last_status': build_status.last_build_status,
                    'branch': build_status.branch_name,
                    'commit': build_status.commit_sha,
                }],
                suggested_action="Fix build failures before merging"
            ))

        # CI provider pattern (informational)
        if build_status.ci_provider != 'unknown':
            patterns.append(Pattern(
                pattern_type=PatternType.LEARNING_OPPORTUNITY,
                description=f"CI/CD via {build_status.ci_provider}",
                confidence=0.5,
                frequency=1,
                affected_components=["ci_cd"],
                evidence=[{'ci_provider': build_status.ci_provider}],
            ))

        return patterns

    def _detect_coverage_patterns(self, coverage: TestCoverageData) -> List[Pattern]:
        """Detect patterns from test coverage sensor."""
        patterns = []

        # Low coverage pattern
        if coverage.overall_coverage_percent < 50:
            patterns.append(Pattern(
                pattern_type=PatternType.COVERAGE_GAP,
                description=f"Critical: Test coverage at {coverage.overall_coverage_percent:.1f}%",
                confidence=1.0,
                frequency=len(coverage.uncovered_files),
                affected_components=["tests", "coverage"],
                evidence=[{
                    'overall_coverage': coverage.overall_coverage_percent,
                    'line_coverage': coverage.line_coverage_percent,
                    'branch_coverage': coverage.branch_coverage_percent,
                    'uncovered_files': coverage.uncovered_files[:5],
                }],
                suggested_action="Add tests for critical code paths"
            ))
        elif coverage.overall_coverage_percent < 70:
            patterns.append(Pattern(
                pattern_type=PatternType.COVERAGE_GAP,
                description=f"Warning: Test coverage at {coverage.overall_coverage_percent:.1f}%",
                confidence=0.8,
                frequency=len(coverage.uncovered_files),
                affected_components=["tests", "coverage"],
                evidence=[{
                    'overall_coverage': coverage.overall_coverage_percent,
                    'uncovered_files_count': len(coverage.uncovered_files),
                }],
                suggested_action="Improve test coverage"
            ))

        # Critical paths uncovered
        if not coverage.critical_paths_covered:
            patterns.append(Pattern(
                pattern_type=PatternType.COVERAGE_GAP,
                description="CRITICAL: Security/auth paths have insufficient test coverage",
                confidence=1.0,
                frequency=1,
                affected_components=["security", "auth", "tests"],
                evidence=[{
                    'critical_paths_covered': False,
                    'trend': coverage.coverage_trend,
                }],
                suggested_action="IMMEDIATE: Add tests for security and authentication code"
            ))

        # Coverage trend
        if coverage.coverage_trend == "declining":
            patterns.append(Pattern(
                pattern_type=PatternType.COVERAGE_GAP,
                description="Test coverage is declining",
                confidence=0.7,
                frequency=1,
                affected_components=["tests", "coverage"],
                evidence=[{
                    'trend': coverage.coverage_trend,
                    'delta': coverage.coverage_delta,
                }],
                suggested_action="Review recent commits for missing tests"
            ))

        return patterns

    def _detect_api_contract_patterns(self, api: APIContractData) -> List[Pattern]:
        """Detect patterns from API contract sensor."""
        patterns = []

        # Invalid spec
        if not api.spec_valid and api.spec_path:
            patterns.append(Pattern(
                pattern_type=PatternType.API_CONTRACT_VIOLATION,
                description="OpenAPI specification is invalid",
                confidence=1.0,
                frequency=1,
                affected_components=["api", "documentation"],
                evidence=[{'spec_path': api.spec_path}],
                suggested_action="Fix OpenAPI specification syntax errors"
            ))

        # Undocumented endpoints
        if api.undocumented_endpoints:
            patterns.append(Pattern(
                pattern_type=PatternType.API_CONTRACT_VIOLATION,
                description=f"{len(api.undocumented_endpoints)} API endpoints not documented",
                confidence=0.9,
                frequency=len(api.undocumented_endpoints),
                affected_components=["api", "documentation"],
                evidence=[{
                    'undocumented': api.undocumented_endpoints[:5],
                    'total_endpoints': api.total_endpoints,
                    'compliance_percent': api.compliance_percent,
                }],
                suggested_action="Add missing endpoints to OpenAPI spec"
            ))

        # Missing implementations
        if api.missing_implementations:
            patterns.append(Pattern(
                pattern_type=PatternType.API_CONTRACT_VIOLATION,
                description=f"{len(api.missing_implementations)} documented endpoints not implemented",
                confidence=0.9,
                frequency=len(api.missing_implementations),
                affected_components=["api", "implementation"],
                evidence=[{
                    'missing': api.missing_implementations[:5],
                }],
                suggested_action="Implement missing documented endpoints or update spec"
            ))

        # Low compliance
        if api.compliance_percent < 80 and api.total_endpoints > 0:
            patterns.append(Pattern(
                pattern_type=PatternType.API_CONTRACT_VIOLATION,
                description=f"API contract compliance at {api.compliance_percent:.1f}%",
                confidence=0.8,
                frequency=api.non_compliant_endpoints,
                affected_components=["api"],
                evidence=[{
                    'compliance_percent': api.compliance_percent,
                    'compliant': api.compliant_endpoints,
                    'total': api.total_endpoints,
                }],
                suggested_action="Align API implementation with documentation"
            ))

        return patterns

    def _detect_infrastructure_patterns(self, infra: InfrastructureData) -> List[Pattern]:
        """Detect patterns from infrastructure sensor."""
        patterns = []

        # Unhealthy containers
        if infra.containers_unhealthy > 0:
            patterns.append(Pattern(
                pattern_type=PatternType.INFRASTRUCTURE_DEGRADATION,
                description=f"{infra.containers_unhealthy} containers in unhealthy state",
                confidence=1.0,
                frequency=infra.containers_unhealthy,
                affected_components=["containers", "docker"],
                evidence=[{
                    'unhealthy_count': infra.containers_unhealthy,
                    'running_count': infra.containers_running,
                    'stopped_count': infra.containers_stopped,
                }],
                suggested_action="Investigate and restart unhealthy containers"
            ))

        # External dependency failures
        unhealthy_deps = [d for d in infra.external_dependencies if d.status != 'healthy']
        if unhealthy_deps:
            patterns.append(Pattern(
                pattern_type=PatternType.INFRASTRUCTURE_DEGRADATION,
                description=f"{len(unhealthy_deps)} external dependencies unreachable",
                confidence=0.9,
                frequency=len(unhealthy_deps),
                affected_components=["infrastructure", "external_services"],
                evidence=[{
                    'unhealthy_services': [
                        {'name': d.name, 'status': d.status, 'error': d.error_message}
                        for d in unhealthy_deps
                    ]
                }],
                suggested_action="Check external service connectivity"
            ))

        # Network connectivity issues
        if not infra.network_connectivity:
            patterns.append(Pattern(
                pattern_type=PatternType.INFRASTRUCTURE_DEGRADATION,
                description="Network connectivity issues detected",
                confidence=1.0,
                frequency=1,
                affected_components=["network", "infrastructure"],
                evidence=[{'network_connectivity': False}],
                suggested_action="Check network configuration and firewall rules"
            ))

        # Resource pressure
        if infra.memory_pressure or infra.disk_space_critical:
            resources = []
            if infra.memory_pressure:
                resources.append("memory")
            if infra.disk_space_critical:
                resources.append("disk")

            patterns.append(Pattern(
                pattern_type=PatternType.INFRASTRUCTURE_DEGRADATION,
                description=f"Resource pressure detected: {', '.join(resources)}",
                confidence=0.9,
                frequency=1,
                affected_components=resources + ["infrastructure"],
                evidence=[{
                    'memory_pressure': infra.memory_pressure,
                    'disk_space_critical': infra.disk_space_critical,
                }],
                suggested_action="Free up resources or scale infrastructure"
            ))

        # Low infrastructure score
        if infra.infrastructure_score < 70:
            patterns.append(Pattern(
                pattern_type=PatternType.INFRASTRUCTURE_DEGRADATION,
                description=f"Infrastructure health score: {infra.infrastructure_score:.1f}/100",
                confidence=0.8,
                frequency=1,
                affected_components=["infrastructure"],
                evidence=[{
                    'score': infra.infrastructure_score,
                    'docker_available': infra.docker_available,
                    'kubernetes_available': infra.kubernetes_available,
                    'total_services': infra.total_services,
                    'healthy_services': infra.healthy_services,
                }],
                suggested_action="Review and remediate infrastructure issues"
            ))

        return patterns

    # ==================== WHOLE-SYSTEM ANOMALY DETECTION ====================

    def _detect_build_anomalies(self, build_status: BuildStatusData) -> List[Anomaly]:
        """Detect anomalies from build status sensor."""
        anomalies = []

        if not build_status.build_passing:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.BUILD_BROKEN,
                severity=0.9,
                description="Build is broken",
                expected_value="passing",
                actual_value=build_status.last_build_status,
                affected_components=["build", "ci_cd"],
            ))

        return anomalies

    def _detect_coverage_anomalies(self, coverage: TestCoverageData) -> List[Anomaly]:
        """Detect anomalies from coverage sensor."""
        anomalies = []

        if coverage.overall_coverage_percent < 50:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.COVERAGE_DROP,
                severity=0.8,
                description=f"Test coverage critically low at {coverage.overall_coverage_percent:.1f}%",
                expected_value=70.0,
                actual_value=coverage.overall_coverage_percent,
                deviation_percent=70 - coverage.overall_coverage_percent,
                affected_components=["tests", "coverage"],
            ))

        if not coverage.critical_paths_covered:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.COVERAGE_DROP,
                severity=1.0,
                description="Critical security paths not covered by tests",
                expected_value="covered",
                actual_value="not covered",
                affected_components=["security", "auth", "tests"],
            ))

        return anomalies

    def _detect_api_anomalies(self, api: APIContractData) -> List[Anomaly]:
        """Detect anomalies from API contract sensor."""
        anomalies = []

        if api.compliance_percent < 80 and api.total_endpoints > 0:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.API_DRIFT,
                severity=0.6,
                description=f"API contract compliance at {api.compliance_percent:.1f}%",
                expected_value=100.0,
                actual_value=api.compliance_percent,
                deviation_percent=100 - api.compliance_percent,
                affected_components=["api", "documentation"],
            ))

        return anomalies

    def _detect_infrastructure_anomalies(self, infra: InfrastructureData) -> List[Anomaly]:
        """Detect anomalies from infrastructure sensor."""
        anomalies = []

        if infra.containers_unhealthy > 0:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.INFRASTRUCTURE_FAILURE,
                severity=0.8,
                description=f"{infra.containers_unhealthy} unhealthy containers",
                expected_value=0,
                actual_value=infra.containers_unhealthy,
                affected_components=["containers", "docker"],
            ))

        if not infra.network_connectivity:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.INFRASTRUCTURE_FAILURE,
                severity=1.0,
                description="Network connectivity lost",
                expected_value="connected",
                actual_value="disconnected",
                affected_components=["network"],
            ))

        if infra.infrastructure_score < 50:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.INFRASTRUCTURE_FAILURE,
                severity=0.9,
                description=f"Infrastructure health critical: {infra.infrastructure_score:.1f}/100",
                expected_value=80.0,
                actual_value=infra.infrastructure_score,
                deviation_percent=80 - infra.infrastructure_score,
                affected_components=["infrastructure"],
            ))

        return anomalies

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

        # WHOLE-SYSTEM ANOMALIES
        if sensor_data.build_status:
            anomalies.extend(self._detect_build_anomalies(sensor_data.build_status))
        if sensor_data.test_coverage:
            anomalies.extend(self._detect_coverage_anomalies(sensor_data.test_coverage))
        if sensor_data.api_contract:
            anomalies.extend(self._detect_api_anomalies(sensor_data.api_contract))
        if sensor_data.infrastructure:
            anomalies.extend(self._detect_infrastructure_anomalies(sensor_data.infrastructure))

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
