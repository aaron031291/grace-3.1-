import { useState, useEffect, useRef } from "react";
import "./App.css";
import ChatTab from "./components/ChatTab";
import RAGTab from "./components/RAGTab";
import MonitoringTab from "./components/MonitoringTab";
import VersionControl from "./components/VersionControl";
import CognitiveTab from "./components/CognitiveTab";
import NotionTab from "./components/NotionTab";
import GovernanceTab from "./components/GovernanceTab";
import CodeBaseTab from "./components/CodeBaseTab";
import ResearchTab from "./components/ResearchTab";
import SandboxTab from "./components/SandboxTab";
import InsightsTab from "./components/InsightsTab";
import APITab from "./components/APITab";
import LibrarianTab from "./components/LibrarianTab";
import PersistentVoicePanel from "./components/PersistentVoicePanel";
import GenesisKeyTab from "./components/GenesisKeyTab";
import LearningTab from "./components/LearningTab";
import MLIntelligenceTab from "./components/MLIntelligenceTab";
import WhitelistTab from "./components/WhitelistTab";
import ExperimentTab from "./components/ExperimentTab";
import ConnectorsTab from "./components/ConnectorsTab";
import OrchestrationTab from "./components/OrchestrationTab";
import TelemetryTab from "./components/TelemetryTab";

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
              className={`tab-button ${activeTab === "insights" ? "active" : ""}`}
              onClick={() => setActiveTab("insights")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
              </svg>
              Insights
            </button>
            <button
              className={`tab-button ${activeTab === "codebase" ? "active" : ""}`}
              onClick={() => setActiveTab("codebase")}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="currentColor"
                viewBox="0 0 16 16"
              >
                <path d="M10.478 1.647a.5.5 0 1 0-.956-.294l-4 13a.5.5 0 0 0 .956.294zM4.854 4.146a.5.5 0 0 1 0 .708L1.707 8l3.147 3.146a.5.5 0 0 1-.708.708l-3.5-3.5a.5.5 0 0 1 0-.708l3.5-3.5a.5.5 0 0 1 .708 0m6.292 0a.5.5 0 0 0 0 .708L14.293 8l-3.147 3.146a.5.5 0 0 0 .708.708l3.5-3.5a.5.5 0 0 0 0-.708l-3.5-3.5a.5.5 0 0 0-.708 0" />
              </svg>
              Code Base
            </button>
            <button
              className={`tab-button ${activeTab === "rag" ? "active" : ""}`}
              onClick={() => setActiveTab("rag")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              Documents
            </button>
            <button
              className={`tab-button ${activeTab === "research" ? "active" : ""}`}
              onClick={() => setActiveTab("research")}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                width={20}
                height={20}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                />
              </svg>
              Research
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
                activeTab === "cognitive" ? "active" : ""
              }`}
              onClick={() => setActiveTab("cognitive")}
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
              Cognitive
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
                activeTab === "learning" ? "active" : ""
              }`}
              onClick={() => setActiveTab("learning")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
                <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"></path>
              </svg>
              Learning
            </button>
            <button
              className={`tab-button ${
                activeTab === "ml-intelligence" ? "active" : ""
              }`}
              onClick={() => setActiveTab("ml-intelligence")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                <path d="M12 17h.01"></path>
              </svg>
              ML Intelligence
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
                activeTab === "experiments" ? "active" : ""
              }`}
              onClick={() => setActiveTab("experiments")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M9 3h6v2H9z"></path>
                <path d="M10 5v4l-4 8h12l-4-8V5"></path>
                <circle cx="12" cy="15" r="1"></circle>
              </svg>
              Experiments
            </button>
            <button
              className={`tab-button ${
                activeTab === "connectors" ? "active" : ""
              }`}
              onClick={() => setActiveTab("connectors")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
              </svg>
              Connectors
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
                activeTab === "telemetry" ? "active" : ""
              }`}
              onClick={() => setActiveTab("telemetry")}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
              </svg>
              Telemetry
            </button>
          </nav>
        </aside>

        {/* Tab Content */}
        <main className="main-content">
          {activeTab === "chat" && <ChatTab />}
          {activeTab === "governance" && <GovernanceTab />}
          {activeTab === "sandbox" && <SandboxTab />}
          {activeTab === "insights" && <InsightsTab />}
          {activeTab === "codebase" && <CodeBaseTab />}
          {activeTab === "rag" && <RAGTab />}
          {activeTab === "research" && <ResearchTab />}
          {activeTab === "api" && <APITab />}
          {activeTab === "librarian" && <LibrarianTab />}
          {activeTab === "cognitive" && <CognitiveTab />}
          {activeTab === "monitoring" && <MonitoringTab />}
          {activeTab === "version-control" && <VersionControl />}
          {activeTab === "notion" && <NotionTab />}
          {activeTab === "genesis" && <GenesisKeyTab />}
          {activeTab === "learning" && <LearningTab />}
          {activeTab === "ml-intelligence" && <MLIntelligenceTab />}
          {activeTab === "whitelist" && <WhitelistTab />}
          {activeTab === "experiments" && <ExperimentTab />}
          {activeTab === "connectors" && <ConnectorsTab />}
          {activeTab === "orchestration" && <OrchestrationTab />}
          {activeTab === "telemetry" && <TelemetryTab />}
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
