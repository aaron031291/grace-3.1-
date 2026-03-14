import { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../config/api";
import { brainCall } from '../api/brain-client';

const C = {
  bg: '#0a0a1a', bgAlt: '#0d0d22', bgDark: '#08081a',
  accent: '#e94560', accentAlt: '#3b82f6',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#1a1a2e',
  success: '#10b981', warn: '#f59e0b', error: '#ef4444', info: '#3b82f6',
};

const PILLARS = [
  { id: "plan", label: "Plan & Architect", icon: "🗺️", desc: "Consensus chat to ideate and break down concepts into the 9-layer coding architecture." },
  { id: "build", label: "Build & Refactor", icon: "🏗️", desc: "Unified prompt to build/fix, triggering the 8-layer pipeline with a 1-click Approve & Deploy." },
  { id: "diagnose", label: "Diagnose & Heal", icon: "🏥", desc: "Autopilot Diagnostics combining probes, triggers, and invariant checks with auto-heal." },
  { id: "observe", label: "Trace & Observe", icon: "📡", desc: "Unified observability dashboard for system health, loops, and trust scores." },
  { id: "govern", label: "Govern & Learn", icon: "🏛️", desc: "Central Context Hub for uploading rules, schemas, and tracking knowledge gaps." },
];

export default function DevTab() {
  const [activePillar, setActivePillar] = useState("plan");
  const [leftWidth, setLeftWidth] = useState(240);
  const [rightWidth, setRightWidth] = useState(300);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [isTaskManagerOpen, setIsTaskManagerOpen] = useState(false);

  // Provide initial layout structure
  return (
    <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, overflow: "hidden", fontFamily: "'Inter', sans-serif" }}>

      {/* ── Panel 1: Navigation & Strategic Pillars ── */}
      {!leftCollapsed ? (
        <>
          <div style={{ width: leftWidth, display: "flex", flexDirection: "column", borderRight: `1px solid ${C.border}`, background: C.bgDark, flexShrink: 0 }}>
            <div style={{ padding: "16px", borderBottom: `1px solid ${C.border}`, background: C.bgAlt }}>
              <span style={{ fontSize: 13, fontWeight: 800, color: C.accent, letterSpacing: 1, textTransform: "uppercase" }}>Dev Lab</span>
            </div>
            <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
              {PILLARS.map(p => (
                <button
                  key={p.id} onClick={() => setActivePillar(p.id)} title={p.desc}
                  style={{
                    display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                    background: activePillar === p.id ? '#1a1a3a' : 'transparent',
                    border: "none", borderRadius: 8, cursor: "pointer",
                    color: activePillar === p.id ? C.text : C.muted,
                    textAlign: "left", fontSize: 13, fontWeight: activePillar === p.id ? 700 : 500,
                    borderLeft: activePillar === p.id ? `3px solid ${C.accent}` : "3px solid transparent",
                    transition: "all 0.2s ease"
                  }}
                  onMouseEnter={e => { if (activePillar !== p.id) e.currentTarget.style.background = '#12122a'; }}
                  onMouseLeave={e => { if (activePillar !== p.id) e.currentTarget.style.background = 'transparent'; }}
                >
                  <span style={{ fontSize: 18 }}>{p.icon}</span>
                  <span>{p.label}</span>
                </button>
              ))}
            </div>
          </div>
          <Resizer onResize={(dx) => setLeftWidth(w => Math.max(180, Math.min(400, w + dx)))} />
        </>
      ) : (
        <button onClick={() => setLeftCollapsed(false)} style={{ width: 32, background: C.bgAlt, border: "none", borderRight: `1px solid ${C.border}`, color: C.muted, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ writingMode: "vertical-lr", fontSize: 12, letterSpacing: 2 }}>PILLARS ▸</span>
        </button>
      )}

      {/* ── Panel 2: The Execution Arena ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 12, background: C.bgAlt }}>
          {leftCollapsed && <button onClick={() => setLeftCollapsed(false)} style={iconBtn}>☰</button>}
          <span style={{ fontSize: 15, fontWeight: 700, color: C.text }}>
            {PILLARS.find(p => p.id === activePillar)?.label}
          </span>
          <div style={{ flex: 1 }} />
          {rightCollapsed && <button onClick={() => setRightCollapsed(false)} style={iconBtn}>◧</button>}
        </div>

        <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
          {activePillar === "plan" && <PlanArena setActivePillar={setActivePillar} />}
          {activePillar === "build" && <BuildArena onOpenTaskManager={() => setIsTaskManagerOpen(true)} />}
          {activePillar === "diagnose" && <DiagnoseArena />}
          {activePillar === "observe" && <ObserveArena />}
          {activePillar === "govern" && <GovernArena />}
        </div>
      </div>

      {/* ── Panel 3: Localized Intelligence & Memory Context ── */}
      {!rightCollapsed ? (
        <>
          <Resizer onResize={(dx) => setRightWidth(w => Math.max(260, Math.min(600, w - dx)))} />
          <div style={{ width: rightWidth, display: "flex", flexDirection: "column", borderLeft: `1px solid ${C.border}`, background: C.bgDark, flexShrink: 0 }}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center", background: C.bgAlt }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: C.dim, letterSpacing: 1, textTransform: "uppercase" }}>Localized Intelligence</span>
              <button onClick={() => setRightCollapsed(true)} style={iconBtn}>×</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 20 }}>
              <BrainsConnected />
              <MemoryCacheWidget />
              <SuccessFailureLogs />
              <TimeSenseSelfMirror />
              <TrustKPIWidget />
            </div>
          </div>
        </>
      ) : null}

      {/* ── Global Task Manager Modal ── */}
      {isTaskManagerOpen && <TaskManagerModal onClose={() => setIsTaskManagerOpen(false)} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ARENAS (Center Panel)
// ─────────────────────────────────────────────────────────────────

function PlanArena({ setActivePillar }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Welcome to the 9-Layer Architect. Describe your concept, and Qwen, DeepSeek, and Kimi will discuss it and break it down into an executable 9-layer architectural plan, including Technical Specs.' }
  ]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const toggleVoice = () => setIsRecording(!isRecording);
  const [layers, setLayers] = useState([
    { id: 1, name: "Runtime & Environment", status: "pending", desc: "Waiting for input..." },
    { id: 2, name: "Decompose & Plan", status: "pending", desc: "Waiting for input..." },
    { id: 3, name: "Technical Specs", status: "pending", desc: "Waiting for input..." },
    { id: 4, name: "Propose Code", status: "pending", desc: "Waiting for input..." },
    { id: 5, name: "Select & Prune", status: "pending", desc: "Waiting for input..." },
    { id: 6, name: "Simulate & Check", status: "pending", desc: "Waiting for input..." },
    { id: 7, name: "Generate & Synthesize", status: "pending", desc: "Waiting for input..." },
    { id: 8, name: "Verify Invariants", status: "pending", desc: "Waiting for input..." },
    { id: 9, name: "Deploy & Commit", status: "pending", desc: "Waiting for input..." }
  ]);

  const [sending, setSending] = useState(false);

  const send = async () => {
    if (!input.trim() || sending) return;
    const userMsg = input;
    setMessages(p => [...p, { role: 'user', content: userMsg }]);
    setInput('');
    setSending(true);
    try {
      let result = await brainCall('ai', 'consensus_chat', { message: userMsg });
      if (!result.ok) {
        result = await brainCall('chat', 'send', { message: userMsg });
      }
      if (result.ok && result.data) {
        const content = typeof result.data === 'string' ? result.data
          : result.data.response || result.data.message || result.data.content || JSON.stringify(result.data);
        setMessages(p => [...p, { role: 'assistant', provider: result.data.provider || 'Grace', content }]);
      } else {
        setMessages(p => [...p, { role: 'assistant', provider: 'System', content: `⚠️ ${result.error || 'No response from backend.'}` }]);
      }
    } catch (err) {
      setMessages(p => [...p, { role: 'assistant', provider: 'System', content: `⚠️ Error: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const deploySubAgents = () => {
    // Bridge to Build Arena
    setActivePillar("build");
  };

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Consensus Chat */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}` }}>
        <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, fontSize: 13, fontWeight: 700, color: C.muted, background: C.bgAlt }}>
          🧠 Multi-Model Consensus Chat
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.map((m, i) => (
            <div key={i} style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? '#1e3a8a' : C.bgAlt,
              padding: '10px 14px', borderRadius: 8, maxWidth: '85%',
              border: `1px solid ${C.border}`
            }}>
              {m.role !== 'user' && <div style={{ fontSize: 10, color: C.accentAlt, marginBottom: 4, fontWeight: 700 }}>{m.provider || 'System'}</div>}
              <div style={{ fontSize: 13, lineHeight: 1.5 }}>{m.content}</div>
            </div>
          ))}
        </div>
        <div style={{ padding: 16, borderTop: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={toggleVoice} style={{ background: isRecording ? '#ef444433' : C.bg, color: isRecording ? C.error : C.text, border: `1px solid ${isRecording ? C.error : C.border}`, borderRadius: '50%', width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
            {isRecording ? "🔴" : "🎤"}
          </button>
          <input
            value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
            placeholder={isRecording ? "Listening... Speak your idea clearly." : "Describe your idea (e.g., 'We need a robust caching layer for the Dev Lab')..."}
            style={{ flex: 1, padding: '10px 14px', background: C.bg, border: `1px solid ${isRecording ? C.error : C.border}`, borderRadius: 6, color: C.text, outline: 'none' }}
          />
          <button onClick={send} disabled={sending} style={{ padding: '0 20px', height: 40, background: sending ? C.dim : C.accent, color: '#fff', border: 'none', borderRadius: 6, fontWeight: 600, cursor: sending ? 'wait' : 'pointer' }}>{sending ? '...' : 'Send'}</button>
        </div>
      </div>

      {/* 9-Layer Visualizer */}
      <div style={{ width: 350, background: C.bg, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, fontSize: 13, fontWeight: 700, color: C.muted, background: C.bgAlt, display: 'flex', justifyContent: 'space-between' }}>
          <span>🏗️ 9-Layer Architecture Board</span>
          <button style={{ background: 'none', border: 'none', color: C.accentAlt, cursor: 'pointer', fontSize: 11 }}>Edit Specs ✎</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {layers.map(l => (
            <div key={l.id} style={{
              padding: 12, marginBottom: 12, borderRadius: 6,
              background: l.status === 'active' ? '#1e3a8a33' : C.bgAlt,
              border: `1px solid ${l.status === 'active' ? C.accentAlt : C.border}`,
              borderLeft: `4px solid ${l.status === 'active' ? C.accentAlt : l.status === 'done' ? C.success : C.dim}`
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: l.status === 'active' ? '#fff' : C.text, marginBottom: 4 }}>Layer {l.id}: {l.name}</div>
              <div style={{ fontSize: 11, color: C.muted, lineHeight: 1.4 }}>{l.desc}</div>
            </div>
          ))}
        </div>
        <div style={{ padding: 16, borderTop: `1px solid ${C.border}` }}>
          <button onClick={deploySubAgents} style={{ width: '100%', padding: '12px', background: C.success, color: '#000', border: 'none', borderRadius: 6, fontWeight: 800, fontSize: 13, cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
            🚀 Deploy Autonomous Sub-Agents
          </button>
        </div>
      </div>
    </div>
  );
}

function BuildArena({ onOpenTaskManager }) {
  const [prompt, setPrompt] = useState("");
  const [activeTask, setActiveTask] = useState(null);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Listen for tasks launched from the Context Menu
  useEffect(() => {
    const handleTaskStarted = (e) => {
      const { taskId, artifactName, intent } = e.detail;
      setActiveTask({ id: taskId, name: artifactName, intent });
      setLogs([`>>> Conecting to Dev Lab Task Queue...`, `>>> Task ID: ${taskId}`, `>>> Artifact: ${artifactName}`, `>>> Intent: ${intent}`]);

      // Open SSE Connection
      const eventSource = new EventSource(`${API_BASE_URL}/api/devlab/stream/${taskId}`);

      eventSource.onmessage = (event) => {
        setLogs(prev => [...prev, event.data]);
        if (event.data.includes("[END OF STREAM]")) {
          eventSource.close();
        }
      };

      eventSource.onerror = () => {
        setLogs(prev => [...prev, "[ERROR] Connection to Task Stream lost."]);
        eventSource.close();
      };

      return () => eventSource.close();
    };

    window.addEventListener('DEVLAB_TASK_STARTED', handleTaskStarted);
    return () => window.removeEventListener('DEVLAB_TASK_STARTED', handleTaskStarted);
  }, []);

  const [swarmTasks, setSwarmTasks] = useState([]);

  // Fetch live swarm tasks recursively
  useEffect(() => {
    let active = true;
    const fetchSwarm = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/devlab/swarm`);
        if (res.ok && active) {
          const d = await res.json();
          setSwarmTasks(d.tasks || []);
        }
      } catch {
        // silent fail for polling
      }
      if (active) {
        setTimeout(fetchSwarm, 2000);
      }
    };

    fetchSwarm();
    return () => { active = false; };
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: 24, overflowY: "auto", background: C.bg }}>
      {/* ── Active Swarm Swimlane ── */}
      <div style={{ marginBottom: 30, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.dim, textTransform: 'uppercase', letterSpacing: 1 }}>🐝 Active Swarm Swimlane</div>
          <button onClick={onOpenTaskManager} style={{ background: C.bg, border: `1px solid ${C.border}`, color: C.text, fontSize: 11, padding: '4px 10px', borderRadius: 4, cursor: 'pointer', transition: 'all 0.2s' }} onMouseEnter={e => e.currentTarget.style.borderColor = C.accentAlt} onMouseLeave={e => e.currentTarget.style.borderColor = C.border}>Open Task Manager ⛭</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {swarmTasks.map(t => (
            <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 16, background: C.bgDark, padding: '10px 14px', borderRadius: 6, border: `1px solid ${C.border}` }}>
              <div style={{ width: 60, fontSize: 10, fontWeight: 800, color: t.status === 'done' ? C.success : t.status === 'running' ? C.info : C.muted, textTransform: 'uppercase' }}>
                {t.status}
              </div>
              <div style={{ width: 180, fontSize: 12, fontWeight: 600 }}>{t.name}</div>
              <div style={{ flex: 1, height: 6, background: C.bg, borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${t.progress}%`, height: '100%', background: t.status === 'done' ? C.success : C.info, transition: 'width 0.5s ease' }} />
              </div>
              <div style={{ width: 40, fontSize: 11, color: C.muted, textAlign: 'right' }}>{t.progress}%</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 8 }}>Build & Refactor Pipeline</div>
      <div style={{ fontSize: 13, color: C.muted, marginBottom: 24 }}>Describe what to build. Grace will run the 8-layer generation pipeline, verify invariants, and propose a ready-to-deploy patch.</div>
      <textarea
        value={prompt} onChange={e => setPrompt(e.target.value)}
        placeholder="e.g., 'Add a new endpoint to api.py that returns user statistics, and upate the frontend dashboard to display it.'"
        style={{ height: 120, padding: 16, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontSize: 14, resize: "none", outline: "none", fontFamily: "inherit", marginBottom: 16, flexShrink: 0 }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button onClick={async () => {
          setActiveTask({ id: "SPINDLE_DAEMON", name: "Spindle Autonomous Daemon", intent: "Parallel Peer Process" });
          setLogs([">>> Connecting to Dev Lab Task Queue...", ">>> Launching Spindle Daemon..."]);
          try {
            await fetch(`${API_BASE_URL}/api/devlab/start_spindle`, { method: "POST" });
            const eventSource = new EventSource(`${API_BASE_URL}/api/devlab/stream/SPINDLE_DAEMON`);
            eventSource.onmessage = (event) => {
              setLogs(prev => [...prev, event.data]);
              if (event.data.includes("[END OF STREAM]")) eventSource.close();
            };
            eventSource.onerror = () => {
              setLogs(prev => [...prev, "[ERROR] Connection to Task Stream lost."]);
              eventSource.close();
            };
          } catch (e) {
            setLogs(prev => [...prev, `[ERROR] Failed to start Spindle: ${e.message}`]);
          }
        }} style={{ padding: "12px 24px", background: "#7c3aed", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
          🚀 Launch Isolated Spindle Daemon
        </button>
        <button style={{ padding: "12px 24px", background: C.accent, border: "none", borderRadius: 6, color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
          Run Build Pipeline
        </button>
      </div>

      {/* Live Agent Terminal */}
      <div style={{ marginTop: 24, flex: 1, minHeight: 400, display: 'flex', flexDirection: 'column', background: '#000', borderRadius: 8, border: `1px solid ${C.border}`, overflow: 'hidden' }}>
        <div style={{ padding: '8px 16px', background: C.bgAlt, borderBottom: `1px solid ${C.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.dim, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>🖥️</span> Live Agent Terminal
            {activeTask && <span style={{ padding: '2px 6px', background: C.accentAlt, color: '#fff', borderRadius: 4, fontSize: 10 }}>{activeTask.id}</span>}
          </div>

        </div>
        <div style={{ flex: 1, padding: 16, overflowY: 'auto', fontFamily: 'monospace', fontSize: 12, color: '#0f0', lineHeight: 1.6 }}>
          {!activeTask ? (
            <div style={{ color: C.dim }}>[ Waiting for task execution... Context-click a file in Code Base to start an agent ]</div>
          ) : (
            <>
              {logs.map((log, i) => (
                <div key={i} style={{
                  color: log.includes('[ERROR]') ? '#ff5555' :
                    log.includes('[SYSTEM]') ? '#55ffff' :
                      log.includes('[VERIFY]') ? '#ffff55' : '#55ff55'
                }}>
                  {log}
                </div>
              ))}
              <div ref={logsEndRef} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function DiagnoseArena() {
  const [diagStatus, setDiagStatus] = useState("idle"); // idle, running, success, error
  const [healthData, setHealthData] = useState(null);
  const [diagError, setDiagError] = useState(null);

  const runDiagnostic = async () => {
    setDiagStatus('running');
    setDiagError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/system-health/dashboard`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHealthData(data);
      setDiagStatus('success');
    } catch (err) {
      setDiagError(err.message);
      setDiagStatus('error');
    }
  };

  return (
    <div style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ background: '#f59e0b15', borderLeft: `4px solid ${C.warn}`, padding: 20, borderRadius: "0 8px 8px 0", marginBottom: 24 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: C.warn, marginBottom: 8 }}>Autopilot Diagnostics</div>
        <div style={{ fontSize: 13, color: '#ddd', lineHeight: 1.6 }}>
          Grace will run the full suite: Dependency checks, network probes, trigger invariant evaluation, and test suite execution. It will identify root causes and propose playbook fixes.
        </div>
        <button
          onClick={runDiagnostic} disabled={diagStatus === 'running'}
          style={{ marginTop: 16, padding: "10px 24px", background: C.warn, border: "none", borderRadius: 6, color: "#000", fontSize: 13, fontWeight: 800, cursor: diagStatus === 'running' ? 'wait' : 'pointer' }}
        >
          {diagStatus === 'running' ? 'Running Diagnostics...' : 'Run Full Diagnostic Spin'}
        </button>
      </div>

      {diagStatus === 'error' && (
        <div style={{ padding: 16, background: '#ef444422', border: `1px solid ${C.error}`, borderRadius: 8, color: C.error, fontSize: 13 }}>
          ⚠️ Diagnostic failed: {diagError}
        </div>
      )}

      {/* ── Health Results ── */}
      {diagStatus === 'success' && healthData && (
        <div style={{ marginTop: 20, animation: 'fadeIn 0.5s ease' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.accentAlt, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>✨ Diagnostic Results</div>
          <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 12 }}>
            Overall: <span style={{ color: healthData.overall_status === 'healthy' ? C.success : C.warn }}>{healthData.overall_status || 'Unknown'}</span>
          </div>
          {healthData.services && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
              {Object.entries(healthData.services).map(([name, info]) => (
                <div key={name} style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{name}</div>
                  <div style={{ fontSize: 13, color: (info.status || info) === 'healthy' ? C.success : C.warn }}>{info.status || String(info)}</div>
                </div>
              ))}
            </div>
          )}
          {!healthData.services && (
            <pre style={{ padding: 12, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 11, color: C.muted, overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(healthData, null, 2)}
            </pre>
          )}

          <div style={{ marginTop: 24, borderTop: `1px solid ${C.border}`, paddingTop: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>Continuous Refinement Ecosystem</div>
            <div style={{ fontSize: 13, color: C.muted, marginBottom: 20 }}>Your code is functionally correct. Would you like to spawn a sub-agent loop to elevate it to a Platinum Standard?</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
              {['Optimize for Speed', 'Enterprise Readability', 'Security Hardening'].map(std => (
                <div key={std} style={{ padding: 16, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, transition: 'all 0.2s ease' }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = C.accentAlt}
                  onMouseLeave={e => e.currentTarget.style.borderColor = C.border}
                >
                  <div style={{ fontSize: 24 }}>{std === 'Optimize for Speed' ? '⚡' : std === 'Enterprise Readability' ? '📖' : '🛡️'}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, textAlign: 'center' }}>{std}</div>
                  <button style={{ width: '100%', padding: '8px', background: 'transparent', border: `1px solid ${C.accentAlt}`, color: C.accentAlt, borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Iterate & Elevate</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ObserveArena() {
  const [health, setHealth] = useState(null);
  const [components, setComponents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [healthRes, compRes] = await Promise.allSettled([
          fetch(`${API_BASE_URL}/api/system-health/dashboard`),
          fetch(`${API_BASE_URL}/api/component-health/status`),
        ]);
        if (active && healthRes.status === 'fulfilled' && healthRes.value.ok) {
          setHealth(await healthRes.value.json());
        }
        if (active && compRes.status === 'fulfilled' && compRes.value.ok) {
          setComponents(await compRes.value.json());
        }
        if (active && healthRes.status === 'rejected' && compRes.status === 'rejected') {
          setError('Could not reach backend health endpoints.');
        }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchData();
    return () => { active = false; };
  }, []);

  const statusColor = (s) => {
    if (!s) return C.muted;
    const sl = String(s).toLowerCase();
    if (sl === 'healthy' || sl === 'running' || sl === 'ok' || sl === 'up') return C.success;
    if (sl === 'degraded' || sl === 'idle' || sl === 'warning') return C.warn;
    return C.error;
  };

  return (
    <div style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>System Observability Dashboard</div>

      {loading && <div style={{ fontSize: 13, color: C.muted }}>Loading system health...</div>}
      {error && <div style={{ fontSize: 13, color: C.error, marginBottom: 16 }}>⚠️ {error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div style={{ padding: 20, background: C.bgAlt, borderRadius: 8, border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.dim, textTransform: 'uppercase', marginBottom: 16 }}>Overall System Status</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: statusColor(health?.overall_status) }}>
            {health?.overall_status?.toUpperCase() || (loading ? '...' : 'UNKNOWN')}
          </div>
          {health?.uptime && <div style={{ fontSize: 12, color: C.muted, marginTop: 8 }}>Uptime: {health.uptime}</div>}
        </div>
        <div style={{ padding: 20, background: C.bgAlt, borderRadius: 8, border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.dim, textTransform: 'uppercase', marginBottom: 16 }}>Core Infrastructure</div>
          <div style={{ fontSize: 13, lineHeight: 1.8 }}>
            {health?.services ? (
              Object.entries(health.services).map(([name, info]) => (
                <div key={name}>{name}: <span style={{ color: statusColor(info.status || info) }}>{info.status || String(info)}</span></div>
              ))
            ) : (
              <div style={{ color: C.muted }}>{loading ? 'Loading...' : 'No service data'}</div>
            )}
          </div>
        </div>
      </div>

      {components && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Component Health</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {(Array.isArray(components) ? components : Object.entries(components).map(([k, v]) => ({ name: k, ...( typeof v === 'object' ? v : { status: v }) }))).map((c, i) => (
              <div key={c.name || i} style={{ padding: 12, background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{c.name || `Component ${i}`}</div>
                <div style={{ fontSize: 13, color: statusColor(c.status) }}>{c.status || 'unknown'}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function GovernArena() {
  return (
    <div style={{ padding: 24, height: '100%' }}>
      <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Central Context Hub</div>
      <div style={{ border: `2px dashed ${C.border}`, borderRadius: 8, padding: 40, textAlign: 'center', background: C.bgAlt }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📥</div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Drop Context Files Here</div>
        <div style={{ fontSize: 13, color: C.muted, maxWidth: 400, margin: '0 auto' }}>Upload project zip, schema definitions, config files, or governance rules. Grace will auto-categorize and inject them.</div>
        <div style={{ marginTop: 16, fontSize: 12, color: C.accentAlt, fontWeight: 600 }}>💡 Upload files using the Docs tab for full ingestion</div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// RIGHT PANEL WIDGETS (Localized Intelligence)
// ─────────────────────────────────────────────────────────────────

const widgetCard = { background: C.bgAlt, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16 };
const widgetTitle = { fontSize: 11, fontWeight: 700, color: C.text, marginBottom: 12, display: "flex", alignItems: "center", gap: 8, textTransform: 'uppercase', letterSpacing: 0.5 };

function BrainsConnected() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    brainCall('system', 'runtime', {}).then(result => {
      if (!active) return;
      setLoading(false);
      if (result.ok) setData(result.data);
      else setError(result.error);
    });
    return () => { active = false; };
  }, []);

  return (
    <div style={widgetCard}>
      <div style={widgetTitle}>🧠 Brains Connected (Synapses)</div>
      {loading && <div style={{ fontSize: 11, color: C.muted }}>Loading...</div>}
      {error && <div style={{ fontSize: 11, color: C.error }}>⚠️ {error}</div>}
      {data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {data.brains ? Object.entries(data.brains).map(([name, info]) => (
            <div key={name} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, padding: "6px 10px", background: C.bg, borderRadius: 4, border: `1px solid ${C.border}` }}>
              <span style={{ color: C.text }}>{name}</span>
              <span style={{ color: info.connected || info.status === 'ok' ? C.success : C.warn }}>{info.status || (info.connected ? 'connected' : 'offline')}</span>
            </div>
          )) : (
            <pre style={{ fontSize: 10, color: C.muted, whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(data, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}

function MemoryCacheWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/learn-heal/dashboard`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(d => { if (active) { setData(d); setLoading(false); } })
      .catch(err => { if (active) { setError(err.message); setLoading(false); } });
    return () => { active = false; };
  }, []);

  return (
    <div style={widgetCard}>
      <div style={widgetTitle}>💾 Memory Cache & Snapshots</div>
      {loading && <div style={{ fontSize: 11, color: C.muted }}>Loading...</div>}
      {error && <div style={{ fontSize: 11, color: C.error }}>⚠️ {error}</div>}
      <div style={{ fontSize: 12, color: C.text, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Episodic Records:</span> <span style={{ color: C.muted }}>{data?.episodic_count ?? data?.episodic_records ?? '—'}</span></div>
        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Learning Concepts:</span> <span style={{ color: C.muted }}>{data?.concept_count ?? data?.learning_concepts ?? '—'}</span></div>
        <div style={{ display: "flex", justifyContent: "space-between" }}><span>Procedural Rules:</span> <span style={{ color: C.muted }}>{data?.procedural_count ?? data?.procedural_rules ?? '—'}</span></div>
        <button style={{ marginTop: 8, padding: "6px 0", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, color: C.accentAlt, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>Explore Memory Graph →</button>
      </div>
    </div>
  );
}

function SuccessFailureLogs() {
  return (
    <div style={widgetCard}>
      <div style={widgetTitle}>📋 Playbook Logs</div>
      <div style={{ display: "flex", gap: 4, height: 10, borderRadius: 5, overflow: "hidden", marginBottom: 10 }}>
        <div style={{ width: "80%", background: C.success }} />
        <div style={{ width: "20%", background: C.error }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted }}>
        <span style={{ color: C.success }}>32 Successes</span>
        <span style={{ color: C.error }}>8 Failures</span>
      </div>
    </div>
  );
}

function TimeSenseSelfMirror() {
  return (
    <div style={widgetCard}>
      <div style={widgetTitle}>🪞 TimeSense & Self-Mirror</div>
      <div style={{ fontSize: 12, color: C.text }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: C.success, fontSize: 10 }}>●</span> Sunday, 08:00 (Off-Hours)
        </div>
        <div style={{ marginTop: 10, padding: 10, background: C.bg, borderRadius: 6, borderLeft: `3px solid ${C.accentAlt}`, fontSize: 11, fontStyle: "italic", color: C.muted, lineHeight: 1.4 }}>
          "System resources are stable. Context window is clear. Ready to process complex architectural planning."
        </div>
      </div>
    </div>
  );
}

function TrustKPIWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/kpi/dashboard`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(d => { if (active) { setData(d); setLoading(false); } })
      .catch(err => { if (active) { setError(err.message); setLoading(false); } });
    return () => { active = false; };
  }, []);

  const models = data?.models || data?.trust_scores || data?.kpis;

  return (
    <div style={widgetCard}>
      <div style={widgetTitle}>🛡️ Trust Progress KPIs</div>
      {loading && <div style={{ fontSize: 11, color: C.muted }}>Loading...</div>}
      {error && <div style={{ fontSize: 11, color: C.error }}>⚠️ {error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {models ? (
          (Array.isArray(models) ? models : Object.entries(models).map(([k, v]) => ({ name: k, ...(typeof v === 'object' ? v : { score: v }) }))).map((m, i) => (
            <ModelTrust key={m.name || i} name={m.name || `Model ${i}`} score={m.score ?? m.trust ?? 0} trend={m.trend || 'flat'} />
          ))
        ) : (
          <>
            <ModelTrust name="Qwen (Coding)" score={0} trend="flat" />
            <ModelTrust name="DeepSeek (Logic)" score={0} trend="flat" />
            <ModelTrust name="Kimi (Search)" score={0} trend="flat" />
          </>
        )}
      </div>
    </div>
  );
}

function ModelTrust({ name, score, trend }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, padding: "4px 0" }}>
      <span style={{ color: C.text }}>{name}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: score > 0.9 ? C.success : C.warn, fontWeight: 700 }}>{score.toFixed(2)}</span>
        <span style={{ color: trend === "up" ? C.success : C.muted, fontSize: 10 }}>{trend === "up" ? "▲" : "▶"}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SHARED UTILS
// ─────────────────────────────────────────────────────────────────

function Resizer({ onResize }) {
  const handleMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const onMove = (ev) => onResize(ev.clientX - startX);
    const onUp = () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };
  return (
    <div onMouseDown={handleMouseDown} style={{ width: 4, cursor: "col-resize", background: "transparent", flexShrink: 0 }}
      onMouseEnter={e => e.currentTarget.style.background = '#e9456033'} onMouseLeave={e => e.currentTarget.style.background = "transparent"} />
  );
}

const iconBtn = { background: "none", border: "none", color: C.muted, cursor: "pointer", fontSize: 16, padding: 4, borderRadius: 4 };

function TaskManagerModal({ onClose }) {
  const taskGroups = [
    {
      title: "Active Bridging Missions", tasks: [
        { id: 'm-1002', desc: 'Deploy Authentication caching layer', status: 'Running Phase: Build', time: '0m 42s', cpu: '85%' },
        { id: 'm-1003', desc: 'Security Hardening Pass (Platinum)', status: 'Diagnostic Invariants', time: '1m 15s', cpu: '40%' }
      ]
    },
    {
      title: "Queued Background Agents", tasks: [
        { id: 'a-54', desc: 'Continuous Learning (Magma Ingestion)', status: 'Waiting on lock', time: '--', cpu: '0%' },
        { id: 'a-55', desc: 'Predictive Log Analysis', status: 'Pending Cycle', time: '--', cpu: '0%' }
      ]
    }
  ];

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: 800, background: C.bgDark, border: `1px solid ${C.border}`, borderRadius: 12, boxShadow: '0 20px 40px rgba(0,0,0,0.5)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px 24px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: C.text, display: 'flex', alignItems: 'center', gap: 8 }}>⛭ Global Task Manager</div>
            <div style={{ fontSize: 12, color: C.dim, marginTop: 4 }}>Control center for parallel sub-agents and background bridging pipelines.</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: C.muted, cursor: 'pointer', fontSize: 24 }}>×</button>
        </div>
        <div style={{ padding: 24, overflowY: 'auto', maxHeight: '70vh' }}>
          {taskGroups.map(group => (
            <div key={group.title} style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.accentAlt, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 16 }}>{group.title}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {group.tasks.map(t => (
                  <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: C.bg, border: `1px solid ${C.border}`, padding: '12px 16px', borderRadius: 8 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{t.desc}</div>
                      <div style={{ fontSize: 12, color: C.muted, marginTop: 6, display: 'flex', gap: 16 }}>
                        <span><span style={{ color: C.dim }}>ID:</span> {t.id}</span>
                        <span><span style={{ color: C.dim }}>Status:</span> {t.status}</span>
                        <span><span style={{ color: C.dim }}>Duration:</span> {t.time}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button style={{ padding: '6px 12px', background: C.bgAlt, border: `1px solid ${C.border}`, color: C.text, borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>Pause</button>
                      <button style={{ padding: '6px 12px', background: '#ef444422', border: `1px solid ${C.error}`, color: C.error, borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>Cancel</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
