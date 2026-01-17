# GRACE 3.1 Startup Issues Resolution Guide

## Overview

GRACE 3.1 is designed with **graceful degradation** - it should start and operate even when optional services (embedding model, Qdrant, Ollama) are unavailable. Recent improvements have enhanced this capability.

---

## ✅ What's Already Fixed

### 1. **Graceful Degradation System**
- ✅ Health checks return `"degraded"` instead of `"unhealthy"` for missing optional services
- ✅ Launcher accepts `DEGRADED` status as acceptable for startup
- ✅ System continues operating with limited capabilities when services are missing
- ✅ Self-healing system is active even in degraded mode

### 2. **Database Error Handling**
- ✅ Database errors are now automatically logged as Genesis Keys
- ✅ Self-healing can detect and create missing database tables automatically
- ✅ `DATABASE_TABLE_CREATE` healing action implemented

### 3. **Character Encoding**
- ✅ Unicode characters replaced with ASCII in print statements
- ✅ Windows console compatibility improved

---

## 🔧 Remaining Issues & Solutions

### Issue 1: Missing Embedding Model

**Status**: ✅ **Handled Gracefully** - Model is lazy-loaded

**What Happens:**
- System starts without the embedding model
- Model downloads automatically on first use
- File ingestion unavailable until model is ready

**Manual Solution** (if you want model pre-loaded):
```bash
# The model will download automatically when first needed
# OR manually download using:
cd backend
python -c "from embedding.embedder import get_embedding_model; get_embedding_model()"
```

**Expected Behavior:**
- ✅ System starts with `"degraded"` status
- ✅ Core API available
- ✅ Embedding operations unavailable until model loads
- ✅ Self-healing monitors and will report when model becomes available

---

### Issue 2: Qdrant Vector Database Not Running

**Status**: ⚠️ **Optional Service** - Should not prevent startup

**What Should Happen:**
- System starts with degraded status
- Document search/similarity unavailable
- Core functionality remains available

**Solution - Start Qdrant:**

**Option A: Docker (Recommended)**
```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Option B: Download Qdrant Binary**
1. Download from: https://github.com/qdrant/qdrant/releases
2. Extract and run: `qdrant.exe` (Windows) or `./qdrant` (Linux/Mac)
3. Service starts on `http://localhost:6333`

**Option C: Skip Qdrant (Degraded Mode)**
- System will start without Qdrant
- RAG/search features unavailable
- Core API and chat features still work

---

### Issue 3: Ollama Not Running

**Status**: ✅ **Optional Service** - Already handled

**What Happens:**
- System starts normally
- Chat endpoints return 503 when Ollama is unavailable
- Health check shows `"degraded"` status

**Solution - Install & Start Ollama:**

1. **Install Ollama:**
   - Windows: Download from https://ollama.ai/download
   - Or: `winget install Ollama.Ollama`

2. **Start Ollama Service:**
   ```bash
   ollama serve
   ```

3. **Pull Required Models** (optional, downloads on first use):
   ```bash
   ollama pull mistral:7b
   ollama pull qwen2.5:7b
   ```

**Expected Behavior:**
- ✅ System starts successfully
- ⚠️ Health check shows `"degraded"` if Ollama not running
- ✅ Chat endpoints handle missing Ollama gracefully

---

### Issue 4: Character Encoding

**Status**: ✅ **Fixed** - ASCII characters used in print statements

**Remaining Issue**: Some log messages may still contain Unicode

**Solution**: Set console encoding:
```powershell
# In PowerShell:
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Or set environment variable:
$env:PYTHONIOENCODING = "utf-8"
```

---

## 🚀 Quick Start Guide

### Minimal Setup (Degraded Mode - Everything Optional)
```bash
# 1. Start backend only (no external services needed)
python launch_grace.py

# System will start in DEGRADED mode:
# ✅ Core API available at http://localhost:8000
# ✅ Database operations work
# ✅ Self-healing active
# ❌ Embedding operations unavailable
# ❌ Vector search unavailable
# ❌ LLM chat unavailable
```

### Full Setup (All Services)
```bash
# 1. Start Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant

# 2. Start Ollama (if not running as service)
ollama serve

# 3. Launch GRACE
python launch_grace.py

# System will start in FULL mode:
# ✅ All services available
# ✅ Full functionality enabled
```

