/**
 * LabTab — Grace's Experiment Lab
 * Propose experiments, track 60-day progress, view reports, approve/reject.
 */
import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', info: '#2196f3',
};

export default function LabTab() {
  const [experiments, setExperiments] = useState([]);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newHypothesis, setNewHypothesis] = useState('');
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState(null);

  const fetchExperiments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/reports/experiments`);
      if (res.ok) {
        const data = await res.json();
        setExperiments(data.experiments || []);
      }
    } catch { /* skip */ }
  }, []);

  useEffect(() => { fetchExperiments(); }, [fetchExperiments]);

  const proposeExperiment = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/reports/experiments/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle, description: newDesc,
          hypothesis: newHypothesis, domain: 'general', tracking_days: 60,
        }),
      });
      if (res.ok) {
        setNewTitle(''); setNewDesc(''); setNewHypothesis('');
        fetchExperiments();
      }
    } catch { /* skip */ }
    setCreating(false);
  };

  const approveExperiment = async (id, approved) => {
    try {
      await fetch(`${API_BASE_URL}/api/reports/experiments/${id}/approve?approved=${approved}`, { method: 'POST' });
      fetchExperiments();
    } catch { /* skip */ }
  };

  const startExperiment = async (id) => {
    try {
      await fetch(`${API_BASE_URL}/api/reports/experiments/${id}/start`, { method: 'POST' });
      fetchExperiments();
    } catch { /* skip */ }
  };

  const analyseExperiment = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/reports/experiments/${id}/analyse`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSelected(data);
      }
      fetchExperiments();
    } catch { /* skip */ }
  };

  const statusColor = (s) => {
    if (s === 'proposed') return C.info;
    if (s === 'running' || s === 'tracking') return C.warn;
    if (s === 'approved' || s === 'adopted') return C.success;
    if (s === 'rejected') return C.accent;
    return C.dim;
  };

  return (
    <div style={{ display: 'flex', height: '100%', color: C.text, background: C.bg }}>
      {/* Left: Experiment list + create */}
      <div style={{ flex: 1, borderRight: `1px solid ${C.border}`, overflow: 'auto' }}>
        {/* Create new */}
        <div style={{ padding: 12, borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 8, textTransform: 'uppercase' }}>
            Propose Experiment
          </div>
          <input placeholder="Title" value={newTitle} onChange={e => setNewTitle(e.target.value)}
            style={{ width: '100%', padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
          <input placeholder="What are you testing?" value={newDesc} onChange={e => setNewDesc(e.target.value)}
            style={{ width: '100%', padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
          <input placeholder="Hypothesis: I think this will..." value={newHypothesis} onChange={e => setNewHypothesis(e.target.value)}
            style={{ width: '100%', padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
          <button onClick={proposeExperiment} disabled={creating || !newTitle.trim()} style={{
            width: '100%', padding: 8, border: 'none', borderRadius: 4, cursor: 'pointer',
            background: C.success, color: '#fff', fontSize: 12, fontWeight: 700,
          }}>{creating ? '...' : '🧪 Propose Experiment (60 days)'}</button>
        </div>

        {/* List */}
        <div style={{ padding: '8px 0' }}>
          {experiments.length === 0 && (
            <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>
              No experiments yet. Propose one above.
            </div>
          )}
          {experiments.map(exp => (
            <div key={exp.id} onClick={() => setSelected(exp)} style={{
              padding: '10px 14px', borderBottom: `1px solid ${C.border}`, cursor: 'pointer',
              background: selected?.id === exp.id ? C.bgDark : 'transparent',
              borderLeft: `3px solid ${statusColor(exp.status)}`,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{exp.title}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 10, color: C.dim }}>
                <span style={{ color: statusColor(exp.status), fontWeight: 700, textTransform: 'uppercase' }}>{exp.status}</span>
                <span>{exp.domain}</span>
                <span>{exp.tracking_days}d tracking</span>
                <span>{exp.checkpoints || 0} checkpoints</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Detail */}
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        {!selected ? (
          <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🧪</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Grace Lab</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>
              Propose experiments. Grace tracks them for 60 days.
              Get a report. Say aye or nay.
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{selected.title}</div>
            <div style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 10,
              background: statusColor(selected.status), color: '#fff', fontWeight: 700,
              textTransform: 'uppercase', marginBottom: 12,
            }}>{selected.status}</div>

            {selected.description && (
              <div style={{ fontSize: 13, color: C.muted, marginBottom: 8 }}>{selected.description}</div>
            )}
            {selected.hypothesis && (
              <div style={{ fontSize: 12, color: C.info, marginBottom: 12, fontStyle: 'italic' }}>
                Hypothesis: {selected.hypothesis}
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
              {selected.status === 'proposed' && (
                <button onClick={() => startExperiment(selected.id)} style={{
                  padding: '6px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                  background: C.info, color: '#fff', fontSize: 11, fontWeight: 700,
                }}>▶ Start Tracking</button>
              )}
              {(selected.status === 'running' || selected.status === 'tracking') && (
                <button onClick={() => analyseExperiment(selected.id)} style={{
                  padding: '6px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                  background: C.warn, color: '#fff', fontSize: 11, fontWeight: 700,
                }}>📊 Analyse Now</button>
              )}
              {selected.status === 'awaiting_approval' && (
                <>
                  <button onClick={() => approveExperiment(selected.id, true)} style={{
                    padding: '6px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                    background: C.success, color: '#fff', fontSize: 11, fontWeight: 700,
                  }}>✅ Approve (Aye)</button>
                  <button onClick={() => approveExperiment(selected.id, false)} style={{
                    padding: '6px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                    background: C.accent, color: '#fff', fontSize: 11, fontWeight: 700,
                  }}>❌ Reject (Nay)</button>
                </>
              )}
            </div>

            {/* Analysis results */}
            {selected.comparisons && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 6, textTransform: 'uppercase' }}>Results</div>
                {selected.comparisons.map((c, i) => (
                  <div key={i} style={{
                    display: 'flex', justifyContent: 'space-between', padding: '6px 10px',
                    background: C.bgAlt, borderRadius: 4, marginBottom: 4, fontSize: 12,
                    borderLeft: `3px solid ${c.improved ? C.success : C.accent}`,
                  }}>
                    <span>{c.metric}</span>
                    <span style={{ color: c.improved ? C.success : C.accent }}>
                      {c.delta_percent > 0 ? '+' : ''}{c.delta_percent}%
                    </span>
                  </div>
                ))}
                <div style={{ marginTop: 8, fontSize: 11, color: C.dim }}>
                  Recommendation: {selected.recommendation}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
