import { useState, useEffect, lazy, Suspense } from "react";
import "./App.css";
import { healthCheck, brainCall, brainDirectory } from "./api/brain-client";

// Lazy-load tab content to speed up initial load (H1)
const ChatTab = lazy(() => import("./components/ChatTab"));
const FoldersTab = lazy(() => import("./components/FoldersTab"));
const DocsTab = lazy(() => import("./components/DocsTab"));
const GovernanceTab = lazy(() => import("./components/GovernanceTab"));
const CodebaseTab = lazy(() => import("./components/CodebaseTab"));
const TasksTab = lazy(() => import("./components/TasksTab"));
const DevTab = lazy(() => import("./components/DevTab"));
const WhitelistTab = lazy(() => import("./components/WhitelistTab"));
const KnowledgeTab = lazy(() => import("./components/KnowledgeTab"));
const SandboxTab = lazy(() => import("./components/SandboxTab"));
const OracleTab = lazy(() => import("./components/OracleTab"));
const BusinessIntelligenceTab = lazy(() => import("./components/BusinessIntelligenceTab"));
const SystemHealthTab = lazy(() => import("./components/SystemHealthTab"));
const LearningHealingTab = lazy(() => import("./components/LearningHealingTab"));
const LabTab = lazy(() => import("./components/LabTab"));
const APIsTab = lazy(() => import("./components/APIsTab"));
const AskTab = lazy(() => import("./components/AskTab"));
const ArchitectTab = lazy(() => import("./components/ArchitectTab"));
const KPIDashboard = lazy(() => import("./components/KPIDashboard"));
import PersistentVoicePanel from "./components/PersistentVoicePanel";
import ActivityFeed from "./components/ActivityFeed";
import GenesisTimeline from "./components/GenesisTimeline";
import ContextMenu from "./components/ContextMenu";
import TerminalLogViewer from "./components/TerminalLogViewer";

// Sidebar sections — descriptions show as tooltips on hover
const WORKSPACE = [
  { id: 'chats', icon: '💬', label: 'Chats', desc: 'Conversational flows and agent orchestration' },
  { id: 'folders', icon: '📁', label: 'Folders', desc: 'Project container organization' },
  { id: 'docs', icon: '📄', label: 'Docs', desc: 'Universal document library & dropzone' },
  { id: 'codebase', icon: '💻', label: 'Code Base', desc: 'Code exploration & artifact management' },
  { id: 'devlab', icon: '🧪', label: 'Dev Lab', desc: 'Advanced sub-agent tracking & verification' },
  { id: 'knowledge', icon: '🧠', label: 'Knowledge Base', desc: 'Deterministic Context & Document Memory' },
  { id: 'whitelist', icon: '🔗', label: 'Integrations', desc: 'API Sources & Whitelisted Web Tools' },
  { id: "agents", icon: "🤖", label: "Oracle", desc: "Oracle and agent training. Trust distribution, audits, and agent capabilities." },
  { id: 'sandbox', icon: '🧬', label: 'Sandbox', desc: 'Isolated Execution & Promotion Engine' }
];

const SYSTEM = [
  { id: "governance", label: "Governance", icon: "🏛️", description: "Governance rules, approvals, trust scores, self-healing, and system policy." },
  { id: "ask", label: "Ask (Architecture)", icon: "🗺️", description: "Ask questions about system architecture. Routes to the right brain and actions." },
  { id: "architect", label: "Proposer", icon: "🏗️", description: "Design a new component in JSON and Grace will build and integrate it autonomously." },
  { id: "memory", label: "Memory", icon: "🧠", description: "Learning and healing. Skills, self-learning triggers, and diagnostic dashboard." },
  { id: "self_healing", label: "Self Healing", icon: "🧬", description: "Healing actions and logic." },
  { id: "health", label: "Health", icon: "🏥", description: "System health dashboard. Processes, components, and service status." },
  { id: "kpi", label: "KPIs & Trust", icon: "📊", description: "Live KPI dashboard and trust score tracking across all 9 brain domains." },
  { id: "settings", label: "Settings", icon: "⚙️", description: "Business intelligence, KPIs, and system configuration." },
];

