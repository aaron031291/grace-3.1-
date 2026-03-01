/**
 * ConsensusChat — All LLMs in one bi-directional conversation.
 * 
 * Kimi, Opus, Qwen, and the user all talk together.
 * LLMs can initiate — they don't just respond, they proactively
 * notify about problems, errors, improvements.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', info: '#2196f3',
  opus: '#9c27b0', kimi: '#e94560', qwen: '#2196f3', reasoning: '#ff9800',
  system: '#4caf50',
};

const MODEL_COLORS = {
  'Opus 4.6 (Claude)': C.opus,
  'Kimi K2.5 (Moonshot)': C.kimi,
  'Qwen 2.5 Coder (Local)': C.qwen,
  'DeepSeek R1 (Local)': C.reasoning,
  'consensus': C.success,
  'system': C.dim,
  'user': C.accent,
};

export default function ConsensusChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [autoMode, setAutoMode] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [showCollab, setShowCollab] = useState(true);
  const [gaps, setGaps] = useState(null);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [verification, setVerification] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const endRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-poll for system notifications when autoMode is on
  useEffect(() => {
    if (!autoMode) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    const poll = async () => {
      try {
        // Check for system events
        const res = await fetch(`${API_BASE_URL}/api/bi/event-log?limit=5`);
        if (res.ok) {
          const data = await res.json();
          const events = data.events || [];
          const newEvents = events.filter(e =>
            e.topic && (e.topic.includes('error') || e.topic.includes('healing') || e.topic.includes('failure'))
          );
          if (newEvents.length > 0) {
            for (const evt of newEvents.slice(0, 2)) {
              const existing = messages.find(m => m.content?.includes(evt.topic));
              if (!existing) {
                setMessages(prev => [...prev, {
                  role: 'system',
                  model: 'Grace',
                  content: `⚡ System event: ${evt.topic.replace(/\./g, ' → ')} (${evt.source})`,
                  ts: new Date().toISOString(),
                }]);
              }
            }
          }
        }
      } catch { /* skip */ }
    };

    pollRef.current = setInterval(poll, 30000);
    return () => clearInterval(pollRef.current);
  }, [autoMode, messages]);

  // Start conversation — LLMs initiate
  const startConversation = async () => {
    setSending(true);
    setMessages([{
      role: 'system', model: 'Grace',
      content: '🤝 Consensus roundtable started. All models are listening.',
      ts: new Date().toISOString(),
    }]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/console/diagnose`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.errors?.length) {
          for (const err of data.errors) {
            setMessages(prev => [...prev, {
              role: 'system', model: 'Grace',
              content: `⚠️ ${err}`,
              ts: new Date().toISOString(),
            }]);
          }
        }
        if (data.diagnosis) {
          setMessages(prev => [...prev, {
            role: 'consensus', model: 'Kimi + Opus Diagnosis',
            content: data.diagnosis,
            confidence: data.confidence,
            ts: new Date().toISOString(),
          }]);
        }
        if (data.warnings?.length) {
          setMessages(prev => [...prev, {
            role: 'system', model: 'Grace',
            content: `Warnings:\n${data.warnings.join('\n')}`,
            ts: new Date().toISOString(),
          }]);
        }
      } else {
        const errText = await res.text().catch(() => '');
        setMessages(prev => [...prev, {
          role: 'system', model: 'Error',
          content: `Diagnose failed (${res.status}): ${errText.substring(0, 200)}`,
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', model: 'Error',
        content: `Connection failed: ${e.message}`,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  };

  const sendMessage = useCallback(async () => {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setSending(true);

    setMessages(prev => [...prev, {
      role: 'user', model: 'You', content: msg,
      ts: new Date().toISOString(),
    }]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/consensus/fast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: msg,
          models: ['kimi', 'opus', 'qwen', 'reasoning'],
          source: 'user',
        }),
      });

      if (res.ok) {
        const data = await res.json();

        // Add individual responses
        const responses = data.individual_responses || data.individual_analyses || [];
        for (const r of responses) {
          const text = r.response || r.analysis || r.content || '';
          if (text) {
            setMessages(prev => [...prev, {
              role: 'assistant',
              model: r.model_name || r.model_id || 'Model',
              content: text,
              latency: r.latency_ms,
              ts: new Date().toISOString(),
            }]);
          }
        }

        // Add consensus/final output
        const finalText = data.final_output || data.consensus || data.aligned_output || data.response || data.diagnosis || '';
        if (finalText) {
          setMessages(prev => [...prev, {
            role: 'consensus', model: 'Consensus',
            content: finalText,
            confidence: data.confidence,
            ts: new Date().toISOString(),
          }]);
        }

        // If nothing came through, show the raw response
        if (responses.length === 0 && !finalText) {
          setMessages(prev => [...prev, {
            role: 'system', model: 'Grace',
            content: `Response received but empty. Raw: ${JSON.stringify(data).substring(0, 500)}`,
            ts: new Date().toISOString(),
          }]);
        }
      } else {
        const errText = await res.text().catch(() => `HTTP ${res.status}`);
        setMessages(prev => [...prev, {
          role: 'system', model: 'Error',
          content: `Server returned ${res.status}: ${errText.substring(0, 300)}`,
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', model: 'Error',
        content: `Connection failed: ${e.message}. Is the backend running on port 8000?`,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, [input, sending]);

  const runHealthCheck = useCallback(async () => {
    setSending(true);
    setMessages(prev => [...prev, {
      role: 'system', model: 'Self-Healing',
      content: '🏥 Running system health check...',
      ts: new Date().toISOString(),
    }]);
    try {
      const res = await fetch(`${API_BASE_URL}/api/health/check`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const health = data.system_health || {};
        const broken = health.broken || [];
        const degraded = health.degraded || [];
        const healthy = health.healthy || [];
        let msg = `**System Health: ${health.overall_status?.toUpperCase()}**\n`;
        if (broken.length) msg += `\n🔴 Broken: ${broken.join(', ')}`;
        if (degraded.length) msg += `\n🟡 Degraded: ${degraded.join(', ')}`;
        msg += `\n🟢 Healthy: ${healthy.length} components`;
        if (health.recent_errors?.length) {
          msg += `\n\nRecent errors:\n${health.recent_errors.slice(0, 3).map(e => `• ${e.component}: ${e.error?.substring(0, 100)}`).join('\n')}`;
        }
        setMessages(prev => [...prev, {
          role: 'consensus', model: 'Health Monitor',
          content: msg,
          confidence: broken.length === 0 ? 1.0 : 0.3,
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', model: 'Error',
        content: `Health check failed: ${e.message}`,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, []);

  const runPatchConsensus = useCallback(async () => {
    if (!input.trim()) return;
    const task = input.trim();
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, {
      role: 'user', model: 'You',
      content: `🔧 Patch consensus: ${task}`,
      ts: new Date().toISOString(),
    }]);
    try {
      const res = await fetch(`${API_BASE_URL}/api/patch-consensus/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, auto_apply: false }),
      });
      if (res.ok) {
        const data = await res.json();
        let msg = `**Patch Proposal: ${data.proposal_id}**\nStatus: ${data.status}\nHash: ${data.patch_hash?.substring(0, 16)}...\n`;
        if (data.instructions?.length) {
          msg += `\nInstructions (${data.instructions.length}):\n`;
          for (const inst of data.instructions.slice(0, 5)) {
            msg += `• ${inst.action} ${inst.file}: ${inst.reason}\n`;
          }
        }
        if (data.votes?.length) {
          const approved = data.votes.filter(v => v.approved).length;
          msg += `\nVotes: ${approved}/${data.votes.length} approved`;
        }
        setMessages(prev => [...prev, {
          role: 'consensus', model: 'Patch Consensus',
          content: msg,
          confidence: data.status === 'verified' ? 0.95 : 0.4,
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', model: 'Error',
        content: `Patch consensus failed: ${e.message}`,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, [input]);

  const fetchGaps = useCallback(async () => {
    setGapsLoading(true);
    try {
      const [gapRes, verifyRes, healthRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/horizon/gaps`),
        fetch(`${API_BASE_URL}/api/horizon/verify`),
        fetch(`${API_BASE_URL}/api/health/status`),
      ]);
      if (gapRes.status === 'fulfilled' && gapRes.value.ok) setGaps(await gapRes.value.json());
      if (verifyRes.status === 'fulfilled' && verifyRes.value.ok) setVerification(await verifyRes.value.json());
      if (healthRes.status === 'fulfilled' && healthRes.value.ok) setHealthData(await healthRes.value.json());
    } catch { /* skip */ }
    setGapsLoading(false);
  }, []);

  useEffect(() => { if (showCollab) fetchGaps(); }, [showCollab, fetchGaps]);

  const askKimiAboutGap = useCallback(async (gap) => {
    setSending(true);
    const prompt = `Analyze this integration gap and suggest a precise fix:\n\n` +
      `Component: ${gap.component}\n` +
      `Type: ${gap.type}\n` +
      `Description: ${gap.description}\n` +
      `Severity: ${gap.severity}\n` +
      `Suggestion: ${gap.fix_suggestion || 'none'}\n\n` +
      `Give me: 1) Root cause, 2) Exact fix (file paths + code), 3) How to verify it worked.`;

    setMessages(prev => [...prev, {
      role: 'user', model: 'You',
      content: `🔌 Fix gap: [${gap.component}] ${gap.description}`,
      ts: new Date().toISOString(),
    }]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/consensus/fast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, models: ['kimi', 'opus'], source: 'collaboration' }),
      });
      if (res.ok) {
        const data = await res.json();
        const responses = data.individual_responses || [];
        for (const r of responses) {
          if (r.response) {
            setMessages(prev => [...prev, {
              role: 'assistant', model: r.model_name || r.model_id,
              content: r.response, latency: r.latency_ms,
              ts: new Date().toISOString(),
            }]);
          }
        }
        if (data.final_output) {
          setMessages(prev => [...prev, {
            role: 'consensus', model: 'Fix Suggestion',
            content: data.final_output,
            confidence: data.confidence,
            ts: new Date().toISOString(),
          }]);
        }
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', model: 'Error', content: e.message,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, []);

  const getColor = (model) => {
    for (const [key, color] of Object.entries(MODEL_COLORS)) {
      if (model?.toLowerCase().includes(key.toLowerCase().split(' ')[0])) return color;
    }
    if (model?.includes('Health') || model?.includes('Self-Heal')) return C.success;
    if (model?.includes('Patch') || model?.includes('Fix')) return '#ff6b35';
    return C.muted;
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: C.bg }}>
      {/* Main chat area */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
      {/* Header */}
      <div style={{
        padding: '8px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.text }}>🤝 Consensus Chat</span>
          <span style={{ fontSize: 11, color: C.dim, marginLeft: 8 }}>All models • collaboration</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={autoMode} onChange={e => setAutoMode(e.target.checked)} />
            Auto-notify
          </label>
          <button onClick={runHealthCheck} disabled={sending} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: '#2196f3', color: '#fff', fontSize: 11, fontWeight: 600,
          }}>
            🏥 Health
          </button>
          <button onClick={runPatchConsensus} disabled={sending || !input.trim()} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: '#ff6b35', color: '#fff', fontSize: 11, fontWeight: 600,
            opacity: !input.trim() ? 0.5 : 1,
          }} title="Type a code task then click to run through patch consensus">
            🔧 Patch
          </button>
          <button onClick={startConversation} disabled={sending} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: C.success, color: '#fff', fontSize: 11, fontWeight: 600,
          }}>
            {messages.length === 0 ? '▶ Start' : '🔄 Diagnose'}
          </button>
          <button onClick={() => setShowCollab(!showCollab)} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: showCollab ? C.accent : C.border, color: '#fff', fontSize: 11, fontWeight: 600,
          }}>
            {showCollab ? '◀ Gaps' : '▶ Gaps'}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: C.dim }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🤝</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.muted }}>Consensus Chat + Collaboration</div>
            <div style={{ fontSize: 12, marginTop: 8, maxWidth: 400, margin: '8px auto' }}>
              All LLMs in one conversation. Click "Start" for them to diagnose Grace,
              or click a gap in the sidebar to ask Kimi + Opus for a fix.
            </div>
          </div>
        )}
        {messages.map((msg, i) => {
          const color = getColor(msg.model);
          const isUser = msg.role === 'user';
          const isSystem = msg.role === 'system';
          return (
            <div key={i} style={{
              padding: '10px 14px', marginBottom: 6, borderRadius: 8,
              background: isUser ? C.bgDark : isSystem ? `${C.dim}11` : C.bgAlt,
              borderLeft: `3px solid ${color}`,
              maxWidth: isUser ? '70%' : '100%',
              marginLeft: isUser ? 'auto' : 0,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color }}>{msg.model}</span>
                <span style={{ fontSize: 9, color: C.dim }}>
                  {msg.latency ? `${msg.latency.toFixed(0)}ms` : ''}
                  {msg.confidence ? ` • ${(msg.confidence * 100).toFixed(0)}% confidence` : ''}
                </span>
              </div>
              <div style={{ fontSize: 13, color: C.text, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {msg.content}
              </div>
              {msg.role === 'assistant' && (
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  <button onClick={() => {
                    fetch(`${API_BASE_URL}/api/feedback/code`, {
                      method: 'POST',
                      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                      body: `verdict=worked&task=${encodeURIComponent(messages[0]?.content || '')}&code_preview=${encodeURIComponent(msg.content?.substring(0, 500) || '')}`,
                    });
                    msg._fb = 'up';
                  }} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, opacity: msg._fb === 'up' ? 1 : 0.4 }}>👍</button>
                  <button onClick={async () => {
                    const res = await fetch(`${API_BASE_URL}/api/feedback/code`, {
                      method: 'POST',
                      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                      body: `verdict=didnt_work&task=${encodeURIComponent(messages[0]?.content || '')}&code_preview=${encodeURIComponent(msg.content?.substring(0, 500) || '')}`,
                    });
                    if (res.ok) {
                      const data = await res.json();
                      if (data.next_steps) {
                        setMessages(prev => [...prev, {
                          role: 'system', model: 'Grace',
                          content: `💡 Next steps:\n${data.next_steps}`,
                          ts: new Date().toISOString(),
                        }]);
                      }
                    }
                    msg._fb = 'down';
                  }} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, opacity: msg._fb === 'down' ? 1 : 0.4 }}>👎</button>
                </div>
              )}
            </div>
          );
        })}
        {sending && (
          <div style={{ padding: 12, color: C.warn, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ animation: 'pulse 1.5s infinite', fontSize: 18 }}>🧠</span>
            <span>All models are thinking... this takes 10-60 seconds for consensus.</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask all models together..."
            disabled={sending}
            style={{
              flex: 1, padding: '10px 14px', background: C.bg, color: C.text,
              border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 13, outline: 'none',
            }}
          />
          <button onClick={sendMessage} disabled={sending || !input.trim()} style={{
            padding: '8px 16px', border: 'none', borderRadius: 6, cursor: 'pointer',
            background: C.accent, color: '#fff', fontSize: 13, fontWeight: 600,
            opacity: sending ? 0.5 : 1,
          }}>
            {sending ? '...' : '🤝 All'}
          </button>
        </div>
      </div>
      </div>

      {/* ── Collaboration Sidebar — Gaps & Fixes ────────────────────── */}
      {showCollab && (
        <div style={{
          flex: '0 0 320px', borderLeft: `1px solid ${C.border}`, overflow: 'auto',
          background: C.bg, display: 'flex', flexDirection: 'column',
        }}>
          {/* Sidebar Header */}
          <div style={{
            padding: '10px 12px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: C.text }}>🔌 Gaps & Fixes</span>
            <button onClick={fetchGaps} disabled={gapsLoading} style={{
              padding: '3px 8px', border: 'none', borderRadius: 4, cursor: 'pointer',
              background: C.info, color: '#fff', fontSize: 10, fontWeight: 600,
            }}>{gapsLoading ? '...' : '↻ Scan'}</button>
          </div>

          {/* Summary stats */}
          {gaps && (
            <div style={{ display: 'flex', gap: 4, padding: '8px 12px', borderBottom: `1px solid ${C.border}` }}>
              <div style={{ flex: 1, textAlign: 'center', padding: 6, background: C.bgAlt, borderRadius: 4 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: C.accent }}>{gaps.total_gaps}</div>
                <div style={{ fontSize: 9, color: C.dim }}>Total</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center', padding: 6, background: C.bgAlt, borderRadius: 4 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#f44336' }}>{gaps.by_severity?.high || 0}</div>
                <div style={{ fontSize: 9, color: C.dim }}>High</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center', padding: 6, background: C.bgAlt, borderRadius: 4 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: C.warn }}>{gaps.by_severity?.medium || 0}</div>
                <div style={{ fontSize: 9, color: C.dim }}>Med</div>
              </div>
              {verification && (
                <div style={{ flex: 1, textAlign: 'center', padding: 6, background: C.bgAlt, borderRadius: 4 }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: C.success }}>{verification.pass_rate}%</div>
                  <div style={{ fontSize: 9, color: C.dim }}>Verified</div>
                </div>
              )}
            </div>
          )}

          {/* Health status */}
          {healthData && (
            <div style={{ padding: '6px 12px', borderBottom: `1px solid ${C.border}`, fontSize: 11 }}>
              <span style={{
                display: 'inline-block', padding: '2px 6px', borderRadius: 4, fontWeight: 700, fontSize: 10,
                background: healthData.overall_status === 'healthy' ? C.success : healthData.overall_status === 'degraded' ? C.warn : '#f44336',
                color: '#fff',
              }}>{healthData.overall_status?.toUpperCase()}</span>
              {healthData.broken?.length > 0 && (
                <span style={{ color: '#f44336', marginLeft: 6 }}>Broken: {healthData.broken.join(', ')}</span>
              )}
            </div>
          )}

          {/* Gap list */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {!gaps && !gapsLoading && (
              <div style={{ padding: 20, textAlign: 'center', color: C.dim, fontSize: 12 }}>
                Click Scan to load gaps
              </div>
            )}

            {gaps?.high_priority?.length > 0 && (
              <div style={{ padding: '8px 12px 4px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#f44336', textTransform: 'uppercase', marginBottom: 4 }}>
                  High Priority
                </div>
                {gaps.high_priority.map((g, i) => (
                  <div key={`high-${i}`} onClick={() => askKimiAboutGap(g)} style={{
                    padding: '8px 10px', marginBottom: 4, borderRadius: 6, cursor: 'pointer',
                    background: C.bgAlt, borderLeft: '3px solid #f44336', fontSize: 11,
                    transition: 'background .1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = C.bgDark}
                  onMouseLeave={e => e.currentTarget.style.background = C.bgAlt}
                  >
                    <div style={{ fontWeight: 600, color: C.text, marginBottom: 2 }}>[{g.component}]</div>
                    <div style={{ color: C.muted, lineHeight: 1.4 }}>{g.description}</div>
                    {g.fix_suggestion && (
                      <div style={{ color: C.info, fontSize: 10, marginTop: 4 }}>💡 {g.fix_suggestion}</div>
                    )}
                    <div style={{ color: C.accent, fontSize: 9, marginTop: 4, fontWeight: 600 }}>Click → Ask Kimi + Opus for fix</div>
                  </div>
                ))}
              </div>
            )}

            {gaps?.all_gaps && (
              <div style={{ padding: '8px 12px 4px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', marginBottom: 4 }}>
                  By Type ({gaps.total_gaps} total)
                </div>
                {Object.entries(gaps.by_type || {}).map(([type, count]) => (
                  <div key={type} style={{
                    display: 'flex', justifyContent: 'space-between', padding: '5px 10px',
                    background: C.bgAlt, borderRadius: 4, marginBottom: 3, fontSize: 11,
                  }}>
                    <span style={{ color: C.muted }}>{type.replace(/_/g, ' ')}</span>
                    <span style={{ fontWeight: 700, color: C.text }}>{count}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Medium priority gaps (clickable) */}
            {gaps?.all_gaps?.filter(g => g.severity === 'medium').slice(0, 15).length > 0 && (
              <div style={{ padding: '8px 12px 4px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: C.warn, textTransform: 'uppercase', marginBottom: 4 }}>
                  Medium Priority (top 15)
                </div>
                {gaps.all_gaps.filter(g => g.severity === 'medium').slice(0, 15).map((g, i) => (
                  <div key={`med-${i}`} onClick={() => askKimiAboutGap(g)} style={{
                    padding: '6px 10px', marginBottom: 3, borderRadius: 4, cursor: 'pointer',
                    background: C.bgAlt, borderLeft: `2px solid ${C.warn}`, fontSize: 10,
                    transition: 'background .1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = C.bgDark}
                  onMouseLeave={e => e.currentTarget.style.background = C.bgAlt}
                  >
                    <span style={{ color: C.muted }}>[{g.component}] </span>
                    <span style={{ color: C.text }}>{g.description?.substring(0, 80)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Verification failures */}
            {verification?.failures?.length > 0 && (
              <div style={{ padding: '8px 12px 4px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: C.accent, textTransform: 'uppercase', marginBottom: 4 }}>
                  Verification Failures ({verification.failures.length})
                </div>
                {verification.failures.slice(0, 10).map((f, i) => (
                  <div key={`fail-${i}`} style={{
                    padding: '5px 10px', marginBottom: 3, borderRadius: 4,
                    background: C.bgAlt, borderLeft: `2px solid ${C.accent}`, fontSize: 10,
                  }}>
                    <div style={{ color: C.text }}>{f.claim?.substring(0, 70)}</div>
                    <div style={{ color: C.accent, fontSize: 9 }}>{f.error?.substring(0, 80)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
