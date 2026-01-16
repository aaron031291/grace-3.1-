# Grace Launcher

**Minimal, strict launcher with no business logic.**

## Philosophy

The launcher is **dumb by design**:

- **No business logic** - Just spawns processes and checks health
- **No cognition** - Doesn't think, just validates
- **No configuration beyond paths** - Only needs to know where things are
- **Fail fast** - If anything is wrong, refuse to start
- **No orphan processes** - Hard PID ownership, everything gets cleaned up

**Think: BIOS, not OS.**

## Features

### Strict Health Checks

- **Backend up ≠ backend healthy** - Verifies actual functionality
- **Embeddings loaded ≠ embeddings compatible** - Checks version and dimensions
- **IDE bridge running ≠ protocol version match** - Validates protocol compatibility

All checks are strict: **fail fast or don't start**. Silent partial boot is poison.

### Version Handshake

Performs version handshake between:
- Launcher ↔ Backend
- Launcher ↔ Embeddings
- Launcher ↔ IDE bridge

If versions mismatch, **refuse to run**. This saves you from "it worked yesterday" hell.

### Folder Contract Validation

- Folders are editable, but schemas are NOT optional
- If a folder breaks the contract, Grace flags it—not crashes quietly
- Validates:
  - `backend/` - Must exist, must have `app.py`
  - `knowledge_base/` - Must exist, must be directory
  - `data/` - Should exist (warning if missing)

### Process Management

- One parent process spawning children with **hard PID ownership**
- **No orphan processes. Ever.**
- Graceful shutdown on SIGINT/SIGTERM
- Monitors processes and shuts down if they die unexpectedly

## Usage

### Basic Launch

```bash
python launch_grace.py
```

### Programmatic Usage

```python
from pathlib import Path
from launcher import GraceLauncher

launcher = GraceLauncher(root_path=Path.cwd())
launcher.launch()
launcher.run()  # Keep alive
```

## Architecture

```
launcher/
├── __init__.py          # Package exports
├── launcher.py          # Main launcher (process management)
├── version.py           # Version handshake system
├── health_checker.py    # Strict health validation
├── folder_validator.py  # Folder contract validation
├── versions.json        # Version manifest
└── README.md           # This file
```

## Version Handshake

The launcher performs version handshakes using:

1. **Version manifest** (`launcher/versions.json`) - Defines required protocol versions
2. **Backend `/version` endpoint** - Backend reports its version
3. **Protocol compatibility check** - Verifies protocol versions match

If any component's protocol version doesn't match requirements, launch fails immediately.

## Health Checks

Health checks verify:

1. **Backend process** - Is the process running?
2. **Backend health** - Is it actually healthy? (database, services, etc.)
3. **Embeddings loaded** - Are embeddings loaded?
4. **Embeddings compatible** - Are they the right version/dimension?
5. **Version endpoint** - Can we perform version handshake?

All checks are retried up to 3 times with exponential backoff.

## Folder Contracts

### `backend/`
- **Must exist** - Error if missing
- **Must be directory** - Error if not
- **Must contain `app.py`** - Error if missing

### `knowledge_base/`
- **Must exist** - Error if missing
- **Must be directory** - Error if not
- **Should contain content** - Warning if empty
- **No system files in root** - Error if found

### `data/`
- **Should exist** - Warning if missing (system creates if needed)
- **Must be directory if exists** - Error if not

## Exit Codes

- `0` - Launch successful
- `1` - Launch failed (validation error, health check failure, etc.)

## What This Enables (Strategically)

### True Drop-in Cognition Upgrades

Swap out the backend, embeddings, or IDE bridge without changing the launcher.

### Multiple Backends

Run different backend configurations (local/remote/sandbox) behind the same launcher.

### Grace-as-a-Product

A stable launcher that stays the same for years while everything else evolves weekly.

### Future Vision

- `grace.exe` stays the same for years
- Everything else evolves weekly
- Launcher remains trivial to users
- Brutally disciplined under the hood
- Scales without architectural regret

## Dependencies

The launcher requires:
- Python 3.8+
- `requests` (for health checks)

All other dependencies are optional and loaded by the backend.

## Troubleshooting

### "Version mismatch" error

Update `launcher/versions.json` to match your backend/embeddings versions, or update the components to match the launcher requirements.

### "Health check failed" error

Check the backend logs. The launcher will show which specific health check failed. Common issues:
- Database not accessible
- Embeddings not loaded
- Backend services not initialized

### "Folder contract validation failed" error

Fix the folder structure:
- Ensure `backend/` exists with `app.py`
- Ensure `knowledge_base/` exists as a directory
- Remove any system files from `knowledge_base/` root

## Design Principles

1. **Dumb by design** - No intelligence, just validation
2. **Fail fast** - Don't start in a broken state
3. **No orphans** - Every process is tracked and cleaned up
4. **Version strict** - Mismatches are fatal
5. **Contract validation** - Folders must meet schemas

These principles ensure the launcher remains simple, reliable, and maintainable.
