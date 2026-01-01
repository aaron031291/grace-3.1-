import { useState } from "react";
import "./RAGTab.css";
import FileBrowser from "./FileBrowser";

export default function RAGTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("files"); // files, search, vscode
  const [vscodePath, setVscodePath] = useState("");

  const API_BASE = "http://localhost:8000";

  // Handle opening VSCode
  const handleOpenVSCode = (currentPath) => {
    const basePath =
      "/home/umer/Public/projects/grace_3/backend/knowledge_base";
    const fullPath = currentPath ? `${basePath}/${currentPath}` : basePath;
    setVscodePath(fullPath);
    setActiveTab("vscode");
  };

  // Handle search
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setError("Please enter a search query");
      return;
    }

    setSearching(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/retrieve/search?query=${encodeURIComponent(
          searchQuery
        )}&limit=10&threshold=0.3`,
        { method: "POST" }
      );

      if (!response.ok) throw new Error("Search failed");
      const data = await response.json();
      setSearchResults(data.chunks || []);
    } catch (err) {
      setError(err.message);
      console.error("Search error:", err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="rag-tab">
      <div className="rag-container">
        {/* Tabs */}
        <div className="rag-tabs">
          <button
            className={`tab-button ${activeTab === "files" ? "active" : ""}`}
            onClick={() => setActiveTab("files")}
          >
            <span className="tab-icon">📁</span>
            Files
          </button>
          <button
            className={`tab-button ${activeTab === "search" ? "active" : ""}`}
            onClick={() => setActiveTab("search")}
          >
            <span className="tab-icon">🔍</span>
            Search
          </button>
          <button
            className={`tab-button ${activeTab === "vscode" ? "active" : ""}`}
            onClick={() => setActiveTab("vscode")}
          >
            <span className="tab-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#179ff1">
                {/* VS Code logo */}
                <path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.987 7.644A.999.999 0 0 0 .934 8.85L3.542 11.9.934 15.15a.999.999 0 0 0 .053 1.206l1.661 1.605a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.49 1.49 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.54A1.5 1.5 0 0 0 23.15 2.587z" />
              </svg>
            </span>
            VS Code
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Files Tab */}
        {activeTab === "files" && (
          <div className="tab-content files-tab">
            <FileBrowser onOpenVSCode={handleOpenVSCode} />
          </div>
        )}

        {/* Search Tab */}
        {activeTab === "search" && (
          <div className="tab-content search-tab">
            <h2>Search Documents</h2>
            <form onSubmit={handleSearch} className="search-form">
              <div className="search-input-group">
                <input
                  type="text"
                  placeholder="Enter search query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  disabled={searching}
                  className="search-input"
                />
                <button
                  type="submit"
                  disabled={searching}
                  className="search-button"
                >
                  {searching ? "Searching..." : "🔍 Search"}
                </button>
              </div>
            </form>

            {searchResults.length === 0 && !searching && (
              <div className="empty-state">
                <p>No search results yet</p>
                <p className="hint">
                  Enter a query to search through uploaded documents
                </p>
              </div>
            )}

            {searchResults.length > 0 && (
              <div className="search-results">
                <p className="results-count">
                  Found {searchResults.length} matching chunks
                </p>
                {searchResults.map((result, idx) => (
                  <div key={idx} className="search-result-card">
                    <div className="result-header">
                      <span className="score">
                        Score:{" "}
                        {result.score ? (result.score * 100).toFixed(0) : "?"}%
                      </span>
                      <span className="doc-ref">
                        {result.metadata?.filename ||
                          `Document ${result.document_id}`}
                      </span>
                    </div>
                    <p className="result-text">{result.text}</p>
                    <div className="result-meta">
                      <span>Chunk {result.chunk_index}</span>
                      <span>Doc ID: {result.document_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VSCode Tab */}
        {activeTab === "vscode" && (
          <div className="tab-content vscode-tab">
            <div className="vscode-container">
              <iframe
                src={`http://localhost:8080/?folder=${encodeURIComponent(
                  vscodePath
                )}`}
                className="vscode-iframe"
                title="VS Code"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
