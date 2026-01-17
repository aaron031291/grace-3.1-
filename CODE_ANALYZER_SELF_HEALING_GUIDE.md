# Code Analyzer Self-Healing Integration
## Automatic Bug Detection and Fixing

This guide explains how the GRACE unified code analyzer integrates with the autonomous healing system to automatically detect and fix code issues.

---

## 🎯 Overview: Self-Healing Code Analysis

The self-healing integration combines:
1. **Code Analyzer** - Detects issues using AST visitor + pattern matching
2. **Fix Applicator** - Applies fixes automatically based on suggested fixes
3. **Autonomous Healing System** - Triggers healing actions based on trust levels
4. **Genesis Key Tracking** - Records all fixes for audit and learning

---

## 🔄 Self-Healing Flow

```
1. Code Analyzer scans codebase
   ↓
2. Issues detected with suggested fixes
   ↓
3. Evaluate which issues can be auto-fixed
   (Based on trust level, severity, confidence)
   ↓
4. Apply fixes automatically (if trust level allows)
   ↓
5. Trigger healing action in autonomous healing system
   ↓
6. Create Genesis keys for tracking
   ↓
7. Learn from fix outcomes
```

---

## 🛠️ How It Works

### Step 1: Code Analysis

The analyzer uses the unified GRACE code analyzer:
- **AST Visitor Pattern** (from Bandit) - Systematic traversal
- **Pattern Matching** (from Semgrep) - Structural pattern detection
- **Context Tracking** - Understands code context

**Example:**
```python
analyzer = GraceCodeAnalyzer()
results = analyzer.analyze_directory('backend')
# Returns: Dict[file_path, List[CodeIssue]]
```

### Step 2: Issue Evaluation

Evaluates which issues can be safely auto-fixed:

**Criteria:**
- ✅ Rule is auto-fixable (has suggested fix)
- ✅ Fix confidence >= 0.8
- ✅ Trust level allows auto-fixing
- ✅ Severity appropriate for trust level

**Trust Level Requirements:**
- **LOW severity** → Requires `LOW_RISK_AUTO` (2+) 
- **MEDIUM severity** → Requires `MEDIUM_RISK_AUTO` (3+)
- **HIGH/CRITICAL** → Requires `HIGH_RISK_AUTO` (4+)

### Step 3: Fix Application

Applies fixes using AST-aware transformations:

**Auto-Fixable Rules:**
- **G006: Print Statement** → Replace with `logger.info()`
- **G007: Bare Except** → Replace with `except Exception:`
- **G012: Missing Logger** → Add logger to class (with caution)
- **SYNTAX_ERROR** → Apply syntax fixes

**Example Fix:**
```python
# Before (G006: Print statement)
print(f"Processing {data}")

# After (Auto-fixed)
logger.info(f"Processing {data}")
```

### Step 4: Healing Action Trigger

Triggers healing action in autonomous healing system:

```python
healing_system.trigger_healing_action(
    action=HealingAction.CODE_FIX,
    details={
        'file': 'backend/api/retrieve.py',
        'issues_fixed': 3,
        'rule_ids': ['G006', 'G007', 'G012']
    },
    trust_required=TrustLevel.MEDIUM_RISK_AUTO
)
```

### Step 5: Genesis Key Tracking

Creates Genesis keys for all analysis and fixes:

- **Analysis Key**: Tracks analysis run, issues found
- **Fix Keys**: Tracks each fix applied, links to analysis key

**Benefits:**
- Complete audit trail
- Learning from fix outcomes
- Track fix success rates
- Identify patterns

---

## 🚀 Usage

### Basic Usage (Script)

```bash
# Run analysis and auto-fix
python scripts/trigger_code_healing.py

# Specify directory
python scripts/trigger_code_healing.py --directory backend/api

# Custom trust level
python scripts/trigger_code_healing.py --trust-level 4

# Dry run (show what would be fixed)
python scripts/trigger_code_healing.py --dry-run

# Analysis only (no auto-fix)
python scripts/trigger_code_healing.py --no-auto-fix
```

### Programmatic Usage

```python
from cognitive.code_analyzer_self_healing import trigger_code_healing
from cognitive.autonomous_healing_system import TrustLevel

# Trigger healing
results = trigger_code_healing(
    directory='backend',
    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
    auto_fix=True
)

print(f"Fixed {results['fixes_applied']} issues")
```

### Integration with CI/CD

```python
# In CI/CD pipeline
from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing

def pre_commit_healing():
    """Run before commit"""
    analyzer_healing = CodeAnalyzerSelfHealing(
        trust_level=TrustLevel.LOW_RISK_AUTO,  # Safe fixes only
        enable_auto_fix=True
    )
    
    results = analyzer_healing.analyze_and_heal(
        directory='.',
        auto_fix=True,
        min_confidence=0.9  # High confidence only
    )
    
    # Fail if critical issues remain
    if results['health_status'] == 'critical':
        return False
    
    return True
```

### Scheduled Healing

