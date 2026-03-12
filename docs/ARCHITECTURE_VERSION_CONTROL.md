# Version Control Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│                      (React Frontend)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐   ┌──────────────────┐                    │
│  │  VersionControl  │   │  App.jsx         │                    │
│  │  (Main Manager)  │   │  (Tab Router)    │                    │
│  └────────┬─────────┘   └──────────────────┘                    │
│           │                                                      │
│     ┌─────┴─────┬────────────┬────────────┐                    │
│     │           │            │            │                    │
│  ┌──▼──┐   ┌───▼───┐   ┌───▼───┐   ┌───▼────┐               │
│  │Timeline│  │Tree    │   │Diff    │   │Module  │               │
│  │Viewer  │  │Viewer  │   │Viewer  │   │History │               │
│  └──┬──┘   └───┬───┘   └───┬───┘   └───┬────┘               │
│     │          │           │           │                       │
│  ┌──▼──┐   ┌──▼──┐   ┌────▼────┐  ┌──▼──┐                 │
│  │Revert│   │      │   │         │  │      │                 │
│  │Modal │   │      │   │         │  │      │                 │
│  └──────┘   │      │   │         │  │      │                 │
│             └──────┘   └─────────┘  └──────┘                 │
│                                                                   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                    HTTP REST API (JSON)
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                       FastAPI Backend                            │
│                   (api/version_control.py)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Endpoints (8 routes):                                     │ │
│  │  • GET  /commits                                           │ │
│  │  • GET  /commits/{sha}                                     │ │
│  │  • GET  /commits/{sha}/diff                               │ │
│  │  • GET  /diff                                              │ │
│  │  • GET  /files/{path}/history                             │ │
│  │  • GET  /tree                                              │ │
│  │  • GET  /modules/statistics                               │ │
│  │  • POST /revert                                            │ │
│  └────┬───────────────────────────────────────────────────────┘ │
│       │                                                          │
│  ┌────▼──────────────────────────────────────────────────────┐ │
│  │         Git Service Layer                                  │ │
│  │   (backend/version_control/git_service.py)               │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │  GitService Class                               │   │ │
│  │  │  • get_commits()                                │   │ │
│  │  │  • get_commit_details()                         │   │ │
│  │  │  • get_commit_diff()                            │   │ │
│  │  │  • get_file_history()                           │   │ │
│  │  │  • get_tree_structure()                         │   │ │
│  │  │  • get_module_statistics()                      │   │ │
│  │  │  • revert_to_commit()                           │   │ │
│  │  │  • get_diff_between_commits()                   │   │ │
│  │  └────────────────┬─────────────────────────────────┘   │ │
│  └─────────────────┼───────────────────────────────────────┘ │
│                    │                                          │
└────────────────────┼──────────────────────────────────────────┘
                     │
                  Dulwich
                (Pure Python Git)
                     │
         ┌───────────▼──────────────┐
         │  .git Repository         │
         │  (at project root)       │
         │                          │
         │ • Objects DB            │
         │ • References            │
         │ • Working Directory     │
         │ • Staging Area          │
         └──────────────────────────┘
```

## Data Flow

### 1. View Commits Timeline

```
User clicks "Version Control" tab
         ↓
VersionControl component mounts
         ↓
fetchCommits() triggered
         ↓
GET /api/version-control/commits?limit=50
         ↓
GitService.get_commits()
         ↓
Dulwich Repo.get_walker()
         ↓
JSON response with commit array
         ↓
CommitTimeline component renders
```

### 2. Explore File Tree

```
User selects commit + clicks "Tree" tab
         ↓
fetchTreeStructure(commit_sha) triggered
         ↓
GET /api/version-control/tree?commit_sha={sha}
         ↓
GitService.get_tree_structure()
         ↓
Dulwich retrieves commit tree object
         ↓
_build_tree_dict() recursively builds structure
         ↓
JSON response with tree hierarchy
         ↓
GitTree component renders expandable tree
```

### 3. View Changes

```
User selects commit + clicks "Changes" tab
         ↓
fetchCommitDiff(commit_sha) triggered
         ↓
GET /api/version-control/commits/{sha}/diff
         ↓
GitService.get_commit_diff()
         ↓
Dulwich compares commit tree with parent
         ↓
iter_tree_recursive() gets file changes
         ↓
