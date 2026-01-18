"""
Audit Middleware - Automatically captures all critical events for immutable storage.

This middleware integrates with all system components to ensure
NO data can disappear without being audited.

Captures:
- All user inputs
- All AI decisions and responses
- All code changes
- All data modifications
- All system events
- All API calls
- All security events
"""

import functools
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable, TypeVar, ParamSpec
from contextlib import contextmanager
from sqlalchemy.orm import Session

from genesis.immutable_audit_storage import (
    ImmutableAuditStorage,
    ImmutableAuditType,
    get_immutable_audit_storage,
    audit_user_input,
    audit_code_change,
    audit_ai_decision,
    audit_data_access,
    audit_system_event,
    audit_security_event
)

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class AuditContext:
    """Context manager for audit operations with automatic tracking."""
    
    def __init__(
        self,
        session: Session,
        operation_name: str,
        actor_type: str,
        actor_id: Optional[str] = None,
        component: Optional[str] = None
    ):
        self.session = session
        self.operation_name = operation_name
        self.actor_type = actor_type
        self.actor_id = actor_id
        self.component = component
        self.storage = get_immutable_audit_storage(session)
        self.parent_record_id: Optional[str] = None
        self.start_time = datetime.utcnow()
    
    def __enter__(self):
        # Record operation start
        record = self.storage.record(
            audit_type=ImmutableAuditType.SYSTEM_STARTUP,
            action_description=f"Started: {self.operation_name}",
            actor_type=self.actor_type,
            actor_id=self.actor_id,
            component=self.component,
            context={"start_time": self.start_time.isoformat()}
        )
        self.parent_record_id = record.record_id
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        if exc_type is not None:
            # Record failure
            self.storage.record(
                audit_type=ImmutableAuditType.SYSTEM_ERROR,
                action_description=f"Failed: {self.operation_name} - {exc_val}",
                actor_type=self.actor_type,
                actor_id=self.actor_id,
                component=self.component,
                severity="error",
                parent_record_id=self.parent_record_id,
                context={
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val),
                    "duration_ms": duration_ms
                }
            )
        else:
            # Record success
            self.storage.record(
                audit_type=ImmutableAuditType.SYSTEM_STARTUP,
                action_description=f"Completed: {self.operation_name}",
                actor_type=self.actor_type,
                actor_id=self.actor_id,
                component=self.component,
                parent_record_id=self.parent_record_id,
                context={
                    "end_time": end_time.isoformat(),
                    "duration_ms": duration_ms
                }
            )
        
        return False  # Don't suppress exceptions
    
    def log_step(
        self,
        description: str,
        data: Optional[Dict] = None,
        severity: str = "info"
    ):
        """Log an intermediate step in the operation."""
        self.storage.record(
            audit_type=ImmutableAuditType.DATA_ACCESS,
            action_description=f"Step: {description}",
            actor_type=self.actor_type,
            actor_id=self.actor_id,
            component=self.component,
            severity=severity,
            parent_record_id=self.parent_record_id,
            action_data=data
        )


