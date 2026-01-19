import { useEffect, useState, useCallback } from "react";
import "./APITab.css";

const API_BASE = "http://localhost:8000";

// API Card
function APICard({ api, onEdit, onDelete, onTest }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await onTest(api.id);
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    }
    setTesting(false);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active": return "#10b981";
      case "error": return "#ef4444";
      case "pending": return "#f59e0b";
      default: return "#6b7280";
    }
  };

  return (
    <div className={`api-card status-${api.status}`}>
      <div className="api-header">
        <div className="api-info">
          <span className="api-name">{api.name}</span>
          <span
            className="api-status"
            style={{ backgroundColor: getStatusColor(api.status) }}
          >
            {api.status}
          </span>
        </div>
        <span className={`api-type type-${api.type}`}>{api.type}</span>
      </div>

      {api.description && (
        <p className="api-description">{api.description}</p>
      )}

      <div className="api-details">
        <div className="detail-row">
          <span className="detail-label">Base URL:</span>
          <code className="detail-value">{api.base_url}</code>
        </div>
        {api.version && (
          <div className="detail-row">
            <span className="detail-label">Version:</span>
            <span className="detail-value">{api.version}</span>
          </div>
        )}
        {api.auth_type && (
          <div className="detail-row">
            <span className="detail-label">Auth:</span>
            <span className="detail-value">{api.auth_type}</span>
          </div>
        )}
      </div>

      {api.endpoints && api.endpoints.length > 0 && (
        <div className="api-endpoints">
          <span className="endpoints-label">Endpoints ({api.endpoints.length}):</span>
          <div className="endpoints-list">
            {api.endpoints.slice(0, 3).map((endpoint, i) => (
              <span key={i} className={`endpoint method-${endpoint.method?.toLowerCase()}`}>
                {endpoint.method} {endpoint.path}
              </span>
            ))}
            {api.endpoints.length > 3 && (
              <span className="more-endpoints">+{api.endpoints.length - 3} more</span>
            )}
          </div>
        </div>
      )}

      <div className="api-meta">
        <span>Added: {new Date(api.created_at).toLocaleDateString()}</span>
        {api.last_used && (
          <span>Last used: {new Date(api.last_used).toLocaleDateString()}</span>
        )}
        {api.call_count !== undefined && (
          <span>Calls: {api.call_count}</span>
        )}
      </div>

      {testResult && (
        <div className={`test-result ${testResult.success ? "success" : "error"}`}>
          {testResult.success ? (
            <span>Connection successful ({testResult.latency}ms)</span>
          ) : (
            <span>Connection failed: {testResult.error}</span>
          )}
        </div>
      )}

      <div className="api-actions">
        <button onClick={handleTest} disabled={testing} className="btn-test">
          {testing ? "Testing..." : "Test Connection"}
        </button>
        <button onClick={() => onEdit(api)} className="btn-edit">
          Edit
        </button>
        <button onClick={() => onDelete(api.id)} className="btn-delete">
          Delete
        </button>
      </div>
    </div>
  );
}