```python
# Run on schedule (cron, scheduler)
import schedule

def run_code_healing():
    """Scheduled code healing"""
    results = trigger_code_healing(
        directory='backend',
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        auto_fix=True
    )
    
    # Log results
    logger.info(f"Code healing: {results['fixes_applied']} fixes applied")

# Schedule daily
schedule.every().day.at("02:00").do(run_code_healing)
```

---

## 🔐 Trust Levels & Safety

### Trust Level 0-1: Manual Only
- **No auto-fixing** - Analysis only
- Human review required for all fixes

### Trust Level 2: Low Risk Auto
- ✅ Auto-fix **LOW** severity issues only
- Examples: Print statements, missing docstrings

### Trust Level 3: Medium Risk Auto (Recommended)
- ✅ Auto-fix **LOW + MEDIUM** severity
- Examples: Bare except, missing logger, print statements
- ❌ Skips HIGH/CRITICAL (requires human review)

### Trust Level 4+: High Risk Auto
- ✅ Auto-fix **HIGH** severity issues
- Use with caution - may make significant changes

---

## 📊 Fix Safety & Confidence

### Fix Confidence Levels

**High Confidence (0.9+):**
- Syntax fixes (well-defined)
- Simple replacements (print → logger)
- Standard patterns (bare except → except Exception)

**Medium Confidence (0.7-0.9):**
- Context-dependent fixes
- Requires validation after fix

**Low Confidence (<0.7):**
- Complex fixes requiring human judgment
- Not auto-fixed by default

### Safety Checks

Before applying any fix:
1. ✅ **Syntax Validation** - Verify fixed code parses correctly
2. ✅ **Trust Level Check** - Ensure trust level allows fix
3. ✅ **Confidence Threshold** - Require minimum confidence
4. ✅ **Backup** - Consider creating backup (future enhancement)

---

## 🎓 Learning from Fixes

The system learns from fix outcomes:

1. **Track Fix Success**
   - Which fixes work reliably?
   - Which fixes cause new issues?

2. **Improve Confidence Scores**
   - Increase confidence for successful fixes
   - Decrease confidence for problematic fixes

3. **Pattern Recognition**
   - Identify common fix patterns
   - Learn from human-approved fixes

4. **Adaptive Trust**
   - Increase trust for proven fixes
   - Maintain caution for new patterns

---

## 📈 Example Output

```
======================================================================
GRACE Code Analyzer Self-Healing
======================================================================

Directory: backend
Trust Level: MEDIUM_RISK_AUTO (3)
Auto-Fix: True

======================================================================
RESULTS
======================================================================

Issues found: 134
  Critical: 0
  High: 0
  Medium: 0
  Low: 134

Fixable issues: 45
Fixes applied: 45
Health status: healthy

Files modified:
  [OK] backend/app.py: 12 fixes
  [OK] backend/api/retrieve.py: 8 fixes
  [OK] backend/api/file_ingestion.py: 5 fixes
  [OK] backend/settings.py: 3 fixes

======================================================================
Self-healing triggered successfully!
======================================================================
```

---

## 🔗 Integration Points

### 1. Autonomous Healing System

```python
# Triggers healing actions
healing_system.trigger_healing_action(
    action=HealingAction.CODE_FIX,
    details={...},
    trust_required=TrustLevel.MEDIUM_RISK_AUTO
)
```

### 2. Genesis Key System

```python
# Tracks all fixes
genesis_service.create_genesis_key(
    key_type=GenesisKeyType.CODE_CHANGE,
    action="auto_code_fix",
    file_path=file_path,
    details={...}
)
```

### 3. Learning System

```python
# Learn from fix outcomes
# (Future integration)
learning_system.record_fix_outcome(
    rule_id='G006',
    success=True,
    outcome='Fixed print statement'
)
```

---

## 🎯 Best Practices

### 1. Start Conservative

```python
# Start with low trust level
trigger_code_healing(
    trust_level=TrustLevel.LOW_RISK_AUTO,  # Safe fixes only
    auto_fix=True
)
```

### 2. Review Before Production

- Always review fixes before merging
- Use dry-run mode to preview changes
- Start with specific directories

### 3. Monitor Fix Outcomes

- Track Genesis keys for fix history
- Monitor for new issues after fixes
- Adjust confidence scores based on outcomes

### 4. Incremental Trust

- Start with LOW_RISK_AUTO
- Gradually increase trust as system proves itself
- Keep HIGH/CRITICAL fixes for manual review

---

## 🔮 Future Enhancements

### Short Term:
- ✅ Basic auto-fixing (current)
- ⏳ More fix patterns
- ⏳ Fix validation testing

### Medium Term:
- ⏳ AST transformation for complex fixes (pytest-style)
- ⏳ Fix rollback on failure
- ⏳ Learning from fix outcomes

### Long Term:
- ⏳ AI-powered fix generation
- ⏳ Multi-file fix coordination
- ⏳ Fix impact analysis

---

## 📚 Related Documentation

- **Code Analyzer**: `backend/cognitive/grace_code_analyzer.py`
- **Healing System**: `backend/cognitive/autonomous_healing_system.py`
- **Self-Healing Integration**: `backend/cognitive/code_analyzer_self_healing.py`
- **Trigger Script**: `scripts/trigger_code_healing.py`

---

**Last Updated:** 2026-01-16