---

## 🔍 Verifying System Status

### Check Health:
```bash
curl http://localhost:8000/health
```

**Expected Response (Degraded Mode):**
```json
{
  "status": "degraded",
  "details": {
    "embedding": "not_loaded",
    "qdrant": "unavailable",
    "ollama": "not_running"
  }
}
```

**Expected Response (Full Mode):**
```json
{
  "status": "healthy",
  "details": {
    "embedding": "loaded",
    "qdrant": "connected",
    "ollama": "running"
  }
}
```

### Check API Documentation:
- Open: http://localhost:8000/docs
- All endpoints should be accessible
- Endpoints requiring services will return appropriate errors

---

## 🛠️ Troubleshooting

### System Still Failing to Start?

1. **Check for Fatal Errors** (shouldn't happen):
   - Database connection failures
   - Port conflicts (8000 already in use)
   - Python version incompatibility

2. **Check Logs**:
   ```bash
   # Look for FATAL or CRITICAL errors
   tail -n 100 backend/logs/grace_background.log
   ```

3. **Verify Graceful Degradation**:
   - Health check should return `"degraded"` not `"unhealthy"`
   - System should not shutdown on missing optional services

### Self-Healing Not Working?

The enhanced self-healing system should:
- ✅ Detect missing database tables → Create them
- ✅ Detect service connection failures → Log as Genesis Keys
- ✅ Monitor health continuously → Report issues
- ✅ Learn from failures → Improve detection

**If self-healing isn't detecting issues:**
- Check that Genesis Keys are being created for errors
- Verify `autonomous_healing_system` is running
- Check logs: `backend/logs/grace_self_healing.log`

---

## 📊 Service Dependency Matrix

| Service | Required? | Impact if Missing | Auto-Fix Available? |
|---------|-----------|-------------------|---------------------|
| **Database** | ✅ Yes | ❌ System cannot start | ✅ Self-healing creates tables |
| **FastAPI Backend** | ✅ Yes | ❌ System cannot start | ❌ Manual fix required |
| **Embedding Model** | ⚠️ Optional | ⚠️ File ingestion unavailable | ✅ Auto-downloads on use |
| **Qdrant** | ⚠️ Optional | ⚠️ Vector search unavailable | ❌ Manual setup required |
| **Ollama** | ⚠️ Optional | ⚠️ LLM chat unavailable | ❌ Manual setup required |

---

## 🎯 Expected Behavior Summary

### ✅ CORRECT Behavior (After Fixes):
1. System starts even with missing optional services
2. Health status shows `"degraded"` (not `"unhealthy"`)
3. Core API available and functional
4. Missing services reported but don't block startup
5. Self-healing active and monitoring

### ❌ INCORRECT Behavior (Shouldn't Happen):
1. ❌ System shuts down due to missing optional services
2. ❌ Health check fails completely
3. ❌ Core API unavailable
4. ❌ Fatal errors for missing embedding model/Qdrant/Ollama

---

## 🔄 Migration Path

### From Degraded → Full Mode:

1. **Start Qdrant:**
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. **Start Ollama:**
   ```bash
   ollama serve
   ```

3. **Trigger Embedding Model Download:**
   ```bash
   # Model downloads on first embedding operation
   curl -X POST http://localhost:8000/api/ingest \
     -F "file=@test.txt"
   ```

4. **Restart GRACE:**
   ```bash
   python launch_grace.py
   ```

5. **Verify Full Mode:**
   ```bash
   curl http://localhost:8000/health
   # Should show "healthy" status
   ```

---

## 📝 Notes

- **Graceful Degradation**: GRACE is designed to operate with reduced capabilities when services are unavailable
- **Self-Healing**: Active monitoring and automatic issue detection/repair
- **Lazy Loading**: Services initialize when needed, not at startup
- **Health Checks**: Non-fatal for optional services

---

## 🆘 If Issues Persist

If the system is still failing to start with these fixes:

1. Check for actual fatal errors (database, port conflicts)
2. Verify recent code changes are deployed
3. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
4. Check launcher logs for specific failure points
5. Review `backend/logs/grace_background.log` for detailed errors

The system should **never** fail to start due to missing optional services after these improvements.