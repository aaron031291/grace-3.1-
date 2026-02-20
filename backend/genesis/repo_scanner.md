# Repo Scanner

**File:** `genesis/repo_scanner.py`

## Overview

Repository Genesis Key Scanner.

Scans the entire repository and assigns Genesis Keys to:
- All directories
- All subdirectories
- All files

Stores in immutable memory for complete tracking.
Integrates with file version tracker for automatic version control.

## Classes

- `RepoScanner`

## Key Methods

- `should_skip()`
- `generate_directory_key()`
- `generate_file_key()`
- `get_file_metadata()`
- `scan_repository()`
- `save_immutable_memory()`
- `get_directory_tree()`
- `find_by_genesis_key()`
- `get_statistics()`
- `integrate_with_version_tracking()`
- `scan_and_save_repo()`
- `get_repo_scanner()`

## DB Tables

None

---
*Grace 3.1 Documentation*
