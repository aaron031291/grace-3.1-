# Genesis Keys Diagnosis Summary

## What Genesis Keys Revealed

### The Problem: 50% → 0% Regression

**Genesis Keys Analysis Shows**:
1. **489 Function Name Errors** (97.8% of failures)
2. **Code generating `solve_task` instead of correct names**
3. **Function name extraction failing silently**

### Root Cause Found

The `fix_function_name_extraction.py` utility was **only replacing `def to()`** but NOT replacing `def solve_task()` or other wrong function names.

**Code Issue**:
```python
# OLD CODE - Only fixed 'to'
if current_name != correct_function_name and current_name == 'to':
    fixed = code.replace(f'def {current_name}(', f'def {correct_function_name}(')
```

This meant:
- ✅ `def to()` → Fixed
- ❌ `def solve_task()` → NOT Fixed (489 errors!)
- ❌ Any other wrong name → NOT Fixed

## Fixes Applied

### 1. Enhanced Function Name Replacement
**File**: `backend/benchmarking/fix_function_name_extraction.py`

**Change**: Now replaces ANY incorrect function name, not just 'to'

```python
# NEW CODE - Fixes ANY wrong name
if current_name != correct_function_name:
    fixed = re.sub(
        r'def\s+' + re.escape(current_name) + r'\s*\(',
        f'def {correct_function_name}(',
        code,
        count=1
    )
```

### 2. More Robust Function Name Extraction
**File**: `backend/benchmarking/mbpp_parallel_integration.py`

**Changes**:
- Multiple regex patterns to find function names
- Skips common non-function words (assert, print, len, etc.)
- More thorough search through test cases

### 3. Explicit Function Name in Prompts
**File**: `backend/benchmarking/mbpp_parallel_integration.py`

**Change**: Made function name requirement CRITICAL and explicit

```python
# OLD: "Function name should be: {function_name}"
# NEW: "CRITICAL REQUIREMENT: The function MUST be named exactly: {function_name}"
```

### 4. Always Fix Function Names
**File**: `backend/benchmarking/mbpp_parallel_integration.py`

**Change**: Ensure function name fixing always happens, even if extraction initially fails

## Expected Impact

### Before Fixes:
- **Pass Rate**: 0% (0/500)
- **Function Name Errors**: 489
- **Root Cause**: `solve_task` not being replaced

### After Fixes:
- **Expected Pass Rate**: 20-40%+ (fixing 489 function name errors)
- **Function Name Errors**: Should drop to near 0
- **Remaining Issues**: Logic errors, edge cases, etc.

## How Genesis Keys Helped

### 1. Error Pattern Tracking
Genesis Keys tracked that:
- NameError was the dominant error type
- Function name mismatches were systematic
- Errors appeared after recent code changes

### 2. Code Change History
Genesis Keys can show:
- When function name extraction was added
- When it might have been broken
- What files were modified around regression time

### 3. Diagnostic Capability
Genesis Keys enable:
- Querying for specific error patterns
- Finding code changes that introduced bugs
- Tracking fix effectiveness over time

## Next Steps

1. ✅ **Fixed**: Function name replacement now handles all wrong names
2. ✅ **Fixed**: More robust function name extraction
3. ✅ **Fixed**: Explicit prompts for function names
4. ⏳ **Pending**: Re-run MBPP evaluation to verify fixes
5. ⏳ **Future**: Use Genesis Keys to prevent regressions automatically

## Prevention Strategy

### Using Genesis Keys for Regression Prevention

1. **Pre-Commit Checks**:
   - Query Genesis Keys for recent NameError patterns
   - Alert if function name errors spike
   - Block commits that introduce known error patterns

2. **Continuous Monitoring**:
   - Track error rates over time
   - Alert on performance regressions
   - Correlate errors with code changes

3. **Automated Fixes**:
   - When Genesis Keys detect function name errors
   - Automatically apply fix_function_name_in_code
   - Verify fix before marking complete

## Key Learnings

1. **Default Values Are Dangerous**: `solve_task` as default masked extraction failures
2. **Partial Fixes Don't Work**: Fixing only `def to()` missed `def solve_task()`
3. **Genesis Keys Provide Visibility**: Can track exactly what broke and when
4. **Explicit > Implicit**: Making function name CRITICAL in prompts helps LLMs

## Conclusion

Genesis Keys revealed that:
- The regression was caused by incomplete function name fixing
- 489 errors were all the same issue: `solve_task` not being replaced
- Fixing this one issue should restore significant performance

The fixes ensure:
- ✅ ANY wrong function name gets replaced
- ✅ Function name extraction is more robust
- ✅ Prompts are explicit about requirements
- ✅ Post-processing always runs

**Expected Result**: Pass rate should jump from 0% to 20-40%+ immediately.
