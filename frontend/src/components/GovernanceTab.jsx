import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3',
};

const btn = (bg = C.accentAlt) => ({
  padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg, transition: 'opacity .15s',
});

function StatusBadge({ status }) {
  const colors = {
    approved: C.success, completed: C.success, healthy: C.success, excellent: C.success, good: C.success,
    pending: C.warn, discussion: C.warn, fair: C.warn, degraded: C.warn, warning: C.warn,
    denied: C.error, failed: C.error, poor: C.error, critical: C.error,
  };
  const bg = colors[(status || '').toLowerCase()] || C.dim;
  return (
    <span style={{
      fontSize: 10, padding: '2px 8px', borderRadius: 10, fontWeight: 700,
      background: bg + '30', color: bg, textTransform: 'uppercase', letterSpacing: '0.3px',
    }}>{status || 'unknown'}</span>
  );
}

function MeterBar({ value, max = 100, color = C.accent }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ height: 6, background: C.bgDark, borderRadius: 3, overflow: 'hidden', flex: 1 }}>
      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width .4s' }} />
    </div>
  );
}

function Card({ title, children, extra }) {
  return (
    <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{title}</span>
        {extra}
      </div>
      {children}
    </div>
  );
}

// ── Sub-tab: Approvals ────────────────────────────────────────────────
function ApprovalsPanel() {
  const [pending, setPending] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actioning, setActioning] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [pRes, hRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/governance-hub/approvals`),
      fetch(`${API_BASE_URL}/api/governance-hub/approvals/history?limit=30`),
    ]);
    if (pRes.status === 'fulfilled' && pRes.value.ok) setPending((await pRes.value.json()).decisions || []);
    if (hRes.status === 'fulfilled' && hRes.value.ok) setHistory((await hRes.value.json()).decisions || []);
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleAction = async (id, decision) => {
    setActioning(id);
    try {
      await fetch(`${API_BASE_URL}/api/governance-hub/approvals/${id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      });
      refresh();
    } catch { /* silent */ }
    finally { setActioning(null); }
  };

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading approvals...</div>;

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      <Card title={`Pending Approvals (${pending.length})`} extra={
        <button onClick={refresh} style={btn(C.bgDark)}>↻ Refresh</button>
      }>
        {pending.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 13 }}>No pending approvals</div>
        ) : pending.map(d => (
          <div key={d.id} style={{ padding: '10px 12px', marginBottom: 6, background: C.bg, borderRadius: 6, border: `1px solid ${C.border}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <StatusBadge status={d.severity} />
              <span style={{ fontSize: 13, fontWeight: 600 }}>{d.title}</span>
              <span style={{ fontSize: 10, color: C.dim, marginLeft: 'auto' }}>{d.pillar_type}</span>
            </div>
            {d.description && <div style={{ fontSize: 12, color: C.muted, marginBottom: 8, lineHeight: 1.4 }}>{d.description}</div>}
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={() => handleAction(d.id, 'approve')} disabled={actioning === d.id} style={btn(C.success)}>✓ Approve</button>
              <button onClick={() => handleAction(d.id, 'deny')} disabled={actioning === d.id} style={btn(C.error)}>✕ Deny</button>
              <button onClick={() => handleAction(d.id, 'discuss')} disabled={actioning === d.id} style={btn(C.warn)}>💬 Discuss</button>
            </div>
          </div>
        ))}
      </Card>

      <Card title={`Decision History (${history.length})`}>
        {history.length === 0 ? (
          <div style={{ padding: 16, textAlign: 'center', color: C.dim, fontSize: 12 }}>No history</div>
        ) : history.map(d => (
          <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
            <StatusBadge status={d.status} />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title}</span>
            <span style={{ color: C.dim, fontSize: 10, flexShrink: 0 }}>{d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}

// ── Sub-tab: Scores ───────────────────────────────────────────────────
function ScoresPanel() {
  const [scores, setScores] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/governance-hub/scores`)
      .then(r => r.ok ? r.json() : { components: [] })
      .then(setScores).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading scores...</div>;
  if (!scores) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Failed to load</div>;

  const systemTrust = scores.system_trust?.trust_score || 0;
  const trustColor = systemTrust >= 0.8 ? C.success : systemTrust >= 0.5 ? C.warn : C.error;

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      <Card title="System Trust Score">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
          <span style={{ fontSize: 36, fontWeight: 800, color: trustColor }}>{(systemTrust * 100).toFixed(0)}%</span>
          <div style={{ flex: 1 }}>
            <MeterBar value={systemTrust * 100} color={trustColor} />
            <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
              Status: <StatusBadge status={scores.system_trust?.status || 'unknown'} />
            </div>
          </div>
        </div>
      </Card>

      <Card title={`Component Scores (${scores.component_count})`}>
        {(scores.components || []).length === 0 ? (
          <div style={{ padding: 16, textAlign: 'center', color: C.dim, fontSize: 12 }}>No components tracked yet</div>
        ) : (scores.components || []).map((comp, i) => {
          const ts = comp.trust_score || 0;
          const tc = ts >= 0.8 ? C.success : ts >= 0.5 ? C.warn : C.error;
          return (
            <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${C.border}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>{comp.name}</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: tc }}>{(ts * 100).toFixed(0)}%</span>
                <StatusBadge status={comp.status} />
              </div>
              <MeterBar value={ts * 100} color={tc} />
            </div>
          );
        })}
      </Card>
    </div>
  );
}

