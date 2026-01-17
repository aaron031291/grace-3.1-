# Layer 1 Evidence Sources
## What Evidence Does Layer 1 Use for Decisions?

**Question:** "Decisions based on evidence - what evidence does Layer 1 use?"

**Answer:** Layer 1 uses **9 types of evidence** stored in the `learning_examples` database table, all with mathematical trust scores.

---

## 🎯 The 9 Types of Evidence

### 1. **Source Reliability Evidence** (40% weight)

**What it is:** Where the knowledge came from and how trustworthy that source is.

**Evidence Sources:**
```python
source_weights = {
    'user_feedback_positive': 0.9,        # User confirmed it works
    'user_feedback_negative': 0.8,          # User said it's wrong (valuable!)
    'system_observation_success': 0.85,    # Grace observed it succeed
    'system_observation_failure': 0.9,     # Grace observed it fail (teaches more!)
    'external_api_validated': 0.7,          # External API confirmed
    'external_api_unvalidated': 0.4,       # External API, not confirmed
    'inferred': 0.3,                       # Grace inferred it
    'assumed': 0.1                         # Grace assumed it
}
```

**Example:**
```python
LearningExample:
    source: "api_design_book.pdf"
    source_reliability: 0.90  # Technical book = high trust
    file_path: "ai research/api_design_book.pdf"
```

**How Layer 1 uses it:**
- Technical books → 0.90 reliability
- Academic papers → 0.95 reliability
- User feedback → 0.9 reliability
- Inferred knowledge → 0.3 reliability

**Evidence:** The actual source file/document where knowledge came from.

---

### 2. **Data Confidence Evidence** (30% weight)

**What it is:** How accurate and relevant the information is.

**Evidence Sources:**
- **Relevance score** - How relevant is this to the topic?
- **Quality score** - How well-formed is the information?
- **Completeness** - Is the information complete?

**Example:**
```python
LearningExample:
    expected_output: {
        "concept": "Use JWT tokens for stateless auth",
        "relevance": 0.85  # High relevance to authentication
    }
    outcome_quality: 0.85  # High quality information
```

**How Layer 1 uses it:**
- Extracted from study materials
- Measured during knowledge extraction
- Updated based on usage patterns

**Evidence:** The quality and relevance of the extracted knowledge.

---

### 3. **Operational Confidence Evidence** (20% weight)

**What it is:** Whether Grace can actually apply this knowledge in practice.

**Evidence Sources:**
- **Practice outcomes** - Did Grace successfully practice this?
- **Implementation attempts** - How many times did Grace try?
- **Success rate** - What percentage succeeded?

**Example:**
```python
LearningExample:
    operational_confidence: 0.70  # Practiced successfully
    
    example_metadata: {
        "last_practiced": "2026-01-11T15:30:00",
        "practice_outcome": "success",
        "practice_count": 2,
        "success_count": 2,
        "evidence": "Implemented JWT auth correctly in sandbox"
    }
```

