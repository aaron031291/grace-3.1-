# 🗂️ Directory Hierarchy with Genesis Keys

## 🎯 Overview

The Directory Hierarchy Genesis Key system creates a **unique identifier for every directory and subdirectory**, establishing a clear versioning and identification scheme at each level of the directory hierarchy.

### Hierarchy Structure

```
Root Directory: DIR-abc123 (Genesis Key)
├── Subdirectory 1: DIR-def456 (Genesis Key)
│   ├── file1.txt (version controlled under DIR-def456)
│   ├── file2.txt (version controlled under DIR-def456)
│   └── Subdirectory 1.1: DIR-ghi789 (Genesis Key)
│       └── file3.txt (version controlled under DIR-ghi789)
├── Subdirectory 2: DIR-jkl012 (Genesis Key)
│   ├── file4.txt (version controlled under DIR-jkl012)
│   └── file5.txt (version controlled under DIR-jkl012)
└── file6.txt (version controlled under DIR-abc123)
```

## 🔑 Key Concepts

### 1. Directory Genesis Keys (DIR-prefix)

Every directory gets a unique identifier:
- **Format**: `DIR-{12-char-hex}` (e.g., `DIR-a1b2c3d4e5f6`)
- **Persistent**: Never changes once assigned
- **Hierarchical**: Links to parent directory's Genesis Key
- **Tracked**: Full metadata (what, where, when, why, who, how)

### 2. File Version Control

Files are version-controlled **within their directory**:
- Each file change creates a new version Genesis Key
- Versions link to their directory's Genesis Key
- Complete history maintained per directory
- Version numbers increment per directory

### 3. Complete Hierarchy

```
knowledge_base/                    → DIR-root123
├── .genesis_directory_keys.json   (Metadata file)
├── layer_1/                       → DIR-layer456
│   ├── .genesis_key_info.md       (Genesis Key info)
│   ├── genesis_key/               → DIR-genkey789
│   │   ├── .genesis_key_info.md
│   │   ├── GU-user123/            → DIR-user001
│   │   │   ├── .genesis_key_info.md
│   │   │   ├── profile.json       (v1, v2, v3...)
│   │   │   └── session_SS-abc.json (v1, v2, v3...)
│   │   └── GU-user456/            → DIR-user002
│   │       └── ...
│   └── documents/                 → DIR-docs555
│       └── ...
└── layer_2/                       → DIR-layer222
    └── ...
```

## 📦 Implementation

### Backend Files

1. **[backend/genesis/directory_hierarchy.py](backend/genesis/directory_hierarchy.py)**
   - Core directory hierarchy management
   - Genesis Key generation for directories
   - Subdirectory scanning and key assignment
   - File version control
   - Tree structure building

2. **[backend/api/directory_hierarchy.py](backend/api/directory_hierarchy.py)**
   - API endpoints for hierarchy management
   - Create directories with Genesis Keys
   - Query directory trees
   - Add file versions
   - Statistics and reporting

### Metadata Storage

**`.genesis_directory_keys.json`** (in knowledge_base root)
```json
{
  "version": "1.0",
  "created_at": "2026-01-11T10:00:00Z",
  "root_genesis_key": "DIR-abc123456789",
  "directories": {
    "": {
      "genesis_key": "DIR-abc123456789",
      "path": "",
      "name": "root",
      "parent_genesis_key": null,
      "created_at": "2026-01-11T10:00:00Z",
      "is_root": true,
      "subdirectories": ["DIR-def456...", "DIR-jkl012..."],
      "files": [],
      "version_count": 0
    },
    "layer_1": {
      "genesis_key": "DIR-def456789012",
      "path": "layer_1",
      "name": "layer_1",
      "parent_genesis_key": "DIR-abc123456789",
      "created_at": "2026-01-11T10:01:00Z",
      "is_root": false,
      "subdirectories": ["DIR-genkey789..."],
      "files": [],
      "version_count": 0
    },
    "layer_1/genesis_key": {
      "genesis_key": "DIR-genkey789012",
      "path": "layer_1/genesis_key",
      "name": "genesis_key",
      "parent_genesis_key": "DIR-def456789012",
      "created_at": "2026-01-11T10:02:00Z",
      "is_root": false,
      "subdirectories": ["DIR-user001...", "DIR-user002..."],
      "files": [],
      "version_count": 0
    }
  }
}
```

### Directory README

Each directory gets a `.genesis_key_info.md` file:

