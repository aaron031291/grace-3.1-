# Deep Dive: Semgrep Architecture Analysis
## Understanding Pattern-Based Static Analysis at Scale

Semgrep is a fast, pattern-based static analysis tool that supports 30+ languages. This guide breaks down how it achieves both speed and accuracy through its unique architecture.

---

## 🎯 Overview: What Makes Semgrep Different

Semgrep's key innovation: **Generic AST Pattern Matching**
- Convert all languages to a common AST format
- Pattern matching works across languages
- Fast (single-file, no complex inter-procedural analysis)
- Easy to write rules (patterns look like code)

---

## 📁 Core Architecture

### 1. **Generic AST (Language-Agnostic Representation)**

**Location**: `libs/ast_generic/AST_generic.ml`

**The Problem It Solves:**
```python
# Python
import os
result = os.system(command)

# JavaScript
const os = require('os');
result = os.system(command);

# Both have the same security issue, but different syntax
# Semgrep converts both to the same generic AST
```

**Generic AST Structure:**
```ocaml
(* Simplified representation *)
type expr =
  | Call of {
      func: expr;
      args: expr list;
      location: location;
    }
  | Name of string * location
  | Import of string * location
  | ...

type stmt =
  | Assign of expr * expr * location
  | If of expr * stmt list * stmt list * location
  | ...
```

**Key Insight:**
- Each language parser converts to generic AST
- Pattern matching only needs to understand generic AST
- Same rules work across languages

---

### 2. **Pattern Matching Engine** (The Core Algorithm)

**Location**: `src/matching/Generic_vs_generic.ml`

**How Pattern Matching Works:**

**Pattern Syntax:**
```yaml
# Rule: Find dangerous os.system() calls
rules:
  - id: dangerous-system-call
    pattern: os.system($X)
    message: Dangerous system call with user input
```

**Matching Algorithm:**
```ocaml
(* Simplified matching logic *)
let rec match_expr pattern target =
  match pattern, target with
  | Call({func=Name("os.system")}, [arg]), Call({func=Name("os.system")}, [arg2]) ->
      (* Match function name *)
      (* Match arguments - bind $X to arg2 *)
      Some([("$X", arg2)])
  
  | Name("$X"), expr ->
      (* Metavariable matches anything *)
      Some([("$X", expr)])
  
  | Call(pat_func, pat_args), Call(target_func, target_args) ->
      (* Recursively match function and arguments *)
      match_expr pat_func target_func >>= fun bindings1 ->
      match_exprs pat_args target_args >>= fun bindings2 ->
      Some(merge_bindings bindings1 bindings2)
  
  | _ -> None  (* No match *)
```

**Key Features:**

1. **Metavariables** (`$X`, `$Y`)
   - Match any expression
   - Can be reused to enforce consistency
   ```yaml
   pattern: $X == $X  # Always true
   ```

2. **Ellipsis** (`...`)
   - Match any sequence of items
   ```yaml
   pattern: func($A, ..., $B)  # Any number of args between $A and $B
   ```

3. **Pattern Operators**
   ```yaml
   patterns:
     - pattern-inside: function($X) { ... }  # Match inside function
     - pattern-not: if ($X) { ... }          # Not inside if
     - pattern-either:                        # OR logic
         - pattern: dangerous1($X)
         - pattern: dangerous2($X)
   ```

---

### 3. **Multi-Language Parsing Pipeline**

**How Different Languages Are Handled:**

```
Python Source Code
    ↓ (Tree-sitter parser)
Python AST
    ↓ (Convert to generic)
Generic AST
    ↓ (Pattern matching)
Matches

JavaScript Source Code
    ↓ (Tree-sitter parser)
JavaScript AST
    ↓ (Convert to generic)
Generic AST
    ↓ (Same patterns!)
Matches
```

**Parser Architecture:**
```ocaml
(* Language-specific parsers *)
let parse_python source =
  let python_ast = TreeSitter_python.parse source in
  convert_to_generic python_ast

let parse_javascript source =
  let js_ast = TreeSitter_javascript.parse source in
  convert_to_generic js_ast

(* Same matching engine for all *)
let find_patterns generic_ast patterns =
  List.map (fun pattern -> match_pattern pattern generic_ast) patterns
```

---

### 4. **Rule Engine** (Pattern + Metadata)

**Location**: `semgrep/semgrep/rule.py`