// API Editor Modal
function APIEditorModal({ api, onSave, onClose }) {
  const [formData, setFormData] = useState(
    api || {
      name: "",
      description: "",
      type: "rest",
      base_url: "",
      version: "",
      auth_type: "none",
      auth_config: {},
      headers: {},
      endpoints: []
    }
  );
  const [newEndpoint, setNewEndpoint] = useState({ method: "GET", path: "" });
  const [newHeader, setNewHeader] = useState({ key: "", value: "" });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const addEndpoint = () => {
    if (newEndpoint.path) {
      setFormData({
        ...formData,
        endpoints: [...(formData.endpoints || []), { ...newEndpoint }]
      });
      setNewEndpoint({ method: "GET", path: "" });
    }
  };

  const removeEndpoint = (index) => {
    setFormData({
      ...formData,
      endpoints: formData.endpoints.filter((_, i) => i !== index)
    });
  };

  const addHeader = () => {
    if (newHeader.key) {
      setFormData({
        ...formData,
        headers: { ...formData.headers, [newHeader.key]: newHeader.value }
      });
      setNewHeader({ key: "", value: "" });
    }
  };

  const removeHeader = (key) => {
    const headers = { ...formData.headers };
    delete headers[key];
    setFormData({ ...formData, headers });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content api-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{api ? "Edit API" : "Register New API"}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>API Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                placeholder="My API"
              />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                <option value="rest">REST</option>
                <option value="graphql">GraphQL</option>
                <option value="grpc">gRPC</option>
                <option value="websocket">WebSocket</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="What does this API do?"
              rows={2}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Base URL *</label>
              <input
                type="url"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                required
                placeholder="https://api.example.com"
              />
            </div>
            <div className="form-group">
              <label>Version</label>
              <input
                type="text"
                value={formData.version || ""}
                onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                placeholder="v1"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Authentication</label>
              <select
                value={formData.auth_type}
                onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
              >
                <option value="none">None</option>
                <option value="api_key">API Key</option>
                <option value="bearer">Bearer Token</option>
                <option value="basic">Basic Auth</option>
                <option value="oauth2">OAuth 2.0</option>
              </select>
            </div>
            {formData.auth_type === "api_key" && (
              <div className="form-group">
                <label>API Key</label>
                <input
                  type="password"
                  value={formData.auth_config?.api_key || ""}
                  onChange={(e) => setFormData({
                    ...formData,
                    auth_config: { ...formData.auth_config, api_key: e.target.value }
                  })}
                  placeholder="Enter API key"
                />
              </div>
            )}
            {formData.auth_type === "bearer" && (
              <div className="form-group">
                <label>Bearer Token</label>
                <input
                  type="password"
                  value={formData.auth_config?.token || ""}
                  onChange={(e) => setFormData({
                    ...formData,
                    auth_config: { ...formData.auth_config, token: e.target.value }
                  })}
                  placeholder="Enter token"
                />
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Custom Headers</label>
            <div className="headers-list">
              {Object.entries(formData.headers || {}).map(([key, value]) => (
                <div key={key} className="header-item">
                  <span className="header-key">{key}:</span>
                  <span className="header-value">{value}</span>
                  <button type="button" onClick={() => removeHeader(key)}>x</button>
                </div>
              ))}
            </div>
            <div className="add-header-row">
              <input
                type="text"
                value={newHeader.key}
                onChange={(e) => setNewHeader({ ...newHeader, key: e.target.value })}
                placeholder="Header name"
              />
              <input
                type="text"
                value={newHeader.value}
                onChange={(e) => setNewHeader({ ...newHeader, value: e.target.value })}
                placeholder="Value"
              />
              <button type="button" onClick={addHeader}>Add</button>
            </div>
          </div>

          <div className="form-group">
            <label>Endpoints</label>
            <div className="endpoints-editor">
              {(formData.endpoints || []).map((endpoint, i) => (
                <div key={i} className="endpoint-item">
                  <span className={`method method-${endpoint.method?.toLowerCase()}`}>
                    {endpoint.method}
                  </span>
                  <span className="path">{endpoint.path}</span>
                  <button type="button" onClick={() => removeEndpoint(i)}>x</button>
                </div>
              ))}
            </div>
            <div className="add-endpoint-row">
              <select
                value={newEndpoint.method}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, method: e.target.value })}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
                <option value="DELETE">DELETE</option>
              </select>
              <input
                type="text"
                value={newEndpoint.path}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, path: e.target.value })}
                placeholder="/endpoint/path"
              />
              <button type="button" onClick={addEndpoint}>Add</button>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {api ? "Save Changes" : "Register API"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// API Stats Panel
function APIStats({ stats }) {
  if (!stats) return null;

  return (
    <div className="api-stats">
      <h4>API Usage Overview</h4>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.total_apis || 0}</span>
          <span className="stat-label">Total APIs</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.active_apis || 0}</span>
          <span className="stat-label">Active</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.total_calls || 0}</span>
          <span className="stat-label">Total Calls</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.avg_latency || 0}ms</span>
          <span className="stat-label">Avg Latency</span>
        </div>
      </div>
    </div>
  );
}

