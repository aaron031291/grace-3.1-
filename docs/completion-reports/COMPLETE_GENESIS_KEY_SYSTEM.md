# 🔑 Complete Genesis Key System - Full Documentation

## 🌟 Overview

The Genesis Key System is a comprehensive tracking, version control, and healing system that provides:

- **Universal Identification**: Every directory, file, user, session, and action gets a unique Genesis Key
- **Complete Version Control**: Files are version-controlled through their Genesis Keys with automatic change detection
- **Immutable Memory**: Permanent snapshot of entire repository structure
- **Scaffolded Healing**: AI-powered debugging and fixing using Genesis Keys for navigation
- **Auto-Population**: Everything saved to knowledge_base/layer_1/genesis_key/
- **Complete Audit Trail**: Track what, where, when, why, who, and how for every operation

## 📊 Genesis Key Types

### User Genesis Keys (GU-prefix)
- Format: `GU-{16-char-hex}`
- Purpose: Unique identifier for each user (serves as profile ID)
- Example: `GU-abc123def456789`

### Session Genesis Keys (SS-prefix)
- Format: `SS-{16-char-hex}`
- Purpose: Track user sessions (24-hour lifespan)
- Example: `SS-xyz789abc123456`

### Directory Genesis Keys (DIR-prefix)
- Format: `DIR-{12-char-hex}`
- Purpose: Unique identifier for each directory in the repository
- Example: `DIR-abc123def456`

### File Genesis Keys (FILE-prefix)
- Format: `FILE-{12-char-hex}` (MD5 hash of relative path)
- Purpose: Unique identifier for each file in the repository
- Example: `FILE-xyz789abc123`

### Version Genesis Keys (VER-prefix)
- Format: `VER-{file-key-portion}-{version-number}`
- Purpose: Track specific versions of files
- Example: `VER-xyz789abc123-1` (version 1 of file FILE-xyz789abc123)

### General Genesis Keys (GK-prefix)
- Format: `GK-{uuid}`
- Purpose: Track operations, requests, responses, errors, fixes
- Example: `GK-550e8400-e29b-41d4-a716-446655440000`

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Genesis Key System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ User Login    │  │ Middleware   │  │ File Operations │  │
│  │ (GU-prefix)   │  │ (GK-prefix)  │  │ (FILE-prefix)   │  │
│  └───────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
│          │                  │                    │            │
│          ▼                  ▼                    ▼            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Genesis Key Service (Core Engine)             │ │
│  │  - Creates and manages all Genesis Keys                │ │
│  │  - Tracks: what, where, when, why, who, how            │ │
│  │  - Auto-saves to knowledge base                        │ │
│  └────────────────┬──────────────────┬────────────────────┘ │
│                   │                  │                       │
│                   ▼                  ▼                       │
│  ┌─────────────────────┐  ┌────────────────────────┐       │
│  │ File Version Tracker│  │ Directory Hierarchy     │       │
│  │ (VER-prefix)        │  │ (DIR-prefix)            │       │
│  │ - Tracks versions   │  │ - Hierarchical structure│       │
│  │ - Hash comparison   │  │ - Parent-child links    │       │
│  │ - Auto-detection    │  │ - README generation     │       │
│  └─────────────────────┘  └────────────────────────┘       │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Repository Scanner (Immutable Memory)         │ │
│  │  - Scans entire repository                              │ │
│  │  - Assigns Genesis Keys to everything                   │ │
│  │  - Creates permanent snapshot                           │ │
│  │  - Integrates with version tracking                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │             Healing System (Debugging)                  │ │
│  │  - Navigate to issues using Genesis Keys                │ │
│  │  - AI-powered code analysis                             │ │
│  │  - One-click fix application                            │ │
│  │  - Scaffolded healing for directories                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Knowledge Base Auto-Population                 │ │
│  │  knowledge_base/layer_1/genesis_key/                    │ │
│  │  ├── GU-abc.../profile.json                             │ │
│  │  ├── GU-abc.../session_SS-xyz....json                   │ │
│  │  └── .genesis_immutable_memory.json                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

### Backend Files Created

1. **[backend/models/genesis_key_models.py](backend/models/genesis_key_models.py)**
   - Database models for Genesis Keys
   - GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile

2. **[backend/genesis/genesis_key_service.py](backend/genesis/genesis_key_service.py)**
   - Core service for creating and managing Genesis Keys
   - Context managers for automatic tracking
   - Auto-saves to knowledge base

