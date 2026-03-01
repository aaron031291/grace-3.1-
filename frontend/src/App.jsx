import { useState, useEffect, useRef } from "react";
import "./App.css";
import { API_ENDPOINTS } from "./config/api";
import ChatTab from "./components/ChatTab";
import FoldersTab from "./components/FoldersTab";
import DocsTab from "./components/DocsTab";
import GovernanceTab from "./components/GovernanceTab";
import WhitelistTab from "./components/WhitelistTab";
import OracleTab from "./components/OracleTab";
import CodebaseTab from "./components/CodebaseTab";
import TasksTab from "./components/TasksTab";
import APIsTab from "./components/APIsTab";
import BusinessIntelligenceTab from "./components/BusinessIntelligenceTab";
import SystemHealthTab from "./components/SystemHealthTab";
import LearningHealingTab from "./components/LearningHealingTab";
import LabTab from "./components/LabTab";
import DevTab from "./components/DevTab";
import PersistentVoicePanel from "./components/PersistentVoicePanel";
import ActivityFeed from "./components/ActivityFeed";
import UndoToast from "./components/UndoManager";
import CrossTabNotifier, { setNavigator } from "./components/CrossTabNotifier";
import TabGuide from "./components/TabGuide";

const VIEWS = [
  { id: "chat", label: "Chat", icon: "💬" },
  { id: "folders", label: "Folders", icon: "📁" },
  { id: "docs", label: "Docs", icon: "📚" },
  { id: "governance", label: "Governance", icon: "🏛️" },
  { id: "whitelist", label: "Whitelist", icon: "🛡️" },
  { id: "oracle", label: "Oracle", icon: "🔮" },
  { id: "codebase", label: "Codebase", icon: "💻" },
  { id: "tasks", label: "Tasks", icon: "📋" },
  { id: "apis", label: "APIs", icon: "🔗" },
  { id: "bi", label: "BI", icon: "📈" },
  { id: "health", label: "Health", icon: "🏥" },
  { id: "learn-heal", label: "Learn", icon: "🧬" },
  { id: "lab", label: "Lab", icon: "🧪" },
  { id: "dev", label: "Dev", icon: "🛠️" },
];

function App() {
  const [activeView, setActiveView] = useState("chat");
  const [apiHealth, setApiHealth] = useState(null);
  const [lastVoiceResponse, setLastVoiceResponse] = useState("");
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);

  // Wire cross-tab navigator
  useEffect(() => { setNavigator(setActiveView); }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.health);
      const data = await response.json();
      setApiHealth(data);
    } catch {
      setApiHealth(null);
    }
  };

  const handleVoiceMessage = async (message) => {
    setIsVoiceProcessing(true);
    try {
      const response = await fetch(API_ENDPOINTS.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: message }],
          temperature: 0.7,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setLastVoiceResponse(data.message);
      } else {
        setLastVoiceResponse("Sorry, I encountered an issue.");
      }
    } catch {
      setLastVoiceResponse("Sorry, I couldn't connect to the server.");
    } finally {
      setIsVoiceProcessing(false);
    }
  };

  return (
    <div className="app">
      {/* ── Header with Horizontal Tab Bar ─────────────────────── */}
      <header style={{
        background: '#12122a', borderBottom: '1px solid #333',
        display: 'flex', alignItems: 'center', padding: '0 12px',
        height: 48, flexShrink: 0,
      }}>
        {/* Logo */}
        <h1 style={{
          fontSize: 18, fontWeight: 800, color: '#e94560', margin: 0,
          marginRight: 16, letterSpacing: '-0.5px', flexShrink: 0,
        }}>Grace</h1>

        {/* Horizontal Tab Bar */}
        <div style={{
          display: 'flex', gap: 0, overflow: 'auto', flex: 1,
          scrollbarWidth: 'none', msOverflowStyle: 'none',
        }}>
          {VIEWS.map(v => (
            <button
              key={v.id}
              onClick={() => setActiveView(v.id)}
              style={{
                padding: '6px 12px', border: 'none', background: 'none',
                cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap',
                color: activeView === v.id ? '#e94560' : '#888',
                borderBottom: activeView === v.id ? '2px solid #e94560' : '2px solid transparent',
                fontWeight: activeView === v.id ? 700 : 500,
                transition: 'all .15s',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{ fontSize: 14 }}>{v.icon}</span>
              {v.label}
            </button>
          ))}
        </div>

        {/* Right side: guide + notifications + health */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, position: 'relative' }}>
          <TabGuide tabId={activeView} />
          <CrossTabNotifier />
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: (apiHealth?.llm_running || apiHealth?.ollama_running) ? '#4caf50' : apiHealth ? '#ff9800' : '#f44336',
            }} />
            <span style={{ fontSize: 11, color: '#888' }}>
              {(apiHealth?.llm_running || apiHealth?.ollama_running) ? 'Online' : apiHealth ? 'Partial' : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Content ───────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <main style={{ width: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {activeView === "chat" && <ChatTab />}
          {activeView === "folders" && <FoldersTab />}
          {activeView === "docs" && <DocsTab />}
          {activeView === "governance" && <GovernanceTab />}
          {activeView === "whitelist" && <WhitelistTab />}
          {activeView === "oracle" && <OracleTab />}
          {activeView === "codebase" && <CodebaseTab />}
          {activeView === "tasks" && <TasksTab />}
          {activeView === "apis" && <APIsTab />}
          {activeView === "bi" && <BusinessIntelligenceTab />}
          {activeView === "health" && <SystemHealthTab />}
          {activeView === "learn-heal" && <LearningHealingTab />}
          {activeView === "lab" && <LabTab />}
          {activeView === "dev" && <DevTab />}
        </main>
      </div>

      {/* ── Floating Components ────────────────────────────────── */}
      <PersistentVoicePanel
        onSendMessage={handleVoiceMessage}
        lastResponse={lastVoiceResponse}
        isProcessing={isVoiceProcessing}
      />
      <ActivityFeed />
      <UndoToast />
    </div>
  );
}

export default App;
