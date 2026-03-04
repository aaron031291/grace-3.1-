# Grace Unified Architecture: OS + To-Dos

## The Core Truth

**Grace OS** is the operating system.
**Grace To-Dos** is the visible nervous system.

They are not two products. They are two lenses on the same engine.

| Layer | Purpose |
|-------|---------|
| **Grace OS** | How Grace thinks, plans, builds, and executes |
| **Grace To-Dos** | How humans see, track, and intervene in that process |

Both sit on top of the same backend, the same memory, the same Genesis/version system, and the same autonomous loops.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HUMAN INTERFACE                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      Grace To-Dos (Truth Mirror)                        ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       ││
│  │  │   To Do     │ │ In Progress │ │  In Review  │ │  Completed  │       ││
│  │  │  (pending)  │ │  (active)   │ │  (blocked)  │ │   (done)    │       ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       ││
│  │                                                                         ││
│  │  Each card: Genesis Key ID | Version | Assignee | Progress | Provenance││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    ▲                                         │
│                                    │ Real-time sync                          │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Grace OS (Execution Layer)                       ││
│  │                                                                          ││
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             ││
│  │  │   Planner      │  │   Executor     │  │   Governor     │             ││
│  │  │  (CDIC Grids)  │  │  (OODA Loop)   │  │  (Layer 1-4)   │             ││
│  │  └────────────────┘  └────────────────┘  └────────────────┘             ││
│  │                                                                          ││
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             ││
│  │  │  Self-Healing  │  │   Ingestion    │  │    Oracle      │             ││
│  │  │   Triggers     │  │    Loops       │  │ Recommendations│             ││
│  │  └────────────────┘  └────────────────┘  └────────────────┘             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    ▲                                         │
│                                    │ State derived from                      │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Genesis Keys (Identity + State Spine)                 ││
│  │                                                                          ││
│  │  GU-*: User Profiles    SS-*: Sessions       DIR-*: Directories         ││
│  │  GK-*: Tasks/Ops        GP-*: Profiles       FILE-*: Files              ││
│  │  VER-*: Versions                                                         ││
│  │                                                                          ││
│  │  Every operation = Who + What + Where + When + Why + How                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    ▲                                         │
│                                    │ Persisted to                            │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Data Layer                                       ││
│  │  PostgreSQL/SQLite | Qdrant Vectors | Redis Cache | Git Repository      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Grace To-Dos: The Human-Visible Layer

### What It Is

Grace To-Dos is a **live, autonomous task surface** that shows:

| Visibility | Description |
|------------|-------------|
| **What Grace is doing** | Current active tasks and their status |
| **Why she's doing it** | Task type, category, and provenance |
| **Where she is in execution** | Progress percentage, subtasks completed |
| **What has been completed** | Version history with timestamps |
| **What is blocked** | Tasks in "In Review" needing intervention |
| **What needs human input** | Assigned tasks awaiting action |

**This is not a planner UI and not a chat app.**
**It is a truth mirror of Grace's internal state.**

### Current Implementation

Located at:
- **Frontend**: `frontend/src/components/NotionTab.jsx`
- **Backend**: `backend/api/notion.py`
- **Models**: `backend/models/notion_models.py`

### Task Card Anatomy

```
┌────────────────────────────────────────────────┐
│ [learning]                        [high]       │ ← Type + Priority badges
│                                                │
│ Implement Memory Mesh Integration              │ ← Title
│                                                │
│ Connect episodic memory to retrieval pipeline  │ ← Description
│                                                │
│ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│ │ Aaron    │ │ backend/ │ │ ████████░░ 80% │  │ ← Assignee, Folder, Progress
│ └──────────┘ └──────────┘ └────────────────┘  │
│                                                │
│ GK-A1B2C3D4E5F6...              v3            │ ← Genesis Key + Version
└────────────────────────────────────────────────┘
```

### Task Sources (Auto-Generated)

Tasks are generated by:

| Source | Description |
|--------|-------------|
| **Planners** | Breaking epics into executable chunks |
| **CDIC Grids** | Decomposed implementation tasks |
| **Self-Healing Triggers** | Auto-detected issues requiring action |
| **Ingestion Loops** | Files requiring processing |
| **Oracle Recommendations** | AI-suggested improvements |
| **Human Input** | Manually created tasks |

### Task States

```python
class TaskStatus(str, enum.Enum):
    TODO = "todo"           # Waiting to start
    IN_PROGRESS = "in_progress"  # Currently being worked on
    IN_REVIEW = "in_review"      # Needs human review/blocked
    COMPLETED = "completed"      # Successfully finished
    ARCHIVED = "archived"        # No longer active
```

