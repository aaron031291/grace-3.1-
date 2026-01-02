# File-Based Ingestion Manager - Reference Card

## Quick Commands

### CLI Commands

```bash
# Initialize git tracking
python -m ingestion.cli init-git

# Scan for changes (one-time)
python -m ingestion.cli scan

# Watch continuously (every 5 seconds)
python -m ingestion.cli watch --interval 5

# List all tracked files
python -m ingestion.cli list-tracked

# Clear tracking state
python -m ingestion.cli clear-state --force

# Show status
python -m ingestion.cli status

# Verbose output
python -m ingestion.cli -v scan
```

## API Endpoints

```bash
# Check status
curl http://localhost:8000/file-ingest/status

# Scan for changes
curl -X POST http://localhost:8000/file-ingest/scan

# Start background scan
curl -X POST http://localhost:8000/file-ingest/scan-background

# List tracked files
curl http://localhost:8000/file-ingest/tracked-files

# Clear tracking
curl -X POST http://localhost:8000/file-ingest/clear-tracking

# Initialize git
curl -X POST http://localhost:8000/file-ingest/initialize-git
```

## Python API

```python
from ingestion.file_manager import IngestionFileManager
from embedding.embedder import get_embedding_model
from api.ingest import get_ingestion_service

# Initialize
manager = IngestionFileManager(
    knowledge_base_path="backend/knowledge_base",
    embedding_model=get_embedding_model(),
    ingestion_service=get_ingestion_service(),
)

# Scan for changes
results = manager.scan_directory()

# Watch continuously
manager.watch_and_process(continuous=True)

# Process specific file
from pathlib import Path
result = manager.process_new_file(Path("backend/knowledge_base/doc.md"))
```

## File Operations

```bash
# Add document
cp myfile.md backend/knowledge_base/
python -m ingestion.cli scan

# Organize in subdirectory
mkdir -p backend/knowledge_base/guides
cp guide.md backend/knowledge_base/guides/
python -m ingestion.cli scan

# Batch import
cp -r /path/to/docs/* backend/knowledge_base/
python -m ingestion.cli scan

# Update document
vim backend/knowledge_base/guide.md
python -m ingestion.cli scan

# Delete document
rm backend/knowledge_base/guide.md
python -m ingestion.cli scan
```

## Workflow Recipes

### Single Document Workflow

```bash
# Add and ingest
cp document.md backend/knowledge_base/
python -m ingestion.cli scan

# Check what was ingested
curl http://localhost:8000/file-ingest/tracked-files

# Verify in database
psql -c "SELECT id, filename, total_chunks FROM documents ORDER BY created_at DESC LIMIT 1;"
```

### Batch Import Workflow

```bash
# Prepare files
mkdir backend/knowledge_base/imported
cp /external/docs/* backend/knowledge_base/imported/

# Scan and ingest
python -m ingestion.cli scan

# Review results
python -m ingestion.cli list-tracked | wc -l
```

### Continuous Monitoring

```bash
# Terminal 1: Watch for changes
python -m ingestion.cli watch --interval 5

# Terminal 2: Add files
cp documents/* backend/knowledge_base/

# Terminal 1 will automatically detect and ingest them
```

### Update Workflow

```bash
# Initial ingestion
cp guide.md backend/knowledge_base/
python -m ingestion.cli scan

# Later: update the file
echo "new content" >> backend/knowledge_base/guide.md

# Re-scan (old embeddings deleted, new ones created)
python -m ingestion.cli scan
```

## Debugging

```bash
# Verbose logging
python -m ingestion.cli -v scan

# Check git history
cd backend/knowledge_base
git log --oneline

# Check what's tracked
python -m ingestion.cli list-tracked

# Verify database
psql -c "SELECT COUNT(*) FROM documents;"
psql -c "SELECT COUNT(*) FROM document_chunks;"

# Check vector database
curl http://localhost:6333/collections

# Check state file
cat backend/knowledge_base/.ingestion_state.json | jq .
```

## Troubleshooting

### Files Not Detected

```bash
# Check file exists
ls -la backend/knowledge_base/myfile.txt

# Check extension is supported
file backend/knowledge_base/myfile.txt

# Run verbose scan
python -m ingestion.cli -v scan

# Check if it's hidden (starts with .)
ls -la backend/knowledge_base/
```

### Ingestion Fails

```bash
# Check database
psql -l

# Check Qdrant
curl http://localhost:6333/health

# Check logs
python -m ingestion.cli -v scan 2>&1 | tee ingestion.log

# Check database connection
python -c "from database.session import SessionLocal; print(SessionLocal())"
```

### Git Issues

