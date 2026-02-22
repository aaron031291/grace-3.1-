# File Version Tracker

**File:** `genesis/file_version_tracker.py`

## Overview

File Version Control through Genesis Keys.

Tracks file changes and versions using Genesis Keys:
- Every file gets a FILE-prefix Genesis Key
- Every change to a file creates a new version Genesis Key
- Versions are linked to the original file Genesis Key
- Complete history of all file changes

## Classes

- `FileVersionTracker`

## Key Methods

- `track_file_version()`
- `get_file_versions()`
- `get_version_details()`
- `get_latest_version()`
- `get_version_diff()`
- `list_all_tracked_files()`
- `get_file_statistics()`
- `auto_track_directory()`
- `get_file_version_tracker()`

## DB Tables

None

---
*Grace 3.1 Documentation*
