# Database Migration Scripts

This directory contains all scripts needed to set up and migrate the GRACE database.

## Quick Start

### For Windows Users
```cmd
run_migrations.bat
```

### For Linux/macOS Users
```bash
./run_migrations.sh
```

### For Any Platform
```bash
python run_all_migrations.py
```

## What These Scripts Do

These scripts automatically:
1. ✅ Initialize the database connection
2. ✅ Create all required tables (8 total)
3. ✅ Add metadata columns to documents
4. ✅ Add folder path tracking
5. ✅ Add confidence scoring columns
6. ✅ Verify the database schema
7. ✅ List all tables and columns

## Files Included

| File | Purpose | Platform |
|------|---------|----------|
| `run_all_migrations.py` | Main Python migration script | Windows, Linux, macOS |
| `run_migrations.bat` | Windows batch wrapper | Windows only |
| `run_migrations.sh` | Linux/macOS shell wrapper | Linux/macOS only |
| `MIGRATIONS.md` | Detailed migration guide | All platforms |
| `MIGRATION_SCRIPTS.md` | Scripts documentation | All platforms |
| `MIGRATION_QUICK_REFERENCE.md` | Quick reference | All platforms |

## Prerequisites

- **Python 3.10+** installed and in PATH
- **SQLite** (included with Python)
- About 1 minute to complete

## Success Indicators

After running, you should see:
```
✓ PASSED: Base Tables
✓ PASSED: Metadata Columns
✓ PASSED: Folder Path
✓ PASSED: Confidence Scoring
✓ PASSED: Database Verification

✓ All migrations completed successfully!

Your database is ready for use.
```

## Database Location

The database is created at:
```
backend/data/grace.db
```

## Tables Created

- `users` - User accounts and profiles
- `conversations` - Chat conversation records
- `messages` - Individual chat messages
- `chats` - Chat session data
- `chat_history` - Chat history tracking
- `documents` - Uploaded documents metadata
- `document_chunks` - Document chunks for RAG retrieval
- `embeddings` - Vector embeddings for semantic search

## Idempotent & Safe

These scripts are **safe to run multiple times**:
- ✅ Won't create duplicate tables
- ✅ Won't recreate existing columns
- ✅ Will skip already migrated columns
- ✅ Perfect for fresh installs or updates

## Troubleshooting

### Python not found
- Install Python 3.10+ from https://www.python.org/downloads/
- Ensure it's added to your system PATH
- Restart your terminal

### Windows: Batch file won't run
- Try: `python run_all_migrations.py` instead
- Or open PowerShell and run: `run_migrations.bat`

### Linux/macOS: Permission denied
- Run: `chmod +x run_migrations.sh`
- Then: `./run_migrations.sh`

### Database locked
- Close any other applications using the database
- Stop the application if it's running
- If corrupted: `rm data/grace.db` then rerun migrations

## Manual Migration

If needed, you can run individual migration steps:

```bash
# Initialize database
python -c "from database.config import DatabaseConfig; from database.connection import DatabaseConnection; DatabaseConnection.initialize(DatabaseConfig()); from database.migration import create_tables; create_tables()"

# Add metadata columns
python migrate_add_metadata_columns.py

# Add folder path
python migrate_add_folder_path.py

# Add confidence scoring
python -c "from database.migrate_add_confidence_scoring import migrate; migrate()"
```

## Full Documentation

For complete documentation, see:
- **Setup Guide**: `../SETUP_GUIDE.md` - Complete project setup
- **Migration Guide**: `MIGRATIONS.md` - Detailed migration docs
- **Scripts Guide**: `MIGRATION_SCRIPTS.md` - Script documentation
- **Quick Reference**: `MIGRATION_QUICK_REFERENCE.md` - Quick reference

## Integration with GRACE

After running migrations:

1. **Backend** starts automatically with database
   ```bash
   python app.py
   ```

2. **Frontend** uses backend API
   ```bash
   npm run dev
   ```

3. **Database** is ready for use
   - All tables created
   - All columns added
   - Schema validated

## Next Steps

1. ✅ Run migrations (this script)
2. ✅ Start backend: `python app.py`
3. ✅ Start frontend: `npm run dev`
4. ✅ Access at: http://localhost:5174

## Support

- For issues, check the detailed guides referenced above
- For errors, review the console output - it's very descriptive
- All migrations log exactly what they're doing

---

**Ready to migrate? Run the appropriate script for your platform!** 🚀
