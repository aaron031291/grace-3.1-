# Immutable Memory Mesh - Unified System

## Overview

The **Immutable Memory Mesh** is now **ONE UNIFIED SYSTEM** that combines:

1. **Learning Memory** - Trust-scored experiences and training data
2. **Episodic Memory** - Concrete experiences for recall
3. **Procedural Memory** - Learned skills and how-tos
4. **Pattern Memory** - Extracted patterns from multiple examples
5. **Immutable Snapshot** - Permanent, recoverable state of all memories

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   UNIFIED MEMORY MESH                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │   Learning     │→ │   Episodic     │→ │  Procedural  │  │
│  │   Memory       │  │   Memory       │  │  Memory      │  │
│  │ (Trust-scored) │  │ (High-trust)   │  │ (Skills)     │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│          ↓                   ↓                    ↓         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Pattern Extraction                        │  │
│  │         (Generalized Knowledge)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│          ↓                                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        IMMUTABLE SNAPSHOT                            │  │
│  │   .genesis_immutable_memory_mesh.json               │  │
│  │                                                       │  │
│  │   • Complete state capture                           │  │
│  │   • Recoverable                                      │  │
│  │   • Versionable                                      │  │
│  │   • Auditable                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## The Snapshot is the Latest State

The **immutable memory mesh snapshot** captures the **CURRENT STATE** of all memories:

### What's in the Snapshot

```json
{
  "snapshot_metadata": {
    "timestamp": "2026-01-11T12:00:00",
    "version": "1.0",
    "type": "memory_mesh_immutable_snapshot"
  },

  "learning_memory": {
    "total_examples": 1542,
    "examples": [
      {
        "id": "LE-xxx",
        "type": "feedback",
        "trust_score": 0.88,
        "input_context": {...},
        "expected_output": {...},
        "source": "user_feedback_correction",
        "times_validated": 5,
        "episodic_episode_id": "EP-yyy",
        "procedure_id": "PROC-zzz"
      }
    ],
    "by_type": {
      "feedback": 450,
      "correction": 320,
      "success": 550,
      "failure": 150,
      "pattern": 72
    },
    "trust_distribution": {
      "very_high_0.9+": 420,
      "high_0.7-0.9": 680,
      "medium_0.5-0.7": 350,
      "low_0.3-0.5": 75,
      "very_low_<0.3": 17
    }
  },

  "episodic_memory": {
    "total_episodes": 1205,
    "episodes": [
      {
        "id": "EP-xxx",
        "problem": "User asked about capital of Australia",
        "action": {"answer_given": "Sydney"},
        "outcome": {"corrected_to": "Canberra"},
        "trust_score": 0.91,
        "prediction_error": 1.0,
        "timestamp": "2026-01-11T11:30:00"
      }
    ],
    "high_trust_episodes": 892,
    "avg_prediction_error": 0.23
  },

  "procedural_memory": {
    "total_procedures": 245,
    "procedures": [
      {
        "id": "PROC-xxx",
        "name": "answer_capital_city_questions",
        "goal": "How to answer capital city questions",
        "steps": [...],
        "preconditions": {...},
        "trust_score": 0.85,
        "success_rate": 0.92,
        "usage_count": 45,
        "success_count": 42
      }
    ],
    "high_success_procedures": 198,
    "avg_success_rate": 0.78
  },

  "pattern_memory": {
    "total_patterns": 87,
    "patterns": [
      {
        "id": "PAT-xxx",
        "name": "geography_correction_pattern",
        "type": "behavioral",
        "trust_score": 0.82,
        "success_rate": 0.87,
        "sample_size": 15,
        "supporting_examples": ["LE-1", "LE-45", "LE-89", ...]
      }
    ],
    "high_success_patterns": 65
  },

  "statistics": {
    "total_memories": 3079,
    "learning_examples": 1542,
    "episodic_memories": 1205,
    "procedural_memories": 245,
    "extracted_patterns": 87,
    "trust_ratio": 0.71,
    "episodic_trust_ratio": 0.74,
    "procedural_success_ratio": 0.81
  },

  "integrity": "a3f5c8d2e9b1a7f4"
}
```

## API Endpoints - Complete Reference

### Creating Snapshots

#### Create Latest Snapshot
```bash
# Creates .genesis_immutable_memory_mesh.json
POST http://localhost:8000/learning-memory/snapshot/create

Response:
{
  "success": true,
  "snapshot": {
    "timestamp": "2026-01-11T12:00:00",
    "total_memories": 3079,
    "statistics": {...}
  },
  "file_path": "backend/knowledge_base/.genesis_immutable_memory_mesh.json"
}
```

