import BackendPanel from './BackendPanel';
import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = { bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460', accent: '#e94560', accentAlt: '#533483', text: '#eee', muted: '#aaa', dim: '#666', border: '#333', success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3' };
const btn = (bg = C.accentAlt) => ({ padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#fff', background: bg });

export default function LearningHealingTab() {
  const [dashboard, setDashboard] = useState(null);
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [learnTopic, setLearnTopic] = useState('');
  const [learnResult, setLearnResult] = useState(null);
  const [learning, setLearning] = useState(false);
  const [healingAction, setHealingAction] = useState(null);
  const [notification, setNotification] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [fullData, setFullData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/tabs/learn-heal/full`).then(r => r.ok ? r.json() : null).then(setFullData).catch(() => {});
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [dRes, sRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/learn-heal/dashboard`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/learn-heal/skills`).then(r => r.ok ? r.json() : null),
    ]);
    if (dRes.status === 'fulfilled') setDashboard(dRes.value);
    if (sRes.status === 'fulfilled') setSkills(sRes.value?.skills || []);
    setLoading(false);
  }, []);

  useEffect(() => { queueMicrotask(refresh); }, [refresh]);

  const triggerLearn = async () => {
    if (!learnTopic.trim()) return;
    setLearning(true); setLearnResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/learn-heal/learn`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: learnTopic, method: 'kimi' }),
      });
      if (res.ok) setLearnResult(await res.json());
    } catch { /* silent */ }
    finally { setLearning(false); }
  };

  const triggerHeal = async (action) => {
    setHealingAction(action);
    try {
      await fetch(`${API_BASE_URL}/api/learn-heal/heal`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      setNotification(`Healing: ${action}`);
      setTimeout(() => setNotification(null), 3000);
    } catch { /* silent */ }
    finally { setHealingAction(null); }
  };

  const d = dashboard || {};
  const l = d.learning || {};
  const hs = d.health_snapshot || {};
  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊', title: 'Learning and healing dashboard and health snapshot' },
    { id: 'learn', label: 'Learn', icon: '🧠', title: 'Trigger self-learning on a topic' },
    { id: 'heal', label: 'Heal', icon: '🔧', title: 'Trigger self-healing actions' },
    { id: 'skills', label: 'Skills', icon: '🎯', title: 'View and manage learned skills' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>
      <div style={{ borderBottom: `1px solid ${C.border}`, background: C.bgAlt, padding: '0 16px', display: 'flex', alignItems: 'stretch' }}>
        <span style={{ fontSize: 15, fontWeight: 700, padding: '12px 16px 12px 0' }}>🧬 Learning & Healing</span>
        {tabs.map(t => (
          <button key={t.id} type="button" title={t.title || t.label} onClick={() => setActiveTab(t.id)} style={{
            padding: '10px 16px', border: 'none', background: 'none', cursor: 'pointer',
            color: activeTab === t.id ? C.accent : C.muted,
            borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
            fontSize: 13, fontWeight: activeTab === t.id ? 700 : 500, display: 'flex', alignItems: 'center', gap: 6,
          }}><span>{t.icon}</span> {t.label}</button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: C.dim }}>
          {hs.status && <span style={{ color: hs.status === 'healthy' ? C.success : C.warn }}>Health: {hs.status}</span>}
          <span>CPU {hs.cpu?.toFixed(0)}%</span>
          <span>MEM {hs.memory?.toFixed(0)}%</span>
          <button onClick={refresh} style={{ ...btn(C.bgDark), fontSize: 10 }}>↻</button>
        </div>
      </div>

      {notification && <div style={{ padding: '6px 16px', background: C.success + '30', border: `1px solid ${C.success}`, fontSize: 12, color: C.success, textAlign: 'center' }}>{notification}</div>}

      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {loading && !dashboard ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>Loading...</div> : (
          <>
            {activeTab === 'overview' && (
              <>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
                  {[
                    { label: 'Examples', val: l.examples?.total || 0, sub: `${((l.examples?.avg_trust || 0) * 100).toFixed(0)}% trust`, color: C.accent, icon: '🧠' },
                    { label: 'Patterns', val: l.patterns?.total || 0, sub: `${((l.patterns?.avg_success || 0) * 100).toFixed(0)}% success`, color: C.info, icon: '📐' },
                    { label: 'Episodes', val: l.episodes || 0, color: C.warn, icon: '📖' },
                    { label: 'Skills', val: l.procedures?.total || 0, sub: `${((l.procedures?.avg_success || 0) * 100).toFixed(0)}% success`, color: C.success, icon: '🎯' },
                    { label: 'Last 24h', val: l.last_24h || 0, sub: 'new examples', color: C.accentAlt, icon: '⏰' },
                  ].map((s, i) => (
                    <div key={i} style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', flex: '1 1 140px', minWidth: 130 }}>
                      <div style={{ fontSize: 10, color: C.muted, marginBottom: 6 }}>{s.icon} {s.label}</div>
                      <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.val}</div>
                      {s.sub && <div style={{ fontSize: 10, color: C.dim, marginTop: 4 }}>{s.sub}</div>}
                    </div>
                  ))}
                </div>

                {/* Trust distribution */}
                {l.trust_distribution && (
                  <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Trust Distribution</div>
                    {Object.entries(l.trust_distribution).map(([level, count]) => (
                      <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                        <span style={{ fontSize: 12, width: 60, color: { high: C.success, medium: C.warn, low: C.error }[level] }}>{level}</span>
                        <div style={{ flex: 1, height: 8, background: C.bgDark, borderRadius: 4 }}>
                          <div style={{ height: '100%', width: `${(count / Math.max(l.examples?.total || 1, 1)) * 100}%`, background: { high: C.success, medium: C.warn, low: C.error }[level], borderRadius: 4 }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 700, width: 40, textAlign: 'right' }}>{count}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Top types */}
                {l.top_types?.length > 0 && (
                  <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px' }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Learning by Type</div>
                    {l.top_types.map((t, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>
                        <span style={{ color: C.muted }}>{t.type}</span>
                        <span style={{ fontWeight: 700 }}>{t.count}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Full aggregation: extra sections */}
                {fullData?.ml_components && (
                  <div style={{ background: '#16213e', border: '1px solid #333', borderRadius: 8, padding: '12px 16px', marginTop: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#aaa', marginBottom: 8 }}>ML Components</div>
                    {typeof fullData.ml_components === 'object' ? (
                      Object.entries(fullData.ml_components).map(([k, v]) => (
                        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #33333344', fontSize: 11 }}>
                          <span style={{ color: '#aaa' }}>{k.replace(/_/g, ' ')}</span>
                          <span style={{ color: '#eee', fontWeight: 600 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                        </div>
                      ))
                    ) : (
                      <span style={{ fontSize: 11, color: '#eee' }}>{String(fullData.ml_components)}</span>
                    )}
                  </div>
                )}
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
              </>
            )}

            {activeTab === 'learn' && (
              <div>
                <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: '16px', marginBottom: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>🧠 Teach Grace</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input placeholder="What should Grace learn about?" value={learnTopic} onChange={e => setLearnTopic(e.target.value)} onKeyDown={e => e.key === 'Enter' && triggerLearn()}
                      style={{ flex: 1, padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 13, outline: 'none' }} />
                    <button onClick={triggerLearn} disabled={learning} style={{ ...btn(C.accent), opacity: learning ? 0.5 : 1 }}>
                      {learning ? '⏳ Learning...' : '🧠 Learn'}
                    </button>
                  </div>
                </div>
                {learnResult && (
                  <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16 }}>
                    {learnResult.knowledge ? (
                      <>
                        <div style={{ fontSize: 11, color: C.success, marginBottom: 8 }}>✅ Knowledge acquired and ingested</div>
                        <pre style={{ margin: 0, fontSize: 12, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.6, maxHeight: 400, overflow: 'auto' }}>{learnResult.knowledge}</pre>
                      </>
                    ) : (
                      <pre style={{ margin: 0, fontSize: 11, color: C.muted }}>{JSON.stringify(learnResult, null, 2)}</pre>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'heal' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {(d.healing?.available_actions || []).map(a => (
                  <button key={a.id} onClick={() => triggerHeal(a.id)} disabled={healingAction === a.id}
                    style={{ ...btn(C.bgDark), padding: '16px', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 6, opacity: healingAction === a.id ? 0.5 : 1, borderRadius: 8, border: `1px solid ${C.border}` }}>
                    <span style={{ fontSize: 14, fontWeight: 700 }}>{a.name}</span>
                    <span style={{ fontSize: 11, color: C.dim, fontWeight: 400 }}>Severity: {a.severity}</span>
                  </button>
                ))}
              </div>
            )}

            {activeTab === 'skills' && (
              <div>
                {skills.length === 0 ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>No skills learned yet</div>
                 : skills.map((s, i) => (
                  <div key={i} style={{ padding: '10px 14px', marginBottom: 6, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 16 }}>🎯</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
                      <div style={{ fontSize: 10, color: C.dim }}>{s.goal} · {s.type} · used {s.usage}x</div>
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: (s.trust || 0) >= 0.7 ? C.success : C.warn }}>{((s.trust || 0) * 100).toFixed(0)}%</span>
                    <span style={{ fontSize: 10, color: C.dim }}>{((s.success || 0) * 100).toFixed(0)}% success</span>
                  </div>
                ))}

                <BackendPanel prefixes={['/training', '/autonomous-learning', '/learning-memory', '/learning-efficiency', '/proactive-learning', '/ml-intelligence', '/sandbox-lab', '/api/learn-heal']} label="Learning & ML" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