JSON response with file changes and stats
         ↓
DiffViewer component displays changes
```

### 4. Revert to Commit

```
User selects commit + clicks "Revert to this commit"
         ↓
RevertModal displays with confirmation
         ↓
User confirms revert
         ↓
POST /api/version-control/revert?commit_sha={sha}
         ↓
GitService.revert_to_commit()
         ↓
Dulwich reset_index() to commit tree
         ↓
Working directory updated
         ↓
JSON response { success: true }
         ↓
fetchCommits() refreshes timeline
```

## Component Hierarchy

```
App
├── VersionControl (main manager)
│   ├── CommitTimeline
│   │   └── RevertModal (nested)
│   ├── GitTree
│   ├── DiffViewer
│   └── ModuleHistory
```

## State Management

```
VersionControl (parent) manages:
├── activeView (string) - 'timeline' | 'tree' | 'diff' | 'modules'
├── commits (array) - All commits fetched
├── selectedCommit (object) - Currently selected commit
├── loading (boolean) - Loading state
├── error (string) - Error message
├── treeData (object) - File tree structure
├── moduleStats (object) - Module statistics
├── diffData (object) - Diff information
└── showRevertModal (boolean) - Modal visibility

Each sub-component has its own local state:
├── CommitTimeline
│   └── expandedCommit (string)
├── GitTree
│   └── expandedPaths (Set)
└── ModuleHistory
    ├── selectedModule (string)
    └── expandedModule (string)
```

## API Response Structure

### CommitInfo

```json
{
  "sha": "abc1234567890...",
  "message": "Commit message",
  "author": "John Doe",
  "author_email": "john@example.com",
  "committer": "John Doe",
  "timestamp": "2024-01-15T10:30:00",
  "parent_shas": ["parent_sha"]
}
```

### CommitDiff

```json
{
  "commit_sha": "abc1234567890...",
  "files_changed": [
    {
      "path": "src/file.js",
      "status": "modified",
      "additions": 10,
      "deletions": 2
    }
  ],
  "stats": {
    "additions": 10,
    "deletions": 2,
    "files_modified": 1
  }
}
```

### TreeStructure

```json
{
  "type": "tree",
  "path": "/",
  "children": [
    {
      "type": "tree",
      "name": "src",
      "path": "src",
      "mode": 16877
    },
    {
      "type": "blob",
      "name": "README.md",
      "path": "README.md",
      "mode": 33188
    }
  ]
}
```

### ModuleStatistics

```json
{
  "modules": [
    { "name": "src", "is_dir": true },
    { "name": "backend", "is_dir": true }
  ],
  "total_commits": 42,
  "last_commit_date": "2024-01-15T10:30:00"
}
```

## Technology Stack

```
Frontend:
├── React 18+ (hooks)
├── CSS3 (custom styling)
└── SVG (inline icons)

Backend:
├── FastAPI
├── Pydantic (validation)
├── Dulwich (Git)
└── Python 3.8+

Database:
└── Git Repository (.git/)
```

## Performance Metrics

- **API Response Time:** < 200ms (typical)
- **Page Load:** < 500ms
- **Commits per Page:** 50 (configurable)
- **Max Commits:** 100 per request
- **Tree Depth:** Unlimited (recursive)
- **SVG Render Time:** < 50ms (background patterns)

## Security Considerations

```
✓ Revert requires explicit confirmation
✓ No destructive operations without modal
✓ All inputs validated by Pydantic
✓ SQL injection: Not applicable (Git objects, not SQL)
✓ XSS protection: React auto-escapes JSX
✓ CSRF: FastAPI CORS configured
✓ Rate limiting: Can be added to endpoints
```

## Error Handling Flow

```
API Error (500)
      ↓
FastAPI catches exception
      ↓
HTTPException with detail message
      ↓
Frontend catches fetch error
      ↓
Error state updated
      ↓
Red error banner displayed to user
```

## Caching Strategy

Currently: No caching (fresh data on each request)

Future improvements:

- Client-side cache for commits (with invalidation)
- Tree structure caching
- Module stats caching
- ETag support for conditional requests

## Scalability

For large repositories (1000+ commits):

- Implement pagination cursor (current: offset/limit)
- Add branch filtering
- Consider commit graph caching
- Implement search indices
- Add request rate limiting

---

**Version Control System - Complete Architecture Overview**
