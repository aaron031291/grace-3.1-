import { useState, useEffect, useRef } from "react";
import { brainCall } from "../api/brain-client";

export default function DevTab() {
  const [detail, setDetail] = useState(null);

  return (
    <div style={{ display: "flex", height: "100%", background: "#0a0a1a", color: "#ccc" }}>
      <LeftPanel onDetail={setDetail} />
      <CenterChat onDetail={setDetail} />
      <RightDetail content={detail} onClose={() => setDetail(null)} />
    </div>
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
    section: "Code",
    items: [
      {
        id: "backend_tree", label: "Backend Files", icon: "🐍",
        brain: "code", action: "tree",
        payload: { folder: "." },
        desc: "Shows the backend file tree. This mirrors the actual Python source code structure. You can browse, read, and write files through the code brain. Connects to: core/services/code_service.py → knowledge_base file system.",
      },
      {
        id: "frontend_tree", label: "Frontend Files", icon: "⚛️",
        special: "frontend_tree",
        desc: "Shows the frontend file tree (React/Vite). Browse the src/ components, hooks, and config. Connects to: core/services/files_service.py → frontend/src/ directory.",
      },
      {
        id: "cicd", label: "CI/CD Pipeline", icon: "🚀",
        brain: "system", action: "diagnostics",
        desc: "Grace's native CI/CD: runs lint, tests, and builds on code changes. Auto-triggered by Genesis key code_change events via the auto-probe system. Shows last pipeline status, pass/fail, and deployment readiness. Connects to: auto_probe → test_grace_system.py → GitHub Actions CI.",
      },
    ],
  },
  {
    section: "Autonomous",
    items: [
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
  ],
  Autonomous: [
    { label: "Force Heal", id: "force_heal", icon: "💊", desc: "Immediately runs the scan-and-heal pipeline: scans all triggers, checks component health, and auto-executes safe healing actions (DB reconnect, GC, diagnostic cycle)." },
    { label: "Pause Loop", id: "pause_loop", icon: "⏸️", desc: "Pauses the Ouroboros autonomous loop. The 30s cycle stops running, but all API endpoints stay available. Self-healing and auto-probe are suspended." },
    { label: "Resume Loop", id: "resume_loop", icon: "▶️", desc: "Resumes the Ouroboros autonomous loop after being paused. The 30s cycle restarts with trust gates, TimeSense, mirror, and episodic recall." },
  ],
};


function LeftPanel({ onDetail }) {
  const [loading, setLoading] = useState({});
  const [hoveredId, setHoveredId] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [fullWindow, setFullWindow] = useState(null);
  const [lastResults, setLastResults] = useState({});

  const run = async (item) => {
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
    // Default: just run the parent action
    run(item);
  };

  return (
    <div style={{ width: 190, borderRight: "1px solid #1a1a2e", overflow: "auto", flexShrink: 0 }}
         onClick={() => setContextMenu(null)}>
      {ACTIONS.map(section => (
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

function CenterChat({ onDetail }) {
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
    setMessages(p => [...p, { role: "user", content: input, ts: Date.now() }]);
    const query = input;
    setInput("");
    setLoading(true);

    try {
      const mods = model === "consensus" ? ["kimi", "opus"] : [model];
      const data = await brainCall("ai", "fast", { prompt: query, models: mods });
      const d = data.data || data;
      setMessages(p => [...p, {
        role: "assistant",
        model: model === "consensus" ? "Consensus" : model,
        content: d.individual_responses?.[0]?.response || d.final_output || d.error || "No response",
        individual: d.individual_responses,
        confidence: d.confidence,
        models_used: d.models_used,
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
        <span style={{ fontSize: 13, fontWeight: 700, color: "#e94560" }}>Dev Console</span>
        <select value={model} onChange={e => setModel(e.target.value)} style={{
          background: "#12122a", border: "1px solid #333", borderRadius: 4,
          color: "#ccc", padding: "2px 6px", fontSize: 10, outline: "none",
        }}>
          <option value="consensus">All Models</option>
          {models.map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}</option>)}
        </select>
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
          placeholder="Ask about errors, architecture, run diagnostics..."
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

function RightDetail({ content, onClose }) {
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
    <div style={{ width: 320, background: "#08081a", borderLeft: "1px solid #1a1a2e", display: "flex", flexDirection: "column" }}>
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
        ) : isTree ? (
          <FileTree node={content.data} />
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

function FileTree({ node, depth = 0 }) {
  const [open, setOpen] = useState(depth < 2);
  if (!node) return null;

  const isDir = node.type === "directory" || node.children;

  return (
    <div style={{ marginLeft: depth * 12 }}>
      <div onClick={() => isDir && setOpen(p => !p)} style={{
        padding: "2px 4px", cursor: isDir ? "pointer" : "default",
        fontSize: 11, color: isDir ? "#ccc" : "#888",
        display: "flex", alignItems: "center", gap: 4,
      }}>
        <span style={{ fontSize: 10, width: 12 }}>{isDir ? (open ? "📂" : "📁") : "📄"}</span>
        {node.name}
        {!isDir && node.size != null && <span style={{ fontSize: 9, color: "#444", marginLeft: 4 }}>{(node.size / 1024).toFixed(1)}kb</span>}
      </div>
      {open && node.children?.map((child, i) => (
        <FileTree key={i} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}
