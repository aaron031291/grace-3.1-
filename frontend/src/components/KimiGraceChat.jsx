import { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../config/api";

const KIMI_API = `${API_BASE_URL}/llm-learning`;

export default function KimiGraceChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activePanel, setActivePanel] = useState("chat"); // chat | progress | schedule
  const [progressData, setProgressData] = useState(null);
  const [scheduleData, setScheduleData] = useState(null);
  const [kimiStatus, setKimiStatus] = useState(null);
  const [pendingConfirmations, setPendingConfirmations] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchKimiStatus();
    fetchProgress();
    fetchPendingConfirmations();
    fetchDashboard();
    const interval = setInterval(() => {
      fetchProgress();
      fetchPendingConfirmations();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchKimiStatus = async () => {
    try {
      const res = await fetch(`${KIMI_API}/kimi/status`);
      if (res.ok) setKimiStatus(await res.json());
    } catch (e) { console.error("Kimi status error:", e); }
  };

  const fetchProgress = async () => {
    try {
      const res = await fetch(`${KIMI_API}/progress`);
      if (res.ok) setProgressData(await res.json());
    } catch (e) { console.error("Progress error:", e); }
  };

  const fetchPendingConfirmations = async () => {
    try {
      const res = await fetch(`${KIMI_API}/grace/verification/pending`);
      if (res.ok) {
        const data = await res.json();
        setPendingConfirmations(data.confirmations || []);
      }
    } catch (e) { console.error("Pending confirmations error:", e); }
  };

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${KIMI_API}/dashboard`);
      if (res.ok) setDashboardData(await res.json());
    } catch (e) { console.error("Dashboard error:", e); }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    setMessages(prev => [...prev, {
      id: Date.now(),
      role: "user",
      content: userMsg,
      timestamp: new Date().toISOString(),
    }]);

    // Step 1: Grace analyzes (read-only)
    setMessages(prev => [...prev, {
      id: Date.now() + 1,
      role: "kimi",
      content: "Analyzing...",
      status: "thinking",
      timestamp: new Date().toISOString(),
    }]);

    try {
      const kimiRes = await fetch(`${KIMI_API}/kimi/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_request: userMsg }),
      });

      if (!kimiRes.ok) throw new Error(`Kimi error: ${kimiRes.status}`);
      const kimiData = await kimiRes.json();

      // Update Grace's message with analysis
      setMessages(prev => {
        const updated = [...prev];
        const kimiIdx = updated.findIndex(m => m.role === "kimi" && m.status === "thinking");
        if (kimiIdx >= 0) {
          updated[kimiIdx] = {
            ...updated[kimiIdx],
            content: kimiData.summary || "Analysis complete.",
            status: "complete",
            data: kimiData,
          };
        }
        return updated;
      });

      // Step 2: Grace verifies and executes
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: "grace",
        content: "Verifying and executing...",
        status: "working",
        timestamp: new Date().toISOString(),
      }]);

      const graceRes = await fetch(`${KIMI_API}/grace/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_request: userMsg }),
      });

      if (!graceRes.ok) throw new Error(`Grace error: ${graceRes.status}`);
      const graceData = await graceRes.json();

      setMessages(prev => {
        const updated = [...prev];
        const graceIdx = updated.findIndex(m => m.role === "grace" && m.status === "working");
        if (graceIdx >= 0) {
          updated[graceIdx] = {
            ...updated[graceIdx],
            content: graceData.grace_execution || "Execution complete.",
            status: "complete",
            data: graceData,
          };
        }
        return updated;
      });

      fetchProgress();
      fetchPendingConfirmations();

    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 3,
        role: "system",
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmation = async (checkId, approved) => {
    try {
      await fetch(`${KIMI_API}/grace/verification/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ check_id: checkId, approved, note: "" }),
      });
      fetchPendingConfirmations();
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: "user",
        content: `${approved ? "Approved" : "Rejected"} action (${checkId})`,
        timestamp: new Date().toISOString(),
      }]);
    } catch (e) {
      console.error("Confirmation error:", e);
    }
  };

  const formatTime = (iso) => {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  };

  const roleStyles = {
    user: { bg: "#2563eb", label: "You", color: "#fff" },
    kimi: { bg: "#8b5cf6", label: "Grace Brain", color: "#fff" },
    grace: { bg: "#059669", label: "Grace", color: "#fff" },
    system: { bg: "#6b7280", label: "System", color: "#fff" },
  };

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>
      {/* Left: Chat */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #333" }}>
        {/* Tab bar */}
        <div style={{ display: "flex", borderBottom: "1px solid #333", background: "#1a1a2e" }}>
          {[
            { key: "chat", label: "Chat" },
            { key: "progress", label: "Progress" },
            { key: "schedule", label: "Schedule" },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActivePanel(tab.key)}
              style={{
                flex: 1, padding: "10px", border: "none", cursor: "pointer",
                background: activePanel === tab.key ? "#2d2d4a" : "transparent",
                color: activePanel === tab.key ? "#fff" : "#888",
                fontWeight: activePanel === tab.key ? 600 : 400,
                borderBottom: activePanel === tab.key ? "2px solid #8b5cf6" : "2px solid transparent",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activePanel === "chat" && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            {/* Messages */}
            <div style={{ flex: 1, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {messages.length === 0 && (
                <div style={{ textAlign: "center", color: "#666", marginTop: "40px" }}>
                  <div style={{ fontSize: "48px", marginBottom: "16px" }}>🧠</div>
                  <h3 style={{ color: "#aaa", marginBottom: "8px" }}>Grace Intelligence Chat</h3>
                  <p style={{ fontSize: "14px" }}>
                    Talk to both Kimi and Grace. Grace analyzes (read-only brain),
                    Grace verifies and executes. You can chip in at any point.
                  </p>
                </div>
              )}
              {messages.map(msg => {
                const style = roleStyles[msg.role] || roleStyles.system;
                return (
                  <div key={msg.id} style={{
                    alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                    maxWidth: "80%",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{
                        fontSize: "11px", fontWeight: 600, padding: "2px 8px",
                        borderRadius: "10px", background: style.bg, color: style.color,
                      }}>
                        {style.label}
                      </span>
                      <span style={{ fontSize: "11px", color: "#666" }}>{formatTime(msg.timestamp)}</span>
                      {msg.status === "thinking" && <span style={{ fontSize: "11px", color: "#8b5cf6" }}>thinking...</span>}
                      {msg.status === "working" && <span style={{ fontSize: "11px", color: "#059669" }}>executing...</span>}
                    </div>
                    <div style={{
                      background: msg.role === "user" ? "#1e3a5f" : "#1a1a2e",
                      border: `1px solid ${msg.role === "user" ? "#2563eb44" : "#33335544"}`,
                      borderRadius: "12px", padding: "12px 16px",
                      color: "#ddd", fontSize: "14px", lineHeight: "1.5",
                      whiteSpace: "pre-wrap",
                    }}>
                      {msg.content}
                      {msg.data && msg.role === "kimi" && msg.data.instructions && (
                        <div style={{ marginTop: "8px", fontSize: "12px", color: "#aaa", borderTop: "1px solid #333", paddingTop: "8px" }}>
                          <strong>{msg.data.instructions.length} instructions</strong> produced
                          {msg.data.diagnosis && (
                            <span> | Health: {msg.data.diagnosis.health?.status || "unknown"}</span>
                          )}
                        </div>
                      )}
                      {msg.data && msg.role === "grace" && (
                        <div style={{ marginTop: "8px", fontSize: "12px", color: "#aaa", borderTop: "1px solid #333", paddingTop: "8px" }}>
                          <span style={{ color: msg.data.succeeded > 0 ? "#4ade80" : "#f87171" }}>
                            {msg.data.succeeded || 0} succeeded
                          </span>
                          {msg.data.failed > 0 && (
                            <span style={{ color: "#f87171" }}> | {msg.data.failed} failed</span>
                          )}
                          {msg.data.approved !== undefined && (
                            <span> | {msg.data.approved} approved, {msg.data.rejected} rejected</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Pending confirmations */}
            {pendingConfirmations.length > 0 && (
              <div style={{ padding: "8px 16px", background: "#332200", borderTop: "1px solid #664400" }}>
                <div style={{ fontSize: "12px", color: "#fbbf24", marginBottom: "4px", fontWeight: 600 }}>
                  Awaiting your confirmation ({pendingConfirmations.length})
                </div>
                {pendingConfirmations.slice(0, 2).map(conf => (
                  <div key={conf.check_id} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <span style={{ flex: 1, fontSize: "12px", color: "#ddd" }}>{conf.action?.substring(0, 80)}</span>
                    <button onClick={() => handleConfirmation(conf.check_id, true)}
                      style={{ padding: "4px 12px", borderRadius: "6px", border: "none", background: "#22c55e", color: "#fff", cursor: "pointer", fontSize: "11px" }}>
                      Approve
                    </button>
                    <button onClick={() => handleConfirmation(conf.check_id, false)}
                      style={{ padding: "4px 12px", borderRadius: "6px", border: "none", background: "#ef4444", color: "#fff", cursor: "pointer", fontSize: "11px" }}>
                      Reject
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Input */}
            <form onSubmit={sendMessage} style={{ display: "flex", gap: "8px", padding: "12px 16px", borderTop: "1px solid #333", background: "#111" }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Talk to Grace Intelligence..."
                disabled={loading}
                style={{
                  flex: 1, padding: "12px 16px", borderRadius: "8px",
                  border: "1px solid #444", background: "#1a1a2e", color: "#fff",
                  fontSize: "14px", outline: "none",
                }}
              />
              <button type="submit" disabled={loading || !input.trim()} style={{
                padding: "12px 24px", borderRadius: "8px", border: "none",
                background: loading ? "#444" : "#8b5cf6", color: "#fff",
                cursor: loading ? "default" : "pointer", fontWeight: 600,
              }}>
                {loading ? "..." : "Send"}
              </button>
            </form>
          </div>
        )}

        {activePanel === "progress" && (
          <div style={{ flex: 1, overflow: "auto", padding: "20px" }}>
            <h3 style={{ color: "#fff", marginBottom: "16px" }}>Learning Progress</h3>
            {progressData ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <StatCard label="Stage" value={progressData.learning_stage || "initial"} color="#8b5cf6" />
                  <StatCard label="Autonomy" value={`${((progressData.autonomy_readiness || 0) * 100).toFixed(1)}%`} color="#059669" />
                  <StatCard label="Patterns" value={progressData.patterns_extracted || 0} color="#2563eb" />
                  <StatCard label="Interactions" value={progressData.interactions_recorded || 0} color="#f59e0b" />
                  <StatCard label="Reasoning Paths" value={progressData.reasoning_paths_captured || 0} color="#ec4899" />
                  <StatCard label="Replaceable" value={progressData.patterns_replaceable || 0} color="#22c55e" />
                </div>
                {progressData.next_milestone && (
                  <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "#888", marginBottom: "4px" }}>Next Milestone</div>
                    <div style={{ color: "#fff", fontWeight: 600, marginBottom: "4px" }}>{progressData.next_milestone.name}</div>
                    <div style={{ fontSize: "13px", color: "#aaa", marginBottom: "8px" }}>{progressData.next_milestone.description}</div>
                    <div style={{ background: "#333", borderRadius: "4px", height: "8px", overflow: "hidden" }}>
                      <div style={{
                        width: `${(progressData.next_milestone.progress || 0) * 100}%`,
                        height: "100%", background: "#8b5cf6", borderRadius: "4px",
                        transition: "width 0.5s",
                      }} />
                    </div>
                  </div>
                )}
                {progressData.task_categories_covered && progressData.task_categories_covered.length > 0 && (
                  <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>Categories Covered</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {progressData.task_categories_covered.map(cat => (
                        <span key={cat} style={{ padding: "4px 10px", background: "#2d2d4a", borderRadius: "12px", fontSize: "12px", color: "#8b5cf6" }}>{cat}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: "#666" }}>Loading progress data...</div>
            )}
          </div>
        )}

        {activePanel === "schedule" && (
          <div style={{ flex: 1, overflow: "auto", padding: "20px" }}>
            <h3 style={{ color: "#fff", marginBottom: "16px" }}>Schedule & Time Sense</h3>
            {dashboardData ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                  <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>Interaction Stats (24h)</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
                    <MiniStat label="Total" value={dashboardData.interaction_stats_24h?.total || 0} />
                    <MiniStat label="Success" value={dashboardData.interaction_stats_24h?.outcomes?.success || 0} color="#4ade80" />
                    <MiniStat label="Failed" value={dashboardData.interaction_stats_24h?.outcomes?.failure || 0} color="#f87171" />
                  </div>
                </div>
                <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                  <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>Dependency Trend (7d)</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    <MiniStat label="Direction" value={dashboardData.dependency_trend_7d?.trend_direction || "unknown"} />
                    <MiniStat label="Current" value={`${((dashboardData.dependency_trend_7d?.current_dependency || 1) * 100).toFixed(0)}%`} />
                  </div>
                </div>
                {dashboardData.top_recommendations && dashboardData.top_recommendations.length > 0 && (
                  <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>Recommendations</div>
                    {dashboardData.top_recommendations.slice(0, 5).map((rec, i) => (
                      <div key={i} style={{
                        padding: "8px", marginBottom: "6px", borderRadius: "6px",
                        background: rec.priority === "high" ? "#331111" : "#1a1a2e",
                        border: `1px solid ${rec.priority === "high" ? "#661111" : "#333"}`,
                      }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                          <span style={{ fontSize: "12px", fontWeight: 600, color: "#fff" }}>{rec.task_type || rec.action}</span>
                          <span style={{
                            fontSize: "10px", padding: "2px 6px", borderRadius: "8px",
                            background: rec.priority === "high" ? "#ef4444" : rec.priority === "medium" ? "#f59e0b" : "#22c55e",
                            color: "#fff",
                          }}>{rec.priority}</span>
                        </div>
                        <div style={{ fontSize: "11px", color: "#aaa" }}>{rec.reason?.substring(0, 120)}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "16px" }}>
                  <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>What's Complete</div>
                  <CompletionItem label="LLM Interaction Tracking" done={true} />
                  <CompletionItem label="Grace Brain (read-only)" done={true} />
                  <CompletionItem label="Grace Verified Executor" done={true} />
                  <CompletionItem label="Multi-Source Verification (10 sources)" done={true} />
                  <CompletionItem label="Pattern Learner" done={true} />
                  <CompletionItem label="Dependency Reducer" done={true} />
                  <CompletionItem label="13-Layer Hallucination Guard" done={true} />
                  <CompletionItem label="Kimi+Grace Chat UI" done={true} />
                  <CompletionItem label="Progress & Schedule Tracking" done={true} />
                  <CompletionItem label="Bidirectional User Confirmation" done={true} />
                  <div style={{ fontSize: "12px", color: "#888", marginTop: "12px", marginBottom: "8px" }}>What's Next</div>
                  <CompletionItem label="Connect to live LLM models" done={false} />
                  <CompletionItem label="WebSocket real-time updates in chat" done={false} />
                  <CompletionItem label="Training data export to fine-tune local model" done={false} />
                  <CompletionItem label="Reach 50% autonomy readiness" done={false} />
                </div>
              </div>
            ) : (
              <div style={{ color: "#666" }}>Loading schedule data...</div>
            )}
          </div>
        )}
      </div>

      {/* Right: Kimi status sidebar */}
      <div style={{ width: "260px", background: "#111", padding: "16px", overflow: "auto" }}>
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "11px", color: "#666", textTransform: "uppercase", marginBottom: "8px" }}>Grace Brain</div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#8b5cf6" }}></span>
            <span style={{ fontSize: "13px", color: "#ddd" }}>Read-Only Intelligence</span>
          </div>
          {kimiStatus?.connected_systems && Object.entries(kimiStatus.connected_systems).map(([sys, connected]) => (
            <div key={sys} style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: connected ? "#4ade80" : "#666" }}></span>
              <span style={{ fontSize: "11px", color: connected ? "#aaa" : "#555" }}>{sys}</span>
            </div>
          ))}
        </div>

        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "11px", color: "#666", textTransform: "uppercase", marginBottom: "8px" }}>Grace Executor</div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#059669" }}></span>
            <span style={{ fontSize: "13px", color: "#ddd" }}>Verifies & Executes</span>
          </div>
          <div style={{ fontSize: "11px", color: "#888" }}>10-source verification active</div>
        </div>

        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "11px", color: "#666", textTransform: "uppercase", marginBottom: "8px" }}>Hallucination Guard</div>
          <div style={{ fontSize: "13px", color: "#ddd", marginBottom: "4px" }}>13 layers active</div>
          <div style={{ fontSize: "11px", color: "#888" }}>Target: 99% accuracy</div>
        </div>

        {progressData && (
          <div>
            <div style={{ fontSize: "11px", color: "#666", textTransform: "uppercase", marginBottom: "8px" }}>Autonomy</div>
            <div style={{ background: "#222", borderRadius: "4px", height: "8px", overflow: "hidden", marginBottom: "4px" }}>
              <div style={{
                width: `${(progressData.autonomy_readiness || 0) * 100}%`,
                height: "100%", background: "#8b5cf6", borderRadius: "4px",
              }} />
            </div>
            <div style={{ fontSize: "11px", color: "#888" }}>
              {((progressData.autonomy_readiness || 0) * 100).toFixed(1)}% ready
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "#fff" }) {
  return (
    <div style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: "8px", padding: "12px" }}>
      <div style={{ fontSize: "11px", color: "#888", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "20px", fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function MiniStat({ label, value, color = "#fff" }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: "18px", fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: "10px", color: "#888" }}>{label}</div>
    </div>
  );
}

function CompletionItem({ label, done }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
      <span style={{
        width: "16px", height: "16px", borderRadius: "4px", display: "flex",
        alignItems: "center", justifyContent: "center", fontSize: "10px",
        background: done ? "#059669" : "#333", color: done ? "#fff" : "#666",
        border: done ? "none" : "1px solid #555",
      }}>
        {done ? "✓" : ""}
      </span>
      <span style={{ fontSize: "12px", color: done ? "#aaa" : "#555" }}>{label}</span>
    </div>
  );
}
