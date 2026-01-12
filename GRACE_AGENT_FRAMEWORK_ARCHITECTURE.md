# Grace Full Agent Framework Architecture

## Overview

This document outlines the integration of OpenHands (OpenDevin) runtime capabilities with Grace's existing cognitive architecture to create a full software engineering agent.

## Current State

### Grace Has (Cognitive Layer)
- RAG system with Qdrant vector DB
- Memory Mesh (Learning, Episodic, Procedural)
- Trust scoring and confidence metrics
- OODA loop decision making
- Genesis Keys audit trail
- Multi-LLM orchestration
- Sandbox Lab framework (metadata only)
- 102 cloned repositories for knowledge

### Grace Lacks (Execution Layer)
- Code execution sandbox
- Shell/terminal access
- File write capability
- Test runner integration
- Git operations
- Build system integration

### OpenHands Provides
- Docker-based sandboxed execution
- Bash command execution
- IPython/Jupyter integration
- File read/write operations
- Browser automation
- Event-driven action system
- Agent loop with tools

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GRACE AGENT FRAMEWORK                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    GRACE COGNITIVE CORE                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │   RAG   │ │ Memory  │ │  OODA   │ │ Trust   │ │ Genesis │   │   │
│  │  │ System  │ │  Mesh   │ │  Loop   │ │ Scorer  │ │  Keys   │   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │   │
│  │       │           │           │           │           │         │   │
│  │       └───────────┴───────────┼───────────┴───────────┘         │   │
│  │                               │                                  │   │
│  │                    ┌──────────▼──────────┐                      │   │
│  │                    │  GRACE ORCHESTRATOR │                      │   │
│  │                    │  (Decision Engine)  │                      │   │
│  │                    └──────────┬──────────┘                      │   │
│  └───────────────────────────────┼──────────────────────────────────┘   │
│                                  │                                      │
│  ┌───────────────────────────────▼──────────────────────────────────┐   │
│  │                    EXECUTION BRIDGE (NEW)                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │   Action    │  │   Event     │  │  Feedback   │              │   │
│  │  │  Translator │  │   Stream    │  │   Parser    │              │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │   │
│  └─────────┼────────────────┼────────────────┼──────────────────────┘   │
│            │                │                │                          │
│  ┌─────────▼────────────────▼────────────────▼──────────────────────┐   │
│  │                 OPENHANDS RUNTIME LAYER                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │    Bash     │  │   Python    │  │    File     │              │   │
│  │  │   Runner    │  │  (IPython)  │  │ Operations  │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │   Browser   │  │    Git      │  │    Test     │              │   │
│  │  │  Automation │  │ Operations  │  │   Runner    │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                  │                                      │
│                     ┌────────────▼────────────┐                        │
│                     │    DOCKER SANDBOX       │                        │
│                     │  (Isolated Execution)   │                        │
│                     └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Execution Bridge (`backend/execution/`)

The bridge translates Grace's decisions into OpenHands actions and parses results back.

```python
# backend/execution/bridge.py

class ExecutionBridge:
    """
    Bridges Grace's cognitive layer with OpenHands runtime.

    Responsibilities:
    - Translate Grace decisions to OpenHands Actions
    - Parse OpenHands Observations back to Grace format
    - Maintain execution context and state
    - Track all actions via Genesis Keys
    """

    def __init__(self, runtime: Runtime, genesis_tracker: GenesisTracker):
        self.runtime = runtime
        self.genesis = genesis_tracker
        self.event_stream = EventStream()

    async def execute_code(self, code: str, language: str = "python") -> ExecutionResult:
        """Execute code in sandbox and return result."""

    async def run_command(self, command: str) -> CommandResult:
        """Run shell command in sandbox."""

    async def run_tests(self, test_path: str) -> TestResult:
        """Execute tests and return structured results."""

    async def write_file(self, path: str, content: str) -> WriteResult:
        """Write file in sandbox/workspace."""

    async def git_operation(self, operation: str, **kwargs) -> GitResult:
        """Execute git operations."""
```

### 2. Grace Agent (`backend/agent/`)

A new agent class that combines Grace's cognition with execution.

```python
# backend/agent/grace_agent.py

class GraceAgent:
    """
    Full software engineering agent combining:
    - Grace's RAG and memory for knowledge
    - Grace's OODA loop for decision making
    - Grace's trust scoring for confidence
    - OpenHands runtime for execution
    """

    def __init__(self):
        self.cognitive = GraceCognitive()  # Existing Grace systems
        self.execution = ExecutionBridge()  # New execution layer
        self.memory = MemoryMesh()  # Existing memory system

    async def solve_task(self, task: str) -> TaskResult:
        """
        Main agent loop:
        1. Understand task (RAG retrieval)
        2. Plan approach (OODA)
        3. Execute steps (OpenHands)
        4. Observe results
        5. Learn from outcome (Memory Mesh)
        6. Iterate until done
        """

    async def write_code(self, spec: str) -> CodeResult:
        """Write code based on specification."""

    async def fix_bug(self, description: str) -> FixResult:
        """Diagnose and fix a bug."""

    async def review_code(self, code: str) -> ReviewResult:
        """Review code and suggest improvements."""
```

### 3. Action Types

Grace-specific actions that map to OpenHands:

