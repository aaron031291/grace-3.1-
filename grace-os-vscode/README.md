# Grace OS - Cognitive IDE Extension

**Grace Operating System integrated into VSCode** - brings the entire Grace cognitive infrastructure through the IDE.

## Overview

Grace OS transforms VSCode into a cognitive development environment by integrating all Grace subsystems directly into the editor:

- **Cognitive Layer** - Code analysis, explanations, and intelligent suggestions
- **Memory Mesh** - Context-aware memory with semantic, episodic, and procedural storage
- **Genesis Keys** - Full code provenance and lineage tracking
- **Ghost Ledger** - Line-by-line change tracking with visual annotations
- **Diagnostic System** - 4-layer health monitoring (Sensors → Interpreters → Judgement → Actions)
- **Autonomous Scheduler** - Background task orchestration
- **Learning System** - Continuous learning from coding patterns

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VSCode Extension                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Grace     │  │   Ghost     │  │  Cognitive  │  │ Autonomous │ │
│  │  OS Core    │  │   Ledger    │  │   Provider  │  │  Scheduler │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Memory     │  │   Genesis   │  │ Diagnostic  │  │  Learning  │ │
│  │   Mesh      │  │    Keys     │  │  Provider   │  │  Provider  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      Bridges Layer                            │  │
│  │   ┌─────────────────┐         ┌───────────────────────────┐  │  │
│  │   │    IDE Bridge   │         │   WebSocket Bridge        │  │  │
│  │   │   (HTTP/REST)   │         │   (Real-time Streaming)   │  │  │
│  │   └─────────────────┘         └───────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP/WebSocket
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Grace Backend                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Cognitive  │  │   Magma     │  │   Genesis   │  │ Diagnostic │ │
│  │   Engine    │  │   Memory    │  │   Service   │  │   Machine  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │    LLM      │  │   Learning  │  │   Agent     │  │   CI/CD    │ │
│  │ Orchestrator│  │   Memory    │  │  Framework  │  │   Engine   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### Ghost Ledger
Line-by-line code tracking with visual annotations:
- Track every code change with timestamps
- Associate changes with genesis keys for provenance
- Visual decorations showing change history
- Hover tooltips with line metadata

### Cognitive IDE
AI-powered code intelligence:
- **Analyze Selection** - Deep code analysis with patterns and suggestions
- **Explain Code** - Natural language explanations
- **Suggest Refactoring** - AI-powered improvement suggestions
- Inline code intelligence with real-time suggestions

### Memory Mesh
Context-aware memory system:
- Store and query memories (episodic, semantic, procedural, learning)
- Magma memory ingestion for deep integration
- Automatic memory consolidation
- Context-aware completions

### Genesis Keys
Full code provenance:
- Create genesis keys for code changes
- View complete code lineage
- Track code evolution over time
- Visual gutter annotations for tracked lines

### Diagnostics
4-layer health monitoring:
1. **Sensors** - Raw data collection
2. **Interpreters** - Pattern recognition
3. **Judgement** - Decision making
4. **Actions** - Healing and remediation

### Autonomous Scheduler
Background task orchestration:
- Schedule diagnostic checks
- Memory consolidation
- Learning pattern analysis
- CI/CD triggers

## Keyboard Shortcuts

| Command | Shortcut | Description |
|---------|----------|-------------|
| Open Chat | `Ctrl+Shift+G` | Open Grace chat panel |
| Analyze | `Ctrl+Shift+A` | Analyze selected code |
| Explain | `Ctrl+Shift+E` | Explain selected code |
| Query Memory | `Ctrl+Shift+M` | Search memory mesh |
| View Lineage | `Ctrl+Shift+L` | View code lineage |
| Toggle Ghost Ledger | `Ctrl+Shift+H` | Toggle line tracking |
| Run Diagnostics | `Ctrl+Shift+D` | Run diagnostic check |

## Configuration

Settings available in VSCode preferences:

```json
{
  "graceOS.backendUrl": "http://localhost:8000",
  "graceOS.wsUrl": "ws://localhost:8000/ws",
  "graceOS.autoActivate": true,
  "graceOS.ghostLedger.enabled": true,
  "graceOS.ghostLedger.showInlineAnnotations": true,
  "graceOS.memory.autoStore": true,
  "graceOS.cognitive.inlineSuggestions": true,
  "graceOS.genesis.autoTrack": true,
  "graceOS.diagnostics.autoRun": true,
  "graceOS.autonomous.enabled": true
}
```

## Installation

1. **Build the extension:**
   ```bash
   cd grace-os-vscode
   npm install
   npm run compile
   ```

2. **Install in VSCode:**
   ```bash
   code --install-extension grace-os-3.1.0.vsix
   ```

3. **Ensure Grace backend is running:**
   ```bash
   cd ../backend
   python app.py
   ```

## Development

### Prerequisites
- Node.js 18+
- TypeScript 5.3+
- VSCode 1.85+

### Building
```bash
npm install
npm run compile
```

### Watching
```bash
npm run watch
```

### Bundling
```bash
npm run bundle
```

## API Integration

The extension communicates with Grace backend through:

- **REST API** (`/api/ide/*`) - Cognitive, memory, genesis, diagnostic operations
- **WebSocket** (`/ws`) - Real-time streaming and updates

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ide/cognitive/analyze` | POST | Analyze code |
| `/api/ide/cognitive/explain` | POST | Explain code |
| `/api/ide/memory/store` | POST | Store memory |
| `/api/ide/memory/query` | POST | Query memories |
| `/api/ide/genesis/create` | POST | Create genesis key |
| `/api/ide/genesis/lineage` | GET | Get code lineage |
| `/api/ide/diagnostics/run` | POST | Run diagnostics |
| `/api/ide/learning/record` | POST | Record insight |
| `/api/ide/chat` | POST | Chat with Grace |
| `/ws` | WebSocket | Real-time updates |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Part of the Grace AI System. All rights reserved.
