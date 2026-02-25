import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', error: '#f44336', info: '#2196f3',
};
const btn = (bg = C.accentAlt) => ({
  padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
  fontSize: 12, fontWeight: 600, color: '#fff', background: bg,
});
const inp = {
  padding: '7px 10px', border: `1px solid ${C.border}`, borderRadius: 4,
  background: C.bg, color: C.text, fontSize: 12, outline: 'none', width: '100%', boxSizing: 'border-box',
};

function typeIcon(t) {
  const m = {
    user_upload: '📤', file_operation: '📁', file_ingestion: '📥', ai_response: '🤖',
    ai_code_generation: '⚡', code_change: '📝', librarian_action: '📚', system_event: '🖥️',
    api_request: '🔗', web_fetch: '🌐', learning_complete: '🎓', error: '❌',
    coding_agent_action: '🛠️', user_input: '💬', database_change: '🗄️', task: '📋',
  };
  return m[t] || '🔑';
}

function priorityColor(p) {
  return { critical: C.error, high: C.warn, medium: C.info, low: C.dim }[p] || C.dim;
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

// ── Live Activity ─────────────────────────────────────────────────────
function LivePanel() {
  const [live, setLive] = useState(null);
  const [history, setHistory] = useState([]);

  const refresh = useCallback(async () => {
    const [lRes, hRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/tasks-hub/live`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/tasks-hub/history?limit=40`).then(r => r.ok ? r.json() : null),
    ]);
    if (lRes.status === 'fulfilled') setLive(lRes.value);
    if (hRes.status === 'fulfilled') setHistory(hRes.value?.history || []);
  }, []);

  useEffect(() => { queueMicrotask(refresh); const i = setInterval(refresh, 5000); return () => clearInterval(i); }, [refresh]);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Live feed */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}` }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: C.success, animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: 13, fontWeight: 700 }}>Live Activity</span>
          <span style={{ fontSize: 11, color: C.dim }}>{live?.activity_count || 0} events (last 5 min)</span>
          {live?.system && (
            <span style={{ marginLeft: 'auto', fontSize: 10, color: C.dim }}>
              CPU {live.system.cpu?.toFixed(0)}% · MEM {live.system.memory?.toFixed(0)}%
            </span>
          )}
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {!live ? <div style={{ padding: 30, textAlign: 'center', color: C.dim }}>Connecting...</div>
           : live.activities?.length === 0 ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32, opacity: 0.5 }}>⏳</div><div style={{ fontSize: 12, marginTop: 8 }}>No activity in the last 5 minutes</div></div>
           : live.activities.map((a, i) => (
            <div key={a.id || i} style={{ padding: '8px 14px', borderBottom: `1px solid ${C.border}22`, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }}>{typeIcon(a.type)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: C.text, lineHeight: 1.4 }}>{a.what}</div>
                <div style={{ fontSize: 10, color: C.dim, marginTop: 2, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <span>{a.type}</span>
                  {a.who && <span>by {a.who}</span>}
                  {a.file_path && <span>📄 {a.file_path.split('/').pop()}</span>}
                  {a.status && <span style={{ color: a.status === 'running' ? C.success : C.warn }}>{a.status}</span>}
                  {a.progress != null && a.progress > 0 && <span>{a.progress}%</span>}
                </div>
              </div>
              <span style={{ fontSize: 10, color: C.dim, flexShrink: 0 }}>{timeAgo(a.timestamp)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* History */}
      <div style={{ flex: '0 0 350px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>24h History</span>
          <span style={{ fontSize: 11, color: C.dim, marginLeft: 8 }}>{history.length} events</span>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {history.map((h, i) => (
            <div key={h.id || i} style={{ padding: '6px 14px', borderBottom: `1px solid ${C.border}22`, fontSize: 11, display: 'flex', gap: 8, alignItems: 'center' }}>
              <span>{typeIcon(h.type)}</span>
              {h.is_error && <span style={{ color: C.error }}>❌</span>}
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: C.muted }}>{h.what}</span>
              <span style={{ color: C.dim, flexShrink: 0 }}>{timeAgo(h.timestamp)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Submit Task ───────────────────────────────────────────────────────
function SubmitPanel() {
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [priority, setPriority] = useState('medium');
  const [taskType, setTaskType] = useState('user_request');
  const [submitting, setSubmitting] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [notification, setNotification] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks-hub/active`);
      if (res.ok) setTasks((await res.json()).tasks || []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchTasks(); const i = setInterval(fetchTasks, 10000); return () => clearInterval(i); }, [fetchTasks]);

  const submit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks-hub/submit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description: desc, priority, task_type: taskType }),
      });
      if (res.ok) { setTitle(''); setDesc(''); setNotification('Task submitted'); fetchTasks(); setTimeout(() => setNotification(null), 3000); }
    } catch { /* silent */ }
    finally { setSubmitting(false); }
  };

  const types = [
    { id: 'user_request', label: '💬 Request' }, { id: 'learning', label: '🎓 Learning' },
    { id: 'healing', label: '🔧 Healing' }, { id: 'ingestion', label: '📥 Ingestion' },
    { id: 'analysis', label: '🔍 Analysis' },
  ];

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Submit form */}
      <div style={{ flex: '0 0 360px', borderRight: `1px solid ${C.border}`, padding: 16, overflow: 'auto' }}>
        {notification && <div style={{ padding: '8px 14px', marginBottom: 12, background: C.success + '30', border: `1px solid ${C.success}`, borderRadius: 6, fontSize: 12, color: C.success }}>{notification}</div>}

        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>📝 Suggest a Task</div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'block', marginBottom: 4 }}>What should Grace do?</label>
          <input placeholder="e.g. Research competitors in AI space" value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} style={inp} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'block', marginBottom: 4 }}>Details (optional)</label>
          <textarea placeholder="Additional context..." value={desc} onChange={e => setDesc(e.target.value)} rows={3} style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'block', marginBottom: 4 }}>Type</label>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {types.map(t => (
              <button key={t.id} onClick={() => setTaskType(t.id)} style={{ ...btn(taskType === t.id ? C.accentAlt : C.bgDark), fontSize: 10, padding: '4px 10px' }}>{t.label}</button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'block', marginBottom: 4 }}>Priority</label>
          <div style={{ display: 'flex', gap: 4 }}>
            {['low', 'medium', 'high', 'critical'].map(p => (
              <button key={p} onClick={() => setPriority(p)} style={{ ...btn(priority === p ? priorityColor(p) : C.bgDark), fontSize: 10, padding: '4px 12px', textTransform: 'capitalize' }}>{p}</button>
            ))}
          </div>
        </div>

        <button onClick={submit} disabled={submitting || !title.trim()} style={{ ...btn(C.accent), width: '100%', padding: '10px', fontSize: 13, opacity: submitting ? 0.5 : 1 }}>
          {submitting ? '⏳ Submitting...' : '▶ Submit Task'}
        </button>
      </div>

      {/* Active tasks */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Active Tasks ({tasks.length})</span>
          <button onClick={fetchTasks} style={{ ...btn(C.bgDark), fontSize: 10, marginLeft: 'auto' }}>↻</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tasks.length === 0 ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32 }}>📋</div><div style={{ fontSize: 12, marginTop: 8 }}>No active tasks</div></div>
           : tasks.map(t => (
            <div key={t.id} style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 10, alignItems: 'center' }}>
              <span style={{ width: 4, height: 30, borderRadius: 2, background: priorityColor(t.priority), flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{t.title}</div>
                <div style={{ fontSize: 10, color: C.dim, marginTop: 2 }}>{t.type} · {t.status} · {timeAgo(t.created_at)}</div>
              </div>
              {t.progress > 0 && <span style={{ fontSize: 12, fontWeight: 700, color: C.success }}>{t.progress}%</span>}
              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: priorityColor(t.priority) + '30', color: priorityColor(t.priority), textTransform: 'uppercase', fontWeight: 700 }}>{t.priority}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Scheduled Tasks ───────────────────────────────────────────────────