### Task Types

```python
class TaskType(str, enum.Enum):
    LEARNING = "learning"        # Learning new concepts/skills
    BUILDING = "building"        # Building features/components
    RESEARCH = "research"        # Researching topics
    MAINTENANCE = "maintenance"  # System maintenance
    EXPERIMENT = "experiment"    # Running experiments
    DOCUMENTATION = "documentation"  # Creating documentation
    ANALYSIS = "analysis"        # Data analysis
    OTHER = "other"
```

---

## Genesis Keys: The Identity + State Spine

### What a Genesis Key Represents

A Genesis Key is a **lineage**, not a task and not a user.

| Aspect | Description |
|--------|-------------|
| **Coherent Intent** | A bounded purpose that can be tracked |
| **Execution Context** | Everything needed to understand scope |
| **Versioned History** | Complete audit trail of changes |
| **Stable Anchor** | For planning, learning, and rollback |

### Genesis Key Types

| Prefix | Type | Purpose |
|--------|------|---------|
| `GU-` | User Genesis Keys | User profiles and identities |
| `GP-` | Profile Genesis Keys | Worker/agent profiles |
| `GK-` | General Operation Keys | Tasks, operations (UUID-based) |
| `SS-` | Session Genesis Keys | 24-hour session tracking |
| `DIR-` | Directory Genesis Keys | Folder-level tracking |
| `FILE-` | File Genesis Keys | File-level tracking (MD5-based) |
| `VER-` | Version Genesis Keys | Version snapshots |

### Genesis Key Generation

```python
# From backend/models/notion_models.py

def generate_genesis_key() -> str:
    """Generate a unique Genesis Key ID in format GK-[hex]."""
    return f"GK-{uuid.uuid4().hex[:16].upper()}"

def generate_profile_genesis_id() -> str:
    """Generate a unique Profile Genesis ID in format GP-[hex]."""
    return f"GP-{uuid.uuid4().hex[:16].upper()}"
```

### Genesis Key in UI

When clicking a Genesis Key in Grace To-Dos, it opens like a container showing:

| View | Content |
|------|---------|
| **Versions** | Complete version history with diffs |
| **Plans** | Associated planning documents |
| **Chunks** | Decomposed work items |
| **Events** | Timeline of all actions |
| **Proofs** | Tests, logs, governance records |
| **Last Completed** | Derived from version control |

### Critical Design Principle

**Grace does not "remember progress" — she derives it from the Genesis lineage + repo state.**

This ensures:
- State is deterministic, not claimed
- Rollback is always possible
- Learning is grounded in real outcomes
- Audit trails are complete

---

## Panels: Parallel Execution Contexts

### What "+ New Panel" Means

When you click `+ New Panel`:
- You are **not** duplicating the UI
- You **are** spawning a new Genesis context
- Same system, same memory, separate lineage

### Panel Properties

| Property | Description |
|----------|-------------|
| **Own Genesis Key** | Unique identifier for this context |
| **Own To-Dos** | Independent task list |
| **Shared Codebase** | Safe concurrent access |
| **Clean Merge/Abandon** | No orphaned state |

### Panel Use Cases

| Use Case | Description |
|----------|-------------|
| **Multiple Humans** | Different users working on same project |
| **Multiple Intents** | Parallel feature development |
| **Parallel Builds** | Concurrent experiments |
| **No Context Collision** | Clean separation of concerns |

### Scaling Model

```
Solo Builder  →  Team OS  →  Enterprise Scale
     │              │              │
     ▼              ▼              ▼
  1 Panel       N Panels      N Panels per Team
  1 Context     N Contexts    Hierarchical Genesis
```

---

## Grace OS: The Execution and Cognition Surface

Grace OS is built on top of VS Code, but functionally it is:
- A **planner**
- A **reasoner**
- A **governed executor**
- A **bi-directional collaborator**

### Core Grace OS Views

#### 1. Codebase View

| Aspect | Description |
|--------|-------------|
| **Ground Truth** | Actual file contents |
| **Last Completed State** | Derived from Git |
| **File/Folder Access** | Full navigation |
| **Gated Read/Write** | Governed operations |

#### 2. Planner Tabs (Top-Level)

| Tab | Purpose |
|-----|---------|
| **Big Concept** | High-level vision and goals |
| **Questions & Answers** | Non-technical clarifications |
| **Technical Stack** | Technology decisions |
| **Execution Plan** | Epics → Chunks breakdown |

#### 3. Execution View

