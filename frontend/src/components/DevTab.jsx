import { useState, useEffect, useRef } from "react";
import { brainCall } from "../api/brain-client";

export default function DevTab() {
  const [detail, setDetail] = useState(null);
  const [leftWidth, setLeftWidth] = useState(200);
  const [rightWidth, setRightWidth] = useState(320);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  // Listen for file open events from file tree
  useEffect(() => {
    const handler = (e) => {
      const { path, content } = e.detail;
      setDetail({
        title: path.split("/").pop(),
        icon: "📝",
        desc: `Editing: ${path}. Ctrl+S to save + hot reload.`,
        data: { _special: "editor", path, content },
      });
      setRightCollapsed(false);
    };
    window.addEventListener("grace-open-editor", handler);
    return () => window.removeEventListener("grace-open-editor", handler);
  }, []);

  return (
    <div style={{ display: "flex", height: "100%", background: "#0a0a1a", color: "#ccc" }}>
      {!leftCollapsed ? (
        <>
          <LeftPanel onDetail={setDetail} width={leftWidth} />
          <Resizer onResize={(dx) => setLeftWidth(w => Math.max(160, Math.min(350, w + dx)))} />
        </>
      ) : (
        <button onClick={() => setLeftCollapsed(false)} style={{ width: 28, background: "#0d0d20", border: "none", borderRight: "1px solid #1a1a2e", color: "#555", cursor: "pointer", fontSize: 14, writingMode: "vertical-lr" }}>Actions ▸</button>
      )}

      <CenterChat
        onDetail={setDetail}
        onToggleLeft={() => setLeftCollapsed(p => !p)}
        onToggleRight={() => setRightCollapsed(p => !p)}
        activeProject={null}
        setActiveProject={() => {}}
      />

      {!rightCollapsed && detail ? (
        <>
          <Resizer onResize={(dx) => setRightWidth(w => Math.max(220, Math.min(500, w - dx)))} />
          <RightDetail content={detail} onClose={() => setDetail(null)} width={rightWidth} />
        </>
      ) : !rightCollapsed ? (
        <div style={{ width: 220, background: "#08081a", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
          <div style={{ color: "#333", fontSize: 11, textAlign: "center" }}>Click any action<br />to view details</div>
        </div>
      ) : (
        <button onClick={() => setRightCollapsed(false)} style={{ width: 28, background: "#08081a", border: "none", borderLeft: "1px solid #1a1a2e", color: "#555", cursor: "pointer", fontSize: 14, writingMode: "vertical-lr" }}>◂ Detail</button>
      )}
    </div>
  );
}

function Resizer({ onResize }) {
  const handleMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const onMove = (ev) => onResize(ev.clientX - startX);
    const onUp = () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  return (
    <div onMouseDown={handleMouseDown} style={{
      width: 4, cursor: "col-resize", background: "transparent", flexShrink: 0,
      borderLeft: "1px solid #1a1a2e", borderRight: "1px solid #1a1a2e",
    }}
    onMouseEnter={e => e.target.style.background = "#e9456033"}
    onMouseLeave={e => e.target.style.background = "transparent"}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════════
   LEFT PANEL — Actions
   Each button calls a brain action and shows the result in the
   right panel. Grouped into Diagnostics, Intelligence, Runtime,
   and Code sections.
   ═══════════════════════════════════════════════════════════════════ */

const ACTIONS = [
  {
    section: "Diagnostics",
    items: [
      {
        id: "probe", label: "Run Probe", icon: "📡",
        brain: "system", action: "probe",
        desc: "Crawls every registered API endpoint and sends a synthetic health-check pulse. Reports which endpoints are alive (200), broken (5xx), or dormant (timeout). Connects to: probe_agent_api → all registered FastAPI routes.",
      },
      {
        id: "stress", label: "Stress Test", icon: "⚡",
        brain: "system", action: "auto_cycle",
        desc: "Runs one full Ouroboros autonomous cycle: scans triggers, checks component health, runs trust gates, consults episodic memory, then executes healing if needed. Connects to: autonomous_loop_api → component_health_api → runtime_triggers_api → diagnostic_engine.",
      },
      {
        id: "health", label: "Health Map", icon: "🗺️",
        brain: "system", action: "health_map",
        desc: "Shows all 16 monitored components color-coded: green=healthy, yellow=idle, orange=degrading, red=broken. Each component is profiled by its Genesis key activity pattern over the time window. Connects to: component_health_api → genesis key DB → service health checks (Ollama, Qdrant, DB).",
      },
      {
        id: "problems", label: "Problems", icon: "🔴",
        brain: "system", action: "problems",
        desc: "Lists all current red/orange components with error rates, event counts, and last-seen timestamps. Shows remediation suggestions and whether auto-healing was triggered. Connects to: component_health_api → remediation rules engine.",
      },
      {
        id: "triggers", label: "Triggers", icon: "🎯",
        brain: "system", action: "triggers",
        desc: "Scans 5 trigger categories: RESOURCE (CPU/RAM/disk), SERVICE (Ollama/Qdrant/Kimi/Opus down), CODE (import errors, missing deps), NETWORK (port conflicts), LOGICAL (test failures). Critical triggers auto-fire healing. Connects to: runtime_triggers_api → psutil → urllib checks.",
      },
      {
        id: "invariants", label: "Invariants", icon: "✅",
        brain: "ai", action: "invariants",
        desc: "Checks system invariants — are all constraints satisfied? Validates trust score bounds (0-1), data integrity, memory consistency. If an invariant is violated, it signals the Ouroboros loop to investigate. Connects to: cognitive_mesh → cognitive/invariants.py → trust_engine.",
      },
      {
        id: "connectivity", label: "Connectivity", icon: "📡",
        brain: "system", action: "connectivity",
        desc: "Checks connectivity to all external services: Ollama, Qdrant Cloud, Kimi API, Opus API, database. Shows which are connected, which are down, and their URLs. Connects to: app.py runtime endpoints → service health checks.",
      },
    ],
  },
  {
    section: "Intelligence",
    items: [
      {
        id: "intelligence", label: "Intelligence", icon: "🧠",
        brain: "system", action: "intelligence",
        desc: "Full intelligence report: mines Genesis keys for patterns (type distribution, error clusters, temporal patterns, hot files, repeated failures), shows adaptive trust state for all models, and episodic memory analysis (recurring problems, source reliability, prediction accuracy). Connects to: core/intelligence.py → Genesis key DB → episodic memory → adaptive trust.",
      },
      {
        id: "trust", label: "Trust Scores", icon: "🛡️",
        brain: "system", action: "trust",
        desc: "Shows real-time adaptive trust scores for each LLM model (Kimi, Opus, Qwen, DeepSeek). Trust updates on every consensus result — agreement boosts trust, disagreement lowers the outlier. Also shows per-action trust from the Ouroboros loop. Connects to: core/intelligence.py → AdaptiveTrust → consensus_engine feedback.",
      },
      {
        id: "synapses", label: "Synapses", icon: "🔗",
        brain: "system", action: "synapses",
        desc: "Shows the Hebbian learning weight table — which brains collaborate most. Every call_brain() updates a synaptic weight: success=+0.05, failure=-0.03. Shows the top 10 strongest connections and per-brain connectivity. Connects to: core/hebbian.py → call_brain() wrapper.",
      },
      {
        id: "cognitive", label: "Cognitive Report", icon: "🧬",
        brain: "ai", action: "cognitive_report",
        desc: "Runs ALL cognitive modules and returns a unified report: OODA loop (observe-orient-decide-act), ambiguity resolution, invariant checks, knowledge gap analysis, procedural memory search. This is the full cognitive pipeline output. Connects to: core/cognitive_mesh.py → all cognitive/ modules.",
      },
      {
        id: "knowledge", label: "Knowledge Gaps", icon: "📚",
        brain: "ai", action: "knowledge_gaps_deep",
        desc: "Uses the memory mesh learner to identify what Grace knows vs what it can't do yet. Finds high-theory/low-practice gaps, high-value topics worth reinforcing, failure patterns that need restudy. Connects to: cognitive/memory_mesh_learner.py → learning_memory DB.",
      },
      {
        id: "dl_train", label: "Train DL", icon: "🎓",
        brain: "ai", action: "dl_train",
        desc: "Trains the PyTorch deep learning model on recent Genesis keys. 3-head MLP: predicts action success probability, component risk, and trust score. Saves weights to data/grace_model.pt. CPU-only, <50MB. Connects to: core/deep_learning.py → Genesis key DB → PyTorch.",
      },
    ],
  },
  {
    section: "Runtime",
    items: [
      {
        id: "runtime", label: "Runtime", icon: "⚙️",
        brain: "system", action: "runtime",
        desc: "Shows runtime state: paused/running, diagnostic engine status, self-healing active/off, uptime. This is the core system pulse. Connects to: app.py state → diagnostic_engine.",
      },
      {
        id: "hot_reload", label: "Hot Reload", icon: "🔄",
        brain: "system", action: "hot_reload",
        desc: "Re-reads .env file, refreshes consensus model registry (so new API keys take effect), reconnects DB pool, and re-runs startup diagnostic — all without restarting the process. Connects to: app.py → settings.py → consensus_engine → DatabaseConnection.",
      },
      {
        id: "genesis", label: "Genesis Stats", icon: "🔑",
        brain: "govern", action: "genesis_stats",
        desc: "Shows total Genesis keys created, error count, and user count. Genesis keys track every operation in the system with what/who/when/where/why/how. They are the audit backbone. Connects to: genesis_key_service.py → SQLite genesis_key table.",
      },
      {
        id: "traces", label: "Trace Buffer", icon: "📊",
        brain: "system", action: "traces",
        desc: "Shows the lightweight Genesis key ring buffer — 50K capacity, 1.6µs per write (300x faster than full keys). These batch-flush to DB every 10s. Shows recent trace IDs and buffer fill level. Connects to: core/tracing.py → in-memory deque → background flush thread.",
      },
    ],
  },
  {
    section: "Tasks",
    items: [
      {
        id: "task_live", label: "Live Activity", icon: "📺",
        brain: "tasks", action: "live",
        desc: "Real-time activity feed showing what Grace is doing right now — recent Genesis key events, running tasks, active brain calls. Updates from the last 5 minutes of system activity. Connects to: tasks_service.py → genesis_key DB (last 5 min).",
      },
      {
        id: "task_scheduled", label: "Scheduled Tasks", icon: "📅",
        brain: "tasks", action: "scheduled",
        desc: "View and manage scheduled tasks. Tasks can be created, prioritised, and reordered by drag-and-drop. Overdue tasks are auto-flagged. Connects to: tasks_service.py → data/scheduled_tasks.json.",
      },
      {
        id: "task_planner", label: "Planner", icon: "🗓️",
        brain: "tasks", action: "planner",
        desc: "Session-based planner for complex multi-step work. Create a plan, break it into steps, track progress. Uses TimeSense for urgency scoring and deadline tracking. Connects to: tasks_service.py → cognitive/time_sense.py.",
      },
      {
        id: "task_submit", label: "New Task", icon: "➕",
        brain: "tasks", action: "submit",
        payload: { title: "New task from Dev tab" },
        desc: "Create a new task with title, priority, and optional deadline. Tasks are tracked via Genesis key and appear in the live activity feed. Connects to: tasks_service.py → genesis_tracker.",
      },
    ],
  },
  {
    section: "Govern",
    items: [
      {
        id: "upload_rules", label: "Upload Rules", icon: "📜",
        special: "upload_govern",
        uploadTarget: "rules",
        desc: "Upload documents that become LAW for the LLMs — PDF, Word, TXT, CSV, JSON, YAML, code files, anything up to 5GB. Whatever these documents specify (coding standards, schemas, configs, API specs, environments) Grace follows in all outputs. Supports: PDF, DOCX, TXT, CSV, JSON, YAML, TOML, MD, XML, SQL, Python, JS, TS, HTML, CSS, ZIP. Connects to: chunked upload → governance_rules/ → GovernanceAwareLLM injects into every system prompt.",
      },
      {
        id: "upload_config", label: "Upload Config", icon: "⚙️",
        special: "upload_govern",
        uploadTarget: "config",
        desc: "Upload configuration files — requirements.txt, Docker compose, env files, package.json, tsconfig, any technical spec up to 5GB. Grace uses these as context for code generation. Connects to: chunked upload → governance_rules/config/ → governance wrapper.",
      },
      {
        id: "upload_schema", label: "Upload Schema", icon: "📐",
        special: "upload_govern",
        uploadTarget: "schema",
        desc: "Upload database schemas, API payloads, data models, type definitions — SQL, JSON Schema, Proto, TypeScript, GraphQL, OpenAPI specs. Grace generates code matching your exact structure. Up to 5GB. Connects to: chunked upload → governance_rules/schema/ → LLM context injection.",
      },
      {
        id: "upload_codebase", label: "Upload Codebase", icon: "📦",
        special: "upload_govern",
        uploadTarget: "codebase",
        desc: "Upload a full codebase as a ZIP, tarball, or individual files — up to 5GB. Grace analyzes the architecture and uses it as a blueprint for building new features that align with the existing code patterns. Connects to: chunked upload → governance_rules/codebase/ → LLM context with full project awareness.",
      },
      {
        id: "view_rules", label: "View Active Rules", icon: "📋",
        brain: "govern", action: "rules",
        desc: "Shows all governance documents currently active PLUS the 8-layer coding pipeline. These are injected into every LLM call as mandatory instructions — coding standards, schemas, configs, and the full pipeline workflow. Connects to: govern_service.list_rules() → data/governance_rules/ → coding_pipeline.",
      },
      {
        id: "view_pipeline", label: "Pipeline Workflow", icon: "🏗️",
        special: "show_pipeline",
        desc: "Shows the 8-layer coding pipeline that ALL models must follow as LAW: Runtime → Decompose → Propose → Select → Simulate → Generate → Verify → Deploy Gate. Each layer shows which brains are called and what trust score is required. This is the governance contract.",
      },
      {
        id: "dev_instruction", label: "Dev Instruction", icon: "📝",
        special: "dev_instruction",
        desc: "Type a free-text instruction that Grace must follow for all future code generation in this session. Example: 'Use TypeScript strict mode', 'Follow PEP 8', 'All APIs must return JSON with status field'. Gets saved as a governance rule. Connects to: govern_service → governance_rules → LLM wrapper.",
      },
    ],
  },
  {
    section: "Code",
    items: [
      {
        id: "backend_tree", label: "Backend Files", icon: "🐍",
        brain: "code", action: "tree",
        payload: { folder: "." },
        desc: "Shows the backend file tree. Browse the Python source code structure, click files to view content in the detail panel. Connects to: core/services/code_service.py → knowledge_base file system.",
      },
      {
        id: "frontend_tree", label: "Frontend Files", icon: "⚛️",
        special: "frontend_tree",
        desc: "Shows the frontend file tree (React/Vite). Browse src/ components, hooks, and config. Click any file to view its content. Connects to: core/services/files_service.py → frontend/src/ directory.",
      },
      {
        id: "visual_projects", label: "Project Cards", icon: "🃏",
        brain: "code", action: "visual_projects",
        desc: "Shows all projects as visual cards — name, type, file count, last updated. Double-click a card to drill into its file tree. Right-click to upload files directly into the project. Each project has its own scoped chat context. Connects to: core/services/project_service.py → data/projects/.",
      },
      {
        id: "create_project", label: "New Project", icon: "🆕",
        brain: "code", action: "create_project",
        special: "create_project_prompt",
        desc: "Create a new project with standard folder structure (frontend, backend, docs, tests). Give it a name and Grace sets up everything. Projects are isolated workspaces with scoped chat. Connects to: project_service.create_project().",
      },
      {
        id: "search_code", label: "Search Code", icon: "🔍",
        brain: "files", action: "search",
        payload: { query: "" },
        special: "search_prompt",
        desc: "Full-text search across the entire codebase. Enter a keyword, function name, or regex to find every file that contains it. Connects to: core/services/files_service.py → recursive file content search.",
      },
      {
        id: "pipeline", label: "Run Pipeline", icon: "🏗️",
        brain: "ai", action: "pipeline",
        special: "generate_prompt",
        desc: "Runs the full 8-layer coding pipeline synchronously. Layers 3+4 run in parallel (propose + select). All models must agree at each stage. Every layer tracked via Genesis key. Shows layer-by-layer results with trust scores when complete. Connects to: core/coding_pipeline.py → 24 brain calls across 8 layers.",
      },
      {
        id: "pipeline_bg", label: "Pipeline (Background)", icon: "⏳",
        brain: "ai", action: "pipeline_bg",
        special: "generate_prompt",
        desc: "Starts the pipeline in a background thread so you can keep working. Returns a run_id immediately. Check progress with Pipeline Progress button. Parallel execution where possible. Connects to: coding_pipeline.run_background() → threading.Thread.",
      },
      {
        id: "pipeline_progress", label: "Pipeline Progress", icon: "📊",
        brain: "ai", action: "pipeline_progress",
        desc: "Shows real-time progress of all running/completed pipelines. Includes: % complete, current chunk/layer, trust scores, errors, duration. Auto-refreshes. Use this after starting a background pipeline. Connects to: PipelineProgress tracker.",
      },
      {
        id: "generate_code", label: "AI Generate", icon: "✨",
        brain: "code", action: "generate",
        payload: { prompt: "" },
        special: "generate_prompt",
        desc: "Describe what you need in plain English and Grace generates the code. Uses the active LLM model with full project context. Connects to: core/services/code_service.py → llm_orchestrator → GovernanceAwareLLM.",
      },
      {
        id: "create_file", label: "New File", icon: "➕",
        brain: "code", action: "create",
        payload: { path: "", content: "" },
        special: "create_prompt",
        desc: "Create a new file in the codebase. Specify the path and optional initial content. Tracked via Genesis key code_change. Connects to: core/services/code_service.py → file system → genesis_tracker.",
      },
      {
        id: "logic_tests", label: "Run Tests", icon: "🧪",
        brain: "ai", action: "logic_tests",
        desc: "Runs the full logic test suite across all components. Shows pass/fail counts, error details, and overall system health score. Connects to: cognitive/deep_test_engine.py → all cognitive modules.",
      },
      {
        id: "cicd", label: "CI/CD Pipeline", icon: "🚀",
        brain: "system", action: "diagnostics",
        desc: "Grace's native CI/CD status. Auto-triggered by Genesis key code_change events via the auto-probe system. Shows last pipeline status, pass/fail, and deployment readiness. Connects to: auto_probe → test_grace_system.py → GitHub Actions CI.",
      },
      {
        id: "api_client", label: "API Client", icon: "🌐",
        special: "api_client",
        desc: "Built-in REST API client. Enter a URL, method, headers, and body to test any endpoint. Shows response status, headers, body, and latency. Like Postman but inside Grace. No external tool needed.",
      },
      {
        id: "draw", label: "Whiteboard", icon: "🎨",
        special: "drawing",
        desc: "Simple drawing canvas for sketching system diagrams, architecture, flows. Export as PNG to share with team. Draw boxes, arrows, text — plan visually before coding. Canvas saves to localStorage.",
      },
      {
        id: "custom_action", label: "+ Custom Action", icon: "➕",
        special: "custom_action",
        desc: "Create your own action button. Define a name, brain domain, action, and payload. The button is saved to localStorage and appears in your action list permanently. Build the Dev tab that fits YOUR workflow.",
      },
      {
        id: "ai_review", label: "AI Code Review", icon: "🤖",
        brain: "ai", action: "cognitive_report",
        desc: "Sends the current codebase state through the full cognitive pipeline for review. OODA analysis, ambiguity check, invariant validation, and knowledge gap detection — applied to the code. Connects to: core/cognitive_mesh.py → all cognitive modules.",
      },
    ],
  },
  {
    section: "Autonomous",
    items: [
      {
        id: "hot_reload_all", label: "Hot Reload Code", icon: "🔥",
        brain: "system", action: "hot_reload_all",
        desc: "Reloads ALL service modules without stopping Grace. Preserves state, rolls back on failure. Use after editing code — changes take effect immediately. Connects to: core/hot_reload.py → importlib.reload → state preservation.",
      },
      {
        id: "reload_history", label: "Reload History", icon: "📜",
        brain: "system", action: "reload_history",
        desc: "Shows the history of hot code reloads — which modules were reloaded, which failed, which rolled back. Useful for debugging reload issues. Connects to: core/hot_reload.py → _reload_history.",
      },
      {
        id: "genesis_storage", label: "Genesis Storage", icon: "💾",
        brain: "system", action: "genesis_storage",
        desc: "Shows Genesis key storage stats: hot tier size, sampling rate, unique fingerprints, compression stats, TTL config. The tiered system keeps 1000 keys in memory, samples high-frequency at 1%, and expires old keys by type. Connects to: core/genesis_storage.py.",
      },
      {
        id: "genesis_cleanup", label: "Cleanup Expired", icon: "🧹",
        brain: "system", action: "genesis_cleanup",
        desc: "Removes expired Genesis keys based on TTL: debug=48h, performance=7d, errors=30d, learning=90d. Reduces DB size while keeping important audit data. Connects to: genesis_storage.cleanup_expired() → SQLite DELETE.",
      },
      {
        id: "generate_report", label: "Generate Report", icon: "📊",
        brain: "system", action: "generate_report",
        desc: "Generates a daily report of everything Grace achieved: Genesis key activity, errors fixed, trust changes, pipeline runs, code changes. LLM-named with timestamp. Saved to data/reports/ and downloadable. Connects to: core/reports.py → intelligence → brain actions.",
      },
      {
        id: "list_reports", label: "View Reports", icon: "📋",
        brain: "system", action: "list_reports",
        desc: "Lists all saved reports with titles, dates, sizes. Click any report to view its full content. Reports are exportable as JSON. Connects to: core/reports.py → data/reports/ directory.",
      },
      {
        id: "frontend_preview", label: "Frontend Preview", icon: "🖥️",
        special: "frontend_preview",
        desc: "Opens a live iframe preview of the running frontend. Grace can see the actual UI, interact with it, and log what happens. Use this to test frontend changes in real-time without switching windows. Connects to: iframe → localhost:5173 (Vite dev) or localhost:8000 (built).",
      },
      {
        id: "auto_status", label: "Loop Status", icon: "♾️",
        brain: "system", action: "auto_status",
        desc: "Shows the Ouroboros autonomous loop state: running/stopped, cycle count, actions taken (healed/learned/coded/escalated), last cycle timestamp. The loop runs every 30s with trust gates, TimeSense, mirror, and episodic recall. Connects to: autonomous_loop_api → _loop_state.",
      },
      {
        id: "auto_cycle", label: "Run Cycle", icon: "🔁",
        brain: "system", action: "auto_cycle",
        desc: "Manually triggers one full autonomous cycle: TIME_FILTER → MIRROR → TRIGGER → DECIDE → TRUST_GATE → EPISODIC_RECALL → ACT → LEARN → KPI_UPDATE. Shows exactly what was found and what action was taken. Connects to: autonomous_loop_api → all cognitive modules.",
      },
      {
        id: "auto_log", label: "Cycle Log", icon: "📜",
        brain: "system", action: "auto_log",
        desc: "History of recent autonomous cycles — what triggers were found, what actions were taken, whether healing succeeded. Each cycle creates a Genesis key for full provenance. Connects to: autonomous_loop_api → _loop_log.",
      },
      {
        id: "consensus_fix", label: "Consensus Fix", icon: "🔧",
        brain: "system", action: "consensus_fix",
        desc: "Scans all problems, sends each to ALL models (Kimi, Opus, Qwen, DeepSeek) for diagnosis. If all models agree with >60% confidence, auto-executes the fix. Everything tracked via Genesis key. Connects to: consensus_fixer_api → consensus_engine → diagnostic_engine.",
      },
      {
        id: "intelligence_loop", label: "Intelligence Report", icon: "🧠",
        brain: "system", action: "intelligence",
        desc: "Full intelligence report combining Genesis key pattern mining (58K+ keys), adaptive trust state, and episodic memory analysis. This is the system's self-awareness output. Connects to: core/intelligence.py → GenesisKeyMiner + AdaptiveTrust + EpisodicMiner.",
      },
      {
        id: "approvals", label: "Pending Approvals", icon: "✋",
        brain: "govern", action: "approvals",
        desc: "Shows actions queued for human approval. The autonomous loop escalates risky actions here instead of auto-executing. Approve or reject each action. Connects to: component_health_api → approval queue → governance brain.",
      },
    ],
  },
];

// Universal right-click menu items (appear on every action)
const UNIVERSAL_MENU = [
  { label: "View Logs (Last 100)", id: "logs", icon: "📋", desc: "Pulls the last 100 entries from the lightweight trace ring buffer. Shows what happened recently across all brains — timestamps, actions, errors." },
  { label: "Copy Result", id: "copy", icon: "📎", desc: "Copies the last action result to your clipboard as formatted JSON. Useful for pasting into bug reports or sharing with team." },
  { label: "Export JSON", id: "export", icon: "💾", desc: "Downloads the full action result as a .json file with timestamp in the filename. Archives the output for offline analysis." },
  { label: "Compare with Previous", id: "compare", icon: "🔄", desc: "Side-by-side diff of the current result vs the last time this action ran. Highlights what changed — new errors, resolved issues, metric shifts." },
  { label: "Genesis Key History", id: "genesis_history", icon: "🔑", desc: "Shows the last 50 Genesis keys related to this action. Full audit trail — who triggered it, when, what happened, whether it was an error." },
  { label: "Run on Schedule", id: "schedule", icon: "⏰", desc: "Set up this action to run automatically on a recurring schedule (every hour, daily, weekly). Creates a scheduled task tracked by Genesis key." },
  { label: "Run Again", id: "rerun", icon: "▶️", desc: "Re-executes this action with the same parameters as last time. No need to configure — just fires immediately." },
];

const SECTION_MENU = {
  Diagnostics: [
    { label: "Save as Baseline", id: "baseline", icon: "📌", desc: "Stores the current output as the 'golden state' for this action. Future runs can be diffed against this baseline to spot regressions." },
    { label: "Run Verbose", id: "verbose", icon: "🔍", desc: "Runs the same action with extra detail — includes per-component latency, memory usage, and raw sensor data from the diagnostic engine." },
    { label: "Stress x10", id: "stress10", icon: "⚡", desc: "Runs the probe or stress test 10 times in parallel to simulate high load. Shows aggregate pass/fail rates and identifies flaky endpoints." },
    { label: "Export Report", id: "report", icon: "📄", desc: "Generates a comprehensive diagnostic report as a downloadable file. Includes health map, trigger scan, problems list, and remediation actions." },
  ],
  Intelligence: [
    { label: "Trust Heatmap", id: "heatmap", icon: "🌡️", desc: "Opens a visual matrix showing trust scores between every model and every brain domain. Red=low trust, green=high trust. Based on consensus feedback loop." },
    { label: "Retrain Subset", id: "retrain", icon: "🎯", desc: "Trains the DL model on a specific date range or tag subset instead of all keys. Useful for focusing learning on recent activity or a specific domain." },
    { label: "Reset Cache", id: "reset_cache", icon: "🗑️", desc: "Flushes the cognitive working memory caches without restarting. Clears stale predictions and forces fresh computation on next cycle." },
    { label: "Export Model", id: "export_model", icon: "📦", desc: "Downloads the current PyTorch model weights (grace_model.pt) as a portable file. Can be loaded on another Grace instance or used for offline analysis." },
  ],
  Runtime: [
    { label: "GC Now", id: "gc", icon: "♻️", desc: "Forces Python garbage collection immediately. Reclaims memory from dead objects. Shows how many objects were collected." },
    { label: "Heap Dump", id: "heap", icon: "💽", desc: "Captures a snapshot of current memory allocation. Shows what objects are consuming the most RAM — useful for finding memory leaks." },
    { label: "Thread Dump", id: "threads", icon: "🧵", desc: "Lists all active Python threads with their current stack traces. Shows if any thread is stuck, deadlocked, or consuming excessive CPU." },
  ],
  Tasks: [
    { label: "Duplicate Task", id: "duplicate", icon: "📋", desc: "Creates a copy of the selected task with the same title, priority, and config. Pre-fills the new task form so you can adjust and submit." },
    { label: "Pause Queue", id: "pause_queue", icon: "⏸️", desc: "Stops accepting new tasks into the queue. Tasks already running will finish, but nothing new starts. Resume to accept tasks again." },
    { label: "Drain Workers", id: "drain", icon: "🚰", desc: "Lets all in-flight tasks complete naturally but prevents new ones from starting. Useful before deployments or maintenance windows." },
  ],
  Code: [
    { label: "Git Diff", id: "git_diff", icon: "📝", desc: "Shows uncommitted changes in the backend or frontend codebase. Compares working directory against the last commit — highlights additions, deletions, and modifications." },
    { label: "Run Tests", id: "run_tests", icon: "🧪", desc: "Executes the full test suite (35 tests across 4 levels: smoke, component, integration, end-to-end). Reports pass/fail counts and any error details." },
    { label: "Lint Check", id: "lint", icon: "✨", desc: "Runs flake8 lint check on the backend Python code. Catches syntax errors, undefined names, and style violations before they hit CI." },
    { label: "AI Suggest Fix", id: "suggest_fix", icon: "🔧", desc: "Sends the current error or failing test to the consensus engine. All models propose a fix — if they agree, the patch is shown for review." },
    { label: "File History", id: "file_history", icon: "📜", desc: "Shows the Genesis key history for the selected file — every create, edit, and delete event with timestamps and who made the change." },
    { label: "Explain Code", id: "explain", icon: "💡", desc: "Sends the selected file to the AI for a plain-English explanation. Useful for onboarding or understanding unfamiliar code." },
  ],
  Autonomous: [
    { label: "Force Heal", id: "force_heal", icon: "💊", desc: "Immediately runs the scan-and-heal pipeline: scans all triggers, checks component health, and auto-executes safe healing actions (DB reconnect, GC, diagnostic cycle)." },
    { label: "Pause Loop", id: "pause_loop", icon: "⏸️", desc: "Pauses the Ouroboros autonomous loop. The 30s cycle stops running, but all API endpoints stay available. Self-healing and auto-probe are suspended." },
    { label: "Resume Loop", id: "resume_loop", icon: "▶️", desc: "Resumes the Ouroboros autonomous loop after being paused. The 30s cycle restarts with trust gates, TimeSense, mirror, and episodic recall." },
  ],
};


// Load custom actions from localStorage
function getCustomActions() {
  try {
    return JSON.parse(localStorage.getItem("grace_custom_actions") || "[]");
  } catch { return []; }
}

function LeftPanel({ onDetail, width = 200 }) {
  const [loading, setLoading] = useState({});
  const [hoveredId, setHoveredId] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [fullWindow, setFullWindow] = useState(null);
  const [lastResults, setLastResults] = useState({});

  const run = async (item) => {
    // File upload with 5GB chunked support
    if (item.special === "upload_govern") {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.accept = ".txt,.csv,.md,.json,.yaml,.yml,.toml,.pdf,.env,.sql,.proto,.ts,.tsx,.js,.jsx,.py,.xml,.html,.css,.scss,.zip,.tar,.gz,.docx,.doc,.xlsx,.xls,.pptx,.graphql,.openapi,.swagger,.prisma,.tf,.sh,.bat,.cfg,.ini,.conf,.log,.r,.go,.rs,.java,.kt,.swift,.c,.cpp,.h,.hpp,.cs,.rb,.php,.pl,.ex,.exs,.hs,.ml,.scala,.lua,.dart,.vue,.svelte,.astro";
      input.onchange = async (e) => {
        const files = Array.from(e.target.files);
        if (!files.length) return;
        setLoading(p => ({ ...p, [item.id]: true }));

        const category = item.uploadTarget || "general";
        const results = [];

        for (const file of files) {
          const sizeMB = (file.size / 1048576).toFixed(1);

          if (file.size > 50 * 1024 * 1024) {
            // Large file (>50MB): use chunked upload
            try {
              const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
              const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
              const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

              // Initiate
              const initResp = await fetch(`${BASE}/api/upload/initiate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: file.name, file_size: file.size, folder: `governance_rules/${category}`, auto_ingest: true }),
              });
              const initData = await initResp.json();
              const uploadId = initData.upload_id;

              // Upload chunks
              for (let i = 0; i < totalChunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunk = file.slice(start, end);
                const formData = new FormData();
                formData.append("file", chunk);
                formData.append("upload_id", uploadId);
                formData.append("chunk_index", i.toString());
                await fetch(`${BASE}/api/upload/chunk`, { method: "POST", body: formData });
              }

              // Complete
              await fetch(`${BASE}/api/upload/complete`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ upload_id: uploadId }),
              });

              results.push({ file: file.name, size: `${sizeMB}MB`, status: "uploaded (chunked)", chunks: totalChunks });
            } catch (err) {
              results.push({ file: file.name, size: `${sizeMB}MB`, status: "failed", error: err.message });
            }
          } else {
            // Small file: direct read and save
            try {
              let content;
              if (file.name.endsWith(".pdf") || file.name.endsWith(".docx") || file.name.endsWith(".zip") || file.name.endsWith(".gz") || file.name.endsWith(".tar")) {
                // Binary files: upload via FormData to librarian
                const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                const formData = new FormData();
                formData.append("file", file);
                formData.append("folder", `governance_rules/${category}`);
                const r = await fetch(`${BASE}/api/librarian-fs/file/upload`, { method: "POST", body: formData });
                results.push({ file: file.name, size: `${sizeMB}MB`, status: r.ok ? "uploaded" : "failed" });
                continue;
              }

              content = await file.text();
              const r = await brainCall("files", "create", {
                path: `governance_rules/${category}/${file.name}`,
                content: content,
                directory: `governance_rules/${category}`,
              });
              results.push({
                file: file.name,
                size: `${sizeMB}MB`,
                status: r.ok ? "uploaded" : "failed",
                preview: content.slice(0, 200),
              });
            } catch (err) {
              results.push({ file: file.name, size: `${sizeMB}MB`, status: "failed", error: err.message });
            }
          }
        }

        setLoading(p => ({ ...p, [item.id]: false }));
        onDetail({
          title: `Uploaded ${results.length} file(s)`,
          icon: item.icon,
          desc: `Saved to governance_rules/${category}/. These documents now govern all LLM behavior — injected into every system prompt as mandatory rules.`,
          data: { files: results, category, total: results.length, succeeded: results.filter(r => r.status.includes("uploaded")).length },
        });
      };
      input.click();
      return;
    }

    // Dev instruction (free text → governance rule)
    if (item.special === "dev_instruction") {
      const instruction = prompt("Enter instruction for Grace to follow:\n\nExamples:\n- Use TypeScript strict mode\n- Follow PEP 8 coding standards\n- All API responses must include a 'status' field\n- Use PostgreSQL syntax, not MySQL");
      if (!instruction) return;
      setLoading(p => ({ ...p, [item.id]: true }));
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, "");
      const r = await brainCall("files", "create", {
        path: `governance_rules/instructions/dev_${timestamp}.txt`,
        content: `# Dev Instruction\n# Created: ${new Date().toISOString()}\n# Source: Dev Tab manual entry\n\n${instruction}`,
        directory: "governance_rules/instructions",
      });
      setLoading(p => ({ ...p, [item.id]: false }));
      onDetail({
        title: "Instruction Saved",
        icon: "📝",
        desc: "This instruction is now active. Grace will follow it in all future code generation and responses.",
        data: r.ok ? { saved: true, instruction, active: true } : { error: r.error },
      });
      return;
    }

    // Frontend live preview
    if (item.special === "frontend_preview") {
      onDetail({
        title: "Frontend Preview", icon: "🖥️",
        desc: "Live iframe of the running frontend. Interact with it to test changes.",
        data: { _special: "preview" },
      });
      return;
    }

    // Pipeline Workflow View
    if (item.special === "show_pipeline") {
      onDetail({
        title: "8-Layer Coding Pipeline", icon: "🏗️",
        desc: "This is the LAW that governs how ALL models produce code. No model can skip layers. No layer passes without 100% completion.",
        data: {
          pipeline: [
            { layer: 1, name: "Runtime Environment", brains: ["system/health", "system/connectivity", "govern/rules", "ai/knowledge_gaps"], trust_required: 0.6 },
            { layer: 2, name: "Task Decomposition", brains: ["files/search", "ai/fast"], trust_required: 0.6 },
            { layer: 3, name: "Solution Proposal", brains: ["govern/rules", "files/search", "ai/fast(kimi+opus)"], trust_required: 0.6, parallel: true },
            { layer: 4, name: "Solution Selection", brains: ["system/trust", "ai/bandit_select", "ai/dl_predict"], trust_required: 0.6, parallel: true },
            { layer: 5, name: "Simulation & Reasoning", brains: ["ai/dl_predict", "ai/cognitive_report"], trust_required: 0.6 },
            { layer: 6, name: "Code Generation", brains: ["govern/persona", "files/search", "code/generate"], trust_required: 0.7 },
            { layer: 7, name: "Verification & Testing", brains: ["ai/invariants", "system/probe", "system/triggers", "ai/cognitive_report"], trust_required: 0.8 },
            { layer: 8, name: "Deployment Gate", brains: ["govern/approvals", "system/trust", "system/auto_cycle"], trust_required: 0.9, requires_human: true },
          ],
          cross_cutting: ["Genesis Key tracking", "Trust Score at every layer", "Self-Mirror observation", "TimeSense awareness", "LLM Reasoning (OODA)", "Probe verification", "Activity tracking"],
          total_brain_calls: 24,
        },
      });
      return;
    }

    // API Client
    if (item.special === "api_client") {
      const url = prompt("URL (e.g. http://localhost:8000/health):");
      if (!url) return;
      setLoading(p => ({ ...p, [item.id]: true }));
      try {
        const start = performance.now();
        const resp = await fetch(url);
        const latency = Math.round(performance.now() - start);
        const body = await resp.text();
        let parsed;
        try { parsed = JSON.parse(body); } catch { parsed = body; }
        setLoading(p => ({ ...p, [item.id]: false }));
        onDetail({ title: `${resp.status} ${url}`, icon: "🌐", desc: `${resp.status} in ${latency}ms`,
          data: { status: resp.status, latency_ms: latency, headers: Object.fromEntries(resp.headers.entries()), body: parsed } });
      } catch (e) {
        setLoading(p => ({ ...p, [item.id]: false }));
        onDetail({ title: "Request Failed", icon: "🌐", data: { error: e.message, url } });
      }
      return;
    }

    // Drawing/Whiteboard
    if (item.special === "drawing") {
      onDetail({
        title: "Whiteboard", icon: "🎨",
        desc: "Draw system diagrams. Click and drag to draw. Right-click to add text. Export button saves as PNG.",
        data: { _special: "canvas" },
      });
      return;
    }

    // Custom Action Builder
    if (item.special === "custom_action") {
      const name = prompt("Action name:");
      if (!name) return;
      const brain = prompt("Brain domain (chat/files/govern/ai/system/data/tasks/code):");
      if (!brain) return;
      const action = prompt("Action name in that brain:");
      if (!action) return;
      const newAction = { id: `custom_${Date.now()}`, label: name, icon: "⚡", brain, action, desc: `Custom action: ${brain}/${action}. User-created.` };
      const saved = JSON.parse(localStorage.getItem("grace_custom_actions") || "[]");
      saved.push(newAction);
      localStorage.setItem("grace_custom_actions", JSON.stringify(saved));
      onDetail({ title: "Action Created", icon: "➕", data: { saved: true, name, brain, action, total_custom: saved.length } });
      return;
    }

    // Actions that need user input first
    if (item.special === "search_prompt") {
      const query = prompt("Search codebase for:");
      if (!query) return;
      item = { ...item, payload: { query } };
    }
    if (item.special === "generate_prompt") {
      const p = prompt("Describe what code to generate:");
      if (!p) return;
      item = { ...item, payload: { prompt: p, project_folder: "." } };
    }
    if (item.special === "create_project_prompt") {
      const name = prompt("Project name (e.g. Tim-AI, Green-Gardens):");
      if (!name) return;
      const desc = prompt("Brief description (optional):");
      item = { ...item, payload: { name, description: desc || "" } };
    }
    if (item.special === "create_prompt") {
      const path = prompt("File path (e.g. core/services/new_service.py):");
      if (!path) return;
      item = { ...item, payload: { path, content: "" } };
    }

    setLoading(p => ({ ...p, [item.id]: true }));
    let data;
    if (item.special === "frontend_tree") {
      data = await brainCall("files", "tree", { path: "../frontend/src" });
    } else {
      data = await brainCall(item.brain, item.action, item.payload || {});
    }
    setLoading(p => ({ ...p, [item.id]: false }));
    const result = { title: item.label, icon: item.icon, desc: item.desc, data: data.ok ? data.data : { error: data.error } };
    setLastResults(p => ({ ...p, [item.id]: result }));
    onDetail(result);
  };

  const handleContextMenu = (e, item, section) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, item, section });
  };

  const handleContextAction = async (menuItem) => {
    const item = contextMenu?.item;
    setContextMenu(null);
    if (!item) return;

    if (menuItem.id === "rerun") { run(item); return; }
    if (menuItem.id === "copy") {
      const last = lastResults[item.id];
      if (last) navigator.clipboard?.writeText(JSON.stringify(last.data, null, 2));
      return;
    }
    if (menuItem.id === "export") {
      const last = lastResults[item.id];
      if (last) {
        const blob = new Blob([JSON.stringify(last.data, null, 2)], { type: "application/json" });
        const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
        a.download = `${item.id}_${Date.now()}.json`; a.click();
      }
      return;
    }
    if (menuItem.id === "logs") {
      const r = await brainCall("system", "traces", {});
      onDetail({ title: `Logs: ${item.label}`, icon: "📋", desc: "Last 100 trace entries from the lightweight ring buffer.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "genesis_history") {
      const r = await brainCall("govern", "genesis_keys", { limit: 50 });
      onDetail({ title: `Genesis History: ${item.label}`, icon: "🔑", desc: "Recent Genesis keys related to this action.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "gc") {
      await brainCall("system", "hot_reload", {});
      onDetail({ title: "GC Complete", icon: "♻️", data: { status: "garbage collected" } });
      return;
    }
    if (menuItem.id === "run_tests") {
      const r = await brainCall("ai", "logic_tests", {});
      onDetail({ title: "Test Results", icon: "🧪", desc: "Logic test suite output.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "force_heal") {
      const r = await brainCall("system", "scan_heal", {});
      onDetail({ title: "Force Heal", icon: "💊", desc: "Triggered scan + auto-heal pipeline.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "pause_loop") {
      await brainCall("system", "pause", {});
      onDetail({ title: "Loop Paused", icon: "⏸️", data: { status: "paused" } });
      return;
    }
    if (menuItem.id === "resume_loop") {
      await brainCall("system", "resume", {});
      onDetail({ title: "Loop Resumed", icon: "▶️", data: { status: "resumed" } });
      return;
    }
    if (menuItem.id === "suggest_fix") {
      const err = prompt("Paste the error or describe what's broken:");
      if (!err) return;
      const r = await brainCall("ai", "fast", { prompt: `Fix this error in Grace: ${err}. Propose a specific code fix.`, models: ["kimi", "opus"] });
      onDetail({ title: "AI Fix Suggestion", icon: "🔧", desc: "Consensus fix proposal from all models.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "explain") {
      const file = prompt("File path to explain:");
      if (!file) return;
      const content = await brainCall("code", "read", { path: file });
      if (content.ok) {
        const r = await brainCall("ai", "fast", { prompt: `Explain this code in plain English:\n\n${(content.data?.content || "").slice(0, 2000)}`, models: ["kimi"] });
        onDetail({ title: `Explain: ${file}`, icon: "💡", desc: "AI plain-English explanation.", data: r.ok ? r.data : { error: r.error } });
      }
      return;
    }
    if (menuItem.id === "file_history") {
      const r = await brainCall("govern", "genesis_keys", { limit: 30 });
      onDetail({ title: "File History", icon: "📜", desc: "Genesis key changes for files.", data: r.ok ? r.data : { error: r.error } });
      return;
    }
    if (menuItem.id === "stress10") {
      const results = [];
      for (let i = 0; i < 10; i++) {
        const r = await brainCall("system", "probe", {});
        results.push({ run: i + 1, ok: r.ok });
      }
      onDetail({ title: "Stress x10 Results", icon: "⚡", desc: "10 parallel probe runs.", data: results });
      return;
    }
    if (menuItem.id === "baseline") {
      const last = lastResults[item.id];
      if (last) localStorage.setItem(`baseline_${item.id}`, JSON.stringify(last.data));
      onDetail({ title: "Baseline Saved", icon: "📌", data: { saved: true, action: item.id } });
      return;
    }
    if (menuItem.id === "compare") {
      const baseline = localStorage.getItem(`baseline_${item.id}`);
      const current = lastResults[item.id]?.data;
      onDetail({ title: "Compare", icon: "🔄", desc: "Current vs baseline.", data: { baseline: baseline ? JSON.parse(baseline) : "No baseline saved", current: current || "No current result" } });
      return;
    }
    // Default: just run the parent action
    run(item);
  };

  return (
    <div style={{ width: width, borderRight: "1px solid #1a1a2e", overflow: "auto", flexShrink: 0 }}
         onClick={() => setContextMenu(null)}>
      {[...ACTIONS, ...(getCustomActions().length ? [{ section: "Custom", items: getCustomActions() }] : [])].map(section => (
        <div key={section.section}>
          <div style={{ padding: "8px 12px 3px", fontSize: 9, fontWeight: 800, color: "#555", textTransform: "uppercase", letterSpacing: 1 }}>
            {section.section}
          </div>
          {section.items.map(item => (
            <div key={item.id} style={{ position: "relative" }}>
              <button
                onClick={() => run(item)}
                onDoubleClick={() => { run(item); setFullWindow(item); }}
                onContextMenu={(e) => handleContextMenu(e, item, section.section)}
                onMouseEnter={() => setHoveredId(item.id)}
                onMouseLeave={() => setHoveredId(null)}
                disabled={loading[item.id]}
                style={{
                  display: "flex", alignItems: "center", gap: 6, width: "100%",
                  padding: "5px 12px", border: "none", background: "transparent",
                  color: loading[item.id] ? "#e94560" : "#888", cursor: "pointer",
                  fontSize: 11, textAlign: "left",
                }}
              >
                <span style={{ fontSize: 12 }}>{item.icon}</span>
                {loading[item.id] ? "Running..." : item.label}
              </button>
              {hoveredId === item.id && !contextMenu && (
                <div style={{
                  position: "absolute", left: 195, top: 0, width: 260, padding: 8,
                  background: "#12122a", border: "1px solid #333", borderRadius: 6,
                  fontSize: 10, color: "#aaa", lineHeight: 1.4, zIndex: 100,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.5)", pointerEvents: "none",
                }}>
                  <strong style={{ color: "#e94560" }}>{item.label}</strong><br />{item.desc}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}

      {/* Context Menu */}
      {contextMenu && (
        <div style={{
          position: "fixed", left: contextMenu.x, top: contextMenu.y,
          background: "#12122a", border: "1px solid #333", borderRadius: 8,
          padding: "4px 0", zIndex: 1000, minWidth: 200,
          boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        }} onClick={e => e.stopPropagation()}>
          <div style={{ padding: "4px 12px", fontSize: 10, color: "#e94560", fontWeight: 700, borderBottom: "1px solid #222" }}>
            {contextMenu.item.icon} {contextMenu.item.label}
          </div>
          {(SECTION_MENU[contextMenu.section] || []).map(m => (
            <CtxMenuItem key={m.id} item={m} onClick={() => handleContextAction(m)} />
          ))}
          <div style={{ borderTop: "1px solid #222", margin: "2px 0" }} />
          {UNIVERSAL_MENU.map(m => (
            <CtxMenuItem key={m.id} item={m} onClick={() => handleContextAction(m)} />
          ))}
        </div>
      )}

      {/* Full Window Overlay */}
      {fullWindow && lastResults[fullWindow.id] && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", zIndex: 900,
          display: "flex", alignItems: "center", justifyContent: "center",
        }} onClick={() => setFullWindow(null)}>
          <div style={{
            width: "85%", height: "85%", background: "#0a0a1a", border: "1px solid #333",
            borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column",
          }} onClick={e => e.stopPropagation()}>
            <div style={{ padding: "10px 16px", borderBottom: "1px solid #222", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 14, fontWeight: 700 }}>{fullWindow.icon} {fullWindow.label}</span>
              <button onClick={() => setFullWindow(null)} style={{ background: "none", border: "none", color: "#888", cursor: "pointer", fontSize: 18 }}>×</button>
            </div>
            <div style={{ padding: "8px 16px", borderBottom: "1px solid #111", fontSize: 11, color: "#666" }}>
              {fullWindow.desc}
            </div>
            <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
              <pre style={{ fontSize: 11, color: "#aaa", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, lineHeight: 1.6 }}>
                {JSON.stringify(lastResults[fullWindow.id]?.data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CodeEditor({ filePath, initialContent, onSave }) {
  const [content, setContent] = useState(initialContent || "");
  const [saved, setSaved] = useState(false);
  const [ghost, setGhost] = useState("");
  const [showCmdK, setShowCmdK] = useState(false);
  const [cmdKInput, setCmdKInput] = useState("");
  const textareaRef = useRef(null);

  const save = async () => {
    const { brainCall } = await import("../api/brain-client");
    const r = await brainCall("code", "write", { path: filePath, content });
    setSaved(r.ok);
    if (onSave) onSave(r);
    await brainCall("system", "hot_reload_service", { service: "code" });
  };

  // Tab autocomplete — request completion after pause
  const requestCompletion = async (cursorPos) => {
    try {
      const before = content.substring(0, cursorPos);
      const after = content.substring(cursorPos);
      const { brainCall } = await import("../api/brain-client");
      const r = await brainCall("code", "generate", {
        prompt: `Complete this code. Return ONLY the next 1-3 lines:\n\n${before.slice(-500)}`,
        project_folder: ".",
      });
      if (r.ok && r.data?.code) {
        const completion = r.data.code.replace(/^```[\w]*\n?/, "").replace(/\n?```$/, "").trim();
        if (completion && completion.length < 200) {
          setGhost(completion);
        }
      }
    } catch {}
  };

  // Cmd+K refactor
  const handleCmdK = async () => {
    if (!cmdKInput.trim()) return;
    const { brainCall } = await import("../api/brain-client");
    const r = await brainCall("code", "generate", {
      prompt: `Refactor this code according to: "${cmdKInput}"\n\nOriginal:\n${content.slice(0, 3000)}`,
      project_folder: ".",
    });
    if (r.ok && r.data?.code) {
      const newCode = r.data.code.replace(/^```[\w]*\n?/, "").replace(/\n?```$/, "").trim();
      if (newCode) setContent(newCode);
    }
    setShowCmdK(false);
    setCmdKInput("");
  };

  const lang = filePath?.split(".").pop() || "txt";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", gap: 4, marginBottom: 4, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 10, color: "#888", flex: 1 }}>{filePath} ({lang})</span>
        <button onClick={save} style={{ padding: "2px 8px", background: "#10b981", border: "none", borderRadius: 3, color: "#fff", fontSize: 10, cursor: "pointer" }}>
          {saved ? "Saved ✓" : "Save + Reload"}
        </button>
        <button onClick={() => setShowCmdK(true)} style={{ padding: "2px 8px", background: "#2563eb", border: "none", borderRadius: 3, color: "#fff", fontSize: 10, cursor: "pointer" }}>
          ⌘K Refactor
        </button>
      </div>

      {showCmdK && (
        <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
          <input value={cmdKInput} onChange={e => setCmdKInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCmdK()}
            placeholder="Describe refactoring (e.g. 'add error handling', 'convert to TypeScript')"
            autoFocus
            style={{ flex: 1, padding: "4px 8px", background: "#12122a", border: "1px solid #2563eb", borderRadius: 3, color: "#ccc", fontSize: 11, outline: "none" }}
          />
          <button onClick={handleCmdK} style={{ padding: "2px 8px", background: "#2563eb", border: "none", borderRadius: 3, color: "#fff", fontSize: 10, cursor: "pointer" }}>Apply</button>
          <button onClick={() => setShowCmdK(false)} style={{ padding: "2px 8px", background: "#333", border: "none", borderRadius: 3, color: "#888", fontSize: 10, cursor: "pointer" }}>Cancel</button>
        </div>
      )}

      {ghost && (
        <div style={{ fontSize: 10, color: "#555", padding: "2px 8px", background: "#0d0d15", borderRadius: 3, marginBottom: 2, fontFamily: "monospace" }}>
          Ghost: <span style={{ color: "#4caf5066" }}>{ghost}</span>
          <button onClick={() => { setContent(c => c + ghost); setGhost(""); }} style={{ marginLeft: 8, padding: "1px 6px", background: "#10b981", border: "none", borderRadius: 2, color: "#fff", fontSize: 9, cursor: "pointer" }}>Tab ↹ Accept</button>
          <button onClick={() => setGhost("")} style={{ marginLeft: 4, padding: "1px 6px", background: "#333", border: "none", borderRadius: 2, color: "#888", fontSize: 9, cursor: "pointer" }}>Esc</button>
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={content}
        onChange={e => { setContent(e.target.value); setSaved(false); setGhost(""); }}
        spellCheck={false}
        style={{
          flex: 1, width: "100%", background: "#0d0d20", color: "#e0e0e0",
          border: "1px solid #222", borderRadius: 4, padding: 8,
          fontFamily: "monospace", fontSize: 12, lineHeight: 1.5,
          resize: "none", outline: "none", tabSize: 2,
        }}
        onKeyDown={e => {
          if (e.key === "Tab" && ghost) {
            e.preventDefault();
            setContent(c => c + ghost);
            setGhost("");
            return;
          }
          if (e.key === "Tab" && !ghost) {
            e.preventDefault();
            const start = e.target.selectionStart;
            const end = e.target.selectionEnd;
            setContent(content.substring(0, start) + "  " + content.substring(end));
            setTimeout(() => { e.target.selectionStart = e.target.selectionEnd = start + 2; }, 0);
          }
          if (e.key === "Escape") { setGhost(""); setShowCmdK(false); }
          if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); }
          if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setShowCmdK(true); }
        }}
        onKeyUp={e => {
          // Request completion after typing pause
          if (!ghost && e.key !== "Escape" && e.key !== "Tab" && content.length > 10) {
            const pos = e.target.selectionStart;
            clearTimeout(window._graceCompletionTimer);
            window._graceCompletionTimer = setTimeout(() => requestCompletion(pos), 1500);
          }
        }}
      />
    </div>
  );
}

function DiffViewer({ original, modified, fileName }) {
  const origLines = (original || "").split("\n");
  const modLines = (modified || "").split("\n");
  const maxLines = Math.max(origLines.length, modLines.length);

  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>{fileName || "Diff View"}</div>
      <div style={{ display: "flex", gap: 2, fontSize: 10, fontFamily: "monospace", maxHeight: 400, overflow: "auto" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 9, color: "#f44336", marginBottom: 2 }}>Original</div>
          {origLines.map((line, i) => (
            <div key={i} style={{
              padding: "1px 4px", background: modLines[i] !== line ? "#2a1515" : "transparent",
              color: modLines[i] !== line ? "#f44336" : "#888", whiteSpace: "pre",
            }}>{line}</div>
          ))}
        </div>
        <div style={{ width: 1, background: "#333" }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 9, color: "#4caf50", marginBottom: 2 }}>Modified</div>
          {modLines.map((line, i) => (
            <div key={i} style={{
              padding: "1px 4px", background: origLines[i] !== line ? "#152a15" : "transparent",
              color: origLines[i] !== line ? "#4caf50" : "#888", whiteSpace: "pre",
            }}>{line}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DrawingCanvas() {
  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0a0a1a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#e94560";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    let isDrawing = false;
    const start = (e) => { isDrawing = true; ctx.beginPath(); ctx.moveTo(e.offsetX, e.offsetY); };
    const draw = (e) => { if (!isDrawing) return; ctx.lineTo(e.offsetX, e.offsetY); ctx.stroke(); };
    const stop = () => { isDrawing = false; };

    canvas.addEventListener("mousedown", start);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", stop);
    canvas.addEventListener("mouseleave", stop);

    return () => {
      canvas.removeEventListener("mousedown", start);
      canvas.removeEventListener("mousemove", draw);
      canvas.removeEventListener("mouseup", stop);
      canvas.removeEventListener("mouseleave", stop);
    };
  }, []);

  const exportPNG = () => {
    const canvas = canvasRef.current;
    const link = document.createElement("a");
    link.download = `grace_diagram_${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  const clear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0a0a1a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
        <button onClick={exportPNG} style={{ padding: "3px 8px", background: "#2563eb", border: "none", borderRadius: 4, color: "#fff", fontSize: 10, cursor: "pointer" }}>Export PNG</button>
        <button onClick={clear} style={{ padding: "3px 8px", background: "#333", border: "none", borderRadius: 4, color: "#aaa", fontSize: 10, cursor: "pointer" }}>Clear</button>
        <select onChange={(e) => {
          const canvas = canvasRef.current;
          canvas.getContext("2d").strokeStyle = e.target.value;
        }} style={{ padding: "2px 4px", background: "#12122a", border: "1px solid #333", borderRadius: 4, color: "#ccc", fontSize: 10 }}>
          <option value="#e94560">Red</option>
          <option value="#4caf50">Green</option>
          <option value="#2563eb">Blue</option>
          <option value="#f59e0b">Yellow</option>
          <option value="#ffffff">White</option>
        </select>
      </div>
      <canvas ref={canvasRef} width={280} height={400} style={{ border: "1px solid #222", borderRadius: 4, cursor: "crosshair" }} />
    </div>
  );
}

function CtxMenuItem({ item, onClick }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div style={{ position: "relative" }}
         onMouseEnter={() => setHovered(true)}
         onMouseLeave={() => setHovered(false)}>
      <button onClick={onClick} style={{
        display: "flex", alignItems: "center", gap: 6, width: "100%",
        padding: "5px 12px", border: "none",
        background: hovered ? "#1a1a3a" : "transparent",
        color: "#aaa", cursor: "pointer", fontSize: 11, textAlign: "left",
      }}>
        <span>{item.icon}</span> {item.label}
      </button>
      {hovered && item.desc && (
        <div style={{
          position: "absolute", left: "100%", top: 0, marginLeft: 4,
          width: 240, padding: 8, background: "#12122a", border: "1px solid #333",
          borderRadius: 6, fontSize: 10, color: "#aaa", lineHeight: 1.4, zIndex: 1001,
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)", pointerEvents: "none",
        }}>
          {item.desc}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   CENTER — Consensus Chat
   Chat with all LLM models. They see system state, source code,
   and Genesis keys. Connected to the full brain API pipeline.
   ═══════════════════════════════════════════════════════════════════ */

function CenterChat({ onDetail, onToggleLeft, onToggleRight, activeProject, setActiveProject }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("consensus");
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    brainCall("ai", "models", {}).then(r => {
      if (r.ok && r.data?.models) setModels(r.data.models);
    });
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const rawInput = input;
    setMessages(p => [...p, { role: "user", content: rawInput, ts: Date.now() }]);
    setInput("");
    setLoading(true);

    // Parse @ mentions
    const { parseMentions } = await import("../api/stream");
    const { cleanText, mentions } = parseMentions(rawInput);

    // Try streaming first
    try {
      const { streamChat } = await import("../api/stream");
      const streamModel = model === "consensus" ? "kimi" : model;

      let tokens = "";
      const msgIdx = { current: -1 };

      // Add placeholder message
      setMessages(p => {
        msgIdx.current = p.length;
        return [...p, { role: "assistant", model: streamModel, content: "▌", streaming: true, ts: Date.now() }];
      });

      await streamChat(
        cleanText || rawInput,
        streamModel,
        mentions,
        (token) => {
          tokens += token;
          setMessages(p => {
            const updated = [...p];
            if (msgIdx.current >= 0 && updated[msgIdx.current]) {
              updated[msgIdx.current] = { ...updated[msgIdx.current], content: tokens + "▌" };
            }
            return updated;
          });
        },
        () => {
          setMessages(p => {
            const updated = [...p];
            if (msgIdx.current >= 0 && updated[msgIdx.current]) {
              updated[msgIdx.current] = { ...updated[msgIdx.current], content: tokens, streaming: false };
            }
            return updated;
          });
          setLoading(false);
        },
        (err) => {
          // Fallback to batch if streaming fails
          fallbackBatch(cleanText || rawInput, mentions);
        }
      );
    } catch {
      fallbackBatch(cleanText || rawInput, mentions);
    }
  };

  const fallbackBatch = async (query, mentions) => {
    try {
      const mods = model === "consensus" ? ["kimi", "opus"] : [model];
      const data = await brainCall("ai", "fast", { prompt: query, models: mods });
      const d = data.data || data;
      setMessages(p => [...p, {
        role: "assistant",
        model: model === "consensus" ? "Consensus" : model,
        content: d.individual_responses?.[0]?.response || d.final_output || d.error || "No response",
        individual: d.individual_responses,
        ts: Date.now(),
      }]);
    } catch (e) {
      setMessages(p => [...p, { role: "error", content: e.message, ts: Date.now() }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #1a1a2e" }}>
      <div style={{ padding: "6px 12px", borderBottom: "1px solid #1a1a2e", display: "flex", alignItems: "center", gap: 8 }}>
        {onToggleLeft && <button onClick={onToggleLeft} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 12 }}>☰</button>}
        <span style={{ fontSize: 13, fontWeight: 700, color: "#e94560" }}>Dev Console</span>
        <select value={model} onChange={e => setModel(e.target.value)} style={{
          background: "#12122a", border: "1px solid #333", borderRadius: 4,
          color: "#ccc", padding: "2px 6px", fontSize: 10, outline: "none",
        }}>
          <option value="consensus">All Models</option>
          {models.map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        {onToggleRight && <button onClick={onToggleRight} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 12 }}>◧</button>}
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "8px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        {messages.length === 0 && (
          <div style={{ color: "#444", fontSize: 12, padding: 20, textAlign: "center" }}>
            Talk to Grace. All models see system state and source code.<br />
            Ask about errors, architecture, or run diagnostics.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} onClick={() => m.individual && onDetail({
            title: "Individual Responses", icon: "🤖",
            desc: "Each model's independent response before consensus synthesis.",
            data: m.individual,
          })} style={{
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%", padding: "8px 12px", borderRadius: 8,
            background: m.role === "user" ? "#1a2a4a" : m.role === "error" ? "#2a1515" : "#12122a",
            cursor: m.individual ? "pointer" : "default", fontSize: 12,
          }}>
            {m.model && <div style={{ fontSize: 9, color: "#e94560", fontWeight: 700, marginBottom: 2 }}>{m.model}</div>}
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{m.content}</div>
            {m.individual?.length > 1 && <div style={{ fontSize: 9, color: "#e94560", marginTop: 2 }}>Click for individual responses →</div>}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div style={{ padding: "8px 12px", borderTop: "1px solid #1a1a2e", display: "flex", gap: 6 }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask Grace... Use @file.py to include context"
          style={{ flex: 1, padding: "8px 10px", background: "#12122a", border: "1px solid #222", borderRadius: 6, color: "#ccc", fontSize: 12, outline: "none" }}
          disabled={loading} />
        <button onClick={send} disabled={loading} style={{
          padding: "6px 14px", background: "#e94560", border: "none", borderRadius: 6,
          color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer", opacity: loading ? 0.5 : 1,
        }}>{loading ? "..." : "Send"}</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   RIGHT PANEL — Detail View
   Shows results from actions and chat clicks. Renders JSON data,
   individual model responses, file trees, and error details.
   ═══════════════════════════════════════════════════════════════════ */

function RightDetail({ content, onClose, width = 320 }) {
  if (!content) {
    return (
      <div style={{ width: 260, background: "#08081a", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
        <div style={{ color: "#333", fontSize: 11, textAlign: "center" }}>
          Click any action button<br />or chat response to<br />view details here
        </div>
      </div>
    );
  }

  const isArray = Array.isArray(content.data);
  const isTree = content.data?.children || content.data?.type === "directory";

  return (
    <div style={{ width: width, background: "#08081a", borderLeft: "1px solid #1a1a2e", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "6px 12px", borderBottom: "1px solid #1a1a2e", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700 }}>{content.icon} {content.title}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 16 }}>×</button>
      </div>

      {content.desc && (
        <div style={{ padding: "6px 12px", borderBottom: "1px solid #111", fontSize: 10, color: "#666", lineHeight: 1.5 }}>
          {content.desc}
        </div>
      )}

      <div style={{ flex: 1, overflow: "auto", padding: 10 }}>
        {isArray ? (
          content.data.map((r, i) => (
            <div key={i} style={{ marginBottom: 8, padding: 8, background: "#0d0d20", borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: "#e94560", fontWeight: 700 }}>{r.model_name || r.model_id || `Item ${i}`}</div>
              {r.error && <div style={{ fontSize: 10, color: "#f44336" }}>{r.error}</div>}
              <div style={{ fontSize: 11, color: "#aaa", marginTop: 4, whiteSpace: "pre-wrap" }}>{(r.response || JSON.stringify(r, null, 2)).slice(0, 600)}</div>
            </div>
          ))
        ) : content.data?._special === "preview" ? (
          <div style={{ height: "100%" }}>
            <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>Live frontend — interact to test</div>
            <iframe
              src="http://localhost:5173"
              style={{ width: "100%", height: "calc(100% - 20px)", border: "1px solid #222", borderRadius: 4, background: "#fff" }}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              title="Frontend Preview"
            />
          </div>
        ) : content.data?._special === "editor" ? (
          <CodeEditor filePath={content.data.path} initialContent={content.data.content} />
        ) : content.data?._special === "diff" ? (
          <DiffViewer original={content.data.original} modified={content.data.modified} fileName={content.data.fileName} />
        ) : isTree ? (
          <FileTree node={content.data} onOpenFile={async (path) => {
            const { brainCall } = await import("../api/brain-client");
            const r = await brainCall("code", "read", { path });
            if (r.ok && r.data?.content != null) {
              onClose();
              setTimeout(() => {
                // Re-open with editor
                const event = new CustomEvent("grace-open-editor", { detail: { path, content: r.data.content } });
                window.dispatchEvent(event);
              }, 50);
            }
          }} />
        ) : content.data?._special === "canvas" ? (
          <DrawingCanvas />
        ) : content.data?.error ? (
          <div style={{ color: "#f44336", fontSize: 12, padding: 8, background: "#2a1515", borderRadius: 6 }}>
            {typeof content.data.error === "string" ? content.data.error : JSON.stringify(content.data.error)}
          </div>
        ) : (
          <pre style={{ fontSize: 10, color: "#aaa", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, lineHeight: 1.6 }}>
            {JSON.stringify(content.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

/* ── File Tree Renderer ───────────────────────────────────────── */

function FileTree({ node, depth = 0, onOpenFile }) {
  const [open, setOpen] = useState(depth < 2);
  if (!node) return null;

  const isDir = node.type === "directory" || node.children;

  const handleClick = async () => {
    if (isDir) {
      setOpen(p => !p);
    } else if (onOpenFile) {
      onOpenFile(node.path || node.name);
    }
  };

  return (
    <div style={{ marginLeft: depth * 12 }}>
      <div onClick={handleClick} style={{
        padding: "2px 4px", cursor: "pointer",
        fontSize: 11, color: isDir ? "#ccc" : "#888",
        display: "flex", alignItems: "center", gap: 4,
      }}
      onMouseEnter={e => !isDir && (e.target.style.color = "#e94560")}
      onMouseLeave={e => !isDir && (e.target.style.color = "#888")}
      >
        <span style={{ fontSize: 10, width: 12 }}>{isDir ? (open ? "📂" : "📁") : "📄"}</span>
        {node.name}
        {!isDir && node.size != null && <span style={{ fontSize: 9, color: "#444", marginLeft: 4 }}>{(node.size / 1024).toFixed(1)}kb</span>}
      </div>
      {open && node.children?.map((child, i) => (
        <FileTree key={i} node={child} depth={depth + 1} onOpenFile={onOpenFile} />
      ))}
    </div>
  );
}
