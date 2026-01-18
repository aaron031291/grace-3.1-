# Reverse KNN Proactive Learning System

## Overview

The Oracle doesn't just passively receive knowledge - it **actively seeks to expand** using Reverse KNN.

Instead of traditional KNN ("find items similar to my query"), Reverse KNN asks:
> "What knowledge is MISSING around what I already know?"

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVERSE KNN ALGORITHM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EMBED ALL ORACLE KNOWLEDGE                                  │
│     ↓                                                           │
│  2. BUILD KNN GRAPH (find neighbors for each item)              │
│     ↓                                                           │
│  3. CLUSTER ANALYSIS                                            │
│     • Dense clusters = well-covered topics                      │
│     • Sparse clusters = knowledge gaps                          │
│     • Frontier clusters = edges of known knowledge              │
│     • Isolated clusters = disconnected knowledge                │
│     ↓                                                           │
│  4. REVERSE KNN: Count inbound references                       │
│     • Few items point TO this cluster = high gap score          │
│     • Many items reference it = well-connected                  │
│     ↓                                                           │
│  5. GENERATE EXPANSION QUERIES                                  │
│     • Target original sources (GitHub, SO, arXiv)               │
│     • Strategy based on cluster type                            │
│     ↓                                                           │
│  6. LLM OPTIMIZATION                                            │
│     • Improve queries for relevance                             │
│     • Discover hidden connections                               │
│     ↓                                                           │
│  7. EXECUTE & INGEST                                            │
│     • Fetch from sources                                        │
│     • Ingest through Oracle Hub                                 │
│     ↓                                                           │
│  8. REPEAT (continuous loop)                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Gap Score (Reverse KNN)

Traditional KNN: "How many neighbors does this item have?"
Reverse KNN: "How many OTHER items have this as a neighbor?"

**Low reverse KNN count = isolated knowledge = HIGH GAP SCORE**

```python
# The reverse KNN insight:
gap_score = 1.0 - (reverse_knn_count / expected_references)

# Cluster types boost gap score:
if sparse: gap_score *= 1.3
if frontier: gap_score *= 1.5
if isolated: gap_score *= 1.8
```

### Cluster Types

| Type | Description | Strategy |
|------|-------------|----------|
| **Dense** | Well-covered topic | Depth First - go deeper |
| **Sparse** | Needs more knowledge | Gap Fill - find missing pieces |
| **Frontier** | Edge of knowledge | Frontier Push - expand boundaries |
| **Isolated** | Disconnected | Breadth First - find connections |

### Expansion Strategies

| Strategy | Description | When Used |
|----------|-------------|-----------|
| `depth` | Go deeper on existing topics | Dense clusters |
| `breadth` | Explore related topics | Isolated clusters |
| `gap_fill` | Fill sparse areas | Sparse clusters |
| `frontier` | Push knowledge boundaries | Frontier clusters |
| `reinforce` | Strengthen weak connections | Low confidence items |

## LLM Orchestration

The system uses LLM for:

1. **Query Optimization** - Improve expansion queries
2. **Connection Discovery** - Find hidden links between clusters
3. **Gap Analysis** - Identify knowledge holes

### Example LLM Optimization

**Input Query:** `error handling patterns`
**LLM Output:**
```json
{
    "optimized_query": "Python exception handling best practices try except finally",
    "related_queries": ["error recovery strategies", "graceful degradation patterns"],
    "key_terms": ["exception", "retry", "fallback", "circuit breaker"],
    "reasoning": "More specific terms for better code search results"
}
```

## API Endpoints

### Core Operations

| Endpoint | Description |
|----------|-------------|
| `POST /proactive-learning/analyze` | Analyze knowledge landscape |
| `POST /proactive-learning/generate-queries` | Generate expansion queries |
| `POST /proactive-learning/execute-expansions` | Execute and ingest |
| `POST /proactive-learning/run-cycle` | Run complete cycle |

### LLM Operations

