# Template Fixes Needed - Action Plan

## 🚨 **Critical Issues Found**

### **1. Auto-Learned Templates Have `pass` Statements**

**Problem:** Many auto-learned templates just have `pass` - they match but don't generate code!

**Examples:**
- `auto_binary_convert` - Has `pass` instead of actual code
- `auto_smallest_missing_find_missing` - Likely has `pass`
- Many others from reversed KNN learning

**Fix:** Replace `pass` with actual implementations

### **2. Template Code Quality**

**Current Success Rate:** 19.6% (37/189)
- 50 AssertionErrors = Wrong logic
- 17 Parameter mismatches = Wrong parameters

**Action:** Fix templates one by one based on failure analysis

## 📋 **Immediate Fixes**

### **Fix 1: Auto-Learned Templates**

All templates with `pass` need implementations:

```python
# BEFORE (BROKEN):
template_code="""def to(n):
    # Keywords: binary, convert, decimal
    pass
"""

# AFTER (FIXED):
template_code="""def {function_name}(n):
    \"\"\"Convert binary number to decimal.\"\"\"
    return int(str(n), 2)
"""
```

### **Fix 2: Parameter Inference**

Templates need correct parameter extraction from test cases.

### **Fix 3: Run Reversed KNN Again**

Generate better templates from current failures.

## 🎯 **Next Steps**

1. ✅ **FIXED**: `auto_binary_convert` template
2. **TODO**: Fix all other `pass` templates
3. **TODO**: Run reversed KNN on 463 failures
4. **TODO**: Improve parameter inference
5. **TODO**: Re-evaluate

---

**Status**: In Progress  
**Priority**: HIGH