```markdown
# Directory Genesis Key

**Genesis Key:** `DIR-abc123456789`
**Directory:** `layer_1`
**Created:** 2026-01-11T10:01:00Z

## Hierarchy

- **Parent Genesis Key:** DIR-root123456789
- **Is Root:** false

## Purpose

This directory is uniquely identified by its Genesis Key. All files within this directory
are version-controlled under this Genesis Key hierarchy.

## Structure

- Each subdirectory has its own Genesis Key
- Files are version-controlled within their directory
- Complete hierarchy tracking from root to leaf

## Version Control

All changes to files in this directory are tracked with:
- What: File operation (create, update, delete)
- Where: File path within this directory
- When: Timestamp
- Why: Reason for change
- Who: User making change
- How: Method used

Genesis Key: DIR-abc123456789
```

## 🚀 Usage

### Initialize Hierarchy

```bash
# Initialize entire knowledge_base hierarchy
POST /directory-hierarchy/initialize
{
  "user_id": "GU-user123..."
}

Response:
{
  "message": "Knowledge base hierarchy initialized",
  "root_genesis_key": "DIR-abc123456789",
  "total_directories": 15,
  "total_files": 42,
  "tree": { ... }
}
```

### Create Directory

```bash
# Create new directory with Genesis Key
POST /directory-hierarchy/directories
{
  "directory_path": "layer_1/my_folder",
  "parent_genesis_key": "DIR-layer456...",
  "user_id": "GU-user123...",
  "description": "My custom folder"
}

Response:
{
  "genesis_key": "DIR-newfolder123",
  "path": "layer_1/my_folder",
  "name": "my_folder",
  "parent_genesis_key": "DIR-layer456...",
  "created_at": "2026-01-11T10:05:00Z",
  "is_root": false,
  "subdirectories": [],
  "files": [],
  "version_count": 0
}
```

### Get Directory Info

```bash
# Get Genesis Key for directory
GET /directory-hierarchy/directories/layer_1/genesis_key/genesis-key

Response:
{
  "directory_path": "layer_1/genesis_key",
  "genesis_key": "DIR-genkey789012"
}

# Get full directory info
GET /directory-hierarchy/directories/layer_1/genesis_key

Response:
{
  "genesis_key": "DIR-genkey789012",
  "path": "layer_1/genesis_key",
  "name": "genesis_key",
  "parent_genesis_key": "DIR-layer456...",
  "created_at": "2026-01-11T10:02:00Z",
  "is_root": false,
  "subdirectories": ["DIR-user001...", "DIR-user002..."],
  "files": [
    {"name": "README.md", "path": "layer_1/genesis_key/README.md", "added_at": "..."}
  ],
  "version_count": 5
}
```

### Get Directory Tree

```bash
# Get complete tree with all Genesis Keys
GET /directory-hierarchy/trees/layer_1/genesis_key

Response:
{
  "genesis_key": "DIR-genkey789012",
  "name": "genesis_key",
  "path": "layer_1/genesis_key",
  "is_root": false,
  "created_at": "2026-01-11T10:02:00Z",
  "parent_genesis_key": "DIR-layer456...",
  "subdirectories": [
    {
      "genesis_key": "DIR-user001234",
      "name": "GU-user123...",
      "path": "layer_1/genesis_key/GU-user123...",
      "subdirectories": [],
      "files": [
        {"name": "profile.json", "path": "...", "added_at": "..."},
        {"name": "session_SS-abc.json", "path": "...", "added_at": "..."}
      ],
      "file_count": 2,
      "subdirectory_count": 0
    }
  ],
  "files": [
    {"name": "README.md", "path": "...", "added_at": "..."}
  ],
  "file_count": 1,
  "subdirectory_count": 1
}
```

### Add File Version

```bash
# Version control a file within directory
POST /directory-hierarchy/files/versions
{
  "directory_path": "layer_1/genesis_key/GU-user123...",
  "file_name": "profile.json",
  "user_id": "GU-user123...",
  "version_note": "Updated user preferences",
  "file_content": "{\"username\": \"john_doe\", ...}"
}

Response:
{
  "version_key": "GK-version123...",
  "version_number": 3,
  "directory_genesis_key": "DIR-user001234",
  "file_path": "layer_1/genesis_key/GU-user123.../profile.json",
  "timestamp": "2026-01-11T10:10:00Z"
}
```

### List All Directories

```bash
# Get all directories with Genesis Keys
GET /directory-hierarchy/directories

Response:
{
  "": {
    "genesis_key": "DIR-root123...",
    "path": "",
    "name": "root",
    ...
  },
  "layer_1": {
    "genesis_key": "DIR-layer456...",
    "path": "layer_1",
    "name": "layer_1",
    ...
  },
  ...
}
```

### Get Statistics

```bash
# Get hierarchy statistics
GET /directory-hierarchy/stats

Response:
{
  "total_directories": 15,
  "total_files": 42,
  "total_versions": 156,
  "root_genesis_key": "DIR-root123...",
  "created_at": "2026-01-11T10:00:00Z"
}
```

## 💻 Python Usage

### Create Hierarchy