function SchedulePanel() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [priority, setPriority] = useState('medium');
  const [taskType] = useState('user_request');
  const [schedDate, setSchedDate] = useState('');
  const [schedTime, setSchedTime] = useState('09:00');
  const [repeat, setRepeat] = useState('once');
  const [notification, setNotification] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks-hub/scheduled`);
      if (res.ok) setTasks((await res.json()).tasks || []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { queueMicrotask(refresh); }, [refresh]);

  const schedule = async () => {
    if (!title.trim() || !schedDate) return;
    const iso = `${schedDate}T${schedTime}:00`;
    await fetch(`${API_BASE_URL}/api/tasks-hub/schedule`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, priority, task_type: taskType, scheduled_for: iso, repeat: repeat === 'once' ? null : repeat }),
    });
    setTitle(''); setDesc(''); setSchedDate('');
    setNotification('Task scheduled'); setTimeout(() => setNotification(null), 3000);
    refresh();
  };

  const deleteTask = async (id) => {
    await fetch(`${API_BASE_URL}/api/tasks-hub/scheduled/${id}`, { method: 'DELETE' });
    refresh();
  };

  const runNow = async (id) => {
    await fetch(`${API_BASE_URL}/api/tasks-hub/scheduled/${id}/run`, { method: 'POST' });
    refresh();
  };

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Schedule form */}
      <div style={{ flex: '0 0 360px', borderRight: `1px solid ${C.border}`, padding: 16, overflow: 'auto' }}>
        {notification && <div style={{ padding: '8px 14px', marginBottom: 12, background: C.success + '30', border: `1px solid ${C.success}`, borderRadius: 6, fontSize: 12, color: C.success }}>{notification}</div>}

        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>⏰ Schedule a Task</div>

        <div style={{ marginBottom: 10 }}>
          <input placeholder="Task title" value={title} onChange={e => setTitle(e.target.value)} style={inp} />
        </div>
        <div style={{ marginBottom: 10 }}>
          <textarea placeholder="Details..." value={desc} onChange={e => setDesc(e.target.value)} rows={2} style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} />
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <input type="date" value={schedDate} onChange={e => setSchedDate(e.target.value)} style={{ ...inp, flex: 1 }} />
          <input type="time" value={schedTime} onChange={e => setSchedTime(e.target.value)} style={{ ...inp, flex: 1 }} />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'block', marginBottom: 4 }}>Repeat</label>
          <div style={{ display: 'flex', gap: 4 }}>
            {['once', 'daily', 'weekly', 'monthly'].map(r => (
              <button key={r} onClick={() => setRepeat(r)} style={{ ...btn(repeat === r ? C.accentAlt : C.bgDark), fontSize: 10, padding: '4px 10px', textTransform: 'capitalize' }}>{r}</button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
          {['low', 'medium', 'high', 'critical'].map(p => (
            <button key={p} onClick={() => setPriority(p)} style={{ ...btn(priority === p ? priorityColor(p) : C.bgDark), fontSize: 10, padding: '3px 10px', textTransform: 'capitalize', flex: 1 }}>{p}</button>
          ))}
        </div>

        <button onClick={schedule} disabled={!title.trim() || !schedDate} style={{ ...btn(C.accent), width: '100%', padding: '10px', fontSize: 13 }}>
          ⏰ Schedule Task
        </button>
      </div>

      {/* Scheduled list */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Scheduled Tasks ({tasks.length})</span>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tasks.length === 0 ? <div style={{ padding: 40, textAlign: 'center', color: C.dim }}><div style={{ fontSize: 32 }}>⏰</div><div style={{ fontSize: 12, marginTop: 8 }}>No scheduled tasks</div></div>
           : tasks.map(t => (
            <div key={t.id} style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', gap: 10, alignItems: 'center' }}>
              <span style={{ width: 4, height: 30, borderRadius: 2, background: t.status === 'overdue' ? C.error : priorityColor(t.priority), flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{t.title}</div>
                <div style={{ fontSize: 10, color: C.dim, marginTop: 2 }}>
                  📅 {new Date(t.scheduled_for).toLocaleString()}
                  {t.repeat && <span> · 🔄 {t.repeat}</span>}
                </div>
              </div>
              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: (t.status === 'overdue' ? C.error : C.info) + '30', color: t.status === 'overdue' ? C.error : C.info, textTransform: 'uppercase', fontWeight: 700 }}>{t.status}</span>
              <button onClick={() => runNow(t.id)} style={{ ...btn(C.success), fontSize: 10, padding: '3px 8px' }}>▶ Now</button>
              <button onClick={() => deleteTask(t.id)} style={{ ...btn(C.border), fontSize: 10, padding: '3px 6px' }}>🗑</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main TasksTab ─────────────────────────────────────────────────────
export default function TasksTab() {
  const [activeTab, setActiveTab] = useState('live');

  const tabs = [
    { id: 'live', label: 'Live', icon: '🟢' },
    { id: 'submit', label: 'Submit Task', icon: '📝' },
    { id: 'schedule', label: 'Schedule', icon: '⏰' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: C.text, background: C.bg }}>
      <div style={{ borderBottom: `1px solid ${C.border}`, background: C.bgAlt, padding: '0 16px', display: 'flex', alignItems: 'stretch' }}>
        <span style={{ fontSize: 15, fontWeight: 700, padding: '12px 16px 12px 0', display: 'flex', alignItems: 'center', gap: 8 }}>📋 Tasks</span>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '10px 16px', border: 'none', background: 'none', cursor: 'pointer',
            color: activeTab === t.id ? C.accent : C.muted,
            borderBottom: activeTab === t.id ? `2px solid ${C.accent}` : '2px solid transparent',
            fontSize: 13, fontWeight: activeTab === t.id ? 700 : 500,
            display: 'flex', alignItems: 'center', gap: 6, transition: 'all .15s',
          }}><span>{t.icon}</span> {t.label}</button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'live' && <LivePanel />}
        {activeTab === 'submit' && <SubmitPanel />}
        {activeTab === 'schedule' && <SchedulePanel />}
      </div>
    </div>
  );
}