#### Create Versioned Snapshot
```bash
# Creates .genesis_immutable_memory_mesh_20260111_120000.json
POST http://localhost:8000/learning-memory/snapshot/versioned

Response:
{
  "success": true,
  "file_path": "backend/knowledge_base/.genesis_immutable_memory_mesh_20260111_120000.json"
}
```

### Loading and Restoring

#### Load Snapshot (Read-Only)
```bash
# Just view the snapshot, don't restore
GET http://localhost:8000/learning-memory/snapshot/load

Response:
{
  "success": true,
  "snapshot": {
    "snapshot_metadata": {...},
    "learning_memory": {...},
    "episodic_memory": {...},
    "procedural_memory": {...},
    "pattern_memory": {...},
    "statistics": {...}
  }
}
```

#### Restore from Snapshot
```bash
# Restore database from snapshot file
POST http://localhost:8000/learning-memory/snapshot/restore

Response:
{
  "success": true,
  "restoration_stats": {
    "learning_examples_restored": 1542,
    "episodes_restored": 1205,
    "procedures_restored": 245,
    "patterns_restored": 87
  }
}
```

### Comparing Snapshots

```bash
GET http://localhost:8000/learning-memory/snapshot/compare?snapshot1_path=...&snapshot2_path=...

Response:
{
  "success": true,
  "comparison": {
    "snapshot1_time": "2026-01-10T12:00:00",
    "snapshot2_time": "2026-01-11T12:00:00",
    "learning_diff": {
      "added": 145,
      "old_count": 1397,
      "new_count": 1542
    },
    "episodic_diff": {
      "added": 98,
      "old_count": 1107,
      "new_count": 1205
    },
    "procedural_diff": {
      "added": 12,
      "old_count": 233,
      "new_count": 245
    },
    "trust_quality_change": {
      "old_trust_ratio": 0.68,
      "new_trust_ratio": 0.71,
      "improvement": 0.03
    }
  }
}
```

## Usage Patterns

### Pattern 1: Daily Snapshot (Recommended)

```bash
# Run daily via cron at 2 AM
0 2 * * * curl -X POST http://localhost:8000/learning-memory/snapshot/create
```

This ensures you always have the latest state saved as immutable memory.

### Pattern 2: Pre/Post Major Event Snapshots

```bash
# Before ingesting large dataset
curl -X POST http://localhost:8000/learning-memory/snapshot/versioned

# Ingest data
curl -X POST http://localhost:8000/ingest -F "file=@large_dataset.pdf"

# After ingestion
curl -X POST http://localhost:8000/learning-memory/snapshot/versioned

# Compare what changed
curl -X GET "http://localhost:8000/learning-memory/snapshot/compare?snapshot1_path=...&snapshot2_path=..."
```

### Pattern 3: Backup and Recovery

```bash
# 1. Create backup before risky operation
curl -X POST http://localhost:8000/learning-memory/snapshot/versioned

# 2. Perform risky operation
# ... something goes wrong ...

# 3. Restore from snapshot
curl -X POST http://localhost:8000/learning-memory/snapshot/restore
```

### Pattern 4: Environment Sync

```bash
# Development → Production

# 1. On dev: Create snapshot
curl -X POST http://localhost:8000/learning-memory/snapshot/create

# 2. Copy .genesis_immutable_memory_mesh.json to production

# 3. On prod: Restore snapshot
curl -X POST http://localhost:8000/learning-memory/snapshot/restore
```

## Complete Data Flow

```
┌──────────────────────────────────────────────────────────┐
│ 1. USER INPUT (Feedback, corrections, interactions)     │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ 2. LEARNING MEMORY                                       │
│    • Trust scoring (0-1)                                 │
│    • Source reliability                                  │
│    • Outcome quality                                     │
│    • Consistency check                                   │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ 3. INTELLIGENT ROUTING                                   │
│    IF trust >= 0.7 → Episodic Memory                    │
│    IF trust >= 0.8 → Procedural Memory                  │
│    IF 3+ similar → Pattern Extraction                    │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ 4. MEMORY MESH (Active, in-database)                    │
│    • Episodic: Recalls past experiences                 │
│    • Procedural: Suggests learned solutions             │
│    • Patterns: Generalized knowledge                     │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ 5. IMMUTABLE SNAPSHOT (Permanent record)                │
│    • Complete state capture                              │
│    • .genesis_immutable_memory_mesh.json                │
│    • Recoverable and versionable                         │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ 6. INFERENCE ENGINE                                      │
│    Uses all memory types to generate answers            │
└──────────────────────────────────────────────────────────┘
```

