# Embedding Model Unload Fix (Round 2) ✅

## Problem
```
ERROR: Model has been unloaded. Create a new instance to use embeddings.
```

Occurred during internet search result ingestion.

## Root Cause
Previous fix used `self.retriever.embedding_model`, but that instance can still be garbage collected and unloaded.

## Solution
**File**: `backend/retrieval/query_intelligence.py` (line 605)

**Changed from**:
```python
embedding_model = self.retriever.embedding_model  # Can be unloaded
```

**Changed to**:
```python
from embedding import get_embedding_model
embedding_model = get_embedding_model()  # Global singleton, never unloaded
```

## Why This Works
- `get_embedding_model()` returns the **global singleton** instance
- Singleton is kept alive for entire application lifecycle
- Cannot be garbage collected
- Shared across all components

## Status
✅ **Fixed** - Backend auto-reloading

---

**Test**: Try internet search query again - should work now! 🚀
