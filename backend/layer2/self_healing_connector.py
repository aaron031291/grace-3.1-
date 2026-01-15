"""
Layer 2 Self-Healing Connector

Connects Grace's self-healing agent to:
- Layer 1 Message Bus (to act on Layer 1 information)
- LLM Orchestration (to query LLMs when needed)
- All Layer 1 components (RAG, Memory Mesh, Genesis Keys, etc.)

This makes the self-healing agent a Layer 2 component that can:
1. Monitor Layer 1 events and messages
2. Query LLMs when encountering problems
3. Act on information from Layer 1 components
4. Coordinate healing across the entire system
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from layer1.message_bus import (
    Layer1MessageBus,
    ComponentType,
    Message,
    MessageType,
    get_message_bus
)
from cognitive.devops_healing_agent import DevOpsHealingAgent
from llm_orchestrator.llm_orchestrator import LLMOrchestrator, TaskType

logger = logging.getLogger(__name__)

# Thread pool for async operations
_executor = ThreadPoolExecutor(max_workers=4)


class SelfHealingConnector:
    """
    Layer 2 connector for Grace's self-healing agent.
    
    Connects to:
    - Layer 1 Message Bus (subscribe to events, request information)
    - LLM Orchestration (query LLMs when needed)
    - All Layer 1 components (via message bus)
    """
    
    def __init__(
        self,
        self_healing_agent: DevOpsHealingAgent,
        llm_orchestrator: Optional[LLMOrchestrator] = None,
        message_bus: Optional[Layer1MessageBus] = None
    ):
        """
        Initialize Layer 2 self-healing connector.
        
        Args:
            self_healing_agent: Grace's DevOps healing agent
            llm_orchestrator: LLM orchestrator for querying LLMs
            message_bus: Layer 1 message bus
        """
        self.self_healing_agent = self_healing_agent
        self.llm_orchestrator = llm_orchestrator
        self.message_bus = message_bus or get_message_bus()
        
        # Track Layer 1 component health
        self.layer1_component_health = {}
        self.layer1_issues = []
        
        # Register with message bus (as Layer 2 component)
        # Note: We'll add SELF_HEALING to ComponentType if needed
        try:
            self.message_bus.register_component(
                ComponentType.AUTONOMOUS_LEARNING,  # Use existing type for now
                self
            )
        except Exception as e:
            logger.warning(f"[LAYER2-SELF-HEALING] Could not register with message bus: {e}")
        
        logger.info("[LAYER2-SELF-HEALING] Self-healing connector initialized")
        
        # Set up Layer 1 subscriptions and handlers
        self._subscribe_to_layer1_events()
        self._register_request_handlers()
    
    def _subscribe_to_layer1_events(self):
        """Subscribe to Layer 1 events to monitor system health."""
        # Subscribe to error events
        self.message_bus.subscribe(
            topic="*.error",
            handler=self._handle_layer1_error
        )
        
        # Subscribe to health check events
        self.message_bus.subscribe(
            topic="*.health_check",
            handler=self._handle_layer1_health_check
        )
        
        # Subscribe to component failures
        self.message_bus.subscribe(
            topic="*.component_failure",
            handler=self._handle_component_failure
        )
        
        # Subscribe to RAG retrieval failures
        self.message_bus.subscribe(
            topic="rag.retrieval_failed",
            handler=self._handle_rag_failure
        )
        
        # Subscribe to database errors
        self.message_bus.subscribe(
            topic="*.database_error",
            handler=self._handle_database_error
        )
        
        # Subscribe to ingestion failures
        self.message_bus.subscribe(
            topic="ingestion.processing_failed",
            handler=self._handle_ingestion_failure
        )
        
        logger.info("[LAYER2-SELF-HEALING] Subscribed to Layer 1 events")
    
    def _register_request_handlers(self):
        """Register request handlers for Layer 1 components."""
        # Handle healing requests from Layer 1
        self.message_bus.register_request_handler(
            component=ComponentType.AUTONOMOUS_LEARNING,
            topic="request_healing",
            handler=self._handle_healing_request
        )
        
        # Handle health check requests
        self.message_bus.register_request_handler(
            component=ComponentType.AUTONOMOUS_LEARNING,
            topic="check_system_health",
            handler=self._handle_health_check_request
        )
        
        logger.info("[LAYER2-SELF-HEALING] Registered request handlers")
    
    # ================================================================
    # LAYER 1 EVENT HANDLERS
    # ================================================================
    
    async def _handle_layer1_error(self, message: Message):
        """Handle errors from Layer 1 components."""
        component = message.from_component.value
        error_info = message.payload
        
        logger.warning(f"[LAYER2-SELF-HEALING] Layer 1 error from {component}: {error_info.get('error', 'Unknown')}")
        
        # Record issue
        issue = {
            "component": component,
            "type": "layer1_error",
            "error": error_info.get("error"),
            "context": error_info.get("context", {}),
            "timestamp": datetime.now()
        }
        self.layer1_issues.append(issue)
        
        # Attempt to heal
        try:
            result = await self._heal_layer1_issue(issue)
            if result.get("success"):
                logger.info(f"[LAYER2-SELF-HEALING] Fixed Layer 1 issue in {component}")
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] Failed to heal Layer 1 issue: {e}")
    
    async def _handle_layer1_health_check(self, message: Message):
        """Handle health check results from Layer 1 components."""
        component = message.from_component.value
        health_status = message.payload.get("status", "unknown")
        
        self.layer1_component_health[component] = {
            "status": health_status,
            "timestamp": datetime.now(),
            "details": message.payload.get("details", {})
        }
        
        # If unhealthy, trigger healing
        if health_status in ("unhealthy", "critical", "failing"):
            logger.warning(f"[LAYER2-SELF-HEALING] Component {component} is {health_status}")
            await self._handle_layer1_error(message)
    
    async def _handle_component_failure(self, message: Message):
        """Handle component failure events."""
        component = message.from_component.value
        failure_info = message.payload
        
        logger.error(f"[LAYER2-SELF-HEALING] Component failure: {component}")
        
        # Create critical issue
        issue = {
            "component": component,
            "type": "component_failure",
            "failure_info": failure_info,
            "timestamp": datetime.now(),
            "priority": "critical"
        }
        
        # Attempt immediate healing
        try:
            result = await self._heal_layer1_issue(issue)
            if not result.get("success"):
                # If healing fails, query LLM for help
                await self._query_llm_for_healing(issue)
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] Failed to handle component failure: {e}")
            await self._query_llm_for_healing(issue)
    
    async def _handle_rag_failure(self, message: Message):
        """Handle RAG retrieval failures."""
        failure_info = message.payload
        
        issue = {
            "component": "rag",
            "type": "retrieval_failure",
            "query": failure_info.get("query"),
            "error": failure_info.get("error"),
            "timestamp": datetime.now()
        }
        
        await self._heal_layer1_issue(issue)
    
    async def _handle_database_error(self, message: Message):
        """Handle database errors."""
        error_info = message.payload
        
        issue = {
            "component": "database",
            "type": "database_error",
            "error": error_info.get("error"),
            "operation": error_info.get("operation"),
            "timestamp": datetime.now()
        }
        
        await self._heal_layer1_issue(issue)
    
    async def _handle_ingestion_failure(self, message: Message):
        """Handle ingestion processing failures."""
        failure_info = message.payload
        
        issue = {
            "component": "ingestion",
            "type": "ingestion_failure",
            "file": failure_info.get("file"),
            "error": failure_info.get("error"),
            "timestamp": datetime.now()
        }
        
        await self._heal_layer1_issue(issue)
    
    # ================================================================
    # REQUEST HANDLERS
    # ================================================================
    
    async def _handle_healing_request(self, message: Message) -> Dict[str, Any]:
        """Handle healing requests from Layer 1 components."""
        request = message.payload
        issue_description = request.get("issue_description")
        context = request.get("context", {})
        
        logger.info(f"[LAYER2-SELF-HEALING] Healing request: {issue_description}")
        
        # Use self-healing agent
        try:
            result = self.self_healing_agent.detect_and_heal(
                issue_description=issue_description,
                context=context
            )
            return result
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] Healing request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_health_check_request(self, message: Message) -> Dict[str, Any]:
        """Handle health check requests."""
        return {
            "layer1_components": self.layer1_component_health,
            "recent_issues": self.layer1_issues[-10:],  # Last 10 issues
            "total_issues": len(self.layer1_issues)
        }
    
    # ================================================================
    # HEALING METHODS
    # ================================================================
    
    async def _heal_layer1_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to heal a Layer 1 issue."""
        component = issue.get("component")
        issue_type = issue.get("type")
        
        # Build issue description
        issue_description = f"Layer 1 {component} issue: {issue_type}"
        if issue.get("error"):
            issue_description += f" - {issue.get('error')}"
        
        # Use self-healing agent
        try:
            result = self.self_healing_agent.detect_and_heal(
                issue_description=issue_description,
                context={
                    "layer1_issue": issue,
                    "component": component,
                    "issue_type": issue_type
                }
            )
            return result
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] Healing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _query_llm_for_healing(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Query LLM for help with healing."""
        if not self.llm_orchestrator:
            logger.warning("[LAYER2-SELF-HEALING] LLM orchestrator not available")
            return None
        
        # Build prompt for LLM
        component = issue.get("component", "unknown")
        issue_type = issue.get("type", "unknown")
        error = issue.get("error", issue.get("failure_info", {}).get("error", "Unknown error"))
        
        prompt = f"""
I'm Grace, an autonomous self-healing system. I've encountered an issue that I couldn't fix automatically.

Component: {component}
Issue Type: {issue_type}
Error: {error}

Please provide:
1. A diagnosis of what might be causing this issue
2. Step-by-step instructions on how to fix it
3. Any code changes or configuration updates needed
4. How to verify the fix worked

Context: {issue.get('context', {})}
"""
        
        try:
            logger.info(f"[LAYER2-SELF-HEALING] Querying LLM for healing help...")
            
            # Query LLM via orchestrator
            result = self.llm_orchestrator.execute_task(
                prompt=prompt,
                task_type=TaskType.DEBUGGING,
                require_verification=True,
                require_grounding=True,
                system_prompt="You are helping Grace, an autonomous self-healing system, debug and fix issues."
            )
            
            if result.success:
                logger.info(f"[LAYER2-SELF-HEALING] LLM provided healing guidance")
                
                # Extract guidance from LLM response
                guidance = result.content
                
                # Try to apply the guidance
                # (This could be enhanced to parse and execute LLM suggestions)
                logger.info(f"[LAYER2-SELF-HEALING] LLM Guidance: {guidance[:200]}...")
                
                return {
                    "success": True,
                    "guidance": guidance,
                    "llm_response": result
                }
            else:
                logger.warning(f"[LAYER2-SELF-HEALING] LLM query failed")
                return None
                
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] LLM query error: {e}")
            return None
    
    # ================================================================
    # LAYER 1 INFORMATION ACCESS
    # ================================================================
    
    async def get_layer1_info(self, component: str, info_type: str) -> Optional[Dict[str, Any]]:
        """Get information from Layer 1 components."""
        try:
            # Map component names to ComponentType
            component_map = {
                "rag": ComponentType.RAG,
                "memory_mesh": ComponentType.MEMORY_MESH,
                "genesis_keys": ComponentType.GENESIS_KEYS,
                "ingestion": ComponentType.INGESTION,
                "llm_orchestration": ComponentType.LLM_ORCHESTRATION
            }
            
            component_type = component_map.get(component.lower())
            if not component_type:
                logger.warning(f"[LAYER2-SELF-HEALING] Unknown component: {component}")
                return None
            
            # Request information from Layer 1 component
            response = await self.message_bus.request(
                to_component=component_type,
                topic=f"get_{info_type}",
                payload={},
                from_component=ComponentType.AUTONOMOUS_LEARNING,
                timeout=10.0
            )
            
            return response
            
        except Exception as e:
            logger.error(f"[LAYER2-SELF-HEALING] Failed to get Layer 1 info: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get self-healing connector statistics."""
        return {
            "layer1_component_health": self.layer1_component_health,
            "total_layer1_issues": len(self.layer1_issues),
            "recent_issues": self.layer1_issues[-5:],
            "connected_to_llm": self.llm_orchestrator is not None,
            "connected_to_layer1": self.message_bus is not None
        }
