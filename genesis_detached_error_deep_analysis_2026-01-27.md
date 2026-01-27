# Genesis Key DetachedInstanceError - Deep Analysis Report
**Date**: January 27, 2026, 1:17 PM  
**Status**: **CRITICAL - Fix Incomplete**

---

## Executive Summary

The `sess.flush()` fix applied earlier **partially worked** but did not fully resolve the `DetachedInstanceError`. The error is now appearing in **multiple locations** and the root cause is more complex than initially diagnosed.

**Current Status**: ❌ **Still Broken** - Automatic file tracking is completely non-functional

---

## Error Analysis

### Primary Error Pattern

```python
sqlalchemy.orm.exc.ObjectDeletedError: Instance '<GenesisKey at 0x7ae272010950>' has been deleted, or its row is otherwise not present.
```

### Error Locations

1. **symbiotic_version_control.py:123** - Accessing `operation_genesis_key.key_id`
2. **file_version_tracker.py:187** - Accessing `version_key.key_id`  
3. **kb_integration.py** - Saving Genesis Key to KB
4. **memory_mesh_integration.py** - Feeding to Memory Mesh

### Cascading Failures

The error triggers a cascade of failures:
```
ERROR: Error in symbiotic tracking
  ↓
ERROR: Failed to create file version
  ↓
ERROR: Failed to save Genesis Key to KB
  ↓
WARNING: Failed to feed Genesis Key to Memory Mesh
```

---

## Root Cause: Session Rollback After Flush

### The Problem

The `sess.flush()` fix **does work** initially, but the session is being **rolled back** later in the transaction, causing all flushed objects to be deleted from the session.

### Evidence

Looking at `genesis_key_service.py` lines 285-292:

```python
except Exception as e:
    logger.error(f"Failed to create Genesis Key: {e}")
    if close_session:
        sess.rollback()  # ← This rolls back the flush!
    raise
finally:
    if close_session:
        sess.close()
```

### The Flow

1. `create_key()` is called with a **passed-in session** (not created locally)
2. Object is added and **flushed** successfully
3. `key_id` is accessible at this point
4. **Exception occurs** in one of the post-creation hooks:
   - KB integration (`save_genesis_key`)
   - Memory Mesh integration (`ingest_learning_experience`)
   - Autonomous triggers (`on_genesis_key_created`)
5. Exception handler calls `sess.rollback()` **even though session was passed in**
6. Rollback deletes the flushed object from the session
7. Caller tries to access `key.key_id` → **DetachedInstanceError**

---

## Secondary Issues

### 1. KB Integration Failure

```python
ERROR: Failed to save Genesis Key to KB: Instance '<GenesisKey at 0x7ae272053b90>' has been deleted
```

**Location**: `genesis_key_service.py:239-243`

The KB integration is trying to access the Genesis Key after it's been detached.

### 2. Memory Mesh Integration Failure

```python
WARNING: Failed to feed Genesis Key to Memory Mesh: Instance '<LearningExample at 0x7ae270f09370>' has been deleted
```

**Location**: `genesis_key_service.py:246-270`

Same issue - trying to access objects after session rollback.

### 3. File Version Tracker

The same pattern exists in `file_version_tracker.py:187`:

```python
# Store key_id immediately to prevent DetachedInstanceError
version_key_db_id = version_key.key_id  # ← Still fails if session rolled back
```

---

## Why The Fix Didn't Work

### What We Fixed

```python
# genesis_key_service.py:231
sess.flush()  # ← This works!
```

### What We Missed

```python
# genesis_key_service.py:287-288
if close_session:
    sess.rollback()  # ← This undoes the flush!
```

**The Problem**: The rollback condition checks `close_session`, but it should **never rollback a session that was passed in** by the caller, regardless of who created it.

---

## The Correct Fix

### Issue 1: Don't Rollback Passed-In Sessions

```python
# genesis_key_service.py (Lines 285-292)
except Exception as e:
    logger.error(f"Failed to create Genesis Key: {e}")
    # CRITICAL: Only rollback if WE created the session
    # Never rollback a session passed in by the caller
    if close_session:
        sess.rollback()
    # If session was passed in, let the CALLER handle rollback
    raise
```

**Problem**: This logic is correct, but the issue is that `close_session` is `False` when a session is passed in, so the rollback **shouldn't** happen. But it's still happening somewhere.

### Issue 2: Post-Creation Hooks Failing

The real problem is that **exceptions in post-creation hooks** are causing the entire transaction to fail:

```python
# Lines 239-243: KB Integration
try:
    kb_integration = get_kb_integration()
    kb_integration.save_genesis_key(key)  # ← This is failing!
except Exception as kb_error:
    logger.warning(f"Failed to save Genesis Key to KB: {kb_error}")
    # Should NOT raise, just log warning
```

