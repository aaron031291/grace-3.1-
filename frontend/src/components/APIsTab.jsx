import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  live: '#4caf50', broken: '#f44336', unconnected: '#ff9800', info: '#2196f3',
};
const btn = (bg = C.accentAlt) => ({
  padding: '5px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});

function StatusDot({ status }) {
  const color = { live: C.live, broken: C.broken, unconnected: C.unconnected }[status] || C.dim;
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />;
}

function StatusBadge({ status }) {
  const color = { live: C.live, broken: C.broken, unconnected: C.unconnected }[status] || C.dim;
  return (
    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, fontWeight: 700, background: color + '25', color, textTransform: 'uppercase' }}>
      {status}
    </span>
  );
}

function MethodBadge({ method }) {
  const colors = { GET: '#61affe', POST: '#49cc90', PUT: '#fca130', DELETE: '#f93e3e', PATCH: '#50e3c2' };
  return (
    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, fontWeight: 800, background: (colors[method] || C.dim) + '30', color: colors[method] || C.dim, fontFamily: 'monospace' }}>
      {method}
    </span>
  );
}

export default function APIsTab() {
  const [mode, setMode] = useState('catalogue'); // 'catalogue' | 'explorer'
  const [registry, setRegistry] = useState(null);
  const [healthCheck, setHealthCheck] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(null);

  // Explorer state
  const [explorerRoutes, setExplorerRoutes] = useState([]);
  const [explorerMethod, setExplorerMethod] = useState('GET');
  const [explorerPath, setExplorerPath] = useState('');
  const [explorerBody, setExplorerBody] = useState('{}');
  const [explorerResult, setExplorerResult] = useState(null);
  const [explorerCalling, setExplorerCalling] = useState(false);
  const [explorerFilter, setExplorerFilter] = useState('');
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);
  const [filter, setFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expandedGroups, setExpandedGroups] = useState(new Set());

  const fetchRegistry = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/registry/all`);
      if (res.ok) {
        const d = await res.json();
        setRegistry(d);
        setExpandedGroups(new Set(Object.keys(d.groups || {})));
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  const runHealthCheck = useCallback(async () => {
    setChecking(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/registry/health-check`);
      if (res.ok) setHealthCheck(await res.json());
    } catch { /* silent */ }
    finally { setChecking(false); }
  }, []);

  useEffect(() => { fetchRegistry(); }, [fetchRegistry]);

  useEffect(() => {
    if (mode === 'explorer' && explorerRoutes.length === 0) {
      fetch(`${API_BASE_URL}/api/explorer/routes`)
        .then(r => r.ok ? r.json() : { routes: [] })
        .then(d => setExplorerRoutes(d.routes || []))
        .catch(() => {});
    }
  }, [mode, explorerRoutes.length]);

  const callEndpoint = async () => {
    if (!explorerPath) return;
    setExplorerCalling(true); setExplorerResult(null);
    try {
      let body = null;
      if (explorerMethod !== 'GET' && explorerBody.trim()) {
        try { body = JSON.parse(explorerBody); } catch { body = null; }
      }
      const res = await fetch(`${API_BASE_URL}/api/explorer/call`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: explorerMethod, path: explorerPath, body }),
      });
      if (res.ok) setExplorerResult(await res.json());
    } catch { /* silent */ }
    finally { setExplorerCalling(false); }
  };

  const diagnoseAPI = async (path, error) => {
    setDiagnosing(true);
    setDiagnosis(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/registry/diagnose`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_path: path, error_info: error }),
      });
      if (res.ok) setDiagnosis(await res.json());
    } catch { /* silent */ }
    finally { setDiagnosing(false); }
  };

  const toggleGroup = (g) => {
    setExpandedGroups(prev => { const n = new Set(prev); if (n.has(g)) n.delete(g); else n.add(g); return n; });
  };

  const allGroups = registry ? Object.keys(registry.groups || {}) : [];

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: C.dim, background: C.bg }}>Loading API registry...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>

      {/* Header */}
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>🔗 APIs</span>
        <div style={{ display: 'flex', background: C.bgDark, borderRadius: 4, overflow: 'hidden' }}>
          <button onClick={() => setMode('catalogue')} style={{ ...btn(mode === 'catalogue' ? C.accentAlt : 'transparent'), borderRadius: 0, fontSize: 11, padding: '4px 12px' }}>Catalogue</button>
          <button onClick={() => setMode('explorer')} style={{ ...btn(mode === 'explorer' ? C.accentAlt : 'transparent'), borderRadius: 0, fontSize: 11, padding: '4px 12px' }}>Explorer</button>
        </div>
        {registry && <span style={{ fontSize: 11, color: C.dim }}>{registry.total_routes} endpoints</span>}

        <input placeholder="Filter endpoints..." value={filter} onChange={e => setFilter(e.target.value)}
          style={{ padding: '5px 10px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bg, color: C.text, fontSize: 12, outline: 'none', flex: '0 1 200px' }} />

        <select value={groupFilter} onChange={e => setGroupFilter(e.target.value)}
          style={{ padding: '5px 8px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bg, color: C.text, fontSize: 11, outline: 'none' }}>
          <option value="all">All Groups</option>
          {allGroups.map(g => <option key={g} value={g}>{g}</option>)}
        </select>

        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '5px 8px', border: `1px solid ${C.border}`, borderRadius: 4, background: C.bg, color: C.text, fontSize: 11, outline: 'none' }}>
          <option value="all">All Status</option>
          <option value="live">🟢 Live</option>
          <option value="broken">🔴 Broken</option>
          <option value="unconnected">🟡 Unconnected</option>
        </select>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button onClick={runHealthCheck} disabled={checking} style={{ ...btn(C.info), opacity: checking ? 0.5 : 1 }}>
            {checking ? '⏳ Checking...' : '🏥 Health Check'}
          </button>
          <button onClick={fetchRegistry} style={btn(C.bgDark)}>↻</button>
        </div>
      </div>

      {/* Health check summary bar */}
      {healthCheck && (
        <div style={{ padding: '8px 16px', borderBottom: `1px solid ${C.border}`, background: C.bg, display: 'flex', gap: 16, alignItems: 'center', fontSize: 12 }}>
          <span style={{ fontWeight: 700, color: C.muted }}>Health:</span>
          <span style={{ color: C.live }}>🟢 {healthCheck.summary?.live || 0} live</span>
          <span style={{ color: C.broken }}>🔴 {healthCheck.summary?.broken || 0} broken</span>
          <span style={{ color: C.unconnected }}>🟡 {healthCheck.summary?.unconnected || 0} unconnected</span>
          <span style={{ fontSize: 10, color: C.dim, marginLeft: 'auto' }}>Checked: {healthCheck.checked_at ? new Date(healthCheck.checked_at).toLocaleTimeString() : ''}</span>
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {mode === 'explorer' ? (
          /* ── Explorer Mode ─────────────────────────────── */
          <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            {/* Route list */}
            <div style={{ flex: '0 0 320px', borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
                <input placeholder="Filter routes..." value={explorerFilter} onChange={e => setExplorerFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 8px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 11, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                {explorerRoutes
                  .filter(r => !explorerFilter || r.path.toLowerCase().includes(explorerFilter.toLowerCase()) || (r.description || '').toLowerCase().includes(explorerFilter.toLowerCase()))
                  .map((r, i) => (
                  <div key={`${r.method}-${r.path}-${i}`}
                    onClick={() => { setExplorerMethod(r.method); setExplorerPath(r.path); setExplorerResult(null); }}
                    style={{
                      padding: '5px 12px', cursor: 'pointer', fontSize: 11,
                      display: 'flex', alignItems: 'center', gap: 6,
                      background: explorerPath === r.path && explorerMethod === r.method ? C.bgDark : 'transparent',
                      borderBottom: `1px solid ${C.border}11`,
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = C.bgAlt}
                    onMouseLeave={e => { if (!(explorerPath === r.path && explorerMethod === r.method)) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <MethodBadge method={r.method} />
                    <span style={{ flex: 1, fontFamily: 'monospace', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.path}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Call panel */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {/* Request bar */}
              <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center' }}>
                <select value={explorerMethod} onChange={e => setExplorerMethod(e.target.value)}
                  style={{ padding: '6px 8px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none', fontWeight: 700 }}>
                  {['GET', 'POST', 'PUT', 'DELETE'].map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <input value={explorerPath} onChange={e => setExplorerPath(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && callEndpoint()}
                  placeholder="/api/endpoint/path"
                  style={{ flex: 1, padding: '6px 10px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none', fontFamily: 'monospace' }} />
                <button onClick={callEndpoint} disabled={explorerCalling || !explorerPath}
                  style={{ ...btn(C.live), opacity: explorerCalling ? 0.5 : 1 }}>
                  {explorerCalling ? '⏳' : '▶ Send'}
                </button>
              </div>

              {/* Body editor for POST/PUT */}
              {(explorerMethod === 'POST' || explorerMethod === 'PUT') && (
                <div style={{ borderBottom: `1px solid ${C.border}` }}>
                  <div style={{ padding: '4px 16px', fontSize: 10, color: C.muted }}>Request Body (JSON)</div>
                  <textarea value={explorerBody} onChange={e => setExplorerBody(e.target.value)}
                    style={{ width: '100%', height: 80, resize: 'vertical', background: '#0d1117', color: '#e6edf3', border: 'none', padding: '8px 16px', fontFamily: 'monospace', fontSize: 12, outline: 'none', boxSizing: 'border-box' }} />
                </div>
              )}

              {/* Response */}
              <div style={{ flex: 1, overflow: 'auto' }}>
                {explorerResult ? (
                  <div style={{ padding: 16 }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
                      <span style={{
                        fontSize: 14, fontWeight: 800,
                        color: explorerResult.status_code >= 200 && explorerResult.status_code < 300 ? C.live
                          : explorerResult.status_code >= 400 ? C.broken : C.unconnected,
                      }}>
                        {explorerResult.status_code || 'ERR'}
                      </span>
                      {explorerResult.response_time_ms && (
                        <span style={{ fontSize: 11, color: C.dim }}>{explorerResult.response_time_ms}ms</span>
                      )}
                      {explorerResult.error && (
                        <span style={{ fontSize: 11, color: C.broken }}>{explorerResult.error}</span>
                      )}
                    </div>
                    <pre style={{
                      margin: 0, padding: 16, background: '#0d1117', color: '#e6edf3',
                      borderRadius: 6, fontSize: 12, lineHeight: 1.5,
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                      maxHeight: 'calc(100vh - 300px)', overflow: 'auto',
                    }}>
                      {typeof explorerResult.data === 'string'
                        ? explorerResult.data
                        : JSON.stringify(explorerResult.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div style={{ padding: 60, textAlign: 'center', color: C.dim }}>
                    <div style={{ fontSize: 48, opacity: 0.4 }}>🔍</div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: C.muted, marginTop: 12 }}>API Explorer</div>
                    <div style={{ fontSize: 12, marginTop: 4, maxWidth: 300, margin: '4px auto 0' }}>
                      Select any endpoint from the list or type a path, then hit Send.
                      See the raw response — no black boxes.
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
        <>
        {/* Left: API list by group */}
        <div style={{ flex: 1, overflowY: 'auto', borderRight: selectedRoute ? `1px solid ${C.border}` : 'none' }}>

          {/* External services */}
          {registry?.external_services?.length > 0 && (groupFilter === 'all' || groupFilter === 'External') && (
            <div style={{ marginBottom: 4 }}>
              <div style={{ padding: '8px 16px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: C.accent, textTransform: 'uppercase', letterSpacing: '0.5px' }}>External Services</span>
              </div>
              {registry.external_services.map((ext, i) => (
                <div key={i} style={{ padding: '8px 16px', borderBottom: `1px solid ${C.border}22`, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <StatusDot status={ext.health?.status} />
                  <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>{ext.name}</span>
                  <span style={{ fontSize: 10, color: C.dim, fontFamily: 'monospace' }}>{ext.url}</span>
                  <StatusBadge status={ext.health?.status} />
                  {ext.health?.response_ms && <span style={{ fontSize: 10, color: C.dim }}>{ext.health.response_ms.toFixed(0)}ms</span>}
                </div>
              ))}
            </div>
          )}

          {/* Internal groups */}
          {allGroups.filter(g => groupFilter === 'all' || g === groupFilter).map(groupName => {
            const group = registry.groups[groupName];
            const isOpen = expandedGroups.has(groupName);

            let routes = group.routes || [];
            if (filter) routes = routes.filter(r => r.path.toLowerCase().includes(filter.toLowerCase()) || r.who?.toLowerCase().includes(filter.toLowerCase()));
            if (statusFilter !== 'all') {
              const hcMap = {};
              if (healthCheck?.internal) healthCheck.internal.forEach(h => { hcMap[h.path] = h.status; });
              if (statusFilter === 'live') routes = routes.filter(r => hcMap[r.path] === 'live' || !hcMap[r.path]);
              else routes = routes.filter(r => hcMap[r.path] === statusFilter);
            }
            if (routes.length === 0 && filter) return null;

            return (
              <div key={groupName}>
                <div onClick={() => toggleGroup(groupName)} style={{
                  padding: '8px 16px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`,
                  display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none',
                }}>
                  <span style={{ fontSize: 10, width: 14, textAlign: 'center', color: C.muted }}>{isOpen ? '▼' : '▶'}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.5px', flex: 1 }}>{groupName}</span>
                  <span style={{ fontSize: 10, color: C.dim }}>{routes.length} endpoints</span>
                </div>
                {isOpen && routes.map((r, i) => {
                  const hc = healthCheck?.internal?.find(h => h.path === r.path);
                  const isSel = selectedRoute?.path === r.path && selectedRoute?.method === r.method;
                  return (
                    <div key={`${r.method}-${r.path}-${i}`}
                      onClick={() => setSelectedRoute(r)}
                      style={{
                        padding: '6px 16px 6px 36px', display: 'flex', alignItems: 'center', gap: 8,
                        borderBottom: `1px solid ${C.border}11`, cursor: 'pointer', fontSize: 12,
                        background: isSel ? C.bgDark : 'transparent',
                        borderLeft: isSel ? `3px solid ${C.accent}` : '3px solid transparent',
                      }}
                      onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = C.bgAlt; }}
                      onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = 'transparent'; }}
                    >
                      {hc && <StatusDot status={hc.status} />}
                      <MethodBadge method={r.method} />
                      <span style={{ flex: 1, fontFamily: 'monospace', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.path}</span>
                      <span style={{ fontSize: 10, color: C.dim, flexShrink: 0 }}>{r.who}</span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Right: Detail panel */}
        {selectedRoute && (
          <div style={{ flex: '0 0 380px', overflow: 'auto', padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <MethodBadge method={selectedRoute.method} />
              <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'monospace', wordBreak: 'break-all' }}>{selectedRoute.path}</span>
              <span onClick={() => { setSelectedRoute(null); setDiagnosis(null); }} style={{ marginLeft: 'auto', cursor: 'pointer', fontSize: 16, color: C.muted }}>✕</span>
            </div>

            <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, marginBottom: 14 }}>
              {[
                ['What', selectedRoute.name?.replace(/_/g, ' ')],
                ['Where', selectedRoute.path],
                ['Who', selectedRoute.who],
                ['Why', selectedRoute.why],
                ['How', `${selectedRoute.method} request`],
                ['Group', selectedRoute.group],
                ['Category', selectedRoute.category],
              ].map(([label, val]) => (
                <div key={label} style={{ display: 'flex', gap: 8, padding: '4px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
                  <span style={{ color: C.muted, width: 60, flexShrink: 0, fontWeight: 600 }}>{label}</span>
                  <span style={{ color: C.text }}>{val || '—'}</span>
                </div>
              ))}
            </div>

            {/* Health check result */}
            {healthCheck?.internal && (() => {
              const hc = healthCheck.internal.find(h => selectedRoute.path.startsWith(h.path.split('?')[0]));
              if (!hc) return null;
              return (
                <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Health Check</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <StatusDot status={hc.status} />
                    <StatusBadge status={hc.status} />
                    {hc.response_ms && <span style={{ fontSize: 11, color: C.dim }}>{hc.response_ms.toFixed(0)}ms</span>}
                    {hc.code && <span style={{ fontSize: 11, color: C.dim }}>HTTP {hc.code}</span>}
                  </div>
                  {hc.error && <div style={{ fontSize: 11, color: C.broken, marginTop: 4 }}>Error: {hc.error}</div>}
                </div>
              );
            })()}

            {/* Diagnose button */}
            <button onClick={() => diagnoseAPI(selectedRoute.path, '')} disabled={diagnosing}
              style={{ ...btn(C.accent), width: '100%', marginBottom: 14, opacity: diagnosing ? 0.5 : 1 }}>
              {diagnosing ? '⏳ Diagnosing...' : '🧠 Diagnose with Kimi'}
            </button>

            {diagnosis && (
              <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: C.accent, marginBottom: 8 }}>🧠 Kimi Diagnosis</div>
                <pre style={{ margin: 0, fontSize: 11, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {diagnosis.diagnosis}
                </pre>
              </div>
            )}
          </div>
        )}
        </>
        )}
      </div>
    </div>
  );
}