```python
from backend.genesis.directory_hierarchy import get_directory_hierarchy

# Get hierarchy manager
hierarchy = get_directory_hierarchy()

# Create root hierarchy
tree = hierarchy.create_hierarchy(
    root_path="",
    user_id="GU-user123...",
    scan_existing=True
)

print(f"Root Genesis Key: {tree['genesis_key']}")
print(f"Subdirectories: {len(tree['subdirectories'])}")
```

### Create Directory

```python
# Create new directory
dir_info = hierarchy.create_directory_genesis_key(
    directory_path="layer_1/my_folder",
    parent_genesis_key="DIR-layer456...",
    user_id="GU-user123...",
    description="Custom folder for documents"
)

print(f"Directory Genesis Key: {dir_info['genesis_key']}")
```

### Get Genesis Key

```python
# Get Genesis Key for directory
genesis_key = hierarchy.get_directory_genesis_key("layer_1/genesis_key")
print(f"Genesis Key: {genesis_key}")  # DIR-genkey789012
```

### Version Control File

```python
# Add file version
version_info = hierarchy.add_file_version(
    directory_path="layer_1/genesis_key/GU-user123...",
    file_name="profile.json",
    user_id="GU-user123...",
    version_note="Updated preferences",
    file_content=json.dumps(profile_data)
)

print(f"Version {version_info['version_number']} created")
print(f"Linked to directory: {version_info['directory_genesis_key']}")
```

## 🎨 Frontend Integration

### Display Directory Tree

```javascript
// Fetch directory tree
const response = await fetch(
  "http://localhost:8000/directory-hierarchy/trees/layer_1",
  { credentials: "include" }
);

const tree = await response.json();

// Render tree
function renderTree(node, level = 0) {
  const indent = "  ".repeat(level);
  console.log(`${indent}📁 ${node.name} [${node.genesis_key}]`);

  node.files.forEach(file => {
    console.log(`${indent}  📄 ${file.name}`);
  });

  node.subdirectories.forEach(subdir => {
    renderTree(subdir, level + 1);
  });
}

renderTree(tree);
```

### Create Directory

```javascript
// Create new directory
const response = await fetch(
  "http://localhost:8000/directory-hierarchy/directories",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      directory_path: "layer_1/my_documents",
      user_id: genesisId,
      description: "My documents folder"
    })
  }
);

const dirInfo = await response.json();
console.log(`Created directory with Genesis Key: ${dirInfo.genesis_key}`);
```

## 📊 Benefits

### Clear Hierarchy
- Every directory uniquely identified
- Parent-child relationships tracked
- Easy navigation and querying

### Version Control
- Files versioned within their directory
- Complete history per directory
- Rollback to any version

### Traceability
- Know which directory a file belongs to
- Track all changes at directory level
- Complete audit trail

### Scalability
- Unlimited directory depth
- Handles large file counts
- Efficient metadata storage

## 🔍 Example Queries

### Find All Subdirectories

```python
def get_all_subdirectories(genesis_key):
    """Get all subdirectories under a directory."""
    hierarchy = get_directory_hierarchy()

    # Find directory by Genesis Key
    for path, info in hierarchy.get_all_directory_keys().items():
        if info["genesis_key"] == genesis_key:
            return info["subdirectories"]

    return []
```

### Find Directory Path by Genesis Key

```python
def find_directory_path(genesis_key):
    """Find directory path by Genesis Key."""
    hierarchy = get_directory_hierarchy()

    for path, info in hierarchy.get_all_directory_keys().items():
        if info["genesis_key"] == genesis_key:
            return path

    return None
```

### Get File History

```python
def get_file_versions(directory_path, file_name):
    """Get all versions of a file."""
    from backend.genesis.genesis_key_service import get_genesis_service

    genesis = get_genesis_service()
    hierarchy = get_directory_hierarchy()

    # Get directory Genesis Key
    dir_key = hierarchy.get_directory_genesis_key(directory_path)

    # Get all Genesis Keys with this parent
    # (All file versions are children of directory Genesis Key)
    file_path = f"{directory_path}/{file_name}"

    # Query database for versions
    # ... implementation depends on your needs
```

## 🎉 Summary

The Directory Hierarchy Genesis Key system provides:

✅ **Unique identifier for every directory** (DIR-prefix)
✅ **Unique identifier for every subdirectory** (DIR-prefix)
✅ **File version control within directories**
✅ **Complete hierarchy tracking**
✅ **Parent-child relationships**
✅ **Metadata storage** (.genesis_directory_keys.json)
✅ **Per-directory README** (.genesis_key_info.md)
✅ **API endpoints for management**
✅ **Full audit trail**
✅ **Scalable architecture**

Every level of your directory hierarchy is now uniquely identified and version-controlled!
