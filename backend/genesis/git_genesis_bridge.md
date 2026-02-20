# Git Genesis Bridge

**File:** `genesis/git_genesis_bridge.py`

## Overview

Git ↔ Genesis Keys Bridge.

Connects Git version control with Genesis Key version control,
making them work together as one unified system.

When Git commits happen, Genesis Keys are automatically created.
When Genesis Keys track file changes, optional Git commits can be triggered.

## Classes

- `GitGenesisBridge`

## Key Methods

- `get_last_commit_info()`
- `get_files_changed_in_last_commit()`
- `sync_git_commit_to_genesis_keys()`
- `create_post_commit_hook()`
- `auto_commit_genesis_tracked_files()`
- `get_bridge_statistics()`
- `get_git_genesis_bridge()`

## DB Tables

None

---
*Grace 3.1 Documentation*
