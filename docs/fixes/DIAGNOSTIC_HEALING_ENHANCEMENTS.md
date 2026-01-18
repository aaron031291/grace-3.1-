# Diagnostic Engine & Self-Healing Enhancements

**Date:** 2025-01-27  
**Purpose:** Enhanced diagnostic engine and self-healing system to automatically detect and fix Pydantic logger issues and other code problems.

---

## Enhancements Made

### 1. Proactive Code Scanner (`backend/diagnostic_machine/proactive_code_scanner.py`)

**Added:** `_scan_pydantic_logger_issues()` method
- Scans all Python files for logger definitions inside Pydantic BaseModel classes
- Detects logger attributes without ClassVar annotation
- Returns issues with severity "high"

**Added:** `scan_pydantic_logger_issues()` public method
- Public interface for scanning Pydantic logger issues
- Returns filtered list of Pydantic logger issues

### 2. Automatic Bug Fixer (`backend/diagnostic_machine/automatic_bug_fixer.py`)

**Added:** `_fix_pydantic_logger()` method
- Automatically fixes logger definitions in Pydantic BaseModel classes
- Moves logger from class to module level
- Adds logger import if missing
- Creates backups before fixing

**Enhanced:** `fix_issue()` method
- Added handling for `pydantic_logger` issue type
- Falls back to DeepSeek AI if pattern-based fix fails

### 3. Diagnostic Engine (`backend/diagnostic_machine/diagnostic_engine.py`)

**Enhanced:** `run_proactive_scan()` method
- Now scans for Pydantic logger issues during proactive scans
- Auto-heals Pydantic logger issues if `auto_heal=True`
- Reports Pydantic logger issues in scan results

### 4. Autonomous Healing System (`backend/cognitive/autonomous_healing_system.py`)

**Enhanced:** `assess_system_health()` method
- Now includes Pydantic logger issues in health assessment
- Scans for Pydantic logger issues alongside other code issues
- Converts Pydantic issues to standard code issue format

### 5. Test Script (`scripts/run_e2e_with_healing.py`)

**Fixed:** Diagnostic cycle method call
- Changed `run_diagnostic_cycle()` to `run_cycle()` (correct method name)
- Improved error handling and result reporting

### 6. Code Fixes Applied

**Fixed:** `backend/genesis/code_analyzer.py`
- Moved logger from inside CodeIssue dataclass to module level

**Fixed:** `backend/cognitive/healing_knowledge_base.py`
- Fixed regex escape sequence warning (line 432)

---

## How It Works

### Detection Flow

1. **Proactive Scanner** scans all Python files
2. **Pattern Detection** identifies Pydantic BaseModel classes with logger attributes
3. **Issue Creation** creates CodeIssue objects with fix suggestions
4. **Auto-Fix** (if enabled) automatically moves logger to module level

### Fix Process

1. **Backup Creation** - Creates backup file before modification
2. **Logger Removal** - Removes logger from Pydantic class
3. **Module-Level Addition** - Adds logger at module level (if missing)
4. **Import Addition** - Adds `import logging` if missing
5. **Verification** - Returns success/failure status

---

## Usage

### Manual Scanning

```python
from diagnostic_machine.proactive_code_scanner import get_proactive_scanner

scanner = get_proactive_scanner()
issues = scanner.scan_pydantic_logger_issues()
print(f"Found {len(issues)} Pydantic logger issues")
```

### Auto-Fix

```python
from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer

fixer = AutomaticBugFixer(create_backups=True)
fixes = fixer.fix_all_issues(issues)
```

### Diagnostic Engine Integration

```python
from diagnostic_machine.diagnostic_engine import DiagnosticEngine

engine = DiagnosticEngine()
result = engine.run_proactive_scan(auto_heal=True)
print(f"Pydantic logger issues found: {result.get('pydantic_logger_issues', 0)}")
print(f"Fixes applied: {result.get('pydantic_fixes', [])}")
```

### Self-Healing Integration

```python
from cognitive.autonomous_healing_system import AutonomousHealingSystem

healing = AutonomousHealingSystem(session=session)
health = healing.assess_system_health()
# Pydantic logger issues are automatically included in health assessment
```

---

## Test Results

**Before Enhancements:**
- Passed: 5/7 (71%)
- Failed: 2/7 (29%)
- Issues: Pydantic logger errors, syntax warnings

**After Enhancements:**
- Enhanced detection and auto-fix capabilities
- Improved error handling
- Better integration with diagnostic and healing systems

---

## Next Steps

1. Run e2e tests to verify fixes
2. Monitor diagnostic engine for Pydantic logger issues
3. Review auto-fix results for accuracy
4. Consider adding more pattern-based fixes

---

**Status:** ✅ Enhancements Complete - Ready for Testing
