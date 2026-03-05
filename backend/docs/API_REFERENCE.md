# Grace AI — API Reference

## Brain API

All actions available via two interfaces:

### v1: POST /brain/{domain}
```json
{ "action": "action_name", "payload": { ... } }
```

### v2: POST /api/v2/{domain}/{action}
```json
{ ... payload directly ... }
```

### Directory
```
GET /brain/directory    → list all domains and actions
GET /api/v2/directory   → same
```

---

## Chat Domain (`/brain/chat` or `/api/v2/chat/{action}`)

| Action | Payload | Description |
|--------|---------|-------------|
| `list` | `{limit: 50}` | List all chats |
| `create` | `{title, model, temperature}` | Create new chat |
| `get` | `{chat_id}` | Get chat by ID |
| `delete` | `{chat_id}` | Delete chat |
| `history` | `{chat_id}` | Get message history |
| `send` | `{chat_id, message}` | Send prompt, get LLM response |
| `consensus` | `{message, models?}` | Run multi-model consensus |
| `world_model` | `{}` | Get system world model state |

## Files Domain (`/brain/files`)

| Action | Payload | Description |
|--------|---------|-------------|
| `tree` | `{path?, max_depth?}` | Directory tree |
| `browse` | `{path}` | List directory contents |
| `read` | `{path}` | Read file content |
| `write` | `{path, content}` | Write file |
| `create` | `{path, content?, directory?}` | Create new file |
| `delete` | `{path}` | Delete file |
| `search` | `{query, limit?}` | Search file contents |
| `docs_all` | `{}` | List all documents |
| `stats` | `{}` | Knowledge base stats |

## Governance Domain (`/brain/govern`)

| Action | Payload | Description |
|--------|---------|-------------|
| `dashboard` | `{}` | Governance dashboard |
| `approvals` | `{}` | Pending approvals |
| `approve` | `{id, action, reason?}` | Act on approval |
| `scores` | `{}` | Trust/KPI scores |
| `rules` | `{}` | List governance rules |
| `persona` | `{}` | Get persona config |
| `update_persona` | `{personal?, professional?}` | Update persona |
| `genesis_stats` | `{}` | Genesis key statistics |
| `genesis_keys` | `{limit?}` | Recent Genesis keys |
| `heal` | `{}` | Trigger healing |
| `learn` | `{}` | Trigger learning |
| `approvals_history` | `{limit?}` | Approval history |

## AI Domain (`/brain/ai`)

| Action | Payload | Description |
|--------|---------|-------------|
| `models` | `{}` | Available consensus models |
| `consensus` | `{prompt, models?}` | Full 4-layer consensus |
| `quick` | `{prompt}` | Quick consensus (local models) |
| `fast` | `{prompt, models?}` | Fast mode (no synthesis) |
| `console` | `{message}` | Console chat (Kimi+Opus) |
| `diagnose` | `{}` | System diagnosis |
| `knowledge_gaps` | `{}` | Knowledge gap scan |
| `integration_matrix` | `{}` | System integration matrix |
| `logic_tests` | `{}` | Run logic tests |
| `generate` | `{prompt, project_folder?}` | Generate code |
| `oracle` | `{}` | Oracle dashboard |
| `training` | `{}` | Training data |

## System Domain (`/brain/system`)

| Action | Payload | Description |
|--------|---------|-------------|
| `runtime` | `{}` | Runtime status |
| `hot_reload` | `{}` | Hot-reload configs |
| `pause` | `{}` | Pause runtime |
| `resume` | `{}` | Resume runtime |
| `health` | `{}` | System health (CPU/RAM/disk) |
| `bi` | `{}` | Business intelligence |
| `diagnostics` | `{}` | Diagnostic engine status |
| `health_map` | `{window_minutes?}` | Component health map |
| `problems` | `{}` | Current problems |
| `baselines` | `{}` | ML-learned baselines |
| `orphans` | `{}` | Orphan service detection |
| `correlate` | `{component}` | Root cause analysis |
| `triggers` | `{}` | Trigger scan |
| `scan_heal` | `{}` | Scan + auto-heal |
| `probe` | `{}` | Probe all endpoints |
| `probe_models` | `{}` | Probe all LLM models |
| `auto_status` | `{}` | Autonomous loop status |
| `auto_start` | `{interval?}` | Start autonomous loop |
| `auto_stop` | `{}` | Stop autonomous loop |
| `auto_cycle` | `{}` | Run single cycle |
| `auto_log` | `{}` | Autonomous loop log |
| `consensus_fix` | `{}` | Consensus fix-all |
| `connectivity` | `{}` | Service connectivity check |

## Monitoring Endpoints

```
GET  /api/monitor/health-map         Component health map
GET  /api/monitor/problems           Current problems
GET  /api/monitor/timeline/{id}      Component timeline
GET  /api/monitor/correlate/{id}     Root cause analysis
GET  /api/monitor/orphans            Orphan services
GET  /api/monitor/baselines          ML-learned baselines
POST /api/monitor/probe/sweep        Probe all endpoints
POST /api/monitor/probe/models       Probe all LLM models
GET  /api/monitor/triggers/scan      Trigger scan
```

## Runtime Endpoints

```
GET  /api/runtime/status             Runtime state
POST /api/runtime/pause              Pause (no restart needed)
POST /api/runtime/resume             Resume
POST /api/runtime/hot-reload         Re-read .env, refresh models
GET  /api/runtime/connectivity       Service connectivity
GET  /api/runtime/resilience         Circuit breaker status
```