// Preload lazy tab chunks on hover so click opens instantly
const TAB_PRELOAD = {
  chat: () => import("./components/ChatTab"),
  folders: () => import("./components/FoldersTab"),
  docs: () => import("./components/DocsTab"),
  governance: () => import("./components/GovernanceTab"),
  codebase: () => import("./components/CodebaseTab"),
  tasks: () => import("./components/TasksTab"),
  dev: () => import("./components/DevTab"),
  whitelist: () => import("./components/WhitelistTab"),
  sandbox: () => import("./components/SandboxTab"),
  knowledge: () => import("./components/KnowledgeTab"),
  memory: () => import("./components/LearningHealingTab"),
  self_healing: () => import("./components/LearningHealingTab"),
  health: () => import("./components/SystemHealthTab"),
  settings: () => import("./components/BusinessIntelligenceTab"),
  lab: () => import("./components/LabTab"),
  apis: () => import("./components/APIsTab"),
  ask: () => import("./components/AskTab"),
  architect: () => import("./components/ArchitectTab"),
  kpi: () => import("./components/KPIDashboard"),
  projects: () => import("./components/TasksTab"),
};

function App() {
  const [view, setView] = useState("home");
  const [health, setHealth] = useState(null);
  const [brains, setBrains] = useState({ connected: false, count: 0, error: null });
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Phase 13: Global Domain State (Mirroring)
  const [domain, setDomain] = useState("Global (All Domains)");
  const DOMAINS = ["Global (All Domains)", "Dog Walking App", "E-Commerce Backend", "Internal Dashboard API"];
  const [showGenesis, setShowGenesis] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, item: null });

  const [model, setModel] = useState("consensus");
  const [models, setModels] = useState([]);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [recentChats, _setRecentChats] = useState([]);
  const [voiceResponse, setVoiceResponse] = useState("");
  const [voiceProcessing, setVoiceProcessing] = useState(false);

  const preloadTab = (id) => {
    const fn = TAB_PRELOAD[id];
    if (fn) fn().catch(() => { });
  };

  useEffect(() => {
    const check = async () => {
      const h = await healthCheck();
      setHealth(h);
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const checkBrains = async () => {
      const r = await brainDirectory();
      setBrains({
        connected: r.ok && r.total_brains > 0,
        count: r.total_brains ?? 0,
        error: r.error || null,
      });
    };
    checkBrains();
    const interval = setInterval(checkBrains, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    brainCall("ai", "models", {}).then(r => {
      if (r.ok && r.data?.models) setModels(r.data.models);
    });
  }, []);

  // Cmd+K command palette
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen(p => !p);
      }
      if (e.key === "Escape") setCmdOpen(false);
    };
    window.addEventListener("keydown", handler);

    const handleContextMenu = (e) => {
      // Only trigger custom context menu if clicking an element with data-context-item
      const target = e.target.closest('[data-context-item]');
      if (target) {
        e.preventDefault();
        const itemData = JSON.parse(target.getAttribute('data-context-item'));
        setContextMenu({ visible: true, x: e.clientX, y: e.clientY, item: itemData });
      }
    };
    window.addEventListener("contextmenu", handleContextMenu);

    return () => {
      window.removeEventListener("keydown", handler);
      window.removeEventListener("contextmenu", handleContextMenu);
    };
  }, []);

  const handleVoice = async (msg) => {
    setVoiceProcessing(true);
    const r = await brainCall("chat", "consensus", { message: msg });
    setVoiceResponse(r.ok ? (r.data?.final_output || "Done") : "Error");
    setVoiceProcessing(false);
  };

  // Switch to Dev Lab when a context menu task is started
  useEffect(() => {
    const handleTaskFocus = () => {
      setView("dev");
    };
    window.addEventListener('DEVLAB_TASK_STARTED', handleTaskFocus);
    return () => window.removeEventListener('DEVLAB_TASK_STARTED', handleTaskFocus);
  }, []);

  const online = health != null && (health.status === "healthy" || health.llm_running === true || health.status === "degraded");
  const offlineTitle = "Start the backend (e.g. run start.bat or: backend on :8000, then refresh)";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0a0a1a", color: "#ccc" }}>
      {/* ── Status Bar ────────────────────────────────────────── */}
      <div style={{
        height: 24, background: "#06061a", display: "flex", alignItems: "center",
        justifyContent: "space-between", padding: "0 12px", fontSize: 10, color: "#555",
        borderBottom: "1px solid #111",
      }}>
        <span>{new Date().toLocaleTimeString()}</span>
        <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }} title={brains.error || (brains.connected ? `${brains.count} brain domains` : 'Brains')}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: brains.connected ? "#4caf50" : "#f44336" }} />
            {brains.connected ? `Brains: ${brains.count}` : `Brains: ${brains.error || "disconnected"}`}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }} title={online ? "Backend reachable" : offlineTitle}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: online ? "#4caf50" : "#f44336" }} />
            {online ? "Connected" : "Offline"}
          </span>
          <span
            style={{ cursor: "pointer", padding: "0 4px", borderRadius: 3, background: "#12122a", fontSize: 9, color: "#888" }}
            title="Open KPI & Trust dashboard"
            onClick={() => typeof setView === 'function' && setView('kpi')}
          >📊 KPIs</span>
        </span>
      </div>

      {/* ── Top Nav ───────────────────────────────────────────── */}
      <div style={{
        height: 44, background: "#0d0d22", display: "flex", alignItems: "center",
        padding: "0 12px", borderBottom: "1px solid #1a1a2e", gap: 12,
      }}>
        <button onClick={() => setSidebarOpen(p => !p)} style={iconBtn}>☰</button>
        <span style={{ fontSize: 16, fontWeight: 800, color: "#e94560", cursor: "pointer" }} onClick={() => setView("home")}>Grace</span>
        <div style={{ flex: 1 }} />

        {/* Domain Selector (Phase 13 Mirroring) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: "#12122a", border: "1px solid #e94560", borderRadius: 6, padding: "2px 8px" }}>
          <select value={domain} onChange={e => setDomain(e.target.value)} style={{
            background: "transparent", border: "none", color: "#e94560", fontSize: 11, outline: "none",
            fontWeight: 700, cursor: 'pointer'
          }}>
            {DOMAINS.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <div style={{ width: 1, height: 14, background: '#e94560', opacity: 0.3 }} />
          <button
            onClick={() => setShowGenesis(true)}
            style={{ background: 'transparent', border: 'none', color: '#e94560', cursor: 'pointer', fontSize: 11, fontWeight: 700, padding: '2px 4px' }}
            title="View Genesis Version Control Timeline"
          >
            ⧗ Genesis Timeline
          </button>
        </div>

        {/* Model Selector */}
        <select value={model} onChange={e => setModel(e.target.value)} style={{
          background: "#12122a", border: "1px solid #333", borderRadius: 6,
          color: "#ccc", padding: "4px 8px", fontSize: 11, outline: "none",
        }}>
          <option value="consensus">All Models (Consensus)</option>
          {models.map(m => (
            <option key={m.id} value={m.id} disabled={!m.available}>{m.name}</option>
          ))}
        </select>

        {/* Cmd+K */}
        <button onClick={() => setCmdOpen(true)} style={{ ...iconBtn, fontSize: 10, padding: "3px 8px", border: "1px solid #333", borderRadius: 4 }}>
          ⌘K
        </button>

        {/* Terminal Toggle */}
        <button
          onClick={() => setShowTerminal(!showTerminal)}
          style={{ ...iconBtn, fontSize: 12, padding: "3px 8px", border: "1px solid #333", borderRadius: 4, background: showTerminal ? '#1a1a3a' : 'transparent', color: showTerminal ? '#e94560' : '#888' }}
          title="Toggle Grace Core Terminal"
        >
          {'>_'}
        </button>

        <button style={iconBtn}>👤</button>
      </div>

      {/* ── Main Area (Sidebar + Content) ─────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Sidebar */}
        {sidebarOpen && (
          <div style={{
            width: 220, background: "#0a0a18", borderRight: "1px solid #1a1a2e",
            display: "flex", flexDirection: "column", overflow: "auto", flexShrink: 0,
          }}>
            {/* Workspace: 5 Primary Tabs */}
            <div style={{ padding: "12px 0" }}>
              <div style={sectionLabel}>5-Tab Workspace</div>
              {WORKSPACE.map(item => (
                <SidebarItem key={item.id} item={item} active={view === item.id} onClick={() => setView(item.id)} onPreload={() => preloadTab(item.id)} />
              ))}
            </div>

            {/* System */}
            <div style={{ padding: "4px 0", borderTop: "1px solid #151530" }}>
              <div style={sectionLabel}>System</div>
              {SYSTEM.map(item => (
                <SidebarItem key={item.id} item={item} active={view === item.id} onClick={() => setView(item.id)} onPreload={() => preloadTab(item.id)} />
              ))}
            </div>

            {/* Projects */}
            <div style={{ padding: "4px 0", borderTop: "1px solid #151530" }}>
              <div style={sectionLabel}>Projects</div>
              <SidebarItem item={{ id: "projects", label: "All Projects", icon: "📋", description: "Tasks hub: live tasks, history, scheduling, and time-sense." }} active={view === "projects"} onClick={() => setView("projects")} onPreload={() => preloadTab("projects")} />
            </div>

            {/* Recent Chats */}
            <div style={{ padding: "4px 0", borderTop: "1px solid #151530", flex: 1 }}>
              <div style={sectionLabel}>Recent</div>
              {recentChats.slice(0, 5).map((c, i) => (
                <div key={i} style={{ padding: "4px 16px", fontSize: 11, color: "#555", cursor: "pointer" }}
                  onClick={() => setView("chat")}>
                  {c.title || `Chat ${c.id}`}
                </div>
              ))}
            </div>

            {/* New Item */}
            <div style={{ padding: "8px 12px", borderTop: "1px solid #151530" }}>
              <button style={{
                width: "100%", padding: "6px", background: "#e94560", border: "none",
                borderRadius: 6, color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer",
              }}>+ New Item</button>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ background: "#080814", color: "#e94560", fontSize: 11, padding: "4px 16px", borderBottom: "1px solid #1a1a2e", fontWeight: 700 }}>
            Active Scoped Domain: {domain}
          </div>
          <Suspense fallback={<div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#666", fontSize: 13 }}>Loading…</div>}>
            {/* Main Workspace Area */}
            <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
              {view === "home" && <HomePage onNavigate={setView} domain={domain} />}
              {view === "chat" && <ChatTab domain={domain} />}
              {view === "folders" && <FoldersTab domain={domain} />}
              {view === "docs" && <DocsTab domain={domain} />}
              {view === "codebase" && <CodebaseTab domain={domain} />}
              {view === "devlab" && <DevTab domain={domain} />}
              {view === "knowledge" && <KnowledgeTab domain={domain} />}
              {view === "whitelist" && <WhitelistTab domain={domain} />}
              {view === "sandbox" && <SandboxTab domain={domain} />}
              {view === "governance" && <GovernanceTab domain={domain} />}
              {view === "agents" && <OracleTab />}
              {view === "memory" && <LearningHealingTab />}
              {view === "self_healing" && <LearningHealingTab />}
              {view === "integrations" && <WhitelistTab />}
              {view === "health" && <SystemHealthTab />}
              {view === "settings" && <BusinessIntelligenceTab />}
              {view === "projects" && <TasksTab />}
              {view === "lab" && <LabTab />}
              {view === "apis" && <APIsTab />}
              {view === "ask" && <AskTab />}
              {view === "architect" && <ArchitectTab />}
              {view === "kpi" && <KPIDashboard />}
            </div>
          </Suspense>
        </div>
      </div>

      {/* ── Input Bar ─────────────────────────────────────────── */}
      <InputBar model={model} onNavigate={setView} />

      {/* ── Terminal Overlays ─────────────────────────────────── */}
      {showTerminal && <TerminalLogViewer onClose={() => setShowTerminal(false)} />}

      {/* ── Floating ──────────────────────────────────────────── */}
      <PersistentVoicePanel onSendMessage={handleVoice} lastResponse={voiceResponse} isProcessing={voiceProcessing} />
      <ActivityFeed />

      {/* ── Command Palette ───────────────────────────────────── */}
      {cmdOpen && <CommandPalette onClose={() => setCmdOpen(false)} onNavigate={(v) => { setView(v); setCmdOpen(false); }} />}

      {/* ── Universal Right-Click Context Menu ─────────────────── */}
      <ContextMenu
        {...contextMenu}
        onClose={() => setContextMenu({ ...contextMenu, visible: false })}
      />

      {/* ── Genesis Timeline Modal ─────────────────────────────── */}
      {showGenesis && <GenesisTimeline domain={domain} onClose={() => setShowGenesis(false)} />}
    </div>
  );
}


