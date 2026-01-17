# Tool Code Study Guide

This guide helps you study the cloned repositories.

## Recommended Study Order

Study these tools in order for best learning:

### 1. BANDIT

- **Description**: Python security scanner (simplest to understand)
- **Language**: Python
- **Key Files to Study**:
  - `bandit/core/visitor.py`
  - `bandit/core/tester.py`
  - `bandit/plugins/blacklist_calls.py`

**How to explore**:
```bash
cd bandit
# Read the README first
cat README.md | less
# Then explore the key files listed above
```

### 2. SEMGREP

- **Description**: Pattern-based static analysis (fast, easy to understand)
- **Language**: OCaml (core) + Python (CLI)
- **Key Files to Study**:
  - `src/engine/Match_rules.ml`
  - `src/matching/Generic_vs_generic.ml`
  - `libs/ast_generic/AST_generic.ml`

**How to explore**:
```bash
cd semgrep
# Read the README first
cat README.md | less
# Then explore the key files listed above
```

### 3. PYTEST

- **Description**: Test framework with AST transformation
- **Language**: Python
- **Key Files to Study**:
  - `src/_pytest/assertion/rewrite.py`
  - `src/_pytest/assertion/util.py`
  - `src/_pytest/plugin.py`

**How to explore**:
```bash
cd pytest
# Read the README first
cat README.md | less
# Then explore the key files listed above
```

### 4. CODEQL

- **Description**: Semantic code analysis (data flow, taint tracking)
- **Language**: QL (query language)
- **Key Files to Study**:
  - `ql/queries/security/cwe/SqlInjection.ql`
  - `ql/<language>/src/DataFlow.qll`
  - `ql/<language>/src/Ast.qll`

**How to explore**:
```bash
cd codeql
# Read the README first
cat README.md | less
# Then explore the key files listed above
```

### 5. SONARQUBE

- **Description**: Code quality platform (full-featured, complex)
- **Language**: Java + JavaScript
- **Key Files to Study**:
  - `server/sonar-core/src/main/java/org/sonar/core/issue/`
  - `sonar-plugin-api/src/main/java/org/sonar/api/`

**How to explore**:
```bash
cd sonarqube
# Read the README first
cat README.md | less
# Then explore the key files listed above
```

## Learning Path

1. **Bandit** - Start here (simplest AST visitor pattern)
2. **Semgrep** - Pattern matching (more complex)
3. **pytest** - AST transformation (advanced)
4. **CodeQL** - Semantic analysis (expert level)
5. **SonarQube** - Full platform (most complex)

## Tips

- Start with the README in each repository
- Focus on one key file at a time
- Use code search (ripgrep, grep) to find related code
- Read tests - they show how the code works
- Build small prototypes based on what you learn

