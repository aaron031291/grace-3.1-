import { useState, useEffect } from "react";
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

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [apiHealth, setApiHealth] = useState(null);

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
        </main>
      </div>
    </div>
  );
}

export default App;
