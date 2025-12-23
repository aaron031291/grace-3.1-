import { useState, useEffect } from "react";
import "./App.css";
import ChatTab from "./components/ChatTab";
import RAGTab from "./components/RAGTab";
import MonitoringTab from "./components/MonitoringTab";
import VersionControl from "./components/VersionControl";

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
          </nav>
        </aside>

        {/* Tab Content */}
        <main className="main-content">
          {activeTab === "chat" && <ChatTab />}
          {activeTab === "rag" && <RAGTab />}
          {activeTab === "monitoring" && <MonitoringTab />}
          {activeTab === "version-control" && <VersionControl />}
        </main>
      </div>
    </div>
  );
}

export default App;
