# KPI as Trust Inputs - System Documentation

## Overview

Grace's KPI tracking system translates component performance metrics into trust scores. Every time a component does its job, its KPIs tick up. Over time, these KPIs aggregate into operational health signals that feed directly into the trust scoring system.

---

## 🎯 Core Concept

**KPIs → Trust Scores → System-Wide Trust**

1. **Component Actions** → Increment KPIs
2. **KPIs Aggregate** → Operational Health Signals
3. **Health Signals** → Component Trust Scores
4. **Component Trust** → System-Wide Trust Metric

---

## 📊 KPI Tracking System

### Location
- **Core System:** `backend/ml_intelligence/kpi_tracker.py`
- **Layer 1 Connector:** `backend/layer1/components/kpi_connector.py`

### Key Components

#### 1. **KPI Class**
Tracks individual performance metrics:
```python
@dataclass
class KPI:
    component_name: str
    metric_name: str
    value: float      # Accumulated value
    count: int        # Number of increments
    timestamp: datetime
    metadata: Dict[str, Any]
```

#### 2. **ComponentKPIs Class**
Aggregates all KPIs for a single component:
```python
@dataclass
class ComponentKPIs:
    component_name: str
    kpis: Dict[str, KPI]
    created_at: datetime
    updated_at: datetime
    
    def get_trust_score(metric_weights: Dict[str, float]) -> float:
        """Convert KPIs to trust score (0-1)"""
```

#### 3. **KPITracker Class**
Tracks KPIs for all components:
```python
class KPITracker:
    def increment_kpi(component_name, metric_name, value=1.0)
    def get_component_trust_score(component_name) -> float
    def get_system_trust_score(component_weights) -> float
    def get_health_signal(component_name) -> Dict[str, Any]
```

---

## 🔄 How It Works

### 1. **KPI Incrementing**
Every time a component performs an action, its KPI increments:

```python
from ml_intelligence.kpi_tracker import get_kpi_tracker

tracker = get_kpi_tracker()

# Component does its job → KPI ticks up
tracker.increment_kpi("rag", "requests_handled", 1.0)
tracker.increment_kpi("rag", "successes", 1.0)
tracker.increment_kpi("ingestion", "files_processed", 1.0)
```

### 2. **KPI-to-Trust Conversion**
KPIs are converted to trust scores based on:
- **Frequency**: More actions = higher trust (normalized)
- **Consistency**: Regular actions = higher trust
- **Metric Weights**: Different metrics weighted differently

```python
# Get component trust score
trust_score = tracker.get_component_trust_score("rag")
# Returns: 0.0 - 1.0

# Trust calculation:
# - Higher count → Higher trust
# - Normalized: count / (count + 10) approaches 1.0
# - Weighted by metric importance
```

### 3. **System-Wide Trust Aggregation**
All component trust scores roll up into system-wide trust:

```python
system_trust = tracker.get_system_trust_score(component_weights)
# Returns: 0.0 - 1.0 (weighted average of all components)
```

---

## 🔌 Layer 1 Integration

### Automatic KPI Tracking

The KPI connector automatically tracks component actions via Layer 1 message bus:

```python
from layer1.components import create_kpi_connector

kpi_connector = create_kpi_connector(message_bus=message_bus)
```

**Autonomous Actions Registered:**
- `rag.query_received` → Track `rag.requests_handled`
- `rag.retrieval_success` → Track `rag.successes`
- `ingestion.file_processed` → Track `ingestion.files_processed`
- `knowledge_base.ingestion_complete` → Track `knowledge_base.repositories_ingested`
- ... and more

### Request Handlers

**Increment KPI:**
```python
await message_bus.send_request(
    "kpi.increment",
    payload={
        "component_name": "rag",
        "metric_name": "requests_handled",
        "value": 1.0,
        "metadata": {"source": "user_query"},
    }
)
```

**Get Component Trust:**
```python
result = await message_bus.send_request(
    "kpi.get_component_trust",
    payload={"component_name": "rag"}
)
# Returns: {"trust_score": 0.85, "health": {...}}
```

**Get System Trust:**
```python
result = await message_bus.send_request(
    "kpi.get_system_trust",
    payload={"component_weights": {"rag": 2.0, "ingestion": 1.0}}
)
# Returns: {"system_trust_score": 0.82, "system_health": {...}}
```

---

## 🧠 Trust Score Calculation

### Component Trust Score

```python
def get_trust_score(metric_weights: Dict[str, float]) -> float:
    # For each metric:
    #   normalized = min(count / (count + 10), 1.0)
    #   weighted_sum += weight * normalized
    
    # trust_score = weighted_sum / total_weight
    # Bounded: 0.0 - 1.0
```

**Example:**
- Component: `rag`
- Metrics: `requests_handled: 100`, `successes: 95`
- Weights: `requests_handled: 1.0`, `successes: 2.0`
- Trust Score: `0.90` (high trust due to high success rate)

### System Trust Score

