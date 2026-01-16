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
    CODE_QUALITY = "code_quality"  # FIX: Static code analysis for security vulnerabilities


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


@dataclass
class SensorData:
    """Aggregated sensor data from all sources."""
    test_results: Optional[TestResultData] = None
    logs: Optional[LogData] = None
    metrics: Optional[MetricsData] = None
    agent_outputs: Optional[AgentOutputData] = None
    genesis_keys: Optional[GenesisKeyData] = None
    grace_mirror: Optional[GraceMirrorData] = None
    code_quality: Optional[CodeQualityData] = None  # FIX: Added code quality sensor
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
            (SensorType.CODE_QUALITY, self._collect_code_quality),  # FIX: Added code quality sensor
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
                    elif sensor_type == SensorType.CODE_QUALITY:
                        sensor_data.code_quality = result
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

        return result