| Component | Purpose |
|-----------|---------|
| **CDIC Grid Runs** | Decomposed task execution |
| **Layer 1-4 Gates** | Governance checkpoints |
| **Security & Governance** | Compliance enforcement |
| **Proofs Attached** | Evidence of completion |

#### 4. Autonomy View

| Feature | Purpose |
|---------|---------|
| **Self-Healing Actions** | Auto-detected repairs |
| **Ingestion Events** | New content processing |
| **Oracle Feedback** | AI recommendations |
| **Grace-Initiated Outreach** | Proactive communication |

---

## Grace's Self-Model Integration

By integrating Grace's self-model, the system provides:

### Awareness

| Awareness Type | Description |
|----------------|-------------|
| **What Grace is doing** | Current execution state |
| **What she believes is complete** | Derived from proofs |
| **What she is unsure about** | Confidence scores |
| **What she thinks is risky** | Risk assessment |

### Adaptability

| Adaptation | Mechanism |
|------------|-----------|
| **Planning Depth** | Adjust based on complexity |
| **Autonomy Level** | User-defined boundaries |
| **Verbosity** | Communication density |
| **Intervention Frequency** | Human touchpoint cadence |

### Self-Model Informs

| Decision | How Self-Model Helps |
|----------|---------------------|
| **Task Chunking** | Optimal decomposition size |
| **Pause vs Proceed** | Confidence thresholds |
| **Ask vs Decide** | Autonomy boundaries |
| **When to Escalate** | Risk-based triggers |

---

## Data Layer Integration

### Database Schema

```sql
-- Profiles (Workers/Agents)
notion_profile
├── genesis_key_id (GP-*)
├── name, display_name
├── skill_set (JSON)
├── is_active
├── tasks_completed, tasks_in_progress, tasks_total
└── total_time_logged

-- Tasks
notion_task
├── genesis_key_id (GK-*)
├── title, description
├── status, priority, task_type
├── assignee_id → notion_profile
├── folder_path, file_paths
├── progress_percent
├── version
└── subtasks (JSON)

-- History (Full Provenance)
task_history
├── task_genesis_key_id
├── action, field_changed
├── old_value, new_value
├── actor_genesis_key_id
├── version_number
└── change_reason
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/notion/board` | GET | Full Kanban board state |
| `/notion/tasks` | GET/POST | List/Create tasks |
| `/notion/tasks/{gk}` | GET/PUT/DELETE | Single task CRUD |
| `/notion/tasks/{gk}/move` | POST | Status change |
| `/notion/tasks/{gk}/history` | GET | Full audit trail |
| `/notion/profiles` | GET/POST | List/Create profiles |
| `/notion/profiles/{gk}` | GET/PUT | Profile CRUD |
| `/notion/profiles/{gk}/log-on` | POST | Start session |
| `/notion/profiles/{gk}/log-off` | POST | End session |
| `/notion/stats` | GET | System statistics |

---

## The Unification (One Sentence)

> **Grace OS is how Grace thinks and builds.**
> **Grace To-Dos is how humans see and steer that thinking in real time.**
> **Genesis Keys are the shared spine that make both deterministic, auditable, and scalable.**

---

## Why This Architecture Is Powerful

| Principle | Reality |
|-----------|---------|
| **Autonomy is visible** | Tasks auto-appear from internal processes |
| **Progress is provable** | Version history + proofs |
| **State is derived, not claimed** | Genesis lineage + repo state |
| **Humans and Grace share execution truth** | Same data, different views |
| **Planning is reversible** | Endpoint → repo reconstruction |
| **Learning is grounded** | Real outcomes, not assumptions |
| **Multiple users don't collide** | Panel isolation |
| **Nothing is "magic"** | Full audit trail |

**This is not Notion + Copilot.**
**This is an operating system for building.**

---

## File Reference

| Component | Location |
|-----------|----------|
| Frontend Kanban | `frontend/src/components/NotionTab.jsx` |
| Frontend Styles | `frontend/src/components/NotionTab.css` |
| Backend API | `backend/api/notion.py` |
| Data Models | `backend/models/notion_models.py` |
| Genesis Key Service | `backend/genesis/genesis_key_service.py` |
| Main App Router | `backend/app.py` |

---

## Next Steps for Enhancement

1. **Auto-Task Generation**: Connect planners and CDIC grids to auto-create tasks
2. **Panel System**: Implement multi-panel UI with isolated Genesis contexts
3. **Self-Model Integration**: Surface Grace's confidence and risk assessments
4. **Real-Time Sync**: WebSocket updates for live task state changes
5. **Oracle Integration**: AI-recommended task prioritization
6. **Self-Healing UI**: Visual indicators for auto-detected repairs
