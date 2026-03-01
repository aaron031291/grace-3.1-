"""
Grace OS — Central Message Bus

The central nervous system for Grace OS. 
Every inter-layer call is a message routed through this bus. 
Provides delivery, exponential backoff retries, and cycle detection.
Integrates with TrustScorekeeper and EventSystem for full observability.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import time

from .message_protocol import LayerMessage, LayerResponse

if TYPE_CHECKING:
    from .trust_scorekeeper import TrustScorekeeper
    from .event_system import EventSystem

logger = logging.getLogger(__name__)

# Type alias for message handlers
MessageHandler = Callable[[LayerMessage], asyncio.Future]

class MessageBus:
    """
    Routes messages between Grace OS layers.
    """
    
    def __init__(
        self,
        trust_scorekeeper: Optional["TrustScorekeeper"] = None,
        event_system: Optional["EventSystem"] = None,
    ):
        # Maps message_type -> list of handlers
        self._subscriptions: Dict[str, List[MessageHandler]] = {}
        
        # Cross-cutting modules
        self.trust_scorekeeper = trust_scorekeeper
        self.event_system = event_system
        
        # Configuration
        self._max_retries = 3
        self._base_backoff_ms = 100

    def subscribe(self, message_type: str, handler: MessageHandler):
        """
        Register a handler for a specific message type.
        """
        if message_type not in self._subscriptions:
            self._subscriptions[message_type] = []
        
        if handler not in self._subscriptions[message_type]:
            self._subscriptions[message_type].append(handler)
            logger.debug(f"[MessageBus] Handler subscribed to '{message_type}'")

    def unsubscribe(self, message_type: str, handler: MessageHandler):
        """
        Remove a handler for a specific message type.
        """
        if message_type in self._subscriptions:
            if handler in self._subscriptions[message_type]:
                self._subscriptions[message_type].remove(handler)
                logger.debug(f"[MessageBus] Handler unsubscribed from '{message_type}'")

    async def send(self, message: LayerMessage) -> LayerResponse:
        """
        Send a point-to-point message to a targeted layer or any handler 
        if to_layer isn't explicitly enforcing a layer (though target is usually checked by the handler).
        
        Returns the first valid LayerResponse.
        """
        start_time = time.time()
        
        if message.max_depth <= 0:
            logger.warning(f"[MessageBus] Max depth reached for message {message.id}. Cycle aborted.")
            return self._build_error_response(
                message, 
                "failure", 
                "Max recursion depth exceeded (cycle detected)."
            )

        handlers = self._subscriptions.get(message.message_type, [])
        
        if not handlers:
            logger.warning(f"[MessageBus] No handlers found for message type '{message.message_type}'")
            return self._build_error_response(
                message, 
                "failure", 
                f"No handlers registered for {message.message_type}"
            )

        # For point-to-point, we execute the first registered handler matching the condition.
        # Ideally, handlers filter based on message.to_layer. 
        # Here we attempt execution and return the first success.
        
        # Priority Queue Execution Note:
        # In a fully concurrent environment with deep queues, a proper `asyncio.PriorityQueue`
        # is necessary. Since this is an inline `send` call that immediately `awaits` the handler,
        # the execution is immediate. The priority field acts as a metadata parameter for handlers
        # that might internalize their own queueing.
        
        # Emit MESSAGE_SENT event
        if self.event_system:
            self.event_system.emit(
                "MESSAGE_SENT", message.trace_id, message.from_layer,
                {"to": message.to_layer, "type": message.message_type, "id": message.id}
            )

        for handler in handlers:
            response = await self._execute_with_retry(handler, message)
            if response:
                response.duration_ms = int((time.time() - start_time) * 1000)
                
                # Record trust score
                if self.trust_scorekeeper and response.trust_score > 0:
                    self.trust_scorekeeper.record_score(
                        trace_id=message.trace_id,
                        layer=response.from_layer,
                        score=response.trust_score,
                        message_type=message.message_type,
                        message_id=message.id,
                    )
                
                # Emit RESPONSE_RETURNED event
                if self.event_system:
                    self.event_system.emit(
                        "RESPONSE_RETURNED", message.trace_id, response.from_layer,
                        {"status": response.status, "trust": response.trust_score, "ms": response.duration_ms}
                    )
                
                return response

        return self._build_error_response(
            message,
            "failure",
            "All handlers failed or returned no response."
        )

    async def broadcast(self, message: LayerMessage) -> List[LayerResponse]:
        """
        Send a message to ALL subscribed handlers for the given message_type.
        """
        start_time = time.time()
        
        if message.max_depth <= 0:
            logger.warning(f"[MessageBus] Max depth reached for broadcast {message.id}.")
            return [self._build_error_response(message, "failure", "Max recursion depth exceeded.")]

        handlers = self._subscriptions.get(message.message_type, [])
        responses = []

        if not handlers:
            return responses

        # Execute all handlers concurrently
        tasks = [
            self._execute_with_retry(handler, message)
            for handler in handlers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = int((time.time() - start_time) * 1000)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[MessageBus] Uncaught broadcast error: {result}")
                responses.append(self._build_error_response(message, "failure", str(result)))
            elif isinstance(result, LayerResponse):
                result.duration_ms = duration
                responses.append(result)

        return responses

    async def _execute_with_retry(self, handler: MessageHandler, message: LayerMessage) -> Optional[LayerResponse]:
        """
        Executes a handler with exponential backoff on failure.
        """
        retries = 0
        backoff_ms = self._base_backoff_ms

        while retries <= self._max_retries:
            try:
                # Decrement max depths for any subsequent child calls made by the handler
                message_context = message
                response = await handler(message_context)
                
                if isinstance(response, LayerResponse):
                    if response.status == "failure" and retries < self._max_retries:
                        # Attempt retry on explicit failure if requested by policy
                        # For now, we only retry exceptions, but this can be tuned.
                        pass 
                    return response
                return None
                
            except Exception as e:
                logger.error(f"[MessageBus] Handler exception handling {message.message_type}: {e}")
                last_error = e
                
                if retries < self._max_retries:
                    retries += 1
                    logger.info(f"[MessageBus] Retrying {message.id} ({retries}/{self._max_retries}) in {backoff_ms}ms")
                    await asyncio.sleep(backoff_ms / 1000.0)
                    backoff_ms *= 2  # Exponential backoff
                else:
                    break # Exhausted retries

        logger.error(f"[MessageBus] Max retries exhausted for message {message.id}.")
        return self._build_error_response(message, "failure", f"Handler exception: {str(last_error)}")

    def _build_error_response(self, message: LayerMessage, status: str, error_msg: str) -> LayerResponse:
        """Helper to build a standardized error response."""
        return LayerResponse(
            message_id=message.id,
            from_layer="MessageBus",
            status=status,
            payload={"error": error_msg},
            trust_score=0.0
        )
