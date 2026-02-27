/**
 * FlashCachePanel — Browse, search, and stream from cached source references.
 *
 * Features:
 *   - Keyword search across all cached references
 *   - View entry metadata (keywords, trust, access count)
 *   - Stream content on demand from original source
 *   - Predict related keywords for a topic
 *   - Cache statistics dashboard
 *   - Validate source accessibility
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3',
};

const btnS = (bg = C.accentAlt) => ({
  padding: '5px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 11, fontWeight: 600, color: '#fff', background: bg,
});

function TypeBadge({ type }) {
  const colors = { api: '#2196f3', web: '#4caf50', search: '#ff9800', internal: '#9c27b0', document: '#795548' };
  const icons = { api: '🔌', web: '🌐', search: '🔍', internal: '⚙️', document: '📄' };
  return (
    <span style={{
      fontSize: 9, padding: '2px 6px', borderRadius: 3,
      background: colors[type] || C.border, color: '#fff', fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.5px',
    }}>
      {icons[type] || '📋'} {type}
    </span>
  );
}

function TrustBar({ score }) {
  const pct = Math.round((score || 0) * 100);
  const color = pct >= 70 ? C.success : pct >= 40 ? C.warn : C.error;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 6, background: '#222', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 10, color: C.dim }}>{pct}%</span>
    </div>
  );
}

export default function FlashCachePanel() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [selected, setSelected] = useState(null);
  const [streamData, setStreamData] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [predictions, setPredictions] = useState(null);
  const [predTopic, setPredTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [subView, setSubView] = useState('search'); // search, predict, stats
  const notifTimer = useRef(null);

  const notify = useCallback((msg, type = 'success') => {
    setNotification({ msg, type });
    clearTimeout(notifTimer.current);
    notifTimer.current = setTimeout(() => setNotification(null), 3000);
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/stats`);
      if (res.ok) setStats(await res.json());
    } catch { /* skip */ }
  }, []);

  const fetchRecent = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/lookup?limit=30`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch { /* skip */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRecent();
  }, [fetchStats, fetchRecent]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) { fetchRecent(); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/search?q=${encodeURIComponent(searchQuery)}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch { /* skip */ }
    setLoading(false);
  };

  const handleStream = async (entryId) => {
    setStreaming(true);
    setStreamData(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/stream/${entryId}`);
      if (res.ok) {
        const data = await res.json();
        setStreamData(data);
      } else {
        notify('Stream failed', 'error');
      }
    } catch {
      notify('Stream error', 'error');
    }
    setStreaming(false);
  };

  const handleValidate = async (entryId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/validate/${entryId}`);
      if (res.ok) {
        const data = await res.json();
        notify(data.valid ? 'Source accessible' : `Source: ${data.reason}`, data.valid ? 'success' : 'error');
      }
    } catch {
      notify('Validation error', 'error');
    }
  };

  const handlePredict = async () => {
    if (!predTopic.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/predict?topic=${encodeURIComponent(predTopic)}`);
      if (res.ok) {
        const data = await res.json();
        setPredictions(data);
      }
    } catch { /* skip */ }
    setLoading(false);
  };

  const handleDelete = async (entryId) => {
    try {
      await fetch(`${API_BASE_URL}/api/flash-cache/entry/${entryId}`, { method: 'DELETE' });
      notify('Entry removed');
      setResults(prev => prev.filter(r => r.id !== entryId));
      if (selected?.id === entryId) setSelected(null);
      fetchStats();
    } catch { /* skip */ }
  };

  const handleCleanup = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/flash-cache/cleanup`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        notify(`Cleaned ${data.removed} stale entries`);
        fetchStats();
        fetchRecent();
      }
    } catch { /* skip */ }
  };

  return (
    <div style={{ display: 'flex', height: '100%', color: C.text, position: 'relative' }}>

      {notification && (
        <div style={{
          position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)', zIndex: 100,
          padding: '6px 18px', borderRadius: 6, fontSize: 12, fontWeight: 600,
          background: notification.type === 'success' ? C.success : notification.type === 'error' ? C.error : C.info,
          color: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,.4)',
        }}>{notification.msg}</div>
      )}

      {/* ── Left: Search & Results ────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}` }}>

        {/* Sub-view tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
          {[
            { id: 'search', label: '🔍 Search', },
            { id: 'predict', label: '🔮 Predict' },
            { id: 'stats', label: '📊 Stats' },
          ].map(t => (
            <button key={t.id} onClick={() => setSubView(t.id)} style={{
              padding: '8px 14px', border: 'none', background: 'none', cursor: 'pointer',
              color: subView === t.id ? C.accent : C.muted, fontSize: 12, fontWeight: subView === t.id ? 700 : 500,
              borderBottom: subView === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
            }}>{t.label}</button>
          ))}
        </div>

        {subView === 'search' && (
          <>
            {/* Search bar */}
            <div style={{ padding: '10px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 6 }}>
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Search keywords, summaries, sources..."
                style={{
                  flex: 1, padding: '7px 10px', border: `1px solid ${C.border}`, borderRadius: 4,
                  background: C.bg, color: C.text, fontSize: 12, outline: 'none',
                }}
              />
              <button onClick={handleSearch} style={btnS(C.accent)}>Search</button>
            </div>

            {/* Results list */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              {loading && <div style={{ padding: 20, textAlign: 'center', color: C.dim }}>Loading...</div>}
              {!loading && results.length === 0 && (
                <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>
                  No cached references yet. Sources are cached automatically when you use Whitelist, Search, or Oracle.
                </div>
              )}
              {results.map(entry => (
                <div
                  key={entry.id}
                  onClick={() => setSelected(entry)}
                  style={{
                    padding: '10px 14px', borderBottom: `1px solid ${C.border}`,
                    cursor: 'pointer',
                    background: selected?.id === entry.id ? C.bgDark : 'transparent',
                    borderLeft: selected?.id === entry.id ? `3px solid ${C.accent}` : '3px solid transparent',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <TypeBadge type={entry.source_type} />
                    <span style={{ fontSize: 12, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {entry.source_name || entry.source_uri?.split('/').pop()}
                    </span>
                    <TrustBar score={entry.trust_score} />
                  </div>
                  <div style={{ fontSize: 10, color: C.dim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.source_uri}
                  </div>
                  {entry.summary && (
                    <div style={{ fontSize: 11, color: C.muted, marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {entry.summary.substring(0, 120)}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {(Array.isArray(entry.keywords) ? entry.keywords : []).slice(0, 8).map((kw, i) => (
                      <span key={i} style={{
                        fontSize: 9, padding: '1px 5px', borderRadius: 3,
                        background: C.bgAlt, color: C.muted, border: `1px solid ${C.border}`,
                      }}>{kw}</span>
                    ))}
                    {entry.access_count > 0 && (
                      <span style={{ fontSize: 9, color: C.dim, marginLeft: 'auto' }}>
                        {entry.access_count} accesses
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {subView === 'predict' && (
          <div style={{ padding: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: C.muted }}>KEYWORD PREDICTION</div>
              <div style={{ fontSize: 11, color: C.dim, marginBottom: 10 }}>
                Enter a topic to discover related keywords across all cached sources. Uses co-occurrence analysis.
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={predTopic}
                  onChange={e => setPredTopic(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handlePredict()}
                  placeholder="e.g. machine learning, trading, psychology..."
                  style={{
                    flex: 1, padding: '7px 10px', border: `1px solid ${C.border}`, borderRadius: 4,
                    background: C.bg, color: C.text, fontSize: 12, outline: 'none',
                  }}
                />
                <button onClick={handlePredict} disabled={loading} style={btnS(C.info)}>
                  {loading ? '...' : 'Predict'}
                </button>
              </div>
            </div>

            {predictions && (
              <div>
                <div style={{ fontSize: 11, color: C.muted, marginBottom: 8 }}>
                  Found {predictions.count} related keywords for "{predictions.topic}"
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(predictions.predictions || []).map((p, i) => (
                    <button
                      key={i}
                      onClick={() => { setSearchQuery(p.keyword); setSubView('search'); }}
                      style={{
                        padding: '4px 10px', border: `1px solid ${C.border}`, borderRadius: 12,
                        background: C.bgAlt, color: C.text, fontSize: 11, cursor: 'pointer',
                      }}
                    >
                      {p.keyword} <span style={{ color: C.dim, fontSize: 9 }}>({p.relevance})</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {subView === 'stats' && stats && (
          <div style={{ padding: 16, overflow: 'auto' }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, color: C.muted }}>CACHE STATISTICS</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[
                { label: 'Total Entries', value: stats.total_entries, icon: '📋' },
                { label: 'Unique Keywords', value: stats.unique_keywords, icon: '🏷️' },
                { label: 'Total Accesses', value: stats.total_accesses, icon: '👁️' },
                { label: 'Avg Trust', value: `${Math.round((stats.avg_trust_score || 0) * 100)}%`, icon: '🛡️' },
                { label: 'Stale Entries', value: stats.stale_entries, icon: '⏳' },
                { label: 'LRU Size', value: stats.lru_size, icon: '💾' },
              ].map((s, i) => (
                <div key={i} style={{
                  padding: '12px 14px', background: C.bgAlt, borderRadius: 6,
                  border: `1px solid ${C.border}`,
                }}>
                  <div style={{ fontSize: 18, marginBottom: 4 }}>{s.icon}</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: C.dim }}>{s.label}</div>
                </div>
              ))}
            </div>

            {stats.by_type && Object.keys(stats.by_type).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: C.dim, marginBottom: 6 }}>BY TYPE</div>
                {Object.entries(stats.by_type).map(([type, count]) => (
                  <div key={type} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12 }}>
                    <span><TypeBadge type={type} /></span>
                    <span style={{ color: C.muted }}>{count}</span>
                  </div>
                ))}
              </div>
            )}

            <button onClick={handleCleanup} style={{ ...btnS(C.warn), marginTop: 16 }}>
              🧹 Cleanup Stale Entries
            </button>
          </div>
        )}
      </div>

      {/* ── Right: Detail Panel ───────────────────────────────── */}
      <div style={{ flex: '0 0 380px', overflow: 'auto', padding: '12px 14px', background: C.bg }}>
        {!selected ? (
          <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>
            Select a cached reference to view details and stream content
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <TypeBadge type={selected.source_type} />
              <span style={{
                fontSize: 8, padding: '2px 5px', borderRadius: 3,
                background: selected.validation_status === 'validated' ? C.success
                  : selected.validation_status === 'unreachable' ? C.error : C.border,
                color: '#fff', textTransform: 'uppercase', fontWeight: 700,
              }}>{selected.validation_status}</span>
            </div>

            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{selected.source_name}</div>
            <div style={{ fontSize: 11, color: C.info, wordBreak: 'break-all', marginBottom: 8 }}>
              <a href={selected.source_uri} target="_blank" rel="noreferrer" style={{ color: C.info }}>
                {selected.source_uri}
              </a>
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'center' }}>
              <TrustBar score={selected.trust_score} />
              <span style={{ fontSize: 10, color: C.dim }}>{selected.access_count || 0} accesses</span>
            </div>

            {selected.summary && (
              <div style={{ fontSize: 12, color: C.muted, marginBottom: 10, lineHeight: 1.5,
                background: C.bgAlt, padding: 10, borderRadius: 4, border: `1px solid ${C.border}`,
              }}>
                {selected.summary}
              </div>
            )}

            {/* Keywords */}
            <div style={{ fontSize: 10, fontWeight: 600, color: C.dim, marginBottom: 4, textTransform: 'uppercase' }}>Keywords</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
              {(Array.isArray(selected.keywords) ? selected.keywords : []).map((kw, i) => (
                <span key={i} onClick={() => { setSearchQuery(kw); setSubView('search'); handleSearch(); }}
                  style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 10,
                    background: C.bgDark, color: C.text, cursor: 'pointer',
                    border: `1px solid ${C.border}`,
                  }}>{kw}</span>
              ))}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
              <button onClick={() => handleStream(selected.id)} disabled={streaming} style={btnS(C.success)}>
                {streaming ? '⏳ Streaming...' : '📥 Stream Content'}
              </button>
              <button onClick={() => handleValidate(selected.id)} style={btnS(C.info)}>✓ Validate</button>
              <button onClick={() => handleDelete(selected.id)} style={btnS(C.error)}>🗑 Remove</button>
            </div>

            {/* Streamed content */}
            {streamData && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.dim, marginBottom: 4, textTransform: 'uppercase' }}>
                  Streamed Content
                  {streamData.changed_since_last && (
                    <span style={{ color: C.warn, marginLeft: 8 }}>⚠ Content changed since last fetch</span>
                  )}
                </div>
                <div style={{ fontSize: 10, color: C.dim, marginBottom: 4 }}>
                  Type: {streamData.content_type} | Size: {streamData.size ? `${(streamData.size / 1024).toFixed(1)} KB` : '?'}
                </div>
                <div style={{
                  background: '#111', border: `1px solid ${C.border}`, borderRadius: 4,
                  padding: 10, maxHeight: 400, overflow: 'auto', fontSize: 11, color: C.muted,
                  fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}>
                  {streamData.data
                    ? JSON.stringify(streamData.data, null, 2).substring(0, 5000)
                    : streamData.text
                      ? streamData.text.substring(0, 5000)
                      : streamData.error || 'No content'}
                </div>
              </div>
            )}

            {/* Metadata */}
            {selected.metadata && typeof selected.metadata === 'object' && Object.keys(selected.metadata).length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.dim, marginBottom: 4, textTransform: 'uppercase' }}>Metadata</div>
                <div style={{
                  background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4,
                  padding: 8, fontSize: 10, color: C.muted, fontFamily: 'monospace',
                }}>
                  {Object.entries(selected.metadata).map(([k, v]) => (
                    <div key={k}><span style={{ color: C.info }}>{k}:</span> {typeof v === 'string' ? v : JSON.stringify(v)}</div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ marginTop: 12, fontSize: 10, color: C.dim }}>
              <div>Created: {selected.created_at}</div>
              <div>Last accessed: {selected.last_accessed}</div>
              <div>TTL: {selected.ttl_hours}h | ID: {selected.id}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
