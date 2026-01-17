# Where to Get Healing Knowledge - Complete Guide

**Date:** 2026-01-16  
**Purpose:** Identify all sources for expanding self-healing knowledge base

---

## 📋 Summary

There are **5 main sources** for healing knowledge:
1. **Internal Sources** (Your own errors/logs)
2. **External Documentation** (Official docs, error databases)
3. **Community Knowledge** (Stack Overflow, GitHub issues)
4. **LLM-Generated Patterns** (AI-generated fix patterns)
5. **Learning from Failures** (System learns from its own attempts)

---

## 1. 🔍 Internal Sources (Your Own System)

### A. **Genesis Keys with Errors**

**Location:** Database `genesis_key` table  
**Query:** All ERROR type Genesis Keys

```python
# Get all error Genesis Keys
errors = session.query(GenesisKey).filter(
    GenesisKey.key_type == GenesisKeyType.ERROR
).all()

# Extract error patterns
for error in errors:
    error_message = error.error_message
    error_type = error.error_type
    # Analyze patterns
```

**What to Extract:**
- Error messages (479 errors detected)
- Error types (ImportError, AttributeError, etc.)
- File paths where errors occur
- Context (what was happening when error occurred)

**Files:**
- `backend/models/genesis_key_models.py` - Genesis Key structure
- `backend/tests/healing_results.json` - Recent healing attempts

---

### B. **Healing Results Log**

**Location:** `backend/tests/healing_results.json`

**What's There:**
- Failed healing attempts
- Error messages that couldn't be fixed
- Anomalies detected
- Actions that didn't work

**Example:**
```json
{
  "action": "database_table_create",
  "status": "failed",
  "message": "Table 'users' is already defined..."
}
```

**How to Use:**
1. Extract all failed actions
2. Categorize by error type
3. Create fix patterns for common failures
4. Learn what doesn't work

---

### C. **Application Logs**

**Location:** `backend/logs/` directory

**What to Look For:**
- Exception tracebacks
- Error patterns
- Repeated errors
- Error frequency

**How to Extract:**
```python
import re
from pathlib import Path

log_dir = Path("backend/logs")
for log_file in log_dir.glob("*.log"):
    with open(log_file) as f:
        for line in f:
            if "Error" in line or "Exception" in line:
                # Extract error pattern
                pattern = extract_error_pattern(line)
                # Add to knowledge base
```

---

### D. **Learning Memory System**

**Location:** `learning_examples` table in database

**What's There:**
- Past healing attempts
- Success/failure outcomes
- Trust scores
- What worked and what didn't

**Query:**
```python
# Get failed healing attempts
failed_examples = session.query(LearningExample).filter(
    LearningExample.example_type == "failure",
    LearningExample.outcome_quality < 0.5
).all()

# Extract patterns from failures
for example in failed_examples:
    input_context = example.input_context  # What was the error?
    actual_output = example.actual_output  # What happened?
    # Create fix pattern
```

---

## 2. 📚 External Documentation Sources

### A. **Python Official Documentation**

**Sources:**
- Python Built-in Exceptions: https://docs.python.org/3/library/exceptions.html
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Common Error Solutions: https://docs.python.org/3/tutorial/errors.html

**What to Extract:**
- Exception types and meanings
- Common causes
- Official solutions
- Best practices

**Example Pattern:**
```python
# From Python docs: ImportError
# Pattern: "ImportError: cannot import name 'X'"
# Common causes:
# 1. Circular imports
# 2. Module not in path
# 3. Module not installed
```

---

### B. **Library-Specific Error Docs**

**SQLAlchemy:**
- Table redefinition: https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Table.params.extend_existing
- Connection errors: https://docs.sqlalchemy.org/en/14/core/pooling.html

**Database Libraries:**
- SQLite errors: https://www.sqlite.org/rescode.html
- PostgreSQL errors: https://www.postgresql.org/docs/current/errcodes-appendix.html

**How to Use:**
1. Scrape error documentation
2. Extract error codes and messages
3. Map to fix patterns
4. Add to knowledge base

---

### C. **Error Code Databases**

**Sources:**
- Python Error Index: https://docs.python.org/3/library/exceptions.html#bltin-exceptions
- Common Python Errors: https://realpython.com/python-exceptions/
- SQLAlchemy Error Reference: https://docs.sqlalchemy.org/en/14/errors.html

**Format:**
```python
{
    "error_type": "ImportError",
    "pattern": "ImportError: cannot import name",
    "common_causes": ["circular import", "module not found"],
    "solutions": ["break circular dependency", "check PYTHONPATH"]
}
```

