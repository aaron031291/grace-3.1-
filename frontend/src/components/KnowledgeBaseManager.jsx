import { useEffect, useState, useCallback } from "react";
import "./KnowledgeBaseManager.css";

const API_BASE = API_BASE_URL;

// Connector type icons (emoji placeholders)
const CONNECTOR_ICONS = {
  github: "G",
  gitlab: "GL",
  confluence: "C",
  notion: "N",
  jira: "J",
  slack: "S",
  google_drive: "GD",
  sharepoint: "SP",
  database: "DB",
  file_system: "FS",
  api: "API",
  rss: "RSS",
  web_scraper: "WS"
};

// Status colors
const getStatusColor = (status) => {
  switch (status) {
    case "active": return "#10b981";
    case "syncing": return "#3b82f6";
    case "pending": return "#f59e0b";
    case "error": return "#ef4444";
    case "inactive": return "#6b7280";
    default: return "#6b7280";
  }
};

// Connector Card
function ConnectorCard({ connector, onSync, onTest, onDelete, onSelect }) {
  const [syncing, setSyncing] = useState(false);
  const [testing, setTesting] = useState(false);

  const handleSync = async (e) => {
    e.stopPropagation();
    setSyncing(true);
    await onSync(connector.id);
    setSyncing(false);
  };

  const handleTest = async (e) => {
    e.stopPropagation();
    setTesting(true);
    await onTest(connector.id);
    setTesting(false);
  };

  return (
    <div className="connector-card" onClick={() => onSelect(connector)}>
      <div className="connector-header">
        <div className="connector-icon">
          {CONNECTOR_ICONS[connector.connector_type] || "?"}
        </div>
        <div className="connector-info">
          <span className="connector-name">{connector.name}</span>
          <span className="connector-type">{connector.connector_type}</span>
        </div>
        <span
          className="connector-status"
          style={{ backgroundColor: getStatusColor(connector.status) }}
        >
          {connector.status}
        </span>
      </div>

      {connector.description && (
        <p className="connector-description">{connector.description}</p>
      )}

      <div className="connector-stats">
        <div className="stat">
          <span className="stat-value">{connector.documents_synced || 0}</span>
          <span className="stat-label">Documents</span>
        </div>
        <div className="stat">
          <span className="stat-value">{connector.sync_frequency}</span>
          <span className="stat-label">Sync</span>
        </div>
      </div>

      {connector.last_sync && (
        <div className="connector-last-sync">
          Last sync: {new Date(connector.last_sync).toLocaleString()}
        </div>
      )}

      <div className="connector-actions">
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-sync"
        >
          {syncing ? "Syncing..." : "Sync"}
        </button>
        <button
          onClick={handleTest}
          disabled={testing}
          className="btn-test"
        >
          {testing ? "Testing..." : "Test"}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(connector.id); }}
          className="btn-delete"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

