# 🔗 Symbiotic Genesis Key + Version Control System

## 🌟 Core Concept: ONE UNIFIED SYSTEM

Genesis Keys and Version Control are **NOT separate systems** - they are **ONE SYMBIOTIC SYSTEM** where:

- **Genesis Keys ARE Version Control entries**
- **Version Control entries ARE Genesis Keys**
- **They cannot exist separately**
- **Every change creates BOTH simultaneously**
- **They reference each other bidirectionally**

## 🧬 Symbiotic Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            SYMBIOTIC VERSION CONTROL SYSTEM                  │
│                                                               │
│    Genesis Key ←────────────────────→ Version Entry          │
│                   BIDIRECTIONAL                               │
│                                                               │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │ Genesis Key  │◄──── linked ─────►│  Version     │       │
│  │              │                    │  Entry       │       │
│  │ • key_id     │                    │ • version_#  │       │
│  │ • what       │                    │ • file_hash  │       │
│  │ • who        │                    │ • timestamp  │       │
│  │ • when       │                    │ • content    │       │
│  │ • why        │                    │ • genesis_id │       │
│  │ • how        │                    │              │       │
│  │ • version_id │                    │              │       │
│  └──────────────┘                    └──────────────┘       │
│         │                                    │                │
│         └────────────── ONE ENTITY ─────────┘                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 How It Works

### Traditional (Separate) Systems ❌
```
File Changed
    ↓
Create Genesis Key  ←── Independent
    ↓
Create Version Entry ←── Independent
    ↓
Maybe link them? (optional)
```

### Symbiotic System ✅
```
File Changed
    ↓
    ╔═══════════════════════════════════╗
    ║  SYMBIOTIC OPERATION (atomic)     ║
    ║                                   ║
    ║  1. Create Genesis Key            ║
    ║  2. Create Version Entry          ║
    ║  3. Link bidirectionally          ║
    ║  4. Update both simultaneously    ║
    ║                                   ║
    ║  → ONE operation, ONE result      ║
    ╚═══════════════════════════════════╝
    ↓
Both created together, linked forever
```

## 📦 New File: Symbiotic Version Control

**[backend/genesis/symbiotic_version_control.py](backend/genesis/symbiotic_version_control.py)**

This file creates the unified system with:

### `track_file_change()` - Symbiotic Tracking
Creates Genesis Key + Version Entry **simultaneously**:

```python
from backend.genesis.symbiotic_version_control import get_symbiotic_version_control

symbiotic = get_symbiotic_version_control()

# ONE operation creates BOTH
result = symbiotic.track_file_change(
    file_path="backend/app.py",
    user_id="GU-abc123...",
    change_description="Fixed authentication bug",
    operation_type="modify"
)

# Returns BOTH Genesis Key and Version info
print(result)
{
    "file_genesis_key": "FILE-abc123...",
    "operation_genesis_key": "GK-550e8400...",  # Genesis Key created
    "version_key_id": "VER-abc123...-5",         # Version created
    "version_number": 5,
    "changed": True,
    "symbiotic": True,  # They're linked!
    "message": "Genesis Key and version entry created symbiotically"
}
```

### `get_complete_history()` - Unified Timeline
Get **BOTH** Genesis Keys and versions in one view:

```python
# Get complete unified history
history = symbiotic.get_complete_history("FILE-abc123...")

print(history)
{
    "file_genesis_key": "FILE-abc123...",
    "total_entries": 10,
    "timeline": [
        {
            "type": "version",
            "timestamp": "2026-01-11T10:00:00Z",
            "version_number": 1,
            "version_key_id": "VER-abc123...-1",
            "genesis_key_id": "GK-...",  # Linked!
            "user_id": "system",
            "note": "Initial version"
        },
        {
            "type": "genesis_key",
            "timestamp": "2026-01-11T10:05:00Z",
            "key_id": "GK-550e8400...",
            "what": "Modified file",
            "who": "GU-abc123...",
            "why": "Fixed bug",
            "linked_version": "VER-abc123...-2"  # Linked!
        },
        {
            "type": "version",
            "timestamp": "2026-01-11T10:05:00Z",
            "version_number": 2,
            "version_key_id": "VER-abc123...-2",
            "genesis_key_id": "GK-550e8400...",  # Same Genesis Key!
            "file_hash": "sha256-..."
        }
    ],
    "symbiotic": True
}
```

### `rollback_to_version()` - Symbiotic Rollback
Rollback creates **BOTH** Genesis Key and new version:

```python
# Rollback to version 3
result = symbiotic.rollback_to_version(
    file_genesis_key="FILE-abc123...",
    version_number=3,
    user_id="GU-xyz789..."
)

print(result)
{
    "rollback_genesis_key": "GK-rollback123...",  # Genesis Key for rollback
    "rolled_back_to_version": 3,
    "new_version_created": 6,                     # New version created!
    "new_version_key": "VER-abc123...-6",
    "symbiotic": True,
    "message": "Rolled back to version 3 - created new version 6"
}
```

