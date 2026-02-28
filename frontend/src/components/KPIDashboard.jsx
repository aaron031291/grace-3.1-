import { useEffect, useState, useCallback } from "react";
import "./KPIDashboard.css";
import { API_BASE_URL } from '../config/api';

const API_BASE = API_BASE_URL;

// Trust score visualization
const getTrustColor = (score) => {
  if (score >= 0.8) return "#10b981";
  if (score >= 0.6) return "#3b82f6";
  if (score >= 0.4) return "#f59e0b";
  return "#ef4444";
};

const getStatusColor = (status) => {
  switch (status) {
    case "excellent": return "#10b981";
    case "good": return "#3b82f6";
    case "fair": return "#f59e0b";
    case "poor": return "#ef4444";
    default: return "#6b7280";
  }
};

// Component Card
function ComponentCard({ component, onSelect }) {
  const trustColor = getTrustColor(component.trust_score);

  return (
    <div
      className={`component-card status-${component.status}`}
      onClick={() => onSelect(component.name)}
    >
      <div className="component-header">
        <span className="component-name">{component.name}</span>
        <span
          className="component-status"
          style={{ backgroundColor: getStatusColor(component.status) }}
        >
          {component.status}
        </span>
      </div>

      <div className="trust-meter">
        <div
          className="trust-fill"
          style={{
            width: `${component.trust_score * 100}%`,
            backgroundColor: trustColor
          }}
        />
      </div>

      <div className="component-stats">
        <div className="stat">
          <span className="stat-value">{Math.round(component.trust_score * 100)}%</span>
          <span className="stat-label">Trust</span>
        </div>
        <div className="stat">
          <span className="stat-value">{component.total_actions || 0}</span>
          <span className="stat-label">Actions</span>
        </div>
        <div className="stat">
          <span className="stat-value">{component.kpi_count || 0}</span>
          <span className="stat-label">KPIs</span>
        </div>
      </div>
    </div>
  );
}

// KPI Metric Display
function KPIMetric({ metric }) {
  return (
    <div className="kpi-metric">
      <div className="metric-header">
        <span className="metric-name">{metric.metric_name}</span>
        <span className="metric-count">x{metric.count}</span>
      </div>
      <div className="metric-value">{metric.value.toFixed(2)}</div>
      <div className="metric-timestamp">
        Last: {new Date(metric.timestamp).toLocaleString()}
      </div>
    </div>
  );
}

// System Health Panel
function SystemHealthPanel({ health }) {
  if (!health) return null;

  const trustColor = getTrustColor(health.system_trust_score);

  return (
    <div className="system-health-panel">
      <h3>System Health</h3>

      <div className="health-overview">
        <div className="trust-circle" style={{ borderColor: trustColor }}>
          <span className="trust-value" style={{ color: trustColor }}>
            {Math.round(health.system_trust_score * 100)}%
          </span>
          <span className="trust-label">Trust</span>
        </div>

        <div className="health-details">
          <div className="health-item">
            <span className="health-label">Status</span>
            <span
              className="health-status"
              style={{ color: getStatusColor(health.status) }}
            >
              {health.status.toUpperCase()}
            </span>
          </div>
          <div className="health-item">
            <span className="health-label">Components</span>
            <span className="health-value">{health.component_count}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Component Detail Panel
function ComponentDetailPanel({ componentName, kpis, onClose }) {
  if (!kpis) return null;

  return (
    <div className="component-detail-panel">
      <div className="detail-header">
        <h3>{componentName}</h3>
        <button onClick={onClose} className="btn-close">Close</button>
      </div>

      <div className="detail-stats">
        <div className="detail-stat">
          <span className="stat-value">{Math.round(kpis.trust_score * 100)}%</span>
          <span className="stat-label">Trust Score</span>
        </div>
        <div className="detail-stat">
          <span className="stat-value">{Object.keys(kpis.kpis || {}).length}</span>
          <span className="stat-label">Metrics</span>
        </div>
      </div>

      <div className="detail-timestamps">
        <span>Created: {new Date(kpis.created_at).toLocaleString()}</span>
        <span>Updated: {new Date(kpis.updated_at).toLocaleString()}</span>
      </div>

      <div className="metrics-list">
        <h4>KPI Metrics</h4>
        {Object.values(kpis.kpis || {}).map((metric, index) => (
          <KPIMetric key={index} metric={metric} />
        ))}
        {Object.keys(kpis.kpis || {}).length === 0 && (
          <p className="no-metrics">No metrics recorded yet</p>
        )}
      </div>
    </div>
  );
}

// Main KPI Dashboard Component
export default function KPIDashboard() {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [componentKPIs, setComponentKPIs] = useState(null);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [healthRes, dashboardRes] = await Promise.all([
        fetch(`${API_BASE}/kpi/health`),
        fetch(`${API_BASE}/kpi/dashboard`)
      ]);

      if (healthRes.ok) {
        setHealth(await healthRes.json());
      }

      if (dashboardRes.ok) {
        setDashboard(await dashboardRes.json());
      }
    } catch (err) {
      console.error("Failed to fetch KPI data:", err);
      setError("Failed to load KPI data. Make sure the API is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchComponentKPIs = useCallback(async (componentName) => {
    try {
      const res = await fetch(`${API_BASE}/kpi/components/${componentName}`);
      if (res.ok) {
        setComponentKPIs(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch component KPIs:", err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    if (selectedComponent) {
      fetchComponentKPIs(selectedComponent);
    } else {
      setComponentKPIs(null);
    }
  }, [selectedComponent, fetchComponentKPIs]);

  if (loading && !health) {
    return (
      <div className="kpi-dashboard">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading KPI Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="kpi-dashboard">
      <div className="dashboard-header">
        <div className="header-left">
          <h2>KPI Dashboard</h2>
          <p>Monitor component performance and trust scores</p>
        </div>

        <div className="header-actions">
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

      <div className="dashboard-content">
        <div className="dashboard-main">
          <SystemHealthPanel health={health} />

          {dashboard && (
            <>
              <div className="performance-summary">
                <div className="summary-card top-performers">
                  <h4>Top Performers</h4>
                  {dashboard.top_performers?.length > 0 ? (
                    <ul>
                      {dashboard.top_performers.map((name, i) => (
                        <li key={i} onClick={() => setSelectedComponent(name)}>
                          {name}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="no-data">No top performers yet</p>
                  )}
                </div>

                <div className="summary-card needs-attention">
                  <h4>Needs Attention</h4>
                  {dashboard.needs_attention?.length > 0 ? (
                    <ul>
                      {dashboard.needs_attention.map((name, i) => (
                        <li key={i} onClick={() => setSelectedComponent(name)}>
                          {name}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="no-data">All components healthy</p>
                  )}
                </div>
              </div>

              <div className="components-section">
                <h3>Components ({dashboard.components?.length || 0})</h3>
                <div className="components-grid">
                  {(dashboard.components || []).map((component, index) => (
                    <ComponentCard
                      key={index}
                      component={component}
                      onSelect={setSelectedComponent}
                    />
                  ))}
                </div>

                {(!dashboard.components || dashboard.components.length === 0) && (
                  <div className="empty-state">
                    <p>No components being tracked yet.</p>
                    <p>KPIs will appear as components perform actions.</p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {selectedComponent && (
          <ComponentDetailPanel
            componentName={selectedComponent}
            kpis={componentKPIs}
            onClose={() => setSelectedComponent(null)}
          />
        )}
      </div>
    </div>
  );
}
