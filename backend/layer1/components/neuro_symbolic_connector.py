from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from layer1.message_bus import Layer1MessageBus, ComponentType, Message, get_message_bus
    MESSAGE_BUS_AVAILABLE = True
except ImportError:
    MESSAGE_BUS_AVAILABLE = False
    Layer1MessageBus = None
    ComponentType = None
    Message = None
    def get_message_bus():
        return None

try:
    from ml_intelligence.neuro_symbolic_reasoner import NeuroSymbolicReasoner
    from ml_intelligence.rule_storage import RuleStorage
    NEURO_SYMBOLIC_AVAILABLE = True
except ImportError:
    NEURO_SYMBOLIC_AVAILABLE = False
    NeuroSymbolicReasoner = None
    RuleStorage = None


class NeuroSymbolicConnector:
    """
    Connects Neuro-Symbolic Reasoner to Layer 1 message bus.
    
    Autonomous Actions:
    1. Query received → Perform unified neuro-symbolic reasoning
    2. Pattern detected → Auto-generate symbolic rules
    3. Rules generated → Store in learning memory
    4. High-trust rules → Notify other components
    """
    
    def __init__(
        self,
        reasoner: Optional[NeuroSymbolicReasoner] = None,
        rule_storage: Optional[RuleStorage] = None,
        message_bus: Optional[Layer1MessageBus] = None,
    ):
        """
        Initialize neuro-symbolic connector.
        
        Args:
            reasoner: NeuroSymbolicReasoner instance (creates if None and available)
            rule_storage: RuleStorage instance (creates if None and available)
            message_bus: Message bus instance
        """
        if not NEURO_SYMBOLIC_AVAILABLE:
            logger.warning("[NEURO-SYMBOLIC-CONNECTOR] Neuro-symbolic components not available")
            self.enabled = False
            return
        
        self.reasoner = reasoner
        self.rule_storage = rule_storage
        self.message_bus = message_bus or get_message_bus()
        self.enabled = True
        
        # Register component (use RAG component type for now)
        # Could add NEURO_SYMBOLIC to ComponentType enum in future
        self.message_bus.register_component(
            ComponentType.RAG,  # Use RAG for now since it's related
            self
        )
        
        logger.info("[NEURO-SYMBOLIC-CONNECTOR] Registered with message bus")
        
        # Set up autonomous actions
        self._register_autonomous_actions()
        self._register_request_handlers()
        self._subscribe_to_events()
    
    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================
    
    def _register_autonomous_actions(self):
        """Register all autonomous actions for neuro-symbolic reasoning."""
        
        if not self.enabled:
            return
        
        # 1. Auto-perform neuro-symbolic reasoning on queries
        self.message_bus.register_autonomous_action(
            trigger_event="rag.query_received",
            action=self._on_query_received,
            component=ComponentType.RAG,  # Use RAG component type
            description="Auto-perform neuro-symbolic reasoning on queries"
        )
        
        # 2. Auto-generate rules from detected patterns
        self.message_bus.register_autonomous_action(
            trigger_event="memory_mesh.pattern_detected",
            action=self._on_pattern_detected,
            component=ComponentType.RAG,  # Use RAG component type
            description="Auto-generate symbolic rules from patterns"
        )
        
        # 3. Auto-store generated rules
        self.message_bus.register_autonomous_action(
            trigger_event="neuro_symbolic.rules_generated",
            action=self._on_rules_generated,
            component=ComponentType.RAG,  # Use RAG component type
            description="Auto-store generated rules in learning memory"
        )
        
        logger.info("[NEURO-SYMBOLIC-CONNECTOR] ⭐ Registered 3 autonomous actions")
    
    # ================================================================
    # EVENT HANDLERS (Autonomous)
    # ================================================================
    
    async def _on_query_received(self, message: Message):
        """Handle query - perform neuro-symbolic reasoning."""
        if not self.enabled or not self.reasoner:
            return
        
        query = message.payload.get("query")
        context = message.payload.get("context", {})
        
        logger.info(f"[NEURO-SYMBOLIC-CONNECTOR] 🤖 Performing neuro-symbolic reasoning: {query[:50]}...")
        
        try:
            # Perform unified neuro-symbolic reasoning
            result = self.reasoner.reason(
                query=query,
                context=context,
                limit=10,
                include_trace=True
            )
            
            # Publish neuro-symbolic reasoning result
            await self.message_bus.publish(
                topic="neuro_symbolic.reasoning_complete",
                payload={
                    "query": query,
                    "neural_results_count": len(result.neural_results),
                    "symbolic_results_count": len(result.symbolic_results),
                    "fused_results_count": len(result.fused_results),
                    "fusion_confidence": result.fusion_confidence,
                    "timestamp": datetime.utcnow().isoformat()
                },
                from_component=ComponentType.RAG
            )
            
        except Exception as e:
            logger.error(f"[NEURO-SYMBOLIC-CONNECTOR] Reasoning failed: {e}")
    
    async def _on_pattern_detected(self, message: Message):
        """Handle pattern detection - generate symbolic rules."""
        if not self.enabled:
            return
        
        pattern_data = message.payload.get("pattern", {})
        pattern_id = message.payload.get("pattern_id")
        
        logger.info(f"[NEURO-SYMBOLIC-CONNECTOR] 🤖 Pattern detected: {pattern_id}")
        
        # Would need NeuralToSymbolicRuleGenerator to generate rules
        # For now, just log
        await self.message_bus.publish(
            topic="neuro_symbolic.pattern_received",
            payload={
                "pattern_id": pattern_id,
                "pattern_data": pattern_data,
                "timestamp": datetime.utcnow().isoformat()
            },
            from_component=ComponentType.RAG
        )
    
    async def _on_rules_generated(self, message: Message):
        """Handle rules generated - store in learning memory."""
        if not self.enabled or not self.rule_storage:
            return
        
        rules = message.payload.get("rules", [])
        
        logger.info(f"[NEURO-SYMBOLIC-CONNECTOR] 🤖 Storing {len(rules)} rules")
        
        try:
            # Store rules in learning memory
            stored_patterns = self.rule_storage.store_rules(
                rules,
                pattern_type="neural_symbolic"
            )
            
            # Publish storage result
            await self.message_bus.publish(
                topic="neuro_symbolic.rules_stored",
                payload={
                    "rules_count": len(stored_patterns),
                    "pattern_ids": [p.pattern_name for p in stored_patterns],
                    "timestamp": datetime.utcnow().isoformat()
                },
                from_component=ComponentType.RAG
            )
            
        except Exception as e:
            logger.error(f"[NEURO-SYMBOLIC-CONNECTOR] Rule storage failed: {e}")
    
    # ================================================================
    # REQUEST HANDLERS
    # ================================================================
    
    def _register_request_handlers(self):
        """Register request handlers for other components."""
        
        if not self.enabled:
            return
        
        self.message_bus.register_request_handler(
            component=ComponentType.RAG,  # Use RAG component type
            topic="neuro_symbolic_reason",
            handler=self._handle_neuro_symbolic_reason
        )
        
        logger.info("[NEURO-SYMBOLIC-CONNECTOR] 🔧 Registered 1 request handler")
    
    async def _handle_neuro_symbolic_reason(self, message: Message) -> Dict[str, Any]:
        """Handle neuro-symbolic reasoning request."""
        if not self.enabled or not self.reasoner:
            return {
                "error": "Neuro-symbolic reasoning not available",
                "results": []
            }
        
        query = message.payload.get("query")
        context = message.payload.get("context", {})
        limit = message.payload.get("limit", 10)
        
        try:
            # Perform unified reasoning
            result = self.reasoner.reason(
                query=query,
                context=context,
                limit=limit,
                include_trace=True
            )
            
            # Format results
            return {
                "query": query,
                "neural_results": [
                    {
                        "id": r.get("chunk_id") or r.get("id"),
                        "content": r.get("text") or r.get("content", ""),
                        "score": r.get("score", 0.0)
                    }
                    for r in result.neural_results
                ],
                "symbolic_results": [
                    {
                        "id": r.get("id"),
                        "content": r.get("text") or r.get("content", ""),
                        "trust_score": r.get("trust_score", 0.0)
                    }
                    for r in result.symbolic_results
                ],
                "fused_results": [
                    {
                        "id": r.get("chunk_id") or r.get("id"),
                        "content": r.get("text") or r.get("content", ""),
                        "fusion_score": r.get("fusion_score", 0.0),
                        "source": r.get("source", "unknown")
                    }
                    for r in result.fused_results
                ],
                "neural_confidence": result.neural_confidence,
                "symbolic_confidence": result.symbolic_confidence,
                "fusion_confidence": result.fusion_confidence
            }
            
        except Exception as e:
            logger.error(f"[NEURO-SYMBOLIC-CONNECTOR] Reasoning request failed: {e}")
            return {
                "error": str(e),
                "results": []
            }
    
    # ================================================================
    # SUBSCRIPTIONS
    # ================================================================
    
    def _subscribe_to_events(self):
        """Subscribe to events from other components."""
        
        if not self.enabled:
            return
        
        # Could subscribe to additional events here
        logger.info("[NEURO-SYMBOLIC-CONNECTOR] 📡 Subscribed to events via autonomous actions")


def create_neuro_symbolic_connector(
    reasoner: Optional[NeuroSymbolicReasoner] = None,
    rule_storage: Optional[RuleStorage] = None,
    message_bus: Optional[Layer1MessageBus] = None,
) -> NeuroSymbolicConnector:
    """
    Create and initialize neuro-symbolic connector.
    
    Args:
        reasoner: NeuroSymbolicReasoner instance
        rule_storage: RuleStorage instance
        message_bus: Message bus instance
        
    Returns:
        NeuroSymbolicConnector instance
    """
    connector = NeuroSymbolicConnector(
        reasoner=reasoner,
        rule_storage=rule_storage,
        message_bus=message_bus,
    )
    
    if connector.enabled:
        logger.info("[NEURO-SYMBOLIC-CONNECTOR] ✓ Initialized and connected to message bus")
    
    return connector
