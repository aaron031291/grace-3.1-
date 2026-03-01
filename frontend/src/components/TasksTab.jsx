import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';
import PlannerPanelIDE from './PlannerPanel';

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
  const [timeSense, setTimeSense] = useState(null);

  const refresh = useCallback(async () => {
    const [lRes, hRes, tsRes] = await Promise.allSettled([
      fetch(`${API_BASE_URL}/api/tasks-hub/live`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/tasks-hub/history?limit=40`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/api/tasks-hub/time-sense`).then(r => r.ok ? r.json() : null),
    ]);
    if (lRes.status === 'fulfilled') setLive(lRes.value);
    if (hRes.status === 'fulfilled') setHistory(hRes.value?.history || []);
    if (tsRes.status === 'fulfilled') setTimeSense(tsRes.value);
  }, []);

  useEffect(() => { queueMicrotask(refresh); const i = setInterval(refresh, 30000); return () => clearInterval(i); }, [refresh]);

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
        {/* TimeSense bar */}
        {timeSense?.now && (
          <div style={{ padding: '8px 14px', borderBottom: `1px solid ${C.border}`, background: C.bg, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', fontSize: 11 }}>
            <span style={{ fontWeight: 700, color: C.accent }}>🕐 TimeSense</span>
            <span style={{ color: C.text }}>{timeSense.now.day_of_week}</span>
            <span style={{ color: C.muted }}>{timeSense.now.period_label}</span>
            <span style={{ color: C.muted }}>{timeSense.now.time}</span>
            <span style={{ color: timeSense.now.is_business_hours ? C.success : C.dim }}>
              {timeSense.now.is_business_hours ? '🟢 Business hours' : '🌙 Off hours'}
            </span>
            {timeSense.activity_pattern?.peak_hour && (
              <span style={{ color: C.dim }}>Peak: {timeSense.activity_pattern.peak_hour} ({timeSense.activity_pattern.peak_day})</span>
            )}
            {timeSense.upcoming_tasks?.length > 0 && (
              <span style={{ color: C.warn }}>
                ⏰ {timeSense.upcoming_tasks.length} upcoming
                {timeSense.upcoming_tasks[0]?.urgency?.label === 'overdue' && <span style={{ color: C.error }}> ({timeSense.upcoming_tasks.filter(t => t.urgency?.label === 'overdue').length} overdue)</span>}
              </span>
            )}
          </div>
        )}

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

// ── Submit + Kanban Board ──────────────────────────────────────────────
function SubmitPanel() {
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [priority, setPriority] = useState('medium');
  const [taskType, setTaskType] = useState('user_request');
  const [submitting, setSubmitting] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [notification, setNotification] = useState(null);
  const [dragId, setDragId] = useState(null);
  const [dragOverCol, setDragOverCol] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks-hub/active`);
      if (res.ok) setTasks((await res.json()).tasks || []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchTasks(); const i = setInterval(fetchTasks, 30000); return () => clearInterval(i); }, [fetchTasks]);

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

  const handleDrop = (newStatus) => {
    if (!dragId) return;
    setTasks(prev => prev.map(t => t.id === dragId ? { ...t, status: newStatus } : t));
    setDragId(null);
    setDragOverCol(null);
  };

  const columns = [
    { id: 'queued', label: 'Queued', color: C.info, icon: '📥' },
    { id: 'running', label: 'Running', color: C.warn, icon: '⚡' },
    { id: 'completed', label: 'Completed', color: C.success, icon: '✅' },
    { id: 'failed', label: 'Failed', color: C.error, icon: '❌' },
  ];

  const types = [
    { id: 'user_request', label: '💬 Request' }, { id: 'learning', label: '🎓 Learning' },
    { id: 'healing', label: '🔧 Healing' }, { id: 'ingestion', label: '📥 Ingestion' },
    { id: 'analysis', label: '🔍 Analysis' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Submit bar at top */}
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        {notification && <div style={{ padding: '4px 12px', background: C.success + '30', border: `1px solid ${C.success}`, borderRadius: 4, fontSize: 11, color: C.success }}>{notification}</div>}
        <input placeholder="What should Grace do?" value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} style={{ ...inp, flex: '1 1 200px', minWidth: 150 }} />
        <input placeholder="Details (optional)" value={desc} onChange={e => setDesc(e.target.value)} style={{ ...inp, flex: '1 1 200px', minWidth: 100 }} />
        <div style={{ display: 'flex', gap: 2 }}>
          {types.map(t => (
            <button key={t.id} onClick={() => setTaskType(t.id)} style={{ ...btn(taskType === t.id ? C.accentAlt : C.bgDark), fontSize: 9, padding: '3px 6px' }}>{t.label}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 2 }}>
          {['low', 'medium', 'high', 'critical'].map(p => (
            <button key={p} onClick={() => setPriority(p)} style={{ ...btn(priority === p ? priorityColor(p) : C.bgDark), fontSize: 9, padding: '3px 8px', textTransform: 'capitalize' }}>{p}</button>
          ))}
        </div>
        <button onClick={submit} disabled={submitting || !title.trim()} style={{ ...btn(C.accent), fontSize: 12, opacity: submitting ? 0.5 : 1 }}>
          {submitting ? '⏳' : '+ Add Task'}
        </button>
        <button onClick={fetchTasks} style={{ ...btn(C.bgDark), fontSize: 11 }}>↻</button>
      </div>

      {/* Kanban board */}
      <div style={{ flex: 1, display: 'flex', gap: 8, padding: 8, overflow: 'auto' }}>
        {columns.map(col => {
          const colTasks = tasks.filter(t => t.status === col.id);
          const isOver = dragOverCol === col.id;
          return (
            <div
              key={col.id}
              onDragOver={e => { e.preventDefault(); setDragOverCol(col.id); }}
              onDragLeave={() => setDragOverCol(null)}
              onDrop={() => handleDrop(col.id)}
              style={{
                flex: 1, minWidth: 180, display: 'flex', flexDirection: 'column',
                background: isOver ? col.color + '15' : C.bgAlt,
                border: `1px solid ${isOver ? col.color : C.border}`,
                borderRadius: 8, overflow: 'hidden', transition: 'border-color .15s, background .15s',
              }}
            >
              {/* Column header */}
              <div style={{ padding: '10px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>{col.icon}</span>
                <span style={{ fontSize: 12, fontWeight: 700, flex: 1 }}>{col.label}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: col.color, background: col.color + '22', padding: '1px 8px', borderRadius: 10 }}>{colTasks.length}</span>
              </div>

              {/* Task cards */}
              <div style={{ flex: 1, overflowY: 'auto', padding: 6 }}>
                {colTasks.length === 0 && (
                  <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 11 }}>
                    {dragId ? 'Drop here' : 'No tasks'}
                  </div>
                )}
                {colTasks.map(t => (
                  <div
                    key={t.id}
                    draggable
                    onDragStart={() => setDragId(t.id)}
                    onDragEnd={() => { setDragId(null); setDragOverCol(null); }}
                    style={{
                      padding: '8px 10px', marginBottom: 6, borderRadius: 6,
                      background: dragId === t.id ? C.bgDark : C.bg,
                      border: `1px solid ${dragId === t.id ? C.accent : C.border}`,
                      cursor: 'grab', opacity: dragId === t.id ? 0.7 : 1,
                      transition: 'opacity .15s, border-color .15s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span style={{ width: 4, height: 16, borderRadius: 2, background: priorityColor(t.priority), flexShrink: 0 }} />
                      <span style={{ fontSize: 12, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.title}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 10, color: C.dim }}>
                      <span>{typeIcon(t.type)}</span>
                      <span style={{ textTransform: 'capitalize' }}>{t.priority}</span>
                      {t.progress > 0 && <span style={{ color: C.success }}>{t.progress}%</span>}
                      <span style={{ marginLeft: 'auto' }}>{timeAgo(t.created_at)}</span>
                    </div>
                    {t.description && (
                      <div style={{ fontSize: 10, color: C.dim, marginTop: 4, lineHeight: 1.3, maxHeight: 26, overflow: 'hidden' }}>{t.description}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
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

// ── Planner Sub-tab — Multi-model consensus ──────────────────────────
function PlannerPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('auto');
  const endRef = useCallback(node => { if (node) node.scrollIntoView({ behavior: 'smooth' }); }, []);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/domain/models`)
      .then(r => r.ok ? r.json() : { models: [] })
      .then(d => setModels(d.models || []))
      .catch(() => {});
  }, []);

  const send = async () => {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setSending(true);

    // Get responses from selected model (or all for consensus)
    const providers = selectedModel === 'consensus'
      ? models.filter(m => m.available).map(m => m.id)
      : [selectedModel === 'auto' ? models.find(m => m.available)?.id || 'ollama' : selectedModel];

    for (const provider of providers) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/domain/chat`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg, folder_path: '', provider }),
        });
        if (res.ok) {
          const d = await res.json();
          setMessages(prev => [...prev, {
            role: 'assistant', content: d.response || '(no response)',
            provider: d.provider || provider,
          }]);
        }
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: `(${provider} unavailable)`, provider }]);
      }
    }
    setSending(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Model selector */}
      <div style={{ padding: '8px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: C.muted }}>Model:</span>
        <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
          style={{ padding: '4px 8px', fontSize: 11, background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, outline: 'none' }}>
          <option value="auto">Auto (best available)</option>
          <option value="consensus">🤝 Consensus (all models)</option>
          {models.map(m => (
            <option key={m.id} value={m.id} disabled={!m.available}>{m.name} {m.available ? '' : '(unavailable)'}</option>
          ))}
        </select>
        <span style={{ fontSize: 10, color: C.dim, marginLeft: 'auto' }}>
          {selectedModel === 'consensus' ? 'All models discuss and find consensus' : ''}
        </span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: C.dim, paddingTop: 60 }}>
            <div style={{ fontSize: 40, opacity: 0.4 }}>🤝</div>
            <div style={{ fontSize: 14, fontWeight: 500, color: C.muted, marginTop: 8 }}>Planner</div>
            <div style={{ fontSize: 12, marginTop: 4, maxWidth: 300, margin: '4px auto 0' }}>
              Discuss tasks with Grace, Kimi, and Opus. Select "Consensus" to have all models contribute and find agreement.
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            padding: '8px 12px', marginBottom: 6, borderRadius: 8,
            background: msg.role === 'user' ? C.bgDark : C.bgAlt,
            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '90%', border: `1px solid ${C.border}`,
          }}>
            <div style={{ fontSize: 10, color: C.dim, marginBottom: 4 }}>
              {msg.role === 'user' ? 'You' : `Grace (${msg.provider || 'auto'})`}
            </div>
            <pre style={{ margin: 0, fontSize: 12, color: C.text, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{msg.content}</pre>
          </div>
        ))}
        {sending && <div style={{ padding: 8, color: C.dim, fontSize: 12 }}>Thinking...</div>}
        <div ref={endRef} />
      </div>

      {/* Input — type or upload */}
      <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input placeholder="Discuss a task, plan, or decision..."
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            disabled={sending}
            style={{ flex: 1, padding: '8px 12px', background: C.bg, color: C.text, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none' }} />
          <input type="file" id="plannerFileUpload" accept=".pdf,.txt,.md,.doc,.docx,.csv,.json" style={{ display: 'none' }}
            onChange={async (e) => {
              if (!e.target.files?.length) return;
              const file = e.target.files[0];
              const text = await file.text().catch(() => `[Uploaded: ${file.name}, ${(file.size/1024).toFixed(1)}KB]`);
              const preview = text.substring(0, 3000);
              setMessages(prev => [...prev, { role: 'user', content: `📎 Uploaded: ${file.name}\n\n${preview}` }]);
              setInput(`Analyse this document: ${file.name}`);
              e.target.value = '';
            }}
          />
          <button onClick={() => document.getElementById('plannerFileUpload')?.click()}
            title="Upload a document to discuss"
            style={{ padding: '6px 10px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14, color: '#fff', background: C.bgDark }}>
            📎
          </button>
          <button onClick={send} disabled={sending || !input.trim()}
            style={{ padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#fff', background: C.accent, opacity: sending ? 0.5 : 1 }}>
            {sending ? '⏳' : '▶ Send'}
          </button>
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
    { id: 'planner', label: 'Planner Chat', icon: '🤝' },
    { id: 'blueprint', label: 'Blueprint IDE', icon: '🧠' },
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
        {activeTab === 'planner' && <PlannerPanel />}
        {activeTab === 'blueprint' && <PlannerPanelIDE />}
      </div>
    </div>
  );
}
