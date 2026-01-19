# Learning Efficiency Tracking - Data-to-Insight Ratio System

## 🎯 What This Does

Tracks **how much data is required to gain new insights, domains, or intelligence**.

This answers questions like:
- "How many MB of data does Grace need to learn Python?"
- "What's the most efficient domain to learn first?"
- "Is Grace getting smarter faster over time?"
- "Which learning path requires the least data?"

---

## 🏗️ Architecture

### Core Concept

```
Data Consumed → Insights Gained → Efficiency Metrics
     ↓                ↓                  ↓
  Bytes         New Concepts      Bytes/Insight
  Documents     Patterns          Documents/Insight
  Chunks        Skills            Chunks/Insight
                Domains           Learning Curve
```

### Components

1. **LearningEfficiencyTracker** (`backend/cognitive/learning_efficiency_tracker.py`)
   - Tracks data consumption (bytes, documents, chunks)
   - Records insights gained
   - Calculates efficiency metrics
   - Identifies optimal learning paths

2. **Learning Efficiency API** (`backend/api/learning_efficiency_api.py`)
   - REST endpoints for tracking and querying
   - Real-time metrics
   - Domain-specific analysis

---

## 📊 Key Metrics Tracked

### 1. Data-to-Insight Ratios

- **Bytes per Insight**: Average bytes needed to gain one insight
- **Documents per Insight**: Average documents needed
- **Chunks per Insight**: Average chunks needed

### 1b. Time-to-Insight Ratios (NEW!)

- **Seconds per Insight**: Average time needed to gain one insight
- **Hours per Insight**: Average hours needed per insight
- **Insights per Hour**: Learning velocity (how fast Grace learns)
- **Insights per Day**: Daily learning rate

**Example:**
```json
{
  "bytes_per_insight": 51200,      // 50 KB per insight
  "documents_per_insight": 0.5,    // Half a document per insight
  "chunks_per_insight": 2.3,       // 2.3 chunks per insight
  "seconds_per_insight": 120,      // 2 minutes per insight (NEW!)
  "hours_per_insight": 0.033,      // 0.033 hours per insight (NEW!)
  "insights_per_hour": 30,         // 30 insights per hour (NEW!)
  "insights_per_day": 720          // 720 insights per day (NEW!)
}
```

### 2. Domain Acquisition Efficiency

- **Bytes per Domain**: Data needed to acquire a new domain
- **Time to Domain**: How long to acquire a domain (NEW: temporal tracking)
- **Average Time to Domain**: Average time across all domains
- **Domain-Specific Efficiency**: Efficiency per domain (data + time)
- **Domain Learning Velocity**: Insights per hour per domain

**Example:**
```json
{
  "python": {
    "bytes_per_insight": 25600,    // 25 KB per insight (very efficient!)
    "seconds_per_insight": 60,     // 1 minute per insight (NEW!)
    "insights_per_hour": 60,       // 60 insights/hour (NEW!)
    "time_to_acquisition": 2.5,    // 2.5 hours to acquire domain (NEW!)
    "total_insights": 45,
    "skill_level": "INTERMEDIATE"
  },
  "javascript": {
    "bytes_per_insight": 102400,   // 100 KB per insight (less efficient)
    "seconds_per_insight": 300,    // 5 minutes per insight (NEW!)
    "insights_per_hour": 12,       // 12 insights/hour (NEW!)
    "time_to_acquisition": 5.0,    // 5 hours to acquire domain (NEW!)
    "total_insights": 12,
    "skill_level": "BEGINNER"
  }
}
```

### 3. Learning Curve

Tracks efficiency over time:
- **Data Efficiency Curve**: Bytes per insight over insight count
- **Temporal Learning Curve**: Efficiency over time (NEW!)
- **Velocity Trend**: Insights per hour over time (NEW!)
- **Time Trend**: Seconds per insight over time (NEW!)
- **Improving**: Getting more efficient (less data/time per insight)
- **Stable**: Consistent efficiency
- **Declining**: Getting less efficient (more data/time needed)

**Example:**
```json
{
  "learning_curve": [
    {"insight_count": 1, "efficiency": 102400},   // First insight: 100 KB
    {"insight_count": 10, "efficiency": 51200},  // 10th insight: 50 KB
    {"insight_count": 50, "efficiency": 25600}   // 50th insight: 25 KB
  ],
  "temporal_learning_curve": [
    {"timestamp": "2026-01-11T10:00:00", "efficiency": 102400},
    {"timestamp": "2026-01-11T11:00:00", "efficiency": 51200},
    {"timestamp": "2026-01-11T12:00:00", "efficiency": 25600}
  ],
  "velocity_trend": [
    {"timestamp": "2026-01-11T10:00:00", "insights_per_hour": 10},
    {"timestamp": "2026-01-11T11:00:00", "insights_per_hour": 20},
    {"timestamp": "2026-01-11T12:00:00", "insights_per_hour": 30}
  ],
  "trend": "improving"  // Getting smarter faster!
}
```