/* ── Home Page ─────────────────────────────────────────────────── */

function HomePage({ onNavigate }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 40 }}>
      <div style={{ fontSize: 48, fontWeight: 900, color: "#e94560", marginBottom: 8 }}>Grace</div>
      <div style={{ fontSize: 14, color: "#888", marginBottom: 32 }}>Autonomous AI System</div>

      <div style={{ fontSize: 20, color: "#ccc", marginBottom: 32, textAlign: "center" }}>
        What are we building today?
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, width: 400, marginBottom: 40 }}>
        {[
          { label: "Start Project", icon: "🚀", view: "projects" },
          { label: "Analyze Code", icon: "🔍", view: "codebase" },
          { label: "New Agent", icon: "🤖", view: "agents" },
          { label: "Open Dev Lab", icon: "🧪", view: "dev" },
          { label: "Chat with Grace", icon: "💬", view: "chat" },
          { label: "System Health", icon: "🏥", view: "health" },
        ].map(a => (
          <button key={a.label} onClick={() => onNavigate(a.view)} style={{
            padding: "16px", background: "#12122a", border: "1px solid #222",
            borderRadius: 10, cursor: "pointer", textAlign: "center",
            color: "#ccc", fontSize: 13, fontWeight: 600,
            transition: "all .15s",
          }}
            onMouseEnter={e => e.target.style.borderColor = "#e94560"}
            onMouseLeave={e => e.target.style.borderColor = "#222"}
          >
            <div style={{ fontSize: 24, marginBottom: 6 }}>{a.icon}</div>
            {a.label}
          </button>
        ))}
      </div>

      <div style={{ color: "#555", fontSize: 12 }}>
        9 brain domains | 108 actions | Autonomous self-healing
      </div>
    </div>
  );
}


