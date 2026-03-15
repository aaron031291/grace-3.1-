import { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../config/api";
import { useTabData } from "../hooks/useTabData";
import { brainCall } from "../api/brain-client";

// ─────────────────────────────────────────────────────────────────
// COLORS
// ─────────────────────────────────────────────────────────────────

const C = {
  bg: '#0a0b14', bgAlt: '#111420', bgPanel: '#0d0e18', bgInput: '#0c0d16',
  accent: '#e94560', blue: '#3498db', purple: '#8e44ad',
  green: '#2ecc71', red: '#e74c3c', yellow: '#f1c40f', orange: '#e67e22',
  text: '#fff', muted: '#636e72', dim: '#3d4450', border: '#1a1d2e',
};

// ─────────────────────────────────────────────────────────────────
// RESIZER
// ─────────────────────────────────────────────────────────────────

function Resizer({ onResize, direction = 'horizontal' }) {
  const dragging = useRef(false);
  const isH = direction === 'horizontal';

  const onMouseDown = (e) => {
    e.preventDefault();
    dragging.current = true;
    const move = (ev) => { if (dragging.current) onResize(isH ? ev.movementX : ev.movementY); };
    const up = () => { dragging.current = false; window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  return (
    <div onMouseDown={onMouseDown} style={{
      [isH ? 'width' : 'height']: 6,
      cursor: isH ? 'col-resize' : 'row-resize',
      background: 'transparent',
      flexShrink: 0,
      position: 'relative',
      zIndex: 5,
    }}>
      <div style={{
        position: 'absolute',
        [isH ? 'left' : 'top']: 2,
        [isH ? 'top' : 'left']: '20%',
        [isH ? 'width' : 'height']: 2,
        [isH ? 'height' : 'width']: '60%',
        background: C.border,
        borderRadius: 1,
      }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// TASK MANAGER MODAL
// ─────────────────────────────────────────────────────────────────

function TaskManagerModal({ open, onClose }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    brainCall('tasks', 'list', { limit: 50 })
      .then(r => { if (r.ok) setTasks(r.data?.tasks || r.data || []); })
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 700, maxHeight: '80vh', background: C.bgPanel, border: `1px solid ${C.border}`, borderRadius: 10, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '14px 20px', borderBottom: `1px solid ${C.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: C.text }}>📋 Task Manager</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: C.muted, fontSize: 18, cursor: 'pointer' }}>✕</button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {loading && <div style={{ color: C.muted, textAlign: 'center', padding: 30 }}>Loading tasks...</div>}
          {!loading && tasks.length === 0 && <div style={{ color: C.muted, textAlign: 'center', padding: 30 }}>No tasks found</div>}
          {tasks.map((t, i) => {
            const statusColor = t.status === 'completed' ? C.green : t.status === 'active' ? C.blue : t.status === 'failed' ? C.red : C.muted;
            return (
              <div key={t.id || i} style={{ padding: '10px 14px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.title || t.name || `Task ${i + 1}`}</div>
                  {t.description && <div style={{ fontSize: 10, color: C.muted, marginTop: 2 }}>{t.description}</div>}
                </div>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 8, background: statusColor + '20', color: statusColor, textTransform: 'uppercase' }}>{t.status || 'unknown'}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// RIGHT PANEL WIDGETS
// ─────────────────────────────────────────────────────────────────

function BrainsConnected() {
  const [brains, setBrains] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE_URL}/brain/directory`).then(r => r.ok ? r.json() : null).then(setBrains).catch(() => {});
  }, []);
  const total = brains?.total_brains || 0;
  const actions = brains?.total_actions || 0;
  return (
    <div style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>🧠 Brains Connected</div>
      <div style={{ display: 'flex', gap: 12 }}>
        <div><div style={{ fontSize: 20, fontWeight: 800, color: C.blue }}>{total}</div><div style={{ fontSize: 9, color: C.dim }}>domains</div></div>
        <div><div style={{ fontSize: 20, fontWeight: 800, color: C.purple }}>{actions}</div><div style={{ fontSize: 9, color: C.dim }}>actions</div></div>
      </div>
    </div>
  );
}

function MemoryCacheWidget() {
  const [mem, setMem] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/learn-heal/dashboard`).then(r => r.ok ? r.json() : null).then(setMem).catch(() => {});
  }, []);
  const l = mem?.learning || {};
  return (
    <div style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>💾 Memory Cache</div>
      <div style={{ fontSize: 11, color: C.text, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Examples</span><span style={{ fontWeight: 700, color: C.blue }}>{l.examples?.total || 0}</span></div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Patterns</span><span style={{ fontWeight: 700, color: C.purple }}>{l.patterns?.total || 0}</span></div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Episodes</span><span style={{ fontWeight: 700, color: C.green }}>{l.episodes || 0}</span></div>
      </div>
    </div>
  );
}

function SuccessFailureLogs() {
  const [logs, setLogs] = useState([]);
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/genesis/keys?limit=10`).then(r => r.ok ? r.json() : { keys: [] }).then(d => setLogs(d.keys || d.data || [])).catch(() => {});
  }, []);
  return (
    <div style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>📊 Success / Failure</div>
      <div style={{ maxHeight: 100, overflow: 'auto' }}>
        {logs.slice(0, 6).map((k, i) => (
          <div key={i} style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <span style={{ color: k.is_error ? C.red : C.green, fontWeight: 800 }}>{k.is_error ? '✗' : '✓'}</span>
            <span style={{ color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{k.what_description || k.what || k.title || 'event'}</span>
          </div>
        ))}
        {logs.length === 0 && <div style={{ fontSize: 10, color: C.dim }}>No recent events</div>}
      </div>
    </div>
  );
}

function TimeSenseSelfMirror() {
  const [uptime, setUptime] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/bi/dashboard`).then(r => r.ok ? r.json() : null).then(d => setUptime(d?.uptime)).catch(() => {});
  }, []);
  return (
    <div style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>⏱ Time Sense / Self Mirror</div>
      <div style={{ fontSize: 11, color: C.text }}>
        {uptime ? (
          <>
            <div>Uptime: <span style={{ fontWeight: 700, color: C.green }}>{uptime.days || 0}d {uptime.hours || 0}h</span></div>
            <div style={{ fontSize: 10, color: C.dim, marginTop: 4 }}>Grace is aware of her own runtime duration and self-state.</div>
          </>
        ) : <span style={{ color: C.dim }}>Loading...</span>}
      </div>
    </div>
  );
}

function TrustKPIWidget() {
  const [trust, setTrust] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/validation/status`).then(r => r.ok ? r.json() : null).then(setTrust).catch(() => {});
  }, []);
  const comps = trust?.components || trust?.kpis || {};
  const entries = Object.entries(comps).slice(0, 5);
  return (
    <div style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>🛡️ Trust KPIs</div>
      {entries.map(([name, info]) => {
        const score = typeof info === 'object' ? (info.trust_score ?? info.trust ?? 0) : info;
        const pct = (score * 100).toFixed(0);
        const color = score >= 0.8 ? C.green : score >= 0.5 ? C.yellow : C.red;
        return (
          <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, marginBottom: 4 }}>
            <span style={{ color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, marginRight: 6 }}>{name.replace(/_/g, ' ')}</span>
            <span style={{ fontWeight: 800, color }}>{pct}%</span>
          </div>
        );
      })}
      {entries.length === 0 && <div style={{ fontSize: 10, color: C.dim }}>No trust data yet</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PILLAR 1: PLAN & ARCHITECT
// ─────────────────────────────────────────────────────────────────

const NINE_LAYERS = [
  { id: 'perception', label: 'Perception', icon: '👁️', color: C.blue },
  { id: 'memory', label: 'Memory', icon: '🧠', color: C.purple },
  { id: 'reasoning', label: 'Reasoning', icon: '💡', color: C.yellow },
  { id: 'planning', label: 'Planning', icon: '📐', color: C.green },
  { id: 'execution', label: 'Execution', icon: '⚡', color: C.orange },
  { id: 'learning', label: 'Learning', icon: '📚', color: C.blue },
  { id: 'governance', label: 'Governance', icon: '🏛️', color: C.accent },
  { id: 'healing', label: 'Self-Healing', icon: '🔧', color: C.green },
  { id: 'identity', label: 'Identity', icon: '🪞', color: C.purple },
];

function PlanArchitect() {
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [activeLayer, setActiveLayer] = useState(null);
  const [subView, setSubView] = useState('chat');
  const scrollRef = useRef(null);

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [chatMessages]);

  const sendChat = async () => {
    if (!chatInput.trim() || sending) return;
    const msg = chatInput.trim();
    setChatInput('');
    setSending(true);
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    const r = await brainCall('chat', 'send', { message: msg, mode: 'consensus' });
    const content = r.ok ? (typeof r.data === 'string' ? r.data : r.data?.response || r.data?.message || r.data?.content || JSON.stringify(r.data)) : `Error: ${r.error}`;
    setChatMessages(prev => [...prev, { role: 'assistant', text: content }]);
    setSending(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 16 }}>🏗️</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>Plan & Architect</span>
        <div style={{ flex: 1 }} />
        <button onClick={() => setSubView('chat')} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: subView === 'chat' ? C.blue : C.bgAlt, color: subView === 'chat' ? '#fff' : C.muted }}>Consensus Chat</button>
        <button onClick={() => setSubView('layers')} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: subView === 'layers' ? C.blue : C.bgAlt, color: subView === 'layers' ? '#fff' : C.muted }}>9-Layer Board</button>
      </div>

      {subView === 'chat' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div ref={scrollRef} style={{ flex: 1, overflow: 'auto', padding: 12 }}>
            {chatMessages.length === 0 && <div style={{ color: C.dim, fontSize: 12, textAlign: 'center', padding: 30 }}>Start a conversation with Grace's consensus engine...</div>}
            {chatMessages.map((m, i) => (
              <div key={i} style={{ marginBottom: 8, display: 'flex', gap: 8 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: m.role === 'user' ? C.blue : C.green, flexShrink: 0, marginTop: 2 }}>{m.role === 'user' ? 'You' : 'Grace'}</span>
                <div style={{ fontSize: 12, color: C.text, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{m.text}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', padding: '8px 12px', gap: 8, borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
            <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendChat()}
              placeholder="Ask the consensus engine..." style={{ flex: 1, padding: '6px 10px', background: C.bgInput, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 12, outline: 'none' }} />
            <button onClick={sendChat} disabled={sending} style={{ padding: '4px 14px', background: C.blue, border: 'none', borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>
              {sending ? '...' : '→'}
            </button>
          </div>
        </div>
      )}

      {subView === 'layers' && (
        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {NINE_LAYERS.map(layer => (
              <div key={layer.id} onClick={() => setActiveLayer(activeLayer === layer.id ? null : layer.id)} style={{
                padding: 12, background: activeLayer === layer.id ? layer.color + '15' : C.bgAlt,
                border: `1px solid ${activeLayer === layer.id ? layer.color + '60' : C.border}`,
                borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 16 }}>{layer.icon}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: layer.color }}>{layer.label}</span>
                </div>
                <div style={{ fontSize: 10, color: C.dim }}>Layer status & configuration</div>
              </div>
            ))}
          </div>
          {activeLayer && (
            <div style={{ marginTop: 12, padding: 14, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 6 }}>{NINE_LAYERS.find(l => l.id === activeLayer)?.label} Layer Details</div>
              <div style={{ fontSize: 11, color: C.muted }}>Configuration, connections, and health status for this cognitive layer. Interact with the consensus engine to modify architecture.</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PILLAR 2: BUILD & REFACTOR
// ─────────────────────────────────────────────────────────────────

function BuildRefactor() {
  const [subView, setSubView] = useState('swarm');
  const [termLogs, setTermLogs] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (subView !== 'terminal') return;
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws') + '/api/autonomous/logs/stream';
    let ws, delay = 1000;
    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => setTermLogs(prev => { const n = [...prev, e.data]; return n.length > 500 ? n.slice(-500) : n; });
      ws.onopen = () => { delay = 1000; };
      ws.onclose = () => { delay = Math.min(delay * 2, 30000); setTimeout(connect, delay); };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { if (ws) { ws.onclose = null; ws.close(); } };
  }, [subView]);

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [termLogs]);

  const SWIMLANES = [
    { id: 'queued', label: 'Queued', color: C.muted },
    { id: 'active', label: 'Active', color: C.blue },
    { id: 'review', label: 'Review', color: C.yellow },
    { id: 'done', label: 'Done', color: C.green },
  ];

  const PIPELINE_STAGES = ['Ingest', 'Parse', 'Validate', 'Transform', 'Embed', 'Index', 'Verify'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 16 }}>🔨</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>Build & Refactor</span>
        <div style={{ flex: 1 }} />
        <button onClick={() => setSubView('swarm')} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: subView === 'swarm' ? C.blue : C.bgAlt, color: subView === 'swarm' ? '#fff' : C.muted }}>Swarm Swimlane</button>
        <button onClick={() => setSubView('pipeline')} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: subView === 'pipeline' ? C.blue : C.bgAlt, color: subView === 'pipeline' ? '#fff' : C.muted }}>Spindle Pipeline</button>
        <button onClick={() => setSubView('terminal')} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: subView === 'terminal' ? C.blue : C.bgAlt, color: subView === 'terminal' ? '#fff' : C.muted }}>Agent Terminal</button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {subView === 'swarm' && (
          <div style={{ display: 'flex', gap: 8, padding: 12, height: '100%' }}>
            {SWIMLANES.map(lane => (
              <div key={lane.id} style={{ flex: 1, display: 'flex', flexDirection: 'column', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, overflow: 'hidden' }}>
                <div style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: lane.color }} />
                  <span style={{ fontSize: 11, fontWeight: 700, color: lane.color }}>{lane.label}</span>
                </div>
                <div style={{ flex: 1, padding: 8 }}>
                  <div style={{ fontSize: 10, color: C.dim, textAlign: 'center', padding: 16 }}>Drop tasks here</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {subView === 'pipeline' && (
          <div style={{ padding: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12, color: C.text }}>Spindle Processing Pipeline</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ padding: '8px 14px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 11, fontWeight: 600, color: C.text }}>{stage}</div>
                  {i < PIPELINE_STAGES.length - 1 && <span style={{ color: C.dim, fontSize: 14 }}>→</span>}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, padding: 14, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: C.muted, marginBottom: 6 }}>Pipeline Status</div>
              <div style={{ fontSize: 11, color: C.dim }}>Idle — submit documents or trigger a scan to activate the pipeline.</div>
              <button onClick={() => fetch(`${API_BASE_URL}/api/problems/scan`, { method: 'POST' }).catch(() => {})} style={{ marginTop: 10, padding: '6px 14px', background: C.accent, border: 'none', borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>▶ Trigger Scan</button>
            </div>
          </div>
        )}

        {subView === 'terminal' && (
          <div ref={scrollRef} style={{ height: '100%', overflow: 'auto', padding: 12, background: '#000', fontFamily: 'monospace', fontSize: 11, lineHeight: 1.5 }}>
            {termLogs.length === 0 && <div style={{ color: C.muted }}>Connecting to live agent terminal...</div>}
            {termLogs.map((l, i) => (
              <div key={i} style={{ color: l.includes('ERROR') ? C.red : l.includes('WARN') ? C.yellow : l.includes('[OK]') || l.includes('SUCCESS') ? C.green : '#aaa' }}>{l}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// PILLAR 3: ENVIRONMENTS
// ─────────────────────────────────────────────────────────────────

function EnvironmentsPillar() {
  const [envs, setEnvs] = useState([
    { id: 'tom', name: 'Tom AI', type: 'assistant', status: 'running', model: 'qwen2.5-coder', persona: 'Technical lead focused on code quality', created: '2026-03-10' },
    { id: 'jack', name: 'Jack AI', type: 'researcher', status: 'running', model: 'deepseek-r1', persona: 'Research analyst with web search capabilities', created: '2026-03-12' },
    { id: 'bev', name: 'Bev AI', type: 'ops', status: 'stopped', model: 'kimi-k2', persona: 'DevOps engineer focused on system reliability', created: '2026-03-14' },
  ]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('assistant');
  const [newModel, setNewModel] = useState('qwen2.5-coder');
  const [newPersona, setNewPersona] = useState('');

  const createEnv = () => {
    if (!newName.trim()) return;
    setEnvs(prev => [...prev, { id: `env-${Date.now()}`, name: newName, type: newType, status: 'stopped', model: newModel, persona: newPersona, created: new Date().toISOString().slice(0, 10) }]);
    setNewName(''); setNewPersona(''); setShowCreate(false);
  };

  const toggleEnv = (id) => setEnvs(prev => prev.map(e => e.id === id ? { ...e, status: e.status === 'running' ? 'stopped' : 'running' } : e));
  const deleteEnv = (id) => setEnvs(prev => prev.filter(e => e.id !== id));

  const typeIcons = { assistant: '🤖', researcher: '🔬', ops: '🔧', creative: '🎨', security: '🛡️' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 16 }}>🧬</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>Environments</span>
        <div style={{ flex: 1 }} />
        <button onClick={() => setShowCreate(!showCreate)} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 700, border: 'none', borderRadius: 4, cursor: 'pointer', background: C.purple, color: '#fff' }}>+ New</button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {showCreate && (
          <div style={{ background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 14, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Create Agent Environment</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
              <div>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 3 }}>Name</div>
                <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Sarah AI" style={{ width: '100%', padding: '6px 8px', background: C.bgInput, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 11, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <div>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 3 }}>Type</div>
                <select value={newType} onChange={e => setNewType(e.target.value)} style={{ width: '100%', padding: '6px 8px', background: C.bgInput, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 11 }}>
                  <option value="assistant">Assistant</option><option value="researcher">Researcher</option><option value="ops">Ops Engineer</option><option value="creative">Creative</option><option value="security">Security</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 3 }}>Model</div>
                <select value={newModel} onChange={e => setNewModel(e.target.value)} style={{ width: '100%', padding: '6px 8px', background: C.bgInput, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 11 }}>
                  <option value="qwen2.5-coder">Qwen 2.5 Coder</option><option value="deepseek-r1">DeepSeek R1</option><option value="kimi-k2">Kimi K2</option><option value="consensus">All Models (Consensus)</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 3 }}>Persona</div>
                <input value={newPersona} onChange={e => setNewPersona(e.target.value)} placeholder="Role description..." style={{ width: '100%', padding: '6px 8px', background: C.bgInput, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 11, outline: 'none', boxSizing: 'border-box' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={createEnv} style={{ padding: '6px 14px', background: C.green, border: 'none', borderRadius: 4, color: '#fff', fontWeight: 700, fontSize: 11, cursor: 'pointer' }}>Create</button>
              <button onClick={() => setShowCreate(false)} style={{ padding: '6px 14px', background: C.bgPanel, border: `1px solid ${C.border}`, borderRadius: 4, color: C.muted, fontSize: 11, cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        )}

        {envs.map(e => (
          <div key={e.id} style={{ background: C.bgAlt, border: `1px solid ${e.status === 'running' ? C.green + '40' : C.border}`, borderRadius: 8, padding: 12, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 24 }}>{typeIcons[e.type] || '🤖'}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <span style={{ fontSize: 13, fontWeight: 700 }}>{e.name}</span>
                <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 8, background: e.status === 'running' ? C.green + '20' : C.red + '20', color: e.status === 'running' ? C.green : C.red, fontWeight: 700 }}>{e.status.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10, color: C.muted }}>{e.persona}</div>
              <div style={{ fontSize: 9, color: C.dim, marginTop: 2 }}>Model: {e.model} · {e.created}</div>
            </div>
            <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
              <button onClick={() => toggleEnv(e.id)} style={{ padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontWeight: 700, background: e.status === 'running' ? C.red + '20' : C.green + '20', color: e.status === 'running' ? C.red : C.green }}>
                {e.status === 'running' ? '■ Stop' : '▶ Start'}
              </button>
              <button onClick={() => deleteEnv(e.id)} style={{ padding: '4px 8px', border: `1px solid ${C.border}`, borderRadius: 4, cursor: 'pointer', fontSize: 10, color: C.muted, background: 'transparent' }}>🗑</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ROOT: CUSTOMER-FACING WORKSPACE
// ─────────────────────────────────────────────────────────────────

const PILLAR_TABS = [
  { id: 'plan', label: 'Plan & Architect', icon: '🏗️' },
  { id: 'build', label: 'Build & Refactor', icon: '🔨' },
  { id: 'envs', label: 'Environments', icon: '🧬' },
];

export default function DevTab() {
  const [activePillar, setActivePillar] = useState('plan');
  const [rightWidth, setRightWidth] = useState(240);
  const [showTaskMgr, setShowTaskMgr] = useState(false);

  const { data: dashData } = useTabData('/api/bi/dashboard', { uptime: { days: 0, hours: 0 }, documents: { total: 0 }, chats: { total_chats: 0 } }, { poll: 30000 });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg, color: C.text, fontFamily: "'Inter', -apple-system, sans-serif" }}>

      {/* ── TOP HEADER ── */}
      <div style={{ height: 44, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', borderBottom: `1px solid ${C.border}`, background: C.bgPanel, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18 }}>⚡</span>
          <span style={{ fontSize: 15, fontWeight: 800, color: C.text }}>Grace 3.1</span>
          <span style={{ fontSize: 11, color: C.muted }}>Developer Workspace</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {dashData && (
            <div style={{ display: 'flex', gap: 14, fontSize: 10, color: C.muted }}>
              <span>📄 {dashData.documents?.total || 0} docs</span>
              <span>💬 {dashData.chats?.total_chats || 0} chats</span>
              <span>⏱ {dashData.uptime?.days || 0}d {dashData.uptime?.hours || 0}h</span>
            </div>
          )}
          <button onClick={() => setShowTaskMgr(true)} style={{ padding: '4px 12px', background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 4, color: C.muted, fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>📋 Tasks</button>
        </div>
      </div>

      {/* ── PILLAR TABS ── */}
      <div style={{ display: 'flex', borderBottom: `1px solid ${C.border}`, background: C.bgPanel, flexShrink: 0 }}>
        {PILLAR_TABS.map(t => (
          <button key={t.id} onClick={() => setActivePillar(t.id)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px', border: 'none', cursor: 'pointer',
            background: 'transparent', color: activePillar === t.id ? C.blue : C.muted, fontSize: 12, fontWeight: activePillar === t.id ? 700 : 500,
            borderBottom: activePillar === t.id ? `2px solid ${C.blue}` : '2px solid transparent',
          }}>
            <span style={{ fontSize: 14 }}>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* ── MAIN BODY ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Main content area */}
        <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
          {activePillar === 'plan' && <PlanArchitect />}
          {activePillar === 'build' && <BuildRefactor />}
          {activePillar === 'envs' && <EnvironmentsPillar />}
        </div>

        {/* Resizer */}
        <Resizer onResize={(dx) => setRightWidth(w => Math.max(180, Math.min(400, w - dx)))} />

        {/* Right Panel */}
        <div style={{ width: rightWidth, flexShrink: 0, borderLeft: `1px solid ${C.border}`, background: C.bgPanel, overflowY: 'auto', padding: 10 }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: C.muted, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 10, padding: '0 2px' }}>System Widgets</div>
          <BrainsConnected />
          <MemoryCacheWidget />
          <SuccessFailureLogs />
          <TimeSenseSelfMirror />
          <TrustKPIWidget />
        </div>
      </div>

      {/* Task Manager Modal */}
      <TaskManagerModal open={showTaskMgr} onClose={() => setShowTaskMgr(false)} />
    </div>
  );
}
