"""
Coding Agent ↔ Self-Healing Bidirectional Communication Bridge

Enables bidirectional communication between:
1. Self-Healing System → Coding Agent (for code generation/fixes)
2. Coding Agent → Self-Healing System (for issue detection/healing)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AssistanceType(str, Enum):
    """Types of assistance requests."""
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_OPTIMIZE = "code_optimize"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    HEALING = "healing"
    DIAGNOSTIC = "diagnostic"
    CODE_ANALYSIS = "code_analysis"


class AssistanceRequest:
    """Request for assistance between systems."""
    
    def __init__(
        self,
        request_id: str,
        from_system: str,
        to_system: str,
        assistance_type: AssistanceType,
        description: str,
        context: Dict[str, Any],
        priority: str = "medium"
    ):
        self.request_id = request_id
        self.from_system = from_system
        self.to_system = to_system
        self.assistance_type = assistance_type
        self.description = description
        self.context = context
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.success: bool = False


class CodingAgentHealingBridge:
    """
    Bidirectional Communication Bridge.
    
    Enables:
    1. Self-Healing → Coding Agent: Request code generation/fixes
    2. Coding Agent → Self-Healing: Request healing/diagnostics
    """
    
    def __init__(
        self,
        coding_agent=None,
        healing_system=None
    ):
        """Initialize bidirectional bridge."""
        self.coding_agent = coding_agent
        self.healing_system = healing_system
        
        # Request tracking
        self.pending_requests: Dict[str, AssistanceRequest] = {}
        self.completed_requests: List[AssistanceRequest] = []
        
        logger.info("[BRIDGE] Initialized Coding Agent ↔ Self-Healing Bridge")
    
    # ==================== SELF-HEALING → CODING AGENT ====================
    
    def healing_request_coding_assistance(
        self,
        assistance_type: AssistanceType,
        description: str,
        context: Dict[str, Any],
        priority: str = "high"
    ) -> Dict[str, Any]:
        """
        Self-Healing System requests assistance from Coding Agent.
        
        Use cases:
        - Need code generation for fixes
        - Need code refactoring
        - Need code optimization
        - Need code review
        """
        if not self.coding_agent:
            return {"success": False, "error": "Coding agent not available"}
        
        try:
            # Create request
            request_id = f"healing_req_{datetime.utcnow().timestamp()}"
            request = AssistanceRequest(
                request_id=request_id,
                from_system="self_healing",
                to_system="coding_agent",
                assistance_type=assistance_type,
                description=description,
                context=context,
                priority=priority
            )
            
            self.pending_requests[request_id] = request
            
            # Map assistance type to coding task type
            task_type_map = {
                AssistanceType.CODE_GENERATION: "code_generation",
                AssistanceType.CODE_FIX: "code_fix",
                AssistanceType.CODE_REFACTOR: "code_refactor",
                AssistanceType.CODE_OPTIMIZE: "code_optimize",
                AssistanceType.CODE_REVIEW: "code_review",
                AssistanceType.BUG_FIX: "bug_fix"
            }
            
            task_type = task_type_map.get(assistance_type, "code_generation")
            
            # Create coding task
            from cognitive.enterprise_coding_agent import CodingTaskType
            coding_task_type = CodingTaskType(task_type)
            
            task = self.coding_agent.create_task(
                task_type=coding_task_type,
                description=description,
                target_files=context.get("target_files", []),
                requirements=context.get("requirements", {}),
                context=context,
                priority=priority,
                trust_level_required=context.get("trust_level_required")
            )
            
            # Execute task
            result = self.coding_agent.execute_task(task.task_id)
            
            # Update request
            request.completed_at = datetime.utcnow()
            request.result = result
            request.success = result.get("success", False)
            
            self.completed_requests.append(request)
            del self.pending_requests[request_id]
            
            logger.info(
                f"[BRIDGE] Self-Healing → Coding Agent: {assistance_type.value} "
                f"completed, success={request.success}"
            )
            
            return {
                "success": request.success,
                "request_id": request_id,
                "task_id": task.task_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"[BRIDGE] Self-Healing → Coding Agent error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== CODING AGENT → SELF-HEALING ====================
    
    def coding_agent_request_healing_assistance(
        self,
        issue_description: str,
        affected_files: List[str],
        issue_type: str = "code_issue",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Coding Agent requests assistance from Self-Healing System.
        
        Use cases:
        - Code generation failed
        - Code has issues that need healing
        - Need diagnostic analysis
        - Need code analysis
        """
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            # Create request
            request_id = f"coding_req_{datetime.utcnow().timestamp()}"
            request = AssistanceRequest(
                request_id=request_id,
                from_system="coding_agent",
                to_system="self_healing",
                assistance_type=AssistanceType.HEALING,
                description=issue_description,
                context={
                    "affected_files": affected_files,
                    "issue_type": issue_type
                },
                priority=priority
            )
            
            self.pending_requests[request_id] = request
            
            # Request healing - use decide_healing_actions and execute_healing
            anomaly = {
                "type": issue_type,
                "severity": priority,
                "description": issue_description,
                "affected_files": affected_files,
                "details": issue_description
            }
            
            # Decide healing actions
            decisions = self.healing_system.decide_healing_actions([anomaly])
            
            # Execute healing
            healing_result = self.healing_system.execute_healing(
                decisions=decisions,
                user_id="coding_agent"
            )
            
            # Update request
            request.completed_at = datetime.utcnow()
            request.result = healing_result
            request.success = healing_result.get("success", False)
            
            self.completed_requests.append(request)
            del self.pending_requests[request_id]
            
            logger.info(
                f"[BRIDGE] Coding Agent → Self-Healing: healing request "
                f"completed, success={request.success}"
            )
            
            return {
                "success": request.success,
                "request_id": request_id,
                "result": healing_result
            }
            
        except Exception as e:
            logger.error(f"[BRIDGE] Coding Agent → Self-Healing error: {e}")
            return {"success": False, "error": str(e)}
    
    def coding_agent_request_diagnostic(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coding Agent requests diagnostic analysis."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            # Use diagnostic engine if available
            if hasattr(self.healing_system, 'diagnostic_engine') and self.healing_system.diagnostic_engine:
                diagnostic_result = self.healing_system.diagnostic_engine.analyze_system_health()
                return {
                    "success": True,
                    "diagnostic": diagnostic_result
                }
            else:
                # Fallback to health assessment
                health_result = self.healing_system.assess_system_health()
                return {
                    "success": True,
                    "health": health_result
                }
                
        except Exception as e:
            logger.error(f"[BRIDGE] Diagnostic request error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== REQUEST TRACKING ====================
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending assistance requests."""
        return [
            {
                "request_id": req.request_id,
                "from_system": req.from_system,
                "to_system": req.to_system,
                "assistance_type": req.assistance_type.value,
                "description": req.description,
                "priority": req.priority,
                "created_at": req.created_at.isoformat()
            }
            for req in self.pending_requests.values()
        ]
    
    def get_completed_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get completed assistance requests."""
        return [
            {
                "request_id": req.request_id,
                "from_system": req.from_system,
                "to_system": req.to_system,
                "assistance_type": req.assistance_type.value,
                "description": req.description,
                "success": req.success,
                "created_at": req.created_at.isoformat(),
                "completed_at": req.completed_at.isoformat() if req.completed_at else None
            }
            for req in self.completed_requests[-limit:]
        ]


def get_coding_agent_healing_bridge(
    coding_agent=None,
    healing_system=None
) -> CodingAgentHealingBridge:
    """Factory function to get bidirectional bridge."""
    return CodingAgentHealingBridge(
        coding_agent=coding_agent,
        healing_system=healing_system
    )
