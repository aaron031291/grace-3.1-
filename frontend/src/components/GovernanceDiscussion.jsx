/**
 * GovernanceDiscussion — Chat with Kimi+Opus about governance approvals.
 * User can discuss each request before approving/denying.
 */
import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', info: '#2196f3',
};

const ROLE_COLORS = {
  user: '#e94560', consensus: '#4caf50', decision: '#ff9800',
  system: '#666', 'Kimi 2.5 (Moonshot)': '#2196f3', 'Opus 4.6 (Claude)': '#9c27b0',
};

export default function GovernanceDiscussion({ discussionId, onClose }) {
  const [discussion, setDiscussion] = useState(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const endRef = useRef(null);

  const load = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance/discuss/${discussionId}`);
      if (res.ok) setDiscussion(await res.json());
    } catch { /* skip */ }
  };

  useEffect(() => { if (discussionId) load(); }, [discussionId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [discussion?.messages]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    setSending(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance/discuss/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discussion_id: discussionId, message: input, ask_models: true }),
      });
      if (res.ok) {
        setDiscussion(await res.json());
        setInput('');
      }
    } catch { /* skip */ }
    setSending(false);
  };

  const decide = async (decision) => {
    const reasoning = window.prompt(`Reasoning for ${decision}:`);
    if (reasoning === null) return;
    setDeciding(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/governance/discuss/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discussion_id: discussionId, decision, reasoning }),
      });
      if (res.ok) setDiscussion(await res.json());
    } catch { /* skip */ }
    setDeciding(false);
  };

  if (!discussion) return <div style={{ padding: 20, color: C.dim }}>Loading...</div>;

  const isOpen = discussion.status === 'open';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: C.bg }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', borderBottom: `1px solid ${C.border}`, background: C.bgAlt,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{discussion.title}</div>
          <div style={{ fontSize: 11, color: C.dim }}>
            {discussion.request_type} · {discussion.severity} severity · {discussion.messages?.length || 0} messages
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {isOpen && (
            <>
              <button onClick={() => decide('approve')} disabled={deciding} style={{
                padding: '5px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                background: C.success, color: '#fff', fontSize: 11, fontWeight: 700,
              }}>Approve</button>
              <button onClick={() => decide('deny')} disabled={deciding} style={{
                padding: '5px 12px', border: 'none', borderRadius: 4, cursor: 'pointer',
                background: C.accent, color: '#fff', fontSize: 11, fontWeight: 700,
              }}>Deny</button>
            </>
          )}
          {!isOpen && (
            <span style={{
              padding: '4px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
              background: discussion.decision === 'approve' ? C.success : C.accent,
              color: '#fff',
            }}>{discussion.decision?.toUpperCase()}</span>
          )}
          {onClose && (
            <button onClick={onClose} style={{
              background: 'none', border: 'none', color: C.dim, fontSize: 16, cursor: 'pointer',
            }}>✕</button>
          )}
        </div>
      </div>

      {/* Description */}
      <div style={{ padding: '8px 14px', borderBottom: `1px solid ${C.border}`, fontSize: 12, color: C.muted }}>
        {discussion.description}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {(discussion.messages || []).map((msg, i) => {
          const color = ROLE_COLORS[msg.role] || C.info;
          const isUser = msg.role === 'user';
          return (
            <div key={i} style={{
              padding: '8px 12px', marginBottom: 6, borderRadius: 8,
              background: isUser ? C.bgDark : C.bgAlt,
              borderLeft: `3px solid ${color}`,
            }}>
              <div style={{ fontSize: 10, color, fontWeight: 700, marginBottom: 3 }}>
                {msg.role === 'user' ? 'You' : msg.role}
              </div>
              <div style={{ fontSize: 12, color: C.text, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {msg.content}
              </div>
              <div style={{ fontSize: 9, color: C.dim, marginTop: 3 }}>
                {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {/* Input */}
      {isOpen && (
        <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, background: C.bgAlt }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask Kimi and Opus about this decision..."
              disabled={sending}
              style={{
                flex: 1, padding: '8px 12px', background: C.bg, color: C.text,
                border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, outline: 'none',
              }}
            />
            <button onClick={sendMessage} disabled={sending || !input.trim()} style={{
              padding: '6px 14px', border: 'none', borderRadius: 4, cursor: 'pointer',
              background: C.info, color: '#fff', fontSize: 12, fontWeight: 600,
              opacity: sending ? 0.5 : 1,
            }}>
              {sending ? '...' : 'Ask Both'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