// ── Sub-tab: Performance ──────────────────────────────────────────────
function PerformancePanel() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    setLoading(true);
    fetch(`${API_BASE_URL}/api/governance-hub/performance`)
      .then(r => r.ok ? r.json() : null)
      .then(setMetrics).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { queueMicrotask(refresh); const i = setInterval(refresh, 15000); return () => clearInterval(i); }, [refresh]);

  if (loading && !metrics) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading metrics...</div>;
  if (!metrics) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Failed to load</div>;

  const cpuColor = (metrics.cpu?.total_percent || 0) > 80 ? C.error : (metrics.cpu?.total_percent || 0) > 50 ? C.warn : C.success;
  const memColor = (metrics.memory?.percent || 0) > 80 ? C.error : (metrics.memory?.percent || 0) > 50 ? C.warn : C.success;
  const diskColor = (metrics.disk?.percent || 0) > 80 ? C.error : (metrics.disk?.percent || 0) > 50 ? C.warn : C.success;

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'CPU', val: metrics.cpu?.total_percent, unit: '%', color: cpuColor, sub: `${metrics.cpu?.core_count} cores` },
          { label: 'Memory', val: metrics.memory?.percent, unit: '%', color: memColor, sub: `${metrics.memory?.used_gb} / ${metrics.memory?.total_gb} GB` },
          { label: 'Disk', val: metrics.disk?.percent, unit: '%', color: diskColor, sub: `${metrics.disk?.used_gb} / ${metrics.disk?.total_gb} GB` },
        ].map((m, i) => (
          <div key={i} style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>{m.label}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: m.color }}>{(m.val || 0).toFixed(1)}{m.unit}</div>
            <MeterBar value={m.val || 0} color={m.color} />
            <div style={{ fontSize: 10, color: C.dim, marginTop: 6 }}>{m.sub}</div>
          </div>
        ))}
      </div>

      {metrics.cpu?.per_core && (
        <Card title="CPU Per Core">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(60px, 1fr))', gap: 6 }}>
            {metrics.cpu.per_core.map((v, i) => (
              <div key={i} style={{ textAlign: 'center', padding: 6, background: C.bg, borderRadius: 4, border: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 10, color: C.dim }}>Core {i}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: v > 80 ? C.error : v > 50 ? C.warn : C.success }}>{v.toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {metrics.database && (
        <Card title="Database">
          <div style={{ display: 'flex', gap: 24, fontSize: 13 }}>
            <div><span style={{ color: C.muted }}>Tables:</span> <b>{metrics.database.tables}</b></div>
            <div><span style={{ color: C.muted }}>Rows:</span> <b>{(metrics.database.total_rows || 0).toLocaleString()}</b></div>
          </div>
        </Card>
      )}

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button onClick={refresh} style={btn(C.bgDark)}>↻ Refresh Metrics</button>
      </div>
    </div>
  );
}

// ── Sub-tab: Actions (Healing + Learning) ─────────────────────────────
function ActionsPanel() {
  const [healActions, setHealActions] = useState([]);
  const [triggering, setTriggering] = useState(null);
  const [learnQuery, setLearnQuery] = useState('');
  const [learnMethod, setLearnMethod] = useState('kimi');
  const [learnResult, setLearnResult] = useState(null);
  const [learnLoading, setLearnLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/governance-hub/healing/actions`)
      .then(r => r.ok ? r.json() : { actions: [] })
      .then(d => setHealActions(d.actions || []))
      .catch(() => {});
  }, []);

  const triggerHealing = async (action) => {
    setTriggering(action);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-hub/healing/trigger`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) setNotification(`Healing action '${action}' triggered`);
    } catch { /* silent */ }
    finally { setTriggering(null); setTimeout(() => setNotification(null), 3000); }
  };

  const triggerLearning = async () => {
    if (!learnQuery.trim()) return;
    setLearnLoading(true);
    setLearnResult(null);
    try {
      const body = { method: learnMethod };
      if (learnMethod === 'kimi' || learnMethod === 'websearch') body.query = learnQuery;
      if (learnMethod === 'study') body.topic = learnQuery;
      if (learnMethod === 'websearch') body.url = learnQuery;

      const res = await fetch(`${API_BASE_URL}/api/governance-hub/learning/trigger`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) setLearnResult(await res.json());
    } catch (e) { setLearnResult({ error: e.message }); }
    finally { setLearnLoading(false); }
  };

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      {notification && (
        <div style={{ padding: '8px 16px', marginBottom: 12, background: C.success + '30', border: `1px solid ${C.success}`, borderRadius: 6, fontSize: 12, color: C.success }}>{notification}</div>
      )}

      <Card title="🔧 Self-Healing Actions">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {healActions.map(a => (
            <button
              key={a.id}
              onClick={() => triggerHealing(a.id)}
              disabled={triggering === a.id}
              style={{
                ...btn(C.bgDark), padding: '10px 12px', textAlign: 'left',
                display: 'flex', flexDirection: 'column', gap: 4,
                opacity: triggering === a.id ? 0.5 : 1,
              }}
            >
              <span style={{ fontWeight: 700, fontSize: 12 }}>{a.name}</span>
              <span style={{ fontWeight: 400, fontSize: 10, color: C.dim }}>{a.description}</span>
            </button>
          ))}
        </div>
      </Card>

      <Card title="🧠 Self-Learning Triggers">
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
            {[
              { id: 'kimi', label: '🌐 Kimi 2.5' },
              { id: 'websearch', label: '🔍 Web Search' },
              { id: 'study', label: '📚 Self-Study' },
              { id: 'ingestion', label: '📥 Ingestion' },
            ].map(m => (
              <button
                key={m.id}
                onClick={() => setLearnMethod(m.id)}
                style={{
                  ...btn(learnMethod === m.id ? C.accentAlt : C.bgDark),
                  fontSize: 11, padding: '4px 10px',
                }}
              >{m.label}</button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <input
              placeholder={learnMethod === 'websearch' ? 'URL to scrape...' : learnMethod === 'study' ? 'Topic to study...' : 'Ask Kimi...'}
              value={learnQuery}
              onChange={e => setLearnQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && triggerLearning()}
              disabled={learnMethod === 'ingestion'}
              style={{
                flex: 1, padding: '8px 10px', background: C.bg, border: `1px solid ${C.border}`,
                borderRadius: 4, color: C.text, fontSize: 12, outline: 'none',
              }}
            />
            <button
              onClick={triggerLearning}
              disabled={learnLoading || learnMethod === 'ingestion'}
              style={{ ...btn(C.accent), opacity: learnLoading ? 0.5 : 1 }}
            >
              {learnLoading ? '⏳' : '▶ Go'}
            </button>
          </div>
        </div>

        {learnResult && (
          <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: 12, fontSize: 12, maxHeight: 300, overflowY: 'auto' }}>
            {learnResult.error ? (
              <div style={{ color: C.error }}>{learnResult.error}</div>
            ) : learnResult.response ? (
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.text, lineHeight: 1.6 }}>{learnResult.response}</pre>
            ) : (
              <pre style={{ margin: 0, color: C.muted }}>{JSON.stringify(learnResult, null, 2)}</pre>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

// ── Main GovernanceTab ────────────────────────────────────────────────
export default function GovernanceTab() {
  const [activeTab, setActiveTab] = useState('approvals');
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/governance-hub/dashboard`)
      .then(r => r.ok ? r.json() : null)
      .then(setDashboard).catch(() => {});
  }, []);

  const tabs = [
    { id: 'approvals', label: 'Approvals', icon: '✓', badge: dashboard?.approvals?.pending_count },
    { id: 'scores', label: 'Scores', icon: '📊' },
    { id: 'performance', label: 'Performance', icon: '⚡' },
    { id: 'actions', label: 'Actions', icon: '🔧' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>

      {/* Header with sub-tabs */}
      <div style={{ borderBottom: `1px solid ${C.border}`, background: C.bgAlt, padding: '0 16px', display: 'flex', alignItems: 'stretch' }}>
        <span style={{ fontSize: 15, fontWeight: 700, padding: '12px 16px 12px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
          🏛️ Governance
        </span>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              padding: '10px 16px', border: 'none', background: 'none', cursor: 'pointer',
              color: activeTab === t.id ? C.accent : C.muted,
              borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
              fontSize: 13, fontWeight: activeTab === t.id ? 700 : 500,
              display: 'flex', alignItems: 'center', gap: 6,
              transition: 'all .15s',
            }}
          >
            <span>{t.icon}</span> {t.label}
            {t.badge > 0 && (
              <span style={{
                background: C.error, color: '#fff', fontSize: 9, fontWeight: 700,
                padding: '1px 6px', borderRadius: 10, lineHeight: '14px',
              }}>{t.badge}</span>
            )}
          </button>
        ))}

        {/* Quick stats from dashboard */}
        {dashboard && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, color: C.dim, paddingRight: 8 }}>
            {dashboard.trust?.system_score != null && (
              <span>Trust: <b style={{ color: dashboard.trust.system_score >= 0.7 ? C.success : C.warn }}>{(dashboard.trust.system_score * 100).toFixed(0)}%</b></span>
            )}
            {dashboard.performance?.cpu_percent != null && (
              <span>CPU: <b>{dashboard.performance.cpu_percent.toFixed(0)}%</b></span>
            )}
            {dashboard.healing?.available && dashboard.healing.health_status && (
              <span>Health: <StatusBadge status={dashboard.healing.health_status} /></span>
            )}
          </div>
        )}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'approvals' && <ApprovalsPanel />}
        {activeTab === 'scores' && <ScoresPanel />}
        {activeTab === 'performance' && <PerformancePanel />}
        {activeTab === 'actions' && <ActionsPanel />}
      </div>
    </div>
  );
}
