import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = { bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460', accent: '#e94560', accentAlt: '#533483', text: '#eee', muted: '#aaa', dim: '#666', border: '#333', success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3' };

function StatCard({ label, value, sub, color = C.text, icon }) {
  return (
    <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '16px 18px', flex: '1 1 160px', minWidth: 140 }}>
      <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
        {icon && <span style={{ fontSize: 14 }}>{icon}</span>}{label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: C.dim, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function Bar({ value, max, color = C.accent }) {
  return (
    <div style={{ height: 20, background: C.bgDark, borderRadius: 4, overflow: 'hidden', flex: 1 }}>
      <div style={{ height: '100%', width: `${Math.min((value / Math.max(max, 1)) * 100, 100)}%`, background: color, borderRadius: 4, transition: 'width .4s' }} />
    </div>
  );
}

export default function BusinessIntelligenceTab() {
  const [dashboard, setDashboard] = useState(null);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [dRes, tRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/bi/dashboard`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/bi/trends`).then(r => r.ok ? r.json() : null),
    ]);
    if (dRes.status === 'fulfilled') setDashboard(dRes.value);
    if (tRes.status === 'fulfilled') setTrends(tRes.value);
    setLoading(false);
  }, []);

  useEffect(() => { queueMicrotask(refresh); }, [refresh]);

  if (loading && !dashboard) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: C.dim, background: C.bg }}>Loading Business Intelligence...</div>;
  const d = dashboard || {};

  const maxTrend = trends?.days ? Math.max(...trends.days.map(t => t.genesis_keys || 0), 1) : 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg, overflow: 'auto' }}>
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>📈 Business Intelligence</span>
        {d.uptime && <span style={{ fontSize: 11, color: C.dim }}>Uptime: {d.uptime.days}d {d.uptime.hours}h</span>}
        <button onClick={refresh} style={{ marginLeft: 'auto', padding: '4px 12px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#fff', background: C.bgDark }}>↻</button>
      </div>

      <div style={{ padding: 16 }}>
        {/* KPI Cards */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
          <StatCard icon="📄" label="Documents" value={d.documents?.total || 0} sub={`${d.documents?.total_size_mb || 0} MB · ${d.documents?.growth === 'up' ? '📈' : '📉'} ${d.documents?.this_week || 0} this week`} color={C.info} />
          <StatCard icon="💬" label="Conversations" value={d.chats?.total_chats || 0} sub={`${d.chats?.total_messages || 0} messages · avg ${d.chats?.avg_per_chat || 0}/chat`} color={C.accent} />
          <StatCard icon="🔑" label="Genesis Keys" value={d.genesis_keys?.total || 0} sub={`${d.genesis_keys?.today || 0} today · ${d.genesis_keys?.error_rate || 0}% error rate`} color={C.warn} />
          <StatCard icon="🧠" label="Knowledge" value={d.learning?.examples || 0} sub={`${d.learning?.skills || 0} skills · ${((d.learning?.avg_trust || 0) * 100).toFixed(0)}% avg trust`} color={C.success} />
          <StatCard icon="📋" label="Tasks" value={d.tasks?.total || 0} sub={Object.entries(d.tasks?.by_status || {}).map(([k, v]) => `${k}: ${v}`).join(' · ')} color={C.accentAlt} />
        </div>

        {/* 7-day trend */}
        {trends?.days && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '16px 18px', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>📊 7-Day Activity Trend</div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', height: 100 }}>
              {trends.days.map((day, i) => {
                const h = Math.max((day.genesis_keys / maxTrend) * 80, 4);
                return (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <span style={{ fontSize: 10, color: C.text, fontWeight: 700 }}>{day.genesis_keys}</span>
                    <div style={{ width: '100%', height: h, background: C.accent, borderRadius: '4px 4px 0 0', transition: 'height .4s' }} />
                    <span style={{ fontSize: 9, color: C.dim }}>{day.date.slice(5)}</span>
                  </div>
                );
              })}
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 6, alignItems: 'flex-end', height: 40 }}>
              {trends.days.map((day, i) => {
                const h = Math.max((day.documents / Math.max(...trends.days.map(t => t.documents || 0), 1)) * 30, 2);
                return (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ width: '100%', height: h, background: C.info, borderRadius: '4px 4px 0 0', opacity: 0.7 }} />
                  </div>
                );
              })}
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 10, color: C.dim }}>
              <span><span style={{ display: 'inline-block', width: 10, height: 10, background: C.accent, borderRadius: 2, marginRight: 4 }} />Genesis Keys</span>
              <span><span style={{ display: 'inline-block', width: 10, height: 10, background: C.info, borderRadius: 2, marginRight: 4, opacity: 0.7 }} />Documents</span>
            </div>
          </div>
        )}

        {/* Document confidence */}
        {d.documents?.avg_confidence != null && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '16px 18px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Document Confidence</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: d.documents.avg_confidence >= 0.7 ? C.success : C.warn }}>{(d.documents.avg_confidence * 100).toFixed(0)}%</span>
              <Bar value={d.documents.avg_confidence * 100} max={100} color={d.documents.avg_confidence >= 0.7 ? C.success : C.warn} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
