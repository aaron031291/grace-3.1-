# NLP File Descriptions - Making Filesystem No-Code Friendly

## Overview

The NLP File Descriptions system processes all files and folders in your filesystem through Natural Language Processing (NLP) to generate human-readable descriptions. This makes the filesystem accessible to non-technical users who can understand what each file and folder does without reading code.

## Features

- **Automatic Processing**: Processes all files and folders recursively
- **Natural Language Descriptions**: Uses LLM (via Ollama) to generate human-readable descriptions
- **Smart Caching**: Caches descriptions and only regenerates when files change
- **Parallel Processing**: Processes multiple files simultaneously for speed
- **Fallback Support**: Works even when Ollama is unavailable (uses heuristics)
- **Search Capability**: Search descriptions by keyword
- **API Access**: RESTful API for accessing descriptions

## How It Works

1. **File Analysis**: Extracts content from files (text, code, documents)
2. **NLP Processing**: Uses LLM to analyze content and generate descriptions
3. **Description Generation**: Creates:
   - Clear description of what the file/folder is
   - Purpose and usage
   - Key points
   - Technical level (beginner/intermediate/advanced)
   - Related files (for folders)
4. **Storage**: Saves descriptions to `.nlp_descriptions.json` in the root directory

## Usage

### Command Line Script

Process all files and folders:

```bash
# Process entire workspace
python scripts/process_files_nlp.py

# Process specific directory
python scripts/process_files_nlp.py --root-path /path/to/directory

# Force regeneration of all descriptions
python scripts/process_files_nlp.py --force

# Use more parallel workers
python scripts/process_files_nlp.py --max-workers 8
```

### API Endpoints

#### Process All Files

```bash
# Start processing (returns immediately, processes in background)
POST /api/nlp-descriptions/process-all?max_workers=4&force=false

# Check processing status
GET /api/nlp-descriptions/status
```

#### Get File Description

```bash
GET /api/nlp-descriptions/file/{path}

# Example:
GET /api/nlp-descriptions/file/backend/app.py
```

Response:
```json
{
  "path": "backend/app.py",
  "name": "app.py",
  "type": "file",
  "description": "Main FastAPI application file for Grace. Contains the API server setup, routes, and middleware configuration.",
  "purpose": "Serves as the entry point for the Grace API server, handling all HTTP requests and routing.",
  "key_points": [
    "FastAPI application",
    "API routes and endpoints",
    "Middleware configuration",
    "Database initialization"
  ],
  "technical_level": "intermediate",
  "extension": ".py",
  "file_size": 123456,
  "generated_at": "2024-01-15T10:30:00"
}
```

#### Get Folder Description

```bash
GET /api/nlp-descriptions/folder/{path}

# Example:
GET /api/nlp-descriptions/folder/backend/api
```

Response:
```json
{
  "path": "backend/api",
  "name": "api",
  "description": "Contains all API endpoint definitions for the Grace system. Includes routes for file management, ingestion, retrieval, and various system features.",
  "purpose": "Organizes all REST API endpoints into modular routers for different system capabilities.",
  "file_count": 45,
  "folder_count": 0,
  "main_topics": [
    "REST API",
    "File management",
    "Data ingestion",
    "System endpoints"
  ],
  "key_files": [
    "app.py",
    "file_management.py",
    "ingest.py",
    "retrieve.py"
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

#### Search Descriptions

```bash
GET /api/nlp-descriptions/search?query=api

# Returns all files/folders matching the search query
```

#### Get All Descriptions

```bash
GET /api/nlp-descriptions/all

# Returns all cached descriptions as a dictionary
```

#### Process Single File/Folder

```bash
# Process a single file
POST /api/nlp-descriptions/process-file?path=backend/app.py

# Process a single folder
POST /api/nlp-descriptions/process-folder?path=backend/api
```

## Configuration

### Root Directory

By default, the system processes the workspace root (parent of `backend/`). You can specify a different root:

```python
from backend.file_manager.nlp_file_descriptor import NLPFileDescriptor

descriptor = NLPFileDescriptor(
    root_path="/path/to/root",
    ollama_client=ollama_client,
    file_handler=file_handler
)
```

### Skipped Patterns

The following patterns are automatically skipped:
- `.git`, `.venv`, `__pycache__`, `node_modules`
- `.pytest_cache`, `.mypy_cache`, `.idea`, `.vscode`
- `dist`, `build`, `.eggs`
- `*.pyc`, `*.pyo`, `*.pyd`
- `.DS_Store`, `Thumbs.db`

## Storage

Descriptions are stored in `.nlp_descriptions.json` in the root directory. The file structure:

```json
{
  "path/to/file.py": {
    "path": "path/to/file.py",
    "name": "file.py",
    "type": "file",
    "description": "...",
    "purpose": "...",
    "key_points": [...],
    "technical_level": "intermediate",
    "file_hash": "abc123...",
    "generated_at": "2024-01-15T10:30:00"
  },
  "path/to/folder": {
    "path": "path/to/folder",
    "name": "folder",
    "type": "folder",
    "description": "...",
    "purpose": "...",
    "file_count": 10,
    "folder_count": 2,
    "main_topics": [...],
    "key_files": [...],
    "generated_at": "2024-01-15T10:30:00"
  }
}
```

## Requirements

- Python 3.8+
- Ollama (optional, for LLM-powered descriptions)
- File handler for text extraction

## Performance

- **Processing Speed**: ~10-50 files/second (depends on file size and Ollama availability)
- **Cache**: Descriptions are cached and only regenerated when files change (detected via file hash)
- **Parallel Processing**: Configurable number of workers (default: 4)

## Use Cases

1. **Documentation Generation**: Automatically generate documentation for codebases
2. **Onboarding**: Help new team members understand project structure
3. **Code Review**: Quick understanding of files before reviewing
4. **Search**: Find files by natural language description
5. **Non-Technical Users**: Make codebases accessible to non-developers

## Examples

### Example: Processing a Python Project

```bash
python scripts/process_files_nlp.py --root-path /path/to/python/project
```

This will:
1. Scan all Python files, documentation, config files, etc.
2. Generate descriptions like:
   - "Main application entry point. Handles HTTP requests and routes them to appropriate handlers."
   - "Database models for user authentication and session management."
   - "API endpoints for file upload and management."
3. Save all descriptions to `.nlp_descriptions.json`

### Example: Finding Files by Description

```bash
# Search for files related to authentication
GET /api/nlp-descriptions/search?query=authentication

# Returns files with descriptions containing "authentication"
```

## Integration

The system integrates with:
- **File Intelligence Agent**: Uses existing file analysis capabilities
- **Ollama Client**: For LLM-powered descriptions
- **File Handler**: For text extraction from various file types
- **Grace API**: Exposed via REST endpoints

## Troubleshooting

### Ollama Not Running

If Ollama is not running, the system will use fallback heuristics based on:
- File extension
- File name patterns
- Basic content analysis

Descriptions will still be generated but may be less detailed.

### Large Files

Very large files (>10MB) may be truncated for NLP processing. The system uses the first 10,000 characters for analysis.

### Processing Errors

If a file fails to process:
- Check file permissions
- Verify file is not corrupted
- Check logs for specific error messages

## Future Enhancements

- Database storage for descriptions (instead of JSON)
- Incremental updates (only process changed files)
- Multi-language support
- Custom description templates
- Integration with IDE plugins
- Export to documentation formats (Markdown, HTML)
