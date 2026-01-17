import { useState, useEffect, useRef } from "react";
import "./App.css";
import ChatTab from "./components/ChatTab";
import IntelligenceTab from "./components/IntelligenceTab";
import SearchDiscoveryTab from "./components/SearchDiscoveryTab";
import MonitoringConsolidatedTab from "./components/MonitoringConsolidatedTab";
import VersionControl from "./components/VersionControl";
import NotionTab from "./components/NotionTab";
import GovernanceTab from "./components/GovernanceTab";
import SandboxTab from "./components/SandboxTab";
import APITab from "./components/APITab";
import LibrarianTab from "./components/LibrarianTab";
import PersistentVoicePanel from "./components/PersistentVoicePanel";
import GenesisKeyTab from "./components/GenesisKeyTab";
import WhitelistTab from "./components/WhitelistTab";
import OrchestrationConsolidatedTab from "./components/OrchestrationConsolidatedTab";
import SelfHealingTab from "./components/SelfHealingTab";
import EnterpriseDashboard from "./components/EnterpriseDashboard";

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [apiHealth, setApiHealth] = useState(null);
  const [lastVoiceResponse, setLastVoiceResponse] = useState("");
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);

  useEffect(() => {
    // Check API health on mount
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch("http://localhost:8000/health");
      const data = await response.json();
      setApiHealth(data);
    } catch (error) {
      console.error("Failed to check API health:", error);
      setApiHealth(null);
    }
  };

  // Handle voice messages from PersistentVoicePanel
  const handleVoiceMessage = async (message) => {
    setIsVoiceProcessing(true);
    try {
      // Send voice message to Grace's chat API
      const response = await fetch("http://localhost:8000/chat", {
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
        setLastVoiceResponse(
          "I don't have information about that in my knowledge base yet. Please upload relevant documents."
        );
      } else {
        setLastVoiceResponse("Sorry, I encountered an error processing your request.");
      }
    } catch (error) {
      console.error("Voice message error:", error);
      setLastVoiceResponse("Sorry, I couldn't connect to the server.");
    } finally {
      setIsVoiceProcessing(false);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <h1>Grace</h1>
          <div className="health-indicator">
            {apiHealth ? (
              <>
                <span
                  className={`status-dot ${
                    apiHealth.ollama_running ? "healthy" : "unhealthy"
                  }`}
                ></span>
                <span className="status-text">
                  {apiHealth.ollama_running ? "Connected" : "Disconnected"}
                </span>
              </>
            ) : (
              <>
                <span className="status-dot unhealthy"></span>
                <span className="status-text">Loading...</span>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="app-container">
        {/* Sidebar */}
        <aside className="sidebar">
          <nav className="tabs-nav">
            <button
              className={`tab-button ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              Chat
            </button>
            <button
              className={`tab-button ${activeTab === "governance" ? "active" : ""}`}
              onClick={() => setActiveTab("governance")}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                width={20}
                height={20}
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
                />
              </svg>
              Governance
            </button>
            <button
              className={`tab-button ${activeTab === "sandbox" ? "active" : ""}`}
              onClick={() => setActiveTab("sandbox")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="3" y1="9" x2="21" y2="9"></line>
                <line x1="9" y1="21" x2="9" y2="9"></line>
              </svg>
              Sandbox
            </button>
            <button
              className={`tab-button ${activeTab === "intelligence" ? "active" : ""}`}
              onClick={() => setActiveTab("intelligence")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M12 1v6m0 6v6m5-9l-4 4m-2 2l-4 4m10-12l-4 4m-2 2l-4 4M1 12h6m6 0h6"></path>
              </svg>
              Intelligence
            </button>
            <button
              className={`tab-button ${activeTab === "search-discovery" ? "active" : ""}`}
              onClick={() => setActiveTab("search-discovery")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
              Search & Discovery
            </button>
            <button
              className={`tab-button ${activeTab === "api" ? "active" : ""}`}
              onClick={() => setActiveTab("api")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M18 20V10"></path>
                <path d="M12 20V4"></path>
                <path d="M6 20v-6"></path>
              </svg>
              APIs
            </button>
            <button
              className={`tab-button ${activeTab === "librarian" ? "active" : ""}`}
              onClick={() => setActiveTab("librarian")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
                <line x1="7" y1="7" x2="7.01" y2="7"></line>
              </svg>
              Librarian
            </button>
            <button
              className={`tab-button ${
                activeTab === "monitoring" ? "active" : ""
              }`}
              onClick={() => setActiveTab("monitoring")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="12 3 20 7.5 20 16.5 12 21 4 16.5 4 7.5 12 3"></polyline>
                <line x1="12" y1="12" x2="20" y2="7.5"></line>
                <line x1="12" y1="12" x2="12" y2="21"></line>
                <line x1="12" y1="12" x2="4" y2="7.5"></line>
              </svg>
              Monitoring
            </button>
            <button
              className={`tab-button ${
                activeTab === "self-healing" ? "active" : ""
              }`}
              onClick={() => setActiveTab("self-healing")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M14.121 1.879a3 3 0 0 0-4.242 0L8.733 3.026l4.261 4.26 1.127-1.165a3 3 0 0 0 0-4.242M12.293 8 8.027 3.734 3.738 8.031 8 12.293zm-5.006 4.994L3.03 8.737 1.879 9.88a3 3 0 0 0 4.241 4.24l.006-.006 1.16-1.121Z" />
              </svg>
              Self-Healing
            </button>
            <button
              className={`tab-button ${
                activeTab === "version-control" ? "active" : ""
              }`}
              onClick={() => setActiveTab("version-control")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="6" cy="6" r="3"></circle>
                <circle cx="18" cy="6" r="3"></circle>
                <circle cx="12" cy="18" r="3"></circle>
                <line x1="8.5" y1="8" x2="12" y2="16"></line>
                <line x1="15.5" y1="8" x2="12" y2="16"></line>
              </svg>
              Version Control
            </button>
            <button
              className={`tab-button ${
                activeTab === "notion" ? "active" : ""
              }`}
              onClick={() => setActiveTab("notion")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
              Task Manager
            </button>
            <button
              className={`tab-button ${
                activeTab === "genesis" ? "active" : ""
              }`}
              onClick={() => setActiveTab("genesis")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
              Genesis Keys
            </button>
            <button
              className={`tab-button ${
                activeTab === "whitelist" ? "active" : ""
              }`}
              onClick={() => setActiveTab("whitelist")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                <path d="M9 12l2 2 4-4"></path>
              </svg>
              Whitelist
            </button>
            <button
              className={`tab-button ${
                activeTab === "orchestration" ? "active" : ""
              }`}
              onClick={() => setActiveTab("orchestration")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="5" r="3"></circle>
                <circle cx="5" cy="19" r="3"></circle>
                <circle cx="19" cy="19" r="3"></circle>
                <line x1="12" y1="8" x2="5" y2="16"></line>
                <line x1="12" y1="8" x2="19" y2="16"></line>
              </svg>
              Orchestration
            </button>
            <button
              className={`tab-button ${
                activeTab === "enterprise" ? "active" : ""
              }`}
              onClick={() => setActiveTab("enterprise")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
                <circle cx="12" cy="12" r="2" fill="currentColor"></circle>
              </svg>
              Enterprise
            </button>
          </nav>
        </aside>

        {/* Tab Content */}
        <main className="main-content">
          {activeTab === "chat" && <ChatTab />}
          {activeTab === "intelligence" && <IntelligenceTab />}
          {activeTab === "search-discovery" && <SearchDiscoveryTab />}
          {activeTab === "governance" && <GovernanceTab />}
          {activeTab === "sandbox" && <SandboxTab />}
          {activeTab === "api" && <APITab />}
          {activeTab === "librarian" && <LibrarianTab />}
          {activeTab === "monitoring" && <MonitoringConsolidatedTab />}
          {activeTab === "self-healing" && <SelfHealingTab />}
          {activeTab === "version-control" && <VersionControl />}
          {activeTab === "notion" && <NotionTab />}
          {activeTab === "genesis" && <GenesisKeyTab />}
          {activeTab === "whitelist" && <WhitelistTab />}
          {activeTab === "orchestration" && <OrchestrationConsolidatedTab />}
          {activeTab === "enterprise" && <EnterpriseDashboard />}
        </main>
      </div>

      {/* Persistent Voice Panel - Always visible floating button */}
      <PersistentVoicePanel
        onSendMessage={handleVoiceMessage}
        lastResponse={lastVoiceResponse}
        isProcessing={isVoiceProcessing}
      />
    </div>
  );
}

export default App;
