"""
Error Learning Integration - Feed Errors to Self-Healing Pipeline

Automatically captures errors and feeds them into Grace's learning and self-healing systems
so they can be learned from and fixed automatically in the future.
"""

import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ErrorLearningIntegration:
    """
    Integrates error handling with Grace's learning and self-healing systems.
    
    When errors occur, they are:
    1. Tracked with Genesis Keys
    2. Fed into Learning Memory
    3. Triggered for self-healing
    4. Stored for pattern recognition
    """
    
    def __init__(
        self,
        session: Optional[Session] = None,
        genesis_service=None,
        learning_manager=None,
        healing_system=None
    ):
        """
        Initialize error learning integration.
        
        Args:
            session: Database session
            genesis_service: Genesis Key service (optional, will get if None)
            learning_manager: Learning Memory Manager (optional, will get if None)
            healing_system: Self-Healing System (optional, will get if None)
        """
        self.session = session
        
        # Lazy load services
        self._genesis_service = genesis_service
        self._learning_manager = learning_manager
        self._healing_system = healing_system
    
    @property
    def genesis_service(self):
        """Get or create Genesis service."""
        if self._genesis_service is None:
            try:
                from genesis.genesis_key_service import get_genesis_service
                self._genesis_service = get_genesis_service(session=self.session)
            except Exception as e:
                logger.warning(f"[ERROR-LEARNING] Could not get Genesis service: {e}")
                return None
        return self._genesis_service
    
    @property
    def learning_manager(self):
        """Get or create Learning Memory Manager."""
        if self._learning_manager is None:
            try:
                from cognitive.learning_memory import LearningMemoryManager
                self._learning_manager = LearningMemoryManager(session=self.session)
            except Exception as e:
                logger.warning(f"[ERROR-LEARNING] Could not get Learning Manager: {e}")
                return None
        return self._learning_manager
    
    @property
    def healing_system(self):
        """Get or create Self-Healing System."""
        if self._healing_system is None:
            try:
                from cognitive.autonomous_healing_system import get_autonomous_healing
                self._healing_system = get_autonomous_healing(session=self.session)
            except Exception as e:
                logger.warning(f"[ERROR-LEARNING] Could not get Healing System: {e}")
                return None
        return self._healing_system
    
    def record_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        component: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Record an error and feed it into the learning/healing pipeline.
        
        Args:
            error: The exception that occurred
            context: Context about where/when/why the error happened
            component: Component name (e.g., "llm_orchestrator", "memory_retrieval")
            severity: Error severity ("low", "medium", "high", "critical")
            user_id: User ID if available
            session_id: Session ID if available
            
        Returns:
            Genesis Key ID if successfully recorded, None otherwise
        """
        try:
            error_type = type(error).__name__
            error_message = str(error)
            error_traceback = traceback.format_exc()
            
            # Create Genesis Key for error
            genesis_key_id = None
            if self.genesis_service:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    
                    key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.ERROR,  # Use ERROR instead of SYSTEM_ERROR
                        what_description=f"Error in {component}: {error_type}",
                        who_actor=component,
                        where_location=context.get("location", component),
                        why_reason=context.get("reason", "System error occurred"),
                        how_method=context.get("method", "error_occurred"),
                        is_error=True,
                        error_type=error_type,
                        error_message=error_message,
                        error_traceback=error_traceback,
                        input_data={
                            "component": component,
                            "severity": severity,
                            "context": context
                        },
                        output_data={
                            "error_type": error_type,
                            "error_message": error_message,
                            "severity": severity
                        },
                        context_data={
                            "component": component,
                            "severity": severity,
                            **context
                        },
                        tags=["error", "learning", component, severity],
                        user_id=user_id,
                        session_id=session_id,
                        session=self.session
                    )
                    genesis_key_id = key.key_id
                    logger.info(f"[ERROR-LEARNING] Error recorded with Genesis Key: {genesis_key_id}")
                except Exception as e:
                    # Ensure logger is available even if there's an import issue
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"[ERROR-LEARNING] Failed to create Genesis Key: {e}")
            
            # Feed to Learning Memory
            if self.learning_manager:
                try:
                    learning_data = {
                        "context": {
                            "component": component,
                            "error_type": error_type,
                            "location": context.get("location", component),
                            "severity": severity
                        },
                        "action_taken": context.get("action", "error_occurred"),
                        "outcome": {
                            "success": False,
                            "error_type": error_type,
                            "error_message": error_message
                        },
                        "expected_outcome": {
                            "success": True
                        }
                    }
                    
                    self.learning_manager.ingest_learning_experience(
                        experience_type="error_occurred",
                        context=learning_data["context"],
                        action_taken=learning_data["action_taken"],
                        outcome=learning_data["outcome"],
                        expected_outcome=learning_data["expected_outcome"],
                        source="error_learning",
                        user_id=user_id,
                        genesis_key_id=genesis_key_id
                    )
                    logger.info(f"[ERROR-LEARNING] Error fed to Learning Memory")
                except Exception as e:
                    logger.warning(f"[ERROR-LEARNING] Failed to feed to Learning Memory: {e}")
            
            # Trigger self-healing if severity is high enough
            if severity in ["high", "critical"] and self.healing_system:
                try:
                    # Create anomaly for healing system
                    anomaly = {
                        "type": "error_pattern",
                        "severity": severity,
                        "component": component,
                        "error_type": error_type,
                        "error_message": error_message,
                        "details": f"Error in {component}: {error_type} - {error_message}",
                        "genesis_key_id": genesis_key_id
                    }
                    
                    # Trigger healing cycle
                    healing_result = self.healing_system.run_monitoring_cycle()
                    logger.info(f"[ERROR-LEARNING] Triggered healing cycle: {healing_result.get('actions_executed', 0)} actions")
                except Exception as e:
                    logger.warning(f"[ERROR-LEARNING] Failed to trigger healing: {e}")
            
            return genesis_key_id
            
        except Exception as e:
            logger.error(f"[ERROR-LEARNING] Failed to record error: {e}", exc_info=True)
            return None
    
    def record_warning(
        self,
        warning_message: str,
        context: Dict[str, Any],
        component: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Record a warning (lower severity than error).
        
        Args:
            warning_message: Warning message
            context: Context about the warning
            component: Component name
            user_id: User ID if available
            session_id: Session ID if available
            
        Returns:
            Genesis Key ID if successfully recorded, None otherwise
        """
        try:
            # Create a warning-level error
            class WarningError(Exception):
                pass
            
            warning_error = WarningError(warning_message)
            
            return self.record_error(
                error=warning_error,
                context=context,
                component=component,
                severity="low",
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"[ERROR-LEARNING] Failed to record warning: {e}")
            return None


def get_error_learning_integration(
    session: Optional[Session] = None,
    genesis_service=None,
    learning_manager=None,
    healing_system=None
) -> ErrorLearningIntegration:
    """
    Get or create error learning integration instance.
    
    Args:
        session: Database session
        genesis_service: Genesis service (optional)
        learning_manager: Learning manager (optional)
        healing_system: Healing system (optional)
        
    Returns:
        ErrorLearningIntegration instance
    """
    return ErrorLearningIntegration(
        session=session,
        genesis_service=genesis_service,
        learning_manager=learning_manager,
        healing_system=healing_system
    )
