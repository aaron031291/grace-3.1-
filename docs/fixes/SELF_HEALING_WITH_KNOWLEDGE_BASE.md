# Self-Healing System with Knowledge Base and Script Generation

## ✅ What Was Added

Enhanced the autonomous self-healing system with:
1. **Healing Knowledge Base** - Common fixes and patterns
2. **Script Generator** - Creates Python scripts to fix issues
3. **Patch Generator** - Generates code patches automatically
4. **Code Fix Action** - New healing action for code-level fixes

## 📁 New Components

### 1. Healing Knowledge Base
**File:** `backend/cognitive/healing_knowledge_base.py`

Contains:
- **Fix Patterns** - Common issue types and how to fix them
  - SQLAlchemy table redefinition
  - Missing imports
  - Syntax errors
  - Attribute errors
  - Database connection issues
- **Issue Identification** - Automatically identifies issue types from error messages
- **Fix Suggestions** - Generates fix suggestions with confidence scores
- **Patch Generation** - Creates code patches for automatic fixing

### 2. Healing Script Generator
**File:** `backend/cognitive/healing_script_generator.py`

Features:
- **Script Generation** - Creates Python scripts to fix multiple issues
- **Patch Application** - Generates and applies code patches
- **Script Execution** - Executes healing scripts autonomously
- **Genesis Key Tracking** - Tracks all script executions

### 3. Enhanced Autonomous Healing System
**File:** `backend/cognitive/autonomous_healing_system.py`

New capabilities:
- **CODE_FIX Action** - New healing action for code fixes
- **Knowledge Base Integration** - Uses knowledge base to identify and fix issues
- **Script Execution** - Automatically generates and executes fix scripts
- **Smart Issue Detection** - Automatically detects code issues from error messages

## 🎯 How It Works

### 1. Issue Detection
```
Error Message → Knowledge Base → Issue Type Identified
```

### 2. Fix Generation
```
Issue Type → Fix Pattern → Script/Patch Generated
```

### 3. Execution
```
Script/Patch → Execute → Track with Genesis Keys → Learn
```

## 🔧 Knowledge Base Patterns

### SQLAlchemy Table Redefinition
- **Pattern:** "Table 'X' is already defined"
- **Fix:** Add `extend_existing=True` to table definitions
- **Confidence:** 0.95
- **Script:** Auto-generates script to fix all occurrences

### Missing Imports
- **Pattern:** "No module named 'X'"
- **Fix:** Add missing import statements
- **Confidence:** 0.85
- **Script:** Auto-generates import fixes

### Syntax Errors
- **Pattern:** "SyntaxError at line X"
- **Fix:** Manual review required (logs location)
- **Confidence:** 0.70

## 🚀 Usage

### Automatic (Integrated)
The healing system automatically uses the knowledge base when:
- Anomalies are detected
- Error messages match known patterns
- Trust level allows code fixes

### Manual Script Generation
```python
from cognitive.healing_script_generator import get_healing_script_generator

generator = get_healing_script_generator()

issues = [{
    "issue_type": "sqlalchemy_table_redefinition",
    "file_path": "backend/models/database_models.py",
    "error_message": "Table 'users' is already defined",
    "line_number": 42
}]

# Generate and execute
result = generator.generate_and_execute_patches(issues, auto_execute=True)
```

### Manual Knowledge Base Query
```python
from cognitive.healing_knowledge_base import get_healing_knowledge_base

kb = get_healing_knowledge_base()

# Identify issue
issue_info = kb.identify_issue_type("Table 'users' is already defined")
if issue_info:
    issue_type, pattern = issue_info
    fix = kb.generate_fix_suggestion(issue_type, error_message)
    print(fix["fix_text"])
```

## 📊 Integration Points

### With Component Tester
- Component tester finds issues
- Issues sent to healing system
- Knowledge base identifies fix patterns
- Scripts generated and executed
- Results tracked with Genesis Keys

### With Autonomous Healing
- Healing system detects anomalies
- Knowledge base identifies code issues
- Scripts/patches generated automatically
- Executed based on trust level
- Results learned and tracked

## 🎓 Learning

The system learns from:
- **Successful Fixes** - Trust scores increase
- **Failed Fixes** - Trust scores decrease
- **Pattern Recognition** - New patterns added to knowledge base
- **Script Effectiveness** - Scripts improved over time

## 📝 Example: SQLAlchemy Fix

**Issue:**
```
Table 'users' is already defined for this MetaData instance.
Specify 'extend_existing=True' to redefine options and columns.
```

**Knowledge Base Response:**
1. Identifies: `SQLALCHEMY_TABLE_REDEFINITION`
2. Confidence: 0.95
3. Generates fix script
4. Executes script
5. Creates Genesis Key for tracking

**Generated Script:**
```python
# Auto-generated healing script
# Fixes SQLAlchemy table redefinition issues

import re
from pathlib import Path

def fix_table_redefinition(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add extend_existing=True to Table() constructors
    content = re.sub(
        r'(Table\s*\([^)]*)(\))',
        r'\1, extend_existing=True\2',
        content
    )
    
    # Add __table_args__ to declarative classes
    # ... (more fix logic)
    
    with open(file_path, 'w') as f:
        f.write(content)
```

## 🔐 Trust Levels

Code fixes use:
- **Trust Level:** LOW_RISK_AUTO (Level 2)
- **Confidence Threshold:** 0.70 minimum
- **Auto-Execute:** Yes (if trust allows)

## 📈 Benefits

1. **Autonomous Code Fixes** - Fixes code issues automatically
2. **Knowledge-Driven** - Uses proven fix patterns
3. **Script Generation** - Creates reusable fix scripts
4. **Complete Tracking** - Genesis Keys track everything
5. **Learning** - Improves over time

## 🔗 Files

- `backend/cognitive/healing_knowledge_base.py` - Knowledge base
- `backend/cognitive/healing_script_generator.py` - Script generator
- `backend/cognitive/autonomous_healing_system.py` - Enhanced healing system
- `.healing_scripts/` - Generated healing scripts directory

---

**Status:** ✅ Complete - Self-healing now has knowledge and script generation capabilities!
