# Semantic Contradiction Detection

## Overview

The confidence scoring system now includes **semantic contradiction detection** to prevent contradictory information from artificially boosting confidence scores. This prevents cases where two chunks discuss the same topic but express opposite claims from being treated as supporting evidence.

## Problem Statement

### Before (Simple Similarity Approach)

```
Chunk A: "The Earth is round"
Chunk B: "The Earth is flat"

Semantic Similarity: 0.85 (very high - both discuss Earth shape)
Simple Consensus: Positive (both chunks exist, so treat as supporting)
Result: Confidence score increased ❌ WRONG
```

The problem: High semantic similarity + simple averaging would incorrectly boost confidence when chunks contradict.

### After (Semantic Contradiction Detection)

```
Chunk A: "The Earth is round"
Chunk B: "The Earth is flat"

Semantic Similarity: 0.85
Contradiction Score: 0.92 (99% likelihood of contradiction)
Simple Consensus: 0.85
Adjusted Consensus: 0.30 (reduced due to detected contradiction)
Result: Confidence score reduced ✓ CORRECT
```

## How It Works

### 1. NLI Model (Natural Language Inference)

The system uses the **cross-encoder/nli-deberta-large** model from Hugging Face, which achieves **96% accuracy on MNLI benchmark**:

- **Model**: DeBERTa (Decoding-enhanced BERT)
- **Task**: Natural Language Inference (NLI)
- **Outputs**: 3 probability scores for each pair:
  - **Entailment** (0-1): Likelihood that Premise → Hypothesis
  - **Neutral** (0-1): No clear relationship
  - **Contradiction** (0-1): Premise contradicts Hypothesis

### 2. Contradiction Detection Flow

```
Input: Two semantically similar chunks
   ↓
[NLI Model]
   ↓
Output: [entailment_score, neutral_score, contradiction_score]
   ↓
If contradiction_score > threshold (0.7):
   → Mark as contradiction
   → Reduce consensus score
   → Log warning
Else:
   → Treat as normal consensus
```

### 3. Consensus Score Adjustment

When contradictions are detected:

```python
# Original approach (WRONG):
consensus_score = mean([0.85, 0.80, 0.75])  # = 0.80

# New approach (CORRECT):
simple_mean = 0.80
contradiction_penalties = [
    0 (no contradiction with doc 1),
    0.8 (strong contradiction with doc 2),
    0 (no contradiction with doc 3)
]
adjusted_consensus = simple_mean * (1 - max_penalty)
adjusted_consensus = 0.80 * (1 - 0.8)  # = 0.16 ✓
```

## Integration Points

### 1. ConfidenceScorer Class

```python
from confidence_scorer import ConfidenceScorer, SemanticContradictionDetector

scorer = ConfidenceScorer(
    embedding_model=embedding_model,
    qdrant_client=qdrant_client,
    collection_name="documents"
)

# Initialize with contradiction detector
result = scorer.calculate_confidence_score(
    text_content="The Earth is round",
    source_type="user_generated",
    created_at=datetime.utcnow(),
    existing_chunks=["The Earth is flat", "Clouds are white"]
)

# Result includes contradiction info:
{
    "confidence_score": 0.35,          # Reduced due to contradiction
    "source_reliability": 0.50,
    "content_quality": 0.65,
    "consensus_score": 0.16,           # Reduced from potential 0.80
    "recency": 1.0,
    "contradictions_detected": True,   # NEW
    "contradiction_count": 1,          # NEW
    "contradiction_details": [...]     # NEW
}
```

### 2. Ingestion Service

```python
# Documents and chunks are automatically scored
document_id, status = ingestion_service.ingest_text(
    text_content="Python is a programming language",
    filename="python_guide.txt",
    source_type="verified_tutorial",
    metadata={"author": "John"}
)

# Logs warnings when contradictions are found:
# WARNING: Document X: Found 2 semantic contradictions.
# WARNING: Chunk Y: Found 1 semantic contradiction
```

### 3. API Endpoints

Confidence scores are returned in all API responses:

```json
{
  "id": 1,
  "text": "...",
  "confidence_score": 0.75,
  "contradictions_detected": false,
  "contradiction_count": 0
}
```

## Performance Considerations

### Model Size & Speed

- **Model**: cross-encoder/nli-deberta-large (~500MB)
- **Inference**: ~200-500ms per pair on CPU, ~20-50ms on GPU
- **GPU Acceleration**: Automatic detection and usage of CUDA

### Batch Processing

For multiple chunks, use batch detection:

