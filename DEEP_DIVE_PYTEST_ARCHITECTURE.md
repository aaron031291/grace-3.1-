# Deep Dive: pytest Architecture Analysis
## Understanding AST Transformation and Test Framework Design

pytest uses AST transformation to provide better error messages and advanced testing features. This guide explains how it rewrites code at import time.

---

## 🎯 Overview: pytest's AST Transformation

pytest's key innovation: **Assertion Rewriting**
- Transform `assert` statements at import time
- Better error messages (show actual values)
- Non-intrusive (only transforms test files)

---

## 📁 Core Architecture

### 1. **Import Hooks** (Intercepting Imports)

**Location**: `src/_pytest/assertion/rewrite.py`

**How Import Hooks Work:**

Python's import system has a hook mechanism:
```python
# When you import a module:
import my_test_module

# Python checks sys.meta_path for importers
# pytest installs a custom importer
```

**pytest's Import Hook:**
```python
class AssertionRewritingHook:
    """Custom import hook that rewrites assertions"""
    
    def find_spec(self, name, path, target=None):
        """Called when Python tries to import a module"""
        # Check if this is a test module
        if self.is_test_module(name):
            # Return spec that will rewrite the module
            return ModuleSpec(
                name=name,
                loader=self,
                origin=path
            )
        return None  # Let other importers handle it
    
    def create_module(self, spec):
        """Create the module (but don't load yet)"""
        return None  # Use default module creation
    
    def exec_module(self, module):
        """Execute the module code (with rewriting)"""
        # 1. Read source code
        source = self.get_source(module.__spec__.origin)
        
        # 2. Parse to AST
        tree = ast.parse(source, filename=module.__spec__.origin)
        
        # 3. Transform AST
        tree = self.rewrite_asserts(tree)
        
        # 4. Compile and execute
        code = compile(tree, module.__spec__.origin, 'exec')
        exec(code, module.__dict__)
```

**Installation:**
```python
# During pytest initialization
sys.meta_path.insert(0, AssertionRewritingHook())
```

---

### 2. **AST Transformation** (Rewriting Assertions)

**Location**: `src/_pytest/assertion/rewrite.py`

**What Gets Transformed:**

**Original Code:**
```python
def test_example():
    assert x == y
```

**Transformed Code:**
```python
def test_example():
    if not (x == y):
        # Generate detailed error message
        raise AssertionError(
            f"assert {repr(x)} == {repr(y)}\n"
            f"  x = {repr(x)}\n"
            f"  y = {repr(y)}"
        )
```

**Transformation Algorithm:**
```python
class AssertionRewriter(ast.NodeTransformer):
    """Transforms assert statements to detailed checks"""
    
    def visit_Assert(self, node):
        """Transform assert statement"""
        # Original: assert condition, message
        
        # Extract condition and message
        condition = node.test
        
        # Transform condition to detailed check
        detailed_check = self.build_detailed_check(condition)
        
        # Create if statement
        if_node = ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=condition),
            body=[
                # Raise detailed AssertionError
                ast.Raise(
                    exc=self.build_assertion_error(condition),
                    cause=None
                )
            ],
            orelse=[]
        )
        
        return if_node
    
    def build_detailed_check(self, condition):
        """Build detailed check that shows values"""
        # For complex expressions, extract sub-expressions
        # e.g., a + b → evaluate separately to show values
        
        if isinstance(condition, ast.Compare):
            # Compare: a == b
            left = condition.left
            ops = condition.ops
            comparators = condition.comparators
            
            # Extract values for error message
            left_value = self.extract_value(left)
            right_value = self.extract_value(comparators[0])
            
            return DetailedCompare(left_value, ops[0], right_value)
        
        # ... handle other expression types
```

**Key Insight:**
- AST transformation happens **before** code execution
- Transformed code is compiled and executed
- Original source remains unchanged

---

### 3. **Detailed Assertion Messages**

**How Detailed Messages Are Generated:**

**Simple Assertion:**
```python
assert x == y
```

