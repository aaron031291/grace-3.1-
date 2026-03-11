import { useState, useEffect, useCallback } from "react";
import "./GenesisKeyPanel.css";
import { API_BASE_URL } from '../config/api';

export default function GenesisKeyPanel() {
  const [keys, setKeys] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // all, errors, fixes
  const [showMetadata, setShowMetadata] = useState(false);
  const [metadataFormat, setMetadataFormat] = useState("human");
  const [archives, setArchives] = useState([]);
  const [_selectedArchive, _setSelectedArchive] = useState(null);
  const [stats, setStats] = useState(null);

  const API_BASE = API_BASE_URL;

  // Load Genesis Keys
  useEffect(() => {
    loadKeys();
    loadStats();
    loadArchives();
  }, [loadKeys, loadStats, loadArchives]);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let url = `${API_BASE}/genesis/keys?limit=50`;

      if (filter === "errors") {
        url += "&is_error=true";
      } else if (filter === "fixes") {
        url += "&key_type=fix";
      }

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to load Genesis Keys");

      const data = await response.json();
      setKeys(data);
    } catch (err) {
      setError(err.message);
      console.error("Error loading keys:", err);
    } finally {
      setLoading(false);
    }
  }, [API_BASE, filter]);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/genesis/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Error loading stats:", err);
    }
  }, [API_BASE]);

  const loadArchives = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/genesis/archives?limit=10`);
      if (response.ok) {
        const data = await response.json();
        setArchives(data);
      }
    } catch (err) {
      console.error("Error loading archives:", err);
    }
  }, [API_BASE]);

  const handleKeyDoubleClick = async (key) => {
    // Double-click opens version control module
    if (key.commit_sha) {
      // Navigate to version control with this commit
      window.location.href = `/version-control?commit=${key.commit_sha}`;
    } else {
      // Show detailed metadata
      setSelectedKey(key);
      setShowMetadata(true);
      await loadKeyMetadata(key.key_id);
    }
  };

  const loadKeyMetadata = async (keyId) => {
    try {
      const response = await fetch(
        `${API_BASE}/genesis/keys/${keyId}/metadata?format=both`
      );
      if (response.ok) {
        const data = await response.json();
        setSelectedKey((prev) => ({
          ...prev,
          metadata_human_full: data.human_readable,
          metadata_ai_full: data.ai_readable,
        }));
      }
    } catch (err) {
      console.error("Error loading metadata:", err);
    }
  };

  const handleApplyFix = async (suggestionId) => {
    if (!confirm("Apply this fix?")) return;

    try {
      const response = await fetch(
        `${API_BASE}/genesis/fixes/${suggestionId}/apply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ applied_by: "User" }),
        }
      );

      if (!response.ok) throw new Error("Failed to apply fix");

      const data = await response.json();
      alert(`Fix applied successfully! Key ID: ${data.fix_key_id}`);
      loadKeys(); // Reload keys
    } catch (err) {
      alert(`Error applying fix: ${err.message}`);
    }
  };

  const handleRollback = async (keyId) => {
    if (!confirm("Rollback to this state? This will revert code changes."))
      return;

    try {
      const response = await fetch(
        `${API_BASE}/genesis/keys/${keyId}/rollback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rolled_back_by: "User" }),
        }
      );

      if (!response.ok) throw new Error("Failed to rollback");

      const data = await response.json();
      alert(`Rolled back successfully! Key ID: ${data.rollback_key_id}`);
      loadKeys();
    } catch (err) {
      alert(`Error rolling back: ${err.message}`);
    }
  };

  const handleTriggerArchival = async () => {
    if (!confirm("Trigger archival for yesterday's keys?")) return;

    try {
      const response = await fetch(`${API_BASE}/genesis/archive/trigger`, {
        method: "POST",
      });

      if (!response.ok) throw new Error("Failed to trigger archival");

      const data = await response.json();
      alert(
        data.message ||
          `Archival complete! Archive ID: ${data.archive_id}, Keys: ${data.key_count}`
      );
      loadArchives();
    } catch (err) {
      alert(`Error triggering archival: ${err.message}`);
    }
  };

  const viewArchiveReport = async (archiveId) => {
    try {
      const response = await fetch(
        `${API_BASE}/genesis/archives/${archiveId}/report?format=text`
      );
      if (response.ok) {
        const data = await response.json();
        // Open report in new window
        const reportWindow = window.open("", "_blank");
        reportWindow.document.write("<pre>" + data.report + "</pre>");
      }
    } catch (err) {
      alert(`Error loading report: ${err.message}`);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getSeverityClass = (severity) => {
    return `severity-${severity || "medium"}`;
  };

  const getStatusClass = (status) => {
    return `status-${status.toLowerCase()}`;
  };

  return (
    <div className="genesis-key-panel">
      <div className="panel-header">
        <h2>🔑 Genesis Key Version Control</h2>
        <p className="subtitle">
          Complete tracking system - What, Where, When, Why, Who, and How
        </p>
      </div>

      {/* Statistics Dashboard */}
      {stats && (
        <div className="stats-dashboard">
          <div className="stat-card">
            <div className="stat-value">{stats.total_keys}</div>
            <div className="stat-label">Total Keys</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_errors}</div>
            <div className="stat-label">Errors Detected</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_fixes}</div>
            <div className="stat-label">Fixes Applied</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.keys_last_24h}</div>
            <div className="stat-label">Last 24h</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_archives}</div>
            <div className="stat-label">Archives</div>
          </div>
        </div>
      )}

      {/* Filter Controls */}
      <div className="filter-controls">
        <button
          className={`filter-btn ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          All Keys
        </button>
        <button
          className={`filter-btn ${filter === "errors" ? "active" : ""}`}
          onClick={() => setFilter("errors")}
        >
          🚨 Errors Only
        </button>
        <button
          className={`filter-btn ${filter === "fixes" ? "active" : ""}`}
          onClick={() => setFilter("fixes")}
        >
          ✅ Fixes Only
        </button>
        <button className="action-btn" onClick={loadKeys}>
          🔄 Refresh
        </button>
        <button className="action-btn" onClick={handleTriggerArchival}>
          📦 Archive Now
        </button>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading ? (
        <div className="loading-state">Loading Genesis Keys...</div>
      ) : (
        <div className="content-container">
          {/* Keys List */}
          <div className="keys-section">
            <h3>Genesis Keys ({keys.length})</h3>
            <p className="hint">💡 Double-click a key to view details or open version control</p>

            <div className="keys-list">
              {keys.map((key) => (
                <div
                  key={key.key_id}
                  className={`key-card ${key.is_error ? "error-card" : ""} ${
                    key.fix_applied ? "fixed-card" : ""
                  }`}
                  onDoubleClick={() => handleKeyDoubleClick(key)}
                >
                  <div className="key-header">
                    <div className="key-type-badge">{key.key_type}</div>
                    <div className={`key-status ${getStatusClass(key.status)}`}>
                      {key.status}
                    </div>
                  </div>

                  <div className="key-what">{key.what_description}</div>

                  <div className="key-metadata-grid">
                    <div className="metadata-item">
                      <strong>WHO:</strong> {key.who_actor}
                    </div>
                    <div className="metadata-item">
                      <strong>WHEN:</strong> {formatTimestamp(key.when_timestamp)}
                    </div>
                    {key.where_location && (
                      <div className="metadata-item">
                        <strong>WHERE:</strong> {key.where_location}
                      </div>
                    )}
                    {key.file_path && (
                      <div className="metadata-item">
                        <strong>FILE:</strong> {key.file_path}
                        {key.line_number && `:${key.line_number}`}
                      </div>
                    )}
                  </div>

                  {key.is_error && (
                    <div className="error-indicator">
                      ⚠️ Error Detected
                      {key.has_fix_suggestion && !key.fix_applied && (
                        <span className="fix-available">✨ Fix Available</span>
                      )}
                      {key.fix_applied && <span className="fix-applied">✅ Fixed</span>}
                    </div>
                  )}

                  <div className="key-actions">
                    <button
                      className="action-link"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleKeyDoubleClick(key);
                      }}
                    >
                      View Details
                    </button>
                    {key.commit_sha && (
                      <button
                        className="action-link"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRollback(key.key_id);
                        }}
                      >
                        🔄 Rollback
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Archives Section */}
          <div className="archives-section">
            <h3>Recent Archives</h3>
            <div className="archives-list">
              {archives.map((archive) => (
                <div key={archive.archive_id} className="archive-card">
                  <div className="archive-date">
                    📅 {formatTimestamp(archive.archive_date)}
                  </div>
                  <div className="archive-stats">
                    <span>{archive.key_count} keys</span>
                    <span>{archive.error_count} errors</span>
                    <span>{archive.fix_count} fixes</span>
                  </div>
                  {archive.most_active_user && (
                    <div className="archive-info">
                      👤 Most Active: {archive.most_active_user}
                    </div>
                  )}
                  <button
                    className="view-report-btn"
                    onClick={() => viewArchiveReport(archive.archive_id)}
                  >
                    📄 View Report
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Metadata Modal */}
      {showMetadata && selectedKey && (
        <div className="modal-overlay" onClick={() => setShowMetadata(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Genesis Key Details</h3>
              <button
                className="close-btn"
                onClick={() => setShowMetadata(false)}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="metadata-format-toggle">
                <button
                  className={metadataFormat === "human" ? "active" : ""}
                  onClick={() => setMetadataFormat("human")}
                >
                  Human Readable
                </button>
                <button
                  className={metadataFormat === "ai" ? "active" : ""}
                  onClick={() => setMetadataFormat("ai")}
                >
                  AI Readable
                </button>
              </div>

              <div className="metadata-display">
                {metadataFormat === "human" ? (
                  <pre>{selectedKey.metadata_human_full || selectedKey.metadata_human}</pre>
                ) : (
                  <pre>
                    {JSON.stringify(
                      selectedKey.metadata_ai_full || selectedKey.metadata_ai,
                      null,
                      2
                    )}
                  </pre>
                )}
              </div>

              {selectedKey.is_error && selectedKey.has_fix_suggestion && (
                <div className="fix-suggestions-section">
                  <h4>Available Fixes</h4>
                  <button
                    className="load-fixes-btn"
                    onClick={async () => {
                      try {
                        const response = await fetch(
                          `${API_BASE}/genesis/keys/${selectedKey.key_id}/fixes`
                        );
                        if (response.ok) {
                          const fixes = await response.json();
                          setSelectedKey((prev) => ({ ...prev, fixes }));
                        }
                      } catch (err) {
                        console.error("Error loading fixes:", err);
                      }
                    }}
                  >
                    Load Fix Suggestions
                  </button>

                  {selectedKey.fixes && (
                    <div className="fixes-list">
                      {selectedKey.fixes.map((fix) => (
                        <div
                          key={fix.suggestion_id}
                          className={`fix-card ${getSeverityClass(fix.severity)}`}
                        >
                          <div className="fix-title">{fix.title}</div>
                          <div className="fix-description">{fix.description}</div>
                          {fix.fix_code && (
                            <div className="fix-code">
                              <pre>{fix.fix_code}</pre>
                            </div>
                          )}
                          <div className="fix-actions">
                            <span className="confidence">
                              Confidence: {(fix.confidence * 100).toFixed(0)}%
                            </span>
                            {fix.status === "pending" && (
                              <button
                                className="apply-fix-btn"
                                onClick={() => handleApplyFix(fix.suggestion_id)}
                              >
                                ✨ Apply Fix
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