**Current Behavior**: These exceptions are being caught and logged, but they're still somehow causing session issues.

---

## Solution Strategy

### Option 1: Extract key_id Before Any Operations (Recommended)

```python
# genesis_key_service.py
sess.add(key)
sess.flush()

# CRITICAL: Extract all needed data IMMEDIATELY after flush
key_id = key.key_id
key_dict = {
    "key_id": key.key_id,
    "what_description": key.what_description,
    "who_actor": key.who_actor,
    # ... all other fields
}

# Only commit if we created our own session
if close_session:
    sess.commit()

# Update user statistics (using extracted data)
if user_id:
    self._update_user_stats(user_id, key_type, is_error, sess)

# Post-creation hooks (using extracted data, not the object)
try:
    kb_integration = get_kb_integration()
    kb_integration.save_genesis_key_dict(key_dict)  # Use dict, not object
except Exception as kb_error:
    logger.warning(f"Failed to save Genesis Key to KB: {kb_error}")

return key  # Object might be detached, but we already extracted data
```

### Option 2: Separate Transaction for Post-Creation Hooks

```python
# Commit the Genesis Key first
sess.add(key)
sess.flush()
if close_session:
    sess.commit()

# THEN do post-creation hooks in a separate transaction
try:
    with new_session() as hook_session:
        # Reload the key in new session
        reloaded_key = hook_session.query(GenesisKey).filter_by(key_id=key.key_id).first()
        kb_integration.save_genesis_key(reloaded_key)
        memory_mesh.ingest(reloaded_key)
except Exception as e:
    logger.warning(f"Post-creation hooks failed: {e}")
    # Don't propagate - key is already saved
```

### Option 3: Make Post-Creation Hooks Async

```python
# Save key synchronously
sess.add(key)
sess.flush()
if close_session:
    sess.commit()

# Queue post-creation hooks for async processing
async_queue.enqueue(
    task="process_genesis_key_hooks",
    key_id=key.key_id
)

return key
```

---

## Recommended Immediate Fix

### Step 1: Fix `genesis_key_service.py`

```python
# Line 227-245
sess.add(key)

# CRITICAL: Always flush to ensure key_id is accessible
sess.flush()

# Extract key_id immediately while still in session
extracted_key_id = key.key_id

# Only commit if we created our own session
if close_session:
    sess.commit()

# Update user statistics
if user_id:
    self._update_user_stats(user_id, key_type, is_error, sess)

# Post-creation hooks - use try/except to prevent failures
# Use extracted_key_id instead of key.key_id
try:
    kb_integration = get_kb_integration()
    # Pass key object while still in session context
    if not close_session or sess.is_active:
        kb_integration.save_genesis_key(key)
except Exception as kb_error:
    logger.warning(f"Failed to save Genesis Key to KB: {kb_error}")
    # Don't raise - key is already saved
```

### Step 2: Fix `file_version_tracker.py`

Same pattern - extract `key_id` immediately after flush.

### Step 3: Fix `symbiotic_version_control.py`

Already has the extraction at line 123, but needs to ensure session isn't rolled back.

---

## Testing Plan

### 1. Create a Test File

```bash
echo "test content" > /tmp/test_genesis_tracking.txt
cp /tmp/test_genesis_tracking.txt backend/knowledge_base/test_file.txt
```

### 2. Monitor Logs

```bash
tail -f backend/logs/grace.log | grep -E "(FILE_WATCHER|Genesis Key|DetachedInstance)"
```

### 3. Expected Success Output

```
[FILE_WATCHER] Tracked: test_file.txt - Operation: create, Genesis Key: GK-..., Version: 1
Created Genesis Key: GK-... - File version 1: test_file.txt
```

### 4. Expected Failure Output (Current State)

```
ERROR: Error in symbiotic tracking: Instance '<GenesisKey at 0x...>' has been deleted
ERROR: [FILE_WATCHER] Error tracking ...
```

---

## Impact Assessment

### Current Impact

- 🔴 **Critical**: ALL automatic file tracking is broken
- 🔴 **Critical**: Genesis Keys cannot be created reliably
- 🔴 **High**: KB integration failing
- 🔴 **High**: Memory Mesh integration failing
- 🟡 **Medium**: Auto-ingestion may be affected

### Systems Affected

1. File Watcher - Cannot track any file changes
2. Symbiotic Version Control - Non-functional
3. Genesis Key System - Partially functional (manual creation works, automatic fails)
4. Knowledge Base Integration - Failing
5. Memory Mesh - Failing

---

## Priority

**P0 - Critical**: This blocks core functionality and must be fixed immediately.

---

**Report Created**: January 27, 2026, 1:17 PM  
**Analyst**: Antigravity  
**Status**: Awaiting Fix Implementation