3. **[backend/genesis/kb_integration.py](backend/genesis/kb_integration.py)**
   - Auto-population to knowledge_base/layer_1/genesis_key/
   - User folder organization
   - Session-based grouping

4. **[backend/genesis/file_version_tracker.py](backend/genesis/file_version_tracker.py)** ⭐ NEW
   - File version control through Genesis Keys
   - Auto-detects file changes via hash comparison
   - Complete version history with metadata

5. **[backend/genesis/directory_hierarchy.py](backend/genesis/directory_hierarchy.py)**
   - Manages Genesis Keys for directory hierarchies
   - Every directory gets unique DIR-prefix key
   - README generation with Genesis Key info

6. **[backend/genesis/repo_scanner.py](backend/genesis/repo_scanner.py)**
   - Scans entire repository
   - Assigns Genesis Keys to all directories and files
   - Creates immutable memory snapshot
   - Integrates with file version tracker

7. **[backend/genesis/healing_system.py](backend/genesis/healing_system.py)**
   - Scaffolded healing using Genesis Keys
   - AI-powered code analysis
   - One-click fix application

8. **[backend/genesis/code_analyzer.py](backend/genesis/code_analyzer.py)**
   - Error detection and fix suggestions
   - Python/JavaScript analysis

9. **[backend/genesis/archival_service.py](backend/genesis/archival_service.py)**
   - Daily archival (runs at 2 AM)
   - Comprehensive reports

10. **[backend/genesis/middleware.py](backend/genesis/middleware.py)**
    - Automatic request/response tracking
    - Genesis ID assignment on first access

### API Endpoints

11. **[backend/api/auth.py](backend/api/auth.py)**
    - Login with Genesis ID assignment
    - Session management

12. **[backend/api/genesis_keys.py](backend/api/genesis_keys.py)**
    - CRUD for Genesis Keys
    - Code analysis and fix suggestions

13. **[backend/api/directory_hierarchy.py](backend/api/directory_hierarchy.py)**
    - Directory hierarchy management
    - Genesis Key assignment

14. **[backend/api/repo_genesis.py](backend/api/repo_genesis.py)** ⭐ UPDATED
    - Repository scanning endpoints
    - File version tracking endpoints
    - Healing system endpoints
    - Layer_1 structure display

### Frontend Components

15. **[frontend/src/components/GenesisKeyPanel.jsx](frontend/src/components/GenesisKeyPanel.jsx)**
    - Main Genesis Key dashboard
    - Error/fix viewing with double-click navigation

16. **[frontend/src/components/GenesisLogin.jsx](frontend/src/components/GenesisLogin.jsx)**
    - Login interface with Genesis ID display

## 🔑 Complete API Reference

### Repository Scanning

#### POST /repo-genesis/scan
Scan entire repository and assign Genesis Keys.

**Request:**
```json
{
  "repo_path": "/path/to/repo",  // Optional, defaults to grace_3 root
  "integrate_version_tracking": true,  // Optional, default true
  "user_id": "GU-abc123..."  // Optional
}
```

**Response:**
```json
{
  "scan_timestamp": "2026-01-11T10:00:00Z",
  "repo_path": "/path/to/repo",
  "root_genesis_key": "DIR-abc123...",
  "total_directories": 45,
  "total_files": 230,
  "total_size_bytes": 5242880,
  "immutable_memory_path": "/path/to/.genesis_immutable_memory.json"
}
```

#### GET /repo-genesis/tree/{path}
Get directory tree with Genesis Keys.

#### GET /repo-genesis/find/{genesis_key}
Find directory or file by Genesis Key.

#### GET /repo-genesis/layer1
Display layer_1 folder structure.

### File Version Tracking

#### POST /repo-genesis/file/track-version
Track a new version of a file.

**Request:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "file_path": "backend/app.py",
  "user_id": "GU-xyz789...",
  "version_note": "Fixed authentication bug",
  "auto_detect_change": true
}
```

**Response:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "version_key_id": "VER-abc123...-5",
  "version_number": 5,
  "changed": true,
  "file_hash": "sha256-hash...",
  "timestamp": "2026-01-11T10:00:00Z"
}
```

#### GET /repo-genesis/file/{file_genesis_key}/versions
Get all versions for a file.

#### GET /repo-genesis/file/{file_genesis_key}/version/{version_number}
Get details for specific version.

#### GET /repo-genesis/file/{file_genesis_key}/latest
Get latest version of a file.

#### GET /repo-genesis/file/{file_genesis_key}/diff?version1=1&version2=2
Get differences between two versions.

#### POST /repo-genesis/directory/auto-track
Automatically track all files in a directory.

