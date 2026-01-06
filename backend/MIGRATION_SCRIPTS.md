# Migration Scripts Summary

Three migration scripts have been created to handle all database migrations for the GRACE project. Choose the one that matches your operating system.

## Files Created

### 1. `run_all_migrations.py` (Core Script - All Platforms)
The main Python migration orchestrator that:
- Initializes the database connection
- Runs all migrations in correct order
- Verifies the database schema
- Provides detailed logging and error handling
- Works on Windows, Linux, and macOS

**Usage:**
```bash
python run_all_migrations.py
# or
python3 run_all_migrations.py
```

### 2. `run_migrations.bat` (Windows Only)
Windows batch file that wraps the Python script with:
- Python availability check
- Automatic pause to show output
- Colored status indicators
- Windows-friendly file paths

**Usage:**
- Double-click the file in File Explorer, OR
- Run from command prompt: `run_migrations.bat`

### 3. `run_migrations.sh` (Linux/macOS Only)
Shell script that wraps the Python script with:
- Python availability check
- Exit code handling
- Standard Unix conventions

**Usage:**
```bash
./run_migrations.sh
# or
bash run_migrations.sh
```

## What Gets Migrated

The migration script handles:

1. **Base Tables** - SQLAlchemy model creation
   - users, conversations, messages, embeddings
   - chats, chat_history, documents, document_chunks

2. **Metadata Columns** - Document metadata fields
   - upload_method, trust_score, description, tags
   - document_metadata, and indexes

3. **Folder Path** - Document organization
   - folder_path column for tracking locations

4. **Confidence Scoring** - Semantic analysis
   - Confidence scoring columns (if available)

5. **Verification** - Database health check
   - Connection test, table count, column listing

## Quick Start

### Windows
```bash
cd backend
run_migrations.bat
```

### Linux/macOS
```bash
cd backend
./run_migrations.sh
```

### Any Platform (Direct Python)
```bash
cd backend
python run_all_migrations.py
```

## Expected Output

```
════════════════════════════════════════════════════════════
MIGRATION SUMMARY
════════════════════════════════════════════════════════════
✓ PASSED: Base Tables
✓ PASSED: Metadata Columns
✓ PASSED: Folder Path
✓ PASSED: Confidence Scoring
✓ PASSED: Database Verification
════════════════════════════════════════════════════════════

✓ All migrations completed successfully!
```

## Features

✅ **Idempotent** - Safe to run multiple times
✅ **Detailed Logging** - Clear status messages
✅ **Error Handling** - Graceful failure recovery
✅ **Cross-Platform** - Works on Windows, Linux, macOS
✅ **Automatic** - No manual configuration needed
✅ **Fast** - Completes in seconds
✅ **Verified** - Final schema validation

## Troubleshooting

**"Python not found"**
- Install Python 3.10+ from python.org
- Add Python to your system PATH
- Restart your terminal

**"Permission denied" (Linux/macOS)**
- Run: `chmod +x run_migrations.sh`

**"Database locked"**
- Close other applications using the database
- Delete `data/grace.db` and re-run if corrupted

**Safe to run multiple times?**
- Yes! Migrations are idempotent and skip existing columns/tables

## Documentation

For more detailed information, see `MIGRATIONS.md` in the backend folder.

## Support

All three scripts do the same thing - choose based on your platform:
- Windows users → `run_migrations.bat`
- Linux/macOS users → `run_migrations.sh`
- Any platform → `python run_all_migrations.py`
