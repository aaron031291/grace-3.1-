# File Watcher

**File:** `genesis/file_watcher.py`

## Overview

File System Watcher for Automatic Version Control.

Watches file changes in the workspace and automatically creates
Genesis Keys + Version entries for all modifications.

This makes GRACE truly autonomous - file changes are tracked
in real-time without manual intervention.

## Classes

- `GenesisFileWatcher`
- `FileWatcherService`

## Key Methods

- `on_modified()`
- `on_created()`
- `on_deleted()`
- `get_statistics()`
- `start_watching()`
- `stop_watching()`
- `stop_all()`
- `get_statistics()`
- `get_file_watcher_service()`
- `start_watching_workspace()`

## DB Tables

None

---
*Grace 3.1 Documentation*
