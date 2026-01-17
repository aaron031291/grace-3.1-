# Qdrant Setup Instructions

## Status: ⚠️ REQUIRES DOCKER DESKTOP

Qdrant is not running because Docker Desktop is not started.

## Quick Fix

1. **Start Docker Desktop**:
   - Open Docker Desktop application
   - Wait for it to fully start (Docker icon in system tray should be green)

2. **Start Qdrant**:
   ```bash
   python scripts/start_qdrant.py
   ```

3. **Verify**:
   ```bash
   curl http://localhost:6333/health
   # Expected: {"status": "ok"}
   ```

## Manual Start (Alternative)

If the script doesn't work, start Qdrant manually:

```bash
# Check if container exists
docker ps -a | findstr qdrant

# If exists, start it
docker start qdrant

# If doesn't exist, create it
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

## After Starting

Once Qdrant is running, the backend will automatically connect to it on next health check.
