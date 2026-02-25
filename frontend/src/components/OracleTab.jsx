import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';
import BackendPanel from './BackendPanel';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3',
};
const btn = (bg = C.accentAlt) => ({
  padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});

function MeterBar({ value, max = 1, color = C.accent }) {
  return (
    <div style={{ height: 6, background: C.bgDark, borderRadius: 3, overflow: 'hidden', flex: 1 }}>
      <div style={{ height: '100%', width: `${Math.min((value / max) * 100, 100)}%`, background: color, borderRadius: 3 }} />
    </div>
  );
}

function StatCard({ label, value, sub, color = C.text }) {
  return (
    <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', textAlign: 'center', flex: '1 1 140px' }}>
      <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: C.dim, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ── Training Data Sub-tab ─────────────────────────────────────────────
function TrainingDataPanel() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('newest');
  const [typeFilter, setTypeFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({ sort, limit: '100' });
    if (typeFilter) params.set('example_type', typeFilter);
    try {
      const res = await fetch(`${API_BASE_URL}/api/oracle/training-data?${params}`);
      if (res.ok) { const d = await res.json(); setData(d.examples || []); setTotal(d.total || 0); }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [sort, typeFilter]);

  useEffect(() => { fetch_(); }, [fetch_]);

  const loadDetail = async (id) => {
    setSelected(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/oracle/training-data/${id}`);
      if (res.ok) setDetail(await res.json());
    } catch { /* silent */ }
  };

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* List */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}` }}>
        <div style={{ padding: '8px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 8, alignItems: 'center', background: C.bgAlt }}>
          <span style={{ fontSize: 11, color: C.muted }}>{total} examples</span>
          <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding: '4px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none' }}>
            <option value="newest">Newest</option>
            <option value="trust">Highest Trust</option>
            <option value="oldest">Oldest</option>
          </select>
          <input placeholder="Filter by type..." value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ padding: '4px 8px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none', flex: 1 }} />
          <button onClick={fetch_} style={{ ...btn(C.bgDark), fontSize: 10 }}>↻</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>Loading...</div>
           : data.length === 0 ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32 }}>🧠</div><div style={{ fontSize: 12, marginTop: 8 }}>No training data yet</div></div>
           : data.map(ex => {
              const tc = ex.trust_score >= 0.7 ? C.success : ex.trust_score >= 0.4 ? C.warn : C.error;
              return (
                <div key={ex.id} onClick={() => loadDetail(ex.id)} style={{
                  padding: '8px 14px', cursor: 'pointer', borderBottom: `1px solid ${C.border}22`,
                  background: selected === ex.id ? C.bgDark : 'transparent',
                  borderLeft: selected === ex.id ? `3px solid ${C.accent}` : '3px solid transparent',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: C.accentAlt + '44', color: C.text }}>{ex.type}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: tc }}>{(ex.trust_score * 100).toFixed(0)}%</span>
                    <span style={{ fontSize: 10, color: C.dim, marginLeft: 'auto' }}>{ex.source}</span>
                  </div>
                  <div style={{ fontSize: 12, color: C.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ex.input}</div>
                </div>
              );
           })}
        </div>
      </div>

      {/* Detail */}
      <div style={{ flex: '0 0 380px', overflow: 'auto', padding: detail ? 16 : 0 }}>
        {detail ? (
          <>
            <div style={{ fontSize: 10, fontFamily: 'monospace', color: C.accent, marginBottom: 8 }}>Example #{detail.id}</div>
            {[
              ['Type', detail.example_type],
              ['Trust Score', detail.trust_score != null ? `${(detail.trust_score * 100).toFixed(1)}%` : ''],
              ['Source', detail.source],
              ['File', detail.file_path],
              ['Created', detail.created_at],
            ].filter(([,v]) => v).map(([k,v]) => (
              <div key={k} style={{ display: 'flex', gap: 8, fontSize: 11, padding: '4px 0', borderBottom: `1px solid ${C.border}` }}>
                <span style={{ color: C.muted, width: 80, flexShrink: 0 }}>{k}</span>
                <span style={{ color: C.text, wordBreak: 'break-all' }}>{String(v)}</span>
              </div>
            ))}
            {detail.input_context && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, marginBottom: 4 }}>INPUT</div>
                <pre style={{ margin: 0, padding: 10, background: '#0d1117', color: '#e6edf3', borderRadius: 4, fontSize: 11, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>{detail.input_context}</pre>
              </div>
            )}
            {detail.expected_output && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.success, marginBottom: 4 }}>EXPECTED OUTPUT</div>
                <pre style={{ margin: 0, padding: 10, background: C.success + '10', borderRadius: 4, fontSize: 11, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto', color: C.text }}>{detail.expected_output}</pre>
              </div>
            )}
            {detail.actual_output && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.info, marginBottom: 4 }}>ACTUAL OUTPUT</div>
                <pre style={{ margin: 0, padding: 10, background: C.info + '10', borderRadius: 4, fontSize: 11, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto', color: C.text }}>{detail.actual_output}</pre>
              </div>
            )}
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: C.dim }}>
            <div style={{ textAlign: 'center' }}><div style={{ fontSize: 40, opacity: 0.5 }}>🧠</div><div style={{ fontSize: 12, marginTop: 8 }}>Select an example</div></div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Audit Sub-tab ─────────────────────────────────────────────────────
