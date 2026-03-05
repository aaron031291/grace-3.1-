# Confidence Scoring System

## Overview

The confidence scoring system automatically calculates and assigns confidence scores to all ingested documents and their chunks. This replaces the manual trust_score system with an intelligent, multi-factor scoring mechanism that evaluates knowledge quality based on source reliability, content quality, consensus with existing knowledge, and recency.

**User Control Removed**: Confidence scores are now calculated automatically. Users cannot manually set scores.

## Scoring Formula

```
confidence_score = (
    source_reliability * 0.35 +
    content_quality * 0.25 +
    consensus_score * 0.25 +
    recency * 0.10
)
```

### Component Weights

- **source_reliability**: 35% - How trustworthy the source is
- **content_quality**: 25% - Quality indicators of the content itself
- **consensus_score**: 25% - Agreement with existing knowledge base
- **recency**: 10% - How recent the information is

## Component Details

### 1. Source Reliability (35%)

Determined by the `source_type` parameter during ingestion:

| Source Type       | Score |
| ----------------- | ----- |
| official_docs     | 0.95  |
| academic_paper    | 0.90  |
| verified_tutorial | 0.85  |
| trusted_blog      | 0.75  |
| community_qa      | 0.65  |
| user_generated    | 0.50  |
| unverified        | 0.30  |

**Default**: `user_generated` (0.50)

### 2. Content Quality (25%)

Calculated based on content characteristics:

- **Length > 1000 characters**: +0.2
- **Length > 500 characters**: +0.1
- **Has structure** (headers, lists, sections): +0.1
  - Indicators: `#`, `##`, `###`, `-`, `*`, `1.`, etc.
- **Contains code/technical content**: +0.1
  - Indicators: ` ``` `, `def`, `class`, `import`, etc.
- **Has citations/references**: +0.1
  - Indicators: `[`, `](`, `http`, `www`, `Reference:`, etc.

**Range**: 0.0 to 1.0

### 3. Consensus Score (25%)

Calculated through semantic similarity matching:

1. Generates embeddings for the new content
2. Compares with all existing chunks using cosine similarity
3. Collects similarity scores for related content (threshold: 0.3+)
4. Consensus score = mean of collected similarity scores
5. If no related content found: 0.5 (neutral consensus)

**Range**: 0.0 to 1.0

### 4. Recency (10%)

Based on when content was created:

| Age         | Score |
| ----------- | ----- |
| < 3 months  | 1.0   |
| 3-12 months | 0.7   |
| 1-3 years   | 0.4   |
| > 3 years   | 0.2   |

## API Changes

### Text Ingestion Endpoint

**Before (removed)**:

```json
{
  "text": "...",
  "filename": "...",
  "trust_score": 0.75
}
```

**Now**:

```json
{
  "text": "...",
  "filename": "...",
  "source_type": "verified_tutorial"
}
```

### Available source_type Values

- `official_docs` - Official documentation
- `academic_paper` - Academic/peer-reviewed paper
- `verified_tutorial` - Verified tutorial or guide
- `trusted_blog` - Blog from trusted source
- `community_qa` - Community Q&A site
- `user_generated` (default) - User-generated content
- `unverified` - Unverified source

### Response Example

**GET /ingest/documents/{document_id}**

```json
{
  "id": 1,
  "filename": "tutorial.txt",
  "source": "upload",
  "upload_method": "ui-upload",
  "confidence_score": 0.72,
  "source_reliability": 0.85,
  "content_quality": 0.6,
  "consensus_score": 0.65,
  "recency_score": 1.0,
  "description": "Python tutorial",
  "status": "completed",
  "total_chunks": 5,
  "chunks": [
    {
      "id": 1,
      "index": 0,
      "text_length": 450,
      "vector_id": "1000",
      "confidence_score": 0.7,
      "consensus_similarities": [0.65, 0.62, 0.58]
    }
  ]
}
```

### Retrieval with Confidence Scores

**POST /retrieve/search**

Results now include `confidence_score` for each chunk:

```json
{
  "query": "Python loops",
  "results": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "chunk_index": 0,
      "text": "...",
      "score": 0.92,
      "confidence_score": 0.7,
      "metadata": {
        "filename": "tutorial.txt",
        "confidence_score": 0.7,
        "document_confidence_score": 0.72
      }
    }
  ]
}
```

## Database Schema

### Documents Table

New columns:

- `confidence_score` (FLOAT, NOT NULL, DEFAULT 0.5)
- `source_reliability` (FLOAT, NOT NULL, DEFAULT 0.5)
- `content_quality` (FLOAT, NOT NULL, DEFAULT 0.5)
- `consensus_score` (FLOAT, NOT NULL, DEFAULT 0.5)
- `recency_score` (FLOAT, NOT NULL, DEFAULT 0.5)
- `confidence_metadata` (TEXT) - JSON with detailed calculation data

Removed columns:

- `trust_score` (old manual field)

Index added:

- `idx_confidence_score` on `confidence_score` column

### DocumentChunks Table

New columns:

- `confidence_score` (FLOAT, NOT NULL, DEFAULT 0.5)
- `consensus_similarity_scores` (TEXT) - JSON array of similarity scores

Index added:

- `idx_chunk_confidence_score` on `confidence_score` column

## Migration

Run the migration to add new columns:

```bash
python -m backend.database.migrate_add_confidence_scoring
```

Or programmatically:

```python
from database.migrate_add_confidence_scoring import migrate_add_confidence_scoring

