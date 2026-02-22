# Message Bus

**File:** `layer1/message_bus.py`

## Overview

Layer 1 Message Bus - Bidirectional Component Communication

Enables all Layer 1 components to communicate, coordinate, and trigger
autonomous actions intelligently.

Components:
- Genesis Keys
- Memory Mesh
- Learning Memory
- RAG (Retrieval)
- Ingestion
- World Model
- Autonomous Learning
- LLM Orchestration
- Version Control
- Librarian

## Classes

- `MessageType`
- `ComponentType`
- `Message`
- `AutonomousAction`
- `Layer1MessageBus`

## Key Methods

- `register_component()`
- `get_component()`
- `register_autonomous_action()`
- `subscribe()`
- `register_request_handler()`
- `get_message_history()`
- `get_stats()`
- `get_autonomous_actions()`
- `enable_autonomous_action()`
- `disable_autonomous_action()`
- `get_message_bus()`
- `reset_message_bus()`

---
*Grace 3.1*
