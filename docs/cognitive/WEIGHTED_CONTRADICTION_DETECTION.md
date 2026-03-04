# Weighted Contradiction Detection with Trust Scores

## Overview

The semantic contradiction detection system has been enhanced to **weight contradictions by the trust score (confidence score) of existing knowledge**. This means:

- **Contradictions with high-trust knowledge** (100% confidence score) have **maximum impact**
- **Contradictions with low-trust knowledge** (10% confidence score) have **minimal impact**
- This creates **intelligent conflict resolution** based on knowledge reliability

## Problem Solved

### Before (Unweighted)

```python
New Chunk: "Python is slow"

Similar Knowledge:
1. "Python is fast" (confidence: 100%, similarity: 0.85)
2. "Python is efficient" (confidence: 10%, similarity: 0.80)

Contradiction Score Impact:
- Both contradictions penalized equally
- Impact = similarity × contradiction_score
- Doesn't account for knowledge reliability

Result: Consensus reduced by both contradictions equally ❌
```

### After (Trust-Weighted)

```python
New Chunk: "Python is slow"

Similar Knowledge:
1. "Python is fast" (confidence: 100%, similarity: 0.85) ← HIGH TRUST
2. "Python is efficient" (confidence: 10%, similarity: 0.80) ← LOW TRUST

Weighted Contradiction Score Impact:
- Contradiction with high-trust knowledge: HIGH impact
- Contradiction with low-trust knowledge: LOW impact
- Impact = similarity × contradiction_score × trust_score

Result: New chunk heavily penalized by #1, minimally by #2 ✓
```

## How It Works

### 1. Trust Score Acquisition

When searching for similar chunks in the knowledge base:

```
Vector DB Search Results
    ↓
Payload contains:
- text: The chunk content
- confidence_score: Trust/confidence score (0.0-1.0)
    ↓
Extract confidence_score for each result
```

### 2. Weighted Penalty Calculation

```python
# For each contradiction found:

base_penalty = similarity_score × contradiction_confidence

weighted_penalty = base_penalty × trust_score

# Examples:
# High trust: 0.85 × 0.92 × 1.0 = 0.782 (high impact)
# Low trust:  0.80 × 0.90 × 0.1 = 0.072 (low impact)
```

### 3. Consensus Adjustment

```python
# Collect supporting chunks (non-contradicting)
supporting_chunks = [chunk for chunk if not contradicts]

# Calculate weighted contradiction impact
total_weighted_penalty = sum(penalties for each contradiction)

# Adjust consensus
if supporting_chunks:
    avg_support = mean(supporting_similarities)
    consensus = max(0.1, avg_support - total_weighted_penalty)
else:
    consensus = max(0.1, 0.5 - total_weighted_penalty)
```

## Implementation Details

### Updated Methods

#### `batch_detect_contradictions()`

```python
def batch_detect_contradictions(
    self,
    new_chunk: str,
    existing_chunks: List[str],
    similarity_scores: List[float],
    trust_scores: Optional[List[float]] = None,  # ← NEW: Trust scores
    threshold: float = 0.7,
) -> List[Dict]:
```

**Changes**:

- Added `trust_scores` parameter
- Weights penalty by trust score: `penalty = sim × contradiction × trust`
- Returns trust_score in contradiction details
- Logs weighted contradiction impact

#### `adjust_consensus_for_contradictions()`

```python
def adjust_consensus_for_contradictions(
    self,
    new_chunk: str,
    existing_chunks_with_scores: List[Tuple[str, float]],
    existing_chunks_trust_scores: Optional[List[float]] = None,  # ← NEW
    threshold: float = 0.7,
) -> Tuple[float, List[Dict]]:
```

**Changes**:

- Added `existing_chunks_trust_scores` parameter
- Passes trust scores to batch detection
- Logs trust-weighted impact details

### Updated ConfidenceScorer

In `calculate_consensus_score()`:

1. **Extract trust scores from vector DB**:

   ```python
   # From Qdrant payload
   chunk_trust_score = payload.get("confidence_score", 0.5)
   trust_scores.append(chunk_trust_score)
   ```

2. **Default trust scores for offline chunks**:

   ```python
   # For existing_chunks parameter
   trust_scores.append(0.5)  # Medium trust by default
   ```

3. **Pass to contradiction detector**:
   ```python
   consensus_score, contradiction_details = \
       self.contradiction_detector.adjust_consensus_for_contradictions(
           chunk_text,
           similarity_results,
           trust_scores,  # ← NEW: Pass trust scores
           threshold=0.7
       )
   ```

### Updated Ingestion Service

In `ingest_text()`:

**Payload now includes**:

```python
chunk_metadata = {
    "document_id": document_id,
    "chunk_index": chunk_index,
    "text": chunk_text,  # ← NEW: For retrieval
    "confidence_score": confidence_score,  # ← Trust score for weighting
    ...
}
```

This payload is stored in Qdrant, making it available for weighted contradiction detection in future ingestions.

## Examples

### Example 1: Official Documentation Contradiction

```python
New Chunk:
  "Python variables are statically typed"

Existing Knowledge:
  1. "Python is dynamically typed"
     - Confidence: 0.95 (Official Python docs)
     - Similarity: 0.88
     - Contradiction score: 0.98

Weight Calculation:
  - Penalty = 0.88 × 0.98 × 0.95 = 0.821
  - HIGH IMPACT: Consensus significantly reduced
```