**Transformed:**
```python
if not (x == y):
    # Show both values
    raise AssertionError(
        f"assert {x!r} == {y!r}\n"
        f"  where {x!r} = {x}\n"
        f"  where {y!r} = {y}"
    )
```

**Complex Assertion:**
```python
assert result.status_code == 200 and result.data == expected
```

**Transformed:**
```python
# Extract each part
@py_assert0 = result.status_code
@py_assert1 = result.data
@py_assert2 = (result.status_code == 200)
@py_assert3 = (result.data == expected)
@py_assert4 = (@py_assert2 and @py_assert3)

if not @py_assert4:
    raise AssertionError(
        f"assert ({result.status_code!r} == 200 and {result.data!r} == {expected!r})\n"
        f"  where result.status_code = {result.status_code}\n"
        f"  where result.data = {result.data}\n"
        f"  where expected = {expected}"
    )
```

**Value Extraction:**
```python
def extract_value(self, expr):
    """Extract value for error message"""
    if isinstance(expr, ast.Name):
        # Variable: use variable name
        return VariableReference(expr.id)
    
    elif isinstance(expr, ast.Attribute):
        # Attribute: obj.attr
        obj = self.extract_value(expr.value)
        return AttributeReference(obj, expr.attr)
    
    elif isinstance(expr, ast.Call):
        # Function call: func(args)
        func = self.extract_value(expr.func)
        args = [self.extract_value(arg) for arg in expr.args]
        return CallReference(func, args)
    
    # ... handle other expression types
```

---

### 4. **Plugin System** (Extensible Architecture)

**Location**: `src/_pytest/plugin.py`

**How Plugins Work:**

**Plugin Discovery:**
```python
def discover_plugins():
    """Discover and load plugins"""
    plugins = []
    
    # 1. Built-in plugins (in pytest package)
    plugins.extend(load_package_plugins('_pytest'))
    
    # 2. Installed plugins (setuptools entry points)
    plugins.extend(load_entry_point_plugins('pytest11'))
    
    # 3. File-based plugins (conftest.py)
    plugins.extend(load_conftest_plugins())
    
    return plugins
```

**Hook System:**
```python
class HookRegistry:
    """Registry for pytest hooks"""
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register(self, hook_name: str, func: Callable):
        """Register a hook function"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(func)
    
    def call(self, hook_name: str, **kwargs):
        """Call all registered hooks"""
        if hook_name in self.hooks:
            for func in self.hooks[hook_name]:
                result = func(**kwargs)
                # Process result based on hook type
                # (some hooks allow modifying results)
        return result
```

**Example Plugin:**
```python
@pytest.hookimpl
def pytest_collection_modifyitems(config, items):
    """Modify test items after collection"""
    # Add markers based on test names
    for item in items:
        if 'slow' in item.name:
            item.add_marker(pytest.mark.slow)
```

---

## 🔍 Detailed Code Walkthrough

### Example: Transforming `assert a == b`

**Original AST:**
```python
ast.Assert(
    test=ast.Compare(
        left=ast.Name(id='a'),
        ops=[ast.Eq()],
        comparators=[ast.Name(id='b')]
    ),
    msg=None
)
```

**Transformation Steps:**

1. **Extract Comparison Parts:**
   ```python
   left = ast.Name(id='a')
   op = ast.Eq()
   right = ast.Name(id='b')
   ```

2. **Create Detailed Error Message:**
   ```python
   error_msg = ast.JoinedStr(
       values=[
           ast.Constant(value="assert "),
           format_expr(left),  # 'a'
           ast.Constant(value=" == "),
           format_expr(right),  # 'b'
           ast.Constant(value="\n  where a = "),
           format_value(left),  # actual value of a
           ast.Constant(value="\n  where b = "),
           format_value(right)  # actual value of b
       ]
   )
   ```

3. **Create If Statement:**
   ```python
   ast.If(
       test=ast.UnaryOp(
           op=ast.Not(),
           operand=original_compare
       ),
       body=[
           ast.Raise(
               exc=ast.Call(
                   func=ast.Name(id='AssertionError'),
                   args=[error_msg]
               )
           )
       ]
   )
   ```

