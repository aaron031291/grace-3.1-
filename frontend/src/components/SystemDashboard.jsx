import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";
import "./SystemDashboard.css";

export default function SystemDashboard() {
  const [activeView, setActiveView] = useState("overview");
  const [systemHealth, setSystemHealth] = useState(null);
  const [agents, setAgents] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [playbooks, setPlaybooks] = useState(null);
  const [slaStatus, setSlaStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    await Promise.allSettled([
      fetchJSON(`${API_BASE_URL}/system-health/status`).then(setSystemHealth),
      fetchJSON(`${API_BASE_URL}/pipeline/status`).then(setPipeline),
    ]);
    setLoading(false);
  };

  const fetchJSON = async (url) => {
    try {
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch {}
    return null;
  };

  return (
    <div className="system-dashboard">
      <div className="dash-header">
        <h2>Grace Autonomous Systems</h2>
        <div className="dash-tabs">
          {["overview", "agents", "pipeline", "playbooks", "intelligence"].map((v) => (
            <button
              key={v}
              className={`dash-tab ${activeView === v ? "active" : ""}`}
              onClick={() => setActiveView(v)}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="dash-content">
        {activeView === "overview" && <OverviewPanel health={systemHealth} pipeline={pipeline} loading={loading} />}
        {activeView === "agents" && <AgentsPanel />}
        {activeView === "pipeline" && <PipelinePanel data={pipeline} />}
        {activeView === "playbooks" && <PlaybooksPanel />}
        {activeView === "intelligence" && <IntelligencePanel />}
      </div>
    </div>
  );
}

function OverviewPanel({ health, pipeline, loading }) {
  if (loading) return <div className="loading-spinner">Loading system status...</div>;

  return (
    <div className="overview-grid">
      <div className="stat-card">
        <h3>System Health</h3>
        <div className="stat-value">{health?.overall_status || "Unknown"}</div>
        <div className="stat-detail">{health?.components_healthy || 0} components healthy</div>
      </div>

      <div className="stat-card">
        <h3>Learning Pipeline</h3>
        <div className="stat-value">{pipeline?.running ? "Active" : "Stopped"}</div>
        <div className="stat-detail">
          {pipeline?.stats?.total_expansions || 0} expansions,{" "}
          {pipeline?.stats?.total_topics_discovered || 0} topics
        </div>
      </div>

      <div className="stat-card">
        <h3>Background Daemons</h3>
        <div className="stat-value">10</div>
        <div className="stat-detail">Handshake, Pipeline, Intelligence, Closed-Loop, TimeSense...</div>
      </div>

      <div className="stat-card">
        <h3>Constitutional Rules</h3>
        <div className="stat-value">11</div>
        <div className="stat-detail">Including Honesty, Integrity, Accountability</div>
      </div>
    </div>
  );
}

function AgentsPanel() {
  const [agents, setAgents] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/system-health/status`)
      .then((r) => r.ok ? r.json() : null)
      .then(setAgents)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const agentNames = [
    { key: "self_healer", label: "Self-Healer", icon: "🔧" },
    { key: "self_mirror", label: "Self-Mirror", icon: "🪞" },
    { key: "self_model", label: "Self-Model", icon: "📊" },
    { key: "self_learner", label: "Self-Learner", icon: "📚" },
    { key: "code_agent", label: "Code Agent", icon: "💻" },
    { key: "self_evolver", label: "Self-Evolver", icon: "🧬" },
  ];

  return (
    <div className="agents-panel">
      <h3>Self-* Agent Ecosystem</h3>
      <p className="panel-desc">6 autonomous agents in a closed-loop improvement cycle</p>
      <div className="agent-grid">
        {agentNames.map(({ key, label, icon }) => (
          <div key={key} className="agent-card">
            <div className="agent-icon">{icon}</div>
            <div className="agent-name">{label}</div>
            <div className="agent-status">
              {agents?.subsystems?.[key] ? (
                <>
                  <span className={`status-badge ${agents.subsystems[key].status}`}>
                    {agents.subsystems[key].status}
                  </span>
                  <span className="kpi">KPI: {(agents.subsystems[key].kpi || 0).toFixed(0)}%</span>
                </>
              ) : (
                <span className="status-badge waiting">Waiting for data</span>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="loop-indicator">
        Mirror → Model → Healer → Learner → Code Agent → Evolver → Mirror...
      </div>
    </div>
  );
}

function PipelinePanel({ data }) {
  return (
    <div className="pipeline-panel">
      <h3>24/7 Learning Pipeline</h3>
      <div className="pipeline-stats">
        <div className="pipe-stat">
          <span className="pipe-label">Status</span>
          <span className={`pipe-value ${data?.running ? "active" : "stopped"}`}>
            {data?.running ? "Running" : "Stopped"}
          </span>
        </div>
        <div className="pipe-stat">
          <span className="pipe-label">Total Expansions</span>
          <span className="pipe-value">{data?.stats?.total_expansions || 0}</span>
        </div>
        <div className="pipe-stat">
          <span className="pipe-label">Topics Discovered</span>
          <span className="pipe-value">{data?.stats?.total_topics_discovered || 0}</span>
        </div>
        <div className="pipe-stat">
          <span className="pipe-label">Connections Made</span>
          <span className="pipe-value">{data?.stats?.total_connections_made || 0}</span>
        </div>
        <div className="pipe-stat">
          <span className="pipe-label">Total Cycles</span>
          <span className="pipe-value">{data?.stats?.total_cycles || 0}</span>
        </div>
        <div className="pipe-stat">
          <span className="pipe-label">Pending Seeds</span>
          <span className="pipe-value">{data?.pending_seeds || 0}</span>
        </div>
      </div>

      <div className="pipeline-actions">
        <button onClick={() => fetch(`${API_BASE_URL}/pipeline/start`, { method: "POST" })}>
          Start Pipeline
        </button>
        <button onClick={() => fetch(`${API_BASE_URL}/pipeline/stop`, { method: "POST" })}>
          Stop Pipeline
        </button>
      </div>
    </div>
  );
}

function PlaybooksPanel() {
  const [healingPlaybooks, setHealingPlaybooks] = useState([]);
  const [codePlaybooks, setCodePlaybooks] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/system-health/status`)
      .then((r) => r.ok ? r.json() : { healing_playbooks: [], code_playbooks: [] })
      .then((data) => {
        setHealingPlaybooks(data.healing_playbooks || []);
        setCodePlaybooks(data.code_playbooks || []);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="playbooks-panel">
      <h3>Playbook Library</h3>
      <p className="panel-desc">Proven strategies stored from successful operations</p>

      <div className="playbook-section">
        <h4>Healing Playbooks ({healingPlaybooks.length})</h4>
        {healingPlaybooks.length === 0 ? (
          <p className="empty-msg">No healing playbooks yet. They'll be created as the system heals itself.</p>
        ) : (
          <div className="playbook-list">
            {healingPlaybooks.map((p, i) => (
              <div key={i} className="playbook-item">
                <span className="pb-name">{p.name}</span>
                <span className="pb-trust">Trust: {(p.trust_score * 100).toFixed(0)}%</span>
                <span className="pb-uses">Uses: {p.success_count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="playbook-section">
        <h4>Code Playbooks ({codePlaybooks.length})</h4>
        {codePlaybooks.length === 0 ? (
          <p className="empty-msg">No code playbooks yet. They'll be created as the code agent completes tasks.</p>
        ) : (
          <div className="playbook-list">
            {codePlaybooks.map((p, i) => (
              <div key={i} className="playbook-item">
                <span className="pb-name">{p.name}</span>
                <span className="pb-trust">Trust: {(p.trust_score * 100).toFixed(0)}%</span>
                <span className="pb-uses">Pass rate: {(p.avg_test_pass_rate * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IntelligencePanel() {
  const [snapshot, setSnapshot] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/system-health/status`)
      .then((r) => r.ok ? r.json() : null)
      .then(setSnapshot)
      .catch(() => {});
  }, []);

  return (
    <div className="intelligence-panel">
      <h3>Unified Intelligence</h3>
      <p className="panel-desc">Single source of truth — 18 subsystem collectors every 2 minutes</p>

      <div className="intel-sources">
        {[
          "Component Registry", "KPI Tracker", "Healing Playbooks",
          "Learning Pipeline", "Self-Agents (6)", "Memory Mesh",
          "Magma Memory", "Episodic Memory", "Learning Memory",
          "Genesis Keys", "Document Ingestion", "LLM Tracking",
          "Handshake Protocol", "Governance", "Closed-Loop",
          "3-Layer Reasoning", "HIA Framework", "TimeSense SLAs",
        ].map((source) => (
          <div key={source} className="intel-source">
            <span className="source-dot">●</span>
            <span>{source}</span>
          </div>
        ))}
      </div>

      <div className="intel-footer">
        <p>Librarian audits completeness after every collection cycle.</p>
        <p>ML/DL runs directly on this unified table for predictions and anomaly detection.</p>
      </div>
    </div>
  );
}
