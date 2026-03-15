import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';
import { useTabData } from '../hooks/useTabData';

const C = {
  bg: '#0a0a1a', bgAlt: '#0d0d22', bgDark: '#08081a',
  accent: '#e94560', accentAlt: '#3b82f6',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#1a1a2e',
  success: '#10b981', warn: '#f59e0b', error: '#ef4444', info: '#3b82f6',
};

const DASHBOARD_SCHEMA = {
  last_run: null,
  total_runs: 0,
  pass_rate: 0,
  total_tests_executed: 0,
  suites_available: 0,
  scheduled_jobs: 0,
  chaos_experiments: 0,
  spindle_status: 'unknown',
};

const btn = (bg = C.accentAlt) => ({
  padding: '8px 16px', border: 'none', borderRadius: 6, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});

const card = {
  background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16,
};

const VIEWS = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'run', label: 'Run Tests', icon: '▶️' },
  { id: 'history', label: 'History', icon: '📋' },
  { id: 'schedule', label: 'Schedule', icon: '⏰' },
  { id: 'chaos', label: 'Chaos Lab', icon: '💥' },
  { id: 'spindle', label: 'Spindle Bridge', icon: '🔬' },
];

export default function TestingTab() {
  const [activeView, setActiveView] = useState('dashboard');

  return (
    <div style={{ display: 'flex', height: '100%', background: C.bg, color: C.text, overflow: 'hidden' }}>
      {/* Left Nav */}
      <div style={{ width: 220, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}`, background: C.bgDark, flexShrink: 0 }}>
        <div style={{ padding: 16, borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
          <span style={{ fontSize: 14, fontWeight: 800, color: C.accent, letterSpacing: 1, textTransform: 'uppercase' }}>🧪 Testing</span>
        </div>
        <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {VIEWS.map(v => (
            <button
              key={v.id} onClick={() => setActiveView(v.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
                background: activeView === v.id ? '#1a1a3a' : 'transparent',
                border: 'none', borderRadius: 6, cursor: 'pointer',
                color: activeView === v.id ? C.text : C.muted,
                textAlign: 'left', fontSize: 13, fontWeight: activeView === v.id ? 700 : 500,
                borderLeft: activeView === v.id ? `3px solid ${C.accent}` : '3px solid transparent',
              }}
            >
              <span style={{ fontSize: 16 }}>{v.icon}</span>
              <span>{v.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 24 }}>
        {activeView === 'dashboard' && <DashboardView />}
        {activeView === 'run' && <RunTestsView />}
        {activeView === 'history' && <HistoryView />}
        {activeView === 'schedule' && <ScheduleView />}
        {activeView === 'chaos' && <ChaosView />}
        {activeView === 'spindle' && <SpindleBridgeView />}
      </div>
    </div>
  );
}

// ─── Dashboard ───────────────────────────────────────────────────
function DashboardView() {
  const { data: dash, loading, refresh } = useTabData('/api/testing/dashboard', DASHBOARD_SCHEMA);
  if (loading && !dash) return <div style={{ color: C.dim }}>Loading dashboard...</div>;
  const d = dash || {};
  const lr = d.last_run;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>Testing Dashboard</h2>
        <button onClick={refresh} style={btn(C.bgDark)}>↻ Refresh</button>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        {[
          { label: 'Total Runs', value: d.total_runs, icon: '🏃', color: C.info },
          { label: 'Pass Rate', value: `${d.pass_rate?.toFixed(1) || 0}%`, icon: '✅', color: d.pass_rate >= 80 ? C.success : d.pass_rate >= 50 ? C.warn : C.error },
          { label: 'Tests Executed', value: d.total_tests_executed, icon: '🧪', color: C.accentAlt },
          { label: 'Suites', value: d.suites_available, icon: '📦', color: C.muted },
          { label: 'Scheduled', value: d.scheduled_jobs, icon: '⏰', color: C.warn },
          { label: 'Chaos Runs', value: d.chaos_experiments, icon: '💥', color: C.accent },
        ].map((s, i) => (
          <div key={i} style={{ ...card, flex: '1 1 140px', minWidth: 130, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.muted, marginBottom: 6 }}>{s.icon} {s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Spindle Status */}
      <div style={{ ...card, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: d.spindle_status === 'online' ? C.success : C.error }} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>Spindle Formal Verifier</span>
        <span style={{ fontSize: 12, color: d.spindle_status === 'online' ? C.success : C.error, fontWeight: 700 }}>{(d.spindle_status || 'unknown').toUpperCase()}</span>
      </div>

      {/* Last Run */}
      {lr && (
        <div style={{ ...card }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Last Test Run</div>
          <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
            <span>Suite: <b>{lr.suite}</b></span>
            <span style={{ color: lr.status === 'passed' ? C.success : C.error, fontWeight: 700 }}>{lr.status?.toUpperCase()}</span>
            <span>{lr.passed}/{lr.total} passed</span>
            <span>{lr.duration?.toFixed(1)}s</span>
            <span style={{ color: C.dim }}>{lr.finished_at ? new Date(lr.finished_at).toLocaleString() : ''}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Run Tests ───────────────────────────────────────────────────
function RunTestsView() {
  const { data: discovery } = useTabData('/api/testing/discover', { suites: [], total_files: 0, total_suites: 0 });
  const [suite, setSuite] = useState('all');
  const [markers, setMarkers] = useState('');
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const logsEndRef = useRef(null);

  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  const runTests = async () => {
    setRunning(true); setLogs([]); setResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/testing/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suite, markers: markers || null, verbose: true }),
      });
      if (!res.ok) { setRunning(false); return; }
      const { task_id } = await res.json();

      const sse = new EventSource(`${API_BASE_URL}/api/testing/stream/${task_id}`);
      sse.onmessage = (e) => {
        const line = e.data;
        if (line === '[END OF STREAM]') {
          sse.close();
          setRunning(false);
          if (line.includes('RESULT')) setResult(line);
        } else {
          setLogs(prev => [...prev, line]);
        }
      };
      sse.onerror = () => { sse.close(); setRunning(false); };
    } catch { setRunning(false); }
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 800 }}>Run Tests</h2>

      <div style={{ ...card, marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={suite} onChange={e => setSuite(e.target.value)}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12 }}>
          <option value="all">All Suites</option>
          {(discovery?.suites || []).map(s => (
            <option key={s.name} value={s.name}>{s.name} ({s.test_count} files)</option>
          ))}
        </select>
        <input placeholder="Markers (e.g. unit, not slow)" value={markers} onChange={e => setMarkers(e.target.value)}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12, flex: 1 }} />
        <button onClick={runTests} disabled={running} style={{ ...btn(running ? C.dim : C.success), minWidth: 120 }}>
          {running ? '⏳ Running...' : '▶ Run Suite'}
        </button>
      </div>

      {/* Console Output */}
      <div style={{
        ...card, height: 400, overflowY: 'auto', fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 11, lineHeight: 1.6, padding: '12px 16px', background: '#000',
      }}>
        {logs.length === 0 && !running && <div style={{ color: C.dim }}>Select a suite and click Run to execute tests...</div>}
        {logs.map((line, i) => {
          let color = C.text;
          if (line.includes('PASSED') || line.includes('[SUCCESS]') || line.includes('✅')) color = C.success;
          else if (line.includes('FAILED') || line.includes('[ERROR]') || line.includes('❌')) color = C.error;
          else if (line.includes('[START]') || line.includes('[RESULT]')) color = C.info;
          else if (line.includes('SKIP') || line.includes('[WARN]')) color = C.warn;
          return <div key={i} style={{ color }}>{line}</div>;
        })}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

// ─── History ─────────────────────────────────────────────────────
function HistoryView() {
  const { data: history, refresh } = useTabData('/api/testing/history', { runs: [], total_runs: 0 });
  const runs = history?.runs || [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>Test History ({runs.length} runs)</h2>
        <button onClick={refresh} style={btn(C.bgDark)}>↻</button>
      </div>

      {runs.length === 0 ? (
        <div style={{ ...card, textAlign: 'center', padding: 40, color: C.dim }}>No test runs yet. Go to "Run Tests" to execute your first suite.</div>
      ) : runs.map((r, i) => (
        <div key={i} style={{ ...card, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: 20 }}>{r.status === 'passed' ? '✅' : r.status === 'failed' ? '❌' : '⚠️'}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{r.suite}</div>
            <div style={{ fontSize: 11, color: C.dim }}>
              {r.passed}/{r.total} passed · {r.failed} failed · {r.skipped} skipped · {r.duration?.toFixed(1)}s
            </div>
          </div>
          <div style={{ fontSize: 20, fontWeight: 800, color: r.success_rate >= 80 ? C.success : r.success_rate >= 50 ? C.warn : C.error }}>
            {r.success_rate?.toFixed(0)}%
          </div>
          <div style={{ fontSize: 10, color: C.dim, minWidth: 140, textAlign: 'right' }}>
            {r.finished_at ? new Date(r.finished_at).toLocaleString() : ''}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Schedule ────────────────────────────────────────────────────
function ScheduleView() {
  const { data: schedules, refresh } = useTabData('/api/testing/schedule', { jobs: [] });
  const [suite, setSuite] = useState('all');
  const [interval, setInterval_] = useState(60);
  const [chaos, setChaos] = useState(false);
  const [name, setName] = useState('');

  const createSchedule = async () => {
    await fetch(`${API_BASE_URL}/api/testing/schedule`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suite, interval_minutes: interval, chaos_enabled: chaos, name: name || `${suite} every ${interval}m` }),
    });
    refresh();
  };

  const cancelJob = async (id) => {
    await fetch(`${API_BASE_URL}/api/testing/schedule/${id}`, { method: 'DELETE' });
    refresh();
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 800 }}>Scheduled Tests</h2>

      <div style={{ ...card, marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <input placeholder="Schedule name" value={name} onChange={e => setName(e.target.value)}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12, flex: 1 }} />
        <select value={suite} onChange={e => setSuite(e.target.value)}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12 }}>
          <option value="all">All Suites</option>
          <option value="unit">Unit</option>
          <option value="integration">Integration</option>
          <option value="api">API</option>
          <option value="cognitive">Cognitive</option>
          <option value="security">Security</option>
        </select>
        <input type="number" value={interval} onChange={e => setInterval_(+e.target.value)} min={5} max={1440}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12, width: 80 }} />
        <span style={{ fontSize: 11, color: C.dim }}>min</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: C.warn, cursor: 'pointer' }}>
          <input type="checkbox" checked={chaos} onChange={e => setChaos(e.target.checked)} /> 💥 + Chaos
        </label>
        <button onClick={createSchedule} style={btn(C.success)}>+ Create</button>
      </div>

      {(schedules?.jobs || []).length === 0 ? (
        <div style={{ ...card, textAlign: 'center', padding: 40, color: C.dim }}>No scheduled jobs. Create one above.</div>
      ) : (schedules.jobs || []).map(j => (
        <div key={j.id} style={{ ...card, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: 16 }}>{j.chaos_enabled ? '💥' : '⏰'}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{j.name}</div>
            <div style={{ fontSize: 11, color: C.dim }}>Suite: {j.suite} · Every {j.interval_minutes}m{j.chaos_enabled ? ' · +Chaos' : ''}</div>
          </div>
          <span style={{ fontSize: 11, color: j.status === 'active' ? C.success : C.dim, fontWeight: 700 }}>{j.status.toUpperCase()}</span>
          <button onClick={() => cancelJob(j.id)} style={{ ...btn(C.bgDark), fontSize: 10, color: C.error }}>Cancel</button>
        </div>
      ))}
    </div>
  );
}

// ─── Chaos Lab ───────────────────────────────────────────────────
function ChaosView() {
  const { data: actions } = useTabData('/api/testing/chaos/actions', []);
  const { data: history, refresh: refreshHistory } = useTabData('/api/testing/chaos/history', { experiments: [] });
  const [running, setRunning] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const runChaos = async (actionId) => {
    setRunning(actionId); setLastResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/testing/chaos/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, duration_seconds: 30, intensity: 'medium' }),
      });
      if (res.ok) { setLastResult(await res.json()); refreshHistory(); }
    } catch { /* silent */ }
    finally { setRunning(null); }
  };

  const severityColor = { low: C.info, medium: C.warn, high: C.error, critical: '#ff0000' };

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 800 }}>💥 Chaos Engineering Lab</h2>
      <p style={{ fontSize: 12, color: C.dim, marginBottom: 20 }}>Controlled failure injection to test system resilience. All experiments auto-recover.</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, marginBottom: 24 }}>
        {(Array.isArray(actions) ? actions : []).map(a => (
          <div key={a.id} style={{ ...card, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>{a.name}</span>
              <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, background: (severityColor[a.severity] || C.dim) + '30', color: severityColor[a.severity] || C.dim, fontWeight: 700, textTransform: 'uppercase' }}>{a.severity}</span>
            </div>
            <div style={{ fontSize: 11, color: C.dim, lineHeight: 1.4 }}>{a.description}</div>
            <button onClick={() => runChaos(a.id)} disabled={running === a.id}
              style={{ ...btn(running === a.id ? C.dim : C.accent), marginTop: 'auto', fontSize: 11 }}>
              {running === a.id ? '⏳ Running...' : '🔥 Execute'}
            </button>
          </div>
        ))}
      </div>

      {/* Last Result */}
      {lastResult && (
        <div style={{ ...card, marginBottom: 16, borderLeft: `4px solid ${lastResult.recovery_status === 'healthy' ? C.success : C.error}` }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{lastResult.action_name} — Result</div>
          {lastResult.observations.map((o, i) => (
            <div key={i} style={{ fontSize: 11, color: C.text, padding: '2px 0', fontFamily: 'monospace' }}>→ {o}</div>
          ))}
          <div style={{ marginTop: 8, fontSize: 12, fontWeight: 700, color: lastResult.recovery_status === 'healthy' ? C.success : C.error }}>
            Recovery: {lastResult.recovery_status.toUpperCase()}
          </div>
        </div>
      )}

      {/* History */}
      {(history?.experiments || []).length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Experiment History</div>
          {history.experiments.map((e, i) => (
            <div key={i} style={{ ...card, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px' }}>
              <span style={{ color: e.recovery_status === 'healthy' ? C.success : C.error, fontWeight: 700 }}>{e.recovery_status === 'healthy' ? '✅' : '❌'}</span>
              <span style={{ fontSize: 12, flex: 1 }}>{e.action_name}</span>
              <span style={{ fontSize: 10, color: C.dim }}>{e.duration}s</span>
              <span style={{ fontSize: 10, color: C.dim }}>{new Date(e.started_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Spindle Bridge ──────────────────────────────────────────────
function SpindleBridgeView() {
  const { data: spindleStatus } = useTabData('/api/testing/spindle/status', { ok: false, status: 'unknown', gate_available: false });
  const [suite, setSuite] = useState('all');
  const [verifying, setVerifying] = useState(false);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  const verify = async () => {
    setVerifying(true); setLogs([]);
    try {
      const res = await fetch(`${API_BASE_URL}/api/testing/spindle/verify-suite`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suite }),
      });
      if (!res.ok) { setVerifying(false); return; }
      const { task_id } = await res.json();

      const sse = new EventSource(`${API_BASE_URL}/api/testing/stream/${task_id}`);
      sse.onmessage = (e) => {
        if (e.data === '[END OF STREAM]') { sse.close(); setVerifying(false); }
        else setLogs(prev => [...prev, e.data]);
      };
      sse.onerror = () => { sse.close(); setVerifying(false); };
    } catch { setVerifying(false); }
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 800 }}>🔬 Spindle Formal Verification Bridge</h2>
      <p style={{ fontSize: 12, color: C.dim, marginBottom: 20 }}>
        Run test suites through Spindle's Z3 SMT solver before execution. Ensures test actions are formally safe.
      </p>

      <div style={{ ...card, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: spindleStatus?.status === 'online' ? C.success : C.error }} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>Spindle Status: </span>
        <span style={{ fontSize: 13, color: spindleStatus?.status === 'online' ? C.success : C.error, fontWeight: 700 }}>{(spindleStatus?.status || 'unknown').toUpperCase()}</span>
        <span style={{ fontSize: 11, color: C.dim }}>Gate: {spindleStatus?.gate_available ? '✓ Available' : '✗ Unavailable'}</span>
      </div>

      <div style={{ ...card, marginBottom: 16, display: 'flex', gap: 10, alignItems: 'center' }}>
        <select value={suite} onChange={e => setSuite(e.target.value)}
          style={{ padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 12 }}>
          <option value="all">All Suites</option>
          <option value="unit">Unit</option>
          <option value="integration">Integration</option>
          <option value="cognitive">Cognitive</option>
          <option value="security">Security</option>
        </select>
        <button onClick={verify} disabled={verifying} style={btn(verifying ? C.dim : C.accentAlt)}>
          {verifying ? '⏳ Verifying...' : '🔬 Verify & Run'}
        </button>
      </div>

      <div style={{
        ...card, height: 300, overflowY: 'auto', fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 11, lineHeight: 1.6, background: '#000',
      }}>
        {logs.length === 0 && <div style={{ color: C.dim }}>Select a suite and click Verify to run through Spindle...</div>}
        {logs.map((line, i) => {
          let color = C.text;
          if (line.includes('✅') || line.includes('SAT')) color = C.success;
          else if (line.includes('⚠️') || line.includes('UNSAT')) color = C.error;
          else if (line.includes('[SPINDLE]')) color = C.accentAlt;
          return <div key={i} style={{ color }}>{line}</div>;
        })}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
