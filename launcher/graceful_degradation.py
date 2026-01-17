"""
Graceful Degradation Manager for Enterprise Launcher

Manages system operation in degraded mode when optional services are unavailable.
Similar to Netflix's chaos engineering and resilience patterns.
"""

import logging
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OperationalMode(Enum):
    """System operational modes."""
    FULL = "full"                    # All services available
    DEGRADED = "degraded"            # Some optional services unavailable
    MINIMAL = "minimal"              # Only core services available
    UNAVAILABLE = "unavailable"     # Core services unavailable


@dataclass
class ServiceState:
    """State of a service."""
    name: str
    available: bool
    degraded: bool = False
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class GracefulDegradationManager:
    """
    Manages graceful degradation of services.
    
    Features:
    - Tracks service availability
    - Determines operational mode
    - Provides fallback strategies
    - Automatic recovery detection
    """
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self.service_states: Dict[str, ServiceState] = {}
        self.core_services = {"backend", "database"}
        self.optional_services = {"qdrant", "ollama", "frontend"}
        self.operational_mode = OperationalMode.UNAVAILABLE
    
    def register_service(self, name: str, available: bool, reason: Optional[str] = None):
        """
        Register service state.
        
        Args:
            name: Service name
            available: Whether service is available
            reason: Optional reason for unavailability
        """
        self.service_states[name] = ServiceState(
            name=name,
            available=available,
            degraded=not available and name in self.optional_services,
            reason=reason
        )
        
        # Update operational mode
        self._update_operational_mode()
        
        if not available:
            logger.warning(
                f"[DEGRADATION] Service '{name}' unavailable: {reason or 'Unknown reason'}"
            )
    
    def _update_operational_mode(self):
        """Update operational mode based on service states."""
        # Check core services
        core_available = all(
            self.service_states.get(s, ServiceState(s, False)).available
            for s in self.core_services
        )
        
        if not core_available:
            self.operational_mode = OperationalMode.UNAVAILABLE
            return
        
        # Check optional services
        optional_available = sum(
            1 for s in self.optional_services
            if self.service_states.get(s, ServiceState(s, False)).available
        )
        
        if optional_available == len(self.optional_services):
            self.operational_mode = OperationalMode.FULL
        elif optional_available > 0:
            self.operational_mode = OperationalMode.DEGRADED
        else:
            self.operational_mode = OperationalMode.MINIMAL
    
    def can_operate(self) -> bool:
        """Check if system can operate (core services available)."""
        return self.operational_mode != OperationalMode.UNAVAILABLE
    
    def get_operational_mode(self) -> OperationalMode:
        """Get current operational mode."""
        return self.operational_mode
    
    def get_degraded_services(self) -> Set[str]:
        """Get set of degraded services."""
        return {
            name for name, state in self.service_states.items()
            if state.degraded or (not state.available and name in self.optional_services)
        }
    
    def get_status_summary(self) -> Dict[str, any]:
        """Get comprehensive status summary."""
        return {
            "operational_mode": self.operational_mode.value,
            "can_operate": self.can_operate(),
            "core_services": {
                name: {
                    "available": self.service_states.get(name, ServiceState(name, False)).available,
                    "degraded": self.service_states.get(name, ServiceState(name, False)).degraded
                }
                for name in self.core_services
            },
            "optional_services": {
                name: {
                    "available": self.service_states.get(name, ServiceState(name, False)).available,
                    "degraded": self.service_states.get(name, ServiceState(name, False)).degraded,
                    "reason": self.service_states.get(name, ServiceState(name, False)).reason
                }
                for name in self.optional_services
            },
            "degraded_count": len(self.get_degraded_services()),
            "available_count": sum(
                1 for state in self.service_states.values() if state.available
            )
        }
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get system capabilities based on available services."""
        states = self.service_states
        
        return {
            "api_available": states.get("backend", ServiceState("backend", False)).available,
            "database_available": states.get("database", ServiceState("database", False)).available,
            "vector_search_available": states.get("qdrant", ServiceState("qdrant", False)).available,
            "llm_chat_available": states.get("ollama", ServiceState("ollama", False)).available,
            "frontend_available": states.get("frontend", ServiceState("frontend", False)).available,
            "document_ingestion_available": (
                states.get("qdrant", ServiceState("qdrant", False)).available and
                states.get("backend", ServiceState("backend", False)).available
            ),
            "full_rag_available": (
                states.get("qdrant", ServiceState("qdrant", False)).available and
                states.get("ollama", ServiceState("ollama", False)).available and
                states.get("backend", ServiceState("backend", False)).available
            )
        }
