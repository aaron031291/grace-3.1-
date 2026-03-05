import { useState } from "react";
import { useConnectionStatus } from "../hooks/useConnectionStatus";
import "./ConnectionStatusPanel.css";

const STATUS_COLORS = {
  connected: "#10b981",
  disconnected: "#ef4444",
  degraded: "#f59e0b",
  not_configured: "#6b7280",
  unknown: "#6b7280",
};

const CATEGORY_LABELS = {
  infrastructure: "Infrastructure",
  external_api: "External APIs",
  layer1_connector: "Layer 1 Connectors",
  background_service: "Background Services",
  websocket: "WebSocket",
};

const VALIDATION_COLORS = {
  pass: "#10b981",
  fail: "#ef4444",
  warn: "#f59e0b",
  skip: "#6b7280",
};

function StatusDot({ status }) {
  return (
    <span
      className="status-dot"
      style={{ backgroundColor: STATUS_COLORS[status] || STATUS_COLORS.unknown }}
      title={status}
    />
  );
}

function ValidationBadge({ result }) {
  return (
    <span
      className="validation-badge"
      style={{ backgroundColor: VALIDATION_COLORS[result] || VALIDATION_COLORS.skip }}
    >
      {result}
    </span>
  );
}

function ConnectionRow({ conn, expanded, onToggle }) {
  const hasActions = conn.action_validations && conn.action_validations.length > 0;

  return (
    <div className="connection-row">
      <div
        className="connection-summary"
        onClick={() => hasActions && onToggle()}
        style={{ cursor: hasActions ? "pointer" : "default" }}
      >
        <StatusDot status={conn.status} />
        <span className="connection-name">{conn.name.replace(/_/g, " ")}</span>
        <span className="connection-category">
          {CATEGORY_LABELS[conn.category] || conn.category}
        </span>
        {conn.latency_ms != null && (
          <span className="connection-latency">{conn.latency_ms.toFixed(0)}ms</span>
        )}
        {conn.actions_total > 0 && (
          <span className="connection-actions-count">
            {conn.actions_passing}/{conn.actions_total} actions
          </span>
        )}
        {conn.message && !conn.connected && (
          <span className="connection-message">{conn.message}</span>
        )}
        {hasActions && (
          <span className="expand-arrow">{expanded ? "\u25B2" : "\u25BC"}</span>
        )}
      </div>

      {expanded && hasActions && (
        <div className="connection-actions">
          {conn.action_validations.map((action, i) => (
            <div key={i} className="action-row">
              <ValidationBadge result={action.result} />
              <span className="action-name">{action.action_name}</span>
              <span className="action-desc">{action.description}</span>
              {action.latency_ms != null && (
                <span className="action-latency">{action.latency_ms.toFixed(0)}ms</span>
              )}
              {action.message && (
                <span className="action-message">{action.message}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ConnectionStatusPanel() {
  const {
    summary,
    connectionStatuses: _connectionStatuses,
    loading,
    lastChecked,
    refresh,
    refreshFull,
    report,
  } = useConnectionStatus(30000);

  const [expandedConn, setExpandedConn] = useState(null);
  const [_showFullReport, setShowFullReport] = useState(false);

  const connections = report?.connections || [];

  const grouped = {};
  for (const conn of connections) {
    const cat = conn.category || "unknown";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(conn);
  }

  const handleFullValidation = async () => {
    setShowFullReport(true);
    await refreshFull();
  };

  return (
    <div className="connection-status-panel">
      <div className="panel-header">
        <h3>Connection Status</h3>
        <div className="panel-actions">
          <button onClick={refresh} disabled={loading} className="btn-refresh-conn">
            {loading ? "Checking..." : "Refresh"}
          </button>
          <button onClick={handleFullValidation} disabled={loading} className="btn-validate">
            {loading ? "Validating..." : "Full Validation"}
          </button>
        </div>
      </div>

      <div className="summary-bar">
        <div className="summary-item">
          <span className="summary-count" style={{ color: STATUS_COLORS.connected }}>
            {summary.connected}
          </span>
          <span className="summary-label">Connected</span>
        </div>
        <div className="summary-item">
          <span className="summary-count" style={{ color: STATUS_COLORS.disconnected }}>
            {summary.disconnected}
          </span>
          <span className="summary-label">Disconnected</span>
        </div>
        <div className="summary-item">
          <span className="summary-count" style={{ color: STATUS_COLORS.degraded }}>
            {summary.degraded}
          </span>
          <span className="summary-label">Degraded</span>
        </div>
        {summary.actionsValidated > 0 && (
          <div className="summary-item">
            <span className="summary-count">
              {summary.actionsPassing}/{summary.actionsValidated}
            </span>
            <span className="summary-label">Actions OK</span>
          </div>
        )}
        <div className="summary-status-badge" data-status={summary.status}>
          {summary.status === "all_connected"
            ? "All Connected"
            : summary.status === "partial"
            ? "Partial"
            : summary.status === "critical"
            ? "Critical"
            : summary.status === "degraded"
            ? "Degraded"
            : "Unknown"}
        </div>
      </div>

      <div className="connections-list">
        {Object.entries(grouped).map(([category, conns]) => (
          <div key={category} className="category-group">
            <div className="category-header">
              {CATEGORY_LABELS[category] || category}
              <span className="category-count">
                {conns.filter((c) => c.connected).length}/{conns.length}
              </span>
            </div>
            {conns.map((conn) => (
              <ConnectionRow
                key={conn.name}
                conn={conn}
                expanded={expandedConn === conn.name}
                onToggle={() =>
                  setExpandedConn(expandedConn === conn.name ? null : conn.name)
                }
              />
            ))}
          </div>
        ))}
      </div>

      {lastChecked && (
        <div className="last-checked">
          Last checked: {new Date(lastChecked).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