### 4. Skill Progression Efficiency

Tracks data AND time needed per skill level:
- **NOVICE**: Initial learning (data + time)
- **BEGINNER**: Basic understanding (data + time)
- **INTERMEDIATE**: Can apply with guidance (data + time)
- **ADVANCED**: Can apply independently (data + time)
- **EXPERT**: Can teach others (data + time)

**Example:**
```json
{
  "bytes_per_skill_level": {
    "NOVICE": 51200,        // 50 KB to get started
    "BEGINNER": 102400,     // 100 KB to understand basics
    "INTERMEDIATE": 204800,  // 200 KB to apply
    "ADVANCED": 512000,     // 500 KB to master
    "EXPERT": 1024000       // 1 MB to teach
  },
  "time_per_skill_level": {
    "NOVICE": "PT30M",      // 30 minutes to get started (NEW!)
    "BEGINNER": "PT2H",     // 2 hours to understand basics (NEW!)
    "INTERMEDIATE": "PT8H",  // 8 hours to apply (NEW!)
    "ADVANCED": "PT24H",    // 24 hours to master (NEW!)
    "EXPERT": "PT72H"       // 72 hours to teach (NEW!)
  }
}
```

---

## 🚀 Usage

### 1. Record Data Consumption

**Automatic (during ingestion):**
```python
# This happens automatically when documents are ingested
POST /learning-efficiency/record-data-consumption
{
  "bytes_consumed": 1048576,      // 1 MB
  "documents_consumed": 1,
  "chunks_consumed": 50,
  "domain": "python",
  "genesis_key_id": "GK-abc123"
}
```

### 2. Record Insights Gained

**When Grace learns something new:**
```python
POST /learning-efficiency/record-insight
{
  "insight_type": "concept",      // or "pattern", "skill", "domain", "procedure"
  "description": "Learned about Python decorators",
  "trust_score": 0.85,
  "domain": "python",
  "learning_example_id": "LE-123",
  "genesis_key_id": "GK-abc123",
  "time_to_insight_seconds": 120  // Optional: 2 minutes spent learning (NEW!)
}
```

### 3. Get Efficiency Metrics

**Overall metrics:**
```bash
GET /learning-efficiency/metrics
```

**Response:**
```json
{
  "summary": {
    "total_bytes_consumed": 104857600,    // 100 MB
    "total_documents_consumed": 232,
    "total_chunks_consumed": 67431,
    "total_insights": 1542,
    "total_domains": 12
  },
  "efficiency": {
    "bytes_per_insight": 68000,           // 68 KB per insight
    "documents_per_insight": 0.15,
    "chunks_per_insight": 43.7,
    "seconds_per_insight": 180,           // 3 minutes per insight (NEW!)
    "hours_per_insight": 0.05,            // 0.05 hours per insight (NEW!)
    "insights_per_hour": 20,              // 20 insights/hour (NEW!)
    "insights_per_day": 480               // 480 insights/day (NEW!)
  },
  "domains": {
    "python": {
      "insights": 245,
      "trust_score": 0.88,
      "skill_level": "INTERMEDIATE",
      "data_at_acquisition": {"bytes": 5120000}
    }
  },
  "domain_efficiency": {
    "python": {
      "bytes_per_insight": 25600,         // Very efficient!
      "documents_per_insight": 0.08,
      "chunks_per_insight": 12.3,
      "total_insights": 245
    }
  },
  "domain_temporal_efficiency": {
    "python": {
      "seconds_per_insight": 60,          // 1 minute per insight (NEW!)
      "hours_per_insight": 0.017,         // Very fast learning (NEW!)
      "insights_per_hour": 60,            // 60 insights/hour (NEW!)
      "time_to_acquisition": 2.5,        // 2.5 hours to acquire (NEW!)
      "first_insight": "2026-01-11T10:00:00",
      "last_insight": "2026-01-11T12:30:00"
    }
  },
  "learning_curve": [
    {"insight_count": 1, "efficiency": 102400},
    {"insight_count": 100, "efficiency": 51200},
    {"insight_count": 500, "efficiency": 25600},
    {"insight_count": 1542, "efficiency": 68000}
  ],
  "temporal_learning_curve": [
    {"timestamp": "2026-01-11T10:00:00", "efficiency": 102400},
    {"timestamp": "2026-01-11T11:00:00", "efficiency": 51200},
    {"timestamp": "2026-01-11T12:00:00", "efficiency": 25600}
  ],
  "velocity_trend": [
    {"timestamp": "2026-01-11T10:00:00", "insights_per_hour": 10},
    {"timestamp": "2026-01-11T11:00:00", "insights_per_hour": 20},
    {"timestamp": "2026-01-11T12:00:00", "insights_per_hour": 30}
  ],
  "time_per_insight_trend": [
    {"timestamp": "2026-01-11T10:00:00", "seconds_per_insight": 360},
    {"timestamp": "2026-01-11T11:00:00", "seconds_per_insight": 180},
    {"timestamp": "2026-01-11T12:00:00", "seconds_per_insight": 120}
  ],
  "optimal_paths": {
    "most_efficient_domains": [
      {"domain": "python", "bytes_per_insight": 25600},
      {"domain": "javascript", "bytes_per_insight": 51200},
      {"domain": "sql", "bytes_per_insight": 76800}
    ],
    "learning_path": ["python", "javascript", "sql", "docker", "kubernetes"]
  }
}
```