**Rule Structure:**
```yaml
rules:
  - id: sql-injection
    languages: [python, javascript]
    severity: ERROR
    message: Potential SQL injection
    patterns:
      - pattern-inside: |
          $DB.query(...)
      - pattern-either:
          - pattern: "SELECT * FROM ... WHERE id = $USER_INPUT"
          - pattern: f"SELECT * FROM ... WHERE id = {$_}"
    fix: |
      # Use parameterized queries instead
      $DB.query("SELECT * FROM ... WHERE id = ?", $USER_INPUT)
```

**Rule Execution:**
```python
def execute_rule(rule, file_ast):
    """Execute a single rule against an AST"""
    matches = []
    
    for pattern_group in rule.patterns:
        # Match pattern group (AND/OR logic)
        pattern_matches = match_pattern_group(pattern_group, file_ast)
        
        if pattern_matches:
            # Create finding
            for match in pattern_matches:
                matches.append(Finding(
                    rule_id=rule.id,
                    message=rule.message,
                    severity=rule.severity,
                    location=match.location,
                    fix=rule.fix if rule.fix else None
                ))
    
    return matches
```

---

## 🔍 Key Algorithm: Structural Pattern Matching

### How It Differs from Text Matching (grep):

**Text Matching (grep):**
```bash
# Problem: Matches too much, breaks on whitespace
grep "os.system" file.py
# Matches: os.system(...), os. system(...), os. system (...)
```

**Structural Matching (Semgrep):**
```yaml
pattern: os.system($X)
# Matches: os.system(command)
# Matches: os.system(get_user_input())
# Doesn't match: os.system()  # Wrong args
# Doesn't match: os.system  # Not a call
```

**Why It's Better:**
1. **Syntax-Aware** - Understands code structure
2. **Resilient** - Handles formatting differences
3. **Precise** - Only matches valid code patterns

---

### Pattern Matching Algorithm (Detailed)

```ocaml
(* Core matching function *)
let rec match_expr pattern target bindings =
  match pattern, target with
  
  (* Metavariable: bind to anything *)
  | Metavariable(name), expr ->
      if binding_exists name bindings then
        (* Check consistency *)
        if same_ast (get_binding name bindings) expr then
          Some(bindings)
        else
          None
      else
        (* New binding *)
        Some(add_binding name expr bindings)
  
  (* Exact match *)
  | Literal(str1), Literal(str2) when str1 = str2 ->
      Some(bindings)
  
  (* Call matching *)
  | Call(func1, args1), Call(func2, args2) ->
      match_expr func1 func2 bindings >>= fun bindings ->
      match_exprs args1 args2 bindings
  
  (* Ellipsis: match zero or more items *)
  | Ellipsis, _ -> Some(bindings)
  
  (* Default: no match *)
  | _ -> None
```

**Optimizations:**
1. **Early Failure** - Stop if bindings are inconsistent
2. **Indexing** - Index AST by node type for faster lookup
3. **Caching** - Cache pattern compilation

---

## 📊 Performance Characteristics

### Why Semgrep is Fast:

1. **Single-File Analysis**
   - No cross-file dependencies
   - Parallel file processing

2. **Incremental Matching**
   - Only visit relevant node types
   - Skip entire subtrees when possible

3. **Optimized Pattern Compilation**
   - Pre-compile patterns to matching functions
   - Reuse across files

4. **Language Parser Performance**
   - Tree-sitter parsers are fast (C-based)
   - Incremental parsing where possible

**Time Complexity:**
- **Parsing**: O(n) per file
- **Matching**: O(m × p) where m = AST nodes, p = patterns
- **Total**: O(files × (n + m × p))

**In Practice:**
- Scans 1000 files in seconds
- Handles large codebases efficiently

---

## 🎨 Design Patterns Used

### 1. **Strategy Pattern** (Language Parsers)

```python
class ParserStrategy:
    def parse(self, source): pass
    def to_generic(self, ast): pass

class PythonParser(ParserStrategy):
    def parse(self, source):
        return tree_sitter_python.parse(source)

class JavaScriptParser(ParserStrategy):
    def parse(self, source):
        return tree_sitter_javascript.parse(source)
```

### 2. **Visitor Pattern** (AST Traversal)