**Request:**
```json
{
  "directory_path": "backend/",
  "user_id": "GU-xyz789...",
  "recursive": true,
  "file_pattern": "*.py"
}
```

#### GET /repo-genesis/file/statistics
Get file tracking statistics.

#### GET /repo-genesis/file/list-tracked
List all tracked files.

### Healing System

#### POST /repo-genesis/heal/file
Heal a file using its Genesis Key.

**Request:**
```json
{
  "file_genesis_key": "FILE-abc123...",
  "user_id": "GU-xyz789...",
  "auto_apply": false
}
```

#### POST /repo-genesis/heal/directory
Heal all files in a directory.

#### POST /repo-genesis/navigate
Navigate to an issue using Genesis Key.

#### GET /repo-genesis/healing/summary
Get healing system summary.

### Authentication

#### POST /auth/login
Login and get Genesis ID.

#### GET /auth/session
Get current session info.

#### GET /auth/whoami
Check current Genesis ID.

#### POST /auth/logout
Logout and clear Genesis ID.

### Genesis Keys

#### GET /genesis/keys
List Genesis Keys with filters.

#### POST /genesis/keys
Create a Genesis Key.

#### GET /genesis/keys/{key_id}
Get specific Genesis Key.

#### DELETE /genesis/keys/{key_id}
Delete Genesis Key.

#### POST /genesis/analyze-code
Analyze code for errors.

#### POST /genesis/fixes/{id}/apply
Apply a fix suggestion.

#### GET /genesis/stats
Get statistics.

#### GET /genesis/archives
Get archived keys.

### Directory Hierarchy

#### POST /directory-hierarchy/directories
Create directory with Genesis Key.

#### POST /directory-hierarchy/hierarchies
Create complete directory hierarchy.

#### GET /directory-hierarchy/directories/{path}
Get directory info.

#### GET /directory-hierarchy/trees/{path}
Get directory tree.

#### POST /directory-hierarchy/initialize
Initialize knowledge_base hierarchy.

## 🚀 Complete Usage Guide

### 1. Initial Setup

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run migration
python database/migrate_add_genesis_keys.py

# Start backend
uvicorn app:app --reload

# Start frontend (in another terminal)
cd frontend
npm start
```

### 2. Scan Your Repository

**Via API:**
```bash
curl -X POST http://localhost:8000/repo-genesis/scan \
  -H "Content-Type: application/json" \
  -d '{
    "integrate_version_tracking": true,
    "user_id": "system"
  }'
```

**Via Python:**
```python
from backend.genesis.repo_scanner import scan_and_save_repo

# Scan entire repository
immutable_memory = scan_and_save_repo(
    repo_path="/path/to/grace_3",
    integrate_version_tracking=True,
    user_id="system"
)

print(f"Scanned {immutable_memory['statistics']['total_files']} files")
print(f"Assigned {immutable_memory['statistics']['total_directories']} directory keys")
```

### 3. Track File Versions

**Automatic Tracking (during scan):**
Files are automatically version-tracked when you scan with `integrate_version_tracking=True`.

**Manual Tracking:**
```bash
curl -X POST http://localhost:8000/repo-genesis/file/track-version \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "file_path": "backend/app.py",
    "user_id": "GU-xyz789...",
    "version_note": "Fixed bug in authentication"
  }'
```

**Python API:**
```python
from backend.genesis.file_version_tracker import get_file_version_tracker

tracker = get_file_version_tracker()

# Track a new version
result = tracker.track_file_version(
    file_genesis_key="FILE-abc123...",
    file_path="backend/app.py",
    user_id="GU-xyz789...",
    version_note="Fixed bug"
)

print(f"Version {result['version_number']} created")
```

### 4. View File History

```bash
# Get all versions of a file
curl http://localhost:8000/repo-genesis/file/FILE-abc123.../versions

# Get specific version
curl http://localhost:8000/repo-genesis/file/FILE-abc123.../version/3

# Compare versions
curl "http://localhost:8000/repo-genesis/file/FILE-abc123.../diff?version1=1&version2=3"
```

### 5. Use Healing System

```bash
# Heal a specific file
curl -X POST http://localhost:8000/repo-genesis/heal/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "user_id": "GU-xyz789...",
    "auto_apply": false
  }'

# Heal entire directory
curl -X POST http://localhost:8000/repo-genesis/heal/directory \
  -H "Content-Type: application/json" \
  -d '{
    "dir_genesis_key": "DIR-abc123...",
    "user_id": "GU-xyz789...",
    "auto_apply": false,
    "recursive": true
  }'