---

## 3. 🌐 Community Knowledge Sources

### A. **Stack Overflow**

**API:** https://api.stackexchange.com/docs

**Search Queries:**
- "Python ImportError circular import"
- "SQLAlchemy table already defined"
- "ModuleNotFoundError fix"

**How to Extract:**
```python
import requests

# Search Stack Overflow
url = "https://api.stackexchange.com/2.3/search"
params = {
    "order": "desc",
    "sort": "votes",
    "tagged": "python",
    "intitle": "ImportError",
    "site": "stackoverflow"
}
response = requests.get(url, params=params)
answers = response.json()["items"]

# Extract solutions
for answer in answers:
    solution = answer["body"]  # Markdown solution
    # Parse and extract fix pattern
```

**What to Get:**
- Common error messages
- Working solutions (upvoted answers)
- Code examples
- Edge cases

---

### B. **GitHub Issues**

**Sources:**
- SQLAlchemy Issues: https://github.com/sqlalchemy/sqlalchemy/issues
- Python Issues: https://github.com/python/cpython/issues

**Search:**
- Search for error messages
- Find closed issues with solutions
- Extract fix patterns

**Example:**
```
Issue: "Table 'X' is already defined"
Solution: "Add extend_existing=True"
Status: Closed (fixed)
```

---

### C. **Reddit / Forums**

**Sources:**
- r/learnpython
- r/Python
- Python Discord

**What to Extract:**
- Common questions
- Error patterns
- Community solutions

---

## 4. 🤖 LLM-Generated Patterns

### A. **Using Grace's LLM System**

**Location:** `backend/llm_orchestrator/`

**How to Generate:**
```python
from llm_orchestrator.llm_orchestrator import get_llm_orchestrator

orchestrator = get_llm_orchestrator()

prompt = """
Given this error message:
"ImportError: cannot import name 'X' from partially initialized module"

Generate a fix pattern including:
1. Error pattern (regex)
2. Fix template
3. Confidence score
4. Example fixes
"""

response = orchestrator.generate_response(prompt)
# Parse response and add to knowledge base
```

**Advantages:**
- Can generate patterns for any error
- Includes context and examples
- Can explain why fixes work

---

### B. **Using External LLMs**

**Sources:**
- OpenAI API
- Anthropic Claude
- Google Gemini

**Prompt Template:**
```
You are a Python error fixing expert. For this error:

{error_message}

Provide:
1. Error type
2. Common causes
3. Fix pattern (regex)
4. Fix code template
5. Confidence (0-1)
6. Example fixes
```

---

## 5. 🧠 Learning from Failures (Autonomous)

### A. **Current Learning System**

**Location:** `backend/cognitive/autonomous_healing_system.py`

**How It Works:**
```python
def _learn_from_healing(self, decision, result, success):
    """Learn from healing outcome."""
    if self.enable_learning:
        # Store in learning memory
        learning_example = LearningExample(
            example_type="healing_outcome",
            input_context={"anomaly": decision["anomaly"]},
            expected_output={"action": decision["healing_action"]},
            actual_output={"result": result, "success": success},
            trust_score=0.9 if success else 0.3,
            source="system_observation"
        )
        session.add(learning_example)
```

**What Gets Learned:**
- Which actions work for which errors
- Trust scores update based on success
- Patterns emerge from 3+ similar experiences

---

### B. **Mirror Self-Modeling**

**Location:** `backend/cognitive/mirror_self_modeling.py`

**What It Does:**
- Observes last 24 hours of operations
- Detects patterns (3+ occurrences)
- Suggests improvements
- Identifies what works and what doesn't

**How to Use:**
```python
# Mirror observes patterns
patterns = mirror_system.analyze_patterns()

# Extract successful fix patterns
for pattern in patterns:
    if pattern["success_rate"] > 0.8:
        # Add to knowledge base
        add_fix_pattern(pattern)
```

---

## 📊 Knowledge Extraction Workflow

### Step 1: **Collect Errors**
```python
# From Genesis Keys
errors = get_error_genesis_keys()

# From logs
log_errors = parse_log_files()

# From healing results
failed_heals = get_failed_healing_attempts()
```

### Step 2: **Categorize**
```python
# Group by error type
error_groups = {}
for error in errors:
    error_type = categorize_error(error.message)
    error_groups[error_type].append(error)
```

