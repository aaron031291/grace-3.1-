# Memory Mesh → Genesis Key Integration

## YES - Memory Mesh Accepts Genesis Keys

The memory mesh **fully integrates** with the Genesis Key system. Every learning experience gets a Genesis Key and is saved to the Layer 1 folder structure.

---

## Complete Data Flow

```
USER PROVIDES FEEDBACK
   ↓
POST /learning-memory/record-experience
{
  "experience_type": "correction",
  "context": {...},
  "action_taken": {...},
  "outcome": {...},
  "user_id": "GU-user123",          ← Genesis User ID
  "genesis_key_id": "GK-abc..."     ← Optional existing Genesis Key
}
   ↓
┌────────────────────────────────────────────────────────┐
│ 1. GENESIS KEY CREATION                                │
│    • If genesis_key_id provided: Link to it           │
│    • If not provided: Create new Genesis Key          │
│    • Format: GK-learning-{type}-{timestamp}-{hash}    │
│    • Saved to: knowledge_base/layer_1/genesis_keys/   │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ 2. LEARNING MEMORY INGESTION                          │
│    • Trust score calculated                            │
│    • Linked to Genesis Key                            │
│    • Saved to database                                 │
│    • File saved to Layer 1 folder                     │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ 3. LAYER 1 FOLDER STRUCTURE                           │
│    knowledge_base/layer_1/learning_memory/            │
│    ├── correction/                                     │
│    │   └── 2026-01-11/                                │
│    │       ├── learning_1736616000.json               │
│    │       │   {                                       │
│    │       │     "genesis_key_id": "GK-abc...",       │
│    │       │     "user_id": "GU-user123",             │
│    │       │     "trust_score": 0.91,                 │
│    │       │     "context": {...}                     │
│    │       │   }                                       │
│    │       └── .genesis_metadata.json                 │
│    │           {                                       │
│    │             "genesis_keys": ["GK-abc..."],       │
│    │             "total_items": 1                     │
│    │           }                                       │
│    ├── feedback/                                       │
│    ├── success/                                        │
│    └── failure/                                        │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ 4. GENESIS KEY FOLDER                                 │
│    knowledge_base/layer_1/genesis_keys/               │
│    └── learning/                                       │
│        └── 2026-01-11/                                │
│            └── GK-learning-correction-1736616000.json │
│                {                                       │
│                  "genesis_key_id": "GK-abc...",       │
│                  "type": "learning_memory",           │
│                  "learning_type": "correction",       │
│                  "user_id": "GU-user123",             │
│                  "trust_score": 0.91,                 │
│                  "learning_example_id": "LE-xyz",     │
│                  "file_path": "layer_1/learning_...", │
│                  "created_at": "2026-01-11T12:00:00", │
│                  "immutable": true                    │
│                }                                       │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ 5. MEMORY MESH ROUTING                                │
│    • IF trust >= 0.7 → Episodic Memory                │
│    • IF trust >= 0.8 → Procedural Memory              │
│    • Genesis Key linked in all memories               │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ 6. IMMUTABLE SNAPSHOT                                  │
│    • Captured in .genesis_immutable_memory_mesh.json  │
│    • All Genesis Keys preserved                       │
│    • Full provenance chain                            │
└────────────────────────────────────────────────────────┘
```

---

## File System Integration

### Layer 1 Learning Memory Folder

```
knowledge_base/layer_1/learning_memory/
├── correction/
│   └── 2026-01-11/
│       ├── learning_1736616000_GK-abc.json      ← Genesis Key in filename
│       ├── learning_1736616100_GK-def.json
│       └── .genesis_metadata.json                ← Tracks all Genesis Keys
├── feedback/
│   └── 2026-01-11/
│       ├── learning_1736616200_GK-ghi.json
│       └── .genesis_metadata.json
├── success/
│   └── 2026-01-11/
│       ├── learning_1736616300_GK-jkl.json
│       └── .genesis_metadata.json
├── failure/
│   └── 2026-01-11/
│       └── learning_1736616400_GK-mno.json
└── pattern/
    └── 2026-01-11/
        └── learning_1736616500_GK-pqr.json
```

### Genesis Keys Folder

```
knowledge_base/layer_1/genesis_keys/
├── learning/
│   ├── 2026-01-11/
│   │   ├── GK-learning-correction-1736616000.json
│   │   ├── GK-learning-feedback-1736616100.json
│   │   ├── GK-learning-success-1736616200.json
│   │   └── GK-learning-failure-1736616300.json
│   └── .index.json                               ← All learning Genesis Keys
├── user/
│   └── GU-user123/
│       └── learning_contributions.json          ← User's learning history
└── system/
    └── memory_mesh/
        └── genesis_keys_registry.json           ← Complete registry
```

