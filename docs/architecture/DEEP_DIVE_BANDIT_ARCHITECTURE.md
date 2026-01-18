# Deep Dive: Bandit Architecture Analysis
## Understanding How a Production Static Analysis Tool Works

This guide provides a **detailed breakdown** of Bandit's architecture - one of the simplest yet most effective static analysis tools. Perfect for understanding core patterns you can use to build your own.

---

## 🎯 Overview: What Bandit Does

Bandit scans Python code for security issues using:
1. **AST Parsing** - Converts Python source code to Abstract Syntax Tree
2. **AST Visitor Pattern** - Walks through the tree checking for dangerous patterns
3. **Plugin System** - Extensible security tests (plugins)
4. **Context Tracking** - Understands code context (function names, class hierarchy)

---

## 📁 Core Architecture

### 1. **AST Visitor Pattern** (The Heart of Bandit)

**Location**: `bandit/core/visitor.py`

**How It Works:**
```python
# Simplified version of Bandit's visitor pattern

import ast

class BanditNodeVisitor(ast.NodeVisitor):
    """Base visitor that walks AST nodes"""
    
    def __init__(self):
        self.issues = []  # Found security issues
        self.context = []  # Track current context (function, class)
    
    def visit(self, node):
        """Visit a node and all its children"""
        # Do something before visiting children
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        
        # Visit the node
        result = visitor(node)
        
        # Visit children
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        
        # Do something after visiting children
        return result
    
    def visit_Call(self, node):
        """Called when a function call is encountered"""
        # Check if this is a dangerous function
        # e.g., eval(), exec(), subprocess.call()
        pass
    
    def visit_Import(self, node):
        """Called when an import is encountered"""
        # Check if dangerous module is imported
        pass
    
    def visit_Assign(self, node):
        """Called when assignment is encountered"""
        # Check if password/secret is hardcoded
        pass
```

