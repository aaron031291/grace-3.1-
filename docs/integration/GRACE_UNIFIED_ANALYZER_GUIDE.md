# GRACE Unified Code Analyzer
## Merging Bandit + Semgrep + pytest into One Powerful System

This document explains how we merged the best patterns from three proven tools to create a unified GRACE-specific code analyzer.

---

## 🎯 Overview: The Merger Strategy

### Three Tools → One Unified System

| Tool | Pattern Borrowed | What It Does for GRACE |
|------|------------------|------------------------|
| **Bandit** | AST Visitor Pattern | Systematic code traversal, context tracking |
| **Semgrep** | Pattern Matching Engine | Structural pattern detection, rule-based system |
| **pytest** | AST Transformation | Enhanced error messages, code enhancement (future) |

### The Result: `grace_code_analyzer.py`

A unified analyzer that combines:
- ✅ **Visitor pattern** for systematic analysis
- ✅ **Pattern matching** for flexible rule definition
- ✅ **Context tracking** for intelligent detection
- ✅ **GRACE-specific rules** for architecture compliance

---

## 📐 Architecture: How The Patterns Merge

### 1. **AST Visitor Pattern** (from Bandit)

**What We Borrowed:**
```python
class GraceCodeVisitor(ast.NodeVisitor):
    """Systematic AST traversal with context tracking"""
    
    def visit_Call(self, node):
        """Visit all function calls"""
        self._check_rules(node)  # Check patterns here
        self.generic_visit(node)
```

**Why We Need It:**
- Ensures we visit **every** relevant code construct
- Maintains context (function, class, scope)
- Efficient single-pass traversal

**How It Works:**
1. Python's `ast.NodeVisitor` automatically walks AST
2. Each node type triggers `visit_*` method
3. We check patterns at each relevant node
4. Context is maintained throughout traversal

---

### 2. **Pattern Matching Engine** (from Semgrep)

**What We Borrowed:**
```python
class PatternMatcher:
    """Structural pattern matching"""
    
    def match_pattern(self, pattern, target):
        """Match pattern AST against target AST"""
        # Returns metavariable bindings if match
```

**Why We Need It:**
- Write rules that **look like code**
- Match patterns structurally (not textually)
- Handle syntax variations automatically

**How It Works:**
1. Rules define patterns using AST syntax
2. Pattern matcher compares pattern AST to code AST
3. Metavariables (`$X`) bind to matched values
4. Returns bindings if match found

**Example Pattern:**
```python
# Pattern: qdrant_client.query($USER_INPUT)
pattern = ast.Call(
    func=ast.Attribute(
        value=ast.Name(id='qdrant_client'),
        attr='query'
    ),
    args=[Metavariable('USER_INPUT')]
)

# Matches: qdrant_client.query(user_data)
# Binds: USER_INPUT → user_data
```

---

### 3. **AST Transformation** (from pytest - Future)

**What We Can Borrow:**
```python
class GraceASTTransformer(ast.NodeTransformer):
    """Transform code for better error messages"""
    
    def visit_Assert(self, node):
        """Enhance assertions with detailed messages"""
        return enhanced_assert
```

