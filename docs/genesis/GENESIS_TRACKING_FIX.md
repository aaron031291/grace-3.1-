# Genesis Tracking Error Fix

## Problem
When internet search results were saved to `knowledge_base/auto_search/`, the file watcher tried to track them with Genesis version control, causing this error:

```
ERROR: Error in symbiotic tracking: tuple index out of range
ERROR: [FILE_WATCHER] Error tracking .../auto_search/20260205_180613/Sadness_and_Depression.txt
```

## Root Cause
- Genesis file watcher monitors all file changes
- Internet search cache files (`auto_search/`) were being tracked
- Genesis has a database schema issue causing "tuple index out of range"
- These cache files don't need version control anyway

## Solution
Added `auto_search` to the file watcher's exclude patterns.

### Files Modified
**`genesis/file_watcher.py`** (2 locations):

1. **Line 53** - Instance exclude patterns:
```python
self.exclude_patterns = exclude_patterns or {
    # ... other patterns ...
    'auto_search',  # Exclude internet search cache - no need for version control
}
```

2. **Line 386** - Global exclude patterns:
```python
exclude_patterns={
    # ... other patterns ...
    'auto_search'  # Exclude internet search cache
}
```

## Result
✅ **No more Genesis tracking errors for auto_search files**
✅ **Internet search results still saved and ingested**
✅ **File watcher ignores cache files (as it should)**

## Status
**Restart backend to apply changes!**