## 🔌 New API Endpoints

### POST /repo-genesis/symbiotic/track-change
Track file change symbiotically.

**Request:**
```json
{
  "file_path": "backend/app.py",
  "user_id": "GU-abc123...",
  "change_description": "Fixed authentication bug",
  "operation_type": "modify"
}
```

**Response:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "operation_genesis_key": "GK-550e8400...",
  "version_key_id": "VER-abc123...-5",
  "version_number": 5,
  "changed": true,
  "file_path": "backend/app.py",
  "timestamp": "2026-01-11T10:00:00Z",
  "symbiotic": true,
  "message": "Genesis Key and version entry created symbiotically"
}
```

### GET /repo-genesis/symbiotic/history/{file_genesis_key}
Get complete unified history.

**Response:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "total_entries": 10,
  "timeline": [
    {
      "type": "version",
      "timestamp": "2026-01-11T10:00:00Z",
      "version_number": 1,
      "version_key_id": "VER-abc123...-1",
      "genesis_key_id": "GK-...",
      "linked": true
    },
    {
      "type": "genesis_key",
      "timestamp": "2026-01-11T10:05:00Z",
      "key_id": "GK-550e8400...",
      "what": "Modified file",
      "linked_version": "VER-abc123...-2"
    }
  ],
  "symbiotic": true
}
```

### POST /repo-genesis/symbiotic/rollback
Rollback to a version symbiotically.

**Request:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "version_number": 3,
  "user_id": "GU-xyz789..."
}
```

**Response:**
```json
{
  "rollback_genesis_key": "GK-rollback123...",
  "rolled_back_to_version": 3,
  "new_version_created": 6,
  "new_version_key": "VER-abc123...-6",
  "symbiotic": true,
  "message": "Rolled back to version 3 - created new version 6"
}
```

### POST /repo-genesis/symbiotic/watch
Watch a file for automatic symbiotic tracking.

**Request:**
```json
{
  "file_path": "backend/app.py",
  "user_id": "GU-abc123..."
}
```

**Response:**
```json
{
  "watching": "backend/app.py",
  "file_genesis_key": "FILE-abc123...",
  "user_id": "GU-abc123...",
  "auto_track": true,
  "symbiotic": true,
  "message": "File changes will automatically create Genesis Keys and versions"
}
```

### GET /repo-genesis/symbiotic/stats
Get symbiotic integration statistics.

**Response:**
```json
{
  "version_control": {
    "total_files_tracked": 230,
    "total_versions": 845,
    "average_versions_per_file": 3.67
  },
  "genesis_keys": {
    "total_file_operations": 845,
    "symbiotic_operations": 845
  },
  "integration_percentage": 100,
  "message": "Genesis Keys and Version Control working symbiotically"
}
```

## 🎯 Usage Examples

### Example 1: Track a File Change

```bash
# Traditional approach (separate)
curl -X POST http://localhost:8000/genesis/keys \
  -d '{"what": "Modified app.py", ...}'

curl -X POST http://localhost:8000/repo-genesis/file/track-version \
  -d '{"file_genesis_key": "FILE-...", ...}'

# Symbiotic approach (unified)
curl -X POST http://localhost:8000/repo-genesis/symbiotic/track-change \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "backend/app.py",
    "user_id": "GU-abc123...",
    "change_description": "Fixed authentication bug",
    "operation_type": "modify"
  }'

# ONE call creates BOTH Genesis Key and version!
```

### Example 2: View Complete History

```bash
# Traditional approach (separate queries)
curl http://localhost:8000/genesis/keys?file_path=app.py
curl http://localhost:8000/repo-genesis/file/FILE-abc.../versions

# Symbiotic approach (unified view)
curl http://localhost:8000/repo-genesis/symbiotic/history/FILE-abc123...

# ONE call returns BOTH in unified timeline!
```

### Example 3: Rollback with Full Tracking

```bash
# Symbiotic rollback
curl -X POST http://localhost:8000/repo-genesis/symbiotic/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "version_number": 3,
    "user_id": "GU-xyz789..."
  }'

# Creates:
# 1. Genesis Key for the rollback operation
# 2. New version entry (rollback IS a new version)
# 3. Links them bidirectionally
# 4. Updates file content
```

### Example 4: Python Usage

```python
from backend.genesis.symbiotic_version_control import get_symbiotic_version_control

# Get symbiotic system
symbiotic = get_symbiotic_version_control()

# Track a change (creates both)
result = symbiotic.track_file_change(
    file_path="backend/api/auth.py",
    user_id="GU-abc123...",
    change_description="Added JWT token validation",
    operation_type="modify"
)

print(f"Genesis Key: {result['operation_genesis_key']}")
print(f"Version: {result['version_number']}")
print(f"They're linked: {result['symbiotic']}")

