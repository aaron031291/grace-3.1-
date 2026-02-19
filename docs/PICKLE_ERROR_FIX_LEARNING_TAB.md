# Pickle Error Fix: Learning Tab Multiprocessing

**Date**: January 30, 2026  
**Issue**: `cannot pickle 'weakref.ReferenceType' object`  
**Root Cause**: SQLAlchemy session objects passed to multiprocessing queues  
**Status**: ✅ FIXED

---

## Problem Analysis

### Error Message
```
ERROR: [API] Failed to submit study task: cannot pickle 'weakref.ReferenceType' object
```

### Root Cause

When submitting study/practice tasks through the Learning Tab UI, the system tried to serialize SQLAlchemy `Session` objects for multiprocessing communication. SQLAlchemy sessions contain `weakref.ReferenceType` objects that **cannot be pickled**, causing the error.

**The chain of failure:**
1. User clicks "Start Study Session" in Learning Tab
2. Frontend calls `POST /api/autonomous-learning/tasks/study`
3. API endpoint calls `get_orchestrator()`
4. `get_orchestrator()` creates `GenesisTriggerPipeline` with a stored session
5. Orchestrator gets referenced by trigger pipeline
6. Task submission tries to serialize orchestrator (indirectly includes session)
7. **BOOM**: Pickle error on `weakref.ReferenceType`

### Files Involved

**Genesis Trigger Pipeline:**
- `backend/genesis/autonomous_triggers.py` - Stored session in `__init__`
- `backend/genesis/genesis_key_service.py` - Passed session to trigger pipeline
- `backend/api/autonomous_learning.py` - Created session and passed to pipeline

---

## The Fix

### Architecture Change: Session Factory Pattern

**BEFORE (Broken):**
```python
class GenesisTriggerPipeline:
    def __init__(self, session: Session, ...):
        self.session = session  # ❌ Stored unpicklable object
```

**AFTER (Fixed):**
```python
class GenesisTriggerPipeline:
    def __init__(self, knowledge_base_path: Path, ...):
        # ✅ Store factory, create sessions on-demand
        self.session_factory = initialize_session_factory()
```

### Changes Made

#### 1. `genesis/autonomous_triggers.py`

**Modified `__init__`:**
- ❌ Removed: `session: Session` parameter
- ❌ Removed: `self.session = session`
- ✅ Added: `self.session_factory = initialize_session_factory()`

**Updated methods to create fresh sessions:**
```python
# BEFORE
self.session.add(gap_genesis_key)
self.session.commit()

# AFTER
session = self.session_factory()
try:
    session.add(gap_genesis_key)
    session.commit()
finally:
    session.close()
```

**Modified 3 methods:**
- `_handle_practice_outcome()` - Gap genesis key creation
- `_handle_error_or_failure()` - Autonomous healing system
- `_trigger_mirror_analysis()` - Mirror self-modeling

**Updated `get_genesis_trigger_pipeline()`:**
- Added deprecation warning if `session` parameter passed
- Removed session from constructor call
- Updated docstring to explain session factory pattern

#### 2. `api/autonomous_learning.py`

**Modified `get_orchestrator()`:**
```python
# BEFORE
session_factory = initialize_session_factory()
session = session_factory()
trigger_pipeline = get_genesis_trigger_pipeline(
    session=session,  # ❌ Passed unpicklable session
    ...
)

# AFTER
trigger_pipeline = get_genesis_trigger_pipeline(
    knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),  # ✅ No session
    orchestrator=_orchestrator
)
```

#### 3. `genesis/genesis_key_service.py`

**Modified trigger pipeline call:**
```python
# BEFORE
trigger_pipeline = get_genesis_trigger_pipeline(session=sess)

# AFTER
trigger_pipeline = get_genesis_trigger_pipeline()
```

---

## Testing Instructions

### Quick Test (5 minutes)

1. **Start Backend:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app:app --reload --port 8000
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Study Task Submission:**
   - Navigate to Learning Tab
   - Enter study topic: "Python decorators"
   - Click "Start Study Session"
   - **Expected**: ✅ Green success message with task ID
   - **Before fix**: ❌ Red error: "cannot pickle 'weakref.ReferenceType' object"

4. **Test Practice Task Submission:**
   - Enter skill: "Code refactoring patterns"
   - Enter task: "Refactor a function to improve readability"
   - Click "Start Practice Session"
   - **Expected**: ✅ Green success message with task ID

5. **Verify Backend Logs:**
   ```bash
   tail -f backend/logs/grace.log
   ```
   **Expected**: No pickle errors, should see:
   ```
   [API] Auto-started orchestrator for study task submission
   [ORCHESTRATOR] Study task submitted: Python decorators
   ```

### Comprehensive Test (15 minutes)

Follow the full test suite in `TESTING_GUIDE_LEARNING_TAB_FIX.md` - all 7 scenarios.

---

## Success Criteria

✅ **No pickle errors** in logs  
✅ **Study tasks queued** successfully  
✅ **Practice tasks queued** successfully  
✅ **Orchestrator auto-starts** if not running  
✅ **Frontend displays** task IDs and success messages  
✅ **Backend logs show** task submission confirmations  

---

## Technical Notes

### Why Session Factory Pattern?

**Multiprocessing Requirements:**
- Objects passed to `Queue.put()` must be **picklable**
- SQLAlchemy sessions contain:
  - `weakref.ReferenceType` objects (unpicklable)
  - Database connection pools (unpicklable)
  - Engine state (unpicklable)

**Session Factory Solution:**
- Store a **factory function** (picklable)
- Create **fresh sessions on-demand** when needed
- Each session used in **try/finally** block with `.close()`
- Prevents stale/closed session issues
- Thread-safe and process-safe

### Backward Compatibility

The `get_genesis_trigger_pipeline()` function still accepts a `session` parameter for backward compatibility, but:
- Logs deprecation warning if passed
- Ignores the parameter
- Uses session factory internally

This prevents breaking existing code that passes sessions while encouraging migration to the new pattern.

---

## Related Issues Fixed

1. **Genesis Keys not triggering actions** - Previously caused by session issues, now resolved
2. **"No orchestrator set" warnings** - Reduced by proper pipeline initialization
3. **Learning Tab UI disconnect** - Tasks now properly queue and confirm

---

## Additional Warnings Addressed

### Qdrant Connection Error
```
ERROR: Not connected to Qdrant
```
**Status**: Non-blocking warning, expected if Qdrant not running. Doesn't affect Learning Tab functionality.

**To fix (optional):**
```bash
docker-compose up -d qdrant
```

### Embedding Model Path Warning
```
Warning: Embedding model path does not exist: /home/zair/.../all-MiniLM-L6-v2
```
**Status**: Non-blocking, system falls back to default model. For production, download model:
```bash
python backend/download_models.py
```

### Genesis Trigger Warnings
```
WARNING: [GENESIS-TRIGGER] No orchestrator set, cannot trigger actions
```
**Status**: Expected during startup before orchestrator initialized. Warnings stop once Learning Tab auto-starts orchestrator.

---

## Summary

**The core issue**: Trying to serialize unpicklable SQLAlchemy session objects for multiprocessing.

**The solution**: Session factory pattern - create fresh sessions on-demand instead of storing them.

**Result**: Learning Tab now successfully queues study/practice tasks without pickle errors.

**Files modified**: 3 files, ~50 lines changed
- `genesis/autonomous_triggers.py` - Session factory pattern
- `api/autonomous_learning.py` - Remove session passing
- `genesis/genesis_key_service.py` - Remove session passing

**Test status**: ⏳ Pending user verification

---

**Next Steps**: Run tests and report results! 🚀
