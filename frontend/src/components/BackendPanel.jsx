/**
 * BackendPanel — Reusable component that shows live data from
 * ALL backend endpoints that belong to a tab's domain.
 *
 * Usage: <BackendPanel prefixes={['/kpi', '/monitoring']} label="Governance" />
 *
 * It fetches the route list, filters by prefixes, and lets users
 * click any endpoint to see its live response. No black boxes.
 */
import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#0d1117', bgAlt: '#161b22', text: '#e6edf3', muted: '#8b949e',
  dim: '#484f58', border: '#30363d', accent: '#e94560', success: '#3fb950',
  warn: '#d29922', error: '#f85149', info: '#58a6ff',
};

function MethodBadge({ method }) {
  const colors = { GET: '#61affe', POST: '#49cc90', PUT: '#fca130', DELETE: '#f93e3e' };
  return (
    <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, fontWeight: 800,
      background: (colors[method] || C.dim) + '30', color: colors[method] || C.dim, fontFamily: 'monospace' }}>
      {method}
    </span>
  );
}

export default function BackendPanel({ prefixes = [], label = 'Backend' }) {
  const [routes, setRoutes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [calling, setCalling] = useState(false);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/explorer/routes`)
      .then(r => r.ok ? r.json() : { routes: [] })
      .then(d => {
        const filtered = (d.routes || []).filter(r =>
          prefixes.some(p => r.path.startsWith(p))
        );
        setRoutes(filtered);
      })
      .catch(() => {});
  }, [prefixes]);

  const callEndpoint = useCallback(async (method, path) => {
    setSelected(`${method} ${path}`);
    setCalling(true); setResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/explorer/call`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method, path }),
      });
      if (res.ok) setResult(await res.json());
    } catch { /* silent */ }
    finally { setCalling(false); }
  }, []);

  const filtered = filter
    ? routes.filter(r => r.path.toLowerCase().includes(filter.toLowerCase()))
    : routes;

  if (routes.length === 0) return null;

  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 8, overflow: 'hidden', marginTop: 16 }}>
      <div style={{ padding: '8px 12px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: C.muted }}>🔌 {label} Backend ({routes.length} endpoints)</span>
        <input placeholder="Filter..." value={filter} onChange={e => setFilter(e.target.value)}
          style={{ marginLeft: 'auto', padding: '3px 8px', background: C.bg, color: C.text, border: `1px solid ${C.border}`,
            borderRadius: 4, fontSize: 10, outline: 'none', width: 140 }} />
      </div>

      <div style={{ display: 'flex', maxHeight: 350 }}>
        {/* Route list */}
        <div style={{ flex: '0 0 280px', overflowY: 'auto', borderRight: `1px solid ${C.border}` }}>
          {filtered.map((r, i) => (
            <div key={`${r.method}-${r.path}-${i}`}
              onClick={() => callEndpoint(r.method, r.path)}
              style={{
                padding: '4px 10px', cursor: 'pointer', fontSize: 10,
                display: 'flex', alignItems: 'center', gap: 5,
                background: selected === `${r.method} ${r.path}` ? C.bgAlt : 'transparent',
                borderBottom: `1px solid ${C.border}11`,
              }}
              onMouseEnter={e => e.currentTarget.style.background = C.bgAlt}
              onMouseLeave={e => { if (selected !== `${r.method} ${r.path}`) e.currentTarget.style.background = 'transparent'; }}
            >
              <MethodBadge method={r.method} />
              <span style={{ fontFamily: 'monospace', fontSize: 9, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.path}</span>
            </div>
          ))}
        </div>

        {/* Response */}
        <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
          {calling ? (
            <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 11 }}>Loading...</div>
          ) : result ? (
            <>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 800,
                  color: result.status_code >= 200 && result.status_code < 300 ? C.success : C.error }}>
                  {result.status_code}
                </span>
                <span style={{ fontSize: 10, color: C.dim }}>{result.response_time_ms}ms</span>
              </div>
              <pre style={{ margin: 0, padding: 8, background: C.bg, borderRadius: 4, fontSize: 10,
                lineHeight: 1.4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.text, maxHeight: 280, overflow: 'auto' }}>
                {typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2)}
              </pre>
            </>
          ) : (
            <div style={{ padding: 30, textAlign: 'center', color: C.dim, fontSize: 11 }}>
              Click any endpoint to see live data
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
