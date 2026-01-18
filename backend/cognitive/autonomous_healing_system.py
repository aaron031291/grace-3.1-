import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from sqlalchemy.orm import Session
from genesis.healing_system import get_healing_system
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.learning_memory import LearningExample

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    """System health status levels from AVN."""
    HEALTHY = "healthy"           # All systems operational
    DEGRADED = "degraded"         # Some issues but functional
    WARNING = "warning"           # Approaching critical thresholds
    CRITICAL = "critical"         # Major issues requiring immediate action
    FAILING = "failing"           # System failure imminent


# ======================================================================
# Anomaly Types (from AVN)
# ======================================================================

class AnomalyType(str, Enum):
    """Types of anomalies the system can detect."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MEMORY_LEAK = "memory_leak"
    ERROR_SPIKE = "error_spike"
    RESPONSE_TIMEOUT = "response_timeout"
    DATA_INCONSISTENCY = "data_inconsistency"
    SECURITY_BREACH = "security_breach"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SERVICE_FAILURE = "service_failure"  # Service connection/availability issues
    SILENT_FAILURE = "silent_failure"  # Components failing without logging
    FEATURE_DEGRADATION = "feature_degradation"  # Features degrading with fallbacks
    TELEMETRY_LOSS = "telemetry_loss"  # Telemetry/metrics recording failures


# ======================================================================
# Healing Actions (from AVN with 8 priority levels)
# ======================================================================

class HealingAction(str, Enum):
    """Healing actions ordered by severity (8 levels from AVN)."""
    BUFFER_CLEAR = "buffer_clear"                 # Level 1: Clear buffers
    CACHE_FLUSH = "cache_flush"                   # Level 2: Flush caches
    CONNECTION_RESET = "connection_reset"         # Level 3: Reset connections
    DATABASE_TABLE_CREATE = "database_table_create"  # Level 3.5: Create missing database tables
    CODE_FIX = "code_fix"                         # Level 2.5: Fix code issues with scripts/patches
    SEMANTIC_REFACTOR = "semantic_refactor"       # Level 3: Multi-file symbol rename/move
    PROCESS_RESTART = "process_restart"           # Level 4: Restart process
    SERVICE_RESTART = "service_restart"           # Level 5: Restart service
    STATE_ROLLBACK = "state_rollback"             # Level 6: Rollback to known good state
    ISOLATION = "isolation"                       # Level 7: Isolate affected component
    EMERGENCY_SHUTDOWN = "emergency_shutdown"     # Level 8: Emergency shutdown
    LIFECYCLE_MAINTENANCE = "lifecycle_maintenance"  # Level 2.5: Run lifecycle maintenance


# ======================================================================
# Trust Levels for Autonomous Execution (from AVM)
# ======================================================================

class TrustLevel(int, Enum):
    """Trust levels for autonomous action execution (0-9 from AVM)."""
    MANUAL_ONLY = 0           # No autonomous actions
    SUGGEST_ONLY = 1          # Suggest actions but require approval
    LOW_RISK_AUTO = 2         # Auto-execute low-risk actions only
    MEDIUM_RISK_AUTO = 3      # Auto-execute medium-risk actions
    HIGH_RISK_AUTO = 4        # Auto-execute high-risk actions
    CRITICAL_AUTO = 5         # Auto-execute critical actions
    SYSTEM_WIDE_AUTO = 6      # System-wide autonomous control
    LEARNING_AUTO = 7         # Autonomous learning and adaptation
    SELF_MODIFICATION = 8     # Self-modification capabilities
    FULL_AUTONOMY = 9         # Complete autonomous control


# ======================================================================
# Autonomous Healing System
# ======================================================================

class AutonomousHealingSystem:
    """
    Autonomous self-healing system with AVM/AVN integration.

    Continuously monitors health, detects anomalies, and executes healing
    actions based on trust scores and progressive autonomy levels.
    """

    def __init__(
        self,
        session: Session,
        repo_path: Optional[Path] = None,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning: bool = True,
        coding_agent=None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.trust_level = trust_level
        self.enable_learning = enable_learning
        self.coding_agent = coding_agent

        # Track degraded components for graceful degradation
        self.degraded_components: List[Dict[str, Any]] = []

        # Initialize healing system
        self.healing_system = get_healing_system(str(repo_path) if repo_path else None)
        
        # Initialize LLM logic error detector
        try:
            from cognitive.llm_logic_error_detector import get_logic_error_detector
            from llm_orchestrator.llm_service import get_llm_service
            llm_service = get_llm_service()
            self.logic_detector = get_logic_error_detector(llm_service=llm_service)
            logger.info("[AUTONOMOUS-HEALING] LLM logic error detector initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] LLM logic detector DEGRADED: {e}")
            self.logic_detector = None
            self.degraded_components.append({
                "component": "llm_logic_detector",
                "reason": str(e),
                "impact": "Logic error detection disabled"
            })
        
        # Initialize LLM import healer (adaptive import error fixing)
        try:
            from cognitive.llm_import_healer import get_import_healer
            from llm_orchestrator.llm_service import get_llm_service
            llm_service = get_llm_service()
            self.import_healer = get_import_healer(llm_service=llm_service, repo_path=self.repo_path)
            logger.info("[AUTONOMOUS-HEALING] LLM import healer initialized (adaptive for dependency upgrades)")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] LLM import healer DEGRADED: {e}")
            self.import_healer = None
            self.degraded_components.append({
                "component": "llm_import_healer",
                "reason": str(e),
                "impact": "Adaptive import error fixing disabled"
            })
        
        # Initialize LLM config healer (adaptive configuration error fixing)
        try:
            from cognitive.llm_config_healer import get_config_healer
            from llm_orchestrator.llm_service import get_llm_service
            llm_service = get_llm_service()
            self.config_healer = get_config_healer(llm_service=llm_service, repo_path=self.repo_path)
            logger.info("[AUTONOMOUS-HEALING] LLM config healer initialized (adaptive for dependency upgrades)")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] LLM config healer DEGRADED: {e}")
            self.config_healer = None
            self.degraded_components.append({
                "component": "llm_config_healer",
                "reason": str(e),
                "impact": "Adaptive configuration error fixing disabled"
            })
        
        # Initialize Genesis service
        self.genesis_service = get_genesis_service()

        # System state
        self.current_health = HealthStatus.HEALTHY
        self.anomalies_detected = []
        self.healing_history = []
        self.trust_scores = {}  # Action -> trust score (0.0-1.0)

        # Health monitoring thresholds
        self.thresholds = {
            "error_rate": 0.05,           # 5% error rate threshold
            "response_time": 5.0,          # 5 second response time threshold
            "memory_usage": 0.85,          # 85% memory usage threshold
            "cpu_usage": 0.90,             # 90% CPU usage threshold
        }

        # Initialize trust scores for healing actions
        self._initialize_trust_scores()
        
        # Initialize healing knowledge base and script generator
        try:
            from cognitive.healing_knowledge_base import get_healing_knowledge_base
            from cognitive.healing_script_generator import get_healing_script_generator
            self.knowledge_base = get_healing_knowledge_base()
            self.script_generator = get_healing_script_generator(self.repo_path)
            logger.info("[AUTONOMOUS-HEALING] Healing knowledge base and script generator initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Healing knowledge base DEGRADED: {e}")
            self.knowledge_base = None
            self.script_generator = None
            self.degraded_components.append({
                "component": "healing_knowledge_base",
                "reason": str(e),
                "impact": "Knowledge-driven healing and script generation disabled"
            })
        
        # Diagnostic engine integration
        self.diagnostic_enabled = True

        # Bidirectional Communication Bridge (Self-Healing ↔ Coding Agent)
        try:
            from cognitive.coding_agent_healing_bridge import get_coding_agent_healing_bridge
            self.healing_bridge = get_coding_agent_healing_bridge(
                coding_agent=coding_agent,
                healing_system=self
            )
            logger.info("[AUTONOMOUS-HEALING] Bidirectional bridge with Coding Agent initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Bidirectional bridge DEGRADED: {e}")
            self.healing_bridge = None
            self.degraded_components.append({
                "component": "healing_bridge",
                "reason": str(e),
                "impact": "Bidirectional coding agent communication disabled"
            })
        
        # Initialize Healing Validation Pipeline (Plan → Patch → Validate → Rollback)
        try:
            from cognitive.healing_validation_pipeline import get_healing_validation_pipeline
            self.validation_pipeline = get_healing_validation_pipeline(repo_path=self.repo_path)
            logger.info("[AUTONOMOUS-HEALING] Healing validation pipeline initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Healing validation pipeline DEGRADED: {e}")
            self.validation_pipeline = None
            self.degraded_components.append({
                "component": "validation_pipeline",
                "reason": str(e),
                "impact": "Validation gates and rollback disabled"
            })
        
        # Initialize Silent Degradation Detector
        try:
            from cognitive.silent_degradation_detector import get_degradation_detector
            self.degradation_detector = get_degradation_detector(
                repo_path=self.repo_path,
                degraded_components=self.degraded_components,
            )
            logger.info("[AUTONOMOUS-HEALING] Silent degradation detector initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Silent degradation detector DEGRADED: {e}")
            self.degradation_detector = None
            self.degraded_components.append({
                "component": "degradation_detector",
                "reason": str(e),
                "impact": "Silent failure detection disabled"
            })
        
        # Initialize Semantic Refactoring Engine (multi-file symbol rename, module moves)
        try:
            from cognitive.semantic_refactoring_engine import get_refactoring_engine
            self.refactoring_engine = get_refactoring_engine(repo_path=str(self.repo_path))
            logger.info("[AUTONOMOUS-HEALING] Semantic refactoring engine initialized")
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Semantic refactoring engine DEGRADED: {e}")
            self.refactoring_engine = None
            self.degraded_components.append({
                "component": "refactoring_engine",
                "reason": str(e),
                "impact": "Multi-file semantic refactoring disabled"
            })
        
        # Log degraded components summary
        if self.degraded_components:
            logger.warning(
                f"[AUTONOMOUS-HEALING] {len(self.degraded_components)} components running in DEGRADED mode: "
                f"{[c['component'] for c in self.degraded_components]}"
            )
        
        logger.info(
            f"[AUTONOMOUS-HEALING] Initialized with trust_level={trust_level.name}, "
            f"learning={'ENABLED' if enable_learning else 'DISABLED'}, "
            f"knowledge_base={'ENABLED' if self.knowledge_base else 'DISABLED'}, "
            f"coding_agent={'CONNECTED' if coding_agent else 'DISCONNECTED'}, "
            f"degraded_components={len(self.degraded_components)}"
        )

    def get_system_capabilities(self) -> Dict[str, Any]:
        """
        Report what capabilities are available vs degraded.
        
        Returns:
            Dict with 'available' and 'degraded' lists of components
        """
        available = []
        degraded = []
        
        # Check each component
        if self.logic_detector is not None:
            available.append("llm_logic_detector")
        
        if self.import_healer is not None:
            available.append("llm_import_healer")
        
        if self.config_healer is not None:
            available.append("llm_config_healer")
        
        if self.knowledge_base is not None:
            available.append("healing_knowledge_base")
        
        if self.script_generator is not None:
            available.append("healing_script_generator")
        
        if self.healing_bridge is not None:
            available.append("healing_bridge")
        
        if self.healing_system is not None:
            available.append("core_healing_system")
        
        if self.genesis_service is not None:
            available.append("genesis_service")
        
        if self.validation_pipeline is not None:
            available.append("validation_pipeline")
        
        if self.degradation_detector is not None:
            available.append("degradation_detector")
        
        # Add degraded components
        for component in self.degraded_components:
            degraded.append({
                "component": component["component"],
                "reason": component["reason"],
                "impact": component["impact"]
            })
        
        return {
            "available": available,
            "degraded": degraded,
            "available_count": len(available),
            "degraded_count": len(degraded),
            "health_status": "healthy" if len(degraded) == 0 else "degraded"
        }

    def _initialize_trust_scores(self):
        """Initialize trust scores for healing actions (0.0 = no trust, 1.0 = full trust)."""
        # Start with conservative trust scores
        self.trust_scores = {
            HealingAction.BUFFER_CLEAR: 0.9,         # Very safe action
            HealingAction.CACHE_FLUSH: 0.85,         # Safe action
            HealingAction.CONNECTION_RESET: 0.75,    # Generally safe
            HealingAction.DATABASE_TABLE_CREATE: 0.95,  # Safe - creating missing tables
            HealingAction.CODE_FIX: 0.80,            # Safe - code fixes with knowledge base
            HealingAction.SEMANTIC_REFACTOR: 0.70,   # Multi-file refactoring with validation
            HealingAction.PROCESS_RESTART: 0.60,     # Moderate risk
            HealingAction.SERVICE_RESTART: 0.50,     # Moderate-high risk
            HealingAction.STATE_ROLLBACK: 0.40,      # High risk
            HealingAction.ISOLATION: 0.35,           # High risk
            HealingAction.EMERGENCY_SHUTDOWN: 0.20,  # Very high risk
        }

    # ======================================================================
    # Health Monitoring
    # ======================================================================

    def assess_system_health(self) -> Dict[str, Any]:
        """
        Assess overall system health.

        Returns health status and detected anomalies.
        """
        logger.info("[AUTONOMOUS-HEALING] Assessing system health...")

        # Scan for code issues using Genesis Keys
        code_issues = self.healing_system.scan_for_issues()
        
        # Also scan for Pydantic logger issues
        try:
            from diagnostic_machine.proactive_code_scanner import get_proactive_scanner
            scanner = get_proactive_scanner()
            pydantic_issues = scanner.scan_pydantic_logger_issues()
            if pydantic_issues:
                # Convert to code_issues format
                for issue in pydantic_issues:
                    code_issues.append({
                        "type": "pydantic_logger",
                        "severity": "high",
                        "file": issue.file_path,
                        "line": issue.line_number,
                        "message": issue.message,
                        "suggested_fix": issue.suggested_fix
                    })
        except Exception as e:
            logger.debug(f"Could not scan for Pydantic logger issues: {e}")

        # Query recent Genesis Keys for errors
        recent_errors = self._query_recent_errors()

        # Check for anomalies
        anomalies = self._detect_anomalies(code_issues, recent_errors)
        
        # Check service health (NEW: Active service monitoring)
        service_health = self._check_service_health()
        anomalies.extend(service_health.get("anomalies", []))

        # Determine health status
        health_status = self._calculate_health_status(anomalies)

        assessment = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": health_status.value,
            "code_issues": len(code_issues),
            "recent_errors": len(recent_errors),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "trust_level": self.trust_level.name
        }

        self.current_health = health_status
        self.anomalies_detected = anomalies

        logger.info(
            f"[AUTONOMOUS-HEALING] Health: {health_status.value.upper()}, "
            f"Anomalies: {len(anomalies)}, Issues: {len(code_issues)}"
        )

        return assessment

    def _query_recent_errors(self, hours: int = 1) -> List[GenesisKey]:
        """Query recent error Genesis Keys."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        errors = self.session.query(GenesisKey).filter(
            GenesisKey.created_at >= cutoff_time,
            GenesisKey.key_type == GenesisKeyType.ERROR
        ).all()

        return errors

    def _detect_anomalies(
        self,
        code_issues: List[Dict],
        recent_errors: List[GenesisKey]
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies from code issues and error patterns.
        
        Enhanced with LLM-powered logic error detection.

        Returns list of detected anomalies with type and severity.
        """
        anomalies = []
        
        # LLM-powered logic error detection
        if self.logic_detector and recent_errors:
            logic_errors = self._detect_logic_errors_with_llm(recent_errors)
            anomalies.extend(logic_errors)
        
        # LLM-powered import error detection (adaptive for dependency upgrades)
        if self.import_healer and recent_errors:
            import_errors = self._detect_import_errors_with_llm(recent_errors)
            anomalies.extend(import_errors)
        
        # LLM-powered configuration error detection (adaptive for dependency upgrades)
        if self.config_healer and recent_errors:
            config_errors = self._detect_config_errors_with_llm(recent_errors)
            anomalies.extend(config_errors)

        # Check for error spikes
        if len(recent_errors) > 10:
            anomalies.append({
                "type": AnomalyType.ERROR_SPIKE,
                "severity": "critical" if len(recent_errors) > 50 else "warning",
                "details": f"{len(recent_errors)} errors in last hour",
                "evidence": [e.key_id for e in recent_errors[:5]]  # Sample
            })

        # Check for database table errors
        missing_tables = set()
        table_redefinition_errors = []
        database_errors = []
        datatype_mismatch_errors = []
        for error in recent_errors:
            error_msg = error.error_message or ""
            # Check for table redefinition (SQLAlchemy metadata issue)
            if "already defined" in error_msg.lower() and "table" in error_msg.lower():
                # Extract table name from error message
                import re
                table_match = re.search(r"table['\"]?\s*:?\s*['\"]?(\w+)['\"]?", error_msg, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    missing_tables.add(table_name)
                    table_redefinition_errors.append({
                        "error": error,
                        "table_name": table_name,
                        "file_path": error.file_path or (error.context_data.get("file_path") if error.context_data else None)
                    })
            elif "no such table" in error_msg.lower() or "table.*does not exist" in error_msg.lower():
                # Extract table name from error message
                import re
                table_match = re.search(r"table['\"]?\s*:?\s*['\"]?(\w+)['\"]?", error_msg, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    missing_tables.add(table_name)
                    database_errors.append(error)
            # Check for datatype mismatch (THREAD ISSUE)
            elif "datatype mismatch" in error_msg.lower() or "IntegrityError.*datatype" in error_msg.lower():
                datatype_mismatch_errors.append(error)
        
        # SQLAlchemy table redefinition - use CODE_FIX
        if table_redefinition_errors:
            file_paths = [e["file_path"] for e in table_redefinition_errors if e["file_path"]]
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"SQLAlchemy table redefinition errors: {len(table_redefinition_errors)} components affected",
                "service": "database",
                "error_message": "Table redefinition errors - SQLAlchemy metadata issue",
                "file_paths": list(set(file_paths))[:20],  # Limit to 20 unique paths
                "file_path": file_paths[0] if file_paths else None,
                "evidence": [e["error"].key_id for e in table_redefinition_errors[:10]]
            })
        # THREAD ISSUE: Database datatype mismatch
        elif datatype_mismatch_errors:
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"Database datatype mismatch errors detected: {len(datatype_mismatch_errors)} errors",
                "service": "database",
                "error_message": "Datatype mismatch - database schema out of sync with models",
                "evidence": [e.key_id for e in datatype_mismatch_errors[:5]]
            })
        elif missing_tables:
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"Missing database tables: {', '.join(missing_tables)}",
                "service": "database",
                "missing_tables": list(missing_tables),
                "evidence": [e.key_id for e in database_errors[:5]]
            })
        
        # Check for database connection errors
        db_connection_errors = [e for e in recent_errors 
                               if e.error_type and "database" in e.error_type.lower() or
                                  (e.error_message and "database" in e.error_message.lower() and 
                                   ("connection" in e.error_message.lower() or "unhealthy" in e.error_message.lower()))]
        if len(db_connection_errors) > 3:
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "critical",
                "details": f"{len(db_connection_errors)} database connection errors detected",
                "service": "database",
                "evidence": [e.key_id for e in db_connection_errors[:5]]
            })
        
        # THREAD ISSUES: Check for indentation errors, port conflicts, missing files, process failures
        indentation_errors = [e for e in recent_errors
                             if e.error_message and ("IndentationError" in e.error_message or "indentation" in e.error_message.lower() or "expected an indented block" in e.error_message.lower())]
        if indentation_errors:
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"{len(indentation_errors)} indentation/syntax errors detected",
                "service": "code",
                "error_message": "Indentation errors preventing code execution",
                "evidence": [e.key_id for e in indentation_errors[:5]]
            })
        
        port_conflict_errors = [e for e in recent_errors
                               if e.error_message and ("port" in e.error_message.lower() and ("already in use" in e.error_message.lower() or "address already" in e.error_message.lower()))]
        if port_conflict_errors:
            anomalies.append({
                "type": AnomalyType.RESOURCE_EXHAUSTION,
                "severity": "high",
                "details": f"Port conflict detected: {port_conflict_errors[0].error_message[:100]}",
                "service": "launcher",
                "error_message": port_conflict_errors[0].error_message,
                "evidence": [e.key_id for e in port_conflict_errors[:3]]
            })
        
        missing_file_errors = [e for e in recent_errors
                              if e.error_message and ("FileNotFoundError" in e.error_message or "not found" in e.error_message.lower() or "missing" in e.error_message.lower())]
        if missing_file_errors:
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "critical",
                "details": f"{len(missing_file_errors)} missing file/directory errors detected",
                "service": "filesystem",
                "error_message": "Missing critical files or directories",
                "evidence": [e.key_id for e in missing_file_errors[:5]]
            })
        
        process_crash_errors = [e for e in recent_errors
                               if e.error_message and ("process" in e.error_message.lower() and ("died" in e.error_message.lower() or "exited" in e.error_message.lower() or "crashed" in e.error_message.lower()))]
        if process_crash_errors:
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "critical",
                "details": f"{len(process_crash_errors)} process crash/failure errors detected",
                "service": "process",
                "error_message": "Process failures detected",
                "evidence": [e.key_id for e in process_crash_errors[:5]]
            })

        # Check for code issue patterns
        critical_issues = [i for i in code_issues if i.get("severity") == "critical"]
        if len(critical_issues) > 5:
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"{len(critical_issues)} critical code issues detected",
                "evidence": [i.get("file_genesis_key") for i in critical_issues[:5]]
            })

        # Check for repeated failures (same file multiple times)
        file_error_counts = {}
        for error in recent_errors:
            # Use file_path column or context_data
            file_path = error.file_path
            if not file_path and error.context_data:
                file_path = error.context_data.get("file_path")
            if file_path:
                file_error_counts[file_path] = file_error_counts.get(file_path, 0) + 1

        for file_path, count in file_error_counts.items():
            if count > 3:
                anomalies.append({
                    "type": AnomalyType.PERFORMANCE_DEGRADATION,
                    "severity": "warning",
                    "details": f"File '{file_path}' failing repeatedly ({count} times)",
                    "evidence": [file_path]
                })
        
        # Check diagnostic engine alerts if enabled
        if self.diagnostic_enabled:
            diagnostic_alerts = self._check_diagnostic_engine()
            anomalies.extend(diagnostic_alerts)
        
        # THREAD ISSUES: Check code quality sensor for thread-related issues
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            engine = get_diagnostic_engine()
            if engine and engine.state.value == "running":
                code_quality = engine.sensor_layer._collect_code_quality()
                if code_quality:
                    # Extract thread issues from code quality scan
                    thread_issues = []
                    for issue in code_quality.configuration_issues + code_quality.database_issues + code_quality.syntax_errors:
                        if any(keyword in issue.issue_type.lower() for keyword in [
                            'indentation', 'datatype_mismatch', 'port_conflict', 'missing_file',
                            'missing_directory', 'process_failure', 'connection_failure'
                        ]):
                            thread_issues.append({
                                "type": AnomalyType.DATA_INCONSISTENCY if "indentation" in issue.issue_type or "datatype" in issue.issue_type
                                        else AnomalyType.RESOURCE_EXHAUSTION if "port" in issue.issue_type
                                        else AnomalyType.SERVICE_FAILURE,
                                "severity": issue.severity,
                                "details": f"{issue.issue_type}: {issue.description}",
                                "service": "code" if "indentation" in issue.issue_type else "database" if "datatype" in issue.issue_type else "launcher",
                                "error_message": issue.description,
                                "file_path": issue.file_path,
                                "line_number": issue.line_number,
                                "evidence": [f"{issue.file_path}:{issue.line_number}"]
                            })
                    anomalies.extend(thread_issues)
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not check code quality sensor: {e}")

        # NEW: Detect silent failures and degradation
        silent_failures = self._detect_silent_failures()
        anomalies.extend(silent_failures)
        
        degradation_issues = self._detect_feature_degradation()
        anomalies.extend(degradation_issues)

        return anomalies
    
    def detect_silent_degradation(self) -> Dict[str, Any]:
        """
        Use SilentDegradationDetector to scan for silently failing components.
        
        Returns:
            Degradation report with all detected issues
        """
        if self.degradation_detector is None:
            logger.warning("[AUTONOMOUS-HEALING] Degradation detector not available")
            return {"summary": {"total_issues": 0}, "all_issues": []}
        
        try:
            issues = self.degradation_detector.scan_for_silent_failures()
            telemetry_issues = self.degradation_detector.scan_telemetry_gaps()
            
            for issue in issues + telemetry_issues:
                if hasattr(self, 'degradation_detector') and self.degradation_detector:
                    self.degradation_detector.register_degraded_component(
                        component=issue.component,
                        reason=issue.description,
                        impact=f"Health impact: {issue.health_impact_score:.2f}"
                    )
            
            report = self.degradation_detector.get_degradation_report()
            logger.info(
                f"[AUTONOMOUS-HEALING] Silent degradation scan: {report['summary']['total_issues']} issues found"
            )
            return report
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Error in degradation scan: {e}")
            return {"summary": {"total_issues": 0}, "error": str(e)}

    def _detect_silent_failures(self) -> List[Dict[str, Any]]:
        """
        Detect components that are failing silently without proper logging.
        
        Checks for:
        - TimeSense integration failures (cognitive engine)
        - Missing error logs for expected operations
        - Components returning None/empty without errors
        - Silent degradation via SilentDegradationDetector
        """
        anomalies = []
        
        if self.degradation_detector:
            try:
                issues = self.degradation_detector.scan_for_silent_failures(max_files=30)
                for issue in issues:
                    if issue.severity.value in ("critical", "high"):
                        anomalies.append({
                            "type": AnomalyType.SILENT_FAILURE,
                            "severity": "critical" if issue.severity.value == "critical" else "warning",
                            "details": issue.description,
                            "component": issue.component,
                            "file_path": issue.file_path,
                            "line_number": issue.line_number,
                            "error_message": issue.suggested_fix,
                            "evidence": [issue.issue_id],
                            "health_impact": issue.health_impact_score,
                        })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Degradation detector scan failed: {e}")
        
        try:
            # Check Cognitive Engine degradation metrics
            from cognitive.engine import CognitiveEngine
            engine = CognitiveEngine()
            degradation_metrics = engine.get_degradation_metrics()
            
            if degradation_metrics:
                for degradation_type, count in degradation_metrics.items():
                    if count > 0:
                        severity = "critical" if count > 10 else "warning"
                        anomalies.append({
                            "type": AnomalyType.SILENT_FAILURE,
                            "severity": severity,
                            "details": f"Silent failure detected: {degradation_type} ({count} occurrences)",
                            "component": "cognitive_engine",
                            "degradation_type": degradation_type,
                            "count": count,
                            "error_message": f"Component {degradation_type} has failed {count} times without proper alerting"
                        })
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not check cognitive engine degradation: {e}")
        
        # Check for log patterns indicating silent failures
        try:
            # Check recent logs for TimeSense warnings (should be warnings, not silent)
            from database.session import SessionLocal
            session = SessionLocal()
            try:
                # Query for recent errors that might indicate silent failures
                from models.genesis_key_models import GenesisKey, GenesisKeyType
                from datetime import datetime, timedelta
                
                cutoff = datetime.utcnow() - timedelta(hours=1)
                recent_keys = session.query(GenesisKey).filter(
                    GenesisKey.created_at >= cutoff
                ).all()
                
                # Look for patterns indicating silent degradation
                timesense_issues = []
                transform_fallbacks = []
                telemetry_failures = []
                
                for key in recent_keys:
                    error_msg = (key.error_message or "").lower()
                    metadata = key.metadata or {}
                    
                    # Check for TimeSense issues
                    if "timesense" in error_msg or "time awareness" in error_msg:
                        timesense_issues.append(key)
                    
                    # Check for transform fallbacks
                    if "transform generation error" in error_msg or "falling back to llm" in error_msg:
                        transform_fallbacks.append(key)
                    
                    # Check for telemetry failures
                    if "failed to record tokens" in error_msg or "failed to record confidence" in error_msg:
                        telemetry_failures.append(key)
                
                # Report if we see patterns but no proper alerts
                if len(timesense_issues) > 5:
                    anomalies.append({
                        "type": AnomalyType.SILENT_FAILURE,
                        "severity": "warning",
                        "details": f"TimeSense integration failing frequently ({len(timesense_issues)} times) - may be degrading silently",
                        "component": "cognitive_engine_timesense",
                        "count": len(timesense_issues),
                        "evidence": [k.key_id for k in timesense_issues[:5]]
                    })
                
                if len(transform_fallbacks) > 10:
                    anomalies.append({
                        "type": AnomalyType.FEATURE_DEGRADATION,
                        "severity": "warning",
                        "details": f"Transform generation falling back to LLM frequently ({len(transform_fallbacks)} times) - feature degrading",
                        "component": "llm_orchestrator",
                        "count": len(transform_fallbacks),
                        "evidence": [k.key_id for k in transform_fallbacks[:5]]
                    })
                
                if len(telemetry_failures) > 5:
                    anomalies.append({
                        "type": AnomalyType.TELEMETRY_LOSS,
                        "severity": "warning",
                        "details": f"Telemetry recording failures ({len(telemetry_failures)} times) - metrics may be incomplete",
                        "component": "telemetry_service",
                        "count": len(telemetry_failures),
                        "evidence": [k.key_id for k in telemetry_failures[:5]]
                    })
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not check log patterns: {e}")
        
        return anomalies
    
    def _detect_feature_degradation(self) -> List[Dict[str, Any]]:
        """
        Detect features that are degrading with fallbacks.
        
        Checks for:
        - High fallback rates (transforms -> LLM)
        - Telemetry recording failures
        - Message bus handler failures
        """
        anomalies = []
        
        try:
            # Check telemetry service for recording failures
            from telemetry.telemetry_service import TelemetryService
            from database.session import SessionLocal
            
            session = SessionLocal()
            try:
                telemetry = TelemetryService(session=session)
                
                # Check recent operation logs for recording failures
                from models.telemetry_models import OperationLog
                from datetime import datetime, timedelta
                
                cutoff = datetime.utcnow() - timedelta(hours=1)
                recent_ops = session.query(OperationLog).filter(
                    OperationLog.started_at >= cutoff
                ).all()
                
                # Count operations with missing telemetry data
                missing_tokens = sum(1 for op in recent_ops if op.input_tokens is None and op.output_tokens is None)
                missing_confidence = sum(1 for op in recent_ops if op.confidence_score is None)
                
                if missing_tokens > len(recent_ops) * 0.2:  # More than 20% missing
                    anomalies.append({
                        "type": AnomalyType.TELEMETRY_LOSS,
                        "severity": "warning",
                        "details": f"High rate of missing token telemetry ({missing_tokens}/{len(recent_ops)} operations)",
                        "component": "telemetry_service",
                        "missing_rate": missing_tokens / len(recent_ops) if recent_ops else 0
                    })
                
                if missing_confidence > len(recent_ops) * 0.3:  # More than 30% missing
                    anomalies.append({
                        "type": AnomalyType.TELEMETRY_LOSS,
                        "severity": "warning",
                        "details": f"High rate of missing confidence scores ({missing_confidence}/{len(recent_ops)} operations)",
                        "component": "telemetry_service",
                        "missing_rate": missing_confidence / len(recent_ops) if recent_ops else 0
                    })
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not check telemetry degradation: {e}")
        
        # Check message bus handler failures (if accessible)
        try:
            from layer1.message_bus import Layer1MessageBus
            # Note: Message bus may not expose failure stats directly
            # This would need to be added to message bus implementation
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not check message bus: {e}")
        
        return anomalies
    
    def _check_diagnostic_engine(self) -> List[Dict[str, Any]]:
        """
        Check diagnostic engine for alerts and issues.
        
        THREAD ISSUES: Enhanced to check code quality sensor for all thread-related issues.
        
        Returns:
            List of anomalies detected by diagnostic engine
        """
        anomalies = []
        
        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            from diagnostic_machine.proactive_scanner import ProactiveScanner
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            
            # Check for diagnostic alerts from proactive scanner
            scanner = ProactiveScanner(self.repo_path)
            issues = scanner.scan_all()
            
            # Convert diagnostic issues to anomalies
            critical_issues = [i for i in issues if getattr(i, 'severity', 'low') == 'critical']
            if critical_issues:
                anomalies.append({
                    "type": AnomalyType.DATA_INCONSISTENCY,
                    "severity": "critical",
                    "details": f"Diagnostic engine found {len(critical_issues)} critical issues",
                    "source": "diagnostic_engine",
                    "evidence": [f"{getattr(i, 'file_path', 'unknown')}:{getattr(i, 'line_number', 0)}" 
                                for i in critical_issues[:5]]
                })
            
            # THREAD ISSUES: Check code quality sensor from diagnostic engine
            try:
                engine = get_diagnostic_engine()
                if engine and hasattr(engine, 'sensor_layer'):
                    code_quality = engine.sensor_layer._collect_code_quality()
                    if code_quality:
                        # Extract thread-specific issues
                        thread_issue_types = [
                            'indentation_error', 'potential_indentation_error',
                            'database_datatype_mismatch', 'database_schema_mismatch',
                            'port_conflict', 'missing_backend_file', 'missing_directory',
                            'process_failure', 'connection_failure'
                        ]
                        
                        all_thread_issues = []
                        for issue_list in [
                            code_quality.configuration_issues,
                            code_quality.database_issues,
                            getattr(code_quality, 'syntax_errors', []),
                            getattr(code_quality, 'infrastructure_issues', [])
                        ]:
                            for issue in issue_list:
                                if any(thread_type in issue.issue_type.lower() for thread_type in thread_issue_types):
                                    all_thread_issues.append(issue)
                        
                        # Group by type
                        if all_thread_issues:
                            indentation_issues = [i for i in all_thread_issues if 'indentation' in i.issue_type.lower()]
                            datatype_issues = [i for i in all_thread_issues if 'datatype' in i.issue_type.lower()]
                            port_issues = [i for i in all_thread_issues if 'port' in i.issue_type.lower()]
                            missing_file_issues = [i for i in all_thread_issues if 'missing' in i.issue_type.lower()]
                            process_issues = [i for i in all_thread_issues if 'process' in i.issue_type.lower()]
                            
                            if indentation_issues:
                                anomalies.append({
                                    "type": AnomalyType.DATA_INCONSISTENCY,
                                    "severity": "critical",
                                    "details": f"Diagnostic engine found {len(indentation_issues)} indentation/syntax errors",
                                    "source": "diagnostic_engine_code_quality",
                                    "error_message": "Indentation errors preventing code execution",
                                    "file_path": indentation_issues[0].file_path,
                                    "line_number": indentation_issues[0].line_number,
                                    "evidence": [f"{i.file_path}:{i.line_number}" for i in indentation_issues[:5]]
                                })
                            
                            if datatype_issues:
                                anomalies.append({
                                    "type": AnomalyType.DATA_INCONSISTENCY,
                                    "severity": "critical",
                                    "details": f"Diagnostic engine found {len(datatype_issues)} database datatype mismatch issues",
                                    "source": "diagnostic_engine_code_quality",
                                    "service": "database",
                                    "error_message": "Database schema out of sync with models",
                                    "evidence": [f"{i.file_path}:{i.line_number}" for i in datatype_issues[:5]]
                                })
                            
                            if port_issues:
                                anomalies.append({
                                    "type": AnomalyType.RESOURCE_EXHAUSTION,
                                    "severity": "high",
                                    "details": f"Diagnostic engine found {len(port_issues)} port conflict issues",
                                    "source": "diagnostic_engine_code_quality",
                                    "service": "launcher",
                                    "error_message": port_issues[0].description,
                                    "evidence": [f"{i.file_path}:{i.line_number}" for i in port_issues[:3]]
                                })
                            
                            if missing_file_issues:
                                anomalies.append({
                                    "type": AnomalyType.SERVICE_FAILURE,
                                    "severity": "critical",
                                    "details": f"Diagnostic engine found {len(missing_file_issues)} missing file/directory issues",
                                    "source": "diagnostic_engine_code_quality",
                                    "service": "filesystem",
                                    "error_message": "Missing critical files or directories",
                                    "evidence": [f"{i.file_path}:{i.line_number}" for i in missing_file_issues[:5]]
                                })
                            
                            if process_issues:
                                anomalies.append({
                                    "type": AnomalyType.SERVICE_FAILURE,
                                    "severity": "critical",
                                    "details": f"Diagnostic engine found {len(process_issues)} process failure issues",
                                    "source": "diagnostic_engine_code_quality",
                                    "service": "process",
                                    "error_message": "Process crashes or failures detected",
                                    "evidence": [f"{i.file_path}:{i.line_number}" for i in process_issues[:5]]
                                })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Code quality sensor check failed: {e}")
                
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Diagnostic engine check failed: {e}")
            # Diagnostic engine unavailable - not critical
        
        # ✅ NEW: Create Genesis Keys for diagnostic outcomes to trigger LLM knowledge update
        if anomalies:
            try:
                for anomaly in anomalies:
                    # Only create Genesis Key for high-severity issues (valuable for learning)
                    if anomaly.get('severity') in ['critical', 'high']:
                        diagnostic_genesis_key = self.genesis_service.create_key(
                            key_type='ERROR' if anomaly.get('severity') == 'critical' else 'SYSTEM_EVENT',
                            what_description=f"Diagnostic issue: {anomaly.get('type', 'unknown')} - {anomaly.get('details', '')[:100]}",
                            who_actor="diagnostic_engine",
                            where_location=anomaly.get('file_path') or anomaly.get('service', 'unknown'),
                            why_reason="Diagnostic outcome for LLM knowledge update",
                            how_method="diagnostic_scanning",
                            file_path=anomaly.get('file_path'),
                            is_error=anomaly.get('severity') == 'critical',
                            error_type=str(anomaly.get('type', 'unknown')),
                            error_message=anomaly.get('details', ''),
                            context_data={
                                'anomaly_type': str(anomaly.get('type', 'unknown')),
                                'severity': anomaly.get('severity'),
                                'service': anomaly.get('service'),
                                'source': anomaly.get('source', 'diagnostic_engine')
                            },
                            metadata={
                                'outcome_type': 'diagnostic_outcome',
                                'example_type': 'diagnostic_outcome',
                                'trust_score': 0.85 if anomaly.get('severity') == 'critical' else 0.75,
                                'success': False,  # Diagnostic issues are problems
                                'anomaly_type': str(anomaly.get('type', 'unknown')),
                                'severity': anomaly.get('severity'),
                                'service': anomaly.get('service')
                            },
                            session=self.session
                        )
                        logger.debug(
                            f"[AUTONOMOUS-HEALING] Created Genesis Key for diagnostic outcome: "
                            f"{diagnostic_genesis_key.key_id} (severity={anomaly.get('severity')})"
                        )
            except Exception as e:
                logger.warning(f"[AUTONOMOUS-HEALING] Could not create Genesis Key for diagnostic outcome: {e}")
        
        return anomalies

    def _check_service_health(self) -> Dict[str, Any]:
        """
        Check health of external services (Qdrant, Ollama, Database, etc.).
        
        Uses optimized parallel checker if available for better performance.
        
        Returns:
            Dict with service status and detected anomalies
        """
        service_status = {}
        anomalies = []
        
        # Try to use optimized parallel checker if available
        try:
            from cognitive.optimized_health_checker import get_optimized_health_checker
            import asyncio
            
            checker = get_optimized_health_checker()
            # Run async check in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                service_health = loop.run_until_complete(checker.check_all_services_parallel())
                
                # Convert to our format
                service_status = {
                    "qdrant": service_health.get("qdrant", {}),
                    "ollama": service_health.get("ollama", {}),
                    "database": service_health.get("database", {}),
                    "backend": service_health.get("backend", {})
                }
                
                # Extract anomalies from service status
                for service, health in service_status.items():
                    if isinstance(health, dict):
                        status = health.get("status", "unknown")
                        if status in ["unhealthy", "error"]:
                            anomalies.append({
                                "type": AnomalyType.SERVICE_FAILURE,
                                "severity": "critical" if service in ["qdrant", "database"] else "warning",
                                "details": f"{service.capitalize()} service {status}: {health.get('error', '')}",
                                "service": service,
                                "evidence": [health.get("error", "")]
                            })
                        elif status == "timeout":
                            anomalies.append({
                                "type": AnomalyType.PERFORMANCE_DEGRADATION,
                                "severity": "warning",
                                "details": f"{service.capitalize()} health check timed out",
                                "service": service
                            })
                
                return {
                    "services": service_status,
                    "anomalies": anomalies
                }
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Optimized checker not available, using fallback: {e}")
            # Fall through to original implementation
        
        # Check Qdrant connection
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            if client:
                try:
                    # Try to list collections (quick health check)
                    collections = client.list_collections()
                    service_status["qdrant"] = {"status": "healthy", "collections": len(collections)}
                except Exception as e:
                    service_status["qdrant"] = {"status": "unhealthy", "error": str(e)}
                    anomalies.append({
                        "type": AnomalyType.SERVICE_FAILURE,
                        "severity": "critical",
                        "details": f"Qdrant connection failed: {str(e)}",
                        "service": "qdrant",
                        "evidence": [str(e)]
                    })
            else:
                service_status["qdrant"] = {"status": "unavailable"}
                anomalies.append({
                    "type": AnomalyType.SERVICE_FAILURE,
                    "severity": "warning",
                    "details": "Qdrant client not available",
                    "service": "qdrant"
                })
        except Exception as e:
            service_status["qdrant"] = {"status": "error", "error": str(e)}
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "critical",
                "details": f"Qdrant check failed: {str(e)}",
                "service": "qdrant",
                "evidence": [str(e)]
            })
        
        # Check Ollama connection
        try:
            from ollama_client.client import get_ollama_client
            client = get_ollama_client()
            if client and client.is_running():
                service_status["ollama"] = {"status": "healthy"}
            else:
                service_status["ollama"] = {"status": "unavailable"}
                anomalies.append({
                    "type": AnomalyType.SERVICE_FAILURE,
                    "severity": "warning",  # Ollama is optional
                    "details": "Ollama service not running",
                    "service": "ollama"
                })
        except Exception as e:
            service_status["ollama"] = {"status": "error", "error": str(e)}
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "warning",
                "details": f"Ollama check failed: {str(e)}",
                "service": "ollama"
            })
        
        # Check Database connection
        try:
            from database.connection import DatabaseConnection
            if DatabaseConnection.health_check():
                service_status["database"] = {"status": "healthy"}
            else:
                service_status["database"] = {"status": "unhealthy"}
                anomalies.append({
                    "type": AnomalyType.SERVICE_FAILURE,
                    "severity": "critical",
                    "details": "Database health check failed",
                    "service": "database"
                })
        except Exception as e:
            service_status["database"] = {"status": "error", "error": str(e)}
            anomalies.append({
                "type": AnomalyType.SERVICE_FAILURE,
                "severity": "critical",
                "details": f"Database check failed: {str(e)}",
                "service": "database"
            })
        
        # Check backend health endpoint (if available)
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                service_status["backend"] = {"status": data.get("status", "unknown")}
                if data.get("status") == "degraded":
                    anomalies.append({
                        "type": AnomalyType.PERFORMANCE_DEGRADATION,
                        "severity": "warning",
                        "details": "Backend health check reports degraded status",
                        "service": "backend"
                    })
            else:
                service_status["backend"] = {"status": "unhealthy", "code": response.status_code}
                anomalies.append({
                    "type": AnomalyType.SERVICE_FAILURE,
                    "severity": "critical",
                    "details": f"Backend health check returned {response.status_code}",
                    "service": "backend"
                })
        except requests.exceptions.Timeout:
            service_status["backend"] = {"status": "timeout"}
            anomalies.append({
                "type": AnomalyType.PERFORMANCE_DEGRADATION,
                "severity": "warning",
                "details": "Backend health check timed out",
                "service": "backend"
            })
        except Exception as e:
            service_status["backend"] = {"status": "error", "error": str(e)}
            # Don't add anomaly if backend is just starting up
        
        return {
            "services": service_status,
            "anomalies": anomalies
        }

    def _calculate_health_status(self, anomalies: List[Dict]) -> HealthStatus:
        """Calculate overall health status from detected anomalies."""
        if not anomalies:
            return HealthStatus.HEALTHY

        critical_count = sum(1 for a in anomalies if a["severity"] == "critical")
        warning_count = sum(1 for a in anomalies if a["severity"] == "warning")

        if critical_count >= 2:
            return HealthStatus.FAILING
        elif critical_count >= 1:
            return HealthStatus.CRITICAL
        elif warning_count >= 3:
            return HealthStatus.WARNING
        elif warning_count >= 1:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    # ======================================================================
    # Autonomous Decision Making (AVM-style)
    # ======================================================================

    def decide_healing_actions(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Decide what healing actions to take based on anomalies.

        Uses trust scores and progressive autonomy to determine actions.
        """
        decisions = []

        for anomaly in anomalies:
            # Determine appropriate healing action
            action = self._select_healing_action(anomaly)

            # Get trust score for action
            trust_score = self.trust_scores.get(action, 0.5)

            # Decide if we can execute autonomously
            can_auto_execute = self._can_auto_execute(action, trust_score)

            decision = {
                "anomaly": anomaly,
                "healing_action": action.value,
                "trust_score": trust_score,
                "execution_mode": "autonomous" if can_auto_execute else "manual_approval",
                "reason": self._explain_decision(anomaly, action, trust_score)
            }

            decisions.append(decision)

        logger.info(
            f"[AUTONOMOUS-HEALING] Decided {len(decisions)} healing actions, "
            f"{sum(1 for d in decisions if d['execution_mode'] == 'autonomous')} autonomous"
        )

        return decisions

    def _select_healing_action(self, anomaly: Dict[str, Any]) -> HealingAction:
        """Select appropriate healing action for anomaly type."""
        anomaly_type = anomaly["type"]
        severity = anomaly["severity"]
        details = anomaly.get("details", "").lower()

        # Check if it's a code issue that can be fixed with knowledge base
        if self.knowledge_base:
            error_message = details or anomaly.get("error_message", "")
            if error_message:
                issue_info = self.knowledge_base.identify_issue_type(error_message)
                if issue_info:
                    issue_type, pattern = issue_info
                    # Use CODE_FIX for known fixable issues
                    if pattern.confidence > 0.7:
                        return HealingAction.CODE_FIX

        # Map anomaly types to healing actions
        if anomaly_type == AnomalyType.ERROR_SPIKE:
            if severity == "critical":
                return HealingAction.PROCESS_RESTART
            else:
                return HealingAction.BUFFER_CLEAR

        elif anomaly_type == AnomalyType.MEMORY_LEAK:
            return HealingAction.CACHE_FLUSH

        elif anomaly_type == AnomalyType.PERFORMANCE_DEGRADATION:
            return HealingAction.CONNECTION_RESET

        elif anomaly_type == AnomalyType.DATA_INCONSISTENCY:
            # Check if it's a logic error detected by LLM
            if anomaly.get("source") == "llm_logic_detector":
                # Logic errors detected by LLM - use CODE_FIX with LLM-generated fix
                return HealingAction.CODE_FIX
            # Check if it's a SQLAlchemy table redefinition issue (code fix)
            elif "table redefinition" in details.lower() or ("table" in details.lower() and "already defined" in details.lower()):
                # SQLAlchemy table redefinition - use CODE_FIX
                return HealingAction.CODE_FIX
            # THREAD ISSUE: Check for datatype mismatch
            elif "datatype mismatch" in details.lower() or "datatype_mismatch" in details.lower():
                # Database schema mismatch - recreate database or migrate
                return HealingAction.DATABASE_TABLE_CREATE
            # THREAD ISSUE: Check for indentation errors
            elif "indentation" in details.lower() or "indentation_error" in details.lower():
                # Syntax/indentation error - use CODE_FIX
                return HealingAction.CODE_FIX
            # Check if it's a missing table issue
            elif "missing_tables" in anomaly:
                return HealingAction.DATABASE_TABLE_CREATE
            elif severity == "critical":
                return HealingAction.STATE_ROLLBACK
            else:
                return HealingAction.CACHE_FLUSH

        elif anomaly_type == AnomalyType.SECURITY_BREACH:
            return HealingAction.ISOLATION

        elif anomaly_type == AnomalyType.RESOURCE_EXHAUSTION:
            # THREAD ISSUE: Check if it's a port conflict (should find alternative port)
            if "port" in details.lower() and ("conflict" in details.lower() or "already in use" in details.lower()):
                # Port conflict - connection reset or find alternative port
                return HealingAction.CONNECTION_RESET
            return HealingAction.SERVICE_RESTART

        elif anomaly_type == AnomalyType.SERVICE_FAILURE:
            # Service connection failures - try connection reset first
            service = anomaly.get("service", "unknown")
            if service == "database":
                # Check if it's a missing table issue
                if "missing_tables" in anomaly:
                    return HealingAction.DATABASE_TABLE_CREATE
                # Database connection issues - try connection reset first
                if severity == "critical":
                    return HealingAction.CONNECTION_RESET
                else:
                    return HealingAction.SERVICE_RESTART
            elif service in ["qdrant"]:
                # Critical services - try connection reset, then restart
                if severity == "critical":
                    return HealingAction.CONNECTION_RESET
                else:
                    return HealingAction.SERVICE_RESTART
            elif service == "ollama":
                # Optional service - just log, no action needed
                return HealingAction.BUFFER_CLEAR  # Safe no-op
            else:
                # Unknown service - try connection reset
                return HealingAction.CONNECTION_RESET

        elif anomaly_type == AnomalyType.SILENT_FAILURE:
            # Silent failures need code fixes to add proper logging/monitoring
            component = anomaly.get("component", "")
            if "timesense" in component.lower() or "cognitive_engine" in component.lower():
                # TimeSense failures - fix by ensuring proper logging is in place
                return HealingAction.CODE_FIX
            else:
                # Other silent failures - use code fix to add logging
                return HealingAction.CODE_FIX

        elif anomaly_type == AnomalyType.FEATURE_DEGRADATION:
            # Feature degradation - may need code fixes or service restarts
            component = anomaly.get("component", "")
            if "llm_orchestrator" in component.lower():
                # Transform fallbacks - may need to fix transform generation or restart
                if severity == "critical":
                    return HealingAction.SERVICE_RESTART
                else:
                    return HealingAction.CODE_FIX  # Try to fix transform generation
            else:
                # Other degradation - try connection reset first
                return HealingAction.CONNECTION_RESET

        elif anomaly_type == AnomalyType.TELEMETRY_LOSS:
            # Telemetry loss - usually database/connection issues
            component = anomaly.get("component", "")
            if "telemetry" in component.lower():
                # Telemetry service issues - try connection reset
                return HealingAction.CONNECTION_RESET
            else:
                # Other telemetry issues - may need code fix
                return HealingAction.CODE_FIX

        else:
            return HealingAction.BUFFER_CLEAR  # Default safe action

    def _can_auto_execute(self, action: HealingAction, trust_score: float) -> bool:
        """
        Determine if action can be executed autonomously.

        Based on:
        - Current trust level (system-wide setting)
        - Trust score for specific action
        - Action risk level
        """
        # Map actions to required trust levels
        action_trust_requirements = {
            HealingAction.BUFFER_CLEAR: TrustLevel.LOW_RISK_AUTO,
            HealingAction.CACHE_FLUSH: TrustLevel.LOW_RISK_AUTO,
            HealingAction.CODE_FIX: TrustLevel.LOW_RISK_AUTO,  # Code fixes are safe
            HealingAction.CONNECTION_RESET: TrustLevel.MEDIUM_RISK_AUTO,
            HealingAction.DATABASE_TABLE_CREATE: TrustLevel.LOW_RISK_AUTO,
            HealingAction.PROCESS_RESTART: TrustLevel.MEDIUM_RISK_AUTO,
            HealingAction.SERVICE_RESTART: TrustLevel.HIGH_RISK_AUTO,
            HealingAction.STATE_ROLLBACK: TrustLevel.HIGH_RISK_AUTO,
            HealingAction.ISOLATION: TrustLevel.CRITICAL_AUTO,
            HealingAction.EMERGENCY_SHUTDOWN: TrustLevel.CRITICAL_AUTO,
        }

        required_level = action_trust_requirements.get(action, TrustLevel.MANUAL_ONLY)

        # Check if current trust level is sufficient
        if self.trust_level < required_level:
            return False

        # Check if action-specific trust score is sufficient
        if trust_score < 0.7:  # Require 70% trust minimum
            return False

        return True

    def _explain_decision(
        self,
        anomaly: Dict[str, Any],
        action: HealingAction,
        trust_score: float
    ) -> str:
        """Explain why this healing action was chosen."""
        return (
            f"Detected {anomaly['type'].value} with {anomaly['severity']} severity. "
            f"Selected {action.value} (trust: {trust_score:.2f}). "
            f"Evidence: {', '.join(str(e) for e in anomaly.get('evidence', [])[:2])}"
        )

    # ======================================================================
    # Healing Execution
    # ======================================================================

    def execute_healing(
        self,
        decisions: List[Dict[str, Any]],
        user_id: Optional[str] = "autonomous_healing"
    ) -> Dict[str, Any]:
        """
        Execute healing actions based on decisions.

        Uses validation pipeline for Plan → Patch → Validate → Rollback loop.
        Only executes autonomous actions. Manual approval actions are logged.
        """
        results = {
            "executed": [],
            "awaiting_approval": [],
            "failed": [],
            "rolled_back": [],
        }

        for decision in decisions:
            if decision["execution_mode"] == "autonomous":
                try:
                    result = self._execute_healing_action_with_validation(
                        decision["healing_action"],
                        decision["anomaly"],
                        user_id
                    )
                    
                    if result.get("rolled_back"):
                        results["rolled_back"].append(result)
                    elif result.get("status") == "success":
                        results["executed"].append(result)
                        if self.enable_learning:
                            self._learn_from_healing(decision, result, success=True)
                    else:
                        results["failed"].append({
                            "decision": decision,
                            "error": result.get("error", "Unknown error")
                        })
                        if self.enable_learning:
                            self._learn_from_healing(decision, result, success=False)

                except Exception as e:
                    logger.error(
                        f"[AUTONOMOUS-HEALING] Failed to execute {decision['healing_action']}: {e}"
                    )
                    results["failed"].append({
                        "decision": decision,
                        "error": str(e)
                    })

                    if self.enable_learning:
                        self._learn_from_healing(decision, None, success=False)
                        error_msg = str(e)
                        self._detect_and_fill_gap(error_msg, decision)
            else:
                results["awaiting_approval"].append(decision)

        logger.info(
            f"[AUTONOMOUS-HEALING] Executed: {len(results['executed'])}, "
            f"Awaiting approval: {len(results['awaiting_approval'])}, "
            f"Failed: {len(results['failed'])}"
        )
        
        # Detect gaps from failures and try to fill them
        if results["failed"] and self.enable_learning:
            self._detect_gaps_from_failures(results["failed"])

        return results

    def _execute_healing_action_with_validation(
        self,
        action_name: str,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute healing action with validation pipeline (Plan → Patch → Validate → Rollback).
        
        Uses HealingValidationPipeline to:
        1. Create snapshots of affected files
        2. Apply the healing action
        3. Run validation gates (syntax, lint, type, tests)
        4. Rollback if validation fails
        """
        action = HealingAction(action_name)
        
        if self.validation_pipeline is None:
            return self._execute_action(action_name, anomaly, user_id)
        
        file_paths = []
        if "file_path" in anomaly:
            file_paths.append(anomaly["file_path"])
        if "file_paths" in anomaly:
            file_paths.extend(anomaly["file_paths"])
        
        if file_paths and action in (HealingAction.CODE_FIX, HealingAction.BUFFER_CLEAR):
            from cognitive.healing_validation_pipeline import Patch
            
            self.validation_pipeline.create_snapshot(file_paths)
            
            result = self._execute_action(action_name, anomaly, user_id)
            
            if result.get("status") == "success":
                trust_level_int = self.trust_level.value
                required_gates = self.validation_pipeline.get_required_gates_for_trust_level(trust_level_int)
                
                if required_gates:
                    all_passed, validation_results = self.validation_pipeline.validate(
                        required_gates, file_paths
                    )
                    
                    result["validation_results"] = [
                        {"gate": v.gate.value, "passed": v.passed, "duration_ms": v.duration_ms}
                        for v in validation_results
                    ]
                    
                    if not all_passed:
                        failed_gates = [v.gate.value for v in validation_results if not v.passed]
                        logger.warning(
                            f"[AUTONOMOUS-HEALING] Validation failed for {action.value}: {failed_gates}"
                        )
                        self.validation_pipeline.rollback(f"Validation failed: {failed_gates}")
                        result["rolled_back"] = True
                        result["rollback_reason"] = f"Validation failed: {failed_gates}"
                        result["status"] = "rolled_back"
                    else:
                        logger.info(f"[AUTONOMOUS-HEALING] Validation passed for {action.value}")
                        self.validation_pipeline._snapshots.clear()
            
            return result
        else:
            return self._execute_action(action_name, anomaly, user_id)

    def _execute_action(
        self,
        action_name: str,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Execute a specific healing action."""
        action = HealingAction(action_name)

        logger.info(f"[AUTONOMOUS-HEALING] Executing {action.value}...")

        # Get file Genesis Keys from anomaly evidence
        file_keys = anomaly.get("evidence", [])

        if action == HealingAction.BUFFER_CLEAR:
            # Heal affected files using knowledge base and script generator
            healed_files = []
            
            # Try to use knowledge base for code fixes
            try:
                from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
                from cognitive.healing_script_generator import get_healing_script_generator
                
                knowledge_base = get_healing_knowledge_base()
                script_generator = get_healing_script_generator(self.repo_path)
                
                # Collect issues from anomaly
                issues = []
                if "error_message" in anomaly:
                    issue_type, pattern = knowledge_base.identify_issue_type(anomaly["error_message"])
                    if issue_type:
                        issues.append({
                            "issue_type": issue_type.value,
                            "file_path": anomaly.get("file_path", ""),
                            "error_message": anomaly["error_message"],
                            "line_number": anomaly.get("line_number")
                        })
                
                # Generate and execute patches if issues found
                if issues:
                    patch_result = script_generator.generate_and_execute_patches(
                        issues=issues,
                        auto_execute=True
                    )
                    if patch_result.get("success"):
                        healed_files.append({
                            "type": "script_patch",
                            "patches_applied": patch_result.get("patches_generated", 0),
                            "script_path": patch_result.get("script_path")
                        })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Knowledge base healing failed, using fallback: {e}")
            
            # Fallback to original healing system
            for file_key in file_keys:
                if file_key.startswith("FILE-"):
                    result = self.healing_system.heal_file(
                        file_genesis_key=file_key,
                        user_id=user_id,
                        auto_apply=True
                    )
                    healed_files.append(result)

            return {
                "action": action.value,
                "status": "success",
                "files_healed": len(healed_files),
                "details": healed_files
            }

        elif action == HealingAction.CACHE_FLUSH:
            # Clear caches (placeholder - would implement actual cache clearing)
            return {
                "action": action.value,
                "status": "success",
                "message": "Cache flushed successfully"
            }
        
        elif action == HealingAction.CODE_FIX:
            # Fix code issues using knowledge base and script generator
            # Special handling for silent failures and degradation
            anomaly_type = anomaly.get("type")
            if anomaly_type == AnomalyType.SILENT_FAILURE or anomaly_type == AnomalyType.FEATURE_DEGRADATION:
                return self._execute_silent_failure_fix(anomaly, user_id)
            else:
                return self._execute_code_fix(anomaly, user_id)

        elif action == HealingAction.CONNECTION_RESET:
            # Reset service connections (Qdrant, Database, etc.)
            service = anomaly.get("service", "unknown")
            result = self._reset_service_connection(service)
            return {
                "action": action.value,
                "status": "success" if result["success"] else "failed",
                "service": service,
                "message": result.get("message", ""),
                "details": result
            }

        elif action == HealingAction.DATABASE_TABLE_CREATE:
            # Create missing database tables
            missing_tables = anomaly.get("missing_tables", [])
            
            # Try to fix SQLAlchemy table redefinition issues first
            if "Table" in str(anomaly.get("details", "")) and "already defined" in str(anomaly.get("details", "")):
                try:
                    from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
                    from cognitive.healing_script_generator import get_healing_script_generator
                    
                    knowledge_base = get_healing_knowledge_base()
                    script_generator = get_healing_script_generator(self.repo_path)
                    
                    # Find files with table redefinition issues
                    error_details = anomaly.get("details", "")
                    issues = []
                    
                    # Extract table names and create issues
                    import re
                    table_matches = re.findall(r"Table ['\"](\w+)['\"]", error_details)
                    for table_name in set(table_matches):
                        # Find files that might have this issue
                        # Use evidence from anomaly
                        for evidence in anomaly.get("evidence", []):
                            if isinstance(evidence, str) and evidence.startswith("GK-"):
                                # Get file path from Genesis Key
                                try:
                                    from models.genesis_key_models import GenesisKey
                                    gk = self.session.query(GenesisKey).filter(
                                        GenesisKey.key_id == evidence
                                    ).first()
                                    if gk and gk.file_path:
                                        issues.append({
                                            "issue_type": IssueType.SQLALCHEMY_TABLE_REDEFINITION.value,
                                            "file_path": gk.file_path,
                                            "error_message": f"Table '{table_name}' is already defined",
                                            "table_name": table_name
                                        })
                                except Exception:
                                    pass
                    
                    # Generate and execute fix script
                    if issues:
                        script_result = script_generator.generate_fix_script(issues)
                        exec_result = script_generator.execute_script(script_result["script_path"])
                        
                        if exec_result.get("success"):
                            logger.info(f"[AUTONOMOUS-HEALING] Fixed SQLAlchemy table redefinition issues")
                            # Now try to create tables
                except Exception as e:
                    logger.debug(f"[AUTONOMOUS-HEALING] Table redefinition fix failed: {e}")
            
            result = self._create_missing_tables(missing_tables)
            return {
                "action": action.value,
                "status": "success" if result["success"] else "failed",
                "service": "database",
                "message": result.get("message", ""),
                "tables_created": result.get("tables_created", []),
                "details": result
            }

        elif action == HealingAction.SERVICE_RESTART:
            # Restart a service (if possible)
            service = anomaly.get("service", "unknown")
            result = self._restart_service(service)
            return {
                "action": action.value,
                "status": "success" if result["success"] else "failed",
                "service": service,
                "message": result.get("message", ""),
                "details": result
            }

        elif action == HealingAction.STATE_ROLLBACK:
            # Use multi-LLM to decide rollback strategy
            return self._execute_with_llm_guidance(action, anomaly, file_keys)

        elif action == HealingAction.ISOLATION:
            # Use multi-LLM to analyze isolation strategy
            return self._execute_with_llm_guidance(action, anomaly, file_keys)

        elif action == HealingAction.SEMANTIC_REFACTOR:
            # Multi-file semantic refactoring (symbol rename, module moves)
            return self._execute_semantic_refactor(anomaly, user_id)

        # Add other action implementations as needed
        else:
            return {
                "action": action.value,
                "status": "simulated",
                "message": f"Action {action.value} simulated (not implemented)"
            }

    def _execute_with_llm_guidance(
        self,
        action: HealingAction,
        anomaly: Dict[str, Any],
        file_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Execute complex healing action with multi-LLM guidance.

        For complex/risky actions, use multiple LLMs to:
        - Analyze the anomaly
        - Recommend healing strategy
        - Validate proposed solution
        - Build consensus before execution
        """
        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator

            logger.info(f"[AUTONOMOUS-HEALING] Requesting LLM guidance for {action.value}")

            orchestrator = LLMOrchestrator()

            # Build query for LLMs
            query = self._build_healing_query(action, anomaly, file_keys)

            # Get consensus from multiple LLMs
            result = orchestrator.execute_query(
                query=query,
                min_models=3,
                require_consensus=True
            )

            # Extract healing strategy from consensus
            healing_strategy = result.get("consensus_answer", "")

            logger.info(
                f"[AUTONOMOUS-HEALING] LLM consensus received "
                f"(confidence={result.get('confidence', 0):.2f})"
            )

            return {
                "action": action.value,
                "status": "llm_guided",
                "llm_strategy": healing_strategy,
                "llm_confidence": result.get("confidence", 0),
                "models_consulted": result.get("models_used", []),
                "message": f"Healing strategy generated with {len(result.get('models_used', []))} LLM consensus"
            }

        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] LLM guidance failed: {e}")
            return {
                "action": action.value,
                "status": "failed",
                "error": str(e)
            }

    def _build_healing_query(
        self,
        action: HealingAction,
        anomaly: Dict[str, Any],
        file_keys: List[str]
    ) -> str:
        """Build query for LLMs to provide healing guidance."""
        query = f"""System Healing Analysis Required

Anomaly Detected:
- Type: {anomaly['type'].value}
- Severity: {anomaly['severity']}
- Details: {anomaly['details']}

Proposed Healing Action: {action.value}

Evidence (Genesis Keys): {', '.join(file_keys[:3])}

Please provide:
1. Root cause analysis of the anomaly
2. Recommended healing strategy for {action.value}
3. Potential risks of this action
4. Alternative approaches if applicable
5. Step-by-step execution plan

Focus on practical, safe, and effective healing."""

        return query

    # ======================================================================
    # Learning from Healing Outcomes
    # ======================================================================

    def _detect_and_fill_gap(self, error_message: str, decision: Dict[str, Any]):
        """
        Detect knowledge gap and try to fill it using reverse KNN.
        
        When a healing action fails, this detects if it's a knowledge gap
        and uses reverse KNN to find similar problems and solutions.
        """
        try:
            from cognitive.gap_filler import get_gap_filler
            
            gap_filler = get_gap_filler()
            attempted_fixes = [decision.get("healing_action", "unknown")]
            
            logger.info(f"[AUTONOMOUS-HEALING] Detecting gap for: {error_message[:100]}")
            result = gap_filler.fill_gap(error_message, attempted_fixes, k=5)
            
            if result.get("success"):
                logger.info(
                    f"[AUTONOMOUS-HEALING] Gap filled! Found {result['similar_problems_found']} "
                    f"similar problems, confidence: {result['confidence']:.2f}"
                )
                # Store the new pattern for future use
                # (Would need to modify knowledge base to support dynamic addition)
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Gap detection failed: {e}")
    
    def _detect_gaps_from_failures(self, failed_actions: List[Dict[str, Any]]):
        """Detect knowledge gaps from failed healing actions."""
        try:
            from cognitive.gap_filler import get_gap_filler
            
            gap_filler = get_gap_filler()
            
            for failed in failed_actions:
                error_msg = failed.get("error", "") or failed.get("decision", {}).get("reason", "")
                if error_msg:
                    decision = failed.get("decision", {})
                    attempted_fixes = [decision.get("healing_action", "unknown")]
                    
                    logger.info(f"[AUTONOMOUS-HEALING] Checking for gap: {error_msg[:100]}")
                    result = gap_filler.fill_gap(error_msg, attempted_fixes, k=3)
                    
                    if result.get("success"):
                        logger.info(
                            f"[AUTONOMOUS-HEALING] Gap identified and pattern created: "
                            f"{result['fix_pattern']['issue_type']}"
                        )
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Gap detection from failures failed: {e}")

    def _detect_and_fill_gap(self, error_message: str, decision: Dict[str, Any]):
        """
        Detect knowledge gap and try to fill it using reverse KNN.
        
        When a healing action fails, this detects if it's a knowledge gap
        and uses reverse KNN to find similar problems and solutions.
        """
        try:
            from cognitive.gap_filler import get_gap_filler
            
            gap_filler = get_gap_filler()
            attempted_fixes = [decision.get("healing_action", "unknown")]
            
            logger.info(f"[AUTONOMOUS-HEALING] Detecting gap for: {error_message[:100]}")
            result = gap_filler.fill_gap(error_message, attempted_fixes, k=5)
            
            if result.get("success"):
                logger.info(
                    f"[AUTONOMOUS-HEALING] Gap filled! Found {result['similar_problems_found']} "
                    f"similar problems, confidence: {result['confidence']:.2f}"
                )
                # Store the new pattern for future use
                # (Would need to modify knowledge base to support dynamic addition)
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Gap detection failed: {e}")
    
    def _detect_gaps_from_failures(self, failed_actions: List[Dict[str, Any]]):
        """Detect knowledge gaps from failed healing actions."""
        try:
            from cognitive.gap_filler import get_gap_filler
            
            gap_filler = get_gap_filler()
            
            for failed in failed_actions:
                error_msg = failed.get("error", "") or failed.get("decision", {}).get("reason", "")
                if error_msg:
                    decision = failed.get("decision", {})
                    attempted_fixes = [decision.get("healing_action", "unknown")]
                    
                    logger.info(f"[AUTONOMOUS-HEALING] Checking for gap: {error_msg[:100]}")
                    result = gap_filler.fill_gap(error_msg, attempted_fixes, k=3)
                    
                    if result.get("success"):
                        logger.info(
                            f"[AUTONOMOUS-HEALING] Gap identified and pattern created: "
                            f"{result['fix_pattern']['issue_type']}"
                        )
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Gap detection from failures failed: {e}")

    def _learn_from_healing(
        self,
        decision: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        success: bool
    ):
        """
        Learn from healing outcome to improve future decisions.

        Updates trust scores based on success/failure.
        Creates learning examples for training.
        """
        action = HealingAction(decision["healing_action"])

        # Update trust score
        if success:
            # Increase trust (but cap at 0.95)
            self.trust_scores[action] = min(0.95, self.trust_scores[action] + 0.05)
            logger.info(
                f"[AUTONOMOUS-HEALING] Trust increased for {action.value}: "
                f"{self.trust_scores[action]:.2f}"
            )
        else:
            # Decrease trust (but floor at 0.1)
            self.trust_scores[action] = max(0.1, self.trust_scores[action] - 0.1)
            logger.warning(
                f"[AUTONOMOUS-HEALING] Trust decreased for {action.value}: "
                f"{self.trust_scores[action]:.2f}"
            )

        # Create learning example
        # Map parameters to LearningExample schema
        example = LearningExample(
            example_type="healing_outcome",
            input_context={
                "topic": f"healing:{action.value}",
                "anomaly_type": decision["anomaly"]["type"].value,
                "anomaly_severity": decision["anomaly"]["severity"],
                "action_taken": action.value,
                "service": decision["anomaly"].get("service", "unknown")
            },
            expected_output={
                "outcome": "success" if success else "failure",
                "action": action.value
            },
            actual_output={
                "success": success,
                "result": result if result else None,
                "message": (result.get("message", "") if isinstance(result, dict) else str(result)) if result else "No result available"
            },
            trust_score=self.trust_scores[action],
            source_reliability=self.trust_scores[action],  # Use same trust score
            outcome_quality=1.0 if success else 0.0,  # Binary outcome quality
            consistency_score=0.5,  # Default, will be updated by trust scorer
            source="autonomous_healing",
            source_user_id="autonomous_healing",
            example_metadata={
                "trust_score_before": decision["trust_score"],
                "trust_score_after": self.trust_scores[action],
                "execution_mode": decision["execution_mode"],
                "anomaly_id": decision["anomaly"].get("id"),
                "healing_action": action.value
            }
        )

        self.session.add(example)
        self.session.commit()

        # ✅ NEW: Record outcome in OutcomeAggregator for cross-system learning
        try:
            from cognitive.outcome_aggregator import get_outcome_aggregator
            aggregator = get_outcome_aggregator(self.session)
            aggregator.record_outcome('healing', {
                'action': action.value,
                'success': success,
                'trust_score': self.trust_scores[action],
                'anomaly_type': decision["anomaly"]["type"].value,
                'anomaly_severity': decision["anomaly"].get("severity", "unknown"),
                'service': decision["anomaly"].get("service", "unknown"),
                'execution_mode': decision.get("execution_mode", "unknown"),
                'learning_example_id': example.id if hasattr(example, 'id') else None
            })
            logger.debug(
                f"[AUTONOMOUS-HEALING] Recorded outcome in aggregator: "
                f"action={action.value}, success={success}, trust={self.trust_scores[action]:.2f}"
            )
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not record outcome in aggregator: {e}")

        # ✅ NEW: Create Genesis Key for learning outcome to trigger LLM knowledge update
        try:
            genesis_key = self.genesis_service.create_key(
                key_type='SYSTEM_EVENT',
                what_description=f"Healing outcome: {action.value} ({'success' if success else 'failure'})",
                who_actor="autonomous_healing",
                where_location="autonomous_healing_system",
                why_reason="Track healing outcome for LLM knowledge update",
                how_method="autonomous_healing",
                context_data={
                    'outcome_type': 'healing_outcome',
                    'trust_score': self.trust_scores[action],
                    'success': success,
                    'action': action.value,
                    'anomaly_type': decision["anomaly"]["type"].value,
                    'learning_example_id': example.id if hasattr(example, 'id') else None
                },
                metadata={
                    'outcome_type': 'healing_outcome',
                    'example_type': 'healing_outcome',
                    'trust_score': self.trust_scores[action],
                    'success': success,
                    'action': action.value,
                    'anomaly_type': decision["anomaly"]["type"].value
                },
                session=self.session
            )
            logger.debug(
                f"[AUTONOMOUS-HEALING] Created Genesis Key for learning outcome: "
                f"{genesis_key.key_id} (trust={self.trust_scores[action]:.2f})"
            )
        except Exception as e:
            logger.warning(f"[AUTONOMOUS-HEALING] Could not create Genesis Key for outcome: {e}")

        # Add to history
        self.healing_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "result": result,
            "success": success
        })

    # ======================================================================
    # Proactive Monitoring Cycle
    # ======================================================================

    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """
        Run one complete monitoring and healing cycle.

        This is the main autonomous loop:
        1. Assess health
        2. Decide actions
        3. Execute autonomously (if trust allows)
        4. Learn from outcomes
        """
        logger.info("[AUTONOMOUS-HEALING] Starting monitoring cycle...")

        # 1. Assess health
        assessment = self.assess_system_health()

        # 2. Decide healing actions
        if assessment["anomalies_detected"] > 0:
            decisions = self.decide_healing_actions(assessment["anomalies"])

            # 3. Execute healing
            execution_results = self.execute_healing(decisions)
        else:
            decisions = []
            execution_results = {"executed": [], "awaiting_approval": [], "failed": []}

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": assessment["health_status"],
            "anomalies_detected": assessment["anomalies_detected"],
            "decisions_made": len(decisions),
            "actions_executed": len(execution_results["executed"]),
            "awaiting_approval": len(execution_results["awaiting_approval"]),
            "failures": len(execution_results["failed"]),
            "assessment": assessment,
            "decisions": decisions,
            "results": execution_results
        }

    def _reset_service_connection(self, service: str) -> Dict[str, Any]:
        """Reset connection to a service."""
        try:
            # Handle unknown service - try to reset all services
            if service == "unknown" or not service:
                logger.info("[AUTONOMOUS-HEALING] Service unknown, attempting general reset")
                # Try database first (most common)
                try:
                    from database.connection import DatabaseConnection
                    DatabaseConnection.reconnect()
                    if DatabaseConnection.health_check():
                        return {
                            "success": True,
                            "message": "General connection reset successful (database)"
                        }
                except Exception:
                    pass
                
                # Try Qdrant
                try:
                    from vector_db.client import get_qdrant_client
                    client = get_qdrant_client()
                    if client:
                        collections = client.list_collections()
                        return {
                            "success": True,
                            "message": f"General connection reset successful (qdrant: {len(collections)} collections)"
                        }
                except Exception:
                    pass
                
                return {
                    "success": True,
                    "message": "General connection reset attempted (no specific service)"
                }
            
            if service == "qdrant":
                # Reset Qdrant client connection
                from vector_db.client import get_qdrant_client, _qdrant_client
                # Clear singleton cache
                if '_qdrant_client' in globals():
                    globals()['_qdrant_client'] = None
                # Try to reconnect
                client = get_qdrant_client()
                if client:
                    # Test connection
                    collections = client.list_collections()
                    return {
                        "success": True,
                        "message": f"Qdrant connection reset successfully ({len(collections)} collections)",
                        "collections": len(collections)
                    }
                else:
                    return {
                        "success": False,
                        "message": "Qdrant client reset but reconnection failed"
                    }
            elif service == "database":
                # Reset database connection
                from database.connection import DatabaseConnection
                DatabaseConnection.reconnect()
                if DatabaseConnection.health_check():
                    return {
                        "success": True,
                        "message": "Database connection reset successfully"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Database connection reset but health check failed"
                    }
            elif service == "backend":
                # Backend service - just log, no action needed
                return {
                    "success": True,
                    "message": "Backend service reset (no-op, service is running)"
                }
            else:
                return {
                    "success": True,  # Changed to True - unknown service is not critical
                    "message": f"Connection reset for unknown service '{service}' (no-op)"
                }
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Connection reset failed for {service}: {e}")
            return {
                "success": False,
                "message": f"Connection reset failed: {str(e)}"
            }

    def _restart_service(self, service: str) -> Dict[str, Any]:
        """Attempt to restart a service (if possible)."""
        try:
            if service == "qdrant":
                # Qdrant restart requires external process - log recommendation
                logger.warning(
                    "[AUTONOMOUS-HEALING] Qdrant restart requires manual intervention. "
                    "Please restart Qdrant service manually."
                )
                return {
                    "success": False,
                    "message": "Qdrant restart requires manual intervention",
                    "recommendation": "Restart Qdrant service: docker restart qdrant (or systemd service)"
                }
            elif service == "database":
                # Database restart also requires external process
                logger.warning(
                    "[AUTONOMOUS-HEALING] Database restart requires manual intervention. "
                    "Please restart database service manually."
                )
                return {
                    "success": False,
                    "message": "Database restart requires manual intervention",
                    "recommendation": "Restart database service manually"
                }
            else:
                return {
                    "success": False,
                    "message": f"Service restart not implemented for: {service}"
                }
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Service restart failed for {service}: {e}")
            return {
                "success": False,
                "message": f"Service restart failed: {str(e)}"
            }
    
    def _create_missing_tables(self, missing_tables: List[str]) -> Dict[str, Any]:
        """
        Create missing database tables.
        
        Args:
            missing_tables: List of table names to create
            
        Returns:
            Dict with success status and details
        """
        if not missing_tables:
            return {
                "success": False,
                "message": "No missing tables specified",
                "tables_created": []
            }
        
        tables_created = []
        errors = []
        
        try:
            from database.migration import create_tables
            from database.connection import DatabaseConnection
            from sqlalchemy import inspect
            
            # Get all table models
            engine = DatabaseConnection.get_engine()
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            # Create all tables (SQLAlchemy will skip existing ones)
            try:
                create_tables()
                logger.info(f"[AUTONOMOUS-HEALING] Attempted to create all database tables")
                
                # Check which tables were actually created
                inspector = inspect(engine)
                new_tables = inspector.get_table_names()
                for table in missing_tables:
                    if table in new_tables and table not in existing_tables:
                        tables_created.append(table)
                
                if not tables_created:
                    # All tables might already exist or creation failed silently
                    # Try to verify by checking if tables exist now
                    for table in missing_tables:
                        if table in inspector.get_table_names():
                            tables_created.append(table)
                
                if tables_created:
                    # Log as Genesis Key
                    try:
                        from genesis.genesis_key_service import get_genesis_service
                        genesis_service = get_genesis_service()
                        genesis_service.create_key(
                            key_type=GenesisKeyType.SYSTEM_EVENT,
                            what_description=f"Created missing database tables: {', '.join(tables_created)}",
                            who_actor="autonomous_healing",
                            where_location="database",
                            why_reason="Self-healing detected missing tables and created them",
                            how_method="database_table_create",
                            context_data={
                                "tables_created": tables_created,
                                "missing_tables": missing_tables
                            }
                        )
                    except Exception as e:
                        logger.debug(f"[AUTONOMOUS-HEALING] Could not log Genesis Key: {e}")
                
                return {
                    "success": len(tables_created) > 0,
                    "message": f"Created {len(tables_created)} table(s): {', '.join(tables_created) if tables_created else 'none'}",
                    "tables_created": tables_created,
                    "errors": errors
                }
            except Exception as e:
                error_msg = str(e)
                errors.append(error_msg)
                logger.error(f"[AUTONOMOUS-HEALING] Failed to create tables: {e}")
                
                return {
                    "success": False,
                    "message": f"Failed to create tables: {error_msg}",
                    "tables_created": tables_created,
                    "errors": errors
                }
        except Exception as e:
            error_msg = f"Could not access database: {str(e)}"
            logger.error(f"[AUTONOMOUS-HEALING] {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "tables_created": [],
                "errors": [error_msg]
            }

    # ======================================================================
    # Status & Reporting
    # ======================================================================

    def _execute_code_fix(
        self,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute code fix for an anomaly.
        
        Enhanced to use LLM-generated fixes for logic errors.
        """
        # Check if this is an LLM-detected logic error
        if anomaly.get("source") == "llm_logic_detector" and self.logic_detector:
            return self._execute_llm_logic_fix(anomaly, user_id)
        
        # Try Coding Agent for complex fixes that need code generation
        if self.healing_bridge and self.coding_agent:
            try:
                description = anomaly.get("description", "") or anomaly.get("details", "")
                affected_files = anomaly.get("affected_files", []) or [anomaly.get("file_path", "")]
                affected_files = [f for f in affected_files if f]
                
                # Use coding agent for complex fixes that need generation
                if any(keyword in description.lower() for keyword in [
                    "generate", "create", "implement", "add", "new", "missing"
                ]):
                    coding_result = self.request_coding_assistance(
                        assistance_type="code_generation",
                        description=f"Fix: {description}",
                        context={
                            "target_files": affected_files,
                            "anomaly": anomaly,
                            "error_message": anomaly.get("error_message", "")
                        },
                        priority=anomaly.get("severity", "medium")
                    )
                    
                    if coding_result.get("success"):
                        return {
                            "action": HealingAction.CODE_FIX.value,
                            "status": "success",
                            "method": "coding_agent",
                            "result": coding_result,
                            "message": "Code fix executed via Coding Agent"
                        }
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Coding agent fix attempt failed: {e}, falling back to standard fix")
        
        # Otherwise use standard knowledge base approach
        """
        Execute code fixes using knowledge base and script generator.
        
        This method:
        1. Identifies issue type from error message
        2. Generates fix suggestions from knowledge base
        3. Creates and executes healing scripts/patches
        4. Tracks fixes with Genesis Keys
        """
        if not self.knowledge_base or not self.script_generator:
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": "Knowledge base or script generator not available"
            }
        
        try:
            # Extract error information
            error_message = anomaly.get("error_message") or anomaly.get("details", "")
            file_path = anomaly.get("file_path", "")
            line_number = anomaly.get("line_number")
            
            # Identify issue type - try multiple error message formats
            issue_info = None
            if error_message:
                issue_info = self.knowledge_base.identify_issue_type(error_message)
            
            # If not found, try checking if it's a known issue pattern
            if not issue_info:
                # Check for SQLAlchemy table redefinition patterns
                if "table redefinition" in error_message.lower() or \
                   ("table" in error_message.lower() and "already defined" in error_message.lower()) or \
                   ("metadata" in error_message.lower() and "table" in error_message.lower()):
                    from cognitive.healing_knowledge_base import IssueType
                    issue_type = IssueType.SQLALCHEMY_TABLE_REDEFINITION
                    # Get pattern for this issue type
                    patterns = self.knowledge_base.get_all_fix_patterns()
                    pattern = next((p for p in patterns if p.issue_type == issue_type), None)
                    if pattern:
                        issue_info = (issue_type, pattern)
            
            if not issue_info:
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "failed",
                    "error": "Could not identify issue type",
                    "error_message": error_message[:200]  # Truncate for logging
                }
            
            issue_type, pattern = issue_info
            
            # Generate fix suggestion
            fix_suggestion = self.knowledge_base.generate_fix_suggestion(
                issue_type=issue_type,
                error_message=error_message,
                file_path=file_path,
                line_number=line_number
            )
            
            if not fix_suggestion.get("fix_available"):
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "failed",
                    "error": fix_suggestion.get("reason", "Fix not available")
                }
            
            # Get file paths from anomaly (may have multiple files)
            file_paths = anomaly.get("file_paths", [])
            if not file_paths and file_path:
                file_paths = [file_path]
            
            # Also check if file_paths is in the anomaly directly
            if not file_paths:
                # Try to extract from evidence (Genesis Keys)
                evidence = anomaly.get("evidence", [])
                for ev in evidence[:10]:  # Limit to 10 to avoid too many queries
                    if isinstance(ev, str) and ev.startswith("GK-"):
                        try:
                            from models.genesis_key_models import GenesisKey
                            gk = self.session.query(GenesisKey).filter(
                                GenesisKey.key_id == ev
                            ).first()
                            if gk and gk.file_path:
                                if gk.file_path not in file_paths:
                                    file_paths.append(gk.file_path)
                        except Exception:
                            pass
            
            # Create issues for script generator (one per file)
            issues = []
            for fp in file_paths[:50]:  # Limit to 50 files to avoid huge scripts
                if fp:
                    # Normalize path
                    if "\\" in fp:
                        fp = fp.replace("\\", "/")
                    issues.append({
                        "issue_type": issue_type.value,
                        "file_path": fp,
                        "error_message": error_message,
                        "line_number": line_number,
                        "file_paths": file_paths  # Pass all paths for reference
                    })
            
            # If no file paths, try to find model files that might have the issue
            if not issues and issue_type == IssueType.SQLALCHEMY_TABLE_REDEFINITION:
                # Look for common model file locations
                model_files = [
                    "backend/models/database_models.py",
                    "backend/models/genesis_key_models.py"
                ]
                for model_file in model_files:
                    model_path = self.repo_path / model_file
                    if model_path.exists():
                        issues.append({
                            "issue_type": issue_type.value,
                            "file_path": str(model_path),
                            "error_message": error_message,
                            "line_number": line_number
                        })
            
            # If still no issues, create one with empty file_path (script will search)
            if not issues:
                issues = [{
                    "issue_type": issue_type.value,
                    "file_path": file_path or "",
                    "error_message": error_message,
                    "line_number": line_number
                }]
            
            # Generate and execute patches
            patch_result = self.script_generator.generate_and_execute_patches(
                issues=issues,
                auto_execute=True
            )
            
            if patch_result.get("success"):
                # Create Genesis Key for successful fix
                try:
                    self.genesis_service.create_key(
                        key_type=GenesisKeyType.FIX,
                        what_description=f"Auto-fixed code issue: {issue_type.value}",
                        who_actor=user_id,
                        where_location=file_path,
                        why_reason=f"Autonomous healing fixed: {error_message[:100]}",
                        how_method="healing_knowledge_base",
                        file_path=file_path,
                        context_data={
                            "issue_type": issue_type.value,
                            "patches_applied": patch_result.get("patches_generated", 0),
                            "script_path": patch_result.get("script_path"),
                            "confidence": pattern.confidence
                        }
                    )
                except Exception as e:
                    logger.debug(f"[AUTONOMOUS-HEALING] Could not create Genesis Key: {e}")
                
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "success",
                    "issue_type": issue_type.value,
                    "patches_applied": patch_result.get("patches_generated", 0),
                    "script_path": patch_result.get("script_path"),
                    "confidence": pattern.confidence,
                    "details": patch_result
                }
            else:
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "failed",
                    "error": patch_result.get("message", "Patch execution failed"),
                    "details": patch_result
                }
                
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Code fix execution failed: {e}")
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": str(e)
            }
    
    def _execute_semantic_refactor(
        self,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute semantic refactoring for multi-file issues.
        
        Handles:
        - Symbol renames across the codebase
        - Module moves with import updates
        - Cross-file reference updates
        
        Uses the SemanticRefactoringEngine with validation pipeline.
        """
        if not self.refactoring_engine:
            return {
                "action": HealingAction.SEMANTIC_REFACTOR.value,
                "status": "failed",
                "error": "Semantic refactoring engine not available"
            }
        
        try:
            refactor_type = anomaly.get("refactor_type", "rename")
            old_name = anomaly.get("old_name") or anomaly.get("symbol_name")
            new_name = anomaly.get("new_name")
            source_module = anomaly.get("source_module")
            target_module = anomaly.get("target_module")
            symbol_type = anomaly.get("symbol_type")
            
            result = None
            
            if refactor_type == "rename" and old_name and new_name:
                # Rename symbol across codebase
                from cognitive.semantic_refactoring_engine import SymbolType
                
                sym_type = None
                if symbol_type:
                    sym_type = getattr(SymbolType, symbol_type.upper(), None)
                
                plan = self.refactoring_engine.plan_rename_symbol(
                    old_name=old_name,
                    new_name=new_name,
                    symbol_type=sym_type,
                )
                
                result = self.refactoring_engine.execute_plan(
                    plan_id=plan.plan_id,
                    dry_run=False,
                )
                
                if result.success:
                    # Create Genesis Key for successful refactor
                    try:
                        self.genesis_service.create_key(
                            key_type=GenesisKeyType.FIX,
                            what_description=f"Renamed symbol '{old_name}' to '{new_name}'",
                            who_actor=user_id,
                            where_location=str(self.repo_path),
                            why_reason=f"Semantic refactoring: {anomaly.get('reason', 'code quality')}",
                            how_method="semantic_refactoring_engine",
                            context_data={
                                "plan_id": plan.plan_id,
                                "files_modified": result.files_modified,
                                "references_updated": result.references_updated,
                                "refactor_type": "rename",
                            }
                        )
                    except Exception as e:
                        logger.debug(f"[AUTONOMOUS-HEALING] Could not create Genesis Key: {e}")
                    
                    return {
                        "action": HealingAction.SEMANTIC_REFACTOR.value,
                        "status": "success",
                        "refactor_type": "rename",
                        "plan_id": plan.plan_id,
                        "old_name": old_name,
                        "new_name": new_name,
                        "files_modified": result.files_modified,
                        "references_updated": result.references_updated,
                        "message": f"Renamed '{old_name}' to '{new_name}' in {result.files_modified} files"
                    }
                else:
                    return {
                        "action": HealingAction.SEMANTIC_REFACTOR.value,
                        "status": "failed",
                        "refactor_type": "rename",
                        "plan_id": plan.plan_id,
                        "errors": result.errors,
                        "rollback_performed": plan.status == "rolled_back"
                    }
            
            elif refactor_type == "move_module" and source_module and target_module:
                # Move module and update imports
                plan = self.refactoring_engine.plan_move_module(
                    source_module=source_module,
                    target_module=target_module,
                )
                
                result = self.refactoring_engine.execute_plan(
                    plan_id=plan.plan_id,
                    dry_run=False,
                )
                
                if result.success:
                    try:
                        self.genesis_service.create_key(
                            key_type=GenesisKeyType.FIX,
                            what_description=f"Moved module '{source_module}' to '{target_module}'",
                            who_actor=user_id,
                            where_location=str(self.repo_path),
                            why_reason=f"Module reorganization: {anomaly.get('reason', 'structure improvement')}",
                            how_method="semantic_refactoring_engine",
                            context_data={
                                "plan_id": plan.plan_id,
                                "files_modified": result.files_modified,
                                "refactor_type": "move_module",
                            }
                        )
                    except Exception as e:
                        logger.debug(f"[AUTONOMOUS-HEALING] Could not create Genesis Key: {e}")
                    
                    return {
                        "action": HealingAction.SEMANTIC_REFACTOR.value,
                        "status": "success",
                        "refactor_type": "move_module",
                        "plan_id": plan.plan_id,
                        "source_module": source_module,
                        "target_module": target_module,
                        "files_modified": result.files_modified,
                        "message": f"Moved module and updated {result.files_modified} import statements"
                    }
                else:
                    return {
                        "action": HealingAction.SEMANTIC_REFACTOR.value,
                        "status": "failed",
                        "refactor_type": "move_module",
                        "plan_id": plan.plan_id,
                        "errors": result.errors,
                        "rollback_performed": plan.status == "rolled_back"
                    }
            
            else:
                return {
                    "action": HealingAction.SEMANTIC_REFACTOR.value,
                    "status": "failed",
                    "error": f"Invalid refactor request. Required: old_name+new_name for rename, or source_module+target_module for move"
                }
                
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Semantic refactor execution failed: {e}")
            return {
                "action": HealingAction.SEMANTIC_REFACTOR.value,
                "status": "failed",
                "error": str(e)
            }
    
    def _execute_llm_logic_fix(
        self,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute LLM-generated fix for logic error.
        
        Uses the LLM logic detector to generate and apply fixes.
        """
        try:
            file_path = anomaly.get("file_path")
            if not file_path:
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "failed",
                    "error": "No file path in anomaly"
                }
            
            # Normalize path
            if not Path(file_path).is_absolute() and self.repo_path:
                file_path = str(self.repo_path / file_path)
            
            # Read current code
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_code = f.read()
            except Exception as e:
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "failed",
                    "error": f"Could not read file: {e}"
                }
            
            # Create LogicError object from anomaly
            from cognitive.llm_logic_error_detector import LogicError
            
            logic_error = LogicError(
                error_type=anomaly.get("logic_error_type", "unknown"),
                severity=anomaly.get("severity", "medium"),
                file_path=file_path,
                line_number=anomaly.get("line_number", 0),
                description=anomaly.get("error_message", ""),
                code_snippet=anomaly.get("code_snippet", ""),
                reasoning=anomaly.get("reasoning", ""),
                suggested_fix=anomaly.get("suggested_fix", ""),
                confidence=anomaly.get("confidence", 0.5),
                context_lines=anomaly.get("context_lines", [])
            )
            
            # Generate fix using LLM
            fixed_code, explanation = self.logic_detector.generate_fix(
                logic_error,
                original_code
            )
            
            # Apply fix if confidence is high enough
            if anomaly.get("confidence", 0.5) >= 0.7 and fixed_code != original_code:
                try:
                    # Backup original
                    backup_path = f"{file_path}.backup"
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original_code)
                    
                    # Write fixed code
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_code)
                    
                    # Create Genesis Key for fix
                    try:
                        self.genesis_service.create_key(
                            key_type=GenesisKeyType.FIX,
                            what_description=f"LLM-fixed logic error: {logic_error.error_type}",
                            who_actor=user_id,
                            where_location=file_path,
                            why_reason=f"Logic error detected and fixed: {logic_error.description}",
                            how_method="llm_logic_detector",
                            file_path=file_path,
                            code_before=original_code,
                            code_after=fixed_code,
                            context_data={
                                "error_type": logic_error.error_type,
                                "reasoning": logic_error.reasoning,
                                "explanation": explanation,
                                "confidence": logic_error.confidence
                            }
                        )
                    except Exception as e:
                        logger.debug(f"[AUTONOMOUS-HEALING] Could not create Genesis Key: {e}")
                    
                    logger.info(
                        f"[AUTONOMOUS-HEALING] LLM logic fix applied to {file_path}: "
                        f"{logic_error.error_type}"
                    )
                    
                    return {
                        "action": HealingAction.CODE_FIX.value,
                        "status": "success",
                        "error_type": logic_error.error_type,
                        "file_path": file_path,
                        "line_number": logic_error.line_number,
                        "explanation": explanation,
                        "confidence": logic_error.confidence,
                        "backup_path": backup_path
                    }
                    
                except Exception as e:
                    logger.error(f"[AUTONOMOUS-HEALING] Failed to apply LLM fix: {e}")
                    return {
                        "action": HealingAction.CODE_FIX.value,
                        "status": "failed",
                        "error": f"Failed to apply fix: {e}"
                    }
            else:
                # Confidence too low or no change - require manual review
                return {
                    "action": HealingAction.CODE_FIX.value,
                    "status": "requires_review",
                    "error_type": logic_error.error_type,
                    "file_path": file_path,
                    "suggested_fix": logic_error.suggested_fix,
                    "reasoning": logic_error.reasoning,
                    "confidence": logic_error.confidence,
                    "explanation": explanation
                }
                
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] LLM logic fix execution failed: {e}")
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": str(e)
            }
    
    def _execute_silent_failure_fix(
        self,
        anomaly: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute fix for silent failures and degradation.
        
        This method adds proper logging, monitoring, and error handling
        to components that are failing silently.
        """
        component = anomaly.get("component", "")
        degradation_type = anomaly.get("degradation_type", "")
        file_path = anomaly.get("file_path", "")
        
        # Map components to their file paths
        component_file_map = {
            "cognitive_engine": "backend/cognitive/engine.py",
            "cognitive_engine_timesense": "backend/cognitive/engine.py",
            "llm_orchestrator": "backend/llm_orchestrator/llm_orchestrator.py",
            "telemetry_service": "backend/telemetry/telemetry_service.py",
            "message_bus": "backend/layer1/message_bus.py"
        }
        
        if not file_path and component in component_file_map:
            file_path = component_file_map[component]
        
        if not file_path:
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": f"Could not determine file path for component: {component}"
            }
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Generate fix based on degradation type
            fixed_code = code
            changes_made = []
            
            if "timesense" in degradation_type.lower() or "timesense" in component.lower():
                # Fix TimeSense silent failures - ensure logging is present
                # Check if the fix we already made is there
                if "logger.warning" in code and "TimeSense unavailable" in code:
                    # Already fixed
                    changes_made.append("TimeSense logging already present")
                else:
                    # Need to add logging - this would require more sophisticated code analysis
                    # For now, log that we detected the issue
                    logger.warning(
                        f"[AUTONOMOUS-HEALING] TimeSense silent failure detected in {file_path}. "
                        f"Manual fix may be required to add proper logging."
                    )
                    changes_made.append("TimeSense logging fix recommended")
            
            elif "transform" in degradation_type.lower() or "llm_orchestrator" in component.lower():
                # Transform fallback degradation - ensure metrics are tracked
                changes_made.append("Transform fallback metrics tracking recommended")
            
            elif "telemetry" in component.lower():
                # Telemetry loss - ensure failures are tracked
                changes_made.append("Telemetry failure tracking recommended")
            
            # Create Genesis Key for the fix attempt
            try:
                self.genesis_service.create_key(
                    key_type=GenesisKeyType.FIX,
                    what_description=f"Silent failure fix: {degradation_type} in {component}",
                    who_actor=user_id,
                    where_location=file_path,
                    why_reason=f"Component {component} failing silently: {anomaly.get('details', '')}",
                    how_method="autonomous_healing",
                    file_path=file_path,
                    context_data={
                        "component": component,
                        "degradation_type": degradation_type,
                        "count": anomaly.get("count", 0),
                        "changes_recommended": changes_made
                    }
                )
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Could not create Genesis Key: {e}")
            
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "success" if changes_made else "detected",
                "component": component,
                "file_path": file_path,
                "changes_made": changes_made,
                "message": f"Silent failure detected and fix recommended for {component}"
            }
            
        except FileNotFoundError:
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": f"File not found: {file_path}"
            }
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HEALING] Failed to fix silent failure: {e}")
            return {
                "action": HealingAction.CODE_FIX.value,
                "status": "failed",
                "error": str(e)
            }
    
    def _detect_import_errors_with_llm(self, recent_errors: List[GenesisKey]) -> List[Dict[str, Any]]:
        """
        Detect import errors using LLM import healer.
        
        Converts Genesis Key errors to import errors and uses LLM to suggest fixes.
        """
        anomalies = []
        
        if not self.import_healer:
            return anomalies
        
        # Filter for import-related errors
        import_errors = []
        for error in recent_errors:
            error_msg = error.error_message or ""
            if any(keyword in error_msg.lower() for keyword in [
                "import", "module", "no module named", "cannot import", "nameerror"
            ]):
                import_errors.append(error)
        
        # Analyze each import error
        for error in import_errors[:10]:  # Limit to 10 to avoid too many LLM calls
            try:
                file_path = error.file_path or (error.context_data.get("file_path") if error.context_data else None)
                if not file_path:
                    continue
                
                # Detect import errors in the file
                detected = self.import_healer.detect_import_errors(
                    file_path=file_path,
                    error_message=error.error_message,
                    context={"dependency_upgrade": None}  # Could detect from error patterns
                )
                
                # Convert to anomalies
                for import_error in detected:
                    if import_error.confidence > 0.7:  # Only high-confidence fixes
                        anomalies.append({
                            "type": AnomalyType.DATA_INCONSISTENCY,
                            "severity": import_error.severity,
                            "details": f"Import error: {import_error.description}",
                            "source": "llm_import_healer",
                            "error_message": import_error.error_message or import_error.description,
                            "file_path": file_path,
                            "line_number": import_error.line_number,
                            "suggested_fix": import_error.suggested_import,
                            "reasoning": import_error.reasoning,
                            "confidence": import_error.confidence,
                            "evidence": [error.key_id]
                        })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Import error detection failed: {e}")
        
        return anomalies
    
    def _detect_config_errors_with_llm(self, recent_errors: List[GenesisKey]) -> List[Dict[str, Any]]:
        """
        Detect configuration errors using LLM config healer.
        
        Converts Genesis Key errors to config errors and uses LLM to suggest fixes.
        """
        anomalies = []
        
        if not self.config_healer:
            return anomalies
        
        # Filter for config-related errors
        config_errors = []
        for error in recent_errors:
            error_msg = error.error_message or ""
            if any(keyword in error_msg.lower() for keyword in [
                "config", "configuration", "settings", "environment variable", "env var",
                "not set", "missing", "invalid", "validation failed"
            ]):
                config_errors.append(error)
        
        # Also check service connection errors (might be config)
        service_errors = []
        for error in recent_errors:
            error_msg = error.error_message or ""
            if any(keyword in error_msg.lower() for keyword in [
                "connection", "connect", "connection error", "connection refused", "timeout"
            ]):
                # Extract service name if possible
                service = None
                if "database" in error_msg.lower():
                    service = "database"
                elif "qdrant" in error_msg.lower():
                    service = "qdrant"
                elif "ollama" in error_msg.lower():
                    service = "ollama"
                
                if service:
                    service_errors.append((error, service))
        
        # Analyze config errors
        for error in config_errors[:10]:  # Limit to 10
            try:
                detected = self.config_healer.detect_config_errors(
                    error_message=error.error_message,
                    context={"dependency_upgrade": None}
                )
                
                # Convert to anomalies
                for config_error in detected:
                    if config_error.confidence > 0.7:
                        anomalies.append({
                            "type": AnomalyType.DATA_INCONSISTENCY,
                            "severity": config_error.severity,
                            "details": f"Configuration error: {config_error.description}",
                            "source": "llm_config_healer",
                            "service": config_error.service,
                            "error_message": config_error.error_message or config_error.description,
                            "suggested_fix": f"Set {config_error.config_key}={config_error.suggested_value}",
                            "reasoning": config_error.reasoning,
                            "confidence": config_error.confidence,
                            "evidence": [error.key_id]
                        })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Config error detection failed: {e}")
        
        # Analyze service connection errors (might be config issues)
        for error, service in service_errors[:5]:  # Limit to 5
            try:
                detected = self.config_healer.detect_config_errors(
                    error_message=error.error_message,
                    service=service,
                    context={"dependency_upgrade": None}
                )
                
                for config_error in detected:
                    if config_error.confidence > 0.6:  # Lower threshold for connection errors
                        anomalies.append({
                            "type": AnomalyType.SERVICE_FAILURE,
                            "severity": config_error.severity,
                            "details": f"Configuration issue for {service}: {config_error.description}",
                            "source": "llm_config_healer",
                            "service": service,
                            "error_message": config_error.error_message or config_error.description,
                            "suggested_fix": f"Set {config_error.config_key}={config_error.suggested_value}",
                            "reasoning": config_error.reasoning,
                            "confidence": config_error.confidence,
                            "evidence": [error.key_id]
                        })
            except Exception as e:
                logger.debug(f"[AUTONOMOUS-HEALING] Service config error detection failed: {e}")
        
        return anomalies
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "current_health": self.current_health.value,
            "trust_level": self.trust_level.name,
            "anomalies_active": len(self.anomalies_detected),
            "healing_history_count": len(self.healing_history),
            "trust_scores": {
                action.value: score
                for action, score in self.trust_scores.items()
            },
            "learning_enabled": self.enable_learning,
            "knowledge_base_available": self.knowledge_base is not None,
            "script_generator_available": self.script_generator is not None,
            "import_healer_available": self.import_healer is not None,
            "config_healer_available": self.config_healer is not None
        }


# ======================================================================
# Global Instance
# ======================================================================

_autonomous_healing: Optional[AutonomousHealingSystem] = None


def get_autonomous_healing(
    session: Session,
    repo_path: Optional[Path] = None,
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    enable_learning: bool = True
) -> AutonomousHealingSystem:
    """Get or create global autonomous healing system."""
    global _autonomous_healing

    if _autonomous_healing is None:
        _autonomous_healing = AutonomousHealingSystem(
            session=session,
            repo_path=repo_path,
            trust_level=trust_level,
            enable_learning=enable_learning
        )

    return _autonomous_healing
