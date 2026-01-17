# Reverse KNN Gap Filling System

**Date:** 2026-01-16  
**Status:** ✅ IMPLEMENTED

---

## 📋 Summary

Grace can now **identify knowledge gaps** (what she doesn't know) and use **reverse KNN** to find similar problems and solutions from external sources (Stack Overflow, GitHub) to fill those gaps.

---

## 🎯 How It Works

### The Problem
When Grace encounters an error she can't fix:
1. ❌ No matching fix pattern in knowledge base
2. ❌ Fix was attempted but failed
3. ❌ Low confidence pattern match

### The Solution: Reverse KNN

**Traditional KNN:** Given a query, find K nearest neighbors in your dataset  
**Reverse KNN:** Given a gap (what you don't know), find K nearest neighbors in external knowledge space

**Process:**
```
1. Detect Gap (error we can't fix)
   ↓
2. Extract Search Terms (error type, key phrases)
   ↓
3. Search External Sources (Stack Overflow, GitHub)
   ↓
4. Calculate Similarity (Jaccard, word overlap, error type matching)
   ↓
5. Find K Nearest Neighbors (most similar problems)
   ↓
6. Extract Solutions (from neighbors)
   ↓
7. Create Fix Pattern (learn from solutions)
   ↓
8. Add to Knowledge Base (fill the gap)
```

---

## 🔍 Components

### 1. **Gap Detector** (`backend/cognitive/gap_detector.py`)

**Detects knowledge gaps:**
- ✅ Error can't be categorized → Gap
- ✅ Fix attempted but failed → Gap
- ✅ Low confidence pattern match → Gap

**Example:**
```python
from cognitive.gap_detector import get_gap_detector

detector = get_gap_detector()
gap = detector.detect_gap(
    "SomeNewError: unknown error type",
    attempted_fixes=["buffer_clear", "connection_reset"]
)
# Returns: KnowledgeGap if it's a gap, None if we can handle it
```

---

### 2. **Reverse KNN Searcher** (`backend/cognitive/reverse_knn_searcher.py`)

**Finds similar problems using reverse KNN:**

**Similarity Calculation:**
- **Jaccard Similarity**: Word overlap between errors
- **Error Type Matching**: Boost for same error type
- **Key Phrase Extraction**: Extracts important terms

**Example:**
```python
from cognitive.reverse_knn_searcher import get_reverse_knn_searcher

searcher = get_reverse_knn_searcher()
similar = searcher.find_similar_problems(gap, k=5)

# Returns: List of SimilarProblem with:
# - error_message (similar error)
# - solution (how it was fixed)
# - similarity_score (0.0-1.0)
# - source (stackoverflow/github)
# - upvotes (quality indicator)
```

**Search Strategy:**
1. Extract search terms from error
2. Search Stack Overflow (relevance sort = similarity)
3. Search GitHub Issues (reactions sort = helpfulness)
4. Calculate similarity scores
5. Return top K most similar

---

### 3. **Gap Filler** (`backend/cognitive/gap_filler.py`)

**Fills gaps by learning from similar problems:**

**Process:**
1. Detect gap
2. Use reverse KNN to find K similar problems
3. Extract common solution pattern
4. Create fix pattern
5. Calculate confidence

**Example:**
```python
from cognitive.gap_filler import get_gap_filler

filler = get_gap_filler()
result = filler.fill_gap(
    "NewError: something went wrong",
    attempted_fixes=["buffer_clear"],
    k=5  # Find 5 similar problems
)

# Returns:
# {
#     "success": True,
#     "similar_problems_found": 5,
#     "fix_pattern": {...},
#     "confidence": 0.85
# }
```

---

## 🔄 Integration with Autonomous Healing

### Automatic Gap Detection

The autonomous healing system now automatically:
1. **Detects gaps** when healing fails
2. **Searches for solutions** using reverse KNN
3. **Creates fix patterns** from similar problems
4. **Learns** for future use

**Code Integration:**
```python
# In autonomous_healing_system.py
if self.enable_learning:
    self._learn_from_healing(decision, None, success=False)
    
    # NEW: Detect and fill gap
    error_msg = str(e)
    self._detect_and_fill_gap(error_msg, decision)
```

---

## 📊 Reverse KNN Algorithm

### Similarity Metrics

**1. Word Overlap (Jaccard Similarity)**
```python
words1 = set(error1.split())
words2 = set(error2.split())
similarity = len(words1 & words2) / len(words1 | words2)
```

**2. Error Type Matching**
```python
if error_type1 == error_type2:
    similarity += 0.2  # Boost for same error type
```

**3. Key Phrase Extraction**
- Extracts error type (ImportError, TimeoutError, etc.)
- Extracts quoted strings (module names, table names)
- Extracts phrases after colons

### KNN Search

**Stack Overflow:**
- Sort by: `relevance` (most similar first)
- Filter: `tagged:python`, `is:closed`
- Get: Accepted answers + top upvoted answers

**GitHub:**
- Sort by: `reactions` (most helpful first)
- Filter: `is:closed`, `language:python`
- Get: Comments with solutions

---

## 🚀 Usage

### Manual Gap Filling

```bash
# Fill gaps from healing results
python backend/scripts/fill_knowledge_gaps.py
```

**What it does:**
1. Finds gaps from `healing_results.json`
2. Uses reverse KNN to find similar problems
3. Creates fix patterns
4. Reports results

### Automatic (Integrated)

Gap detection and filling happens automatically when:
- Healing action fails
- Error can't be categorized
- Fix pattern exists but doesn't work

---

## 📈 Example Flow

### Scenario: Grace encounters unknown error

```
1. Error occurs: "CustomError: something new happened"
   ↓
2. Healing system tries to fix → Fails
   ↓
3. Gap Detector: "No matching pattern" → GAP DETECTED
   ↓
4. Reverse KNN Searcher:
   - Extracts: "CustomError", "something new"
   - Searches Stack Overflow
   - Finds 5 similar problems
   ↓
5. Similarity Scores:
   - Problem 1: 0.85 similarity (accepted answer, 50 upvotes)
   - Problem 2: 0.72 similarity (20 upvotes)
   - Problem 3: 0.68 similarity (15 upvotes)
   - ...
   ↓
6. Extract Solution:
   - Common solution: "Add try-except block"
   - Best solution: Problem 1 (highest similarity + upvotes)
   ↓
7. Create Fix Pattern:
   {
     "issue_type": "custom_error",
     "pattern": "CustomError.*",
     "fix_template": "Add try-except block...",
     "confidence": 0.85
   }
   ↓
8. Gap Filled! ✅
   - Next time Grace sees this error, she knows how to fix it
```

---

## 🎯 Benefits

### 1. **Proactive Learning**
- Grace learns from failures automatically
- No manual pattern creation needed
- Continuous improvement

### 2. **External Knowledge**
- Learns from Stack Overflow (millions of solutions)
- Learns from GitHub (real code fixes)
- Leverages community knowledge

### 3. **Similarity-Based**
- Finds truly similar problems (not just keyword matches)
- Uses multiple similarity metrics
- Quality filtering (upvotes, accepted answers)

### 4. **Automatic Integration**
- Works with existing healing system
- No manual intervention needed
- Learns in background

---

## 📊 Current Status

### Implemented:
- ✅ Gap detection (identifies what Grace doesn't know)
- ✅ Reverse KNN search (finds similar problems)
- ✅ Solution extraction (gets fixes from neighbors)
- ✅ Pattern creation (learns from solutions)
- ✅ Integration with healing system (automatic)

### Capabilities:
- ✅ Detects gaps from failed healing attempts
- ✅ Searches Stack Overflow for similar problems
- ✅ Searches GitHub Issues for similar problems
- ✅ Calculates similarity scores
- ✅ Extracts solutions from markdown
- ✅ Creates fix patterns automatically

---

## 🔧 Configuration

### K Value (Number of Neighbors)
```python
# Default: k=5
result = gap_filler.fill_gap(error_message, k=10)  # Find 10 similar problems
```

### Sources
```python
# Default: ["stackoverflow", "github"]
similar = searcher.find_similar_problems(gap, sources=["stackoverflow"])
```

### Similarity Threshold
```python
# Only use solutions with similarity > 0.5
similar = [p for p in similar if p.similarity_score > 0.5]
```

---

## 📈 Future Enhancements

### 1. **Embedding-Based Similarity**
- Use Grace's embedding model for semantic similarity
- More accurate than word overlap
- Better for complex errors

### 2. **Pattern Confidence Updates**
- Track which patterns work
- Update confidence based on success rate
- Remove patterns that don't work

### 3. **Automatic Pattern Addition**
- Add patterns to knowledge base automatically
- No manual review needed (for high-confidence patterns)
- Continuous learning

### 4. **Multi-Source Learning**
- Reddit, Discord, forums
- Documentation scraping
- Code repository analysis

---

## 🔗 Related Files

- `backend/cognitive/gap_detector.py` - Gap detection
- `backend/cognitive/reverse_knn_searcher.py` - Reverse KNN search
- `backend/cognitive/gap_filler.py` - Gap filling logic
- `backend/scripts/fill_knowledge_gaps.py` - Run script
- `backend/cognitive/autonomous_healing_system.py` - Integration

---

## ✅ Summary

**Grace can now:**
- ✅ Identify what she doesn't know (gap detection)
- ✅ Find similar problems using reverse KNN
- ✅ Learn solutions from external sources
- ✅ Create fix patterns automatically
- ✅ Fill knowledge gaps proactively

**To use:**
```bash
# Fill gaps manually
python backend/scripts/fill_knowledge_gaps.py

# Or it happens automatically when healing fails
```

**Status:** ✅ **REVERSE KNN GAP FILLING IMPLEMENTED**

Grace can now identify knowledge gaps and use reverse KNN to find the knowledge she needs!
