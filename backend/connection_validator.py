"""
Connection Status Validator
============================
Comprehensive validation of ALL system connections.

Maps every connection in the system, checks whether it's actually connected,
and validates that each connection is doing its job properly.

Connection Categories:
1. Infrastructure: Database, Qdrant, LLM Provider, Embedding Model
2. External APIs: SerpAPI, Kimi, Opus
3. Layer 1 Connectors: Message bus component registrations
4. Background Services: Diagnostic engine, autonomous loop, file watcher, etc.
5. WebSocket: Real-time client connections
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionCategory(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    EXTERNAL_API = "external_api"
    LAYER1_CONNECTOR = "layer1_connector"
    BACKGROUND_SERVICE = "background_service"
    WEBSOCKET = "websocket"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"


class ValidationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


@dataclass
class ActionValidation:
    """Result of validating a single action/capability of a connection."""
    action_name: str
    description: str
    result: ValidationResult
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ConnectionReport:
    """Full report for a single connection."""
    name: str
    category: ConnectionCategory
    status: ConnectionStatus
    connected: bool
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    action_validations: List[ActionValidation] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def actions_passing(self) -> int:
        return sum(1 for a in self.action_validations if a.result == ValidationResult.PASS)

    @property
    def actions_failing(self) -> int:
        return sum(1 for a in self.action_validations if a.result == ValidationResult.FAIL)

    @property
    def actions_total(self) -> int:
        return len(self.action_validations)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["actions_passing"] = self.actions_passing
        d["actions_failing"] = self.actions_failing
        d["actions_total"] = self.actions_total
        return d


@dataclass
class SystemConnectionReport:
    """Full system-wide connection validation report."""
    status: str  # all_connected, partial, critical
    timestamp: str
    total_connections: int
    connected_count: int
    disconnected_count: int
    degraded_count: int
    connections: List[ConnectionReport] = field(default_factory=list)
    total_actions_validated: int = 0
    total_actions_passing: int = 0
    total_actions_failing: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "total_connections": self.total_connections,
            "connected_count": self.connected_count,
            "disconnected_count": self.disconnected_count,
            "degraded_count": self.degraded_count,
            "total_actions_validated": self.total_actions_validated,
            "total_actions_passing": self.total_actions_passing,
            "total_actions_failing": self.total_actions_failing,
            "connections": [c.to_dict() for c in self.connections],
            "categories": self._category_summary(),
        }

    def _category_summary(self) -> Dict[str, Dict[str, int]]:
        summary = {}
        for conn in self.connections:
            cat = conn.category.value
            if cat not in summary:
                summary[cat] = {"total": 0, "connected": 0, "disconnected": 0, "degraded": 0}
            summary[cat]["total"] += 1
            if conn.connected:
                summary[cat]["connected"] += 1
            elif conn.status == ConnectionStatus.DEGRADED:
                summary[cat]["degraded"] += 1
            else:
                summary[cat]["disconnected"] += 1
        return summary


def _timed(fn):
    """Execute fn and return (result, latency_ms)."""
    start = time.time()
    try:
        result = fn()
        latency = (time.time() - start) * 1000
        return result, round(latency, 2)
    except Exception as e:
        latency = (time.time() - start) * 1000
        return e, round(latency, 2)


# ---------------------------------------------------------------------------
# Infrastructure validators
# ---------------------------------------------------------------------------

def validate_database() -> ConnectionReport:
    """Validate database connection and actions."""
    report = ConnectionReport(
        name="database",
        category=ConnectionCategory.INFRASTRUCTURE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig

        result, latency = _timed(DatabaseConnection.health_check)
        report.latency_ms = latency

        if isinstance(result, Exception):
            report.status = ConnectionStatus.DISCONNECTED
            report.message = str(result)
            report.action_validations.append(ActionValidation(
                action_name="health_check",
                description="Execute SELECT 1 against database",
                result=ValidationResult.FAIL,
                latency_ms=latency,
                message=str(result),
            ))
            return report

        if result:
            report.status = ConnectionStatus.CONNECTED
            report.connected = True

            report.action_validations.append(ActionValidation(
                action_name="health_check",
                description="Execute SELECT 1 against database",
                result=ValidationResult.PASS,
                latency_ms=latency,
            ))

            # Validate session factory
            try:
                from database.session import SessionLocal
                from sqlalchemy import text
                sess_result, sess_latency = _timed(lambda: _test_session())
                if isinstance(sess_result, Exception):
                    report.action_validations.append(ActionValidation(
                        action_name="session_factory",
                        description="Create session and execute query",
                        result=ValidationResult.FAIL,
                        latency_ms=sess_latency,
                        message=str(sess_result),
                    ))
                else:
                    report.action_validations.append(ActionValidation(
                        action_name="session_factory",
                        description="Create session and execute query",
                        result=ValidationResult.PASS,
                        latency_ms=sess_latency,
                    ))
            except Exception as e:
                report.action_validations.append(ActionValidation(
                    action_name="session_factory",
                    description="Create session and execute query",
                    result=ValidationResult.FAIL,
                    message=str(e),
                ))

            # Validate table existence
            try:
                tables_result, tables_latency = _timed(lambda: _check_tables())
                if isinstance(tables_result, Exception):
                    report.action_validations.append(ActionValidation(
                        action_name="tables_exist",
                        description="Verify core database tables exist",
                        result=ValidationResult.FAIL,
                        latency_ms=tables_latency,
                        message=str(tables_result),
                    ))
                else:
                    report.action_validations.append(ActionValidation(
                        action_name="tables_exist",
                        description="Verify core database tables exist",
                        result=ValidationResult.PASS,
                        latency_ms=tables_latency,
                        details=tables_result,
                    ))
            except Exception as e:
                report.action_validations.append(ActionValidation(
                    action_name="tables_exist",
                    description="Verify core database tables exist",
                    result=ValidationResult.WARN,
                    message=str(e),
                ))

            try:
                config = DatabaseConnection.get_config()
                report.details = {
                    "db_type": config.db_type.value if hasattr(config.db_type, 'value') else str(config.db_type),
                    "pool_pre_ping": getattr(config, 'pool_pre_ping', None),
                }
            except Exception:
                pass
        else:
            report.status = ConnectionStatus.DISCONNECTED
            report.message = "health_check returned False"
            report.action_validations.append(ActionValidation(
                action_name="health_check",
                description="Execute SELECT 1 against database",
                result=ValidationResult.FAIL,
                latency_ms=latency,
                message="Returned False",
            ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Import/init error: {e}"

    return report


def _test_session():
    from database.session import SessionLocal
    from sqlalchemy import text
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return True
    finally:
        session.close()


def _check_tables():
    from database.connection import DatabaseConnection
    from sqlalchemy import inspect as sa_inspect
    engine = DatabaseConnection.get_engine()
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    return {"table_count": len(tables), "tables": tables[:20]}


def validate_qdrant() -> ConnectionReport:
    """Validate Qdrant vector database connection and actions."""
    report = ConnectionReport(
        name="qdrant",
        category=ConnectionCategory.INFRASTRUCTURE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from vector_db.client import get_qdrant_client

        qdrant = get_qdrant_client()

        # Check basic connection
        result, latency = _timed(qdrant.is_connected)
        report.latency_ms = latency

        if isinstance(result, Exception) or not result:
            report.status = ConnectionStatus.DISCONNECTED
            report.message = str(result) if isinstance(result, Exception) else "Not connected"
            report.action_validations.append(ActionValidation(
                action_name="is_connected",
                description="Check Qdrant server connectivity",
                result=ValidationResult.FAIL,
                latency_ms=latency,
                message=report.message,
            ))
            return report

        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.action_validations.append(ActionValidation(
            action_name="is_connected",
            description="Check Qdrant server connectivity",
            result=ValidationResult.PASS,
            latency_ms=latency,
        ))

        # Validate collection listing
        collections_result, coll_latency = _timed(qdrant.list_collections)
        if isinstance(collections_result, Exception):
            report.action_validations.append(ActionValidation(
                action_name="list_collections",
                description="List all vector collections",
                result=ValidationResult.FAIL,
                latency_ms=coll_latency,
                message=str(collections_result),
            ))
        else:
            report.action_validations.append(ActionValidation(
                action_name="list_collections",
                description="List all vector collections",
                result=ValidationResult.PASS,
                latency_ms=coll_latency,
                details={"collection_count": len(collections_result), "collections": collections_result[:10]},
            ))
            report.details = {"collections": len(collections_result)}

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Import/init error: {e}"

    return report


def validate_llm_provider() -> ConnectionReport:
    """Validate LLM provider connection and actions."""
    report = ConnectionReport(
        name="llm_provider",
        category=ConnectionCategory.INFRASTRUCTURE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from llm_orchestrator.factory import get_llm_client
        try:
            from settings import settings
            provider_name = getattr(settings, 'LLM_PROVIDER', 'unknown')
        except ImportError:
            provider_name = "unknown"

        client = get_llm_client()

        # Check if running
        result, latency = _timed(client.is_running)
        report.latency_ms = latency

        if isinstance(result, Exception) or not result:
            report.status = ConnectionStatus.DISCONNECTED
            report.message = str(result) if isinstance(result, Exception) else f"{provider_name} not responding"
            report.action_validations.append(ActionValidation(
                action_name="is_running",
                description=f"Check {provider_name} service availability",
                result=ValidationResult.FAIL,
                latency_ms=latency,
                message=report.message,
            ))
            return report

        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.details = {"provider": provider_name}
        report.action_validations.append(ActionValidation(
            action_name="is_running",
            description=f"Check {provider_name} service availability",
            result=ValidationResult.PASS,
            latency_ms=latency,
        ))

        # Validate model listing
        models_result, models_latency = _timed(client.get_all_models)
        if isinstance(models_result, Exception):
            report.action_validations.append(ActionValidation(
                action_name="get_all_models",
                description="List available models from provider",
                result=ValidationResult.FAIL,
                latency_ms=models_latency,
                message=str(models_result),
            ))
        else:
            model_count = len(models_result) if models_result else 0
            report.action_validations.append(ActionValidation(
                action_name="get_all_models",
                description="List available models from provider",
                result=ValidationResult.PASS if model_count > 0 else ValidationResult.WARN,
                latency_ms=models_latency,
                details={"models_available": model_count},
                message=None if model_count > 0 else "No models available",
            ))
            report.details["models_available"] = model_count

        # Validate configured model exists
        try:
            from settings import settings
            configured_model = getattr(settings, 'LLM_MODEL', None)
            if configured_model and hasattr(client, 'model_exists'):
                exists_result, exists_latency = _timed(lambda: client.model_exists(configured_model))
                if isinstance(exists_result, Exception):
                    report.action_validations.append(ActionValidation(
                        action_name="configured_model_exists",
                        description=f"Verify configured model '{configured_model}' is available",
                        result=ValidationResult.WARN,
                        latency_ms=exists_latency,
                        message=str(exists_result),
                    ))
                else:
                    report.action_validations.append(ActionValidation(
                        action_name="configured_model_exists",
                        description=f"Verify configured model '{configured_model}' is available",
                        result=ValidationResult.PASS if exists_result else ValidationResult.FAIL,
                        latency_ms=exists_latency,
                        message=None if exists_result else f"Model '{configured_model}' not found",
                    ))
        except ImportError:
            pass

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Import/init error: {e}"

    return report


def validate_embedding_model() -> ConnectionReport:
    """Validate embedding model connection and actions."""
    report = ConnectionReport(
        name="embedding_model",
        category=ConnectionCategory.INFRASTRUCTURE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from embedding import get_embedder
        embedder = get_embedder()

        result, latency = _timed(lambda: embedder.embed_text(["connection validation test"]))
        report.latency_ms = latency

        if isinstance(result, Exception):
            report.status = ConnectionStatus.DISCONNECTED
            report.message = str(result)
            report.action_validations.append(ActionValidation(
                action_name="embed_text",
                description="Generate test embedding vector",
                result=ValidationResult.FAIL,
                latency_ms=latency,
                message=str(result),
            ))
            return report

        if result is not None and hasattr(result, 'shape') and result.shape[0] > 0:
            report.status = ConnectionStatus.CONNECTED
            report.connected = True
            dimension = result.shape[0] if len(result.shape) == 1 else result.shape[1]
            report.details = {"dimension": int(dimension)}
            report.action_validations.append(ActionValidation(
                action_name="embed_text",
                description="Generate test embedding vector",
                result=ValidationResult.PASS,
                latency_ms=latency,
                details={"dimension": int(dimension)},
            ))
        else:
            report.status = ConnectionStatus.DEGRADED
            report.message = "Embedding returned empty result"
            report.action_validations.append(ActionValidation(
                action_name="embed_text",
                description="Generate test embedding vector",
                result=ValidationResult.WARN,
                latency_ms=latency,
                message="Empty result",
            ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Import/init error: {e}"

    return report


# ---------------------------------------------------------------------------
# External API validators
# ---------------------------------------------------------------------------

def validate_serpapi() -> ConnectionReport:
    """Validate SerpAPI connection."""
    report = ConnectionReport(
        name="serpapi",
        category=ConnectionCategory.EXTERNAL_API,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from settings import settings
        api_key = getattr(settings, 'SERPAPI_KEY', None) or getattr(settings, 'SERPAPI_API_KEY', None)

        if not api_key:
            report.status = ConnectionStatus.NOT_CONFIGURED
            report.message = "SERPAPI_KEY not set"
            report.action_validations.append(ActionValidation(
                action_name="api_key_configured",
                description="Check SerpAPI key is configured",
                result=ValidationResult.SKIP,
                message="No API key configured",
            ))
            return report

        report.action_validations.append(ActionValidation(
            action_name="api_key_configured",
            description="Check SerpAPI key is configured",
            result=ValidationResult.PASS,
        ))

        from search.serpapi_service import SerpAPIService
        service = SerpAPIService(api_key=api_key)

        if hasattr(service, 'test_connection'):
            result, latency = _timed(service.test_connection)
            report.latency_ms = latency
            if isinstance(result, Exception) or not result:
                report.status = ConnectionStatus.DEGRADED
                report.message = str(result) if isinstance(result, Exception) else "test_connection returned False"
                report.action_validations.append(ActionValidation(
                    action_name="test_connection",
                    description="Execute test search query",
                    result=ValidationResult.FAIL,
                    latency_ms=latency,
                    message=report.message,
                ))
            else:
                report.status = ConnectionStatus.CONNECTED
                report.connected = True
                report.action_validations.append(ActionValidation(
                    action_name="test_connection",
                    description="Execute test search query",
                    result=ValidationResult.PASS,
                    latency_ms=latency,
                ))
        else:
            report.status = ConnectionStatus.CONNECTED
            report.connected = True
            report.message = "API key configured (no test_connection method)"

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Error: {e}"

    return report


def validate_kimi() -> ConnectionReport:
    """Validate Kimi API connection."""
    report = ConnectionReport(
        name="kimi",
        category=ConnectionCategory.EXTERNAL_API,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from settings import settings
        api_key = getattr(settings, 'KIMI_API_KEY', None)
        model = getattr(settings, 'KIMI_MODEL', None)

        if not api_key:
            report.status = ConnectionStatus.NOT_CONFIGURED
            report.message = "KIMI_API_KEY not set"
            report.action_validations.append(ActionValidation(
                action_name="api_key_configured",
                description="Check Kimi API key is configured",
                result=ValidationResult.SKIP,
                message="No API key configured",
            ))
            return report

        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.details = {"model": model, "configured": True}
        report.action_validations.append(ActionValidation(
            action_name="api_key_configured",
            description="Check Kimi API key is configured",
            result=ValidationResult.PASS,
            details={"model": model},
        ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Error: {e}"

    return report


def validate_opus() -> ConnectionReport:
    """Validate Opus API connection."""
    report = ConnectionReport(
        name="opus",
        category=ConnectionCategory.EXTERNAL_API,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from settings import settings
        api_key = getattr(settings, 'OPUS_API_KEY', None)
        model = getattr(settings, 'OPUS_MODEL', None)

        if not api_key:
            report.status = ConnectionStatus.NOT_CONFIGURED
            report.message = "OPUS_API_KEY not set"
            report.action_validations.append(ActionValidation(
                action_name="api_key_configured",
                description="Check Opus API key is configured",
                result=ValidationResult.SKIP,
                message="No API key configured",
            ))
            return report

        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.details = {"model": model, "configured": True}
        report.action_validations.append(ActionValidation(
            action_name="api_key_configured",
            description="Check Opus API key is configured",
            result=ValidationResult.PASS,
            details={"model": model},
        ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Error: {e}"

    return report


# ---------------------------------------------------------------------------
# Layer 1 Connector validators
# ---------------------------------------------------------------------------

def validate_layer1_connectors() -> List[ConnectionReport]:
    """Validate all Layer 1 message bus connector registrations and actions."""
    reports = []

    try:
        from layer1.message_bus import get_message_bus, ComponentType
        bus = get_message_bus()

        registered = set()
        if hasattr(bus, '_components'):
            registered = set(bus._components.keys())
        elif hasattr(bus, 'components'):
            registered = set(bus.components.keys())

        autonomous_actions = {}
        if hasattr(bus, '_autonomous_actions'):
            for action in bus._autonomous_actions:
                comp = action.get('component', action.get('from_component', None))
                comp_key = comp.value if hasattr(comp, 'value') else str(comp)
                if comp_key not in autonomous_actions:
                    autonomous_actions[comp_key] = []
                autonomous_actions[comp_key].append(action)

        request_handlers = {}
        if hasattr(bus, '_request_handlers'):
            for comp, handlers in bus._request_handlers.items():
                comp_key = comp.value if hasattr(comp, 'value') else str(comp)
                request_handlers[comp_key] = list(handlers.keys()) if isinstance(handlers, dict) else handlers

        subscriptions = {}
        if hasattr(bus, '_subscriptions'):
            for topic, subs in bus._subscriptions.items():
                for sub in subs:
                    comp = sub.get('component', 'unknown') if isinstance(sub, dict) else 'unknown'
                    comp_key = comp.value if hasattr(comp, 'value') else str(comp)
                    if comp_key not in subscriptions:
                        subscriptions[comp_key] = []
                    subscriptions[comp_key].append(topic)

        connector_spec = {
            ComponentType.MEMORY_MESH: {
                "expected_actions": 6,
                "expected_handlers": 3,
                "expected_subscriptions": 2,
                "description": "Memory Mesh - Learning memory integration",
            },
            ComponentType.GENESIS_KEYS: {
                "expected_actions": 3,
                "expected_handlers": 3,
                "expected_subscriptions": 1,
                "description": "Genesis Keys - Universal tracking",
            },
            ComponentType.RAG: {
                "expected_actions": 4,
                "expected_handlers": 2,
                "expected_subscriptions": 1,
                "description": "RAG - Retrieval-augmented generation",
            },
            ComponentType.INGESTION: {
                "expected_actions": 3,
                "expected_handlers": 2,
                "expected_subscriptions": 0,
                "description": "Ingestion - File processing",
            },
            ComponentType.LLM_ORCHESTRATION: {
                "expected_actions": 2,
                "expected_handlers": 3,
                "expected_subscriptions": 1,
                "description": "LLM Orchestration - Multi-LLM coordination",
            },
            ComponentType.VERSION_CONTROL: {
                "expected_actions": 3,
                "expected_handlers": 2,
                "expected_subscriptions": 0,
                "description": "Version Control - Git/version tracking",
            },
        }

        for comp_type, spec in connector_spec.items():
            comp_key = comp_type.value
            is_registered = comp_type in registered

            report = ConnectionReport(
                name=f"layer1_{comp_key}",
                category=ConnectionCategory.LAYER1_CONNECTOR,
                status=ConnectionStatus.CONNECTED if is_registered else ConnectionStatus.DISCONNECTED,
                connected=is_registered,
                details={"description": spec["description"]},
            )

            report.action_validations.append(ActionValidation(
                action_name="bus_registration",
                description=f"Component registered on Layer 1 message bus",
                result=ValidationResult.PASS if is_registered else ValidationResult.FAIL,
                message=None if is_registered else "Not registered on message bus",
            ))

            actual_actions = len(autonomous_actions.get(comp_key, []))
            expected_actions = spec["expected_actions"]
            report.action_validations.append(ActionValidation(
                action_name="autonomous_actions",
                description=f"Autonomous actions registered (expected: {expected_actions})",
                result=ValidationResult.PASS if actual_actions >= expected_actions else ValidationResult.WARN,
                details={"registered": actual_actions, "expected": expected_actions},
                message=None if actual_actions >= expected_actions else f"Only {actual_actions}/{expected_actions} actions registered",
            ))

            actual_handlers = len(request_handlers.get(comp_key, []))
            expected_handlers = spec["expected_handlers"]
            report.action_validations.append(ActionValidation(
                action_name="request_handlers",
                description=f"Request handlers registered (expected: {expected_handlers})",
                result=ValidationResult.PASS if actual_handlers >= expected_handlers else ValidationResult.WARN,
                details={"registered": actual_handlers, "expected": expected_handlers,
                         "handlers": request_handlers.get(comp_key, [])},
                message=None if actual_handlers >= expected_handlers else f"Only {actual_handlers}/{expected_handlers} handlers registered",
            ))

            actual_subs = len(subscriptions.get(comp_key, []))
            expected_subs = spec["expected_subscriptions"]
            if expected_subs > 0:
                report.action_validations.append(ActionValidation(
                    action_name="event_subscriptions",
                    description=f"Event subscriptions registered (expected: {expected_subs})",
                    result=ValidationResult.PASS if actual_subs >= expected_subs else ValidationResult.WARN,
                    details={"registered": actual_subs, "expected": expected_subs,
                             "topics": subscriptions.get(comp_key, [])},
                    message=None if actual_subs >= expected_subs else f"Only {actual_subs}/{expected_subs} subscriptions",
                ))

            if not is_registered:
                report.status = ConnectionStatus.DISCONNECTED

            reports.append(report)

        # Check for any additional registered components not in spec
        for comp in registered:
            comp_key = comp.value if hasattr(comp, 'value') else str(comp)
            if comp not in connector_spec:
                reports.append(ConnectionReport(
                    name=f"layer1_{comp_key}",
                    category=ConnectionCategory.LAYER1_CONNECTOR,
                    status=ConnectionStatus.CONNECTED,
                    connected=True,
                    details={"description": f"Additional component: {comp_key}"},
                    action_validations=[ActionValidation(
                        action_name="bus_registration",
                        description="Component registered on Layer 1 message bus",
                        result=ValidationResult.PASS,
                    )],
                ))

    except ImportError as e:
        reports.append(ConnectionReport(
            name="layer1_message_bus",
            category=ConnectionCategory.LAYER1_CONNECTOR,
            status=ConnectionStatus.DISCONNECTED,
            connected=False,
            message=f"Message bus not available: {e}",
        ))
    except Exception as e:
        reports.append(ConnectionReport(
            name="layer1_message_bus",
            category=ConnectionCategory.LAYER1_CONNECTOR,
            status=ConnectionStatus.DISCONNECTED,
            connected=False,
            message=f"Error checking message bus: {e}",
        ))

    return reports


# ---------------------------------------------------------------------------
# Background Service validators
# ---------------------------------------------------------------------------

def validate_diagnostic_engine() -> ConnectionReport:
    """Validate diagnostic engine is running."""
    report = ConnectionReport(
        name="diagnostic_engine",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        engine = get_diagnostic_engine()

        state = "unknown"
        if hasattr(engine, 'state'):
            state = engine.state.value if hasattr(engine.state, 'value') else str(engine.state)

        is_running = state not in ("stopped", "unavailable", "unknown")
        report.status = ConnectionStatus.CONNECTED if is_running else ConnectionStatus.DISCONNECTED
        report.connected = is_running
        report.details = {"state": state}

        report.action_validations.append(ActionValidation(
            action_name="engine_running",
            description="Diagnostic engine is actively running",
            result=ValidationResult.PASS if is_running else ValidationResult.FAIL,
            details={"state": state},
        ))

        if hasattr(engine, 'get_health_summary'):
            try:
                summary_result, latency = _timed(engine.get_health_summary)
                if isinstance(summary_result, Exception):
                    report.action_validations.append(ActionValidation(
                        action_name="health_summary",
                        description="Retrieve health summary from engine",
                        result=ValidationResult.FAIL,
                        latency_ms=latency,
                        message=str(summary_result),
                    ))
                else:
                    report.action_validations.append(ActionValidation(
                        action_name="health_summary",
                        description="Retrieve health summary from engine",
                        result=ValidationResult.PASS,
                        latency_ms=latency,
                    ))
            except Exception as e:
                report.action_validations.append(ActionValidation(
                    action_name="health_summary",
                    description="Retrieve health summary from engine",
                    result=ValidationResult.WARN,
                    message=str(e),
                ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Not available: {e}"

    return report


def validate_autonomous_loop() -> ConnectionReport:
    """Validate autonomous loop is running."""
    report = ConnectionReport(
        name="autonomous_loop",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from api.autonomous_loop_api import _loop_state, _stop_event
        is_running = _loop_state.get("running", False) and not _stop_event.is_set()

        report.status = ConnectionStatus.CONNECTED if is_running else ConnectionStatus.DISCONNECTED
        report.connected = is_running
        report.details = {"state": _loop_state}

        report.action_validations.append(ActionValidation(
            action_name="loop_running",
            description="Autonomous loop background thread is active",
            result=ValidationResult.PASS if is_running else ValidationResult.FAIL,
            details={"running": is_running},
        ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Not available: {e}"

    return report


def validate_continuous_learning() -> ConnectionReport:
    """Validate continuous learning orchestrator."""
    report = ConnectionReport(
        name="continuous_learning",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from cognitive.continuous_learning_orchestrator import get_continuous_learning_status
        status = get_continuous_learning_status()
        is_running = status.get("running", False) if status else False

        report.status = ConnectionStatus.CONNECTED if is_running else ConnectionStatus.DISCONNECTED
        report.connected = is_running
        report.details = status

        report.action_validations.append(ActionValidation(
            action_name="orchestrator_running",
            description="Continuous learning orchestrator is active",
            result=ValidationResult.PASS if is_running else ValidationResult.FAIL,
        ))

    except ImportError:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = "Module not available"
    except Exception as e:
        try:
            from cognitive.continuous_learning_orchestrator import start_continuous_learning
            report.status = ConnectionStatus.DEGRADED
            report.message = f"Status check unavailable: {e}"
            report.action_validations.append(ActionValidation(
                action_name="module_importable",
                description="Continuous learning module can be imported",
                result=ValidationResult.PASS,
            ))
        except Exception:
            report.status = ConnectionStatus.DISCONNECTED
            report.message = f"Not available: {e}"

    return report


def validate_file_watcher() -> ConnectionReport:
    """Validate file watcher service."""
    report = ConnectionReport(
        name="file_watcher",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from genesis.file_watcher import get_watcher_status
        status = get_watcher_status()
        is_running = status.get("running", False) if status else False

        report.status = ConnectionStatus.CONNECTED if is_running else ConnectionStatus.DISCONNECTED
        report.connected = is_running

        report.action_validations.append(ActionValidation(
            action_name="watcher_running",
            description="File system watcher is actively monitoring",
            result=ValidationResult.PASS if is_running else ValidationResult.FAIL,
        ))

    except (ImportError, AttributeError):
        try:
            from genesis.file_watcher import start_watching_workspace
            report.status = ConnectionStatus.DEGRADED
            report.message = "Module importable but status check not available"
            report.connected = True
            report.action_validations.append(ActionValidation(
                action_name="module_importable",
                description="File watcher module can be imported",
                result=ValidationResult.PASS,
            ))
        except ImportError:
            report.status = ConnectionStatus.DISCONNECTED
            report.message = "Module not available"
    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Error: {e}"

    return report


def validate_ml_intelligence() -> ConnectionReport:
    """Validate ML Intelligence orchestrator."""
    report = ConnectionReport(
        name="ml_intelligence",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator
        orchestrator = MLIntelligenceOrchestrator()
        features = list(orchestrator.enabled_features.keys()) if hasattr(orchestrator, 'enabled_features') else []

        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.details = {"features": features, "feature_count": len(features)}

        report.action_validations.append(ActionValidation(
            action_name="orchestrator_initialized",
            description="ML Intelligence orchestrator is initialized",
            result=ValidationResult.PASS,
            details={"features": features},
        ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Not available: {e}"

    return report


def validate_genesis_tracking() -> ConnectionReport:
    """Validate Genesis Key tracking middleware."""
    report = ConnectionReport(
        name="genesis_tracking",
        category=ConnectionCategory.BACKGROUND_SERVICE,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from settings import settings
        disabled = getattr(settings, 'DISABLE_GENESIS_TRACKING', False)

        if disabled:
            report.status = ConnectionStatus.NOT_CONFIGURED
            report.message = "Genesis tracking disabled via DISABLE_GENESIS_TRACKING"
            report.action_validations.append(ActionValidation(
                action_name="tracking_enabled",
                description="Genesis tracking middleware is active",
                result=ValidationResult.SKIP,
                message="Disabled by configuration",
            ))
            return report

        from genesis.middleware import GenesisKeyMiddleware
        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.action_validations.append(ActionValidation(
            action_name="middleware_importable",
            description="Genesis Key middleware can be loaded",
            result=ValidationResult.PASS,
        ))

        from genesis.genesis_key_service import get_genesis_service
        report.action_validations.append(ActionValidation(
            action_name="service_importable",
            description="Genesis Key service can be loaded",
            result=ValidationResult.PASS,
        ))

    except ImportError as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Module not available: {e}"
    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Error: {e}"

    return report


# ---------------------------------------------------------------------------
# WebSocket validators
# ---------------------------------------------------------------------------

def validate_websocket_manager() -> ConnectionReport:
    """Validate WebSocket connection manager."""
    report = ConnectionReport(
        name="websocket_manager",
        category=ConnectionCategory.WEBSOCKET,
        status=ConnectionStatus.UNKNOWN,
        connected=False,
    )

    try:
        from diagnostic_machine.realtime import get_connection_manager
        manager = get_connection_manager()

        client_count = manager.client_count
        report.status = ConnectionStatus.CONNECTED
        report.connected = True
        report.details = {"connected_clients": client_count}

        report.action_validations.append(ActionValidation(
            action_name="manager_operational",
            description="WebSocket connection manager is operational",
            result=ValidationResult.PASS,
            details={"client_count": client_count},
        ))

        clients = manager.get_all_clients()
        report.action_validations.append(ActionValidation(
            action_name="client_listing",
            description="Can list connected WebSocket clients",
            result=ValidationResult.PASS,
            details={"clients": len(clients)},
        ))

        history = manager.get_event_history(limit=5)
        report.action_validations.append(ActionValidation(
            action_name="event_history",
            description="Can retrieve event history",
            result=ValidationResult.PASS,
            details={"recent_events": len(history)},
        ))

    except Exception as e:
        report.status = ConnectionStatus.DISCONNECTED
        report.message = f"Not available: {e}"

    return report


# ---------------------------------------------------------------------------
# Full system validation
# ---------------------------------------------------------------------------

def validate_all_connections(
    include_layer1: bool = True,
    include_background: bool = True,
    include_external: bool = True,
) -> SystemConnectionReport:
    """
    Validate ALL system connections and return comprehensive report.

    This is the single source of truth for connection status across
    the entire system.
    """
    connections: List[ConnectionReport] = []

    # 1. Infrastructure (always checked)
    logger.info("[CONNECTION-VALIDATOR] Checking infrastructure connections...")
    connections.append(validate_database())
    connections.append(validate_qdrant())
    connections.append(validate_llm_provider())
    connections.append(validate_embedding_model())

    # 2. External APIs
    if include_external:
        logger.info("[CONNECTION-VALIDATOR] Checking external API connections...")
        connections.append(validate_serpapi())
        connections.append(validate_kimi())
        connections.append(validate_opus())

    # 3. Layer 1 Connectors
    if include_layer1:
        logger.info("[CONNECTION-VALIDATOR] Checking Layer 1 connector registrations...")
        connections.extend(validate_layer1_connectors())

    # 4. Background Services
    if include_background:
        logger.info("[CONNECTION-VALIDATOR] Checking background services...")
        connections.append(validate_diagnostic_engine())
        connections.append(validate_autonomous_loop())
        connections.append(validate_continuous_learning())
        connections.append(validate_file_watcher())
        connections.append(validate_ml_intelligence())
        connections.append(validate_genesis_tracking())

    # 5. WebSocket
    connections.append(validate_websocket_manager())

    # Calculate totals
    connected_count = sum(1 for c in connections if c.connected)
    disconnected_count = sum(1 for c in connections if c.status == ConnectionStatus.DISCONNECTED)
    degraded_count = sum(1 for c in connections if c.status == ConnectionStatus.DEGRADED)
    not_configured_count = sum(1 for c in connections if c.status == ConnectionStatus.NOT_CONFIGURED)
    total = len(connections)

    total_actions = sum(c.actions_total for c in connections)
    total_passing = sum(c.actions_passing for c in connections)
    total_failing = sum(c.actions_failing for c in connections)

    # Determine overall status
    infra_disconnected = sum(
        1 for c in connections
        if c.category == ConnectionCategory.INFRASTRUCTURE and c.status == ConnectionStatus.DISCONNECTED
    )

    if infra_disconnected > 0:
        overall_status = "critical"
    elif disconnected_count > 2:
        overall_status = "degraded"
    elif disconnected_count > 0 or degraded_count > 0:
        overall_status = "partial"
    else:
        overall_status = "all_connected"

    report = SystemConnectionReport(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_connections=total,
        connected_count=connected_count,
        disconnected_count=disconnected_count,
        degraded_count=degraded_count,
        connections=connections,
        total_actions_validated=total_actions,
        total_actions_passing=total_passing,
        total_actions_failing=total_failing,
    )

    logger.info(
        f"[CONNECTION-VALIDATOR] Complete: {connected_count}/{total} connected, "
        f"{total_passing}/{total_actions} actions passing, status={overall_status}"
    )

    return report
