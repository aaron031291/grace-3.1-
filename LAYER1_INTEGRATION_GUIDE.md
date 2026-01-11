# Layer 1 Integration Guide - Add to Your App

## Quick Start (5 Minutes)

### 1. Initialize Layer 1 in Your App

```python
# backend/app.py

from flask import Flask
from backend.layer1.initialize import initialize_layer1
from backend.database.session import get_db

app = Flask(__name__)

# Initialize Layer 1 on startup
@app.before_first_request
def setup_layer1():
    """Initialize complete Layer 1 autonomous system."""
    session = next(get_db())
    kb_path = "backend/knowledge_base"

    global layer1
    layer1 = initialize_layer1(session, kb_path)

    print("✓ Layer 1 autonomous system initialized")
    print(f"✓ Components: {len(layer1.get_stats()['components'])}")
    print(f"✓ Autonomous actions: {layer1.get_autonomous_actions()}")
```

### 2. Use in Your Endpoints

```python
# All existing endpoints automatically enhanced!

@app.route("/learning-memory/record-experience", methods=["POST"])
async def record_learning():
    """Record learning - now triggers full autonomous pipeline."""
    data = request.json

    # This ONE call triggers EVERYTHING automatically:
    # - Genesis Key creation
    # - Episodic memory (if trust >= 0.7)
    # - Procedural memory (if trust >= 0.8)
    # - LLM skill registration
    # - RAG indexing
    learning_id = await layer1.memory_mesh.trigger_learning_ingestion(
        experience_type=data["experience_type"],
        context=data["context"],
        action_taken=data["action_taken"],
        outcome=data["outcome"],
        user_id=data.get("user_id")
    )

    return jsonify({
        "learning_id": learning_id,
        "autonomous_pipeline": "triggered"
    })


@app.route("/retrieve", methods=["POST"])
async def retrieve():
    """RAG retrieval - now enhanced with procedural memory."""
    data = request.json

    # This automatically:
    # - Requests procedures from Memory Mesh
    # - Enhances retrieval context
    # - Sends feedback to learning system
    response = await layer1.message_bus.request(
        to_component=ComponentType.RAG,
        topic="retrieve_with_context",
        payload={"query": data["query"]},
        from_component=ComponentType.LLM_ORCHESTRATION
    )

    return jsonify(response)


@app.route("/ingest/file", methods=["POST"])
async def ingest_file():
    """File ingestion - now with automatic Genesis Key."""
    file_path = request.json["file_path"]

    # This automatically:
    # - Creates Genesis Key
    # - Processes file
    # - Notifies RAG when ready
    # - Links version control
    response = await layer1.message_bus.request(
        to_component=ComponentType.INGESTION,
        topic="ingest_file",
        payload={
            "file_path": file_path,
            "file_type": "pdf",
            "user_id": request.json.get("user_id")
        },
        from_component=ComponentType.LLM_ORCHESTRATION
    )

    return jsonify(response)
```

---

## What You Get Automatically

### Every Learning Experience

```python
# Just call this:
learning_id = await layer1.memory_mesh.trigger_learning_ingestion(...)

# Get all this automatically:
✓ Trust score calculated
✓ Genesis Key created/linked
✓ Saved to layer_1/learning_memory/
✓ Episodic memory created (if trust >= 0.7)
✓ Procedural memory created (if trust >= 0.8)
✓ Skill registered with LLMs
✓ Indexed for RAG retrieval
✓ User contribution tracked
✓ All components notified
```

### Every File Upload

```python
# Just call this:
response = await layer1.message_bus.request(
    to_component=ComponentType.INGESTION,
    topic="ingest_file",
    ...
)

# Get all this automatically:
✓ Genesis Key created
✓ File processed and chunked
✓ Saved to knowledge base
✓ RAG notified - ready for retrieval
✓ Version control linked
✓ All components coordinated
```

### Every RAG Query

```python
# Just call this:
response = await layer1.message_bus.request(
    to_component=ComponentType.RAG,
    topic="retrieve_with_context",
    ...
)

# Get all this automatically:
✓ Procedures requested from Memory Mesh
✓ Retrieval context enhanced
✓ Results returned
✓ Success/failure feedback sent
✓ Learning system updated
✓ Continuous improvement triggered
```

---

## API Endpoints to Add

### Message Bus Stats

```python
@app.route("/layer1/stats", methods=["GET"])
def get_layer1_stats():
    """Get Layer 1 system statistics."""
    stats = layer1.get_stats()

    return jsonify({
        "message_bus": {
            "total_messages": stats["total_messages"],
            "requests": stats["requests"],
            "events": stats["events"],
            "autonomous_actions_triggered": stats["autonomous_actions_triggered"]
        },
        "components": stats["components"],
        "autonomous_actions": len(layer1.get_autonomous_actions())
    })
```

### Autonomous Actions List

```python
@app.route("/layer1/autonomous-actions", methods=["GET"])
def get_autonomous_actions():
    """List all registered autonomous actions."""
    actions = layer1.get_autonomous_actions()

    return jsonify({
        "total": len(actions),
        "actions": [
            {
                "component": action["component"],
                "description": action["description"],
                "trigger": action["trigger_event"],
                "enabled": action["enabled"]
            }
            for action in actions
        ]
    })
```

### Message History

