import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL } from "../config/api";

const B = API_BASE_URL;

const SECTIONS = [
  { id: "console", label: "Console Chat" },
  { id: "diagnostics", label: "Diagnostics" },
  { id: "stress", label: "Stress Test" },
  { id: "triggers", label: "Triggers" },
  { id: "gaps", label: "Knowledge Gaps" },
  { id: "apis", label: "API Audit" },
  { id: "connectivity", label: "Connectivity" },
  { id: "runtime", label: "Runtime" },
  { id: "healing", label: "Self-Healing" },
];

export default function DevTab() {
  const [section, setSection] = useState("console");

  return (
    <div style={{ display: "flex", height: "100%", background: "#0a0a1a", color: "#ccc" }}>
      <Sidebar section={section} setSection={setSection} />
      <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
        {section === "console" && <ConsoleChat />}
        {section === "diagnostics" && <DiagnosticsPanel />}
        {section === "stress" && <StressTestPanel />}
        {section === "triggers" && <TriggersPanel />}
        {section === "gaps" && <KnowledgeGapsPanel />}
        {section === "apis" && <APIAuditPanel />}
        {section === "connectivity" && <ConnectivityPanel />}
        {section === "runtime" && <RuntimePanel />}
        {section === "healing" && <HealingPanel />}
      </div>
    </div>
  );
}

/* ── Sidebar ──────────────────────────────────────────────────────── */

