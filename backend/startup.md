# Startup

**File:** `startup.py`

## Overview

Grace Unified Startup - Activates All Subsystems

This module connects every subsystem that was built but never wired.
Called from app.py lifespan after core services (DB, Ollama, Qdrant) are ready.

Subsystems activated:
1. Layer 1 Message Bus (nervous system - connects 9 components)
2. Component Registry (lifecycle management)
3. Cognitive Engine (OODA decision-making)
4. Magma Memory (graph-based memory with causal inference)
5. Diagnostic Engine (4-layer health monitoring with 60s heartbeat)
6. Systems Integration (connects Planning/Todos/Memory/Diagnostics)
7. Autonomous Engine (self-triggered task execution)

Each subsystem is wrapped in try/except so one failure doesn't block others.

---
*Grace 3.1*
