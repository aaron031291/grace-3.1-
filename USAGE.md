# GRACE 3.1 — Client Usage Guide

> **Version:** 3.1.1 (Enterprise Handoff Release, March 2026)
> **Platform:** GRACE — Genesis-driven RAG Autonomous Cognitive Engine

Welcome to GRACE. This guide covers everything you need to launch, use, and maintain the system day-to-day. For technical deployment details, refer to the developer `README.md`.

---

## Table of Contents

1. [Launching GRACE](#1-launching-grace)
2. [Accessing the Interface](#2-accessing-the-interface)
3. [Navigation Overview](#3-navigation-overview)
4. [Core Features](#4-core-features)
   - [Chat & Assistant](#41-chat--assistant)
   - [Document Ingestion & Knowledge Base](#42-document-ingestion--knowledge-base)
   - [AI Librarian](#43-ai-librarian)
   - [File Browser](#44-file-browser)
   - [Folders & Directory Chat](#45-folders--directory-chat)
5. [Cognitive & Learning Features](#5-cognitive--learning-features)
   - [Cognitive Tab](#51-cognitive-tab)
   - [Learning & Healing Tab](#52-learning--healing-tab)
   - [Oracle Tab](#53-oracle-tab)
   - [GRACE Lab (Sandbox Experiments)](#54-grace-lab-sandbox-experiments)
   - [Flash Cache Panel](#55-flash-cache-panel)
6. [Governance & Safety](#6-governance--safety)
   - [Governance Tab (Three-Pillar Control)](#61-governance-tab-three-pillar-control)
   - [Whitelist Tab (Human-to-AI Learning)](#62-whitelist-tab-human-to-ai-learning)
7. [Autonomous Agents & Tools](#7-autonomous-agents--tools)
   - [Consensus Chat (Multi-Agent Debate)](#71-consensus-chat-multi-agent-debate)
   - [Model Context Protocol (MCP) Agentic Tools](#72-model-context-protocol-mcp-agentic-tools)
   - [GRACE Planning Tab](#73-grace-planning-tab)
   - [GRACE Todos Tab](#74-grace-todos-tab)
   - [Tasks Tab](#75-tasks-tab)
8. [ML Intelligence & Analytics](#8-ml-intelligence--analytics)
   - [ML Intelligence Tab](#81-ml-intelligence-tab)
   - [KPI Dashboard](#82-kpi-dashboard)
   - [Business Intelligence Tab](#83-business-intelligence-tab)
   - [RAG Pipeline Tab](#84-rag-pipeline-tab)
   - [Insights Tab](#85-insights-tab)
9. [Genesis Provenance & Version Control](#9-genesis-provenance--version-control)
   - [Genesis Key Panel & Timeline](#91-genesis-key-panel--timeline)
   - [Version Control Tab](#92-version-control-tab)
   - [Repository Manager](#93-repository-manager)
10. [System Monitoring & Diagnostics](#10-system-monitoring--diagnostics)
    - [Monitoring Tab](#101-monitoring-tab)
    - [System Health Tab (Immune System)](#102-system-health-tab-immune-system)
    - [Telemetry Tab](#103-telemetry-tab)
    - [Activity Feed](#104-activity-feed)
    - [Terminal Log Viewer](#105-terminal-log-viewer)
11. [Developer & Power-User Tools](#11-developer--power-user-tools)
    - [Codebase Tab](#111-codebase-tab)
    - [CI/CD Dashboard](#112-cicd-dashboard)
    - [Orchestration Tab](#113-orchestration-tab)
    - [Web Scraper](#114-web-scraper)
    - [Voice Interface](#115-voice-interface)
    - [API Testing Tab](#116-api-testing-tab)
    - [Dev Tab](#117-dev-tab)
    - [Notion / Kanban Tab](#118-notion--kanban-tab)
12. [Documentation Library (Docs Tab)](#12-documentation-library-docs-tab)
13. [Maintenance & Troubleshooting](#13-maintenance--troubleshooting)
    - [Checking System Logs](#131-checking-system-logs)
    - [GPU / Embedding Issues](#132-gpu--embedding-issues)
    - [Common Issues & Fixes](#133-common-issues--fixes)
    - [Shutting Down Gracefully](#134-shutting-down-gracefully)
14. [Environment & Configuration](#14-environment--configuration)

---

## 1. Launching GRACE

GRACE consists of four services: the Python backend, the React frontend, a Qdrant vector database, and a local LLM (Ollama). All of these are started with **one command**.

### Windows (Recommended)

Open **PowerShell** or **Command Prompt**, navigate to the project folder, and run:

```powershell
cd path\to\grace-3.1-
.\start.bat
```

This script:
- Starts **Qdrant** (vector database) via Docker, if available
- Activates the Python virtual environment and starts the **FastAPI backend** on port `8000`
- Starts the **React frontend** dev server on port `5173`

> **Tip:** You can also double-click `Launch Grace.bat` in Windows Explorer for a one-click launch.

### Partial Startup (Advanced)

```powershell
.\start.bat backend    # Backend only
.\start.bat frontend   # Frontend only
```

### Linux / macOS

```bash
./start.sh             # Full stack
./start.sh backend     # Backend only
./start.sh frontend    # Frontend only
```

---

## 2. Accessing the Interface

Once started, open your web browser and go to:

| Service | URL |
|---------|-----|
| **GRACE Frontend (Main UI)** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **Interactive API Docs (Swagger)** | http://localhost:8000/docs |
| **Qdrant Dashboard** | http://localhost:6333/dashboard |

You will be presented with the **Genesis Login** screen. Enter your credentials to proceed into the main interface.

---

## 3. Navigation Overview

The GRACE UI is a single-page application with a **tab-based navigation sidebar** on the left. Each tab opens a different panel or feature. The top bar contains quick-access controls (voice, search, notifications).

**Primary navigation groups:**

| Group | Tabs Included |
|-------|---------------|
| **Chat** | Chat, Consensus Chat, Directory Chat |
| **Knowledge** | File Browser, Folders, Ingestion Dashboard, Librarian, Knowledge Base Manager, Web Scraper |
| **Cognitive** | Cognitive, Learning & Healing, Oracle, GRACE Lab, Flash Cache |
| **Governance** | Governance, Whitelist |
| **Planning** | GRACE Planning, GRACE Todos, Tasks, Notion |
| **Analytics** | ML Intelligence, KPI Dashboard, Business Intelligence, RAG, Insights, Telemetry |
| **Provenance** | Genesis Key Panel, Genesis Timeline, Version Control, Repository Manager |
| **System** | Monitoring, System Health, Activity Feed, Terminal Log Viewer |
| **Developer** | Codebase Browser, CI/CD Dashboard, Orchestration, API Testing, Dev Tab |
| **Docs** | Documentation Library |

> **New to GRACE?** Open the **TabGuide** (bubble icon in the sidebar) for an interactive walkthrough of each tab.

---

## 4. Core Features

### 4.1 Chat & Assistant

The **ChatWindow** is the primary interface for interacting with GRACE.

**How to use:**
1. Type your question or command in the input field at the bottom and press **Enter** or click **Send**.
2. GRACE will respond using its **Multi-Tier RAG Pipeline**:
   - **Tier 1 (Vector DB):** Searches your ingested documents semantically via Qdrant. This is the most reliable source.
   - **Tier 2 (Model Knowledge):** Falls back to the LLM's built-in knowledge if no strong document match is found.
   - **Tier 3 (Web Search / User Context):** If confidence is still low, GRACE can perform a web search (SerpAPI) or ask you for additional context.
3. You can view **conversation history** in the left sidebar (**ChatList**). Click any previous chat to resume it.

**Key features:**
- Full **Markdown rendering** in responses (code blocks, tables, lists)
- **Streaming responses** via Server-Sent Events (SSE) — answers appear word-by-word
- **File context:** Attach an uploaded file as context for your next message
- **Search Internet button** — trigger a live web search alongside your question

---

### 4.2 Document Ingestion & Knowledge Base

This is how you teach GRACE about your specific business data, procedures, or documentation.

**Supported file formats:**
PDF, DOCX, PPTX, XLSX, TXT, Markdown (`.md`), Python (`.py`), JSON, YAML, CSV

**How to ingest a document:**
1. Go to the **File Browser** tab or **Ingestion Dashboard** tab.
2. Click **Upload** and select one or more files from your computer.
3. GRACE will automatically:
   - Split the document into chunks
   - Generate semantic embeddings
   - Store them in the Qdrant vector database
   - Run the **AI Librarian** to categorize and tag the document
4. Once ingested, the document will appear in future chat answers when relevant.

**Bulk ingestion:** Place files in the `knowledge_base/` folder and GRACE will auto-ingest them on startup (controlled by the `SKIP_AUTO_INGESTION` environment variable).

---

### 4.3 AI Librarian

The **Librarian Tab** provides an AI-powered document management layer on top of your knowledge base.

**Features:**
- **Auto-categorization** — uses the LLM to assign categories to each document
- **Smart tagging** — suggests and applies tags automatically
- **Relationship detection** — identifies semantic relationships between documents (e.g., "this policy document is related to this procedure guide")
- **Approval workflow** — AI suggestions above the confidence threshold are applied automatically; borderline suggestions go to a human review queue
- **Manual overrides** — you can always edit categories, tags, and relationships manually

**How to use:**
1. Open the **Librarian Tab**.
2. Browse documents, filter by category or tag.
3. Check the **Pending Approvals** section for AI suggestions awaiting your review.
4. Click **Approve** or **Reject** for each suggestion.

---

### 4.4 File Browser

The **File Browser** provides a full file management UI backed directly by GRACE's file intelligence system.

- Upload, download, rename, and delete files
- Preview text and code files inline
- See Genesis provenance information per file (creation time, modification history)
- Trigger manual re-ingestion of any file

---

### 4.5 Folders & Directory Chat

- **Folders Tab** — navigate the full directory tree of your GRACE knowledge base. Expand folders, browse files, and trigger folder-level operations.
- **Directory Chat** — scope your conversation to a specific folder. Ask questions that are answered *only* using documents within that folder. Useful for project-specific Q&A.

---

## 5. Cognitive & Learning Features

### 5.1 Cognitive Tab

Visualizes the internal state of GRACE's reasoning engine:

- **Active OODA Loop state** (Observe → Orient → Decide → Act)
- **Contradiction alerts** — if two of your ingested documents conflict, they appear here
- **Ambiguity resolution** — queries that GRACE found ambiguous and how it resolved them
- **Episodic memory** — notable past interactions stored as structured memories

---

### 5.2 Learning & Healing Tab

Shows GRACE's autonomous self-improvement activity:

- **Pattern extractions** — knowledge patterns the system has distilled from interactions
- **Active learning** — knowledge gaps GRACE has identified and is trying to fill
- **Healing events** — self-repair actions taken by the autonomous healing system (e.g., "restarted degraded embedding service", "garbage-collected stale memory cache")
- **Healing timeline** — chronological log of all healing actions

---

### 5.3 Oracle Tab

The **Oracle** is GRACE's highest-level reasoning abstraction:

- **Ask the Oracle** — pose deep, strategic questions. The Oracle reasons across all memory types (episodic, procedural, learned patterns) before answering.
- **World Model** — view GRACE's continuously updated model of the project's current state (what's working, what's broken, what's incomplete).
- **Knowledge gap audit** — run a full audit to identify what GRACE doesn't know. You can then instruct GRACE to autonomously fill those gaps via web research or document study.
- **Trust Leaderboard** — see which documents and data sources the system trusts most highly.

---

### 5.4 GRACE Lab (Sandbox Experiments)

The **Lab Tab** lets you run controlled experiments over time.

**How to propose an experiment:**
1. Open the **Lab Tab**.
2. Enter a **Title**, **Description**, and **Hypothesis** (e.g., "Does chunking PDFs at 256 tokens improve retrieval accuracy?").
3. Click **Propose Experiment**.
4. GRACE will track relevant metrics automatically for up to **60 days**.
5. Click **Analyse Now** at any point for an interim report.

Experiments are isolated — they do not affect the production knowledge base.

---

### 5.5 Flash Cache Panel

The **Flash Cache Panel** exposes GRACE's ultra-fast transient retrieval layer:

- View what's currently cached (recent queries, preloaded context)
- Manually flush the cache if stale data is affecting responses
- See cache hit/miss ratios in real time

---

## 6. Governance & Safety

### 6.1 Governance Tab (Three-Pillar Control)

This is your **safety command center**. GRACE operates semi-autonomously but requires human approval for high-impact actions.

**The Three Pillars:**
1. **Aye / Nay Gate** — Approve or reject pending autonomous actions before they execute
2. **Audit Trail** — Every approved or rejected action is logged with timestamp, rationale, and outcome
3. **Policy Configuration** — Set thresholds: which action types always require approval vs. which can auto-execute

**Typical workflow:**
1. GRACE proposes a high-risk action (e.g., "delete 47 stale documents from the knowledge base", "modify a core configuration file").
2. A notification badge appears on the **Governance Tab**.
3. Open the tab and review the **pending request**: action description, GRACE's confidence score, and its reasoning.
4. Open **Governance Discussion** to see GRACE's internal debate about the action.
5. Click **Approve (Aye)** or **Reject (Nay)**.
6. GRACE executes (or discards) the action and logs the outcome.

> **Important:** Never approve actions you don't understand. GRACE's confidence score above 85% generally indicates high safety; below 60% warrants extra scrutiny.

---

### 6.2 Whitelist Tab (Human-to-AI Learning)

The **Whitelist** lets you directly feed curated information into GRACE's learning pipeline:

- **Add a Whitelist Entry** — paste a fact, rule, or procedure. GRACE treats whitelisted entries as high-trust ground truth.
- **Review & Edit** — you can update or remove entries at any time.
- **Pipeline Integration** — whitelisted entries bypass the standard confidence filter and are stored directly in the learning memory layer.

Use this to correct GRACE's wrong assumptions or inject institutional knowledge that isn't in any document.

---

## 7. Autonomous Agents & Tools

### 7.1 Consensus Chat (Multi-Agent Debate)

For complex or high-stakes questions, use **Consensus Chat** instead of the regular chat:

1. Open the **Consensus Chat** tab.
2. Type your question.
3. Instead of a single response, GRACE will:
   - Ask multiple AI models (e.g., Qwen, Mistral, Kimi/Claude) the same question simultaneously
   - Display each model's raw answer
   - Run a **debate round** where models challenge each other's responses
   - Synthesize a **final verified consensus answer** with a confidence score
4. The UI shows the full deliberation in real time.

**When to use it:** Critical decisions, complex technical questions, any situation where a single-model hallucination would be costly.

---

### 7.2 Model Context Protocol (MCP) Agentic Tools

GRACE includes a **Unified Agentic Orchestrator** (`/api/mcp`) that lets the AI directly interact with your local environment using safe, audited tools.

**You don't need to configure anything.** When you ask GRACE to perform a file, terminal, or code task, it automatically selects and uses the right tool.

**Available tools:**

| Category | Tool | What it does |
|----------|------|-------------|
| **Knowledge** | `rag_search` | Search the GRACE knowledge base |
| **Web** | `web_search`, `web_fetch` | Search the internet and fetch page content |
| **Filesystem** | `read_file`, `write_file`, `list_directory`, `move_file`, `get_file_info`, `write_pdf` | Read/write files within allowed boundaries |
| **Terminal** | `start_process`, `read_process_output`, `interact_with_process`, `force_terminate` | Run OS-level commands securely |
| **Code** | `edit_block` | Surgically modify source code files |
| **Search** | `start_search`, `get_more_search_results` | Advanced local file indexing and search |

**Example prompts that trigger MCP tools:**
- *"Read the file `config/settings.yaml` and summarize it"* → uses `read_file`
- *"Run `pytest tests/` and show me the output"* → uses `start_process` + `read_process_output`
- *"Search this codebase for all uses of `deprecated_function`"* → uses `start_search`

> **Safety:** High-risk actions (e.g., writing to files, running terminal commands) are intercepted by the **Governance Gate** if the action crosses a risk threshold.

---

### 7.3 GRACE Planning Tab

The **Planning Tab** takes a concept and turns it into a structured execution plan:

1. Enter a high-level goal (e.g., "Build a data pipeline to ingest weekly CSV reports").
2. Click **Generate Plan**. GRACE produces a phased breakdown with tasks, dependencies, and estimated effort.
3. Click **Send to Todos** to push the plan's tasks into the GRACE Todos board.
4. Each task gets tracked, updated, and verified as GRACE executes it.

---

### 7.4 GRACE Todos Tab

A **drag-and-drop autonomous task board** — like a Kanban board, but tasks can self-execute.

- Columns: **Backlog → In Progress → Done → Blocked**
- Tasks can be created manually or imported from the Planning Tab
- Each task shows its Genesis Key (provenance ID) and execution log
- GRACE auto-moves tasks from In Progress to Done when it completes them
- Blocked tasks trigger a Governance review

---

### 7.5 Tasks Tab

The **Tasks Tab** provides a more detailed view of all autonomous tasks currently running, queued, or completed:

- View full task history with timestamps and outcomes
- Re-trigger failed tasks
- See which MCP tools each task used
- Export task logs for audit purposes

---

## 8. ML Intelligence & Analytics

### 8.1 ML Intelligence Tab

Real-time visibility into GRACE's ML subsystems:

- **Neural Trust Scores** — per-document and per-source trust ratings (0.0 – 1.0)
- **Multi-Armed Bandit** — which retrieval strategies GRACE is currently exploring vs. exploiting
- **Meta-Learning progress** — how quickly GRACE generalizes from few-shot examples
- **Uncertainty Quantification** — confidence intervals on current model predictions
- **Online Learning pipeline** — streaming training events and their outcomes

---

### 8.2 KPI Dashboard

Tracks key performance indicators for the GRACE system:

| KPI | Description |
|-----|-------------|
| **Query Success Rate** | % of queries that returned a confident answer |
| **Retrieval Hit Rate** | % of queries resolved via vector DB (Tier 1) |
| **Hallucination Rate** | % of responses flagged by the hallucination guard |
| **Ingestion Throughput** | Documents ingested per hour |
| **Avg Response Latency** | End-to-end response time in milliseconds |
| **Healing Actions / Day** | Number of autonomous self-repair events |

Click any KPI card to drill down into a time-series chart.

---

### 8.3 Business Intelligence Tab

Transforms raw system telemetry into **human-readable technical narratives**:

- "The retrieval hit rate dropped 12% on Tuesday because three key policy documents expired and were removed from the KB."
- Shows trend charts for all major metrics
- Highlights anomalies and explains their likely causes
- Useful for weekly review meetings and client reporting

---

### 8.4 RAG Pipeline Tab

Visualize exactly how a query flows through the multi-tier RAG pipeline:

- Run a test query and watch it flow through Tier 1 → Tier 2 → Tier 3
- See which documents were retrieved, their similarity scores, and their re-ranking order
- Inspect the final prompt assembled before sending to the LLM
- Identify why certain queries are falling through to Tier 3 (web search)

---

### 8.5 Insights Tab

AI-generated insights derived from system patterns:

- "Your knowledge base has a cluster of highly related documents on [topic] — consider consolidating them."
- "Query volume spiked 3x on questions related to [topic] — you may want to add more documentation here."
- "Trust score for source X has been declining — consider re-ingesting or updating those documents."

---

## 9. Genesis Provenance & Version Control

### 9.1 Genesis Key Panel & Timeline

Every data mutation in GRACE (file ingestion, document update, configuration change, learning event) generates a **Genesis Key** — an immutable provenance record.

**Viewing Genesis Keys:**
1. Open the **Genesis Key Panel** tab.
2. Browse the full provenance ledger. Filter by date, operation type, or entity.
3. Click any entry for full details: what changed, when, by which system component, and what the previous state was.

**Genesis Timeline** — a visual, chronological timeline of all Genesis events, perfect for audit reviews.

---

### 9.2 Version Control Tab

GRACE maintains **full file version history** via the Genesis system, independent of Git:

- Browse any file's full edit history
- See a diff view between any two versions
- **Revert** any file to any previous version with one click (triggers a Governance approval if configured)
- View the **Commit Timeline** and **Git Tree** if the project is linked to a Git repository via the Genesis-Git Bridge

---

### 9.3 Repository Manager

Manage multiple code/data repositories connected to GRACE:

- Add remote repositories (Git URLs)
- Trigger repository scans to analyze structure, patterns, and add them to the knowledge base
- View per-repository Genesis history

---

## 10. System Monitoring & Diagnostics

### 10.1 Monitoring Tab

Real-time system health at a glance:

- CPU, memory, and disk usage
- Qdrant vector database status and collection statistics
- Ollama LLM server status and active model
- Active WebSocket connections
- Recent API error rate

---

### 10.2 System Health Tab (Immune System)

The **Immune System** (AVN) runs continuously in the background. This tab shows its activity:

- **Current health status** — Green / Yellow / Red per subsystem
- **Detected anomalies** — what the system detected and when
- **Healing actions taken** — automatic recovery steps executed
- **Escalated issues** — problems that couldn't be auto-healed and were sent to the Governance queue
- **Proactive healing predictions** — issues the system predicts may occur and pre-emptive steps taken

---

### 10.3 Telemetry Tab

Raw telemetry data viewer:

- Drill into any telemetry event (type, timestamp, component, payload)
- Filter by event type or time range
- **Action Replay** — replay any recorded sequence of events for debugging

---

### 10.4 Activity Feed

A live, real-time stream of everything happening inside GRACE:

- Documents being ingested
- Queries being processed
- Learning events
- Healing actions
- Governance requests raised and resolved
- MCP tool calls made by the agent

---

### 10.5 Terminal Log Viewer

View the **live backend application log** directly from the UI without needing to access the server:

- Streams `backend/logs/grace.log` in real time
- Filter by log level (DEBUG / INFO / WARNING / ERROR)
- Search for specific error messages or keywords
- Equivalent to running `Get-Content backend\logs\grace.log -Tail 200 -Wait` from PowerShell

---

## 11. Developer & Power-User Tools

### 11.1 Codebase Tab

An AI-powered code browser for the entire GRACE codebase:

- Browse files and directories
- View syntax-highlighted source code
- Ask questions about any file (e.g., "What does this function do?")
- Get dependency graphs for any module

---

### 11.2 CI/CD Dashboard

Monitor and control the **Genesis CI/CD** self-hosted pipeline:

- View pipeline run history for `grace-ci`, `grace-quick`, and `grace-deploy`
- Trigger a pipeline run manually: click **Run Pipeline** and select a pipeline name
- See per-step logs, durations, and pass/fail status
- Configure trust-based gating — a pipeline step can be blocked until its Genesis trust score meets a threshold

---

### 11.3 Orchestration Tab

Control the **LLM Orchestration** layer:

- Switch the active LLM model (e.g., from `mistral:7b` to `gpt-4o`)
- View multi-LLM collaboration sessions
- Inspect the hallucination guard's recent detections and what responses were blocked

---

### 11.4 Web Scraper

Manually trigger URL scraping to add web-sourced content to the knowledge base:

1. Paste a URL into the input field.
2. Click **Scrape**. GRACE fetches, parses, and extracts clean text from the page.
3. Click **Ingest** to add the extracted content to the vector database.

You can also queue multiple URLs for batch scraping.

---

### 11.5 Voice Interface

GRACE supports full voice interaction:

- Click the **microphone button** (VoiceButton) in the top right corner to start speaking. Your speech is converted to text (STT) and sent as a chat message.
- Responses can be read aloud via text-to-speech (TTS) using the **PersistentVoicePanel**.
- The persistent voice panel remains available across all tabs — you don't need to return to chat to use voice.

---

### 11.6 API Testing Tab

An embedded **interactive API explorer** (powered by the GRACE API schema):

- Browse all 50+ API router endpoints
- Send test requests directly from the UI
- View real JSON response bodies
- Useful for integration testing without needing Postman or curl

Also accessible at `http://localhost:8000/docs` (Swagger UI).

---

### 11.7 Dev Tab

A comprehensive developer diagnostics panel:

- Live component registry state
- Internal message bus event viewer
- Memory mesh snapshot viewer
- Layer 1 connector status (all 11 pluggable connectors)
- Raw embedding model info (model name, device, dimension)

---

### 11.18 Notion / Kanban Tab

A native **Kanban task board** compatible with Notion task structures:

- Create, edit, and move task cards between columns
- Assign tasks to team members
- Link tasks to GRACE Planning entries or autonomous action results
- Sync with an external Notion workspace (requires Notion API key in `.env`)

---

## 12. Documentation Library (Docs Tab)

The **Docs Tab** provides an integrated, searchable documentation library directly within the GRACE UI:

- Browse the full `docs/` folder (229 documentation files)
- Search across all docs by keyword
- View rendered Markdown documentation inline
- Reference architecture diagrams, API references, deployment guides, and more — without leaving the app

---

## 13. Maintenance & Troubleshooting

### 13.1 Checking System Logs

**Option 1 — In-App (Recommended):** Open the **Terminal Log Viewer** tab for a live log stream.

**Option 2 — File System:**
- **Log file location:** `backend/logs/grace.log`
- **Windows PowerShell:** `Get-Content backend\logs\grace.log -Tail 200`
- **Linux/Mac:** `tail -f backend/logs/grace.log`

**Log levels to look for:**
| Level | Meaning |
|-------|---------|
| `INFO` | Normal operation |
| `WARNING` | Non-critical issue, system continued |
| `ERROR` | A component failed — check context |
| `CRITICAL` | System-level failure — requires intervention |

---

### 13.2 GPU / Embedding Issues

If AI responses are very slow or you see embedding errors:

1. Open `http://localhost:8000/api/runtime/connectivity` in your browser.
2. Look for `"cuda_available": true` and `"services.embedding.using_gpu": true`.
3. If both show `false` and you have an NVIDIA GPU, run:
   ```powershell
   .\setup_gpu.bat
   ```
4. Restart GRACE (`Ctrl+C` then `.\start.bat`).

If you don't have a GPU, set `EMBEDDING_DEVICE=cpu` in `backend/.env` (will be slower but fully functional).

---

### 13.3 Common Issues & Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Frontend shows "Cannot connect to server" | Backend not running | Check terminal for Python errors; restart with `.\start.bat backend` |
| Chat returns "No relevant documents found" | Knowledge base empty | Upload documents via File Browser and wait for ingestion to complete |
| Qdrant errors in log | Qdrant container not running | Run `docker start grace-qdrant` or restart Docker Desktop |
| Ollama errors in log | Ollama not running | Run `ollama serve` in a separate terminal |
| Governance queue filling up | GRACE is overly cautious | Adjust governance thresholds in the Governance Tab settings |
| Embeddings failing to load | Missing model file or wrong device | Check `EMBEDDING_DEFAULT` and `EMBEDDING_DEVICE` in `backend/.env` |
| Database errors on startup | Schema out of date | Run `cd backend && python run_all_migrations.py` |
| Very slow responses | CPU-only mode or low memory | Enable GPU (`setup_gpu.bat`) or reduce `MAX_NUM_PREDICT` in `.env` |

---

### 13.4 Shutting Down Gracefully

1. Find the terminal window where `start.bat` / `start.sh` is running.
2. Press **`Ctrl + C`**.
3. If prompted "Terminate batch job (Y/N)?", press **`Y`** and hit **Enter**.
4. Qdrant (if running in Docker) can be stopped with: `docker stop grace-qdrant`

GRACE saves state automatically — conversations, learned patterns, and Genesis provenance data are all persisted to disk.

---

## 14. Environment & Configuration

All configuration is in `backend/.env`. Key settings you may need to change:

| Variable | Default | When to change |
|----------|---------|----------------|
| `LLM_PROVIDER` | `ollama` | Change to `openai` to use GPT-4o |
| `LLM_API_KEY` | _(empty)_ | Required if using OpenAI |
| `LLM_MODEL` | `mistral:7b` | Change to any Ollama model you've pulled |
| `EMBEDDING_DEVICE` | `cuda` | Change to `cpu` if no GPU |
| `DATABASE_TYPE` | `sqlite` | Change to `postgresql` for production |
| `SERPAPI_KEY` | _(empty)_ | Required for web search feature |
| `LIGHTWEIGHT_MODE` | `false` | Set `true` to disable all heavy components (debug/testing only) |
| `DISABLE_GENESIS_TRACKING` | `false` | Set `true` to disable provenance tracking (not recommended) |

After editing `.env`, restart GRACE for changes to take effect.

---

*For technical deployment support, infrastructure questions, or source code documentation, refer to the developer **[README.md](README.md)** and the **`docs/`** folder.*
