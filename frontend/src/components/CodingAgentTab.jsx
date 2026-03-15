import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";

const C = {
  bg: '#0a0b14', bgAlt: '#111420', bgPanel: '#0d0e18',
  accent: '#e94560', blue: '#3498db', green: '#2ecc71',
  red: '#e74c3c', yellow: '#f1c40f', orange: '#e67e22',
  text: '#fff', muted: '#636e72', border: '#1a1d2e',
};

function HealthBadge({ health }) {
  const colors = { healthy: C.green, warning: C.yellow, broken: C.red };
  const labels = { healthy: '✓ Healthy', warning: '⚠ Warning', broken: '✗ Broken' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
      background: `${colors[health] || C.muted}20`,
      color: colors[health] || C.muted,
      border: `1px solid ${colors[health] || C.muted}40`,
    }}>
      {labels[health] || health}
    </span>
  );
}

function CodePanel({ code, health }) {
  if (!code) return <div style={{ color: C.muted, fontSize: 12, padding: 12 }}>No code output</div>;
  const borderColor = health === 'healthy' ? C.green : health === 'broken' ? C.red : C.yellow;
  return (
    <pre style={{
      background: '#050610',
      border: `1px solid ${borderColor}40`,
      borderLeft: `3px solid ${borderColor}`,
      borderRadius: 6,
      padding: 12,
      fontSize: 12,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      color: '#e0e0e0',
      overflow: 'auto',
      maxHeight: 300,
      margin: '8px 0',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    }}>
      {code}
    </pre>
  );
}

