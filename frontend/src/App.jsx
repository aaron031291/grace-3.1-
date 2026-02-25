import { useState, useEffect, useRef } from "react";
import "./App.css";
import { API_ENDPOINTS } from "./config/api";
import ChatTab from "./components/ChatTab";
import FoldersTab from "./components/FoldersTab";
import DocsTab from "./components/DocsTab";
import GovernanceTab from "./components/GovernanceTab";
import WhitelistTab from "./components/WhitelistTab";
import PersistentVoicePanel from "./components/PersistentVoicePanel";

function App() {
  const [activeView, setActiveView] = useState("chat");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [apiHealth, setApiHealth] = useState(null);
  const [lastVoiceResponse, setLastVoiceResponse] = useState("");
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
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
      } else if (response.status === 404) {
        setLastVoiceResponse("I don't have information about that in my knowledge base yet.");
      } else {
        setLastVoiceResponse("Sorry, I encountered an error processing your request.");
      }
    } catch {
      setLastVoiceResponse("Sorry, I couldn't connect to the server.");
    } finally {
      setIsVoiceProcessing(false);
    }
  };

  const views = [
    { id: "chat", label: "Chat", icon: "💬", desc: "World model & system chat" },
    { id: "folders", label: "Folders", icon: "📁", desc: "File management & librarian" },
    { id: "docs", label: "Docs", icon: "📚", desc: "Document library — all uploads" },
    { id: "governance", label: "Governance", icon: "🏛️", desc: "Approvals, scores, healing, learning" },
    { id: "whitelist", label: "Whitelist", icon: "🛡️", desc: "API & web sources, learning pipeline" },
  ];

  const current = views.find((v) => v.id === activeView) || views[0];

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Grace</h1>

          <div className="view-selector" ref={dropdownRef}>
            <button
              className="view-selector-btn"
              onClick={() => setDropdownOpen(!dropdownOpen)}
            >
              <span className="view-icon">{current.icon}</span>
              <span className="view-label">{current.label}</span>
              <svg
                width="12" height="12" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" strokeWidth="3"
                style={{ transform: dropdownOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {dropdownOpen && (
              <div className="view-dropdown">
                {views.map((v) => (
                  <button
                    key={v.id}
                    className={`view-dropdown-item ${v.id === activeView ? "active" : ""}`}
                    onClick={() => { setActiveView(v.id); setDropdownOpen(false); }}
                  >
                    <span className="view-dropdown-icon">{v.icon}</span>
                    <div>
                      <div className="view-dropdown-label">{v.label}</div>
                      <div className="view-dropdown-desc">{v.desc}</div>
                    </div>
                    {v.id === activeView && (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4caf50" strokeWidth="3">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="health-indicator">
            {apiHealth ? (
              <>
                <span className={`status-dot ${apiHealth.ollama_running ? "healthy" : "unhealthy"}`} />
                <span className="status-text">
                  {apiHealth.ollama_running ? "Connected" : "Disconnected"}
                </span>
              </>
            ) : (
              <>
                <span className="status-dot unhealthy" />
                <span className="status-text">Loading...</span>
              </>
            )}
          </div>
        </div>
      </header>

      <div className="app-container">
        <main className="main-content" style={{ width: "100%" }}>
          {activeView === "chat" && <ChatTab />}
          {activeView === "folders" && <FoldersTab />}
          {activeView === "docs" && <DocsTab />}
          {activeView === "governance" && <GovernanceTab />}
          {activeView === "whitelist" && <WhitelistTab />}
        </main>
      </div>

      <PersistentVoicePanel
        onSendMessage={handleVoiceMessage}
        lastResponse={lastVoiceResponse}
        isProcessing={isVoiceProcessing}
      />
    </div>
  );
}

export default App;