```

### 6. Navigate Using Genesis Keys

```bash
# Find anything by Genesis Key
curl http://localhost:8000/repo-genesis/find/FILE-abc123...

# Get directory tree
curl http://localhost:8000/repo-genesis/tree/backend

# View layer_1 structure
curl http://localhost:8000/repo-genesis/layer1
```

### 7. Access Immutable Memory

The immutable memory is stored as a JSON file at the repository root:

```bash
# View immutable memory
cat .genesis_immutable_memory.json

# Query with jq
cat .genesis_immutable_memory.json | jq '.files | length'
cat .genesis_immutable_memory.json | jq '.directories["backend"]'
```

## 📊 Data Storage Structure

### Immutable Memory (.genesis_immutable_memory.json)
```json
{
  "scan_timestamp": "2026-01-11T10:00:00Z",
  "repo_path": "/path/to/grace_3",
  "root_genesis_key": "DIR-abc123...",
  "directories": {
    "backend": {
      "genesis_key": "DIR-abc123...",
      "path": "backend",
      "name": "backend",
      "parent_genesis_key": "DIR-root...",
      "subdirectories": ["DIR-xyz...", "DIR-def..."],
      "files": ["FILE-ghi...", "FILE-jkl..."]
    }
  },
  "files": {
    "backend/app.py": {
      "genesis_key": "FILE-abc123...",
      "path": "backend/app.py",
      "name": "app.py",
      "directory_genesis_key": "DIR-backend...",
      "size_bytes": 15420,
      "last_modified": "2026-01-11T09:30:00Z"
    }
  },
  "statistics": {
    "total_directories": 45,
    "total_files": 230,
    "total_size_bytes": 5242880
  },
  "version_tracking": {
    "total_files": 230,
    "tracked": 225,
    "skipped": 5,
    "errors": 0
  }
}
```

### File Version Metadata (.genesis_file_versions.json)
```json
{
  "version": "1.0",
  "created_at": "2026-01-11T10:00:00Z",
  "files": {
    "FILE-abc123...": {
      "file_genesis_key": "FILE-abc123...",
      "file_path": "backend/app.py",
      "version_count": 5,
      "last_hash": "sha256-hash...",
      "versions": [
        {
          "version_number": 1,
          "version_key_id": "VER-abc123...-1",
          "timestamp": "2026-01-11T10:00:00Z",
          "file_hash": "sha256-hash-v1...",
          "file_size": 15000,
          "user_id": "system",
          "version_note": "Initial scan version"
        },
        {
          "version_number": 2,
          "version_key_id": "VER-abc123...-2",
          "timestamp": "2026-01-11T11:30:00Z",
          "file_hash": "sha256-hash-v2...",
          "file_size": 15420,
          "user_id": "GU-xyz789...",
          "version_note": "Fixed authentication bug"
        }
      ]
    }
  }
}
```

### Knowledge Base Structure
```
knowledge_base/layer_1/genesis_key/
├── README.md
├── GU-abc123.../
│   ├── profile.json
│   ├── session_SS-xyz789....json
│   └── keys_2026-01-11.json
└── system/
    └── scan_operations.json