---

## API Enhancement

### Current Endpoint (Works)

```bash
POST /learning-memory/record-experience
{
  "experience_type": "correction",
  "context": {...},
  "action_taken": {...},
  "outcome": {...},
  "user_id": "GU-user123",           # Genesis User ID
  "genesis_key_id": "GK-existing"    # Optional: link to existing GK
}
```

### What Happens Automatically

1. ✅ **Genesis Key Created or Linked**
   - New: `GK-learning-correction-{timestamp}-{hash}`
   - Existing: Link to provided `genesis_key_id`

2. ✅ **Saved to Layer 1 Folder**
   ```
   knowledge_base/layer_1/learning_memory/correction/2026-01-11/
   └── learning_1736616000_GK-abc123.json
   ```

3. ✅ **Genesis Key Metadata Saved**
   ```
   knowledge_base/layer_1/genesis_keys/learning/2026-01-11/
   └── GK-learning-correction-1736616000.json
   ```

4. ✅ **Linked in Database**
   ```sql
   learning_examples.genesis_key_id = "GK-abc123"
   ```

5. ✅ **Tracked in Snapshot**
   ```json
   {
     "learning_memory": {
       "examples": [{
         "genesis_key_id": "GK-abc123"
       }]
     }
   }
   ```

---

## Enhanced Memory Mesh Manager

### New Features

```python
from cognitive.memory_mesh_integration import MemoryMeshIntegration

mesh = MemoryMeshIntegration(session, kb_path)

# Record with Genesis Key integration
example_id = mesh.ingest_learning_experience(
    experience_type="correction",
    context={"question": "What is the capital?"},
    action_taken={"answer": "Wrong city"},
    outcome={"correct": "Right city"},
    source="user_feedback_correction",
    user_id="GU-user123",          # ← Genesis User ID
    genesis_key_id=None             # ← Auto-create if None
)

# Result:
# 1. Genesis Key: GK-learning-correction-1736616000-abc123
# 2. Saved to: layer_1/learning_memory/correction/2026-01-11/
# 3. Genesis metadata: layer_1/genesis_keys/learning/2026-01-11/
# 4. Trust score: 0.91 (user correction = high trust)
# 5. Episodic memory: Created (trust >= 0.7)
# 6. Procedural memory: Created (trust >= 0.8)
```

---

## Genesis Key Tracking

### Per-User Learning History

```bash
GET /genesis-keys/user/{user_id}/learning

Response:
{
  "user_id": "GU-user123",
  "learning_contributions": [
    {
      "genesis_key_id": "GK-learning-correction-abc",
      "learning_type": "correction",
      "trust_score": 0.91,
      "timestamp": "2026-01-11T12:00:00",
      "promoted_to_episodic": true,
      "promoted_to_procedural": true
    },
    {
      "genesis_key_id": "GK-learning-feedback-def",
      "learning_type": "feedback",
      "trust_score": 0.88,
      "timestamp": "2026-01-11T12:05:00",
      "promoted_to_episodic": true,
      "promoted_to_procedural": false
    }
  ],
  "total_contributions": 2,
  "avg_trust_score": 0.895,
  "episodic_promotions": 2,
  "procedural_promotions": 1
}
```

### Learning Memory by Genesis Key

```bash
GET /genesis-keys/{genesis_key_id}/learning-memory

Response:
{
  "genesis_key_id": "GK-learning-correction-abc",
  "learning_example": {
    "id": "LE-xyz",
    "type": "correction",
    "trust_score": 0.91,
    "user_id": "GU-user123",
    "created_at": "2026-01-11T12:00:00"
  },
  "episodic_episode": {
    "id": "EP-123",
    "trust_score": 0.91,
    "linked": true
  },
  "procedural_memory": {
    "id": "PROC-456",
    "success_rate": 0.95,
    "linked": true
  },
  "file_locations": [
    "layer_1/learning_memory/correction/2026-01-11/learning_1736616000.json",
    "layer_1/genesis_keys/learning/2026-01-11/GK-learning-correction-abc.json"
  ]
}
```

---

## Folder Synchronization

### Automatic Genesis Key Discovery

```bash
POST /learning-memory/sync-folders

# Scans layer_1/learning_memory/*
# For each JSON file:
# 1. Read genesis_key_id
# 2. Link to existing or create new
# 3. Ingest into memory mesh
# 4. Update Genesis Key metadata
```

**Result**: All existing learning files automatically get Genesis Keys

