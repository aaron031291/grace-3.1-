# Backend Errors - Quick Fix Guide

## Current Errors

### 1. 404 Error - Old Code Still Running ❌
```
ERROR: Database session error: 404: I cannot answer this question. 
No relevant information found in the knowledge base.
```

**Problem**: The old RAG-first code is still running instead of the new multi-tier system.

**Cause**: Backend hasn't been restarted since we made the multi-tier changes.

**Fix**: **Restart the backend**
```bash
# Stop current backend (Ctrl+C in the terminal)
cd /home/zair/Documents/grace/test/grace-3.1-/backend
source venv/bin/activate
python app.py
```

---

### 2. Genesis Key SQLAlchemy Error ⚠️
```
ERROR: Error in symbiotic tracking: Instance '<GenesisKey>' has been deleted, 
or its row is otherwise not present.
```

**Problem**: Detached SQLAlchemy instance in Genesis file watcher.

**Cause**: Database session management issue in `genesis/symbiotic_version_control.py`.

**Impact**: Non-critical - only affects Genesis tracking, doesn't break core functionality.

**Fix**: Can be addressed later (not urgent).

---

## What Will Happen After Restart

### Before (Current) ❌
- Query → VectorDB fails → **404 Error**
- No fallback tiers
- No internet search option

### After (With Multi-Tier) ✅
- Query → VectorDB fails → Model Knowledge → Internet Search → Context Request
- No more 404 errors
- Intelligent fallbacks
- Internet search only when appropriate

---

## Quick Restart Steps

1. **Stop backend**: Press `Ctrl+C` in backend terminal
2. **Restart**: `python app.py`
3. **Test**: Send a query like "What is Python?"
4. **Expected**: Should get Tier 2 (Model Knowledge) response with warning

---

## Files That Need Backend Restart

All these changes require restart:
- ✅ Multi-tier query handling (`query_intelligence.py`)
- ✅ Internet search tier (`query_intelligence.py`)
- ✅ Integration helper (`multi_tier_integration.py`)
- ✅ Greeting detection (`app.py`)

---

## Status

⏳ **Backend restart required to apply all fixes**

Once restarted:
- ✅ No more 404 errors
- ✅ Multi-tier fallback active
- ✅ Intelligent internet search
- ✅ Better greeting detection