## Benefits of Unified System

### 1. Single Source of Truth
- The snapshot IS the latest memory mesh state
- No separate "immutable memory" vs "memory mesh"
- One system, one snapshot, one truth

### 2. Recoverable
```bash
# Database corruption? No problem
POST /learning-memory/snapshot/restore
# → All memories back in 30 seconds
```

### 3. Versionable
```bash
# Track learning over time
.genesis_immutable_memory_mesh_20260101_120000.json  # Jan 1
.genesis_immutable_memory_mesh_20260111_120000.json  # Jan 11
# → See exactly what Grace learned in 10 days
```

### 4. Auditable
```json
{
  "learning_example": {
    "id": "LE-123",
    "trust_score": 0.88,
    "times_validated": 5,
    "times_invalidated": 0,
    "source": "user_feedback_correction",
    "genesis_key_id": "GK-abc",
    "episodic_episode_id": "EP-456",
    "procedure_id": "PROC-789"
  }
}
```
Complete provenance: Who → What → When → Why → How

### 5. Portable
```bash
# Copy one file = copy all knowledge
scp .genesis_immutable_memory_mesh.json server2:/path/
# → Grace's entire learned knowledge transferred
```

## Automatic Snapshot Strategy

### Recommended Cron Jobs

```bash
# Daily snapshot (overwrites .genesis_immutable_memory_mesh.json)
0 2 * * * curl -X POST http://localhost:8000/learning-memory/snapshot/create

# Weekly versioned snapshot (creates timestamped file)
0 3 * * 0 curl -X POST http://localhost:8000/learning-memory/snapshot/versioned

# Monthly trust decay
0 4 1 * * curl -X POST http://localhost:8000/learning-memory/decay-trust-scores

# Hourly folder sync (if using file-based learning)
0 * * * * curl -X POST http://localhost:8000/learning-memory/sync-folders
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/learning-memory/stats

{
  "learning_memory": {
    "total_examples": 1542,
    "high_trust_examples": 1092,
    "trust_ratio": 0.71
  },
  "episodic_memory": {
    "total_episodes": 1205,
    "linked_from_learning": 1092,
    "linkage_ratio": 0.91
  },
  "procedural_memory": {
    "total_procedures": 245,
    "high_success_procedures": 198,
    "success_ratio": 0.81
  }
}
```

### Warning Signs
- `trust_ratio < 0.5` → Too much low-quality data
- `linkage_ratio < 0.7` → Episodic memory not being populated
- `success_ratio < 0.5` → Procedures failing too often

## File Locations

```
knowledge_base/
├── .genesis_immutable_memory_mesh.json          # Latest snapshot (updated daily)
├── .genesis_immutable_memory_mesh_20260111.json # Versioned snapshots
├── .genesis_immutable_memory_mesh_20260110.json
├── layer_1/
│   └── learning_memory/                         # Source learning data
│       ├── feedback/
│       ├── correction/
│       ├── success/
│       ├── failure/
│       └── pattern/
└── exports/
    └── training_data_1736614800.jsonl          # Exported training sets
```

## Python Integration

```python
from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot, create_memory_mesh_snapshot
from database.session import get_session
from pathlib import Path

# Create snapshot
session = next(get_session())
snapshot = create_memory_mesh_snapshot(
    session=session,
    knowledge_base_path=Path("backend/knowledge_base"),
    save=True
)

print(f"Snapshot created: {snapshot['statistics']['total_memories']} memories")

# Load and restore
snapshotter = MemoryMeshSnapshot(session, Path("backend/knowledge_base"))
loaded = snapshotter.load_snapshot()
stats = snapshotter.restore_from_snapshot(loaded)

print(f"Restored: {stats}")
```

## Summary

**The immutable memory mesh is now ONE unified system:**

1. **Active Memory Mesh** (in database)
   - Learning examples with trust scores
   - Episodic memories for recall
   - Procedural memories for skills
   - Extracted patterns for generalization

2. **Immutable Snapshot** (on disk)
   - `.genesis_immutable_memory_mesh.json`
   - Complete state of ALL memories
   - Latest = current memory mesh state
   - Recoverable, versionable, portable

**The snapshot IS the memory mesh in permanent form.**

No separation. No confusion. One system. One truth. ✓
