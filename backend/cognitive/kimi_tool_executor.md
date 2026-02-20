# Kimi Tool Executor

**File:** `cognitive/kimi_tool_executor.py`

## Overview

Kimi Tool Executor

Kimi is NOT just intelligence -- Kimi is a tool-using agent that can
execute across ALL of Grace's system capabilities.

This module maps every system tool surface to Kimi's execution ability:

TOOL CATEGORIES:
  1. FILE OPERATIONS     - read, write, edit, delete, search files
  2. CODE EXECUTION      - run python, bash, tests
  3. GIT OPERATIONS      - status, diff, add, commit, push, PR
  4. DIAGNOSTICS         - health checks, healing cycles, sensor data
  5. INGESTION           - ingest documents, manage knowledge base
  6. LEARNING            - trigger study, practice, extract patterns
  7. SCRAPING            - scrape URLs, crawl sites
  8. DEPLOYMENT          - CI/CD, build, deploy
  9. MONITORING          - system health, metrics, telemetry
  10. TASK MANAGEMENT    - todos, planning, Notion sync
  11. KNOWLEDGE BASE     - query, update, manage KB
  12. AUTONOMOUS ACTIONS  - trigger rules, schedule actions
  13. SANDBOX LAB        - propose experiments, run trials
  14. GOVERNANCE         - check policies, evaluate actions
  15. VOICE              - STT/TTS processing
  16. LLM ORCHESTRATION  - multi-model debate, consensus, delegation

Every tool execution is tracked by the LLM Interaction Tracker.
Every outcome feeds the Pattern Learner for dependency reduction.

## Classes

- `ToolCategory`
- `ToolDefinition`
- `ToolCall`
- `ToolResult`
- `KimiToolExecutor`

## Key Methods

- `list_tools()`
- `list_categories()`
- `get_tool_schema()`
- `get_stats()`
- `get_kimi_tool_executor()`

---
*Grace 3.1*
