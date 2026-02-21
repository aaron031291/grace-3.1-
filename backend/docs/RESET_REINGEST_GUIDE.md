# Reset & Re-ingestion Script Guide

## Overview

`reset_and_reingest.py` is a comprehensive Python script that clears all data from your Grace knowledge base system and re-ingests all files from scratch. It provides detailed logging to show exactly which files are being processed.

## What It Does

### 1. Clears SQLite Database

- Removes all documents
- Removes all document chunks
- Removes all chats and chat history
- Creates fresh tables if needed

### 2. Clears Qdrant Vector Database

- Deletes the 'documents' collection
- Removes all vector embeddings

### 3. Resets File Ingestion Tracking

- Deletes `.ingestion_state.json` file
- Removes and reinitializes git repository
- Allows all files to be detected as "new"

### 4. Triggers Auto-Ingestion

- Detects all files in `knowledge_base/` directory
- Processes each file individually
- Generates embeddings and stores in both SQL and Qdrant
- Provides real-time progress logs

## Usage

### Basic Usage

```bash
cd /home/umer/Public/projects/grace_3/backend
python ./reset_and_reingest.py
```

### Output Example

```
================================================================================
[INGESTION START] NEW FILE
  File: text.txt
  Size: 1.2 KB
  Full path: /home/umer/Public/projects/grace_3/backend/knowledge_base/text.txt
  Started at: 2026-01-06 20:12:48.342
================================================================================
[INGESTION] Reading file content...
[INGESTION] ✓ Read 1234 characters
[INGESTION] Extracting text and generating embeddings...
[INGESTION] ✓ Text extraction and embedding completed
[INGESTION] Document ID: 1
[INGESTION] Updating document metadata...
[INGESTION] ✓ Document metadata updated
[INGESTION] Tracking file state...
[INGESTION] Committing to git...
================================================================================
[INGESTION SUCCESS] text.txt
  Document ID: 1
  Processing time: 0.45 seconds
  Content length: 1234 characters
  Message: Document ingested successfully
  Completed at: 2026-01-06 20:12:48.897
================================================================================
```

## Output Details

### Per-File Logging

For each file being ingested, you'll see:

- **File**: Relative path from knowledge_base/
- **Size**: File size in KB
- **Full path**: Absolute path to file
- **Started at**: Timestamp when ingestion began
- **Document ID**: ID assigned in database
- **Processing time**: How long ingestion took
- **Content length**: Number of characters
- **Status**: SUCCESS or FAILED

### Summary Statistics

At the end, you'll see:

- Total files processed
- Number successful
- Number failed
- Breakdown by change type (added/modified/deleted)

## Supported File Types

The script can ingest the following file types:

- `.txt` - Plain text
- `.md` - Markdown
- `.pdf` - PDF documents
- `.docx`, `.doc` - Word documents
- `.json`, `.yaml`, `.yml`, `.xml`, `.html` - Data formats
- `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c` - Source code

## Important Notes

1. **Backup First**: Before running this script, make sure you have backups of important data if needed

2. **Time Required**: Ingesting many files can take time. The script displays progress for each file

3. **Database Initialization**: The script automatically creates database tables if they don't exist

4. **Git Initialization**: A fresh git repository is created in the knowledge_base/ directory

5. **File Deduplication**: Files with identical content won't be ingested twice (content hash is used)

6. **No Internet Required**: Ingestion happens locally using your configured models

## Troubleshooting

### "No such table" Error

- The script now automatically creates tables
- If you still see this error, ensure Ollama and Qdrant are running

### Files Not Being Ingested

- Check that files are in a supported format
- Ensure files are in `backend/knowledge_base/` directory
- Check that filenames don't start with a dot (`.`)

### Slow Ingestion

- Processing time depends on:
  - File size
  - Number of embeddings to generate
  - System resources
  - Embedding model complexity
- Be patient and let it complete

## Log Levels

The script provides detailed logging:

- **INFO** (🟢 Green): Normal operations, file progress
- **WARNING** (🟡 Yellow): Non-critical issues
- **ERROR** (🔴 Red): Ingestion failures
- **DEBUG** (🔵 Cyan): Detailed troubleshooting info

## Advanced Options

The script uses environment configuration:

- Database type: Set in `backend/settings.py`
- Embedding model: Configured in `backend/settings.py`
- Vector DB: Qdrant (localhost:6333)

To modify these, edit `backend/settings.py` before running the script.

## What Happens Next

After the script completes:

1. Your knowledge base is fully loaded and searchable
2. Auto-ingestion monitor runs in the background (checks every 30 seconds)
3. New files added to `knowledge_base/` are automatically ingested
4. All files are available for RAG search and document chat

## Performance Tips

- Close other applications to free up resources
- If ingesting many large files, consider running overnight
- Check system memory and CPU during ingestion
- Monitor Qdrant and database performance in separate terminals
