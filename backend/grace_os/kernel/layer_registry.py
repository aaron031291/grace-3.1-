"""
Grace OS — Layer Registry

Dynamic discovery and health-checking for all layers.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class LayerRegistration:
    """Metadata about a registered layer."""
    def __init__(self, name: str, capabilities: List[str], instance: Any):
        self.name = name
        self.capabilities = capabilities
        self.instance = instance
        self.status = "healthy"  # healthy | degraded | offline
        self.last_heartbeat = datetime.now(timezone.utc)

class LayerRegistry:
    """
    Registry for Grace OS Layers.
    """
    
    def __init__(self):
        self._layers: Dict[str, LayerRegistration] = {}

    def register(self, layer_name: str, capabilities: List[str], instance: Any):
        """
        Registers a layer with the system.
        """
        self._layers[layer_name] = LayerRegistration(
            name=layer_name,
            capabilities=capabilities,
            instance=instance
        )
        logger.info(f"[LayerRegistry] Registered layer: {layer_name} with capabilities: {capabilities}")

    def deregister(self, layer_name: str):
        """
        Removes a layer from the registry.
        """
        if layer_name in self._layers:
            del self._layers[layer_name]
            logger.info(f"[LayerRegistry] Deregistered layer: {layer_name}")

    def get_layer(self, layer_name: str) -> Optional[Any]:
        """
        Retrieve a layer instance by name.
        """
        registration = self._layers.get(layer_name)
        if registration and registration.status == "healthy":
            return registration.instance
        return None

    def query_capabilities(self, capability: str) -> List[str]:
        """
        Find all layer names that support a specific capability.
        """
        capable_layers = []
        for name, reg in self._layers.items():
            if reg.status == "healthy" and capability in reg.capabilities:
                capable_layers.append(name)
        return capable_layers

    def set_status(self, layer_name: str, status: str):
        """
        Update the health status of a layer.
        """
        if layer_name in self._layers:
            if status not in ["healthy", "degraded", "offline"]:
                raise ValueError(f"Invalid status: {status}")
            self._layers[layer_name].status = status
            logger.debug(f"[LayerRegistry] Layer {layer_name} status -> {status}")

    def heartbeat(self, layer_name: str):
        """
        Record a heartbeat for a layer to mark it as healthy.
        """
        if layer_name in self._layers:
            self._layers[layer_name].last_heartbeat = datetime.now(timezone.utc)
            if self._layers[layer_name].status != "healthy":
                self.set_status(layer_name, "healthy")