| Endpoint | Description |
|----------|-------------|
| `POST /proactive-learning/discover-connections` | LLM find hidden links |

### Continuous Learning

| Endpoint | Description |
|----------|-------------|
| `POST /proactive-learning/start` | Start continuous learning |
| `POST /proactive-learning/stop` | Stop continuous learning |

### Monitoring

| Endpoint | Description |
|----------|-------------|
| `GET /proactive-learning/status` | System status |
| `GET /proactive-learning/clusters` | All clusters |
| `GET /proactive-learning/pending-queries` | Pending expansions |
| `GET /proactive-learning/stats` | Detailed statistics |

## Usage Examples

### 1. Analyze Knowledge Gaps
```bash
curl -X POST http://localhost:8000/proactive-learning/analyze
```

Response:
```json
{
    "total_knowledge_items": 150,
    "clusters": 12,
    "sparse_clusters": 3,
    "frontier_clusters": 2,
    "clusters_data": [
        {
            "cluster_id": "CLUSTER-abc123",
            "type": "sparse",
            "centroid": "async error handling",
            "members": 5,
            "gap_score": 0.72,
            "priority": 0.85,
            "sources": ["github", "stackoverflow"]
        }
    ]
}
```

### 2. Generate Optimized Queries
```bash
curl -X POST http://localhost:8000/proactive-learning/generate-queries \
  -H "Content-Type: application/json" \
  -d '{"max_queries": 10, "use_llm_optimization": true}'
```

### 3. Execute Expansions
```bash
curl -X POST "http://localhost:8000/proactive-learning/execute-expansions?max_per_source=5"
```

### 4. Start Continuous Learning
```bash
curl -X POST http://localhost:8000/proactive-learning/start \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 600}'
```

### 5. Discover Hidden Connections
```bash
curl -X POST http://localhost:8000/proactive-learning/discover-connections
```

## Integration with Oracle Hub

The Reverse KNN system is fully integrated with the Oracle Hub:

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Reverse KNN     │────▶│  Oracle Hub     │────▶│  Oracle Core     │
│  (Find Gaps)     │     │  (Ingest)       │     │  (Store)         │
└──────────────────┘     └─────────────────┘     └──────────────────┘
        │                                                │
        │                                                │
        ▼                                                ▼
┌──────────────────┐                         ┌──────────────────┐
│  Source APIs     │                         │  Knowledge Base  │
│  GitHub, SO, etc │                         │  oracle/         │
└──────────────────┘                         └──────────────────┘
```

## Source-Specific Query Generation

Queries are tailored to each source:

### GitHub
- Depth: `{topic} implementation example code`
- Gap Fill: `{topic} edge cases error handling`
- Breadth: `{topic} related patterns best practices`

### Stack Overflow
- Gap Fill: `{topic} common issues solutions`
- Default: `{topic} how to tutorial`

### AI Research
- Frontier: `{topic} latest advances state of the art`
- Default: `{topic} technique algorithm`

### Templates
- All: `{topic} template pattern boilerplate`

## Files Created

| File | Purpose |
|------|---------|
| `backend/oracle_intelligence/reverse_knn_learning.py` | Core algorithm |
| `backend/api/reverse_knn_api.py` | REST API endpoints |

## Continuous Learning Loop

Every 10 minutes (configurable):
1. Analyze all Oracle knowledge
2. Identify sparse/frontier clusters
3. Generate expansion queries
4. Optimize with LLM
5. Fetch from original sources
6. Ingest new knowledge
7. Repeat

## Summary

✅ **Reverse KNN** identifies knowledge gaps by counting inbound references
✅ **Cluster Analysis** categorizes knowledge areas by density
✅ **LLM Orchestration** optimizes queries and discovers connections
✅ **Same Sources** uses GitHub, SO, arXiv - the original ingestion routes
✅ **Continuous Loop** proactively expands knowledge every 10 minutes
✅ **Full Integration** with Oracle Hub for ingestion and storage
