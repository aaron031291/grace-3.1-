import { useState, useEffect, useCallback, useRef } from 'react';
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
  const [bridge, setBridge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fullData, setFullData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/governance/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    Promise.allSettled([
      fetch(`${API_BASE_URL}/api/governance-hub/performance`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/bridge/governance/full`).then(r => r.ok ? r.json() : null),
    ]).then(([mRes, bRes]) => {
      if (mRes.status === 'fulfilled') setMetrics(mRes.value);
      if (bRes.status === 'fulfilled') setBridge(bRes.value);
      setLoading(false);
    });
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

      {/* Bridge data — connected subsystems */}
      {bridge && (
        <>
          {bridge.memory_mesh && Object.keys(bridge.memory_mesh).length > 0 && (
            <Card title="🧠 Memory Mesh">
              {Object.entries(bridge.memory_mesh).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0', borderBottom: `1px solid ${C.border}` }}>
                  <span style={{ color: C.muted }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ fontWeight: 700 }}>{(v || 0).toLocaleString()}</span>
                </div>
              ))}
            </Card>
          )}

          {bridge.monitoring?.organs && (
            <Card title="🫀 Organs of Grace">
              {bridge.monitoring.organs.map((o, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0', borderBottom: `1px solid ${C.border}` }}>
                  <span style={{ fontSize: 12, flex: 1 }}>{o.name}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: o.progress >= 50 ? C.success : C.warn }}>{o.progress}%</span>
                  <MeterBar value={o.progress} color={o.progress >= 50 ? C.success : C.warn} />
                </div>
              ))}
            </Card>
          )}

          {bridge.ml_intelligence?.available && (
            <Card title="🤖 ML Intelligence">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {(bridge.ml_intelligence.components || []).map((c, i) => (
                  <span key={i} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: C.accentAlt + '44', color: C.text }}>{c.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </Card>
          )}

          {bridge.ooda?.recent_decisions?.length > 0 && (
            <Card title="🔄 Recent OODA Decisions">
              {bridge.ooda.recent_decisions.slice(0, 5).map((d, i) => (
                <div key={i} style={{ fontSize: 11, padding: '4px 0', borderBottom: `1px solid ${C.border}`, color: C.muted }}>
                  <span style={{ color: C.text }}>{d.type}</span> — {d.action} ({((d.confidence || 0) * 100).toFixed(0)}%)
                </div>
              ))}
            </Card>
          )}
        </>
      )}

      {/* Full aggregation: extra sections */}
      {fullData?.governance_pillars && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Governance Pillars</div>
          {typeof fullData.governance_pillars === 'object' ? (
            Object.entries(fullData.governance_pillars).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.governance_pillars)}</span>
          )}
        </div>
      )}
      {fullData?.kpi_dashboard && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>KPI Dashboard</div>
          {typeof fullData.kpi_dashboard === 'object' ? (
            Object.entries(fullData.kpi_dashboard).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.kpi_dashboard)}</span>
          )}
        </div>
      )}
      {fullData?.monitoring_organs && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Monitoring Organs</div>
          {typeof fullData.monitoring_organs === 'object' ? (
            Object.entries(fullData.monitoring_organs).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.monitoring_organs)}</span>
          )}
        </div>
      )}
      {fullData?.diagnostic_status && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Diagnostic Status</div>
          {typeof fullData.diagnostic_status === 'object' ? (
            Object.entries(fullData.diagnostic_status).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.diagnostic_status)}</span>
          )}
        </div>
      )}
      {fullData?.telemetry_status && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Telemetry Status</div>
          {typeof fullData.telemetry_status === 'object' ? (
            Object.entries(fullData.telemetry_status).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.telemetry_status)}</span>
          )}
        </div>
      )}
      {fullData?.autonomous_status && (
        <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Autonomous Status</div>
          {typeof fullData.autonomous_status === 'object' ? (
            Object.entries(fullData.autonomous_status).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.autonomous_status)}</span>
          )}
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button onClick={refresh} style={btn(C.bgDark)}>↻ Refresh All</button>
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

// ── Sub-tab: Rules & Persona ──────────────────────────────────────────
function RulesPersonaPanel() {
  const [docs, setDocs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docContent, setDocContent] = useState('');
  const [docLoading, setDocLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasUnsaved, setHasUnsaved] = useState(false);

  // Persona
  const [personal, setPersonal] = useState('');
  const [professional, setProfessional] = useState('');
  const [personaLoading, setPersonaLoading] = useState(true);
  const [personaSaving, setPersonaSaving] = useState(false);

  // Upload
  const [showUpload, setShowUpload] = useState(false);
  const [uploadCat, setUploadCat] = useState('general');
  const [uploadDesc, setUploadDesc] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  // Reasoning
  const [reasonQ, setReasonQ] = useState('');
  const [reasonResult, setReasonResult] = useState(null);
  const [reasoning, setReasoning] = useState(false);

  // Domain rules
  const [domainMode, setDomainMode] = useState('global'); // 'global' or 'domain'
  const [domainFolders, setDomainFolders] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState('');
  const [domainRules, setDomainRules] = useState([]);
  const domainFileRef = useRef(null);

  useEffect(() => {
    if (domainMode === 'domain') {
      fetch(`${API_BASE_URL}/api/librarian-fs/tree?max_depth=1`)
        .then(r => r.ok ? r.json() : { children: [] })
        .then(d => {
          const folders = (d.children || []).filter(c => c.type === 'directory').map(c => c.name);
          setDomainFolders(folders);
        }).catch(() => {});
    }
  }, [domainMode]);

  useEffect(() => {
    if (selectedDomain) {
      fetch(`${API_BASE_URL}/api/v1/domain/${encodeURIComponent(selectedDomain)}/rules`)
        .then(r => r.ok ? r.json() : { rules: [] })
        .then(d => setDomainRules(d.rules || []))
        .catch(() => setDomainRules([]));
    }
  }, [selectedDomain]);

  const [notification, setNotification] = useState(null);
  const notifTimer = useRef(null);
  const notify = useCallback((msg, type = 'success') => {
    setNotification({ msg, type });
    clearTimeout(notifTimer.current);
    notifTimer.current = setTimeout(() => setNotification(null), 4000);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/documents`);
      if (res.ok) {
        const d = await res.json();
        setDocs(d.documents || []);
        setCategories(d.categories || []);
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    refresh();
    fetch(`${API_BASE_URL}/api/governance-rules/persona`)
      .then(r => r.ok ? r.json() : {})
      .then(d => { setPersonal(d.personal || ''); setProfessional(d.professional || ''); })
      .catch(() => {})
      .finally(() => setPersonaLoading(false));
  }, [refresh]);

  const openDoc = async (doc) => {
    setSelectedDoc(doc);
    setDocLoading(true);
    setEditMode(false);
    setHasUnsaved(false);
    setReasonResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/documents/${encodeURIComponent(doc.id)}/content`);
      if (res.ok) { const d = await res.json(); setDocContent(d.content || ''); setEditText(d.content || ''); }
    } catch { /* silent */ }
    finally { setDocLoading(false); }
  };

  const saveDoc = async () => {
    if (!selectedDoc) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/documents/${encodeURIComponent(selectedDoc.id)}/content`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editText }),
      });
      if (res.ok) { setDocContent(editText); setHasUnsaved(false); notify('Rule document saved'); }
    } catch { notify('Save failed', 'error'); }
    finally { setSaving(false); }
  };

  const deleteDoc = async (docId) => {
    if (!window.confirm('Delete this governance rule document?')) return;
    try {
      await fetch(`${API_BASE_URL}/api/governance-rules/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' });
      notify('Document deleted');
      if (selectedDoc?.id === docId) { setSelectedDoc(null); setDocContent(''); }
      refresh();
    } catch { notify('Delete failed', 'error'); }
  };

  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('category', uploadCat);
      fd.append('description', uploadDesc);
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/documents/upload`, { method: 'POST', body: fd });
      if (res.ok) { notify('Rule document uploaded — it is now LAW'); refresh(); setShowUpload(false); }
    } catch { notify('Upload failed', 'error'); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const savePersona = async () => {
    setPersonaSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/persona`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ personal, professional }),
      });
      if (res.ok) notify('Persona saved');
    } catch { notify('Save failed', 'error'); }
    finally { setPersonaSaving(false); }
  };

  const handleReason = async () => {
    if (!reasonQ.trim() || !selectedDoc) return;
    setReasoning(true); setReasonResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance-rules/documents/reason`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: selectedDoc.id, question: reasonQ, use_kimi: true }),
      });
      if (res.ok) setReasonResult(await res.json());
    } catch { setReasonResult({ error: 'Reasoning failed' }); }
    finally { setReasoning(false); }
  };

  const catOptions = ['general', 'gdpr', 'iso', 'anti_bribery', 'code_standards', 'user_rules', 'industry'];

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden', position: 'relative' }}>
      {notification && (
        <div style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 100, padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 500, background: notification.type === 'success' ? C.success : C.error, color: '#fff', boxShadow: '0 4px 14px rgba(0,0,0,.4)' }}>{notification.msg}</div>
      )}

      {/* Left: Document list + Persona */}
      <div style={{ flex: '0 0 280px', borderRight: `1px solid ${C.border}`, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Persona context windows */}
        <div style={{ borderBottom: `1px solid ${C.border}`, padding: '12px' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.accent, marginBottom: 8 }}>🎭 Persona</div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 4 }}>Personal — how Grace talks to you</div>
            <textarea
              value={personal}
              onChange={e => setPersonal(e.target.value)}
              placeholder="e.g. Be casual and friendly, use my name, explain things simply..."
              disabled={personaLoading}
              style={{ width: '100%', height: 60, resize: 'vertical', padding: 8, fontSize: 11, lineHeight: 1.5, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' }}
            />
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: 'uppercase', marginBottom: 4 }}>Professional — how Grace shows up externally</div>
            <textarea
              value={professional}
              onChange={e => setProfessional(e.target.value)}
              placeholder="e.g. Formal tone, use company name, cite sources, UK English..."
              disabled={personaLoading}
              style={{ width: '100%', height: 60, resize: 'vertical', padding: 8, fontSize: 11, lineHeight: 1.5, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' }}
            />
          </div>

          <button onClick={savePersona} disabled={personaSaving} style={{ ...btn(C.success), width: '100%', fontSize: 11 }}>
            {personaSaving ? '⏳ Saving...' : '💾 Save Persona'}
          </button>
        </div>

        {/* Scope toggle: Global vs Domain */}
        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
            <button onClick={() => setDomainMode('global')} style={{ ...btn(domainMode === 'global' ? C.accentAlt : C.bgDark), flex: 1, fontSize: 10 }}>🌐 Global Rules</button>
            <button onClick={() => setDomainMode('domain')} style={{ ...btn(domainMode === 'domain' ? C.accentAlt : C.bgDark), flex: 1, fontSize: 10 }}>📁 Per Domain</button>
          </div>
          {domainMode === 'domain' && (
            <div>
              <select value={selectedDomain} onChange={e => setSelectedDomain(e.target.value)}
                style={{ width: '100%', padding: '5px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none', marginBottom: 6 }}>
                <option value="">Select domain folder...</option>
                {domainFolders.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
              {selectedDomain && (
                <>
                  <input type="file" ref={domainFileRef} style={{ display: 'none' }} onChange={async (e) => {
                    if (!e.target.files?.length) return;
                    const fd = new FormData();
                    fd.append('file', e.target.files[0]);
                    await fetch(`${API_BASE_URL}/api/v1/domain/${encodeURIComponent(selectedDomain)}/rules/upload`, { method: 'POST', body: fd });
                    e.target.value = '';
                    fetch(`${API_BASE_URL}/api/v1/domain/${encodeURIComponent(selectedDomain)}/rules`).then(r => r.ok ? r.json() : { rules: [] }).then(d => setDomainRules(d.rules || []));
                    notify('Domain rule uploaded');
                  }} />
                  <button onClick={() => domainFileRef.current?.click()} style={{ ...btn(C.success), width: '100%', fontSize: 10, marginBottom: 4 }}>📤 Upload Rule to {selectedDomain}</button>
                  {domainRules.length > 0 && domainRules.map(r => (
                    <div key={r.filename} style={{ padding: '4px 8px', fontSize: 11, borderBottom: `1px solid ${C.border}22`, display: 'flex', alignItems: 'center', gap: 6, color: C.muted }}>
                      <span>⚖️</span><span style={{ flex: 1 }}>{r.filename}</span>
                    </div>
                  ))}
                  {domainRules.length === 0 && <div style={{ fontSize: 10, color: C.dim, textAlign: 'center', padding: 8 }}>No domain rules yet</div>}
                </>
              )}
            </div>
          )}
        </div>

        {/* Upload global */}
        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 6 }}>
          <button onClick={() => setShowUpload(!showUpload)} style={{ ...btn(C.accent), flex: 1, fontSize: 11 }}>📤 Upload Global Rule</button>
          <button onClick={refresh} style={{ ...btn(C.bgDark), fontSize: 11 }}>↻</button>
        </div>

        {showUpload && (
          <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
            <select value={uploadCat} onChange={e => setUploadCat(e.target.value)} style={{ width: '100%', padding: '5px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, marginBottom: 6, outline: 'none' }}>
              {catOptions.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ').toUpperCase()}</option>)}
            </select>
            <input placeholder="Description..." value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} style={{ width: '100%', padding: '5px 8px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
            <input type="file" ref={fileRef} onChange={handleUpload} style={{ display: 'none' }} />
            <button onClick={() => fileRef.current?.click()} disabled={uploading} style={{ ...btn(C.success), width: '100%', fontSize: 11 }}>
              {uploading ? '⏳' : '📎 Choose File'}
            </button>
          </div>
        )}

        {/* Document list by category */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>Loading...</div>
          ) : categories.length === 0 && docs.length === 0 ? (
            <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📜</div>
              <div style={{ fontSize: 12 }}>No rule documents yet</div>
              <div style={{ fontSize: 10, marginTop: 4 }}>Upload GDPR, ISO, or custom rules</div>
            </div>
          ) : categories.map(cat => (
            <div key={cat.name}>
              <div style={{ padding: '6px 12px', fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', background: C.bgAlt, borderBottom: `1px solid ${C.border}` }}>
                📂 {cat.name.replace(/_/g, ' ')} ({cat.count})
              </div>
              {cat.documents.map(doc => (
                <div
                  key={doc.id}
                  onClick={() => openDoc(doc)}
                  style={{
                    padding: '7px 12px', cursor: 'pointer', fontSize: 12,
                    background: selectedDoc?.id === doc.id ? C.bgDark : 'transparent',
                    borderLeft: selectedDoc?.id === doc.id ? `3px solid ${C.accent}` : '3px solid transparent',
                    display: 'flex', alignItems: 'center', gap: 8,
                    transition: 'background .1s',
                  }}
                  onMouseEnter={e => { if (selectedDoc?.id !== doc.id) e.currentTarget.style.background = C.bgAlt; }}
                  onMouseLeave={e => { if (selectedDoc?.id !== doc.id) e.currentTarget.style.background = 'transparent'; }}
                >
                  <span>{doc.enforced ? '⚖️' : '📄'}</span>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</div>
                    {doc.description && <div style={{ fontSize: 10, color: C.dim }}>{doc.description}</div>}
                  </div>
                  <span onClick={e => { e.stopPropagation(); deleteDoc(doc.id); }} style={{ cursor: 'pointer', fontSize: 12, color: C.dim, padding: '0 2px' }}>🗑</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Right: Document viewer/editor + Reasoning */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selectedDoc ? (
          <>
            {/* Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
              <span>⚖️</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{selectedDoc.filename}</span>
              {hasUnsaved && <span style={{ fontSize: 10, color: C.accent, fontWeight: 600 }}>UNSAVED</span>}
              <span style={{ fontSize: 10, color: C.dim }}>({selectedDoc.category})</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
                {editMode ? (
                  <>
                    <button onClick={saveDoc} disabled={saving || !hasUnsaved} style={{ ...btn(hasUnsaved ? C.success : C.bgDark), fontSize: 11 }}>{saving ? '⏳' : '💾 Save'}</button>
                    <button onClick={() => { if (hasUnsaved && !window.confirm('Discard?')) return; setEditMode(false); setEditText(docContent); setHasUnsaved(false); }} style={{ ...btn(C.border), fontSize: 11 }}>View</button>
                  </>
                ) : (
                  <button onClick={() => { setEditMode(true); setEditText(docContent); }} style={{ ...btn(C.accentAlt), fontSize: 11 }}>✏️ Edit</button>
                )}
                <span onClick={() => { setSelectedDoc(null); setDocContent(''); }} style={{ cursor: 'pointer', fontSize: 16, color: C.muted }}>✕</span>
              </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              {docLoading ? (
                <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading...</div>
              ) : editMode ? (
                <textarea
                  value={editText}
                  onChange={e => { setEditText(e.target.value); setHasUnsaved(e.target.value !== docContent); }}
                  onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveDoc(); } }}
                  spellCheck={false}
                  style={{ width: '100%', height: '100%', resize: 'none', background: '#0d1117', color: '#e6edf3', border: 'none', outline: 'none', padding: '16px 20px', fontFamily: '"Fira Code", Consolas, monospace', fontSize: 13, lineHeight: 1.7, boxSizing: 'border-box' }}
                />
              ) : (
                <pre style={{ margin: 0, padding: '16px 20px', fontFamily: '"Fira Code", Consolas, monospace', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#e6edf3', background: '#0d1117', height: '100%', overflow: 'auto' }}>
                  {docContent || '(empty document)'}
                </pre>
              )}
            </div>

            {/* Reasoning bar */}
            <div style={{ borderTop: `1px solid ${C.border}`, padding: '8px 16px', background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: C.muted, flexShrink: 0 }}>🤖 Ask about this rule:</span>
              <input
                placeholder="What does this document require? How should Grace comply?"
                value={reasonQ}
                onChange={e => setReasonQ(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleReason()}
                disabled={reasoning}
                style={{ flex: 1, padding: '6px 10px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none' }}
              />
              <button onClick={handleReason} disabled={reasoning || !reasonQ.trim()} style={{ ...btn(C.accent), fontSize: 11, opacity: reasoning ? 0.5 : 1 }}>
                {reasoning ? '⏳' : '🧠 Reason'}
              </button>
            </div>
            {reasonResult && (
              <div style={{ borderTop: `1px solid ${C.border}`, padding: '12px 16px', background: C.bg, maxHeight: 200, overflowY: 'auto' }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, marginBottom: 6 }}>
                  Grace + Kimi Analysis ({reasonResult.provider || 'kimi'})
                </div>
                <pre style={{ margin: 0, fontSize: 12, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {reasonResult.response || reasonResult.error || JSON.stringify(reasonResult)}
                </pre>
              </div>
            )}
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: C.dim }}>
              <div style={{ fontSize: 56, marginBottom: 12, opacity: 0.5 }}>⚖️</div>
              <div style={{ fontSize: 15, fontWeight: 500, color: C.muted }}>Select a rule document</div>
              <div style={{ fontSize: 12, marginTop: 4, maxWidth: 300 }}>
                Upload industry standards (GDPR, ISO, anti-bribery), code parameters, or custom rules.
                They become law — Grace and Kimi will follow them.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-tab: Genesis Keys ─────────────────────────────────────────────
function GenesisKeysPanel() {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(null);
  const [dayData, setDayData] = useState(null);
  const [dayLoading, setDayLoading] = useState(false);
  const [selectedKey, setSelectedKey] = useState(null);
  const [keyDetail, setKeyDetail] = useState(null);
  const [keyLoading, setKeyLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [expandedTypes, setExpandedTypes] = useState(new Set());

  useEffect(() => {
    Promise.allSettled([
      fetch(`${API_BASE_URL}/api/genesis-daily/folders?days=60`).then(r => r.ok ? r.json() : { folders: [] }),
      fetch(`${API_BASE_URL}/api/genesis-daily/stats`).then(r => r.ok ? r.json() : null),
    ]).then(([fRes, sRes]) => {
      if (fRes.status === 'fulfilled') setFolders(fRes.value.folders || []);
      if (sRes.status === 'fulfilled') setStats(sRes.value);
      setLoading(false);
    });
  }, []);

  const openFolder = useCallback(async (date) => {
    setSelectedDate(date);
    setSelectedKey(null);
    setKeyDetail(null);
    setDayLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/genesis-daily/folder/${date}`);
      if (res.ok) setDayData(await res.json());
    } catch { /* silent */ }
    finally { setDayLoading(false); }
  }, []);

  const openKey = useCallback(async (keyId) => {
    setSelectedKey(keyId);
    setKeyLoading(true);
    setKeyDetail(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/genesis-daily/key/${keyId}`);
      if (res.ok) setKeyDetail(await res.json());
    } catch { /* silent */ }
    finally { setKeyLoading(false); }
  }, []);

  const toggleType = (type) => {
    setExpandedTypes(prev => {
      const n = new Set(prev);
      if (n.has(type)) n.delete(type); else n.add(type);
      return n;
    });
  };

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading Genesis Keys...</div>;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* Left: Date folders */}
      <div style={{ flex: '0 0 240px', borderRight: `1px solid ${C.border}`, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {stats && (
          <div style={{ padding: '10px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>Total Keys: <b style={{ color: C.text }}>{(stats.total_keys || 0).toLocaleString()}</b></div>
            <div style={{ fontSize: 11, color: C.muted }}>Today: <b style={{ color: C.accent }}>{(stats.today_keys || 0).toLocaleString()}</b></div>
          </div>
        )}
        <div style={{ padding: '8px 12px', fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', borderBottom: `1px solid ${C.border}` }}>
          📅 Daily Folders
        </div>
        {folders.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>No genesis keys yet</div>
        ) : folders.map(f => (
          <div
            key={f.date}
            onClick={() => openFolder(f.date)}
            style={{
              padding: '8px 12px', cursor: 'pointer', fontSize: 12,
              background: selectedDate === f.date ? C.bgDark : 'transparent',
              borderLeft: selectedDate === f.date ? `3px solid ${C.accent}` : '3px solid transparent',
              borderBottom: `1px solid ${C.border}22`,
              transition: 'background .1s',
            }}
            onMouseEnter={e => { if (selectedDate !== f.date) e.currentTarget.style.background = C.bgAlt; }}
            onMouseLeave={e => { if (selectedDate !== f.date) e.currentTarget.style.background = 'transparent'; }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>📁</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{f.date}</div>
                <div style={{ fontSize: 10, color: C.dim }}>{f.label}</div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontWeight: 700, color: C.text }}>{f.key_count}</div>
                {f.error_count > 0 && <div style={{ fontSize: 9, color: C.error }}>{f.error_count} err</div>}
              </div>
            </div>
            {/* Metadata summary */}
            {f.summary && (
              <div style={{ fontSize: 10, color: C.muted, marginTop: 4, lineHeight: 1.5, paddingLeft: 24 }}>
                {f.summary}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, fontSize: 9, color: C.dim, marginTop: 3, paddingLeft: 24, flexWrap: 'wrap' }}>
              {f.unique_actors > 0 && <span>👤 {f.unique_actors}</span>}
              {f.unique_files > 0 && <span>📄 {f.unique_files} files</span>}
              {f.fix_count > 0 && <span style={{ color: C.success }}>✅ {f.fix_count} fixes</span>}
              {f.top_file && <span title={f.top_file}>📌 {f.top_file}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Center: Day contents grouped by type */}
      <div style={{ flex: 1, overflow: 'auto', borderRight: selectedKey ? `1px solid ${C.border}` : 'none' }}>
        {!selectedDate ? (
          <div style={{ padding: 60, textAlign: 'center', color: C.dim }}>
            <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.5 }}>🔑</div>
            <div style={{ fontSize: 14, fontWeight: 500, color: C.muted }}>Select a daily folder</div>
            <div style={{ fontSize: 12 }}>Each folder contains all Genesis Keys from that 24-hour window</div>
          </div>
        ) : dayLoading ? (
          <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading keys...</div>
        ) : dayData ? (
          <div style={{ padding: 16 }}>
            {/* Demographics bar */}
            <div style={{
              display: 'flex', gap: 16, padding: '10px 14px', marginBottom: 14,
              background: C.bgAlt, borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 12, flexWrap: 'wrap',
            }}>
              <span>🔑 <b>{dayData.demographics?.total_keys || 0}</b> keys</span>
              <span>❌ <b style={{ color: C.error }}>{dayData.demographics?.total_errors || 0}</b> errors</span>
              <span>✅ <b style={{ color: C.success }}>{dayData.demographics?.total_fixes || 0}</b> fixes</span>
              <span>👤 <b>{dayData.demographics?.unique_actors || 0}</b> actors</span>
              <span>📄 <b>{dayData.demographics?.unique_files || 0}</b> files</span>
            </div>

            {/* Types */}
            {(dayData.by_type || []).map(group => {
              const isOpen = expandedTypes.has(group.type);
              return (
                <div key={group.type} style={{ marginBottom: 6 }}>
                  <div
                    onClick={() => toggleType(group.type)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                      background: C.bgAlt, borderRadius: 6, cursor: 'pointer',
                      border: `1px solid ${C.border}`, userSelect: 'none',
                    }}
                  >
                    <span style={{ fontSize: 10, width: 14, textAlign: 'center', color: C.muted }}>{isOpen ? '▼' : '▶'}</span>
                    <span style={{ fontSize: 16 }}>{group.icon}</span>
                    <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{group.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: C.accent }}>{group.count}</span>
                    {group.error_count > 0 && <span style={{ fontSize: 10, color: C.error }}>({group.error_count} errors)</span>}
                  </div>
                  {isOpen && (
                    <div style={{ paddingLeft: 12, borderLeft: `2px solid ${C.border}`, marginLeft: 20, marginTop: 4 }}>
                      {group.keys.map(k => (
                        <div
                          key={k.key_id || k.id}
                          onDoubleClick={() => openKey(k.key_id)}
                          onClick={() => openKey(k.key_id)}
                          style={{
                            padding: '6px 10px', marginBottom: 2, borderRadius: 4, cursor: 'pointer',
                            background: selectedKey === k.key_id ? C.bgDark : 'transparent',
                            borderLeft: selectedKey === k.key_id ? `2px solid ${C.accent}` : '2px solid transparent',
                            fontSize: 12, transition: 'background .1s',
                          }}
                          onMouseEnter={e => { if (selectedKey !== k.key_id) e.currentTarget.style.background = C.bgAlt; }}
                          onMouseLeave={e => { if (selectedKey !== k.key_id) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {k.is_error && <span style={{ color: C.error }}>❌</span>}
                            {k.fix_applied && <span style={{ color: C.success }}>✅</span>}
                            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: C.text }}>{k.what}</span>
                            <span style={{ fontSize: 10, color: C.dim, flexShrink: 0 }}>
                              {k.timestamp ? new Date(k.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                            </span>
                          </div>
                          {k.file_path && <div style={{ fontSize: 10, color: C.dim, marginTop: 2 }}>📄 {k.file_path}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      {/* Right: Key detail panel */}
      {selectedKey && (
        <div style={{ flex: '0 0 380px', overflow: 'auto', padding: '12px 16px' }}>
          {keyLoading ? (
            <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>Loading key...</div>
          ) : keyDetail ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 18 }}>🔑</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, fontFamily: 'monospace', color: C.accent, wordBreak: 'break-all' }}>{keyDetail.key_id}</div>
                  <StatusBadge status={keyDetail.key_type} />
                </div>
                <span onClick={() => { setSelectedKey(null); setKeyDetail(null); }} style={{ cursor: 'pointer', fontSize: 16, color: C.muted }}>✕</span>
              </div>

              {/* What/Who/When/Where/Why/How */}
              <Card title="Details">
                {[
                  ['What', keyDetail.what],
                  ['Who', keyDetail.who],
                  ['When', keyDetail.timestamp ? new Date(keyDetail.timestamp).toLocaleString() : ''],
                  ['Where', keyDetail.where],
                  ['Why', keyDetail.why],
                  ['How', keyDetail.how],
                  ['Status', keyDetail.status],
                  ['File', keyDetail.file_path],
                  ['Function', keyDetail.function_name],
                  ['Line', keyDetail.line_number],
                ].filter(([, v]) => v).map(([label, val]) => (
                  <div key={label} style={{ display: 'flex', gap: 8, padding: '4px 0', borderBottom: `1px solid ${C.border}`, fontSize: 11 }}>
                    <span style={{ color: C.muted, width: 55, flexShrink: 0 }}>{label}</span>
                    <span style={{ color: C.text, wordBreak: 'break-all' }}>{String(val)}</span>
                  </div>
                ))}
              </Card>

              {/* Source code context */}
              {keyDetail.source_context && (
                <Card title={`📄 Source: ${keyDetail.source_context.file_path || keyDetail.file_path}`}>
                  <pre style={{
                    margin: 0, padding: 10, background: '#0d1117', borderRadius: 4,
                    fontSize: 11, lineHeight: 1.5, overflow: 'auto', maxHeight: 300,
                    fontFamily: '"Fira Code", "JetBrains Mono", Consolas, monospace',
                    color: '#e6edf3', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  }}>
                    {keyDetail.source_context.lines
                      ? keyDetail.source_context.lines.map((line, i) => {
                          const lineNum = (keyDetail.source_context.start_line || 1) + i;
                          const isHighlight = lineNum === keyDetail.source_context.highlight_line;
                          return (
                            <div key={i} style={{ background: isHighlight ? '#e9456020' : 'transparent', display: 'flex' }}>
                              <span style={{ width: 40, textAlign: 'right', paddingRight: 10, color: isHighlight ? C.accent : '#484f58', userSelect: 'none', flexShrink: 0 }}>{lineNum}</span>
                              <span>{line}</span>
                            </div>
                          );
                        })
                      : keyDetail.source_context.preview || '(no preview)'
                    }
                  </pre>
                </Card>
              )}

              {/* Code before/after */}
              {(keyDetail.code_before || keyDetail.code_after) && (
                <Card title="Code Change">
                  {keyDetail.code_before && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 10, color: C.error, fontWeight: 600, marginBottom: 4 }}>— Before</div>
                      <pre style={{ margin: 0, padding: 8, background: C.error + '10', borderRadius: 4, fontSize: 11, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto' }}>{keyDetail.code_before}</pre>
                    </div>
                  )}
                  {keyDetail.code_after && (
                    <div>
                      <div style={{ fontSize: 10, color: C.success, fontWeight: 600, marginBottom: 4 }}>+ After</div>
                      <pre style={{ margin: 0, padding: 8, background: C.success + '10', borderRadius: 4, fontSize: 11, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto' }}>{keyDetail.code_after}</pre>
                    </div>
                  )}
                </Card>
              )}

              {/* Error info */}
              {keyDetail.is_error && (
                <Card title="❌ Error">
                  <div style={{ fontSize: 12, color: C.error, fontWeight: 600 }}>{keyDetail.error_type}</div>
                  <div style={{ fontSize: 11, color: C.muted, marginTop: 4, whiteSpace: 'pre-wrap' }}>{keyDetail.error_message}</div>
                </Card>
              )}

              {/* Tags */}
              {keyDetail.tags && keyDetail.tags.length > 0 && (
                <Card title="Tags">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {keyDetail.tags.map((t, i) => (
                      <span key={i} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: C.accentAlt + '44', color: C.text }}>{t}</span>
                    ))}
                  </div>
                </Card>
              )}

              {/* Input/Output data */}
              {keyDetail.input_data && Object.keys(keyDetail.input_data).length > 0 && (
                <Card title="Input Data">
                  <pre style={{ margin: 0, fontSize: 10, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto' }}>{JSON.stringify(keyDetail.input_data, null, 2)}</pre>
                </Card>
              )}
              {keyDetail.output_data && Object.keys(keyDetail.output_data).length > 0 && (
                <Card title="Output Data">
                  <pre style={{ margin: 0, fontSize: 10, color: C.muted, whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto' }}>{JSON.stringify(keyDetail.output_data, null, 2)}</pre>
                </Card>
              )}

              {/* Child/parent keys */}
              {keyDetail.parent_key && (
                <Card title="Parent Key">
                  <div onClick={() => openKey(keyDetail.parent_key.key_id)} style={{ cursor: 'pointer', fontSize: 12, color: C.info }}>
                    🔗 {keyDetail.parent_key.what} <span style={{ fontSize: 10, color: C.dim }}>({keyDetail.parent_key.type})</span>
                  </div>
                </Card>
              )}
              {keyDetail.child_keys && keyDetail.child_keys.length > 0 && (
                <Card title={`Child Keys (${keyDetail.child_keys.length})`}>
                  {keyDetail.child_keys.map(ck => (
                    <div key={ck.key_id} onClick={() => openKey(ck.key_id)} style={{ cursor: 'pointer', fontSize: 11, padding: '3px 0', borderBottom: `1px solid ${C.border}`, color: C.info }}>
                      🔗 {ck.what} <span style={{ fontSize: 9, color: C.dim }}>({ck.type})</span>
                    </div>
                  ))}
                </Card>
              )}

              {/* Fix suggestions */}
              {keyDetail.fix_suggestions && keyDetail.fix_suggestions.length > 0 && (
                <Card title={`Fix Suggestions (${keyDetail.fix_suggestions.length})`}>
                  {keyDetail.fix_suggestions.map(fs => (
                    <div key={fs.id} style={{ padding: '6px 8px', marginBottom: 4, background: C.bg, borderRadius: 4, border: `1px solid ${C.border}` }}>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{fs.title}</div>
                      <div style={{ fontSize: 10, color: C.muted }}><StatusBadge status={fs.status} /> · {fs.severity} · {fs.confidence ? (fs.confidence * 100).toFixed(0) + '% confidence' : ''}</div>
                      {fs.fix_code && <pre style={{ margin: '4px 0 0', fontSize: 10, color: C.success, background: C.success + '10', padding: 6, borderRadius: 3, whiteSpace: 'pre-wrap', maxHeight: 80, overflow: 'auto' }}>{fs.fix_code}</pre>}
                    </div>
                  ))}
                </Card>
              )}
            </>
          ) : (
            <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>Failed to load key detail</div>
          )}
        </div>
      )}
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
    { id: 'rules', label: 'Rules & Persona', icon: '⚖️' },
    { id: 'genesis', label: 'Genesis Keys', icon: '🔑' },
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
        {activeTab === 'rules' && <RulesPersonaPanel />}
        {activeTab === 'genesis' && <GenesisKeysPanel />}
      </div>
    </div>
  );
}