**Future Use Cases:**
- Enhanced error messages (like pytest's assertion rewriting)
- Automatic logging injection
- Monitoring code insertion

**Currently:** Infrastructure ready, transformations can be added as needed

---

## 🔧 Implementation Details

### Core Components

#### 1. **PatternRule** (from Semgrep)

Defines a rule with:
- Pattern AST to match
- Message to show
- Severity level
- Suggested fix

```python
rule = PatternRule(
    rule_id='G001',
    description='Unsafe vector query',
    severity=Severity.HIGH,
    patterns=[pattern_ast],
    message='Unsanitized query: $USER_INPUT',
    suggested_fix='Sanitize input'
)
```

#### 2. **AnalysisContext** (from Bandit)

Tracks current analysis state:
- Current function/class
- Scope stack
- Variable assignments
- Import statements

```python
context = AnalysisContext(
    function='process_data',
    class_='DataProcessor',
    scope_stack=['class', 'function'],
    imports={'qdrant_client', 'fastapi'}
)
```

#### 3. **CodeIssue** (Combined)

Represents a found issue:
- Rule ID
- Severity/confidence
- Location (file, line, column)
- Context
- Suggested fix
- Pattern match bindings

```python
issue = CodeIssue(
    rule_id='G001',
    severity=Severity.HIGH,
    message='Unsanitized query: user_input',
    file_path='backend/api/retrieve.py',
    line_number=42,
    pattern_match={'USER_INPUT': ast_node}
)
```

---

## 🎨 How Patterns Work Together

### Analysis Flow

```
1. Source Code
   ↓
2. Parse to AST (Python's ast.parse)
   ↓
3. Create Visitor with Rules
   ↓
4. Visit AST Node by Node
   ├─ Update Context (Bandit pattern)
   ├─ Match Patterns (Semgrep pattern)
   └─ Collect Issues
   ↓
5. Return Issues with Context
```

### Example: Finding Unsafe Vector Query

**Step 1: Rule Definition (Semgrep-style)**
```python
rule = GraceRuleBuilder.unsafe_vector_query()
# Pattern: qdrant_client.query($USER_INPUT)
```

**Step 2: Code Traversal (Bandit-style)**
```python
visitor.visit_Call(node)  # Called for every function call
```

**Step 3: Pattern Matching (Semgrep-style)**
```python
bindings = pattern_matcher.match_pattern(rule.patterns[0], node)
# Returns: {'USER_INPUT': ast_node} if match
```

**Step 4: Issue Creation (Combined)**
```python
issue = CodeIssue(
    rule_id='G001',
    severity=Severity.HIGH,
    message='Unsanitized query: user_input',  # Uses bindings
    line_number=node.lineno,
    context=context.get_context_string()  # From Bandit
)
```

---

## 📚 GRACE-Specific Rules

### Current Rules

1. **G001: Unsafe Vector Query**
   - Pattern: `qdrant_client.query($USER_INPUT)`
   - Checks: Vector DB queries with user input

2. **G002: Missing Error Handling**
   - Pattern: Function calls without try/except
   - Checks: Error handling compliance

3. **G003: Cognitive Layer Call Without Logging**
   - Pattern: `cognitive_engine.*()` without logging
   - Checks: Cognitive layer monitoring

4. **G004: Hardcoded Credentials**
   - Pattern: `password = "value"` or similar
   - Checks: Security best practices

### Adding New Rules

```python
@staticmethod
def my_custom_rule() -> PatternRule:
    """Custom GRACE rule"""
    pattern = ast.Call(
        func=ast.Name(id='my_function'),
        args=[Metavariable('X')]
    )
    
    return PatternRule(
        rule_id='G005',
        description='Custom check',
        severity=Severity.MEDIUM,
        patterns=[pattern],
        message='Found: $X',
        check_node_types={ast.Call}
    )

# Add to rules list
rules = GraceRuleBuilder.get_all_rules()
rules.append(GraceRuleBuilder.my_custom_rule())
```

---

## 🚀 Usage Examples

### Basic Usage

```python
from backend.cognitive.grace_code_analyzer import (
    GraceCodeAnalyzer,
    analyze_grace_codebase
)

# Analyze entire codebase
results = analyze_grace_codebase('backend')

# Print results
for file_path, issues in results.items():
    print(f"{file_path}: {len(issues)} issues")
    for issue in issues:
        print(f"  [{issue.severity.value}] {issue.message}")
```

### Custom Rules

```python
from backend.cognitive.grace_code_analyzer import (
    PatternRule,
    Severity,
    GraceCodeAnalyzer
)

# Define custom rule
custom_rule = PatternRule(
    rule_id='CUSTOM_001',
    description='Custom check',
    severity=Severity.HIGH,
    patterns=[my_pattern],
    message='Custom issue: $X',
    check_node_types={ast.Call}
)

# Analyze with custom rules
analyzer = GraceCodeAnalyzer(custom_rules=[custom_rule])
issues = analyzer.analyze_file('path/to/file.py')
```

### Analyze Single File

```python
analyzer = GraceCodeAnalyzer()
issues = analyzer.analyze_file('backend/api/retrieve.py')

for issue in issues:
    print(f"Line {issue.line_number}: {issue.message}")
    if issue.suggested_fix:
        print(f"  Fix: {issue.suggested_fix}")
```

---

## 🔄 Integration with GRACE

### Integration Points

1. **Genesis System**
   - Track code changes via code analyzer
   - Store analysis results in Genesis keys

2. **Cognitive Layer**
   - Use analyzer to detect cognitive layer issues
   - Monitor API compliance

3. **Learning System**
   - Learn from patterns in code
   - Improve rules based on findings

4. **Autonomous Healing**
   - Auto-fix issues (using suggested fixes)
   - Track fixes over time

### Example Integration

```python
# In autonomous healing system
from backend.cognitive.grace_code_analyzer import analyze_grace_codebase

def check_code_health():
    """Check codebase health"""
    results = analyze_grace_codebase('backend')
    
    critical_issues = [
        issue for issues in results.values()
        for issue in issues
        if issue.severity == Severity.CRITICAL
    ]
    
    if critical_issues:
        trigger_healing_process(critical_issues)
```

---

## 📊 Comparison: Before vs After

### Before (Original CodeAnalyzer)

- ✅ Basic AST parsing
- ✅ Simple pattern checking (regex-based)
- ❌ No structural pattern matching
- ❌ Limited context tracking
- ❌ No rule-based system

### After (Unified Analyzer)

- ✅ AST Visitor pattern (systematic traversal)
- ✅ Structural pattern matching (Semgrep-style)
- ✅ Full context tracking (Bandit-style)
- ✅ Rule-based system (easy to extend)
- ✅ GRACE-specific rules
- ✅ Metavariable bindings
- ✅ Pattern composition support

---

## 🎓 Learning from the Merger

### Key Insights

1. **Visitor Pattern** (Bandit)
   - Perfect for systematic traversal
   - Maintains context naturally
   - Easy to extend

2. **Pattern Matching** (Semgrep)
   - Flexible rule definition
   - Structural matching > text matching
   - Metavariables enable powerful patterns

3. **AST Transformation** (pytest)
   - Foundation for code enhancement
   - Future-proof architecture
   - Non-intrusive code modification

### Best Practices Applied

1. **Separation of Concerns**
   - Visitor handles traversal
   - Pattern matcher handles matching
   - Rules handle definitions

2. **Extensibility**
   - Easy to add new rules
   - Easy to add new patterns
   - Easy to add new checks

3. **Performance**
   - Single-pass traversal
   - Pattern-specific checks
   - Efficient matching

---

## 🔮 Future Enhancements

### Short Term

1. **More GRACE-Specific Rules**
   - Memory mesh compliance
   - Learning system checks
   - API consistency

2. **Enhanced Pattern Matching**
   - Ellipsis support (`...`)
   - Pattern composition (AND/OR)
   - Negative patterns

3. **Better Error Messages**
   - Use pytest-style transformation
   - Show actual values
   - Contextual suggestions

### Medium Term

1. **AST Transformation**
   - Automatic logging injection
   - Monitoring code insertion
   - Code enhancement

2. **Learning Integration**
   - Learn patterns from issues
   - Auto-generate rules
   - Improve suggestions

3. **Auto-Fix**
   - Apply suggested fixes automatically
   - Test fixes before applying
   - Track fix success rate

---

## 📚 References

- **Bandit Deep Dive**: `DEEP_DIVE_BANDIT_ARCHITECTURE.md`
- **Semgrep Deep Dive**: `DEEP_DIVE_SEMGREP_ARCHITECTURE.md`
- **pytest Deep Dive**: `DEEP_DIVE_PYTEST_ARCHITECTURE.md`
- **Implementation**: `backend/cognitive/grace_code_analyzer.py`

---

**Last Updated:** 2026-01-16
