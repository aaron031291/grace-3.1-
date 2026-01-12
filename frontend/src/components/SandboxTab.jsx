import { useEffect, useState, useCallback } from "react";
import "./SandboxTab.css";

const API_BASE = "http://localhost:8000";

// Active Process Card
function ProcessCard({ process, onStop, onViewLogs }) {
  const getStatusColor = (status) => {
    switch (status) {
      case "running": return "#10b981";
      case "paused": return "#f59e0b";
      case "error": return "#ef4444";
      case "completed": return "#3b82f6";
      default: return "#6b7280";
    }
  };

  return (
    <div className={`process-card status-${process.status}`}>
      <div className="process-header">
        <span className="process-name">{process.name}</span>
        <span
          className="process-status"
          style={{ backgroundColor: getStatusColor(process.status) }}
        >
          {process.status}
        </span>
      </div>

      <div className="process-type">
        <span className={`type-badge type-${process.type}`}>
          {process.type}
        </span>
      </div>

      {process.description && (
        <p className="process-description">{process.description}</p>
      )}

      <div className="process-metrics">
        {process.progress !== undefined && (
          <div className="progress-section">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${process.progress}%` }}
              />
            </div>
            <span className="progress-text">{process.progress}%</span>
          </div>
        )}

        <div className="metrics-row">
          {process.memory_usage && (
            <span className="metric">
              Memory: {process.memory_usage}
            </span>
          )}
          {process.cpu_usage && (
            <span className="metric">
              CPU: {process.cpu_usage}%
            </span>
          )}
          {process.duration && (
            <span className="metric">
              Duration: {process.duration}
            </span>
          )}
        </div>
      </div>

      <div className="process-meta">
        <span>Started: {new Date(process.started_at).toLocaleString()}</span>
        {process.genesis_key && (
          <span className="genesis-key" title={process.genesis_key}>
            Key: {process.genesis_key.slice(0, 12)}...
          </span>
        )}
      </div>

      <div className="process-actions">
        <button onClick={() => onViewLogs(process)} className="btn-logs">
          View Logs
        </button>
        {process.status === "running" && (
          <button onClick={() => onStop(process.id)} className="btn-stop">
            Stop
          </button>
        )}
      </div>
    </div>
  );
}

// Queue Item Card
function QueueItem({ item, onRemove }) {
  return (
    <div className="queue-item">
      <div className="queue-info">
        <span className="queue-name">{item.name}</span>
        <span className={`queue-priority priority-${item.priority}`}>
          {item.priority}
        </span>
      </div>
      <div className="queue-meta">
        <span>Queued: {new Date(item.queued_at).toLocaleTimeString()}</span>
        <span>Type: {item.type}</span>
      </div>
      <button onClick={() => onRemove(item.id)} className="btn-remove">
        Remove
      </button>
    </div>
  );
}

// Logs Modal
function LogsModal({ process, logs, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content logs-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Logs: {process.name}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <div className="logs-content">
          {logs.length === 0 ? (
            <p className="no-logs">No logs available</p>
          ) : (
            <pre className="logs-text">
              {logs.map((log, i) => (
                <div key={i} className={`log-line level-${log.level}`}>
                  <span className="log-time">{log.timestamp}</span>
                  <span className={`log-level ${log.level}`}>{log.level}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </pre>
          )}
        </div>
        <div className="modal-actions">
          <button onClick={onClose} className="btn-secondary">Close</button>
        </div>
      </div>
    </div>
  );
}

// System Resources Panel
function SystemResources({ resources }) {
  if (!resources) return null;

  return (
    <div className="system-resources">
      <h4>System Resources</h4>
      <div className="resources-grid">
        <div className="resource-card">
          <span className="resource-label">CPU</span>
          <div className="resource-bar">
            <div
              className="resource-fill cpu"
              style={{ width: `${resources.cpu || 0}%` }}
            />
          </div>
          <span className="resource-value">{resources.cpu || 0}%</span>
        </div>
        <div className="resource-card">
          <span className="resource-label">Memory</span>
          <div className="resource-bar">
            <div
              className="resource-fill memory"
              style={{ width: `${resources.memory || 0}%` }}
            />
          </div>
          <span className="resource-value">{resources.memory || 0}%</span>
        </div>
        <div className="resource-card">
          <span className="resource-label">GPU</span>
          <div className="resource-bar">
            <div
              className="resource-fill gpu"
              style={{ width: `${resources.gpu || 0}%` }}
            />
          </div>
          <span className="resource-value">{resources.gpu || 0}%</span>
        </div>
        <div className="resource-card">
          <span className="resource-label">Disk I/O</span>
          <div className="resource-bar">
            <div
              className="resource-fill disk"
              style={{ width: `${resources.disk || 0}%` }}
            />
          </div>
          <span className="resource-value">{resources.disk || 0}%</span>
        </div>
      </div>
    </div>
  );
}

// Main Sandbox Tab
export default function SandboxTab() {
  const [activeProcesses, setActiveProcesses] = useState([]);
  const [queuedItems, setQueuedItems] = useState([]);
  const [recentCompleted, setRecentCompleted] = useState([]);
  const [systemResources, setSystemResources] = useState(null);
  const [loading, setLoading] = useState(true);
  const [logsModal, setLogsModal] = useState({ open: false, process: null, logs: [] });

  // Fetch active processes
  const fetchProcesses = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sandbox/processes`);
      if (response.ok) {
        const data = await response.json();
        setActiveProcesses(data.active || []);
        setQueuedItems(data.queued || []);
        setRecentCompleted(data.completed || []);
      } else {
        // Fallback demo data
        setActiveProcesses([
          {
            id: "proc-1",
            name: "Document Ingestion Pipeline",
            type: "ingestion",
            status: "running",
            progress: 67,
            description: "Processing uploaded documents for RAG system",
            started_at: new Date().toISOString(),
            memory_usage: "256MB",
            cpu_usage: 45,
            duration: "2m 34s",
            genesis_key: "gk-abc123def456"
          },
          {
            id: "proc-2",
            name: "Neuro-Symbolic Rule Learning",
            type: "learning",
            status: "running",
            progress: 23,
            description: "Generating symbolic rules from neural patterns",
            started_at: new Date(Date.now() - 300000).toISOString(),
            memory_usage: "512MB",
            cpu_usage: 78,
            duration: "5m 12s",
            genesis_key: "gk-xyz789abc123"
          }
        ]);
      }
    } catch (err) {
      console.error("Error fetching processes:", err);
    }
  }, []);

  // Fetch system resources
  const fetchResources = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sandbox/resources`);
      if (response.ok) {
        const data = await response.json();
        setSystemResources(data);
      } else {
        // Fallback demo data
        setSystemResources({
          cpu: 45,
          memory: 62,
          gpu: 30,
          disk: 15
        });
      }
    } catch (err) {
      console.error("Error fetching resources:", err);
    }
  }, []);

  // Initial load and polling
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchProcesses(), fetchResources()]);
      setLoading(false);
    };
    loadData();

    // Poll for updates
    const interval = setInterval(() => {
      fetchProcesses();
      fetchResources();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchProcesses, fetchResources]);

  // Stop process
  const stopProcess = async (processId) => {
    try {
      const response = await fetch(`${API_BASE}/sandbox/processes/${processId}/stop`, {
        method: "POST"
      });
      if (response.ok) {
        fetchProcesses();
      }
    } catch (err) {
      console.error("Error stopping process:", err);
    }
  };

  // View logs
  const viewLogs = async (process) => {
    try {
      const response = await fetch(`${API_BASE}/sandbox/processes/${process.id}/logs`);
      if (response.ok) {
        const data = await response.json();
        setLogsModal({ open: true, process, logs: data.logs || [] });
      } else {
        // Demo logs
        setLogsModal({
          open: true,
          process,
          logs: [
            { timestamp: "12:34:56", level: "info", message: "Process started" },
            { timestamp: "12:34:57", level: "info", message: "Loading configuration..." },
            { timestamp: "12:34:58", level: "debug", message: "Connected to database" },
            { timestamp: "12:35:00", level: "info", message: "Processing batch 1/10" },
            { timestamp: "12:35:15", level: "info", message: "Processing batch 2/10" },
          ]
        });
      }
    } catch (err) {
      console.error("Error fetching logs:", err);
    }
  };

  // Remove from queue
  const removeFromQueue = async (itemId) => {
    try {
      const response = await fetch(`${API_BASE}/sandbox/queue/${itemId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        fetchProcesses();
      }
    } catch (err) {
      console.error("Error removing from queue:", err);
    }
  };

  if (loading) {
    return (
      <div className="sandbox-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Sandbox...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="sandbox-tab">
      <div className="sandbox-header">
        <div className="header-left">
          <h2>Sandbox</h2>
          <p>Monitor active processes and system resources</p>
        </div>
        <div className="header-stats">
          <div className="stat-item running">
            <span className="stat-value">
              {activeProcesses.filter(p => p.status === "running").length}
            </span>
            <span className="stat-label">Running</span>
          </div>
          <div className="stat-item queued">
            <span className="stat-value">{queuedItems.length}</span>
            <span className="stat-label">Queued</span>
          </div>
          <div className="stat-item completed">
            <span className="stat-value">{recentCompleted.length}</span>
            <span className="stat-label">Completed</span>
          </div>
        </div>
      </div>

      <div className="sandbox-content">
        <div className="main-panel">
          <SystemResources resources={systemResources} />

          <div className="processes-section">
            <h4>Active Processes ({activeProcesses.length})</h4>
            {activeProcesses.length === 0 ? (
              <div className="empty-state">
                <p>No active processes running</p>
              </div>
            ) : (
              <div className="processes-grid">
                {activeProcesses.map((process) => (
                  <ProcessCard
                    key={process.id}
                    process={process}
                    onStop={stopProcess}
                    onViewLogs={viewLogs}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="side-panel">
          <div className="queue-section">
            <h4>Queue ({queuedItems.length})</h4>
            {queuedItems.length === 0 ? (
              <p className="empty-queue">No items in queue</p>
            ) : (
              <div className="queue-list">
                {queuedItems.map((item) => (
                  <QueueItem
                    key={item.id}
                    item={item}
                    onRemove={removeFromQueue}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="completed-section">
            <h4>Recently Completed</h4>
            {recentCompleted.length === 0 ? (
              <p className="empty-completed">No recent completions</p>
            ) : (
              <div className="completed-list">
                {recentCompleted.slice(0, 5).map((item) => (
                  <div key={item.id} className="completed-item">
                    <span className="completed-name">{item.name}</span>
                    <span className="completed-time">
                      {new Date(item.completed_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {logsModal.open && (
        <LogsModal
          process={logsModal.process}
          logs={logsModal.logs}
          onClose={() => setLogsModal({ open: false, process: null, logs: [] })}
        />
      )}
    </div>
  );
}
