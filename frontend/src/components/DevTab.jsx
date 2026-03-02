import { useState, useEffect, useRef, useCallback } from "react";
import { brainCall } from "../api/brain-client";

const B = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000");

export default function DevTab() {
  const [detailPanel, setDetailPanel] = useState(null);

  return (
    <div style={{ display: "flex", height: "100%", background: "#0a0a1a", color: "#ccc" }}>
      <LeftPanel onAction={setDetailPanel} />
      <CenterChat onDetail={setDetailPanel} />
      <RightDetail content={detailPanel} onClose={() => setDetailPanel(null)} />
    </div>
  );
}

/* ── LEFT PANEL — Actions ──────────────────────────────────────── */

const LEFT_ACTIONS = [
  { id: "probe", label: "Run Probe", icon: "📡", brain: "system", action: "probe" },
  { id: "stress", label: "Stress Test", icon: "⚡", brain: "system", action: "auto_cycle" },
  { id: "health", label: "Health Map", icon: "🗺️", brain: "system", action: "health_map" },
  { id: "problems", label: "Problems", icon: "🔴", brain: "system", action: "problems" },
  { id: "triggers", label: "Triggers", icon: "🎯", brain: "system", action: "triggers" },
  { id: "intelligence", label: "Intelligence", icon: "🧠", brain: "system", action: "intelligence" },
  { id: "trust", label: "Trust Scores", icon: "🛡️", brain: "system", action: "trust" },
  { id: "synapses", label: "Synapses", icon: "🔗", brain: "system", action: "synapses" },
  { id: "traces", label: "Traces", icon: "📊", brain: "system", action: "traces" },
  { id: "invariants", label: "Invariants", icon: "✅", brain: "ai", action: "invariants" },
  { id: "genesis", label: "Genesis Keys", icon: "🔑", brain: "govern", action: "genesis_stats" },
  { id: "runtime", label: "Runtime", icon: "⚙️", brain: "system", action: "runtime" },
  { id: "hot_reload", label: "Hot Reload", icon: "🔄", brain: "system", action: "hot_reload" },
  { id: "dl_train", label: "Train DL", icon: "🎓", brain: "ai", action: "dl_train" },
  { id: "cognitive", label: "Cognitive Report", icon: "🧬", brain: "ai", action: "cognitive_report" },
  { id: "knowledge", label: "Knowledge Gaps", icon: "📚", brain: "ai", action: "knowledge_gaps_deep" },
];

function LeftPanel({ onAction }) {
  const [loading, setLoading] = useState({});

  const run = async (item) => {
    setLoading(p => ({ ...p, [item.id]: true }));
    const r = await brainCall(item.brain, item.action, {});
    setLoading(p => ({ ...p, [item.id]: false }));
    onAction({ title: item.label, icon: item.icon, data: r.ok ? r.data : { error: r.error } });
  };

  return (
    <div style={{ width: 180, borderRight: "1px solid #1a1a2e", padding: "8px 0", overflow: "auto", flexShrink: 0 }}>
      <div style={{ padding: "4px 12px 8px", fontSize: 11, fontWeight: 800, color: "#e94560" }}>Actions</div>
      {LEFT_ACTIONS.map(item => (
        <button key={item.id} onClick={() => run(item)} disabled={loading[item.id]} style={{
          display: "flex", alignItems: "center", gap: 6, width: "100%",
          padding: "5px 12px", border: "none", background: "transparent",
          color: loading[item.id] ? "#e94560" : "#888", cursor: "pointer",
          fontSize: 11, textAlign: "left", opacity: loading[item.id] ? 0.6 : 1,
        }}>
          <span style={{ fontSize: 12 }}>{item.icon}</span>
          {loading[item.id] ? "..." : item.label}
        </button>
      ))}
    </div>
  );
}

/* ── CENTER — Consensus Chat ───────────────────────────────────── */