/* ── Input Bar ─────────────────────────────────────────────────── */

function InputBar({ onNavigate }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);

    // Auto-route the query
    const r = await brainCall("chat", "send", {
      chat_id: 1,
      message: input,
    }).catch(() => ({ ok: false }));

    // If it fails, try brain/ask as fallback
    if (!r.ok) {
      const { brainAsk } = await import("./api/brain-client");
      const askRes = await brainAsk(input).catch(() => ({ ok: false }));
      if (askRes.ok && askRes.data) {
        onNavigate("chat");
      }
    }

    setInput("");
    setLoading(false);
    onNavigate("chat");
  };

  return (
    <div style={{
      height: 52, background: "#0d0d22", borderTop: "1px solid #1a1a2e",
      display: "flex", alignItems: "center", padding: "0 12px", gap: 8,
    }}>
      <button style={iconBtn}>+</button>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => e.key === "Enter" && send()}
        placeholder="Ask Grace anything..."
        style={{
          flex: 1, padding: "8px 14px", background: "#12122a", border: "1px solid #222",
          borderRadius: 8, color: "#ccc", fontSize: 13, outline: "none",
        }}
      />
      <button style={iconBtn}>🎤</button>
      <button onClick={send} disabled={loading} style={{
        padding: "6px 16px", background: "#e94560", border: "none",
        borderRadius: 6, color: "#fff", fontSize: 12, fontWeight: 700,
        cursor: loading ? "wait" : "pointer", opacity: loading ? 0.5 : 1,
      }}>
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
}