function AuditPanel() {
  const [auditResult, setAuditResult] = useState(null);
  const [auditing, setAuditing] = useState(false);
  const [focus, setFocus] = useState('');
  const [gapTopic, setGapTopic] = useState('');
  const [gapMethod, setGapMethod] = useState('kimi');
  const [gapResult, setGapResult] = useState(null);
  const [filling, setFilling] = useState(false);
  const [trustDist, setTrustDist] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/oracle/trust-distribution`)
      .then(r => r.ok ? r.json() : null).then(setTrustDist).catch(() => {});
  }, []);

  const runAudit = async () => {
    setAuditing(true); setAuditResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/oracle/audit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focus: focus || null, use_kimi: true }),
      });
      if (res.ok) setAuditResult(await res.json());
    } catch { /* silent */ }
    finally { setAuditing(false); }
  };

  const fillGap = async () => {
    if (!gapTopic.trim()) return;
    setFilling(true); setGapResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/oracle/fill-gap`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: gapTopic, method: gapMethod }),
      });
      if (res.ok) setGapResult(await res.json());
    } catch { /* silent */ }
    finally { setFilling(false); }
  };

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      {/* Trust distribution */}
      {trustDist && (
        <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Trust Score Distribution ({trustDist.total} examples)</div>
          {Object.entries(trustDist.distribution || {}).map(([range, count]) => (
            <div key={range} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: C.muted, width: 60, flexShrink: 0 }}>{range}</span>
              <MeterBar value={count} max={Math.max(...Object.values(trustDist.distribution || {}))} color={range >= '0.8' ? C.success : range >= '0.4' ? C.warn : C.error} />
              <span style={{ fontSize: 12, fontWeight: 700, width: 40, textAlign: 'right' }}>{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Audit */}
      <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>🧠 Kimi Audit</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <input placeholder="Focus area (optional)..." value={focus} onChange={e => setFocus(e.target.value)} style={{ flex: 1, padding: '6px 10px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none' }} />
          <button onClick={runAudit} disabled={auditing} style={{ ...btn(C.accent), opacity: auditing ? 0.5 : 1 }}>
            {auditing ? '⏳ Auditing...' : '🔍 Run Audit'}
          </button>
        </div>
        {auditResult && (
          <pre style={{ margin: 0, padding: 12, background: '#0d1117', color: '#e6edf3', borderRadius: 6, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>
            {auditResult.audit}
          </pre>
        )}
      </div>

      {/* Fill gaps */}
      <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>🔄 Fill Knowledge Gaps</div>
        <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
          {[{ id: 'kimi', label: '🧠 Kimi' }, { id: 'websearch', label: '🔍 Web' }, { id: 'study', label: '📚 Study' }].map(m => (
            <button key={m.id} onClick={() => setGapMethod(m.id)} style={{ ...btn(gapMethod === m.id ? C.accentAlt : C.bgDark), fontSize: 10, padding: '4px 10px' }}>{m.label}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input placeholder="Topic to research..." value={gapTopic} onChange={e => setGapTopic(e.target.value)} onKeyDown={e => e.key === 'Enter' && fillGap()} style={{ flex: 1, padding: '6px 10px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none' }} />
          <button onClick={fillGap} disabled={filling} style={{ ...btn(C.success), opacity: filling ? 0.5 : 1 }}>
            {filling ? '⏳' : '▶ Fill Gap'}
          </button>
        </div>
        {gapResult && (
          <div style={{ marginTop: 10 }}>
            {gapResult.knowledge ? (
              <pre style={{ margin: 0, padding: 12, background: '#0d1117', color: '#e6edf3', borderRadius: 6, fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto' }}>{gapResult.knowledge}</pre>
            ) : (
              <pre style={{ margin: 0, fontSize: 11, color: C.muted }}>{JSON.stringify(gapResult, null, 2)}</pre>
            )}
            {gapResult.status === 'completed' && (
              <div style={{ marginTop: 6, fontSize: 11, color: C.success }}>✅ Knowledge ingested into training data</div>
            )}
          </div>
        )}
        <BackendPanel prefixes={['/training', '/learning-memory', '/api/oracle', '/autonomous-learning']} label="Training & Learning" />
      </div>
    </div>
  );
}

// ── Main OracleTab ────────────────────────────────────────────────────
export default function OracleTab() {
  const [activeTab, setActiveTab] = useState('overview');
  const [dashboard, setDashboard] = useState(null);
  const [fullData, setFullData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/oracle/dashboard`)
      .then(r => r.ok ? r.json() : null).then(setDashboard).catch(() => {});
  }, []);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/oracle/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'training', label: 'Training Data', icon: '🧠' },
    { id: 'audit', label: 'Audit & Gaps', icon: '🔍' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>
      <div style={{ borderBottom: `1px solid ${C.border}`, background: C.bgAlt, padding: '0 16px', display: 'flex', alignItems: 'stretch' }}>
        <span style={{ fontSize: 15, fontWeight: 700, padding: '12px 16px 12px 0', display: 'flex', alignItems: 'center', gap: 8 }}>🔮 Oracle</span>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '10px 16px', border: 'none', background: 'none', cursor: 'pointer',
            color: activeTab === t.id ? C.accent : C.muted,
            borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
            fontSize: 13, fontWeight: activeTab === t.id ? 700 : 500,
            display: 'flex', alignItems: 'center', gap: 6, transition: 'all .15s',
          }}><span>{t.icon}</span> {t.label}</button>
        ))}
        {dashboard && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, color: C.dim }}>
            <span>🧠 {dashboard.learning_examples?.total || 0} examples</span>
            <span>📐 {dashboard.learning_patterns?.total || 0} patterns</span>
            <span>🎯 {dashboard.procedures?.total || 0} skills</span>
            <span>📄 {dashboard.documents?.total || 0} docs</span>
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'overview' && dashboard && (
          <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
              <StatCard label="Learning Examples" value={dashboard.learning_examples?.total || 0} sub={`avg trust: ${((dashboard.learning_examples?.avg_trust || 0) * 100).toFixed(0)}%`} color={C.accent} />
              <StatCard label="Patterns" value={dashboard.learning_patterns?.total || 0} sub={`success: ${((dashboard.learning_patterns?.avg_success_rate || 0) * 100).toFixed(0)}%`} color={C.info} />
              <StatCard label="Episodes" value={dashboard.episodes?.total || 0} sub={`avg trust: ${((dashboard.episodes?.avg_trust || 0) * 100).toFixed(0)}%`} color={C.warn} />
              <StatCard label="Procedures" value={dashboard.procedures?.total || 0} sub={`success: ${((dashboard.procedures?.avg_success_rate || 0) * 100).toFixed(0)}%`} color={C.success} />
              <StatCard label="Documents" value={dashboard.documents?.total || 0} sub={`${dashboard.documents?.total_chunks || 0} chunks`} />
              <StatCard label="Vectors" value={dashboard.vector_store?.vectors || 0} />
            </div>

            {/* By type */}
            {dashboard.learning_examples?.by_type?.length > 0 && (
              <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Training Data by Type</div>
                {dashboard.learning_examples.by_type.map((t, i) => {
                  const tc = t.avg_trust >= 0.7 ? C.success : t.avg_trust >= 0.4 ? C.warn : C.error;
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: `1px solid ${C.border}` }}>
                      <span style={{ fontSize: 12, flex: 1 }}>{t.type}</span>
                      <span style={{ fontSize: 12, fontWeight: 700 }}>{t.count}</span>
                      <span style={{ fontSize: 11, color: tc }}>{(t.avg_trust * 100).toFixed(0)}% trust</span>
                      <MeterBar value={t.avg_trust} color={tc} />
                    </div>
                  );
                })}
              </div>
            )}

            {/* Top sources */}
            {dashboard.learning_examples?.top_sources?.length > 0 && (
              <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Top Sources</div>
                {dashboard.learning_examples.top_sources.map((s, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
                    <span style={{ color: C.muted }}>{s.source}</span>
                    <span style={{ fontWeight: 700 }}>{s.count}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Full aggregation: extra sections */}
            {fullData?.learning_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Learning Status</div>
                {typeof fullData.learning_status === 'object' ? (
                  Object.entries(fullData.learning_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.learning_status)}</span>
                )}
              </div>
            )}
            {fullData?.ml_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>ML Status</div>
                {typeof fullData.ml_status === 'object' ? (
                  Object.entries(fullData.ml_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ml_status)}</span>
                )}
              </div>
            )}
            {fullData?.sandbox_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Sandbox Status</div>
                {typeof fullData.sandbox_status === 'object' ? (
                  Object.entries(fullData.sandbox_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.sandbox_status)}</span>
                )}
              </div>
            )}
            {fullData?.proactive_status && (
              <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Proactive Status</div>
                {typeof fullData.proactive_status === 'object' ? (
                  Object.entries(fullData.proactive_status).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                      <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.proactive_status)}</span>
                )}
              </div>
            )}
          </div>
        )}
        {activeTab === 'overview' && !dashboard && (
          <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading dashboard...</div>
        )}
        {activeTab === 'training' && <TrainingDataPanel />}
        {activeTab === 'audit' && <AuditPanel />}
      </div>
    </div>
  );
}