function Sidebar({ section, setSection }) {
  const [actionResult, setActionResult] = useState(null);
  const act = async (label, url) => {
    const data = await jf(url, { method: "POST" });
    setActionResult({ label, data, ts: Date.now() });
  };

  return (
    <div style={{ width: 190, borderRight: "1px solid #222", padding: "12px 0", flexShrink: 0, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "0 16px 12px", fontSize: 15, fontWeight: 800, color: "#e94560" }}>Dev Command</div>
      <div style={{ flex: 1, overflow: "auto" }}>
        {SECTIONS.map(s => (
          <button key={s.id} onClick={() => setSection(s.id)} style={{
            display: "block", width: "100%", textAlign: "left", padding: "7px 16px",
            background: section === s.id ? "#1a1a3a" : "none", border: "none",
            color: section === s.id ? "#e94560" : "#888", cursor: "pointer",
            fontSize: 12, fontWeight: section === s.id ? 700 : 400,
            borderLeft: section === s.id ? "3px solid #e94560" : "3px solid transparent",
          }}>{s.label}</button>
        ))}
      </div>
      <div style={{ borderTop: "1px solid #222", padding: "10px 12px" }}>
        <div style={{ fontSize: 10, color: "#555", marginBottom: 6 }}>QUICK ACTIONS</div>
        <button onClick={() => act("Hot Reload", `${B}/api/runtime/hot-reload`)} style={qBtn("#2563eb")}>Hot Reload</button>
        <button onClick={() => act("Scan+Heal", `${B}/api/triggers/scan-and-heal`)} style={qBtn("#8b5cf6")}>Scan &amp; Heal</button>
        <button onClick={() => act("Pause", `${B}/api/runtime/pause`)} style={qBtn("#f59e0b")}>Pause Runtime</button>
        <button onClick={() => act("Resume", `${B}/api/runtime/resume`)} style={qBtn("#10b981")}>Resume Runtime</button>
        {actionResult && (
          <div style={{ marginTop: 6, fontSize: 10, color: actionResult.data?.error ? "#f44336" : "#4caf50", wordBreak: "break-all" }}>
            {actionResult.label}: {actionResult.data?.status || actionResult.data?.error || "done"}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Console Chat (bidirectional — individual models + consensus) ── */

function ConsoleChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("consensus");
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    jf(`${B}/api/consensus/models`).then(d => setModels(d.models || []));
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input, ts: Date.now() };
    setMessages(p => [...p, userMsg]);
    setInput("");
    setLoading(true);

    try {
      let data;
      if (model === "consensus") {
        data = await jf(`${B}/api/consensus/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: input }),
        });
        setMessages(p => [...p, {
          role: "assistant", model: "Consensus",
          content: data.final_output || data.consensus || data.error || "No response",
          confidence: data.confidence,
          models_used: data.models_used,
          agreements: data.agreements,
          disagreements: data.disagreements,
          individual: data.individual_responses,
          ts: Date.now(),
        }]);
      } else if (model === "console") {
        data = await jf(`${B}/api/console/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: input, use_consensus: false }),
        });
        setMessages(p => [...p, {
          role: "assistant", model: "Console",
          content: data.response || data.error || "No response",
          confidence: data.confidence,
          ts: Date.now(),
        }]);
      } else {
        data = await jf(`${B}/api/consensus/fast`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: input, models: [model] }),
        });
        const resp = data.individual_responses?.[0];
        setMessages(p => [...p, {
          role: "assistant", model: model,
          content: resp?.response || data.final_output || data.error || "No response",
          latency: resp?.latency_ms,
          ts: Date.now(),
        }]);
      }
    } catch (e) {
      setMessages(p => [...p, { role: "error", content: e.message, ts: Date.now() }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <h2 style={h2s}>Talk to Grace</h2>
        <select value={model} onChange={e => setModel(e.target.value)} style={selectS}>
          <option value="consensus">Consensus (All Models)</option>
          <option value="console">Console (Kimi+Opus)</option>
          {models.map(m => (
            <option key={m.id} value={m.id} disabled={!m.available}>
              {m.name} {m.available ? "" : "(unavailable)"}
            </option>
          ))}
        </select>
      </div>

      <div style={{ flex: 1, overflow: "auto", marginBottom: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.length === 0 && (
          <div style={{ color: "#555", fontSize: 13, padding: 20, textAlign: "center" }}>
            Ask Grace about diagnostics, what's broken, what needs fixing,<br />
            or discuss architecture decisions with any model directly.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "80%", padding: "10px 14px", borderRadius: 10,
            background: m.role === "user" ? "#1a3a5a" : m.role === "error" ? "#3a1a1a" : "#12122a",
            border: `1px solid ${m.role === "user" ? "#2563eb33" : m.role === "error" ? "#f4433633" : "#33333366"}`,
          }}>
            {m.model && <div style={{ fontSize: 10, color: "#e94560", fontWeight: 700, marginBottom: 4 }}>{m.model}</div>}
            <div style={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{m.content}</div>
            {m.confidence != null && <div style={{ fontSize: 10, color: "#888", marginTop: 4 }}>Confidence: {(m.confidence * 100).toFixed(0)}%</div>}
            {m.models_used && <div style={{ fontSize: 10, color: "#888" }}>Models: {m.models_used.join(", ")}</div>}
            {m.agreements?.length > 0 && <div style={{ fontSize: 10, color: "#4caf50", marginTop: 4 }}>Agreements: {m.agreements.join("; ")}</div>}
            {m.disagreements?.length > 0 && <div style={{ fontSize: 10, color: "#f59e0b" }}>Disagreements: {m.disagreements.join("; ")}</div>}
            {m.individual && m.individual.length > 1 && (
              <details style={{ marginTop: 6 }}>
                <summary style={{ fontSize: 10, color: "#888", cursor: "pointer" }}>Individual responses ({m.individual.length})</summary>
                {m.individual.map((r, j) => (
                  <div key={j} style={{ marginTop: 4, padding: 6, background: "#0d0d20", borderRadius: 4, fontSize: 11 }}>
                    <strong style={{ color: "#e94560" }}>{r.model_name}</strong>
                    {r.error && <span style={{ color: "#f44336" }}> (error: {r.error})</span>}
                    <div style={{ marginTop: 2, color: "#aaa" }}>{(r.response || "").slice(0, 400)}{r.response?.length > 400 ? "..." : ""}</div>
                  </div>
                ))}
              </details>
            )}
            {m.latency && <div style={{ fontSize: 10, color: "#888" }}>{m.latency}ms</div>}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder={`Ask ${model === "consensus" ? "all models" : model}...`}
          style={{ flex: 1, padding: "10px 14px", background: "#12122a", border: "1px solid #333", borderRadius: 8, color: "#ccc", fontSize: 13, outline: "none" }}
          disabled={loading}
        />
        <button onClick={send} disabled={loading} style={{ ...actBtn("#e94560"), opacity: loading ? 0.5 : 1, minWidth: 80 }}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

/* ── Diagnostics Panel ────────────────────────────────────────────── */

function DiagnosticsPanel() {
  const [diag, setDiag] = useState(null);
  const [fullReport, setFullReport] = useState(null);
  const [logicTests, setLogicTests] = useState(null);
  const [loading, setLoading] = useState({});

  const run = async (key, url, setter) => {
    setLoading(p => ({ ...p, [key]: true }));
    setter(await jf(url));
    setLoading(p => ({ ...p, [key]: false }));
  };

  return (
    <div>
      <h2 style={h2s}>Diagnostics</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={() => run("diag", `${B}/api/audit/diagnostics/startup`, setDiag)} style={actBtn("#2563eb")} disabled={loading.diag}>{loading.diag ? "Running..." : "Startup Diagnostic"}</button>
        <button onClick={() => run("full", `${B}/diagnostic/full-report`, setFullReport)} style={actBtn("#8b5cf6")} disabled={loading.full}>{loading.full ? "Running..." : "Full 4-Layer Report"}</button>
        <button onClick={() => run("logic", `${B}/api/audit/test/logic`, setLogicTests)} style={actBtn("#10b981")} disabled={loading.logic}>{loading.logic ? "Running..." : "Logic Tests"}</button>
        <button onClick={() => run("diag", `${B}/api/audit/diagnostics/daily`, setDiag)} style={actBtn("#f59e0b")}>Daily Report</button>
        <button onClick={() => run("diag", `${B}/api/console/diagnose`, setDiag)} style={actBtn("#ef4444")}>Kimi+Opus Diagnose</button>
      </div>

      {logicTests && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={h3s}>Logic Test Results</h3>
          <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
            {["passed", "failed", "total", "pass_rate", "status"].map(k => logicTests[k] != null && (
              <div key={k} style={{ ...card, padding: "8px 14px", textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: k === "failed" && logicTests[k] > 0 ? "#f44336" : k === "status" && logicTests[k] === "pass" ? "#4caf50" : "#ccc" }}>
                  {k === "pass_rate" ? `${logicTests[k]}%` : logicTests[k]}
                </div>
              </div>
            ))}
          </div>
          {logicTests.results && (
            <table style={tbl}><thead><tr>{["Test", "Status", "Detail"].map(h => <th key={h} style={th}>{h}</th>)}</tr></thead>
              <tbody>{logicTests.results.map((r, i) => (
                <tr key={i} style={trS}><td style={td}>{r.name || r.test}</td><td style={td}>{badge(r.status === "pass" || r.passed, r.status || (r.passed ? "pass" : "fail"))}</td><td style={td}>{r.detail || r.error || ""}</td></tr>
              ))}</tbody></table>
          )}
        </div>
      )}

      {fullReport && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={h3s}>4-Layer Diagnostic Report</h3>
          {["sensors", "interpretation", "judgement", "action"].map(layer => fullReport[layer] && (
            <details key={layer} open={layer === "judgement" || layer === "action"} style={{ marginBottom: 8 }}>
              <summary style={{ fontSize: 13, fontWeight: 700, color: "#e94560", cursor: "pointer", textTransform: "capitalize" }}>{layer}</summary>
              <pre style={pre}>{JSON.stringify(fullReport[layer], null, 2)}</pre>
            </details>
          ))}
        </div>
      )}

      {diag && <div><h3 style={h3s}>Diagnostic Output</h3><pre style={pre}>{JSON.stringify(diag, null, 2)}</pre></div>}
    </div>
  );
}

/* ── Stress Test Panel ────────────────────────────────────────────── */

function StressTestPanel() {
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState({});

  const run = async (key, url, setter, method = "GET") => {
    setLoading(p => ({ ...p, [key]: true }));
    setter(await jf(url, method !== "GET" ? { method } : undefined));
    setLoading(p => ({ ...p, [key]: false }));
  };

  useEffect(() => { run("status", `${B}/api/audit/test/stress/status`, setStatus); }, []);

  return (
    <div>
      <h2 style={h2s}>Stress Testing</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={() => run("start", `${B}/api/audit/test/stress/start?duration_minutes=5&interval_seconds=30`, setResult, "POST")} style={actBtn("#ef4444")} disabled={loading.start}>Start Stress Test</button>
        <button onClick={() => run("stop", `${B}/api/audit/test/stress/stop`, setResult, "POST")} style={actBtn("#f59e0b")} disabled={loading.stop}>Stop</button>
        <button onClick={() => run("status", `${B}/api/audit/test/stress/status`, setStatus)} style={actBtn("#2563eb")}>Refresh Status</button>
        <button onClick={() => run("pipeline", `${B}/api/triggers/stress-heal`, setResult, "POST")} style={actBtn("#8b5cf6")} disabled={loading.pipeline}>
          {loading.pipeline ? "Running..." : "Stress → Diagnose → Heal (Full Pipeline)"}
        </button>
      </div>

      {status && <div style={{ marginBottom: 16 }}><h3 style={h3s}>Status</h3><pre style={pre}>{JSON.stringify(status, null, 2)}</pre></div>}
      {result && (
        <div>
          <h3 style={h3s}>Results</h3>
          {result.stress && (
            <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
              {Object.entries(result.stress).filter(([k]) => k !== "error").map(([k, v]) => (
                <div key={k} style={{ ...card, padding: "8px 14px", textAlign: "center" }}>
                  <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: k === "failed" && v > 0 ? "#f44336" : "#ccc" }}>{typeof v === "number" ? (k.includes("rate") ? `${v}%` : v) : String(v)}</div>
                </div>
              ))}
            </div>
          )}
          <pre style={pre}>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

/* ── Triggers Panel ───────────────────────────────────────────────── */

function TriggersPanel() {
  const [scan, setScan] = useState(null);
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState({});

  const run = async (key, url, setter, method) => {
    setLoading(p => ({ ...p, [key]: true }));
    setter(await jf(url, method ? { method } : undefined));
    setLoading(p => ({ ...p, [key]: false }));
  };

  useEffect(() => { run("log", `${B}/api/triggers/log?limit=50`, setLog); }, []);

  const sevColor = { critical: "#f44336", warning: "#f59e0b", info: "#2563eb" };

  return (
    <div>
      <h2 style={h2s}>Trigger Monitor</h2>
      <p style={{ fontSize: 12, color: "#888", marginBottom: 12 }}>Scans: CPU/RAM, services, code imports, port conflicts, test failures. Critical triggers auto-fire self-healing.</p>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => run("scan", `${B}/api/triggers/scan`, setScan)} style={actBtn("#2563eb")} disabled={loading.scan}>{loading.scan ? "Scanning..." : "Scan Now"}</button>
        <button onClick={() => run("heal", `${B}/api/triggers/scan-and-heal`, setScan, "POST")} style={actBtn("#8b5cf6")} disabled={loading.heal}>{loading.heal ? "Healing..." : "Scan & Auto-Heal"}</button>
        <button onClick={() => run("log", `${B}/api/triggers/log?limit=50`, setLog)} style={actBtn("#10b981")}>Refresh Log</button>
      </div>

      {scan && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <div style={{ ...card, padding: "8px 14px" }}>Total: <strong>{scan.total ?? scan.scan?.total}</strong></div>
            <div style={{ ...card, padding: "8px 14px", color: "#f44336" }}>Critical: <strong>{scan.critical ?? scan.scan?.critical}</strong></div>
            <div style={{ ...card, padding: "8px 14px", color: "#f59e0b" }}>Warning: <strong>{scan.warning ?? scan.scan?.warning}</strong></div>
          </div>
          {(scan.triggers || scan.scan?.triggers || []).map((t, i) => (
            <div key={i} style={{ ...card, marginBottom: 6, padding: "8px 12px", borderLeft: `3px solid ${sevColor[t.severity] || "#555"}` }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, fontWeight: 700 }}>{t.category} / {t.name}</span>
                <span style={{ fontSize: 10, color: sevColor[t.severity] || "#888" }}>{t.severity}</span>
              </div>
              <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>{t.detail}</div>
            </div>
          ))}
          {scan.healing && scan.healing.healed > 0 && (
            <div style={{ ...card, marginTop: 8, borderLeft: "3px solid #4caf50" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#4caf50" }}>Auto-healed {scan.healing.healed} issue(s)</div>
              {scan.healing.actions.map((a, i) => <div key={i} style={{ fontSize: 11, color: "#aaa" }}>{a.action}: {a.trigger || a.note || ""}</div>)}
            </div>
          )}
        </div>
      )}

      {log?.log?.length > 0 && (
        <div>
          <h3 style={h3s}>Trigger History</h3>
          <table style={tbl}>
            <thead><tr>{["Time", "Category", "Name", "Severity", "Detail"].map(h => <th key={h} style={th}>{h}</th>)}</tr></thead>
            <tbody>{log.log.map((t, i) => (
              <tr key={i} style={trS}>
                <td style={td}>{t.timestamp?.slice(11, 19)}</td>
                <td style={td}>{t.category}</td>
                <td style={td}>{t.name}</td>
                <td style={td}><span style={{ color: sevColor[t.severity] || "#888" }}>{t.severity}</span></td>
                <td style={td}>{t.detail?.slice(0, 80)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── Knowledge Gaps Panel ─────────────────────────────────────────── */

function KnowledgeGapsPanel() {
  const [gaps, setGaps] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState({});

  const run = async (key, url, setter) => {
    setLoading(p => ({ ...p, [key]: true }));
    setter(await jf(url));
    setLoading(p => ({ ...p, [key]: false }));
  };

  return (
    <div>
      <h2 style={h2s}>Knowledge Gaps &amp; Integration Matrix</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={() => run("gaps", `${B}/api/audit/knowledge-gaps`, setGaps)} style={actBtn("#2563eb")} disabled={loading.gaps}>{loading.gaps ? "Scanning..." : "Scan Knowledge Gaps"}</button>
        <button onClick={() => run("sug", `${B}/api/audit/knowledge-gaps/suggestions?limit=20`, setSuggestions)} style={actBtn("#10b981")} disabled={loading.sug}>Get Suggestions</button>
        <button onClick={() => run("matrix", `${B}/api/audit/integration-matrix`, setMatrix)} style={actBtn("#8b5cf6")} disabled={loading.matrix}>{loading.matrix ? "Building..." : "Integration Matrix"}</button>
      </div>

      {gaps && <div style={{ marginBottom: 16 }}><h3 style={h3s}>Knowledge Gaps</h3><pre style={pre}>{JSON.stringify(gaps, null, 2)}</pre></div>}
      {suggestions && <div style={{ marginBottom: 16 }}><h3 style={h3s}>Expansion Suggestions</h3><pre style={pre}>{JSON.stringify(suggestions, null, 2)}</pre></div>}
      {matrix && (
        <div>
          <h3 style={h3s}>Integration Matrix</h3>
          {matrix.matrix ? (
            <table style={tbl}>
              <thead><tr><th style={th}>System</th>{(matrix.systems || []).map(s => <th key={s} style={{ ...th, fontSize: 10, writingMode: "vertical-lr" }}>{s}</th>)}</tr></thead>
              <tbody>{(matrix.matrix || []).map((row, i) => (
                <tr key={i} style={trS}>
                  <td style={{ ...td, fontWeight: 700 }}>{row.system}</td>
                  {(matrix.systems || []).map(s => {
                    const v = row.connections?.[s];
                    const c = v === "connected" ? "#4caf50" : v === "should_connect" ? "#f44336" : v === "self" ? "#555" : "#333";
                    return <td key={s} style={{ ...td, background: c + "22", color: c, fontSize: 10, textAlign: "center" }}>{v === "connected" ? "OK" : v === "should_connect" ? "MISS" : v === "self" ? "-" : ""}</td>;
                  })}
                </tr>
              ))}</tbody>
            </table>
          ) : <pre style={pre}>{JSON.stringify(matrix, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}

/* ── API Audit Panel ──────────────────────────────────────────────── */

function APIAuditPanel() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    setHealth(await jf(`${B}/api/registry/health-check`));
    setLoading(false);
  };

  useEffect(() => { run(); }, []);

  return (
    <div>
      <h2 style={h2s}>API Connectivity Audit</h2>
      <button onClick={run} style={{ ...actBtn("#2563eb"), marginBottom: 12 }} disabled={loading}>{loading ? "Scanning..." : "Re-Scan All APIs"}</button>

      {health?.summary && (
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          {Object.entries(health.summary).map(([k, v]) => (
            <div key={k} style={{ ...card, padding: "8px 14px", textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: k === "broken" && v > 0 ? "#f44336" : k === "unconnected" && v > 0 ? "#f59e0b" : "#4caf50" }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      {health?.internal && (
        <table style={tbl}>
          <thead><tr>{["Path", "Status", "Latency"].map(h => <th key={h} style={th}>{h}</th>)}</tr></thead>
          <tbody>{health.internal.map((r, i) => (
            <tr key={i} style={trS}>
              <td style={td}><code style={{ fontSize: 11 }}>{r.path}</code></td>
              <td style={td}>{badge(r.healthy || r.status_code < 400, r.status_code || (r.healthy ? "OK" : "ERR"))}</td>
              <td style={td}>{r.latency_ms ? `${r.latency_ms}ms` : "-"}</td>
            </tr>
          ))}</tbody>
        </table>
      )}

      {health && !health.internal && <pre style={pre}>{JSON.stringify(health, null, 2)}</pre>}
    </div>
  );
}

/* ── Connectivity Panel ───────────────────────────────────────────── */

function ConnectivityPanel() {
  const [conn, setConn] = useState(null);
  const [runtime, setRuntime] = useState(null);
  useEffect(() => {
    jf(`${B}/api/runtime/connectivity`).then(setConn);
    jf(`${B}/api/runtime/status`).then(setRuntime);
  }, []);

  return (
    <div>
      <h2 style={h2s}>Service Connectivity</h2>
      {conn?.services && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12, marginBottom: 20 }}>
          {Object.entries(conn.services).map(([name, info]) => (
            <div key={name} style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 700, textTransform: "capitalize" }}>{name}</span>
                {badge(info.connected || info.configured)}
              </div>
              {Object.entries(info).filter(([k]) => !["connected", "configured"].includes(k)).map(([k, v]) => (
                <div key={k} style={{ fontSize: 11, color: "#888" }}>{k}: <span style={{ color: "#aaa" }}>{String(v)}</span></div>
              ))}
            </div>
          ))}
        </div>
      )}
      {runtime && (
        <div>
          <h3 style={h3s}>Runtime</h3>
          <div style={card}>
            <div>State: {badge(!runtime.paused, "Running", "Paused")}</div>
            <div>Diagnostic: {badge(runtime.self_healing, runtime.diagnostic_engine)}</div>
            <div>Uptime: {runtime.uptime_seconds ? `${Math.floor(runtime.uptime_seconds / 60)}m` : "?"}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Runtime Panel ────────────────────────────────────────────────── */

function RuntimePanel() {
  const [result, setResult] = useState(null);
  const act = async (label, url) => {
    setResult({ label, data: await jf(url, { method: "POST" }), ts: Date.now() });
  };

  return (
    <div>
      <h2 style={h2s}>Runtime Controls</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div style={card}>
          <h3 style={h3s}>Pause / Resume</h3>
          <p style={{ fontSize: 11, color: "#888", marginBottom: 8 }}>Suspend diagnostic heartbeat and self-healing. APIs stay up.</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => act("Pause", `${B}/api/runtime/pause`)} style={actBtn("#f59e0b")}>Pause</button>
            <button onClick={() => act("Resume", `${B}/api/runtime/resume`)} style={actBtn("#10b981")}>Resume</button>
          </div>
        </div>
        <div style={card}>
          <h3 style={h3s}>Hot Reload</h3>
          <p style={{ fontSize: 11, color: "#888", marginBottom: 8 }}>Re-read .env, refresh models, reconnect DB, re-run diagnostic.</p>
          <button onClick={() => act("Hot Reload", `${B}/api/runtime/hot-reload`)} style={actBtn("#2563eb")}>Hot Reload Now</button>
        </div>
        <div style={card}>
          <h3 style={h3s}>Diagnostic Engine</h3>
          <p style={{ fontSize: 11, color: "#888", marginBottom: 8 }}>4-layer engine: Sensors → Interpreters → Judgement → Action Router.</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => act("Start", `${B}/diagnostic/start`)} style={actBtn("#10b981")}>Start</button>
            <button onClick={() => act("Stop", `${B}/diagnostic/stop`)} style={actBtn("#ef4444")}>Stop</button>
          </div>
        </div>
        <div style={card}>
          <h3 style={h3s}>Full Pipeline</h3>
          <p style={{ fontSize: 11, color: "#888", marginBottom: 8 }}>Stress → Diagnose → Scan Triggers → Auto-Heal.</p>
          <button onClick={() => act("Pipeline", `${B}/api/triggers/stress-heal`)} style={actBtn("#8b5cf6")}>Run Full Pipeline</button>
        </div>
      </div>
      {result && <div><h3 style={h3s}>{result.label} Result</h3><pre style={pre}>{JSON.stringify(result.data, null, 2)}</pre></div>}
    </div>
  );
}

/* ── Healing Panel ────────────────────────────────────────────────── */

function HealingPanel() {
  const [actions, setActions] = useState(null);
  const [log, setLog] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState({});

  const run = async (key, url, setter, opts) => {
    setLoading(p => ({ ...p, [key]: true }));
    setter(await jf(url, opts));
    setLoading(p => ({ ...p, [key]: false }));
  };

  useEffect(() => {
    run("actions", `${B}/diagnostic/healing/actions`, setActions);
    run("log", `${B}/api/system-health/heal/log`, setLog);
  }, []);

  const heal = async (actionType) => {
    setResult(await jf(`${B}/diagnostic/healing/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: actionType, dry_run: false }),
    }));
  };

  return (
    <div>
      <h2 style={h2s}>Self-Healing</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button onClick={() => run("log", `${B}/api/system-health/heal/log`, setLog)} style={actBtn("#2563eb")}>Refresh Log</button>
        <button onClick={() => heal("full")} style={actBtn("#8b5cf6")}>Full Heal</button>
        <button onClick={() => heal("database")} style={actBtn("#10b981")}>DB Reconnect</button>
        <button onClick={() => heal("gc")} style={actBtn("#f59e0b")}>GC Collect</button>
        <button onClick={() => run("immune", `${B}/api/system-health/immune/scan`, setResult, { method: "POST" })} style={actBtn("#ef4444")} disabled={loading.immune}>Immune Scan</button>
      </div>

      {actions?.actions && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={h3s}>Available Healing Actions</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
            {(Array.isArray(actions.actions) ? actions.actions : Object.entries(actions.actions).map(([k, v]) => ({ action_type: k, ...v }))).map((a, i) => (
              <div key={i} style={{ ...card, padding: "8px 12px", cursor: "pointer" }} onClick={() => heal(a.action_type || a.name)}>
                <div style={{ fontSize: 12, fontWeight: 700 }}>{a.action_type || a.name}</div>
                <div style={{ fontSize: 10, color: "#888" }}>Risk: {a.risk_level || "low"}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && <div style={{ marginBottom: 16 }}><h3 style={h3s}>Healing Result</h3><pre style={pre}>{JSON.stringify(result, null, 2)}</pre></div>}
      {log && <div><h3 style={h3s}>Healing History</h3><pre style={pre}>{JSON.stringify(log, null, 2)}</pre></div>}
    </div>
  );
}

/* ── Shared helpers ───────────────────────────────────────────────── */

async function jf(url, opts) {
  try {
    const r = await fetch(url, opts);
    return r.ok ? await r.json() : { error: `${r.status} ${r.statusText}` };
  } catch (e) {
    return { error: e.message };
  }
}

function badge(ok, yes = "OK", no = "FAIL") {
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700,
      background: ok ? "#1b3a2a" : "#3a1b1b", color: ok ? "#4caf50" : "#f44336",
    }}>{ok ? yes : no}</span>
  );
}

const h2s = { fontSize: 16, fontWeight: 700, color: "#e94560", margin: "0 0 12px" };
const h3s = { fontSize: 13, fontWeight: 700, color: "#ccc", margin: "0 0 8px" };
const card = { background: "#12122a", border: "1px solid #222", borderRadius: 8, padding: 16 };
const pre = { background: "#0d0d20", padding: 12, borderRadius: 6, fontSize: 11, overflow: "auto", maxHeight: 400, color: "#aaa", whiteSpace: "pre-wrap", wordBreak: "break-word" };
const th = { textAlign: "left", padding: "6px 10px", color: "#888", fontWeight: 600, borderBottom: "1px solid #333", fontSize: 11 };
const td = { padding: "5px 10px", color: "#ccc", fontSize: 12 };
const tbl = { width: "100%", borderCollapse: "collapse" };
const trS = { borderBottom: "1px solid #1a1a2e" };
const selectS = { padding: "6px 10px", background: "#12122a", border: "1px solid #333", borderRadius: 6, color: "#ccc", fontSize: 12, outline: "none" };
const qBtn = c => ({ display: "block", width: "100%", padding: "5px 8px", marginBottom: 4, border: "none", borderRadius: 4, background: c, color: "#fff", fontSize: 10, fontWeight: 600, cursor: "pointer" });
const actBtn = c => ({ padding: "6px 14px", border: "none", borderRadius: 4, background: c, color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer" });
