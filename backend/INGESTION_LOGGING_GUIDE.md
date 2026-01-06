# Enhanced Auto-Ingestion Logging

## Overview

The auto-ingestion system now provides detailed, real-time logging that shows exactly which file is being processed, how long it takes, and what happens at each step.

## Logging Features

### 1. File Processing Headers

Each file ingestion starts with a clear header:

```
================================================================================
[INGESTION START] NEW FILE
  File: biology/bio_text.txt
  Size: 2.1 KB
  Full path: /home/umer/Public/projects/grace_3/backend/knowledge_base/biology/bio_text.txt
  Started at: 2026-01-06 20:12:48.342
================================================================================
```

### 2. Step-by-Step Progress

As the file is processed, you see each step:

```
[INGESTION] Reading file content...
[INGESTION] ✓ Read 782 characters
[INGESTION] Extracting text and generating embeddings...
[INGEST_FAST] Creating new embedding model instance...
[INGEST_FAST] ✓ Chunked text into 3 chunks
[INGEST_FAST] ✓ Generated embeddings for 3 chunks
[INGEST_FAST] ✓ Successfully stored vectors in Qdrant
[INGESTION] ✓ Text extraction and embedding completed
[INGESTION] Document ID: 2
[INGESTION] Updating document metadata...
[INGESTION] ✓ Document metadata updated
[INGESTION] Tracking file state...
[INGESTION] Committing to git...
```

### 3. Success Summary

After successful ingestion:

```
================================================================================
[INGESTION SUCCESS] biology/bio_text.txt
  Document ID: 2
  Processing time: 0.39 seconds
  Content length: 782 characters
  Message: Document ingested successfully
  Completed at: 2026-01-06 20:11:31.872
================================================================================
```

### 4. Error Reporting

If ingestion fails:

```
================================================================================
[INGESTION FAILED] ai_things/text.txt
  Error: Some error message here
  Processing time: 0.12 seconds
  Completed at: 2026-01-06 20:11:32.003
================================================================================
```

### 5. Exception Details

Detailed stack traces for debugging:

```
================================================================================
[INGESTION EXCEPTION] problem_file.txt
  Error: Detailed error description
  Processing time: 0.05 seconds
  Completed at: 2026-01-06 20:11:33.123
================================================================================
(Full stack trace follows...)
```

## Three Types of File Processing

### New Files

```
[INGESTION START] NEW FILE
  File: new_document.txt
  ...
```

- Detected when file is not in tracking state
- Creates new document record
- Generates embeddings and stores in Qdrant

### Modified Files

```
[INGESTION START] MODIFIED FILE
  File: updated_document.txt
  ...
```

- Detected when file hash has changed
- Deletes old embeddings
- Re-ingests with new content
- Creates new document record

### Deleted Files

```
[INGESTION START] DELETED FILE
  File: removed_document.txt
  ...
```

- Detected when file is missing from disk
- Removes embeddings from Qdrant
- Deletes document record from database

## What Each Log Section Means

### [INGESTION] - File Manager Level

High-level file operations:

- Reading file content
- Document metadata updates
- File state tracking
- Git commits

### [INGEST_FAST] - Ingestion Service Level

Lower-level processing:

- Content hashing
- Duplicate checking
- Chunking strategy
- Embedding generation
- Vector storage

### [EMBEDDING] - Embedding Model Level

Model initialization:

- Model loading
- Device selection
- Batch processing

### [SCAN] - Scanner Level

Directory scanning:

- File detection
- Change detection
- Database sync

### [VECTOR_DB.CLIENT] - Vector Database Level

Qdrant operations:

- Collection creation/deletion
- Vector upsert/delete
- Connection status

## Using the Logs

### Finding Files That Ingested Successfully

```bash
grep "\[INGESTION SUCCESS\]" /path/to/logs
```

### Finding Ingestion Failures

```bash
grep "\[INGESTION FAILED\]" /path/to/logs
```

### Tracking Processing Times

```bash
grep "Processing time:" /path/to/logs
```

### Watching Real-Time Progress

```bash
python reset_and_reingest.py 2>&1 | grep "\[INGESTION"
```

## Log Format

All logs follow this format:

```
YYYY-MM-DD HH:MM:SS.mmm | LEVEL | MODULE | MESSAGE
```

Example:

```
2026-01-06 20:11:31.872 | INFO | ingestion.file_manager | [INGESTION SUCCESS] biology/bio_text.txt
```

### Timestamp Precision

- Date: Year-Month-Day
- Time: Hours:Minutes:Seconds.Milliseconds
- Helps correlate events across different systems

### Log Levels

