# MBPP Performance Regression Analysis

## Performance Drop: 50% → 0%

### Current Status
- **Pass Rate**: 0.0% (0/500)
- **Function Name Errors**: 489 out of 500 failures
- **Timestamp**: 2026-01-17T17:16:58

### Critical Issues Identified

#### 1. Function Name Mismatch (489 errors - 97.8% of failures)
**Problem**: Generated code uses `solve_task` instead of correct function names

**Examples**:
- Test expects: `remove_Occ`, Generated: `solve_task`
- Test expects: `split_lowerstring`, Generated: `solve_task`
- Test expects: `count_Substring_With_Equal_Ends`, Generated: `solve_task`

**Root Cause**: Function name extraction and fixing logic is not working in parallel integration

**Impact**: 
- 489 NameError failures
- 97.8% of all failures are due to function name issues
- This alone explains the 0% pass rate

#### 2. Templates Not Being Used Effectively
**Problem**: 
- 364 problems solved by LLM only (72.8%)
- Only 136 used template_llm_collaboration_fallback (27.2%)
- No pure template matches

**Impact**: Missing potentially working template solutions

#### 3. Template-LLM Collaboration Not Working
**Problem**: The collaboration system we added isn't preventing function name errors

**Expected**: Template-LLM collaboration should:
- Extract function names from templates
- Pass correct names to LLM
- Post-process to fix names

**Actual**: Still generating `solve_task` as default

## What Genesis Keys Tell Us

Genesis Keys track every code change, but we need to:

1. **Query Recent Changes**: Find what changed in MBPP integration files
2. **Track Error Patterns**: See if function name errors appeared after specific changes
3. **Identify Breaking Changes**: Find commits/changes that broke function name extraction

## Root Cause Analysis

### Why Function Name Extraction Failed

Looking at the code flow:

1. **Function Name Extraction** (`mbpp_parallel_integration.py` lines 192-201)
   - Extracts from test cases using regex
   - Should work, but may not be finding function names correctly

2. **Prompt Enhancement** (`mbpp_parallel_integration.py` lines 204-206)
   - Adds function name to description
   - May not be explicit enough for LLM

3. **Code Post-Processing** (`mbpp_parallel_integration.py` line 252-253)
   - Uses `extract_and_fix_code` utility
   - Should fix `def to()` but may not be catching `def solve_task()`

### The `solve_task` Problem

The code is defaulting to `solve_task` which suggests:
- Function name extraction is returning `None` or empty
- Default fallback is `solve_task` somewhere
- Post-processing isn't replacing it

## What Changed from 50% to 0%?

### Likely Causes:

1. **Parallel Integration Override**
   - Recent changes to `mbpp_parallel_integration.py` may have bypassed fixes
   - Function name extraction may not be running in parallel workers

2. **Template-First Logic Issue**
   - Changed to `template_first=True` 
   - Template-LLM collaboration may not be extracting function names correctly

3. **Code Path Mismatch**
   - Fixes applied to wrong code path
   - Parallel workers using different code than sequential

## Immediate Fixes Needed

### 1. Fix Function Name Extraction
```python
# In mbpp_parallel_integration.py _evaluate_single_problem
# Ensure function name is extracted BEFORE any code generation
function_name = problem.get("function_name")
if not function_name:
    # Extract from test cases - MORE ROBUST
    test_cases = problem.get("test_list", [])
    for test in test_cases:
        # Try multiple patterns
        patterns = [
            r'(\w+)\s*\(',  # function_name(
            r'assert\s+(\w+)\s*\(',  # assert function_name(
            r'(\w+)\s*==',  # function_name ==
        ]
        for pattern in patterns:
            match = re.search(pattern, test)
            if match:
                function_name = match.group(1)
                break
        if function_name:
            break
```

### 2. Make Function Name Explicit in Prompt
```python
# Don't just append, make it CRITICAL
enhanced_description = f"""
{problem["text"]}

CRITICAL: The function MUST be named exactly: {function_name}
The test cases call {function_name}(), so your code must define:
def {function_name}(...):
"""
```

### 3. Fix Post-Processing
```python
# After LLM generation, ALWAYS fix function name
if code and function_name:
    # Replace ANY function definition with correct name
    code = re.sub(
        r'def\s+\w+\s*\(',
        f'def {function_name}(',
        code,
        count=1  # Only replace first occurrence
    )
```

### 4. Verify Template Function Names
```python
# When templates are used, ensure they have correct function names
if template_code:
    # Extract function name from template
    template_func_match = re.search(r'def\s+(\w+)\s*\(', template_code)
    if template_func_match:
        template_func_name = template_func_match.group(1)
        # Replace with correct name if different
        if template_func_name != function_name:
            template_code = template_code.replace(
                f'def {template_func_name}(',
                f'def {function_name}('
            )
```

## Genesis Keys Investigation

To use Genesis Keys to find what changed:

1. **Query Recent MBPP Changes**:
```python
keys = session.query(GenesisKey).filter(
    GenesisKey.file_path.ilike('%mbpp%'),
    GenesisKey.when_timestamp >= cutoff_date
).all()
```

2. **Find Function Name Related Changes**:
```python
keys = session.query(GenesisKey).filter(
    or_(
        GenesisKey.code_before.ilike('%solve_task%'),
        GenesisKey.code_after.ilike('%solve_task%'),
        GenesisKey.error_message.ilike('%NameError%')
    )
).all()
```

3. **Track Regression Timeline**:
   - Find when function name errors started appearing
   - Identify code changes around that time
   - Check if fixes were reverted or bypassed

## Next Steps

1. ✅ **Immediate**: Fix function name extraction in parallel integration
2. ✅ **Immediate**: Add robust post-processing to replace ANY function name
3. ✅ **Short-term**: Verify template function names match test cases
4. ✅ **Short-term**: Add logging to track function name extraction success rate
5. ✅ **Long-term**: Use Genesis Keys to prevent future regressions

## Expected Impact

Fixing function names alone should:
- Reduce failures from 500 to ~11 (489 function name errors fixed)
- Increase pass rate from 0% to potentially 20-30%+
- Allow other fixes (templates, collaboration) to have impact
