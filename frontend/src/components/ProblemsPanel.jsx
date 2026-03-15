import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = { bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460', accent: '#e94560', accentAlt: '#533483', text: '#eee', muted: '#aaa', dim: '#666', border: '#333', success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3' };

const sevColor = { critical: '#f44336', warning: '#ff9800', info: '#2196f3' };
const sevIcon = { critical: '🔴', warning: '🟡', info: '🔵' };

const sourceColor = {
  blackbox: '#9c27b0',
  component_health: '#ff5722',
  diagnostic: '#2196f3',
  validation: '#ff9800',
  cognitive: '#e91e63',
};
const sourceLabel = {
  blackbox: 'Scanner',
  component_health: 'Components',
  diagnostic: 'Diagnostic',
  validation: 'Trust/KPI',
  cognitive: 'Cognitive',
};

function SeverityBadge({ severity }) {
  return (
    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, fontWeight: 700, background: (sevColor[severity] || C.dim) + '25', color: sevColor[severity] || C.dim, textTransform: 'uppercase' }}>
      {sevIcon[severity] || '⚪'} {severity}
    </span>
  );
}

function SourceBadge({ source }) {
  const color = sourceColor[source] || C.dim;
  return (
    <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, fontWeight: 700, background: color + '20', color, textTransform: 'uppercase', letterSpacing: 0.5 }}>
      {sourceLabel[source] || source}
    </span>
  );
}

