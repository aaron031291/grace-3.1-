# Codebase Api

**File:** `api/codebase_api.py`

## Overview

Codebase Browser API.

Provides endpoints for browsing, searching, and analyzing code repositories.
Supports file browsing, code search, commit history, and code analysis.

## Classes

- `RepositoryInfo`
- `RepositoriesResponse`
- `FileInfo`
- `FilesResponse`
- `FileContentResponse`
- `SearchResult`
- `SearchResponse`
- `CommitInfo`
- `CommitsResponse`
- `LanguageStats`
- `ComplexityInfo`
- `CodeIssue`
- `AnalysisResponse`

## Key Methods

- `get_file_size_str()`
- `detect_language()`
- `get_repo_root()`
- `validate_path_traversal()`

---
*Grace 3.1*
