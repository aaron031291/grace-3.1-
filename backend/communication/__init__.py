"""
Communication Systems for Grace

Provides bidirectional LLM communication and messaging.
"""

from communication.grace_llm_bridge import (
    GraceLLMBridge,
    GraceLLMMessage,
    MessageType,
    get_grace_llm_bridge
)

__all__ = [
    "GraceLLMBridge",
    "GraceLLMMessage",
    "MessageType",
    "get_grace_llm_bridge"
]