// Add Connector Form
function AddConnectorForm({ onAdd, onCancel }) {
  const [formData, setFormData] = useState({
    name: "",
    connector_type: "github",
    description: "",
    sync_frequency: "daily",
    enabled: true
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onAdd(formData);
  };

  return (
    <div className="add-connector-form">
      <h3>Add New Connector</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Connector name"
            required
          />
        </div>

        <div className="form-group">
          <label>Type</label>
          <select
            value={formData.connector_type}
            onChange={(e) => setFormData({ ...formData, connector_type: e.target.value })}
          >
            <option value="github">GitHub</option>
            <option value="gitlab">GitLab</option>
            <option value="confluence">Confluence</option>
            <option value="notion">Notion</option>
            <option value="jira">Jira</option>
            <option value="slack">Slack</option>
            <option value="google_drive">Google Drive</option>
            <option value="sharepoint">SharePoint</option>
            <option value="database">Database</option>
            <option value="file_system">File System</option>
            <option value="api">API</option>
            <option value="rss">RSS Feed</option>
            <option value="web_scraper">Web Scraper</option>
          </select>
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Optional description"
            rows={2}
          />
        </div>

        <div className="form-group">
          <label>Sync Frequency</label>
          <select
            value={formData.sync_frequency}
            onChange={(e) => setFormData({ ...formData, sync_frequency: e.target.value })}
          >
            <option value="realtime">Realtime</option>
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="manual">Manual</option>
          </select>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="btn-cancel">
            Cancel
          </button>
          <button type="submit" className="btn-add">
            Add Connector
          </button>
        </div>
      </form>
    </div>
  );
}

// Search Panel
function SearchPanel({ onSearch }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    const data = await onSearch(query);
    setResults(data);
    setLoading(false);
  };

  return (
    <div className="search-panel">
      <h4>Search Knowledge Base</h4>

      <div className="search-input">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents..."
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
        />
        <button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "..." : "Search"}
        </button>
      </div>

      {results && (
        <div className="search-results">
          <div className="results-header">
            Found {results.total_results} results in {results.search_time_ms?.toFixed(1)}ms
          </div>
          <div className="results-list">
            {results.results?.map((result, i) => (
              <div key={i} className="search-result">
                <div className="result-title">{result.title}</div>
                <div className="result-snippet">{result.snippet}</div>
                <div className="result-meta">
                  <span className="result-score">
                    Score: {Math.round(result.score * 100)}%
                  </span>
                  <span className="result-source">{result.source_type}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Stats Panel
function StatsPanel({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-panel">
      <h4>Knowledge Base Stats</h4>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.connectors?.total || 0}</span>
          <span className="stat-label">Connectors</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.connectors?.active || 0}</span>
          <span className="stat-label">Active</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.sources?.total || 0}</span>
          <span className="stat-label">Sources</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.documents?.total || 0}</span>
          <span className="stat-label">Documents</span>
        </div>
      </div>

      {stats.sync?.last_sync && (
        <div className="last-activity">
          Last sync: {new Date(stats.sync.last_sync).toLocaleString()}
        </div>
      )}
    </div>
  );
}

// Main Knowledge Base Manager Component
export default function KnowledgeBaseManager() {
  const [loading, setLoading] = useState(true);
  const [connectors, setConnectors] = useState([]);
  const [stats, setStats] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [error, setError] = useState(null);
  const [view, setView] = useState("connectors"); // connectors, search

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [connectorsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/knowledge-base/connectors`),
        fetch(`${API_BASE}/knowledge-base/stats`)
      ]);

      if (connectorsRes.ok) {
        setConnectors(await connectorsRes.json());
      }

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      console.error("Failed to fetch knowledge base data:", err);
      setError("Failed to load data. Make sure the API is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddConnector = async (config) => {
    try {
      const res = await fetch(`${API_BASE}/knowledge-base/connectors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      });

      if (res.ok) {
        setShowAddForm(false);
        fetchData();
      }
    } catch (err) {
      console.error("Failed to add connector:", err);
    }
  };

  const handleSync = async (connectorId) => {
    try {
      await fetch(`${API_BASE}/knowledge-base/connectors/${connectorId}/sync`, {
        method: "POST"
      });
      fetchData();
    } catch (err) {
      console.error("Sync failed:", err);
    }
  };

  const handleTest = async (connectorId) => {
    try {
      const res = await fetch(`${API_BASE}/knowledge-base/connectors/${connectorId}/test`, {
        method: "POST"
      });
      if (res.ok) {
        const result = await res.json();
        alert(`Connection test: ${result.connection_status}\nLatency: ${result.latency_ms}ms`);
      }
    } catch (err) {
      console.error("Test failed:", err);
    }
  };

  const handleDelete = async (connectorId) => {
    if (!window.confirm("Delete this connector?")) return;

    try {
      await fetch(`${API_BASE}/knowledge-base/connectors/${connectorId}`, {
        method: "DELETE"
      });
      fetchData();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleSearch = async (query) => {
    try {
      const res = await fetch(`${API_BASE}/knowledge-base/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 10 })
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
    return null;
  };

  if (loading && connectors.length === 0) {
    return (
      <div className="knowledge-base-manager">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading Knowledge Base Manager...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="knowledge-base-manager">
      <div className="manager-header">
        <div className="header-left">
          <h2>Knowledge Base Manager</h2>
          <p>Manage connectors and knowledge sources</p>
        </div>

        <div className="header-actions">
          <div className="view-tabs">
            <button
              className={view === "connectors" ? "active" : ""}
              onClick={() => setView("connectors")}
            >
              Connectors
            </button>
            <button
              className={view === "search" ? "active" : ""}
              onClick={() => setView("search")}
            >
              Search
            </button>
          </div>
          <button onClick={() => setShowAddForm(true)} className="btn-add-new">
            + Add Connector
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

      <div className="manager-content">
        <div className="content-main">
          {view === "connectors" && (
            <>
              {showAddForm ? (
                <AddConnectorForm
                  onAdd={handleAddConnector}
                  onCancel={() => setShowAddForm(false)}
                />
              ) : (
                <div className="connectors-section">
                  <h3>Connectors ({connectors.length})</h3>
                  <div className="connectors-grid">
                    {connectors.map((connector) => (
                      <ConnectorCard
                        key={connector.id}
                        connector={connector}
                        onSync={handleSync}
                        onTest={handleTest}
                        onDelete={handleDelete}
                        onSelect={setSelectedConnector}
                      />
                    ))}
                  </div>

                  {connectors.length === 0 && (
                    <div className="empty-state">
                      <p>No connectors configured yet.</p>
                      <p>Add a connector to start syncing knowledge.</p>
                      <button
                        onClick={() => setShowAddForm(true)}
                        className="btn-add-new"
                      >
                        Add First Connector
                      </button>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {view === "search" && (
            <SearchPanel onSearch={handleSearch} />
          )}
        </div>

        <div className="content-sidebar">
          <StatsPanel stats={stats} />

          {selectedConnector && (
            <div className="connector-details">
              <h4>Connector Details</h4>
              <div className="detail-item">
                <span className="detail-label">ID</span>
                <span className="detail-value">{selectedConnector.id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Created</span>
                <span className="detail-value">
                  {new Date(selectedConnector.created_at).toLocaleString()}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Updated</span>
                <span className="detail-value">
                  {new Date(selectedConnector.updated_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedConnector(null)}
                className="btn-close-details"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
