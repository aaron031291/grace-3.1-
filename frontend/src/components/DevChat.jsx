/**
 * DevChat — Grace educates developers about her entire system.
 *
 * A dev can ask Grace anything about APIs, components, memory systems,
 * intelligence loops, genesis keys, architecture — and she'll teach them.
 * Uses Kimi for deep understanding, with raw data queries as fallback.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', info: '#2196f3', dev: '#00bcd4',
};

const QUICK_QUERIES = [
  { label: 'All APIs', query: 'apis' },
  { label: 'Components', query: 'components' },
  { label: 'Memory', query: 'memory' },
  { label: 'Graphs', query: 'graphs' },
  { label: 'Pipeline', query: 'pipeline' },
  { label: 'Architecture', query: 'architecture' },
  { label: 'LLM Models', query: 'models' },
  { label: 'Genesis', query: 'genesis' },
  { label: 'Gaps', query: 'gaps' },
  { label: 'Verify', query: 'verification' },
];

export default function DevChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [systemMap, setSystemMap] = useState(null);
  const [includeGaps, setIncludeGaps] = useState(false);
  const [includeVerification, setIncludeVerification] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    setMessages([{
      role: 'system', sender: 'Grace',
      content: "Welcome, developer. I'm Grace — ask me anything about my systems.\n\n" +
        "Try: 'How does the consensus engine work?' or 'What memory systems exist?' or " +
        "'Show me all API endpoints' or 'What integration gaps are there?'\n\n" +
        "Use the quick query buttons below for raw data, or ask in natural language for explanations.",
      ts: new Date().toISOString(),
    }]);
  }, []);

  const askGrace = useCallback(async () => {
    if (!input.trim() || sending) return;
    const question = input.trim();
    setInput('');
    setSending(true);

    setMessages(prev => [...prev, {
      role: 'user', sender: 'You', content: question,
      ts: new Date().toISOString(),
    }]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/dev-chat/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          include_gaps: includeGaps,
          include_verification: includeVerification,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: 'assistant', sender: `Grace (${data.model})`,
          content: data.response,
          ts: new Date().toISOString(),
        }]);
      } else {
        const errText = await res.text().catch(() => `HTTP ${res.status}`);
        setMessages(prev => [...prev, {
          role: 'system', sender: 'Error',
          content: `Failed: ${errText.substring(0, 300)}`,
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', sender: 'Error',
        content: `Connection failed: ${e.message}`,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, [input, sending, includeGaps, includeVerification]);

  const runQuickQuery = useCallback(async (queryType) => {
    setSending(true);
    setMessages(prev => [...prev, {
      role: 'user', sender: 'You',
      content: `Query: ${queryType}`,
      ts: new Date().toISOString(),
    }]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/dev-chat/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_type: queryType }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: 'data', sender: `Grace (${queryType})`,
          content: JSON.stringify(data, null, 2),
          ts: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'system', sender: 'Error',
        content: e.message,
        ts: new Date().toISOString(),
      }]);
    }
    setSending(false);
  }, []);

  const loadSystemMap = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/dev-chat/system-map`);
      if (res.ok) setSystemMap(await res.json());
    } catch { /* skip */ }
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg }}>
      {/* Header */}
      <div style={{
        padding: '8px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.dev }}>🛠️ Dev Chat</span>
          <span style={{ fontSize: 11, color: C.dim, marginLeft: 8 }}>Ask Grace about her systems</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <label style={{ fontSize: 10, color: C.muted, display: 'flex', alignItems: 'center', gap: 3, cursor: 'pointer' }}>
            <input type="checkbox" checked={includeGaps} onChange={e => setIncludeGaps(e.target.checked)} />
            +Gaps
          </label>
          <label style={{ fontSize: 10, color: C.muted, display: 'flex', alignItems: 'center', gap: 3, cursor: 'pointer' }}>
            <input type="checkbox" checked={includeVerification} onChange={e => setIncludeVerification(e.target.checked)} />
            +Verify
          </label>
          <button onClick={loadSystemMap} style={{
            padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer',
            background: C.dev, color: '#fff', fontSize: 11, fontWeight: 600,
          }}>System Map</button>
        </div>
      </div>

      {/* Quick query buttons */}
      <div style={{
        padding: '6px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
        display: 'flex', gap: 4, flexWrap: 'wrap',
      }}>
        {QUICK_QUERIES.map(q => (
          <button key={q.query} onClick={() => runQuickQuery(q.query)} disabled={sending} style={{
            padding: '3px 8px', border: `1px solid ${C.border}`, borderRadius: 4,
            cursor: 'pointer', fontSize: 10, fontWeight: 600,
            background: 'transparent', color: C.muted,
          }}>{q.label}</button>
        ))}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          const isData = msg.role === 'data';
          const isSystem = msg.role === 'system';
          const color = isUser ? C.accent : isData ? C.info : isSystem ? C.dim : C.dev;
          return (
            <div key={i} style={{
              padding: '10px 14px', marginBottom: 6, borderRadius: 8,
              background: isUser ? C.bgDark : isData ? '#0d1117' : C.bgAlt,
              borderLeft: `3px solid ${color}`,
              maxWidth: isUser ? '70%' : '100%',
              marginLeft: isUser ? 'auto' : 0,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color, marginBottom: 4 }}>{msg.sender}</div>
              {isData ? (
                <pre style={{
                  margin: 0, fontSize: 11, lineHeight: 1.5, color: C.muted,
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  maxHeight: 400, overflow: 'auto',
                }}>{msg.content}</pre>
              ) : (
                <div style={{ fontSize: 13, color: C.text, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </div>
              )}
            </div>
          );
        })}
        {sending && (
          <div style={{ padding: 12, color: C.dev, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ animation: 'pulse 1.5s infinite', fontSize: 18 }}>🛠️</span>
            <span>Grace is thinking...</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* System map panel */}
      {systemMap && (
        <div style={{
          maxHeight: 200, overflow: 'auto', padding: '8px 14px',
          borderTop: `1px solid ${C.border}`, background: '#0d1117', fontSize: 11,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, color: C.dev }}>System Map</span>
            <span onClick={() => setSystemMap(null)} style={{ cursor: 'pointer', color: C.dim }}>✕</span>
          </div>
          <pre style={{ margin: 0, color: C.muted, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(systemMap, null, 2)}
          </pre>
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && askGrace()}
            placeholder="Ask Grace about her systems... (APIs, components, memory, architecture)"
            disabled={sending}
            style={{
              flex: 1, padding: '10px 14px', background: C.bg, color: C.text,
              border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 13, outline: 'none',
            }}
          />
          <button onClick={askGrace} disabled={sending || !input.trim()} style={{
            padding: '8px 16px', border: 'none', borderRadius: 6, cursor: 'pointer',
            background: C.dev, color: '#fff', fontSize: 13, fontWeight: 600,
            opacity: sending ? 0.5 : 1,
          }}>
            {sending ? '...' : '🛠️ Ask'}
          </button>
        </div>
      </div>
    </div>
  );
}