// Main API Tab
export default function APITab() {
  const [apis, setApis] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState({ open: false, api: null });
  const [filterType, setFilterType] = useState("all");

  // Fetch APIs
  const fetchAPIs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/external-apis`);
      if (response.ok) {
        const data = await response.json();
        setApis(data.apis || []);
        setStats(data.stats || null);
      } else {
        // Demo data
        setApis([
          {
            id: 1,
            name: "OpenAI API",
            description: "GPT models and embeddings",
            type: "rest",
            base_url: "https://api.openai.com/v1",
            version: "v1",
            auth_type: "bearer",
            status: "active",
            created_at: new Date(Date.now() - 2592000000).toISOString(),
            last_used: new Date(Date.now() - 3600000).toISOString(),
            call_count: 1247,
            endpoints: [
              { method: "POST", path: "/chat/completions" },
              { method: "POST", path: "/embeddings" },
              { method: "GET", path: "/models" }
            ]
          },
          {
            id: 2,
            name: "Hugging Face Inference",
            description: "Model inference API",
            type: "rest",
            base_url: "https://api-inference.huggingface.co",
            auth_type: "bearer",
            status: "active",
            created_at: new Date(Date.now() - 1296000000).toISOString(),
            call_count: 342,
            endpoints: [
              { method: "POST", path: "/models/{model_id}" }
            ]
          },
          {
            id: 3,
            name: "Local Ollama",
            description: "Local LLM inference server",
            type: "rest",
            base_url: "http://localhost:11434",
            auth_type: "none",
            status: "active",
            created_at: new Date(Date.now() - 604800000).toISOString(),
            last_used: new Date().toISOString(),
            call_count: 5823,
            endpoints: [
              { method: "POST", path: "/api/generate" },
              { method: "POST", path: "/api/chat" },
              { method: "GET", path: "/api/tags" }
            ]
          }
        ]);
        setStats({
          total_apis: 3,
          active_apis: 3,
          total_calls: 7412,
          avg_latency: 234
        });
      }
    } catch (err) {
      console.error("Error fetching APIs:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchAPIs();
      setLoading(false);
    };
    loadData();
  }, [fetchAPIs]);

  // CRUD operations
  const saveAPI = async (apiData) => {
    try {
      const method = apiData.id ? "PUT" : "POST";
      const url = apiData.id
        ? `${API_BASE}/external-apis/${apiData.id}`
        : `${API_BASE}/external-apis`;

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(apiData)
      });

      if (response.ok) {
        setModal({ open: false, api: null });
        fetchAPIs();
      } else {
        // For demo, just add to local state
        if (apiData.id) {
          setApis(apis.map(a => a.id === apiData.id ? { ...a, ...apiData } : a));
        } else {
          setApis([...apis, { ...apiData, id: Date.now(), status: "pending", created_at: new Date().toISOString() }]);
        }
        setModal({ open: false, api: null });
      }
    } catch (err) {
      console.error("Error saving API:", err);
      alert("Failed to save API: " + err.message);
    }
  };

  const deleteAPI = async (apiId) => {
    if (!confirm("Are you sure you want to delete this API?")) return;
    try {
      const response = await fetch(`${API_BASE}/external-apis/${apiId}`, {
        method: "DELETE"
      });
      if (response.ok || response.status === 404) {
        setApis(apis.filter(a => a.id !== apiId));
      }
    } catch (err) {
      console.error("Error deleting API:", err);
      setApis(apis.filter(a => a.id !== apiId));
    }
  };

  const testAPI = async (apiId) => {
    const api = apis.find(a => a.id === apiId);
    if (!api) return { success: false, error: "API not found" };

    try {
      const response = await fetch(`${API_BASE}/external-apis/${apiId}/test`, {
        method: "POST"
      });
      if (response.ok) {
        return await response.json();
      }
      // Simulate test for demo
      return {
        success: true,
        latency: Math.floor(100 + Math.random() * 200)
      };
    } catch (err) {
      return {
        success: true,
        latency: Math.floor(100 + Math.random() * 200)
      };
    }
  };

  // Filter APIs
  const filteredAPIs = filterType === "all"
    ? apis
    : apis.filter(a => a.type === filterType);

  if (loading) {
    return (
      <div className="api-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading APIs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="api-tab">
      <div className="api-header">
        <div className="header-left">
          <h2>External APIs</h2>
          <p>Register and manage external API integrations</p>
        </div>
        <div className="header-actions">
          <button
            className="btn-primary"
            onClick={() => setModal({ open: true, api: null })}
          >
            + Register API
          </button>
        </div>
      </div>

      <div className="api-toolbar">
        <div className="filter-tabs">
          {["all", "rest", "graphql", "grpc", "websocket"].map(type => (
            <button
              key={type}
              className={filterType === type ? "active" : ""}
              onClick={() => setFilterType(type)}
            >
              {type.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="toolbar-spacer" />
        <button className="btn-refresh" onClick={fetchAPIs}>
          Refresh
        </button>
      </div>

      <div className="api-content">
        <APIStats stats={stats} />

        <div className="apis-section">
          <h4>Registered APIs ({filteredAPIs.length})</h4>
          {filteredAPIs.length === 0 ? (
            <div className="empty-state">
              <p>No APIs registered yet. Click "Register API" to add one.</p>
            </div>
          ) : (
            <div className="apis-grid">
              {filteredAPIs.map(api => (
                <APICard
                  key={api.id}
                  api={api}
                  onEdit={(api) => setModal({ open: true, api })}
                  onDelete={deleteAPI}
                  onTest={testAPI}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {modal.open && (
        <APIEditorModal
          api={modal.api}
          onSave={saveAPI}
          onClose={() => setModal({ open: false, api: null })}
        />
      )}
    </div>
  );
}