```python
def get_system_trust_score(component_weights: Dict[str, float]) -> float:
    # For each component:
    #   component_trust = component.get_trust_score()
    #   weighted_sum += weight * component_trust
    
    # system_trust = weighted_sum / total_weight
    # Bounded: 0.0 - 1.0
```

**Example:**
- Components: `rag: 0.90`, `ingestion: 0.85`, `memory_mesh: 0.88`
- Weights: `rag: 2.0`, `ingestion: 1.0`, `memory_mesh: 1.5`
- System Trust: `0.88` (weighted average)

---

## 📈 Operational Health Signals

### Component Health

```python
health = tracker.get_health_signal("rag")
# Returns:
# {
#     "component_name": "rag",
#     "status": "excellent",  # excellent/good/fair/poor
#     "trust_score": 0.90,
#     "kpi_count": 2,
#     "total_actions": 195,
#     "updated_at": "2026-01-11T12:00:00"
# }
```

**Status Thresholds:**
- `excellent`: trust >= 0.8
- `good`: trust >= 0.6
- `fair`: trust >= 0.4
- `poor`: trust < 0.4

### System Health

```python
system_health = tracker.get_system_health()
# Returns:
# {
#     "system_trust_score": 0.88,
#     "status": "excellent",
#     "component_count": 6,
#     "components": {
#         "rag": {...},
#         "ingestion": {...},
#         ...
#     }
# }
```

---

## 🔗 Integration with Trust-Aware Systems

### Trust-Aware Embeddings

KPI-based trust scores can feed into trust-aware embeddings:

```python
from ml_intelligence.trust_aware_embedding import TrustContext

# Get component trust from KPIs
component_trust = tracker.get_component_trust_score("rag")

# Create trust context
trust_context = TrustContext(
    trust_score=component_trust,
    source_reliability=component_trust,
    validation_count=tracker.get_component_kpis("rag").get_kpi("successes").count,
)

# Use in trust-aware embedding
embedding = trust_aware_model.embed_text_with_trust(
    text,
    trust_context=trust_context
)
```

### Neuro-Symbolic Reasoning

KPI trust scores inform neuro-symbolic reasoning:

```python
# Get system trust
system_trust = tracker.get_system_trust_score()

# Use in neuro-symbolic reasoner
result = await neuro_symbolic_reasoner.reason(
    query=query,
    context={"system_trust": system_trust},
    min_overall_trust=system_trust * 0.9,  # Scale threshold by system trust
)
```

---

## 📝 Usage Examples

### Example 1: Track Component Action

```python
from ml_intelligence.kpi_tracker import get_kpi_tracker

tracker = get_kpi_tracker()

# Component performs action
tracker.increment_kpi(
    component_name="rag",
    metric_name="requests_handled",
    value=1.0,
    metadata={"user_id": "user123"}
)

# Check trust score
trust = tracker.get_component_trust_score("rag")
print(f"RAG trust score: {trust:.2f}")
```

### Example 2: Monitor System Health

```python
# Get system health
health = tracker.get_system_health()

print(f"System Trust: {health['system_trust_score']:.2f}")
print(f"Status: {health['status']}")

for component_name, component_health in health['components'].items():
    print(f"  {component_name}: {component_health['trust_score']:.2f} ({component_health['status']})")
```

### Example 3: Layer 1 Integration

```python
from layer1.initialize import initialize_layer1

layer1 = initialize_layer1(
    session=db_session,
    kb_path="/path/to/kb",
    enable_kpi_tracking=True,  # Enable KPI tracking
)

# KPIs automatically tracked via message bus
# Query system trust
result = await layer1.message_bus.send_request(
    "kpi.get_system_trust"
)
print(f"System Trust: {result['system_trust_score']:.2f}")
```

---

## ⚙️ Configuration

### Metric Weights

Configure metric importance per component:

```python
tracker.register_component(
    component_name="rag",
    metric_weights={
        "requests_handled": 1.0,   # Base weight
        "successes": 2.0,          # High importance
        "failures": -1.0,          # Negative (reduces trust)
    }
)
```

### Component Weights

Configure component importance for system trust:

```python
system_trust = tracker.get_system_trust_score(
    component_weights={
        "rag": 2.0,              # High importance
        "ingestion": 1.0,        # Standard
        "memory_mesh": 1.5,      # Above average
    }
)
```

---

## ✅ Benefits

1. **Automatic Tracking**: KPIs increment automatically via Layer 1 events
2. **Real-Time Trust**: Trust scores update in real-time as components operate
3. **Operational Health**: Clear health signals for monitoring
4. **System-Wide View**: Aggregated trust for entire system
5. **Integration Ready**: Feeds into trust-aware embeddings and neuro-symbolic reasoning

---

## 📚 Related Systems

- **Trust-Aware Embeddings:** Uses KPI trust scores
- **Neuro-Symbolic Reasoning:** Incorporates system trust
- **Layer 1 Message Bus:** Provides event tracking
- **Component Connectors:** Auto-increment KPIs

---

**Status:** ✅ **FULLY IMPLEMENTED**

The KPI tracking system is complete and integrated, translating component performance into trust scores that feed into Grace's neuro-symbolic AI architecture.
