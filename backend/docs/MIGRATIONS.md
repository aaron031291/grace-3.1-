# GRACE Database Migration Guide

This guide explains how to run database migrations for the GRACE project.

## Quick Start

### On Windows:

Double-click `run_migrations.bat` in the `backend` folder, or run:

```cmd
run_migrations.bat
```

### On Linux/macOS:

Run the shell script:

```bash
./run_migrations.sh
```

Or run the Python script directly:

```bash
python run_all_migrations.py
```

## What Gets Migrated

The migration script runs the following steps in order:

1. **Base Tables** - Creates all database tables from SQLAlchemy models

   - Users, Conversations, Messages, Embeddings
   - Chats, ChatHistory, Documents, DocumentChunks

2. **Metadata Columns** - Adds metadata fields to the documents table

   - File metadata, extraction details
   - Processing information

3. **Folder Path** - Adds folder_path column to track document locations

   - Enables folder-specific organization
   - Supports document hierarchy

4. **Confidence Scoring** - Adds confidence scoring columns

   - Trust scores for information retrieval
   - Semantic contradiction detection
   - Weighted confidence metrics

5. **Database Verification** - Validates the database setup
   - Checks connection
   - Lists all tables and columns

## Prerequisites

- **Python 3.10+** installed and added to PATH
- **SQLite** (included with Python)
- Database file will be created at `backend/data/grace.db`

## Manual Migration (If Needed)

If you need to run individual migrations:

### Create Base Tables:

```bash
python -c "from database.migration import create_tables; create_tables()"
```

### Add Metadata Columns:

```bash
python migrate_add_metadata_columns.py
```

### Add Folder Path:

```bash
python migrate_add_folder_path.py
```

### Add Confidence Scoring:

```bash
python -c "from database.migrate_add_confidence_scoring import migrate; migrate()"
```

## Troubleshooting

### "Python is not installed"

- Install Python 3.10+ from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation
- Restart your terminal after installation

### "Database is locked"

- Close any other applications using the database
- Make sure no other instances of the app are running
- Delete `data/grace.db` and rerun migrations if corrupted

### "Column already exists"

- This is normal - migrations are idempotent and safe to run multiple times
- If a column exists, it will skip and continue

### "Permission denied" (Linux/macOS)

Make the script executable first:

```bash
chmod +x run_migrations.sh
./run_migrations.sh
```

## Migration Status

After running migrations, you should see output like:

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

## Files Included

- `run_all_migrations.py` - Main Python migration orchestrator
- `run_migrations.bat` - Windows batch script
- `run_migrations.sh` - Linux/macOS shell script
- `database/migration.py` - Core migration utilities
- `migrate_add_metadata_columns.py` - Metadata migration
- `migrate_add_folder_path.py` - Folder path migration
- `database/migrate_add_confidence_scoring.py` - Confidence scoring migration

## After Migration

Your database is now ready for use. The GRACE application will automatically:

- Use the created tables
- Store conversations and chat history
- Process documents with metadata
- Track folder locations
- Calculate confidence scores

If you need to reset the database:

```bash
python clear_all_data.py
```

Then run migrations again:

```bash
# Windows
run_migrations.bat

# Linux/macOS
./run_migrations.sh
```

## Support

For issues or questions about migrations, check the logs in the console output or contact the development team.
