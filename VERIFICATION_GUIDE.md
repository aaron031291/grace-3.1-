# Autonomous Feedback Loop - Verification Guide

## 🎯 Quick Verification

Run the verification script to test the complete autonomous feedback loop:

```bash
python scripts/verify_autonomous_loop.py
```

---

## 📋 What the Script Tests

### **1. Trigger Pipeline Handler** ✅
- Verifies `_should_update_llm_knowledge()` method exists
- Verifies `_handle_llm_knowledge_update()` method exists
- Confirms integration into trigger pipeline

### **2. Healing System Genesis Keys** ✅
- Checks for Genesis Keys with `outcome_type: 'healing_outcome'`
- Verifies trust scores and success status
- Confirms metadata structure

### **3. Testing System Genesis Keys** ✅
- Checks for Genesis Keys with `outcome_type: 'test_outcome'`
- Verifies test pass/fail outcomes are tracked
- Confirms test details in metadata

### **4. Diagnostic System Genesis Keys** ✅
- Checks for Genesis Keys with `outcome_type: 'diagnostic_outcome'`
- Verifies severity and anomaly type tracking
- Confirms diagnostic details in metadata

### **5. File Processing Genesis Keys** ✅
- Checks for Genesis Keys with `outcome_type: 'file_processing_outcome'`
- Verifies file type and quality score tracking
- Confirms processing strategy in metadata

### **6. LLM Knowledge Updates** ✅
- Checks for high-trust outcomes (≥0.75)
- Verifies LearningIntegration is available
- Confirms trigger mechanism is in place

### **7. LearningExample Creation** ✅
- Verifies LearningExamples are created for outcomes
- Checks trust scores and source tracking
- Confirms link between outcomes and learning

### **8. Metadata Structure** ✅
- Verifies required metadata fields exist
- Checks `outcome_type` and `trust_score` are present
- Confirms proper data structure

---

## 🔍 Manual Verification

### **Check Genesis Keys in Database:**

```sql
-- All outcome Genesis Keys
SELECT 
    key_id,
    key_type,
    metadata->>'outcome_type' as outcome_type,
    metadata->>'trust_score' as trust_score,
    metadata->>'success' as success,
    when_timestamp
FROM genesis_key
WHERE metadata->>'outcome_type' IS NOT NULL
ORDER BY when_timestamp DESC
LIMIT 20;
```

### **Check High-Trust Outcomes:**

```sql
-- High-trust outcomes that should trigger LLM updates
SELECT 
    key_id,
    metadata->>'outcome_type' as outcome_type,
    metadata->>'trust_score' as trust_score,
    when_timestamp
FROM genesis_key
WHERE (metadata->>'outcome_type') IN (
    'healing_outcome', 
    'test_outcome', 
    'diagnostic_outcome', 
    'file_processing_outcome'
)
AND CAST(metadata->>'trust_score' AS FLOAT) >= 0.75
ORDER BY when_timestamp DESC
LIMIT 10;
```

### **Check LearningExamples:**

```sql
-- LearningExamples from outcomes
SELECT 
    id,
    example_type,
    trust_score,
    source,
    created_at
FROM learning_examples
WHERE example_type IN (
    'healing_outcome',
    'test_outcome', 
    'diagnostic_outcome',
    'file_processing_outcome'
)
AND trust_score >= 0.75
ORDER BY created_at DESC
LIMIT 10;
```

---

## 🧪 Generate Test Data

To generate test data for verification:

### **1. Run Tests:**
```bash
pytest backend/tests/ -v
```
This will create test outcome Genesis Keys.

### **2. Run Healing System:**
```python
from backend.cognitive.autonomous_healing_system import get_autonomous_healing
from database.session import get_db

session = next(get_db())
healing = get_autonomous_healing(session=session)
result = healing.run_monitoring_cycle()
```
This will create healing outcome Genesis Keys.

### **3. Process Files:**
```python
from backend.file_manager.adaptive_file_processor import AdaptiveFileProcessor
from database.session import get_db

session = next(get_db())
processor = AdaptiveFileProcessor(session=session)
# Process a file to generate outcome Genesis Keys
```
This will create file processing outcome Genesis Keys.

---

## ✅ Expected Results

### **After Running Verification:**

1. ✅ **All 8 tests pass** (or show warnings if no data exists yet)
2. ✅ **Genesis Keys found** for each outcome type
3. ✅ **High-trust outcomes** identified (≥0.75)
4. ✅ **LearningExamples** linked to outcomes
5. ✅ **Metadata structure** correct

### **If Tests Show Warnings:**

- ⚠️ "No Genesis Keys found" - Run the system to generate outcomes
- ⚠️ "LearningIntegration not available" - May need to initialize LLM orchestrator
- ⚠️ "No LearningExamples found" - Outcomes may not have created LearningExamples yet

**These warnings are normal if the system hasn't generated outcomes yet.**

---

## 🚀 Next Steps

1. **Run verification script** to check implementation
2. **Generate test data** by running tests, healing, diagnostics, file processing
3. **Verify Genesis Keys** are created automatically
4. **Check LLM knowledge updates** in logs (look for "LLM knowledge updated")
5. **Monitor continuous improvement** as outcomes accumulate

---

## 📊 Monitoring

### **Check Logs for LLM Updates:**

```bash
# Look for LLM knowledge update messages
grep "LLM knowledge updated" logs/*.log

# Or in Python:
# Should see: "[GENESIS-TRIGGER] LLM knowledge updated: X examples, Y patterns"
```

### **Track Outcome Counts:**

```sql
-- Count outcomes by type
SELECT 
    metadata->>'outcome_type' as outcome_type,
    COUNT(*) as count,
    AVG(CAST(metadata->>'trust_score' AS FLOAT)) as avg_trust
FROM genesis_key
WHERE metadata->>'outcome_type' IS NOT NULL
GROUP BY metadata->>'outcome_type';
```

---

## 🎯 Success Criteria

The autonomous feedback loop is working correctly if:

1. ✅ Genesis Keys are created for all outcome types
2. ✅ High-trust outcomes (≥0.75) trigger LLM knowledge updates
3. ✅ LearningExamples are created and linked to outcomes
4. ✅ Metadata structure is consistent across all outcome types
5. ✅ Trigger pipeline automatically processes outcome Genesis Keys

**All of these are verified by the test script!** 🎉
