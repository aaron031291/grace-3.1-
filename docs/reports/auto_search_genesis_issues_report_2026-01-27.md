# Auto-Search and Genesis Key Issues Report
**Date**: January 27, 2026, 1:06 PM  
**Reporter**: Zair  
**System**: Grace AI - Auto-Search & Version Control

---

## Executive Summary

Three interconnected issues were identified during auto-search testing for "how to make cheese cake":

1. **File Path Warning**: File vanished warning due to incorrect path reference
2. **Ingestion Status**: Unclear if auto-search results are being ingested to Qdrant
3. **Genesis Key Error**: `DetachedInstanceError` in symbiotic version control tracking

---

## Issue 1: File Path Discrepancy

### Problem

```
WARNING: File vanished before tracking: /home/zair/Documents/grace/test/grace-3.1-/backend/auto_search/20260127_130035/The_Best_Cheesecake_Recipe.txt
```

### Root Cause

**Path Mismatch**: The warning references `/backend/auto_search/` but the file was actually saved to `/backend/knowledge_base/auto_search/`

**Actual File Location**:
```
/home/zair/Documents/grace/test/grace-3.1-/backend/knowledge_base/auto_search/20260127_130035/The_Best_Cheesecake_Recipe.txt
```

### Analysis

Looking at [auto_search.py](file:///home/zair/Documents/grace/test/grace-3.1-/backend/search/auto_search.py) lines 98-103:

```python
# Determine save directory based on folder_path
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
if folder_path:
    base_save_dir = f"{folder_path}/auto_search/{timestamp}"
else:
    base_save_dir = f"auto_search/{timestamp}"
```

The code uses a **relative path** `auto_search/{timestamp}` when no `folder_path` is provided. However, the scraping service is likely resolving this relative to the `knowledge_base` directory, resulting in:
- **Expected by file watcher**: `/backend/auto_search/...`
- **Actual location**: `/backend/knowledge_base/auto_search/...`

### Impact

- ⚠️ **Medium**: File is saved successfully but not tracked by Genesis Key version control
- The file exists and is accessible but won't have version history
- Auto-ingestion may still work if it scans the correct directory

### Recommended Fix

Update `auto_search.py` to use absolute paths or ensure consistency:

```python
# Option 1: Use absolute path
from pathlib import Path
backend_dir = Path(__file__).parent.parent
base_save_dir = backend_dir / "knowledge_base" / "auto_search" / timestamp

# Option 2: Always specify folder_path when calling
folder_path = "knowledge_base"  # Pass this when calling search_and_scrape
```

---

## Issue 2: Qdrant Ingestion Status

### Question

Is the auto-search result file being ingested into Qdrant for RAG retrieval?

### Current Status

**Unknown** - Requires verification through:

1. **Check Qdrant Collection**:
   ```bash
   curl http://localhost:6333/collections/grace_knowledge/points/scroll?limit=10
   ```

2. **Check Auto-Ingestion Logs**:
   - Look for `[AUTO-INGEST]` entries mentioning the file
   - Check if file appears in excluded files list

3. **Test Retrieval**:
   ```bash
   curl -X POST http://localhost:8000/retrieve \
     -H "Content-Type: application/json" \
     -d '{"query": "how to make cheesecake", "top_k": 5}'
   ```

### Expected Behavior

If auto-ingestion is working correctly:
1. File watcher detects new file in `knowledge_base/auto_search/`
2. Auto-ingestion service picks up the file
3. File is chunked and embedded
4. Vectors are stored in Qdrant
5. File becomes searchable via RAG

### Potential Issues

- ❌ File path mismatch may prevent file watcher from detecting it
- ❌ `auto_search` directory might be in exclusion list
- ❌ File may be detected but Genesis Key error prevents tracking
- ✅ File might still be ingested if auto-ingestion scans the directory directly

---

## Issue 3: Genesis Key DetachedInstanceError

### Error Details

```python
ERROR: Error in symbiotic tracking: Instance '<GenesisKey at 0x7592b22222a0>' has been deleted, or its row is otherwise not present.

sqlalchemy.orm.exc.ObjectDeletedError: Instance '<GenesisKey at 0x7592b22222a0>' has been deleted, or its row is otherwise not present.
```

**Location**: [symbiotic_version_control.py](file:///home/zair/Documents/grace/test/grace-3.1-/backend/genesis/symbiotic_version_control.py):123  
**Triggered by**: [file_watcher.py](file:///home/zair/Documents/grace/test/grace-3.1-/backend/genesis/file_watcher.py):112

### Root Cause Analysis

This is a **SQLAlchemy session management issue**. The error occurs when trying to access an attribute (`key_id`) of a database object that has been:
1. Deleted from the database
2. Expired from the session
3. Detached from the session

### Code Flow

1. **File Watcher** detects file change
2. Calls `symbiotic.track_file_change()` at line 112
3. **Symbiotic VC** creates `operation_genesis_key` at line 99-119
4. Tries to access `operation_genesis_key.key_id` at line 123
5. **Error**: Object is detached from session

### Why This Happens

Looking at the code in `symbiotic_version_control.py`:

```python
# Line 99-119: Create Genesis Key
operation_genesis_key = self.genesis_service.create_key(
    key_type=GenesisKeyType.FILE_OPERATION,
    # ... parameters ...
    session=session
)

# Line 123: Access attribute - FAILS HERE
operation_key_id = operation_genesis_key.key_id  # DetachedInstanceError!
```

**Possible causes**:
1. **Session closed prematurely**: The session passed to `create_key()` might be closed before line 123
2. **Object not committed**: The object might not be flushed/committed to the database
3. **Session scope issue**: The object was created in a different session scope
4. **Lazy loading**: The `key_id` attribute might be lazy-loaded and session is gone

### Impact

- 🔴 **High**: Prevents automatic version tracking of file changes
- Files are not being tracked in Genesis Key system
- Version history is not being created
- This affects ALL file changes detected by the file watcher

### Recommended Fix

**Option 1: Immediate attribute access** (Already attempted in code)
```python
# Line 121-123 - This is already in the code but still failing
# Store key_id immediately while object is still bound to session
operation_key_id = operation_genesis_key.key_id
```

**Option 2: Explicit session refresh**
```python
session.flush()  # Ensure object is persisted
session.refresh(operation_genesis_key)  # Reload from database
operation_key_id = operation_genesis_key.key_id
```

**Option 3: Return key_id from create_key()**
Modify `genesis_key_service.create_key()` to return the key_id directly:
```python
# In genesis_key_service.py
def create_key(...) -> str:  # Return key_id instead of object
    key = GenesisKey(...)
    session.add(key)
    session.flush()
    return key.key_id  # Return ID immediately
```

**Option 4: Session management fix**
```python
# Ensure session is properly managed
try:
    operation_genesis_key = self.genesis_service.create_key(...)
    session.flush()  # Persist to database
    operation_key_id = operation_genesis_key.key_id  # Access while in session
    # ... rest of code ...
    session.commit()  # Commit at the end
except Exception as e:
    session.rollback()
    raise
```

---

## Related Warnings

### Genesis Orchestrator Warning

```
WARNING: [GENESIS-TRIGGER] No orchestrator set, cannot trigger actions
```

**Status**: ⚠️ **Low Priority**  
**Explanation**: This is expected when the Genesis orchestrator is not configured. It doesn't affect core functionality, only autonomous action triggering.

---

## Testing Recommendations

### 1. Verify File Ingestion

```bash
# Check if file is in Qdrant
curl http://localhost:6333/collections/grace_knowledge/points/scroll | jq '.result.points[] | select(.payload.source | contains("cheesecake"))'

# Test retrieval
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "cheesecake recipe", "top_k": 3}' | jq
```

### 2. Test Genesis Key Tracking

```bash
# Check Genesis Keys for the file
curl http://localhost:8000/genesis/search?file_path=auto_search | jq

# Check version history
curl http://localhost:8000/api/version-control/stats | jq
```

### 3. Monitor File Watcher

```bash
# Watch logs for file watcher activity
tail -f backend/logs/grace.log | grep -E "(FILE_WATCHER|SYMBIOTIC|GENESIS)"
```

---

## Priority Recommendations

### Immediate (P0)
1. **Fix Genesis Key DetachedInstanceError** - Blocking version control
   - Implement session management fix
   - Test with a sample file change

### High (P1)
2. **Fix Auto-Search Path Consistency** - Preventing file tracking
   - Update `auto_search.py` to use correct base path
   - Ensure file watcher can find the files

### Medium (P2)
3. **Verify Qdrant Ingestion** - Ensure RAG functionality
   - Test if auto-search results are searchable
   - Check auto-ingestion logs

### Low (P3)
4. **Genesis Orchestrator Configuration** - Optional feature
   - Configure orchestrator if autonomous actions are needed
   - Document how to enable/disable

---

## Summary

The auto-search feature successfully:
- ✅ Searches the web via SerpAPI
- ✅ Scrapes content from websites
- ✅ Saves content to text files

But has issues with:
- ❌ File path consistency (wrong directory reference)
- ❓ Qdrant ingestion status (needs verification)
- ❌ Genesis Key version tracking (DetachedInstanceError)

**Next Steps**: Fix the Genesis Key session management issue first, as it's blocking all automatic version tracking functionality.

---

## Additional Notes

- The cheesecake recipe file (14.6 KB) was successfully saved
- File location: `/backend/knowledge_base/auto_search/20260127_130035/The_Best_Cheesecake_Recipe.txt`
- Auto-search triggered correctly from chat interface
- Web scraping completed successfully (1 source)

---

**Report Generated**: January 27, 2026, 1:06 PM  
**System Version**: Grace 3.1  
**Components Analyzed**: Auto-Search, Genesis Keys, File Watcher, Symbiotic Version Control
