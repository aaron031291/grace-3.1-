# Reset and Reingest Bug Fix - Root Cause and Solution

## Problem Summary
After running `reset_and_reingest.py`, the GDP document would disappear from search results despite the reset script reporting successful ingestion.

## Root Cause Analysis

The bug was in `/backend/reset_and_reingest.py` at **line 92**.

### The Bug
```python
# INCORRECT (line 92)
database_path="grace.db",
```

This path is **relative** and resolves to `./grace.db` in the current working directory.

### The Issue
1. The actual application database is at: `./data/grace.db`
2. The reset script was clearing: `./grace.db` (different location, may not even exist)
3. Result: The actual database was NEVER cleared
4. When reset_and_reingest called `scan_directory()` to ingest files:
   - Files were found as "new" (since state file was empty)
   - But the database still had old document hashes
   - Files were rejected as "already ingested" via content hash deduplication
   - Search results were empty because no NEW vectors were created

### Evidence
- After reset_and_reingest with the bug: `./grace.db` was modified, but `./data/grace.db` was untouched
- GDP would successfully ingest (logging showed success), but wouldn't appear in search
- All database query results returned empty (wrong database was being reset)

## Solution

Change line 92 in `/backend/reset_and_reingest.py` from:
```python
database_path="grace.db",
```

To:
```python
database_path="./data/grace.db",
```

This ensures the reset script operates on the SAME database file that the application uses.

## Implementation Status
✅ **FIXED** - Reset script now correctly clears the production database before re-ingestion.

## Verification
After applying the fix:
1. Run: `python3 reset_and_reingest.py`
2. Query: `curl -X POST http://localhost:8000/retrieve/search?query=GDP&limit=5`
3. Result: GDP document now appears at top with scores 0.60+

### Test Results
- Document ID 2: `gdp_volatility.pdf` - Successfully ingested
- Top 3 results for "GDP" query: All from gdp_volatility.pdf with scores:
  - 0.607 (chunk 0)
  - 0.589 (chunk 12)
  - 0.562 (chunk 11)

## Related Context
This bug was masked by earlier fixes to the ingestion deduplication system. The deduplication logic itself is correct; it was the reset script's failure to clear the correct database that caused the problem to reoccur.

### Previous Fixes (Still Valid)
- Hybrid search implementation with keyword boosting (30% keyword weight)
- Content hash deduplication prevents true duplicates
- Proper vector-database synchronization

### Why This Happened
The database path configuration evolved:
- Originally may have been `grace.db` in root
- Later moved to `./data/grace.db` (following standard pattern)
- Reset script was never updated to match the new location
- The bug went undetected because manual uploads and auto-ingestion used the correct path

## Files Modified
- `/backend/reset_and_reingest.py` - Line 92: Updated database_path parameter

## Preventive Measures
Consider:
1. Using `DatabaseConfig.from_env()` in reset_and_reingest to match application config exactly
2. Adding a database path validation step before starting reset process
3. Documentation update specifying the correct database path location
