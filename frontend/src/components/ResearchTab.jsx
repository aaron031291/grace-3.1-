import { useEffect, useState, useCallback } from "react";
import "./ResearchTab.css";

const API_BASE = "http://localhost:8000";

// Repository Card
function RepositoryCard({ repo, onIngest, isIngesting }) {
  return (
    <div className={`repo-card ${repo.ingested ? "ingested" : ""}`}>
      <div className="repo-header">
        <span className="repo-name">{repo.name}</span>
        {repo.ingested && <span className="ingested-badge">Ingested</span>}
      </div>

      {repo.description && (
        <p className="repo-description">{repo.description}</p>
      )}

      <div className="repo-meta">
        {repo.language && <span className="repo-lang">{repo.language}</span>}
        {repo.stars !== undefined && (
          <span className="repo-stars">{repo.stars} stars</span>
        )}
        {repo.last_updated && (
          <span className="repo-updated">
            Updated: {new Date(repo.last_updated).toLocaleDateString()}
          </span>
        )}
      </div>

      {repo.url && (
        <a href={repo.url} target="_blank" rel="noopener noreferrer" className="repo-link">
          View Repository
        </a>
      )}

      {!repo.ingested && (
        <button
          className="btn-ingest"
          onClick={() => onIngest(repo)}
          disabled={isIngesting}
        >
          {isIngesting ? "Ingesting..." : "Ingest to Knowledge Base"}
        </button>
      )}
    </div>
  );
}