# Get complete history (unified timeline)
history = symbiotic.get_complete_history("FILE-auth123...")

# See both Genesis Keys and versions together
for entry in history["timeline"]:
    if entry["type"] == "version":
        print(f"Version {entry['version_number']}: {entry['version_key_id']}")
        print(f"  → Linked to Genesis Key: {entry['genesis_key_id']}")
    elif entry["type"] == "genesis_key":
        print(f"Genesis Key: {entry['key_id']}")
        print(f"  → Linked to Version: {entry['linked_version']}")

# Rollback (creates both)
rollback_result = symbiotic.rollback_to_version(
    file_genesis_key="FILE-auth123...",
    version_number=2,
    user_id="GU-abc123..."
)

print(f"Rollback Genesis Key: {rollback_result['rollback_genesis_key']}")
print(f"New version created: {rollback_result['new_version_created']}")
```

## 🔄 Data Flow

### Symbiotic File Change

```
1. User modifies file
   ↓
2. Symbiotic system triggered
   ↓
3. ╔════════════════════════════════════╗
   ║ ATOMIC OPERATION                   ║
   ║                                    ║
   ║ a) Create Genesis Key:             ║
   ║    - what: "Modified app.py"       ║
   ║    - who: "GU-abc123..."           ║
   ║    - when: timestamp               ║
   ║    - why: "Fixed bug"              ║
   ║    - how: "Symbiotic VC"           ║
   ║    - context: {version_info}       ║
   ║                                    ║
   ║ b) Create Version Entry:           ║
   ║    - version_number: 5             ║
   ║    - file_hash: sha256             ║
   ║    - content: full file            ║
   ║    - note: "Genesis Key: GK-..."   ║
   ║                                    ║
   ║ c) Link bidirectionally:           ║
   ║    Genesis Key → version_key_id    ║
   ║    Version → genesis_key_db_id     ║
   ║                                    ║
   ║ d) Save both:                      ║
   ║    - Database (Genesis Key)        ║
   ║    - JSON file (Version metadata)  ║
   ║    - Knowledge base (auto-save)    ║
   ╚════════════════════════════════════╝
   ↓
4. Return unified result
   ↓
5. Both systems updated simultaneously
```

## 💡 Key Benefits

### 1. **Guaranteed Consistency**
- Genesis Key **always** has corresponding version
- Version **always** has corresponding Genesis Key
- No orphaned entries

### 2. **Complete Traceability**
- Every change has full context (what, why, who, when)
- Every version linked to its Genesis Key
- Bidirectional navigation

### 3. **Single Source of Truth**
- One operation to track changes
- One query to get complete history
- No data synchronization issues

### 4. **Atomic Operations**
- Either both created or neither
- No partial states
- Transaction-safe

### 5. **Simplified API**
- One endpoint instead of two
- Unified response format
- Less code, fewer errors

## 🔍 Comparison

### Before (Separate Systems)

```python
# Need TWO operations
genesis_key = create_genesis_key(...)
version = create_version(...)

# Hope they're linked correctly
# Maybe they are, maybe they're not
# Could have genesis_key without version
# Could have version without genesis_key
```

### After (Symbiotic System)

```python
# ONE operation
result = symbiotic.track_file_change(...)

# GUARANTEED to have both
# ALWAYS linked
# ALWAYS consistent
# ONE source of truth
```

## 📊 Integration Percentage

The symbiotic system tracks **integration percentage**:

```bash
curl http://localhost:8000/repo-genesis/symbiotic/stats

{
  "integration_percentage": 100,
  "message": "Genesis Keys and Version Control working symbiotically"
}
```

- **100%** = All file operations are symbiotic
- **< 100%** = Some operations are still separate (legacy)

Goal: **100% symbiotic integration**

## 🎉 Summary

The Symbiotic Genesis Key + Version Control System makes them **ONE UNIFIED SYSTEM**:

✅ **Genesis Keys ARE Version Control**
✅ **Version Control IS Genesis Keys**
✅ **One operation creates both**
✅ **Bidirectionally linked forever**
✅ **Guaranteed consistency**
✅ **Complete traceability**
✅ **Single source of truth**
✅ **Atomic operations**
✅ **Simplified API**

## 🚀 Quick Start

```bash
# 1. Track a file change (symbiotic)
curl -X POST http://localhost:8000/repo-genesis/symbiotic/track-change \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "backend/app.py",
    "user_id": "GU-abc123...",
    "change_description": "My change"
  }'

# 2. View complete history (unified)
curl http://localhost:8000/repo-genesis/symbiotic/history/FILE-abc123...

# 3. Rollback (symbiotic)
curl -X POST http://localhost:8000/repo-genesis/symbiotic/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "version_number": 3
  }'

# 4. Check symbiotic stats
curl http://localhost:8000/repo-genesis/symbiotic/stats
```

---

**🧬 Genesis Keys + Version Control = ONE SYMBIOTIC SYSTEM**