export default function CodingAgentTab() {
  const [status, setStatus] = useState(null);
  const [items, setItems] = useState([]);
  const [health, setHealth] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [reviewing, setReviewing] = useState({});
  const [autofixing, setAutofixing] = useState({});
  const [hardening, setHardening] = useState(false);

  const fetchAll = () => {
    fetch(`${API_BASE_URL}/coding-agent/governance/status`).then(r => r.json()).then(setStatus).catch(() => {});
    fetch(`${API_BASE_URL}/coding-agent/governance/pending`).then(r => r.json()).then(d => setItems(d.items || [])).catch(() => {});
    fetch(`${API_BASE_URL}/coding-agent/governance/health`).then(r => r.json()).then(setHealth).catch(() => {});
  };

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, []);

  const submitReview = async (taskId, decision) => {
    setReviewing(r => ({ ...r, [taskId]: true }));
    try {
      await fetch(`${API_BASE_URL}/coding-agent/governance/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, decision }),
      });
      fetchAll();
    } catch (e) { /* ignore */ }
    setReviewing(r => ({ ...r, [taskId]: false }));
  };

  const triggerAutofix = async (item) => {
    if (!item.patch) return;
    setAutofixing(a => ({ ...a, [item.task_id]: true }));
    try {
      const res = await fetch(`${API_BASE_URL}/coding-agent/governance/autofix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: item.task_id, file_path: '', patch_code: item.patch }),
      });
      const data = await res.json();
      if (data.applied) {
        fetchAll();
      }
    } catch (e) { /* ignore */ }
    setAutofixing(a => ({ ...a, [item.task_id]: false }));
  };

  const runHardening = async () => {
    setHardening(true);
    try {
      await fetch(`${API_BASE_URL}/coding-agent/governance/run-hardening`, { method: 'POST' });
    } catch (e) { /* ignore */ }
    setTimeout(() => setHardening(false), 3000);
  };

  const poolData = status?.data || {};

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: C.bg, color: C.text, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>🤖</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Coding Agent Governance</span>
          <span style={{ fontSize: 11, color: C.muted }}>HITL Review Panel</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Active jobs indicator */}
          <div style={{
            padding: '4px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
            background: poolData.active_jobs > 0 ? `${C.blue}20` : `${C.muted}15`,
            color: poolData.active_jobs > 0 ? C.blue : C.muted,
            border: `1px solid ${poolData.active_jobs > 0 ? C.blue : C.muted}30`,
          }}>
            ⚡ {poolData.active_jobs || 0}/{poolData.max_concurrent_jobs || 5} Active
          </div>
          {/* Health summary */}
          {health && (
            <>
              <span style={{ color: C.green, fontSize: 11 }}>✓ {health.healthy || 0}</span>
              <span style={{ color: C.yellow, fontSize: 11 }}>⚠ {health.warning || 0}</span>
              <span style={{ color: C.red, fontSize: 11 }}>✗ {health.broken || 0}</span>
            </>
          )}
          <button onClick={runHardening} disabled={hardening} style={{
            background: hardening ? `${C.accent}40` : C.accent, color: '#fff', border: 'none',
            borderRadius: 6, padding: '4px 12px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
            opacity: hardening ? 0.7 : 1,
          }}>{hardening ? '⏳ Dispatching 20 tasks...' : '🔩 Run Hardening (20 tasks)'}</button>
          <button onClick={fetchAll} style={{
            background: 'none', border: `1px solid ${C.border}`, color: C.muted,
            borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer',
          }}>↻ Refresh</button>
        </div>
      </div>

      {/* Results list */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {items.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: C.muted, fontSize: 13 }}>
            No coding agent results yet. Run the coding pipeline to generate output.
          </div>
        )}
        {items.map((item, i) => (
          <div key={item.task_id + i} style={{
            background: C.bgPanel, border: `1px solid ${C.border}`,
            borderRadius: 8, marginBottom: 8, overflow: 'hidden',
          }}>
            {/* Result header — always visible */}
            <div
              onClick={() => setExpanded(expanded === i ? null : i)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 14px', cursor: 'pointer',
                borderBottom: expanded === i ? `1px solid ${C.border}` : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 14 }}>{item.agent === 'kimi' ? '🧠' : item.agent === 'opus' ? '🎭' : '🦙'}</span>
                <span style={{ fontWeight: 600, fontSize: 13, textTransform: 'capitalize' }}>{item.agent}</span>
                <HealthBadge health={item.health} />
                <span style={{ fontSize: 11, color: C.muted }}>
                  {(item.confidence * 100).toFixed(0)}% confidence
                </span>
                {item.duration_s && (
                  <span style={{ fontSize: 11, color: C.muted }}>{item.duration_s.toFixed(1)}s</span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {item.genesis_key && (
                  <span style={{ fontSize: 10, color: C.muted, fontFamily: 'monospace' }}>
                    GK:{item.genesis_key.slice(0, 12)}
                  </span>
                )}
                <span style={{ fontSize: 11, color: C.muted }}>{expanded === i ? '▲' : '▼'}</span>
              </div>
            </div>

            {/* Expanded detail — code panel + actions */}
            {expanded === i && (
              <div style={{ padding: '0 14px 14px' }}>
                {/* Code panel */}
                {item.patch && <CodePanel code={item.patch} health={item.health} />}

                {/* Analysis */}
                {item.analysis && (
                  <div style={{
                    background: `${C.blue}10`, border: `1px solid ${C.blue}20`,
                    borderRadius: 6, padding: 10, fontSize: 12, color: '#b0c4de',
                    margin: '8px 0',
                  }}>
                    <strong>Analysis:</strong> {item.analysis}
                  </div>
                )}

                {/* Error */}
                {item.error && (
                  <div style={{
                    background: `${C.red}10`, border: `1px solid ${C.red}20`,
                    borderRadius: 6, padding: 10, fontSize: 12, color: '#e8a0a0',
                    margin: '8px 0',
                  }}>
                    <strong>Error:</strong> {item.error}
                  </div>
                )}

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button
                    onClick={() => submitReview(item.task_id, 'accept')}
                    disabled={reviewing[item.task_id]}
                    style={{
                      background: C.green, color: '#fff', border: 'none',
                      borderRadius: 6, padding: '6px 16px', fontSize: 12,
                      fontWeight: 600, cursor: 'pointer', opacity: reviewing[item.task_id] ? 0.5 : 1,
                    }}
                  >
                    ✓ Accept
                  </button>
                  <button
                    onClick={() => submitReview(item.task_id, 'reject')}
                    disabled={reviewing[item.task_id]}
                    style={{
                      background: C.red, color: '#fff', border: 'none',
                      borderRadius: 6, padding: '6px 16px', fontSize: 12,
                      fontWeight: 600, cursor: 'pointer', opacity: reviewing[item.task_id] ? 0.5 : 1,
                    }}
                  >
                    ✗ Reject
                  </button>
                  {item.patch && item.health === 'broken' && (
                    <button
                      onClick={() => triggerAutofix(item)}
                      disabled={autofixing[item.task_id]}
                      style={{
                        background: C.orange, color: '#fff', border: 'none',
                        borderRadius: 6, padding: '6px 16px', fontSize: 12,
                        fontWeight: 600, cursor: 'pointer', opacity: autofixing[item.task_id] ? 0.5 : 1,
                      }}
                    >
                      {autofixing[item.task_id] ? '⏳ Fixing...' : '🔧 Autofix'}
                    </button>
                  )}
                  {item.patch && item.health !== 'broken' && (
                    <button
                      onClick={() => triggerAutofix(item)}
                      disabled={autofixing[item.task_id]}
                      style={{
                        background: 'none', color: C.blue, border: `1px solid ${C.blue}40`,
                        borderRadius: 6, padding: '6px 16px', fontSize: 12,
                        fontWeight: 600, cursor: 'pointer', opacity: autofixing[item.task_id] ? 0.5 : 1,
                      }}
                    >
                      {autofixing[item.task_id] ? '⏳ Applying...' : '▶ Apply'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
