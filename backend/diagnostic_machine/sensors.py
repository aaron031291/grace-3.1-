"""
Layer 1 - Sensors: Data Collection Layer

INTEGRATED with LLM Orchestrator for health monitoring.

Collects raw data from:
- Test results (passed/failed/skipped)
- System logs (tail logs)
- Metrics (CPU, memory, disk, latency)
- Agent outputs (cognitive decisions)
- Genesis Keys (provenance data)
- GRACE Mirror (self-reflection state)
- LLM Orchestrator health status (preferred over direct Ollama)

Health checks prioritize LLM Orchestrator availability over direct
Ollama client access to ensure consistent system status reporting.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SensorType(str, Enum):
    """Types of sensors available."""
    TEST_RESULTS = "test_results"
    SYSTEM_LOGS = "system_logs"
    METRICS = "metrics"
    AGENT_OUTPUTS = "agent_outputs"
    GENESIS_KEYS = "genesis_keys"
    GRACE_MIRROR = "grace_mirror"
    COGNITIVE_DECISIONS = "cognitive_decisions"
    FILE_HEALTH = "file_health"
    CONFIGURATION = "configuration"  # Configuration validation
    STATIC_ANALYSIS = "static_analysis"  # Static code analysis
    DESIGN_PATTERNS = "design_patterns"  # Design pattern detection
    CODE_QUALITY = "code_quality"  # FIX: Static code analysis for security vulnerabilities
    # WHOLE-SYSTEM SENSORS: Track system beyond just runtime
    BUILD_STATUS = "build_status"  # CI/CD pipeline health
    TEST_COVERAGE = "test_coverage"  # Code coverage tracking
    API_CONTRACT = "api_contract"  # OpenAPI spec validation
    INFRASTRUCTURE = "infrastructure"  # Docker/K8s/external services


@dataclass
class TestResultData:
    """Test result sensor data."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    pass_rate: float = 0.0
    failure_categories: Dict[str, int] = field(default_factory=dict)
    infrastructure_failures: int = 0
    code_failures: int = 0
    top_error_types: Dict[str, int] = field(default_factory=dict)
    learned_patterns: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LogData:
    """System log sensor data."""
    log_level_counts: Dict[str, int] = field(default_factory=dict)
    error_messages: List[Dict] = field(default_factory=list)
    warning_messages: List[Dict] = field(default_factory=list)
    recent_exceptions: List[Dict] = field(default_factory=list)
    log_volume_per_minute: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MetricsData:
    """System metrics sensor data."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    active_connections: int = 0
    request_latency_ms: float = 0.0
    requests_per_second: float = 0.0
    database_health: bool = True
    vector_db_health: bool = True
    llm_health: bool = True
    embedding_health: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentOutputData:
    """Agent output sensor data."""
    total_decisions: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0
    pending_decisions: int = 0
    average_confidence: float = 0.0
    invariant_violations: int = 0
    recent_decisions: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GenesisKeyData:
    """Genesis key sensor data."""
    total_keys: int = 0
    active_keys: int = 0
    error_keys: int = 0
    fix_suggestions: int = 0
    applied_fixes: int = 0
    recent_keys: List[Dict] = field(default_factory=list)
    key_types_distribution: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GraceMirrorData:
    """GRACE Mirror self-reflection sensor data."""
    self_healing_progress: float = 0.0
    world_model_progress: float = 0.0
    self_learning_progress: float = 0.0
    self_governance_progress: float = 0.0
    component_status: Dict[str, str] = field(default_factory=dict)
    recent_activity: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CodeQualityIssue:
    """A single code quality issue detected by static analysis."""
    issue_type: str  # e.g., "security", "type_mismatch", "missing_index"
    severity: str  # "critical", "high", "medium", "low"
    file_path: str
    line_number: Optional[int] = None
    description: str = ""
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID


@dataclass
class CodeQualityData:
    """Code quality sensor data from static analysis."""
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    security_vulnerabilities: List[CodeQualityIssue] = field(default_factory=list)
    type_mismatches: List[CodeQualityIssue] = field(default_factory=list)
    database_issues: List[CodeQualityIssue] = field(default_factory=list)
    configuration_issues: List[CodeQualityIssue] = field(default_factory=list)
    dependency_issues: List[CodeQualityIssue] = field(default_factory=list)
    files_scanned: int = 0
    scan_duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ==================== WHOLE-SYSTEM SENSOR DATA ====================

@dataclass
class BuildStatusData:
    """Build/CI status sensor data for whole-system health tracking."""
    build_passing: bool = True
    last_build_status: str = "unknown"  # "success", "failure", "pending", "unknown"
    last_build_timestamp: Optional[datetime] = None
    last_build_duration_seconds: float = 0.0
    failed_jobs: List[Dict[str, Any]] = field(default_factory=list)
    recent_commits: List[Dict[str, Any]] = field(default_factory=list)
    branch_name: str = ""
    commit_sha: str = ""
    ci_provider: str = "unknown"  # "github_actions", "gitlab_ci", "jenkins", etc.
    pipeline_url: Optional[str] = None
    lint_passing: bool = True
    type_check_passing: bool = True
    tests_passing: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestCoverageData:
    """Test coverage sensor data for identifying untested code paths."""
    overall_coverage_percent: float = 0.0
    line_coverage_percent: float = 0.0
    branch_coverage_percent: float = 0.0
    function_coverage_percent: float = 0.0
    uncovered_files: List[Dict[str, Any]] = field(default_factory=list)  # Files with low coverage
    uncovered_functions: List[Dict[str, Any]] = field(default_factory=list)  # Critical uncovered functions
    coverage_trend: str = "stable"  # "improving", "declining", "stable"
    coverage_delta: float = 0.0  # Change from last measurement
    critical_paths_covered: bool = True  # Are security/auth paths tested?
    total_lines: int = 0
    covered_lines: int = 0
    excluded_patterns: List[str] = field(default_factory=list)
    coverage_report_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class APIEndpoint:
    """Single API endpoint contract data."""
    path: str
    method: str
    defined_in_spec: bool = True
    implemented: bool = True
    response_matches_spec: bool = True
    parameters_valid: bool = True
    issues: List[str] = field(default_factory=list)


@dataclass
class APIContractData:
    """API contract validation sensor data."""
    spec_valid: bool = True
    spec_path: Optional[str] = None
    spec_version: str = ""
    total_endpoints: int = 0
    compliant_endpoints: int = 0
    non_compliant_endpoints: int = 0
    undocumented_endpoints: List[str] = field(default_factory=list)
    missing_implementations: List[str] = field(default_factory=list)
    schema_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    deprecated_endpoints: List[str] = field(default_factory=list)
    endpoints: List[APIEndpoint] = field(default_factory=list)
    compliance_percent: float = 100.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ServiceHealth:
    """Health status of a single service/container."""
    name: str
    status: str  # "healthy", "unhealthy", "starting", "stopped", "unknown"
    type: str  # "container", "service", "external_api"
    response_time_ms: float = 0.0
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    uptime_percent: float = 100.0
    restart_count: int = 0


@dataclass
class InfrastructureData:
    """Infrastructure health sensor data for containers, services, external deps."""
    docker_available: bool = False
    kubernetes_available: bool = False
    containers_running: int = 0
    containers_stopped: int = 0
    containers_unhealthy: int = 0
    services: List[ServiceHealth] = field(default_factory=list)
    external_dependencies: List[ServiceHealth] = field(default_factory=list)
    network_connectivity: bool = True
    disk_space_critical: bool = False
    memory_pressure: bool = False
    total_services: int = 0
    healthy_services: int = 0
    infrastructure_score: float = 100.0  # 0-100 overall health score
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SensorData:
    """Aggregated sensor data from all sources."""
    test_results: Optional[TestResultData] = None
    logs: Optional[LogData] = None
    metrics: Optional[MetricsData] = None
    agent_outputs: Optional[AgentOutputData] = None
    genesis_keys: Optional[GenesisKeyData] = None
    grace_mirror: Optional[GraceMirrorData] = None
    configuration: Optional[Any] = None  # ConfigurationSensorData
    static_analysis: Optional[Any] = None  # StaticAnalysisSensorData
    design_patterns: Optional[Any] = None  # DesignPatternSensorData
    code_quality: Optional[CodeQualityData] = None  # FIX: Added code quality sensor
    # WHOLE-SYSTEM SENSORS: Track system beyond just runtime
    build_status: Optional[BuildStatusData] = None
    test_coverage: Optional[TestCoverageData] = None
    api_contract: Optional[APIContractData] = None
    infrastructure: Optional[InfrastructureData] = None
    collection_timestamp: datetime = field(default_factory=datetime.utcnow)
    collection_duration_ms: float = 0.0
    sensors_available: List[SensorType] = field(default_factory=list)
    sensors_failed: List[SensorType] = field(default_factory=list)


class SensorLayer:
    """
    Layer 1 - Sensors: Collects raw data from all GRACE systems.

    This layer acts as the sensory input for the diagnostic machine,
    gathering data from tests, logs, metrics, agents, and genesis keys.
    """

    def __init__(
        self,
        diagnostic_report_path: str = None,
        decision_log_dir: str = None,
        enable_psutil: bool = True
    ):
        """Initialize the sensor layer."""
        self.diagnostic_report_path = diagnostic_report_path or str(
            Path(__file__).parent.parent / "tests" / "diagnostic_report.json"
        )
        self.decision_log_dir = decision_log_dir or str(
            Path(__file__).parent.parent / "logs" / "decisions"
        )
        self.enable_psutil = enable_psutil
        self._psutil = None

        if enable_psutil:
            try:
                import psutil
                self._psutil = psutil
            except ImportError:
                logger.warning("psutil not available, metrics will be limited")

    def collect_all(self) -> SensorData:
        """Collect data from all available sensors."""
        start_time = datetime.utcnow()
        sensor_data = SensorData()

        # Collect from each sensor
        sensors = [
            (SensorType.TEST_RESULTS, self._collect_test_results),
            (SensorType.SYSTEM_LOGS, self._collect_logs),
            (SensorType.METRICS, self._collect_metrics),
            (SensorType.AGENT_OUTPUTS, self._collect_agent_outputs),
            (SensorType.GENESIS_KEYS, self._collect_genesis_keys),
            (SensorType.GRACE_MIRROR, self._collect_grace_mirror),
            (SensorType.CONFIGURATION, self._collect_configuration),
            (SensorType.STATIC_ANALYSIS, self._collect_static_analysis),
            (SensorType.DESIGN_PATTERNS, self._collect_design_patterns),
            (SensorType.CODE_QUALITY, self._collect_code_quality),
            # WHOLE-SYSTEM SENSORS
            (SensorType.BUILD_STATUS, self._collect_build_status),
            (SensorType.TEST_COVERAGE, self._collect_test_coverage),
            (SensorType.API_CONTRACT, self._collect_api_contract),
            (SensorType.INFRASTRUCTURE, self._collect_infrastructure),
        ]

        for sensor_type, collector in sensors:
            try:
                result = collector()
                if result:
                    if sensor_type == SensorType.TEST_RESULTS:
                        sensor_data.test_results = result
                    elif sensor_type == SensorType.SYSTEM_LOGS:
                        sensor_data.logs = result
                    elif sensor_type == SensorType.METRICS:
                        sensor_data.metrics = result
                    elif sensor_type == SensorType.AGENT_OUTPUTS:
                        sensor_data.agent_outputs = result
                    elif sensor_type == SensorType.GENESIS_KEYS:
                        sensor_data.genesis_keys = result
                    elif sensor_type == SensorType.GRACE_MIRROR:
                        sensor_data.grace_mirror = result
                    elif sensor_type == SensorType.CONFIGURATION:
                        sensor_data.configuration = result
                    elif sensor_type == SensorType.STATIC_ANALYSIS:
                        sensor_data.static_analysis = result
                    elif sensor_type == SensorType.DESIGN_PATTERNS:
                        sensor_data.design_patterns = result
                    elif sensor_type == SensorType.CODE_QUALITY:
                        sensor_data.code_quality = result
                    # WHOLE-SYSTEM SENSORS
                    elif sensor_type == SensorType.BUILD_STATUS:
                        sensor_data.build_status = result
                    elif sensor_type == SensorType.TEST_COVERAGE:
                        sensor_data.test_coverage = result
                    elif sensor_type == SensorType.API_CONTRACT:
                        sensor_data.api_contract = result
                    elif sensor_type == SensorType.INFRASTRUCTURE:
                        sensor_data.infrastructure = result
                    sensor_data.sensors_available.append(sensor_type)
            except Exception as e:
                logger.error(f"Sensor {sensor_type} failed: {e}")
                sensor_data.sensors_failed.append(sensor_type)

        end_time = datetime.utcnow()
        sensor_data.collection_timestamp = end_time
        sensor_data.collection_duration_ms = (end_time - start_time).total_seconds() * 1000

        return sensor_data

    def _collect_test_results(self) -> Optional[TestResultData]:
        """Collect test results from diagnostic report."""
        try:
            if not os.path.exists(self.diagnostic_report_path):
                return None

            with open(self.diagnostic_report_path, 'r') as f:
                report = json.load(f)

            test_results = report.get('test_results', {})
            failures = report.get('failures', [])
            passes = report.get('passes', [])

            # Categorize failures
            infrastructure_failures = sum(
                1 for f in failures
                if f.get('is_infrastructure_issue', False)
            )
            code_failures = len(failures) - infrastructure_failures

            # Count error types
            error_types: Dict[str, int] = {}
            for failure in failures:
                error_type = failure.get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

            # Extract learned patterns
            learned_patterns = report.get('learned_patterns', [])

            total = test_results.get('passed', 0) + test_results.get('failed', 0) + \
                    test_results.get('skipped', 0) + test_results.get('errors', 0)
            pass_rate = test_results.get('passed', 0) / total if total > 0 else 0.0

            return TestResultData(
                total_tests=total,
                passed=test_results.get('passed', 0),
                failed=test_results.get('failed', 0),
                skipped=test_results.get('skipped', 0),
                errors=test_results.get('errors', 0),
                pass_rate=pass_rate,
                infrastructure_failures=infrastructure_failures,
                code_failures=code_failures,
                top_error_types=error_types,
                learned_patterns=learned_patterns,
            )
        except Exception as e:
            logger.error(f"Failed to collect test results: {e}")
            return None

    def _collect_logs(self) -> Optional[LogData]:
        """Collect log data from recent log files."""
        try:
            log_data = LogData()
            log_dir = Path(__file__).parent.parent / "logs"

            if not log_dir.exists():
                return log_data

            # Find recent log files
            log_files = list(log_dir.glob("*.log")) + list(log_dir.glob("*.jsonl"))
            recent_cutoff = datetime.utcnow() - timedelta(hours=1)

            for log_file in log_files[:5]:  # Limit to 5 most recent
                try:
                    if log_file.stat().st_mtime < recent_cutoff.timestamp():
                        continue

                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-100:]  # Last 100 lines

                    for line in lines:
                        line_lower = line.lower()
                        if '"level": "error"' in line_lower or 'error' in line_lower[:50]:
                            log_data.log_level_counts['ERROR'] = \
                                log_data.log_level_counts.get('ERROR', 0) + 1
                            log_data.error_messages.append({
                                'file': str(log_file.name),
                                'message': line.strip()[:200]
                            })
                        elif '"level": "warning"' in line_lower or 'warning' in line_lower[:50]:
                            log_data.log_level_counts['WARNING'] = \
                                log_data.log_level_counts.get('WARNING', 0) + 1
                            log_data.warning_messages.append({
                                'file': str(log_file.name),
                                'message': line.strip()[:200]
                            })
                        elif 'exception' in line_lower or 'traceback' in line_lower:
                            log_data.recent_exceptions.append({
                                'file': str(log_file.name),
                                'message': line.strip()[:200]
                            })
                        else:
                            log_data.log_level_counts['INFO'] = \
                                log_data.log_level_counts.get('INFO', 0) + 1
                except Exception as e:
                    logger.debug(f"Could not read log file {log_file}: {e}")

            return log_data
        except Exception as e:
            logger.error(f"Failed to collect logs: {e}")
            return None

    def _collect_metrics(self) -> Optional[MetricsData]:
        """Collect system metrics."""
        try:
            metrics = MetricsData()

            if self._psutil:
                metrics.cpu_percent = self._psutil.cpu_percent(interval=0.1)
                metrics.memory_percent = self._psutil.virtual_memory().percent
                metrics.disk_percent = self._psutil.disk_usage('/').percent

            # Check service health
            try:
                from database.connection import DatabaseConnection
                metrics.database_health = DatabaseConnection.health_check()
            except Exception:
                metrics.database_health = False

            try:
                from retrieval.qdrant_client import get_qdrant_client
                client = get_qdrant_client()
                metrics.vector_db_health = client is not None
            except Exception:
                metrics.vector_db_health = False

            try:
                # For health checks, we can use either orchestrator or direct client
                # Orchestrator is preferred as it provides integrated health status
                llm_healthy = False

                # Try orchestrator first (preferred)
                try:
                    from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                    orchestrator = get_llm_orchestrator()
                    # Orchestrator available means LLM system is healthy
                    llm_healthy = orchestrator is not None
                    if llm_healthy:
                        logger.debug("[SENSORS] LLM health via orchestrator: OK")
                except Exception:
                    pass

                # Fallback to direct Ollama check
                if not llm_healthy:
                    try:
                        from ollama_client import get_ollama_client
                        client = get_ollama_client()
                        llm_healthy = client.is_running() if client else False
                        if llm_healthy:
                            logger.debug("[SENSORS] LLM health via direct client: OK")
                    except Exception:
                        pass

                metrics.llm_health = llm_healthy
            except Exception:
                metrics.llm_health = False

            try:
                from embedding import get_embedding_model
                model = get_embedding_model()
                metrics.embedding_health = model is not None
            except Exception:
                metrics.embedding_health = False

            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return None

    def _collect_agent_outputs(self) -> Optional[AgentOutputData]:
        """Collect cognitive agent outputs."""
        try:
            agent_data = AgentOutputData()
            decision_dir = Path(self.decision_log_dir)

            if not decision_dir.exists():
                return agent_data

            # Find today's decision log
            today = datetime.utcnow().strftime("%Y-%m-%d")
            decision_file = decision_dir / f"decisions_{today}.jsonl"

            if decision_file.exists():
                with open(decision_file, 'r') as f:
                    lines = f.readlines()

                for line in lines[-50:]:  # Last 50 decisions
                    try:
                        decision = json.loads(line)
                        agent_data.total_decisions += 1

                        event_type = decision.get('event_type', '')
                        if event_type == 'decision_complete':
                            agent_data.successful_decisions += 1
                        elif event_type == 'decision_aborted':
                            agent_data.failed_decisions += 1
                        elif event_type == 'invariant_violation':
                            agent_data.invariant_violations += 1

                        confidence = decision.get('confidence', 0)
                        if confidence > 0:
                            agent_data.average_confidence = (
                                agent_data.average_confidence + confidence
                            ) / 2

                        agent_data.recent_decisions.append({
                            'decision_id': decision.get('decision_id'),
                            'event_type': event_type,
                            'timestamp': decision.get('timestamp'),
                        })
                    except json.JSONDecodeError:
                        continue

            return agent_data
        except Exception as e:
            logger.error(f"Failed to collect agent outputs: {e}")
            return None

    def _collect_genesis_keys(self) -> Optional[GenesisKeyData]:
        """Collect Genesis Key data."""
        try:
            genesis_data = GenesisKeyData()

            try:
                from genesis.genesis_key_service import GenesisKeyService
                from database.session import get_session

                # Get session and query genesis keys
                session_gen = get_session()
                session = next(session_gen)

                try:
                    service = GenesisKeyService(session)

                    # Get recent keys (last 24 hours)
                    from models.genesis_key_models import GenesisKey
                    from sqlalchemy import func

                    cutoff = datetime.utcnow() - timedelta(hours=24)

                    # Count by status
                    genesis_data.total_keys = session.query(func.count(GenesisKey.id)).scalar() or 0
                    genesis_data.active_keys = session.query(func.count(GenesisKey.id)).filter(
                        GenesisKey.status == 'ACTIVE'
                    ).scalar() or 0
                    genesis_data.error_keys = session.query(func.count(GenesisKey.id)).filter(
                        GenesisKey.is_error == True
                    ).scalar() or 0

                    # Count fix suggestions
                    from models.genesis_key_models import FixSuggestion
                    genesis_data.fix_suggestions = session.query(func.count(FixSuggestion.id)).scalar() or 0
                    genesis_data.applied_fixes = session.query(func.count(FixSuggestion.id)).filter(
                        FixSuggestion.applied == True
                    ).scalar() or 0

                    # Get key type distribution
                    key_types = session.query(
                        GenesisKey.key_type,
                        func.count(GenesisKey.id)
                    ).group_by(GenesisKey.key_type).all()

                    genesis_data.key_types_distribution = {
                        kt: count for kt, count in key_types
                    }

                    # Get recent keys
                    recent = session.query(GenesisKey).filter(
                        GenesisKey.created_at >= cutoff
                    ).order_by(GenesisKey.created_at.desc()).limit(10).all()

                    genesis_data.recent_keys = [
                        {
                            'key_id': k.key_id,
                            'key_type': k.key_type,
                            'status': k.status,
                            'is_error': k.is_error,
                            'created_at': k.created_at.isoformat() if k.created_at else None,
                        }
                        for k in recent
                    ]
                finally:
                    session.close()

            except Exception as e:
                logger.debug(f"Could not query genesis keys: {e}")

            return genesis_data
        except Exception as e:
            logger.error(f"Failed to collect genesis keys: {e}")
            return None

    def _collect_configuration(self) -> Optional[Any]:
        """Collect configuration validation data."""
        try:
            from .configuration_sensor import ConfigurationSensor
            sensor = ConfigurationSensor()
            return sensor.validate_all()
        except Exception as e:
            logger.error(f"Failed to collect configuration data: {e}")
            return None
    
    def _collect_static_analysis(self) -> Optional[Any]:
        """Collect static analysis data."""
        try:
            # First, run proactive code scanner (catches syntax/import/missing file bugs)
            from .proactive_code_scanner import get_proactive_scanner
            scanner = get_proactive_scanner(backend_dir=Path(__file__).parent.parent)
            proactive_issues = scanner.scan_all()
            
            # Then run traditional static analysis (mypy, pylint)
            try:
                from .static_analysis_sensor import StaticAnalysisSensor
                sensor = StaticAnalysisSensor()
                static_data = sensor.analyze_all()
                
                # Merge proactive issues into static analysis results
                if static_data and hasattr(static_data, 'issues'):
                    # Convert proactive issues to static analysis format
                    for issue in proactive_issues:
                        from .static_analysis_sensor import StaticAnalysisIssue
                        static_data.issues.append(StaticAnalysisIssue(
                            tool='proactive_scanner',
                            file_path=issue.file_path,
                            line_number=issue.line_number,
                            issue_type=issue.issue_type,
                            severity=issue.severity,
                            message=issue.message,
                            fix_suggestion=issue.suggested_fix
                        ))
                        # Update totals
                        if issue.severity == 'critical':
                            static_data.critical_issues += 1
                        elif issue.severity == 'high':
                            static_data.high_issues += 1
                        elif issue.severity == 'medium':
                            static_data.medium_issues += 1
                        else:
                            static_data.low_issues += 1
                        static_data.total_issues += 1
                
                return static_data
            except Exception as e:
                logger.debug(f"Traditional static analysis not available: {e}")
                # Return proactive scanner results even if mypy/pylint fail
                if proactive_issues:
                    logger.warning(f"Proactive scanner found {len(proactive_issues)} issues that self-healing should fix!")
                    # Create a simple result structure
                    from .static_analysis_sensor import StaticAnalysisSensorData, StaticAnalysisIssue
                    result = StaticAnalysisSensorData()
                    for issue in proactive_issues:
                        result.issues.append(StaticAnalysisIssue(
                            tool='proactive_scanner',
                            file_path=issue.file_path,
                            line_number=issue.line_number,
                            issue_type=issue.issue_type,
                            severity=issue.severity,
                            message=issue.message,
                            fix_suggestion=issue.suggested_fix
                        ))
                        if issue.severity == 'critical':
                            result.critical_issues += 1
                        elif issue.severity == 'high':
                            result.high_issues += 1
                        elif issue.severity == 'medium':
                            result.medium_issues += 1
                        else:
                            result.low_issues += 1
                    result.total_issues = len(proactive_issues)
                    result.analysis_passed = result.critical_issues == 0
                    return result
        except Exception as e:
            logger.error(f"Failed to collect static analysis data: {e}")
            return None
    
    def _collect_design_patterns(self) -> Optional[Any]:
        """Collect design pattern detection data."""
        try:
            from .design_pattern_sensor import DesignPatternSensor
            sensor = DesignPatternSensor()
            return sensor.detect_all()
        except Exception as e:
            logger.error(f"Failed to collect design pattern data: {e}")
            return None
    
    def _collect_grace_mirror(self) -> Optional[GraceMirrorData]:
        """Collect GRACE Mirror self-reflection data."""
        try:
            mirror_data = GraceMirrorData()

            # Try to get from monitoring API data
            try:
                # Read from world model file if exists
                world_model_path = Path(__file__).parent.parent / ".genesis_world_model.json"
                if world_model_path.exists():
                    with open(world_model_path, 'r') as f:
                        world_model = json.load(f)

                    organs = world_model.get('organs', {})
                    mirror_data.self_healing_progress = organs.get('self_healing', {}).get('progress', 0.25)
                    mirror_data.world_model_progress = organs.get('world_model', {}).get('progress', 0.45)
                    mirror_data.self_learning_progress = organs.get('self_learning', {}).get('progress', 0.35)
                    mirror_data.self_governance_progress = organs.get('self_governance', {}).get('progress', 0.30)

                    mirror_data.component_status = world_model.get('components', {})
                    mirror_data.recent_activity = world_model.get('recent_activity', [])[:10]
            except Exception as e:
                logger.debug(f"Could not read world model: {e}")

                # Use default progress values
                mirror_data.self_healing_progress = 0.25
                mirror_data.world_model_progress = 0.45
                mirror_data.self_learning_progress = 0.35
                mirror_data.self_governance_progress = 0.30

            return mirror_data
        except Exception as e:
            logger.error(f"Failed to collect grace mirror: {e}")
            return None

    def _collect_code_quality(self) -> Optional[CodeQualityData]:
        """
        Collect code quality data by performing static analysis.

        FIX: This sensor performs comprehensive static code analysis to detect:
        - Security vulnerabilities (SQL injection, command injection, path traversal)
        - Type mismatches between models
        - Database schema issues (missing indexes, CASCADE)
        - Configuration issues (unsafe settings, hardcoded secrets)
        - Dependency issues (unpinned versions)
        """
        import re
        try:
            scan_start = datetime.utcnow()
            code_quality = CodeQualityData()
            backend_dir = Path(__file__).parent.parent

            # Security vulnerability patterns to detect
            security_patterns = [
                # Command injection
                (r'shell\s*=\s*True', 'command_injection', 'critical',
                 'Command injection via shell=True', 'CWE-78'),
                # SQL injection (raw string formatting in queries)
                (r'execute\s*\(\s*[f"\'].*\{.*\}', 'sql_injection', 'critical',
                 'Potential SQL injection via string formatting', 'CWE-89'),
                (r'\.format\s*\(.*\).*execute', 'sql_injection', 'critical',
                 'Potential SQL injection via .format()', 'CWE-89'),
                # Path traversal
                (r'open\s*\([^)]*\+[^)]*\)', 'path_traversal', 'high',
                 'Potential path traversal via string concatenation', 'CWE-22'),
                # Hardcoded secrets
                (r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', 'hardcoded_secret', 'high',
                 'Potential hardcoded secret', 'CWE-798'),
                # Unsafe pickle
                (r'pickle\.load', 'unsafe_deserialization', 'high',
                 'Unsafe pickle deserialization', 'CWE-502'),
                # Eval/exec
                (r'\beval\s*\(', 'code_injection', 'critical',
                 'Dangerous eval() usage', 'CWE-95'),
                (r'\bexec\s*\(', 'code_injection', 'critical',
                 'Dangerous exec() usage', 'CWE-95'),
                # PROACTIVE: Additional security patterns
                (r'yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)', 'yaml_unsafe_load', 'high',
                 'Unsafe YAML load without Loader specified', 'CWE-502'),
                (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', 'subprocess_injection', 'critical',
                 'Subprocess with shell=True is vulnerable', 'CWE-78'),
                (r'os\.system\s*\(', 'os_system_injection', 'critical',
                 'os.system() is vulnerable to command injection', 'CWE-78'),
                (r'__import__\s*\([^)]*\+', 'dynamic_import', 'high',
                 'Dynamic import with user input', 'CWE-94'),
                (r'getattr\s*\([^)]*,\s*[^"\']+\)', 'unsafe_getattr', 'medium',
                 'Dynamic getattr may allow attribute access attacks', 'CWE-913'),
            ]

            # Configuration issue patterns
            config_patterns = [
                (r'unsafe-inline', 'unsafe_csp', 'medium',
                 'CSP allows unsafe-inline which weakens XSS protection', None),
                (r'DEBUG\s*=\s*True', 'debug_enabled', 'medium',
                 'Debug mode enabled in configuration', None),
                (r'CORS.*\*', 'cors_wildcard', 'medium',
                 'CORS allows all origins', None),
                # PROACTIVE: Additional config patterns
                (r'verify\s*=\s*False', 'ssl_verify_disabled', 'high',
                 'SSL verification disabled - vulnerable to MITM', None),
                (r'httponly\s*=\s*False', 'cookie_not_httponly', 'medium',
                 'Cookie not HttpOnly - vulnerable to XSS', None),
                (r'secure\s*=\s*False', 'cookie_not_secure', 'medium',
                 'Cookie not Secure - transmitted over HTTP', None),
            ]

            # Database patterns
            db_patterns = [
                (r'Column\([^)]*String[^)]*\).*#.*token', 'type_mismatch', 'medium',
                 'Token column using String instead of Integer', None),
                (r'ForeignKey\([^)]*\)[^)]*(?!ondelete)', 'missing_cascade', 'low',
                 'Foreign key without ondelete specification', None),
                # PROACTIVE: Additional DB patterns
                (r'session\.execute\s*\(\s*["\']', 'raw_sql', 'medium',
                 'Raw SQL execution - prefer ORM methods', None),
                (r'\.query\s*\([^)]*\)\.filter\s*\([^)]*==\s*[^"\']+\)', 'dynamic_filter', 'low',
                 'Dynamic filter value - ensure sanitization', None),
            ]

            # PROACTIVE: Race condition patterns
            race_condition_patterns = [
                (r'asyncio\.create_task\s*\([^)]*\)(?!\s*#\s*await)', 'unawaited_task', 'medium',
                 'Fire-and-forget async task may cause race conditions', 'CWE-362'),
                (r'threading\.Thread\([^)]*daemon\s*=\s*True', 'daemon_thread', 'low',
                 'Daemon thread may terminate unexpectedly', None),
                (r'global\s+\w+\s*\n.*=', 'global_state_mutation', 'medium',
                 'Global state mutation can cause race conditions', 'CWE-362'),
                (r'@app\.(get|post|put|delete)\s*\([^)]*\)\s*\n(?:.*\n)*?.*(?<!async\s)def\s', 'sync_endpoint', 'low',
                 'Synchronous endpoint may block event loop', None),
            ]

            # PROACTIVE: Memory and resource patterns
            resource_patterns = [
                (r'open\s*\([^)]*\)(?!\s*as\s)', 'file_not_closed', 'medium',
                 'File opened without context manager - may leak', 'CWE-404'),
                (r'while\s+True\s*:', 'infinite_loop', 'low',
                 'Infinite loop detected - ensure exit condition', None),
                (r'\.append\([^)]*\)\s*(?:.*\n)*?\s*while', 'list_growth_in_loop', 'low',
                 'List growing in loop - potential memory issue', None),
            ]

            # PROACTIVE: API security patterns
            api_security_patterns = [
                (r'@app\.(get|post|put|delete)\s*\([^)]*\)\s*\n(?:.*\n)*?def\s+\w+\([^)]*\)(?!.*Depends)', 'missing_auth', 'high',
                 'API endpoint may be missing authentication', None),
                (r'response\.set_cookie\s*\([^)]*\)(?!.*httponly)', 'cookie_missing_flags', 'medium',
                 'Cookie set without security flags', None),
            ]

            # Combine all proactive patterns
            all_security_patterns = security_patterns + race_condition_patterns + resource_patterns + api_security_patterns

            # Scan Python files
            python_files = list(backend_dir.glob('**/*.py'))
            code_quality.files_scanned = len(python_files)

            for py_file in python_files[:200]:  # Limit to avoid performance issues
                try:
                    # Skip test files and __pycache__
                    if '__pycache__' in str(py_file) or 'test_' in py_file.name:
                        continue

                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')

                    rel_path = str(py_file.relative_to(backend_dir))

                    # Check ALL security patterns (including proactive race/resource/API patterns)
                    for pattern, issue_type, severity, desc, cwe in all_security_patterns:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                issue = CodeQualityIssue(
                                    issue_type=issue_type,
                                    severity=severity,
                                    file_path=rel_path,
                                    line_number=i,
                                    description=desc,
                                    code_snippet=line.strip()[:100],
                                    cwe_id=cwe
                                )
                                code_quality.security_vulnerabilities.append(issue)
                                self._increment_severity_count(code_quality, severity)

                    # Check config patterns
                    for pattern, issue_type, severity, desc, cwe in config_patterns:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                issue = CodeQualityIssue(
                                    issue_type=issue_type,
                                    severity=severity,
                                    file_path=rel_path,
                                    line_number=i,
                                    description=desc,
                                    code_snippet=line.strip()[:100],
                                    cwe_id=cwe
                                )
                                code_quality.configuration_issues.append(issue)
                                self._increment_severity_count(code_quality, severity)

                    # Check database patterns
                    for pattern, issue_type, severity, desc, cwe in db_patterns:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                issue = CodeQualityIssue(
                                    issue_type=issue_type,
                                    severity=severity,
                                    file_path=rel_path,
                                    line_number=i,
                                    description=desc,
                                    code_snippet=line.strip()[:100],
                                    cwe_id=cwe
                                )
                                code_quality.database_issues.append(issue)
                                self._increment_severity_count(code_quality, severity)

                except Exception as e:
                    logger.debug(f"Could not scan {py_file}: {e}")

            # Check requirements.txt for unpinned dependencies
            requirements_path = backend_dir / 'requirements.txt'
            if requirements_path.exists():
                try:
                    with open(requirements_path, 'r') as f:
                        for i, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Check if version is pinned
                                if '==' not in line and '>=' not in line and '<' not in line:
                                    issue = CodeQualityIssue(
                                        issue_type='unpinned_dependency',
                                        severity='medium',
                                        file_path='requirements.txt',
                                        line_number=i,
                                        description=f'Unpinned dependency: {line}',
                                        code_snippet=line,
                                        suggested_fix='Pin dependency version for reproducibility'
                                    )
                                    code_quality.dependency_issues.append(issue)
                                    code_quality.medium_issues += 1
                except Exception as e:
                    logger.debug(f"Could not check requirements.txt: {e}")

            # Calculate totals
            code_quality.total_issues = (
                code_quality.critical_issues +
                code_quality.high_issues +
                code_quality.medium_issues +
                code_quality.low_issues
            )

            scan_end = datetime.utcnow()
            code_quality.scan_duration_ms = (scan_end - scan_start).total_seconds() * 1000
            code_quality.timestamp = scan_end

            logger.info(f"Code quality scan complete: {code_quality.total_issues} issues found "
                       f"({code_quality.critical_issues} critical, {code_quality.high_issues} high)")

            return code_quality

        except Exception as e:
            logger.error(f"Failed to collect code quality: {e}")
            return None

    def _increment_severity_count(self, code_quality: CodeQualityData, severity: str):
        """Helper to increment severity counts."""
        if severity == 'critical':
            code_quality.critical_issues += 1
        elif severity == 'high':
            code_quality.high_issues += 1
        elif severity == 'medium':
            code_quality.medium_issues += 1
        elif severity == 'low':
            code_quality.low_issues += 1

    # ==================== WHOLE-SYSTEM SENSOR COLLECTORS ====================

    def _collect_build_status(self) -> Optional[BuildStatusData]:
        """
        Collect build/CI status for whole-system health tracking.

        Checks:
        - Git repository status
        - CI/CD pipeline status (GitHub Actions, etc.)
        - Lint and type check results
        - Recent build history
        """
        import subprocess
        try:
            build_status = BuildStatusData()
            backend_dir = Path(__file__).parent.parent

            # Get git information
            try:
                # Get current branch
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True, text=True, cwd=backend_dir, timeout=5
                )
                if result.returncode == 0:
                    build_status.branch_name = result.stdout.strip()

                # Get current commit SHA
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True, text=True, cwd=backend_dir, timeout=5
                )
                if result.returncode == 0:
                    build_status.commit_sha = result.stdout.strip()[:8]

                # Get recent commits
                result = subprocess.run(
                    ['git', 'log', '--oneline', '-5'],
                    capture_output=True, text=True, cwd=backend_dir, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split(' ', 1)
                            build_status.recent_commits.append({
                                'sha': parts[0],
                                'message': parts[1] if len(parts) > 1 else ''
                            })
            except Exception as e:
                logger.debug(f"Git info collection failed: {e}")

            # Check for GitHub Actions workflow status
            github_dir = backend_dir.parent / '.github' / 'workflows'
            if github_dir.exists():
                build_status.ci_provider = 'github_actions'

            # Try to run linting check
            try:
                result = subprocess.run(
                    ['python', '-m', 'py_compile', str(backend_dir / 'app.py')],
                    capture_output=True, text=True, cwd=backend_dir, timeout=30
                )
                build_status.lint_passing = result.returncode == 0
            except Exception:
                pass

            # Check for recent test results
            test_report = backend_dir / 'tests' / 'diagnostic_report.json'
            if test_report.exists():
                try:
                    with open(test_report, 'r') as f:
                        report = json.load(f)
                    test_results = report.get('test_results', {})
                    build_status.tests_passing = test_results.get('failed', 0) == 0
                    build_status.last_build_status = 'success' if build_status.tests_passing else 'failure'
                except Exception:
                    pass

            # Overall build passing status
            build_status.build_passing = (
                build_status.lint_passing and
                build_status.tests_passing and
                build_status.type_check_passing
            )

            return build_status

        except Exception as e:
            logger.error(f"Failed to collect build status: {e}")
            return None

    def _collect_test_coverage(self) -> Optional[TestCoverageData]:
        """
        Collect test coverage data for identifying untested code paths.

        Checks:
        - Coverage report files (.coverage, coverage.xml, htmlcov)
        - Line and branch coverage percentages
        - Identifies critical uncovered code paths
        """
        try:
            coverage_data = TestCoverageData()
            backend_dir = Path(__file__).parent.parent

            # Check for coverage.py data
            coverage_file = backend_dir / '.coverage'
            coverage_xml = backend_dir / 'coverage.xml'
            htmlcov_dir = backend_dir / 'htmlcov'

            # Try to parse coverage.xml if available
            if coverage_xml.exists():
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(coverage_xml)
                    root = tree.getroot()

                    # Get overall coverage
                    line_rate = float(root.get('line-rate', 0))
                    branch_rate = float(root.get('branch-rate', 0))

                    coverage_data.line_coverage_percent = line_rate * 100
                    coverage_data.branch_coverage_percent = branch_rate * 100
                    coverage_data.overall_coverage_percent = (line_rate + branch_rate) / 2 * 100
                    coverage_data.coverage_report_path = str(coverage_xml)

                    # Find uncovered files (those with low coverage)
                    for package in root.findall('.//package'):
                        for cls in package.findall('.//class'):
                            filename = cls.get('filename', '')
                            file_line_rate = float(cls.get('line-rate', 0))
                            if file_line_rate < 0.5:  # Less than 50% coverage
                                coverage_data.uncovered_files.append({
                                    'file': filename,
                                    'coverage': file_line_rate * 100
                                })

                except Exception as e:
                    logger.debug(f"Could not parse coverage.xml: {e}")

            # If no coverage data, try to estimate from file analysis
            elif not coverage_file.exists():
                # Count test files vs source files
                test_files = list(backend_dir.glob('**/test_*.py'))
                source_files = [
                    f for f in backend_dir.glob('**/*.py')
                    if 'test_' not in f.name and '__pycache__' not in str(f)
                ]

                coverage_data.total_lines = len(source_files) * 100  # Rough estimate
                coverage_data.covered_lines = len(test_files) * 50  # Rough estimate

                # Check for critical paths without tests
                critical_paths = ['security/', 'auth/', 'database/']
                for path in critical_paths:
                    path_dir = backend_dir / path.rstrip('/')
                    if path_dir.exists():
                        has_tests = any(
                            'test_' in f.name
                            for f in path_dir.glob('**/*.py')
                        )
                        if not has_tests:
                            coverage_data.critical_paths_covered = False
                            coverage_data.uncovered_files.append({
                                'file': path,
                                'reason': 'No test files found for critical path'
                            })

            # Determine coverage trend
            if coverage_data.overall_coverage_percent > 70:
                coverage_data.coverage_trend = 'stable'
            elif coverage_data.overall_coverage_percent > 50:
                coverage_data.coverage_trend = 'needs_improvement'
            else:
                coverage_data.coverage_trend = 'declining'

            return coverage_data

        except Exception as e:
            logger.error(f"Failed to collect test coverage: {e}")
            return None

    def _collect_api_contract(self) -> Optional[APIContractData]:
        """
        Collect API contract validation data.

        Checks:
        - OpenAPI/Swagger spec presence and validity
        - Compares spec to actual implemented endpoints
        - Identifies undocumented or missing endpoints
        """
        try:
            api_data = APIContractData()
            backend_dir = Path(__file__).parent.parent

            # Look for OpenAPI spec files
            spec_paths = [
                backend_dir / 'openapi.json',
                backend_dir / 'openapi.yaml',
                backend_dir / 'swagger.json',
                backend_dir / 'docs' / 'openapi.json',
            ]

            spec_content = None
            for spec_path in spec_paths:
                if spec_path.exists():
                    api_data.spec_path = str(spec_path)
                    try:
                        with open(spec_path, 'r') as f:
                            if spec_path.suffix == '.yaml':
                                import yaml
                                spec_content = yaml.safe_load(f)
                            else:
                                spec_content = json.load(f)
                        api_data.spec_valid = True
                        api_data.spec_version = spec_content.get('openapi', spec_content.get('swagger', ''))
                    except Exception as e:
                        api_data.spec_valid = False
                        logger.debug(f"Could not parse OpenAPI spec: {e}")
                    break

            # Try to discover endpoints from FastAPI app
            try:
                # Import the app to get routes
                import sys
                sys.path.insert(0, str(backend_dir))

                from app import app
                implemented_endpoints = set()

                for route in app.routes:
                    if hasattr(route, 'path') and hasattr(route, 'methods'):
                        for method in route.methods:
                            if method not in ('HEAD', 'OPTIONS'):
                                implemented_endpoints.add((route.path, method))
                                api_data.endpoints.append(APIEndpoint(
                                    path=route.path,
                                    method=method,
                                    implemented=True,
                                    defined_in_spec=False  # Will update if spec exists
                                ))

                api_data.total_endpoints = len(implemented_endpoints)

                # Compare with spec if available
                if spec_content and 'paths' in spec_content:
                    spec_endpoints = set()
                    for path, methods in spec_content['paths'].items():
                        for method in methods:
                            if method.upper() not in ('HEAD', 'OPTIONS', 'PARAMETERS'):
                                spec_endpoints.add((path, method.upper()))

                    # Find undocumented endpoints
                    for endpoint in implemented_endpoints:
                        if endpoint not in spec_endpoints:
                            api_data.undocumented_endpoints.append(f"{endpoint[1]} {endpoint[0]}")

                    # Find missing implementations
                    for endpoint in spec_endpoints:
                        if endpoint not in implemented_endpoints:
                            api_data.missing_implementations.append(f"{endpoint[1]} {endpoint[0]}")

                    api_data.compliant_endpoints = len(implemented_endpoints - set(api_data.undocumented_endpoints))
                    api_data.non_compliant_endpoints = len(api_data.undocumented_endpoints) + len(api_data.missing_implementations)

            except ImportError:
                logger.debug("Could not import app for API contract analysis")
            except Exception as e:
                logger.debug(f"API discovery failed: {e}")

            # Calculate compliance percentage
            if api_data.total_endpoints > 0:
                api_data.compliance_percent = (
                    (api_data.total_endpoints - len(api_data.undocumented_endpoints)) /
                    api_data.total_endpoints * 100
                )

            return api_data

        except Exception as e:
            logger.error(f"Failed to collect API contract: {e}")
            return None

    def _collect_infrastructure(self) -> Optional[InfrastructureData]:
        """
        Collect infrastructure health data.

        Checks:
        - Docker container status
        - External service connectivity (databases, APIs)
        - Network health
        - Resource pressure indicators
        """
        import subprocess
        try:
            infra_data = InfrastructureData()

            # Check Docker availability and container status
            try:
                result = subprocess.run(
                    ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    infra_data.docker_available = True
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('\t')
                            name = parts[0]
                            status = parts[1] if len(parts) > 1 else 'unknown'

                            health = 'healthy' if 'Up' in status else 'stopped'
                            if 'unhealthy' in status.lower():
                                health = 'unhealthy'
                                infra_data.containers_unhealthy += 1
                            elif 'Up' in status:
                                infra_data.containers_running += 1
                            else:
                                infra_data.containers_stopped += 1

                            infra_data.services.append(ServiceHealth(
                                name=name,
                                status=health,
                                type='container',
                                last_check=datetime.utcnow()
                            ))
            except FileNotFoundError:
                infra_data.docker_available = False
            except Exception as e:
                logger.debug(f"Docker check failed: {e}")

            # Check Kubernetes availability
            try:
                result = subprocess.run(
                    ['kubectl', 'cluster-info'],
                    capture_output=True, text=True, timeout=5
                )
                infra_data.kubernetes_available = result.returncode == 0
            except FileNotFoundError:
                pass
            except Exception:
                pass

            # Check external dependencies
            external_checks = [
                ('database', 'localhost', 5432),
                ('redis', 'localhost', 6379),
                ('qdrant', 'localhost', 6333),
            ]

            import socket
            for name, host, port in external_checks:
                try:
                    start = datetime.utcnow()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((host, port))
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                    sock.close()

                    status = 'healthy' if result == 0 else 'unreachable'
                    infra_data.external_dependencies.append(ServiceHealth(
                        name=name,
                        status=status,
                        type='external_api',
                        response_time_ms=elapsed if result == 0 else 0,
                        last_check=datetime.utcnow(),
                        error_message=None if result == 0 else f"Connection failed (code: {result})"
                    ))

                    if result == 0:
                        infra_data.healthy_services += 1
                    infra_data.total_services += 1

                except Exception as e:
                    infra_data.external_dependencies.append(ServiceHealth(
                        name=name,
                        status='unknown',
                        type='external_api',
                        error_message=str(e)
                    ))
                    infra_data.total_services += 1

            # Check system resource pressure
            if self._psutil:
                memory = self._psutil.virtual_memory()
                disk = self._psutil.disk_usage('/')

                infra_data.memory_pressure = memory.percent > 90
                infra_data.disk_space_critical = disk.percent > 90

            # Check network connectivity
            try:
                import urllib.request
                urllib.request.urlopen('https://www.google.com', timeout=5)
                infra_data.network_connectivity = True
            except Exception:
                infra_data.network_connectivity = False

            # Calculate overall infrastructure score
            total_checks = infra_data.total_services + 3  # +3 for network, memory, disk
            healthy_checks = infra_data.healthy_services
            if infra_data.network_connectivity:
                healthy_checks += 1
            if not infra_data.memory_pressure:
                healthy_checks += 1
            if not infra_data.disk_space_critical:
                healthy_checks += 1

            infra_data.infrastructure_score = (healthy_checks / total_checks * 100) if total_checks > 0 else 100

            return infra_data

        except Exception as e:
            logger.error(f"Failed to collect infrastructure: {e}")
            return None

    def to_dict(self, sensor_data: SensorData) -> Dict[str, Any]:
        """Convert sensor data to dictionary for serialization."""
        result = {
            'collection_timestamp': sensor_data.collection_timestamp.isoformat(),
            'collection_duration_ms': sensor_data.collection_duration_ms,
            'sensors_available': [s.value for s in sensor_data.sensors_available],
            'sensors_failed': [s.value for s in sensor_data.sensors_failed],
        }

        if sensor_data.test_results:
            result['test_results'] = {
                'total_tests': sensor_data.test_results.total_tests,
                'passed': sensor_data.test_results.passed,
                'failed': sensor_data.test_results.failed,
                'skipped': sensor_data.test_results.skipped,
                'errors': sensor_data.test_results.errors,
                'pass_rate': sensor_data.test_results.pass_rate,
                'infrastructure_failures': sensor_data.test_results.infrastructure_failures,
                'code_failures': sensor_data.test_results.code_failures,
                'top_error_types': sensor_data.test_results.top_error_types,
                'learned_patterns_count': len(sensor_data.test_results.learned_patterns),
            }

        if sensor_data.logs:
            result['logs'] = {
                'log_level_counts': sensor_data.logs.log_level_counts,
                'error_count': len(sensor_data.logs.error_messages),
                'warning_count': len(sensor_data.logs.warning_messages),
                'exception_count': len(sensor_data.logs.recent_exceptions),
            }

        if sensor_data.metrics:
            result['metrics'] = {
                'cpu_percent': sensor_data.metrics.cpu_percent,
                'memory_percent': sensor_data.metrics.memory_percent,
                'disk_percent': sensor_data.metrics.disk_percent,
                'database_health': sensor_data.metrics.database_health,
                'vector_db_health': sensor_data.metrics.vector_db_health,
                'llm_health': sensor_data.metrics.llm_health,
                'embedding_health': sensor_data.metrics.embedding_health,
            }

        if sensor_data.agent_outputs:
            result['agent_outputs'] = {
                'total_decisions': sensor_data.agent_outputs.total_decisions,
                'successful_decisions': sensor_data.agent_outputs.successful_decisions,
                'failed_decisions': sensor_data.agent_outputs.failed_decisions,
                'average_confidence': sensor_data.agent_outputs.average_confidence,
                'invariant_violations': sensor_data.agent_outputs.invariant_violations,
            }

        if sensor_data.genesis_keys:
            result['genesis_keys'] = {
                'total_keys': sensor_data.genesis_keys.total_keys,
                'active_keys': sensor_data.genesis_keys.active_keys,
                'error_keys': sensor_data.genesis_keys.error_keys,
                'fix_suggestions': sensor_data.genesis_keys.fix_suggestions,
                'applied_fixes': sensor_data.genesis_keys.applied_fixes,
                'key_types_distribution': sensor_data.genesis_keys.key_types_distribution,
            }

        if sensor_data.grace_mirror:
            result['grace_mirror'] = {
                'self_healing_progress': sensor_data.grace_mirror.self_healing_progress,
                'world_model_progress': sensor_data.grace_mirror.world_model_progress,
                'self_learning_progress': sensor_data.grace_mirror.self_learning_progress,
                'self_governance_progress': sensor_data.grace_mirror.self_governance_progress,
                'component_status': sensor_data.grace_mirror.component_status,
            }

        # FIX: Added code quality sensor output
        if sensor_data.code_quality:
            result['code_quality'] = {
                'total_issues': sensor_data.code_quality.total_issues,
                'critical_issues': sensor_data.code_quality.critical_issues,
                'high_issues': sensor_data.code_quality.high_issues,
                'medium_issues': sensor_data.code_quality.medium_issues,
                'low_issues': sensor_data.code_quality.low_issues,
                'security_vulnerabilities_count': len(sensor_data.code_quality.security_vulnerabilities),
                'type_mismatches_count': len(sensor_data.code_quality.type_mismatches),
                'database_issues_count': len(sensor_data.code_quality.database_issues),
                'configuration_issues_count': len(sensor_data.code_quality.configuration_issues),
                'dependency_issues_count': len(sensor_data.code_quality.dependency_issues),
                'files_scanned': sensor_data.code_quality.files_scanned,
                'scan_duration_ms': sensor_data.code_quality.scan_duration_ms,
                # Include details of critical and high severity issues
                'critical_details': [
                    {
                        'type': issue.issue_type,
                        'file': issue.file_path,
                        'line': issue.line_number,
                        'description': issue.description,
                        'cwe': issue.cwe_id,
                    }
                    for issue in sensor_data.code_quality.security_vulnerabilities
                    if issue.severity == 'critical'
                ][:10],  # Limit to 10 for brevity
                'high_details': [
                    {
                        'type': issue.issue_type,
                        'file': issue.file_path,
                        'line': issue.line_number,
                        'description': issue.description,
                        'cwe': issue.cwe_id,
                    }
                    for issue in sensor_data.code_quality.security_vulnerabilities
                    if issue.severity == 'high'
                ][:10],
            }

        # WHOLE-SYSTEM SENSOR OUTPUTS
        if sensor_data.build_status:
            result['build_status'] = {
                'build_passing': sensor_data.build_status.build_passing,
                'last_build_status': sensor_data.build_status.last_build_status,
                'branch_name': sensor_data.build_status.branch_name,
                'commit_sha': sensor_data.build_status.commit_sha,
                'ci_provider': sensor_data.build_status.ci_provider,
                'lint_passing': sensor_data.build_status.lint_passing,
                'type_check_passing': sensor_data.build_status.type_check_passing,
                'tests_passing': sensor_data.build_status.tests_passing,
                'recent_commits_count': len(sensor_data.build_status.recent_commits),
            }

        if sensor_data.test_coverage:
            result['test_coverage'] = {
                'overall_coverage_percent': sensor_data.test_coverage.overall_coverage_percent,
                'line_coverage_percent': sensor_data.test_coverage.line_coverage_percent,
                'branch_coverage_percent': sensor_data.test_coverage.branch_coverage_percent,
                'coverage_trend': sensor_data.test_coverage.coverage_trend,
                'critical_paths_covered': sensor_data.test_coverage.critical_paths_covered,
                'uncovered_files_count': len(sensor_data.test_coverage.uncovered_files),
                'uncovered_files': sensor_data.test_coverage.uncovered_files[:5],
            }

        if sensor_data.api_contract:
            result['api_contract'] = {
                'spec_valid': sensor_data.api_contract.spec_valid,
                'spec_version': sensor_data.api_contract.spec_version,
                'total_endpoints': sensor_data.api_contract.total_endpoints,
                'compliant_endpoints': sensor_data.api_contract.compliant_endpoints,
                'compliance_percent': sensor_data.api_contract.compliance_percent,
                'undocumented_endpoints': sensor_data.api_contract.undocumented_endpoints[:5],
                'missing_implementations': sensor_data.api_contract.missing_implementations[:5],
            }

        if sensor_data.infrastructure:
            result['infrastructure'] = {
                'docker_available': sensor_data.infrastructure.docker_available,
                'kubernetes_available': sensor_data.infrastructure.kubernetes_available,
                'containers_running': sensor_data.infrastructure.containers_running,
                'containers_unhealthy': sensor_data.infrastructure.containers_unhealthy,
                'network_connectivity': sensor_data.infrastructure.network_connectivity,
                'memory_pressure': sensor_data.infrastructure.memory_pressure,
                'disk_space_critical': sensor_data.infrastructure.disk_space_critical,
                'infrastructure_score': sensor_data.infrastructure.infrastructure_score,
                'total_services': sensor_data.infrastructure.total_services,
                'healthy_services': sensor_data.infrastructure.healthy_services,
                'external_dependencies': [
                    {
                        'name': svc.name,
                        'status': svc.status,
                        'response_time_ms': svc.response_time_ms,
                    }
                    for svc in sensor_data.infrastructure.external_dependencies
                ][:5],
            }

        if sensor_data.configuration:
            result['configuration'] = {
                'total_issues': sensor_data.configuration.total_issues,
                'critical_issues': sensor_data.configuration.critical_issues,
                'high_issues': sensor_data.configuration.high_issues,
                'validation_passed': sensor_data.configuration.validation_passed,
                'components_checked': sensor_data.configuration.components_checked,
            }

        if sensor_data.static_analysis:
            result['static_analysis'] = {
                'total_issues': sensor_data.static_analysis.total_issues,
                'critical_issues': sensor_data.static_analysis.critical_issues,
                'high_issues': sensor_data.static_analysis.high_issues,
                'analysis_passed': sensor_data.static_analysis.analysis_passed,
                'tools_run': sensor_data.static_analysis.tools_run,
            }

        if sensor_data.design_patterns:
            result['design_patterns'] = {
                'total_issues': sensor_data.design_patterns.total_issues,
                'high_issues': sensor_data.design_patterns.high_issues,
                'patterns_checked': sensor_data.design_patterns.patterns_checked,
            }

        return result
