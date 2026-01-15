# Scripts Directory

This directory contains utility and management scripts for the Grace system.

## Scripts

### Grace Management Scripts

- **`check_grace_status.py`** - Check if Grace's self-healing agent is running and show status
- **`restart_grace.py`** - Restart Grace's self-healing agent (interactive)
- **`restart_grace_auto.py`** - Automatically restart Grace's self-healing agent
- **`start_self_healing_background.py`** - Start Grace's self-healing agent in background mode
- **`show_grace_fixes.py`** - Show what Grace has fixed (queries database)
- **`verify_grace_fixes.py`** - Verify that Grace's fixes are working correctly

### Setup & Configuration

- **`fix_phase2_setup.py`** - Create missing database tables for Phase 2

### Knowledge Ingestion

- **`trigger_grace_self_healing_ingestion.py`** - Trigger Grace to ingest knowledge needed for self-healing

### Testing Scripts

- **`test_complete_file_intelligence.py`** - Complete end-to-end file intelligence test
- **`test_grace_file_intelligence.py`** - Test Grace file intelligence system
- **`test_phase2_adaptive_learning.py`** - Test Phase 2 adaptive learning components

## Usage

All scripts should be run from the repository root directory:

```bash
# From repo root
python scripts/check_grace_status.py
python scripts/start_self_healing_background.py
```

## Notes

- Scripts automatically resolve paths relative to the repository root
- Log files are written to `logs/` directory in the repo root
- Database files are expected in `data/` directory in the repo root
