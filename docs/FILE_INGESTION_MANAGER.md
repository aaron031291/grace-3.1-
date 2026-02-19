# File-Based Ingestion Manager

A sophisticated git-based file tracking system for automatically managing document ingestion in the knowledge base. Monitors `backend/knowledge_base` for file changes and triggers appropriate ingestion, update, or deletion operations.

## Overview

The File-Based Ingestion Manager provides:

- **Automatic Change Detection**: Uses git to track file changes (new, modified, deleted)
- **Intelligent Processing**:
  - **New files**: Automatically ingests documents and generates embeddings
  - **Modified files**: Deletes old embeddings and re-ingests with new content
  - **Deleted files**: Removes embeddings and metadata from the system
- **State Tracking**: Maintains a persistent state file of ingested files
- **Git Integration**: Automatically commits changes for audit trail

## Architecture

### Components

#### `GitFileTracker`

Manages git operations for the knowledge base directory:

- Initialize git repository
- Track file changes using git
- Stage and commit changes
- Get file hashes for change detection

#### `IngestionFileManager`

Main manager class that coordinates file processing:

- Scans directory for changes
- Processes new/modified/deleted files
- Manages embeddings in vector database
- Maintains file state
- Integrates with ingestion service

### File Change Flow

```
┌─────────────────────────────────────────────────┐
│      Scan Knowledge Base Directory              │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    NEW FILE    MODIFIED FILE   DELETED FILE
        │             │             │
        ▼             ▼             ▼
   INGEST      DELETE OLD + RE-INGEST  DELETE ALL
   (Create)    (Update)                (Cleanup)
```

## Supported File Types

The manager ingests the following file types:

- `.txt` - Plain text
- `.md` - Markdown
- `.pdf` - PDF documents
- `.docx`, `.doc` - Word documents
- `.json`, `.yaml`, `.yml`, `.xml` - Configuration/data formats
- `.html` - HTML documents
- `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c` - Source code

## API Endpoints

### `POST /file-ingest/scan`

Scan knowledge base for changes and process them.

**Response:**

```json
{
  "total_processed": 5,
  "successful": 4,
  "failed": 1,
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

### `POST /file-ingest/scan-background`

Start background scan (returns immediately).

**Response:**

```json
{
  "status": "Background scan started",
  "knowledge_base_path": "backend/knowledge_base"
}
```

### `GET /file-ingest/status`

Get file manager status.

**Response:**

```json
{
  "initialized": true,
  "knowledge_base_path": "backend/knowledge_base",
  "tracked_files": 15,
  "git_initialized": true
}
```

### `POST /file-ingest/initialize-git`

Initialize git repository for tracking.

**Response:**

```json
{
  "status": "success",
  "message": "Git repository initialized",
  "path": "backend/knowledge_base"
}
```

### `GET /file-ingest/tracked-files`

Get list of all tracked files.

**Response:**

```json
{
  "count": 15,
  "files": [
    {
      "filepath": "documents/guide.md",
      "hash": "abc123def456..."
    }
  ]
}
```

### `POST /file-ingest/clear-tracking`

Clear all file tracking state (resets hashes).

**Response:**

```json
{
  "status": "success",
  "message": "Tracking state cleared",
  "cleared_count": 15
}
```

## Command-Line Interface

### Usage

```bash
# Run from backend directory
python -m ingestion.cli [OPTIONS] COMMAND
```

### Commands

#### `scan`

Scan knowledge base for changes and process them.

```bash
python -m ingestion.cli scan
```

#### `watch`

Watch knowledge base for changes (continuous mode).

```bash
python -m ingestion.cli watch --interval 5
```

Options:

- `--interval INT` - Scan interval in seconds (default: 5)

#### `init-git`

Initialize git repository for tracking.

```bash
python -m ingestion.cli init-git
```

#### `list-tracked`

List all tracked files.

```bash
python -m ingestion.cli list-tracked
```

#### `clear-state`

Clear file tracking state.

```bash
python -m ingestion.cli clear-state [--force]
```

Options:

- `--force` - Skip confirmation prompt

#### `status`

Show file manager status.

```bash
python -m ingestion.cli status
```

### Examples

```bash
# Scan for changes
python -m ingestion.cli scan

# Watch continuously with 10 second intervals
python -m ingestion.cli watch --interval 10

# Initialize git tracking
python -m ingestion.cli init-git

# List all tracked files
python -m ingestion.cli list-tracked

# Clear state without confirmation
python -m ingestion.cli clear-state --force

# Verbose output
python -m ingestion.cli -v scan
```

## Python API

### Basic Usage

```python
from ingestion.file_manager import IngestionFileManager
from embedding.embedder import get_embedding_model
from api.ingest import get_ingestion_service

# Initialize manager
embedding_model = get_embedding_model()
ingestion_service = get_ingestion_service()

manager = IngestionFileManager(
    knowledge_base_path="backend/knowledge_base",
    embedding_model=embedding_model,
    ingestion_service=ingestion_service,
)

# Scan for changes
results = manager.scan_directory()

for result in results:
    if result.success:
        print(f"✓ {result.change_type}: {result.filepath}")
        print(f"  Document ID: {result.document_id}")
    else:
        print(f"✗ {result.change_type}: {result.filepath}")
        print(f"  Error: {result.error}")
```

### Processing Specific Actions

```python
from pathlib import Path

# Process new file
result = manager.process_new_file(Path("backend/knowledge_base/document.md"))

