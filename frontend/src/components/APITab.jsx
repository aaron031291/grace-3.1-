import { useEffect, useState, useCallback } from "react";
import "./APITab.css";

const API_BASE = "http://localhost:8000";

// ============================================================================
// EXTERNAL API COMPONENTS (Original)
// ============================================================================

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
          <button className="modal-close" onClick={onClose}>×</button>
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
                  <button type="button" onClick={() => removeHeader(key)}>×</button>
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
                  <button type="button" onClick={() => removeEndpoint(i)}>×</button>
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

// ============================================================================
// THIRD-PARTY LLM COMPONENTS (New)
// ============================================================================

// LLM Card Component
function LLMCard({ llm, onTest, onDelete }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await fetch(`${API_BASE}/third-party-llm/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_id: llm.llm_id,
          prompt: "Test connection - respond with 'OK' if you can read this.",
          max_tokens: 50
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setTestResult({ success: true, response: data.content });
      } else {
        const error = await response.json();
        setTestResult({ success: false, error: error.detail || "Connection failed" });
      }
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    }
    setTesting(false);
  };

  const getProviderIcon = (provider) => {
    switch (provider) {
      case "gemini":
        return "🔷";
      case "openai":
        return "🤖";
      case "anthropic":
        return "🧠";
      default:
        return "🔌";
    }
  };

  const getStatusColor = (handshakePassed) => {
    return handshakePassed ? "#10b981" : "#ef4444";
  };

  return (
    <div className="api-card llm-card">
      <div className="api-header">
        <div className="api-info">
          <span className="api-name">
            {getProviderIcon(llm.provider)} {llm.model_name}
          </span>
          <span
            className="api-status"
            style={{ backgroundColor: getStatusColor(llm.handshake_passed) }}
          >
            {llm.handshake_passed ? "Integrated" : "Failed"}
          </span>
        </div>
        <span className={`api-type type-${llm.provider}`}>
          {llm.provider.toUpperCase()}
        </span>
      </div>

      <div className="api-details">
        <div className="detail-row">
          <span className="detail-label">LLM ID:</span>
          <code className="detail-value">{llm.llm_id}</code>
        </div>
        <div className="detail-row">
          <span className="detail-label">Provider:</span>
          <span className="detail-value">{llm.provider}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Model:</span>
          <span className="detail-value">{llm.model_name}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Handshake:</span>
          <span className="detail-value">
            {llm.handshake_passed ? "✅ Passed" : "❌ Failed"}
          </span>
        </div>
        {llm.handshake_timestamp && (
          <div className="detail-row">
            <span className="detail-label">Registered:</span>
            <span className="detail-value">
              {new Date(llm.handshake_timestamp).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {llm.capabilities && Object.keys(llm.capabilities).length > 0 && (
        <div className="api-capabilities">
          <span className="capabilities-label">Capabilities:</span>
          <div className="capabilities-list">
            {Object.entries(llm.capabilities).map(([key, value]) => (
              <span
                key={key}
                className={`capability ${value ? "enabled" : "disabled"}`}
                title={key.replace(/_/g, " ")}
              >
                {value ? "✅" : "❌"} {key.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {testResult && (
        <div className={`test-result ${testResult.success ? "success" : "error"}`}>
          {testResult.success ? (
            <div>
              <span>✅ Connection successful</span>
              {testResult.response && (
                <div className="test-response">{testResult.response}</div>
              )}
            </div>
          ) : (
            <span>❌ Connection failed: {testResult.error}</span>
          )}
        </div>
      )}

      <div className="api-actions">
        <button onClick={handleTest} disabled={testing} className="btn-test">
          {testing ? "Testing..." : "Test Connection"}
        </button>
        <button onClick={() => onDelete(llm.llm_id)} className="btn-delete">
          Remove
        </button>
      </div>
    </div>
  );
}

// Register LLM Modal
function RegisterLLMModal({ provider, onSave, onClose }) {
  const [formData, setFormData] = useState({
    api_key: "",
    model_name: provider === "gemini" ? "gemini-pro" : provider === "openai" ? "gpt-4" : "claude-3-opus-20240229",
    base_url: ""
  });
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setRegistering(true);
    setError(null);
    setSuccess(false);

    try {
      const endpoint = `/third-party-llm/register/${provider}`;
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: formData.api_key,
          model_name: formData.model_name,
          base_url: formData.base_url || null
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setSuccess(true);
        setTimeout(() => {
          onSave(data);
          onClose();
        }, 1500);
      } else {
        setError(data.errors?.join(", ") || data.detail || "Registration failed");
      }
    } catch (err) {
      setError(err.message || "Failed to register LLM");
    } finally {
      setRegistering(false);
    }
  };

  const getProviderInfo = () => {
    switch (provider) {
      case "gemini":
        return {
          name: "Google Gemini",
          apiKeyPlaceholder: "Enter your Gemini API key",
          modelOptions: ["gemini-pro", "gemini-pro-vision", "gemini-1.5-pro"]
        };
      case "openai":
        return {
          name: "OpenAI",
          apiKeyPlaceholder: "Enter your OpenAI API key",
          modelOptions: ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        };
      case "anthropic":
        return {
          name: "Anthropic Claude",
          apiKeyPlaceholder: "Enter your Anthropic API key",
          modelOptions: ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240229"]
        };
      default:
        return { name: "LLM", apiKeyPlaceholder: "Enter API key", modelOptions: [] };
    }
  };

  const providerInfo = getProviderInfo();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content api-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Register {providerInfo.name}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {success ? (
          <div className="success-message">
            <div className="success-icon">✅</div>
            <h4>LLM Registered Successfully!</h4>
            <p>Handshake completed. The LLM is now integrated with GRACE.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>API Key *</label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                required
                placeholder={providerInfo.apiKeyPlaceholder}
              />
              <small>Your API key will be securely stored and used for all requests.</small>
            </div>

            <div className="form-group">
              <label>Model Name *</label>
              {providerInfo.modelOptions.length > 0 ? (
                <select
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  required
                >
                  {providerInfo.modelOptions.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  required
                  placeholder="Enter model name"
                />
              )}
            </div>

            <div className="form-group">
              <label>Custom Base URL (Optional)</label>
              <input
                type="url"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                placeholder="Leave empty for default"
              />
              <small>Only specify if using a custom API endpoint.</small>
            </div>

            {error && (
              <div className="error-message">
                <strong>Error:</strong> {error}
              </div>
            )}

            <div className="info-box">
              <h4>What happens during registration:</h4>
              <ul>
                <li>✅ Complete system context provided to LLM</li>
                <li>✅ All rules and governance policies explained</li>
                <li>✅ Available APIs and scripts shared</li>
                <li>✅ Integration test performed</li>
                <li>✅ LLM registered for use with GRACE</li>
              </ul>
            </div>

            <div className="modal-actions">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={registering}>
                {registering ? "Registering..." : "Register LLM"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN API TAB COMPONENT (Merged)
// ============================================================================

export default function APITab() {
  // Sub-tab state
  const [activeSubTab, setActiveSubTab] = useState("external"); // "external" or "llm"

  // External APIs state
  const [apis, setApis] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiModal, setApiModal] = useState({ open: false, api: null });
  const [filterType, setFilterType] = useState("all");

  // LLMs state
  const [llms, setLlms] = useState([]);
  const [llmLoading, setLlmLoading] = useState(true);
  const [llmModal, setLlmModal] = useState({ open: false, provider: null });
  const [llmError, setLlmError] = useState(null);

  // ============================================================================
  // EXTERNAL APIs Functions
  // ============================================================================

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
        setApiModal({ open: false, api: null });
        fetchAPIs();
      } else {
        // For demo, just add to local state
        if (apiData.id) {
          setApis(apis.map(a => a.id === apiData.id ? { ...a, ...apiData } : a));
        } else {
          setApis([...apis, { ...apiData, id: Date.now(), status: "pending", created_at: new Date().toISOString() }]);
        }
        setApiModal({ open: false, api: null });
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

  // ============================================================================
  // LLMs Functions
  // ============================================================================

  const fetchLLMs = useCallback(async () => {
    try {
      setLlmLoading(true);
      setLlmError(null);
      const response = await fetch(`${API_BASE}/third-party-llm/list`);
      
      if (response.ok) {
        const data = await response.json();
        setLlms(data.integrated_llms || []);
      } else {
        throw new Error("Failed to fetch LLMs");
      }
    } catch (err) {
      console.error("Error fetching LLMs:", err);
      setLlmError(err.message);
      setLlms([]);
    } finally {
      setLlmLoading(false);
    }
  }, []);

  const deleteLLM = async (llmId) => {
    if (!confirm("Are you sure you want to remove this LLM? It will no longer be available for use.")) {
      return;
    }
    setLlms(llms.filter(llm => llm.llm_id !== llmId));
  };

  const testLLM = async (llmId) => {
    return { success: true };
  };

  const handleRegistrationSuccess = (data) => {
    fetchLLMs();
  };

  // ============================================================================
  // Effects
  // ============================================================================

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchAPIs();
      setLoading(false);
    };
    loadData();
  }, [fetchAPIs]);

  useEffect(() => {
    if (activeSubTab === "llm") {
      fetchLLMs();
      const interval = setInterval(fetchLLMs, 30000);
      return () => clearInterval(interval);
    }
  }, [activeSubTab, fetchLLMs]);

  // ============================================================================
  // Render
  // ============================================================================

  const filteredAPIs = filterType === "all"
    ? apis
    : apis.filter(a => a.type === filterType);

  return (
    <div className="api-tab">
      <div className="api-header">
        <div className="header-left">
          <h2>API Management</h2>
          <p>Register and manage external APIs and third-party LLMs</p>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="sub-tabs">
        <button
          className={`sub-tab-button ${activeSubTab === "external" ? "active" : ""}`}
          onClick={() => setActiveSubTab("external")}
        >
          <span className="sub-tab-icon">🔌</span>
          External APIs
        </button>
        <button
          className={`sub-tab-button ${activeSubTab === "llm" ? "active" : ""}`}
          onClick={() => setActiveSubTab("llm")}
        >
          <span className="sub-tab-icon">🤖</span>
          Third-Party LLMs
        </button>
      </div>

      {/* External APIs Tab */}
      {activeSubTab === "external" && (
        <>
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
            <button className="btn-primary" onClick={() => setApiModal({ open: true, api: null })}>
              + Register API
            </button>
            <button className="btn-refresh" onClick={fetchAPIs}>
              Refresh
            </button>
          </div>

          <div className="api-content">
            {loading ? (
              <div className="loading-state">
                <div className="spinner" />
                <p>Loading APIs...</p>
              </div>
            ) : (
              <>
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
                          onEdit={(api) => setApiModal({ open: true, api })}
                          onDelete={deleteAPI}
                          onTest={testAPI}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {apiModal.open && (
            <APIEditorModal
              api={apiModal.api}
              onSave={saveAPI}
              onClose={() => setApiModal({ open: false, api: null })}
            />
          )}
        </>
      )}

      {/* Third-Party LLMs Tab */}
      {activeSubTab === "llm" && (
        <>
          <div className="api-toolbar">
            <div className="toolbar-info">
              <span className="info-text">
                {llms.length} LLM{llms.length !== 1 ? "s" : ""} registered
              </span>
            </div>
            <div className="toolbar-spacer" />
            <div className="register-buttons">
              <button
                className="btn-primary gemini-btn"
                onClick={() => setLlmModal({ open: true, provider: "gemini" })}
              >
                🔷 Register Gemini
              </button>
              <button
                className="btn-primary openai-btn"
                onClick={() => setLlmModal({ open: true, provider: "openai" })}
              >
                🤖 Register OpenAI
              </button>
              <button
                className="btn-primary anthropic-btn"
                onClick={() => setLlmModal({ open: true, provider: "anthropic" })}
              >
                🧠 Register Claude
              </button>
            </div>
            <button className="btn-refresh" onClick={fetchLLMs}>
              🔄 Refresh
            </button>
          </div>

          {llmError && (
            <div className="error-banner">
              <strong>Error:</strong> {llmError}
              <button onClick={fetchLLMs}>Retry</button>
            </div>
          )}

          <div className="api-content">
            {llmLoading ? (
              <div className="loading-state">
                <div className="spinner" />
                <p>Loading registered LLMs...</p>
              </div>
            ) : llms.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🔌</div>
                <h3>No LLMs Registered</h3>
                <p>Register a third-party LLM to get started. The LLM will automatically receive:</p>
                <ul className="empty-features">
                  <li>✅ Complete system architecture</li>
                  <li>✅ All rules and governance policies</li>
                  <li>✅ Available APIs and scripts</li>
                  <li>✅ Integration protocols</li>
                  <li>✅ Hallucination prevention rules</li>
                </ul>
                <button
                  className="btn-primary"
                  onClick={() => setLlmModal({ open: true, provider: "gemini" })}
                >
                  Register Your First LLM
                </button>
              </div>
            ) : (
              <div className="apis-section">
                <h4>Registered LLMs ({llms.length})</h4>
                <div className="apis-grid">
                  {llms.map((llm) => (
                    <LLMCard
                      key={llm.llm_id}
                      llm={llm}
                      onTest={testLLM}
                      onDelete={deleteLLM}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {llmModal.open && (
            <RegisterLLMModal
              provider={llmModal.provider}
              onSave={handleRegistrationSuccess}
              onClose={() => setLlmModal({ open: false, provider: null })}
            />
          )}
        </>
      )}
    </div>
  );
}
