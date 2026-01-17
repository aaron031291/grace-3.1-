"""
Launcher Self-Healing Integration

Integrates Grace's autonomous healing system into the launcher to automatically
detect and fix problems, or notify users when manual intervention is needed.
"""

import logging
import sys
import socket
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class LauncherSelfHealing:
    """
    Self-healing integration for the launcher.
    
    Detects common launcher problems and attempts automatic fixes.
    If no fix is available, notifies the user.
    """
    
    def __init__(
        self,
        root_path: Path,
        backend_port: int = 8000,
        enable_healing: bool = True,
        enable_notifications: bool = True
    ):
        """
        Initialize launcher self-healing.
        
        Args:
            root_path: Root path of Grace installation
            backend_port: Backend port number
            enable_healing: Whether to attempt automatic healing
            enable_notifications: Whether to send notifications for unhealable issues
        """
        self.root_path = Path(root_path)
        self.backend_port = backend_port
        self.enable_healing = enable_healing
        self.enable_notifications = enable_notifications
        
        # Initialize healing system (lazy load)
        self.healing_system = None
        self.session = None
        
        # Initialize notification manager (lazy load)
        self.notification_manager = None
        
        # Track healing attempts to avoid loops
        self.healing_attempts: Dict[str, int] = {}
        self.max_attempts_per_issue = 3
        
        logger.info("Grace's launcher self-healing system initialized")
    
    def _ensure_healing_system(self) -> bool:
        """Lazy-load the healing system if backend is available."""
        if self.healing_system is not None:
            return True
        
        if not self.enable_healing:
            return False
        
        try:
            # Try to connect to backend to get database session
            import requests
            from sqlalchemy.orm import Session
            from database.connection import DatabaseConnection
            
            # Check if backend is running
            try:
                response = requests.get(
                    f"http://localhost:{self.backend_port}/health",
                    timeout=2
                )
                if response.status_code != 200:
                    return False
            except Exception:
                # Backend not available yet
                return False
            
            # Get database session
            from database.connection import get_db_session
            self.session = next(get_db_session())
            
            # Initialize healing system
            from cognitive.autonomous_healing_system import (
                get_autonomous_healing,
                TrustLevel
            )
            
            self.healing_system = get_autonomous_healing(
                session=self.session,
                repo_path=self.root_path,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )
            
            logger.info("✓ Launcher self-healing system connected to Grace's healing infrastructure")
            return True
            
        except Exception as e:
            logger.debug(f"Could not initialize healing system: {e}")
            return False
    
    def _ensure_notification_manager(self) -> bool:
        """Lazy-load the notification manager."""
        if self.notification_manager is not None:
            return True
        
        if not self.enable_notifications:
            return False
        
        try:
            from diagnostic_machine.notifications import (
                get_notification_manager,
                NotificationPriority
            )
            self.notification_manager = get_notification_manager()
            return True
        except Exception as e:
            logger.debug(f"Could not initialize notification manager: {e}")
            return False
    
    def detect_and_heal_problem(
        self,
        error: Exception,
        context: Dict[str, Any],
        problem_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect a problem and attempt to heal it automatically.
        
        Args:
            error: The exception that occurred
            context: Context about where/when the error occurred
            problem_type: Optional pre-identified problem type
            
        Returns:
            Dict with healing results:
            {
                "healed": bool,
                "healing_action": str or None,
                "message": str,
                "requires_user": bool,
                "notification_sent": bool
            }
        """
        # Identify problem type
        if not problem_type:
            problem_type = self._identify_problem_type(error, context)
        
        logger.info(f"Grace detected a problem: {problem_type}. Attempting to understand and fix it...")
        
        # Check if we've tried to heal this before (avoid loops)
        issue_key = f"{problem_type}:{str(error)}"
        attempts = self.healing_attempts.get(issue_key, 0)
        if attempts >= self.max_attempts_per_issue:
            logger.warning(
                f"Grace has already tried to heal '{problem_type}' {attempts} times without success. "
                f"Notifying user instead of trying again."
            )
            return self._notify_user_no_healing_knowledge(
                problem_type=problem_type,
                error=error,
                context=context
            )
        
        self.healing_attempts[issue_key] = attempts + 1
        
        # Try to heal using knowledge base first
        healing_result = self._attempt_healing_with_knowledge_base(
            problem_type=problem_type,
            error=error,
            context=context
        )
        
        if healing_result.get("healed"):
            logger.info(f"✓ Grace successfully healed the problem: {problem_type}")
            return healing_result
        
        # If knowledge base couldn't fix it, try autonomous healing system
        if self._ensure_healing_system():
            healing_result = self._attempt_autonomous_healing(
                problem_type=problem_type,
                error=error,
                context=context
            )
            
            if healing_result.get("healed"):
                logger.info(f"✓ Grace successfully healed the problem using autonomous healing: {problem_type}")
                return healing_result
        
        # If all healing attempts failed, check if we have relevant knowledge
        has_knowledge = self._check_healing_knowledge(problem_type, error)
        
        if not has_knowledge:
            # No relevant knowledge - notify user
            logger.warning(
                f"Grace doesn't have knowledge to fix '{problem_type}'. "
                f"This is a new problem that Grace needs help with."
            )
            return self._notify_user_no_healing_knowledge(
                problem_type=problem_type,
                error=error,
                context=context
            )
        else:
            # We have knowledge but healing failed - might be a deeper issue
            logger.warning(
                f"Grace knows about '{problem_type}' but the healing attempt didn't work. "
                f"This might require manual intervention."
            )
            return self._notify_user_healing_failed(
                problem_type=problem_type,
                error=error,
                context=context,
                healing_result=healing_result
            )
    
    def _identify_problem_type(self, error: Exception, context: Dict[str, Any]) -> str:
        """Identify the type of problem from error and context."""
        error_msg = str(error).lower()
        error_type = type(error).__name__
        
        # Port conflicts
        if "port" in error_msg and ("already in use" in error_msg or "address already" in error_msg):
            return "port_conflict"
        
        # Missing files/directories
        if any(term in error_msg for term in ["not found", "does not exist", "missing", "no such file"]):
            if "backend" in error_msg or "app.py" in context.get("file", ""):
                return "missing_backend_file"
            elif "directory" in error_msg:
                return "missing_directory"
            else:
                return "missing_file"
        
        # Permission issues
        if any(term in error_msg for term in ["permission denied", "access denied", "not permitted"]):
            return "permission_denied"
        
        # Process crashes
        if error_type == "RuntimeError" and "process" in error_msg:
            if "died" in error_msg or "exited" in error_msg:
                return "process_crash"
            elif "didn't start" in error_msg:
                return "process_startup_failure"
        
        # Connection issues
        if any(term in error_msg for term in ["connection", "connect", "refused", "timeout"]):
            return "connection_failure"
        
        # Version mismatches
        if "version" in error_msg or error_type == "VersionMismatchError":
            return "version_mismatch"
        
        # Health check failures
        if "health" in error_msg or "unhealthy" in error_msg:
            return "health_check_failure"
        
        # Default
        return f"unknown_error:{error_type}"
    
    def _attempt_healing_with_knowledge_base(
        self,
        problem_type: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Attempt healing using Grace's healing knowledge base.
        
        Returns dict with healing results.
        """
        try:
            from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
            
            knowledge_base = get_healing_knowledge_base()
            error_message = str(error)
            
            # Map problem types to issue types
            issue_type_map = {
                "port_conflict": IssueType.PORT_CONFLICT,
                "missing_backend_file": IssueType.MISSING_FILE,
                "missing_directory": IssueType.MISSING_DIRECTORY,
                "permission_denied": IssueType.PERMISSION_ERROR,
                "process_crash": IssueType.PROCESS_FAILURE,
                "connection_failure": IssueType.CONNECTION_ERROR,
            }
            
            issue_type = issue_type_map.get(problem_type)
            
            if issue_type:
                # Check if we have a fix pattern
                fix_suggestion = knowledge_base.generate_fix_suggestion(
                    issue_type=issue_type,
                    error_message=error_message,
                    file_path=context.get("file", ""),
                    line_number=context.get("line")
                )
                
                if fix_suggestion.get("fix_available"):
                    # Execute the fix
                    healing_action = self._execute_launcher_healing_fix(
                        problem_type=problem_type,
                        fix_suggestion=fix_suggestion,
                        context=context
                    )
                    
                    if healing_action.get("success"):
                        return {
                            "healed": True,
                            "healing_action": fix_suggestion.get("fix_type", "knowledge_base_fix"),
                            "message": healing_action.get("message", "Problem fixed using healing knowledge base"),
                            "requires_user": False,
                            "notification_sent": False
                        }
            
        except Exception as e:
            logger.debug(f"Healing knowledge base check failed: {e}")
        
        return {"healed": False}
    
    def _attempt_autonomous_healing(
        self,
        problem_type: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt healing using autonomous healing system."""
        try:
            # Create anomaly for healing system
            anomaly = {
                "type": self._map_problem_to_anomaly_type(problem_type),
                "severity": "critical" if problem_type in ["process_crash", "missing_backend_file"] else "warning",
                "details": f"Launcher error: {str(error)}",
                "service": "launcher",
                "error_message": str(error),
                "context": context
            }
            
            # Get healing decisions
            decisions = self.healing_system.decide_healing_actions([anomaly])
            
            if not decisions:
                return {"healed": False}
            
            # Execute healing
            results = self.healing_system.execute_healing(decisions)
            
            if results.get("executed"):
                executed = results["executed"][0]
                if executed.get("status") in ["success", "llm_guided"]:
                    return {
                        "healed": True,
                        "healing_action": executed.get("action", "autonomous_healing"),
                        "message": executed.get("message", "Problem fixed using autonomous healing"),
                        "requires_user": False,
                        "notification_sent": False
                    }
        
        except Exception as e:
            logger.debug(f"Autonomous healing attempt failed: {e}")
        
        return {"healed": False}
    
    def _map_problem_to_anomaly_type(self, problem_type: str) -> str:
        """Map launcher problem types to healing system anomaly types."""
        from cognitive.autonomous_healing_system import AnomalyType
        
        mapping = {
            "port_conflict": AnomalyType.RESOURCE_EXHAUSTION,
            "missing_backend_file": AnomalyType.SERVICE_FAILURE,
            "missing_directory": AnomalyType.DATA_INCONSISTENCY,
            "permission_denied": AnomalyType.SECURITY_BREACH,
            "process_crash": AnomalyType.SERVICE_FAILURE,
            "connection_failure": AnomalyType.SERVICE_FAILURE,
            "version_mismatch": AnomalyType.DATA_INCONSISTENCY,
            "health_check_failure": AnomalyType.PERFORMANCE_DEGRADATION,
        }
        
        return mapping.get(problem_type, AnomalyType.ERROR_SPIKE).value
    
    def _execute_launcher_healing_fix(
        self,
        problem_type: str,
        fix_suggestion: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific launcher healing fix."""
        fix_type = fix_suggestion.get("fix_type", "")
        
        try:
            if problem_type == "port_conflict" and fix_type == "change_port":
                # Try to find an available port
                new_port = self._find_available_port()
                if new_port:
                    self.backend_port = new_port
                    logger.info(f"Grace automatically changed to port {new_port} to resolve the conflict")
                    return {
                        "success": True,
                        "message": f"Port conflict resolved by switching to port {new_port}"
                    }
            
            elif problem_type == "missing_directory" and fix_type == "create_directory":
                # Create missing directory
                missing_dir = context.get("path") or context.get("directory")
                if missing_dir:
                    Path(missing_dir).mkdir(parents=True, exist_ok=True)
                    logger.info(f"Grace created missing directory: {missing_dir}")
                    return {
                        "success": True,
                        "message": f"Created missing directory: {missing_dir}"
                    }
            
            elif problem_type == "process_startup_failure" and fix_type == "retry_start":
                # Retry process startup
                logger.info("Grace will retry starting the process...")
                return {
                    "success": True,
                    "message": "Process startup retry initiated"
                }
        
        except Exception as e:
            logger.error(f"Healing fix execution failed: {e}")
            return {"success": False, "message": str(e)}
        
        return {"success": False, "message": "Fix type not implemented"}
    
    def _find_available_port(self, start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(port):
                return port
        return None
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", port))
                return result != 0
        except Exception:
            return False
    
    def _check_healing_knowledge(self, problem_type: str, error: Exception) -> bool:
        """Check if Grace has knowledge about this problem type."""
        try:
            from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
            
            knowledge_base = get_healing_knowledge_base()
            
            # Map problem types
            issue_type_map = {
                "port_conflict": IssueType.PORT_CONFLICT,
                "missing_backend_file": IssueType.MISSING_FILE,
                "permission_denied": IssueType.PERMISSION_ERROR,
            }
            
            issue_type = issue_type_map.get(problem_type)
            if issue_type:
                # Check if we have patterns for this issue
                patterns = knowledge_base.get_all_fix_patterns()
                for pattern in patterns:
                    if pattern.issue_type == issue_type:
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _notify_user_no_healing_knowledge(
        self,
        problem_type: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Notify user that Grace doesn't have knowledge to fix this problem."""
        if not self._ensure_notification_manager():
            # Fallback to console notification
            logger.error("")
            logger.error("=" * 70)
            logger.error("⚠ GRACE NEEDS YOUR HELP")
            logger.error("=" * 70)
            logger.error(f"Problem Type: {problem_type}")
            logger.error(f"Error: {str(error)}")
            logger.error(f"Context: {context}")
            logger.error("")
            logger.error("Grace encountered a problem that she doesn't know how to fix yet.")
            logger.error("This is a learning opportunity for Grace!")
            logger.error("=" * 70)
            logger.error("")
            
            return {
                "healed": False,
                "healing_action": None,
                "message": f"Grace doesn't have knowledge to fix '{problem_type}'. User notification displayed.",
                "requires_user": True,
                "notification_sent": True
            }
        
        # Send formal notification
        from diagnostic_machine.notifications import NotificationPriority
        
        notification_message = f"""
Grace encountered a problem during launcher startup that she cannot automatically fix:

Problem Type: {problem_type}
Error: {str(error)}
Location: {context.get('location', 'Unknown')}

Grace doesn't have relevant knowledge in her healing knowledge base to address this specific issue.

This is a new problem type that Grace needs to learn about. You may need to:
1. Manually fix the issue
2. Help Grace learn by documenting the solution
3. Check Grace's logs for more details

Context Information:
{self._format_context_for_notification(context)}
"""
        
        results = self.notification_manager.notify(
            title=f"Grace Needs Help: Unknown Problem Type '{problem_type}'",
            message=notification_message,
            priority=NotificationPriority.HIGH,
            details={
                "problem_type": problem_type,
                "error": str(error),
                "error_type": type(error).__name__,
                "context": context,
                "requires_manual_intervention": True
            },
            tags=["launcher", "self-healing", "knowledge_gap", problem_type]
        )
        
        return {
            "healed": False,
            "healing_action": None,
            "message": f"Grace notified user: No healing knowledge for '{problem_type}'",
            "requires_user": True,
            "notification_sent": len([r for r in results if r.status.value == "sent"]) > 0
        }
    
    def _notify_user_healing_failed(
        self,
        problem_type: str,
        error: Exception,
        context: Dict[str, Any],
        healing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Notify user that healing was attempted but failed."""
        if not self._ensure_notification_manager():
            logger.error("")
            logger.error("=" * 70)
            logger.error("⚠ GRACE HEALING ATTEMPT FAILED")
            logger.error("=" * 70)
            logger.error(f"Problem Type: {problem_type}")
            logger.error(f"Error: {str(error)}")
            logger.error(f"Healing Result: {healing_result}")
            logger.error("")
            logger.error("Grace tried to fix this problem but the healing attempt didn't work.")
            logger.error("Manual intervention may be required.")
            logger.error("=" * 70)
            logger.error("")
            
            return {
                "healed": False,
                "healing_action": healing_result.get("healing_action"),
                "message": "Healing attempt failed. User notification displayed.",
                "requires_user": True,
                "notification_sent": True
            }
        
        from diagnostic_machine.notifications import NotificationPriority
        
        notification_message = f"""
Grace attempted to automatically fix a problem but the healing attempt did not succeed:

Problem Type: {problem_type}
Error: {str(error)}
Healing Action Attempted: {healing_result.get('healing_action', 'Unknown')}

Grace knows about this type of problem and attempted to fix it, but the automatic fix didn't resolve the issue.

You may need to:
1. Manually investigate the root cause
2. Try the healing action manually
3. Check Grace's logs for more details

Context Information:
{self._format_context_for_notification(context)}
"""
        
        results = self.notification_manager.notify(
            title=f"Grace Healing Failed: '{problem_type}'",
            message=notification_message,
            priority=NotificationPriority.HIGH,
            details={
                "problem_type": problem_type,
                "error": str(error),
                "healing_result": healing_result,
                "context": context,
                "requires_manual_intervention": True
            },
            tags=["launcher", "self-healing", "healing_failed", problem_type]
        )
        
        return {
            "healed": False,
            "healing_action": healing_result.get("healing_action"),
            "message": f"Grace notified user: Healing failed for '{problem_type}'",
            "requires_user": True,
            "notification_sent": len([r for r in results if r.status.value == "sent"]) > 0
        }
    
    def _format_context_for_notification(self, context: Dict[str, Any]) -> str:
        """Format context dict for notification message."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"  • {key}: {value}")
            elif isinstance(value, (list, tuple)):
                lines.append(f"  • {key}: {', '.join(str(v) for v in value[:5])}")
            else:
                lines.append(f"  • {key}: {type(value).__name__}")
        return "\n".join(lines) if lines else "  (No additional context)"# Global instance
_launcher_self_healing: Optional[LauncherSelfHealing] = None


def get_launcher_self_healing(
    root_path: Path,
    backend_port: int = 8000,
    enable_healing: bool = True,
    enable_notifications: bool = True
) -> LauncherSelfHealing:
    """Get or create global launcher self-healing instance."""
    global _launcher_self_healing
    
    if _launcher_self_healing is None:
        _launcher_self_healing = LauncherSelfHealing(
            root_path=root_path,
            backend_port=backend_port,
            enable_healing=enable_healing,
            enable_notifications=enable_notifications
        )
    
    return _launcher_self_healing