# Process modified file
result = manager.process_modified_file(Path("backend/knowledge_base/document.md"))

# Process deleted file
result = manager.process_deleted_file("backend/knowledge_base/document.md")
```

### Continuous Watching

```python
# Watch directory and process changes (continuous)
manager.watch_and_process(continuous=True)

# Or single scan only
manager.watch_and_process(continuous=False)
```

### Git Operations

```python
# Initialize git repository
manager.git_tracker.initialize_git()

# Add file to git
manager.git_tracker.add_file("documents/guide.md")

# Commit changes
manager.git_tracker.commit_changes("Ingested new documentation")

# Get untracked files
untracked = manager.git_tracker.get_untracked_files()
```

## State Management

### State File

The manager maintains a `.ingestion_state.json` file in the knowledge base directory:

```json
{
  "documents/guide.md": "abc123def456789...",
  "documents/tutorial.md": "def456ghi789012...",
  "docs/api.md": "ghi789jkl012345..."
}
```

Each entry maps a file path to its SHA256 hash. This is used to detect modifications.

### Loading and Saving State

```python
# State is automatically loaded on initialization
manager._load_state()

# Save current state
manager._save_state()

# Clear state
manager.file_states.clear()
manager._save_state()
```

## Workflow Examples

### Automatic Ingestion on New File

1. User adds a new file to `backend/knowledge_base/`
2. Manager detects the new file
3. Reads file content
4. Calls ingestion service to:
   - Create document record in database
   - Generate chunks
   - Generate embeddings
   - Store in Qdrant vector database
5. Updates state file with file hash
6. Commits to git

### Handling File Updates

1. User modifies a file in `backend/knowledge_base/`
2. Manager detects the modification (hash mismatch)
3. Finds existing document record
4. Deletes old embeddings from Qdrant
5. Deletes old chunks from database
6. Deletes document record
7. Re-ingests as new document
8. Updates state file with new hash
9. Commits to git

### Cleaning Up Deleted Files

1. User deletes a file from `backend/knowledge_base/`
2. Manager detects the deletion (file no longer in directory)
3. Finds document record
4. Deletes all related embeddings from Qdrant
5. Deletes all chunks from database
6. Deletes document record
7. Removes file from state file
8. Commits to git

## Error Handling

The manager handles various error conditions:

- **Unreadable files**: Skipped with error logged
- **Database errors**: Logged and rolled back
- **Embedding errors**: Logged, returns error in result
- **Git errors**: Logged but doesn't block ingestion
- **Missing documents**: Files treated as new if document not found during update

All errors are captured in `IngestionResult` objects with detailed messages.

## Configuration

### File Type Support

Modify the `_is_ingestionable_file` method to change supported extensions:

```python
supported_extensions = {
    '.txt', '.md', '.pdf', '.docx', '.doc',
    '.json', '.yaml', '.yml', '.xml', '.html',
    '.py', '.js', '.ts', '.java', '.cpp', '.c',
    # Add more as needed
}
```

### Embedding Configuration

The manager uses the default ingestion service settings:

- Chunk size: 512 characters
- Chunk overlap: 50 characters
- Embedding model: qwen_4b (via `get_embedding_model()`)

### Watch Interval

Default scan interval is 5 seconds. Customize via CLI:

```bash
python -m ingestion.cli watch --interval 10
```

Or in Python:

```python
manager.watch_and_process(continuous=True)
# Modify the sleep(5) in watch_and_process method
```

## Troubleshooting

### Git Not Found

Ensure git is installed and in PATH:

```bash
which git
```

### Files Not Being Detected

Check that:

1. Files are in `backend/knowledge_base` directory
2. File extensions are supported
3. Files aren't prefixed with `.`
4. Run status check: `python -m ingestion.cli status`

### Embeddings Not Stored

Check that:

1. Qdrant vector database is running
2. Embedding model is available
3. Database connections are working
4. Check logs for detailed error messages

### State File Issues

Reset tracking state if issues occur:

```bash
python -m ingestion.cli clear-state --force
python -m ingestion.cli scan
```

## Integration with Existing System

### With FastAPI App

The file ingestion router is automatically registered in `app.py`:

```python
from api.file_ingestion import router as file_ingestion_router
app.include_router(file_ingestion_router)
```

Access endpoints at: `http://localhost:8000/file-ingest/`

### With Ingestion Service

Uses the existing `TextIngestionService`:

- Same chunking strategy
- Same embedding model
- Same vector database (Qdrant)
- Same database (PostgreSQL with SQLAlchemy)

### With Document Model

Integrates with the `Document` and `DocumentChunk` models:

- Creates document records
- Manages chunks
- Tracks embeddings

## Performance Considerations

- **Scan Performance**: Depends on number of files and file sizes
- **Embedding Generation**: Largest bottleneck for large files
- **Git Operations**: Minimal overhead after directory scan
- **State File**: Very small (just file paths and hashes)

## Security Considerations

- **File Access**: Manager runs with same permissions as application
- **Git Commits**: Auto-commits with "Ingestion Manager" user
- **Sensitive Files**: No special handling - ensure knowledge base only contains appropriate files
- **Error Logs**: May contain file paths and contents in error messages

## Future Enhancements

Potential improvements:

- Webhook triggers from git hooks
- Batch file processing optimizations
- Automatic cleanup of orphaned embeddings
- File change history tracking
- Selective re-ingestion of specific files
- Parallel file processing
- Resume interrupted ingestions