def audit_function(
    audit_type: ImmutableAuditType,
    component: Optional[str] = None,
    capture_args: bool = True,
    capture_result: bool = True
):
    """
    Decorator to automatically audit function calls.
    
    Usage:
        @audit_function(ImmutableAuditType.CODE_CHANGE, component="code_analyzer")
        def analyze_code(file_path: str) -> Dict:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Get session from args if available
            session = None
            for arg in args:
                if isinstance(arg, Session):
                    session = arg
                    break
            if session is None:
                for value in kwargs.values():
                    if isinstance(value, Session):
                        session = value
                        break
            
            if session is None:
                # Can't audit without session, just run the function
                logger.warning(f"[AUDIT-MIDDLEWARE] No session for auditing: {func.__name__}")
                return func(*args, **kwargs)
            
            storage = get_immutable_audit_storage(session)
            start_time = datetime.utcnow()
            
            # Record function call
            call_data = {}
            if capture_args:
                # Safely serialize args (avoid sensitive data)
                call_data["args_count"] = len(args)
                call_data["kwargs_keys"] = list(kwargs.keys())
            
            try:
                result = func(*args, **kwargs)
                
                # Record success
                result_data = {}
                if capture_result and result is not None:
                    result_data["result_type"] = type(result).__name__
                    if hasattr(result, '__len__'):
                        result_data["result_length"] = len(result)
                
                storage.record(
                    audit_type=audit_type,
                    action_description=f"Function: {func.__name__}",
                    actor_type="function",
                    actor_id=func.__module__,
                    component=component or func.__module__,
                    action_data=call_data,
                    context={
                        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                        "result": result_data,
                        "status": "success"
                    }
                )
                
                return result
                
            except Exception as e:
                # Record failure
                storage.record(
                    audit_type=audit_type,
                    action_description=f"Function failed: {func.__name__}",
                    actor_type="function",
                    actor_id=func.__module__,
                    component=component or func.__module__,
                    severity="error",
                    action_data=call_data,
                    context={
                        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "status": "failed"
                    }
                )
                raise
        
        return wrapper
    return decorator


class AutoAuditMiddleware:
    """
    Middleware class for automatic auditing in API routes and handlers.
    
    Integrates with FastAPI/Flask/etc. to automatically audit all requests.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.storage = get_immutable_audit_storage(session)
    
    def audit_request(
        self,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        request_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> str:
        """Audit an incoming API request. Returns record_id for linking response."""
        record = self.storage.record(
            audit_type=ImmutableAuditType.API_REQUEST,
            action_description=f"API Request: {method} {path}",
            actor_type="api",
            actor_id=user_id or "anonymous",
            component="api",
            action_data={
                "method": method,
                "path": path,
                "has_body": request_data is not None
            },
            context={
                "user_agent": headers.get("user-agent") if headers else None
            }
        )
        return record.record_id
    
    def audit_response(
        self,
        request_record_id: str,
        status_code: int,
        response_time_ms: float,
        error: Optional[str] = None
    ):
        """Audit an API response."""
        severity = "info"
        if status_code >= 500:
            severity = "error"
        elif status_code >= 400:
            severity = "warning"
        
        self.storage.record(
            audit_type=ImmutableAuditType.API_RESPONSE,
            action_description=f"API Response: {status_code}",
            actor_type="api",
            actor_id="api-server",
            component="api",
            severity=severity,
            parent_record_id=request_record_id,
            action_data={
                "status_code": status_code,
                "response_time_ms": response_time_ms
            },
            context={"error": error} if error else None
        )


# Global singleton for easy access
_global_audit_middleware: Optional[AutoAuditMiddleware] = None


def init_audit_middleware(session: Session) -> AutoAuditMiddleware:
    """Initialize the global audit middleware."""
    global _global_audit_middleware
    _global_audit_middleware = AutoAuditMiddleware(session)
    
    # Log initialization
    _global_audit_middleware.storage.record(
        audit_type=ImmutableAuditType.SYSTEM_STARTUP,
        action_description="Audit middleware initialized",
        actor_type="system",
        actor_id="audit-middleware",
        component="audit"
    )
    
    return _global_audit_middleware


def get_audit_middleware() -> Optional[AutoAuditMiddleware]:
    """Get the global audit middleware."""
    return _global_audit_middleware


# ==================== Integration Points ====================

def integrate_with_genesis_keys(session: Session):
    """
    Integrate audit storage with Genesis Key system.
    
    This ensures all Genesis Keys are also audited immutably.
    """
    from genesis.genesis_key_service import GenesisKeyService
    
    original_create_key = GenesisKeyService.create_key
    
    @functools.wraps(original_create_key)
    def audited_create_key(self, *args, **kwargs):
        result = original_create_key(self, *args, **kwargs)
        
        # Also record in immutable audit
        if result and session:
            storage = get_immutable_audit_storage(session)
            storage.record(
                audit_type=ImmutableAuditType.GENESIS_KEY_CREATED,
                action_description=f"Genesis Key created: {result.key_id}",
                actor_type=kwargs.get("who_actor", "unknown"),
                actor_id=kwargs.get("user_id"),
                component="genesis",
                genesis_key_id=result.key_id,
                action_data={
                    "key_type": kwargs.get("key_type"),
                    "what": kwargs.get("what_description")
                }
            )
        
        return result
    
    GenesisKeyService.create_key = audited_create_key
    logger.info("[AUDIT-MIDDLEWARE] Integrated with Genesis Key service")


def integrate_with_coding_agent(session: Session):
    """
    Integrate audit storage with Coding Agent.
    
    Ensures all coding agent actions are audited.
    """
    storage = get_immutable_audit_storage(session)
    
    def audit_coding_action(
        action_type: str,
        file_path: str,
        code_before: Optional[str],
        code_after: Optional[str],
        reason: Optional[str] = None
    ):
        storage.record(
            audit_type=ImmutableAuditType.CODING_AGENT_ACTION,
            action_description=f"Coding Agent: {action_type} on {file_path}",
            actor_type="coding_agent",
            actor_id="grace-coding-agent",
            component="coding_agent",
            file_path=file_path,
            reason=reason,
            state_before={"code": code_before[:1000] if code_before else None},
            state_after={"code": code_after[:1000] if code_after else None}
        )
    
    return audit_coding_action


def integrate_with_self_healing(session: Session):
    """
    Integrate audit storage with Self-Healing system.
    
    Ensures all self-healing actions are audited.
    """
    storage = get_immutable_audit_storage(session)
    
    def audit_healing_action(
        action_type: str,
        target: str,
        problem: str,
        solution: str,
        success: bool
    ):
        storage.record(
            audit_type=ImmutableAuditType.SELF_HEALING_ACTION,
            action_description=f"Self-Healing: {action_type} - {problem[:50]}",
            actor_type="self_healing",
            actor_id="grace-healer",
            component="self_healing",
            severity="warning" if not success else "info",
            action_data={
                "action_type": action_type,
                "target": target,
                "problem": problem,
                "solution": solution,
                "success": success
            }
        )
    
    return audit_healing_action
