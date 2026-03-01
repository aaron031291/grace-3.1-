/**
 * PlannerPanel — Intelligent Dual-Pane Planning System
 *
 * LEFT PANE (User): Rich text editor with bullet points, bold, headers.
 *   - Text mode / Mind map mode / Voice mode toggle
 *   - Persistent voice input
 *   - Mini word processor feel
 *
 * RIGHT PANE (Grace): Auto-generates plan in real time.
 *   - Structured blueprint
 *   - Thinking steps (7 steps ahead)
 *   - Predictions and challenges
 *   - Learning insights from memory
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';

const C = {
  bg: '#1a1a2e', bgAlt: '#16213e', bgDark: '#0f3460',
  accent: '#e94560', accentAlt: '#533483',
  text: '#eee', muted: '#aaa', dim: '#666', border: '#333',
  success: '#4caf50', warn: '#ff9800', info: '#2196f3',
};

function ToolbarButton({ icon, label, active, onClick, title }) {
  return (
    <button
      onClick={onClick}
      title={title || label}
      style={{
        padding: '4px 8px', border: `1px solid ${active ? C.accent : C.border}`,
        borderRadius: 4, background: active ? `${C.accent}22` : 'transparent',
        color: active ? C.accent : C.muted, fontSize: 11, cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: 3,
      }}
    >
      <span style={{ fontSize: 13 }}>{icon}</span>
      {label && <span>{label}</span>}
    </button>
  );
}

export default function PlannerPanel() {
  const [sessionId, setSessionId] = useState(null);
  const [userContent, setUserContent] = useState('');
  const [gracePlan, setGracePlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('text'); // text, mindmap, voice
  const [sessions, setSessions] = useState([]);
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceText, setVoiceText] = useState('');
  const [notification, setNotification] = useState(null);
  const editorRef = useRef(null);
  const debounceRef = useRef(null);

  const notify = useCallback((msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3000);
  }, []);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/planner/sessions`)
      .then(r => r.ok ? r.json() : { sessions: [] })
      .then(d => setSessions(d.sessions || []))
      .catch(() => {});
  }, []);

  const generatePlan = async (content) => {
    if (!content || content.trim().length < 5) return;
    setLoading(true);
    try {
      const endpoint = sessionId ? `${API_BASE_URL}/api/planner/refine` : `${API_BASE_URL}/api/planner/generate`;
      const body = sessionId
        ? { session_id: sessionId, user_content: content }
        : { content, mode, session_id: sessionId };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setGracePlan(data.grace_pane?.plan || data.grace_pane || null);
      }
    } catch { /* skip */ }
    setLoading(false);
  };

  const handleContentChange = (e) => {
    const value = e.target.value;
    setUserContent(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (value.trim().length > 10) generatePlan(value);
    }, 1500);
  };

  const handleSubmit = () => {
    generatePlan(userContent);
  };

  const loadSession = async (sid) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/planner/session/${sid}`);
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setUserContent(data.user_pane?.content || '');
        setGracePlan(data.grace_pane?.plan || null);
      }
    } catch { /* skip */ }
  };

  const newSession = () => {
    setSessionId(null);
    setUserContent('');
    setGracePlan(null);
  };

  // Voice input (Web Speech API)
  const toggleVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      notify('Voice not supported in this browser', 'error');
      return;
    }
    setVoiceActive(!voiceActive);
  };

  useEffect(() => {
    if (!voiceActive) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setVoiceText(transcript);
      if (event.results[event.resultIndex].isFinal) {
        setUserContent(prev => prev + ' ' + transcript);
      }
    };

    recognition.onerror = () => setVoiceActive(false);
    recognition.onend = () => { if (voiceActive) recognition.start(); };

    recognition.start();
    return () => recognition.stop();
  }, [voiceActive]);

  return (
    <div style={{ display: 'flex', height: '100%', color: C.text, background: C.bg, position: 'relative' }}>
      {notification && (
        <div style={{
          position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)', zIndex: 100,
          padding: '6px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600,
          background: notification.type === 'success' ? C.success : C.accent, color: '#fff',
        }}>{notification.msg}</div>
      )}

      {/* ── Left: User Pane ───────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${C.border}` }}>
        {/* Toolbar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px',
          borderBottom: `1px solid ${C.border}`, background: C.bgAlt, flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.accent, marginRight: 8 }}>YOUR PLAN</span>
          <ToolbarButton icon="📝" label="Text" active={mode === 'text'} onClick={() => setMode('text')} />
          <ToolbarButton icon="🕸️" label="Mind Map" active={mode === 'mindmap'} onClick={() => setMode('mindmap')} />
          <ToolbarButton
            icon={voiceActive ? '🔴' : '🎙️'}
            label={voiceActive ? 'Stop' : 'Voice'}
            active={voiceActive}
            onClick={toggleVoice}
          />
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
            <ToolbarButton icon="➕" label="New" onClick={newSession} />
            <ToolbarButton icon="▶" label="Generate" onClick={handleSubmit} />
          </div>
        </div>

        {/* Session list */}
        {sessions.length > 0 && (
          <div style={{
            display: 'flex', gap: 4, padding: '4px 10px', borderBottom: `1px solid ${C.border}`,
            overflowX: 'auto', background: C.bg, flexShrink: 0,
          }}>
            {sessions.slice(0, 8).map(s => (
              <button
                key={s.session_id}
                onClick={() => loadSession(s.session_id)}
                style={{
                  padding: '2px 8px', border: `1px solid ${sessionId === s.session_id ? C.accent : C.border}`,
                  borderRadius: 3, background: sessionId === s.session_id ? `${C.accent}22` : 'transparent',
                  color: sessionId === s.session_id ? C.accent : C.dim, fontSize: 10, cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {s.preview?.substring(0, 25) || s.session_id?.substring(0, 12)}
              </button>
            ))}
          </div>
        )}

        {/* Editor */}
        <div style={{ flex: 1, padding: 12, overflow: 'auto' }}>
          {mode === 'text' && (
            <textarea
              ref={editorRef}
              value={userContent}
              onChange={handleContentChange}
              placeholder="Type your idea, problem, or plan here...&#10;&#10;Grace will generate her plan in real time as you type.&#10;&#10;Tips:&#10;• Start with what you want to build&#10;• Describe the problem you're solving&#10;• List any constraints or requirements"
              style={{
                width: '100%', height: '100%', resize: 'none',
                background: 'transparent', color: C.text, border: 'none',
                fontSize: 14, lineHeight: 1.7, outline: 'none',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              }}
            />
          )}

          {mode === 'mindmap' && (
            <div style={{ textAlign: 'center', padding: 40, color: C.dim }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🕸️</div>
              <div style={{ fontSize: 14 }}>Mind Map mode</div>
              <div style={{ fontSize: 11, marginTop: 8 }}>
                Use text mode to plan, then switch here to visualise the structure.
              </div>
              {gracePlan?.steps && (
                <div style={{ marginTop: 20, textAlign: 'left' }}>
                  {gracePlan.steps.map((step, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
                      paddingLeft: step.type === 'design' ? 0 : step.type === 'verification' ? 40 : 20,
                    }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: step.type === 'design' ? C.info : step.type === 'verification' ? C.success : C.accent,
                        flexShrink: 0,
                      }} />
                      <span style={{ fontSize: 12, color: C.text }}>{step.description}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {voiceActive && voiceText && (
            <div style={{
              position: 'absolute', bottom: 60, left: 12, right: '50%',
              padding: '8px 12px', background: `${C.accent}22`, border: `1px solid ${C.accent}`,
              borderRadius: 6, fontSize: 12, color: C.accent, fontStyle: 'italic',
            }}>
              🎙️ {voiceText}
            </div>
          )}
        </div>
      </div>

      {/* ── Right: Grace Pane ──────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          padding: '6px 10px', borderBottom: `1px solid ${C.border}`,
          background: C.bgAlt, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: C.success }}>
            GRACE'S PLAN {loading && '⏳'}
          </span>
          {gracePlan && (
            <span style={{ fontSize: 10, color: C.dim }}>
              {gracePlan.steps?.length || 0} steps | {gracePlan.estimated_complexity || '?'} complexity
            </span>
          )}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          {!gracePlan ? (
            <div style={{ textAlign: 'center', padding: 40, color: C.dim }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🧠</div>
              <div style={{ fontSize: 14 }}>Grace is waiting for your input</div>
              <div style={{ fontSize: 11, marginTop: 8 }}>
                Start typing in the left pane. Grace will auto-generate her plan.
              </div>
            </div>
          ) : (
            <div>
              {/* Intent */}
              <div style={{
                padding: '8px 12px', background: C.bgDark, borderRadius: 6,
                marginBottom: 12, border: `1px solid ${C.border}`,
              }}>
                <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 4 }}>Intent</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{gracePlan.intent}</div>
              </div>

              {/* Thinking Steps */}
              {gracePlan.thinking_steps?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 6 }}>
                    Grace's Thinking (7 Steps Ahead)
                  </div>
                  {gracePlan.thinking_steps.map((step, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: 8, marginBottom: 4, fontSize: 12, color: C.muted,
                    }}>
                      <span style={{ color: C.info, fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Steps */}
              {gracePlan.steps?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 6 }}>
                    Blueprint Steps
                  </div>
                  {gracePlan.steps.map((step, i) => (
                    <div key={i} style={{
                      padding: '8px 10px', background: C.bgAlt, borderRadius: 4,
                      marginBottom: 4, border: `1px solid ${C.border}`,
                      borderLeft: `3px solid ${step.type === 'design' ? C.info : step.type === 'verification' ? C.success : C.accent}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>{step.description}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          background: step.type === 'design' ? C.info : step.type === 'verification' ? C.success : C.accentAlt,
                          color: '#fff',
                        }}>{step.type}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 10, color: C.dim }}>
                        <span>Effort: {step.estimated_effort}</span>
                        <span>Verify: {step.verification}</span>
                        {step.is_decision && <span style={{ color: C.warn }}>⚡ Decision Point</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Predictions */}
              {gracePlan.predictions?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 6 }}>
                    Predicted Challenges
                  </div>
                  {gracePlan.predictions.map((p, i) => (
                    <div key={i} style={{ fontSize: 12, color: C.warn, marginBottom: 3 }}>⚠ {p}</div>
                  ))}
                </div>
              )}

              {/* Learning Insights */}
              {gracePlan.learning_insights?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: 'uppercase', marginBottom: 6 }}>
                    Learning Insights
                  </div>
                  {gracePlan.learning_insights.map((li, i) => (
                    <div key={i} style={{
                      padding: '6px 10px', background: `${C.success}11`, border: `1px solid ${C.success}33`,
                      borderRadius: 4, marginBottom: 4, fontSize: 11, color: C.muted,
                    }}>
                      <span style={{ color: C.success, fontSize: 9, marginRight: 6 }}>{li.source?.toUpperCase()}</span>
                      {typeof li.insight === 'string' ? li.insight.substring(0, 300) : JSON.stringify(li.insight).substring(0, 300)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
