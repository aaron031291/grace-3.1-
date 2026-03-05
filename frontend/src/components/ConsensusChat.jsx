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
  'Qwen 3': C.qwen,
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
  const [_notifications, _setNotifications] = useState([]);
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

    pollRef.current = setInterval(poll, 10000);
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

  const getColor = (model) => {
    for (const [key, color] of Object.entries(MODEL_COLORS)) {
      if (model?.toLowerCase().includes(key.toLowerCase().split(' ')[0])) return color;
    }
    return C.muted;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg }}>
      {/* Header */}
      <div style={{
        padding: '8px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.text }}>🤝 Consensus Chat</span>
          <span style={{ fontSize: 11, color: C.dim, marginLeft: 8 }}>All models • bi-directional</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <label style={{ fontSize: 11, color: C.muted, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={autoMode} onChange={e => setAutoMode(e.target.checked)} />
            Auto-notify
          </label>
          <button onClick={startConversation} disabled={sending} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: C.success, color: '#fff', fontSize: 11, fontWeight: 600,
          }}>
            {messages.length === 0 ? '▶ Start' : '🔄 Diagnose'}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: C.dim }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🤝</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.muted }}>Consensus Chat</div>
            <div style={{ fontSize: 12, marginTop: 8, maxWidth: 400, margin: '8px auto' }}>
              All LLMs in one conversation. Click "Start" for them to diagnose Grace,
              or type a message for all models to discuss together.
              Toggle "Auto-notify" for real-time alerts.
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
  );
}
