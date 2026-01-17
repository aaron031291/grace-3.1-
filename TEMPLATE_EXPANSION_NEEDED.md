# Template Knowledge Expansion - CRITICAL NEED ✅

## 🚨 **Current Problem**

**Template Performance:**
- **189 template matches** out of 500 problems (37.8% coverage)
- **Only 37 passed** (19.6% success rate!)
- **152 failed** (80.4% failure rate)

**Main Issues:**
1. **50 AssertionErrors** - Templates have wrong logic
2. **17 Parameter mismatches** - Wrong parameter inference
3. **Low coverage** - Only 37.8% of problems matched

## 📊 **What Needs to Happen**

### **1. Fix Existing Templates (HIGH PRIORITY)**

**Problem:** 50 AssertionErrors = templates matched but code is wrong

**Examples:**
- `binary_to_decimal` - Template returns wrong result
- `find_missing` - Logic doesn't match test cases
- `find_Sum` - Missing parameter handling

**Action:**
- Analyze each failing template
- Fix the logic to match test cases
- Re-run tests to verify fixes

### **2. Improve Parameter Inference (MEDIUM PRIORITY)**

**Problem:** 17 parameter mismatches

**Examples:**
- `find_Sum(arr, n)` - Template only takes `arr`
- Functions need multiple parameters but templates infer wrong

**Action:**
- Improve `_infer_parameters()` in template learning system
- Better extraction from test cases
- Handle multiple parameters correctly

### **3. Expand Template Library (HIGH PRIORITY)**

**Problem:** Only 189/500 matches (37.8% coverage)

**Action:**
- Use reversed KNN to analyze 463 failures
- Generate templates for unmatched problems
- Target: 70%+ coverage

### **4. Improve Template Matching (MEDIUM PRIORITY)**

**Problem:** Templates may be matching wrong problems

**Action:**
- Review matching confidence thresholds
- Improve keyword extraction
- Better test case pattern matching

## 🎯 **Immediate Action Plan**

### **Step 1: Fix Failing Templates**
```bash
# Analyze which templates are failing
python scripts/analyze_template_failures.py

# Fix templates with AssertionErrors
# Update template_code in mbpp_templates.py
```

### **Step 2: Run Reversed KNN on Failures**
```bash
# Generate new templates from 463 failures
python scripts/auto_improve_from_failures.py

# Add high-confidence templates
python scripts/add_learned_templates.py 0.4
```

### **Step 3: Improve Parameter Inference**
- Update `_infer_parameters()` in template_learning_system.py
- Better test case analysis
- Handle edge cases

### **Step 4: Re-evaluate**
```bash
# Test improvements
python scripts/run_full_mbpp.py
```

## 📈 **Expected Improvements**

**Current:**
- Coverage: 37.8% (189/500)
- Success rate: 19.6% (37/189)
- Overall pass: 7.4% (37/500)

**Target:**
- Coverage: 70%+ (350+/500)
- Success rate: 60%+ (210+/350)
- Overall pass: 40%+ (200+/500)

## 🔧 **Specific Fixes Needed**

### **1. Binary to Decimal Template**
**Current:** `return int(bin(n)[2:])` - WRONG (converts decimal to binary string, then to int)
**Should be:** `return int(str(n), 2)` - Convert binary string to decimal

### **2. Find Missing Template**
**Current:** Uses sum formula but doesn't match test case logic
**Should be:** Check for missing number in sequence

### **3. Find Sum Template**
**Current:** Missing second parameter `n`
**Should be:** Handle both `arr` and `n` parameters

---

**Status**: ✅ YES - Template knowledge expansion is CRITICAL  
**Priority**: HIGH - Current 7.4% pass rate is unacceptable  
**Next Step**: Fix failing templates + Run reversed KNN analysis
