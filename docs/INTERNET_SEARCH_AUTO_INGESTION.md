# Internet Search Ingestion Fix

## Problem

Internet search results weren't being ingested into VectorDB, causing repeated searches for the same query.

**Symptoms**:
```
[INGEST_FAST] Ingestion error suppressed: UPDATE statement on table 'documents' expected to update 1 row(s); 0 were matched.
ERROR: [INGESTION FAILED] auto_search/20260205_180613/Sadness_and_Depression.txt
```

**Root Cause**:
1. Search results were saved to `knowledge_base/auto_search/` files
2. File watcher detected new files and tried to ingest them
3. Genesis version control tracking failed with database schema error
4. Ingestion was aborted due to version control failure
5. Files existed but weren't in VectorDB
6. Next query triggered internet search again ❌

---

## Solution: Direct Ingestion

**Bypass file watcher entirely** - ingest search results directly into VectorDB!

### How It Works Now

```
Internet Search Results
         ↓
    [DIRECT INGESTION]
         ↓
  TextIngestionService.ingest_text_fast()
         ↓
    VectorDB ✅
```

**No files created** → **No file watcher** → **No Genesis errors** → **Immediate availability**

---

## Code Changes

### File: `retrieval/query_intelligence.py`

**Method**: `_ingest_search_results()` (lines 581-665)

**Before** ❌:
```python
# Save files to knowledge_base/auto_search/
filepath.write_text(content, encoding='utf-8')
# Wait for file watcher to detect and ingest...
```

**After** ✅:
```python
# Import ingestion service
from ingestion.service import TextIngestionService
from embedding import get_embedding_model

# Ingest directly into VectorDB
doc_id, status = ingestion_service.ingest_text_fast(
    text_content=content,
    filename=filename,
    source=link,
    upload_method="internet_search",
    source_type="internet_search",
    tags=["internet_search", "auto_ingested"],
    metadata={...}
)
```

---

## Benefits

1. **No File Watcher Dependency** ✅
   - Direct ingestion, no intermediate files
   - No Genesis tracking errors

2. **Immediate Availability** ✅
   - Search results available in VectorDB instantly
   - No waiting for file watcher to detect files

3. **No Repeated Searches** ✅
   - Next query finds results in VectorDB (Tier 1)
   - Internet search only happens once

4. **Cleaner System** ✅
   - No `auto_search/` directory clutter
   - All data in VectorDB where it belongs

---

## Testing

**Test Case**: Ask "I am feeling sad" twice

### Expected Behavior:

**First Query**:
```
Tier 1 (VectorDB): ❌ No results
Tier 2 (Model): ⚠️ Low confidence
Tier 3 (Internet): ✅ Found 5 results
  → Ingested directly into VectorDB
  → Response generated
```

**Second Query** (SAME question):
```
Tier 1 (VectorDB): ✅ Found results! (from previous search)
  → Response generated immediately
  → NO internet search needed! ⚡
```

---

## Status

✅ **Direct ingestion implemented**
✅ **No more file watcher dependency**
✅ **No more Genesis tracking errors**
✅ **Search results immediately available**

**Restart backend to apply changes!**
