# Synaptic Ingestion

**File:** `cognitive/magma/synaptic_ingestion.py`

## Overview

Magma Memory - Synaptic Ingestion

Write/update path for the Magma memory system:
1. Event Segmentation - Break content into meaningful segments
2. Dense/Sparse Embedding - Generate embeddings for segments
3. Semantic Linking - Connect to existing semantic concepts
4. Temporal Linking - Establish time relationships
5. Entity Linking - Link entities across contexts
6. Causal Inference - Detect cause-effect relationships

This is the ingestion pipeline that feeds the relation graphs.

## Classes

- `SegmentType`
- `Segment`
- `IngestionResult`
- `EventSegmenter`
- `SemanticLinker`
- `TemporalLinker`
- `EntityLinker`
- `CausalLinker`
- `SynapticIngestionPipeline`

## Key Methods

- `segment()`
- `link_segment()`
- `link_segment()`
- `link_entities()`
- `detect_causal_relations()`
- `link_causal_relations()`
- `ingest()`
- `ingest_batch()`

---
*Grace 3.1*
