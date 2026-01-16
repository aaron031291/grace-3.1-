# API Connection Status

## Real-Time Intelligence Features

With all APIs connected, the following real-time intelligence features are now active:

### ✅ Intelligence Tab - Real-Time Decisions

**Location:** Intelligence Tab → Real-Time Decisions (default view)

**Features:**
- **Live Decision Streaming**: Polls `/cognitive/decisions/recent` every 2 seconds
- **Decision Timeline**: Shows recent OODA loop decisions in chronological order
- **OODA Phase Indicators**: Visual indicators for Observe → Orient → Decide → Act phases
- **Strategy Display**: Shows which strategy Grace selected for each decision
- **Quality Scores**: Displays quality metrics for each decision
- **Streaming Indicator**: Green pulsing dot shows when live data is being received

### ✅ Cognitive Blueprint Integration

**Location:** Intelligence Tab → Cognitive Blueprint

**Features:**
- Full OODA loop breakdown for each decision
- Ambiguity tracking (Known, Unknown, Inferred information)
- Invariant validation (12 core invariants)
- Decision details with all phases visible

### ✅ ML Intelligence

**Location:** Intelligence Tab → ML Intelligence

**Connected APIs:**
- `/api/ml-intelligence/status` - ML system status
- `/api/kpi/trust/system` - System trust scores
- `/api/kpi/components` - Component health metrics
- `/api/ml-intelligence/bandit/stats` - Multi-armed bandit statistics
- `/api/ml-intelligence/uncertainty/stats` - Uncertainty estimation

### ✅ Insights

**Location:** Intelligence Tab → Insights

**Connected APIs:**
- `/cognitive/insights` - Learning insights and patterns
- `/cognitive/learning-metrics` - Learning progress metrics
- `/cognitive/learning-goals` - Active learning goals
- `/cognitive/knowledge-growth` - Knowledge growth over time

### ✅ Learning

**Location:** Intelligence Tab → Learning

**Connected APIs:**
- `/api/autonomous-learning/status` - Autonomous learning status
- `/api/proactive-learning/status` - Proactive learning status
- `/api/training/skills` - Skill development tracking
- `/api/training/analytics/progress` - Training progress
- `/api/learning-memory/stats` - Learning memory statistics

### ✅ Monitoring & Telemetry

**Location:** Monitoring Tab

**Connected APIs:**
- `/api/monitoring/organs` - System organs progress
- `/telemetry/system-state/current` - Current system state
- `/telemetry/operations` - Recent operations
- `/telemetry/baselines` - Performance baselines
- `/telemetry/drift-alerts` - Anomaly detection alerts
- `/telemetry/stats` - System statistics

## Real-Time Updates

All intelligence features update automatically:
- **Decisions**: Every 2 seconds
- **Telemetry**: Every 30 seconds
- **ML Intelligence**: On tab switch
- **Insights**: On tab switch
- **Learning**: On tab switch

## Visual Indicators

- **Green Pulsing Dot**: Live data streaming active
- **Decision Count Badge**: Number of recent decisions
- **Phase Indicators**: Color-coded OODA phases (green = complete, gray = pending)
- **Quality Scores**: Percentage display for decision quality
- **Status Badges**: Color-coded status (completed, pending, failed)

## Testing Real-Time Intelligence

1. **Make a Query**: Send a message in Chat tab
2. **Watch Decisions**: Navigate to Intelligence → Real-Time Decisions
3. **See OODA Loop**: Watch as Grace processes through Observe → Orient → Decide → Act
4. **View Details**: Click on any decision to see full cognitive breakdown
5. **Check Quality**: See quality scores and strategy selections

## API Endpoints Summary

### Cognitive Engine
- `GET /cognitive/decisions/recent` - Recent decisions
- `GET /cognitive/decisions/{id}` - Decision details
- `GET /cognitive/insights` - Learning insights
- `GET /cognitive/learning-metrics` - Learning metrics
- `GET /cognitive/learning-goals` - Learning goals
- `GET /cognitive/knowledge-growth` - Knowledge growth

### ML Intelligence
- `GET /api/ml-intelligence/status` - ML status
- `GET /api/kpi/trust/system` - Trust scores
- `GET /api/kpi/components` - Component health
- `GET /api/ml-intelligence/bandit/stats` - Bandit stats
- `GET /api/ml-intelligence/uncertainty/stats` - Uncertainty stats

### Learning
- `GET /api/autonomous-learning/status` - Autonomous learning
- `GET /api/proactive-learning/status` - Proactive learning
- `GET /api/training/skills` - Skills
- `GET /api/training/analytics/progress` - Progress
- `GET /api/learning-memory/stats` - Memory stats

### Telemetry
- `GET /telemetry/system-state/current` - System state
- `GET /telemetry/operations` - Operations
- `GET /telemetry/baselines` - Baselines
- `GET /telemetry/drift-alerts` - Alerts
- `GET /telemetry/stats` - Statistics

All endpoints are proxied through Vite dev server at `http://localhost:5173` to `http://localhost:8000`.
