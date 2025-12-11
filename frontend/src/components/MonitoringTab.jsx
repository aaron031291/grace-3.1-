import "./MonitoringTab.css";

export default function MonitoringTab() {
  return (
    <div className="monitoring-tab">
      <div className="tab-placeholder">
        <svg
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <polyline points="12 3 20 7.5 20 16.5 12 21 4 16.5 4 7.5 12 3"></polyline>
          <line x1="12" y1="12" x2="20" y2="7.5"></line>
          <line x1="12" y1="12" x2="12" y2="21"></line>
          <line x1="12" y1="12" x2="4" y2="7.5"></line>
        </svg>
        <h2>System Monitoring</h2>
        <p>Monitor the health and performance of the application</p>
        <p className="coming-soon">Coming soon...</p>
      </div>
    </div>
  );
}