- 🟢 **INFO** (Green): Normal progress
- 🟡 **WARNING** (Yellow): Non-critical issues
- 🔴 **ERROR** (Red): Failures
- 🔵 **DEBUG** (Cyan): Detailed debugging info

## Performance Metrics in Logs

### Processing Time

Shows how long each file took:

```
Processing time: 0.39 seconds
```

### Content Metrics

Shows what was processed:

```
Content length: 782 characters
```

### Document Reference

Shows database ID for later lookup:

```
Document ID: 2
```

## Integrated Logging Sources

The script shows logs from multiple components:

1. **Reset & Reingest Script** (`__main__`)

   - High-level progress
   - Summary statistics

2. **File Manager** (`ingestion.file_manager`)

   - File processing steps
   - Success/failure reporting

3. **Ingestion Service** (`ingestion.service`)

   - Content processing
   - Embedding generation
   - Database operations

4. **Vector Database** (`vector_db.client`)

   - Connection status
   - Qdrant operations

5. **Database** (`database.*`)
   - Table creation
   - Connection status

## Tips for Monitoring

### Use Tail for Real-Time Monitoring

```bash
python reset_and_reingest.py 2>&1 | tail -f
```

### Save Logs to File

```bash
python reset_and_reingest.py > ingestion.log 2>&1
```

### Filter for Specific Information

```bash
python reset_and_reingest.py 2>&1 | grep -E "SUCCESS|FAILED"
```

### Count Ingested Files

```bash
python reset_and_reingest.py 2>&1 | grep -c "INGESTION SUCCESS"
```

### Monitor Processing Speed

```bash
python reset_and_reingest.py 2>&1 | grep "Processing time:"
```

## Example: Full Ingestion Session Log

```
2026-01-06 20:07:43 | INFO | __main__ | ╔════════════════════════════════════════╗
2026-01-06 20:07:43 | INFO | __main__ | ║ GRACE KNOWLEDGE BASE - COMPLETE RESET  ║
2026-01-06 20:07:43 | INFO | __main__ | ╚════════════════════════════════════════╝

2026-01-06 20:07:43 | INFO | __main__ | [1/4] CLEARING SQLITE DATABASE
2026-01-06 20:07:43 | INFO | __main__ | Setting up SQLite configuration...
2026-01-06 20:07:43 | INFO | __main__ | ✓ SQLite data cleared successfully

2026-01-06 20:07:44 | INFO | __main__ | [2/4] CLEARING QDRANT VECTOR DATABASE
2026-01-06 20:07:44 | INFO | __main__ | ✓ Qdrant collection 'documents' deleted

2026-01-06 20:07:44 | INFO | __main__ | [3/4] RESETTING FILE INGESTION TRACKING
2026-01-06 20:07:44 | INFO | __main__ | ✓ File tracking state removed
2026-01-06 20:07:44 | INFO | __main__ | ✓ Git repository removed

2026-01-06 20:07:44 | INFO | __main__ | [4/4] TRIGGERING AUTO-INGESTION
2026-01-06 20:07:47 | INFO | __main__ | ✓ Session factory initialized
2026-01-06 20:07:47 | INFO | __main__ | ✓ Database tables created

2026-01-06 20:11:30 | INFO | ingestion.file_manager | [INGESTION START] NEW FILE
2026-01-06 20:11:30 | INFO | ingestion.file_manager |   File: text.txt
2026-01-06 20:11:30 | INFO | ingestion.file_manager | ✓ Read 1234 characters
2026-01-06 20:11:31 | INFO | ingestion.file_manager | [INGESTION SUCCESS] text.txt

2026-01-06 20:11:31 | INFO | ingestion.file_manager | [INGESTION START] NEW FILE
2026-01-06 20:11:31 | INFO | ingestion.file_manager |   File: biology/bio_text.txt
2026-01-06 20:11:31 | INFO | ingestion.file_manager | ✓ Read 782 characters
2026-01-06 20:11:31 | INFO | ingestion.file_manager | [INGESTION SUCCESS] biology/bio_text.txt

2026-01-06 20:11:31 | INFO | __main__ | Summary Statistics:
2026-01-06 20:11:31 | INFO | __main__ |   Total processed: 3
2026-01-06 20:11:31 | INFO | __main__ |   Successful: 3
2026-01-06 20:11:31 | INFO | __main__ |   Failed: 0

2026-01-06 20:11:31 | INFO | __main__ | ✓ RESET AND RE-INGESTION COMPLETED SUCCESSFULLY
```

This detailed logging makes it easy to:

- Track what's happening
- Identify which files had problems
- Monitor performance
- Debug issues
- Understand the ingestion pipeline