**How Layer 1 uses it:**
- Before practice: `operational_confidence = 0.30` (just read about it)
- After successful practice: `operational_confidence = 0.75` (proven in practice)
- After failed practice: `operational_confidence = 0.20` (can't apply it)

**Evidence:** Actual practice results showing Grace can/can't use this knowledge.

---

### 4. **Consistency Score Evidence** (10% weight)

**What it is:** How well this knowledge aligns with other knowledge in Layer 1.

**Evidence Sources:**
- **Cross-reference check** - Does this contradict other examples?
- **Pattern alignment** - Does this match known patterns?
- **Coherence score** - Does this make sense with other knowledge?

**How Layer 1 calculates it:**
```python
def calculate_consistency_score(example: LearningExample):
    # Get all related examples
    related_examples = query_layer1(
        topic=example.topic,
        min_trust_score=0.5
    )
    
    # Check for contradictions
    contradictions = 0
    alignments = 0
    
    for related in related_examples:
        if contradicts(example, related):
            contradictions += 1
        elif aligns_with(example, related):
            alignments += 1
    
    # Consistency = alignments / (alignments + contradictions)
    consistency = alignments / (alignments + contradictions + 1)
    
    return consistency
```

**Example:**
```python
LearningExample:
    consistency_score: 0.85  # Aligns with 85% of related knowledge
    
    # Evidence:
    # - 15 examples support this
    # - 2 examples contradict this
    # - Consistency = 15/(15+2) = 0.88
```

**Evidence:** Statistical comparison against all other Layer 1 knowledge.

---

### 5. **Validation History Evidence** (Adjustment factor)

**What it is:** How many times this knowledge was proven correct or wrong.

**Evidence Sources:**
- **times_validated** - Count of successful validations
- **times_invalidated** - Count of failed validations
- **Validation ratio** - Success rate

**Example:**
```python
LearningExample:
    times_validated: 3      # Proven correct 3 times
    times_invalidated: 0    # Never proven wrong
    
    validation_history: {
        'validated': 3,
        'invalidated': 0,
        'validation_rate': 1.0  # 100% success
    }
```

**How Layer 1 uses it:**
```python
# Boost for validated knowledge
if validation_history['validated'] > 0:
    boost = min(0.1, validation_history['validated'] * 0.02)
    trust_score += boost  # +0.06 for 3 validations

# Penalty for invalidated knowledge
if validation_history['invalidated'] > 0:
    penalty = min(0.2, validation_history['invalidated'] * 0.05)
    trust_score -= penalty  # -0.10 for 2 invalidations
```

**Evidence:** Historical record of correctness.

---

### 6. **Co-occurrence Evidence** (Relationship strength)

**What it is:** Topics appearing together in documents, indicating relationships.

**Evidence Sources:**
- **Document co-occurrence** - Topics in same document
- **Query co-occurrence** - Users querying topics together
- **Practice co-occurrence** - Topics practiced together

**Example:**
```python
# Query Layer 1 for relationship evidence
relationship_evidence = {
    "topic1": "REST API",
    "topic2": "Authentication",
    "co_occurrence_count": 15,      # Appeared together 15 times
    "correlation": 0.67,             # 67% correlation
    "relationship_trust": 0.82      # High trust relationship
}

# Evidence:
# - REST API and Authentication in 15 documents
# - Users who studied REST API queried Authentication 87% of the time
# - Grace's practice: REST API → Authentication = 92% transition
```

**How Layer 1 uses it:**
```python
def should_prefetch(topic: str, related_topic: str):
    evidence = get_relationship_evidence(topic, related_topic)
    
    # Deterministic decision
    return (
        evidence['correlation'] > 0.65 and
        evidence['relationship_trust'] > 0.70 and
        evidence['co_occurrence_count'] >= 5
    )
```

**Evidence:** Statistical patterns showing topic relationships.

---

### 7. **File Provenance Evidence** (Traceability)

**What it is:** The exact source file where knowledge was extracted.

**Evidence Sources:**
- **file_path** - Exact path to source file
- **document_id** - Link to document in database
- **chunk_index** - Which chunk in the document
- **SHA-256 hash** - Cryptographic proof of source

**Example:**
```python
LearningExample:
    file_path: "ai research/api_design_book.pdf"
    document_id: 12345
    chunk_index: 42
    content_hash: "a3f5b2c1..."  # SHA-256 hash
    
    # Can trace back to exact source:
    # - File: api_design_book.pdf
    # - Page: ~42 (from chunk_index)
    # - Content: Exact text with hash
```

**How Layer 1 uses it:**
- **Traceability** - Can prove where knowledge came from
- **Verification** - Can re-check source file
- **Audit trail** - Complete provenance chain

**Evidence:** Cryptographic proof of source file.

---

### 8. **Practice Outcome Evidence** (Operational proof)

**What it is:** Actual results from Grace practicing the knowledge.

**Evidence Sources:**
- **Practice attempts** - How many times practiced
- **Success/failure** - Did practice succeed?
- **Outcome details** - What happened during practice
- **Performance metrics** - How well did it work?

**Example:**
```python
LearningExample:
    actual_output: {
        "practice_attempt": 1,
        "outcome": "success",
        "performance": {
            "accuracy": 0.95,
            "time_taken": 2.3,
            "errors": 0
        },
        "evidence": "Implemented JWT auth correctly in sandbox"
    }
    
    # Before practice:
    operational_confidence: 0.30
    
    # After successful practice:
    operational_confidence: 0.75  # Increased!
```

**How Layer 1 uses it:**
- **Before practice:** Low operational confidence (0.30)
- **After success:** High operational confidence (0.75)
- **After failure:** Low operational confidence (0.20)

**Evidence:** Actual execution results proving Grace can/can't apply knowledge.

---

### 9. **Genesis Key Evidence** (Complete audit trail)

**What it is:** Complete tracking of every operation that touched this knowledge.

**Evidence Sources:**
- **genesis_key_id** - Link to Genesis Key system
- **Operation history** - Every operation that used this
- **Decision log** - Every decision made about this
- **Audit trail** - Complete provenance

**Example:**
```python
LearningExample:
    genesis_key_id: "GK-abc123"
    
    # Genesis Key contains:
    genesis_key = {
        "what": "Knowledge extracted from api_design_book.pdf",
        "when": "2026-01-11T10:30:00",
        "who": "proactive_learner",
        "why": "File ingestion triggered learning",
        "how": "LLM extraction + Layer 1 validation",
        "trust_score": 0.82,
        "operations": [
            {"op": "extract", "trust": 0.75},
            {"op": "validate", "trust": 0.82},
            {"op": "practice", "trust": 0.85}
        ]
    }
```

**How Layer 1 uses it:**
- **Complete traceability** - Can see every operation
- **Decision history** - Why decisions were made
- **Trust evolution** - How trust score changed over time

**Evidence:** Complete audit trail of all operations.

---

## 📊 How Layer 1 Combines Evidence

### Trust Score Calculation

```python
def calculate_trust_score(
    source_reliability: float,      # Evidence Type 1 (40% weight)
    data_confidence: float,          # Evidence Type 2 (30% weight)
    operational_confidence: float,   # Evidence Type 3 (20% weight)
    consistency_score: float,        # Evidence Type 4 (10% weight)
    validation_history: dict         # Evidence Type 5 (adjustment)
) -> float:
    
    # Weighted combination of evidence
    trust_score = (
        source_reliability * 0.40 +      # 40% - Where from?
        data_confidence * 0.30 +         # 30% - How accurate?
        operational_confidence * 0.20 +  # 20% - Can use it?
        consistency_score * 0.10         # 10% - Aligns with other?
    )
    
    # Adjust for validation history (Evidence Type 5)
    if validation_history['validated'] > 0:
        boost = min(0.1, validation_history['validated'] * 0.02)
        trust_score += boost
    
    if validation_history['invalidated'] > 0:
        penalty = min(0.2, validation_history['invalidated'] * 0.05)
        trust_score -= penalty
    
    return max(0.0, min(1.0, trust_score))
```

**Result:** Deterministic trust score from all evidence types.

---

## 🔍 Example: Complete Evidence Chain

### Scenario: "How do I authenticate an API?"

**Layer 1 Query:**
```python
results = query_layer1(topic="API authentication", min_trust_score=0.7)
```

**Evidence Found:**
```python
LearningExample:
    id: 12345
    example_type: "knowledge_extraction"
    
    # Evidence Type 1: Source Reliability
    source: "api_design_book.pdf"
    source_reliability: 0.90  # Technical book
    file_path: "ai research/api_design_book.pdf"
    
    # Evidence Type 2: Data Confidence
    expected_output: {
        "concept": "Use JWT tokens for stateless auth",
        "relevance": 0.85
    }
    outcome_quality: 0.85
    
    # Evidence Type 3: Operational Confidence
    operational_confidence: 0.70
    example_metadata: {
        "practice_count": 2,
        "success_count": 2,
        "last_practiced": "2026-01-11T15:30:00",
        "practice_outcome": "success"
    }
    
    # Evidence Type 4: Consistency Score
    consistency_score: 0.85  # Aligns with 15/17 related examples
    
    # Evidence Type 5: Validation History
    times_validated: 3
    times_invalidated: 0
    validation_history: {
        'validated': 3,
        'invalidated': 0,
        'validation_rate': 1.0
    }
    
    # Evidence Type 6: Co-occurrence
    # REST API + Authentication appeared together 15 times
    
    # Evidence Type 7: File Provenance
    document_id: 12345
    chunk_index: 42
    content_hash: "a3f5b2c1..."
    
    # Evidence Type 8: Practice Outcome
    actual_output: {
        "practice_attempt": 2,
        "outcome": "success",
        "performance": {"accuracy": 0.95}
    }
    
    # Evidence Type 9: Genesis Key
    genesis_key_id: "GK-abc123"
    
    # Final Trust Score (calculated from all evidence)
    trust_score: 0.82
```

**Layer 1 Decision:**
```python
# Calculate trust score from evidence
trust_score = (
    0.90 * 0.40 +  # Source reliability
    0.85 * 0.30 +  # Data confidence
    0.70 * 0.20 +  # Operational confidence
    0.85 * 0.10    # Consistency score
) + 0.06  # Validation boost (3 validations * 0.02)

# Result: trust_score = 0.82

# Deterministic decision
if trust_score >= 0.7:
    return knowledge  # ACCEPT
else:
    return None  # REJECT
```

**Result:** Knowledge accepted with trust_score=0.82, backed by 9 types of evidence.

---

## 📋 Evidence Summary

| Evidence Type | Weight | What It Proves | Source |
|--------------|--------|----------------|--------|
| **1. Source Reliability** | 40% | Where knowledge came from | File/document source |
| **2. Data Confidence** | 30% | How accurate/relevant | Quality analysis |
| **3. Operational Confidence** | 20% | Can Grace use it? | Practice results |
| **4. Consistency Score** | 10% | Aligns with other knowledge? | Cross-reference |
| **5. Validation History** | Adjustment | Proven correct/wrong? | Historical record |
| **6. Co-occurrence** | Relationship | Topics related? | Statistical patterns |
| **7. File Provenance** | Traceability | Exact source? | File path + hash |
| **8. Practice Outcome** | Operational | Did it work? | Actual execution |
| **9. Genesis Key** | Audit trail | Complete history? | Operation log |

---

## ✅ Key Points

### All Evidence is Stored

**Location:** `learning_examples` table in PostgreSQL database

**Structure:**
```sql
CREATE TABLE learning_examples (
    id INTEGER PRIMARY KEY,
    source_reliability FLOAT,      -- Evidence Type 1
    outcome_quality FLOAT,          -- Evidence Type 2
    operational_confidence FLOAT,   -- Evidence Type 3
    consistency_score FLOAT,        -- Evidence Type 4
    times_validated INTEGER,        -- Evidence Type 5
    times_invalidated INTEGER,      -- Evidence Type 5
    file_path VARCHAR,              -- Evidence Type 7
    genesis_key_id VARCHAR,         -- Evidence Type 9
    example_metadata JSON,          -- Evidence Types 6, 8
    ...
);
```

### All Evidence is Queryable

```python
# Query by evidence
examples = session.query(LearningExample).filter(
    LearningExample.source_reliability >= 0.8,  # High source trust
    LearningExample.operational_confidence >= 0.7,  # Can use it
    LearningExample.times_validated >= 2,  # Proven correct
    LearningExample.consistency_score >= 0.8  # Aligns with knowledge
).all()
```

### All Evidence is Deterministic

- **Same evidence** → **Same trust score**
- **Same trust score** → **Same decision**
- **No guessing** → **Only calculations**

---

## 🎯 Bottom Line

**Layer 1 uses 9 types of evidence:**

1. ✅ **Source Reliability** - Where from? (40% weight)
2. ✅ **Data Confidence** - How accurate? (30% weight)
3. ✅ **Operational Confidence** - Can use it? (20% weight)
4. ✅ **Consistency Score** - Aligns with other? (10% weight)
5. ✅ **Validation History** - Proven correct? (adjustment)
6. ✅ **Co-occurrence** - Topics related? (relationships)
7. ✅ **File Provenance** - Exact source? (traceability)
8. ✅ **Practice Outcome** - Did it work? (operational proof)
9. ✅ **Genesis Key** - Complete history? (audit trail)

**All evidence is:**
- ✅ Stored in `learning_examples` table
- ✅ Queryable via SQL/database
- ✅ Used in deterministic trust score calculation
- ✅ Traceable to exact sources
- ✅ Auditable via Genesis Keys

**Every Layer 1 decision is backed by mathematical evidence!** 🛡️
