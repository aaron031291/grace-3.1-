# Memory Mesh Quick Start

## TL;DR

The **immutable memory** and **memory mesh** are **ONE SYSTEM**.

- **Active form**: PostgreSQL database (fast, queryable)
- **Immutable form**: `.genesis_immutable_memory_mesh.json` (permanent, recoverable)

## 5-Minute Setup

```bash
# 1. Start server
cd backend
python app.py

# 2. Create first snapshot
curl -X POST http://localhost:8000/learning-memory/snapshot/create

# 3. Done! Your memory mesh is now permanently saved.
```

## Essential Commands

### Create Snapshot
```bash
# Latest state (overwrites existing)
POST http://localhost:8000/learning-memory/snapshot/create

# Versioned (timestamped backup)
POST http://localhost:8000/learning-memory/snapshot/versioned
```

### Restore
```bash
# Restore from snapshot if database is lost
POST http://localhost:8000/learning-memory/snapshot/restore
```

### Check Status
```bash
# See what's in memory
GET http://localhost:8000/learning-memory/stats
```

### Record Learning
```bash
# Add new experience
POST http://localhost:8000/learning-memory/record-experience
{
  "experience_type": "correction",
  "context": {"question": "..."},
  "action_taken": {"answer": "..."},
  "outcome": {"correct_answer": "..."},
  "source": "user_feedback_correction"
}
```

## What's Captured in Snapshot

```json
{
  "learning_memory": { ... },    // All trust-scored experiences
  "episodic_memory": { ... },    // High-trust episodes
  "procedural_memory": { ... },  // Learned skills
  "pattern_memory": { ... },     // Extracted patterns
  "statistics": { ... }          // Complete stats
}
```

## Daily Automation

```bash
# Add to crontab
0 2 * * * curl -X POST http://localhost:8000/learning-memory/snapshot/create
```

## Files

- **Latest**: `knowledge_base/.genesis_immutable_memory_mesh.json`
- **Versioned**: `knowledge_base/.genesis_immutable_memory_mesh_YYYYMMDD_HHMMSS.json`

## Full Documentation

- [ONE_UNIFIED_MEMORY_SYSTEM.md](ONE_UNIFIED_MEMORY_SYSTEM.md) - Complete explanation
- [IMMUTABLE_MEMORY_MESH_UNIFIED.md](IMMUTABLE_MEMORY_MESH_UNIFIED.md) - Detailed guide
- [test_immutable_memory_mesh.py](test_immutable_memory_mesh.py) - Working examples

## Key Point

**The snapshot IS the memory mesh in permanent form.**

Not two systems. One system, two representations. ✓
