import { useEffect, useState, useCallback } from "react";
import "./LibrarianTab.css";

const API_BASE = "http://localhost:8000";

// Trust score color mapping
const getTrustColor = (score) => {
  if (score >= 0.8) return "#10b981"; // Green - excellent
  if (score >= 0.6) return "#3b82f6"; // Blue - good
  if (score >= 0.4) return "#f59e0b"; // Yellow - fair
  return "#ef4444"; // Red - poor
};

const getTrustLabel = (score) => {
  if (score >= 0.8) return "Excellent";
  if (score >= 0.6) return "Good";
  if (score >= 0.4) return "Fair";
  return "Poor";
};

// Tag Widget Component
function TagWidget({ tag, onRemove, showConfidence = true, compact = false }) {
  const confidencePercent = Math.round((tag.confidence || 1) * 100);

  return (
    <div
      className={`tag-widget ${compact ? "compact" : ""}`}
      style={{
        backgroundColor: tag.color || "#3b82f6",
        borderLeftColor: getTrustColor(tag.confidence || 1)
      }}
    >
      <span className="tag-name">{tag.name}</span>
      {showConfidence && tag.confidence < 1 && (
        <span className="tag-confidence" title={`Confidence: ${confidencePercent}%`}>
          {confidencePercent}%
        </span>
      )}
      {tag.assigned_by && (
        <span className="tag-source" title={`Assigned by: ${tag.assigned_by}`}>
          {tag.assigned_by === "ai" ? "AI" :
           tag.assigned_by === "rule" ? "R" :
           tag.assigned_by === "user" ? "U" : "A"}
        </span>
      )}
      {onRemove && (
        <button className="tag-remove" onClick={() => onRemove(tag.name)}>
          x
        </button>
      )}
    </div>
  );
}

