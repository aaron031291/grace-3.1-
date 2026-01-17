# Code Analyzer Self-Healing - Startup Integration

## ✅ Boot Integration Complete

The code analyzer self-healing system is now **integrated into GRACE's startup sequence** and will automatically run on boot.

---

## 🚀 What Happens on Boot

### 1. **Initialization**
- Code analyzer self-healing system initializes in background
- Connected to autonomous healing system
- Timesense integration enabled for time estimation

### 2. **Pre-Flight Analysis**
- Runs code analysis in **pre-flight mode** (analysis only, no auto-fix)
- Scans entire `backend` directory
- Identifies all code issues
- Evaluates which issues are auto-fixable
- Estimates fix times using Timesense

### 3. **Boot Results**
- Issues found count
- Fixable issues count
- Health status
- Timesense statistics (if enabled)

### 4. **Approval Required**
- All fixes prepared for **manual approval**
- No automatic fixes on boot
- Use API endpoints or scripts to apply fixes after review

---

## 📊 Boot Sequence

```
1. Database initialization
   ↓
2. Self-healing system initialization
   ↓
3. Code analyzer self-healing initialization
   ↓
4. Pre-flight code analysis (background)
   ↓
5. Results logged to console
   ↓
6. System ready (fixes await approval)
```

---

## 🔍 Boot Output Example

```
[CODE-ANALYZER-HEALING] Initializing code analyzer self-healing...
[CODE-ANALYZER-HEALING] Code analyzer self-healing initialized
[CODE-ANALYZER-HEALING] Mode: Pre-flight (analysis on boot, fixes require approval)

[CODE-ANALYZER-HEALING] Running initial code analysis (pre-flight)...
[CODE-ANALYZER-HEALING] Initial analysis complete: Issues=134, Fixable=46, Health=healthy, Timesense=True

[CODE-ANALYZER-HEALING] Note: 46 issues ready for approval. 
Use /grace/code-healing/apply to review and apply fixes.
```

---

## 🎯 Configuration

### Boot Mode Settings
- **Pre-flight mode**: `True` (default on boot)
- **Auto-fix**: `False` (requires approval)
- **Timesense**: `True` (enabled)
- **Trust level**: `MEDIUM_RISK_AUTO`

### Location in Code
**File**: `backend/app.py`
**Function**: `lifespan()` → `initialize_self_healing_background()`
**Line**: ~299-315

---

## 🔄 Applying Fixes After Boot

### Option 1: API Endpoint (Future)
```bash
POST /grace/code-healing/apply
```

### Option 2: Script
```bash
python scripts/trigger_code_healing.py --auto-fix
```

### Option 3: Programmatic
```python
from cognitive.code_analyzer_self_healing import trigger_code_healing

results = trigger_code_healing(
    directory='backend',
    auto_fix=True,  # Enable auto-fix
    pre_flight=False  # Apply fixes
)
```

---

## ⚙️ Background Monitoring

The code analyzer self-healing runs:
- **On boot**: Pre-flight analysis (one-time)
- **On demand**: Via API/scripts
- **Scheduled**: Can be added to cron/scheduler

Future enhancement: Add periodic code analysis in background thread (similar to health monitoring).

---

## 🛡️ Safety Features

1. **Pre-flight Mode on Boot**
   - Analysis only, no automatic fixes
   - All fixes require manual approval

2. **Trust Level Based**
   - Respects trust level settings
   - Only safe fixes at configured level

3. **Timesense Integration**
   - Time estimation for fixes
   - Time-based prioritization
   - Performance tracking

4. **Error Handling**
   - Graceful degradation if initialization fails
   - Warnings logged, system continues

---

## 📚 Related Files

- **Startup Code**: `backend/app.py` (lines ~299-315)
- **Self-Healing Integration**: `backend/cognitive/code_analyzer_self_healing.py`
- **Trigger Script**: `scripts/trigger_code_healing.py`
- **Live Demo**: `scripts/live_healing_demo.py`

---

## ✅ Status

- ✅ Startup integration complete
- ✅ Pre-flight mode on boot
- ✅ Timesense integration enabled
- ✅ Background initialization (non-blocking)
- ✅ Error handling added
- ✅ Boot analysis logging

**The code analyzer self-healing system now starts automatically on boot!**

---

**Last Updated:** 2026-01-16