// Knowledge Entry Card
function KnowledgeEntryCard({ entry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="knowledge-card">
      <div className="knowledge-header" onClick={() => setExpanded(!expanded)}>
        <span className="knowledge-title">{entry.title || entry.filename}</span>
        <span className="knowledge-source">{entry.source}</span>
        <span className="expand-icon">{expanded ? "-" : "+"}</span>
      </div>

      {expanded && (
        <div className="knowledge-content">
          {entry.summary && (
            <div className="knowledge-summary">
              <h5>Summary</h5>
              <p>{entry.summary}</p>
            </div>
          )}

          {entry.key_concepts && entry.key_concepts.length > 0 && (
            <div className="knowledge-concepts">
              <h5>Key Concepts</h5>
              <div className="concepts-list">
                {entry.key_concepts.map((concept, i) => (
                  <span key={i} className="concept-tag">{concept}</span>
                ))}
              </div>
            </div>
          )}

          {entry.trust_score !== undefined && (
            <div className="knowledge-trust">
              Trust Score: {Math.round(entry.trust_score * 100)}%
            </div>
          )}

          <div className="knowledge-meta">
            <span>Created: {new Date(entry.created_at).toLocaleString()}</span>
            {entry.file_path && <span>Path: {entry.file_path}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

// Search Panel
function SearchPanel({ onSearch, loading }) {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("semantic");

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query, searchType);
    }
  };

  return (
    <div className="search-panel">
      <h4>Knowledge Base Search</h4>
      <div className="search-input-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search the knowledge base..."
        />
        <select value={searchType} onChange={(e) => setSearchType(e.target.value)}>
          <option value="semantic">Semantic Search</option>
          <option value="keyword">Keyword Search</option>
          <option value="hybrid">Hybrid Search</option>
        </select>
        <button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
    </div>
  );
}

// Clone Repositories Panel
function ClonePanel({ onStartCloning, cloningStatus }) {
  return (
    <div className="clone-panel">
      <h4>AI Research Repository Ingestion</h4>
      <p className="description">
        Clone and ingest curated AI research repositories into the knowledge base.
        This includes papers, implementations, and documentation from leading AI research.
      </p>

      <div className="clone-status">
        {cloningStatus ? (
          <div className="status-info">
            <span className={`status-badge ${cloningStatus.status}`}>
              {cloningStatus.status}
            </span>
            <span className="status-message">{cloningStatus.message}</span>
            {cloningStatus.progress !== undefined && (
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${cloningStatus.progress}%` }}
                />
              </div>
            )}
          </div>
        ) : (
          <p>No active ingestion process</p>
        )}
      </div>

      <button
        className="btn-start-clone"
        onClick={onStartCloning}
        disabled={cloningStatus?.status === "running"}
      >
        Start Repository Ingestion
      </button>
    </div>
  );
}

// Categories Overview
function CategoriesOverview({ categories }) {
  if (!categories || Object.keys(categories).length === 0) {
    return null;
  }

  return (
    <div className="categories-overview">
      <h4>Knowledge Categories</h4>
      <div className="categories-grid">
        {Object.entries(categories).map(([category, count]) => (
          <div key={category} className="category-card">
            <span className="category-name">{category}</span>
            <span className="category-count">{count} entries</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main Research Tab
export default function ResearchTab() {
  const [activeView, setActiveView] = useState("browse");
  const [repositories, setRepositories] = useState([]);
  const [knowledgeEntries, setKnowledgeEntries] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [categories, setCategories] = useState({});
  const [stats, setStats] = useState(null);
  const [cloningStatus, setCloningStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [ingestingRepo, setIngestingRepo] = useState(null);

  // Fetch repositories list
  const fetchRepositories = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/layer1/knowledge-base/repositories`);
      if (response.ok) {
        const data = await response.json();
        setRepositories(data.repositories || []);
      } else {
        // Fallback to predefined list
        setRepositories([
          { name: "transformers", description: "State-of-the-art ML for NLP", language: "Python", ingested: false },
          { name: "langchain", description: "Building applications with LLMs", language: "Python", ingested: false },
          { name: "llama", description: "Inference code for LLaMA models", language: "Python", ingested: false },
          { name: "stable-diffusion", description: "Latent text-to-image diffusion", language: "Python", ingested: false },
        ]);
      }
    } catch (err) {
      console.error("Error fetching repositories:", err);
    }
  }, []);

  // Fetch knowledge entries
  const fetchKnowledgeEntries = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/layer1/knowledge-base/entries?limit=50`);
      if (response.ok) {
        const data = await response.json();
        setKnowledgeEntries(data.entries || []);
        setCategories(data.categories || {});
      }
    } catch (err) {
      console.error("Error fetching knowledge entries:", err);
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/statistics`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }, []);

  // Check cloning status
  const checkCloningStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/layer1/knowledge-base/cloning-status`);
      if (response.ok) {
        const data = await response.json();
        setCloningStatus(data);
      }
    } catch (err) {
      // Ignore - endpoint may not exist
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchRepositories(),
        fetchKnowledgeEntries(),
        fetchStats(),
        checkCloningStatus()
      ]);
      setLoading(false);
    };
    loadData();
  }, [fetchRepositories, fetchKnowledgeEntries, fetchStats, checkCloningStatus]);

  // Search knowledge base
  const searchKnowledgeBase = async (query, searchType) => {
    setSearchLoading(true);
    try {
      const response = await fetch(`${API_BASE}/rag/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          search_type: searchType,
          limit: 20
        })
      });
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
    setSearchLoading(false);
  };

  // Ingest repository
  const ingestRepository = async (repo) => {
    setIngestingRepo(repo.name);
    try {
      const response = await fetch(`${API_BASE}/layer1/knowledge-base/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository_name: repo.name,
          repository_url: repo.url
        })
      });
      if (response.ok) {
        // Refresh repositories list
        fetchRepositories();
        fetchKnowledgeEntries();
      }
    } catch (err) {
      console.error("Ingestion failed:", err);
      alert("Failed to ingest repository: " + err.message);
    }
    setIngestingRepo(null);
  };

  // Start bulk cloning
  const startCloning = async () => {
    try {
      const response = await fetch(`${API_BASE}/layer1/knowledge-base/start-cloning`, {
        method: "POST"
      });
      if (response.ok) {
        checkCloningStatus();
        // Poll for status updates
        const interval = setInterval(async () => {
          const status = await checkCloningStatus();
          if (status?.status === "completed" || status?.status === "failed") {
            clearInterval(interval);
            fetchRepositories();
            fetchKnowledgeEntries();
          }
        }, 5000);
      }
    } catch (err) {
      console.error("Failed to start cloning:", err);
      alert("Failed to start repository cloning");
    }
  };

  if (loading) {
    return (
      <div className="research-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Research Hub...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="research-tab">
      <div className="research-header">
        <div className="header-left">
          <h2>Research Hub</h2>
          <p>AI research knowledge base and repository management</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value">{repositories.length}</span>
            <span className="stat-label">Repositories</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{knowledgeEntries.length}</span>
            <span className="stat-label">Knowledge Entries</span>
          </div>
          {stats && (
            <div className="stat-item">
              <span className="stat-value">{stats.documents_processed || 0}</span>
              <span className="stat-label">Documents</span>
            </div>
          )}
        </div>
      </div>

      <div className="research-toolbar">
        <div className="view-tabs">
          <button
            className={activeView === "browse" ? "active" : ""}
            onClick={() => setActiveView("browse")}
          >
            Browse
          </button>
          <button
            className={activeView === "search" ? "active" : ""}
            onClick={() => setActiveView("search")}
          >
            Search
          </button>
          <button
            className={activeView === "repositories" ? "active" : ""}
            onClick={() => setActiveView("repositories")}
          >
            Repositories
          </button>
          <button
            className={activeView === "ingest" ? "active" : ""}
            onClick={() => setActiveView("ingest")}
          >
            Ingest
          </button>
        </div>
        <div className="toolbar-spacer" />
        <button className="btn-refresh" onClick={() => {
          fetchRepositories();
          fetchKnowledgeEntries();
          fetchStats();
        }}>
          Refresh
        </button>
      </div>

      <div className="research-content">
        {activeView === "browse" && (
          <div className="browse-view">
            <CategoriesOverview categories={categories} />

            <div className="knowledge-list">
              <h4>Recent Knowledge Entries</h4>
              {knowledgeEntries.length === 0 ? (
                <div className="empty-state">
                  <p>No knowledge entries yet. Ingest repositories to populate the knowledge base.</p>
                </div>
              ) : (
                knowledgeEntries.map((entry, i) => (
                  <KnowledgeEntryCard key={entry.id || i} entry={entry} />
                ))
              )}
            </div>
          </div>
        )}

        {activeView === "search" && (
          <div className="search-view">
            <SearchPanel onSearch={searchKnowledgeBase} loading={searchLoading} />

            <div className="search-results">
              <h4>Search Results ({searchResults.length})</h4>
              {searchResults.length === 0 ? (
                <div className="empty-state">
                  <p>Enter a query to search the knowledge base</p>
                </div>
              ) : (
                searchResults.map((result, i) => (
                  <div key={i} className="search-result-card">
                    <div className="result-header">
                      <span className="result-title">{result.title || result.filename}</span>
                      <span className="result-score">
                        {Math.round((result.score || result.similarity) * 100)}% match
                      </span>
                    </div>
                    <p className="result-content">{result.content?.slice(0, 300)}...</p>
                    <div className="result-meta">
                      <span>{result.source}</span>
                      {result.file_path && <span>{result.file_path}</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeView === "repositories" && (
          <div className="repositories-view">
            <h4>AI Research Repositories</h4>
            <div className="repos-grid">
              {repositories.map((repo, i) => (
                <RepositoryCard
                  key={repo.name || i}
                  repo={repo}
                  onIngest={ingestRepository}
                  isIngesting={ingestingRepo === repo.name}
                />
              ))}
            </div>
          </div>
        )}

        {activeView === "ingest" && (
          <div className="ingest-view">
            <ClonePanel
              onStartCloning={startCloning}
              cloningStatus={cloningStatus}
            />
          </div>
        )}
      </div>
    </div>
  );
}