// Tag Statistics Card
function TagStatsCard({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-card">
      <h4>Tag Statistics</h4>
      <div className="stats-grid">
        <div className="stat-box">
          <span className="stat-number">{stats.total_tags || 0}</span>
          <span className="stat-label">Total Tags</span>
        </div>
        <div className="stat-box">
          <span className="stat-number">{Object.keys(stats.by_category || {}).length}</span>
          <span className="stat-label">Categories</span>
        </div>
      </div>

      {stats.most_used && stats.most_used.length > 0 && (
        <div className="popular-tags">
          <h5>Most Used</h5>
          <div className="tags-row">
            {stats.most_used.slice(0, 5).map((tag) => (
              <div
                key={tag.id}
                className="popular-tag"
                style={{ backgroundColor: tag.color || "#3b82f6" }}
              >
                {tag.name}
                <span className="usage-count">{tag.usage_count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {stats.by_category && Object.keys(stats.by_category).length > 0 && (
        <div className="categories-list">
          <h5>By Category</h5>
          <div className="category-bars">
            {Object.entries(stats.by_category).map(([category, count]) => (
              <div key={category} className="category-bar">
                <span className="category-name">{category}</span>
                <div className="bar-container">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${Math.min((count / stats.total_tags) * 100, 100)}%`
                    }}
                  />
                </div>
                <span className="category-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// KPI Dashboard Component
function KPIDashboard({ health }) {
  if (!health) return null;

  return (
    <div className="kpi-dashboard">
      <div className="kpi-header">
        <h4>System Health</h4>
        <div
          className="system-trust-badge"
          style={{ backgroundColor: getTrustColor(health.system_trust_score) }}
        >
          {getTrustLabel(health.system_trust_score)} ({Math.round(health.system_trust_score * 100)}%)
        </div>
      </div>

      <div className="kpi-grid">
        {Object.entries(health.components || {}).map(([name, component]) => (
          <div key={name} className="kpi-card">
            <div className="kpi-card-header">
              <span className="component-name">{name.replace(/_/g, " ")}</span>
              <span
                className="component-status"
                style={{ color: getTrustColor(component.trust_score) }}
              >
                {component.status}
              </span>
            </div>
            <div className="trust-bar">
              <div
                className="trust-fill"
                style={{
                  width: `${component.trust_score * 100}%`,
                  backgroundColor: getTrustColor(component.trust_score)
                }}
              />
            </div>
            <div className="kpi-meta">
              <span>{component.total_actions || 0} actions</span>
              <span>{component.kpi_count || 0} metrics</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Tag Search Component
function TagSearch({ onSearch, loading }) {
  const [searchTags, setSearchTags] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [matchAll, setMatchAll] = useState(false);

  const addTag = () => {
    const tag = inputValue.trim().toLowerCase();
    if (tag && !searchTags.includes(tag)) {
      setSearchTags([...searchTags, tag]);
      setInputValue("");
    }
  };

  const removeTag = (tag) => {
    setSearchTags(searchTags.filter((t) => t !== tag));
  };

  const handleSearch = () => {
    if (searchTags.length > 0) {
      onSearch(searchTags, matchAll);
    }
  };

  return (
    <div className="tag-search">
      <div className="search-input-row">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && addTag()}
          placeholder="Enter tag name..."
        />
        <button onClick={addTag} className="btn-add">+</button>
      </div>

      {searchTags.length > 0 && (
        <div className="search-tags">
          {searchTags.map((tag) => (
            <span key={tag} className="search-tag">
              {tag}
              <button onClick={() => removeTag(tag)}>x</button>
            </span>
          ))}
        </div>
      )}

      <div className="search-options">
        <label>
          <input
            type="checkbox"
            checked={matchAll}
            onChange={(e) => setMatchAll(e.target.checked)}
          />
          Match all tags (AND)
        </label>
        <button
          onClick={handleSearch}
          disabled={searchTags.length === 0 || loading}
          className="btn-search"
        >
          {loading ? "Searching..." : "Search Documents"}
        </button>
      </div>
    </div>
  );
}

// Document with Tags Component
function DocumentCard({ doc, onAssignTags, onRemoveTag }) {
  const [showAssign, setShowAssign] = useState(false);
  const [newTags, setNewTags] = useState("");

  const handleAssign = () => {
    const tags = newTags.split(",").map((t) => t.trim()).filter((t) => t);
    if (tags.length > 0) {
      onAssignTags(doc.id, tags);
      setNewTags("");
      setShowAssign(false);
    }
  };

  return (
    <div className="document-card">
      <div className="doc-header">
        <span className="doc-filename">{doc.filename}</span>
        <span className="doc-path" title={doc.file_path}>
          {doc.file_path?.slice(0, 40)}...
        </span>
      </div>

      <div className="doc-tags">
        {doc.tags && doc.tags.length > 0 ? (
          doc.tags.map((tag) => (
            <TagWidget
              key={tag.id || tag.name}
              tag={tag}
              onRemove={(name) => onRemoveTag(doc.id, name)}
              compact
            />
          ))
        ) : (
          <span className="no-tags">No tags assigned</span>
        )}
      </div>

      <div className="doc-actions">
        {showAssign ? (
          <div className="assign-form">
            <input
              type="text"
              value={newTags}
              onChange={(e) => setNewTags(e.target.value)}
              placeholder="tag1, tag2, ..."
              onKeyPress={(e) => e.key === "Enter" && handleAssign()}
            />
            <button onClick={handleAssign} className="btn-small btn-primary">Add</button>
            <button onClick={() => setShowAssign(false)} className="btn-small btn-secondary">Cancel</button>
          </div>
        ) : (
          <button onClick={() => setShowAssign(true)} className="btn-small btn-secondary">
            + Add Tags
          </button>
        )}
      </div>
    </div>
  );
}

// Tag Editor Modal
function TagEditorModal({ tag, onSave, onClose }) {
  const [formData, setFormData] = useState(
    tag || {
      name: "",
      description: "",
      color: "#3b82f6",
      category: "",
    }
  );

  const colors = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1"
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content tag-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{tag ? "Edit Tag" : "Create New Tag"}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Tag Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Enter tag name..."
              disabled={!!tag}
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what this tag represents..."
              rows={2}
            />
          </div>

          <div className="form-group">
            <label>Category</label>
            <input
              type="text"
              value={formData.category || ""}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              placeholder="e.g., technology, research, code"
            />
          </div>

          <div className="form-group">
            <label>Color</label>
            <div className="color-picker">
              {colors.map((color) => (
                <button
                  key={color}
                  type="button"
                  className={`color-option ${formData.color === color ? "selected" : ""}`}
                  style={{ backgroundColor: color }}
                  onClick={() => setFormData({ ...formData, color })}
                />
              ))}
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {tag ? "Save Changes" : "Create Tag"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Rule Manager Component
function RuleManager({ rules, onToggle, onDelete, onTest }) {
  return (
    <div className="rules-section">
      <h4>Categorization Rules</h4>
      {rules.length === 0 ? (
        <p className="no-rules">No rules configured</p>
      ) : (
        <div className="rules-list">
          {rules.map((rule) => (
            <div key={rule.id} className={`rule-card ${rule.enabled ? "" : "disabled"}`}>
              <div className="rule-header">
                <span className="rule-name">{rule.name}</span>
                <span className={`rule-type badge-${rule.pattern_type}`}>
                  {rule.pattern_type}
                </span>
              </div>
              <div className="rule-pattern">
                <code>{rule.pattern_value}</code>
              </div>
              <div className="rule-action">
                {rule.action_type}: {JSON.stringify(rule.action_params)}
              </div>
              <div className="rule-meta">
                <span>Priority: {rule.priority}</span>
                <span>Matches: {rule.matches_count}</span>
              </div>
              <div className="rule-actions">
                <button onClick={() => onToggle(rule.id, !rule.enabled)}>
                  {rule.enabled ? "Disable" : "Enable"}
                </button>
                <button onClick={() => onTest(rule.id)}>Test</button>
                <button onClick={() => onDelete(rule.id)} className="btn-danger">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Main Librarian Tab Component
export default function LibrarianTab() {
  // State
  const [activeView, setActiveView] = useState("tags");
  const [tags, setTags] = useState([]);
  const [tagStats, setTagStats] = useState(null);
  const [rules, setRules] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [kpiHealth, setKpiHealth] = useState(null);
  const [librarianStats, setLibrarianStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modals
  const [tagModal, setTagModal] = useState({ open: false, tag: null });

  // Fetch functions
  const fetchTags = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/tags`);
      if (!response.ok) throw new Error("Failed to fetch tags");
      const data = await response.json();
      setTags(data.tags || []);
    } catch (err) {
      console.error("Error fetching tags:", err);
    }
  }, []);

  const fetchTagStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/tags/statistics`);
      if (!response.ok) throw new Error("Failed to fetch tag stats");
      const data = await response.json();
      setTagStats(data);
    } catch (err) {
      console.error("Error fetching tag stats:", err);
    }
  }, []);

  const fetchRules = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/rules?enabled_only=false`);
      if (!response.ok) throw new Error("Failed to fetch rules");
      const data = await response.json();
      setRules(data.rules || []);
    } catch (err) {
      console.error("Error fetching rules:", err);
    }
  }, []);

  const fetchKPIHealth = useCallback(async () => {
    try {
      // Fetch from KPI connector endpoint
      const response = await fetch(`${API_BASE}/layer1/kpi/health`);
      if (response.ok) {
        const data = await response.json();
        setKpiHealth(data);
      }
    } catch (err) {
      console.error("Error fetching KPI health:", err);
    }
  }, []);

  const fetchLibrarianStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/statistics`);
      if (!response.ok) throw new Error("Failed to fetch librarian stats");
      const data = await response.json();
      setLibrarianStats(data);
    } catch (err) {
      console.error("Error fetching librarian stats:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([
          fetchTags(),
          fetchTagStats(),
          fetchRules(),
          fetchKPIHealth(),
          fetchLibrarianStats()
        ]);
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    };
    loadData();
  }, [fetchTags, fetchTagStats, fetchRules, fetchKPIHealth, fetchLibrarianStats]);

  // CRUD Operations
  const createTag = async (tagData) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tagData),
      });
      if (!response.ok) throw new Error("Failed to create tag");
      setTagModal({ open: false, tag: null });
      fetchTags();
      fetchTagStats();
    } catch (err) {
      console.error("Error creating tag:", err);
      alert("Failed to create tag: " + err.message);
    }
  };

  const updateTag = async (tagData) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/tags/${tagData.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tagData),
      });
      if (!response.ok) throw new Error("Failed to update tag");
      setTagModal({ open: false, tag: null });
      fetchTags();
      fetchTagStats();
    } catch (err) {
      console.error("Error updating tag:", err);
      alert("Failed to update tag: " + err.message);
    }
  };

  const deleteTag = async (tagId) => {
    if (!confirm("Are you sure you want to delete this tag?")) return;
    try {
      const response = await fetch(`${API_BASE}/librarian/tags/${tagId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete tag");
      fetchTags();
      fetchTagStats();
    } catch (err) {
      console.error("Error deleting tag:", err);
      alert("Failed to delete tag: " + err.message);
    }
  };

  const searchByTags = async (tagNames, matchAll) => {
    setSearchLoading(true);
    try {
      const response = await fetch(`${API_BASE}/librarian/search/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag_names: tagNames, match_all: matchAll, limit: 50 }),
      });
      if (!response.ok) throw new Error("Failed to search");
      const data = await response.json();
      setSearchResults(data.documents || []);
    } catch (err) {
      console.error("Error searching:", err);
      alert("Search failed: " + err.message);
    }
    setSearchLoading(false);
  };

  const assignTagsToDoc = async (docId, tagNames) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/documents/${docId}/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag_names: tagNames, assigned_by: "user", confidence: 1.0 }),
      });
      if (!response.ok) throw new Error("Failed to assign tags");
      // Refresh search results
      fetchTagStats();
    } catch (err) {
      console.error("Error assigning tags:", err);
      alert("Failed to assign tags: " + err.message);
    }
  };

  const removeTagFromDoc = async (docId, tagName) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/documents/${docId}/tags/${tagName}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to remove tag");
      fetchTagStats();
    } catch (err) {
      console.error("Error removing tag:", err);
      alert("Failed to remove tag: " + err.message);
    }
  };

  const toggleRule = async (ruleId, enabled) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/rules/${ruleId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error("Failed to update rule");
      fetchRules();
    } catch (err) {
      console.error("Error toggling rule:", err);
    }
  };

  const deleteRule = async (ruleId) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    try {
      const response = await fetch(`${API_BASE}/librarian/rules/${ruleId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete rule");
      fetchRules();
    } catch (err) {
      console.error("Error deleting rule:", err);
    }
  };

  const testRule = async (ruleId) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/rules/${ruleId}/test`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to test rule");
      const data = await response.json();
      alert(`Rule matched ${data.total_matches} documents`);
    } catch (err) {
      console.error("Error testing rule:", err);
    }
  };

  if (loading) {
    return (
      <div className="librarian-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Librarian System...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="librarian-tab">
        <div className="error-state">
          <p>Error: {error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="librarian-tab">
      <div className="librarian-header">
        <div className="header-left">
          <h2>Librarian System</h2>
          <p>Tag management with trust-aware organization</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value">{tags.length}</span>
            <span className="stat-label">Tags</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{rules.length}</span>
            <span className="stat-label">Rules</span>
          </div>
          {librarianStats && (
            <div className="stat-item">
              <span className="stat-value">{librarianStats.documents_processed || 0}</span>
              <span className="stat-label">Documents</span>
            </div>
          )}
        </div>
      </div>

      <div className="librarian-toolbar">
        <div className="view-tabs">
          <button
            className={activeView === "tags" ? "active" : ""}
            onClick={() => setActiveView("tags")}
          >
            Tags
          </button>
          <button
            className={activeView === "search" ? "active" : ""}
            onClick={() => setActiveView("search")}
          >
            Search
          </button>
          <button
            className={activeView === "rules" ? "active" : ""}
            onClick={() => setActiveView("rules")}
          >
            Rules
          </button>
          <button
            className={activeView === "kpi" ? "active" : ""}
            onClick={() => setActiveView("kpi")}
          >
            KPI Health
          </button>
        </div>
        <div className="toolbar-spacer" />
        {activeView === "tags" && (
          <button
            className="btn-primary"
            onClick={() => setTagModal({ open: true, tag: null })}
          >
            + New Tag
          </button>
        )}
        <button className="btn-refresh" onClick={() => {
          fetchTags();
          fetchTagStats();
          fetchRules();
          fetchKPIHealth();
        }}>
          Refresh
        </button>
      </div>

      <div className="librarian-content">
        {activeView === "tags" && (
          <div className="tags-view">
            <div className="tags-panel">
              <TagStatsCard stats={tagStats} />

              <div className="all-tags">
                <h4>All Tags ({tags.length})</h4>
                <div className="tags-grid">
                  {tags.map((tag) => (
                    <div key={tag.id} className="tag-item">
                      <div
                        className="tag-color-bar"
                        style={{ backgroundColor: tag.color }}
                      />
                      <div className="tag-info">
                        <span className="tag-name">{tag.name}</span>
                        {tag.category && (
                          <span className="tag-category">{tag.category}</span>
                        )}
                        <span className="tag-usage">Used {tag.usage_count} times</span>
                      </div>
                      <div className="tag-actions">
                        <button
                          onClick={() => setTagModal({ open: true, tag })}
                          title="Edit"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteTag(tag.id)}
                          className="btn-danger"
                          title="Delete"
                        >
                          x
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === "search" && (
          <div className="search-view">
            <TagSearch onSearch={searchByTags} loading={searchLoading} />

            <div className="search-results">
              <h4>Results ({searchResults.length})</h4>
              {searchResults.length === 0 ? (
                <p className="no-results">Search for documents by tags above</p>
              ) : (
                <div className="documents-list">
                  {searchResults.map((doc) => (
                    <DocumentCard
                      key={doc.id}
                      doc={doc}
                      onAssignTags={assignTagsToDoc}
                      onRemoveTag={removeTagFromDoc}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeView === "rules" && (
          <div className="rules-view">
            <RuleManager
              rules={rules}
              onToggle={toggleRule}
              onDelete={deleteRule}
              onTest={testRule}
            />
          </div>
        )}

        {activeView === "kpi" && (
          <div className="kpi-view">
            <KPIDashboard health={kpiHealth} />

            {librarianStats && (
              <div className="librarian-health">
                <h4>Librarian Status</h4>
                <div className="health-grid">
                  <div className="health-item">
                    <span className="health-label">AI Available</span>
                    <span className={`health-value ${librarianStats.ai_available ? "active" : "inactive"}`}>
                      {librarianStats.ai_available ? "Yes" : "No"}
                    </span>
                  </div>
                  <div className="health-item">
                    <span className="health-label">Relationships</span>
                    <span className={`health-value ${librarianStats.relationships_enabled ? "active" : "inactive"}`}>
                      {librarianStats.relationships_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {tagModal.open && (
        <TagEditorModal
          tag={tagModal.tag}
          onSave={tagModal.tag ? updateTag : createTag}
          onClose={() => setTagModal({ open: false, tag: null })}
        />
      )}
    </div>
  );
}