function CenterChat({ onDetail }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("consensus");
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [systemCtx, setSystemCtx] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    brainCall("ai", "models", {}).then(r => {
      if (r.ok && r.data?.models) setModels(r.data.models);
    });
    brainCall("system", "runtime", {}).then(r => {
      if (r.ok) setSystemCtx(r.data);
    });
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input, ts: Date.now() };
    setMessages(p => [...p, userMsg]);
    const query = input;
    setInput("");
    setLoading(true);

    try {
      let data;
      if (model === "consensus") {
        data = await brainCall("ai", "fast", { prompt: query, models: ["kimi", "opus"] });
      } else {
        data = await brainCall("ai", "fast", { prompt: query, models: [model] });
      }

      const d = data.data || data;
      setMessages(p => [...p, {
        role: "assistant",
        model: model === "consensus" ? "Consensus" : model,
        content: d.final_output || d.individual_responses?.[0]?.response || d.error || "No response",
        individual: d.individual_responses,
        confidence: d.confidence,
        models_used: d.models_used,
        ts: Date.now(),
      }]);
    } catch (e) {
      setMessages(p => [...p, { role: "error", content: e.message, ts: Date.now() }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #1a1a2e" }}>
      {/* Header */}
      <div style={{ padding: "8px 12px", borderBottom: "1px solid #1a1a2e", display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#e94560" }}>Dev Console</span>
        <select value={model} onChange={e => setModel(e.target.value)} style={{
          background: "#12122a", border: "1px solid #333", borderRadius: 4,
          color: "#ccc", padding: "2px 6px", fontSize: 10, outline: "none",
        }}>
          <option value="consensus">All Models</option>
          {models.map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        {systemCtx && (
          <span style={{ fontSize: 9, color: "#555" }}>
            {systemCtx.diagnostic_engine} | {systemCtx.self_healing ? "healing" : "off"}
          </span>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "8px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        {messages.length === 0 && (
          <div style={{ color: "#444", fontSize: 12, padding: 20, textAlign: "center" }}>
            Talk to Grace. All models see the system state, source code, and Genesis keys.<br />
            Ask about errors, architecture, what to fix, or run diagnostics.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} onClick={() => m.individual && onDetail({
            title: "Model Responses", data: { individual: m.individual, confidence: m.confidence }
          })} style={{
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%", padding: "8px 12px", borderRadius: 8,
            background: m.role === "user" ? "#1a2a4a" : m.role === "error" ? "#2a1515" : "#12122a",
            border: `1px solid ${m.role === "user" ? "#2563eb22" : "#22222244"}`,
            cursor: m.individual ? "pointer" : "default",
            fontSize: 12,
          }}>
            {m.model && <div style={{ fontSize: 9, color: "#e94560", fontWeight: 700, marginBottom: 3 }}>{m.model}</div>}
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{m.content}</div>
            {m.confidence != null && <div style={{ fontSize: 9, color: "#555", marginTop: 3 }}>Confidence: {(m.confidence * 100).toFixed(0)}% | Models: {m.models_used?.join(", ")}</div>}
            {m.individual?.length > 1 && <div style={{ fontSize: 9, color: "#e94560", marginTop: 2 }}>Click to see individual responses</div>}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "8px 12px", borderTop: "1px solid #1a1a2e", display: "flex", gap: 6 }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about errors, architecture, run diagnostics..."
          style={{ flex: 1, padding: "8px 10px", background: "#12122a", border: "1px solid #222", borderRadius: 6, color: "#ccc", fontSize: 12, outline: "none" }}
          disabled={loading} />
        <button onClick={send} disabled={loading} style={{
          padding: "6px 14px", background: "#e94560", border: "none", borderRadius: 6,
          color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer", opacity: loading ? 0.5 : 1,
        }}>{loading ? "..." : "Send"}</button>
      </div>
    </div>
  );
}

/* ── RIGHT PANEL — Detail View ─────────────────────────────────── */

function RightDetail({ content, onClose }) {
  if (!content) {
    return (
      <div style={{ width: 260, background: "#08081a", padding: 12, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#333", fontSize: 11, textAlign: "center" }}>
          Click actions or chat responses<br />to view details here
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: 300, background: "#08081a", borderLeft: "1px solid #1a1a2e", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: "8px 12px", borderBottom: "1px solid #1a1a2e", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700 }}>{content.icon || ""} {content.title}</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 14 }}>×</button>
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: 10 }}>
        {content.data?.individual ? (
          <div>
            {content.data.individual.map((r, i) => (
              <div key={i} style={{ marginBottom: 8, padding: 8, background: "#0d0d20", borderRadius: 6 }}>
                <div style={{ fontSize: 10, color: "#e94560", fontWeight: 700 }}>{r.model_name || r.model_id}</div>
                {r.error && <div style={{ fontSize: 10, color: "#f44336" }}>{r.error}</div>}
                <div style={{ fontSize: 11, color: "#aaa", marginTop: 4, whiteSpace: "pre-wrap" }}>{(r.response || "").slice(0, 500)}</div>
                {r.latency_ms && <div style={{ fontSize: 9, color: "#555" }}>{r.latency_ms}ms</div>}
              </div>
            ))}
          </div>
        ) : content.data?.error ? (
          <div style={{ color: "#f44336", fontSize: 12, padding: 8, background: "#2a1515", borderRadius: 6 }}>
            {content.data.error}
          </div>
        ) : (
          <pre style={{ fontSize: 10, color: "#aaa", whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>
            {JSON.stringify(content.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