```python
detector = SemanticContradictionDetector(use_gpu=True)

# Efficient batch processing
contradiction_scores = detector.batch_detect_contradictions(
    reference_text="Python is fast",
    comparison_texts=[
        "Python is slow",
        "Python is efficient",
        "Dogs are animals"
    ],
    threshold=0.7
)
```

### Caching Strategy

The model is initialized once and reused:

```python
# Initialization happens once
scorer = ConfidenceScorer(...)  # Model loaded to GPU

# Subsequent calls are fast
for chunk in chunks:
    result = scorer.calculate_confidence_score(...)  # Reuses loaded model
```

## Configuration

### Threshold Tuning

Adjust contradiction detection sensitivity:

```python
# More strict (fewer contradictions marked)
adjust_consensus_for_contradictions(..., threshold=0.9)

# More lenient (more contradictions marked)
adjust_consensus_for_contradictions(..., threshold=0.5)

# Default
adjust_consensus_for_contradictions(..., threshold=0.7)
```

### Device Selection

```python
# Automatic (CUDA if available, else CPU)
detector = SemanticContradictionDetector(use_gpu=True)

# Force CPU
detector = SemanticContradictionDetector(use_gpu=False)
```

## Examples

### Example 1: Supporting Statements

```python
chunk1 = "Water boils at 100 degrees Celsius"
chunk2 = "Boiling point of water is 100C"

score = detector.detect_contradiction(chunk1, chunk2)
# score ≈ 0.05 (low contradiction - these support each other)

# Result: Consensus score maintained
```

### Example 2: Clear Contradiction

```python
chunk1 = "The sky is blue"
chunk2 = "The sky is red"

score = detector.detect_contradiction(chunk1, chunk2)
# score ≈ 0.95 (high contradiction)

# Result: Consensus score reduced significantly
```

### Example 3: Unrelated Statements

```python
chunk1 = "Python is a programming language"
chunk2 = "Bananas are yellow"

score = detector.detect_contradiction(chunk1, chunk2)
# score ≈ 0.1 (neutral - unrelated)

# Result: Not treated as contradiction (low semantic similarity)
```

## Testing

Run the test suite to verify contradiction detection:

```bash
# Test basic detector
python -m pytest backend/tests/test_contradiction_detection.py::TestSemanticContradictionDetector -v

# Test integration with ConfidenceScorer
python -m pytest backend/tests/test_contradiction_detection.py::TestConfidenceScorerIntegration -v

# Test accuracy with known examples
python -m pytest backend/tests/test_contradiction_detection.py::TestContradictionDetectionAccuracy -v

# Run system test
python backend/test_semantic_system.py
```

## Fallback Behavior

If the NLI model is unavailable (network issues, missing dependencies):

1. **Detection still works**: Simple similarity-based detection
2. **No errors**: System logs warnings but continues
3. **Graceful degradation**: Confidence scores calculated without contradiction detection
4. **Warnings logged**: Administrator can see model unavailability

```python
if not detector.model_available:
    logger.warning("NLI model unavailable - using fallback similarity-based detection")
    # System continues with reduced contradiction detection capability
```

## Model Details

### cross-encoder/nli-deberta-large

**Architecture**:

- DeBERTa base model with 110M parameters
- Fine-tuned on MNLI (Multi-Genre Natural Language Inference) dataset
- Supports context length up to 512 tokens

**Accuracy**:

- MNLI-m: 96.0%
- MNLI-mm: 96.0%
- RTE: 92.6%
- QNLI: 96.0%

**Inference Speed**:

- CPU: ~5-10 pairs/second
- GPU (RTX 3090): ~100+ pairs/second

### Alternative Models

If needed, can be swapped with:

- `cross-encoder/nli-MiniLM-L6-v2` (faster, less accurate)
- `cross-encoder/nli-mpnet-base-v2` (balanced performance)
- `cross-encoder/nli-distilroberta-base` (smaller, faster)

## Future Improvements

1. **Multi-language Support**: Add models for non-English text
2. **Custom Fine-tuning**: Train on domain-specific contradiction patterns
3. **Caching**: Cache model outputs for repeated comparisons
4. **Ensemble Methods**: Combine multiple NLI models for higher accuracy
5. **Claim Extraction**: Extract specific claims before comparison
6. **Temporal Reasoning**: Handle time-dependent contradictions

## References

- DeBERTa Paper: https://arxiv.org/abs/2006.03654
- MNLI Dataset: https://cims.nyu.edu/~sbowman/multinli/
- Cross-Encoder: https://www.sbert.net/docs/pretrained-models/nli-models.html
- Sentence Transformers: https://www.sbert.net/