```

## 🎯 Key Features Summary

### ✅ Universal Genesis Keys
- **Users**: GU-prefix (profile IDs)
- **Sessions**: SS-prefix (24-hour tracking)
- **Directories**: DIR-prefix (hierarchical structure)
- **Files**: FILE-prefix (unique identifiers)
- **Versions**: VER-prefix (file change history)
- **Operations**: GK-prefix (all actions tracked)

### ✅ Complete Version Control
- **Auto-detection**: Files tracked via hash comparison
- **Complete history**: Every version saved with metadata
- **Diff support**: Compare any two versions
- **Rollback capability**: Restore previous versions
- **Bulk operations**: Track entire directories at once

### ✅ Immutable Memory
- **Permanent snapshot**: Cannot be modified, only extended
- **Complete structure**: Every directory and file recorded
- **Genesis Key mapping**: Fast lookup by Genesis Key
- **Statistics**: Complete metrics on repository

### ✅ Scaffolded Healing
- **AI-powered analysis**: Automatic error detection
- **One-click fixes**: Apply fixes with single call
- **Directory healing**: Heal multiple files at once
- **Navigation**: Jump directly to issues via Genesis Keys

### ✅ Auto-Population
- **Knowledge base integration**: Everything saved automatically
- **User organization**: Organized by Genesis ID
- **Session grouping**: Grouped by session
- **Complete audit trail**: Full history preserved

### ✅ Complete Metadata
Every Genesis Key tracks:
- **What**: Description of the operation
- **Where**: Location (file path, endpoint, etc.)
- **When**: Timestamp (UTC)
- **Why**: Reason for operation
- **Who**: User Genesis ID
- **How**: Method used

## 🔄 Workflow Examples

### Example 1: New File Added to Repository

```
1. Developer creates new file "backend/new_feature.py"
2. File is detected during next scan or manual tracking
3. Genesis Key assigned: FILE-new123...
4. Initial version created: VER-new123...-1
5. File info saved to immutable memory
6. Version metadata saved to .genesis_file_versions.json
7. Genesis Key created in database with metadata
8. Auto-saved to knowledge_base/layer_1/genesis_key/
```

### Example 2: File Modified

```
1. Developer modifies "backend/app.py"
2. Manual or automatic version tracking triggered
3. File hash computed and compared
4. Change detected (hash different)
5. New version created: VER-abc123...-6
6. Version Genesis Key linked to file Genesis Key
7. Complete file content snapshot saved
8. Version metadata updated
9. All changes auto-saved to knowledge base
```

### Example 3: Error Detected and Fixed

```
1. Error occurs in "backend/api/auth.py"
2. Healing system analyzes file via FILE-auth123...
3. AI detects syntax error on line 45
4. Fix suggestion generated with 0.95 confidence
5. User navigates to issue via Genesis Key
6. One-click fix applied
7. New version created: VER-auth123...-3
8. Healing Genesis Key created tracking the fix
9. All steps saved to knowledge base
```

## 📈 Benefits

### For Developers
- **Complete history**: Never lose track of changes
- **Quick debugging**: Navigate directly to issues
- **AI assistance**: Get fix suggestions automatically
- **Version comparison**: See exactly what changed

### For Teams
- **Full audit trail**: Know who changed what and why
- **Collaboration**: Track all team member actions
- **Code quality**: Automatic error detection
- **Rollback capability**: Restore previous versions easily

### For AI/System
- **Complete context**: Full history for better responses
- **Pattern learning**: Learn from changes and fixes
- **Personalization**: Tailor to user behavior
- **Continuous improvement**: Learn from errors

## 🔒 Security Features

- **Opaque IDs**: Genesis Keys don't expose information
- **HTTP-only cookies**: Protected from XSS
- **Local storage**: All data in your knowledge base
- **Access control**: User-based permissions
- **Immutable audit**: Can't alter history

## 📚 Additional Documentation

- **[GENESIS_KEY_SETUP.md](GENESIS_KEY_SETUP.md)** - Initial setup guide
- **[GENESIS_ID_LOGIN.md](GENESIS_ID_LOGIN.md)** - Login system details
- **[GENESIS_COMPLETE_IMPLEMENTATION.md](GENESIS_COMPLETE_IMPLEMENTATION.md)** - Implementation summary
- **[DIRECTORY_HIERARCHY_GENESIS_KEYS.md](DIRECTORY_HIERARCHY_GENESIS_KEYS.md)** - Directory hierarchy details

## 🎉 Summary

You now have a **complete Genesis Key system** that:

✅ **Scans your entire repository** and assigns Genesis Keys to everything
✅ **Tracks file versions automatically** with hash-based change detection
✅ **Stores everything in immutable memory** for permanent record
✅ **Provides scaffolded healing** for AI-powered debugging
✅ **Auto-saves to knowledge base** for complete audit trail
✅ **Supports complete version control** with rollback capability
✅ **Enables Genesis Key navigation** to jump directly to any file/directory
✅ **Tracks complete metadata** (what, where, when, why, who, how)

The system is **production-ready** and ready for use!

## 🚀 Quick Start Commands

```bash
# Scan repository
curl -X POST http://localhost:8000/repo-genesis/scan \
  -H "Content-Type: application/json" \
  -d '{"integrate_version_tracking": true}'

# View results
curl http://localhost:8000/repo-genesis/layer1

# Track file version
curl -X POST http://localhost:8000/repo-genesis/file/track-version \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "file_path": "backend/app.py",
    "version_note": "My changes"
  }'

# Get file history
curl http://localhost:8000/repo-genesis/file/FILE-abc123.../versions

# Heal a file
curl -X POST http://localhost:8000/repo-genesis/heal/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_genesis_key": "FILE-abc123...",
    "auto_apply": false
  }'
```

---

**🎊 Genesis Key System v2.0 - Complete with File Version Control!**
