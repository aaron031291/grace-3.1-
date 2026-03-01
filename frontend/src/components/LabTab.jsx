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

  // Horizon planner state
  const [activePanel, setActivePanel] = useState('experiments'); // experiments, goals, sandbox, gaps
  const [goals, setGoals] = useState([]);
  const [goalProgress, setGoalProgress] = useState(null);
  const [sandboxSession, setSandboxSession] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [sandboxResult, setSandboxResult] = useState(null);
  const [newGoalTitle, setNewGoalTitle] = useState('');
  const [newGoalTarget, setNewGoalTarget] = useState('');
  const [goalBranch, setGoalBranch] = useState('internal');
  const [sandboxTask, setSandboxTask] = useState('');
  const [busy, setBusy] = useState(false);

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

  // ── Horizon Planner functions ────────────────────────────────────────
  const fetchGoals = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/goals`);
      if (res.ok) { const data = await res.json(); setGoals(data.goals || []); }
    } catch { /* skip */ }
  }, []);

  const createGoal = async () => {
    if (!newGoalTitle.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/goals`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newGoalTitle, description: newGoalTarget,
          target_outcome: newGoalTarget || newGoalTitle,
          target_improvement_pct: 30, timeline_days: 60,
          branch: goalBranch, use_consensus: true,
        }),
      });
      if (res.ok) { setNewGoalTitle(''); setNewGoalTarget(''); fetchGoals(); }
    } catch { /* skip */ }
    setBusy(false);
  };

  const activateGoal = async (goalId) => {
    try {
      await fetch(`${API_BASE_URL}/api/horizon/goals/${goalId}/activate`, { method: 'POST' });
      fetchGoals();
    } catch { /* skip */ }
  };

  const checkProgress = async (goalId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/goals/${goalId}/progress`);
      if (res.ok) setGoalProgress(await res.json());
    } catch { /* skip */ }
  };

  const fetchGaps = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/gaps`);
      if (res.ok) setGaps(await res.json());
    } catch { /* skip */ }
    setBusy(false);
  };

  const createSandbox = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/sandbox/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch: goalBranch }),
      });
      if (res.ok) setSandboxSession(await res.json());
    } catch { /* skip */ }
    setBusy(false);
  };

  const runSandboxDiagnostics = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/sandbox/diagnostics`, { method: 'POST' });
      if (res.ok) setSandboxResult(await res.json());
    } catch { /* skip */ }
    setBusy(false);
  };

  const runSandboxExperiment = async () => {
    if (!sandboxTask.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/sandbox/experiment`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: sandboxTask, use_consensus: true }),
      });
      if (res.ok) { setSandboxResult(await res.json()); setSandboxTask(''); }
    } catch { /* skip */ }
    setBusy(false);
  };

  const runSandboxLearning = async (focus) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/horizon/sandbox/learn`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focus }),
      });
      if (res.ok) setSandboxResult(await res.json());
    } catch { /* skip */ }
    setBusy(false);
  };

  useEffect(() => { if (activePanel === 'goals') fetchGoals(); }, [activePanel, fetchGoals]);

  const statusColor = (s) => {
    if (s === 'proposed') return C.info;
    if (s === 'running' || s === 'tracking') return C.warn;
    if (s === 'approved' || s === 'adopted') return C.success;
    if (s === 'rejected') return C.accent;
    return C.dim;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>
      {/* Panel switcher */}
      <div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
        {[
          { id: 'experiments', label: 'Experiments', icon: '🧪' },
          { id: 'goals', label: 'Horizon Goals', icon: '🎯' },
          { id: 'sandbox', label: 'Sandbox', icon: '🏗️' },
          { id: 'gaps', label: 'Integration Gaps', icon: '🔌' },
        ].map(p => (
          <button key={p.id} onClick={() => setActivePanel(p.id)} style={{
            padding: '8px 16px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
            background: activePanel === p.id ? C.bgDark : 'transparent',
            color: activePanel === p.id ? C.text : C.dim,
            borderBottom: activePanel === p.id ? `2px solid ${C.accent}` : '2px solid transparent',
          }}>{p.icon} {p.label}</button>
        ))}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

      {/* ── Experiments Panel ─────────────────────────────────── */}
      {activePanel === 'experiments' && <>
      <div style={{ flex: 1, borderRight: `1px solid ${C.border}`, overflow: 'auto' }}>
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
      </>}

      {/* ── Horizon Goals Panel ──────────────────────────────── */}
      {activePanel === 'goals' && <>
      <div style={{ flex: 1, borderRight: `1px solid ${C.border}`, overflow: 'auto' }}>
        <div style={{ padding: 12, borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 8, textTransform: 'uppercase' }}>Set Long-Term Goal</div>
          <input placeholder="Goal title (e.g. 30% faster response)" value={newGoalTitle} onChange={e => setNewGoalTitle(e.target.value)}
            style={{ width: '100%', padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
          <input placeholder="Target outcome to measure" value={newGoalTarget} onChange={e => setNewGoalTarget(e.target.value)}
            style={{ width: '100%', padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, marginBottom: 6, outline: 'none', boxSizing: 'border-box' }} />
          <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
            {['internal', 'exploration'].map(b => (
              <button key={b} onClick={() => setGoalBranch(b)} style={{
                flex: 1, padding: 6, border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
                background: goalBranch === b ? (b === 'internal' ? C.info : C.warn) : C.bgAlt,
                color: goalBranch === b ? '#fff' : C.dim,
              }}>{b === 'internal' ? '🔧 Internal (Fix Grace)' : '🔬 Exploration (Research)'}</button>
            ))}
          </div>
          <button onClick={createGoal} disabled={busy || !newGoalTitle.trim()} style={{
            width: '100%', padding: 8, border: 'none', borderRadius: 4, cursor: 'pointer',
            background: C.success, color: '#fff', fontSize: 12, fontWeight: 700, opacity: busy ? 0.5 : 1,
          }}>{busy ? 'Creating...' : '🎯 Create Goal (60-day, 30% target)'}</button>
        </div>
        <div style={{ padding: '8px 0' }}>
          {goals.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>No goals yet. Set one above.</div>}
          {goals.map(g => (
            <div key={g.id} onClick={() => checkProgress(g.id)} style={{
              padding: '10px 14px', borderBottom: `1px solid ${C.border}`, cursor: 'pointer',
              borderLeft: `3px solid ${g.status === 'active' ? C.success : g.status === 'achieved' ? C.info : C.dim}`,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{g.title}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 10, color: C.dim }}>
                <span style={{ color: g.branch === 'internal' ? C.info : C.warn, fontWeight: 700 }}>{g.branch}</span>
                <span>{g.status}</span>
                <span>{g.timeline_days}d</span>
                <span>{g.tasks} tasks</span>
                <span>{g.milestones} milestones</span>
              </div>
              {g.status === 'draft' && (
                <button onClick={e => { e.stopPropagation(); activateGoal(g.id); }} style={{
                  marginTop: 6, padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
                  background: C.info, color: '#fff', fontSize: 10, fontWeight: 700,
                }}>▶ Activate</button>
              )}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        {!goalProgress ? (
          <div style={{ padding: 40, textAlign: 'center', color: C.dim }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🎯</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Horizon Goals</div>
            <div style={{ fontSize: 12, marginTop: 8 }}>Set a measurable goal. Grace reverse-engineers it into milestones and tasks. 30% minimum improvement.</div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{goalProgress.title}</div>
            <div style={{ fontSize: 11, color: C.dim, marginBottom: 12 }}>
              {goalProgress.timeline?.days_elapsed}d elapsed / {goalProgress.timeline?.days_remaining}d remaining
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.success }}>{goalProgress.tasks?.completion_pct}%</div>
                <div style={{ fontSize: 10, color: C.dim }}>Tasks Done</div>
              </div>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.info }}>{goalProgress.tasks?.completed || 0}</div>
                <div style={{ fontSize: 10, color: C.dim }}>Completed</div>
              </div>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.warn }}>{goalProgress.tasks?.measuring || 0}</div>
                <div style={{ fontSize: 10, color: C.dim }}>Measuring</div>
              </div>
            </div>
            {goalProgress.milestones?.map((ms, i) => (
              <div key={ms.id || i} style={{ background: C.bgAlt, padding: 10, borderRadius: 6, marginBottom: 8, borderLeft: `3px solid ${ms.progress_pct >= 100 ? C.success : C.info}` }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{ms.title}</div>
                <div style={{ fontSize: 11, color: C.dim }}>Target: {ms.target} | Progress: {ms.progress_pct?.toFixed(0)}%</div>
                <div style={{ height: 4, background: C.border, borderRadius: 2, marginTop: 4 }}>
                  <div style={{ height: 4, background: C.success, borderRadius: 2, width: `${Math.min(100, ms.progress_pct || 0)}%` }} />
                </div>
              </div>
            ))}
            {Object.entries(goalProgress.improvements || {}).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: C.bgAlt, borderRadius: 4, marginBottom: 4, fontSize: 12, borderLeft: `3px solid ${v.meets_target ? C.success : C.accent}` }}>
                <span>{k.replace(/_/g, ' ')}</span>
                <span style={{ color: v.meets_target ? C.success : C.accent }}>{v.delta_pct > 0 ? '+' : ''}{v.delta_pct}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
      </>}

      {/* ── Sandbox Panel ────────────────────────────────────── */}
      {activePanel === 'sandbox' && <>
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>🏗️ Sandbox Mirror</div>
        <div style={{ fontSize: 12, color: C.muted, marginBottom: 16 }}>
          Mirror Grace's full backend. Test, experiment, learn — nothing touches production.
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <button onClick={createSandbox} disabled={busy} style={{ padding: '8px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: C.info, color: '#fff', fontSize: 12, fontWeight: 700 }}>
            {busy ? '...' : '🪞 Create Sandbox'}
          </button>
          <button onClick={runSandboxDiagnostics} disabled={busy} style={{ padding: '8px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: C.warn, color: '#fff', fontSize: 12, fontWeight: 700 }}>
            {busy ? '...' : '🔍 Run Diagnostics'}
          </button>
          <button onClick={() => runSandboxLearning('internal')} disabled={busy} style={{ padding: '8px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: '#9c27b0', color: '#fff', fontSize: 12, fontWeight: 700 }}>
            🔧 Internal Learning
          </button>
          <button onClick={() => runSandboxLearning('exploration')} disabled={busy} style={{ padding: '8px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: '#ff6b35', color: '#fff', fontSize: 12, fontWeight: 700 }}>
            🔬 Exploration
          </button>
        </div>

        {sandboxSession && (
          <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, marginBottom: 12, fontSize: 12, border: `1px solid ${C.border}` }}>
            <div style={{ fontWeight: 700, color: C.success, marginBottom: 4 }}>Session: {sandboxSession.session_id}</div>
            <div style={{ color: C.dim }}>Components mirrored: {sandboxSession.components_mirrored}</div>
            <div style={{ color: C.dim }}>Health: {sandboxSession.health_baseline}</div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input placeholder="Task for consensus experiment (e.g. 'fix broken event bridge')" value={sandboxTask} onChange={e => setSandboxTask(e.target.value)}
            style={{ flex: 1, padding: 8, background: C.bgAlt, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none' }} />
          <button onClick={runSandboxExperiment} disabled={busy || !sandboxTask.trim()} style={{ padding: '8px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: C.accent, color: '#fff', fontSize: 12, fontWeight: 700 }}>
            {busy ? '...' : '🤝 Consensus'}
          </button>
        </div>

        {sandboxResult && (
          <div style={{ background: C.bgAlt, padding: 12, borderRadius: 6, fontSize: 12, border: `1px solid ${C.border}`, maxHeight: 400, overflowY: 'auto' }}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Result</div>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: C.muted, fontSize: 11 }}>
              {JSON.stringify(sandboxResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
      </>}

      {/* ── Integration Gaps Panel ───────────────────────────── */}
      {activePanel === 'gaps' && <>
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>🔌 Integration Gaps</div>
          <button onClick={fetchGaps} disabled={busy} style={{ padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', background: C.info, color: '#fff', fontSize: 12, fontWeight: 700 }}>
            {busy ? '...' : '🔍 Scan'}
          </button>
        </div>

        {!gaps ? (
          <div style={{ padding: 40, textAlign: 'center', color: C.dim, fontSize: 12 }}>Click Scan to detect integration gaps</div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.accent }}>{gaps.total_gaps}</div>
                <div style={{ fontSize: 10, color: C.dim }}>Total Gaps</div>
              </div>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.accent }}>{gaps.by_severity?.high || 0}</div>
                <div style={{ fontSize: 10, color: C.dim }}>High</div>
              </div>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.warn }}>{gaps.by_severity?.medium || 0}</div>
                <div style={{ fontSize: 10, color: C.dim }}>Medium</div>
              </div>
              <div style={{ background: C.bgAlt, padding: 10, borderRadius: 6, flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.dim }}>{gaps.by_severity?.low || 0}</div>
                <div style={{ fontSize: 10, color: C.dim }}>Low</div>
              </div>
            </div>

            {gaps.high_priority?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: C.accent, marginBottom: 6, textTransform: 'uppercase' }}>High Priority</div>
                {gaps.high_priority.map((g, i) => (
                  <div key={i} style={{ padding: '8px 10px', background: C.bgAlt, borderRadius: 4, marginBottom: 4, fontSize: 12, borderLeft: `3px solid ${C.accent}` }}>
                    <div style={{ fontWeight: 600 }}>[{g.component}] {g.description}</div>
                    <div style={{ fontSize: 11, color: C.info, marginTop: 4 }}>{g.fix_suggestion}</div>
                  </div>
                ))}
              </div>
            )}

            <div style={{ fontSize: 12, fontWeight: 700, color: C.muted, marginBottom: 6, textTransform: 'uppercase' }}>By Type</div>
            {Object.entries(gaps.by_type || {}).map(([type, count]) => (
              <div key={type} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: C.bgAlt, borderRadius: 4, marginBottom: 4, fontSize: 12 }}>
                <span>{type.replace(/_/g, ' ')}</span>
                <span style={{ fontWeight: 700 }}>{count}</span>
              </div>
            ))}
          </>
        )}
      </div>
      </>}

      </div>
    </div>
  );
}
