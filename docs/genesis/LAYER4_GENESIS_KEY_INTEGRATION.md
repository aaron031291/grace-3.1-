# Layer 4 Action Router - Genesis Key Integration Plan

## 🎯 What This Does

Integrates **Genesis Keys** with **Layer 4 Action Router** so every action executed by the diagnostic machine is tracked with complete provenance (what/where/when/who/how/why).

---

## 🏗️ Layer 4 Architecture

### 4-Layer Diagnostic Machine

```
Layer 1: Sensors (data collection)
    ↓
Layer 2: Interpreters (pattern analysis)
    ↓
Layer 3: Judgement (decision making)
    ↓
Layer 4: Action Router (response execution) ← WE ARE HERE
```

### Layer 4 Action Types

1. **ALERT_HUMAN** - Notify operators
2. **TRIGGER_HEALING** - Execute self-healing
3. **FREEZE_SYSTEM** - Halt operations
4. **RECOMMEND_LEARNING** - Capture insights
5. **TRIGGER_CICD** - Run CI/CD pipeline
6. **LOG_OBSERVATION** - Record state
7. **DO_NOTHING** - System healthy
8. **ESCALATE** - Escalate to higher authority

---

## ✅ Current Integration Status

### Already Integrated ✅

1. **Genesis Keys in Sensors (Layer 1)**
   - ✅ Collects Genesis Key data
   - ✅ Tracks error keys, fix suggestions
   - ✅ Monitors key distribution

2. **Genesis Keys in Interpreters (Layer 2)**
   - ✅ Detects Genesis Key anomalies
   - ✅ Identifies error patterns
   - ✅ Pattern detection uses Genesis Keys

3. **Genesis Keys in Cognitive Integration**
   - ✅ Stores diagnostic insights with Genesis Keys
   - ✅ Links patterns to Genesis Keys
   - ✅ Learning memory integration

### Missing Integration ❌

**Layer 4 Action Router does NOT create Genesis Keys for actions executed!**

---

## 🔴 What's Missing

### Current Flow (WITHOUT Genesis Keys)

```
Layer 3: Judgement → "Heal database"
    ↓
Layer 4: Execute healing action
    ↓
Action completed
    ↓
❌ NO GENESIS KEY CREATED
❌ NO TRACKING OF WHAT WAS DONE
❌ NO PROVENANCE
```

### Desired Flow (WITH Genesis Keys)

```
Layer 3: Judgement → "Heal database"
    ↓
Layer 4: Execute healing action
    ↓
✅ CREATE GENESIS KEY (GK-action-xxx)
    ↓
✅ Track: what/where/when/who/how/why
    ↓
✅ Link to diagnostic cycle
    ↓
✅ Feed to Memory Mesh
    ↓
✅ Trigger learning if needed
```

---

## 🚀 Required Integrations

### 1. **Genesis Key Creation for Every Action** ⭐ CRITICAL

**What:** Every action executed by Layer 4 creates a Genesis Key

**Integration Point:** `backend/diagnostic_machine/action_router.py`

**Actions to Track:**
- `_execute_freeze()` → Genesis Key: "SYSTEM_FREEZE"
- `_execute_alert()` → Genesis Key: "ALERT_HUMAN"
- `_execute_healing()` → Genesis Key: "HEALING_ACTION" (one per healing)
- `_execute_cicd()` → Genesis Key: "CICD_TRIGGER"
- `_execute_learning_capture()` → Genesis Key: "LEARNING_RECOMMENDATION"
- `_execute_log_observation()` → Genesis Key: "OBSERVATION_LOG"

**Example:**
```python
def _execute_healing(self, decision, sensor_data, judgement):
    # Before executing healing
    genesis_key = genesis_service.create_genesis_key(
        key_type=GenesisKeyType.HEALING_ACTION,
        what="Execute self-healing",
        where=decision.target_components,
        when=datetime.utcnow(),
        who="autonomous_healing_system",
        how=healing.function,
        why=decision.reason,
        metadata={
            "decision_id": decision.decision_id,
            "healing_id": healing.healing_id,
            "cycle_id": sensor_data.cycle_id
        }
    )
    
    # Execute healing
    result = execute_healing(...)
    
    # Update Genesis Key with outcome
    genesis_service.update_genesis_key(
        genesis_key.key_id,
        status="COMPLETED" if result.success else "FAILED",
        metadata={"result": result}
    )
```

---

### 2. **Self-Healing System Integration** ⭐ CRITICAL

**What:** Connect Layer 4 healing actions to Grace's Autonomous Healing System

**Current:** Layer 4 has basic healing functions
**Needed:** Integration with `backend/cognitive/autonomous_healing_system.py`

**Why:**
- Grace's healing system has trust-based execution
- Multi-LLM guidance for complex issues
- Learning from outcomes
- Trust score updates

