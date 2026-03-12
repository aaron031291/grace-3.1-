/**
 * AskTab — Query Grace's living architectural map in plain language.
 *
 * Examples:
 *   "What embedding model are we using?"
 *   "Trace path from pipeline to trust_engine"
 *   "What can handle code review?"
 *   "Explain the pipeline component"
 */

import { useState } from "react";
import { brainAsk } from "../api/brain-client";

const C = {
  bg: "#0a0a1a",
  panel: "#0d0d22",
  border: "#1a1a2e",
  accent: "#e94560",
  muted: "#555",
  text: "#ccc",
};

const SUGGESTIONS = [
  "How is memory unified in Grace?",
  "What embedding model are we using?",
  "What brains and APIs are available?",
  "Trace path from pipeline to trust_engine",
  "Explain the pipeline component",
  "Schema and databases info",
  "Models summary (LLM + embedding)",
  "Graphs in the system",
  "Full architecture map",
  "What can handle code review?",
];

export default function AskTab() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAsk = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await brainAsk(q);
      if (res?.error) setError(res.error);
      else setResult(res ?? { ok: false, data: null, error: "No response" });
    } catch (err) {
      setError(err?.message || "Request failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.bg, color: C.text }}>
      <div style={{ padding: 16, borderBottom: `1px solid ${C.border}`, background: C.panel }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: C.accent, marginBottom: 8 }}>
          Ask Grace about her architecture
        </div>
        <div style={{ fontSize: 12, color: C.muted, marginBottom: 12 }}>
          Query Grace in plain language: architecture, components, paths, models, schema, DBs, graphs, APIs, brains. Your question is routed to the right brain and the answer appears below.
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder="e.g. How is memory unified? What does the pipeline do?"
            style={{
              flex: 1,
              padding: "10px 12px",
              background: "#12122a",
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              color: C.text,
              fontSize: 14,
              outline: "none",
            }}
          />
          <button
            onClick={handleAsk}
            disabled={loading || !query.trim()}
            style={{
              padding: "10px 20px",
              background: loading ? C.muted : C.accent,
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: 13,
            }}
          >
            {loading ? "…" : "Ask"}
          </button>
        </div>
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setQuery(s)}
              style={{
                padding: "6px 10px",
                background: "transparent",
                border: `1px solid ${C.border}`,
                borderRadius: 6,
                color: C.muted,
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 16, minHeight: 0, background: C.bg }}>
        {error && (
          <div style={{ padding: 12, background: "#2a1515", border: "1px solid #5a2525", borderRadius: 8, color: "#f88", marginBottom: 12 }}>
            {typeof error === "string" ? error : JSON.stringify(error)}
          </div>
        )}
        {loading && (
          <div style={{ color: C.muted, fontSize: 13, padding: 16 }}>Asking Grace…</div>
        )}
        {result && !loading && (
          <div style={{ marginBottom: 12 }}>
            {result.routing && (
              <div style={{ padding: 10, background: "#0f0f28", border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 10, fontSize: 12, color: C.muted }}>
                <div>
                  <span style={{ color: C.accent }}>Routed:</span> {result.routing.brain}/{result.routing.action}
                  {result.routing.confidence != null && ` (confidence: ${result.routing.confidence})`}
                </div>
                {result.routing.low_confidence_hint && (
                  <div style={{ marginTop: 8, color: "#f5a623" }}>
                    {result.routing.low_confidence_hint}
                  </div>
                )}
                {result.routing.nearest_actions?.length > 0 && (
                  <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {result.routing.nearest_actions.map(a => (
                      <button
                        key={a.path}
                        onClick={() => { setQuery(a.path); handleAsk(); }}
                        style={{
                          padding: "4px 8px", background: "rgba(233, 69, 96, 0.1)",
                          border: `1px solid ${C.accent}`, borderRadius: 4,
                          color: C.accent, fontSize: 11, cursor: "pointer"
                        }}
                      >
                        {a.path} (Match: {a.score})
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {result.data != null && typeof result.data === "object" && result.data.summary && (
              <div style={{ padding: 12, background: "#0f1220", border: `1px solid ${C.border}`, borderRadius: 8, marginBottom: 10, fontSize: 14, color: C.text, lineHeight: 1.5 }}>
                {typeof result.data.summary === "string" ? result.data.summary : JSON.stringify(result.data.summary)}
              </div>
            )}
            <pre
              style={{
                margin: 0,
                padding: 12,
                background: "#08081a",
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                fontSize: 12,
                overflow: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                color: C.text,
              }}
            >
              {result.data == null
                ? (typeof result.error === "string" ? result.error : JSON.stringify(result.error) || "No data")
                : typeof result.data === "string"
                  ? result.data
                  : (() => {
                    try {
                      return JSON.stringify(result.data, null, 2);
                    } catch (_) {
                      return String(result.data);
                    }
                  })()}
            </pre>
          </div>
        )}
        {!result && !error && !loading && (
          <div style={{ color: C.muted, fontSize: 13, textAlign: "center", padding: 40 }}>
            Enter a question above or pick a suggestion. Results appear here.
          </div>
        )}
      </div>
    </div>
  );
}