/* ── Sidebar Item ──────────────────────────────────────────────── */

function SidebarItem({ item, active, onClick, onPreload }) {
  const tooltip = item.description || item.label;
  return (
    <button
      type="button"
      title={tooltip}
      onClick={onClick}
      onMouseEnter={onPreload}
      style={{
        display: "flex", alignItems: "center", gap: 6, width: "100%",
        padding: "4px 12px", border: "none", background: active ? "#1a1a3a" : "transparent",
        color: active ? "#e94560" : "#888", cursor: "pointer", fontSize: 11,
        fontWeight: active ? 700 : 400, textAlign: "left",
        borderLeft: active ? "3px solid #e94560" : "3px solid transparent",
      }}
    >
      <span style={{ fontSize: 13 }}>{item.icon}</span>
      {item.label}
    </button>
  );
}


/* ── Command Palette ───────────────────────────────────────────── */

function CommandPalette({ onClose, onNavigate }) {
  const [query, setQuery] = useState("");
  const all = [...WORKSPACE, ...SYSTEM, { id: "home", label: "Home", icon: "🏠" }, { id: "projects", label: "Projects", icon: "📋" }];
  const filtered = query ? all.filter(i => i.label.toLowerCase().includes(query.toLowerCase())) : all;

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000,
      display: "flex", alignItems: "flex-start", justifyContent: "center", paddingTop: 120,
    }} onClick={onClose}>
      <div style={{
        width: 500, background: "#12122a", border: "1px solid #333", borderRadius: 12,
        overflow: "hidden",
      }} onClick={e => e.stopPropagation()}>
        <input
          autoFocus
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search or jump to..."
          style={{
            width: "100%", padding: "14px 16px", background: "transparent",
            border: "none", borderBottom: "1px solid #222", color: "#ccc",
            fontSize: 14, outline: "none",
          }}
        />
        <div style={{ maxHeight: 300, overflow: "auto" }}>
          {filtered.map(item => (
            <button key={item.id} onClick={() => onNavigate(item.id)} style={{
              display: "flex", alignItems: "center", gap: 10, width: "100%",
              padding: "10px 16px", border: "none", background: "transparent",
              color: "#ccc", cursor: "pointer", fontSize: 13, textAlign: "left",
            }}
              onMouseEnter={e => e.target.style.background = "#1a1a3a"}
              onMouseLeave={e => e.target.style.background = "transparent"}
            >
              <span>{item.icon}</span> {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}


const iconBtn = {
  background: "none", border: "none", color: "#888", cursor: "pointer",
  fontSize: 16, padding: 4, borderRadius: 4,
};
const sectionLabel = {
  padding: "4px 16px", fontSize: 10, fontWeight: 700, color: "#555",
  textTransform: "uppercase", letterSpacing: 1,
};


export default App;