### Step 3: **Find Solutions**
```python
# For each error type:
for error_type, errors in error_groups.items():
    # 1. Check knowledge base (already know?)
    if not in_knowledge_base(error_type):
        # 2. Search Stack Overflow
        solutions = search_stackoverflow(error_type)
        # 3. Check documentation
        docs = search_documentation(error_type)
        # 4. Ask LLM
        llm_solution = ask_llm(error_type)
        # 5. Combine best solution
        best_solution = combine_solutions(solutions, docs, llm_solution)
        # 6. Add to knowledge base
        add_to_knowledge_base(error_type, best_solution)
```

### Step 4: **Test and Learn**
```python
# Apply fix pattern
result = apply_fix_pattern(error, pattern)

# Learn from outcome
if result.success:
    increase_trust_score(pattern)
else:
    decrease_trust_score(pattern)
    # Try alternative pattern
```

---

## 🎯 Recommended Implementation

### Immediate (Manual Curation):

1. **Extract from `healing_results.json`**
   ```python
   # Parse failed actions
   # Create patterns for:
   # - SQLAlchemy table errors (187 components)
   # - Import errors (9 components)
   # - Connection errors (73 errors)
   ```

2. **Query Genesis Keys**
   ```python
   # Get all ERROR Genesis Keys
   # Extract error messages
   # Categorize by type
   # Create fix patterns
   ```

3. **Search Stack Overflow**
   ```python
   # For each error type:
   # - Search Stack Overflow
   # - Get top 3 solutions
   # - Create fix pattern
   ```

### Short Term (Automated):

4. **LLM Pattern Generation**
   ```python
   # For each error type:
   # - Ask LLM to generate fix pattern
   # - Include examples and confidence
   # - Add to knowledge base
   ```

5. **Learning from Failures**
   ```python
   # Enable learning system
   # Track healing outcomes
   # Extract patterns from successes
   # Update knowledge base automatically
   ```

### Long Term (Continuous):

6. **Continuous Learning**
   ```python
   # Monitor all errors
   # Auto-extract patterns
   # Auto-generate fixes
   # Auto-update knowledge base
   ```

---

## 📁 Files to Modify

### Add Patterns To:
- `backend/cognitive/healing_knowledge_base.py` - Add new `FixPattern` entries

### Extract From:
- `backend/tests/healing_results.json` - Failed attempts
- `backend/data/grace.db` - Genesis Keys, Learning Examples
- `backend/logs/*.log` - Application logs

### Generate With:
- `backend/llm_orchestrator/llm_orchestrator.py` - LLM pattern generation
- Stack Overflow API - Community solutions
- Python documentation - Official fixes

---

## 🔧 Quick Start Script

```python
"""
Extract healing knowledge from multiple sources.
"""
from pathlib import Path
import json
from sqlalchemy.orm import Session

def extract_knowledge_from_sources(session: Session):
    """Extract knowledge from all sources."""
    
    # 1. From healing results
    with open("backend/tests/healing_results.json") as f:
        results = json.load(f)
        failed_actions = [r for r in results["healing_actions"] 
                         if r["execution_results"]["failed"]]
    
    # 2. From Genesis Keys
    errors = session.query(GenesisKey).filter(
        GenesisKey.key_type == GenesisKeyType.ERROR
    ).all()
    
    # 3. From learning examples
    failures = session.query(LearningExample).filter(
        LearningExample.outcome_quality < 0.5
    ).all()
    
    # 4. Categorize and create patterns
    patterns = {}
    for error in errors:
        error_type = categorize_error(error.error_message)
        if error_type not in patterns:
            patterns[error_type] = []
        patterns[error_type].append(error.error_message)
    
    # 5. Generate fix patterns (using LLM or manual)
    for error_type, messages in patterns.items():
        if len(messages) >= 3:  # Pattern detected
            fix_pattern = generate_fix_pattern(error_type, messages)
            add_to_knowledge_base(fix_pattern)
```

---

## ✅ Summary

**Best Sources (Priority Order):**

1. **Your own errors** (`healing_results.json`, Genesis Keys) - Most relevant
2. **Stack Overflow** - Proven solutions, high quality
3. **Official documentation** - Authoritative, reliable
4. **LLM generation** - Fast, comprehensive
5. **Learning system** - Continuous improvement

**Next Steps:**
1. Extract from `healing_results.json` (immediate)
2. Query Genesis Keys for error patterns (immediate)
3. Search Stack Overflow for missing patterns (short term)
4. Enable LLM pattern generation (short term)
5. Enable continuous learning (long term)

---

**Status:** 📚 **KNOWLEDGE SOURCES IDENTIFIED - READY TO EXTRACT**
