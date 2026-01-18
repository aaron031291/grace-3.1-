# Grace Coding Agent - Unified System

## Overview

The Grace Coding Agent is a unified, enterprise-grade code generation system that consolidates all coding agent functionality into a single cohesive module.

## What Changed

### Merged Components

The following components have been unified into `backend/cognitive/coding_agent.py`:

1. **EnterpriseCodingAgent** → `CodingAgent`
2. **CodingAgentHealingBridge** → Integrated into `CodingAgent`
3. **AssistanceRequest/AssistanceType** → Moved to `coding_agent.py`

### Backward Compatibility

For backward compatibility, the following aliases are provided:

```python
# These still work
from cognitive.coding_agent import EnterpriseCodingAgent  # Alias for CodingAgent
from cognitive.coding_agent import get_enterprise_coding_agent  # Alias for get_coding_agent
```

The original `enterprise_coding_agent.py` remains for existing imports but new code should use `coding_agent.py`.

## Usage

### Basic Usage

```python
from cognitive.coding_agent import get_coding_agent, CodingTaskType

# Get the coding agent
agent = get_coding_agent(
    session=db_session,
    repo_path=Path("/path/to/repo"),
    enable_learning=True,
    enable_sandbox=True
)

# Create a task
task = agent.create_task(
    task_type=CodingTaskType.CODE_GENERATION,
    description="Write a function to calculate factorial",
    context={"function_name": "factorial"}
)

# Execute the task
result = agent.execute_task(task.task_id)
```

### Bidirectional Communication with Self-Healing

```python
# Request healing assistance
result = agent.request_healing_assistance(
    issue_description="Code generation failed",
    affected_files=["src/module.py"],
    issue_type="code_quality"
)

# Request diagnostic
diagnostic = agent.request_diagnostic(
    description="Analyze system health",
    context={"component": "api_layer"}
)

# Handle request from healing system
result = agent.handle_healing_request(
    assistance_type=AssistanceType.CODE_FIX,
    description="Fix null pointer error",
    context={"file": "src/handler.py"}
)
```

### Sandbox Practice

```python
# Practice in sandbox (safe environment)
result = agent.practice_in_sandbox(
    task_type=CodingTaskType.CODE_GENERATION,
    description="Generate sorting algorithm",
    difficulty_level=2
)
```

## Architecture

```
CodingAgent
├── Task Management
│   ├── create_task()
│   ├── execute_task()
│   └── OODA Loop (_observe, _orient, _decide, _act)
│
├── Code Generation
│   ├── Knowledge-driven generation
│   ├── Template pattern matching
│   ├── LLM generation (fallback)
│   └── Beyond-LLM capabilities
│
├── Testing & Review
│   ├── _test_in_sandbox()
│   ├── _test_code()
│   └── _review_code()
│
├── Bidirectional Communication
│   ├── request_healing_assistance()
│   ├── request_diagnostic()
│   └── handle_healing_request()
│
├── Learning
│   ├── Memory Mesh integration
│   ├── Federated learning
│   └── Template learning
│
└── Analytics
    ├── get_metrics()
    ├── get_health_status()
    └── get_learning_connections()
```

## Integrated Systems

The unified Coding Agent integrates with:

| System | Purpose |
|--------|---------|
| Genesis Keys | Track all operations for provenance |
| Memory Mesh | Learn from patterns and experiences |
| LLM Orchestrator | Grace-aligned code generation |
| Diagnostic Engine | System health analysis |
| Self-Healing System | Bidirectional healing support |
| Code Analyzer | Code review and quality checks |
| Testing System | Test execution |
| Training System | Sandbox practice |
| Federated Learning | Cross-instance learning |
| TimeSense | Time estimation |
| Version Control | Change tracking |
| Cognitive Engine | OODA loop reasoning |

## API Endpoints

The unified agent is exposed via the coding agent API:

- `POST /coding-agent/task` - Create task
- `POST /coding-agent/task/{id}/execute` - Execute task
- `GET /coding-agent/task/{id}` - Get task info
- `GET /coding-agent/tasks` - List tasks
- `GET /coding-agent/metrics` - Get metrics
- `GET /coding-agent/health` - Get health status
- `POST /coding-agent/sandbox/practice` - Practice in sandbox
- `POST /coding-agent/sandbox/cleanup` - Cleanup sandbox
- `GET /coding-agent/learning/connections` - Get learning connections
- `POST /coding-agent/healing/request` - Request healing
- `POST /coding-agent/healing/diagnostic` - Request diagnostic

## Task Types

```python
class CodingTaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_OPTIMIZE = "code_optimize"
    CODE_REVIEW = "code_review"
    CODE_DOCUMENT = "code_document"
    CODE_TEST = "code_test"
    CODE_MIGRATE = "code_migrate"
    FEATURE_IMPLEMENT = "feature_implement"
    BUG_FIX = "bug_fix"
```

## Quality Levels

```python
class CodeQualityLevel(str, Enum):
    DRAFT = "draft"        # Initial draft
    REVIEW = "review"      # Needs review
    PRODUCTION = "production"  # Production-ready
    ENTERPRISE = "enterprise"  # Enterprise-grade
```

## Migration Guide

### From enterprise_coding_agent.py

```python
# Before
from cognitive.enterprise_coding_agent import (
    EnterpriseCodingAgent,
    get_enterprise_coding_agent
)

# After
from cognitive.coding_agent import (
    CodingAgent,  # or EnterpriseCodingAgent (alias)
    get_coding_agent  # or get_enterprise_coding_agent (alias)
)
```

### From coding_agent_healing_bridge.py

```python
# Before
from cognitive.coding_agent_healing_bridge import (
    CodingAgentHealingBridge,
    get_coding_agent_healing_bridge
)
bridge = get_coding_agent_healing_bridge(coding_agent, healing_system)
bridge.healing_request_coding_assistance(...)

# After
from cognitive.coding_agent import CodingAgent
agent = CodingAgent(...)
agent.handle_healing_request(...)  # Healing → Coding Agent
agent.request_healing_assistance(...)  # Coding Agent → Healing
```

## Files

| File | Description |
|------|-------------|
| `backend/cognitive/coding_agent.py` | **Unified coding agent (PRIMARY)** |
| `backend/cognitive/enterprise_coding_agent.py` | Legacy file (kept for imports) |
| `backend/cognitive/coding_agent_healing_bridge.py` | Legacy bridge (functionality merged) |
| `backend/api/coding_agent_api.py` | API endpoints |
| `tests/test_coding_agent.py` | Tests |
