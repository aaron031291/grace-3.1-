# File-Based Ingestion Manager - Quick Start

## Overview

The File-Based Ingestion Manager automatically handles document ingestion for files in `backend/knowledge_base`:

- **New files** → Automatically ingested with embeddings generated
- **Modified files** → Old embeddings deleted, new ones generated
- **Deleted files** → Embeddings and metadata removed

## Installation

The manager is built into the system. No additional installation needed.

### Prerequisites

- Git installed on your system
- PostgreSQL database running
- Qdrant vector database running
- Embedding model available (qwen_4b)

## Quick Start

### 1. Initialize Git Tracking

```bash
cd backend
python -m ingestion.cli init-git
```

This creates a `.git` repository in the knowledge base directory.

### 2. Add Documents

Place files in `backend/knowledge_base/`:

```bash
cp my_document.md backend/knowledge_base/
cp my_guide.txt backend/knowledge_base/
```

### 3. Scan and Ingest

Run the scanner to detect and process new files:

```bash
python -m ingestion.cli scan
```

Output:

```
================================================================================
SCAN RESULTS: 2 changes processed
  ✓ Successful: 2
  ✗ Failed: 0
================================================================================

✓ [ADDED] documents/guide.md
    Document ID: 42
    Message: Document ingested successfully
✓ [ADDED] docs/tutorial.md
    Document ID: 43
    Message: Document ingested successfully
```

### 4. Update Files

Modify a document:

```bash
echo "Updated content" >> backend/knowledge_base/documents/guide.md
python -m ingestion.cli scan
```

The manager will:

1. Detect the modification
2. Delete old embeddings
3. Re-ingest with new content
4. Generate new embeddings

### 5. Delete Files

Remove a document:

```bash
rm backend/knowledge_base/documents/guide.md
python -m ingestion.cli scan
```

The manager will:

1. Remove embeddings from Qdrant
2. Remove metadata from database
3. Clean up completely

## Using via API

### Start the FastAPI server

```bash
cd backend
python app.py
```

### Scan via API

```bash
curl -X POST http://localhost:8000/file-ingest/scan
```

Response:

```json
{
  "total_processed": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "success": true,
      "filepath": "documents/guide.md",
      "change_type": "added",
      "document_id": 42,
      "message": "Document ingested successfully"
    }
  ]
}
```

### Get Status

```bash
curl http://localhost:8000/file-ingest/status
```

### List Tracked Files

```bash
curl http://localhost:8000/file-ingest/tracked-files
```

## Common Commands

### Watch for Changes (Continuous)

```bash
# Scan every 5 seconds
python -m ingestion.cli watch --interval 5

# Press Ctrl+C to stop
```

### List All Tracked Files

```bash
python -m ingestion.cli list-tracked
```

### Check Manager Status

```bash
python -m ingestion.cli status
```

### Reset Tracking State

```bash
python -m ingestion.cli clear-state --force
```

## Directory Structure

```
backend/
├── knowledge_base/           # Your documents go here
│   ├── .git/                 # Git repository
│   ├── .ingestion_state.json # Tracking state
│   ├── document1.md
│   ├── document2.txt
│   └── guides/
│       └── tutorial.md
├── ingestion/
│   ├── file_manager.py       # Main manager class
│   ├── cli.py                # CLI utility
│   └── service.py            # Ingestion service
└── app.py                    # FastAPI app
```

## Supported File Types

- Documents: `.txt`, `.md`, `.pdf`, `.docx`, `.doc`
- Code: `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`
- Data: `.json`, `.yaml`, `.yml`, `.xml`, `.html`

## Tips

### Organize Documents

Create subdirectories for better organization:

```
backend/knowledge_base/
├── guides/
│   ├── getting-started.md
│   └── best-practices.md
├── api/
│   ├── reference.md
│   └── examples.md
└── tutorials/
    └── step-by-step.md
```

The manager recursively processes all subdirectories.

### Batch Import

Import multiple documents:

```bash
cp -r /path/to/documents/* backend/knowledge_base/
python -m ingestion.cli scan
```

### Monitor Ingestion

Check what's being tracked:

```bash
python -m ingestion.cli list-tracked | head -20
```

### Verify Git History

See git commits for ingestion:

```bash
cd backend/knowledge_base
git log --oneline | head -10
```

## Troubleshooting

### Files not detected

1. Check file extension is supported
2. Verify file is not prefixed with `.` (hidden files ignored)
3. Ensure file is readable:
   ```bash
   ls -la backend/knowledge_base/
   ```

### Ingestion fails

1. Check database is running:

   ```bash
   psql -c "SELECT 1"
   ```

2. Check Qdrant is running:

   ```bash
   curl http://localhost:6333/health
   ```

3. Check logs for detailed errors:
   ```bash
   python -m ingestion.cli -v scan
   ```

### Git initialization fails

1. Ensure git is installed:

   ```bash
   git --version
   ```

2. Check directory permissions:
   ```bash
   ls -ld backend/knowledge_base/
   ```

## Next Steps

- Read [FILE_INGESTION_MANAGER.md](FILE_INGESTION_MANAGER.md) for complete documentation
- Check API endpoints at `/file-ingest/*` in the FastAPI docs
- Integrate with your workflow (scripts, webhooks, etc.)
- Customize supported file types as needed

## Support

For issues or questions:

1. Check logs with verbose mode: `python -m ingestion.cli -v scan`
2. Verify all services are running
3. Check database for document records
4. Reset state if needed: `python -m ingestion.cli clear-state --force`