```ocaml
(* Traverse AST during pattern matching *)
let rec traverse_ast node pattern =
  (* Try to match at this node *)
  match_expr pattern node >>= fun matches ->
  
  (* Recursively check children *)
  List.fold_left (fun acc child ->
    traverse_ast child pattern :: acc
  ) [matches] (children node)
```

### 3. **Chain of Responsibility** (Rule Evaluation)

```python
class PatternMatcher:
    def match(self, rule, ast):
        # Chain patterns together
        for pattern_group in rule.patterns:
            if not self.match_pattern_group(pattern_group, ast):
                return None  # Chain breaks
        return True  # All patterns matched
```

---

## 💡 Building Your Own: GRACE Pattern Matcher

Based on Semgrep's architecture:

### Step 1: Generic AST Definition

```python
from dataclasses import dataclass
from typing import Optional, List, Union

@dataclass
class Location:
    file: str
    line: int
    column: int

class GenericAST:
    """Generic AST node - works across languages"""
    pass

@dataclass
class CallExpr(GenericAST):
    func: GenericAST
    args: List[GenericAST]
    location: Location

@dataclass
class NameExpr(GenericAST):
    name: str
    location: Location

@dataclass
class ImportExpr(GenericAST):
    module: str
    location: Location
```

### Step 2: Pattern Matching Engine

```python
from typing import Dict, Optional

class PatternMatcher:
    """Match patterns against generic AST"""
    
    def __init__(self):
        self.bindings: Dict[str, GenericAST] = {}
    
    def match(self, pattern: GenericAST, target: GenericAST) -> bool:
        """Match pattern against target AST"""
        if isinstance(pattern, Metavariable):
            # Bind metavariable
            var_name = pattern.name
            if var_name in self.bindings:
                return self.same_ast(self.bindings[var_name], target)
            else:
                self.bindings[var_name] = target
                return True
        
        if isinstance(pattern, CallExpr) and isinstance(target, CallExpr):
            # Match function and arguments
            return (self.match(pattern.func, target.func) and
                    self.match_list(pattern.args, target.args))
        
        # Exact match for literals
        return pattern == target
```

### Step 3: GRACE-Specific Rules

```python
class GraceRule:
    """GRACE-specific pattern rules"""
    
    def __init__(self):
        self.rules = [
            {
                'id': 'unsafe-vector-query',
                'pattern': CallExpr(
                    func=NameExpr('qdrant_client.query'),
                    args=[Metavariable('$USER_INPUT')]
                ),
                'message': 'Unsanitized vector database query',
                'severity': 'HIGH'
            },
            {
                'id': 'missing-error-handling',
                'pattern': CallExpr(
                    func=NameExpr('$FUNC'),
                    args=[Ellipsis()]
                ),
                'message': 'Function call without error handling',
                'severity': 'MEDIUM'
            }
        ]
```

---

## 🔬 Key Files to Study

### Must-Read Files (in order):

1. **`libs/ast_generic/AST_generic.ml`**
   - Generic AST definition
   - Core data structure

2. **`src/matching/Generic_vs_generic.ml`**
   - Core matching algorithm
   - How patterns match AST

3. **`src/engine/Match_rules.ml`**
   - Rule execution
   - Pattern group evaluation

4. **`semgrep/semgrep/rule.py`**
   - Rule parsing (Python)
   - YAML rule format

5. **`parsing/Parse_target.ml`**
   - Language parsing
   - Converting to generic AST

---

## 🎓 Key Insights for GRACE

### What to Borrow:

1. **Generic AST Pattern**
   - Convert all code to common format
   - Write rules once, work everywhere

2. **Structural Pattern Matching**
   - More precise than text matching
   - Understands code structure

3. **Rule-Based System**
   - Easy to add new patterns
   - YAML-based rule definitions

4. **Fast Execution**
   - Single-file analysis
   - Parallel processing

### What to Adapt:

1. **GRACE-Specific Patterns**
   - Vector database queries
   - Cognitive layer checks
   - Memory mesh operations

2. **Integration with GRACE**
   - Cognitive layer integration
   - Learning from patterns
   - Self-improvement

---

## 📚 References

- **Semgrep GitHub**: https://github.com/semgrep/semgrep
- **Semgrep Docs**: https://semgrep.dev/docs
- **Pattern Syntax**: https://semgrep.dev/docs/writing-rules/pattern-syntax
- **Tree-sitter**: https://tree-sitter.github.io/tree-sitter/

---

**Last Updated:** 2026-01-16