result = migrate_add_confidence_scoring()
print(f"Migration complete: {result}")
```

## Implementation Details

### ConfidenceScorer Class

Located in `backend/confidence_scorer/confidence_scorer.py`

Key methods:

```python
scorer = ConfidenceScorer(embedding_model, qdrant_client)

# Calculate all scores
scores = scorer.calculate_confidence_score(
    text_content="...",
    source_type="verified_tutorial",
    created_at=datetime.utcnow(),
    existing_chunks=[...],  # optional, for offline consensus
)

# Returns:
{
    "confidence_score": 0.72,
    "source_reliability": 0.85,
    "content_quality": 0.60,
    "consensus_score": 0.65,
    "recency": 1.0,
    "similarity_scores": [0.65, 0.62, 0.58],
}
```

### Integration with Ingestion

During document ingestion:

1. Document-level confidence score is calculated
2. All chunks are analyzed for content quality
3. Consensus scores calculated via vector similarity
4. Scores stored in database
5. Metadata preserved for audit trails

## Querying by Confidence

### Find High-Confidence Documents

```python
from models.database_models import Document
from database.session import SessionLocal

db = SessionLocal()
high_confidence = db.query(Document).filter(
    Document.confidence_score >= 0.7
).all()
```

### Sort by Confidence in Retrieval

Modify retrieval to prioritize by confidence:

```python
# In retrieve() method, sort results by combined score:
score = result["score"] * 0.6 + result["confidence_score"] * 0.4
```

## Best Practices

1. **Specify Source Type**: Always provide accurate `source_type` for best scoring
2. **Well-Structured Content**: Use headers and organization to boost content_quality
3. **Include References**: Citations improve quality scores
4. **Code Examples**: Technical content gets quality boost
5. **Monitor Consensus**: Use similarity scores to identify contradictions

## Troubleshooting

### All scores are 0.5

- Check if embedding model is initialized
- Verify database tables have new columns
- Run migration script: `python -m backend.database.migrate_add_confidence_scoring`

### Consensus scores are always low

- May indicate new knowledge domain
- Content differs significantly from existing base
- This is normal for novel information

### Performance issues

- Add indexes: `CREATE INDEX idx_confidence_score ON documents(confidence_score)`
- Vector similarity calculation uses existing Qdrant infrastructure
- Consensus calculation happens at ingestion time (not on retrieval)

## Future Enhancements

Potential additions:

1. **Fake News Detection Model**: Integrate small ML models for content verification
2. **User Feedback Loop**: Adjust consensus based on user ratings
3. **Time-Decay**: Further weight recency based on domain needs
4. **Custom Weights**: Allow per-user weight customization
5. **Anomaly Detection**: Flag outlier confidence scores

## Related Files

- `backend/confidence_scorer/confidence_scorer.py` - Main scoring logic
- `backend/ingestion/service.py` - Integration with ingestion
- `backend/models/database_models.py` - Schema definitions
- `backend/api/ingest.py` - API endpoints
- `backend/api/retrieve.py` - Retrieval with confidence scores
- `backend/retrieval/retriever.py` - Retriever implementation
- `backend/database/migrate_add_confidence_scoring.py` - Database migration
