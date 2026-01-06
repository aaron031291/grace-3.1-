# Database Migration - Quick Reference

## TL;DR

### Windows
```cmd
cd backend
run_migrations.bat
```

### Linux/macOS  
```bash
cd backend
./run_migrations.sh
```

### Any OS (Direct Python)
```bash
cd backend
python run_all_migrations.py
```

## What It Does

Creates and migrates your database with:
- ✅ 8 tables (users, conversations, chats, documents, embeddings, etc.)
- ✅ 25 columns in documents table
- ✅ Metadata and folder tracking
- ✅ Full schema validation

## Success Looks Like

```
✓ PASSED: Base Tables
✓ PASSED: Metadata Columns
✓ PASSED: Folder Path
✓ PASSED: Confidence Scoring
✓ PASSED: Database Verification

✓ All migrations completed successfully!
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Python not found" | Install Python 3.10+ and add to PATH |
| "Permission denied" | Run `chmod +x run_migrations.sh` |
| "Database locked" | Close other apps, or `rm data/grace.db` and rerun |
| Batch file won't run | Use `python run_all_migrations.py` instead |

## Files

| File | Purpose | Platform |
|------|---------|----------|
| `run_all_migrations.py` | Main script | All |
| `run_migrations.bat` | Wrapper script | Windows |
| `run_migrations.sh` | Wrapper script | Linux/macOS |
| `MIGRATIONS.md` | Full documentation | All |
| `MIGRATION_SCRIPTS.md` | Scripts guide | All |

## Run Multiple Times?

Yes, it's completely safe! Migrations are idempotent and will:
- Skip existing tables
- Skip existing columns
- Update indexes as needed
- Work perfectly on fresh or existing databases

## Need Help?

Check these files for more info:
- `MIGRATIONS.md` - Full migration guide
- `MIGRATION_SCRIPTS.md` - Scripts overview
- `database/migration.py` - Core migration code