```python
@app.route("/layer1/messages", methods=["GET"])
def get_message_history():
    """Get recent message bus activity."""
    component = request.args.get("component")
    limit = int(request.args.get("limit", 100))

    from backend.layer1.message_bus import ComponentType

    history = layer1.message_bus.get_message_history(
        component=ComponentType[component.upper()] if component else None,
        limit=limit
    )

    return jsonify({
        "total": len(history),
        "messages": [
            {
                "id": msg.message_id,
                "type": msg.message_type.value,
                "from": msg.from_component.value,
                "to": msg.to_component.value if msg.to_component else "broadcast",
                "topic": msg.topic,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in history
        ]
    })
```

---

## Frontend Integration

### Show Autonomous Activity

```jsx
// frontend/src/components/Layer1Monitor.jsx

import React, { useState, useEffect } from 'react';

function Layer1Monitor() {
  const [stats, setStats] = useState(null);
  const [actions, setActions] = useState([]);

  useEffect(() => {
    // Get stats every 5 seconds
    const interval = setInterval(async () => {
      const response = await fetch('/layer1/stats');
      const data = await response.json();
      setStats(data);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Get autonomous actions
    fetch('/layer1/autonomous-actions')
      .then(r => r.json())
      .then(data => setActions(data.actions));
  }, []);

  return (
    <div className="layer1-monitor">
      <h2>Layer 1 Autonomous System</h2>

      {stats && (
        <div className="stats">
          <div className="stat">
            <label>Total Messages</label>
            <value>{stats.message_bus.total_messages}</value>
          </div>
          <div className="stat">
            <label>Autonomous Actions Triggered</label>
            <value>{stats.message_bus.autonomous_actions_triggered}</value>
          </div>
          <div className="stat">
            <label>Active Components</label>
            <value>{stats.components.length}</value>
          </div>
        </div>
      )}

      <h3>Autonomous Actions ({actions.length})</h3>
      <ul className="actions">
        {actions.map(action => (
          <li key={action.component + action.trigger}>
            <strong>{action.component}</strong>: {action.description}
            <br />
            <small>Trigger: {action.trigger}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Layer1Monitor;
```

---

## Testing

```bash
# Run comprehensive test
python test_layer1_autonomous_system.py

# Expected output:
# ✓ Learning ingested → Full pipeline triggered
# ✓ File uploaded → Genesis Key + processing
# ✓ RAG query → Enhanced with procedures
# ✓ All autonomous actions working
# ✓ 16 autonomous actions registered
# ✓ 5 components connected
```

---

## Migration from Old Code

### Before (Manual Coordination)

```python
# OLD WAY - lots of manual steps
learning_id = create_learning_example(...)
genesis_key = create_genesis_key(...)
link_genesis_key(learning_id, genesis_key)
if trust_score >= 0.7:
    create_episodic_memory(learning_id)
if trust_score >= 0.8:
    create_procedural_memory(learning_id)
    register_skill_with_llm(skill_name)
    index_for_rag(procedure_id)
```

### After (Autonomous)

```python
# NEW WAY - one call, everything automatic
learning_id = await layer1.memory_mesh.trigger_learning_ingestion(...)

# That's it! Everything else happens automatically:
# ✓ Genesis Key
# ✓ Episodic memory
# ✓ Procedural memory
# ✓ LLM skill registration
# ✓ RAG indexing
# ✓ All notifications
```

---

## Configuration

### Enable/Disable Autonomous Actions

```python
# Disable specific action
layer1.message_bus.disable_autonomous_action(action_id)

# Enable it back
layer1.message_bus.enable_autonomous_action(action_id)

# Get action status
actions = layer1.get_autonomous_actions()
for action in actions:
    print(f"{action['description']}: {action['enabled']}")
```

### Adjust Message History Size

```python
# In backend/layer1/message_bus.py
layer1.message_bus._max_history = 5000  # Keep last 5000 messages
```

---

## Monitoring

### Check System Health

```python
@app.route("/layer1/health", methods=["GET"])
def layer1_health():
    """Check Layer 1 system health."""
    stats = layer1.get_stats()

    health = {
        "status": "healthy",
        "components_registered": stats["registered_components"],
        "autonomous_actions_working": stats["autonomous_actions_triggered"] > 0,
        "message_flow": stats["total_messages"] > 0,
        "components": stats["components"]
    }

    return jsonify(health)
```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.getLogger('backend.layer1').setLevel(logging.DEBUG)

# See every message, every trigger, every autonomous action
```

---

## Summary

### What You Need to Do

1. ✅ Add `initialize_layer1()` to app startup (1 line)
2. ✅ Replace manual coordination with message bus calls (simplified code)
3. ✅ Add monitoring endpoints (optional, 3 endpoints)
4. ✅ Test the system (`python test_layer1_autonomous_system.py`)

### What You Get

✅ All components communicate automatically
✅ Autonomous action triggering (16 actions)
✅ Complete provenance with Genesis Keys
✅ Learning → Episodic → Procedural → Skills pipeline
✅ RAG enhancement with procedures
✅ Feedback loops for continuous improvement
✅ Zero manual coordination needed

### Time to Integrate

- **Code changes**: 10 minutes
- **Testing**: 5 minutes
- **Total**: 15 minutes

**Then you have a fully autonomous, self-coordinating, self-improving system.** ✓
