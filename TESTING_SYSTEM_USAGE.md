# Testing System Usage Guide

## 🧪 **Overview**

Grace's Testing System provides comprehensive code testing capabilities for generated code. It supports multiple testing methods and automatically falls back if advanced methods aren't available.

---

## 🚀 **Quick Start**

### **Basic Usage**

```python
from cognitive.testing_system import get_testing_system

# Initialize testing system
testing_system = get_testing_system(session=session)

# Test a file
result = testing_system.run_tests("path/to/file.py")

if result["passed"]:
    print(f"✅ All {result['test_count']} tests passed!")
else:
    print(f"❌ {result['failed_count']} tests failed")
    for error in result["errors"]:
        print(f"  - {error}")
```

---

## 📋 **Testing Methods**

The Testing System tries multiple methods in order:

1. **pytest** (if available) - Best for unit tests
2. **unittest** (if available) - Python standard library
3. **Execution Testing** - Runs code and checks for errors
4. **Syntax Checking** - Validates Python syntax (always available)

### **Method Selection**

The system automatically selects the best available method:

```python
result = testing_system.run_tests("file.py")
print(f"Method used: {result['method']}")  # "pytest", "unittest", "execution_test", or "syntax_check"
```

---

## 📊 **Response Format**

### **Success Response**

```python
{
    "passed": True,
    "test_count": 5,
    "passed_count": 5,
    "failed_count": 0,
    "errors": [],
    "method": "pytest"
}
```

### **Failure Response**

```python
{
    "passed": False,
    "test_count": 5,
    "passed_count": 3,
    "failed_count": 2,
    "errors": [
        "test_function_1 FAILED: AssertionError: expected 5, got 4",
        "test_function_2 ERROR: NameError: name 'x' is not defined"
    ],
    "method": "pytest",
    "output": "... full test output ..."
}
```

---

## 🔧 **Failure Analysis**

### **Analyze Failures**

```python
# Get test results
result = testing_system.run_tests("file.py")

if not result["passed"]:
    # Analyze failures
    failures = [{"error": error} for error in result["errors"]]
    analysis = testing_system.fix_failures(failures)
    
    print("Suggestions:")
    for suggestion in analysis["suggestions"]:
        print(f"  - {suggestion}")
```

### **Common Fix Suggestions**

The system provides intelligent suggestions for common errors:

- **Syntax Errors**: Missing colons, indentation issues
- **NameError**: Missing variables or imports
- **TypeError**: Type mismatches
- **AttributeError**: Missing attributes/methods
- **Import Errors**: Missing modules

---

## 💻 **Integration Examples**

### **With Enterprise Coding Agent**

The Testing System is automatically integrated with the Enterprise Coding Agent:

```python
from cognitive.enterprise_coding_agent import get_enterprise_coding_agent

agent = get_enterprise_coding_agent(session=session)

# Generate code
result = agent.generate_code(task)

# Test is automatically run
test_result = result.get("test_result")
if test_result and test_result["passed"]:
    print("✅ Code passed tests!")
```

### **Standalone Testing**

```python
from cognitive.testing_system import TestingSystem

# Create testing system
testing = TestingSystem(session=session)

# Test multiple files
files = ["file1.py", "file2.py", "file3.py"]
results = {}

for file_path in files:
    results[file_path] = testing.run_tests(file_path)

# Summary
total_tests = sum(r["test_count"] for r in results.values())
passed_tests = sum(r["passed_count"] for r in results.values())
failed_tests = sum(r["failed_count"] for r in results.values())

print(f"Total: {total_tests} tests")
print(f"Passed: {passed_tests}")
print(f"Failed: {failed_tests}")
```

---

## 🎯 **Testing Methods Details**

### **1. Pytest (Recommended)**

**Requirements:**
- `pytest` package installed
- Test files follow pytest conventions

**Usage:**
```bash
pip install pytest
```

The system automatically detects and uses pytest if available.

### **2. Unittest (Standard Library)**

**Requirements:**
- Python standard library (always available)
- Test files follow unittest conventions

**Usage:**
No installation needed - uses Python's built-in unittest module.

### **3. Execution Testing**

**What it does:**
- Parses code with AST
- Attempts to execute code
- Catches runtime errors

**Use case:**
- Quick validation when no tests exist
- Syntax + basic execution check

### **4. Syntax Checking**

**What it does:**
- Validates Python syntax
- Always available as fallback

**Use case:**
- Basic validation
- Quick syntax error detection

---

## 🔍 **Error Handling**

### **File Not Found**

```python
result = testing_system.run_tests("nonexistent.py")
# Returns:
{
    "passed": False,
    "test_count": 0,
    "errors": ["File not found: nonexistent.py"],
    "method": "file_check"
}
```

### **Syntax Errors**

```python
result = testing_system.run_tests("syntax_error.py")
# Returns:
{
    "passed": False,
    "errors": ["Syntax error: invalid syntax (line 5)"],
    "method": "syntax_check"
}
```

### **Execution Errors**

```python
result = testing_system.run_tests("runtime_error.py")
# Returns:
{
    "passed": False,
    "errors": ["Execution error: NameError: name 'x' is not defined"],
    "method": "execution_test"
}
```

---

## 📝 **Best Practices**

1. **Use pytest** for comprehensive testing
2. **Write unit tests** for generated code
3. **Check test results** before deploying code
4. **Use failure analysis** to improve code generation
5. **Monitor test coverage** over time

---

## 🔗 **Related Files**

- `backend/cognitive/testing_system.py` - Testing System implementation
- `backend/cognitive/enterprise_coding_agent.py` - Integration with coding agent
- `backend/benchmarking/` - Benchmark testing integration

---

**Last Updated:** Current Session  
**Status:** Testing System fully functional and ready to use
