import BackendPanel from './BackendPanel';
import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL, API_V2 } from '../config/api';

const C = { bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460', accent: '#e94560', accentAlt: '#533483', text: '#eee', muted: '#aaa', dim: '#666', border: '#333', success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3' };

function Gauge({ label, value, max = 100, icon }) {
  const pct = Math.min((value / max) * 100, 100);
  const color = pct > 80 ? C.error : pct > 60 ? C.warn : C.success;
  return (
    <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16, textAlign: 'center', flex: '1 1 140px' }}>
      <div style={{ fontSize: 11, color: C.muted, marginBottom: 6 }}>{icon} {label}</div>
      <div style={{ fontSize: 32, fontWeight: 800, color }}>{pct.toFixed(1)}%</div>
      <div style={{ height: 6, background: C.bgDark, borderRadius: 3, marginTop: 8 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

function ServiceDot({ status }) {
  const color = { live: C.success, down: C.error, configured: C.info, not_configured: C.dim }[status] || C.dim;
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color }} />;
}

export default function SystemHealthTab() {
  const [health, setHealth] = useState(null);
  const [procs, setProcs] = useState([]);
  const [graceState, setGraceState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fullData, setFullData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/health/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [hRes, pRes, gRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/system-health/dashboard`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/system-health/processes`).then(r => r.ok ? r.json() : null),
      fetch(API_V2.graceState(), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }).then(r => r.ok ? r.json() : null).then(d => d?.data ?? d),
    ]);
    if (hRes.status === 'fulfilled') setHealth(hRes.value);
    if (pRes.status === 'fulfilled') setProcs(pRes.value?.processes || []);
    if (gRes.status === 'fulfilled') setGraceState(gRes.value);
    setLoading(false);
  }, []);

  useEffect(() => { queueMicrotask(refresh); const i = setInterval(refresh, 10000); return () => clearInterval(i); }, [refresh]);

  if (loading && !health) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: C.dim, background: C.bg }}>Loading System Health...</div>;
  const h = health || {};
  const r = h.resources || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg, overflow: 'auto' }}>
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>🏥 System Health</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: { healthy: C.success, degraded: C.warn, critical: C.error }[h.overall] || C.dim }}>{(h.overall || 'unknown').toUpperCase()}</span>
        <button onClick={refresh} style={{ marginLeft: 'auto', padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#fff', background: C.bgDark }}>↻</button>
      </div>

      <div style={{ padding: 16 }}>
        {/* Grace State — single view of Ouroboros, mirror, health */}
        {graceState && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>🧠 Grace State</div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}>
              <div>
                <span style={{ color: C.muted }}>Ouroboros: </span>
                <span style={{ fontWeight: 600 }}>{graceState.ouroboros?.running ? 'Running' : 'Stopped'}</span>
                <span style={{ color: C.dim }}> · cycles {graceState.ouroboros?.cycle_count ?? 0} · last {graceState.ouroboros?.last_result ?? '—'}</span>
              </div>
              <div>
                <span style={{ color: C.muted }}>Mirror: </span>
                <span style={{ fontWeight: 600 }}>{graceState.mirror?.problems_observed ?? 0} issues</span>
                {Array.isArray(graceState.mirror?.problems) && graceState.mirror.problems.length > 0 && (
                  <span style={{ color: C.warn }}> · {graceState.mirror.problems.slice(0, 2).map(p => p.component).join(', ')}</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resource gauges */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
          <Gauge label="CPU" value={r.cpu_total || 0} icon="⚡" />
          <Gauge label="Memory" value={r.memory_percent || 0} icon="🧠" />
          <Gauge label="Disk" value={r.disk_percent || 0} icon="💾" />
        </div>

        <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
          {/* Services */}
          <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>🔌 Services</div>
            {Object.entries(h.services || {}).map(([name, info]) => (
              <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: `1px solid ${C.border}` }}>
                <ServiceDot status={info.status} />
                <span style={{ fontSize: 12, flex: 1, textTransform: 'capitalize' }}>{name}</span>
                <span style={{ fontSize: 10, color: { live: C.success, down: C.error }[info.status] || C.dim, fontWeight: 700, textTransform: 'uppercase' }}>{info.status}</span>
              </div>
            ))}
          </div>

          {/* Organs */}
          <div style={{ flex: 1, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>🫀 Organs of Grace</div>
            {(h.organs || []).map((o, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span>{o.name}</span>
                  <span style={{ fontWeight: 700, color: o.progress >= 50 ? C.success : C.warn }}>{o.progress}%</span>
                </div>
                <div style={{ height: 6, background: C.bgDark, borderRadius: 3 }}>
                  <div style={{ height: '100%', width: `${o.progress}%`, background: o.progress >= 50 ? C.success : C.warn, borderRadius: 3 }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CPU per core */}
        {r.cpu_per_core && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>CPU Per Core ({r.cpu_cores})</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(55px, 1fr))', gap: 6 }}>
              {r.cpu_per_core.map((v, i) => (
                <div key={i} style={{ textAlign: 'center', padding: 6, background: C.bg, borderRadius: 4, border: `1px solid ${C.border}` }}>
                  <div style={{ fontSize: 9, color: C.dim }}>#{i}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: v > 80 ? C.error : v > 50 ? C.warn : C.success }}>{v.toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top processes */}
        {procs.length > 0 && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Top Processes</div>
            {procs.slice(0, 10).map((p, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, fontSize: 11, padding: '4px 0', borderBottom: `1px solid ${C.border}` }}>
                <span style={{ color: C.dim, width: 40 }}>{p.pid}</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                <span style={{ color: C.warn }}>{(p.cpu_percent || 0).toFixed(1)}% CPU</span>
                <span style={{ color: C.info }}>{(p.memory_percent || 0).toFixed(1)}% MEM</span>
              </div>
            ))}
          </div>
        )}

        {/* Resource details */}
        <div style={{ display: 'flex', gap: 16, marginTop: 16, fontSize: 12 }}>
          <div style={{ color: C.muted }}>Memory: {r.memory_used_gb || 0} / {r.memory_total_gb || 0} GB</div>
          <div style={{ color: C.muted }}>Disk: {r.disk_used_gb || 0} / {r.disk_total_gb || 0} GB</div>
          <div style={{ color: C.muted }}>Cores: {r.cpu_cores || 0}</div>
        </div>

        {/* Full aggregation: extra sections */}
        {fullData?.diagnostic_sensors && (
          <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Diagnostic Sensors</div>
            {typeof fullData.diagnostic_sensors === 'object' ? (
              Object.entries(fullData.diagnostic_sensors).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                  <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.diagnostic_sensors)}</span>
            )}
          </div>
        )}
        {fullData?.diagnostic_healing && (
          <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Diagnostic Healing</div>
            {typeof fullData.diagnostic_healing === 'object' ? (
              Object.entries(fullData.diagnostic_healing).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                  <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.diagnostic_healing)}</span>
            )}
          </div>
        )}
        {fullData?.diagnostic_trends && (
          <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>Diagnostic Trends</div>
            {typeof fullData.diagnostic_trends === 'object' ? (
              Object.entries(fullData.diagnostic_trends).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                  <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.diagnostic_trends)}</span>
            )}
          </div>
        )}

        <BackendPanel prefixes={['/health', '/diagnostic', '/monitoring', '/api/system-health']} label="Health & Diagnostics" />
      </div>
    </div>
  );
}
