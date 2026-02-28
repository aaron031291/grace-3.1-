import { useEffect, useState, useCallback } from "react";
import "./RepositoryManager.css";

const API_BASE = API_BASE_URL;

// Status colors
const getStatusColor = (status) => {
  switch (status) {
    case "completed": return "#10b981";
    case "in_progress": return "#3b82f6";
    case "pending": return "#f59e0b";
    case "failed": return "#ef4444";
    case "partial": return "#8b5cf6";
    case "outdated": return "#6b7280";
    default: return "#6b7280";
  }
};

// Priority colors
const getPriorityColor = (priority) => {
  switch (priority) {
    case "critical": return "#ef4444";
    case "high": return "#f59e0b";
    case "medium": return "#3b82f6";
    case "low": return "#6b7280";
    default: return "#6b7280";
  }
};

// Health score color
const getHealthColor = (score) => {
  if (score >= 0.8) return "#10b981";
  if (score >= 0.6) return "#3b82f6";
  if (score >= 0.4) return "#f59e0b";
  return "#ef4444";
};

// Repository Card
function RepositoryCard({ repo, onIngest, onSelect }) {
  const [ingesting, setIngesting] = useState(false);

  const handleIngest = async (e) => {
    e.stopPropagation();
    setIngesting(true);
    await onIngest(repo.id);
    setIngesting(false);
  };

  return (
    <div className="repository-card" onClick={() => onSelect(repo)}>
      <div className="repo-header">
        <div className="repo-info">
          <span className="repo-name">{repo.name}</span>
          <span className="repo-language">{repo.language}</span>
        </div>
        <div className="repo-badges">
          <span
            className="priority-badge"
            style={{ backgroundColor: getPriorityColor(repo.priority) }}
          >
            {repo.priority}
          </span>
          <span
            className="status-badge"
            style={{ backgroundColor: getStatusColor(repo.ingestion_status) }}
          >
            {repo.ingestion_status.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      {repo.description && (
        <p className="repo-description">{repo.description}</p>
      )}

      <div className="repo-stats">
        <div className="stat">
          <span className="stat-value">{repo.files_indexed || 0}</span>
          <span className="stat-label">Files</span>
        </div>
        <div className="stat">
          <span className="stat-value">{(repo.stars / 1000).toFixed(0)}k</span>
          <span className="stat-label">Stars</span>
        </div>
        <div className="stat">
          <span
            className="stat-value"
            style={{ color: getHealthColor(repo.health_score) }}
          >
            {Math.round(repo.health_score * 100)}%
          </span>
          <span className="stat-label">Health</span>
        </div>
      </div>

      {repo.tags && repo.tags.length > 0 && (
        <div className="repo-tags">
          {repo.tags.slice(0, 4).map((tag, i) => (
            <span key={i} className="tag">{tag}</span>
          ))}
        </div>
      )}

      <div className="repo-footer">
        <span className="repo-url">{repo.url}</span>
        <button
          onClick={handleIngest}
          disabled={ingesting || repo.ingestion_status === "in_progress"}
          className="btn-ingest"
        >
          {ingesting ? "Ingesting..." : "Ingest"}
        </button>
      </div>
    </div>
  );
}

// Filters Panel
function FiltersPanel({ filters, onChange }) {
  return (
    <div className="filters-panel">
      <div className="filter-group">
        <label>Status</label>
        <select
          value={filters.status || ""}
          onChange={(e) => onChange({ ...filters, status: e.target.value || null })}
        >
          <option value="">All</option>
          <option value="completed">Completed</option>
          <option value="in_progress">In Progress</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="partial">Partial</option>
          <option value="outdated">Outdated</option>
        </select>
      </div>

      <div className="filter-group">
        <label>Language</label>
        <select
          value={filters.language || ""}
          onChange={(e) => onChange({ ...filters, language: e.target.value || null })}
        >
          <option value="">All</option>
          <option value="Python">Python</option>
          <option value="JavaScript">JavaScript</option>
          <option value="TypeScript">TypeScript</option>
          <option value="Go">Go</option>
          <option value="Rust">Rust</option>
          <option value="Java">Java</option>
          <option value="C++">C++</option>
          <option value="Ruby">Ruby</option>
          <option value="PHP">PHP</option>
        </select>
      </div>

      <div className="filter-group">
        <label>Priority</label>
        <select
          value={filters.priority || ""}
          onChange={(e) => onChange({ ...filters, priority: e.target.value || null })}
        >
          <option value="">All</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>
    </div>
  );
}

// Stats Overview
function StatsOverview({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-overview">
      <div className="stat-card main">
        <span className="stat-value">{stats.total_repositories}</span>
        <span className="stat-label">Total Repositories</span>
      </div>

      <div className="stat-card">
        <span className="stat-value">{stats.total_files_indexed?.toLocaleString()}</span>
        <span className="stat-label">Files Indexed</span>
      </div>

      <div className="stat-card">
        <span
          className="stat-value"
          style={{ color: getHealthColor(stats.avg_health_score) }}
        >
          {Math.round(stats.avg_health_score * 100)}%
        </span>
        <span className="stat-label">Avg Health</span>
      </div>

      <div className="stat-card status-breakdown">
        <span className="stat-label">By Status</span>
        <div className="status-bars">
          {Object.entries(stats.by_status || {}).map(([status, count]) => (
            <div key={status} className="status-bar">
              <div
                className="bar-fill"
                style={{
                  width: `${(count / stats.total_repositories) * 100}%`,
                  backgroundColor: getStatusColor(status)
                }}
              />
              <span className="bar-label">{status}: {count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Language Stats
function LanguageStats({ languages }) {
  if (!languages) return null;

  const sortedLangs = Object.entries(languages)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);

  return (
    <div className="language-stats">
      <h4>Top Languages</h4>
      <div className="language-list">
        {sortedLangs.map(([lang, data]) => (
          <div key={lang} className="language-item">
            <span className="lang-name">{lang}</span>
            <span className="lang-count">{data.count} repos</span>
            <span className="lang-files">{data.files_indexed?.toLocaleString()} files</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Repository Details Panel
function RepositoryDetails({ repo, onClose, onIngest, onSetPriority }) {
  const [newPriority, setNewPriority] = useState(repo.priority);

  if (!repo) return null;

  const handleSetPriority = () => {
    onSetPriority(repo.id, newPriority);
  };

  return (
    <div className="repository-details">
      <div className="details-header">
        <h3>{repo.name}</h3>
        <button onClick={onClose} className="btn-close">Close</button>
      </div>

      <div className="details-section">
        <div className="detail-row">
          <span className="detail-label">URL</span>
          <a href={repo.url} target="_blank" rel="noopener noreferrer" className="detail-link">
            {repo.url}
          </a>
        </div>
        <div className="detail-row">
          <span className="detail-label">Language</span>
          <span className="detail-value">{repo.language}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Branch</span>
          <span className="detail-value">{repo.branch}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Stars</span>
          <span className="detail-value">{repo.stars?.toLocaleString()}</span>
        </div>
      </div>

      <div className="details-section">
        <h4>Ingestion Status</h4>
        <div className="detail-row">
          <span className="detail-label">Status</span>
          <span
            className="status-badge"
            style={{ backgroundColor: getStatusColor(repo.ingestion_status) }}
          >
            {repo.ingestion_status}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Files Indexed</span>
          <span className="detail-value">{repo.files_indexed?.toLocaleString()}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Last Commit</span>
          <span className="detail-value">{repo.last_commit || "N/A"}</span>
        </div>
        {repo.last_synced && (
          <div className="detail-row">
            <span className="detail-label">Last Synced</span>
            <span className="detail-value">
              {new Date(repo.last_synced).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      <div className="details-section">
        <h4>Priority</h4>
        <div className="priority-selector">
          <select value={newPriority} onChange={(e) => setNewPriority(e.target.value)}>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <button onClick={handleSetPriority} className="btn-set">
            Set Priority
          </button>
        </div>
      </div>

      {repo.tags && repo.tags.length > 0 && (
        <div className="details-section">
          <h4>Tags</h4>
          <div className="tags-list">
            {repo.tags.map((tag, i) => (
              <span key={i} className="tag">{tag}</span>
            ))}
          </div>
        </div>
      )}

      <div className="details-actions">
        <button
          onClick={() => onIngest(repo.id)}
          className="btn-ingest-large"
        >
          Trigger Ingestion
        </button>
      </div>
    </div>
  );
}

// Main Repository Manager Component
export default function RepositoryManager() {
  const [loading, setLoading] = useState(true);
  const [repositories, setRepositories] = useState([]);
  const [stats, setStats] = useState(null);
  const [languageStats, setLanguageStats] = useState(null);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [filters, setFilters] = useState({});
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.status) params.append("status", filters.status);
      if (filters.language) params.append("language", filters.language);
      if (filters.priority) params.append("priority", filters.priority);

      const [reposRes, statsRes, langRes] = await Promise.all([
        fetch(`${API_BASE}/repositories/?${params}`),
        fetch(`${API_BASE}/repositories/stats/overview`),
        fetch(`${API_BASE}/repositories/stats/languages`)
      ]);

      if (reposRes.ok) {
        setRepositories(await reposRes.json());
      }

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }

      if (langRes.ok) {
        const data = await langRes.json();
        setLanguageStats(data.languages);
      }
    } catch (err) {
      console.error("Failed to fetch repository data:", err);
      setError("Failed to load data. Make sure the API is running.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleIngest = async (repoId) => {
    try {
      await fetch(`${API_BASE}/repositories/${repoId}/ingest`, {
        method: "POST"
      });
      fetchData();
    } catch (err) {
      console.error("Ingestion failed:", err);
    }
  };

  const handleSetPriority = async (repoId, priority) => {
    try {
      await fetch(`${API_BASE}/repositories/${repoId}/priority`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ priority })
      });
      fetchData();
    } catch (err) {
      console.error("Failed to set priority:", err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchData();
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE}/repositories/search?query=${encodeURIComponent(searchQuery)}`
      );
      if (res.ok) {
        const data = await res.json();
        setRepositories(data.results || []);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  const handleIngestAll = async () => {
    if (!window.confirm("Ingest all repositories? This may take a while.")) return;

    try {
      await fetch(`${API_BASE}/repositories/ingest-all`, {
        method: "POST"
      });
      fetchData();
    } catch (err) {
      console.error("Bulk ingestion failed:", err);
    }
  };

  // Filter repositories by search
  const filteredRepos = repositories;

  if (loading && repositories.length === 0) {
    return (
      <div className="repository-manager">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading Repository Manager...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="repository-manager">
      <div className="manager-header">
        <div className="header-left">
          <h2>Repository Manager</h2>
          <p>Manage enterprise repositories and ingestion</p>
        </div>

        <div className="header-actions">
          <div className="search-box">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search repositories..."
              onKeyPress={(e) => e.key === "Enter" && handleSearch()}
            />
            <button onClick={handleSearch}>Search</button>
          </div>
          <button onClick={handleIngestAll} className="btn-ingest-all">
            Ingest All
          </button>
          <button onClick={fetchData} className="btn-refresh">
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <StatsOverview stats={stats} />

      <div className="manager-content">
        <div className="content-main">
          <div className="toolbar">
            <FiltersPanel filters={filters} onChange={setFilters} />
            <span className="repo-count">{filteredRepos.length} repositories</span>
          </div>

          <div className="repositories-grid">
            {filteredRepos.map((repo) => (
              <RepositoryCard
                key={repo.id}
                repo={repo}
                onIngest={handleIngest}
                onSelect={setSelectedRepo}
              />
            ))}
          </div>

          {filteredRepos.length === 0 && (
            <div className="empty-state">
              <p>No repositories found.</p>
              <p>Try adjusting your filters or search query.</p>
            </div>
          )}
        </div>

        <div className="content-sidebar">
          {selectedRepo ? (
            <RepositoryDetails
              repo={selectedRepo}
              onClose={() => setSelectedRepo(null)}
              onIngest={handleIngest}
              onSetPriority={handleSetPriority}
            />
          ) : (
            <LanguageStats languages={languageStats} />
          )}
        </div>
      </div>
    </div>
  );
}