**Result:**
```python
if not (a == b):
    raise AssertionError(
        f"assert {a!r} == {b!r}\n"
        f"  where a = {a}\n"
        f"  where b = {b}"
    )
```

---

## 🎨 Design Patterns Used

### 1. **AST Visitor Pattern** (Transformation)

```python
class ASTTransformer(ast.NodeTransformer):
    """Base class for AST transformations"""
    
    def visit_Assert(self, node):
        # Transform assert nodes
        return transformed_node
    
    def generic_visit(self, node):
        # Visit children recursively
        return super().generic_visit(node)
```

### 2. **Import Hook Pattern** (Code Interception)

```python
class CustomImporter:
    """Intercept imports and transform code"""
    
    def find_spec(self, name, path, target=None):
        # Decide if we should handle this import
        return spec if should_handle else None
    
    def exec_module(self, module):
        # Transform and execute module
        pass
```

### 3. **Plugin Registry Pattern** (Extensibility)

```python
class PluginRegistry:
    """Register and invoke plugins"""
    
    def register(self, hook_name, func):
        # Add to registry
        pass
    
    def call(self, hook_name, **kwargs):
        # Invoke all registered functions
        pass
```

---

## 💡 Building Your Own: GRACE Code Transformer

Based on pytest's architecture:

### Step 1: Import Hook

```python
import sys
import ast

class GraceCodeTransformer:
    """Transform GRACE code at import time"""
    
    def __init__(self):
        self.transformations = []
    
    def find_spec(self, name, path, target=None):
        """Intercept imports"""
        if self.should_transform(name):
            return importlib.util.spec_from_loader(
                name,
                self,
                origin=self.find_origin(name)
            )
        return None
    
    def exec_module(self, module):
        """Transform and execute module"""
        source = self.get_source(module.__spec__.origin)
        tree = ast.parse(source)
        
        # Apply transformations
        for transform in self.transformations:
            tree = transform(tree)
        
        code = compile(tree, module.__spec__.origin, 'exec')
        exec(code, module.__dict__)
```

### Step 2: GRACE-Specific Transformations

```python
class GraceTransformer(ast.NodeTransformer):
    """GRACE-specific AST transformations"""
    
    def visit_Call(self, node):
        """Transform function calls for monitoring"""
        # Wrap in monitoring code
        # e.g., track cognitive layer calls
        
        if self.is_cognitive_call(node):
            return self.wrap_with_monitoring(node)
        
        return self.generic_visit(node)
    
    def visit_Import(self, node):
        """Track imports for dependency analysis"""
        # Record imports for Genesis key tracking
        
        self.record_import(node)
        return self.generic_visit(node)
```

---

## 🔬 Key Files to Study

### Must-Read Files (in order):

1. **`src/_pytest/assertion/rewrite.py`**
   - AST transformation logic
   - Import hook implementation

2. **`src/_pytest/assertion/util.py`**
   - Value formatting utilities
   - Error message generation

3. **`src/_pytest/plugin.py`**
   - Plugin system
   - Hook registry

4. **`src/_pytest/python.py`**
   - Test discovery
   - Test execution

---

## 🎓 Key Insights for GRACE

### What to Borrow:

1. **AST Transformation**
   - Transform code at import time
   - Non-intrusive (doesn't modify source)

2. **Import Hooks**
   - Intercept and transform modules
   - Selective transformation

3. **Plugin System**
   - Extensible architecture
   - Hook-based design

### What to Adapt:

1. **GRACE-Specific Transformations**
   - Cognitive layer monitoring
   - Memory mesh tracking
   - Genesis key logging

2. **Integration with GRACE**
   - Transform only GRACE modules
   - Integrate with learning system
   - Use for debugging and analysis

---

## 📚 References

- **pytest GitHub**: https://github.com/pytest-dev/pytest
- **pytest Docs**: https://docs.pytest.org/
- **Python Import System**: https://docs.python.org/3/reference/import.html
- **AST Module**: https://docs.python.org/3/library/ast.html

---

**Last Updated:** 2026-01-16
