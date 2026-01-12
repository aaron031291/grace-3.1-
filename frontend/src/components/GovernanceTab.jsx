import { useEffect, useState, useCallback } from "react";
import "./GovernanceTab.css";

const API_BASE = "http://localhost:8000";

// Trust score visualization
const getTrustColor = (score) => {
  if (score >= 0.8) return "#10b981";
  if (score >= 0.6) return "#3b82f6";
  if (score >= 0.4) return "#f59e0b";
  return "#ef4444";
};

const getTrustLevel = (score) => {
  if (score >= 0.8) return "High";
  if (score >= 0.6) return "Medium";
  if (score >= 0.4) return "Low";
  return "Critical";
};

// Approval Action Card
function ActionCard({ action, onApprove, onReject }) {
  const [reason, setReason] = useState("");
  const [showReject, setShowReject] = useState(false);

  return (
    <div className={`action-card tier-${action.permission_tier}`}>
      <div className="action-header">
        <span className={`action-type type-${action.action_type}`}>
          {action.action_type.replace(/_/g, " ")}
        </span>
        <span className={`tier-badge tier-${action.permission_tier}`}>
          {action.permission_tier}
        </span>
      </div>

      <div className="action-details">
        {action.document_id && (
          <span className="detail-item">Doc: #{action.document_id}</span>
        )}
        <span className="detail-item">
          Confidence: {Math.round(action.confidence * 100)}%
        </span>
      </div>

      {action.reason && (
        <div className="action-reason">{action.reason}</div>
      )}

      <div className="action-params">
        <code>{JSON.stringify(action.action_params, null, 2)}</code>
      </div>

      <div className="action-meta">
        <span>Created: {new Date(action.created_at).toLocaleString()}</span>
      </div>

      {action.status === "pending" && (
        <div className="action-buttons">
          {showReject ? (
            <div className="reject-form">
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Rejection reason..."
              />
              <button onClick={() => onReject(action.id, reason)} className="btn-danger">
                Confirm Reject
              </button>
              <button onClick={() => setShowReject(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button onClick={() => onApprove(action.id)} className="btn-approve">
                Approve
              </button>
              <button onClick={() => setShowReject(true)} className="btn-reject">
                Reject
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// Neuro-Symbolic Query Component
function NeuroSymbolicQuery({ onQuery }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await onQuery(query);
      setResult(data);
    } catch (err) {
      console.error("Query failed:", err);
    }
    setLoading(false);
  };

  return (
    <div className="neuro-symbolic-query">
      <h4>Neuro-Symbolic Reasoning</h4>
      <p className="description">
        Query the unified reasoning system that combines neural embeddings with symbolic rules.
      </p>

      <div className="query-input">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your query for neuro-symbolic reasoning..."
          rows={3}
        />
        <button onClick={handleQuery} disabled={loading || !query.trim()}>
          {loading ? "Processing..." : "Reason"}
        </button>
      </div>

      {result && (
        <div className="query-result">
          <div className="result-section">
            <h5>Neural Results (Similarity-based)</h5>
            <div className="result-score">
              Confidence: {Math.round((result.neural_confidence || 0) * 100)}%
            </div>
            {result.neural_results && result.neural_results.length > 0 ? (
              <ul>
                {result.neural_results.slice(0, 5).map((r, i) => (
                  <li key={i}>
                    <span className="result-text">{r.content?.slice(0, 150)}...</span>
                    <span className="result-score">{Math.round(r.score * 100)}%</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-results">No neural results</p>
            )}
          </div>

          <div className="result-section">
            <h5>Symbolic Results (Rule-based)</h5>
            <div className="result-score">
              Confidence: {Math.round((result.symbolic_confidence || 0) * 100)}%
            </div>
            {result.symbolic_results && result.symbolic_results.length > 0 ? (
              <ul>
                {result.symbolic_results.slice(0, 5).map((r, i) => (
                  <li key={i}>
                    <span className="result-text">{r.fact || r.content}</span>
                    <span className="result-trust" style={{ color: getTrustColor(r.trust || 0.5) }}>
                      Trust: {Math.round((r.trust || 0.5) * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-results">No symbolic results</p>
            )}
          </div>

          <div className="result-section fused">
            <h5>Fused Results (Combined)</h5>
            <div className="result-score">
              Overall Confidence: {Math.round((result.overall_confidence || 0) * 100)}%
            </div>
            {result.fused_results && result.fused_results.length > 0 ? (
              <ul>
                {result.fused_results.slice(0, 5).map((r, i) => (
                  <li key={i}>
                    <span className="result-text">{r.content?.slice(0, 150)}...</span>
                    <span className="result-score">{Math.round(r.combined_score * 100)}%</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-results">No fused results</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Data Integrity Panel
function DataIntegrityPanel({ stats }) {
  if (!stats) return null;

  return (
    <div className="integrity-panel">
      <h4>Data Integrity</h4>
      <div className="integrity-grid">
        <div className="integrity-item">
          <span className="integrity-label">Verified Documents</span>
          <span className="integrity-value">{stats.verified_count || 0}</span>
        </div>
        <div className="integrity-item">
          <span className="integrity-label">Pending Verification</span>
          <span className="integrity-value warning">{stats.pending_count || 0}</span>
        </div>
        <div className="integrity-item">
          <span className="integrity-label">Failed Checks</span>
          <span className="integrity-value danger">{stats.failed_count || 0}</span>
        </div>
        <div className="integrity-item">
          <span className="integrity-label">System Trust</span>
          <span
            className="integrity-value"
            style={{ color: getTrustColor(stats.system_trust || 0.5) }}
          >
            {getTrustLevel(stats.system_trust || 0.5)}
          </span>
        </div>
      </div>
    </div>
  );
}

// Rule Generation Panel
function RuleGenerationPanel({ onGenerate }) {
  const [loading, setLoading] = useState(false);
  const [generatedRules, setGeneratedRules] = useState([]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const rules = await onGenerate();
      setGeneratedRules(rules || []);
    } catch (err) {
      console.error("Rule generation failed:", err);
    }
    setLoading(false);
  };

  return (
    <div className="rule-generation">
      <h4>Neural-to-Symbolic Rule Generation</h4>
      <p className="description">
        Generate symbolic rules from learned neural patterns.
      </p>

      <button onClick={handleGenerate} disabled={loading} className="btn-generate">
        {loading ? "Generating..." : "Generate Rules from Patterns"}
      </button>

      {generatedRules.length > 0 && (
        <div className="generated-rules">
          <h5>Generated Rules ({generatedRules.length})</h5>
          {generatedRules.map((rule, i) => (
            <div key={i} className="generated-rule">
              <div className="rule-header">
                <span className="rule-name">{rule.name || `Rule ${i + 1}`}</span>
                <span className="rule-confidence">
                  {Math.round((rule.confidence || 0) * 100)}% confident
                </span>
              </div>
              <div className="rule-pattern">
                Pattern: <code>{rule.pattern}</code>
              </div>
              <div className="rule-action">
                Action: {rule.action_type} - {JSON.stringify(rule.action_params)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Main Governance Tab
export default function GovernanceTab() {
  const [activeView, setActiveView] = useState("approvals");
  const [pendingActions, setPendingActions] = useState([]);
  const [actionStats, setActionStats] = useState(null);
  const [integrityStats, setIntegrityStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch pending actions
  const fetchPendingActions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/librarian/actions/pending`);
      if (!response.ok) throw new Error("Failed to fetch pending actions");
      const data = await response.json();
      setPendingActions(data.actions || []);
      setActionStats({
        pending: data.pending_count,
        approved: data.approved_count,
        rejected: data.rejected_count,
        total: data.total
      });
    } catch (err) {
      console.error("Error fetching actions:", err);
    }
  }, []);

  // Fetch integrity stats (simulated)
  const fetchIntegrityStats = useCallback(async () => {
    try {
      // Try to fetch from data integrity connector
      const response = await fetch(`${API_BASE}/layer1/data-integrity/stats`);
      if (response.ok) {
        const data = await response.json();
        setIntegrityStats(data);
      } else {
        // Fallback to default stats
        setIntegrityStats({
          verified_count: 0,
          pending_count: 0,
          failed_count: 0,
          system_trust: 0.5
        });
      }
    } catch (err) {
      setIntegrityStats({
        verified_count: 0,
        pending_count: 0,
        failed_count: 0,
        system_trust: 0.5
      });
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        await Promise.all([
          fetchPendingActions(),
          fetchIntegrityStats()
        ]);
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    };
    loadData();
  }, [fetchPendingActions, fetchIntegrityStats]);

  // Action handlers
  const approveAction = async (actionId) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/actions/${actionId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewed_by: "user", notes: "" })
      });
      if (!response.ok) throw new Error("Failed to approve action");
      fetchPendingActions();
    } catch (err) {
      console.error("Error approving action:", err);
      alert("Failed to approve: " + err.message);
    }
  };

  const rejectAction = async (actionId, reason) => {
    try {
      const response = await fetch(`${API_BASE}/librarian/actions/${actionId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewed_by: "user", reason: reason || "Rejected by user" })
      });
      if (!response.ok) throw new Error("Failed to reject action");
      fetchPendingActions();
    } catch (err) {
      console.error("Error rejecting action:", err);
      alert("Failed to reject: " + err.message);
    }
  };

  const batchApprove = async () => {
    if (!confirm("Approve all pending actions?")) return;
    try {
      const actionIds = pendingActions.map(a => a.id);
      const response = await fetch(`${API_BASE}/librarian/actions/batch-approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_ids: actionIds, reviewed_by: "user" })
      });
      if (!response.ok) throw new Error("Failed to batch approve");
      fetchPendingActions();
    } catch (err) {
      console.error("Error batch approving:", err);
      alert("Failed to batch approve: " + err.message);
    }
  };

  // Neuro-symbolic query
  const runNeuroSymbolicQuery = async (query) => {
    try {
      const response = await fetch(`${API_BASE}/layer1/neuro-symbolic/reason`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (!response.ok) {
        // Fallback: return simulated result
        return {
          neural_results: [],
          symbolic_results: [],
          fused_results: [],
          neural_confidence: 0,
          symbolic_confidence: 0,
          overall_confidence: 0
        };
      }
      return await response.json();
    } catch (err) {
      console.error("Query failed:", err);
      throw err;
    }
  };

  // Rule generation
  const generateRules = async () => {
    try {
      const response = await fetch(`${API_BASE}/layer1/neuro-symbolic/generate-rules`, {
        method: "POST"
      });
      if (!response.ok) {
        return []; // Return empty if endpoint doesn't exist
      }
      const data = await response.json();
      return data.rules || [];
    } catch (err) {
      console.error("Rule generation failed:", err);
      return [];
    }
  };

  if (loading) {
    return (
      <div className="governance-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading Governance System...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="governance-tab">
      <div className="governance-header">
        <div className="header-left">
          <h2>Governance</h2>
          <p>Approval workflows, trust management, and neuro-symbolic reasoning</p>
        </div>
        <div className="header-stats">
          {actionStats && (
            <>
              <div className="stat-item warning">
                <span className="stat-value">{actionStats.pending}</span>
                <span className="stat-label">Pending</span>
              </div>
              <div className="stat-item success">
                <span className="stat-value">{actionStats.approved}</span>
                <span className="stat-label">Approved</span>
              </div>
              <div className="stat-item danger">
                <span className="stat-value">{actionStats.rejected}</span>
                <span className="stat-label">Rejected</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="governance-toolbar">
        <div className="view-tabs">
          <button
            className={activeView === "approvals" ? "active" : ""}
            onClick={() => setActiveView("approvals")}
          >
            Approvals
          </button>
          <button
            className={activeView === "reasoning" ? "active" : ""}
            onClick={() => setActiveView("reasoning")}
          >
            Reasoning
          </button>
          <button
            className={activeView === "rules" ? "active" : ""}
            onClick={() => setActiveView("rules")}
          >
            Rule Generation
          </button>
          <button
            className={activeView === "integrity" ? "active" : ""}
            onClick={() => setActiveView("integrity")}
          >
            Data Integrity
          </button>
        </div>
        <div className="toolbar-spacer" />
        {activeView === "approvals" && pendingActions.length > 0 && (
          <button className="btn-approve-all" onClick={batchApprove}>
            Approve All ({pendingActions.length})
          </button>
        )}
        <button className="btn-refresh" onClick={fetchPendingActions}>
          Refresh
        </button>
      </div>

      <div className="governance-content">
        {activeView === "approvals" && (
          <div className="approvals-view">
            {pendingActions.length === 0 ? (
              <div className="empty-state">
                <p>No pending actions require approval</p>
              </div>
            ) : (
              <div className="actions-list">
                {pendingActions.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    onApprove={approveAction}
                    onReject={rejectAction}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeView === "reasoning" && (
          <div className="reasoning-view">
            <NeuroSymbolicQuery onQuery={runNeuroSymbolicQuery} />
          </div>
        )}

        {activeView === "rules" && (
          <div className="rules-view">
            <RuleGenerationPanel onGenerate={generateRules} />
          </div>
        )}

        {activeView === "integrity" && (
          <div className="integrity-view">
            <DataIntegrityPanel stats={integrityStats} />
          </div>
        )}
      </div>
    </div>
  );
}
