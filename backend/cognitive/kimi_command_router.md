# Kimi Command Router

**File:** `cognitive/kimi_command_router.py`

## Overview

Kimi Command Router

Routes Kimi's decisions to the appropriate execution path:
- Direct command execution: Kimi executes commands via the execution bridge
- Coding task delegation: Kimi hands off coding tasks to the coding agent
- Reasoning tasks: Kimi handles directly, results are tracked
- Hybrid tasks: Split between Kimi and coding agent

Architecture:
    User -> Kimi (reasoning/command) -> Command Router
                                         |
                                         |--> Direct Execution (commands, git, shell)
                                         |--> Coding Agent (code writing, refactoring, testing)
                                         |--> Tool Execution (diagnostics, ingestion, monitoring, etc.)
                                         |--> Hybrid (Kimi plans, coding agent implements)
                                         |
                                         +--> ALL paths tracked by LLM Interaction Tracker

Kimi is NOT just intelligence. Kimi is a tool-using agent that routes
to the right tool for the job. The KimiToolExecutor provides access to
50+ system tools across 20 categories.

The router classifies each request and routes it accordingly,
while ensuring every interaction is recorded for learning.

## Classes

- `RouteDecision`
- `RoutedTask`
- `ExecutionResult`
- `KimiCommandRouter`

## Key Methods

- `classify_and_route()`
- `get_routing_stats()`
- `get_kimi_command_router()`

---
*Grace 3.1*