```python
# backend/execution/actions.py

class GraceAction(Enum):
    # Code Operations
    WRITE_CODE = "write_code"
    EDIT_CODE = "edit_code"
    READ_CODE = "read_code"

    # Execution
    RUN_PYTHON = "run_python"
    RUN_BASH = "run_bash"
    RUN_TESTS = "run_tests"

    # Git Operations
    GIT_STATUS = "git_status"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_PR = "git_pr"

    # Analysis
    SEARCH_CODE = "search_code"
    ANALYZE_ERROR = "analyze_error"

    # Learning
    RECORD_SUCCESS = "record_success"
    RECORD_FAILURE = "record_failure"
```

### 4. Feedback Loop Integration

Connect execution results back to Grace's learning systems:

```python
# backend/execution/feedback.py

class FeedbackProcessor:
    """
    Processes execution results and feeds them to Grace's learning systems.
    """

    def __init__(self, memory_mesh: MemoryMesh, trust_scorer: TrustScorer):
        self.memory = memory_mesh
        self.trust = trust_scorer

    async def process_result(self, action: GraceAction, result: ExecutionResult):
        """
        1. Parse execution result
        2. Determine success/failure
        3. Update trust scores
        4. Store in learning memory
        5. Extract patterns for procedural memory
        6. Create Genesis Key audit entry
        """

    async def learn_from_error(self, error: ExecutionError):
        """Extract learnable patterns from errors."""

    async def reinforce_success(self, success: ExecutionSuccess):
        """Strengthen patterns that led to success."""
```

---

## Implementation Plan

### Phase 1: Runtime Integration (Week 1)

1. **Install OpenHands Runtime Dependencies**
   - Docker setup
   - OpenHands package installation
   - Runtime configuration

2. **Create Execution Bridge**
   - `backend/execution/bridge.py`
   - `backend/execution/actions.py`
   - `backend/execution/results.py`

3. **Basic Execution Tests**
   - Run Python code
   - Run bash commands
   - File operations

### Phase 2: Agent Loop (Week 2)

1. **Create Grace Agent**
   - `backend/agent/grace_agent.py`
   - `backend/agent/planner.py`
   - `backend/agent/executor.py`

2. **Integrate with OODA Loop**
   - Connect cognitive decisions to actions
   - Handle observations from execution
   - Update orientation based on results

3. **Add Test Runner**
   - pytest integration
   - Test result parsing
   - Failure analysis

### Phase 3: Learning Integration (Week 3)

1. **Feedback Processing**
   - `backend/execution/feedback.py`
   - Connect to Memory Mesh
   - Trust score updates

2. **Pattern Extraction**
   - Learn from successful code
   - Learn from fixed bugs
   - Store in procedural memory

3. **Genesis Key Integration**
   - Track all executions
   - Audit trail for learning

### Phase 4: Full Agent API (Week 4)

1. **API Endpoints**
   - `/agent/task` - Submit task
   - `/agent/status` - Check progress
   - `/agent/history` - View actions
   - `/agent/learn` - Trigger learning

2. **Frontend Integration**
   - Agent control panel
   - Live execution view
   - Learning visualization

---

## File Structure

```
backend/
├── execution/                 # NEW: Execution layer
│   ├── __init__.py
│   ├── bridge.py             # Main execution bridge
│   ├── actions.py            # Action definitions
│   ├── results.py            # Result types
│   ├── feedback.py           # Feedback processor
│   └── runtime_config.py     # OpenHands config
│
├── agent/                     # NEW: Agent layer
│   ├── __init__.py
│   ├── grace_agent.py        # Main agent class
│   ├── planner.py            # Task planning
│   ├── executor.py           # Action execution
│   └── tools/                # Agent tools
│       ├── code_writer.py
│       ├── test_runner.py
│       ├── git_ops.py
│       └── file_ops.py
│
├── api/
│   └── agent_api.py          # NEW: Agent API endpoints
│
└── cognitive/                 # EXISTING: Grace cognitive
    ├── ooda.py               # Connect to agent
    ├── engine.py             # Connect to agent
    └── ...
```

---

## Configuration

```toml
# config/agent.toml

[runtime]
type = "docker"  # or "local" for development
sandbox_image = "grace-sandbox:latest"
timeout = 300
max_memory = "4g"

[agent]
max_iterations = 50
confidence_threshold = 0.7
auto_commit = false
test_before_commit = true

[learning]
learn_from_execution = true
store_successful_patterns = true
store_failure_patterns = true
min_trust_for_storage = 0.5

[genesis]
track_all_executions = true
track_file_changes = true
track_git_operations = true
```

---

## Security Considerations

1. **Sandbox Isolation**
   - All code runs in Docker container
   - No access to host filesystem (except mounted workspace)
   - Network restrictions configurable

2. **Resource Limits**
   - CPU/memory limits per execution
   - Timeout on all operations
   - Rate limiting on API

3. **Audit Trail**
   - Genesis Keys for all executions
   - Full command logging
   - Rollback capability

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Code execution success rate | > 90% |
| Test pass rate improvement | Measurable learning |
| Bug fix success rate | > 70% |
| Code quality scores | Improving over time |
| Learning pattern extraction | > 100 patterns/week |

---

## Next Steps

1. **Immediate**: Set up Docker environment
2. **This Week**: Build execution bridge
3. **Next Week**: Create agent loop
4. **Following**: Learning integration

---

*Document Version: 1.0*
*Created: 2026-01-12*
*Status: PLANNING*