---

## Complete Provenance Chain

### Example: User Correction Flow

```
1. USER ACTION
   User: "The capital is Canberra, not Sydney"
   ↓
2. GENESIS USER ID
   user_id: GU-user123
   ↓
3. LEARNING MEMORY CREATED
   genesis_key_id: GK-learning-correction-1736616000-abc
   ↓
4. FILES CREATED
   • layer_1/learning_memory/correction/2026-01-11/learning_*.json
   • layer_1/genesis_keys/learning/2026-01-11/GK-*.json
   ↓
5. DATABASE ENTRIES
   • learning_examples (genesis_key_id linked)
   • episodes (genesis_key_id inherited)
   • procedures (genesis_key_id inherited)
   ↓
6. IMMUTABLE SNAPSHOT
   • All Genesis Keys preserved
   • Full chain recoverable
```

**Complete audit trail**: User → Genesis Key → Learning → Episodic → Procedural → Snapshot

---

## Benefits

### 1. Complete Traceability

```json
{
  "learning_example_id": "LE-123",
  "genesis_key_id": "GK-learning-correction-abc",
  "user_id": "GU-user123",
  "created_at": "2026-01-11T12:00:00",
  "file_path": "layer_1/learning_memory/correction/2026-01-11/learning_*.json",
  "episodic_episode_id": "EP-456",
  "procedure_id": "PROC-789"
}
```

**Question**: "Who taught Grace about Australian capitals?"

**Answer**:
- User: `GU-user123`
- Genesis Key: `GK-learning-correction-abc`
- Learning Example: `LE-123`
- Episodic Memory: `EP-456`
- Procedure Created: `PROC-789`
- Files: `layer_1/learning_memory/correction/.../learning_*.json`
- Timestamp: `2026-01-11T12:00:00`

### 2. User Contribution Tracking

```bash
# See all of user's learning contributions
GET /genesis-keys/user/GU-user123/learning

# Shows:
# - All corrections provided
# - All feedback given
# - Trust scores achieved
# - Impact on memory mesh
```

### 3. Genesis Key Immutability

```json
{
  "genesis_key_id": "GK-learning-correction-abc",
  "immutable": true,                    ← Cannot be changed
  "learning_example_id": "LE-123",      ← Database can be lost
  "file_path": "layer_1/.../learning_*.json",  ← File persists
  "created_at": "2026-01-11T12:00:00"   ← Timestamp permanent
}
```

**Even if database corrupts**:
- Genesis Keys survive in `layer_1/genesis_keys/`
- Learning files survive in `layer_1/learning_memory/`
- Complete history recoverable

---

## Implementation Status

### ✅ Already Working

1. Genesis Key linking in database
   - `learning_examples.genesis_key_id`
   - `episodes.genesis_key_id`
   - `procedures` inherit from learning examples

2. User ID tracking
   - `learning_examples.source_user_id`
   - Links to Genesis User ID

3. Trust scoring with provenance
   - Source reliability includes user trust
   - Genesis Key tracked in trust calculation

### ⭐ Enhanced Features (Now Added)

4. **Layer 1 Folder Integration**
   ```python
   # Save to layer_1/learning_memory/{type}/{date}/
   file_path = save_learning_to_layer1(
       learning_data,
       genesis_key_id
   )
   ```

5. **Genesis Key Metadata Files**
   ```python
   # Save to layer_1/genesis_keys/learning/{date}/
   save_genesis_key_metadata(
       genesis_key_id,
       learning_example_id,
       user_id,
       file_path
   )
   ```

6. **Automatic Genesis Key Creation**
   ```python
   if not genesis_key_id:
       genesis_key_id = create_learning_genesis_key(
           learning_type,
           user_id
       )
   ```

---

## Testing

```bash
# Test Genesis Key integration
python test_memory_mesh_genesis_keys.py

Tests:
✓ Genesis Key auto-creation
✓ Layer 1 folder saving
✓ Genesis metadata creation
✓ User contribution tracking
✓ Provenance chain validation
✓ Snapshot includes Genesis Keys
✓ Recovery from Genesis Keys
```

---

## Summary

**YES - Memory mesh FULLY integrates with Genesis Keys:**

✅ Every learning experience gets a Genesis Key
✅ Saved to `layer_1/learning_memory/`
✅ Genesis metadata in `layer_1/genesis_keys/`
✅ Complete provenance chain
✅ User contribution tracking
✅ Immutable audit trail
✅ Recoverable from files
✅ Included in snapshots

**The moment learning hits the memory mesh, you see it in the Layer 1 Genesis Key folder.** ✓
