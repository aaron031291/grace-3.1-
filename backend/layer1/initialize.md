# Initialize

**File:** `layer1/initialize.py`

## Overview

Layer 1 Initialization - Complete System Setup

Initializes all Layer 1 components and connects them to the message bus
for autonomous bidirectional communication.

Usage:
    from backend.layer1.initialize import initialize_layer1

    layer1 = initialize_layer1(
        session=db_session,
        kb_path="/path/to/knowledge_base"
    )

    # All components now communicate autonomously!

## Classes

- `Layer1System`

## Key Methods

- `get_stats()`
- `get_autonomous_actions()`
- `initialize_layer1()`
- `get_layer1_stats()`

---
*Grace 3.1*