```bash
# Check git status
cd backend/knowledge_base
git status

# Check git config
git config -l

# Reinitialize git
rm -rf .git
python -m ingestion.cli init-git
```

## State Management

```bash
# View current state
python -m ingestion.cli list-tracked

# Backup state
cp backend/knowledge_base/.ingestion_state.json backup.json

# Clear state (force re-ingestion)
python -m ingestion.cli clear-state --force

# Restore state
cp backup.json backend/knowledge_base/.ingestion_state.json
```

## Performance Tuning

### Reduce Scan Frequency

```bash
# Check every 30 seconds instead of 5
python -m ingestion.cli watch --interval 30
```

### Process Large Files

```bash
# Use background scan to avoid blocking
curl -X POST http://localhost:8000/file-ingest/scan-background
```

### Batch Process Many Files

```bash
# Copy all files first
cp -r /many/documents/* backend/knowledge_base/

# Then scan once (not repeatedly)
python -m ingestion.cli scan
```

## Common Scenarios

### Daily Document Update

```bash
# Cron job: scan every hour
0 * * * * cd /path/to/backend && python -m ingestion.cli scan >> /var/log/ingestion.log 2>&1
```

### Webhook Integration

```python
from fastapi import FastAPI
from ingestion.file_manager import IngestionFileManager

@app.post("/webhook/ingest")
async def webhook_ingest(file_manager = Depends(get_file_manager)):
    results = file_manager.scan_directory()
    return {"processed": len(results)}
```

### Custom Processing

```python
class CustomManager(IngestionFileManager):
    def process_new_file(self, filepath):
        # Custom validation
        if not self._should_ingest(filepath):
            return skip_result
        return super().process_new_file(filepath)
```

## Environment Variables

```bash
# Knowledge base path
export KB_PATH="backend/knowledge_base"

# Use in code
import os
kb_path = os.getenv("KB_PATH", "backend/knowledge_base")
```

## File Organization Tips

```
backend/knowledge_base/
├── guides/              # User guides
│   ├── getting-started.md
│   └── best-practices.md
├── api/                 # API documentation
│   ├── endpoints.md
│   └── examples.md
├── tutorials/           # Step-by-step tutorials
│   ├── basic.md
│   └── advanced.md
└── reference/           # Reference material
    ├── glossary.md
    └── changelog.md
```

The manager will recursively process all subdirectories.

## Status Codes

### Scan Results

```
success: true  → File processed successfully
success: false → Error occurred during processing

change_type values:
- "added"      → New file ingested
- "modified"   → Old embeddings deleted, new ones created
- "deleted"    → Embeddings and metadata removed
```

## Limits & Constraints

- **File Size**: No hard limit, limited by memory and processing time
- **Chunk Size**: Default 512 chars (configurable)
- **Extensions**: Customize in `_is_ingestionable_file()`
- **Scan Frequency**: Minimum 1 second recommended
- **Concurrent Scans**: Safe to run multiple times

## Integration Checklist

- [ ] Database (PostgreSQL) running
- [ ] Vector DB (Qdrant) running
- [ ] Embedding model available
- [ ] Knowledge base directory exists
- [ ] API server running
- [ ] Git installed
- [ ] Files added to knowledge_base/
- [ ] Initial scan completed
- [ ] Verify documents in database
- [ ] Test API endpoints

## Quick Fixes

### "Git not found"

```bash
which git  # Install if not found
apt install git  # Ubuntu/Debian
brew install git  # macOS
```

### "Database connection failed"

```bash
psql -c "SELECT 1"  # Test connection
# Check database.config settings
```

### "Embedding model not available"

```bash
python -c "from embedding.embedder import get_embedding_model; print(get_embedding_model())"
```

### "Files keep being reprocessed"

```bash
# Clear state to reset
python -m ingestion.cli clear-state --force
python -m ingestion.cli scan
```

## Documentation Files

- **FILE_INGESTION_MANAGER.md** - Complete documentation (600+ lines)
- **FILE_INGESTION_MANAGER_QUICKSTART.md** - Quick start guide (300+ lines)
- **INGESTION_MANAGER_SUMMARY.md** - Implementation summary
- **backend/ingestion/EXAMPLES.py** - 10 working code examples
- **This file** - Quick reference

## Getting Help

1. Check QuickStart: `FILE_INGESTION_MANAGER_QUICKSTART.md`
2. Read full docs: `FILE_INGESTION_MANAGER.md`
3. Review examples: `backend/ingestion/EXAMPLES.py`
4. Use verbose mode: `python -m ingestion.cli -v scan`
5. Check logs: `backend/ingestion.log`