### 4. Get Optimal Learning Paths

**Recommended learning order:**
```bash
GET /learning-efficiency/optimal-paths
```

**Response:**
```json
{
  "recommendations": {
    "most_efficient_domains": [
      {"domain": "python", "bytes_per_insight": 25600},
      {"domain": "javascript", "bytes_per_insight": 51200}
    ],
    "learning_path": [
      "python",
      "javascript",
      "sql",
      "docker"
    ],
    "efficiency_insights": {
      "average_bytes_per_insight": 68000,
      "most_efficient_domain": "python",
      "least_efficient_domain": "kubernetes"
    }
  }
}
```

### 5. Domain-Specific Efficiency

**Get efficiency for a specific domain:**
```bash
GET /learning-efficiency/domain/python/efficiency
```

**Response:**
```json
{
  "domain": "python",
  "efficiency": {
    "bytes_per_insight": 25600,
    "documents_per_insight": 0.08,
    "chunks_per_insight": 12.3
  },
  "data_consumption": {
    "bytes": 6272000,
    "documents": 19,
    "chunks": 3014
  },
  "acquisition": {
    "skill_level": "INTERMEDIATE",
    "total_insights": 245,
    "trust_score": 0.88,
    "data_at_acquisition": {
      "bytes": 5120000,
      "documents": 15,
      "chunks": 2500
    }
  }
}
```

### 6. Quick Summary

**Human-readable summary:**
```bash
GET /learning-efficiency/summary
```

**Response:**
```json
{
  "total_data_consumed": {
    "bytes": 104857600,
    "mb": 100.0,
    "gb": 0.1,
    "documents": 232,
    "chunks": 67431
  },
  "insights_gained": {
    "total": 1542,
    "by_type": {
      "concept": 892,
      "pattern": 234,
      "skill": 312,
      "domain": 12,
      "procedure": 92
    }
  },
  "efficiency": {
    "bytes_per_insight": 68000,
    "mb_per_insight": 0.065,
    "documents_per_insight": 0.15,
    "chunks_per_insight": 43.7
  },
  "domains": {
    "total": 12,
    "list": ["python", "javascript", "sql", "docker", "kubernetes", ...],
    "bytes_per_domain": 8738133,
    "mb_per_domain": 8.33
  },
  "learning_curve": {
    "trend": "improving",
    "first_insight_efficiency": 102400,
    "latest_efficiency": 25600
  }
}
```

---

## 🔄 Integration Points

### Automatic Integration

1. **During Ingestion** (`backend/ingestion/service.py`):
   ```python
   from api.learning_efficiency_api import record_data_consumption
   
   # After ingesting document
   await record_data_consumption({
       "bytes_consumed": file_size,
       "documents_consumed": 1,
       "chunks_consumed": len(chunks),
       "domain": detected_domain,
       "genesis_key_id": genesis_key_id
   })
   ```

2. **When Learning** (`backend/cognitive/learning_memory.py`):
   ```python
   from api.learning_efficiency_api import record_insight
   
   # When trust score >= 0.7 (episodic memory)
   await record_insight({
       "insight_type": "concept",
       "description": "Learned about X",
       "trust_score": trust_score,
       "domain": domain,
       "learning_example_id": example_id,
       "genesis_key_id": genesis_key_id
   })
   ```

3. **When Domain Acquired** (`backend/cognitive/active_learning_system.py`):
   ```python
   # When skill level changes
   tracker.record_domain_acquisition(
       domain="python",
       skill_level="INTERMEDIATE"
   )
   ```

