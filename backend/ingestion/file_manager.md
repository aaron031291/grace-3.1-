# File Manager

**File:** `ingestion/file_manager.py`

## Overview

Git-based ingestion file manager for tracking knowledge base files.
Monitors backend/knowledge_base for changes and triggers appropriate ingestion actions.

## Classes

- `FileChange`
- `IngestionResult`
- `GitFileTracker`
- `IngestionFileManager`

## Key Methods

- `initialize_git()`
- `get_file_hash()`
- `get_staged_changes()`
- `get_untracked_files()`
- `add_file()`
- `remove_file()`
- `commit_changes()`
- `process_new_file()`
- `process_modified_file()`
- `process_deleted_file()`
- `scan_directory()`
- `watch_and_process()`

---
*Grace 3.1*