### Example 2: User-Generated Contradiction

```python
New Chunk:
  "Python is compiled"

Existing Knowledge:
  1. "Python is interpreted"
     - Confidence: 0.25 (User-generated comment)
     - Similarity: 0.82
     - Contradiction score: 0.85

Weight Calculation:
  - Penalty = 0.82 × 0.85 × 0.25 = 0.174
  - LOW IMPACT: Consensus minimally reduced
```

### Example 3: Agreement with High-Trust Knowledge

```python
New Chunk:
  "Python uses duck typing"

Existing Knowledge:
  1. "Python supports duck typing"
     - Confidence: 0.90 (Academic paper)
     - Similarity: 0.91
     - No contradiction detected

Result:
  - Consensus BOOSTED by high-trust supporting knowledge
```

## Logging Output

```
INFO: Consensus adjusted from 0.850 to 0.420 due to 1 contradictions.
      Weighted by trust scores of existing knowledge.

DEBUG: Found 1 contradictions in 3 comparisons. Weighted by trust scores.

Contradiction Details:
{
  "chunk_index": 0,
  "existing_chunk": "Python is fast...",
  "similarity": 0.85,
  "contradiction_confidence": 0.92,
  "trust_score": 1.0,          # ← Trust weight applied
  "penalty": 0.782,            # ← Weighted penalty
}
```

## API Response

The response now includes trust scores in contradiction details:

```json
{
  "confidence_score": 0.42,
  "contradictions_detected": true,
  "contradiction_count": 1,
  "contradiction_details": [
    {
      "chunk_index": 0,
      "existing_chunk": "Python is fast...",
      "similarity": 0.85,
      "contradiction_confidence": 0.92,
      "trust_score": 1.0,
      "penalty": 0.782
    }
  ]
}
```

## Configuration

### Adjusting Trust Weight

The trust score weight can be adjusted in the penalty calculation:

```python
# Current formula (linear weighting):
weighted_penalty = similarity × contradiction × trust

# Alternative: Exponential weighting (amplify high-trust contradictions):
weighted_penalty = similarity × contradiction × (trust ** 2)

# Alternative: Threshold-based:
weighted_penalty = (
    similarity × contradiction × trust if trust > 0.6
    else similarity × contradiction × 0.1
)
```

### Default Trust Scores

For chunks without explicit trust scores:

```python
# In ConfidenceScorer:
trust_scores.append(0.5)  # Medium trust for unknown chunks

# In SemanticContradictionDetector:
if trust_scores is None:
    trust_scores = [1.0] * len(existing_chunks)  # Assume high trust if unknown
```

## Best Practices

1. **Ensure Quality Knowledge Base**

   - High-quality chunks should have high confidence scores
   - Regularly review and update confidence scores
   - Remove or downgrade unreliable information

2. **Monitor Weighted Contradictions**

   - Check logs for patterns of high-trust contradictions
   - Review new chunks that contradict well-known information
   - Manually verify significant confidence score changes

3. **Tune Thresholds**
   - Adjust contradiction threshold based on domain
   - Consider trust score distribution
   - Test with real-world data

## Benefits

✅ **Intelligent Conflict Resolution**

- Prioritizes high-quality knowledge
- Minimizes impact of unreliable information

✅ **Progressive Learning**

- New information can gradually override low-trust knowledge
- High-trust information acts as a reliable anchor

✅ **Transparent Decision Making**

- Trust scores visible in responses
- Understand why confidence changed
- Audit trail of contradictions

✅ **Production-Ready**

- Graceful degradation if trust scores unavailable
- Backward compatible
- No performance impact

## Testing

Run tests to verify weighted contradiction detection:

```bash
# Run system test
python backend/test_semantic_system.py

# Run specific tests
pytest backend/tests/test_contradiction_detection.py::TestContradictionDetectionAccuracy -v

# Check logs for weighted impact messages
grep "Weighted by trust" output.log
```

## Migration Guide

### For Existing Data

1. **Verify payload structure**:

   ```bash
   # Check Qdrant collection for confidence_score in payload
   curl http://localhost:6333/collections/documents/points
   ```

2. **Re-index documents** (optional):

   ```bash
   # Delete and re-ingest to get new payloads with text field
   DELETE FROM documents;  # Or selective delete
   # Re-ingest documents
   ```

3. **No breaking changes**:
   - If trust_scores not provided, defaults to 1.0 (backward compatible)
   - Existing calculations continue to work

## Future Enhancements

1. **Trust Score Decay**

   - Gradually reduce trust score for old information
   - Combine with recency scoring

2. **Automatic Trust Adjustment**

   - Learn trust scores from user feedback
   - Adjust based on how often information is contradicted

3. **Domain-Specific Weights**

   - Different weight multipliers per domain
   - Custom weighting formulas

4. **Trust Propagation**
   - Inherit trust from source documents
   - Track information lineage

---

**Status**: ✅ COMPLETE AND TESTED  
**Version**: 1.1  
**Breaking Changes**: None  
**Backward Compatible**: Yes
