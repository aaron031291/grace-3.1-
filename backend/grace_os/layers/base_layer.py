"""
Grace OS — Base Layer

The abstract base class that all 9 processing layers implement. 
It encapsulates the mesh architecture connection details, leaving the 
concrete classes to focus on their specific logic.
"""

from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Any, Dict, List, Optional
import time

from ..kernel.message_bus import MessageBus
from ..kernel.layer_registry import LayerRegistry
from ..kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

class BaseLayer(ABC):
    """
    Abstract Base Class for all Grace OS Layers.
    """
    
    def __init__(self, bus: MessageBus, registry: LayerRegistry):
        self.bus = bus
        self.registry = registry
        self._is_running = False

    @property
    @abstractmethod
    def layer_name(self) -> str:
        """e.g., 'L3_Proposer'"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """e.g., ['propose_solutions', 'brainstorming']"""
        pass

    @property
    @abstractmethod
    def accepted_message_types(self) -> List[str]:
        """e.g., ['request_proposals']"""
        pass

    def start(self):
        """
        Register with the registry and subscribe to the message bus.
        """
        if self._is_running:
            return
            
        logger.info(f"[{self.layer_name}] Starting layer...")
        
        # Register capabilities
        self.registry.register(
            layer_name=self.layer_name, 
            capabilities=self.capabilities, 
            instance=self
        )
        
        # Subscribe to message types
        for msg_type in self.accepted_message_types:
            self.bus.subscribe(msg_type, self._on_message_received)
            
        self._is_running = True
        logger.info(f"[{self.layer_name}] Started and listening on {self.accepted_message_types}")

    def stop(self):
        """
        Deregister and unsubscribe.
        """
        if not self._is_running:
            return
            
        logger.info(f"[{self.layer_name}] Stopping layer...")
        
        self.registry.deregister(self.layer_name)
        for msg_type in self.accepted_message_types:
            self.bus.unsubscribe(msg_type, self._on_message_received)
            
        self._is_running = False
        logger.info(f"[{self.layer_name}] Stopped")

    async def send_message(
        self, 
        to_layer: str, 
        message_type: str, 
        payload: Dict[str, Any], 
        trace_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        priority: int = 0,
        current_depth: int = 10
    ) -> LayerResponse:
        """
        Helper method for layers to send messages.
        """
        msg = LayerMessage(
            from_layer=self.layer_name,
            to_layer=to_layer,
            message_type=message_type,
            payload=payload,
            trace_id=trace_id or "",  # In a real app we'd auto-propagate this
            parent_message_id=parent_message_id,
            priority=priority,
            max_depth=current_depth - 1
        )
        logger.debug(f"[{self.layer_name}] Sending '{message_type}' to '{to_layer}'")
        return await self.bus.send(msg)

    async def _on_message_received(self, message: LayerMessage) -> LayerResponse:
        """
        Internal wrapper around the abstract `handle_message`.
        Performs target validation.
        """
        # Validate that we are the intended recipient
        # Allow processing if it's a broadcast ("*") or explicitly targeted to us.
        if message.to_layer != "*" and message.to_layer != self.layer_name:
            return self.bus._build_error_response(message, "ignored", "Not intended for this layer")
            
        logger.debug(f"[{self.layer_name}] Received message: {message.message_type} from {message.from_layer}")
        
        # Update heartbeat on activity
        self.registry.heartbeat(self.layer_name)
        
        # Delegate to concrete implementation. 
        # Exceptions intentionally bubble up so the MessageBus can apply backoff retries.
        return await self.handle_message(message)

    @abstractmethod
    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        """
        Process the incoming layer message.
        Concrete layers must implement this method to perform their specific work.
        """
        pass