export default function ProblemsPanel() {
  const [viewMode, setViewMode] = useState('problems');
  const [report, setReport] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [scanning, setScanning] = useState(false);

  // Tail logs state
  const [logs, setLogs] = useState([]);
  const [logConnected, setLogConnected] = useState(false);
  const [logPaused, setLogPaused] = useState(false);
  const logScrollRef = useRef(null);
  const logWsRef = useRef(null);
  const logPausedRef = useRef(false);

  // Keep ref in sync with state (avoids WS reconnect on pause toggle)
  useEffect(() => { logPausedRef.current = logPaused; }, [logPaused]);

  // Fetch unified report
  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/problems/unified`);
      if (res.ok) {
        const data = await res.json();
        if (data.ok) {
          setReport(data.report);
          setActions(data.recent_actions || []);
        }
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  // Trigger manual scan (runs blackbox then re-fetches unified)
  const triggerScan = async () => {
    setScanning(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/problems/scan`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.ok) {
          setReport(data.report);
          setActions(data.recent_actions || []);
        }
      }
    } catch { /* silent */ }
    finally { setScanning(false); }
  };

  // WebSocket for real-time unified events
  useEffect(() => {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/api/problems/ws';
    let ws;
    let reconnectDelay = 1000;
    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.topic === 'spindle.blackbox.report') {
            // Full report refresh
            fetchReport();
          } else if (msg.topic === 'audit.spindle') {
            setActions(prev => {
              const updated = [{ ...msg.data, timestamp: msg.timestamp }, ...prev];
              return updated.length > 100 ? updated.slice(0, 100) : updated;
            });
          } else if (msg.topic?.startsWith('system.health_changed') || msg.topic?.startsWith('invariant.') || msg.topic?.startsWith('confidence.')) {
            // Health change or invariant violation — refresh
            fetchReport();
          }
        } catch { /* ignore */ }
      };
      ws.onclose = () => { reconnectDelay = Math.min(reconnectDelay * 2, 30000); setTimeout(connect, reconnectDelay); };
      ws.onopen = () => { reconnectDelay = 1000; };
      ws.onerror = () => { ws.close(); };
    };
    connect();
    return () => { if (ws) { ws.onclose = null; ws.close(); } };
  }, [fetchReport]);

  // Tail logs WebSocket (only connects when view is 'logs')
  useEffect(() => {
    if (viewMode !== 'logs') return;
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/api/autonomous/logs/stream';
    let logReconnectDelay = 1000;
    const connect = () => {
      logWsRef.current = new WebSocket(wsUrl);
      logWsRef.current.onopen = () => {
        setLogConnected(true);
        setLogs(prev => [...prev, '[SYSTEM] Connected to log stream...']);
        logReconnectDelay = 1000;
      };
      logWsRef.current.onmessage = (event) => {
        if (!logPausedRef.current) {
          setLogs(prev => {
            const newLogs = [...prev, event.data];
            return newLogs.length > 1000 ? newLogs.slice(newLogs.length - 1000) : newLogs;
          });
        }
      };
      logWsRef.current.onclose = () => {
        setLogConnected(false);
        logReconnectDelay = Math.min(logReconnectDelay * 2, 30000);
        setTimeout(connect, logReconnectDelay);
      };
      logWsRef.current.onerror = () => { logWsRef.current.close(); };
    };
    connect();
    return () => {
      if (logWsRef.current) { logWsRef.current.onclose = null; logWsRef.current.close(); }
    };
  }, [viewMode]);

  // Auto-scroll logs
  useEffect(() => {
    if (!logPaused && logScrollRef.current) {
      logScrollRef.current.scrollTop = logScrollRef.current.scrollHeight;
    }
  }, [logs, logPaused]);

  // Filter alerts
  const alerts = report?.alerts || [];
  const filtered = alerts.filter(a => {
    if (filter !== 'all' && a.severity !== filter) return false;
    if (categoryFilter !== 'all' && a.category !== categoryFilter) return false;
    if (sourceFilter !== 'all' && a.source !== sourceFilter) return false;
    return true;
  });
  const categories = [...new Set(alerts.map(a => a.category))].sort();
  const sources = [...new Set(alerts.map(a => a.source))].sort();

  const renderLogLine = (line, index) => {
    if (!line) return null;
    let color = '#ccc';
    if (line.includes('[ERROR]') || line.includes('Exception') || line.includes('Failed')) color = '#f44336';
    else if (line.includes('[WARNING]') || line.includes('WARN')) color = '#ff9800';
    else if (line.includes('[INFO]') || line.includes('SUCCESS') || line.includes('[OK]')) color = '#4caf50';
    else if (line.includes('DEBUG')) color = '#888';
    else if (line.includes('API') || line.includes('HTTP')) color = '#2196f3';
    else if (line.includes('[SYSTEM]')) color = '#4caf50';
    return <div key={index} style={{ color, marginBottom: 2, wordBreak: 'break-all', fontSize: 12, fontFamily: 'monospace' }}>{line}</div>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toggle bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', marginBottom: 12 }}>
        <button onClick={() => setViewMode('problems')} style={{
          padding: '6px 16px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          background: viewMode === 'problems' ? C.accent : C.bgDark, color: '#fff',
        }}>🚨 Problems</button>
        <button onClick={() => setViewMode('logs')} style={{
          padding: '6px 16px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          background: viewMode === 'logs' ? C.accent : C.bgDark, color: '#fff',
        }}>📜 Tail Logs</button>
        {viewMode === 'problems' && (
          <>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
              <select value={filter} onChange={e => setFilter(e.target.value)} style={{ background: C.bgDark, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, padding: '4px 8px', fontSize: 11 }}>
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
              <select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)} style={{ background: C.bgDark, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, padding: '4px 8px', fontSize: 11 }}>
                <option value="all">All Sources</option>
                {sources.map(s => <option key={s} value={s}>{sourceLabel[s] || s}</option>)}
              </select>
              <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} style={{ background: C.bgDark, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, padding: '4px 8px', fontSize: 11 }}>
                <option value="all">All Categories</option>
                {categories.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
              <button onClick={triggerScan} disabled={scanning} style={{ padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, color: '#fff', background: C.accentAlt, opacity: scanning ? 0.5 : 1 }}>
                {scanning ? '⏳ Scanning...' : '🔍 Scan Now'}
              </button>
              <button onClick={fetchReport} style={{ padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, color: '#fff', background: C.bgDark }}>↻</button>
            </div>
          </>
        )}
        {viewMode === 'logs' && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: logConnected ? C.success : C.error }} />
            <span style={{ fontSize: 11, color: C.muted }}>{logConnected ? 'Connected' : 'Disconnected'}</span>
            <button onClick={() => setLogPaused(!logPaused)} style={{ padding: '4px 10px', border: '1px solid #444', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#aaa', background: 'transparent' }}>
              {logPaused ? '▶ Resume' : '⏸ Pause'}
            </button>
            <button onClick={() => setLogs([])} style={{ padding: '4px 10px', border: '1px solid #444', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#aaa', background: 'transparent' }}>🗑 Clear</button>
          </div>
        )}
      </div>

      {/* Problems View */}
      {viewMode === 'problems' && (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading && !report ? (
            <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading problems...</div>
          ) : (
            <>
              {/* Summary cards */}
              {report && (
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
                  {[
                    { label: 'Total', val: report.total_issues || 0, color: C.text, icon: '📋' },
                    { label: 'Critical', val: report.critical_count || 0, color: C.error, icon: '🔴' },
                    { label: 'Warning', val: report.warning_count || 0, color: C.warn, icon: '🟡' },
                    { label: 'Info', val: report.info_count || 0, color: C.info, icon: '🔵' },
                    { label: 'Sources', val: (report.sources_queried || []).length, color: C.muted, icon: '🔌' },
                  ].map((s, i) => (
                    <div key={i} style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '12px 14px', flex: '1 1 110px', minWidth: 100 }}>
                      <div style={{ fontSize: 10, color: C.muted, marginBottom: 4 }}>{s.icon} {s.label}</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.val}</div>
                    </div>
                  ))}
                  {report.scan_duration_ms != null && (
                    <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '12px 14px', flex: '1 1 110px', minWidth: 100 }}>
                      <div style={{ fontSize: 10, color: C.muted, marginBottom: 4 }}>⏱ Aggregation</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: C.muted }}>{(report.scan_duration_ms / 1000).toFixed(1)}s</div>
                    </div>
                  )}
                </div>
              )}

              {/* Source health strip */}
              {report?.sources_queried?.length > 0 && (
                <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
                  {['blackbox', 'component_health', 'diagnostic', 'validation', 'cognitive'].map(src => {
                    const queried = (report.sources_queried || []).includes(src);
                    const failed = (report.sources_failed || []).includes(src);
                    const color = failed ? C.error : queried ? C.success : C.dim;
                    return (
                      <div key={src} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 10 }}>
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
                        <span style={{ color: C.muted }}>{sourceLabel[src] || src}</span>
                        {failed && <span style={{ color: C.error, fontWeight: 700 }}>✗</span>}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Alerts list */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                  {filtered.length} Alert{filtered.length !== 1 ? 's' : ''}
                  {filter !== 'all' && <span style={{ color: C.dim, fontWeight: 400 }}> ({filter})</span>}
                  {sourceFilter !== 'all' && <span style={{ color: C.dim, fontWeight: 400 }}> from {sourceLabel[sourceFilter] || sourceFilter}</span>}
                </div>
                {filtered.length === 0 ? (
                  <div style={{ padding: 20, textAlign: 'center', color: C.dim, background: C.bgAlt, borderRadius: 8 }}>
                    {report ? '✅ No issues found' : 'No scan data available'}
                  </div>
                ) : (
                  filtered.map((a, i) => (
                    <div key={i} style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, padding: '10px 14px', marginBottom: 6 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <SeverityBadge severity={a.severity} />
                        <SourceBadge source={a.source} />
                        <span style={{ fontSize: 11, color: C.dim, padding: '1px 6px', background: C.bgDark, borderRadius: 3 }}>{(a.category || '').replace(/_/g, ' ')}</span>
                        {a.occurrences > 1 && <span style={{ fontSize: 10, color: C.warn }}>×{a.occurrences}</span>}
                        {a.component && <span style={{ fontSize: 10, color: C.info, padding: '1px 5px', background: C.info + '15', borderRadius: 3 }}>⚙ {a.component}</span>}
                        {a.auto_healable && <span style={{ fontSize: 10, color: C.success, padding: '1px 5px', background: C.success + '15', borderRadius: 3 }}>🔧 auto-heal</span>}
                        {a.file && <span style={{ fontSize: 10, color: C.dim, marginLeft: 'auto', fontFamily: 'monospace' }}>{a.file}{a.line ? `:${a.line}` : ''}</span>}
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{a.title}</div>
                      {a.description && a.description !== a.title && <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{a.description}</div>}
                      {a.fix_suggestion && (
                        <div style={{ fontSize: 11, color: C.success, background: C.success + '15', padding: '4px 8px', borderRadius: 4, marginTop: 4 }}>
                          💡 {a.fix_suggestion}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Recent autonomous actions */}
              {actions.length > 0 && (
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>🤖 Recent Spindle Actions</div>
                  {actions.slice(0, 20).map((a, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', marginBottom: 4, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 11 }}>
                      <span style={{ color: a.decision === 'act' ? C.success : a.action?.includes('rejected') ? C.error : C.info }}>
                        {a.decision === 'act' ? '⚡' : a.action?.includes('rejected') ? '❌' : '📋'}
                      </span>
                      <span style={{ color: C.muted, flex: '0 0 120px' }}>{a.action || 'unknown'}</span>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.title || a.target || ''}</span>
                      {a.trust !== undefined && <span style={{ color: a.trust >= 0.8 ? C.success : C.warn }}>trust: {(a.trust * 100).toFixed(0)}%</span>}
                      {a.timestamp && <span style={{ color: C.dim }}>{new Date(a.timestamp).toLocaleTimeString()}</span>}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tail Logs View */}
      {viewMode === 'logs' && (
        <div ref={logScrollRef} style={{
          flex: 1, overflow: 'auto', background: 'rgba(10, 10, 26, 0.95)',
          border: `1px solid ${C.border}`, borderRadius: 8, padding: 12,
        }}>
          {logs.length === 0 && <div style={{ color: '#666', fontFamily: 'monospace', fontSize: 12 }}>Waiting for logs...</div>}
          {logs.map((line, i) => renderLogLine(line, i))}
        </div>
      )}
    </div>
  );
}
