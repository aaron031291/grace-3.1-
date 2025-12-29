import { useState } from "react";
import "./RAGTab.css";
import FileBrowser from "./FileBrowser";

export default function RAGTab() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("files"); // files, search

  const API_BASE = "http://localhost:8000";

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
            <FileBrowser />
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
      </div>
    </div>
  );
}
