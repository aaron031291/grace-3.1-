# Proven Testing, Debugging & Bug-Fixing Tools for GRACE

Based on research from GitHub, research papers, and industry best practices, here are the **most proven tools** to make your system bug-free.

---

## 🏆 Top Recommendations for Python/FastAPI Projects

### 1. **Pytest Ecosystem** (You already have this ✅)
- **pytest** - Core testing framework
- **pytest-cov** - Coverage reporting (already in requirements)
- **pytest-asyncio** - For async FastAPI endpoints
- **pytest-mock** - Better mocking capabilities
- **pytest-xdist** - Parallel test execution
- **pytest-timeout** - Prevent hanging tests
- **pytest-benchmark** - Performance regression testing

**Add to requirements.txt:**
```txt
pytest-asyncio>=0.21.0,<0.24.0
pytest-mock>=3.12.0,<3.14.0
pytest-xdist>=3.5.0,<3.6.0
pytest-timeout>=2.2.0,<2.3.0
pytest-benchmark>=4.0.0,<4.1.0
```

---

## 🔍 Static Analysis & Bug Detection (GitHub-Proven)

### **Semgrep** ⭐ 17,000+ GitHub Stars
**Why it's proven:**
- Fast, pattern-based static analysis
- Low false positive rate
- Supports 30+ languages including Python
- Great for security vulnerabilities and common bugs
- Integrates with GitHub Actions

**Install:**
```bash
pip install semgrep
# Or use Docker
docker pull returntocorp/semgrep
```

**Usage:**
```bash
# Scan entire codebase
semgrep --config=auto backend/

# Python-specific rules
semgrep --config=p/python backend/

# Security-focused
semgrep --config=p/security-audit backend/
```

**GitHub Action:**
```yaml
- uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      p/python
      p/security-audit
```

**GitHub:** https://github.com/semgrep/semgrep

---

### **CodeQL (GitHub Advanced Security)** ⭐ 8,500+ Stars
**Why it's proven:**
- Semantic code analysis (understands code structure)
- Powers GitHub Copilot Autofix
- Detects SQL injection, XSS, and 100+ vulnerability types
- Free for public repos, available for private

**GitHub Action (Free for public repos):**
```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v2
  with:
    languages: python

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v2
```

**GitHub:** https://github.com/github/codeql

---

### **Bandit** - Python Security Linter
**Why it's proven:**
- Specifically designed for Python security issues
- Finds SQL injection, shell injection, hardcoded passwords
- Used by major Python projects

**Install:**
```bash
pip install bandit[toml]
```

**Usage:**
```bash
bandit -r backend/ -f json -o bandit-report.json
bandit -r backend/ -ll  # Low and medium severity
```

---

### **Pylint + Flake8 + Black + mypy** - Code Quality
**Why proven:**
- **Pylint** - Comprehensive code analysis
- **Flake8** - Style guide enforcement (PEP 8)
- **Black** - Automatic code formatting
- **mypy** - Static type checking

**Install:**
```bash
pip install pylint flake8 black mypy
```

**Pre-commit hook setup:**
```bash
pip install pre-commit
```

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/pylint-dev/pylint
    rev: v3.0.3
    hooks:
      - id: pylint

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## 🐛 AI-Powered Debugging & Bug Fixing

### **ChatDBG** - AI Debugging Assistant
**Why it's cutting-edge:**
- Integrates with PDB, GDB, LLDB
- AI-powered root cause analysis
- Can generate fixes automatically
- Based on research from UC Berkeley

**Install:**
```bash
pip install chatdbg
```

**Usage:**
```bash
# In your pytest
pytest --pdb  # Drops into PDB on failure
# Then in PDB:
(ChatDBG) why  # AI explains why the failure occurred
(ChatDBG) fix  # AI suggests a fix
```

**GitHub:** https://github.com/plasma-umass/ChatDBG

---

### **GitHub Copilot Autofix** (If using GitHub)
**Why proven:**
- 3× faster remediation overall
- 7× faster for XSS fixes
- 12× faster for SQL injection fixes
- Already integrated with CodeQL

**How to enable:**
1. Enable GitHub Advanced Security
2. Enable Code Scanning
3. Autofix suggestions appear automatically in PRs

---

## 🧪 Advanced Testing Tools

### **Hypothesis** - Property-Based Testing
**Why it's proven:**
- Finds edge cases you never thought of
- Used by major companies (Dropbox, Mozilla)
- Automatically generates test cases
- Finds bugs in production code

**Install:**
```bash
pip install hypothesis
```

**Example:**
```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert add(a, b) == add(b, a)
```

**GitHub:** https://github.com/HypothesisWorks/hypothesis

---

### **Locust** - Load Testing
**Why it's proven:**
- Easy to write load tests in Python
- Distributed load testing
- Real-time metrics and charts
- Find performance bugs before production

**Install:**
```bash
pip install locust
```

**Example:**
```python
from locust import HttpUser, task, between

class GraceAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def retrieve_documents(self):
        self.client.post("/api/retrieve", json={"query": "test"})
```

**GitHub:** https://github.com/locustio/locust

---

### **Fault Localization Tools**

#### **FauxPy** - Fault Localization for pytest
**Why it's proven:**
- Research-backed fault localization
- Ranks suspicious lines based on test coverage
- Multiple techniques (spectrum-based, mutation-based)
- Helps pinpoint where bugs are

**Install:**
```bash
pip install fauxpy
```

**Usage:**
```bash
fauxpy run -- python -m pytest tests/
```

**Paper:** https://arxiv.org/abs/2404.18596

---

## 🔐 Security Scanning

### **Safety** - Dependency Vulnerability Scanner
**Why it's proven:**
- Checks Python dependencies against known vulnerabilities
- Fast and reliable
- Free tier available

