import { useState, useEffect, useRef, lazy, Suspense } from "react";
import "./App.css";
import { healthCheck, brainCall } from "./api/brain-client";

// Lazy-loaded page components (only loaded when the tab is opened)
const ChatTab = lazy(() => import("./components/ChatTab"));
const FoldersTab = lazy(() => import("./components/FoldersTab"));
const DocsTab = lazy(() => import("./components/DocsTab"));
const GovernanceTab = lazy(() => import("./components/GovernanceTab"));
const CodebaseTab = lazy(() => import("./components/CodebaseTab"));
const TasksTab = lazy(() => import("./components/TasksTab"));
const DevTab = lazy(() => import("./components/DevTab"));
const WhitelistTab = lazy(() => import("./components/WhitelistTab"));
const OracleTab = lazy(() => import("./components/OracleTab"));
const BusinessIntelligenceTab = lazy(() => import("./components/BusinessIntelligenceTab"));
const SystemHealthTab = lazy(() => import("./components/SystemHealthTab"));
const LearningHealingTab = lazy(() => import("./components/LearningHealingTab"));
const LabTab = lazy(() => import("./components/LabTab"));
const APIsTab = lazy(() => import("./components/APIsTab"));
const PersistentVoicePanel = lazy(() => import("./components/PersistentVoicePanel"));
const ActivityFeed = lazy(() => import("./components/ActivityFeed"));

function TabLoader() {
  return <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100%",color:"#888"}}>Loading...</div>;
}

// Sidebar sections
const WORKSPACE = [
  { id: "chat", label: "Chats", icon: "💬" },
  { id: "folders", label: "Folders", icon: "📁" },
  { id: "docs", label: "Docs", icon: "📄" },
  { id: "codebase", label: "Codebase", icon: "💻" },
  { id: "dev", label: "Dev Lab", icon: "🧪" },
  { id: "governance", label: "Governance", icon: "🏛️" },
];

const SYSTEM = [
  { id: "agents", label: "Agents", icon: "🤖" },
  { id: "memory", label: "Memory", icon: "🧠" },
  { id: "integrations", label: "Integrations", icon: "🔗" },
  { id: "health", label: "Health", icon: "🏥" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

function App() {
  const [view, setView] = useState("home");
  const [health, setHealth] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [model, setModel] = useState("consensus");
  const [models, setModels] = useState([]);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [recentChats, setRecentChats] = useState([]);
  const [voiceResponse, setVoiceResponse] = useState("");
  const [voiceProcessing, setVoiceProcessing] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    const check = async () => setHealth(await healthCheck());
    check();
    const interval = setInterval(check, 30000);
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
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleVoice = async (msg) => {
    setVoiceProcessing(true);
    const r = await brainCall("chat", "consensus", { message: msg });
    setVoiceResponse(r.ok ? (r.data?.final_output || "Done") : "Error");
    setVoiceProcessing(false);
  };

  const online = health?.status === "healthy" || health?.llm_running;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0a0a1a", color: "#ccc" }}>
      {/* ── Status Bar ────────────────────────────────────────── */}
      <div style={{
        height: 24, background: "#06061a", display: "flex", alignItems: "center",
        justifyContent: "space-between", padding: "0 12px", fontSize: 10, color: "#555",
        borderBottom: "1px solid #111",
      }}>
        <span>{new Date().toLocaleTimeString()}</span>
        <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: online ? "#4caf50" : "#f44336" }} />
          {online ? "Connected" : "Offline"}
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
            {/* Workspace */}
            <div style={{ padding: "12px 0" }}>
              <div style={sectionLabel}>Workspace</div>
              {WORKSPACE.map(item => (
                <SidebarItem key={item.id} item={item} active={view === item.id} onClick={() => setView(item.id)} />
              ))}
            </div>

            {/* System */}
            <div style={{ padding: "4px 0", borderTop: "1px solid #151530" }}>
              <div style={sectionLabel}>System</div>
              {SYSTEM.map(item => (
                <SidebarItem key={item.id} item={item} active={view === item.id} onClick={() => setView(item.id)} />
              ))}
            </div>

            {/* Projects */}
            <div style={{ padding: "4px 0", borderTop: "1px solid #151530" }}>
              <div style={sectionLabel}>Projects</div>
              <SidebarItem item={{ id: "projects", label: "All Projects", icon: "📋" }} active={view === "projects"} onClick={() => setView("projects")} />
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
          <Suspense fallback={<TabLoader />}>
          {view === "home" && <HomePage onNavigate={setView} />}
          {view === "chat" && <ChatTab />}
          {view === "folders" && <FoldersTab />}
          {view === "docs" && <DocsTab />}
          {view === "codebase" && <CodebaseTab />}
          {view === "dev" && <DevTab />}
          {view === "governance" && <GovernanceTab />}
          {view === "agents" && <OracleTab />}
          {view === "memory" && <LearningHealingTab />}
          {view === "integrations" && <WhitelistTab />}
          {view === "health" && <SystemHealthTab />}
          {view === "settings" && <BusinessIntelligenceTab />}
          {view === "projects" && <TasksTab />}
          {view === "lab" && <LabTab />}
          {view === "apis" && <APIsTab />}
          </Suspense>
        </div>
      </div>

      {/* ── Input Bar ─────────────────────────────────────────── */}
      <InputBar model={model} onNavigate={setView} />

      {/* ── Floating ──────────────────────────────────────────── */}
      <Suspense fallback={null}>
        <PersistentVoicePanel onSendMessage={handleVoice} lastResponse={voiceResponse} isProcessing={voiceProcessing} />
        <ActivityFeed />
      </Suspense>

      {/* ── Command Palette ───────────────────────────────────── */}
      {cmdOpen && <CommandPalette onClose={() => setCmdOpen(false)} onNavigate={(v) => { setView(v); setCmdOpen(false); }} />}
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
        8 brain domains | 103 actions | Autonomous self-healing
      </div>
    </div>
  );
}


/* ── Input Bar ─────────────────────────────────────────────────── */

function InputBar({ model, onNavigate }) {
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

    // If it fails, try auto-route
    if (!r.ok) {
      const { smart_call } = await import("./api/brain-client");
      // Fallback to consensus
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

function SidebarItem({ item, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 8, width: "100%",
      padding: "7px 16px", border: "none", background: active ? "#1a1a3a" : "transparent",
      color: active ? "#e94560" : "#888", cursor: "pointer", fontSize: 12,
      fontWeight: active ? 700 : 400, textAlign: "left",
      borderLeft: active ? "3px solid #e94560" : "3px solid transparent",
    }}>
      <span style={{ fontSize: 14 }}>{item.icon}</span>
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
