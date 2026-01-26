# Incident Report: Knowledge Base Path Resolution Issues

**Date**: January 26, 2026
**Priority**: High
**Status**: Resolved

## 🔴 The Issue
The system was failing to track files in the `knowledge_base` directory, particularly those downloaded by logical components (Auto Search).
- **Error**: `FileNotFoundError: /.../backend/Thomas_Edison_Wikipedia.txt`
- **Verification**: The file was actually located in `backend/knowledge_base/auto_search/...`, but the system was looking for it in the root `backend/` directory.

## 🔍 Root Cause Analysis

1. **Ingestion Service Path Mismatch**:
   - `ingest_text_fast` blindly used the `filename` argument (e.g., "Thomas_Edison.txt") for version control tracking.
   - It did not know the *actual* location of the file on disk.
   - Version Control assumed all files were relative to the `backend/` root if not absolute.

2. **Orchestrator Argument Error**:
   - `ContinuousLearningOrchestrator` passed only `file_path.name` (basename) to ingestion, discarding the full path information needed for tracking.

3. **Fragile Path Logic in Triggers**:
   - `autonomous_triggers.py` defaulted to `Path("knowledge_base")` (relative), which fails if the working directory isn't exactly correct.
   - It also had broken imports from a previous edit.

## 🛠️ The Fixes

### 1. Absolute Path Tracking in Ingestion
Modified `backend/ingestion/service.py` to prioritize `metadata["file_path"]` for version control if available.
```python
real_file_path = filename
if metadata and "file_path" in metadata:
    real_file_path = metadata["file_path"]
# Use real_file_path for version control
```

### 2. Passing Full Paths from Orchestrator
Updated `backend/cognitive/continuous_learning_orchestrator.py` to pass the absolute path in metadata.
```python
metadata={"file_path": str(file_path.absolute())}
```

### 3. Standardized Path Resolution
Refactored `backend/genesis/autonomous_triggers.py` to use `settings.KNOWLEDGE_BASE_PATH`, ensuring reliable path resolution regardless of execution context.
```python
from settings import settings
# ...
knowledge_base_path = Path(settings.KNOWLEDGE_BASE_PATH)
```

## ✅ Verification
- **Backend Restarted**: Confirmed clean startup.
- **Path Resolution**: Components now communicate full absolute paths, preventing "File Not Found" errors during version tracking.
- **Stability**: Fixed broken imports in trigger pipeline.