---

## 📈 Use Cases

### 1. Optimize Learning Order

**Question:** "What should Grace learn first?"

**Answer:** Use optimal paths API:
```bash
GET /learning-efficiency/optimal-paths
# → Learn Python first (most efficient)
```

### 2. Track Learning Progress

**Question:** "Is Grace getting smarter faster?"

**Answer:** Check learning curve and velocity:
```bash
GET /learning-efficiency/summary
# → "trend": "improving" (efficiency decreasing = getting smarter)
# → "insights_per_hour": increasing (learning velocity improving)
# → "seconds_per_insight": decreasing (faster learning)
```

### 3. Identify Efficient Domains

**Question:** "Which domains does Grace learn fastest?"

**Answer:** Check domain efficiency:
```bash
GET /learning-efficiency/metrics
# → python: 25 KB/insight (most efficient)
# → kubernetes: 200 KB/insight (least efficient)
```

### 4. Estimate Learning Time

**Question:** "How much data AND time does Grace need to learn X?"

**Answer:** Use domain efficiency:
```bash
GET /learning-efficiency/domain/python/efficiency
# → 25 KB per insight, 60 seconds per insight
# → Estimate: 100 insights × 25 KB = 2.5 MB data
# → Estimate: 100 insights × 60 seconds = 100 minutes = 1.67 hours
```

### 5. Compare Learning Efficiency

**Question:** "Is Grace learning Python faster than JavaScript?"

**Answer:** Compare domain efficiencies (data + time):
```bash
GET /learning-efficiency/domain/python/efficiency
GET /learning-efficiency/domain/javascript/efficiency
# → Python: 25 KB/insight, 60 sec/insight, 60 insights/hour
# → JavaScript: 50 KB/insight, 300 sec/insight, 12 insights/hour
# → Python is 2x more data-efficient AND 5x faster!
```

---

## 🎯 Key Insights This Enables

1. **Learning Efficiency**: Track how efficiently Grace learns (data + time)
2. **Learning Velocity**: Track how fast Grace learns (insights per hour)
3. **Optimal Paths**: Identify best learning order (by efficiency + speed)
4. **Domain Comparison**: Compare efficiency AND speed across domains
5. **Progress Tracking**: See if Grace is getting smarter faster (data + time trends)
6. **Resource Planning**: Estimate data AND time needed for new domains
7. **Quality Assessment**: High efficiency + high velocity = high-quality learning materials
8. **Temporal Patterns**: Identify when Grace learns fastest (time-of-day patterns)

---

## 🔮 Future Enhancements

1. **Predictive Modeling**: Predict data needed for new domains
2. **Efficiency Alerts**: Alert when efficiency drops
3. **Learning Recommendations**: Suggest what to learn next
4. **Efficiency Visualization**: Charts and graphs
5. **Comparative Analysis**: Compare Grace to other systems
6. **Efficiency Optimization**: Automatically optimize learning paths

---

## 📝 Example Scenarios

### Scenario 1: Learning Python

```
1. Ingest 10 MB of Python docs
   → record_data_consumption(10MB, 5 docs, 200 chunks, "python")

2. Grace learns 50 concepts
   → record_insight("concept", "decorators", 0.85, "python") × 50

3. Check efficiency
   → GET /learning-efficiency/domain/python/efficiency
   → Result: 200 KB per insight (very efficient!)

4. Grace reaches INTERMEDIATE level
   → record_domain_acquisition("python", "INTERMEDIATE")
   → Total: 10 MB for INTERMEDIATE Python
```

### Scenario 2: Comparing Domains

```
Python:  25 KB per insight  (most efficient)
SQL:     50 KB per insight
Docker:  100 KB per insight
K8s:     200 KB per insight (least efficient)

Recommendation: Learn Python first, then SQL, then Docker, then K8s
```

### Scenario 3: Learning Curve (Data + Time)

```
Data Efficiency:
Insight 1:   100 KB per insight
Insight 10:  50 KB per insight
Insight 50:  25 KB per insight
Insight 100: 20 KB per insight

Time Efficiency:
Insight 1:   360 seconds per insight (6 minutes)
Insight 10:  180 seconds per insight (3 minutes)
Insight 50:  120 seconds per insight (2 minutes)
Insight 100: 60 seconds per insight (1 minute)

Velocity:
Hour 1:  10 insights/hour
Hour 2:  20 insights/hour
Hour 3:  30 insights/hour
Hour 4:  40 insights/hour

Trend: Improving! Grace is getting smarter AND faster!
```

---

**This system transforms Grace from "learning" to "learning efficiently" - tracking exactly how much data is needed to gain new intelligence!** 🚀