**Key Insight:** 
- Bandit uses Python's built-in `ast` module
- `NodeVisitor` pattern automatically walks the entire AST
- Each node type has a corresponding `visit_*` method
- Context is maintained during traversal (which function/class you're in)

---

### 2. **Plugin System** (Extensible Security Tests)

**Location**: `bandit/plugins/`

**How Plugins Work:**
```python
# Example: bandit/plugins/blacklist_calls.py

import ast
from bandit.core import test_properties as test

@test.checks('Call')  # Only check Call nodes
@test.test_id('B001')
def blacklist_calls(context, config):
    """
    Check for dangerous function calls like eval(), exec()
    """
    dangerous_functions = {
        'eval': 'Use of eval() is dangerous',
        'exec': 'Use of exec() is dangerous',
        'execfile': 'Use of execfile() is dangerous',
        '__import__': 'Use of __import__() is dangerous',
    }
    
    # Check if function name is in blacklist
    if isinstance(context.node.func, ast.Name):
        func_name = context.node.func.id
        if func_name in dangerous_functions:
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.MEDIUM,
                text=dangerous_functions[func_name]
            )
```

**Key Patterns:**

1. **Decorator-Based Registration**
   - `@test.checks('Call')` - Only runs on Call nodes
   - `@test.test_id('B001')` - Unique identifier

2. **Context Object**
   - `context.node` - Current AST node
   - `context.function` - Current function (if any)
   - `context.class` - Current class (if any)
   - `context.statement` - Current statement

3. **Return Issues**
   - Plugins return `Issue` objects or `None`
   - Issues have severity, confidence, and message

**Plugin Discovery:**
```python
# Bandit automatically discovers plugins
# It scans bandit/plugins/ directory
# Loads all Python files
# Finds functions with @test.checks decorator
# Registers them as tests
```

---

### 3. **Context Tracking** (Understanding Code Structure)

**Location**: `bandit/core/context.py`

**Why Context Matters:**
```python
# Consider this code:
class Database:
    def connect(self, password):
        # This is OK - password is a parameter
        pass

def connect_to_db():
    password = "hardcoded123"  # This is BAD - hardcoded password
    db.connect(password)
```

Bandit needs to know:
- Is the variable a function parameter? (OK)
- Is it a hardcoded string? (BAD)
- Is it in a test file? (Maybe OK)

**How Bandit Tracks Context:**
```python
class Context:
    """Tracks current code context during AST traversal"""
    
    def __init__(self):
        self.node = None        # Current AST node
        self.function = None    # Current function name
        self.class_ = None      # Current class name
        self.statement = None   # Current statement
        self.scope = []         # Stack of scopes (function/class)
        self.call_stack = []    # Call stack
    
    def update(self, node):
        """Update context when entering new node"""
        # Track when entering/exiting functions
        if isinstance(node, ast.FunctionDef):
            self.function = node.name
            self.scope.append('function')
        
        # Track when entering/exiting classes
        if isinstance(node, ast.ClassDef):
            self.class_ = node.name
            self.scope.append('class')
```

---

### 4. **Main Execution Flow**

**Location**: `bandit/core/manager.py`

**Execution Pipeline:**
```python
class BanditManager:
    """Main manager that orchestrates analysis"""
    
    def run(self, files, tests):
        """Run bandit on files"""
        results = []
        
        for file_path in files:
            # 1. Parse file to AST
            tree = self._parse_file(file_path)
            
            # 2. Create visitor
            visitor = BanditNodeVisitor(tests=tests)
            
            # 3. Walk the AST
            visitor.visit(tree)
            
            # 4. Collect issues
            issues = visitor.get_issues()
            results.extend(issues)
        
        # 5. Report results
        self._report(results)
        return results
    
    def _parse_file(self, file_path):
        """Parse Python file to AST"""
        with open(file_path, 'r') as f:
            source = f.read()
        return ast.parse(source, filename=file_path)
```

**Step-by-Step Flow:**
1. **File Discovery** - Find all Python files
2. **Parse** - Convert source code to AST
3. **Create Visitor** - Set up visitor with enabled tests
4. **Visit** - Walk AST, running tests on each node
5. **Collect** - Gather all issues found
6. **Report** - Output results (JSON, text, etc.)

---

## 🔍 Detailed Code Walkthrough

### Example: Detecting Hardcoded Passwords

Let's trace through how Bandit finds hardcoded passwords:

**Plugin Code** (`bandit/plugins/hardcoded_password.py`):
```python
@test.checks('Str')
@test.test_id('B105')
def hardcoded_password_string(context, config):
    """Check for hardcoded password strings"""
    
    # Get the string value
    string_value = context.node.s
    
    # Common password patterns
    password_patterns = ['password', 'passwd', 'pwd', 'secret']
    
    # Check if variable name suggests password
    if context.is_assigned():
        # Get assignment node
        assign = context.statement
        
        # Check variable name
        for target in assign.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                
                # Check if variable name matches pattern
                if any(pattern in var_name for pattern in password_patterns):
                    # Check if value looks like a real password
                    if len(string_value) >= 8:
                        return bandit.Issue(
                            severity=bandit.HIGH,
                            confidence=bandit.MEDIUM,
                            text=f"Possible hardcoded password: {var_name}"
                        )
```

**What Happens:**

1. **AST Traversal** - Visitor walks through AST
2. **String Node Found** - `visit_Str()` is called for `"mysecret123"`
3. **Check Context** - Is this string assigned to a password variable?
4. **Pattern Matching** - Does variable name match password patterns?
5. **Issue Creation** - If match, create Issue object
6. **Collection** - Issue added to results

---

## 🎨 Design Patterns Used

### 1. **Visitor Pattern**
**Purpose:** Separate algorithm from data structure (AST)

**Benefits:**
- Easy to add new checks (new visitor methods)
- Traversal logic in one place
- Each check is independent

**In Bandit:**
```python
class NodeVisitor:
    def visit_<NodeType>(self, node):
        # Handle specific node type
        pass
```

### 2. **Plugin Architecture**
**Purpose:** Extensible, modular checks

**Benefits:**
- Easy to add new security tests
- Can enable/disable specific tests
- Tests are self-contained

**In Bandit:**
```python
# Register plugin via decorator
@test.checks('Call')
def my_security_check(context, config):
    # Check logic
    pass
```

### 3. **Context Object**
**Purpose:** Maintain state during traversal

**Benefits:**
- Know where you are in the code
- Track scopes (function/class)
- Understand relationships

**In Bandit:**
```python
context.function  # Current function name
context.class_    # Current class name
context.statement # Current statement
```

---

## 💡 Building Your Own: GRACE Security Scanner

Based on Bandit's architecture, here's how to build a GRACE-specific scanner:

### Step 1: Define Your AST Visitor

```python
import ast
from typing import List, Dict

class GraceSecurityVisitor(ast.NodeVisitor):
    """Visitor for GRACE-specific security checks"""
    
    def __init__(self):
        self.issues = []
        self.context = {
            'function': None,
            'class': None,
            'scope': []
        }
    
    def visit_Call(self, node):
        """Check for dangerous function calls"""
        # GRACE-specific checks
        # e.g., unsafe database queries
        # e.g., insecure API calls
        pass
    
    def visit_Import(self, node):
        """Check for dangerous imports"""
        # GRACE-specific checks
        # e.g., deprecated modules
        pass
```

### Step 2: Create GRACE-Specific Tests

```python
@test.checks('Call')
@test.test_id('G001')
def unsafe_vector_db_query(context, config):
    """Check for unsafe vector database queries"""
    
    if isinstance(context.node.func, ast.Attribute):
        # Check if it's a vector DB query
        if context.node.func.attr == 'query' and 'qdrant' in str(context.node.func.value):
            # Check if query is properly sanitized
            if not context.is_sanitized(context.node):
                return Issue(
                    severity=HIGH,
                    confidence=MEDIUM,
                    text="Unsanitized vector database query"
                )
```

### Step 3: Integrate with GRACE

```python
class GraceSecurityScanner:
    """Security scanner for GRACE codebase"""
    
    def __init__(self):
        self.visitor = GraceSecurityVisitor()
    
    def scan_file(self, file_path: str) -> List[Issue]:
        """Scan a single file"""
        with open(file_path, 'r') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=file_path)
        self.visitor.visit(tree)
        return self.visitor.issues
    
    def scan_directory(self, directory: str) -> Dict[str, List[Issue]]:
        """Scan all Python files in directory"""
        results = {}
        
        for file_path in Path(directory).rglob('*.py'):
            issues = self.scan_file(file_path)
            if issues:
                results[str(file_path)] = issues
        
        return results
```

---

## 🔬 Key Files to Study in Bandit

### Must-Read Files (in order):

1. **`bandit/core/visitor.py`**
   - Core visitor implementation
   - How AST traversal works

2. **`bandit/core/tester.py`**
   - Test execution logic
   - How plugins are invoked

3. **`bandit/plugins/blacklist_calls.py`**
   - Simplest plugin example
   - Good starting point

4. **`bandit/core/manager.py`**
   - Main execution flow
   - File discovery and parsing

5. **`bandit/core/context.py`**
   - Context tracking
   - Understanding code structure

### Example Plugin to Study:

**`bandit/plugins/hardcoded_password.py`**
- More complex plugin
- Shows context usage
- Pattern matching example

---

## 📊 Performance Characteristics

### Why Bandit is Fast:

1. **Single-Pass Traversal**
   - AST walked once
   - All tests run during same traversal

2. **Node-Specific Tests**
   - Tests only run on relevant nodes
   - `@test.checks('Call')` filters automatically

3. **Early Termination**
   - Can stop after first issue (if configured)
   - Skip files that don't need checking

4. **Efficient Parsing**
   - Python's `ast` module is C-optimized
   - Parsing is fast compared to analysis

### Time Complexity:

- **Parsing**: O(n) where n = lines of code
- **Traversal**: O(n) where n = AST nodes
- **Testing**: O(m × k) where m = nodes checked, k = tests per node

**Total**: O(n + m × k) ≈ **O(n)** in practice

---

## 🎓 Learning Exercises

### Exercise 1: Simple AST Walker
Write a simple AST walker that prints all function names:

```python
import ast

class FunctionPrinter(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        print(f"Found function: {node.name}")
        self.generic_visit(node)

# Test it
code = """
def hello():
    pass

def world():
    pass
"""

tree = ast.parse(code)
FunctionPrinter().visit(tree)
# Output:
# Found function: hello
# Found function: world
```

### Exercise 2: Find Dangerous Functions
Write a scanner that finds `eval()` calls:

```python
class EvalFinder(ast.NodeVisitor):
    def __init__(self):
        self.found = []
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == 'eval':
                self.found.append(ast.get_source_segment(...))
        self.generic_visit(node)
```

### Exercise 3: Build GRACE Checker
Create a GRACE-specific check for unsafe vector queries:

```python
@test.checks('Call')
def check_unsafe_vector_query(context, config):
    # Your implementation here
    pass
```

---

## 🔗 Next Steps

1. **Clone Bandit Repository**
   ```bash
   git clone https://github.com/PyCQA/bandit.git
   cd bandit
   ```

2. **Read Core Files**
   - Start with `bandit/core/visitor.py`
   - Then `bandit/plugins/blacklist_calls.py`

3. **Run Bandit on GRACE**
   ```bash
   bandit -r backend/
   ```

4. **Build Prototype**
   - Start with simple AST walker
   - Add GRACE-specific checks
   - Integrate with existing systems

5. **Study Other Tools**
   - Move to Semgrep (pattern matching)
   - Then pytest (AST transformation)

---

## 📚 References

- **Bandit GitHub**: https://github.com/PyCQA/bandit
- **Python AST Docs**: https://docs.python.org/3/library/ast.html
- **AST Visualizer**: https://python-ast-explorer.com/
- **Bandit Documentation**: https://bandit.readthedocs.io/

---

**Last Updated:** 2026-01-16
