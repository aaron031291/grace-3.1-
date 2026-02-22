"""
Backward compatibility wrapper.
Real code moved to cognitive/grace_command_router.py

Classes:
- `RouteDecision`
- `RoutedTask`
- `ExecutionResult`
- `KimiCommandRouter`

Key Methods:
- `classify_and_route()`
- `get_routing_stats()`
- `get_kimi_command_router()`
"""
from cognitive.grace_command_router import *
from cognitive.grace_command_router import GraceCommandRouter as KimiCommandRouter
from cognitive.grace_command_router import get_kimi_command_router
