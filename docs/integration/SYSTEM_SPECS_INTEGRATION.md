# System Specifications Integration

## Overview

GRACE now includes your computer specifications in all LLM interactions to ensure all architecture decisions and code generation respect hardware constraints. External coding agents (Claude Code, Cursor, etc.) are also politely reminded about these specs.

## Features

### 1. **System Specs in All LLM Prompts**
- Every LLM interaction includes system specifications
- LLMs automatically respect hardware constraints
- Prevents over-engineering and out-of-scope designs

### 2. **Repository Access Integration**
- System specs available via `repo_access.get_system_specs()`
- Formatted prompt string via `repo_access.get_system_specs_prompt()`
- Always accessible to LLMs working with code

### 3. **External Agent Reminders**
- Polite reminder files created automatically
- `GRACE_SYSTEM_SPECS.txt` in project root
- `backend/config/agent_reminder.json` for programmatic access
- Reminders shown when external agents work on architecture/model selection

### 4. **API Endpoints**
- `GET /system-specs/` - Get specs as JSON
- `GET /system-specs/prompt` - Get formatted prompt string
- `GET /system-specs/reminder` - Get reminder message
- `POST /system-specs/create-reminder-files` - Manually create reminder files

## Your System Specifications

**CPU:**
- Model: AMD Ryzen 9 9950X3D
- Cores: 16
- Threads: 32

**GPU:**
- Model: NVIDIA RTX 5090
- VRAM: 32 GB
- Compute Capability: Ada Lovelace

**RAM:**
- Total: 64 GB
- Type: DDR5

**Storage:**
- Total: 4096 GB (4TB)
- Type: NVMe SSD

**Constraints:**
- Max model size: 24 GB (leaves room for operations)
- Recommended batch size: 4
- Max concurrent models: 2
- Storage reserved for GRACE: 500 GB
- Available storage: 3500 GB

## How It Works

### 1. **LLM Integration**

System specs are automatically included in:
- GRACE system prompts (all LLM interactions)
- Code generation prompts
- Architecture design prompts
- Model selection prompts

**Example:**
```python
# System specs automatically added to all LLM prompts
prompt = get_grace_system_prompt(task_type="code")
# Includes full system specifications and architecture guidelines
```

### 2. **Repository Access**

LLMs can access specs programmatically:
```python
# Get specs as dictionary
specs = repo_access.get_system_specs()

# Get formatted prompt string
specs_prompt = repo_access.get_system_specs_prompt()
```

### 3. **External Agent Detection**

The system detects when external agents are working:
- Large code changes (>5 files)
- Architecture changes
- Model recommendations
- Resource-intensive operations

When detected, reminder files are created/updated.

### 4. **Reminder Files**

**`GRACE_SYSTEM_SPECS.txt`** (Project Root):
- Human-readable reminder message
- Full system specifications
- Architecture guidelines
- Easy for external agents to read

**`backend/config/agent_reminder.json`**:
- Machine-readable format
- Includes timestamp
- Full specs as JSON

## Architecture Guidelines

When designing architecture or generating code:

**DO:**
- Optimize models to fit within constraints
- Use efficient data structures and algorithms
- Consider batch sizes that respect memory limits
- Design scalable solutions that work within limits

**DON'T:**
- Design architectures requiring more VRAM than available
- Suggest models larger than GPU can handle
- Create memory-intensive operations without optimization
- Over-engineer solutions beyond hardware capabilities

## Configuration

### Updating System Specs

Edit `backend/config/system_specs.json`:

```json
{
  "cpu": {
    "model": "AMD Ryzen 9 9950X3D",
    "cores": 16,
    "threads": 32
  },
  "gpu": {
    "model": "NVIDIA RTX 5090",
    "vram_gb": 32,
    "compute_capability": "Ada Lovelace"
  },
  "ram": {
    "total_gb": 64,
    "type": "DDR5"
  },
  "storage": {
    "total_gb": 4096,
    "type": "NVMe SSD"
  },
  "os": {
    "name": "Windows",
    "version": "10.0.26200"
  },
  "python": {
    "version": "3.11+"
  },
  "constraints": {
    "max_model_size_gb": 24,
    "recommended_batch_size": 4,
    "max_concurrent_models": 2,
    "storage_reserved_for_grace_gb": 500,
    "available_storage_gb": 3500
  }
}
```

### Manual Reminder Creation

```python
from agent_reminder import create_reminder_files

# Create reminder files
create_reminder_files()
```

Or via API:
```bash
curl -X POST http://localhost:8000/system-specs/create-reminder-files
```

## Files

- `backend/system_specs.py` - System specs data structure and loading
- `backend/config/system_specs.json` - Specs configuration file
- `backend/agent_reminder.py` - Reminder system for external agents
- `backend/api/system_specs_api.py` - API endpoints
- `GRACE_SYSTEM_SPECS.txt` - Human-readable reminder (auto-generated)
- `backend/config/agent_reminder.json` - Machine-readable reminder (auto-generated)

## Integration Points

1. **LLM Orchestrator** - System specs included in all prompts
2. **GRACE System Prompts** - Specs automatically added
3. **Repository Access** - Specs available via API
4. **App Startup** - Reminder files created automatically
5. **External Agent Detection** - Reminders triggered on architecture changes

## Benefits

1. **Prevents Over-Engineering** - LLMs won't design beyond hardware
2. **Optimized Recommendations** - Model suggestions respect constraints
3. **External Agent Awareness** - Third-party agents see specs automatically
4. **Consistent Constraints** - All code/architecture respects same limits
5. **Better Resource Management** - Efficient use of available hardware

## Example Usage

### For LLMs (Automatic)

System specs are automatically included in all LLM prompts. No action needed.

### For External Agents

When external agents (Claude Code, Cursor) work on GRACE:
1. They can read `GRACE_SYSTEM_SPECS.txt` in project root
2. Reminder is automatically created/updated
3. Specs are available via API if needed

### For Developers

```python
from system_specs import get_system_specs

# Get specs
specs = get_system_specs()

# Access properties
print(f"GPU VRAM: {specs.gpu_vram_gb} GB")
print(f"Max model size: {specs.constraints['max_model_size_gb']} GB")

# Get formatted prompt
prompt = specs.to_prompt_string()
```

## Notes

- Specs are loaded once at startup and cached
- Reminder files are created/updated automatically
- External agent detection is heuristic-based (may have false positives)
- All LLM interactions include specs (no opt-out needed)
- Specs are read-only (modify via config file)