**Install:**
```bash
pip install safety
```

**Usage:**
```bash
safety check --json
safety check --file requirements.txt
```

**GitHub:** https://github.com/pyupio/safety

---

### **Gitleaks** - Secret Detection
**Why it's proven:**
- Finds hardcoded secrets, API keys, passwords
- Prevents security breaches
- Used in CI/CD pipelines

**Install:**
```bash
# Download from releases
# Or use Docker
docker pull zricethezav/gitleaks
```

**Usage:**
```bash
gitleaks detect --source . --verbose
```

**GitHub:** https://github.com/gitleaks/gitleaks

---

## 📊 Coverage & Quality Metrics

### **Coverage.py** (Enhanced)
**Why it's proven:**
- Industry standard for Python
- Branch coverage, not just line coverage
- HTML reports

**You already have it!** Enhance with:

**pytest-cov configuration** (add to `pytest.ini`):
```ini
[pytest]
addopts = 
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-branch
    --cov-fail-under=80
```

---

### **SonarQube / SonarCloud** (Enterprise Option)
**Why it's proven:**
- Comprehensive code quality platform
- Tracks technical debt
- Supports 30+ languages
- Free tier available for open source

**SonarCloud:** https://sonarcloud.io (Free for public repos)

---

## 🚀 Recommended Testing Stack for GRACE

Based on your existing setup, here's the **optimal stack**:

### **Phase 1: Immediate (High Impact, Low Effort)**
1. ✅ **pytest** (already have)
2. **Add pytest-asyncio** - For FastAPI async tests
3. **Semgrep** - Quick static analysis setup
4. **Safety** - Check dependencies
5. **Bandit** - Python security scanning

### **Phase 2: Short Term (1-2 weeks)**
1. **Pre-commit hooks** - Catch issues before commit
2. **Hypothesis** - Property-based testing for critical paths
3. **Coverage enforcement** - Fail builds if coverage < 80%
4. **ChatDBG** - AI-assisted debugging

### **Phase 3: Medium Term (1-2 months)**
1. **CodeQL** - Deep semantic analysis (if using GitHub)
2. **Locust** - Load testing for API endpoints
3. **FauxPy** - Fault localization for complex bugs
4. **SonarCloud** - Comprehensive quality tracking

---

## 📝 Quick Start: Add These to Your Project

### 1. Update `requirements-dev.txt`:
```txt
# Testing
pytest>=7.4.0,<8.1.0
pytest-cov>=4.1.0,<5.0.0
pytest-asyncio>=0.21.0,<0.24.0
pytest-mock>=3.12.0,<3.14.0
pytest-xdist>=3.5.0,<3.6.0
pytest-timeout>=2.2.0,<2.3.0
pytest-benchmark>=4.0.0,<4.1.0
hypothesis>=6.92.0,<7.0.0

# Static Analysis
bandit[toml]>=1.7.5,<1.8.0
pylint>=3.0.0,<3.1.0
flake8>=6.1.0,<7.0.0
black>=24.1.0,<25.0.0
mypy>=1.8.0,<1.9.0

# Security
safety>=2.3.5,<3.0.0

# AI Debugging (optional)
chatdbg>=0.1.0,<1.0.0

# Pre-commit
pre-commit>=3.6.0,<4.0.0
```

### 2. Create `pytest.ini`:
```ini
[pytest]
testpaths = backend/tests tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-branch
    --cov-fail-under=75
asyncio_mode = auto
```

### 3. Create `.bandit` config:
```ini
[bandit]
exclude_dirs = tests,venv,__pycache__
skips = B101  # Skip assert_used
```

### 4. GitHub Actions Workflow (`.github/workflows/test.yml`):
```yaml
name: Test & Quality

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: pytest
      
      - name: Security scan (Bandit)
        run: bandit -r backend/
      
      - name: Check dependencies (Safety)
        run: safety check --file backend/requirements.txt
      
      - name: Semgrep scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/python
            p/security-audit
```

---

## 🎯 Tools Proven to Work (Research-Backed)

| Tool | Proof of Effectiveness | Best For |
|------|------------------------|----------|
| **Semgrep** | 17k+ GitHub stars, used by major companies | Static analysis, security |
| **CodeQL** | Powers GitHub's security scanning, 8.5k+ stars | Deep semantic analysis |
| **Hypothesis** | Used by Dropbox, Mozilla, finds real bugs | Property-based testing |
| **ChatDBG** | UC Berkeley research, ~68-75% fix success rate | AI debugging |
| **pytest** | Python standard, used by millions | General testing |
| **FauxPy** | Research paper, fault localization | Bug localization |

---

## 📚 Additional Resources

- **Semgrep Registry**: https://semgrep.dev/r
- **Bandit Checks**: https://bandit.readthedocs.io/
- **Hypothesis Documentation**: https://hypothesis.readthedocs.io/
- **pytest Best Practices**: https://docs.pytest.org/en/stable/

---

## ✅ Next Steps

1. **Install the Phase 1 tools** (Semgrep, Bandit, Safety)
2. **Set up pytest.ini** with coverage requirements
3. **Add GitHub Actions workflow** for automated scanning
4. **Run initial scan** to see current issues
5. **Gradually add Phase 2 tools** as needed

**Recommended order:**
```bash
# 1. Install Phase 1 tools
pip install bandit safety semgrep pytest-asyncio

# 2. Run initial scans
bandit -r backend/
safety check --file backend/requirements.txt
semgrep --config=auto backend/

# 3. Set up pre-commit hooks
pip install pre-commit
pre-commit install

# 4. Run your test suite with coverage
pytest --cov=backend --cov-report=html
```

---

**Last Updated:** 2026-01-16  
**Based on:** GitHub stars, research papers, and industry adoption as of 2024-2026
