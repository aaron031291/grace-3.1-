import { useState, useEffect, useRef, useCallback } from "react";
import { brainCall } from "../api/brain-client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function QueryChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [worldState, setWorldState] = useState(null);
  const [subsystems, setSubsystems] = useState([]);
  const [stateLoading, setStateLoading] = useState(true);
  const [activePanel, setActivePanel] = useState("chat");
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const fetchWorldState = useCallback(async () => {
    setStateLoading(true);
    try {
      const [stateRes, subRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/world-model/state`),
        fetch(`${API_BASE_URL}/api/world-model/subsystems`),
      ]);
      if (stateRes.status === "fulfilled" && stateRes.value.ok) {
        setWorldState(await stateRes.value.json());
      }
      if (subRes.status === "fulfilled" && subRes.value.ok) {
        const data = await subRes.value.json();
        setSubsystems(data.subsystems || []);
      }
    } catch {}
    setStateLoading(false);
  }, []);

  useEffect(() => {
    fetchWorldState();
    const interval = setInterval(fetchWorldState, 60000);
    return () => clearInterval(interval);
  }, [fetchWorldState]);

  const send = async () => {
    if (!input.trim() || sending) return;
    const query = input.trim();
    setInput("");
    setMessages(p => [...p, { role: "user", content: query, ts: Date.now() }]);
    setSending(true);

    // Try streaming first for fast response
    try {
      const { streamChat } = await import("../api/stream");
      let tokens = "";
      const msgIdx = { current: -1 };
      setMessages(p => {
        msgIdx.current = p.length;
        return [...p, { role: "assistant", content: "▌", streaming: true, ts: Date.now() }];
      });

      await streamChat(
        query, "kimi", [],
        (token) => {
          tokens += token;
          setMessages(p => {
            const u = [...p];
            if (msgIdx.current >= 0 && u[msgIdx.current]) {
              u[msgIdx.current] = { ...u[msgIdx.current], content: tokens + "▌" };
            }
            return u;
          });
        },
        () => {
          setMessages(p => {
            const u = [...p];
            if (msgIdx.current >= 0 && u[msgIdx.current]) {
              u[msgIdx.current] = { ...u[msgIdx.current], content: tokens, streaming: false };
            }
            return u;
          });
          setSending(false);
        },
        () => fallbackWorldModelChat(query)
      );
    } catch {
      fallbackWorldModelChat(query);
    }
  };

  const fallbackWorldModelChat = async (query) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/world-model/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, include_system_state: true }),
      });
      const data = await resp.json();
      const content = data.response || data.message || JSON.stringify(data);
      setMessages(p => {
        const u = [...p];
        const lastIdx = u.length - 1;
        if (lastIdx >= 0 && u[lastIdx].streaming) {
          u[lastIdx] = { role: "assistant", content, ts: Date.now() };
        } else {
          u.push({ role: "assistant", content, ts: Date.now() });
        }
        return u;
      });
    } catch (e) {
      setMessages(p => [...p, { role: "assistant", content: `Error: ${e.message}`, ts: Date.now() }]);
    }
    setSending(false);
  };

  const quickActions = [
    { label: "System Health", icon: "🏥", query: "What is the current system health status? List any problems." },
    { label: "What can you do?", icon: "🧠", query: "List all the brain domains and how many actions each has." },
    { label: "Recent Activity", icon: "📊", query: "What has happened in the system in the last 24 hours?" },
    { label: "Trust Scores", icon: "🛡️", query: "What are the current trust scores for all models?" },
    { label: "Find Problems", icon: "🔴", query: "Are there any errors, broken components, or issues right now?" },
    { label: "Architecture", icon: "🏗️", query: "Explain the overall architecture of Grace — what are the main components?" },
  ];

  return (
    <div style={{ display: "flex", height: "100%", background: "#0a0a1a" }}>
      {/* Main Chat */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{
          padding: "10px 16px", borderBottom: "1px solid #1a1a2e",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          <span style={{ fontSize: 18, fontWeight: 800, color: "#e94560" }}>Ask Grace</span>
          <span style={{ fontSize: 11, color: "#555" }}>World model aware — knows system state, components, trust, health</span>
          <div style={{ flex: 1 }} />
          <button
            onClick={fetchWorldState}
            style={{
              padding: "4px 10px", background: "#12122a", border: "1px solid #333",
              borderRadius: 4, color: "#888", fontSize: 10, cursor: "pointer",
            }}
          >
            {stateLoading ? "Loading..." : "Refresh State"}
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
          {messages.length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: 20 }}>
              <div style={{ fontSize: 36, fontWeight: 900, color: "#e94560" }}>Ask Grace Anything</div>
              <div style={{ fontSize: 13, color: "#666", textAlign: "center", maxWidth: 500 }}>
                This chat has full access to the world model — system health, brain capabilities,
                trust scores, database state, cognitive systems, and more. Ask about the system or give commands.
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, maxWidth: 600, width: "100%" }}>
                {quickActions.map(a => (
                  <button key={a.label} onClick={() => { setInput(a.query); }} style={{
                    padding: "12px", background: "#12122a", border: "1px solid #222",
                    borderRadius: 8, cursor: "pointer", textAlign: "center",
                    color: "#aaa", fontSize: 11, transition: "all .15s",
                  }}
                  onMouseEnter={e => e.target.style.borderColor = "#e94560"}
                  onMouseLeave={e => e.target.style.borderColor = "#222"}
                  >
                    <div style={{ fontSize: 20, marginBottom: 4 }}>{a.icon}</div>
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "75%", padding: "10px 14px", borderRadius: 12,
              background: m.role === "user" ? "#1a2a4a" : "#12122a",
              fontSize: 13, lineHeight: 1.6,
            }}>
              {m.role === "assistant" && (
                <div style={{ fontSize: 9, color: "#e94560", fontWeight: 700, marginBottom: 4 }}>Grace</div>
              )}
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
              <div style={{ fontSize: 9, color: "#444", marginTop: 4 }}>
                {new Date(m.ts).toLocaleTimeString()}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: "10px 16px", borderTop: "1px solid #1a1a2e",
          display: "flex", gap: 8, alignItems: "center",
        }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Ask about system health, architecture, trust scores, capabilities..."
            disabled={sending}
            style={{
              flex: 1, padding: "10px 14px", background: "#12122a",
              border: "1px solid #222", borderRadius: 8, color: "#ccc",
              fontSize: 13, outline: "none",
            }}
          />
          <button onClick={send} disabled={sending} style={{
            padding: "8px 20px", background: "#e94560", border: "none",
            borderRadius: 8, color: "#fff", fontSize: 12, fontWeight: 700,
            cursor: sending ? "wait" : "pointer", opacity: sending ? 0.5 : 1,
          }}>
            {sending ? "Thinking..." : "Ask"}
          </button>
        </div>
      </div>

      {/* Right Panel — World State */}
      <div style={{
        width: 280, borderLeft: "1px solid #1a1a2e", display: "flex",
        flexDirection: "column", overflow: "hidden", flexShrink: 0,
      }}>
        {/* Panel Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #1a1a2e" }}>
          {["status", "subsystems", "actions"].map(tab => (
            <button key={tab} onClick={() => setActivePanel(tab)} style={{
              flex: 1, padding: "7px 0", border: "none",
              background: activePanel === tab ? "#12122a" : "transparent",
              color: activePanel === tab ? "#e94560" : "#555",
              fontSize: 10, fontWeight: 700, cursor: "pointer",
              textTransform: "uppercase",
              borderBottom: activePanel === tab ? "2px solid #e94560" : "2px solid transparent",
            }}>
              {tab}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: 10 }}>
          {activePanel === "status" && (
            <StatusPanel worldState={worldState} loading={stateLoading} />
          )}
          {activePanel === "subsystems" && (
            <SubsystemsPanel subsystems={subsystems} loading={stateLoading} />
          )}
          {activePanel === "actions" && (
            <ActionsPanel onSend={(q) => { setInput(q); }} />
          )}
        </div>
      </div>
    </div>
  );
}


function StatusPanel({ worldState, loading }) {
  if (loading) return <div style={{ color: "#555", fontSize: 11 }}>Loading state...</div>;
  if (!worldState) return <div style={{ color: "#555", fontSize: 11 }}>No state available</div>;

  const sections = [
    { label: "Health", value: worldState.health || "unknown", color: worldState.health === "healthy" ? "#4caf50" : "#f44336" },
    { label: "Runtime", value: worldState.runtime?.paused ? "Paused" : "Running", color: worldState.runtime?.paused ? "#f59e0b" : "#4caf50" },
  ];

  const kb = worldState.knowledge_base || {};
  const caps = worldState.capabilities || {};
  const cache = worldState.cache || {};
  const costs = worldState.api_costs || {};

  return (
    <div style={{ fontSize: 10, color: "#aaa", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#e94560" }}>System Status</div>
      {sections.map(s => (
        <div key={s.label} style={{ display: "flex", justifyContent: "space-between" }}>
          <span>{s.label}</span>
          <span style={{ color: s.color, fontWeight: 700 }}>{s.value}</span>
        </div>
      ))}

      <div style={{ borderTop: "1px solid #1a1a2e", paddingTop: 6, marginTop: 2 }}>
        <div style={{ fontWeight: 700, color: "#888", marginBottom: 4 }}>Database</div>
        <div>Tables: {kb.total_tables || 0}</div>
        <div>Rows: {(kb.total_rows || 0).toLocaleString()}</div>
        <div>Size: {kb.db_size_mb || 0} MB</div>
      </div>

      <div style={{ borderTop: "1px solid #1a1a2e", paddingTop: 6 }}>
        <div style={{ fontWeight: 700, color: "#888", marginBottom: 4 }}>Brain Capabilities</div>
        <div>Total actions: {caps.total_actions || 0}</div>
        {caps.domains && Object.entries(caps.domains).map(([k, v]) => (
          <div key={k} style={{ paddingLeft: 8 }}>{k}: {v.count} actions</div>
        ))}
      </div>

      {cache.size !== undefined && (
        <div style={{ borderTop: "1px solid #1a1a2e", paddingTop: 6 }}>
          <div style={{ fontWeight: 700, color: "#888", marginBottom: 4 }}>LLM Cache</div>
          <div>Size: {cache.size}/{cache.max_size}</div>
          <div>Hit rate: {(cache.hit_rate * 100).toFixed(1)}%</div>
        </div>
      )}

      {costs.total_cost_usd !== undefined && (
        <div style={{ borderTop: "1px solid #1a1a2e", paddingTop: 6 }}>
          <div style={{ fontWeight: 700, color: "#888", marginBottom: 4 }}>API Costs</div>
          <div>Total: ${costs.total_cost_usd.toFixed(4)}</div>
        </div>
      )}
    </div>
  );
}


function SubsystemsPanel({ subsystems, loading }) {
  if (loading) return <div style={{ color: "#555", fontSize: 11 }}>Loading...</div>;

  const statusIcon = (s) => {
    if (s === "healthy") return "🟢";
    if (s === "degraded") return "🟡";
    if (s === "stopped" || s === "disabled") return "⚪";
    if (s === "unhealthy" || s === "error") return "🔴";
    return "⚪";
  };

  return (
    <div style={{ fontSize: 10, color: "#aaa" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#e94560", marginBottom: 8 }}>Subsystems</div>
      {subsystems.map((s, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "4px 0", borderBottom: "1px solid #0d0d20",
        }}>
          <span>{statusIcon(s.status)}</span>
          <span style={{ flex: 1 }}>{s.name}</span>
          <span style={{ fontSize: 9, color: "#555" }}>{s.status}</span>
        </div>
      ))}
    </div>
  );
}


function ActionsPanel({ onSend }) {
  const quickQueries = [
    { label: "Run health check", icon: "🏥" },
    { label: "Show all errors", icon: "🔴" },
    { label: "What's the trust score for Kimi?", icon: "🛡️" },
    { label: "How many brain actions exist?", icon: "🧠" },
    { label: "What is the database size?", icon: "🗄️" },
    { label: "Show worker pool status", icon: "🏊" },
    { label: "What is the LLM cache hit rate?", icon: "💾" },
    { label: "List all components", icon: "🔎" },
    { label: "Show Genesis key stats", icon: "🔑" },
    { label: "Explain the coding pipeline", icon: "🏗️" },
    { label: "What models are available?", icon: "🤖" },
    { label: "Show recent activity", icon: "📊" },
  ];

  return (
    <div style={{ fontSize: 10, color: "#aaa" }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#e94560", marginBottom: 8 }}>Quick Queries</div>
      {quickQueries.map((q, i) => (
        <button key={i} onClick={() => onSend(q.label)} style={{
          display: "flex", alignItems: "center", gap: 6, width: "100%",
          padding: "5px 6px", border: "none", background: "transparent",
          color: "#888", cursor: "pointer", fontSize: 10, textAlign: "left",
          borderRadius: 4,
        }}
        onMouseEnter={e => e.target.style.background = "#12122a"}
        onMouseLeave={e => e.target.style.background = "transparent"}
        >
          <span>{q.icon}</span> {q.label}
        </button>
      ))}
    </div>
  );
}