**Integration:**
```python
from cognitive.autonomous_healing_system import AutonomousHealingSystem

def _execute_healing(self, decision, sensor_data, judgement):
    # Use Grace's healing system instead of basic functions
    healing_system = AutonomousHealingSystem(session)
    
    # Create Genesis Key
    genesis_key = create_action_genesis_key(...)
    
    # Execute via Grace's healing system
    healing_result = healing_system.execute_healing(
        decisions=[...],
        genesis_key_id=genesis_key.key_id
    )
    
    # Healing system automatically:
    # - Creates Genesis Keys for each healing action
    # - Updates trust scores
    # - Learns from outcomes
    # - Feeds to Memory Mesh
```

---

### 3. **Learning Memory Integration** ⭐ CRITICAL

**What:** Every action outcome feeds into Learning Memory

**Current:** Partial integration exists
**Needed:** Complete integration for all action types

**Integration:**
```python
def _execute_learning_capture(self, decision, interpreted_data):
    # Create Genesis Key
    genesis_key = create_action_genesis_key(...)
    
    # Store learning insight
    learning_memory.record_experience(
        experience_type="diagnostic_pattern",
        context=interpreted_data.patterns,
        action_taken=decision.action_type,
        outcome={"patterns_detected": len(patterns)},
        genesis_key_id=genesis_key.key_id
    )
    
    # This automatically:
    # - Calculates trust score
    # - Promotes to episodic memory (if trust >= 0.7)
    # - Creates procedure (if trust >= 0.8)
```

---

### 4. **Memory Mesh Integration** ⭐ CRITICAL

**What:** Action outcomes feed into Memory Mesh for pattern learning

**Current:** Partial integration
**Needed:** Complete integration

**Integration:**
```python
def _execute_action(self, decision, ...):
    genesis_key = create_action_genesis_key(...)
    
    # Execute action
    result = execute(...)
    
    # Feed to Memory Mesh
    memory_mesh.ingest_learning_experience(
        experience_type="action_outcome",
        context={"action": decision.action_type},
        action_taken={"action": decision.action_type},
        outcome={"success": result.success},
        genesis_key_id=genesis_key.key_id
    )
```

---

### 5. **Autonomous Trigger Integration** ⭐ CRITICAL

**What:** Layer 4 actions trigger autonomous learning/healing loops

**Current:** Not integrated
**Needed:** Connect to `backend/genesis/autonomous_triggers.py`

**Integration:**
```python
def _execute_action(self, decision, ...):
    genesis_key = create_action_genesis_key(...)
    
    # Execute action
    result = execute(...)
    
    # Trigger autonomous pipeline
    trigger_pipeline = get_genesis_trigger_pipeline()
    trigger_result = trigger_pipeline.on_genesis_key_created(genesis_key)
    
    # This automatically:
    # - Triggers learning if pattern detected
    # - Triggers healing if error detected
    # - Triggers mirror analysis if needed
```

---

### 6. **CI/CD Integration** ⭐ HIGH PRIORITY

**What:** CI/CD triggers create Genesis Keys and link to version control

**Current:** Basic CI/CD triggering
**Needed:** Genesis Key tracking + version control integration

**Integration:**
```python
def _execute_cicd(self, decision):
    # Create Genesis Key
    genesis_key = create_action_genesis_key(
        key_type=GenesisKeyType.CICD_TRIGGER,
        what="Trigger CI/CD pipeline",
        why=decision.reason,
        metadata={"pipeline": self.cicd_config.pipeline_command}
    )
    
    # Execute CI/CD
    result = run_cicd_pipeline(...)
    
    # Link to version control
    version_control.create_commit(
        message=f"CI/CD triggered: {decision.reason}",
        genesis_key_id=genesis_key.key_id
    )
```

---

### 7. **Mirror Self-Modeling Integration** ⭐ HIGH PRIORITY

**What:** Layer 4 actions feed into Mirror for self-reflection

**Current:** Not integrated
**Needed:** Connect to `backend/cognitive/mirror_self_modeling.py`

**Integration:**
```python
def _execute_action(self, decision, ...):
    genesis_key = create_action_genesis_key(...)
    result = execute(...)
    
    # Feed to Mirror (periodic analysis)
    # Mirror observes Genesis Keys and detects patterns
    # No direct call needed - Mirror reads Genesis Keys
```

---

### 8. **Learning Efficiency Tracking** ⭐ NEW!

**What:** Track data/time efficiency of diagnostic actions

**Current:** Not integrated
**Needed:** Connect to `backend/cognitive/learning_efficiency_tracker.py`

**Integration:**
```python
def _execute_action(self, decision, ...):
    # Track action execution time
    start_time = datetime.utcnow()
    
    genesis_key = create_action_genesis_key(...)
    result = execute(...)
    
    duration = datetime.utcnow() - start_time
    
    # Record efficiency
    efficiency_tracker.record_insight(
        insight_type="action",
        description=f"Executed {decision.action_type}",
        trust_score=result.confidence if hasattr(result, 'confidence') else 0.8,
        time_to_insight_seconds=duration.total_seconds(),
        genesis_key_id=genesis_key.key_id
    )
```

---

## 📋 Complete Integration Checklist

### Core Systems (Required)

- [ ] **Genesis Key Service** - Create keys for every action
- [ ] **Autonomous Healing System** - Use Grace's healing instead of basic functions
- [ ] **Learning Memory** - Store action outcomes as learning examples
- [ ] **Memory Mesh** - Feed outcomes to episodic/procedural memory
- [ ] **Autonomous Triggers** - Trigger learning/healing loops

### Enhanced Systems (High Priority)

- [ ] **CI/CD Integration** - Link CI/CD triggers to version control
- [ ] **Mirror Self-Modeling** - Enable self-reflection on actions
- [ ] **Learning Efficiency** - Track action efficiency metrics
- [ ] **Version Control** - Link actions to git commits
- [ ] **Librarian** - Categorize actions by type/domain

### Advanced Systems (Nice to Have)

- [ ] **Telemetry** - Link to telemetry system
- [ ] **KPI Tracking** - Track action KPIs
- [ ] **Governance** - Human-in-the-loop for critical actions
- [ ] **Sandbox Lab** - Test actions in sandbox first

---

## 🔄 Complete Flow with Genesis Keys

### Example: Healing Action

```
1. Layer 1: Sensor detects database connection issue
   → Creates Genesis Key: GK-sensor-xxx

2. Layer 2: Interpreter detects pattern
   → Links to GK-sensor-xxx

3. Layer 3: Judgement decides "heal database"
   → Links to GK-sensor-xxx

4. Layer 4: Execute healing
   → Creates Genesis Key: GK-healing-xxx
   → Links to GK-sensor-xxx (parent)
   → Executes via Autonomous Healing System
   → Creates Genesis Key: GK-healing-action-xxx
   → Updates trust scores
   → Feeds to Learning Memory
   → Promotes to Episodic Memory (if trust >= 0.7)
   → Creates Procedure (if trust >= 0.8)
   → Triggers autonomous learning loop
   → Feeds to Mirror for analysis
   → Tracks efficiency metrics

5. Result: Complete provenance chain
   GK-sensor-xxx → GK-healing-xxx → GK-healing-action-xxx
   → Learning Example → Episodic Memory → Procedure
```

---

## 🎯 Key Benefits

1. **Complete Audit Trail**: Every action tracked
2. **Learning Loop**: Actions feed into learning system
3. **Trust-Based Execution**: Uses Grace's trust system
4. **Self-Improvement**: Actions improve over time
5. **Provenance**: Full chain from sensor to action
6. **Efficiency Tracking**: Track action efficiency
7. **Pattern Learning**: Learn from action outcomes

---

## 📝 Implementation Priority

### Phase 1: Core Integration (Critical)
1. Genesis Key creation for every action
2. Autonomous Healing System integration
3. Learning Memory integration
4. Memory Mesh integration

### Phase 2: Enhanced Integration (High Priority)
5. Autonomous Trigger integration
6. CI/CD + Version Control integration
7. Mirror Self-Modeling integration
8. Learning Efficiency tracking

### Phase 3: Advanced Integration (Nice to Have)
9. Telemetry integration
10. KPI tracking
11. Governance integration
12. Sandbox Lab integration

---

## 🔗 Integration Points

### File: `backend/diagnostic_machine/action_router.py`

**Add to `__init__`:**
```python
from genesis.genesis_key_service import GenesisKeyService
from cognitive.autonomous_healing_system import AutonomousHealingSystem
from cognitive.learning_memory import LearningMemoryManager
from cognitive.memory_mesh_integration import MemoryMeshIntegration
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.learning_efficiency_tracker import LearningEfficiencyTracker
```

**Add to `ActionRouter.__init__`:**
```python
self.genesis_service = GenesisKeyService(session)
self.healing_system = AutonomousHealingSystem(session)
self.learning_memory = LearningMemoryManager(session, kb_path)
self.memory_mesh = MemoryMeshIntegration(session, kb_path)
self.trigger_pipeline = get_genesis_trigger_pipeline(session, kb_path)
self.efficiency_tracker = LearningEfficiencyTracker(session)
```

**Update each `_execute_*` method:**
```python
def _execute_healing(self, decision, sensor_data, judgement):
    # Create Genesis Key
    genesis_key = self.genesis_service.create_genesis_key(...)
    
    # Execute via Grace's healing system
    result = self.healing_system.execute_healing(...)
    
    # Feed to learning systems
    self.learning_memory.record_experience(...)
    self.memory_mesh.ingest_learning_experience(...)
    
    # Trigger autonomous loops
    self.trigger_pipeline.on_genesis_key_created(genesis_key)
    
    # Track efficiency
    self.efficiency_tracker.record_insight(...)
```

---

**This integration makes Layer 4 a fully tracked, learning-enabled action system with complete provenance!** 🚀
